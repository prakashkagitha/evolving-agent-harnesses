# CORE — Contrastive Reflection as a drop-in alternative to GEPA

This package evolves the **exact same** nested multi-agent BattleSnake harness as [`cc_decomp`](../cc_decomp),
but replaces the GEPA-style breeder with **CORE** ([*Contrastive Reflection Enables Rapid Improvements
in Reasoning*](https://arxiv.org/abs/2605.28742), [code](https://github.com/LinasNas/core-reasoning)).
Everything else — the genotype (`planner_prompt` + `decomposition`), the harness assembly, the fixed
opponent ladder, the ablations, the ladder-anchored scoring, and the **verified-acceptance gate**
(paired common-seed 95 % CI) — is reused verbatim from `cc_decomp`, so the GEPA-vs-CORE comparison is
apples-to-apples: **only the way new harnesses are proposed differs.**

## Why CORE fits a tournament

GEPA reflects on **one** harness's failures through four fixed lenses and mutates directly; its
reflection is *stateless* across generations. CORE's signal is **contrastive** — and a tournament
*natively* emits the pairs it needs: every generation has winners and losers on the same fixed ladder.

| | GEPA (`cc_decomp`) | CORE (`cc_core`) |
|---|---|---|
| Reflection input | one parent's per-rung weaknesses | **winner-vs-loser** harness pairs |
| Reflection output | a direct mutation (4 lenses) | compact NL **lessons** (`specific` / `meta`) |
| Memory | none (stateless lenses) | a **persistent lesson bank**; utility-weighted retrieval (cosine × Beta-utility + UCB); near-duplicates merged (`support`) |
| Mutation | lens guide | conditioned on the **top-K lessons** retrieved for the parent's weakness |
| Credit | — | admitted → win / rejected → use updates lesson utility → drives UCB next gen |

The bank **compounds**: a lesson distilled in gen 1 can be retrieved to fix a different parent in gen 4,
and its verified track record (wins/uses) raises its retrieval priority. That accumulation is the
distinctive CORE mechanism the paper contrasts against GEPA.

## The CORE breeding cycle (per generation)

```
select survivors                                   (reused from cc_decomp)
core-reflect-plan   → winner/loser contrastive pairs from the scored generation
  ↳ Sonnet analyst reads both genotypes+metrics, distils MAX_LESSONS lessons per pair → JSON
core-ingest         → add lessons to the bank (dedup → support++), snapshot
core-breed-plan     → per offspring: retrieve top-K lessons for the parent's weakness → breed_context.json
  ↳ Sonnet mutation applies the retrieved lesson(s): one incremental single-aspect edit
runHarness + score + admit                         (reused; identical verified-acceptance gate)
core-credit         → admitted→win / rejected→use on every lesson the offspring used
finalize-gen                                       (reused)
```

## Layout

```
cc_core/
  bank.py       the LESSON BANK — deterministic domain embedding, dedup, utility, UCB retrieval, credit
  reflect.py    contrastive-pair formation, weakness-profile text, lenient lesson-JSON parser
  control.py    CLI: reuses cc_decomp's controller for everything shared + adds the 5 CORE commands
  workflow.js   the Claude Dynamic Workflow (same scaffold as cc_decomp; CORE Evolve phase)
  analysis.py   reuses cc_decomp analysis + adds the lesson-bank trajectory & per-lesson attribution
  _mocktest.py  token-free end-to-end test of the whole cycle + a bank unit test
```

## Faithful simplification

The reference CORE uses a neural sentence embedder; we use a **deterministic, dependency-free domain
embedding** (a curated BattleSnake-strategy vocabulary + hashed buckets for OOV tokens, cosine
retrieval). The retrieval *mechanism* (similarity + Beta-utility + UCB + dedup) is identical; only the
embedding backend is local. This keeps the bank reproducible and token-free (it powers the mock test)
and matches the repo's stdlib + numpy footprint.

## Run it

```bash
# token-free end-to-end test of the CORE controller + bank (no model calls)
python3 -m cc_core._mocktest
```

Reproducing the full LLM evolution runs `cc_core/workflow.js` through Claude Code's Dynamic Workflows.
Set `ccroot` to your repo path and launch the `Workflow` with knobs, e.g.
`{ "ccroot": "/abs/path/to/evolving-agent-harnesses", "out": "/abs/.../cc_core_evo", "pop": 8,
"generations": 4, "refine_rounds": 2, "topk": 3, "max_lessons": 4 }`. Use the **same** `pop`/`generations`
as the `cc_decomp` run for a clean comparison. (The native sims spin up many subprocesses — keep `MAXW`
in `cc_decomp/control.py` well under your core count, as documented there.)
```
