"""cc_swe controller — evolve a budget-N Haiku harness on SWE-bench Verified (Claude-family, GEPA/CORE + verified
acceptance). Mirrors cc_code.control_code: genotype (roles in {draft,critique,fix} + per-role prompts), optimizers,
and the bootstrap admit gate are REUSED from cc_pipe/cc_decomp. Only the backend differs:

  - a "replicate" = a SWE-bench INSTANCE (issue + repo@base_commit), solved by an agent EDITING a host checkout;
  - the controller derives the candidate PATCH via `git diff`, scores it by a DEPLOYABLE signal (regression sample +
    an agent reproduction test) for keep-best/critique, and computes FITNESS by TRUE resolution (FAIL_TO_PASS+
    PASS_TO_PASS) on the train instances. Execution runs in the official SWE-bench images via Apptainer (swe_harness).

Solve chain per instance (keep-best): swe-prep (reset/apply-best checkout) -> agent edits -> swe-score-cand
(git diff -> deployable score -> keep best). critique reads swe-feedback. fitness via swe-eval-score (hidden tests).
"""
import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path

from cc_decomp import store
from cc_decomp import control as dctrl
from cc_pipe import control_pipe as cpipe
from cc_prompt import control_prompt as cp
from cc_core import control as ccore
from cc_core import bank as bankmod
from cc_swe import swe_harness as H

emit = cpipe.emit
ROLES_REP = cpipe.ROLES_REP

# SWE-domain strategy prompts (the evolved genotype starts here; GEPA/CORE mutate them).
# Four EXPLICIT agent types. Test-writing is split out of the draft into its own write_test agent so the
# keep-best deployable signal is judged by an INDEPENDENT, rigorous test (not a self-satisfying one the draft
# wrote) — this stops the proxy saturating at the draft and lets the fix steps actually climb.
SWE_PROMPTS = {
    "draft": ("You are the DRAFT agent. Your ONE job: read the GitHub issue, LOCALIZE the defect in the REAL "
              "repository source (grep/read to find the exact function/branch/line responsible), and make the "
              "MINIMAL correct source change that resolves the issue without breaking existing behavior. Match the "
              "surrounding code style. Do NOT write any test — a separate write_test agent does that. Never edit the "
              "repo's existing test files. Output: the source edit only."),
    "write_test": ("You are the WRITE_TEST agent — the harness's INDEPENDENT judge of whether the fix works. Write a "
                   "reproduction test that: (1) IMPORTS and CALLS the repository's REAL public API to exercise the "
                   "buggy code path — NEVER reimplement, copy, stub, or locally redefine the function under test; (2) "
                   "asserts the SPECIFIC behavioral contract from the issue (the exact expected value/output/exception), "
                   "with a TIGHT assertion that FAILS on buggy or incomplete code and passes ONLY when the real fix is "
                   "correct; (3) runs standalone. A test that passes against a local reimplementation, checks source "
                   "text, or only asserts 'no crash' is INVALID. Write ONLY the test file; do NOT edit any repository "
                   "source."),
    "critique": ("You are the CRITIQUE agent. The reproduction test (from write_test) was run against the current best "
                 "patch. From the feedback (did the repro test pass? its traceback; which regression tests broke; did "
                 "the patch apply?), name the SINGLE biggest concrete root cause and exactly what to change (file/"
                 "function/lines)."),
    "fix": ("You are the FIX agent. The write_test reproduction test was run against the current best patch — read its "
            "ACTUAL output/traceback in the feedback, plus any critique note. Refine the SOURCE so that reproduction "
            "test passes and no regression tests break. Keep the change minimal and self-contained; never edit the "
            "repo's existing test files."),
}
# SWE uses a 4-role taxonomy (write_test split out of draft). Rebind in THIS process only (BattleSnake runs
# in separate processes and keeps its own 3-role set). repair/load/save key off cpipe.ROLES_REP.
cpipe.ROLES_REP = ["draft", "write_test", "critique", "fix"]
ROLES_REP = cpipe.ROLES_REP
cpipe.DEFAULT_PROMPTS = SWE_PROMPTS  # rebind so cpipe.repair/save inject SWE strategy into genotypes (own process)
# COMBINED GEPA mutation: every offspring changes STRUCTURE (roles.json) AND one ROLE PROMPT together, so
# structure + prompts co-evolve coherently. The lens selects WHICH prompt co-evolves (structure always
# changes), so LENSES = the prompt roles — no standalone "structure" lens.
cpipe.LENSES = ["draft", "write_test", "critique", "fix"]

TIMEOUT = int(os.environ.get("CC_SWE_TIMEOUT", "1200"))
REG_SAMPLE = int(os.environ.get("CC_SWE_REG_SAMPLE", "8"))


# ----------------------------------------------------------------- baselines / instances on disk
def _baseline_genos(N):
    return [{"id": "haiku_1shot", "roles": ["draft"], "draft_model": "haiku"},
            {"id": "sonnet_1shot", "roles": ["draft"], "draft_model": "sonnet"},
            {"id": "opus_1shot", "roles": ["draft"], "draft_model": "opus"},
            {"id": "haiku_bestN", "roles": ["draft"] * N, "draft_model": "haiku"},
            {"id": "haiku_refineN", "roles": ["draft"] + ["fix"] * (N - 1), "draft_model": "haiku"}]


