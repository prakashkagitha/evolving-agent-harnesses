"""Deterministic controller for PURE PROMPT EVOLUTION (GEPA vs CORE).

Genotype = one bot-generation prompt. A prompt is evaluated by generating R independent single-shot
bots (the cheapest harness: 1 call/bot) and taking the MEAN ladder win-rate over them (Haiku
realization variance is large, so we measure expected quality over replicates). The verified gate is a
TWO-SAMPLE bootstrap over the pooled per-(bot,game) outcomes of child-prompt vs parent-prompt.

Reuses cc_decomp for clean ladder scoring / selection / generation reconciliation and cc_core's bank
for the CORE arm. MAXW=16 everywhere -> no contention/latency contamination of fitness. Each command
prints a single JSON object on its last stdout line (the workflow reads it).
"""
import argparse
import json
import os
import shutil
from pathlib import Path

import numpy as np

from cc_decomp import control as dctrl
from cc_decomp import harness, store
from cc_core import control as ccore
from cc_core import bank as bankmod
from cc_core import reflect as creflect

from . import seeds

# Clean scoring concurrency. Lower it (via CC_MAXW) when running two evolution workflows in PARALLEL
# on the same box, so the combined native-sim load stays under the core count (else BotServers miss the
# 500ms move deadline and fitness is silently corrupted).
dctrl.MAXW = int(os.environ.get("CC_MAXW", "16"))
ROOT = Path(__file__).resolve().parent.parent
LADDER_SRC = {"weak": ROOT / "cc_decomp" / "ladder" / "weak.py",
              "moderate": ROOT / "cc_gepa" / "opponents" / "greedy_bot.py",
              "strong": ROOT / "cc_decomp" / "ladder" / "strong.py"}
LENSES = ["strategy", "concept", "specificity", "fix"]
RUNGS = ["weak", "moderate", "strong"]


def emit(obj):
    print(json.dumps(obj))
    return obj


# ----------------------------------------------------------------- genotype I/O
def prompt_path(out, gen, aid):
    return store.agent_dir(out, gen, aid) / "prompt.md"


def load_prompt(out, gen, aid):
    return store.read_text(prompt_path(out, gen, aid))


def save_geno(out, gen, geno):
    d = store.agent_dir(out, gen, geno["id"])
    store.write_text(d / "prompt.md", geno["prompt"])
    store.write_json(d / "lineage.json", geno.get("lineage", {}))


# ----------------------------------------------------------------- init
def cmd_init(a):
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for rung, src in LADDER_SRC.items():
        store.write_text(store.ladder_path(out, rung), Path(src).read_text())
    store.write_text(out / "contracts" / "simple_bot_contract.txt", harness.SIMPLE_BOT_CONTRACT)
    sp = seeds.seed_prompts()[: a.pop]
    for g in sp:
        save_geno(out, 0, g)
    store.write_json(store.gen_dir(out, 0) / "population.json",
                     {"gen": 0, "ids": [g["id"] for g in sp], "carried": [], "new_ids": [g["id"] for g in sp]})
    cfg = {"out": str(out), "optimizer": a.optimizer, "seed": a.seed, "generations": a.generations,
           "pop": a.pop, "survivors": a.survivors, "R": a.R, "sims_eval": a.sims_eval,
           "sims_final": a.sims_final, "lenses": LENSES,
           "ladder": {"weak": "naive food-seeker", "moderate": "greedy flood-fill (CodeClash bench)",
                      "strong": "flood-fill + head-to-head + space-guard"}}
    store.write_json(out / "config.json", cfg)
    if a.optimizer == "core":
        b = bankmod.Bank(); b.save(ccore.bank_path(out)); ccore._snap(b, 0, out)
    return emit({"ok": True, "optimizer": a.optimizer, "R": a.R, "seed_ids": [g["id"] for g in sp]})


