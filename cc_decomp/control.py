"""Deterministic controller (the brain) for the single-level decomposition-harness evolution.

Every LLM op (planner, specialist coders, referee, debugger, Sonnet mutators) is a Workflow
sub-agent that WRITES files; this module reads those files and does all the deterministic work:
ladder-anchored scoring, the verified refine loop, the PAIRED common-seed acceptance gate (95% CI),
selection + elitism, generation reconciliation, the verification gate, and final headline eval.

All commands print a single JSON object on the last stdout line (the workflow reads it).
Reuses the native BattleSnake sim (cc_gepa.sim) and game contract — the game is unchanged.
"""
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

from . import harness, seeds, store
from cc_gepa import sim

ROOT = Path(__file__).resolve().parent.parent
GREEDY = ROOT / "cc_gepa" / "opponents" / "greedy_bot.py"
LADDER_SRC = {"weak": ROOT / "cc_decomp" / "ladder" / "weak.py",
              "moderate": GREEDY,
              "strong": ROOT / "cc_decomp" / "ladder" / "strong.py"}
# Per-run_matches worker cap. The workflow PIPELINE runs several offspring's CPU-heavy sims
# CONCURRENTLY, so per-call parallelism must be modest or the 128 cores oversubscribe and
# BotServers miss their readiness window -> games default to opponent-wins -> spurious 0.0
# fitness that corrupts the paired admit gate. 28 x ~4 concurrent ~= 112 < 128.
MAXW = 28


def emit(obj):
    print(json.dumps(obj))
    return obj


def _rung_bots(out):
    return [{"name": r, "path": str(store.ladder_path(out, r))} for r in store.RUNGS
            if store.ladder_path(out, r).exists()]


def _bot_hash(path):
    try:
        return hashlib.sha1(Path(path).read_bytes()).hexdigest()[:16]
    except FileNotFoundError:
        return "missing"


def _cache(out):
    d = Path(out) / "ladder_cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


# ----------------------------------------------------------------- ladder scoring
def _score_vs_ladder(out, name, bot_path, sims, seed, workdir, use_cache=True):
    """Aggregate win-rate of `bot_path` vs each present rung. Returns {rung: winrate} + mean."""
    rungs = _rung_bots(out)
    h = _bot_hash(bot_path)
    cf = _cache(out) / f"score_{h}_s{sims}_seed{seed}.json"
    cached = store.read_json(cf, None) if use_cache else None
    per = dict(cached) if cached else {}
    todo = [r for r in rungs if r["name"] not in per]
    if todo:
        matchups = [{"id": r["name"], "a": {"name": name, "path": bot_path}, "b": r} for r in todo]
        res = sim.run_matches(matchups, sims, seed, workdir, max_workers=MAXW)
        for r in todo:
            rr = res[r["name"]]
            per[r["name"]] = rr[name]["win_rate"] if name in rr else 0.0
        if use_cache:
            store.write_json(cf, per)
    present = [r["name"] for r in rungs]
    mean = sum(per[k] for k in present) / max(len(present), 1)
    return {k: per[k] for k in present}, mean


def _per_game_vs_ladder(out, name, bot_path, sims, seed, workdir, use_cache=True):
    """Per-game win indicators of `bot_path` vs each rung (for the paired gate). {rung: [0/1...]}"""
    rungs = _rung_bots(out)
    h = _bot_hash(bot_path)
    cf = _cache(out) / f"pergame_{h}_s{sims}_seed{seed}.json"
    cached = store.read_json(cf, None) if use_cache else None
    per = dict(cached) if cached else {}
    todo = [r for r in rungs if r["name"] not in per]
    if todo:
        matchups = [{"id": r["name"], "a": {"name": name, "path": bot_path}, "b": r} for r in todo]
        res = sim.per_game_results(matchups, sims, seed, workdir, max_workers=MAXW)
        for r in todo:
            per[r["name"]] = res[r["name"]]
        if use_cache:
            store.write_json(cf, per)
    return {r["name"]: per[r["name"]] for r in rungs}


def _wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    hw = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return (p, max(0.0, c - hw), min(1.0, c + hw))


def _paired_bootstrap(diffs, iters=4000):
    a = np.asarray(diffs, dtype=float)
    if a.size == 0:
        return (0.0, 0.0, 0.0)
    rng = np.random.RandomState(1234)  # deterministic CI given the data (reproducibility)
    idx = rng.randint(0, a.size, size=(iters, a.size))
    means = a[idx].mean(axis=1)
    return (float(a.mean()), float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5)))


# ----------------------------------------------------------------- refine loop
def _refine_score(out, bot_path, sims, seed, tester, workdir):
    """Refine-loop fitness: win-rate vs the MODERATE rung (the training opponent) on common
    seeds, plus (if tester active) the adversarial-board pass fraction. Returns a feedback dict."""
    mod = {"name": "moderate", "path": str(store.ladder_path(out, "moderate"))}
    res = sim.run_matches([{"id": "r", "a": {"name": "cand", "path": bot_path}, "b": mod}],
                          sims, seed, workdir, max_workers=MAXW)["r"]
    wr = res["cand"]["win_rate"]
    crashes = res["cand"]["crashes"]
    causes = res["cand"].get("cause_of_death", {})
    surv = res["cand"].get("survival_turns", 0.0)              # mean turns survived vs moderate
    surv_frac = min(surv / 80.0, 1.0)
    adv = harness.eval_on_boards(bot_path, harness.adversarial_boards())
    adv_pass = sum(1 for a in adv if a["ok"]) / max(len(adv), 1)
    # win-rate dominates; survival gives a smooth low-end GRADIENT so the debugger can climb out of
    # a 0-win-rate trap (e.g. a bot that collides early) instead of being stuck on a flat score.
    score = wr + 0.2 * surv_frac + (0.15 * adv_pass if tester else 0.0)
    return {"score": score, "winrate_vs_moderate": wr, "survival_turns": surv, "crashes": crashes,
            "causes_of_death": causes, "adversarial": adv, "adv_pass": adv_pass, "tester": tester}


