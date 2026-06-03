"""Reliable OFFLINE re-evaluation of a completed (possibly contention-corrupted) run.

The during-run admit gate / scoring can be corrupted when many offspring sims run CONCURRENTLY
in the workflow pipeline (CPU/fork oversubscription -> BotServers miss readiness -> spurious 0.0,
or the admit process fails -> None). The EXPENSIVE work (Sonnet mutations + Haiku harness runs) is
saved on disk for every offspring (including rejected ones under _rejected_*). The gate itself is
TOKEN-FREE sims, so we recompute everything SEQUENTIALLY (one run_matches at a time -> no contention
-> reliable) and rebuild the corrected analysis + report.

Usage: python3 -m cc_decomp.reeval --out cc_decomp_evo [--sims-evolve 150 --sims-admit 300 --sims-final 1500]
"""
import argparse
import json
from pathlib import Path

import numpy as np

from . import analysis, control, store, viz
from cc_gepa import sim

# Sequential => safe to use high parallelism within a SINGLE run_matches (no concurrent calls).
control.MAXW = 64


def _all_offspring_dirs(out, gen):
    """All offspring evaluated for generation `gen` (admitted live in genotypes/, rejected under
    _rejected_*). Returns list of (id, dir)."""
    gd = store.gen_dir(out, gen) / "genotypes"
    out_list = []
    if not gd.exists():
        return out_list
    for p in sorted(gd.iterdir()):
        nm = p.name
        if nm.startswith("agent_") and nm[len("agent_"):].startswith(f"g{gen:02d}"):
            out_list.append((nm[len("agent_"):], p))
        elif nm.startswith("_rejected_"):
            out_list.append((nm[len("_rejected_"):], p))
    return out_list


def _score_dir(out, name, bot_path, sims, seed, wd):
    per, mean = control._score_vs_ladder(out, name, str(bot_path), sims, seed, wd, use_cache=False)
    return per, mean


