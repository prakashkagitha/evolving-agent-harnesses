"""Deterministic controller for the budget-constrained allocation search.

Reuses cc_decomp's controller for everything genotype-agnostic (clean ladder scoring, the paired
verified-acceptance gate, selection, generation reconciliation) and cc_core's lesson bank for the
CORE arm. The NEW logic is recipe-specific: execute a budget-B allocation (drafts / specialists+merge
/ revisions) into one produced bot, and recipe-aware breeding for GEPA (lens mutation) and CORE
(contrastive reflection over winner/loser RECIPES). Both arms run identically except the breeder.

Clean scoring everywhere (MAXW=16) so per-move-latency under CPU contention never enters fitness.
Each command prints a single JSON object on its last stdout line (the workflow reads it).
"""
import argparse
import io
import contextlib
import json
import shutil
from pathlib import Path

from cc_decomp import control as dctrl
from cc_decomp import harness, store
from cc_core import control as ccore           # bank_path / cmd_core_ingest / cmd_core_credit / cmd_bank_status
from cc_core import bank as bankmod
from cc_core import reflect as creflect

from . import recipe

dctrl.MAXW = 16                                  # CLEAN scoring (selection + candidates + admit) — no contention bias

ROOT = Path(__file__).resolve().parent.parent
LADDER_SRC = {"weak": ROOT / "cc_decomp" / "ladder" / "weak.py",
              "moderate": ROOT / "cc_gepa" / "opponents" / "greedy_bot.py",
              "strong": ROOT / "cc_decomp" / "ladder" / "strong.py"}
LENSES = ["alloc", "concerns", "prompt", "mix"]


def emit(obj):
    print(json.dumps(obj))
    return obj


def _cands_path(out, gen, aid):
    return store.agent_dir(out, gen, aid) / "candidates.json"


def _score_candidate(out, path, sims, seed):
    ok, reason = dctrl._validate(path)
    if not ok:
        return -1.0, {}, reason
    wd = str(Path(path).parent / "_score")
    per, mean = dctrl._score_vs_ladder(out, f"cand_{abs(hash(str(path))) % 99999}", str(path), sims, seed, wd)
    return mean, per, "ok"


# ----------------------------------------------------------------- init
def cmd_init(a):
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for rung, src in LADDER_SRC.items():
        store.write_text(store.ladder_path(out, rung), Path(src).read_text())
    cdir = out / "contracts"
    store.write_text(cdir / "simple_bot_contract.txt", harness.SIMPLE_BOT_CONTRACT)
    store.write_text(cdir / "specialist_contract.txt", harness.SPECIALIST_CONTRACT)
    store.write_text(cdir / "referee_contract.txt", harness.REFEREE_CONTRACT)
    store.write_json(cdir / "specialist_concerns.json", harness.SPECIALIST_CONCERNS)
    seeds = recipe.seed_recipes(a.B)[:a.pop]
    for g in seeds:
        recipe.save(out, 0, g)
    store.write_json(store.gen_dir(out, 0) / "population.json",
                     {"gen": 0, "ids": [g["id"] for g in seeds], "carried": [], "new_ids": [g["id"] for g in seeds]})
    cfg = {"out": str(out), "B": a.B, "optimizer": a.optimizer, "seed": a.seed,
           "generations": a.generations, "pop": a.pop, "survivors": a.survivors,
           "sims_cand": a.sims_cand, "sims_evolve": a.sims_evolve, "sims_admit": a.sims_admit,
           "sims_final": a.sims_final, "menu": recipe.MENU, "lenses": LENSES,
           "ladder": {"weak": "naive food-seeker", "moderate": "greedy flood-fill (CodeClash bench)",
                      "strong": "flood-fill + head-to-head + space-guard"}}
    store.write_json(out / "config.json", cfg)
    if a.optimizer == "core":
        b = bankmod.Bank(); b.save(ccore.bank_path(out)); ccore._snap(b, 0, out)
    return emit({"ok": True, "B": a.B, "optimizer": a.optimizer,
                 "seed_ids": [g["id"] for g in seeds],
                 "seed_allocs": {g["id"]: recipe.alloc_label(g["alloc"]) for g in seeds}})