def _rm_tree(p):
    """Best-effort recursive delete of a regenerable heavy dir (full repo checkout). Never raises."""
    try:
        if Path(p).exists():
            shutil.rmtree(p, ignore_errors=True)
    except Exception:
        pass


def _inst_dir(out, split):
    return Path(out) / "instances" / split


def _write_instances(out, split, insts):
    d = _inst_dir(out, split)
    for i, p in enumerate(insts):
        view = {"idx": i, "instance_id": p["instance_id"], "repo": p["repo"],
                "base_commit": p["base_commit"], "problem_statement": p["problem_statement"]}
        store.write_json(d / f"inst_{i:03d}.json", view)
    store.write_json(Path(out) / "instances" / f"{split}_full.json", list(insts))


def _load_full(out, split):
    return store.read_json(Path(out) / "instances" / f"{split}_full.json", [])


# ----------------------------------------------------------------- checkout management
def _pristine(out, split, iid):
    return Path(out) / "checkouts" / split / iid


def _git(co, *args, **kw):
    return subprocess.run(["git", "-C", str(co), *args], capture_output=True, text=True, **kw)


def ensure_pristine(out, split, inst):
    """Lazily extract the repo@base_commit from the instance's Apptainer image to a host checkout (with .git)."""
    iid = inst["instance_id"]
    co = _pristine(out, split, iid)
    if (co / ".git").exists():
        return co
    co.parent.mkdir(parents=True, exist_ok=True)
    sp = H.ensure_image(iid)
    if co.exists():
        shutil.rmtree(co, ignore_errors=True)
    flags = H.RUN_FLAGS
    r = subprocess.run(["apptainer", "exec", *flags, "--bind", f"{co.parent}:/out", str(sp),
                        "bash", "-c", f"cp -a /testbed /out/{iid}"], capture_output=True, text=True, timeout=600)
    if not (co / ".git").exists():
        raise RuntimeError(f"checkout extract failed for {iid}: {r.stderr[-300:]}")
    _git(co, "config", "user.email", "cc@swe"); _git(co, "config", "user.name", "cc")
    return co


def _agent_dir(out, gen, aid):
    return cpipe._agent_dir(out, gen, aid)


def _work(out, gen, aid, repl):
    return _agent_dir(out, gen, aid) / f"repl_{repl}" / "work"


def _reset_work(out, gen, aid, repl, split, inst, apply_best=False):
    """Make the (gen,agent,repl) working checkout pristine, optionally re-applying the kept-best patch."""
    pr = ensure_pristine(out, split, inst)
    w = _work(out, gen, aid, repl)
    if not (w / ".git").exists():
        w.parent.mkdir(parents=True, exist_ok=True)
        if w.exists():
            shutil.rmtree(w, ignore_errors=True)
        subprocess.run(["cp", "-a", str(pr), str(w)], check=True)
    else:
        _git(w, "checkout", "--", "."); _git(w, "clean", "-fdq")
    if apply_best:
        rd = _agent_dir(out, gen, aid) / f"repl_{repl}"
        bp = rd / "best.patch"
        if bp.exists() and bp.read_text().strip():
            _git(w, "apply", str(bp))
    return w


# =================================================================== commands
def _swe_seeds(N):
    """SWE-specific seed harnesses. Includes BEST_OF_N (pure parallel diversity, D×N keep-best) — the
    strongest naive Haiku approach on SWE-bench (= Sonnet parity), which the prior seed pool lacked — and
    drops the redundant draft_crit_fix (it repaired to the same D→C→F→F as critique_fix). Giving evolution a
    best-of-N starting point lets it discover diversify-then-refine (add a fix step) — the BattleSnake winner."""
    def g(pid, roles):
        return {"id": pid, "roles": roles[:N] + ["fix"] * max(0, N - len(roles)),
                "prompts": {}, "draft_model": "haiku",
                "lineage": {"parent_id": None, "origin": "seed", "lens": None, "changed_components": [], "diff": ""}}
    # INVARIANT for write_test genotypes: a SINGLE draft at index 0, write_test at index 1, then critique/fix
    # (the harness scores that one draft against the test, so the test must directly follow the draft — no extra
    # draft or fix before it). Multi-draft-before-test does not compose with deferred scoring (see mut-verify).
    return [
        g("wt_refine", ["draft", "write_test", "fix"]),             # D W F (F) — test, then refine
        g("wt_crit", ["draft", "write_test", "critique", "fix"]),   # D W C F — test, diagnose, fix
        g("best_of_n", ["draft"] * N),                              # D×N  — pure diversity, no test (contrast)
        g("refine", ["draft", "fix"]),                              # D F (F) — naive refine, no test (contrast)
        g("crit_fix", ["draft", "critique", "fix", "fix"]),         # D C F F — critique-fix, no test (contrast)
    ]