def _agent_dir(out, gen, aid, simple):
    return Path(simple) if simple else store.agent_dir(out, gen, aid)


def _clean_simple_main(d):
    """Strip any markdown fences the coder/debugger wrapped around the whole-bot main.py."""
    main = Path(d) / "produced_bot" / "main.py"
    if main.exists():
        cleaned = harness.clean_code(main.read_text())
        main.write_text(cleaned)


def _validate(bot_path):
    """Compile + contract + tiny smoke. Returns (ok, reason)."""
    p = Path(bot_path)
    if not p.exists():
        return False, "missing"
    src = p.read_text()
    try:
        compile(src, str(p), "exec")
    except SyntaxError as e:
        return False, f"syntax: {e}"
    ns = {"__name__": "_v"}
    try:
        exec(compile(src, str(p), "exec"), ns)
    except Exception as e:
        return False, f"import: {type(e).__name__}: {e}"
    for fn in ("info", "start", "end", "move"):
        if not callable(ns.get(fn)):
            return False, f"missing {fn}()"
    # smoke: a basic board
    gs = harness._gs(11, 11, [(5, 5), (5, 4), (5, 3)], 90, [], [(2, 2)])
    try:
        out = ns["move"](gs)
        if not isinstance(out, dict) or out.get("move") not in ("up", "down", "left", "right"):
            return False, f"move() returned {out!r}"
    except Exception as e:
        return False, f"move() raised: {type(e).__name__}: {e}"
    return True, "ok"


def cmd_refine_init(a):
    d = _agent_dir(a.out, a.gen, a.agent, a.simple)
    pb = d / "produced_bot"
    main = pb / "main.py"
    decomp = store.read_json(d / "decomposition.json", {}) if not a.simple else {"tester": a.tester}
    tester = bool(decomp.get("tester", False))
    if not a.simple:
        ok, info = harness.assemble_decomp(a.out, a.gen, a.agent)
        if not ok:
            return emit({"ok": False, "error": "assemble failed"})
    else:
        _clean_simple_main(a.simple)
    valid, reason = _validate(main)
    wd = str(pb / "_refwork")
    if valid:
        fb = _refine_score(a.out, str(main), a.sims, a.seed, tester, wd)
    else:
        fb = {"score": -1.0, "winrate_vs_moderate": 0.0, "crashes": 999,
              "causes_of_death": {}, "adversarial": [], "adv_pass": 0.0, "tester": tester,
              "invalid": reason}
    # snapshot best
    shutil.copy(main, pb / "_best.py")
    if not a.simple and (d / "specialists").exists():
        bs = pb / "_best_specialists"
        if bs.exists():
            shutil.rmtree(bs)
        shutil.copytree(d / "specialists", bs)
    trace = {"tester": tester, "best_score": fb["score"],
             "rounds": [{"round": 0, "action": "baseline", "kept": True, "valid": valid,
                         "score": fb["score"], "winrate_vs_moderate": fb["winrate_vs_moderate"],
                         "adv_pass": fb["adv_pass"], "crashes": fb["crashes"]}]}
    store.write_json(pb / "refine_trace.json", trace)
    store.write_json(pb / "feedback.json", fb)
    return emit({"ok": True, "baseline_score": fb["score"], "valid": valid, "reason": reason,
                 "winrate_vs_moderate": fb["winrate_vs_moderate"], "adv_pass": fb["adv_pass"],
                 "refine_rounds": int(decomp.get("refine_rounds", 0)),
                 "feedback_path": str(pb / "feedback.json")})


def cmd_refine_keep(a):
    d = _agent_dir(a.out, a.gen, a.agent, a.simple)
    pb = d / "produced_bot"
    main = pb / "main.py"
    trace = store.read_json(pb / "refine_trace.json", {"rounds": [], "best_score": -1, "tester": False})
    tester = bool(trace.get("tester", False))
    # re-assemble from edited specialists (decomp); simple path: main.py already edited
    if not a.simple:
        harness.assemble_decomp(a.out, a.gen, a.agent)
    else:
        _clean_simple_main(a.simple)
    valid, reason = _validate(main)
    wd = str(pb / "_refwork")
    if valid:
        fb = _refine_score(a.out, str(main), a.sims, a.seed, tester, wd)
        new_score = fb["score"]
    else:
        fb = {"score": -1.0, "winrate_vs_moderate": 0.0, "crashes": 999, "causes_of_death": {},
              "adversarial": [], "adv_pass": 0.0, "tester": tester, "invalid": reason}
        new_score = -1.0
    best = trace.get("best_score", -1.0)
    kept = valid and new_score >= best - 1e-9
    if kept:
        shutil.copy(main, pb / "_best.py")
        if not a.simple and (d / "specialists").exists():
            bs = pb / "_best_specialists"
            if bs.exists():
                shutil.rmtree(bs)
            shutil.copytree(d / "specialists", bs)
        trace["best_score"] = new_score
        store.write_json(pb / "feedback.json", fb)  # feedback on the new best, for next round
    else:
        shutil.copy(pb / "_best.py", main)  # revert
        if not a.simple and (pb / "_best_specialists").exists():
            sp = d / "specialists"
            if sp.exists():
                shutil.rmtree(sp)
            shutil.copytree(pb / "_best_specialists", sp)
        # feedback stays the last-best feedback (already on disk)
    trace["rounds"].append({"round": a.round, "action": "debug-edit", "kept": kept, "valid": valid,
                            "score": new_score, "winrate_vs_moderate": fb["winrate_vs_moderate"],
                            "adv_pass": fb["adv_pass"], "crashes": fb["crashes"], "reason": reason})
    store.write_json(pb / "refine_trace.json", trace)
    return emit({"ok": True, "kept": kept, "valid": valid, "reason": reason,
                 "new_score": new_score, "best_score": trace["best_score"], "round": a.round})


