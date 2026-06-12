"""Deterministic controller for the CORE harness evolution.

Reuses cc_decomp's controller VERBATIM for everything shared with the GEPA run (init, harness
plan/assemble/validate, refine loop, ladder-anchored scoring, the PAIRED verified-acceptance gate,
selection, generation reconciliation, the verification gate, ablations, final eval) so the
GEPA-vs-CORE comparison is apples-to-apples. The ONLY new machinery is the CORE breeding cycle:

  core-reflect-plan  -> form winner/loser contrastive pairs from the scored generation
  (agents reflect)   -> Sonnet distils lessons per pair into JSON files
  core-ingest        -> add lessons to the persistent bank (dedup -> support++), snapshot
  core-breed-plan    -> per offspring: retrieve top-K lessons for the parent's weakness, write the
                        child's breed_context.json (the lesson-conditioned mutation reads it)
  (agents mutate / run harness / score / admit  -- all reused from cc_decomp)
  core-credit        -> verified-acceptance outcomes update lesson utility (admitted->win)

Each command prints a single JSON object on its last stdout line (the workflow reads it).
"""
import argparse
import contextlib
import io
import json
from pathlib import Path

from cc_decomp import control as dctrl
from cc_decomp import store

from . import bank, reflect


def emit(obj):
    print(json.dumps(obj))
    return obj


# ----------------------------------------------------------------- bank paths
def bank_dir(out):
    return Path(out) / "core_bank"


def bank_path(out):
    return bank_dir(out) / "bank.json"


def _snap(b, gen, out):
    p = bank_dir(out) / "snapshots.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a") as f:
        f.write(json.dumps(b.snapshot_row(gen)) + "\n")


# ----------------------------------------------------------------- init (reuse + bank)
def cmd_init(a):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):     # swallow the reused controller's own emit line
        r = dctrl.cmd_init(a)
    b = bank.Bank()
    b.save(bank_path(a.out))
    _snap(b, 0, a.out)
    r["bank_initialized"] = True
    r["bank_path"] = str(bank_path(a.out))
    return emit(r)


# ----------------------------------------------------------------- CORE breeding cycle
def cmd_core_reflect_plan(a):
    """Form contrastive winner/loser pairs from gen `a.gen`'s scored ranking and tell the workflow
    where each reflection agent should write its lessons."""
    rows = dctrl._ranked(a.out, a.gen)
    pairs = reflect.form_pairs(rows, a.pairs, margin=getattr(a, "margin", 0.03))
    refl_dir = bank_dir(a.out) / "reflections" / f"gen_{a.gen:02d}"
    plan = []
    for i, p in enumerate(pairs):
        ldir = store.agent_dir(a.out, a.gen, p["loser_id"])
        weakness = reflect.weakness_text(store.read_text(ldir / "planner_prompt.md"), p["loser_per_rung"])
        plan.append({
            "idx": i, "winner_id": p["winner_id"], "loser_id": p["loser_id"],
            "winner_dir": str(store.agent_dir(a.out, a.gen, p["winner_id"])),
            "loser_dir": str(ldir),
            "winner_fitness": round(p["winner_fitness"], 4), "loser_fitness": round(p["loser_fitness"], 4),
            "weakness": weakness, "lessons_path": str(refl_dir / f"pair_{i:02d}.json"),
        })
    store.write_json(refl_dir / "reflect_plan.json", {"gen": a.gen, "pairs": plan})
    return emit({"ok": True, "gen": a.gen, "n_pairs": len(plan), "plan": plan})


def cmd_core_ingest(a):
    """Read the lessons each reflection agent wrote, add them to the bank (dedup -> support++)."""
    refl_dir = bank_dir(a.out) / "reflections" / f"gen_{a.gen:02d}"
    plan_path = Path(a.plan) if getattr(a, "plan", "") else (refl_dir / "reflect_plan.json")
    plan = store.read_json(plan_path, {"pairs": []})
    b = bank.Bank.load(bank_path(a.out))
    added = merged = parsed = 0
    for p in plan["pairs"]:
        raw = store.read_text(Path(p["lessons_path"]))
        lessons = reflect.parse_lessons(raw, a.max_lessons)
        src = f"g{a.gen}:{p['winner_id']}>{p['loser_id']}"
        for text, label in lessons:
            lid, was_merged = b.add(text, label, p["weakness"], a.gen, source=src)
            if lid is None:
                continue
            parsed += 1
            merged += int(was_merged)
            added += int(not was_merged)
    b.save(bank_path(a.out))
    _snap(b, a.gen, a.out)
    return emit({"ok": True, "gen": a.gen, "added": added, "merged": merged,
                 "parsed": parsed, "bank_size": len(b.lessons),
                 "n_meta": sum(1 for l in b.lessons if l["label"] == "meta")})