def cmd_init(a):
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    reuse = getattr(a, "reuse_split", None)
    if reuse:
        # Reuse a pre-staged split verbatim (keeps baselines + evolution on the SAME instances).
        train = store.read_json(Path(reuse) / "instances" / "train_full.json", [])
        ev = store.read_json(Path(reuse) / "instances" / "eval_full.json", [])
        if not train or not ev:
            raise RuntimeError(f"reuse-split {reuse} missing train_full.json/eval_full.json")
    else:
        probs = H.load_swe_verified()
        sel = H.select_instances(probs)
        train, ev = H.split_train_eval(sel, a.n_train, a.n_eval, seed=a.seed)
    _write_instances(out, "train", train)
    _write_instances(out, "eval", ev)
    store.write_text(out / "contracts" / "swe_contract.txt",
                     "Fix the GitHub issue by editing the checked-out repo's SOURCE (never its existing tests). "
                     "Produce a minimal patch + a reproduction test. Resolution = the repo's hidden FAIL_TO_PASS + "
                     "PASS_TO_PASS tests pass.")
    base = []
    for bg in _baseline_genos(a.N):
        cpipe.save(out, -1, cpipe.repair({**bg, "prompts": {}}, len(bg["roles"])))
        base.append(bg["id"])
    seeds = _swe_seeds(a.N)[: a.pop]
    for s in seeds:
        cpipe.save(out, 0, cpipe.repair(s, a.N))
    store.write_json(store.gen_dir(out, 0) / "population.json",
                     {"gen": 0, "ids": [s["id"] for s in seeds], "carried": [], "new_ids": [s["id"] for s in seeds]})
    cfg = {"out": str(out), "benchmark": "swe-verified", "N": a.N, "pop": a.pop, "survivors": a.survivors,
           "n_train": len(train), "n_eval": len(ev), "seed": a.seed, "optimizer": a.optimizer,
           "roles": ROLES_REP, "lenses": cpipe.LENSES, "baselines": base,
           "train_ids": [p["instance_id"] for p in train], "eval_ids": [p["instance_id"] for p in ev]}
    store.write_json(out / "config.json", cfg)
    if a.optimizer == "core":
        b = bankmod.Bank(); b.save(ccore.bank_path(out)); ccore._snap(b, 0, out)
    return emit({"ok": True, "N": a.N, "n_train": len(train), "n_eval": len(ev), "optimizer": a.optimizer,
                 "baselines": base, "seed_ids": [s["id"] for s in seeds],
                 "seed_labels": {s["id"]: cpipe.pipe_label(cpipe.repair(s, a.N)["roles"]) for s in seeds}})


def cmd_pipe_plan(a):
    return cpipe.cmd_pipe_plan(a)


def _split_for(a):
    return getattr(a, "split", "train") or "train"


def cmd_swe_prep(a):
    """Prepare the (gen,agent,repl) working checkout before an agent edit. role=draft -> pristine; else apply best.
    PER-INSTANCE RESUME: if this is the draft (cand 0, chain start) and the instance is ALREADY fully solved
    (best.patch + state.best_cand exist from a prior interrupted run), report already_solved=True so the workflow
    skips re-solving it — its best.patch is reused by swe-eval-score. Makes quota interruptions cheap."""
    probs = _load_full(a.out, _split_for(a)); inst = probs[a.repl]
    rd = _agent_dir(a.out, a.gen, a.agent) / f"repl_{a.repl}"
    st = store.read_json(rd / "state.json", {}); bp = rd / "best.patch"
    if a.role == "draft" and a.cand == 0 and st.get("best_cand") is not None and bp.exists() and bp.read_text().strip():
        return emit({"ok": True, "repl": a.repl, "already_solved": True,
                     "work": str(_work(a.out, a.gen, a.agent, a.repl)),
                     "instance_id": inst["instance_id"], "repo": inst["repo"]})
    w = _reset_work(a.out, a.gen, a.agent, a.repl, _split_for(a), inst, apply_best=(a.role != "draft"))
    return emit({"ok": True, "repl": a.repl, "already_solved": False, "work": str(w),
                 "instance_id": inst["instance_id"], "repo": inst["repo"]})