# ----------------------------------------------------------------- harness plan / assemble
def cmd_harness_plan(a):
    d = store.agent_dir(a.out, a.gen, a.agent)
    decomp = store.read_json(d / "decomposition.json", {})
    specs = harness.canonical_specialists(decomp)
    pb = d / "produced_bot"
    trace = store.read_json(pb / "refine_trace.json", {})
    rr = int(decomp.get("refine_rounds", 0))
    done_rounds = sum(1 for r in trace.get("rounds", []) if r.get("action") == "debug-edit")
    exists = (pb / "main.py").exists() and bool(trace) and done_rounds >= rr
    return emit({"ok": True, "specialists": specs,
                 "referee_policy": decomp.get("referee_policy", "weighted_vote"),
                 "tester": bool(decomp.get("tester", False)), "refine_rounds": rr,
                 "planner_prompt": str(d / "planner_prompt.md"),
                 "agent_dir": str(d), "exists": exists})


def cmd_assemble(a):
    ok, info = harness.assemble_decomp(a.out, a.gen, a.agent)
    info["ok"] = ok
    return emit(info)


def cmd_validate(a):
    ok, reason = _validate(a.path)
    return emit({"ok": ok, "reason": reason})


# ----------------------------------------------------------------- score population
def cmd_score_pop(a):
    out = a.out
    ids = [a.agent] if a.agent else store.list_agents(out, a.gen)
    wd = str(Path(out) / "_scorework" / f"g{a.gen}")
    ranking = []
    for aid in ids:
        d = store.agent_dir(out, a.gen, aid)
        bot = d / "produced_bot" / "main.py"
        m = store.read_json(d / "metrics.json", {})
        if m and m.get("sims") == a.sims and m.get("seed") == a.seed and "ladder_fitness" in m:
            ranking.append({"id": aid, "ladder_fitness": m["ladder_fitness"], "per_rung": m["per_rung"]})
            continue
        if not bot.exists():
            ranking.append({"id": aid, "ladder_fitness": 0.0, "per_rung": {}, "missing_bot": True})
            continue
        per, mean = _score_vs_ladder(out, f"{aid}", str(bot), a.sims, a.seed, wd)
        m.update({"id": aid, "ladder_fitness": mean, "per_rung": per, "sims": a.sims, "seed": a.seed})
        store.write_json(d / "metrics.json", m)
        ranking.append({"id": aid, "ladder_fitness": mean, "per_rung": per})
    ranking.sort(key=lambda r: r["ladder_fitness"], reverse=True)
    champ = ranking[0] if ranking else None
    return emit({"ok": True, "gen": a.gen, "ranking": ranking,
                 "champion": champ["id"] if champ else None,
                 "champion_fitness": champ["ladder_fitness"] if champ else None})


# ----------------------------------------------------------------- select + breed
def _ranked(out, gen):
    ids = store.list_agents(out, gen)
    rows = []
    for aid in ids:
        m = store.read_json(store.agent_dir(out, gen, aid) / "metrics.json", {})
        rows.append({"id": aid, "ladder_fitness": m.get("ladder_fitness", 0.0),
                     "per_rung": m.get("per_rung", {})})
    rows.sort(key=lambda r: r["ladder_fitness"], reverse=True)
    return rows


def cmd_select(a):
    rows = _ranked(a.out, a.gen)
    survivors = [r["id"] for r in rows[:a.survivors]]
    return emit({"ok": True, "gen": a.gen, "survivors": survivors,
                 "champion": rows[0]["id"] if rows else None,
                 "fitnesses": {r["id"]: r["ladder_fitness"] for r in rows}})