# ----------------------------------------------------------------- prompt evaluation (R replicates)
def cmd_eval_plan(a):
    out, gen, aid = a.out, a.gen, a.agent
    d = store.agent_dir(out, gen, aid)
    store.write_text(d / "prompt.md", load_prompt(out, gen, aid))   # ensure present (mutator wrote it)
    exists = bool(store.read_json(d / "metrics.json", {})) and (d / "evals.json").exists()
    return emit({"ok": True, "gen": gen, "agent": aid, "R": a.R, "exists": exists,
                 "prompt_path": str(d / "prompt.md")})


def _representative(bot_means):
    """Index of the bot whose fitness is closest to the mean (a representative realization)."""
    if not bot_means:
        return None
    mu = sum(bot_means) / len(bot_means)
    return min(range(len(bot_means)), key=lambda i: abs(bot_means[i] - mu))


def cmd_eval_score(a):
    """Score the R generated bots cleanly; fitness = MEAN ladder win-rate over ALL R bots (an invalid
    generation scores 0 — a real quality signal of the prompt); store the pooled per-(bot,game)
    outcomes for the two-sample gate (pooled_mean == fitness); produced bot = a representative realization."""
    out, gen, aid = a.out, a.gen, a.agent
    d = store.agent_dir(out, gen, aid)
    cand_dir = d / "candidates"
    bots, bot_means, per_rung_sum, pooled = {}, [], {r: [] for r in RUNGS}, []
    rep_paths = []
    for r in range(a.R):
        p = cand_dir / f"bot_{r}.py"
        if not p.exists():
            continue
        src = harness.clean_code(p.read_text())
        store.write_text(p, src)
        ok, reason = dctrl._validate(str(p))
        if not ok:
            bots[f"bot_{r}"] = {"valid": False, "reason": reason, "mean": 0.0}
            bot_means.append(0.0); rep_paths.append(str(p))
            for rr in RUNGS:
                pooled += [0] * a.sims_eval  # invalid bot forfeits every game -> same sample count as a
                                             # valid bot, so pooled_mean == equal-weight fitness (the
                                             # two-sample gate then tests exactly what selection uses)
            continue
        per = dctrl._per_game_vs_ladder(out, f"{aid}_b{r}", str(p), a.sims_eval, a.seed, str(cand_dir / "_score"))
        tot_k = tot_n = 0
        prr = {}
        for rr in RUNGS:
            g = per.get(rr, [])
            prr[rr] = (sum(g) / len(g)) if g else 0.0
            per_rung_sum[rr].append(prr[rr])
            pooled += list(g)
            tot_k += sum(g); tot_n += len(g)
        mean = tot_k / max(tot_n, 1)
        bots[f"bot_{r}"] = {"valid": True, "mean": mean, "per_rung": prr}
        bot_means.append(mean); rep_paths.append(str(p))
    fitness = (sum(bot_means) / len(bot_means)) if bot_means else 0.0
    per_rung = {r: (sum(v) / len(v)) if v else 0.0 for r, v in per_rung_sum.items()}
    store.write_json(d / "evals.json", {"bots": bots, "bot_means": bot_means, "pooled_games": pooled,
                                        "fitness": fitness, "R": a.R, "sims_eval": a.sims_eval})
    m = store.read_json(d / "metrics.json", {})
    m.update({"id": aid, "ladder_fitness": fitness, "per_rung": per_rung, "sims": a.sims_eval,
              "seed": a.seed, "R": a.R, "R_valid": sum(1 for b in bots.values() if b.get("valid"))})
    store.write_json(d / "metrics.json", m)
    # produced bot = a representative realization (closest to the mean)
    rep = _representative(bot_means)
    pb = d / "produced_bot"; pb.mkdir(parents=True, exist_ok=True)
    if rep is not None and rep < len(rep_paths):
        shutil.copy(rep_paths[rep], pb / "main.py")
    else:
        store.write_text(pb / "main.py", _SAFE_BOT)
    return emit({"ok": True, "gen": gen, "agent": aid, "fitness": round(fitness, 4),
                 "R_valid": m["R_valid"], "per_rung": {r: round(v, 3) for r, v in per_rung.items()}})


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