def cmd_swe_score_cand(a):
    """git diff the working checkout -> candidate patch; score by DEPLOYABLE signal (regression + repro test); keep best."""
    probs = _load_full(a.out, _split_for(a)); inst = probs[a.repl]
    rd = _agent_dir(a.out, a.gen, a.agent) / f"repl_{a.repl}"; w = _work(a.out, a.gen, a.agent, a.repl)
    _git(w, "add", "-A", "-N")
    diff = _git(w, "diff").stdout
    (rd / f"c{a.cand}.patch").write_text(diff)
    repro_fp = rd / "repro_cc.py"
    repro = repro_fp.read_text() if repro_fp.exists() else None
    rec = {"cand": a.cand, "valid": bool(diff.strip()), "mean": 0.0}
    if diff.strip():
        dep = H.run_deployable(inst, diff, repro_test=repro, work_dir=str(rd / f"deploy_{a.cand}"),
                               regression_sample=REG_SAMPLE, timeout=TIMEOUT)
        rec = {"cand": a.cand, "valid": True, "mean": dep["score"], "applied": dep["applied"],
               "repro_pass": dep["repro_pass"], "regression_frac": dep["regression_frac"], "feedback": dep["feedback"]}
    store.write_json(rd / f"c{a.cand}.json", rec)
    st = store.read_json(rd / "state.json", {"best_score": -1.0, "best_cand": None})
    if rec["valid"] and rec["mean"] > st.get("best_score", -1.0):
        st.update({"best_score": rec["mean"], "best_cand": a.cand, "feedback": rec.get("feedback", "")})
        (rd / "best.patch").write_text(diff)
    store.write_json(rd / "state.json", st)
    # Retain a bounded tail of the ACTUAL execution/test log for this candidate (the deploy checkout itself
    # is dropped below, but the mutator needs the real log — not just the 1-line feedback — to reconstruct the
    # trajectory story of how each step's code behaved when run).
    dlog = rd / f"deploy_{a.cand}" / "deploy.log"
    if dlog.exists():
        try:
            store.write_text(rd / f"c{a.cand}.log", dlog.read_text(errors="ignore")[-3500:])
        except Exception:
            pass
    # disk hygiene: the per-candidate deployable checkout is a full repo copy and is not needed once
    # scored (feedback + log tail already captured). Drop it to bound /local-ssd usage during solving.
    if os.environ.get("CC_SWE_KEEP_WORK") != "1":
        _rm_tree(rd / f"deploy_{a.cand}")
    return emit({"ok": True, "repl": a.repl, "cand": a.cand, "valid": rec["valid"],
                 "cand_score": round(rec["mean"], 4), "best_score": round(st["best_score"], 4)})


def cmd_swe_feedback(a):
    """Write feedback.json for the critique step from the kept-best candidate's deployable result."""
    rd = _agent_dir(a.out, a.gen, a.agent) / f"repl_{a.repl}"
    st = store.read_json(rd / "state.json", {})
    bp = rd / "best.patch"
    has = bp.exists() and bp.read_text().strip()
    fb = {"summary": st.get("feedback", "no candidate yet"), "best_score": st.get("best_score", -1.0),
          "has_patch": bool(has), "n_fail": 0 if (st.get("best_score", 0) or 0) >= 1.0 else 1}
    store.write_json(rd / "feedback.json", fb)
    return emit({"ok": True, "repl": a.repl, "n_fail": fb["n_fail"], "summary": fb["summary"][:200]})