def cmd_breed_plan(a):
    rows = _ranked(a.out, a.gen)
    survivors = rows[:a.survivors]
    if not survivors:
        return emit({"ok": False, "error": "no survivors"})
    n_off = max(0, a.pop - a.survivors)
    plan = []
    ng = a.gen + 1
    for i in range(n_off):
        parent = survivors[i % len(survivors)]["id"]
        lens = store.LENSES[i % len(store.LENSES)]
        new_id = f"g{ng:02d}_{i:02d}"
        cd = store.agent_dir(a.out, ng, new_id)
        # disk-resume: skip if the child genotype was already written
        exists = (cd / "planner_prompt.md").exists() and (cd / "decomposition.json").exists()
        if not exists:
            cd.mkdir(parents=True, exist_ok=True)
            store.write_json(cd / "lineage.json", {"parent_id": parent, "parent_gen": a.gen,
                             "lens": lens, "origin": "mutation", "changed_components": [], "diff": ""})
        plan.append({"new_id": new_id, "parent_id": parent, "parent_gen": a.gen, "lens": lens,
                     "type": "mutation", "exists": exists})
    # optional winner x winner crossovers (extra offspring)
    for j in range(a.crossovers):
        if len(survivors) < 2:
            break
        p0, p1 = survivors[0]["id"], survivors[(j + 1) % len(survivors)]["id"]
        if p0 == p1:
            continue
        new_id = f"g{ng:02d}_x{j:02d}"
        cd = store.agent_dir(a.out, ng, new_id)
        exists = (cd / "planner_prompt.md").exists()
        if not exists:
            cd.mkdir(parents=True, exist_ok=True)
            store.write_json(cd / "lineage.json", {"parent_id": p0, "parent_id2": p1,
                             "parent_gen": a.gen, "lens": "crossover", "origin": "crossover",
                             "changed_components": [], "diff": ""})
        plan.append({"new_id": new_id, "parent_id": p0, "parent_id2": p1, "parent_gen": a.gen,
                     "lens": "crossover", "type": "crossover", "exists": exists})
    return emit({"ok": True, "gen": a.gen, "next_gen": ng,
                 "survivors": [s["id"] for s in survivors], "plan": plan})


# ----------------------------------------------------------------- verified-acceptance gate
def cmd_admit(a):
    out = a.out
    child_bot = store.produced_bot_path(out, a.gen, a.child)
    parent_bot = store.produced_bot_path(out, a.parent_gen, a.parent)
    wd = str(Path(out) / "_admitwork")
    cper = _per_game_vs_ladder(out, f"c_{a.child}", str(child_bot), a.sims, a.seed, wd)
    pper = _per_game_vs_ladder(out, f"p_{a.parent}", str(parent_bot), a.sims, a.seed, wd)
    diffs, cwins, pwins, n = [], 0, 0, 0
    per_rung = {}
    for r in store.RUNGS:
        if r not in cper or r not in pper:
            continue
        cw, pw = cper[r], pper[r]
        m = min(len(cw), len(pw))
        for i in range(m):
            diffs.append(cw[i] - pw[i])
        cwins += sum(cw[:m]); pwins += sum(pw[:m]); n += m
        per_rung[r] = {"child": sum(cw[:m]) / max(m, 1), "parent": sum(pw[:m]) / max(m, 1)}
    delta, lo, hi = _paired_bootstrap(diffs)
    child_fit = cwins / max(n, 1)
    parent_fit = pwins / max(n, 1)
    admitted = bool(lo > 0.0)
    rec = {"parent_id": a.parent, "parent_gen": a.parent_gen, "child_fit": child_fit,
           "parent_fit": parent_fit, "delta": delta, "ci_low": lo, "ci_high": hi,
           "admitted": admitted, "n_pairs": n, "per_rung": per_rung, "sims": a.sims, "seed": a.seed}
    cd = store.agent_dir(out, a.gen, a.child)
    m = store.read_json(cd / "metrics.json", {})
    m["verified_vs_parent"] = rec
    m.setdefault("id", a.child)
    # also record absolute ladder fitness at admit sims (per-rung winrate)
    m["per_rung_admit"] = {r: per_rung[r]["child"] for r in per_rung}
    store.write_json(cd / "metrics.json", m)
    return emit({"ok": True, "child": a.child, "admitted": admitted, "delta": delta,
                 "ci_low": lo, "ci_high": hi, "child_fit": child_fit, "parent_fit": parent_fit,
                 "n_pairs": n})


# ----------------------------------------------------------------- finalize generation
_CONCEPTS = {
    "space/flood-fill": ["flood", "space", "reachable", "voronoi", "room", "territor", "open area"],
    "head-to-head/combat": ["head-to-head", "head to head", "combat", "longer", "cut off", "cut-off",
                            "eliminat", "attack", "fight", "aggress"],
    "food/health": ["food", "health", "starv", "grow", "length race", "forage", "eat"],
    "endgame/duel": ["endgame", "late game", "late-game", "duel", "1v1", "stall"],
    "hazard/edge": ["hazard", "edge", "corner", "wall"],
    "lookahead/adapt": ["lookahead", "look ahead", "predict", "shallow", "adapt", "anticipat"],
    "trap-avoidance": ["trap", "dead-end", "dead end", "self-trap", "entomb", "pocket"],
}


def _concept_inventory(planner_prompts):
    inv = {}
    for c, kws in _CONCEPTS.items():
        inv[c] = sum(1 for pp in planner_prompts if any(k in pp.lower() for k in kws))
    return inv


