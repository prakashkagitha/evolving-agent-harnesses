"""Analysis for the single-level decomposition-harness evolution.

Reads OUTER_DIR and computes (into analysis_data.json) + writes analysis.md:
  1. Ladder trajectory     — champion ladder fitness per generation (monotone by construction)
                             + final per-rung win-rates (weak/moderate/strong/SONNET) with CIs.
  2. Contribution test     — champion vs the simple-refinement and best-of-N ablations.
  3. Two-component lines    — planner_prompt concept emergence + decomposition-structure evolution.
  4. Verified attribution   — per lens / per component: # admitted edits + mean verified delta.
  5. Winning-lineage tour   — the verified edit at each ancestral step that moved the champion.
"""
import argparse
import json
from pathlib import Path

from . import store


def _gens(out):
    g = []
    i = 0
    while store.gen_dir(out, i).exists():
        g.append(i)
        i += 1
    return g


def _ablation_fit(out, name, sims=None):
    """Ladder fitness of an ablation bot (from final headline if present, else None)."""
    head = store.read_json(Path(out) / "final" / "headline.json", {})
    b = head.get("bots", {}).get(name)
    if b and "ladder_mean" in b:
        return b["ladder_mean"]
    return None


def analyze(out):
    cfg = store.config(out)
    gens = _gens(out)
    data = {"config": cfg, "generations": gens}

    # ---- 1. ladder trajectory (champion fitness per gen) ----
    traj = []
    for g in gens:
        ps = store.read_json(store.gen_dir(out, g) / "population_summary.json", {})
        traj.append({"gen": g, "champion": ps.get("champion"),
                     "champion_fitness": ps.get("champion_fitness"),
                     "n_admitted": ps.get("n_admitted", 0)})
    data["ladder_trajectory"] = traj

    head = store.read_json(Path(out) / "final" / "headline.json", {})
    data["final_headline"] = head

    # ---- 2. contribution test (champion vs ablations) ----
    champ = head.get("bots", {}).get("champion", {})
    contrib = {"champion": champ.get("ladder_mean"),
               "simple_refine": _ablation_fit(out, "simple_refine"),
               "best_of_n": _ablation_fit(out, "best_of_n"),
               "champion_vs_ablations": head.get("champion_vs_ablations", {})}
    # does champion beat both ablations (ladder mean, non-overlapping or point estimate)?
    def beats(a, b):
        if not a or not b:
            return None
        return a["winrate"] > b["winrate"]
    contrib["beats_simple_refine"] = beats(contrib["champion"], contrib["simple_refine"])
    contrib["beats_best_of_n"] = beats(contrib["champion"], contrib["best_of_n"])
    data["contribution_test"] = contrib

    # ---- 3a. concept emergence + 3b. structure evolution per gen ----
    concept_lines, structure_lines = [], []
    for g in gens:
        ps = store.read_json(store.gen_dir(out, g) / "population_summary.json", {})
        concept_lines.append({"gen": g, **ps.get("concept_inventory", {})})
        structure_lines.append({"gen": g, **ps.get("structure", {})})
    data["concept_emergence"] = concept_lines
    data["structure_evolution"] = structure_lines

    # ---- 4. verified-mutation attribution (per lens / per component) ----
    by_lens, by_comp = {}, {}
    all_adm = []
    for g in gens:
        adm = store.read_json(store.gen_dir(out, g) / "admissions.json", {})
        for o in adm.get("offspring", []):
            all_adm.append({"gen": g, **o})
            lens = o.get("lens") or "?"
            bl = by_lens.setdefault(lens, {"n": 0, "admitted": 0, "deltas_adm": [], "deltas_all": []})
            bl["n"] += 1
            if o.get("delta") is not None:
                bl["deltas_all"].append(o["delta"])
            if o.get("admitted"):
                bl["admitted"] += 1
                if o.get("delta") is not None:
                    bl["deltas_adm"].append(o["delta"])
            for c in (o.get("changed_components") or []):
                bc = by_comp.setdefault(c, {"n": 0, "admitted": 0, "deltas_adm": []})
                bc["n"] += 1
                if o.get("admitted"):
                    bc["admitted"] += 1
                    if o.get("delta") is not None:
                        bc["deltas_adm"].append(o["delta"])
    def _summ(d):
        out_ = {}
        for k, v in d.items():
            adm = v.get("deltas_adm", [])
            allv = v.get("deltas_all", [])
            out_[k] = {"trials": v["n"], "admitted": v["admitted"],
                       "accept_rate": v["admitted"] / max(v["n"], 1),
                       "mean_delta_admitted": (sum(adm) / len(adm)) if adm else None,
                       "mean_delta_all": (sum(allv) / len(allv)) if allv else None}
        return out_
    data["attribution_by_lens"] = _summ(by_lens)
    data["attribution_by_component"] = _summ(by_comp)
    data["all_admissions"] = all_adm
    n_adm = sum(1 for a in all_adm if a.get("admitted"))
    data["admission_summary"] = {"total_trials": len(all_adm), "total_admitted": n_adm,
                                 "overall_accept_rate": n_adm / max(len(all_adm), 1)}

    # ---- 5. winning-lineage tour (champion ancestry of admitted edits) ----
    tour = []
    if gens:
        gfin = gens[-1]
        cid = traj[-1]["champion"] if traj else None
        cg = gfin
        seen = set()
        while cid and (cg, cid) not in seen:
            seen.add((cg, cid))
            d = store.agent_dir(out, cg, cid)
            lin = store.read_json(d / "lineage.json", {})
            m = store.read_json(d / "metrics.json", {})
            v = m.get("verified_vs_parent", {})
            tour.append({"gen": cg, "id": cid, "origin": lin.get("origin"), "lens": lin.get("lens"),
                         "changed_components": lin.get("changed_components", []), "diff": lin.get("diff", ""),
                         "verified_delta": v.get("delta"), "ci_low": v.get("ci_low"),
                         "ladder_fitness": m.get("ladder_fitness")})
            p, pg = lin.get("parent_id"), lin.get("parent_gen")
            if p is None or pg is None:
                break
            cid, cg = p, pg
        tour.reverse()
    data["winning_lineage"] = tour

    data["ladder_sanity"] = store.read_json(store.ladder_dir(out) / "sanity.json", {})
    store.write_json(Path(out) / "analysis_data.json", data)
    _write_md(out, data)
    return data


