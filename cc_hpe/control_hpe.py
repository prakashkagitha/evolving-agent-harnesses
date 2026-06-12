"""Deterministic controller for HARNESS-PROMPT EVOLUTION.

Genotype = FOUR role-prompts (brief per specialist {space_control, combat, food} + a referee prompt)
for a fixed decomposition harness. A genotype is realized R times (Haiku codes each specialist from its
brief + the referee from its prompt; the cc_decomp scaffold assembles one bot); fitness = mean ladder
win-rate over the R bots. Verified gate = two-sample bootstrap (reused from cc_prompt). GEPA evolves one
role-prompt per lens; CORE reflects contrastively over winner/loser prompt-SETS into an insight bank.

Reuses: cc_prompt.control_prompt (two-sample gate, score-pop, representative, safe bot),
cc_alloc.recipe (decomposition assembly), cc_decomp.control (select/finalize/population-summary/scoring),
cc_core (bank/ingest/credit). MAXW from CC_MAXW env (clean scoring; lower for parallel runs).
"""
import argparse
import json
import os
import shutil
from pathlib import Path

from cc_decomp import control as dctrl
from cc_decomp import harness, store
from cc_core import control as ccore
from cc_core import bank as bankmod
from cc_core import reflect as creflect
from cc_alloc import recipe
from cc_prompt import control_prompt as cp

from . import seeds

dctrl.MAXW = int(os.environ.get("CC_MAXW", "16"))
ROOT = Path(__file__).resolve().parent.parent
LADDER_SRC = {"weak": ROOT / "cc_decomp" / "ladder" / "weak.py",
              "moderate": ROOT / "cc_gepa" / "opponents" / "greedy_bot.py",
              "strong": ROOT / "cc_decomp" / "ladder" / "strong.py"}
CONCERNS = seeds.CONCERNS                      # fixed 3 specialists
ROLES = seeds.ROLES                            # concerns + "referee" = the 4 evolvable prompts / GEPA lenses
RUNGS = ["weak", "moderate", "strong"]


def emit(obj):
    print(json.dumps(obj))
    return obj


# ----------------------------------------------------------------- genotype I/O
def prompt_dir(out, gen, aid):
    return store.agent_dir(out, gen, aid) / "prompts"


def load_set(out, gen, aid):
    d = prompt_dir(out, gen, aid)
    return {r: store.read_text(d / f"{r}.md") for r in ROLES}


def save_set(out, gen, geno):
    d = store.agent_dir(out, gen, geno["id"])
    for r in ROLES:
        store.write_text(d / "prompts" / f"{r}.md", geno["prompts"].get(r, ""))
    store.write_json(d / "lineage.json", geno.get("lineage", {}))


def _clone_prompts(out, pgen, pid, cgen, cid):
    """Copy the parent's 4 role-prompts into the child (the mutator then edits in place)."""
    src = load_set(out, pgen, pid)
    cd = store.agent_dir(out, cgen, cid)
    for r in ROLES:
        store.write_text(cd / "prompts" / f"{r}.md", src.get(r, ""))


# ----------------------------------------------------------------- init
def cmd_init(a):
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for rung, src in LADDER_SRC.items():
        store.write_text(store.ladder_path(out, rung), Path(src).read_text())
    cdir = out / "contracts"
    store.write_text(cdir / "specialist_contract.txt", harness.SPECIALIST_CONTRACT)
    store.write_text(cdir / "referee_contract.txt", harness.REFEREE_CONTRACT)
    store.write_json(cdir / "specialist_concerns.json", harness.SPECIALIST_CONCERNS)
    sp = seeds.seed_prompt_sets()[: a.pop]
    for g in sp:
        save_set(out, 0, g)
    store.write_json(store.gen_dir(out, 0) / "population.json",
                     {"gen": 0, "ids": [g["id"] for g in sp], "carried": [], "new_ids": [g["id"] for g in sp]})
    cfg = {"out": str(out), "optimizer": a.optimizer, "seed": a.seed, "generations": a.generations,
           "pop": a.pop, "survivors": a.survivors, "R": a.R, "sims_eval": a.sims_eval,
           "concerns": CONCERNS, "roles": ROLES, "lenses": ROLES,
           "ladder": {"weak": "naive food-seeker", "moderate": "greedy flood-fill (CodeClash bench)",
                      "strong": "flood-fill + head-to-head + space-guard"}}
    store.write_json(out / "config.json", cfg)
    if a.optimizer == "core":
        b = bankmod.Bank(); b.save(ccore.bank_path(out)); ccore._snap(b, 0, out)
    return emit({"ok": True, "optimizer": a.optimizer, "R": a.R, "concerns": CONCERNS,
                 "seed_ids": [g["id"] for g in sp]})


