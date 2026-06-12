"""Analysis for the CORE harness evolution.

Reuses cc_decomp.analysis for every metric shared with the GEPA run (ladder trajectory, the
contribution test vs both ablations, the two-component timelines, the verified-acceptance
attribution, the winning lineage), then ADDS the CORE-specific view: the lesson-bank growth
trajectory and per-lesson verified attribution (uses/wins/utility/support) — CORE's analogue of
GEPA's per-lens attribution. Appends a "CORE lesson bank" section to analysis.md and a "core_bank"
block to analysis_data.json.
"""
import argparse
import json
from pathlib import Path

from cc_decomp import analysis as danalysis
from cc_decomp import store

from . import bank as bankmod
from .control import bank_path, bank_dir


def _bank_trajectory(out):
    rows = []
    snap = bank_dir(out) / "snapshots.jsonl"
    if snap.exists():
        for line in snap.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except ValueError:
                continue
            rows.append({"gen": r.get("gen"), "n_lessons": r.get("n_lessons"), "n_meta": r.get("n_meta")})
    # collapse to last row per gen (credit + ingest both snapshot a gen)
    by_gen = {}
    for r in rows:
        by_gen[r["gen"]] = r
    return [by_gen[g] for g in sorted(by_gen)]


def analyze(out):
    danalysis.analyze(out)                       # shared metrics -> analysis_data.json + analysis.md
    return overlay_core(out)


def overlay_core(out):
    """Add the CORE lesson-bank block to an EXISTING analysis_data.json + append the CORE section to
    analysis.md. Assumes the shared analysis has already run (so reeval can keep its corrected
    champion_curve_monotone). Returns the augmented data dict."""
    data = store.read_json(Path(out) / "analysis_data.json", {})

    b = bankmod.Bank.load(bank_path(out))
    lessons = sorted(b.lessons, key=lambda l: (-b.utility(l), -l["wins"], l["id"]))
    lesson_rows = [{
        "id": l["id"], "label": l["label"], "text": l["text"],
        "uses": l["uses"], "wins": l["wins"], "support": l["support"],
        "utility": round(b.utility(l), 4), "gen_added": l["gen_added"],
        "sources": l.get("sources", []),
    } for l in lessons]
    core = {
        "optimizer": "CORE",
        "bank_size": len(b.lessons),
        "n_meta": sum(1 for l in b.lessons if l["label"] == "meta"),
        "n_specific": sum(1 for l in b.lessons if l["label"] == "specific"),
        "total_uses": sum(l["uses"] for l in b.lessons),
        "total_wins": sum(l["wins"] for l in b.lessons),
        "bank_trajectory": _bank_trajectory(out),
        "lessons": lesson_rows,
    }
    data["core_bank"] = core
    store.write_json(Path(out) / "analysis_data.json", data)

    # append a CORE section to analysis.md
    L = ["", "## 7. CORE lesson bank (the breeder)", ""]
    L.append(f"The bank accumulated **{core['bank_size']} lessons** "
             f"({core['n_specific']} specific, {core['n_meta']} meta) across the run, used "
             f"**{core['total_uses']}** times to condition mutations with **{core['total_wins']}** "
             f"verified wins (a lesson 'wins' when a mutation that used it cleared the paired-CI gate).")
    traj = core["bank_trajectory"]
    if traj:
        L.append("")
        L.append("| gen | lessons | meta |")
        L.append("|---|---|---|")
        for r in traj:
            L.append(f"| {r['gen']} | {r['n_lessons']} | {r['n_meta']} |")
    L.append("")
    L.append("**Top lessons by verified utility** (utility = Beta-smoothed win-rate of mutations that used the lesson):")
    L.append("")
    L.append("| id | label | uses | wins | utility | lesson |")
    L.append("|---|---|---|---|---|---|")
    for r in lesson_rows[:12]:
        txt = r["text"].replace("|", "\\|")
        L.append(f"| {r['id']} | {r['label']} | {r['uses']} | {r['wins']} | {r['utility']:.3f} | {txt} |")
    md_path = Path(out) / "analysis.md"
    existing = store.read_text(md_path)
    store.write_text(md_path, existing + "\n".join(L) + "\n")
    return data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    analyze(a.out)
    print(json.dumps({"ok": True}))


if __name__ == "__main__":
    main()
