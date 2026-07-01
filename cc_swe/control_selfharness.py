"""cc_swe Self-Harness controller — instantiates Zhang et al. 2026 "Self-Harness" (arXiv:2606.09498) on
SWE-bench Verified with our Apptainer backend.

Self-Harness ≠ our prior GEPA runs: there a STRONGER external model (Sonnet) mutated Haiku's harness
(= the paper's Meta-Harness baseline). Here the SAME fixed model (Haiku) improves its OWN harness, via the
paper's three-stage loop:

  Weakness Mining  -> run h_t on the held-in split, cluster verifier-grounded failures into an evidence bundle
  Harness Proposal -> the SAME model proposes K diverse-yet-minimal bounded edits to declared harness surfaces
  Proposal Validate-> evaluate each candidate on BOTH held-in AND held-out; accept iff non-regressive
                      (d_in>=0 AND d_ho>=0 AND max(d_in,d_ho)>0); merge accepted edits -> h_{t+1}

This module owns ONLY the Self-Harness-specific bookkeeping (init/minimal-harness, genotype cloning, the
two-split acceptance gate, surface-disjoint merge, round status). SOLVING + scoring reuse control_swe verbatim
(swe-prep / swe-score-cand / swe-feedback / swe-eval-score) — they are split-aware and unchanged.

EDITABLE SURFACE ("full surface", per the user's choice). roles.json carries the structural role sequence
(<=N steps, step0=draft, write_test invariant); harness.json carries the richer surfaces the paper's best
edits actually used — a shared system_preamble, four instruction slots (bootstrap / verification /
failure_recovery), and a runtime_policy (max_tool_calls, redirect_after_calls, error_middleware). The runner
points each agent at harness.json so these injections take effect (the workflow JS cannot read files).

DUAL-SPLIT DIRS: control_swe's repl_/work artifacts are NOT split-namespaced, so a single agent dir cannot be
solved on two splits. Each harness/candidate therefore has two solving dirs: the canonical id (train) and
"<id>_ev" (a genotype-only clone, eval). The gate compares solved counts across both.
"""
import argparse
import copy
import json
import shutil
from pathlib import Path

from cc_decomp import store
from cc_pipe import control_pipe as cpipe
from cc_swe import control_swe as cs
from cc_swe import swe_harness as H

emit = cpipe.emit
ROLES_REP = ["draft", "write_test", "critique", "fix"]

# Minimal initial harness (paper Fig 3): structure is a SINGLE draft (== 1-shot Haiku). Self-Harness must
# build up its own scaffolding (write_test / critique / fix steps, runtime policy) from here. Prompts for all
# four role types are seeded so a later structural edit that introduces a role has a prompt to start from.
DEFAULT_HARNESS = {
    "system_preamble": "",
    "instructions": {"bootstrap": "", "verification": "", "failure_recovery": ""},
    "runtime_policy": {"max_tool_calls": 0, "redirect_after_calls": 0, "error_middleware": ""},
}
HARNESS_SURFACES = ["preamble", "bootstrap", "verification", "failure_recovery", "runtime"]
GENO_FILES = ["roles.json", "harness.json", "lineage.json"]


# ----------------------------------------------------------------- genotype dir helpers
def _adir(out, gen, gid):
    return cpipe._agent_dir(out, gen, gid)


def _read_harness(d):
    h = store.read_json(Path(d) / "harness.json", None)
    return h if isinstance(h, dict) else copy.deepcopy(DEFAULT_HARNESS)


def _surface_val(h, key):
    if key == "preamble":
        return (h.get("system_preamble") or "").strip()
    if key == "runtime":
        return json.dumps(h.get("runtime_policy") or {}, sort_keys=True)
    return ((h.get("instructions") or {}).get(key) or "").strip()


def _set_surface(h, key, src):
    if key == "preamble":
        h["system_preamble"] = src.get("system_preamble", "")
    elif key == "runtime":
        h["runtime_policy"] = copy.deepcopy(src.get("runtime_policy") or {})
    else:
        h.setdefault("instructions", {})[key] = (src.get("instructions") or {}).get(key, "")
    return h


