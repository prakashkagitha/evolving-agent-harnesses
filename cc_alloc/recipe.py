"""The budget-constrained allocation genotype (a "recipe") + its deterministic interpreter helpers.

A recipe says how to spend exactly B LLM calls to write ONE BattleSnake bot:
    alloc = {n_draft, n_spec, do_merge in {0,1}, n_revise}   with sum == B
    concerns  = ordered subset of the fixed specialist menu (the n_spec specialists)
    draft_prompt = the generator prompt (the 2nd evolvable lever)

Fixed execution order (so the interpreter is simple/robust): n_draft monolithic drafts (parallel) ->
n_spec specialist coders (+1 merge if do_merge) -> n_revise sequential revisions on the best-so-far ->
final bot = best clean-scoring candidate. Every candidate costs exactly B generative calls.

This module is deterministic (no LLM, no network): genotype I/O, validity/repair (budget preserved),
seed recipes spanning the space, and assembly of the decomposition candidate from specialist files
(reusing the cc_decomp harness scaffold). All scoring lives in control_alloc.
"""
import json
from pathlib import Path

from cc_decomp import harness, store

MENU = store.SPECIALIST_MENU                      # [space_control, combat, food, endgame, hazard]
DEFAULT_B = 8


def alloc_sum(a):
    return int(a.get("n_draft", 0)) + int(a.get("n_spec", 0)) + int(bool(a.get("do_merge", 0))) + int(a.get("n_revise", 0))


def repair(geno, B=DEFAULT_B):
    """Coerce a genotype to a VALID budget-B allocation, preserving intent as much as possible.
    Rules: sum==B; 0<=n_spec<=5; do_merge=1 requires n_spec>=1; at least one base-bot producer
    (n_draft>=1 OR (n_spec>=1 and do_merge)); concerns has >= n_spec distinct menu entries."""
    a = dict(geno.get("alloc", {}))
    n_draft = max(0, int(a.get("n_draft", 0)))
    n_spec = max(0, min(5, int(a.get("n_spec", 0))))
    do_merge = 1 if int(a.get("do_merge", 0)) and n_spec >= 1 else 0
    n_revise = max(0, int(a.get("n_revise", 0)))

    # ensure a base producer exists
    if n_draft == 0 and not (n_spec >= 1 and do_merge):
        if n_spec >= 1:
            do_merge = 1
        else:
            n_draft = 1

    # normalise the sum to B by adjusting n_revise first, then n_draft
    total = n_draft + n_spec + do_merge + n_revise
    if total > B:
        cut = total - B
        take = min(cut, n_revise); n_revise -= take; cut -= take
        if cut:
            take = min(cut, max(0, n_draft - (1 if not (n_spec >= 1 and do_merge) else 0)))
            n_draft -= take; cut -= take
        if cut:                                   # last resort: drop specialists (and merge)
            take = min(cut, n_spec); n_spec -= take; cut -= take
            if n_spec == 0:
                do_merge = 0
            if n_draft == 0 and not (n_spec >= 1 and do_merge):
                n_draft = 1
    elif total < B:
        n_revise += (B - total)

    # concerns: distinct menu entries, at least n_spec of them
    seen, concerns = set(), []
    for c in geno.get("concerns", []):
        if c in MENU and c not in seen:
            seen.add(c); concerns.append(c)
    for c in MENU:
        if len(concerns) >= max(n_spec, 1):
            break
        if c not in seen:
            seen.add(c); concerns.append(c)

    a2 = {"n_draft": n_draft, "n_spec": n_spec, "do_merge": do_merge, "n_revise": n_revise}
    return {"id": geno.get("id"), "alloc": a2, "concerns": concerns,
            "draft_prompt": (geno.get("draft_prompt") or DEFAULT_DRAFT_PROMPT).strip(),
            "lineage": geno.get("lineage", {})}


def is_valid(geno, B=DEFAULT_B):
    a = geno.get("alloc", {})
    if alloc_sum(a) != B:
        return False
    if not (0 <= int(a.get("n_spec", 0)) <= 5):
        return False
    if int(a.get("do_merge", 0)) and int(a.get("n_spec", 0)) < 1:
        return False
    if int(a.get("n_draft", 0)) < 1 and not (int(a.get("n_spec", 0)) >= 1 and int(a.get("do_merge", 0))):
        return False
    if len(geno.get("concerns", [])) < int(a.get("n_spec", 0)):
        return False
    return True