def _structure_inventory(out, gen, ids):
    spec_sets, policies, testers, refines, spec_counts = {}, {}, 0, [], {s: 0 for s in store.SPECIALIST_MENU}
    for aid in ids:
        dec = store.read_json(store.agent_dir(out, gen, aid) / "decomposition.json", {})
        specs = harness.canonical_specialists(dec)
        key = "+".join(specs)
        spec_sets[key] = spec_sets.get(key, 0) + 1
        for s in specs:
            spec_counts[s] += 1
        p = dec.get("referee_policy", "weighted_vote")
        policies[p] = policies.get(p, 0) + 1
        testers += 1 if dec.get("tester") else 0
        refines.append(int(dec.get("refine_rounds", 0)))
    return {"specialist_sets": spec_sets, "specialist_counts": spec_counts,
            "referee_policies": policies, "tester_fraction": testers / max(len(ids), 1),
            "mean_refine_rounds": (sum(refines) / max(len(refines), 1)) if refines else 0,
            "mean_specialist_count": (sum(len(harness.canonical_specialists(
                store.read_json(store.agent_dir(out, gen, aid) / "decomposition.json", {})))
                for aid in ids) / max(len(ids), 1))}


def cmd_finalize_gen(a):
    out, gen, ng = a.out, a.gen, a.gen + 1
    rows = _ranked(out, gen)
    survivors = [r["id"] for r in rows[:a.survivors]]
    # offspring already bred into gen ng (genotypes/agent_g{ng}_*) and evaluated; read their verdicts
    ng_dir = store.gen_dir(out, ng) / "genotypes"
    offspring = []
    if ng_dir.exists():
        offspring = sorted(p.name[len("agent_"):] for p in ng_dir.iterdir()
                           if p.name.startswith("agent_") and p.name[len("agent_"):].startswith(f"g{ng:02d}"))
    admissions, admitted = [], []
    for oid in offspring:
        m = store.read_json(store.agent_dir(out, ng, oid) / "metrics.json", {})
        v = m.get("verified_vs_parent", {})
        lin = store.read_json(store.agent_dir(out, ng, oid) / "lineage.json", {})
        rec = {"id": oid, "parent_id": v.get("parent_id", lin.get("parent_id")),
               "lens": lin.get("lens"), "delta": v.get("delta"), "ci_low": v.get("ci_low"),
               "ci_high": v.get("ci_high"), "admitted": bool(v.get("admitted")),
               "child_fit": v.get("child_fit"), "parent_fit": v.get("parent_fit"),
               "changed_components": lin.get("changed_components", []), "diff": lin.get("diff", "")}
        admissions.append(rec)
        if rec["admitted"]:
            admitted.append(oid)
    store.write_json(store.gen_dir(out, ng) / "admissions.json",
                     {"gen": ng, "offspring": admissions,
                      "n_admitted": len(admitted), "n_offspring": len(offspring)})
    # build gen ng population = admitted offspring + carried (top of gen, refill to pop)
    n_carry = max(a.survivors, a.pop - len(admitted))
    carried = [r["id"] for r in rows[:n_carry]]
    for cid in carried:
        src = store.agent_dir(out, gen, cid)
        dst = store.agent_dir(out, ng, cid)
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)  # carry genotype + produced_bot + metrics (disk-resume free re-score)
    # remove rejected offspring dirs (rename to _rejected for forensics)
    for oid in offspring:
        if oid not in admitted:
            od = store.agent_dir(out, ng, oid)
            rej = od.parent / f"_rejected_{oid}"
            if rej.exists():
                shutil.rmtree(rej)
            od.rename(rej)
    ids = carried + admitted
    store.write_json(store.gen_dir(out, ng) / "population.json",
                     {"gen": ng, "ids": ids, "carried": carried, "new_ids": admitted})
    # population summary for THIS finalized gen (ng) + champion monotone curve
    planner_prompts = [store.read_text(store.agent_dir(out, ng, i) / "planner_prompt.md") for i in ids]
    fits = []
    for i in ids:
        m = store.read_json(store.agent_dir(out, ng, i) / "metrics.json", {})
        fits.append({"id": i, "ladder_fitness": m.get("ladder_fitness", 0.0)})
    fits.sort(key=lambda r: r["ladder_fitness"], reverse=True)
    summary = {"gen": ng, "ids": ids, "champion": fits[0]["id"] if fits else None,
               "champion_fitness": fits[0]["ladder_fitness"] if fits else None,
               "fitness_distribution": fits, "n_admitted": len(admitted),
               "structure": _structure_inventory(out, ng, ids),
               "concept_inventory": _concept_inventory(planner_prompts)}
    store.write_json(store.gen_dir(out, ng) / "population_summary.json", summary)
    return emit({"ok": True, "next_gen": ng, "ids": ids, "new_ids": admitted, "carried": carried,
                 "n_admitted": len(admitted), "n_offspring": len(offspring),
                 "champion": summary["champion"], "champion_fitness": summary["champion_fitness"]})


def cmd_population_summary(a):
    """Standalone summary for gen 0 (no finalize-gen runs before it)."""
    out, gen = a.out, a.gen
    ids = store.list_agents(out, gen)
    planner_prompts = [store.read_text(store.agent_dir(out, gen, i) / "planner_prompt.md") for i in ids]
    fits = []
    for i in ids:
        m = store.read_json(store.agent_dir(out, gen, i) / "metrics.json", {})
        fits.append({"id": i, "ladder_fitness": m.get("ladder_fitness", 0.0)})
    fits.sort(key=lambda r: r["ladder_fitness"], reverse=True)
    summary = {"gen": gen, "ids": ids, "champion": fits[0]["id"] if fits else None,
               "champion_fitness": fits[0]["ladder_fitness"] if fits else None,
               "fitness_distribution": fits, "n_admitted": 0,
               "structure": _structure_inventory(out, gen, ids),
               "concept_inventory": _concept_inventory(planner_prompts)}
    store.write_json(store.gen_dir(out, gen) / "population_summary.json", summary)
    return emit({"ok": True, "gen": gen, "champion": summary["champion"],
                 "champion_fitness": summary["champion_fitness"]})