def _clone_geno(src_dir, dst_dir):
    """Copy ONLY the genotype (roles.json + harness.json + lineage.json + prompts/), never solving artifacts."""
    src, dst = Path(src_dir), Path(dst_dir)
    dst.mkdir(parents=True, exist_ok=True)
    for f in GENO_FILES:
        if (src / f).exists():
            shutil.copy2(src / f, dst / f)
    (dst / "prompts").mkdir(parents=True, exist_ok=True)
    for r in ROLES_REP:
        p = src / "prompts" / f"{r}.md"
        if p.exists():
            shutil.copy2(p, dst / "prompts" / f"{r}.md")


def _roles(d):
    return store.read_json(Path(d) / "roles.json", {}).get("roles", [])


def _roles_valid(roles, N):
    if not roles or len(roles) > N or roles[0] != "draft":
        return False, "step0 must be draft and 1<=len<=N"
    if any(r not in ROLES_REP for r in roles):
        return False, "unknown role"
    if roles[-1] == "critique":
        return False, "no trailing critique"
    if "write_test" in roles:
        if roles.count("draft") != 1 or roles.count("write_test") != 1 or len(roles) < 2 or roles[1] != "write_test":
            return False, "write_test invariant: exactly one draft@0 + one write_test@1"
    return True, "ok"


def _solved(d, split):
    ev = store.read_json(Path(d) / f"evals_{split}.json", {})
    pg = ev.get("pooled_games")
    if pg is None:
        return None, None
    return int(sum(pg)), len(pg)


def _solved_split(out, gen, gid, split):
    """Solved count for a LOGICAL harness id on a split. train lives in the base dir <gid>; eval lives in the
    twin dir <gid>_ev (control_swe's repl_/work artifacts are not split-namespaced, so each split solves in its
    own agent dir). All eval reads in the gate / status / report must go through this."""
    sub = gid if split == "train" else f"{gid}_ev"
    return _solved(_adir(out, gen, sub), split)


# ----------------------------------------------------------------- commands
def cmd_sh_init(a):
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    if getattr(a, "reuse_split", None):
        train = store.read_json(Path(a.reuse_split) / "instances" / "train_full.json", [])
        ev = store.read_json(Path(a.reuse_split) / "instances" / "eval_full.json", [])
        if not train or not ev:
            raise RuntimeError(f"reuse-split {a.reuse_split} missing train/eval_full.json")
    else:
        probs = H.load_swe_verified(); sel = H.select_instances(probs)
        train, ev = H.split_train_eval(sel, a.n_train, a.n_eval, seed=a.seed)
    cs._write_instances(out, "train", train); cs._write_instances(out, "eval", ev)
    # h0: minimal harness (single draft), all four role prompts seeded from the SWE defaults.
    h0 = _adir(out, 0, "h0")
    store.write_json(h0 / "roles.json", {"roles": ["draft"], "draft_model": "haiku"})
    store.write_json(h0 / "harness.json", copy.deepcopy(DEFAULT_HARNESS))
    store.write_json(h0 / "lineage.json", {"round": 0, "origin": "sh_init", "parent": None,
                                           "surfaces_changed": [], "story": "minimal initial harness (single draft)"})
    for r in ROLES_REP:
        store.write_text(h0 / "prompts" / f"{r}.md", cs.SWE_PROMPTS[r])
    _clone_geno(h0, _adir(out, 0, "h0_ev"))
    cfg = {"out": str(out), "benchmark": "swe-verified", "mode": "self-harness", "N": a.N,
           "n_train": len(train), "n_eval": len(ev), "seed": a.seed, "rounds": a.rounds, "K": a.K,
           "proposer": a.proposer, "roles": ROLES_REP, "surfaces": ["roles"] + [f"prompt:{r}" for r in ROLES_REP] + HARNESS_SURFACES,
           "train_ids": [p["instance_id"] for p in train], "eval_ids": [p["instance_id"] for p in ev]}
    store.write_json(out / "config.json", cfg)
    return emit({"ok": True, "N": a.N, "n_train": len(train), "n_eval": len(ev), "rounds": a.rounds,
                 "K": a.K, "proposer": a.proposer, "h0": "h0"})