# ----------------------------------------------------------------- eval (R replicate harness builds)
def cmd_eval_plan(a):
    out, gen, aid = a.out, a.gen, a.agent
    d = store.agent_dir(out, gen, aid)
    for r in ROLES:                            # ensure the (possibly mutator-written) prompts are on disk
        store.write_text(d / "prompts" / f"{r}.md", load_set(out, gen, aid)[r])
    exists = bool(store.read_json(d / "metrics.json", {})) and (d / "evals.json").exists()
    return emit({"ok": True, "gen": gen, "agent": aid, "R": a.R, "concerns": CONCERNS, "exists": exists,
                 "prompt_dir": str(d / "prompts")})


def cmd_eval_score(a):
    """Assemble each of the R replicate harness builds (Haiku already wrote repl_<r>/specialists/*),
    score cleanly; fitness = MEAN ladder win-rate over the R bots; pooled per-(bot,game) outcomes for the
    two-sample gate; produced bot = a representative realization."""
    out, gen, aid = a.out, a.gen, a.agent
    d = store.agent_dir(out, gen, aid)
    cand_dir = d / "candidates"; cand_dir.mkdir(parents=True, exist_ok=True)
    bots, bot_means, per_rung_sum, pooled, rep_paths = {}, [], {r: [] for r in RUNGS}, [], []
    for r in range(a.R):
        spec_dir = d / f"repl_{r}" / "specialists"
        dest = cand_dir / f"bot_{r}.py"
        ok_asm, loaded = recipe.assemble_decomp_candidate(spec_dir, CONCERNS, True, dest)
        if not ok_asm or not dest.exists():
            bots[f"bot_{r}"] = {"valid": False, "reason": "assemble failed", "mean": 0.0}
            bot_means.append(0.0); rep_paths.append(str(dest))
            for rr in RUNGS:
                pooled += [0] * a.sims_eval
            continue
        ok, reason = dctrl._validate(str(dest))
        if not ok:
            bots[f"bot_{r}"] = {"valid": False, "reason": reason, "mean": 0.0}
            bot_means.append(0.0); rep_paths.append(str(dest))
            for rr in RUNGS:
                pooled += [0] * a.sims_eval
            continue
        per = dctrl._per_game_vs_ladder(out, f"{aid}_b{r}", str(dest), a.sims_eval, a.seed, str(cand_dir / "_score"))
        tot_k = tot_n = 0; prr = {}
        for rr in RUNGS:
            g = per.get(rr, [])
            prr[rr] = (sum(g) / len(g)) if g else 0.0
            per_rung_sum[rr].append(prr[rr]); pooled += list(g); tot_k += sum(g); tot_n += len(g)
        mean = tot_k / max(tot_n, 1)
        bots[f"bot_{r}"] = {"valid": True, "mean": mean, "per_rung": prr, "loaded": loaded}
        bot_means.append(mean); rep_paths.append(str(dest))
    fitness = (sum(bot_means) / len(bot_means)) if bot_means else 0.0
    per_rung = {r: (sum(v) / len(v)) if v else 0.0 for r, v in per_rung_sum.items()}
    store.write_json(d / "evals.json", {"bots": bots, "bot_means": bot_means, "pooled_games": pooled,
                                        "fitness": fitness, "R": a.R, "sims_eval": a.sims_eval})
    m = store.read_json(d / "metrics.json", {})
    m.update({"id": aid, "ladder_fitness": fitness, "per_rung": per_rung, "sims": a.sims_eval,
              "seed": a.seed, "R": a.R, "R_valid": sum(1 for b in bots.values() if b.get("valid"))})
    store.write_json(d / "metrics.json", m)
    rep = cp._representative(bot_means)
    pb = d / "produced_bot"; pb.mkdir(parents=True, exist_ok=True)
    if rep is not None and rep < len(rep_paths) and Path(rep_paths[rep]).exists():
        shutil.copy(rep_paths[rep], pb / "main.py")
    else:
        store.write_text(pb / "main.py", cp._SAFE_BOT)
    return emit({"ok": True, "gen": gen, "agent": aid, "fitness": round(fitness, 4),
                 "R_valid": m["R_valid"], "per_rung": {r: round(v, 3) for r, v in per_rung.items()}})


