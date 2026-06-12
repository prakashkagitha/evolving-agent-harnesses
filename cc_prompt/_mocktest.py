"""Token-free end-to-end test of the prompt-evolution controller (both GEPA and CORE).

Mocks the LLM agents (R bot-writers per prompt, GEPA prompt-mutator, CORE contrastive reflection +
prompt-mutator) by writing files, then drives one full generation for each optimizer:
  init -> eval each seed prompt (R bots -> mean fitness) -> score -> select
       -> breed (gepa lens OR core reflect+retrieve) -> mutate prompt -> eval child
       -> TWO-SAMPLE admit -> finalize -> final-compare.
Verifies R-replicate fitness, the two-sample bootstrap gate, monotone champion, CORE bank credit
(via breed_context fallback). NO model tokens.

Run:  python3 -m cc_prompt._mocktest    (exits non-zero on any failed assertion)
"""
import contextlib
import io
import json
import shutil
import sys
from pathlib import Path
from types import SimpleNamespace as NS

from cc_decomp import control as dctrl, store
from cc_core import control as ccore
from cc_core import bank as bankmod

from . import control_prompt as C

R = 3


def call(fn, **kw):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        return fn(NS(**kw))


def check(cond, msg):
    print(("  OK  " if cond else " FAIL ") + msg)
    if not cond:
        raise AssertionError(msg)


def _bot(out, kind):
    return (store.ladder_dir(out) / f"{kind}.py").read_text()


def mock_eval(out, gen, aid, weak=False):
    call(C.cmd_eval_plan, out=out, gen=gen, agent=aid, R=R)
    d = store.agent_dir(out, gen, aid); (d / "candidates").mkdir(parents=True, exist_ok=True)
    for r in range(R):
        store.write_text(d / "candidates" / f"bot_{r}.py", _bot(out, "weak" if weak else "strong"))
    return call(C.cmd_eval_score, out=out, gen=gen, agent=aid, R=R, sims_eval=12, seed=0)


def mock_mutate(out, gen, item):
    pg, pid, nid = item["parent_gen"], item["parent_id"], item["new_id"]
    parent = C.load_prompt(out, pg, pid)
    cd = store.agent_dir(out, gen + 1, nid)
    store.write_text(cd / "prompt.md", parent + "\n\nAlso: never enter a region smaller than your length.")
    lin = store.read_json(cd / "lineage.json", {}); lin["diff"] = "mock edit"
    store.write_json(cd / "lineage.json", lin)


def mock_reflection(plan):
    for p in plan["pairs"]:
        lessons = [
            {"lesson": "Spell out the flood-fill space metric explicitly in the prompt.", "label": "specific"},
            {"lesson": "Always instruct concrete head-to-head veto rules.", "label": "specific"},
            {"lesson": "Concrete thresholds beat vague guidance.", "label": "meta"},
        ]
        Path(p["lessons_path"]).parent.mkdir(parents=True, exist_ok=True)
        Path(p["lessons_path"]).write_text(json.dumps(lessons))


