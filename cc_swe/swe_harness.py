"""Apptainer-based execution + grading for SWE-bench Verified (the cc_swe analogue of cc_code.code_harness).

No Docker daemon: we run the OFFICIAL per-instance SWE-bench eval images via Apptainer (rootless). Each image
(`swebench/sweb.eval.x86_64.<id>`) ships the repo checked out at base_commit + a `testbed` conda env with deps
pre-installed, so we skip all environment building. We:
  1. apply the MODEL patch to /testbed (root-owned -> needs --fakeroot),
  2. run swebench's own eval_script (resets test files, applies the gold test_patch, runs FAIL_TO_PASS+PASS_TO_PASS
     between `>>>>> Start/End Test Output` markers),
  3. grade with swebench.harness.grading.get_eval_report (official per-repo log parsers) -> resolved bool.

DockerHub name gotcha: instance_id '__' -> image '_1776_' (DockerHub disallows double underscore).
Everything lives on /hdd (local-ssd is full): SIFs, work dirs, apptainer cache/tmp.
"""
import json
import os
import subprocess
from pathlib import Path

os.environ.setdefault("APPTAINER_CACHEDIR", "/hdd/pk669/apptainer/cache")
os.environ.setdefault("APPTAINER_TMPDIR", "/hdd/pk669/apptainer/tmp")
os.environ.setdefault("HF_HOME", "/local-ssd/pk669/.cache/huggingface")

SIF_DIR = Path(os.environ.get("CC_SWE_SIF", "/hdd/pk669/swe/sif"))
IMAGE_NS = "swebench/sweb.eval.x86_64."
DEFAULT_TIMEOUT = int(os.environ.get("CC_SWE_TIMEOUT", "1200"))  # seconds for the test run
# Apptainer run flags. Rootless WITHOUT fakeroot (user not in /etc/subuid): the SWE-bench images ship
# /testbed world-writable (777) and the conda env importable, so --writable-tmpfs (ephemeral overlay for
# patch/pip/pytest writes) + --containall (isolation) is enough. Override via CC_SWE_APPTAINER_FLAGS.
RUN_FLAGS = os.environ.get("CC_SWE_APPTAINER_FLAGS", "--writable-tmpfs --containall").split()


def _dec(x):
    """Decode subprocess output that may be bytes (CPython returns bytes in TimeoutExpired even with text=True)."""
    if x is None:
        return ""
    return x.decode("utf-8", "replace") if isinstance(x, (bytes, bytearray)) else x


def image_ref(instance_id):
    return f"docker://{IMAGE_NS}{instance_id.replace('__', '_1776_')}:latest"


def sif_path(instance_id):
    return SIF_DIR / f"{instance_id}.sif"


def ensure_image(instance_id, force=False):
    """Pull the per-instance eval image to a .sif on /hdd (idempotent). Returns the sif Path."""
    sp = sif_path(instance_id)
    sp.parent.mkdir(parents=True, exist_ok=True)
    if sp.exists() and not force:
        return sp
    r = subprocess.run(["apptainer", "pull", "--force", str(sp), image_ref(instance_id)],
                       capture_output=True, text=True, timeout=3600)
    if not sp.exists():
        raise RuntimeError(f"pull failed for {instance_id}: {r.stderr[-500:]}")
    return sp


def _test_spec(instance):
    from swebench.harness.test_spec.test_spec import make_test_spec
    return make_test_spec(instance)


def _run_script(model_patch):
    """Container script: apply the model patch (git apply, then patch --fuzz fallback) then run eval.sh."""
    return (
        "#!/bin/bash\n"
        "set -uo pipefail\n"
        "cd /testbed\n"
        "git config --global --add safe.directory /testbed 2>/dev/null || true\n"
        "if [ -s /swe_io/model.patch ]; then\n"
        "  if git apply --verbose /swe_io/model.patch 2>/swe_io/apply.err ; then echo '>>>>> Applied Patch';\n"
        "  elif patch --batch --fuzz=5 -p1 < /swe_io/model.patch 2>>/swe_io/apply.err ; then echo '>>>>> Applied Patch (fuzz)';\n"
        "  else echo '>>>>> Patch Apply Failed'; fi\n"
        "else echo '>>>>> Applied Patch (empty)'; fi\n"
        "bash /swe_io/eval.sh\n"
    )