def cmd_core_breed_plan(a):
    """Plan gen `a.gen+1`'s offspring. Same parent assignment as GEPA (survivors round-robin) so
    only the PROPOSAL differs: each child retrieves the top-K lessons for its parent's weakness and
    its breed_context.json drives a lesson-conditioned mutation."""
    rows = dctrl._ranked(a.out, a.gen)
    survivors = rows[: a.survivors]
    if not survivors:
        return emit({"ok": False, "error": "no survivors"})
    b = bank.Bank.load(bank_path(a.out))
    n_off = max(0, a.pop - a.survivors)
    ng = a.gen + 1
    champion_only = bool(getattr(a, "champion_only", 0))   # frontier probe: breed every child from the champion
    plan = []
    dirty = False
    for i in range(n_off):
        parent = survivors[0] if champion_only else survivors[i % len(survivors)]
        pid = parent["id"]
        new_id = f"g{ng:02d}_{i:02d}"
        cd = store.agent_dir(a.out, ng, new_id)
        exists = (cd / "planner_prompt.md").exists() and (cd / "decomposition.json").exists()
        if exists:                              # disk-resume: reuse the already-retrieved lessons
            lin = store.read_json(cd / "lineage.json", {})
            used = lin.get("lessons_used", [])
        else:
            weakness = reflect.weakness_text(
                store.read_text(store.agent_dir(a.out, a.gen, pid) / "planner_prompt.md"),
                parent.get("per_rung", {}))
            lessons = b.retrieve(weakness, a.topk, deterministic=False, mark=True)
            dirty = True
            used = [l["id"] for l in lessons]
            cd.mkdir(parents=True, exist_ok=True)
            store.write_json(cd / "lineage.json", {
                "parent_id": pid, "parent_gen": a.gen, "lens": "core",
                "origin": "core_mutation", "lessons_used": used, "changed_components": [], "diff": ""})
            store.write_json(cd / "breed_context.json", {
                "parent_id": pid, "parent_gen": a.gen,
                "parent_dir": str(store.agent_dir(a.out, a.gen, pid)),
                "weakness": weakness,
                "lessons": [{"id": l["id"], "text": l["text"], "label": l["label"]} for l in lessons]})
        plan.append({"new_id": new_id, "parent_id": pid, "parent_gen": a.gen, "lens": "core",
                     "type": "mutation", "exists": exists, "n_lessons": len(used), "lessons_used": used})
    if dirty:
        b.save(bank_path(a.out))             # persist the bumped retrieval-event counter
    return emit({"ok": True, "gen": a.gen, "next_gen": ng,
                 "survivors": [s["id"] for s in survivors], "plan": plan})


def cmd_core_frontier_plan(a):
    """FRONTIER probe: reframe the contrastive signal so it can target the CHAMPION itself. The
    champion is the winner in every population pair, so ordinary CORE never distils lessons about
    improving it. Here the negative trace is the champion's OWN losses to the rungs it cannot beat
    (strong/sonnet): we ask the analyst to contrast the champion harness against the opponents that
    beat it. Lessons are keyed to the champion's frontier weakness so the champion-only breeder
    retrieves them. Writes frontier_plan.json (same shape core-ingest reads via --plan)."""
    rows = dctrl._ranked(a.out, a.gen)
    if not rows:
        return emit({"ok": False, "error": "no champion"})
    champ = rows[0]
    cid = champ["id"]
    per = champ.get("per_rung", {})
    cdir = store.agent_dir(a.out, a.gen, cid)
    losing = sorted(((r, per[r]) for r in reflect.RUNGS if r in per), key=lambda t: t[1])[:2]
    weakness = reflect.weakness_text(store.read_text(cdir / "planner_prompt.md"), per)
    cfg = store.config(a.out)
    ladder = cfg.get("ladder", {})
    refl_dir = bank_dir(a.out) / "reflections" / f"gen_{a.gen:02d}"
    task = {
        "idx": 0, "frontier": True, "champion_id": cid, "champion_dir": str(cdir),
        "champion_fitness": round(champ.get("ladder_fitness", 0.0), 4),
        "per_rung": {k: round(v, 3) for k, v in per.items()},
        "losing_rungs": [r for r, _ in losing],
        "opponents": {r: ladder.get(r, r) for r, _ in losing},
        "weakness": weakness,
        "lessons_path": str(refl_dir / "frontier_00.json"),
    }
    store.write_json(refl_dir / "frontier_plan.json", {"gen": a.gen, "pairs": [task], "frontier": True})
    return emit({"ok": True, "gen": a.gen, "champion": cid,
                 "champion_fitness": task["champion_fitness"],
                 "losing_rungs": task["losing_rungs"], "plan": [task],
                 "plan_path": str(refl_dir / "frontier_plan.json")})