def alloc_label(a):
    return f"D{a['n_draft']}·S{a['n_spec']}{'+M' if a.get('do_merge') else ''}·R{a['n_revise']}"


# ----------------------------------------------------------------- genotype I/O (own layout)
def recipe_path(out, gen, aid):
    return store.agent_dir(out, gen, aid) / "recipe.json"


def load(out, gen, aid):
    d = store.read_json(recipe_path(out, gen, aid), {})
    d.setdefault("id", aid)
    return d


def save(out, gen, geno):
    store.write_json(recipe_path(out, gen, geno["id"]), geno)
    store.write_json(store.agent_dir(out, gen, geno["id"]) / "lineage.json", geno.get("lineage", {}))


# ----------------------------------------------------------------- decomposition-candidate assembly
def assemble_decomp_candidate(spec_dir, concerns, do_merge, dest_path):
    """Build a decomposition bot (main.py) from the specialist files in spec_dir, reusing the
    cc_decomp harness scaffold. referee = planner_merge (if do_merge and _referee.py present) else
    weighted_vote. Returns (ok, loaded_concerns)."""
    spec_dir = Path(spec_dir)
    spec_b64, loaded = {}, []
    for name in concerns:
        f = spec_dir / f"{name}.py"
        src = harness.clean_code(store.read_text(f, "")) if f.exists() else ""
        if src.strip():
            store.write_text(f, src)
            spec_b64[name] = harness._b64(src)
            loaded.append(name)
    if not spec_b64:
        return False, []
    merge_b64 = ""
    policy = "weighted_vote"
    if do_merge:
        msrc = harness.clean_code(store.read_text(spec_dir / "_referee.py", ""))
        if msrc.strip():
            store.write_text(spec_dir / "_referee.py", msrc)
            merge_b64 = harness._b64(msrc)
            policy = "planner_merge"
    code = harness._SCAFFOLD.format(aid="recipe", gen=0, policy=policy, specs=loaded,
                                    tester=False, rounds=0, spec_b64=spec_b64,
                                    priority=loaded, merge_b64=merge_b64)
    store.write_text(Path(dest_path), code)
    return True, loaded


# ----------------------------------------------------------------- prompts (text injected to agents)
DEFAULT_DRAFT_PROMPT = (
    "Write the strongest single-file BattleSnake bot you can: combine flood-fill space control, "
    "head-to-head avoidance (and opportunism when strictly longer), and measured food/health "
    "management into one fast, crash-proof move() function."
)


# ----------------------------------------------------------------- seed recipes (span the space)
def _g(aid, n_draft, n_spec, do_merge, n_revise, concerns, B=DEFAULT_B, prompt=None):
    return repair({"id": aid,
                   "alloc": {"n_draft": n_draft, "n_spec": n_spec, "do_merge": do_merge, "n_revise": n_revise},
                   "concerns": concerns, "draft_prompt": prompt or DEFAULT_DRAFT_PROMPT,
                   "lineage": {"parent_id": None, "origin": "seed", "lens": None,
                               "changed_components": [], "diff": ""}}, B)


def seed_recipes(B=DEFAULT_B):
    """A diverse seed population spanning best-of-B, revision chains, decomposition, and hybrids,
    plus a couple of deliberately lopsided ones (headroom)."""
    return [
        _g("best_of_b", B, 0, 0, 0, [], B),                                # pure best-of-B baseline shape
        _g("revise_chain", 1, 0, 0, B - 1, [], B),                         # 1 draft + (B-1) revisions
        _g("decomp_full", 0, 5, 1, max(0, B - 6), MENU, B),                # 5 specialists + merge + revises
        _g("decomp_lite", 0, 3, 1, max(0, B - 4), ["space_control", "combat", "food"], B),
        _g("draft_revise", B // 2, 0, 0, B - B // 2, [], B),               # half drafts, half revisions
        _g("hybrid_mixed", 2, 3, 1, max(0, B - 6), ["space_control", "combat", "food"], B),
        _g("spec_no_revise", max(1, B - 6), 5, 1, 0, MENU, B),             # specialists + merge, no revision
        _g("draft_heavy", max(1, B - 2), 0, 0, min(2, B - 1), [], B),      # mostly drafts, light polish
    ]


SIMPLE_BOT_CONTRACT = harness.SIMPLE_BOT_CONTRACT
SPECIALIST_CONTRACT = harness.SPECIALIST_CONTRACT
REFEREE_CONTRACT = harness.REFEREE_CONTRACT
