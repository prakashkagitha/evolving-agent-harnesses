"""Figures + self-contained report.html for the decomposition-harness evolution."""
import argparse
import base64
import io
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from . import store

C = {"weak": "#9ca3af", "moderate": "#2563eb", "strong": "#d97706", "sonnet": "#dc2626",
     "champ": "#16a34a", "simple": "#7c3aed", "bestn": "#0891b2", "ladder_mean": "#111827"}
LENS_C = {"strategy": "#2563eb", "concept": "#16a34a", "decomposition": "#d97706",
          "robustness": "#dc2626", "crossover": "#7c3aed"}


def _png(fig):
    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png", dpi=110, bbox_inches="tight")
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode()


def fig_trajectory(d):
    traj = d.get("ladder_trajectory", [])
    champ = d.get("final_headline", {}).get("bots", {}).get("champion", {})
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
    if traj:
        gens = [t["gen"] for t in traj]
        fit = [t["champion_fitness"] if t["champion_fitness"] is not None else float("nan") for t in traj]
        ax[0].plot(gens, fit, "-o", color=C["champ"], lw=2.2, label="champion ladder fitness")
        ax[0].set_xlabel("generation"); ax[0].set_ylabel("mean win-rate vs ladder")
        ax[0].set_title("Champion ladder trajectory (monotone by construction)")
        ax[0].set_ylim(0, 1); ax[0].grid(alpha=0.3); ax[0].legend()
    rungs = [r for r in ["weak", "moderate", "strong", "sonnet"] if r in champ]
    if rungs:
        xs = range(len(rungs))
        ys = [champ[r]["winrate"] for r in rungs]
        lo = [champ[r]["winrate"] - champ[r]["ci_low"] for r in rungs]
        hi = [champ[r]["ci_high"] - champ[r]["winrate"] for r in rungs]
        ax[1].bar(xs, ys, yerr=[lo, hi], capsize=4, color=[C[r] for r in rungs])
        ax[1].axhline(0.5, ls="--", color="#6b7280", lw=1)
        ax[1].set_xticks(list(xs)); ax[1].set_xticklabels(rungs)
        ax[1].set_ylim(0, 1); ax[1].set_ylabel("win-rate (95% CI)")
        ax[1].set_title("Final champion vs each ladder rung")
        for x, y in zip(xs, ys):
            ax[1].text(x, min(y + 0.04, 0.97), f"{y:.2f}", ha="center", fontsize=9)
    return _png(fig)


def fig_ablation(d):
    c = d.get("contribution_test", {})
    rows = [("evolved champion", c.get("champion"), C["champ"]),
            ("simple-refine", c.get("simple_refine"), C["simple"]),
            ("best-of-N", c.get("best_of_n"), C["bestn"])]
    rows = [(n, v, col) for n, v, col in rows if v]
    fig, ax = plt.subplots(figsize=(6.2, 4.2))
    if rows:
        xs = range(len(rows))
        ys = [v["winrate"] for _, v, _ in rows]
        # clamp to >=0: a Wilson CI can sit slightly off the point estimate (e.g. winrate 0.0),
        # and matplotlib rejects negative yerr.
        lo = [max(0.0, v["winrate"] - v["ci_low"]) for _, v, _ in rows]
        hi = [max(0.0, v["ci_high"] - v["winrate"]) for _, v, _ in rows]
        ax.bar(xs, ys, yerr=[lo, hi], capsize=5, color=[col for _, _, col in rows])
        ax.set_xticks(list(xs)); ax.set_xticklabels([n for n, _, _ in rows], rotation=12)
        ax.set_ylim(0, 1); ax.set_ylabel("ladder mean win-rate (95% CI)")
        ax.set_title("Contribution test: champion vs ablations")
        for x, y in zip(xs, ys):
            ax.text(x, min(y + 0.03, 0.97), f"{y:.3f}", ha="center", fontsize=9)
    return _png(fig)


def fig_concepts(d):
    cl = d.get("concept_emergence", [])
    fig, ax = plt.subplots(figsize=(8.5, 4.4))
    if cl:
        gens = [r["gen"] for r in cl]
        keys = [k for k in cl[0].keys() if k != "gen"]
        for k in keys:
            ax.plot(gens, [r.get(k, 0) for r in cl], "-o", lw=1.8, label=k, markersize=4)
        ax.set_xlabel("generation"); ax.set_ylabel("# population members naming concept")
        ax.set_title("planner_prompt — strategy-concept inventory across generations")
        ax.grid(alpha=0.3); ax.legend(fontsize=8, ncol=2)
    return _png(fig)