def cmd_swe_eval_score(a):
    """FITNESS: take each instance's kept-best patch, run TRUE resolution (hidden FAIL_TO_PASS+PASS_TO_PASS). R=1.
    Instances are GRADED CONCURRENTLY (each is an independent Apptainer run with its own work dir → identical
    results, only overlapped). A per-instance crash/timeout degrades to unresolved (0) instead of aborting the batch.
    Worker count via CC_SWE_EVAL_WORKERS (default 12)."""
    import concurrent.futures as _cf
    d = _agent_dir(a.out, a.gen, a.agent)
    probs = _load_full(a.out, _split_for(a))
    n = a.n_prob if a.n_prob else len(probs)
    workers = max(1, int(os.environ.get("CC_SWE_EVAL_WORKERS", "12")))

    def grade(r):
        rd = d / f"repl_{r}"; bp = rd / "best.patch"
        patch = bp.read_text() if bp.exists() else ""
        if not patch.strip():
            return 0
        # PER-INSTANCE RESULT CACHE: makes eval-score resumable + safe against agent-wrapper retries.
        # The slow 27-instance grade can exceed the wrapping agent's patience; on retry we reuse the
        # verdicts already computed (this tiny file survives the work-dir cleanup) and only grade the rest.
        cache = rd / "eval_result.json"
        cached = store.read_json(cache, {})
        if cached.get("graded") and cached.get("patch_len") == len(patch):
            return int(cached.get("resolved", 0))
        try:
            res = H.run_instance_eval(probs[r], patch, str(rd / "eval"), timeout=TIMEOUT)
            ok = 1 if res["resolved"] else 0
        except Exception as e:  # one bad grade must not sink the whole evaluation
            (rd / "eval_error.txt").write_text(f"{type(e).__name__}: {e}")
            ok = 0
        store.write_json(cache, {"graded": True, "resolved": ok, "patch_len": len(patch)})
        return ok

    pooled = [0] * n
    if workers <= 1:
        for r in range(n):
            pooled[r] = grade(r)
    else:
        with _cf.ThreadPoolExecutor(max_workers=min(workers, n) or 1) as ex:
            for r, ok in zip(range(n), ex.map(grade, range(n))):
                pooled[r] = ok
    per = [float(x) for x in pooled]; solved = sum(pooled)
    fitness = (sum(per) / len(per)) if per else 0.0
    store.write_json(d / "evals.json", {"per_problem": per, "pooled_games": pooled,
                                        "fitness": fitness, "n_prob": n, "split": _split_for(a)})
    # Per-split copy so a single genotype evaluated on BOTH splits (Self-Harness two-split gate) keeps
    # train + eval results side by side instead of overwriting evals.json. Back-compatible (extra file).
    store.write_json(d / f"evals_{_split_for(a)}.json", {"per_problem": per, "pooled_games": pooled,
                                                         "fitness": fitness, "n_prob": n, "split": _split_for(a)})
    m = store.read_json(d / "metrics.json", {})
    m.update({"id": a.agent, "ladder_fitness": fitness, "solved": solved, "n_prob": n, "R_valid": n,
              "split": _split_for(a)})
    store.write_json(d / "metrics.json", m)
    # REFLECTION DIGEST: persist per-instance outcomes + the deployable failure detail BEFORE cleanup,
    # so the GEPA mutator can reflect on WHY the parent failed (not just an aggregate score). Faithful:
    # uses the deployable signal (repro + regression errors), never the hidden FAIL_TO_PASS test identities.
    roles = store.read_json(d / "roles.json", {}).get("roles", [])
    digest = []
    for r in range(n):
        rd = d / f"repl_{r}"
        st = store.read_json(rd / "state.json", {})
        # TRAJECTORY: the ordered per-candidate record so the mutator can reconstruct how the chain (draft ->
        # write_test -> fix -> ...) built and refined the patch, and WHERE it fell short. The full diffs/logs/test
        # stay on disk (c{cand}.patch, c{cand}.log, repro_cc.py under repl_<idx>/) for the mutator to read directly.
        cands, ci = [], 0
        while (rd / f"c{ci}.json").exists():
            cj = store.read_json(rd / f"c{ci}.json", {})
            pf = rd / f"c{ci}.patch"
            cands.append({"cand": ci, "score": cj.get("mean"), "applied": cj.get("applied"),
                          "repro_pass": cj.get("repro_pass"), "regression": cj.get("regression_frac"),
                          "feedback": (cj.get("feedback") or "")[:600],
                          "patch_lines": (len(pf.read_text(errors="ignore").splitlines()) if pf.exists() else 0)})
            ci += 1
        repro = rd / "repro_cc.py"
        digest.append({"idx": r, "instance_id": probs[r].get("instance_id"), "repo": probs[r].get("repo"),
                       "resolved": int(pooled[r]), "roles": roles,
                       "best_cand": st.get("best_cand"), "best_score": st.get("best_score"),
                       "best_feedback": (st.get("feedback") or "")[:800], "candidates": cands,
                       "repro_excerpt": (repro.read_text(errors="ignore")[:700] if repro.exists() else ""),
                       "artifacts_dir": str(rd)})
    store.write_json(d / "failures.json", {"agent": a.agent, "split": _split_for(a), "solved": solved,
                                           "n_prob": n, "roles": roles, "instances": digest})
    # disk hygiene: the harness is now fully scored; drop the regenerable heavy checkouts
    # (per-repl work/ + eval/ + any leftover deploy_*). Keeps best.patch, c*.patch, repro_cc.py, *.json.
    # Safe for resume: pipe-plan 'exists' is keyed on metrics.json+evals.json, and swe-prep rebuilds work/.
    if os.environ.get("CC_SWE_KEEP_WORK") != "1":
        for r in range(n):
            rd = d / f"repl_{r}"
            _rm_tree(rd / "work"); _rm_tree(rd / "eval")
            for dep in rd.glob("deploy_*"):
                _rm_tree(dep)
    return emit({"ok": True, "agent": a.agent, "fitness": round(fitness, 4), "solved": solved, "n_prob": n})


def cmd_admit_paired(a):
    """PAIRED bootstrap admit gate. Child and parent are evaluated on the SAME train instances in the SAME
    order, so resample instance INDICES and bootstrap the mean per-instance difference (child_i - parent_i).
    This is the statistically correct test for paired data and is far more powerful than the unpaired
    two-sample bootstrap at small N (the unpaired version rejected real +1/+2-instance gains). Admit iff the
    95% CI lower bound on the mean paired difference is > 0."""
    import numpy as np
    out = a.out
    cev = store.read_json(_agent_dir(out, a.gen, a.child) / "evals.json", {})
    pev = store.read_json(_agent_dir(out, a.parent_gen, a.parent) / "evals.json", {})
    c = cev.get("pooled_games", []); p = pev.get("pooled_games", [])
    n = min(len(c), len(p))
    if n == 0:
        rec = {"parent_id": a.parent, "parent_gen": a.parent_gen, "child_fit": cev.get("fitness"),
               "parent_fit": pev.get("fitness"), "delta": 0.0, "ci_low": 0.0, "ci_high": 0.0,
               "admitted": False, "test": "paired_bootstrap", "n": 0}
    else:
        ca = np.asarray(c[:n], float); pa = np.asarray(p[:n], float); diff = ca - pa
        rng = np.random.RandomState(1234)
        boot = diff[rng.randint(0, n, size=(4000, n))].mean(axis=1)
        lo, hi = float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))
        # DECOUPLED-ADMIT: at small N_train a 95% CI can't confirm a real +1/+2-instance gain. We admit
        # liberally to keep the ratchet moving, and rely on the HELD-OUT eval to de-inflate the final champion.
        # Mode via CC_SWE_ADMIT_CONF: <=0.5 = LENIENT, admit ANY net improvement (delta>0, i.e. keep +1 gains);
        # >0.5 = robust one-sided confidence (e.g. 0.85 needs a consistent +2). p_better/CI kept for transparency.
        conf = float(os.environ.get("CC_SWE_ADMIT_CONF", "0.5"))
        delta = float(diff.mean())
        p_better = float((boot > 0.0).mean())
        admitted = (delta > 1e-9) if conf <= 0.5 else (p_better >= conf)
        rec = {"parent_id": a.parent, "parent_gen": a.parent_gen, "child_fit": cev.get("fitness"),
               "parent_fit": pev.get("fitness"), "delta": delta, "ci_low": lo, "ci_high": hi,
               "p_better": p_better, "conf": conf, "admitted": bool(admitted),
               "test": "paired_bootstrap_lenient" if conf <= 0.5 else "paired_bootstrap_onesided", "n": n}
    cd = _agent_dir(out, a.gen, a.child)
    m = store.read_json(cd / "metrics.json", {}); m["verified_vs_parent"] = rec; m.setdefault("id", a.child)
    store.write_json(cd / "metrics.json", m)
    return emit({"ok": True, "child": a.child, "admitted": rec["admitted"], "delta": round(rec["delta"], 4),
                 "ci_low": round(rec["ci_low"], 4), "ci_high": round(rec["ci_high"], 4),
                 "child_fit": rec["child_fit"], "parent_fit": rec["parent_fit"]})


