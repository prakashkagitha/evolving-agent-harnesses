"""Token-free end-to-end test of the budget-constrained allocation controller (both GEPA and CORE).

Mocks every LLM agent (draft / specialist / merge / revise bot-writers, GEPA lens mutator, CORE
contrastive reflection + lesson-conditioned mutator) by writing plausible files, then drives the full
recipe pipeline through one generation for EACH optimizer:
  init -> execute every seed recipe (drafts/specialists+merge/revisions -> one bot) -> score -> select
       -> breed (gepa lens OR core reflect+retrieve) -> mutate -> execute child -> admit -> finalize
       -> final-compare.
Verifies budget accounting (every recipe spends exactly B calls' worth of structure), valid produced
bots, the paired CI, monotone champion, and the CORE bank credit. NO model tokens.

Run:  python3 -m cc_alloc._mocktest    (exits non-zero on any failed assertion)
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

from . import control_alloc as C
from . import recipe

B = 6


def call(fn, **kw):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        return fn(NS(**kw))


def check(cond, msg):
    print(("  OK  " if cond else " FAIL ") + msg)
    if not cond:
        raise AssertionError(msg)


def _strong(out):
    return (store.ladder_dir(out) / "strong.py").read_text()


def mock_run_recipe(out, gen, aid):
    """Mock the B bot-writing calls for one recipe, then drive build/revise/finalize."""
    plan = call(C.cmd_recipe_plan, out=out, gen=gen, agent=aid, B=B)
    d = store.agent_dir(out, gen, aid)
    (d / "candidates").mkdir(parents=True, exist_ok=True)
    for k in range(plan["n_draft"]):
        store.write_text(d / "candidates" / f"draft_{k}.py", _strong(out))
    concerns = plan["concerns"][: plan["n_spec"]]
    for c in concerns:
        store.write_text(d / "specialists" / f"{c}.py", MOCK_SPECIALISTS[c])
    if plan["do_merge"]:
        store.write_text(d / "specialists" / "_referee.py", MOCK_REFEREE)
    call(C.cmd_recipe_build_base, out=out, gen=gen, agent=aid, B=B, sims_cand=12, seed=0)
    for r in range(1, plan["n_revise"] + 1):
        store.write_text(d / "candidates" / f"revise_{r}.py", _strong(out))   # a valid (non-regressing) revision
        call(C.cmd_recipe_revise_keep, out=out, gen=gen, agent=aid, round=r, sims_cand=12, seed=0)
    fin = call(C.cmd_recipe_finalize, out=out, gen=gen, agent=aid, B=B)
    return plan, fin


def mock_mutate_recipe(out, gen, item, lessons_used=None):
    """Mock the outer optimizer: copy parent recipe, apply one budget-preserving edit."""
    pg, pid, nid = item["parent_gen"], item["parent_id"], item["new_id"]
    geno = recipe.load(out, pg, pid)
    a = dict(geno["alloc"])
    # a simple budget-preserving edit: move one call from n_draft (or n_revise) into n_revise (or n_draft)
    if a["n_draft"] >= 1:
        a["n_draft"] -= 1; a["n_revise"] += 1
    else:
        a["n_revise"] = max(0, a["n_revise"] - 1); a["n_draft"] += 1
    child = {"id": nid, "alloc": a, "concerns": geno["concerns"], "draft_prompt": geno["draft_prompt"],
             "lineage": store.read_json(store.agent_dir(out, gen + 1, nid) / "lineage.json", {})}
    recipe.save(out, gen + 1, child)


def mock_reflection(plan):
    for p in plan["pairs"]:
        lessons = [
            {"lesson": "Spend most of the budget on revisions rather than many independent drafts.", "label": "specific"},
            {"lesson": "Decomposition beats best-of-N only when at least three specialists are merged.", "label": "specific"},
            {"lesson": "Make one small verified change at a time.", "label": "meta"},
        ]
        Path(p["lessons_path"]).parent.mkdir(parents=True, exist_ok=True)
        Path(p["lessons_path"]).write_text(json.dumps(lessons))


def run_optimizer(out, optimizer):
    print(f"\n==================== {optimizer.upper()} ====================")
    shutil.rmtree(out, ignore_errors=True)
    r = call(C.cmd_init, out=out, B=B, optimizer=optimizer, seed=0, generations=1, pop=4, survivors=2,
             sims_cand=12, sims_evolve=16, sims_admit=24, sims_final=24)
    seeds = r["seed_ids"]
    check(len(seeds) == 4, f"4 seed recipes: {r['seed_allocs']}")
    check(all(recipe.is_valid(recipe.load(out, 0, s), B) for s in seeds), "all seed recipes are valid budget-B allocations")

    print("== execute gen-0 recipes ==")
    for i, aid in enumerate(seeds):
        plan, fin = mock_run_recipe(out, 0, aid)
        b = plan["n_draft"] + plan["n_spec"] + plan["do_merge"] + plan["n_revise"]
        check(b == B, f"recipe {aid} spends exactly B={B} calls (alloc {plan['alloc_label']})")
        if i == len(seeds) - 1:   # make the last seed a GUARANTEED loser so a contrastive pair always forms
            store.write_text(store.produced_bot_path(out, 0, aid), (store.ladder_dir(out) / "weak.py").read_text())
        bot = store.produced_bot_path(out, 0, aid)
        ok, reason = dctrl._validate(str(bot))
        check(ok, f"produced bot valid [{aid}]: {reason}")

    sc = call(dctrl.cmd_score_pop, out=out, gen=0, agent="", sims=16, seed=0)
    check(sc["champion"] is not None, f"gen0 champion {sc['champion']} fit={round(sc['champion_fitness'],3)}")
    call(dctrl.cmd_population_summary, out=out, gen=0)
    sel = call(dctrl.cmd_select, out=out, gen=0, survivors=2)
    check(len(sel["survivors"]) == 2, f"survivors {sel['survivors']}")

    if optimizer == "core":
        rp = call(C.cmd_core_reflect_plan, out=out, gen=0, pairs=2, margin=0.0)
        check(rp["n_pairs"] >= 1, f"contrastive recipe pairs formed: {rp['n_pairs']}")
        plan = store.read_json(ccore.bank_dir(out) / "reflections" / "gen_00" / "reflect_plan.json", {})
        mock_reflection(plan)
        ing = call(ccore.cmd_core_ingest, out=out, gen=0, max_lessons=4, plan="")
        check(ing["bank_size"] >= 1, f"lessons ingested: {ing}")
        bp = call(C.cmd_core_breed_plan, out=out, gen=0, pop=4, survivors=2, topk=3)
    else:
        bp = call(C.cmd_breed_plan_gepa, out=out, gen=0, pop=4, survivors=2)
    plan = bp["plan"]
    check(len(plan) == 2, f"2 offspring planned: {[p['new_id'] for p in plan]}")

    print("== mutate + execute + admit offspring ==")
    for it in plan:
        mock_mutate_recipe(out, 0, it)
        check(recipe.is_valid(recipe.repair(recipe.load(out, 1, it["new_id"]), B), B), f"child {it['new_id']} repairs to valid budget-B")
        mock_run_recipe(out, 1, it["new_id"])
        ad = call(dctrl.cmd_admit, out=out, gen=1, child=it["new_id"], parent_gen=0, parent=it["parent_id"], sims=24, seed=0)
        check("ci_low" in ad, f"paired CI for {it['new_id']}: delta={round(ad['delta'],3)} admitted={ad['admitted']}")

    if optimizer == "core":
        before = sum(l["uses"] for l in bankmod.Bank.load(ccore.bank_path(out)).lessons)
        cr = call(ccore.cmd_core_credit, out=out, gen=0)
        after = sum(l["uses"] for l in bankmod.Bank.load(ccore.bank_path(out)).lessons)
        check(cr["n_credited"] == 2 and after > before, f"lessons credited: {cr['n_credited']}, uses {before}->{after}")

    fin = call(dctrl.cmd_finalize_gen, out=out, gen=0, pop=4, survivors=2)
    check(len(fin["ids"]) == 4, f"gen1 refilled to pop=4: {fin['ids']}")
    g0 = store.read_json(store.gen_dir(out, 0) / "population_summary.json", {})["champion_fitness"]
    check(fin["champion_fitness"] >= g0 - 1e-9, f"champion monotone {round(g0,3)} -> {round(fin['champion_fitness'],3)}")

    fc = call(C.cmd_final_compare, out=out, sims=24, seed=0)
    check(fc["champion_mean"] is not None and fc["best_of_b_mean"] is not None,
          f"final-compare: champion {round(fc['champion_mean'],3)} vs best_of_b {round(fc['best_of_b_mean'],3)}")
    print(f"  {optimizer}: champion={fc['champion']} mean={round(fc['champion_mean'],3)} | best_of_b={round(fc['best_of_b_mean'],3)}")


def main():
    # bank unit (reused mechanism) sanity
    run_optimizer("/tmp/cc_alloc_mock_gepa", "gepa")
    run_optimizer("/tmp/cc_alloc_mock_core", "core")
    print("\nALL MOCK CHECKS PASSED")


if __name__ == "__main__":
    try:
        main()
    except AssertionError:
        sys.exit(1)
