"""Token-free end-to-end test of the CORE controller + lesson bank.

Mocks every LLM agent (planner, specialists, referee, debugger, the CONTRASTIVE-REFLECTION analyst,
and the lesson-conditioned MUTATION operator) by writing plausible files directly, then drives the
full CORE pipeline through one generation:
  init -> ladder -> sonnet rung -> ablations -> gen-0 harnesses -> score
       -> core-reflect-plan -> (mock reflection writes lessons) -> core-ingest (bank grows, dedup)
       -> core-breed-plan (retrieve top-K) -> (mock mutation applies lessons) -> harness -> admit
       -> core-credit (lesson utility updates) -> finalize -> final-eval.
Also unit-tests the bank (embedding determinism, dedup/support, retrieval ordering, credit/utility).

Run:  python3 -m cc_core._mocktest      (exits non-zero on any failed assertion; NO model tokens.)
"""
import json
import shutil
import sys
from pathlib import Path
from types import SimpleNamespace as NS

from cc_decomp import store
from cc_decomp._mocktest import mock_harness, mock_simple, MOCK_SPECIALISTS

from . import bank, control, reflect

OUT = "/tmp/cc_core_mocktest"


def check(cond, msg):
    print(("  OK  " if cond else " FAIL ") + msg)
    if not cond:
        raise AssertionError(msg)


# ----- mock the two CORE agents ---------------------------------------------
def mock_reflection(plan):
    """Mock the Sonnet contrastive-reflection analyst: write a lessons JSON array per pair. We vary
    one lesson by winner_id so distinct lessons accrue, and repeat a shared lesson so dedup fires."""
    for p in plan["pairs"]:
        lessons = [
            {"lesson": "Always keep a flood-fill space_control specialist to veto self-trapping moves.",
             "label": "specific"},
            {"lesson": f"Add a combat specialist when weak vs the {p['winner_id']} matchup head-to-head.",
             "label": "specific"},
            {"lesson": "Prefer a small single-aspect change and verify it before keeping it.",
             "label": "meta"},
        ]
        Path(p["lessons_path"]).parent.mkdir(parents=True, exist_ok=True)
        Path(p["lessons_path"]).write_text(json.dumps(lessons))


def mock_mutation(out, gen, off):
    """Mock the lesson-conditioned mutation: read breed_context, apply by ADDING one specialist
    (a 'decomposition' style edit), keep planner_prompt, preserve lessons_used in lineage."""
    pd = store.agent_dir(out, off["parent_gen"], off["parent_id"])
    cd = store.agent_dir(out, gen + 1, off["new_id"])
    ctx = store.read_json(cd / "breed_context.json", {})
    pp = store.read_text(pd / "planner_prompt.md")
    dec = store.read_json(pd / "decomposition.json", {})
    diff = "no-op"
    for s in store.SPECIALIST_MENU:
        if s not in dec.get("specialists", []):
            dec["specialists"] = dec.get("specialists", []) + [s]
            diff = f"+specialist {s} (applied lessons {','.join(off.get('lessons_used', []))})"
            break
    store.write_text(cd / "planner_prompt.md", pp)
    store.write_json(cd / "decomposition.json", dec)
    lin = store.read_json(cd / "lineage.json", {})
    lin["changed_components"] = ["decomposition"]
    lin["diff"] = diff
    check("lessons_used" in lin, f"breed_plan pre-wrote lessons_used for {off['new_id']}")
    store.write_json(cd / "lineage.json", lin)
    check(isinstance(ctx.get("lessons"), list), f"breed_context.json has lessons for {off['new_id']}")