def reeval(out, sims_evolve, sims_admit, sims_final):
    cfg = store.config(out)
    gens = []
    i = 0
    while store.gen_dir(out, i).exists():
        gens.append(i)
        i += 1
    print(f"re-evaluating {len(gens)} generations (sequential, reliable; sims_evolve={sims_evolve} "
          f"sims_admit={sims_admit} sims_final={sims_final})")
    wd = str(Path(out) / "_reeval_work")

    # 1. reliably re-score every gen's population -> corrected ladder_fitness + champion trajectory
    for g in gens:
        ids = store.list_agents(out, g)
        rows = []
        for aid in ids:
            bot = store.produced_bot_path(out, g, aid)
            if not bot.exists():
                continue
            per, mean = _score_dir(out, f"g{g}_{aid}", bot, sims_evolve, cfg.get("seed", 0), wd)
            m = store.read_json(store.agent_dir(out, g, aid) / "metrics.json", {})
            m.update({"id": aid, "ladder_fitness": mean, "per_rung": per,
                      "sims": sims_evolve, "seed": cfg.get("seed", 0), "reeval": True})
            store.write_json(store.agent_dir(out, g, aid) / "metrics.json", m)
            rows.append((aid, mean))
        rows.sort(key=lambda r: -r[1])
        champ, cf = (rows[0] if rows else (None, None))
        # rewrite population_summary with corrected champion + structure/concepts
        planner_prompts = [store.read_text(store.agent_dir(out, g, i) / "planner_prompt.md") for i in ids]
        store.write_json(store.gen_dir(out, g) / "population_summary.json", {
            "gen": g, "ids": ids, "champion": champ, "champion_fitness": cf,
            "fitness_distribution": [{"id": a, "ladder_fitness": f} for a, f in rows],
            "n_admitted": store.read_json(store.gen_dir(out, g) / "admissions.json", {}).get("n_admitted", 0),
            "structure": control._structure_inventory(out, g, ids),
            "concept_inventory": control._concept_inventory(planner_prompts)})
        print(f"  gen{g}: champion={champ} fit={cf:.3f}" if cf is not None else f"  gen{g}: (no bots)")

    # enforce a MONOTONE champion-fitness curve for reporting (the design guarantees it; we report the
    # best-so-far reliable fitness, since live selection used noisy scores)
    best = -1.0
    mono = []
    for g in gens:
        ps = store.read_json(store.gen_dir(out, g) / "population_summary.json", {})
        cf = ps.get("champion_fitness")
        if cf is not None:
            best = max(best, cf)
        mono.append({"gen": g, "champion": ps.get("champion"), "champion_fitness": cf,
                     "best_so_far": best})

    # 2. reliably re-admit every offspring vs its parent -> corrected per-lens attribution
    for g in gens:
        if g == 0:
            continue
        offs = _all_offspring_dirs(out, g)
        recs = []
        n_adm = 0
        for oid, odir in offs:
            lin = store.read_json(odir / "lineage.json", {})
            pid, pg = lin.get("parent_id"), lin.get("parent_gen")
            cbot = odir / "produced_bot" / "main.py"
            if pid is None or pg is None or not cbot.exists():
                recs.append({"id": oid, "lens": lin.get("lens"), "parent_id": pid,
                             "delta": None, "ci_low": None, "ci_high": None, "admitted": False,
                             "child_fit": None, "parent_fit": None,
                             "changed_components": lin.get("changed_components", []), "diff": lin.get("diff", "")})
            else:
                pbot = store.produced_bot_path(out, pg, pid)
                cper = control._per_game_vs_ladder(out, f"c_{g}_{oid}", str(cbot), sims_admit, cfg.get("seed", 0), wd, use_cache=False)
                pper = control._per_game_vs_ladder(out, f"p_{pg}_{pid}", str(pbot), sims_admit, cfg.get("seed", 0), wd, use_cache=False)
                diffs, cw, pw, n = [], 0, 0, 0
                for r in store.RUNGS:
                    if r in cper and r in pper:
                        m = min(len(cper[r]), len(pper[r]))
                        diffs += [cper[r][i] - pper[r][i] for i in range(m)]
                        cw += sum(cper[r][:m]); pw += sum(pper[r][:m]); n += m
                delta, lo, hi = control._paired_bootstrap(diffs)
                admitted = bool(lo > 0.0)
                if admitted:
                    n_adm += 1
                recs.append({"id": oid, "lens": lin.get("lens"), "parent_id": pid,
                             "delta": delta, "ci_low": lo, "ci_high": hi, "admitted": admitted,
                             "child_fit": cw / max(n, 1), "parent_fit": pw / max(n, 1),
                             "changed_components": lin.get("changed_components", []), "diff": lin.get("diff", "")})
        store.write_json(store.gen_dir(out, g) / "admissions.json",
                         {"gen": g, "offspring": recs, "n_admitted": n_adm, "n_offspring": len(offs), "reeval": True})
        print(f"  gen{g} re-admit: {n_adm}/{len(offs)} admitted; "
              + ", ".join(f"{r['lens']}:{(round(r['delta'],2) if r['delta'] is not None else 'NA')}{'*' if r['admitted'] else ''}" for r in recs))

    # 3. reliable final headline: best bot of the FINAL gen + ablations vs every rung @ sims_final
    rows = control._ranked(out, gens[-1])
    champ = rows[0]["id"] if rows else None
    fwd = str(Path(out) / "final" / "_reeval")
    bots = {}
    if champ:
        bots["champion"] = str(store.produced_bot_path(out, gens[-1], champ))
    simp = store.ablation_dir(out) / "simple_refine" / "produced_bot" / "main.py"
    if simp.exists():
        bots["simple_refine"] = str(simp)
    bon = store.ablation_dir(out) / "best_of_n" / "best" / "main.py"
    if bon.exists():
        bots["best_of_n"] = str(bon)
    headline = {"champion_id": champ, "sims": sims_final, "seed": cfg.get("seed", 0), "bots": {}}
    for name, bp in bots.items():
        headline["bots"][name] = control._final_one(out, name, bp, sims_final, cfg.get("seed", 0), fwd)
        hb = headline["bots"][name]["ladder_mean"]
        print(f"  FINAL {name}: ladder_mean={hb['winrate']:.3f} [{hb['ci_low']:.3f},{hb['ci_high']:.3f}]")
    h2h = {}
    if champ:
        cbot = {"name": "champion", "path": bots["champion"]}
        for name in ("simple_refine", "best_of_n"):
            if name in bots:
                per = sim.per_game_results([{"id": name, "a": cbot, "b": {"name": name, "path": bots[name]}}],
                                           sims_final, cfg.get("seed", 0) + 5000, fwd, max_workers=control.MAXW)[name]
                k, n = sum(per), len(per)
                p, lo, hi = control._wilson(k, n)
                h2h[name] = {"champion_winrate": p, "ci_low": lo, "ci_high": hi, "n": n}
    headline["champion_vs_ablations"] = h2h
    store.write_json(Path(out) / "final" / "headline.json", headline)

    # 4. rebuild analysis + report from corrected data; stash the monotone curve
    data = analysis.analyze(out)
    data["champion_curve_monotone"] = mono
    store.write_json(Path(out) / "analysis_data.json", data)
    rep = viz.build(out)
    print(f"corrected analysis.md + report.html written: {rep}")
    return {"ok": True, "champion": champ, "report": rep}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--sims-evolve", type=int, default=150)
    ap.add_argument("--sims-admit", type=int, default=300)
    ap.add_argument("--sims-final", type=int, default=1500)
    a = ap.parse_args()
    r = reeval(a.out, a.sims_evolve, a.sims_admit, a.sims_final)
    print(json.dumps(r))


if __name__ == "__main__":
    main()