def run_instance_eval(instance, model_patch, work_dir, timeout=DEFAULT_TIMEOUT, run_flags=None):
    """Apply model_patch, run the official eval, grade. Returns dict with resolved/applied/feedback/log_path."""
    ts = _test_spec(instance)
    iid = instance["instance_id"]
    wd = Path(work_dir); wd.mkdir(parents=True, exist_ok=True)
    (wd / "eval.sh").write_text(ts.eval_script)
    (wd / "model.patch").write_text(model_patch or "")
    (wd / "run.sh").write_text(_run_script(model_patch))
    sp = ensure_image(iid)
    flags = run_flags if run_flags is not None else RUN_FLAGS
    cmd = ["apptainer", "exec", *flags, "--bind", f"{wd}:/swe_io", str(sp), "bash", "/swe_io/run.sh"]
    logp = wd / "run.log"
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        log = r.stdout + "\n" + r.stderr
    except subprocess.TimeoutExpired as e:
        log = _dec(e.stdout) + "\n[CC_SWE TIMEOUT]\n" + _dec(e.stderr)
    logp.write_text(log)
    applied = (">>>>> Applied Patch" in log) and (">>>>> Patch Apply Failed" not in log)
    resolved, report = _grade(ts, iid, model_patch, logp)
    fb = _feedback(log, instance, resolved, applied)
    return {"instance_id": iid, "resolved": bool(resolved), "applied": bool(applied),
            "feedback": fb, "log_path": str(logp), "report": report}


_DEPLOY_SCRIPT = r'''#!/bin/bash
set -uo pipefail
cd /testbed
git config --global --add safe.directory /testbed 2>/dev/null || true
if [ -s /swe_io/model.patch ]; then
  git apply --verbose /swe_io/model.patch 2>/swe_io/apply.err && echo ">>>>> Applied Patch" \
    || (patch --batch --fuzz=5 -p1 < /swe_io/model.patch 2>>/swe_io/apply.err && echo ">>>>> Applied Patch (fuzz)") \
    || echo ">>>>> Patch Apply Failed"
else echo ">>>>> Applied Patch (empty)"; fi
source /opt/miniconda3/bin/activate testbed 2>/dev/null || true
python -m pip install -e . -q 2>/dev/null || true
if [ -s /swe_io/repro.py ]; then
  echo ">>>>> REPRO START"; python -m pytest -x -q -p no:cacheprovider /swe_io/repro.py; echo ">>>>> REPRO_RC=$?"
fi
if [ -s /swe_io/regression.txt ]; then
  echo ">>>>> REG START"; python -m pytest -q --tb=no -p no:cacheprovider $(cat /swe_io/regression.txt); echo ">>>>> REG_RC=$?"
fi
'''