def cmd_core_credit(a):
    """Verified-acceptance outcomes credit the lessons each offspring used (admitted->win)."""
    ng = a.gen + 1
    ng_dir = store.gen_dir(a.out, ng) / "genotypes"
    b = bank.Bank.load(bank_path(a.out))
    credited = []
    if ng_dir.exists():
        for p in sorted(ng_dir.iterdir()):
            nm = p.name
            if nm.startswith("agent_") and nm[len("agent_"):].startswith(f"g{ng:02d}"):
                oid = nm[len("agent_"):]
            elif nm.startswith("_rejected_"):
                oid = nm[len("_rejected_"):]
            else:
                continue
            lin = store.read_json(p / "lineage.json", {})
            # lessons_used source of truth = breed_context.json (controller-owned; the mutation agent
            # only READS it). lineage.json is rewritten by that agent and may drop lessons_used.
            used = lin.get("lessons_used") or [
                l["id"] for l in store.read_json(p / "breed_context.json", {}).get("lessons", []) if l.get("id")]
            if lin.get("credited"):           # idempotent under resume
                continue
            if not used:
                continue
            m = store.read_json(p / "metrics.json", {})
            admitted = bool(m.get("verified_vs_parent", {}).get("admitted"))
            b.credit(used, admitted)
            lin["credited"] = True
            store.write_json(p / "lineage.json", lin)
            credited.append({"id": oid, "admitted": admitted, "n_lessons": len(used)})
    b.save(bank_path(a.out))
    _snap(b, ng, a.out)
    return emit({"ok": True, "gen": ng, "credited": credited, "n_credited": len(credited),
                 "bank_size": len(b.lessons)})


def cmd_bank_status(a):
    b = bank.Bank.load(bank_path(a.out))
    top = sorted(b.lessons, key=lambda l: (-b.utility(l), l["id"]))[:5]
    return emit({"ok": True, "bank_size": len(b.lessons),
                 "n_meta": sum(1 for l in b.lessons if l["label"] == "meta"),
                 "total_uses": sum(l["uses"] for l in b.lessons),
                 "total_wins": sum(l["wins"] for l in b.lessons),
                 "top": [{"id": l["id"], "label": l["label"], "uses": l["uses"], "wins": l["wins"],
                          "utility": round(b.utility(l), 3), "text": l["text"][:90]} for l in top]})