# ----- bank unit test --------------------------------------------------------
def test_bank_unit():
    print("== bank unit ==")
    b = bank.Bank()
    e1 = bank.embed("flood fill space control veto self-trap")
    e1b = bank.embed("flood fill space control veto self-trap")
    check(list(e1) == list(e1b), "embedding is deterministic")
    check(abs(float((e1 * e1).sum()) - 1.0) < 1e-9, "embedding is L2-normalised")
    far = bank.cosine(bank.embed("combat head-to-head aggression"), bank.embed("food health growth"))
    near = bank.cosine(bank.embed("flood fill space control"), bank.embed("space control reachable room"))
    check(near > far, f"related texts more similar than unrelated ({near:.2f} > {far:.2f})")

    lid1, m1 = b.add("Keep a space_control specialist to veto self-traps.", "specific",
                     "weak vs strong rung. strategy: control space", 0)
    lid2, m2 = b.add("Keep a space_control specialist to veto self-traps.", "specific",
                     "weak vs moderate rung", 0)   # near-duplicate -> merge
    check(not m1 and m2 and lid1 == lid2, f"dedup merges near-duplicate (support++): {lid1}=={lid2}")
    check(b.lessons[0]["support"] == 2, "merged lesson support == 2")
    b.add("Add combat for head-to-head pressure.", "specific", "weak vs strong rung combat", 0)
    b.add("Make one small verified change at a time.", "meta", "general", 0)
    check(len(b.lessons) == 3, f"3 distinct lessons after dedup: {len(b.lessons)}")

    got = b.retrieve("weak vs strong rung. strategy: control space and never trap", K=2, deterministic=True)
    check(len(got) == 2, "retrieve returns K lessons")
    check(got[0]["text"].lower().startswith("keep a space"), "most-relevant lesson ranked first")

    # credit: a used lesson that leads to an admitted mutation gains utility
    u0 = b.utility(b.lessons[0])
    b.credit([b.lessons[0]["id"]], admitted=True)
    b.credit([b.lessons[1]["id"]], admitted=False)
    check(b.utility(b.lessons[0]) > u0, "admitted-win raises lesson utility")
    check(b.lessons[1]["uses"] == 1 and b.lessons[1]["wins"] == 0, "rejected use raises uses, not wins")


