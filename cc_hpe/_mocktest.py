"""Token-free end-to-end test of the harness-prompt-evolution controller (both GEPA and CORE).

Mocks the LLM agents (3 specialist coders + 1 referee coder per replicate, the GEPA role mutator, CORE
contrastive reflection + mutator) by writing files, then drives one generation per optimizer:
  init -> realize each seed prompt-set R times (specialists+referee -> assembled bot) -> score -> select
       -> breed -> mutate role-prompt(s) -> realize child -> two-sample admit -> finalize -> final-compare.
Verifies multi-prompt assembly, R-replicate fitness, the two-sample gate, prompt cloning on breed,
monotone champion, and CORE bank credit. NO model tokens.

Run:  python3 -m cc_hpe._mocktest
"""
import contextlib
import io
import json
import shutil
import sys
from pathlib import Path
from types import SimpleNamespace as NS

from cc_decomp import control as dctrl, store
from cc_decomp._mocktest import MOCK_SPECIALISTS, MOCK_REFEREE
from cc_core import control as ccore
from cc_core import bank as bankmod

from . import control_hpe as C
from . import seeds

R = 2
CONCERNS = seeds.CONCERNS


def call(fn, **kw):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        return fn(NS(**kw))


def check(cond, msg):
    print(("  OK  " if cond else " FAIL ") + msg)
    if not cond:
        raise AssertionError(msg)


def mock_eval(out, gen, aid):
    call(C.cmd_eval_plan, out=out, gen=gen, agent=aid, R=R)
    d = store.agent_dir(out, gen, aid)
    for r in range(R):
        for c in CONCERNS:
            store.write_text(d / f"repl_{r}" / "specialists" / f"{c}.py", MOCK_SPECIALISTS[c])
        store.write_text(d / f"repl_{r}" / "specialists" / "_referee.py", MOCK_REFEREE)
    return call(C.cmd_eval_score, out=out, gen=gen, agent=aid, R=R, sims_eval=12, seed=0)


def force_loser(out, gen, aid):
    """Pin a guaranteed-weak fitness so a contrastive pair forms deterministically in the mock."""
    d = store.agent_dir(out, gen, aid)
    m = store.read_json(d / "metrics.json", {}); m["ladder_fitness"] = 0.0
    m["per_rung"] = {r: 0.0 for r in C.RUNGS}; store.write_json(d / "metrics.json", m)
    ev = store.read_json(d / "evals.json", {})
    ev["fitness"] = 0.0; ev["pooled_games"] = [0] * max(len(ev.get("pooled_games", [])), 36)
    store.write_json(d / "evals.json", ev)


def mock_mutate(out, gen, item):
    cd = store.agent_dir(out, gen + 1, item["new_id"])
    role = item.get("lens") if item.get("lens") in C.ROLES else "combat"
    cur = store.read_text(cd / "prompts" / f"{role}.md")   # already cloned from parent
    store.write_text(cd / "prompts" / f"{role}.md", cur + "\n\nAlso: hard-veto moves into a cell an equal-or-longer enemy head can reach.")
    lin = store.read_json(cd / "lineage.json", {}); lin["diff"] = f"mock edit {role}"; store.write_json(cd / "lineage.json", lin)


def mock_reflection(plan):
    for p in plan["pairs"]:
        lessons = [
            {"lesson": "Give the space_control brief an explicit flood-fill cell-count and a self-trap veto.", "label": "specific"},
            {"lesson": "The referee must drop vetoed moves before weighting.", "label": "meta"},
            {"lesson": "Name concrete head-to-head rules in the combat brief.", "label": "specific"},
        ]
        Path(p["lessons_path"]).parent.mkdir(parents=True, exist_ok=True)
        Path(p["lessons_path"]).write_text(json.dumps(lessons))


