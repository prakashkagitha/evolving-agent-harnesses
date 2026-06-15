# Budget-constrained allocation search

## The question
**Given a fixed budget of B LLM calls to write one BattleSnake bot, what is the best way to spend
them?** "Harness" = a way of allocating compute; the genotype *is* an allocation of B calls. We
**evolve** (not enumerate) that allocation — the optimizer's job is to find a strong allocation
without trying them all — and the naive **best-of-B** allocation is the baseline it must beat.

Two levers, both evolved: (1) the **allocation** of the B calls; (2) the **generator prompt**.

## The genotype — a budget-B allocation (fixed-template, so it's robust to execute & mutate)
```
alloc = { n_draft, n_spec, do_merge ∈ {0,1}, n_revise }     # n_draft + n_spec + do_merge + n_revise == B
concerns = ordered subset of [space_control, combat, food, endgame, hazard]   # the n_spec specialists
draft_prompt = "<the generator prompt — the 2nd lever>"
```
Every candidate costs **exactly B generative LLM calls** (sims/file-ops are free). The whole
allocation space is reachable:
- `(8,0,0,0)` = **best-of-8** (8 monolithic drafts, keep best)
- `(1,0,0,7)` = **revision chain** (1 draft + 7 self-revisions)
- `(0,5,1,2)` = **decomposition** (5 specialist coders + merge + 2 revisions)
- `(3,0,0,5)`, `(2,3,1,2)`, … = **hybrids**

## Execution (fixed order → simple, deterministic interpreter)
1. **n_draft** monolithic drafts (parallel), each from `draft_prompt`. Each → one candidate `main.py`.
2. **n_spec** specialist coders (parallel) for `concerns[:n_spec]`; if **do_merge**, 1 merge call
   assembles them into a decomposition bot (cc_decomp scaffold) → one candidate.
3. **n_revise** sequential revisions on the current best candidate, each fed clean sim feedback;
   keep-if-not-worse.
4. **Final bot** = the highest clean-scoring candidate produced.

## Scoring — clean, no contention artifact
All scoring (candidate selection *and* champion selection *and* final headline) runs at **low
concurrency (MAXW=16)** so the per-move-latency/CPU-starvation confound never enters fitness. Fitness
= ladder-mean win-rate vs the fixed opponent ladder (weak/moderate/strong[/sonnet]). Wilson CIs.

## The optimizers (same everything except the breeder — clean A/B)
- **GEPA**: reflect on a recipe's weakness through lenses, make one budget-preserving edit
  (`alloc`: move a call between buckets / toggle merge; `concerns`: swap one; `prompt`: reword),
  admit only if it verifiably beats the parent (paired common-seed 95% CI).
- **CORE**: contrastive reflection on winner-recipe vs loser-recipe → compact lessons about *good
  allocations* → a utility-weighted bank → lesson-conditioned recipe mutation; same verified gate.

Both run on the **same** seeds, ladder, budget B, verified gate, and clean scorer. The single
`workflow_alloc.js` switches breeder by an `optimizer ∈ {gepa, core}` arg.

## Baseline & claim
Baseline = the **best-of-B** recipe `(B,0,0,0)` evaluated identically (the "no-search, just sample B
and keep best" control). Headline claim: *an evolved B-call allocation beats spending the same B calls
on best-of-B* — and, secondarily, GEPA vs CORE on this search.

## Variance control
Haiku code realization is high-variance, so the verified gate uses paired common-seed comparisons
(variance largely cancels), champion fitness is reported with CIs, and (budget permitting) the final
headline re-scores at high sims. n=1 evolutionary seed per optimizer for the first cut; ≥3 is the
cheapest path to CIs on the GEPA-vs-CORE gap.

## Reuse
`cc_gepa.sim` (engine), `cc_decomp.ladder` (rungs), `cc_decomp.harness` (decomposition scaffold +
contracts), `cc_decomp.control` scoring/admit/select/finalize/final-eval (genotype-agnostic — they act
on a produced `main.py`), and `cc_core.bank` (CORE lessons). New: the recipe genotype + interpreter,
budget-preserving mutation, and the unified workflow.
```