# ----------------------------------------------------------------- reused: score-pop, admit (two-sample)
def cmd_score_pop(a):
    return cp.cmd_score_pop(a)


def cmd_admit(a):
    return cp.cmd_admit(a)


# ----------------------------------------------------------------- prompt-set weakness (for breeding)
def _set_weakness(out, gen, aid):
    m = store.read_json(store.agent_dir(out, gen, aid) / "metrics.json", {})
    per = m.get("per_rung", {})
    ps = load_set(out, gen, aid)
    parts = []
    rw = sorted(((r, per[r]) for r in per), key=lambda t: t[1])
    if rw:
        parts.append(", ".join(f"weak vs {r} rung (win-rate {wr:.2f})" for r, wr in rw[:2]))
    parts.append("prompts: " + " || ".join(f"[{role}] {(ps.get(role,'') or '')[:110]}" for role in ROLES))
    return ". ".join(parts)


# ----------------------------------------------------------------- GEPA breeding (per-role lens)
def cmd_breed_plan_gepa(a):
    rows = dctrl._ranked(a.out, a.gen)
    survivors = rows[: a.survivors]
    if not survivors:
        return emit({"ok": False, "error": "no survivors"})
    n_off = max(0, a.pop - a.survivors); ng = a.gen + 1; plan = []
    for i in range(n_off):
        parent = survivors[i % len(survivors)]["id"]
        lens = ROLES[i % len(ROLES)]           # which role-prompt this child edits
        new_id = f"g{ng:02d}_{i:02d}"
        cd = store.agent_dir(a.out, ng, new_id)
        exists = (cd / "prompts" / "referee.md").exists()
        if not exists:
            cd.mkdir(parents=True, exist_ok=True)
            _clone_prompts(a.out, a.gen, parent, ng, new_id)   # child starts as a clone of the parent prompt-set
            store.write_json(cd / "lineage.json", {"parent_id": parent, "parent_gen": a.gen, "lens": lens,
                             "origin": "gepa_mutation", "changed_components": [lens], "diff": ""})
        plan.append({"new_id": new_id, "parent_id": parent, "parent_gen": a.gen, "lens": lens,
                     "type": "mutation", "exists": exists})
    return emit({"ok": True, "gen": a.gen, "next_gen": ng,
                 "survivors": [s["id"] for s in survivors], "plan": plan})


# ----------------------------------------------------------------- CORE breeding
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
            "weakness": _set_weakness(a.out, a.gen, p["loser_id"]),
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
    n_off = max(0, a.pop - a.survivors); ng = a.gen + 1; plan, dirty = [], False
    for i in range(n_off):
        parent = survivors[i % len(survivors)]["id"]
        new_id = f"g{ng:02d}_{i:02d}"
        cd = store.agent_dir(a.out, ng, new_id)
        exists = (cd / "prompts" / "referee.md").exists()
        if exists:
            used = store.read_json(cd / "lineage.json", {}).get("lessons_used", [])
        else:
            weakness = _set_weakness(a.out, a.gen, parent)
            lessons = b.retrieve(weakness, a.topk, deterministic=False, mark=True); dirty = True
            used = [l["id"] for l in lessons]
            cd.mkdir(parents=True, exist_ok=True)
            _clone_prompts(a.out, a.gen, parent, ng, new_id)   # child starts as a clone of the parent prompt-set
            store.write_json(cd / "lineage.json", {"parent_id": parent, "parent_gen": a.gen, "lens": "core",
                             "origin": "core_mutation", "lessons_used": used, "changed_components": [], "diff": ""})
            store.write_json(cd / "breed_context.json", {
                "parent_id": parent, "parent_gen": a.gen,
                "parent_dir": str(store.agent_dir(a.out, a.gen, parent)), "weakness": weakness,
                "lessons": [{"id": l["id"], "text": l["text"], "label": l["label"]} for l in lessons]})
        plan.append({"new_id": new_id, "parent_id": parent, "parent_gen": a.gen, "lens": "core",
                     "type": "mutation", "exists": exists, "n_lessons": len(used)})
    if dirty:
        b.save(ccore.bank_path(a.out))
    return emit({"ok": True, "gen": a.gen, "next_gen": ng,
                 "survivors": [s["id"] for s in survivors], "plan": plan})