# ----------------------------------------------------------------- score / select (reuse dctrl)
def cmd_score_pop(a):
    rows = dctrl._ranked(a.out, a.gen)            # reads metrics.ladder_fitness (written by eval-score)
    champ = rows[0] if rows else None
    return emit({"ok": True, "gen": a.gen, "ranking": rows,
                 "champion": champ["id"] if champ else None,
                 "champion_fitness": champ["ladder_fitness"] if champ else None})


# ----------------------------------------------------------------- two-sample verified gate
def _two_sample_boot(child, parent, iters=4000):
    c = np.asarray(child, dtype=float); p = np.asarray(parent, dtype=float)
    if c.size == 0 or p.size == 0:
        return (0.0, 0.0, 0.0)
    rng = np.random.RandomState(1234)
    cm = c[rng.randint(0, c.size, size=(iters, c.size))].mean(axis=1)
    pm = p[rng.randint(0, p.size, size=(iters, p.size))].mean(axis=1)
    diff = cm - pm
    return (float(c.mean() - p.mean()), float(np.percentile(diff, 2.5)), float(np.percentile(diff, 97.5)))


def cmd_admit(a):
    out = a.out
    cev = store.read_json(store.agent_dir(out, a.gen, a.child) / "evals.json", {})
    pev = store.read_json(store.agent_dir(out, a.parent_gen, a.parent) / "evals.json", {})
    delta, lo, hi = _two_sample_boot(cev.get("pooled_games", []), pev.get("pooled_games", []))
    admitted = bool(lo > 0.0)
    rec = {"parent_id": a.parent, "parent_gen": a.parent_gen,
           "child_fit": cev.get("fitness"), "parent_fit": pev.get("fitness"),
           "delta": delta, "ci_low": lo, "ci_high": hi, "admitted": admitted,
           "test": "two_sample_bootstrap"}
    cd = store.agent_dir(out, a.gen, a.child)
    m = store.read_json(cd / "metrics.json", {}); m["verified_vs_parent"] = rec; m.setdefault("id", a.child)
    store.write_json(cd / "metrics.json", m)
    return emit({"ok": True, "child": a.child, "admitted": admitted, "delta": delta,
                 "ci_low": lo, "ci_high": hi, "child_fit": rec["child_fit"], "parent_fit": rec["parent_fit"]})


# ----------------------------------------------------------------- prompt weakness (for breeding)
def _prompt_weakness(out, gen, aid):
    m = store.read_json(store.agent_dir(out, gen, aid) / "metrics.json", {})
    per = m.get("per_rung", {})
    parts = []
    rw = sorted(((r, per[r]) for r in per), key=lambda t: t[1])
    if rw:
        parts.append(", ".join(f"weak vs {r} rung (win-rate {wr:.2f})" for r, wr in rw[:2]))
    parts.append("prompt: " + (load_prompt(out, gen, aid) or "")[:300])
    return ". ".join(parts)


# ----------------------------------------------------------------- GEPA breeding
def cmd_breed_plan_gepa(a):
    rows = dctrl._ranked(a.out, a.gen)
    survivors = rows[: a.survivors]
    if not survivors:
        return emit({"ok": False, "error": "no survivors"})
    n_off = max(0, a.pop - a.survivors); ng = a.gen + 1; plan = []
    for i in range(n_off):
        parent = survivors[i % len(survivors)]["id"]
        lens = LENSES[i % len(LENSES)]
        new_id = f"g{ng:02d}_{i:02d}"
        cd = store.agent_dir(a.out, ng, new_id)
        exists = (cd / "prompt.md").exists()
        if not exists:
            cd.mkdir(parents=True, exist_ok=True)
            store.write_json(cd / "lineage.json", {"parent_id": parent, "parent_gen": a.gen, "lens": lens,
                             "origin": "gepa_mutation", "changed_components": ["prompt"], "diff": ""})
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
            "weakness": _prompt_weakness(a.out, a.gen, p["loser_id"]),
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
        exists = (cd / "prompt.md").exists()
        if exists:
            used = store.read_json(cd / "lineage.json", {}).get("lessons_used", [])
        else:
            weakness = _prompt_weakness(a.out, a.gen, parent)
            lessons = b.retrieve(weakness, a.topk, deterministic=False, mark=True); dirty = True
            used = [l["id"] for l in lessons]
            cd.mkdir(parents=True, exist_ok=True)
            store.write_json(cd / "lineage.json", {"parent_id": parent, "parent_gen": a.gen, "lens": "core",
                             "origin": "core_mutation", "lessons_used": used, "changed_components": ["prompt"], "diff": ""})
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