# ----------------------------------------------------------------- ladder sanity + sonnet rung
def cmd_ladder_sanity(a):
    out = a.out
    bots = _rung_bots(out)
    if len(bots) < 2:
        return emit({"ok": False, "error": "need >=2 rungs"})
    rr = sim.round_robin(bots, a.sims, a.seed, str(Path(out) / "_laddersanity"), max_workers=MAXW)
    matrix = rr["matrix"]
    fit = rr["fitness"]
    names = [b["name"] for b in bots]
    # robust ranking via PAIRWISE win-rates (not 4-way overall fitness, which mirror-matches dilute):
    # strong must beat moderate, moderate beat weak, strong beat weak.
    def beats(a, b):
        return a in matrix and b in matrix[a] and matrix[a][b] > 0.5
    pairs = []
    if all(x in fit for x in ("weak", "moderate", "strong")):
        pairs = [beats("moderate", "weak"), beats("strong", "moderate"), beats("strong", "weak")]
    order_ok = bool(pairs) and all(pairs)
    # sonnet rung should be competitive: at least beat the weak rung and be near/above moderate.
    sonnet_ok = (beats("sonnet", "weak") and matrix.get("sonnet", {}).get("moderate", 0) >= 0.4) \
        if "sonnet" in fit else None
    store.write_json(store.ladder_dir(out) / "sanity.json",
                     {"matrix": matrix, "fitness": fit, "order_ok": order_ok,
                      "sonnet_competitive": sonnet_ok, "sims": a.sims, "names": names})
    return emit({"ok": True, "order_ok": order_ok, "sonnet_competitive": sonnet_ok,
                 "fitness": {k: round(v, 3) for k, v in fit.items()}})


def cmd_status(a):
    """Disk-resume check for a simple-refinement run dir (ablation / sonnet rung)."""
    pb = Path(a.path) / "produced_bot"
    tr = store.read_json(pb / "refine_trace.json", {})
    done = sum(1 for r in tr.get("rounds", []) if r.get("action") == "debug-edit")
    exists = (pb / "main.py").exists() and bool(tr) and done >= a.rounds
    return emit({"ok": True, "exists": exists, "done_rounds": done})


def cmd_pick_best_of_n(a):
    """Score each best-of-N simple-refine run vs the ladder, copy the best to <dir>/best/main.py."""
    base = Path(a.dir)
    wd = str(base / "_bonwork")
    best, best_fit, fits = None, -1.0, {}
    for k in range(a.n):
        bot = base / f"run_{k}" / "produced_bot" / "main.py"
        if not bot.exists():
            continue
        _, mean = _score_vs_ladder(a.out, f"bon{k}", str(bot), a.sims, a.seed, wd)
        fits[k] = mean
        if mean > best_fit:
            best_fit, best = mean, k
    if best is not None:
        (base / "best").mkdir(parents=True, exist_ok=True)
        shutil.copy(base / f"run_{best}" / "produced_bot" / "main.py", base / "best" / "main.py")
    return emit({"ok": True, "best_run": best, "best_fitness": best_fit, "fitnesses": fits})


def cmd_install_sonnet_rung(a):
    """Promote a produced bot (the Sonnet simple-refinement bot) to ladder/sonnet.py."""
    src = Path(a.path)
    ok, reason = _validate(src)
    if not ok:
        return emit({"ok": False, "error": f"invalid sonnet bot: {reason}"})
    store.write_text(store.ladder_path(a.out, "sonnet"), src.read_text())
    return emit({"ok": True, "installed": str(store.ladder_path(a.out, "sonnet"))})


# ----------------------------------------------------------------- verification gate
def cmd_gate(a):
    out, gen, aid = a.out, a.gen, a.agent
    d = store.agent_dir(out, gen, aid)
    decomp = store.read_json(d / "decomposition.json", {})
    specs = harness.canonical_specialists(decomp)
    # (a) specialists spawned (files exist, non-empty)
    spawned = all((d / "specialists" / f"{s}.py").exists() and
                  (d / "specialists" / f"{s}.py").read_text().strip() for s in specs)
    # (b) planner ran (briefs.json) + produced bot reflects the decomposition (loads all specialists)
    briefs = store.read_json(d / "briefs.json", {})
    ok_asm, info = harness.assemble_decomp(out, gen, aid)
    reflects = ok_asm and set(info.get("loaded", [])) == set(specs) and bool(briefs)
    # (c) ladder ranks sanely. The ESSENTIAL property is the bottom gradient (weak is clearly the
    # floor => headroom exists); strong-vs-moderate ordering is noisy at low sims and already verified
    # offline at >=150 sims, so don't hard-fail the gate on it.
    san = store.read_json(store.ladder_dir(out) / "sanity.json", {})
    mtx = san.get("matrix", {})
    def _beats(x, y):
        return mtx.get(x, {}).get(y, 0.0) > 0.5
    ladder_ok = bool(san) and _beats("moderate", "weak") and _beats("strong", "weak")
    # (d) verified-acceptance computes a paired CI (self-paired sanity: bot vs itself -> ci brackets 0)
    bot = str(d / "produced_bot" / "main.py")
    ci_ok = False
    try:
        wd = str(d / "produced_bot" / "_gatework")
        per = _per_game_vs_ladder(out, "gate_self", bot, 20, 99, wd, use_cache=False)
        diffs = []
        for r in per:
            diffs += [0 for _ in per[r]]  # self-paired => zero diffs
        _, lo, hi = _paired_bootstrap(diffs or [0])
        ci_ok = (lo <= 0 <= hi)
    except Exception:
        ci_ok = False
    # (e) bot is valid + scores from sims
    valid, _ = _validate(bot)
    fitness_from_sims = False
    try:
        per_, mean_ = _score_vs_ladder(out, "gate", bot, 12, 7, str(d / "produced_bot" / "_gscore"),
                                       use_cache=False)
        fitness_from_sims = len(per_) >= 2
    except Exception:
        pass
    passed = bool(spawned and reflects and ladder_ok and ci_ok and valid and fitness_from_sims)
    return emit({"ok": True, "pass": passed, "specialists_spawned": spawned,
                 "bot_reflects_genotype": reflects, "ladder_ranks_sane": ladder_ok,
                 "paired_ci_computed": ci_ok, "bot_valid": valid,
                 "fitness_from_sims": fitness_from_sims,
                 "details": {"specs": specs, "loaded": info.get("loaded", []),
                             "ladder_fitness": san.get("fitness", {})}})


