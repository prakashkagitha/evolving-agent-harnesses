"""Controller for cc_pipe — the typed self-correction pipeline (the evolvable harness) + the
Haiku->Sonnet baseline gate, with GEPA and CORE breeders.

Genotype (split for robust mutation): roles.json = {roles: [steps in {draft,critique,fix}], draft_model}
(the STRUCTURE) + prompts/{draft,critique,fix}.md (the free-text role prompts). BOTH evolve.
Execution (driven by the workflow) is a keep-best chain: draft/fix produce a scored candidate (best
tracked); critique reads the best + in-process ENGINE FEEDBACK (harness.eval_on_boards) and writes a
diagnosis the next fix consumes. Fitness = mean ladder win-rate of the per-replicate best over R
replicates; verified two-sample gate (reused from cc_prompt).

Reuses cc_prompt (two-sample gate, representative, safe bot, score-pop), cc_decomp (scoring,
eval_on_boards, _validate), cc_core (bank/ingest/credit), cc_core.reflect (form_pairs). MAXW from CC_MAXW.
"""
import argparse
import json
import os
import shutil
from pathlib import Path

from cc_decomp import control as dctrl
from cc_decomp import harness, store
from cc_prompt import control_prompt as cp
from cc_core import control as ccore
from cc_core import bank as bankmod
from cc_core import reflect as creflect

dctrl.MAXW = int(os.environ.get("CC_MAXW", "16"))
ROOT = Path(__file__).resolve().parent.parent
LADDER_SRC = {"weak": ROOT / "cc_decomp" / "ladder" / "weak.py",
              "moderate": ROOT / "cc_gepa" / "opponents" / "greedy_bot.py",
              "strong": ROOT / "cc_decomp" / "ladder" / "strong.py"}
RUNGS = ["weak", "moderate", "strong"]
ROLES_REP = ["draft", "critique", "fix"]
LENSES = ["draft", "critique", "fix", "structure"]

DEFAULT_PROMPTS = {
    "draft": ("Write the strongest complete single-file BattleSnake bot you can: flood-fill space "
              "control (veto self-traps), head-to-head safety — exclude moves into a cell an equal-or-"
              "longer enemy head can reach next turn — and measured food/health. Fast, crash-proof move()."),
    "critique": ("You are reviewing a BattleSnake bot. From the engine feedback (failed adversarial "
                 "boards: out-of-bounds / body-collision / losing head-to-head / crash) and the code, "
                 "name the SINGLE biggest concrete weakness and exactly what to change."),
    "fix": ("Improve the bot: apply the critique and fix the specific failures in the engine feedback "
            "(keep info/start/end/move; pure; never raises; stdlib only). Make one real behavioral fix."),
}


def emit(obj):
    print(json.dumps(obj))
    return obj


def _agent_dir(out, gen, aid):
    return (Path(out) / "baselines" / aid) if gen < 0 else store.agent_dir(out, gen, aid)


# ----------------------------------------------------------------- genotype I/O (roles.json + prompts/)
def repair(geno, N):
    roles = [r for r in geno.get("roles", []) if r in ROLES_REP]
    if len(roles) < N:
        roles = roles + ["fix"] * (N - len(roles))
    roles = roles[:N] or (["draft"] + ["fix"] * (N - 1))
    roles[0] = "draft"
    if roles[-1] == "critique":
        roles[-1] = "fix"
    prompts = {k: (geno.get("prompts", {}).get(k) or DEFAULT_PROMPTS[k]).strip() for k in ROLES_REP}
    return {"id": geno.get("id"), "roles": roles, "prompts": prompts,
            "draft_model": geno.get("draft_model", "haiku"), "lineage": geno.get("lineage", {})}


def load(out, gen, aid):
    d = _agent_dir(out, gen, aid)
    rj = store.read_json(d / "roles.json", {})
    prompts = {r: store.read_text(d / "prompts" / f"{r}.md") for r in ROLES_REP}
    return {"id": aid, "roles": rj.get("roles", []), "draft_model": rj.get("draft_model", "haiku"),
            "prompts": prompts, "lineage": store.read_json(d / "lineage.json", {})}