def cmd_sh_plan(a):
    """Return the role sequence verbatim (NO padding — h0 must stay a single draft) + per-split solved status."""
    d = _adir(a.out, a.gen, a.agent)
    roles = _roles(d) or ["draft"]
    dm = store.read_json(d / "roles.json", {}).get("draft_model", "haiku")
    tr_s, tr_n = _solved(d, "train"); ev_s, ev_n = _solved(d, "eval")
    fj = store.read_json(d / "failures.json", {})
    n_fail = sum(1 for x in fj.get("instances", []) if not x.get("resolved"))
    return emit({"ok": True, "agent": a.agent, "roles": roles, "draft_model": dm,
                 "label": cpipe.pipe_label(roles), "n_steps": len(roles),
                 "train_done": tr_s is not None, "eval_done": ev_s is not None,
                 "train_solved": tr_s, "eval_solved": ev_s,
                 "mined": (d / "evidence_bundle.json").exists(), "n_fail": n_fail})


def cmd_sh_clone(a):
    """Clone a genotype (roles/harness/prompts only) from (src-gen,src) into (dst-gen,dst). Used to make the
    eval-solving twin (<id>_ev) and to seed candidate dirs from the current harness before the proposer edits."""
    _clone_geno(_adir(a.out, a.src_gen, a.src), _adir(a.out, a.dst_gen, a.dst))
    return emit({"ok": True, "src": a.src, "dst": a.dst, "roles": _roles(_adir(a.out, a.dst_gen, a.dst))})


def _changed_surfaces(cur_d, cand_d):
    """Which declared surfaces does the candidate change vs the current harness?"""
    changed = []
    if _roles(cur_d) != _roles(cand_d):
        changed.append("roles")
    for r in ROLES_REP:
        ct = store.read_text(Path(cur_d) / "prompts" / f"{r}.md", "").strip()
        nt = store.read_text(Path(cand_d) / "prompts" / f"{r}.md", "").strip()
        if ct != nt:
            changed.append(f"prompt:{r}")
    hc, hn = _read_harness(cur_d), _read_harness(cand_d)
    for k in HARNESS_SURFACES:
        if _surface_val(hc, k) != _surface_val(hn, k):
            changed.append(k)
    return changed


def cmd_sh_diff(a):
    """Pre-solve check that a proposed candidate ACTUALLY edited >=1 surface and has a valid role sequence —
    so a no-op/invalid proposal is caught and retried BEFORE spending the (expensive) two-split solve budget."""
    out = a.out; cfg = store.read_json(Path(out) / "config.json", {}); N = cfg.get("N", 4)
    cur_d = _adir(out, a.cur_gen, a.cur); cand_d = _adir(out, a.cand_gen, a.cand)
    cand_exists = (cand_d / "roles.json").exists()
    surfaces = _changed_surfaces(cur_d, cand_d) if cand_exists else []
    roles_ok, roles_msg = _roles_valid(_roles(cand_d), N) if cand_exists else (False, "candidate not created")
    return emit({"ok": True, "cand": a.cand, "cand_exists": cand_exists, "changed": bool(surfaces),
                 "surfaces": surfaces, "roles_valid": roles_ok, "roles_msg": roles_msg, "roles": _roles(cand_d)})