def run_optimizer(out, optimizer):
    print(f"\n==================== {optimizer.upper()} ====================")
    shutil.rmtree(out, ignore_errors=True)
    r = call(C.cmd_init, out=out, optimizer=optimizer, seed=0, generations=1, pop=4, survivors=2, R=R, sims_eval=12)
    sids = r["seed_ids"]; check(len(sids) == 4, f"4 seed prompt-sets: {sids}")
    check(r["concerns"] == CONCERNS, f"concerns fixed = {r['concerns']}")

    print("== realize gen-0 prompt-sets (R replicate harness builds) ==")
    for i, aid in enumerate(sids):
        ev = mock_eval(out, 0, aid)
        check(ev["R_valid"] == R, f"{aid}: all R={R} assembled bots valid (fit {round(ev['fitness'],3)})")
        bot = store.produced_bot_path(out, 0, aid)
        ok, reason = dctrl._validate(str(bot)); check(ok, f"{aid}: produced (assembled) bot valid: {reason}")
        if i == len(sids) - 1:
            force_loser(out, 0, aid)

    sc = call(C.cmd_score_pop, out=out, gen=0); check(sc["champion"] is not None, f"gen0 champion {sc['champion']} {round(sc['champion_fitness'],3)}")
    call(dctrl.cmd_population_summary, out=out, gen=0)
    sel = call(dctrl.cmd_select, out=out, gen=0, survivors=2); check(len(sel["survivors"]) == 2, f"survivors {sel['survivors']}")

    if optimizer == "core":
        rp = call(C.cmd_core_reflect_plan, out=out, gen=0, pairs=2, margin=0.0)
        check(rp["n_pairs"] >= 1, f"contrastive prompt-set pairs: {rp['n_pairs']}")
        mock_reflection(store.read_json(ccore.bank_dir(out) / "reflections" / "gen_00" / "reflect_plan.json", {}))
        ing = call(ccore.cmd_core_ingest, out=out, gen=0, max_lessons=4, plan="")
        check(ing["bank_size"] >= 1, f"insights ingested: {ing['bank_size']}")
        bp = call(C.cmd_core_breed_plan, out=out, gen=0, pop=4, survivors=2, topk=3)
    else:
        bp = call(C.cmd_breed_plan_gepa, out=out, gen=0, pop=4, survivors=2)
    plan = bp["plan"]; check(len(plan) == 2, f"2 offspring planned: {[p['new_id'] for p in plan]}")

    print("== breed-clone + mutate + realize + two-sample admit ==")
    for it in plan:
        cd = store.agent_dir(out, 1, it["new_id"])
        check(all((cd / "prompts" / f"{r}.md").exists() for r in C.ROLES), f"{it['new_id']}: 4 parent prompts cloned")
        mock_mutate(out, 0, it)
        mock_eval(out, 1, it["new_id"])
        ad = call(C.cmd_admit, out=out, gen=1, child=it["new_id"], parent_gen=0, parent=it["parent_id"])
        check("ci_low" in ad, f"two-sample CI for {it['new_id']}: delta={round(ad['delta'],3)} CI=[{round(ad['ci_low'],3)},{round(ad['ci_high'],3)}] adm={ad['admitted']}")

    if optimizer == "core":
        before = sum(l["uses"] for l in bankmod.Bank.load(ccore.bank_path(out)).lessons)
        cr = call(ccore.cmd_core_credit, out=out, gen=0)
        after = sum(l["uses"] for l in bankmod.Bank.load(ccore.bank_path(out)).lessons)
        check(cr["n_credited"] == 2 and after > before, f"insights credited via breed_context: {cr['n_credited']}, uses {before}->{after}")

    fin = call(dctrl.cmd_finalize_gen, out=out, gen=0, pop=4, survivors=2)
    check(len(fin["ids"]) == 4, f"gen1 refilled: {fin['ids']}")
    g0 = store.read_json(store.gen_dir(out, 0) / "population_summary.json", {})["champion_fitness"]
    check(fin["champion_fitness"] >= g0 - 1e-9, f"champion monotone {round(g0,3)} -> {round(fin['champion_fitness'],3)}")

    fc = call(C.cmd_final_compare, out=out, sims=20, seed=0)
    check(fc["champion_fitness"] is not None, f"final-compare: champion {round(fc['champion_fitness'],3)} vs gen0_best {round(fc['gen0_best_fitness'],3)}")
    print(f"  {optimizer}: champion={fc['champion']} {round(fc['champion_fitness'],3)} | gen0_best={fc['gen0_best']} {round(fc['gen0_best_fitness'],3)}")


def main():
    run_optimizer("/tmp/cc_hpe_mock_gepa", "gepa")
    run_optimizer("/tmp/cc_hpe_mock_core", "core")
    print("\nALL MOCK CHECKS PASSED")


if __name__ == "__main__":
    try:
        main()
    except AssertionError:
        sys.exit(1)