def save(out, gen, geno):
    d = _agent_dir(out, gen, geno["id"])
    store.write_json(d / "roles.json", {"roles": geno["roles"], "draft_model": geno.get("draft_model", "haiku")})
    for r in ROLES_REP:
        store.write_text(d / "prompts" / f"{r}.md", geno["prompts"].get(r, DEFAULT_PROMPTS[r]))
    store.write_json(d / "lineage.json", geno.get("lineage", {}))


def pipe_label(roles):
    return "→".join(r[0].upper() for r in roles)


def _clone(out, pgen, pid, cgen, cid):
    g = load(out, pgen, pid)
    g["id"] = cid
    save(out, cgen, g)


# ----------------------------------------------------------------- seeds (diverse N-step pipelines)
def seed_pipes(N):
    def g(pid, roles):
        return {"id": pid, "roles": roles[:N] + ["fix"] * max(0, N - len(roles)),
                "prompts": {}, "draft_model": "haiku",
                "lineage": {"parent_id": None, "origin": "seed", "lens": None, "changed_components": [], "diff": ""}}
    if N <= 6:
        return [
            g("refine", ["draft", "fix", "fix", "fix"]),
            g("critique_fix", ["draft", "critique", "fix", "fix"]),
            g("crit_each", ["draft", "critique", "fix", "critique", "fix"]),
            g("two_draft", ["draft", "draft", "fix", "fix"]),
            g("draft_crit_fix", ["draft", "critique", "fix"]),
            g("best_then_fix", ["draft", "draft", "draft", "fix"]),
            g("alt", ["draft", "fix", "critique", "fix"]),
            g("triple_fix_crit", ["draft", "critique", "fix", "fix"]),
        ]
    # N >= 7: full-length diverse shapes spanning the larger structure space (repair() trims trailing critique)
    D, C, F = "draft", "critique", "fix"
    h = N // 2
    odd = (N - 1) % 2
    return [
        g("refine", [D] + [F] * (N - 1)),                                  # blind revision chain
        g("best_then_fix", [D] * (N - h) + [F] * h),                       # best-of-(N-h) drafts then h fixes
        g("crit_each", [D] + [C, F] * ((N - 1) // 2) + ([F] if odd else [])),  # critique before each fix
        g("two_draft", [D, D] + [F] * (N - 2)),                            # 2 drafts then fixes
        g("draft_heavy", [D] * (N - 2) + [F, F]),                          # many independent drafts, 2 fixes
        g("balanced_crit", [D, D] + [C, F] * ((N - 2) // 2)),              # drafts then critique-fix pairs
        g("critique_fix", [D, C] + [F] * (N - 2)),                         # one critique, then fixes
        g("alt", [D] + [F, C] * ((N - 1) // 2) + ([F] if odd else [])),    # alternating fix/critique
    ]


# ----------------------------------------------------------------- init
def _baseline_genos(N):
    return [{"id": "haiku_1shot", "roles": ["draft"], "draft_model": "haiku"},
            {"id": "sonnet_1shot", "roles": ["draft"], "draft_model": "sonnet"},
            {"id": "opus_1shot", "roles": ["draft"], "draft_model": "opus"},
            {"id": "haiku_bestN", "roles": ["draft"] * N, "draft_model": "haiku"},
            {"id": "haiku_refineN", "roles": ["draft"] + ["fix"] * (N - 1), "draft_model": "haiku"}]


def cmd_init(a):
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for rung, src in LADDER_SRC.items():
        store.write_text(store.ladder_path(out, rung), Path(src).read_text())
    store.write_text(out / "contracts" / "simple_bot_contract.txt", harness.SIMPLE_BOT_CONTRACT)
    base = []
    for bg in _baseline_genos(a.N):
        save(out, -1, repair({**bg, "prompts": {}}, len(bg["roles"])))
        base.append(bg["id"])
    seeds = seed_pipes(a.N)[: a.pop]
    for s in seeds:
        save(out, 0, repair(s, a.N))
    store.write_json(store.gen_dir(out, 0) / "population.json",
                     {"gen": 0, "ids": [s["id"] for s in seeds], "carried": [], "new_ids": [s["id"] for s in seeds]})
    cfg = {"out": str(out), "N": a.N, "R": a.R, "pop": a.pop, "survivors": a.survivors,
           "sims_eval": a.sims_eval, "sims_cand": a.sims_cand, "seed": a.seed, "optimizer": a.optimizer,
           "roles": ROLES_REP, "lenses": LENSES, "baselines": base}
    store.write_json(out / "config.json", cfg)
    if a.optimizer == "core":
        b = bankmod.Bank(); b.save(ccore.bank_path(out)); ccore._snap(b, 0, out)
    return emit({"ok": True, "N": a.N, "R": a.R, "optimizer": a.optimizer, "baselines": base,
                 "seed_ids": [s["id"] for s in seeds],
                 "seed_labels": {s["id"]: pipe_label(repair(s, a.N)["roles"]) for s in seeds}})


# ----------------------------------------------------------------- plan / feedback / score / eval
def cmd_pipe_plan(a):
    g = load(a.out, a.gen, a.agent)
    # Baselines (gen < 0) must run at their OWN intended length (e.g. a 1-shot is exactly ["draft"]);
    # only evolution genotypes (gen >= 0) are normalized to the global budget N. Padding a 1-shot up to
    # N would silently turn it into a refine-N chain (the bug that mislabeled the single-shot bars).
    n_eff = a.N if a.gen >= 0 else max(1, len([r for r in g.get("roles", []) if r in ROLES_REP]))
    geno = repair(g, n_eff)
    geno["id"] = a.agent
    save(a.out, a.gen, geno)
    d = _agent_dir(a.out, a.gen, a.agent)
    exists = bool(store.read_json(d / "metrics.json", {})) and (d / "evals.json").exists()
    return emit({"ok": True, "agent": a.agent, "roles": geno["roles"], "draft_model": geno["draft_model"],
                 "label": pipe_label(geno["roles"]), "exists": exists})


def cmd_pipe_feedback(a):
    d = _agent_dir(a.out, a.gen, a.agent)
    rd = d / f"repl_{a.repl}"
    bp = (rd / "best.py") if (rd / "best.py").exists() else None
    fb = {"findings": [], "summary": "no bot yet", "n_fail": 0}
    if bp:
        findings = harness.eval_on_boards(str(bp), harness.adversarial_boards())
        fails = [f for f in findings if not f["ok"]]
        fb = {"findings": findings, "n_fail": len(fails),
              "summary": ("; ".join(f"{f['board']}: {f['reason']}" for f in fails) or "passes all adversarial boards")}
    store.write_json(rd / "feedback.json", fb)
    return emit({"ok": True, "repl": a.repl, "n_fail": fb["n_fail"], "summary": fb["summary"][:200]})


def cmd_pipe_score_cand(a):
    d = _agent_dir(a.out, a.gen, a.agent); rd = d / f"repl_{a.repl}"; p = rd / f"c{a.cand}.py"
    rec = {"cand": a.cand, "valid": False, "mean": 0.0}
    if p.exists():
        store.write_text(p, harness.clean_code(p.read_text()))
        ok, reason = dctrl._validate(str(p))
        if ok:
            per = dctrl._per_game_vs_ladder(a.out, f"{a.agent}_r{a.repl}_c{a.cand}", str(p), a.sims_cand, a.seed, str(rd / "_score"))
            tk = sum(sum(per.get(rr, [])) for rr in RUNGS); tn = sum(len(per.get(rr, [])) for rr in RUNGS)
            rec = {"cand": a.cand, "valid": True, "mean": tk / max(tn, 1),
                   "games": {rr: per.get(rr, []) for rr in RUNGS}}
        else:
            rec["reason"] = reason
    store.write_json(rd / f"c{a.cand}.json", rec)
    st = store.read_json(rd / "state.json", {"best_score": -1.0, "best_cand": None})
    if rec["valid"] and rec["mean"] > st.get("best_score", -1.0):
        st.update({"best_score": rec["mean"], "best_cand": a.cand}); shutil.copy(p, rd / "best.py")
    store.write_json(rd / "state.json", st)
    return emit({"ok": True, "repl": a.repl, "cand": a.cand, "valid": rec["valid"],
                 "cand_score": round(rec["mean"], 4), "best_score": round(st["best_score"], 4)})


def cmd_pipe_eval_score(a):
    d = _agent_dir(a.out, a.gen, a.agent)
    bot_means, pooled, per_rung_sum, ok_reps = [], [], {r: [] for r in RUNGS}, []
    for r in range(a.R):
        st = store.read_json(d / f"repl_{r}" / "state.json", {}); bc = st.get("best_cand")
        rec = store.read_json(d / f"repl_{r}" / f"c{bc}.json", {}) if bc is not None else {}
        if rec.get("valid"):
            bot_means.append(rec["mean"]); ok_reps.append(r)
            for rr in RUNGS:
                gg = rec.get("games", {}).get(rr, []); pooled += list(gg)
                per_rung_sum[rr].append((sum(gg) / len(gg)) if gg else 0.0)
        else:
            bot_means.append(0.0)
            for rr in RUNGS:
                pooled += [0] * a.sims_cand
    fitness = (sum(bot_means) / len(bot_means)) if bot_means else 0.0
    per_rung = {r: (sum(v) / len(v)) if v else 0.0 for r, v in per_rung_sum.items()}
    store.write_json(d / "evals.json", {"bot_means": bot_means, "pooled_games": pooled, "fitness": fitness, "R": a.R})
    m = store.read_json(d / "metrics.json", {})
    m.update({"id": a.agent, "ladder_fitness": fitness, "per_rung": per_rung, "sims": a.sims_cand,
              "seed": a.seed, "R": a.R, "R_valid": len(ok_reps)})
    store.write_json(d / "metrics.json", m)
    rep = cp._representative(bot_means)
    pb = d / "produced_bot"; pb.mkdir(parents=True, exist_ok=True)
    src = None
    if rep is not None and rep in ok_reps:
        src = (d / f"repl_{rep}" / "best.py")
    if src and Path(src).exists():
        shutil.copy(src, pb / "main.py")
    else:
        store.write_text(pb / "main.py", cp._SAFE_BOT)
    return emit({"ok": True, "agent": a.agent, "fitness": round(fitness, 4), "R_valid": m["R_valid"],
                 "per_rung": {r: round(v, 3) for r, v in per_rung.items()}})


def cmd_score_pop(a):
    return cp.cmd_score_pop(a)


def cmd_admit(a):
    return cp.cmd_admit(a)


# ----------------------------------------------------------------- weakness (for breeding)
def _weakness(out, gen, aid):
    g = load(out, gen, aid); m = store.read_json(store.agent_dir(out, gen, aid) / "metrics.json", {})
    per = m.get("per_rung", {})
    parts = [f"pipeline {pipe_label(g['roles'])} (roles={g['roles']})"]
    rw = sorted(((r, per[r]) for r in per), key=lambda t: t[1])
    if rw:
        parts.append(", ".join(f"weak vs {r} (win-rate {wr:.2f})" for r, wr in rw[:2]))
    parts.append("prompts: " + " || ".join(f"[{r}] {(g['prompts'].get(r,'') or '')[:90]}" for r in ROLES_REP))
    return ". ".join(parts)


# ----------------------------------------------------------------- GEPA breeding
def cmd_breed_plan_gepa(a):
    rows = dctrl._ranked(a.out, a.gen); survivors = rows[: a.survivors]
    if not survivors:
        return emit({"ok": False, "error": "no survivors"})
    n_off = max(0, a.pop - a.survivors); ng = a.gen + 1; plan = []
    for i in range(n_off):
        srow = survivors[i % len(survivors)]; parent = srow["id"]; lens = LENSES[i % len(LENSES)]
        new_id = f"g{ng:02d}_{i:02d}"; cd = store.agent_dir(a.out, ng, new_id)
        exists = (cd / "roles.json").exists()
        if not exists:
            cd.mkdir(parents=True, exist_ok=True); _clone(a.out, a.gen, parent, ng, new_id)
            store.write_json(cd / "lineage.json", {"parent_id": parent, "parent_gen": a.gen, "lens": lens,
                             "origin": "gepa_mutation", "changed_components": [lens], "diff": ""})
        plan.append({"new_id": new_id, "parent_id": parent, "parent_gen": a.gen, "lens": lens,
                     "parent_fit": round(srow.get("ladder_fitness", 0.0), 4), "type": "mutation", "exists": exists})
    return emit({"ok": True, "gen": a.gen, "next_gen": ng, "survivors": [s["id"] for s in survivors], "plan": plan})


# ----------------------------------------------------------------- CORE breeding
def cmd_core_reflect_plan(a):
    rows = dctrl._ranked(a.out, a.gen); pairs = creflect.form_pairs(rows, a.pairs, margin=getattr(a, "margin", 0.03))
    refl_dir = ccore.bank_dir(a.out) / "reflections" / f"gen_{a.gen:02d}"; plan = []
    for i, p in enumerate(pairs):
        plan.append({"idx": i, "winner_id": p["winner_id"], "loser_id": p["loser_id"],
                     "winner_dir": str(store.agent_dir(a.out, a.gen, p["winner_id"])),
                     "loser_dir": str(store.agent_dir(a.out, a.gen, p["loser_id"])),
                     "winner_fitness": round(p["winner_fitness"], 4), "loser_fitness": round(p["loser_fitness"], 4),
                     "winner_label": pipe_label(load(a.out, a.gen, p["winner_id"])["roles"]),
                     "loser_label": pipe_label(load(a.out, a.gen, p["loser_id"])["roles"]),
                     "weakness": _weakness(a.out, a.gen, p["loser_id"]),
                     "lessons_path": str(refl_dir / f"pair_{i:02d}.json")})
    store.write_json(refl_dir / "reflect_plan.json", {"gen": a.gen, "pairs": plan})
    return emit({"ok": True, "gen": a.gen, "n_pairs": len(plan), "plan": plan})


def cmd_core_breed_plan(a):
    rows = dctrl._ranked(a.out, a.gen); survivors = rows[: a.survivors]
    if not survivors:
        return emit({"ok": False, "error": "no survivors"})
    b = bankmod.Bank.load(ccore.bank_path(a.out)); n_off = max(0, a.pop - a.survivors); ng = a.gen + 1
    plan, dirty = [], False
    for i in range(n_off):
        srow = survivors[i % len(survivors)]; parent = srow["id"]; new_id = f"g{ng:02d}_{i:02d}"; cd = store.agent_dir(a.out, ng, new_id)
        exists = (cd / "roles.json").exists()
        if exists:
            used = store.read_json(cd / "lineage.json", {}).get("lessons_used", [])
        else:
            weakness = _weakness(a.out, a.gen, parent); lessons = b.retrieve(weakness, a.topk, deterministic=False, mark=True)
            dirty = True; used = [l["id"] for l in lessons]
            cd.mkdir(parents=True, exist_ok=True); _clone(a.out, a.gen, parent, ng, new_id)
            store.write_json(cd / "lineage.json", {"parent_id": parent, "parent_gen": a.gen, "lens": "core",
                             "origin": "core_mutation", "lessons_used": used, "changed_components": [], "diff": ""})
            store.write_json(cd / "breed_context.json", {"parent_id": parent, "parent_gen": a.gen,
                             "parent_dir": str(store.agent_dir(a.out, a.gen, parent)), "weakness": weakness,
                             "lessons": [{"id": l["id"], "text": l["text"], "label": l["label"]} for l in lessons]})
        plan.append({"new_id": new_id, "parent_id": parent, "parent_gen": a.gen, "lens": "core",
                     "parent_fit": round(srow.get("ladder_fitness", 0.0), 4), "type": "mutation", "exists": exists, "n_lessons": len(used)})
    if dirty:
        b.save(ccore.bank_path(a.out))
    return emit({"ok": True, "gen": a.gen, "next_gen": ng, "survivors": [s["id"] for s in survivors], "plan": plan})


# ----------------------------------------------------------------- final comparison (vs baselines + sonnet)
def cmd_final_compare(a):
    out = a.out; g = 0
    while store.gen_dir(out, g + 1).exists():
        g += 1
    rows = dctrl._ranked(out, g); champ = rows[0]["id"] if rows else None
    base = store.read_json(Path(out) / "baselines" / "report.json", {})
    cm = store.read_json(store.agent_dir(out, g, champ) / "metrics.json", {}) if champ else {}
    g0 = dctrl._ranked(out, 0); g0b = g0[0]["id"] if g0 else None
    g0m = store.read_json(store.agent_dir(out, 0, g0b) / "metrics.json", {}) if g0b else {}
    res = {"final_gen": g, "champion": champ, "champion_fitness": cm.get("ladder_fitness"),
           "champion_label": pipe_label(load(out, g, champ)["roles"]) if champ else None,
           "gen0_best": g0b, "gen0_best_fitness": g0m.get("ladder_fitness"),
           "baselines": {k: (v or {}).get("fitness") for k, v in base.items()}}
    store.write_json(Path(out) / "final" / "compare.json", res)
    return emit({"ok": True, **res})


# ----------------------------------------------------------------- robust champion re-eval (higher R)
def _boot_mean_ci(vals, B=4000, seed=0):
    """Replicate-level 95% CI: percentile bootstrap over the per-replicate bot_means (the honest unit)."""
    import random
    if not vals:
        return (0.0, 0.0, 0.0)
    rng = random.Random(seed); n = len(vals); means = []
    for _ in range(B):
        means.append(sum(vals[rng.randrange(n)] for _ in range(n)) / n)
    means.sort()
    return (sum(vals) / n, means[int(0.025 * B)], means[int(0.975 * B)])


def cmd_reeval_setup(a):
    """Stage a flat gen_00 of champion genotypes (copied from their source runs) + model baselines, for a
    higher-R re-execution. specs = JSON list of {label, tag, R, [src_out,src_gen,src_agent] | [roles,draft_model]}."""
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    specs = json.loads(Path(a.specs).read_text())
    for rung, src in LADDER_SRC.items():
        store.write_text(store.ladder_path(out, rung), Path(src).read_text())
    store.write_text(out / "contracts" / "simple_bot_contract.txt", harness.SIMPLE_BOT_CONTRACT)
    agents = []
    for s in specs:
        label = s["label"]; R = int(s.get("R", a.R))
        if s.get("src_agent"):                                  # copy an evolved champion (roles + evolved prompts)
            g = load(s["src_out"], int(s["src_gen"]), s["src_agent"]); g["id"] = label; save(out, 0, g)
            roles, dm = g["roles"], g["draft_model"]
        else:                                                   # a model baseline genotype (e.g. 1-shot, best-of-N)
            geno = repair({"id": label, "roles": s["roles"], "prompts": {},
                           "draft_model": s.get("draft_model", "haiku")}, len(s["roles"]))
            geno["id"] = label; save(out, 0, geno); roles, dm = geno["roles"], geno["draft_model"]
        agents.append({"label": label, "tag": s.get("tag", ""), "draft_model": dm,
                       "roles": roles, "n_steps": len(roles), "R": R})
    store.write_json(out / "config.json", {"out": str(out), "sims_eval": a.sims_eval, "sims_cand": a.sims_cand,
                                           "seed": a.seed, "reeval": True, "agents": agents})
    store.write_json(store.gen_dir(out, 0) / "population.json", {"gen": 0, "ids": [x["label"] for x in agents]})
    return emit({"ok": True, "n_agents": len(agents), "agents": agents})


def cmd_reeval_report(a):
    out = Path(a.out); cfg = store.read_json(out / "config.json", {}); agents = cfg.get("agents", [])
    rows = {}
    for ag in agents:
        d = store.agent_dir(out, 0, ag["label"])
        e = store.read_json(d / "evals.json", {}); m = store.read_json(d / "metrics.json", {})
        bm = e.get("bot_means", []); mean, lo, hi = _boot_mean_ci(bm)
        rows[ag["label"]] = {"tag": ag.get("tag", ""), "shape": pipe_label(ag["roles"]), "R": ag["R"],
                             "R_valid": m.get("R_valid"), "mean": round(mean, 4), "ci_lo": round(lo, 4),
                             "ci_hi": round(hi, 4), "bot_means": [round(x, 3) for x in bm],
                             "per_rung": {k: round(v, 3) for k, v in m.get("per_rung", {}).items()},
                             "_pooled": e.get("pooled_games", [])}
    bars = [l for l in ("sonnet_1shot", "opus_1shot", "bestof8", "haiku_1shot") if l in rows]
    comps = {}
    for lab, r in rows.items():
        if lab in bars:
            continue
        comps[lab] = {}
        for b in bars:
            if r["_pooled"] and rows[b]["_pooled"]:
                dd, ll, hh = cp._two_sample_boot(r["_pooled"], rows[b]["_pooled"])
                comps[lab][b] = {"d": round(dd, 4), "ci_lo": round(ll, 4), "ci_hi": round(hh, 4)}
    out_rows = {k: {kk: vv for kk, vv in v.items() if kk != "_pooled"} for k, v in rows.items()}
    store.write_json(out / "reeval_report.json", {"rows": out_rows, "comparisons": comps, "bars": bars})
    return emit({"ok": True, "rows": out_rows, "comparisons": comps, "bars": bars})


def cmd_reeval_resume_plan(a):
    """For a re-eval dir interrupted mid-run (e.g. agent-cap), report agents still missing metrics + how many
    replicates are already complete, so a follow-up workflow can finish ONLY the missing replicates sequentially."""
    out = Path(a.out); cfg = store.read_json(out / "config.json", {}); todo = []
    for ag in cfg.get("agents", []):
        d = store.agent_dir(out, 0, ag["label"])
        if (d / "metrics.json").exists() and (d / "evals.json").exists():
            continue
        done = 0
        for r in range(ag["R"]):
            st = store.read_json(d / f"repl_{r}" / "state.json", {})
            if (d / f"repl_{r}" / "best.py").exists() and st.get("best_cand") is not None:
                done += 1
            else:
                break
        pr = d / f"repl_{done}"          # drop a partially-written replicate so it reruns cleanly
        if pr.exists():
            shutil.rmtree(pr)
        todo.append({"label": ag["label"], "tag": ag.get("tag", ""), "R": ag["R"], "done": done,
                     "roles": ag["roles"], "draft_model": ag["draft_model"]})
    return emit({"ok": True, "todo": todo})


# ----------------------------------------------------------------- CLI
def main():
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p):
        p.add_argument("--out", required=True)

    p = sub.add_parser("init"); common(p)
    p.add_argument("--N", type=int, default=4); p.add_argument("--R", type=int, default=5)
    p.add_argument("--pop", type=int, default=8); p.add_argument("--survivors", type=int, default=4)
    p.add_argument("--sims-eval", dest="sims_eval", type=int, default=100)
    p.add_argument("--sims-cand", dest="sims_cand", type=int, default=60)
    p.add_argument("--seed", type=int, default=0); p.add_argument("--optimizer", choices=["gepa", "core"], default="gepa")
    p.set_defaults(fn=cmd_init)

    p = sub.add_parser("pipe-plan"); common(p)
    p.add_argument("--gen", type=int, required=True); p.add_argument("--agent", required=True); p.add_argument("--N", type=int, default=4)
    p.set_defaults(fn=cmd_pipe_plan)

    p = sub.add_parser("pipe-feedback"); common(p)
    p.add_argument("--gen", type=int, required=True); p.add_argument("--agent", required=True); p.add_argument("--repl", type=int, required=True)
    p.set_defaults(fn=cmd_pipe_feedback)

    p = sub.add_parser("pipe-score-cand"); common(p)
    p.add_argument("--gen", type=int, required=True); p.add_argument("--agent", required=True)
    p.add_argument("--repl", type=int, required=True); p.add_argument("--cand", type=int, required=True)
    p.add_argument("--sims-cand", dest="sims_cand", type=int, default=60); p.add_argument("--seed", type=int, default=0)
    p.set_defaults(fn=cmd_pipe_score_cand)

    p = sub.add_parser("pipe-eval-score"); common(p)
    p.add_argument("--gen", type=int, required=True); p.add_argument("--agent", required=True)
    p.add_argument("--R", type=int, default=5); p.add_argument("--sims-cand", dest="sims_cand", type=int, default=60)
    p.add_argument("--seed", type=int, default=0); p.set_defaults(fn=cmd_pipe_eval_score)

    p = sub.add_parser("score-pop"); common(p); p.add_argument("--gen", type=int, required=True); p.set_defaults(fn=cmd_score_pop)

    p = sub.add_parser("select"); common(p)
    p.add_argument("--gen", type=int, required=True); p.add_argument("--survivors", type=int, default=4); p.set_defaults(fn=dctrl.cmd_select)

    p = sub.add_parser("admit"); common(p)
    p.add_argument("--gen", type=int, required=True); p.add_argument("--child", required=True)
    p.add_argument("--parent-gen", dest="parent_gen", type=int, required=True); p.add_argument("--parent", required=True)
    p.set_defaults(fn=cmd_admit)

    p = sub.add_parser("finalize-gen"); common(p)
    p.add_argument("--gen", type=int, required=True); p.add_argument("--pop", type=int, default=8)
    p.add_argument("--survivors", type=int, default=4); p.set_defaults(fn=dctrl.cmd_finalize_gen)

    p = sub.add_parser("population-summary"); common(p); p.add_argument("--gen", type=int, required=True); p.set_defaults(fn=dctrl.cmd_population_summary)

    p = sub.add_parser("breed-plan-gepa"); common(p)
    p.add_argument("--gen", type=int, required=True); p.add_argument("--pop", type=int, default=8); p.add_argument("--survivors", type=int, default=4)
    p.set_defaults(fn=cmd_breed_plan_gepa)

    p = sub.add_parser("core-reflect-plan"); common(p)
    p.add_argument("--gen", type=int, required=True); p.add_argument("--pairs", type=int, default=4); p.add_argument("--margin", type=float, default=0.03)
    p.set_defaults(fn=cmd_core_reflect_plan)

    p = sub.add_parser("core-ingest"); common(p)
    p.add_argument("--gen", type=int, required=True); p.add_argument("--max-lessons", dest="max_lessons", type=int, default=4); p.add_argument("--plan", default="")
    p.set_defaults(fn=ccore.cmd_core_ingest)

    p = sub.add_parser("core-breed-plan"); common(p)
    p.add_argument("--gen", type=int, required=True); p.add_argument("--pop", type=int, default=8); p.add_argument("--survivors", type=int, default=4); p.add_argument("--topk", type=int, default=3)
    p.set_defaults(fn=cmd_core_breed_plan)

    p = sub.add_parser("core-credit"); common(p); p.add_argument("--gen", type=int, required=True); p.set_defaults(fn=ccore.cmd_core_credit)
    p = sub.add_parser("bank-status"); common(p); p.set_defaults(fn=ccore.cmd_bank_status)

    p = sub.add_parser("baseline-report"); common(p)
    p.set_defaults(fn=lambda a: _baseline_report(a))

    p = sub.add_parser("final-compare"); common(p); p.set_defaults(fn=cmd_final_compare)

    p = sub.add_parser("reeval-setup"); common(p)
    p.add_argument("--specs", required=True); p.add_argument("--R", type=int, default=8)
    p.add_argument("--sims-eval", dest="sims_eval", type=int, default=100)
    p.add_argument("--sims-cand", dest="sims_cand", type=int, default=60)
    p.add_argument("--seed", type=int, default=0); p.set_defaults(fn=cmd_reeval_setup)

    p = sub.add_parser("reeval-report"); common(p); p.set_defaults(fn=cmd_reeval_report)

    p = sub.add_parser("reeval-resume-plan"); common(p); p.set_defaults(fn=cmd_reeval_resume_plan)

    a = ap.parse_args(); a.fn(a)


def _baseline_report(a):
    out = a.out; cfg = store.config(out); res = {}
    for bid in cfg.get("baselines", []):
        m = store.read_json(Path(out) / "baselines" / bid / "metrics.json", {})
        res[bid] = {"fitness": m.get("ladder_fitness"), "per_rung": m.get("per_rung"), "R_valid": m.get("R_valid")}
    store.write_json(Path(out) / "baselines" / "report.json", res)
    return emit({"ok": True, "results": {k: (round(v["fitness"], 4) if v.get("fitness") is not None else None) for k, v in res.items()},
                 "sonnet_1shot": (res.get("sonnet_1shot") or {}).get("fitness")})


if __name__ == "__main__":
    main()