def cmd_sh_gate(a):
    """Two-split non-regressive acceptance gate. d_in/d_ho are TRUE-resolution solved-count deltas of the
    candidate over the current harness on held-in (train) / held-out (eval). Accept iff d_in>=0 AND d_ho>=0
    AND max>0 (a candidate that only trades one split for the other is rejected). Also rejects edits that
    change no surface or produce an invalid role sequence."""
    out = a.out; cfg = store.read_json(Path(out) / "config.json", {}); N = cfg.get("N", 4)
    cur_d = _adir(out, a.cur_gen, a.cur); cand_d = _adir(out, a.cand_gen, a.cand)
    cs_tr, _ = _solved_split(out, a.cur_gen, a.cur, "train"); cs_ev, _ = _solved_split(out, a.cur_gen, a.cur, "eval")
    cd_tr, _ = _solved_split(out, a.cand_gen, a.cand, "train"); cd_ev, _ = _solved_split(out, a.cand_gen, a.cand, "eval")
    surfaces = _changed_surfaces(cur_d, cand_d)
    roles_ok, roles_msg = _roles_valid(_roles(cand_d), N)
    verdict = {"cur": a.cur, "cand": a.cand, "cur_train": cs_tr, "cur_eval": cs_ev,
               "cand_train": cd_tr, "cand_eval": cd_ev, "surfaces_changed": surfaces,
               "roles_valid": roles_ok, "roles_msg": roles_msg}
    if None in (cs_tr, cs_ev, cd_tr, cd_ev):
        verdict.update({"admitted": False, "d_in": None, "d_ho": None, "reason": "missing eval on a split"})
    elif not surfaces:
        verdict.update({"admitted": False, "d_in": 0, "d_ho": 0, "reason": "no surface changed (no-op)"})
    elif not roles_ok:
        verdict.update({"admitted": False, "d_in": None, "d_ho": None, "reason": f"invalid roles: {roles_msg}"})
    else:
        d_in = cd_tr - cs_tr; d_ho = cd_ev - cs_ev
        admit = (d_in >= 0 and d_ho >= 0 and max(d_in, d_ho) > 0)
        verdict.update({"admitted": bool(admit), "d_in": d_in, "d_ho": d_ho,
                        "reason": "non-regressive improvement" if admit else "regresses or no net gain"})
    store.write_json(cand_d / "verdict.json", verdict)
    return emit({"ok": True, **verdict})


def cmd_sh_merge(a):
    """Merge accepted candidates into h_{round+1}. Compose over DISJOINT surfaces: rank accepted by (d_in+d_ho)
    desc, and for each, copy each of its changed surfaces onto a fresh clone of the current harness only if that
    surface is still unclaimed (higher-ranked candidate wins a contested surface). With no accepted candidate,
    h_{round+1} is the current harness carried forward unchanged. Also writes the eval twin <next>_ev."""
    out = a.out; ng = a.round + 1; nid = f"h{ng}"
    cur_d = _adir(out, a.cur_gen, a.cur)
    next_d = _adir(out, ng, nid)
    _clone_geno(cur_d, next_d)                       # start from current harness
    accepted = [c for c in (a.accepted or "").split(",") if c]
    ranked = []
    for c in accepted:
        v = store.read_json(_adir(out, a.cand_gen, c) / "verdict.json", {})
        if v.get("admitted"):
            ranked.append((v.get("d_in", 0) + v.get("d_ho", 0), c, v))
    ranked.sort(key=lambda x: -x[0])
    claimed, taken = set(), []
    nh = _read_harness(next_d)
    for _, c, v in ranked:
        cd = _adir(out, a.cand_gen, c)
        for surf in v.get("surfaces_changed", []):
            if surf in claimed:
                continue
            claimed.add(surf)
            taken.append({"surface": surf, "from": c})
            if surf == "roles":
                store.write_json(next_d / "roles.json", store.read_json(cd / "roles.json", {}))
            elif surf.startswith("prompt:"):
                r = surf.split(":", 1)[1]
                store.write_text(next_d / "prompts" / f"{r}.md", store.read_text(cd / "prompts" / f"{r}.md", ""))
            else:
                _set_surface(nh, surf, _read_harness(cd))
    store.write_json(next_d / "harness.json", nh)
    store.write_json(next_d / "lineage.json", {"round": ng, "origin": "sh_merge", "parent": a.cur,
                                               "surfaces_changed": [t["surface"] for t in taken],
                                               "merged_from": taken,
                                               "n_accepted": len(ranked)})
    _clone_geno(next_d, _adir(out, ng, nid + "_ev"))
    return emit({"ok": True, "round": a.round, "next_gen": ng, "next": nid,
                 "n_accepted": len(ranked), "surfaces_taken": taken, "roles": _roles(next_d)})