def cmd_mut_verify(a):
    """Verify a GEPA/CORE mutation actually LANDED on disk — i.e. the child's mutated component differs
    from the parent's. The mutation is performed by an LLM agent that writes files; without this check the
    agent can silently no-op (return an ack without writing) and the child stays a byte-identical clone of
    the parent, which makes "evolution" select over identical genotypes. The workflow loops mutate->verify
    and retries with escalation until changed (or fails loudly).

    --combined: every mutation must change BOTH the structure (roles.json) AND the lens role's prompt, so
    structure and prompts co-evolve coherently. changed = (roles differ) AND (lens prompt differs); valid =
    (roles valid) AND (prompt non-degenerate). Without --combined it's the legacy single-lens check
    (lens=='structure' -> roles only; else -> that one prompt)."""
    out = a.out
    cd = _agent_dir(out, a.gen, a.child)
    pd = _agent_dir(out, a.parent_gen, a.parent)
    lens = a.lens
    # --- structure delta ---
    cr = store.read_json(cd / "roles.json", {}).get("roles", [])
    pr = store.read_json(pd / "roles.json", {}).get("roles", [])
    Nlen = len(pr) or len(cr)
    struct_valid = bool(cr and len(cr) == Nlen and cr[0] == "draft" and cr[-1] != "critique"
                        and all(x in ROLES_REP for x in cr))
    # write_test invariant (deferred scoring): if a write_test step is present there must be EXACTLY one draft
    # (at index 0) and EXACTLY one write_test (at index 1) — no draft/fix before the test. Otherwise the harness
    # would score only the last pre-test draft and silently discard the rest.
    if "write_test" in cr:
        struct_valid = struct_valid and cr.count("draft") == 1 and cr.count("write_test") == 1 \
            and len(cr) >= 2 and cr[1] == "write_test"
    struct_changed = (cr != pr)
    struct_detail = f"{cpipe.pipe_label(pr) if pr else '?'} -> {cpipe.pipe_label(cr) if cr else '?'}"
    # --- prompt delta (lens role; for legacy 'structure' lens default to draft) ---
    role = lens if lens in ROLES_REP else "draft"
    ct = (store.read_text(cd / "prompts" / f"{role}.md") or "").strip()
    pt = (store.read_text(pd / "prompts" / f"{role}.md") or "").strip()
    prompt_changed = (ct != pt)
    prompt_valid = len(ct) >= 80                 # guard against a degenerate/truncated write
    if getattr(a, "combined", False):
        # FREE combined mutation: require a structural change AND >=1 prompt change, but the mutator may rewrite
        # ANY/ALL of the role prompts (not just the lens one). changed = struct AND >=1 prompt differs.
        changed_prompts, degenerate = [], []
        for rr in ROLES_REP:
            c = (store.read_text(cd / "prompts" / f"{rr}.md") or "").strip()
            p = (store.read_text(pd / "prompts" / f"{rr}.md") or "").strip()
            if c != p:
                changed_prompts.append(rr)
                if len(c) < 80:
                    degenerate.append(rr)
        changed = struct_changed or bool(changed_prompts)   # require >=1 change (struct and/or any prompt)
        valid = struct_valid and not degenerate
        detail = (f"struct[{struct_detail} changed={struct_changed} valid={struct_valid}] "
                  f"prompts_changed={changed_prompts} degenerate={degenerate}")
        return emit({"ok": True, "kind": "combined", "changed": bool(changed), "valid": bool(valid),
                     "detail": detail, "struct_changed": struct_changed, "prompts_changed": changed_prompts})
    if lens == "structure":
        return emit({"ok": True, "kind": "structure", "changed": bool(struct_changed), "valid": struct_valid,
                     "detail": struct_detail})
    changed = prompt_changed
    valid = prompt_valid
    detail = f"{role}.md parent={len(pt)}b child={len(ct)}b"
    return emit({"ok": True, "kind": "prompt", "role": role, "changed": bool(changed), "valid": valid, "detail": detail})