def run_optimizer(out, optimizer):
    print(f"\n==================== {optimizer.upper()} ====================")
    shutil.rmtree(out, ignore_errors=True)
    r = call(C.cmd_init, out=out, optimizer=optimizer, seed=0, generations=1, pop=4, survivors=2,
             R=R, sims_eval=12, sims_final=24)
    seeds = r["seed_ids"]; check(len(seeds) == 4, f"4 seed prompts: {seeds}")

    print("== eval gen-0 prompts (R replicates each) ==")
    for i, aid in enumerate(seeds):
        ev = mock_eval(out, 0, aid, weak=(i == len(seeds) - 1))   # last seed = guaranteed loser
        check(ev["R_valid"] == R, f"{aid}: all R={R} bots valid")
        ev2 = store.read_json(store.agent_dir(out, 0, aid) / "evals.json", {})
        check(len(ev2.get("bot_means", [])) == R and "pooled_games" in ev2, f"{aid}: R bot_means + pooled_games stored")

    sc = call(C.cmd_score_pop, out=out, gen=0)
    check(sc["champion"] is not None, f"gen0 champion {sc['champion']} fit={round(sc['champion_fitness'],3)}")
    call(dctrl.cmd_population_summary, out=out, gen=0)
    sel = call(dctrl.cmd_select, out=out, gen=0, survivors=2)
    check(len(sel["survivors"]) == 2, f"survivors {sel['survivors']}")

    if optimizer == "core":
        rp = call(C.cmd_core_reflect_plan, out=out, gen=0, pairs=2, margin=0.0)
        check(rp["n_pairs"] >= 1, f"contrastive prompt pairs: {rp['n_pairs']}")
        mock_reflection(store.read_json(ccore.bank_dir(out) / "reflections" / "gen_00" / "reflect_plan.json", {}))
        ing = call(ccore.cmd_core_ingest, out=out, gen=0, max_lessons=4, plan="")
        check(ing["bank_size"] >= 1, f"insights ingested: {ing['bank_size']}")
        bp = call(C.cmd_core_breed_plan, out=out, gen=0, pop=4, survivors=2, topk=3)
    else:
        bp = call(C.cmd_breed_plan_gepa, out=out, gen=0, pop=4, survivors=2)
    plan = bp["plan"]; check(len(plan) == 2, f"2 offspring planned: {[p['new_id'] for p in plan]}")

    print("== mutate + eval + two-sample admit ==")
    for it in plan:
        mock_mutate(out, 0, it)
        check(C.load_prompt(out, 1, it["new_id"]).strip() != "", f"child {it['new_id']} prompt written")
        mock_eval(out, 1, it["new_id"])
        ad = call(C.cmd_admit, out=out, gen=1, child=it["new_id"], parent_gen=0, parent=it["parent_id"])
        check("ci_low" in ad and ad["test"] if "test" in ad else "ci_low" in ad,
              f"two-sample CI for {it['new_id']}: delta={round(ad['delta'],3)} CI=[{round(ad['ci_low'],3)},{round(ad['ci_high'],3)}] admitted={ad['admitted']}")

    if optimizer == "core":
        before = sum(l["uses"] for l in bankmod.Bank.load(ccore.bank_path(out)).lessons)
        cr = call(ccore.cmd_core_credit, out=out, gen=0)
        after = sum(l["uses"] for l in bankmod.Bank.load(ccore.bank_path(out)).lessons)
        check(cr["n_credited"] == 2 and after > before, f"insights credited via breed_context: {cr['n_credited']}, uses {before}->{after}")

    fin = call(dctrl.cmd_finalize_gen, out=out, gen=0, pop=4, survivors=2)
    check(len(fin["ids"]) == 4, f"gen1 refilled to pop=4: {fin['ids']}")
    g0 = store.read_json(store.gen_dir(out, 0) / "population_summary.json", {})["champion_fitness"]
    check(fin["champion_fitness"] >= g0 - 1e-9, f"champion monotone {round(g0,3)} -> {round(fin['champion_fitness'],3)}")

    fc = call(C.cmd_final_compare, out=out, sims=24, seed=0)
    check(fc["champion_fitness"] is not None and fc["gen0_best_fitness"] is not None,
          f"final-compare: champion {round(fc['champion_fitness'],3)} vs gen0_best {round(fc['gen0_best_fitness'],3)}")
    print(f"  {optimizer}: champion={fc['champion']} fit={round(fc['champion_fitness'],3)} | gen0_best={fc['gen0_best']} fit={round(fc['gen0_best_fitness'],3)}")


def main():
    run_optimizer("/tmp/cc_prompt_mock_gepa", "gepa")
    run_optimizer("/tmp/cc_prompt_mock_core", "core")
    print("\nALL MOCK CHECKS PASSED")


if __name__ == "__main__":
    try:
        main()
    except AssertionError:
        sys.exit(1)