# ----------------------------------------------------------------- CLI (shared cmds delegate to cc_decomp)
def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p):
        p.add_argument("--out", required=True)

    # ---- shared with cc_decomp (delegated verbatim) ----
    p = sub.add_parser("init"); common(p)
    p.add_argument("--seed", type=int, default=0); p.add_argument("--generations", type=int, default=6)
    p.add_argument("--pop", type=int, default=12); p.add_argument("--survivors", type=int, default=4)
    p.add_argument("--refine-rounds", dest="refine_rounds", type=int, default=4)
    p.add_argument("--crossovers", type=int, default=0)
    p.add_argument("--sims-evolve", dest="sims_evolve", type=int, default=120)
    p.add_argument("--sims-admit", dest="sims_admit", type=int, default=200)
    p.add_argument("--sims-final", dest="sims_final", type=int, default=1500)
    p.set_defaults(fn=cmd_init)

    p = sub.add_parser("harness-plan"); common(p)
    p.add_argument("--gen", type=int, required=True); p.add_argument("--agent", required=True)
    p.set_defaults(fn=dctrl.cmd_harness_plan)

    p = sub.add_parser("assemble"); common(p)
    p.add_argument("--gen", type=int, required=True); p.add_argument("--agent", required=True)
    p.set_defaults(fn=dctrl.cmd_assemble)

    p = sub.add_parser("validate"); common(p)
    p.add_argument("--path", required=True); p.set_defaults(fn=dctrl.cmd_validate)

    for name, fn in (("refine-init", dctrl.cmd_refine_init), ("refine-keep", dctrl.cmd_refine_keep)):
        p = sub.add_parser(name); common(p)
        p.add_argument("--gen", type=int, default=0); p.add_argument("--agent", default="")
        p.add_argument("--simple", default=""); p.add_argument("--round", type=int, default=0)
        p.add_argument("--sims", type=int, default=30); p.add_argument("--seed", type=int, default=0)
        p.add_argument("--tester", type=int, default=0)
        p.set_defaults(fn=fn)

    p = sub.add_parser("score-pop"); common(p)
    p.add_argument("--gen", type=int, required=True); p.add_argument("--agent", default="")
    p.add_argument("--sims", type=int, default=120); p.add_argument("--seed", type=int, default=0)
    p.set_defaults(fn=dctrl.cmd_score_pop)

    p = sub.add_parser("select"); common(p)
    p.add_argument("--gen", type=int, required=True); p.add_argument("--survivors", type=int, default=4)
    p.set_defaults(fn=dctrl.cmd_select)

    p = sub.add_parser("admit"); common(p)
    p.add_argument("--gen", type=int, required=True); p.add_argument("--child", required=True)
    p.add_argument("--parent-gen", dest="parent_gen", type=int, required=True)
    p.add_argument("--parent", required=True)
    p.add_argument("--sims", type=int, default=200); p.add_argument("--seed", type=int, default=0)
    p.set_defaults(fn=dctrl.cmd_admit)

    p = sub.add_parser("finalize-gen"); common(p)
    p.add_argument("--gen", type=int, required=True); p.add_argument("--pop", type=int, default=12)
    p.add_argument("--survivors", type=int, default=4); p.set_defaults(fn=dctrl.cmd_finalize_gen)

    p = sub.add_parser("population-summary"); common(p)
    p.add_argument("--gen", type=int, required=True); p.set_defaults(fn=dctrl.cmd_population_summary)

    p = sub.add_parser("ladder-sanity"); common(p)
    p.add_argument("--sims", type=int, default=120); p.add_argument("--seed", type=int, default=4242)
    p.set_defaults(fn=dctrl.cmd_ladder_sanity)

    p = sub.add_parser("install-sonnet-rung"); common(p)
    p.add_argument("--path", required=True); p.set_defaults(fn=dctrl.cmd_install_sonnet_rung)

    p = sub.add_parser("status"); common(p)
    p.add_argument("--path", required=True); p.add_argument("--rounds", type=int, default=0)
    p.set_defaults(fn=dctrl.cmd_status)

    p = sub.add_parser("pick-best-of-n"); common(p)
    p.add_argument("--dir", required=True); p.add_argument("--n", type=int, required=True)
    p.add_argument("--sims", type=int, default=120); p.add_argument("--seed", type=int, default=0)
    p.set_defaults(fn=dctrl.cmd_pick_best_of_n)

    p = sub.add_parser("gate"); common(p)
    p.add_argument("--gen", type=int, default=0); p.add_argument("--agent", required=True)
    p.set_defaults(fn=dctrl.cmd_gate)

    p = sub.add_parser("final-eval"); common(p)
    p.add_argument("--gen", type=int, required=True); p.add_argument("--sims", type=int, default=1500)
    p.add_argument("--seed", type=int, default=0); p.set_defaults(fn=dctrl.cmd_final_eval)

    # ---- CORE-specific ----
    p = sub.add_parser("core-reflect-plan"); common(p)
    p.add_argument("--gen", type=int, required=True); p.add_argument("--pairs", type=int, default=4)
    p.add_argument("--margin", type=float, default=0.03)
    p.set_defaults(fn=cmd_core_reflect_plan)

    p = sub.add_parser("core-ingest"); common(p)
    p.add_argument("--gen", type=int, required=True)
    p.add_argument("--max-lessons", dest="max_lessons", type=int, default=4)
    p.add_argument("--plan", default="")            # optional explicit plan file (frontier probe)
    p.set_defaults(fn=cmd_core_ingest)

    p = sub.add_parser("core-breed-plan"); common(p)
    p.add_argument("--gen", type=int, required=True); p.add_argument("--pop", type=int, default=12)
    p.add_argument("--survivors", type=int, default=4); p.add_argument("--topk", type=int, default=3)
    p.add_argument("--champion-only", dest="champion_only", type=int, default=0)
    p.set_defaults(fn=cmd_core_breed_plan)

    p = sub.add_parser("core-frontier-plan"); common(p)
    p.add_argument("--gen", type=int, required=True); p.set_defaults(fn=cmd_core_frontier_plan)

    p = sub.add_parser("core-credit"); common(p)
    p.add_argument("--gen", type=int, required=True); p.set_defaults(fn=cmd_core_credit)

    p = sub.add_parser("bank-status"); common(p)
    p.set_defaults(fn=cmd_bank_status)

    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