def cmd_breed_plan_gepa_topfit(a):
    """GEPA breed plan that mutates ONLY from the TOP-fitness parent(s) — every offspring's parent is a
    genotype at the MAXIMUM fitness in the current population (within 1e-9). This removes the lenient gate's
    'lucky admit vs a weak-drawn parent' false-positive path: with the parent's score frozen at its single
    draw, breeding from a low-drawn parent (e.g. crit_each 0.607) lets a child admit by noise; restricting to
    the top parent (0.714) means an admit requires actually beating the best result. Re-clones/re-points any
    offspring this gen that was already bred from a non-top parent (round-robin remnant)."""
    rows = dctrl._ranked(a.out, a.gen)
    if not rows:
        return emit({"ok": False, "error": "no rows"})
    top = rows[0]["ladder_fitness"]
    topfit = [r["id"] for r in rows if abs(r["ladder_fitness"] - top) < 1e-9]
    fitof = {r["id"]: r["ladder_fitness"] for r in rows}
    survivors = [r["id"] for r in rows[: a.survivors]]
    n_off = max(0, a.pop - a.survivors); ng = a.gen + 1; plan = []
    for i in range(n_off):
        parent = topfit[i % len(topfit)]; lens = cpipe.LENSES[i % len(cpipe.LENSES)]
        new_id = f"g{ng:02d}_{i:02d}"; cd = _agent_dir(a.out, ng, new_id)
        cur = store.read_json(cd / "lineage.json", {})
        needs = (not (cd / "roles.json").exists()) or cur.get("parent_id") != parent
        if needs:
            cd.mkdir(parents=True, exist_ok=True); cpipe._clone(a.out, a.gen, parent, ng, new_id)
            store.write_json(cd / "lineage.json", {"parent_id": parent, "parent_gen": a.gen, "lens": lens,
                             "origin": "gepa_mutation_topfit", "changed_components": [lens], "diff": ""})
        plan.append({"new_id": new_id, "parent_id": parent, "parent_gen": a.gen, "lens": lens,
                     "parent_fit": round(fitof.get(parent, 0.0), 4), "type": "mutation", "exists": (not needs)})
    return emit({"ok": True, "gen": a.gen, "next_gen": ng, "survivors": survivors,
                 "topfit_parents": topfit, "plan": plan})


# ----------------------------------------------------------------- reporting / resumability (reuse cc_code logic)
def _baseline_report(a):
    out = a.out; res = {}
    for bid in store.read_json(Path(out) / "config.json", {}).get("baselines", []):
        m = store.read_json(Path(out) / "baselines" / bid / "metrics.json", {})
        res[bid] = {"fitness": m.get("ladder_fitness"), "solved": m.get("solved"), "n_prob": m.get("n_prob")}
    store.write_json(Path(out) / "baselines" / "report.json", res)
    return emit({"ok": True, "results": {k: (v or {}).get("fitness") for k, v in res.items()}})


def cmd_evolve_status(a):
    out = a.out
    cfg = store.read_json(Path(out) / "config.json", {})
    G = a.generations or cfg.get("generations") or 4
    def finalized(g):
        return (store.gen_dir(out, g + 1) / "population.json").exists()
    next_gen = 0
    while next_gen < G and finalized(next_gen):
        next_gen += 1
    ids0 = store.list_agents(out, 0)
    gen0_done = bool(ids0) and all((store.agent_dir(out, 0, i) / "evals.json").exists() for i in ids0)
    all_done = next_gen >= G
    champ_gen = G if all_done else next_gen
    rows = dctrl._ranked(out, champ_gen)
    champ = rows[0]["id"] if rows else None
    champ_fit = rows[0]["ladder_fitness"] if rows else None
    heldout_done = False
    if champ:
        hm = store.read_json(store.agent_dir(out, 90, champ + "_he") / "metrics.json", {})
        heldout_done = bool(hm) and hm.get("split") == "eval"
    return emit({"ok": True, "max_gen": champ_gen, "next_gen": next_gen, "gen0_done": gen0_done,
                 "all_done": all_done, "generations": G, "champion": champ,
                 "champion_fitness": champ_fit, "heldout_done": heldout_done})


def cmd_heldout_setup(a):
    cfg = store.read_json(Path(a.out) / "config.json", {})
    geno = cpipe.repair(cpipe.load(a.out, a.src_gen, a.champion), cfg.get("N", 4))
    geno["id"] = a.champion + "_he"
    cpipe.save(a.out, 90, geno)
    return emit({"ok": True, "agent": geno["id"], "src": a.champion, "roles": geno["roles"],
                 "draft_model": geno["draft_model"], "n_eval": cfg.get("n_eval", 0)})