def run_deployable(instance, model_patch, repro_test=None, work_dir=None, regression_sample=8,
                   timeout=600, run_flags=None):
    """DEPLOYABLE keep-best / critique signal (NO hidden FAIL_TO_PASS): does the patch apply, does the agent's
    reproduction test pass, and does a sample of PASS_TO_PASS still pass (regression)? Returns a 0..1 score +
    feedback. score = applied gate * (0.55*repro_pass + 0.45*regression_frac)  (repro_frac=neutral 1.0 if no repro)."""
    import json as _json
    iid = instance["instance_id"]
    wd = Path(work_dir or f"/hdd/pk669/swe/work/{iid}_deploy"); wd.mkdir(parents=True, exist_ok=True)
    (wd / "model.patch").write_text(model_patch or "")
    (wd / "repro.py").write_text(repro_test or "")
    p2p = instance.get("PASS_TO_PASS", [])
    if isinstance(p2p, str):
        try: p2p = _json.loads(p2p)
        except Exception: p2p = []
    sample = list(p2p)[:regression_sample]
    (wd / "regression.txt").write_text(" ".join(sample))
    (wd / "deploy.sh").write_text(_DEPLOY_SCRIPT)
    sp = ensure_image(iid)
    flags = run_flags if run_flags is not None else RUN_FLAGS
    cmd = ["apptainer", "exec", *flags, "--bind", f"{wd}:/swe_io", str(sp), "bash", "/swe_io/deploy.sh"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        log = r.stdout + "\n" + r.stderr
    except subprocess.TimeoutExpired as e:
        log = _dec(e.stdout) + "\n[CC_SWE TIMEOUT]\n" + _dec(e.stderr)
    (wd / "deploy.log").write_text(log)
    applied = (">>>>> Applied Patch" in log) and (">>>>> Patch Apply Failed" not in log)
    repro_pass = ("REPRO_RC=0" in log) if repro_test else None
    reg_frac = _parse_reg(log) if sample else 1.0
    repro_term = (1.0 if repro_pass else 0.0) if repro_test else 1.0
    score = (0.55 * repro_term + 0.45 * reg_frac) if applied else 0.0
    fb = _deploy_feedback(log, applied, repro_pass, reg_frac, sample)
    return {"instance_id": iid, "applied": applied, "repro_pass": repro_pass,
            "regression_frac": reg_frac, "score": round(score, 4), "feedback": fb, "log_path": str(wd / "deploy.log")}


def _deploy_feedback(log, applied, repro_pass, reg_frac, sample, max_len=1800):
    """ACTIONABLE feedback for the critique/fix step from the deployable run (NO hidden FAIL_TO_PASS):
    not just the score, but WHY it failed — the patch-apply error, the reproduction test's traceback,
    and which sampled regression tests broke. This is the diagnostic the refine loop edits against."""
    head = f"applied={applied} repro_pass={repro_pass} regression={reg_frac:.2f} ({len(sample)} regression tests)."
    if not applied:
        err = log.split(">>>>> Patch Apply Failed", 1)[-1] if ">>>>> Patch Apply Failed" in log else log
        return (head + " PATCH DID NOT APPLY — fix the diff so it applies cleanly.\n" + err.strip()[-500:])[:max_len]
    parts = [head]
    # reproduction test: surface the assertion/traceback when it failed (repro runs with -q, full tb)
    if repro_pass is False and ">>>>> REPRO START" in log:
        seg = log.split(">>>>> REPRO START", 1)[1].split(">>>>> REPRO_RC", 1)[0].strip()
        parts.append("REPRODUCTION TEST STILL FAILS — its output:\n" + "\n".join(seg.splitlines()[-25:]))
    # regression: name the specific sampled tests that broke (reg runs with --tb=no -> short FAILED lines)
    if reg_frac < 1.0 and ">>>>> REG START" in log:
        seg = log.split(">>>>> REG START", 1)[1].split(">>>>> REG_RC", 1)[0]
        broke = [ln.strip() for ln in seg.splitlines() if ("FAILED" in ln or "ERROR" in ln)][:10]
        if broke:
            parts.append("REGRESSION — your change broke these previously-passing tests (fix without reverting the bug fix):\n"
                         + "\n".join(broke))
    if repro_pass and reg_frac >= 1.0:
        parts.append("Deployable signal clean (repro passes, no regressions) — but hidden acceptance tests may still fail; "
                     "re-examine whether the reproduction test truly captures the issue's required behavior.")
    return "\n".join(parts)[:max_len]


def _parse_reg(log):
    """Parse pytest summary for the regression sample -> fraction passed."""
    import re
    seg = log.split(">>>>> REG START", 1)[-1]
    p = re.search(r"(\d+) passed", seg); f = re.search(r"(\d+) failed", seg); e = re.search(r"(\d+) error", seg)
    np_ = int(p.group(1)) if p else 0; nf = int(f.group(1)) if f else 0; ne = int(e.group(1)) if e else 0
    tot = np_ + nf + ne
    return (np_ / tot) if tot else (1.0 if "REG_RC=0" in seg else 0.0)


def _grade(ts, iid, model_patch, log_path):
    """Use swebench's official grader. Returns (resolved_bool, report_dict)."""
    from swebench.harness.grading import get_eval_report
    from swebench.harness.constants import KEY_INSTANCE_ID, KEY_PREDICTION, KEY_MODEL
    pred = {KEY_INSTANCE_ID: iid, KEY_PREDICTION: model_patch or "", KEY_MODEL: "cc_swe"}
    try:
        report = get_eval_report(ts, pred, str(log_path), include_tests_status=True)
        return bool(report.get(iid, {}).get("resolved", False)), report.get(iid, {})
    except Exception as e:
        return False, {"error": f"{type(e).__name__}: {e}"}


def _feedback(log, instance, resolved, applied, max_len=1500):
    """Short feedback for the critique/revise step: applied?, which FAIL_TO_PASS failed, last error lines."""
    if not applied:
        err = log.split(">>>>> Patch Apply Failed", 1)[-1][:400]
        return f"PATCH DID NOT APPLY. {err.strip()[:400]}"
    if resolved:
        return "All target tests pass (resolved)."
    # pull the test-output section + failing lines
    seg = log
    if ">>>>> Start Test Output" in log:
        seg = log.split(">>>>> Start Test Output", 1)[1].split(">>>>> End Test Output", 1)[0]
    fails = [ln for ln in seg.splitlines() if ("FAILED" in ln or "ERROR" in ln or "Error" in ln)][:8]
    tail = "\n".join(seg.strip().splitlines()[-15:])
    return (f"NOT resolved. Failing/erroring lines:\n" + "\n".join(fails) + f"\n--- tail ---\n{tail}")[:max_len]


# ---------------------------------------------------------------- dataset helpers
def load_swe_verified():
    from datasets import load_dataset
    return list(load_dataset("princeton-nlp/SWE-bench_Verified", split="test"))


# NB: psf/requests excluded — its hidden tests are httpbin/network-dependent (flaky + slow, ~18 min/grade),
# which injects ~3% grading noise. Removed for a cleaner, reproducible resolution signal.
LIGHT_REPOS = {"pallets/flask", "pylint-dev/pylint", "sphinx-doc/sphinx",
               "pytest-dev/pytest", "sympy/sympy", "mwaskom/seaborn", "pydata/xarray"}


def select_instances(probs, repos=None, difficulties=("<15 min fix", "15 min - 1 hour"), limit=None):
    repos = repos or LIGHT_REPOS
    out = [p for p in probs if p["repo"] in repos and (not difficulties or p.get("difficulty") in difficulties)]
    out.sort(key=lambda p: p["instance_id"])
    return out[:limit] if limit else out


def split_train_eval(insts, n_train, n_eval, seed=0):
    """Deterministic disjoint split stratified by (repo, difficulty) for balance."""
    import random
    from collections import defaultdict
    rng = random.Random(seed)
    pool = sorted(insts, key=lambda p: p["instance_id"]); rng.shuffle(pool)
    by = defaultdict(list)
    for p in pool:
        by[(p["repo"], p.get("difficulty"))].append(p)
    keys = sorted(by); train, ev = [], []
    i = 0
    while (len(train) < n_train or len(ev) < n_eval) and any(by[k] for k in keys):
        k = keys[i % len(keys)]; i += 1
        if not by[k]:
            continue
        p = by[k].pop()
        if len(train) < n_train:
            train.append(p)
        elif len(ev) < n_eval:
            ev.append(p)
    return train, ev


if __name__ == "__main__":
    import sys
    probs = load_swe_verified()
    sel = select_instances(probs)
    print(f"SWE-bench Verified: {len(probs)} total; {len(sel)} light+easy")
    for p in sel[:5]:
        print(" ", p["instance_id"], p["repo"], p["difficulty"], "| image:", image_ref(p["instance_id"]))
