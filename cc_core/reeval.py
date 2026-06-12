"""Reliable OFFLINE re-evaluation of a completed CORE run (the contention-safe path).

Identical in spirit to cc_decomp.reeval: the during-run admit/score steps can be corrupted when many
offspring sims run CONCURRENTLY in the workflow pipeline (CPU oversubscription -> BotServers miss
readiness -> spurious 0.0 fitness / wrong admit verdicts). All the EXPENSIVE work (Sonnet contrastive
reflection + lessons + Haiku harness runs) is on disk, and the gate itself is TOKEN-FREE sims, so we
recompute everything SEQUENTIALLY (reliable) and rebuild the corrected analysis.

CORE adds two steps on top of cc_decomp.reeval:
  - re-credit the lesson bank from the CORRECTED admit verdicts (live credit used noisy verdicts), and
  - overlay the CORE lesson-bank analysis section.

Usage: python3 -m cc_core.reeval --out cc_core_evo [--sims-evolve 150 --sims-admit 300 --sims-final 1500]
"""
import argparse
import json
from pathlib import Path

from cc_decomp import reeval as dreeval
from cc_decomp import store

# Sequential => safe to use high parallelism within a SINGLE run_matches (no concurrent calls).
dreeval.control.MAXW = 64

from . import analysis as canalysis
from . import bank as bankmod
from .control import bank_path, _snap


def _recredit_bank(out):
    """Reset every lesson's uses/wins and replay credit from the CORRECTED admissions.json verdicts
    and each offspring's lineage.lessons_used (lessons themselves are unchanged by reeval)."""
    b = bankmod.Bank.load(bank_path(out))
    for ls in b.lessons:
        ls["uses"] = 0
        ls["wins"] = 0
    gens = []
    i = 0
    while store.gen_dir(out, i).exists():
        gens.append(i)
        i += 1
    for g in gens:
        if g == 0:
            continue
        adm = store.read_json(store.gen_dir(out, g) / "admissions.json", {})
        admitted = {o["id"]: bool(o.get("admitted")) for o in adm.get("offspring", [])}
        for oid, odir in dreeval._all_offspring_dirs(out, g):
            lin = store.read_json(odir / "lineage.json", {})
            used = lin.get("lessons_used") or [
                l["id"] for l in store.read_json(odir / "breed_context.json", {}).get("lessons", []) if l.get("id")]
            if used:
                b.credit(used, admitted.get(oid, False))
    b.save(bank_path(out))
    _snap(b, 999, out)              # snapshot the re-credited (corrected) bank
    return b


def reeval(out, sims_evolve, sims_admit, sims_final):
    # 1-4: corrected scores, admits, final headline, shared analysis_data.json (+ monotone curve) & report
    dreeval.reeval(out, sims_evolve, sims_admit, sims_final)
    # 5: re-credit the bank from the corrected admit verdicts
    b = _recredit_bank(out)
    # 6: overlay the CORE lesson-bank section (keeps the corrected champion_curve_monotone intact)
    canalysis.overlay_core(out)
    print(f"  bank re-credited: {len(b.lessons)} lessons, "
          f"{sum(l['uses'] for l in b.lessons)} uses, {sum(l['wins'] for l in b.lessons)} verified wins")
    return {"ok": True, "bank_size": len(b.lessons)}


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