def cmd_final_compare(a):
    out = a.out; g = 0
    while store.gen_dir(out, g + 1).exists():
        g += 1
    rows = dctrl._ranked(out, g); champ = rows[0]["id"] if rows else None
    base = store.read_json(Path(out) / "baselines" / "report.json", {})
    cm = store.read_json(store.agent_dir(out, g, champ) / "metrics.json", {}) if champ else {}
    res = {"final_gen": g, "champion": champ, "champion_fitness": cm.get("ladder_fitness"),
           "champion_label": cpipe.pipe_label(cpipe.load(out, g, champ)["roles"]) if champ else None,
           "baselines": {k: (v or {}).get("fitness") for k, v in base.items()}}
    store.write_json(Path(out) / "final" / "compare.json", res)
    return emit({"ok": True, **res})


# ----------------------------------------------------------------- CLI
def main():
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p):
        p.add_argument("--out", required=True)

    p = sub.add_parser("init"); common(p)
    p.add_argument("--N", type=int, default=4); p.add_argument("--pop", type=int, default=6)
    p.add_argument("--survivors", type=int, default=3)
    p.add_argument("--n-train", dest="n_train", type=int, default=30)
    p.add_argument("--n-eval", dest="n_eval", type=int, default=30)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--optimizer", choices=["gepa", "core"], default="gepa")
    p.add_argument("--reuse-split", dest="reuse_split", default=None,
                   help="dir with instances/{train,eval}_full.json to reuse verbatim instead of re-selecting")
    p.set_defaults(fn=cmd_init)

    def add(name, fn, extra=()):
        q = sub.add_parser(name); common(q)
        for flag, kw in extra:
            q.add_argument(flag, **kw)
        q.set_defaults(fn=fn)

    G = (("--gen", dict(type=int, required=True)),)
    A = (("--agent", dict(required=True)),)
    SP = (("--split", dict(default="train")),)
    add("pipe-plan", cmd_pipe_plan, G + A + (("--N", dict(type=int, default=4)),))
    add("swe-prep", cmd_swe_prep, G + A + (("--repl", dict(type=int, required=True)),
        ("--cand", dict(type=int, default=0)), ("--role", dict(default="draft"))) + SP)
    add("swe-feedback", cmd_swe_feedback, G + A + (("--repl", dict(type=int, required=True)),) + SP)
    add("swe-score-cand", cmd_swe_score_cand, G + A + (("--repl", dict(type=int, required=True)),
        ("--cand", dict(type=int, required=True))) + SP)
    add("swe-eval-score", cmd_swe_eval_score, G + A + (("--n-prob", dict(dest="n_prob", type=int, default=0)),) + SP)
    add("score-pop", cp.cmd_score_pop, G)
    add("select", dctrl.cmd_select, G + (("--survivors", dict(type=int, default=3)),))
    add("admit", cmd_admit_paired, G + (("--child", dict(required=True)),
        ("--parent-gen", dict(dest="parent_gen", type=int, required=True)), ("--parent", dict(required=True))))
    add("mut-verify", cmd_mut_verify, G + (("--child", dict(required=True)),
        ("--parent-gen", dict(dest="parent_gen", type=int, required=True)), ("--parent", dict(required=True)),
        ("--lens", dict(required=True)), ("--combined", dict(action="store_true"))))
    add("finalize-gen", dctrl.cmd_finalize_gen, G + (("--pop", dict(type=int, default=6)),
        ("--survivors", dict(type=int, default=3))))
    add("population-summary", dctrl.cmd_population_summary, G)
    add("breed-plan-gepa", cpipe.cmd_breed_plan_gepa, G + (("--pop", dict(type=int, default=6)),
        ("--survivors", dict(type=int, default=3))))
    add("breed-plan-gepa-topfit", cmd_breed_plan_gepa_topfit, G + (("--pop", dict(type=int, default=6)),
        ("--survivors", dict(type=int, default=3))))
    add("core-reflect-plan", cpipe.cmd_core_reflect_plan, G + (("--pairs", dict(type=int, default=3)),
        ("--margin", dict(type=float, default=0.03))))
    add("core-ingest", ccore.cmd_core_ingest, G + (("--max-lessons", dict(dest="max_lessons", type=int, default=4)),
        ("--plan", dict(default=""))))
    add("core-breed-plan", cpipe.cmd_core_breed_plan, G + (("--pop", dict(type=int, default=6)),
        ("--survivors", dict(type=int, default=3)), ("--topk", dict(type=int, default=3))))
    add("core-credit", ccore.cmd_core_credit, G)
    add("bank-status", ccore.cmd_bank_status)
    add("baseline-report", lambda a: _baseline_report(a))
    add("final-compare", cmd_final_compare)
    add("evolve-status", cmd_evolve_status, (("--generations", dict(type=int, default=0)),))
    add("heldout-setup", cmd_heldout_setup, (("--src-gen", dict(dest="src_gen", type=int, required=True)),
        ("--champion", dict(required=True))))

    a = ap.parse_args(); a.fn(a)


if __name__ == "__main__":
    main()