def main():
    shutil.rmtree(OUT, ignore_errors=True)
    test_bank_unit()

    print("== init (+ empty bank) ==")
    r = control.cmd_init(NS(out=OUT, seed=0, generations=1, pop=4, survivors=2, refine_rounds=2,
                            crossovers=0, sims_evolve=24, sims_admit=40, sims_final=40))
    seeds_ids = r["seed_ids"]; check(len(seeds_ids) == 4, f"4 seeds: {seeds_ids}")
    check(r["bank_initialized"] and Path(control.bank_path(OUT)).exists(), "empty bank initialised")

    print("== sonnet rung + ladder sanity ==")
    son = Path(OUT) / "ablations" / "sonnet_rung"
    mock_simple(OUT, son, tester=1, rounds=2)
    control.dctrl.cmd_install_sonnet_rung(NS(out=OUT, path=str(son / "produced_bot" / "main.py")))
    s = control.dctrl.cmd_ladder_sanity(NS(out=OUT, sims=90, seed=4242))
    check(s["order_ok"], f"ladder ranks weak<moderate<strong: {s['fitness']}")

    print("== ablations ==")
    mock_simple(OUT, Path(OUT) / "ablations" / "simple_refine", tester=1, rounds=2)
    bon = Path(OUT) / "ablations" / "best_of_n"
    for k in range(2):
        mock_simple(OUT, bon / f"run_{k}", tester=0, rounds=1)
    (bon / "best").mkdir(parents=True, exist_ok=True)
    shutil.copy(bon / "run_0" / "produced_bot" / "main.py", bon / "best" / "main.py")

    print("== gen-0 harnesses + score ==")
    for aid in seeds_ids:
        mock_harness(OUT, 0, aid)
    sc = control.dctrl.cmd_score_pop(NS(out=OUT, gen=0, agent="", sims=24, seed=0))
    check(sc["champion"] is not None, f"champion: {sc['champion']} fit={round(sc['champion_fitness'],3)}")
    control.dctrl.cmd_population_summary(NS(out=OUT, gen=0))

    print("== gate ==")
    g = control.dctrl.cmd_gate(NS(out=OUT, gen=0, agent=seeds_ids[0]))
    check(g["pass"], f"verification gate passes: {g}")

    print("== CORE: reflect-plan -> reflection -> ingest ==")
    sel = control.dctrl.cmd_select(NS(out=OUT, gen=0, survivors=2))
    rp = control.cmd_core_reflect_plan(NS(out=OUT, gen=0, pairs=2, margin=0.0))
    check(rp["n_pairs"] >= 1, f"contrastive pairs formed: {rp['n_pairs']}")
    plan = store.read_json(control.bank_dir(OUT) / "reflections" / "gen_00" / "reflect_plan.json", {})
    mock_reflection(plan)
    ing = control.cmd_core_ingest(NS(out=OUT, gen=0, max_lessons=4))
    check(ing["bank_size"] >= 1, f"lessons ingested into bank: {ing}")
    check(ing["merged"] >= 1, f"dedup fired across pairs (shared lesson merged): merged={ing['merged']}")
    check(ing["n_meta"] >= 1, "at least one meta lesson")

    print("== CORE: breed-plan (retrieve) -> mutation -> harness -> admit ==")
    bp = control.cmd_core_breed_plan(NS(out=OUT, gen=0, pop=4, survivors=2, topk=3))
    bplan = bp["plan"]; check(len(bplan) == 2, f"2 offspring planned: {[p['new_id'] for p in bplan]}")
    check(all(p["n_lessons"] >= 1 for p in bplan), f"each offspring retrieved lessons: {[p['n_lessons'] for p in bplan]}")
    for off in bplan:
        mock_mutation(OUT, 0, off)
        mock_harness(OUT, 1, off["new_id"])
        ad = control.dctrl.cmd_admit(NS(out=OUT, gen=1, child=off["new_id"], parent_gen=0,
                                        parent=off["parent_id"], sims=40, seed=0))
        check("ci_low" in ad, f"paired CI for {off['new_id']}: delta={round(ad['delta'],3)} "
              f"CI=[{round(ad['ci_low'],3)},{round(ad['ci_high'],3)}] admitted={ad['admitted']}")

    print("== CORE: credit lessons (utility update) ==")
    before = bank.Bank.load(control.bank_path(OUT))
    uses_before = sum(l["uses"] for l in before.lessons)
    cr = control.cmd_core_credit(NS(out=OUT, gen=0))
    check(cr["n_credited"] == 2, f"both offspring credited: {cr['n_credited']}")
    after = bank.Bank.load(control.bank_path(OUT))
    uses_after = sum(l["uses"] for l in after.lessons)
    check(uses_after > uses_before, f"credit incremented lesson uses: {uses_before} -> {uses_after}")
    # idempotent under resume
    cr2 = control.cmd_core_credit(NS(out=OUT, gen=0))
    check(cr2["n_credited"] == 0, "credit is idempotent (no double-credit on resume)")

    print("== finalize gen 0 -> gen 1 ==")
    fin = control.dctrl.cmd_finalize_gen(NS(out=OUT, gen=0, pop=4, survivors=2))
    check(len(fin["ids"]) == 4, f"gen1 refilled to pop=4: {fin['ids']}")
    g0 = store.read_json(store.gen_dir(OUT, 0) / "population_summary.json", {})["champion_fitness"]
    check(fin["champion_fitness"] >= g0 - 1e-9, f"champion fitness monotone: {round(g0,3)} -> {round(fin['champion_fitness'],3)}")

    print("== final eval + analysis ==")
    fe = control.dctrl.cmd_final_eval(NS(out=OUT, gen=1, sims=40, seed=0))
    check("champion" in fe["headline"], "final headline has champion")
    from . import analysis
    analysis.analyze(OUT)
    data = store.read_json(Path(OUT) / "analysis_data.json", {})
    check("core_bank" in data and data["core_bank"]["bank_size"] >= 1, "analysis wrote core_bank block")
    check("## 7. CORE lesson bank" in store.read_text(Path(OUT) / "analysis.md"), "analysis.md has CORE section")

    bs = control.cmd_bank_status(NS(out=OUT))
    check(bs["bank_size"] >= 1, f"bank-status ok: {bs['bank_size']} lessons, {bs['total_wins']} wins")

    print("\nALL MOCK CHECKS PASSED")


if __name__ == "__main__":
    try:
        main()
    except AssertionError:
        sys.exit(1)