# ----------------------------------------------------------------- final comparison (offline; capped sims)
def cmd_final_compare(a):
    out = a.out; cfg = store.config(out); R = cfg.get("R", 3)
    g = 0
    while store.gen_dir(out, g + 1).exists():
        g += 1
    rows = dctrl._ranked(out, g); champ = rows[0]["id"] if rows else None
    g0 = dctrl._ranked(out, 0); base = g0[0]["id"] if g0 else None
    def clean(gen, aid, tag):
        cd = store.agent_dir(out, gen, aid) / "candidates"; means = []
        for r in range(R):
            p = cd / f"bot_{r}.py"
            if not p.exists() or not dctrl._validate(str(p))[0]:
                means.append(0.0); continue
            per = dctrl._per_game_vs_ladder(out, f"{tag}_b{r}", str(p), a.sims, a.seed, str(cd / "_fc"), use_cache=False)
            k = sum(sum(per.get(rr, [])) for rr in RUNGS); n = sum(len(per.get(rr, [])) for rr in RUNGS)
            means.append(k / max(n, 1))
        return round(sum(means) / len(means), 4) if means else 0.0
    res = {"final_gen": g, "champion": champ, "gen0_best": base, "sims": a.sims,
           "champion_fitness": clean(g, champ, "champ") if champ else None,
           "gen0_best_fitness": clean(0, base, "g0") if base else None}
    store.write_json(Path(out) / "final" / "compare.json", res)
    return emit({"ok": True, **res})


# ----------------------------------------------------------------- CLI
def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p):
        p.add_argument("--out", required=True)

    p = sub.add_parser("init"); common(p)
    p.add_argument("--optimizer", choices=["gepa", "core"], required=True)
    p.add_argument("--seed", type=int, default=0); p.add_argument("--generations", type=int, default=6)
    p.add_argument("--pop", type=int, default=8); p.add_argument("--survivors", type=int, default=4)
    p.add_argument("--R", type=int, default=3); p.add_argument("--sims-eval", dest="sims_eval", type=int, default=100)
    p.set_defaults(fn=cmd_init)

    for name, fn in (("eval-plan", cmd_eval_plan), ("eval-score", cmd_eval_score)):
        p = sub.add_parser(name); common(p)
        p.add_argument("--gen", type=int, required=True); p.add_argument("--agent", required=True)
        p.add_argument("--R", type=int, default=3); p.add_argument("--sims-eval", dest="sims_eval", type=int, default=100)
        p.add_argument("--seed", type=int, default=0); p.set_defaults(fn=fn)

    p = sub.add_parser("score-pop"); common(p)
    p.add_argument("--gen", type=int, required=True); p.set_defaults(fn=cmd_score_pop)

    p = sub.add_parser("select"); common(p)
    p.add_argument("--gen", type=int, required=True); p.add_argument("--survivors", type=int, default=4)
    p.set_defaults(fn=dctrl.cmd_select)

    p = sub.add_parser("admit"); common(p)
    p.add_argument("--gen", type=int, required=True); p.add_argument("--child", required=True)
    p.add_argument("--parent-gen", dest="parent_gen", type=int, required=True); p.add_argument("--parent", required=True)
    p.set_defaults(fn=cmd_admit)

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
    p.add_argument("--sims", type=int, default=300); p.add_argument("--seed", type=int, default=0)
    p.set_defaults(fn=cmd_final_compare)

    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