# ----------------------------------------------------------------- recipe execution
def cmd_recipe_plan(a):
    """Load + REPAIR the recipe to a valid budget-B allocation (robust to whatever the LLM wrote),
    save it back, and tell the workflow what to run. exists => produced bot already built (resume)."""
    out, gen, aid = a.out, a.gen, a.agent
    geno = recipe.repair(recipe.load(out, gen, aid), a.B)
    geno["id"] = aid
    recipe.save(out, gen, geno)
    d = store.agent_dir(out, gen, aid)
    store.write_text(d / "draft_prompt.md", geno["draft_prompt"])
    al = geno["alloc"]
    n_spec = al["n_spec"]
    concerns = geno["concerns"][:n_spec]
    exists = (d / "produced_bot" / "main.py").exists() and bool(store.read_json(d / "metrics.json", {}))
    return emit({"ok": True, "gen": gen, "agent": aid, "exists": exists,
                 "n_draft": al["n_draft"], "n_spec": n_spec, "do_merge": al["do_merge"],
                 "n_revise": al["n_revise"], "concerns": concerns,
                 "alloc_label": recipe.alloc_label(al), "B": recipe.alloc_sum(al)})


def cmd_recipe_build_base(a):
    """Assemble the merge candidate (if do_merge) from specialist files, then score every base
    candidate (drafts + merge) cleanly; pick the best -> best.py + feedback.json for revision."""
    out, gen, aid = a.out, a.gen, a.agent
    d = store.agent_dir(out, gen, aid)
    geno = recipe.repair(recipe.load(out, gen, aid), a.B)
    al = geno["alloc"]; concerns = geno["concerns"][: al["n_spec"]]
    cand_dir = d / "candidates"; cand_dir.mkdir(parents=True, exist_ok=True)
    cands = {}
    # drafts
    for k in range(al["n_draft"]):
        p = cand_dir / f"draft_{k}.py"
        if p.exists():
            src = harness.clean_code(p.read_text())
            store.write_text(p, src)
            cands[f"draft_{k}"] = str(p)
    # merge candidate from specialists
    if al["do_merge"] and al["n_spec"] >= 1:
        ok, loaded = recipe.assemble_decomp_candidate(d / "specialists", concerns, True, cand_dir / "merge.py")
        if ok:
            cands["merge"] = str(cand_dir / "merge.py")
    elif al["n_spec"] >= 1 and al["n_draft"] == 0:
        # specialists but no merge call: assemble with the deterministic weighted_vote referee
        ok, loaded = recipe.assemble_decomp_candidate(d / "specialists", concerns, False, cand_dir / "merge.py")
        if ok:
            cands["merge"] = str(cand_dir / "merge.py")
    scored = {}
    best, best_score = None, -2.0
    for cid, p in cands.items():
        s, per, reason = _score_candidate(out, p, a.sims_cand, a.seed)
        scored[cid] = {"path": p, "score": s, "per_rung": per, "reason": reason}
        if s > best_score:
            best_score, best = s, cid
    store.write_json(_cands_path(out, gen, aid), {"candidates": scored, "best": best, "best_score": best_score})
    pb = d / "produced_bot"; pb.mkdir(parents=True, exist_ok=True)
    if best is not None:
        shutil.copy(scored[best]["path"], pb / "best.py")
        fb = dctrl._refine_score(out, str(pb / "best.py"), max(24, a.sims_cand // 2), a.seed, True, str(pb / "_fb"))
        store.write_json(pb / "feedback.json", fb)
    return emit({"ok": True, "gen": gen, "agent": aid, "n_candidates": len(cands),
                 "best": best, "best_score": round(best_score, 4),
                 "has_revise": al["n_revise"] > 0})


def cmd_recipe_revise_keep(a):
    """Score a revision candidate; keep-if-not-worse (update best.py + feedback)."""
    out, gen, aid = a.out, a.gen, a.agent
    d = store.agent_dir(out, gen, aid); pb = d / "produced_bot"
    cand_dir = d / "candidates"
    rp = cand_dir / f"revise_{a.round}.py"
    rec = store.read_json(_cands_path(out, gen, aid), {"candidates": {}, "best": None, "best_score": -2.0})
    if not rp.exists():
        return emit({"ok": True, "kept": False, "reason": "no revision written", "best_score": round(rec.get("best_score", -2.0), 4)})
    store.write_text(rp, harness.clean_code(rp.read_text()))
    s, per, reason = _score_candidate(out, str(rp), a.sims_cand, a.seed)
    rec["candidates"][f"revise_{a.round}"] = {"path": str(rp), "score": s, "per_rung": per, "reason": reason}
    kept = s >= rec.get("best_score", -2.0) - 1e-9 and s >= 0
    if kept:
        rec["best"], rec["best_score"] = f"revise_{a.round}", s
        shutil.copy(rp, pb / "best.py")
        fb = dctrl._refine_score(out, str(pb / "best.py"), max(24, a.sims_cand // 2), a.seed, True, str(pb / "_fb"))
        store.write_json(pb / "feedback.json", fb)
    store.write_json(_cands_path(out, gen, aid), rec)
    return emit({"ok": True, "kept": kept, "round": a.round, "new_score": round(s, 4),
                 "best_score": round(rec["best_score"], 4), "reason": reason})


def cmd_recipe_finalize(a):
    """The chosen best candidate becomes the produced bot. (score-pop scores it officially next.)"""
    out, gen, aid = a.out, a.gen, a.agent
    pb = store.agent_dir(out, gen, aid) / "produced_bot"
    best = pb / "best.py"
    if not best.exists():
        # no valid candidate at all -> write a trivial safe bot so scoring yields 0 rather than crashing
        store.write_text(pb / "main.py", _SAFE_BOT)
        return emit({"ok": True, "agent": aid, "valid": False, "note": "no valid candidate"})
    shutil.copy(best, pb / "main.py")
    ok, reason = dctrl._validate(str(pb / "main.py"))
    if not ok:
        store.write_text(pb / "main.py", _SAFE_BOT)
    return emit({"ok": True, "agent": aid, "valid": ok, "reason": reason})


_SAFE_BOT = '''def info():
    return {"apiversion":"1","author":"safe","color":"#888888","head":"default","tail":"default"}
def start(g): pass
def end(g): pass
def move(game_state):
    b=game_state["board"]; w,h=b["width"],b["height"]; hd=game_state["you"]["body"][0]
    for mv,(dx,dy) in {"up":(0,1),"down":(0,-1),"left":(-1,0),"right":(1,0)}.items():
        x,y=hd["x"]+dx,hd["y"]+dy
        if 0<=x<w and 0<=y<h: return {"move":mv}
    return {"move":"up"}
'''


# ----------------------------------------------------------------- recipe weakness (for breeding)
def _recipe_weakness(out, gen, aid):
    geno = recipe.load(out, gen, aid)
    m = store.read_json(store.agent_dir(out, gen, aid) / "metrics.json", {})
    per = m.get("per_rung", {})
    parts = [f"allocation {recipe.alloc_label(geno.get('alloc', {}))} (drafts={geno.get('alloc',{}).get('n_draft')}, "
             f"specialists={geno.get('alloc',{}).get('n_spec')}, merge={geno.get('alloc',{}).get('do_merge')}, "
             f"revisions={geno.get('alloc',{}).get('n_revise')})"]
    rw = sorted(((r, per[r]) for r in per), key=lambda t: t[1])
    if rw:
        parts.append(", ".join(f"weak vs {r} (win-rate {wr:.2f})" for r, wr in rw[:2]))
    parts.append("prompt: " + (geno.get("draft_prompt", "") or "")[:200])
    return ". ".join(parts)


# ----------------------------------------------------------------- GEPA breeding (lens mutation)
def cmd_breed_plan_gepa(a):
    rows = dctrl._ranked(a.out, a.gen)
    survivors = rows[: a.survivors]
    if not survivors:
        return emit({"ok": False, "error": "no survivors"})
    n_off = max(0, a.pop - a.survivors)
    ng = a.gen + 1
    plan = []
    for i in range(n_off):
        parent = survivors[i % len(survivors)]["id"]
        lens = LENSES[i % len(LENSES)]
        new_id = f"g{ng:02d}_{i:02d}"
        cd = store.agent_dir(a.out, ng, new_id)
        exists = (cd / "recipe.json").exists()
        if not exists:
            cd.mkdir(parents=True, exist_ok=True)
            store.write_json(cd / "lineage.json", {"parent_id": parent, "parent_gen": a.gen, "lens": lens,
                             "origin": "gepa_mutation", "changed_components": [], "diff": ""})
        plan.append({"new_id": new_id, "parent_id": parent, "parent_gen": a.gen, "lens": lens,
                     "type": "mutation", "exists": exists})
    return emit({"ok": True, "gen": a.gen, "next_gen": ng,
                 "survivors": [s["id"] for s in survivors], "plan": plan})


# ----------------------------------------------------------------- CORE breeding (contrastive)
def cmd_core_reflect_plan(a):
    rows = dctrl._ranked(a.out, a.gen)
    pairs = creflect.form_pairs(rows, a.pairs, margin=getattr(a, "margin", 0.03))
    refl_dir = ccore.bank_dir(a.out) / "reflections" / f"gen_{a.gen:02d}"
    plan = []
    for i, p in enumerate(pairs):
        plan.append({
            "idx": i, "winner_id": p["winner_id"], "loser_id": p["loser_id"],
            "winner_dir": str(store.agent_dir(a.out, a.gen, p["winner_id"])),
            "loser_dir": str(store.agent_dir(a.out, a.gen, p["loser_id"])),
            "winner_fitness": round(p["winner_fitness"], 4), "loser_fitness": round(p["loser_fitness"], 4),
            "winner_alloc": recipe.alloc_label(recipe.load(a.out, a.gen, p["winner_id"]).get("alloc", {})),
            "loser_alloc": recipe.alloc_label(recipe.load(a.out, a.gen, p["loser_id"]).get("alloc", {})),
            "weakness": _recipe_weakness(a.out, a.gen, p["loser_id"]),
            "lessons_path": str(refl_dir / f"pair_{i:02d}.json"),
        })
    store.write_json(refl_dir / "reflect_plan.json", {"gen": a.gen, "pairs": plan})
    return emit({"ok": True, "gen": a.gen, "n_pairs": len(plan), "plan": plan})


def cmd_core_breed_plan(a):
    rows = dctrl._ranked(a.out, a.gen)
    survivors = rows[: a.survivors]
    if not survivors:
        return emit({"ok": False, "error": "no survivors"})
    b = bankmod.Bank.load(ccore.bank_path(a.out))
    n_off = max(0, a.pop - a.survivors)
    ng = a.gen + 1
    plan, dirty = [], False
    for i in range(n_off):
        parent = survivors[i % len(survivors)]["id"]
        new_id = f"g{ng:02d}_{i:02d}"
        cd = store.agent_dir(a.out, ng, new_id)
        exists = (cd / "recipe.json").exists()
        if exists:
            used = store.read_json(cd / "lineage.json", {}).get("lessons_used", [])
        else:
            weakness = _recipe_weakness(a.out, a.gen, parent)
            lessons = b.retrieve(weakness, a.topk, deterministic=False, mark=True); dirty = True
            used = [l["id"] for l in lessons]
            cd.mkdir(parents=True, exist_ok=True)
            store.write_json(cd / "lineage.json", {"parent_id": parent, "parent_gen": a.gen, "lens": "core",
                             "origin": "core_mutation", "lessons_used": used, "changed_components": [], "diff": ""})
            store.write_json(cd / "breed_context.json", {
                "parent_id": parent, "parent_gen": a.gen,
                "parent_dir": str(store.agent_dir(a.out, a.gen, parent)),
                "weakness": weakness,
                "lessons": [{"id": l["id"], "text": l["text"], "label": l["label"]} for l in lessons]})
        plan.append({"new_id": new_id, "parent_id": parent, "parent_gen": a.gen, "lens": "core",
                     "type": "mutation", "exists": exists, "n_lessons": len(used)})
    if dirty:
        b.save(ccore.bank_path(a.out))
    return emit({"ok": True, "gen": a.gen, "next_gen": ng,
                 "survivors": [s["id"] for s in survivors], "plan": plan})


# ----------------------------------------------------------------- final comparison (offline, clean)
def cmd_final_compare(a):
    out = a.out
    g = 0
    while store.gen_dir(out, g + 1).exists():
        g += 1
    rows = dctrl._ranked(out, g)
    champ = rows[0]["id"] if rows else None
    wd = str(Path(out) / "final" / "_cmp")
    res = {}
    if champ:
        res["champion"] = {"id": champ, **dctrl._final_one(out, "champion", str(store.produced_bot_path(out, g, champ)), a.sims, a.seed, wd)}
    # baseline = the best_of_b seed recipe's produced bot (the no-search control)
    base_bot = store.produced_bot_path(out, 0, "best_of_b")
    if base_bot.exists():
        res["best_of_b"] = dctrl._final_one(out, "best_of_b", str(base_bot), a.sims, a.seed, wd)
    store.write_json(Path(out) / "final" / "compare.json",
                     {"final_gen": g, "champion_id": champ, "sims": a.sims, "results": res})
    return emit({"ok": True, "final_gen": g, "champion": champ,
                 "champion_mean": res.get("champion", {}).get("ladder_mean", {}).get("winrate"),
                 "best_of_b_mean": res.get("best_of_b", {}).get("ladder_mean", {}).get("winrate")})


# ----------------------------------------------------------------- CLI
def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p):
        p.add_argument("--out", required=True)

    p = sub.add_parser("init"); common(p)
    p.add_argument("--B", type=int, default=8); p.add_argument("--optimizer", choices=["gepa", "core"], required=True)
    p.add_argument("--seed", type=int, default=0); p.add_argument("--generations", type=int, default=4)
    p.add_argument("--pop", type=int, default=8); p.add_argument("--survivors", type=int, default=4)
    p.add_argument("--sims-cand", dest="sims_cand", type=int, default=60)
    p.add_argument("--sims-evolve", dest="sims_evolve", type=int, default=120)
    p.add_argument("--sims-admit", dest="sims_admit", type=int, default=200)
    p.add_argument("--sims-final", dest="sims_final", type=int, default=1500)
    p.set_defaults(fn=cmd_init)

    for name, fn in (("recipe-plan", cmd_recipe_plan), ("recipe-build-base", cmd_recipe_build_base),
                     ("recipe-revise-keep", cmd_recipe_revise_keep), ("recipe-finalize", cmd_recipe_finalize)):
        p = sub.add_parser(name); common(p)
        p.add_argument("--gen", type=int, required=True); p.add_argument("--agent", required=True)
        p.add_argument("--round", type=int, default=0); p.add_argument("--B", type=int, default=8)
        p.add_argument("--sims-cand", dest="sims_cand", type=int, default=60); p.add_argument("--seed", type=int, default=0)
        p.set_defaults(fn=fn)

    p = sub.add_parser("score-pop"); common(p)
    p.add_argument("--gen", type=int, required=True); p.add_argument("--agent", default="")
    p.add_argument("--sims", type=int, default=120); p.add_argument("--seed", type=int, default=0)
    p.set_defaults(fn=dctrl.cmd_score_pop)

    p = sub.add_parser("select"); common(p)
    p.add_argument("--gen", type=int, required=True); p.add_argument("--survivors", type=int, default=4)
    p.set_defaults(fn=dctrl.cmd_select)

    p = sub.add_parser("admit"); common(p)
    p.add_argument("--gen", type=int, required=True); p.add_argument("--child", required=True)
    p.add_argument("--parent-gen", dest="parent_gen", type=int, required=True); p.add_argument("--parent", required=True)
    p.add_argument("--sims", type=int, default=200); p.add_argument("--seed", type=int, default=0)
    p.set_defaults(fn=dctrl.cmd_admit)

    p = sub.add_parser("finalize-gen"); common(p)
    p.add_argument("--gen", type=int, required=True); p.add_argument("--pop", type=int, default=8)
    p.add_argument("--survivors", type=int, default=4); p.set_defaults(fn=dctrl.cmd_finalize_gen)

    p = sub.add_parser("population-summary"); common(p)
    p.add_argument("--gen", type=int, required=True); p.set_defaults(fn=dctrl.cmd_population_summary)

    p = sub.add_parser("breed-plan-gepa"); common(p)
    p.add_argument("--gen", type=int, required=True); p.add_argument("--pop", type=int, default=8)
    p.add_argument("--survivors", type=int, default=4); p.set_defaults(fn=cmd_breed_plan_gepa)

    p = sub.add_parser("core-reflect-plan"); common(p)
    p.add_argument("--gen", type=int, required=True); p.add_argument("--pairs", type=int, default=4)
    p.add_argument("--margin", type=float, default=0.03); p.set_defaults(fn=cmd_core_reflect_plan)

    p = sub.add_parser("core-ingest"); common(p)
    p.add_argument("--gen", type=int, required=True); p.add_argument("--max-lessons", dest="max_lessons", type=int, default=4)
    p.add_argument("--plan", default=""); p.set_defaults(fn=ccore.cmd_core_ingest)

    p = sub.add_parser("core-breed-plan"); common(p)
    p.add_argument("--gen", type=int, required=True); p.add_argument("--pop", type=int, default=8)
    p.add_argument("--survivors", type=int, default=4); p.add_argument("--topk", type=int, default=3)
    p.set_defaults(fn=cmd_core_breed_plan)

    p = sub.add_parser("core-credit"); common(p)
    p.add_argument("--gen", type=int, required=True); p.set_defaults(fn=ccore.cmd_core_credit)

    p = sub.add_parser("bank-status"); common(p)
    p.set_defaults(fn=ccore.cmd_bank_status)

    p = sub.add_parser("final-compare"); common(p)
    p.add_argument("--sims", type=int, default=1500); p.add_argument("--seed", type=int, default=0)
    p.set_defaults(fn=cmd_final_compare)

    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