def fig_structure(d):
    sl = d.get("structure_evolution", [])
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
    if sl:
        gens = [r["gen"] for r in sl]
        ax[0].plot(gens, [r.get("mean_specialist_count", 0) for r in sl], "-o", color=C["strong"], label="mean #specialists")
        ax[0].plot(gens, [r.get("mean_refine_rounds", 0) for r in sl], "-s", color=C["moderate"], label="mean refine rounds")
        ax2 = ax[0].twinx()
        ax2.plot(gens, [r.get("tester_fraction", 0) for r in sl], "-^", color=C["sonnet"], label="tester fraction")
        ax2.set_ylim(0, 1); ax2.set_ylabel("tester fraction", color=C["sonnet"])
        ax[0].set_xlabel("generation"); ax[0].set_ylabel("count")
        ax[0].set_title("decomposition structure over generations")
        ax[0].grid(alpha=0.3); ax[0].legend(loc="upper left", fontsize=8)
        # referee policy stacked bars
        pols = ["priority_order", "weighted_vote", "planner_merge"]
        cols = ["#94a3b8", "#2563eb", "#16a34a"]
        bottom = [0] * len(gens)
        for p, col in zip(pols, cols):
            vals = [r.get("referee_policies", {}).get(p, 0) for r in sl]
            ax[1].bar(gens, vals, bottom=bottom, label=p, color=col)
            bottom = [b + v for b, v in zip(bottom, vals)]
        ax[1].set_xlabel("generation"); ax[1].set_ylabel("# population members")
        ax[1].set_title("referee policy mix"); ax[1].legend(fontsize=8)
    return _png(fig)


def fig_attribution(d):
    by = d.get("attribution_by_lens", {})
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
    lenses = list(by.keys())
    if lenses:
        xs = range(len(lenses))
        adm = [by[l]["admitted"] for l in lenses]
        tri = [by[l]["trials"] for l in lenses]
        ax[0].bar(xs, tri, color="#e5e7eb", label="trials")
        ax[0].bar(xs, adm, color=[LENS_C.get(l, "#111827") for l in lenses], label="admitted")
        ax[0].set_xticks(list(xs)); ax[0].set_xticklabels(lenses, rotation=15)
        ax[0].set_ylabel("# offspring"); ax[0].set_title("Verified-mutation attribution by lens")
        ax[0].legend(fontsize=8)
        for x, a_, t_ in zip(xs, adm, tri):
            ax[0].text(x, t_ + 0.1, f"{a_}/{t_}", ha="center", fontsize=9)
        md = [by[l]["mean_delta_all"] if by[l]["mean_delta_all"] is not None else 0 for l in lenses]
        ax[1].bar(xs, md, color=[LENS_C.get(l, "#111827") for l in lenses])
        ax[1].axhline(0, color="#374151", lw=1)
        ax[1].set_xticks(list(xs)); ax[1].set_xticklabels(lenses, rotation=15)
        ax[1].set_ylabel("mean verified Δ (all trials)")
        ax[1].set_title("Mean child−parent ladder Δ by lens")
    return _png(fig)