# ----------------------------------------------------------------- final comparison (offline, clean, R bots)
def _eval_prompt_clean(out, gen, aid, R, sims, seed, tag):
    """Re-evaluate a prompt's produced bots fresh is not possible offline (no LLM); instead re-score the
    R candidate bots already generated for this prompt at high sims, returning mean + Wilson CI."""
    cand_dir = store.agent_dir(out, gen, aid) / "candidates"
    means, pooled = [], []
    for r in range(R):
        p = cand_dir / f"bot_{r}.py"
        if not p.exists():
            continue
        ok, _ = dctrl._validate(str(p))
        if not ok:
            means.append(0.0); continue
        per = dctrl._per_game_vs_ladder(out, f"{tag}_b{r}", str(p), sims, seed, str(cand_dir / "_finalscore"), use_cache=False)
        k = sum(sum(per.get(rr, [])) for rr in RUNGS); n = sum(len(per.get(rr, [])) for rr in RUNGS)
        means.append(k / max(n, 1)); pooled += [v for rr in RUNGS for v in per.get(rr, [])]
    mean = (sum(means) / len(means)) if means else 0.0
    p_, lo, hi = dctrl._wilson(int(round(mean * len(pooled))), len(pooled)) if pooled else (0.0, 0.0, 0.0)
    return {"id": aid, "fitness": round(mean, 4), "ci_low": round(lo, 4), "ci_high": round(hi, 4),
            "n_bots": len(means), "bot_means": [round(m, 3) for m in means]}


def cmd_final_compare(a):
    out = a.out
    cfg = store.config(out); R = cfg.get("R", 5)
    g = 0
    while store.gen_dir(out, g + 1).exists():
        g += 1
    rows = dctrl._ranked(out, g)
    champ = rows[0]["id"] if rows else None
    # baseline = best gen-0 seed prompt (no-evolution control)
    g0 = dctrl._ranked(out, 0)
    base = g0[0]["id"] if g0 else None
    res = {"final_gen": g, "R": R, "sims": a.sims}
    if champ:
        res["champion"] = _eval_prompt_clean(out, g, champ, R, a.sims, a.seed, "champ")
    if base:
        res["gen0_best"] = _eval_prompt_clean(out, 0, base, R, a.sims, a.seed, "g0best")
    store.write_json(Path(out) / "final" / "compare.json", res)
    return emit({"ok": True, "final_gen": g, "champion": champ, "gen0_best": base,
                 "champion_fitness": res.get("champion", {}).get("fitness"),
                 "gen0_best_fitness": res.get("gen0_best", {}).get("fitness")})


# ----------------------------------------------------------------- CLI
def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p):
        p.add_argument("--out", required=True)

    p = sub.add_parser("init"); common(p)
    p.add_argument("--optimizer", choices=["gepa", "core"], required=True)
    p.add_argument("--seed", type=int, default=0); p.add_argument("--generations", type=int, default=4)
    p.add_argument("--pop", type=int, default=8); p.add_argument("--survivors", type=int, default=4)
    p.add_argument("--R", type=int, default=5)
    p.add_argument("--sims-eval", dest="sims_eval", type=int, default=120)
    p.add_argument("--sims-final", dest="sims_final", type=int, default=1500)
    p.set_defaults(fn=cmd_init)

    for name, fn in (("eval-plan", cmd_eval_plan), ("eval-score", cmd_eval_score)):
        p = sub.add_parser(name); common(p)
        p.add_argument("--gen", type=int, required=True); p.add_argument("--agent", required=True)
        p.add_argument("--R", type=int, default=5); p.add_argument("--sims-eval", dest="sims_eval", type=int, default=120)
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
    p.add_argument("--sims", type=int, default=1500); p.add_argument("--seed", type=int, default=0)
    p.set_defaults(fn=cmd_final_compare)

    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