def cmd_sh_status(a):
    """Round/lineage progress probe for the resumable workflow. Finds the highest round R with a harness h_R,
    reports whether it is solved on both splits and whether the whole run is done (R == rounds AND its held-out
    eval is recorded)."""
    out = a.out; cfg = store.read_json(Path(out) / "config.json", {})
    rounds = a.rounds or cfg.get("rounds", 3)
    r = 0
    while (_adir(out, r + 1, f"h{r + 1}") / "roles.json").exists():
        r += 1
    cur = f"h{r}"; cur_d = _adir(out, r, cur)
    tr_s, _ = _solved_split(out, r, cur, "train"); ev_s, _ = _solved_split(out, r, cur, "eval")
    done = (r >= rounds) and (tr_s is not None) and (ev_s is not None)
    return emit({"ok": True, "round": r, "cur": cur, "cur_gen": r, "rounds": rounds,
                 "train_done": tr_s is not None, "eval_done": ev_s is not None,
                 "train_solved": tr_s, "eval_solved": ev_s, "done": done,
                 "roles": _roles(cur_d), "label": cpipe.pipe_label(_roles(cur_d) or ["draft"])})


def cmd_sh_report(a):
    """Final lineage table: each round's harness shape + held-in/held-out solved, vs the reference bars."""
    out = a.out; cfg = store.read_json(Path(out) / "config.json", {})
    rounds = cfg.get("rounds", 3); n_tr = cfg.get("n_train"); n_ev = cfg.get("n_eval")
    lineage = []
    r = 0
    while True:
        d = _adir(out, r, f"h{r}")
        if not (d / "roles.json").exists():
            break
        tr_s, _ = _solved_split(out, r, f"h{r}", "train"); ev_s, _ = _solved_split(out, r, f"h{r}", "eval")
        lin = store.read_json(d / "lineage.json", {})
        lineage.append({"round": r, "id": f"h{r}", "label": cpipe.pipe_label(_roles(d) or ["draft"]),
                        "roles": _roles(d), "train_solved": tr_s, "eval_solved": ev_s,
                        "surfaces_changed": lin.get("surfaces_changed", [])})
        r += 1
    base = store.read_json(Path(out) / "baselines" / "report.json", {})
    res = {"rounds": rounds, "n_train": n_tr, "n_eval": n_ev, "lineage": lineage,
           "baselines": {k: (v or {}).get("fitness") for k, v in base.items()}}
    store.write_json(Path(out) / "final" / "sh_report.json", res)
    return emit({"ok": True, **res})


def main():
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)

    def add(name, fn, args=()):
        q = sub.add_parser(name); q.add_argument("--out", required=True)
        for flag, kw in args:
            q.add_argument(flag, **kw)
        q.set_defaults(fn=fn)

    add("sh-init", cmd_sh_init, (("--N", dict(type=int, default=4)), ("--n-train", dict(dest="n_train", type=int, default=28)),
        ("--n-eval", dict(dest="n_eval", type=int, default=27)), ("--seed", dict(type=int, default=0)),
        ("--rounds", dict(type=int, default=3)), ("--K", dict(type=int, default=3)),
        ("--proposer", dict(default="haiku")), ("--reuse-split", dict(dest="reuse_split", default=None))))
    add("sh-plan", cmd_sh_plan, (("--gen", dict(type=int, required=True)), ("--agent", dict(required=True))))
    add("sh-clone", cmd_sh_clone, (("--src-gen", dict(dest="src_gen", type=int, required=True)), ("--src", dict(required=True)),
        ("--dst-gen", dict(dest="dst_gen", type=int, required=True)), ("--dst", dict(required=True))))
    add("sh-diff", cmd_sh_diff, (("--cur-gen", dict(dest="cur_gen", type=int, required=True)), ("--cur", dict(required=True)),
        ("--cand-gen", dict(dest="cand_gen", type=int, required=True)), ("--cand", dict(required=True))))
    add("sh-gate", cmd_sh_gate, (("--cur-gen", dict(dest="cur_gen", type=int, required=True)), ("--cur", dict(required=True)),
        ("--cand-gen", dict(dest="cand_gen", type=int, required=True)), ("--cand", dict(required=True))))
    add("sh-merge", cmd_sh_merge, (("--round", dict(type=int, required=True)), ("--cur-gen", dict(dest="cur_gen", type=int, required=True)),
        ("--cur", dict(required=True)), ("--cand-gen", dict(dest="cand_gen", type=int, required=True)),
        ("--accepted", dict(default=""))))
    add("sh-status", cmd_sh_status, (("--rounds", dict(type=int, default=0)),))
    add("sh-report", cmd_sh_report)

    a = ap.parse_args(); a.fn(a)


if __name__ == "__main__":
    main()