HTML = """<!doctype html><html><head><meta charset="utf-8">
<title>CodeClash — Decomposition-Harness Evolution (BattleSnake)</title>
<style>
body{{font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;max-width:1080px;margin:24px auto;padding:0 18px;color:#111827;line-height:1.5}}
h1{{font-size:24px}} h2{{font-size:19px;margin-top:30px;border-bottom:2px solid #e5e7eb;padding-bottom:4px}}
img{{max-width:100%;border:1px solid #e5e7eb;border-radius:8px;margin:8px 0}}
table{{border-collapse:collapse;font-size:13px;margin:8px 0}} td,th{{border:1px solid #e5e7eb;padding:5px 9px;text-align:left}}
th{{background:#f9fafb}} code{{background:#f3f4f6;padding:1px 5px;border-radius:4px}}
.kpi{{display:inline-block;background:#f9fafb;border:1px solid #e5e7eb;border-radius:8px;padding:8px 14px;margin:4px}}
.kpi b{{font-size:20px;display:block;color:#16a34a}} .muted{{color:#6b7280}}
</style></head><body>
<h1>Single-Level Evolution of a Nested Multi-Agent BattleSnake Harness</h1>
<p class="muted">A planner fans out parallel <b>Haiku</b> specialist coders → referee → a <b>verified</b> refine loop
(refute-until-converge). <b>Sonnet</b> evolves the harness genotype; every accepted edit is <b>verified</b> to beat its
parent on a fixed opponent ladder (paired 95% CI). The Sonnet rung is one simple-refinement bot. Never Opus in-workflow.</p>
<div>{kpis}</div>
<h2>1. Ladder trajectory + final per-rung win-rates</h2>
<img src="data:image/png;base64,{trajectory}">
<h2>2. Contribution test — champion vs ablations</h2>
<img src="data:image/png;base64,{ablation}">
<h2>3a. planner_prompt — concept emergence</h2>
<img src="data:image/png;base64,{concepts}">
<h2>3b. decomposition — structure evolution</h2>
<img src="data:image/png;base64,{structure}">
<h2>4. Verified-mutation attribution (per lens)</h2>
<img src="data:image/png;base64,{attribution}">
<h2>Winning-lineage tour</h2>
{lineage}
<h2>Full analysis</h2>
<pre class="muted">See <code>analysis.md</code> for the complete tables and honest caveats. Raw numbers in <code>analysis_data.json</code>.</pre>
<p class="muted">config: {cfg}</p>
</body></html>"""


def _kpis(d):
    out = []
    champ = d.get("final_headline", {}).get("bots", {}).get("champion", {})
    c = d.get("contribution_test", {})
    if champ.get("ladder_mean"):
        out.append(f'<div class="kpi">champion ladder<b>{champ["ladder_mean"]["winrate"]:.3f}</b></div>')
    for r in ["strong", "sonnet"]:
        if r in champ:
            out.append(f'<div class="kpi">vs {r} rung<b>{champ[r]["winrate"]:.3f}</b></div>')
    asum = d.get("admission_summary", {})
    if asum:
        out.append(f'<div class="kpi">admitted edits<b>{asum.get("total_admitted",0)}/{asum.get("total_trials",0)}</b></div>')
    out.append(f'<div class="kpi">beats both ablations<b>{bool(c.get("beats_simple_refine")) and bool(c.get("beats_best_of_n"))}</b></div>')
    return "".join(out)


def _lineage_html(d):
    tour = d.get("winning_lineage", [])
    if not tour:
        return "<p class='muted'>(no lineage)</p>"
    r = ["<table><tr><th>gen</th><th>id</th><th>origin</th><th>lens</th><th>diff</th><th>verified Δ</th><th>ladder fit</th></tr>"]
    for s in tour:
        dl = f"{s['verified_delta']:.3f}" if s.get("verified_delta") is not None else "—"
        lf = f"{s['ladder_fitness']:.3f}" if s.get("ladder_fitness") is not None else "—"
        r.append(f"<tr><td>{s['gen']}</td><td>{s['id']}</td><td>{s.get('origin')}</td>"
                 f"<td>{s.get('lens') or '—'}</td><td>{s.get('diff','') or '—'}</td><td>{dl}</td><td>{lf}</td></tr>")
    r.append("</table>")
    return "".join(r)


def build(out):
    d = store.read_json(Path(out) / "analysis_data.json", {})
    figdir = Path(out) / "figures"
    figdir.mkdir(parents=True, exist_ok=True)
    figs = {"trajectory": fig_trajectory(d), "ablation": fig_ablation(d), "concepts": fig_concepts(d),
            "structure": fig_structure(d), "attribution": fig_attribution(d)}
    for name, b in figs.items():
        (figdir / f"{name}.png").write_bytes(base64.b64decode(b))
    cfg = d.get("config", {})
    html = HTML.format(kpis=_kpis(d), lineage=_lineage_html(d),
                       cfg=json.dumps({k: cfg.get(k) for k in ("seed", "generations", "pop", "survivors",
                                       "refine_rounds", "sims_evolve", "sims_admit", "sims_final",
                                       "battlesnake_commit")}),
                       **figs)
    (Path(out) / "report.html").write_text(html)
    return str(Path(out) / "report.html")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    rep = build(a.out)
    print(json.dumps({"ok": True, "report": rep}))


if __name__ == "__main__":
    main()