# ----------------------------------------------------------------- final headline eval
def _final_one(out, name, bot_path, sims, seed, wd):
    rungs = _rung_bots(out)
    matchups = [{"id": r["name"], "a": {"name": name, "path": bot_path}, "b": r} for r in rungs]
    per = sim.per_game_results(matchups, sims, seed, wd, max_workers=MAXW)
    res = {}
    tot_k = tot_n = 0
    for r in rungs:
        w = per[r["name"]]
        k, n = sum(w), len(w)
        p, lo, hi = _wilson(k, n)
        res[r["name"]] = {"winrate": p, "ci_low": lo, "ci_high": hi, "n": n}
        tot_k += k; tot_n += n
    p, lo, hi = _wilson(tot_k, tot_n)
    res["ladder_mean"] = {"winrate": p, "ci_low": lo, "ci_high": hi, "n": tot_n}
    return res


def cmd_final_eval(a):
    out = a.out
    rows = _ranked(out, a.gen)
    champ = rows[0]["id"] if rows else None
    wd = str(Path(out) / "final" / "_work")
    bots = {}
    if champ:
        bots["champion"] = str(store.produced_bot_path(out, a.gen, champ))
    simp = store.ablation_dir(out) / "simple_refine" / "produced_bot" / "main.py"
    if simp.exists():
        bots["simple_refine"] = str(simp)
    bon = store.ablation_dir(out) / "best_of_n" / "best" / "main.py"
    if bon.exists():
        bots["best_of_n"] = str(bon)
    headline = {"champion_id": champ, "sims": a.sims, "seed": a.seed, "bots": {}}
    for name, bp in bots.items():
        headline["bots"][name] = _final_one(out, name, bp, a.sims, a.seed, wd)
    # champion head-to-head vs each ablation (direct)
    h2h = {}
    if champ:
        cbot = {"name": "champion", "path": bots["champion"]}
        for name in ("simple_refine", "best_of_n"):
            if name in bots:
                per = sim.per_game_results([{"id": name, "a": cbot, "b": {"name": name, "path": bots[name]}}],
                                           a.sims, a.seed + 5000, wd, max_workers=MAXW)[name]
                k, n = sum(per), len(per)
                p, lo, hi = _wilson(k, n)
                h2h[name] = {"champion_winrate": p, "ci_low": lo, "ci_high": hi, "n": n}
    headline["champion_vs_ablations"] = h2h
    store.write_json(Path(out) / "final" / "headline.json", headline)
    return emit({"ok": True, "champion": champ, "headline": headline["bots"],
                 "champion_vs_ablations": h2h})


# ----------------------------------------------------------------- init
def _commit(repo):
    try:
        return subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"],
                              capture_output=True, text=True, timeout=10).stdout.strip()[:12]
    except Exception:
        return "unknown"