def _fmt_ci(x):
    if not x:
        return "—"
    return f"{x['winrate']:.3f} [{x['ci_low']:.3f}, {x['ci_high']:.3f}]"


def _write_md(out, d):
    cfg = d["config"]
    L = []
    L.append("# CodeClash — Single-Level Evolution of a Nested Multi-Agent BattleSnake Harness\n")
    L.append(f"*Reuses the CodeClash/BattleSnake rules engine (battlesnake commit "
             f"`{cfg.get('battlesnake_commit')}`). Inner harness execution = Haiku; outer harness evolution = Sonnet; "
             f"the Sonnet ladder rung is a single simple-refinement bot. Never Opus in-workflow.*\n")
    L.append("## Setup\n")
    L.append(f"- Knobs: generations={cfg.get('generations')}, pop={cfg.get('pop')}, survivors={cfg.get('survivors')}, "
             f"refine_rounds={cfg.get('refine_rounds')}, sims_evolve={cfg.get('sims_evolve')}, "
             f"sims_admit={cfg.get('sims_admit')}, sims_final={cfg.get('sims_final')}, seed={cfg.get('seed')}.")
    san = d.get("ladder_sanity", {})
    if san:
        fit = {k: round(v, 3) for k, v in san.get("fitness", {}).items()}
        L.append(f"- Fixed ladder (round-robin fitness): {fit}; ranking weak<moderate<strong "
                 f"**{'holds' if san.get('order_ok') else 'NOT strict'}**; sonnet competitive: {san.get('sonnet_competitive')}.\n")

    L.append("## 1. Headline — ladder trajectory (monotone by construction)\n")
    L.append("| gen | champion | ladder fitness | admitted this gen |")
    L.append("|---|---|---|---|")
    for t in d["ladder_trajectory"]:
        cf = t["champion_fitness"]
        cfs = f"{cf:.3f}" if cf is not None else "—"
        L.append(f"| {t['gen']} | {t['champion']} | {cfs} | {t['n_admitted']} |")
    champ = d["final_headline"].get("bots", {}).get("champion", {})
    if champ:
        L.append(f"\n**Final champion per-rung win-rate ({cfg.get('sims_final')} sims, Wilson 95% CI):**\n")
        L.append("| rung | win-rate [95% CI] |")
        L.append("|---|---|")
        for r in ["weak", "moderate", "strong", "sonnet", "ladder_mean"]:
            if r in champ:
                L.append(f"| {r} | {_fmt_ci(champ[r])} |")

    L.append("\n## 2. The contribution test — champion vs ablations\n")
    c = d["contribution_test"]
    L.append("| bot | ladder mean win-rate [95% CI] |")
    L.append("|---|---|")
    L.append(f"| **evolved champion** | {_fmt_ci(c.get('champion'))} |")
    L.append(f"| simple-refinement (baseline) | {_fmt_ci(c.get('simple_refine'))} |")
    L.append(f"| best-of-N refinement | {_fmt_ci(c.get('best_of_n'))} |")
    L.append(f"\nChampion beats simple-refinement: **{c.get('beats_simple_refine')}**; beats best-of-N: "
             f"**{c.get('beats_best_of_n')}**. (The harness's contribution holds only if BOTH are true.)")
    h2h = c.get("champion_vs_ablations", {})
    if h2h:
        L.append("\nHead-to-head (champion win-rate, Wilson 95% CI):")
        for k, v in h2h.items():
            L.append(f"- vs {k}: {v['champion_winrate']:.3f} [{v['ci_low']:.3f}, {v['ci_high']:.3f}]")

    L.append("\n## 3. Two-component evolution\n")
    L.append("### 3a. planner_prompt — strategy-concept inventory (count of population members naming each concept)\n")
    cl = d["concept_emergence"]
    if cl:
        keys = [k for k in cl[0].keys() if k != "gen"]
        L.append("| gen | " + " | ".join(keys) + " |")
        L.append("|" + "---|" * (len(keys) + 1))
        for row in cl:
            L.append("| " + str(row["gen"]) + " | " + " | ".join(str(row.get(k, 0)) for k in keys) + " |")
    L.append("\n### 3b. decomposition — structure evolution\n")
    sl = d["structure_evolution"]
    L.append("| gen | mean #specialists | tester fraction | mean refine rounds | referee policies |")
    L.append("|---|---|---|---|---|")
    for row in sl:
        L.append(f"| {row['gen']} | {row.get('mean_specialist_count', 0):.2f} | "
                 f"{row.get('tester_fraction', 0):.2f} | {row.get('mean_refine_rounds', 0):.2f} | "
                 f"{row.get('referee_policies', {})} |")

    L.append("\n## 4. Verified-mutation attribution (only verified-helpful edits are admitted)\n")
    L.append("| lens | trials | admitted | accept rate | mean Δ (admitted) | mean Δ (all) |")
    L.append("|---|---|---|---|---|---|")
    for lens, v in d["attribution_by_lens"].items():
        ma = f"{v['mean_delta_admitted']:.3f}" if v['mean_delta_admitted'] is not None else "—"
        mall = f"{v['mean_delta_all']:.3f}" if v['mean_delta_all'] is not None else "—"
        L.append(f"| {lens} | {v['trials']} | {v['admitted']} | {v['accept_rate']:.2f} | {ma} | {mall} |")
    asum = d["admission_summary"]
    L.append(f"\nOverall: {asum['total_admitted']}/{asum['total_trials']} offspring admitted "
             f"(accept rate {asum['overall_accept_rate']:.2f}).")
    L.append("\n**By component changed:**\n")
    L.append("| component | trials | admitted | accept rate | mean Δ (admitted) |")
    L.append("|---|---|---|---|---|")
    for comp, v in d["attribution_by_component"].items():
        ma = f"{v['mean_delta_admitted']:.3f}" if v['mean_delta_admitted'] is not None else "—"
        L.append(f"| {comp} | {v['trials']} | {v['admitted']} | {v['accept_rate']:.2f} | {ma} |")

    L.append("\n## 5. Winning-lineage tour (verified edits that moved the champion)\n")
    if d["winning_lineage"]:
        L.append("| gen | id | origin | lens | changed | diff | verified Δ | ladder fit |")
        L.append("|---|---|---|---|---|---|---|---|")
        for s in d["winning_lineage"]:
            dl = f"{s['verified_delta']:.3f}" if s.get("verified_delta") is not None else "—"
            lf = f"{s['ladder_fitness']:.3f}" if s.get("ladder_fitness") is not None else "—"
            L.append(f"| {s['gen']} | {s['id']} | {s.get('origin')} | {s.get('lens') or '—'} | "
                     f"{','.join(s.get('changed_components', [])) or '—'} | {s.get('diff', '') or '—'} | {dl} | {lf} |")

    L.append("\n## 6. Honest caveats\n")
    L.append("- **n=1 seed.** A single evolutionary run; ≥3 seeds would be the cheapest path to a stronger claim.")
    L.append("- **The Sonnet rung is a simple-refinement Sonnet bot.** Beating it means *evolved-Haiku-harness ≥ "
             "plain-refinement-Sonnet* — a fair, strong claim. It does **not** imply the harness transfers to Sonnet "
             "(transfer is explicitly out of scope; flagged as future work).")
    L.append("- **Verified acceptance + elitism make the champion curve monotone by construction** — the curve shows "
             "*that* improvement was found and verified, not a noisy hill-climb; magnitude and per-rung gains are the "
             "substantive results.")
    store.write_text(Path(out) / "analysis.md", "\n".join(L) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    analyze(a.out)
    print(json.dumps({"ok": True}))


if __name__ == "__main__":
    main()