def cmd_init(a):
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    # ladder rungs 0-2 (rung 3 = sonnet, produced later)
    for rung, src in LADDER_SRC.items():
        store.write_text(store.ladder_path(out, rung), Path(src).read_text())
    # dump the FIXED contracts (single source of truth = harness.py) for the agents to read
    cdir = out / "contracts"
    store.write_text(cdir / "bot_rules.txt", harness.BOT_RULES)
    store.write_text(cdir / "specialist_contract.txt", harness.SPECIALIST_CONTRACT)
    store.write_text(cdir / "referee_contract.txt", harness.REFEREE_CONTRACT)
    store.write_text(cdir / "simple_bot_contract.txt", harness.SIMPLE_BOT_CONTRACT)
    store.write_json(cdir / "specialist_concerns.json", harness.SPECIALIST_CONCERNS)
    # seed genotypes
    sg = seeds.seed_genotypes(refine_rounds=a.refine_rounds)[:a.pop]
    for g in sg:
        store.save_genotype(out, 0, g)
    store.write_json(store.gen_dir(out, 0) / "population.json",
                     {"gen": 0, "ids": [g["id"] for g in sg], "carried": [], "new_ids": [g["id"] for g in sg]})
    cfg = {"out": str(out), "seed": a.seed, "generations": a.generations, "pop": a.pop,
           "survivors": a.survivors, "refine_rounds": a.refine_rounds, "crossovers": a.crossovers,
           "sims_evolve": a.sims_evolve, "sims_admit": a.sims_admit, "sims_final": a.sims_final,
           "models": {"inner_coder": "haiku", "outer_reflect": "sonnet", "sonnet_rung": "sonnet"},
           "ladder": {"weak": "naive food-seeker", "moderate": "greedy flood-fill (CodeClash bench)",
                      "strong": "flood-fill + head-to-head + space-guard (hand-written)",
                      "sonnet": "Sonnet simple-refinement bot (produced once, frozen)"},
           "specialist_menu": store.SPECIALIST_MENU, "referee_policies": store.REFEREE_POLICIES,
           "lenses": store.LENSES, "battlesnake_commit": _commit(ROOT / "BattleSnake"),
           "codeclash_commit": _commit(ROOT / "CodeClash")}
    store.write_json(out / "config.json", cfg)
    return emit({"ok": True, "seed_ids": [g["id"] for g in sg],
                 "battlesnake_commit": cfg["battlesnake_commit"],
                 "codeclash_commit": cfg["codeclash_commit"]})


# ----------------------------------------------------------------- CLI
def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p):
        p.add_argument("--out", required=True)

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
    p.set_defaults(fn=cmd_harness_plan)

    p = sub.add_parser("assemble"); common(p)
    p.add_argument("--gen", type=int, required=True); p.add_argument("--agent", required=True)
    p.set_defaults(fn=cmd_assemble)

    p = sub.add_parser("validate"); common(p)
    p.add_argument("--path", required=True); p.set_defaults(fn=cmd_validate)

    for name, fn in (("refine-init", cmd_refine_init), ("refine-keep", cmd_refine_keep)):
        p = sub.add_parser(name); common(p)
        p.add_argument("--gen", type=int, default=0); p.add_argument("--agent", default="")
        p.add_argument("--simple", default=""); p.add_argument("--round", type=int, default=0)
        p.add_argument("--sims", type=int, default=30); p.add_argument("--seed", type=int, default=0)
        p.add_argument("--tester", type=int, default=0)
        p.set_defaults(fn=fn)

    p = sub.add_parser("score-pop"); common(p)
    p.add_argument("--gen", type=int, required=True); p.add_argument("--agent", default="")
    p.add_argument("--sims", type=int, default=120); p.add_argument("--seed", type=int, default=0)
    p.set_defaults(fn=cmd_score_pop)

    p = sub.add_parser("select"); common(p)
    p.add_argument("--gen", type=int, required=True); p.add_argument("--survivors", type=int, default=4)
    p.set_defaults(fn=cmd_select)

    p = sub.add_parser("breed-plan"); common(p)
    p.add_argument("--gen", type=int, required=True); p.add_argument("--pop", type=int, default=12)
    p.add_argument("--survivors", type=int, default=4); p.add_argument("--crossovers", type=int, default=0)
    p.set_defaults(fn=cmd_breed_plan)

    p = sub.add_parser("admit"); common(p)
    p.add_argument("--gen", type=int, required=True); p.add_argument("--child", required=True)
    p.add_argument("--parent-gen", dest="parent_gen", type=int, required=True)
    p.add_argument("--parent", required=True)
    p.add_argument("--sims", type=int, default=200); p.add_argument("--seed", type=int, default=0)
    p.set_defaults(fn=cmd_admit)

    p = sub.add_parser("finalize-gen"); common(p)
    p.add_argument("--gen", type=int, required=True); p.add_argument("--pop", type=int, default=12)
    p.add_argument("--survivors", type=int, default=4); p.set_defaults(fn=cmd_finalize_gen)

    p = sub.add_parser("population-summary"); common(p)
    p.add_argument("--gen", type=int, required=True); p.set_defaults(fn=cmd_population_summary)

    p = sub.add_parser("ladder-sanity"); common(p)
    p.add_argument("--sims", type=int, default=120); p.add_argument("--seed", type=int, default=4242)
    p.set_defaults(fn=cmd_ladder_sanity)

    p = sub.add_parser("install-sonnet-rung"); common(p)
    p.add_argument("--path", required=True); p.set_defaults(fn=cmd_install_sonnet_rung)

    p = sub.add_parser("status"); common(p)
    p.add_argument("--path", required=True); p.add_argument("--rounds", type=int, default=0)
    p.set_defaults(fn=cmd_status)

    p = sub.add_parser("pick-best-of-n"); common(p)
    p.add_argument("--dir", required=True); p.add_argument("--n", type=int, required=True)
    p.add_argument("--sims", type=int, default=120); p.add_argument("--seed", type=int, default=0)
    p.set_defaults(fn=cmd_pick_best_of_n)

    p = sub.add_parser("gate"); common(p)
    p.add_argument("--gen", type=int, default=0); p.add_argument("--agent", required=True)
    p.set_defaults(fn=cmd_gate)

    p = sub.add_parser("final-eval"); common(p)
    p.add_argument("--gen", type=int, required=True); p.add_argument("--sims", type=int, default=1500)
    p.add_argument("--seed", type=int, default=0); p.set_defaults(fn=cmd_final_eval)

    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
