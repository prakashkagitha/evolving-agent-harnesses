# CORE vs GEPA — evolving the same BattleSnake harness

Both optimizers evolve the **identical** nested multi-agent harness (genotype = `planner_prompt` +
`decomposition` over the fixed 5-specialist menu `space_control · combat · food · endgame · hazard`),
on the **identical** fixed opponent ladder, with the **identical** verified-acceptance gate (paired
common-seed 95 % CI) and ablations. Only the breeder differs (see [README](README.md)). Run scale was
matched to the published cc_decomp run: **pop 8 × 4 generations, refine 2, seed 0.**

All headline numbers below are re-measured **offline, sequentially, at low concurrency (MAXW=16)** —
necessary because the heaviest harness (the 5-specialist `generalist` with a `planner_merge`
integrator) misses its 500 ms move deadline under the high-concurrency final eval (MAXW=64) and posts
artificially low win-rates. cc_decomp's lighter 3-specialist champion is unaffected (0.615 @ MAXW16 ≈
0.617 published @ MAXW64), confirming the correction is sound.

## Headline: champion strength (both fair @ MAXW=16, 1500 sims/rung)

| | **GEPA** (`g03_02`) | **CORE** (`generalist`) |
|---|---|---|
| ladder-mean win-rate | **0.615** [0.602, 0.627] | **0.452** [0.440, 0.465] |
| vs weak | 0.801 | 0.745 |
| vs moderate | 0.513 | 0.430 |
| vs strong | 0.469 | 0.362 |
| vs sonnet | 0.676 | 0.273 |

**GEPA wins decisively (+0.16, non-overlapping CIs).** The gap is largest on the two hardest rungs
(strong, sonnet) — exactly where a well-integrated harness matters most.

## Champion trajectory (corrected monotone best-so-far)

| | gen0 | gen1 | gen2 | gen3 | gen4 |
|---|---|---|---|---|---|
| GEPA | 0.547 | 0.543 | 0.527 | **0.592** | **0.607** |
| CORE | 0.448 | 0.448 | 0.462 | 0.465 | 0.465 |

GEPA's champion **climbed** — evolution *produced* a champion (`g03_02`) better than any seed, via the
verified edit *"add combat to `space_first`"*. CORE's champion is **flat** — it is the unchanged
`generalist` **seed**; evolution never produced anything that beat it.

## Contribution test (did evolution beat the monolithic ablations?)

| bot | GEPA (publ. @ MAXW64) | CORE (@ MAXW16) |
|---|---|---|
| evolved champion | **0.617** | 0.452 |
| best-of-8 monolithic | 0.214 | **0.556** |
| single simple-refine | 0.076 | 0.064 |

GEPA's champion **crushes** both ablations. CORE's champion beats `simple_refine` (0.064) but **loses
to its own `best_of_n` (0.556)** — i.e. on this run, evolving the harness did *worse* than just picking
the best of 8 monolithic Haiku bots. (Caveat: `best_of_n` is a high-variance best-of-8 draw, and
GEPA's ablation bots weren't committed so its 0.214 is the published MAXW=64 figure — the cross-run
ablation magnitudes are not strictly comparable. The **champion-vs-champion** row above is.)

## The surprise: CORE's *breeder* is actually more productive

| | GEPA | CORE |
|---|---|---|
| mutations admitted | 5 / 16 (31 %) | **6 / 16 (37.5 %)** |
| mean verified Δ (admitted) | +0.05 … +0.072 | **+0.104** |
| memory | none (stateless lenses) | **64 lessons** (39 specific, 25 meta), 18 verified wins |

CORE produced **more** verified improvements, with a **larger** mean gain — and the lesson bank worked
as designed (lessons used by admitted mutations gained utility). The admitted CORE edits were:

```
gen1: g01_03 (parent duelist,     Δ+0.20)
gen2: g02_01 (parent space_first, Δ+0.09),  g02_03 (parent duelist, Δ+0.12)
gen3: g03_01 (parent space_first, Δ+0.07),  g03_02 (parent hunter,  Δ+0.07)
gen4: g04_02 (parent hunter,      Δ+0.08)
```

Every admitted edit improved a **weaker** lineage (duelist / space_first / hunter) — and **none caught
the `generalist`**.

## Why CORE underperformed — a structural property of contrastive reflection

CORE distils lessons from **winner-vs-loser** pairs. In an elitist tournament the frontier harness is
the **winner in every pair, never the loser** — so the bank accumulates rich advice on *"how a weak
harness should become more like the generalist"* but **zero signal on how to push the generalist
itself further**. Concretely, all four attempts to mutate the champion **regressed**, increasingly:

| gen | child of `generalist` | verified Δ | fate |
|---|---|---|---|
| 1 | g01_00 | −0.131 | rejected |
| 2 | g02_00 | −0.281 | rejected |
| 3 | g03_00 | −0.385 | rejected |
| 4 | g04_00 | −0.470 | rejected |

The retrieved lessons just nudged the mutator to pile "phase-aware weighting" onto an already-complete
`planner_prompt`, which hurt the Haiku planner/coders. The verified gate correctly killed all four.

**Both methods converged on the same truth.** CORE's highest-utility lessons read *"Always include a
combat specialist; space-only harnesses lose every head-to-head"* and *"Use `planner_merge` over
`weighted_vote` so the planner can contextually override conflicting specialists."* GEPA's single
winning edit was literally *adding the combat specialist*. CORE *knew* the right answer — but its
champion (`generalist`) already embodied it (all 5 specialists + `planner_merge`), so the knowledge had
nowhere to go.

## Verdict

At this scale/seed, **GEPA produced the stronger champion (0.615 vs 0.452)**, because it improved a
*mid-tier* harness past the field, whereas CORE's gains — though more numerous and larger per-edit —
landed on non-champion lineages while the incumbent seed was, by construction, invisible to contrastive
reflection. CORE's distinctive value (a compounding, interpretable lesson bank that converges on the
right design principles) is real and visible; its weakness in a *single-population elitist* tournament
is that the contrastive signal cannot target the frontier.

**Caveats.** n = 1 seed each; the embedding is a local domain bag-of-words, not neural; the `best_of_n`
ablation is high-variance; GEPA's ablation bots were re-used from its published headline (MAXW=64) as
they weren't committed. The champion-vs-champion comparison is the robust claim.

### Natural follow-ups
1. **Champion-improvability probe** — give CORE a champion-vs-strong-rung contrastive frame (treat the
   champion's *lost games* as the "loser" trace) so lessons can target the frontier.
2. **≥3 seeds** for both, to put CIs on the champion gap.
3. A neural embedder for the bank, to test whether richer retrieval changes which lessons win.

---

## CORE-v2 (frontier reflection) + the contention/variance findings

The follow-up #1 above was built (`workflow_frontier.js` probe; then `workflow2.js` = CORE-v2 with a
per-generation **frontier reflection** that reframes the champion's own losses to the strong/sonnet
rungs as the negative trace, so the bank can accrue lessons that target the frontier — which ordinary
winner-vs-loser pairs never reach, since the champion is always the winner).

- **The frontier probe worked in isolation:** by gen 7 the accrued frontier lessons pushed a *structural*
  champion edit (`planner_merge → priority_order`) whose bot clean-scored **0.541** vs the champion's
  0.452 — the first time CORE improved the frontier. Ordinary champion mutations always regressed
  (−0.13 → −0.47, all prompt-elaboration).
- **CORE-v2 full run (8×4, contention-safe reeval):** breeder was the *most* productive yet —
  **9/16 admitted (56%)**, and frontier reflection got generalist-children admitted via the same levers
  (`→ priority_order` Δ+0.325; `− endgame` Δ+0.219). **But the crowned champion plateaued ~0.45**
  (selected `g04_01` = 0.438–0.457 @ MAXW-16), same as v1.
- **No hidden strong harness:** every v2 generalist-derived child, scored cleanly @ MAXW-16, lands
  0.22–0.45 (g02_02 0.454, g04_02 0.339, g03_02 0.221). The probe's 0.541 did **not** reproduce — same
  genotype lever, different Haiku-written specialist code → outcome dominated by **realization variance**.

### Three-way headline (all champions @ MAXW-16, 1500 sims)
| | GEPA | CORE-v1 | CORE-v2 (frontier) |
|---|---|---|---|
| champion ladder-mean | **0.615** | 0.452 | 0.438–0.454 |
| trajectory | climbed 0.55→0.61 | flat | flat |
| mutations admitted | 5/16 (31%) | 6/16 (37.5%) | **9/16 (56%)** |
| breeder memory | none | 64-lesson bank | 48-lesson bank + frontier |

### Two confounds that matter for interpretation
- **Contention-biased scoring.** Scoring under high concurrency (MAXW=64) starves heavy multi-specialist
  bots past the engine's 500 ms move deadline, depressing their *measured* win-rate (generalist swings
  0.18 across MAXW; the light GEPA champion swings 0.002). CORE's lessons push toward heavy harnesses, so
  this biases *against* CORE at selection time. Mitigated for the headline by re-scoring at MAXW=16 (and
  the paired admit gate mostly cancels it), but per-generation *selection* still used MAXW=64 scores.
  This is a runtime/measurement artifact, **orthogonal** to the optimisation objective; the clean fix is
  to score selection at low concurrency too (or measure per-move latency deterministically and feed it
  back as honest fitness, rather than letting it leak as contention noise).
- **Haiku realization variance.** The genotype (prompt + structure) is the lever, but the *bot quality*
  is whatever Haiku writes for the specialists, which is high-variance run-to-run (same `priority_order`
  lever → 0.454 in v2, 0.541 in the probe, 0.22 in a sibling). At **n=1 run per method**, the
  GEPA(0.615)-vs-CORE(~0.45) champion gap is therefore confounded with a lucky/unlucky draw — it is **not**
  a clean measurement of search quality. ≥3 seeds per method are needed to separate method from variance.

### Alignment caveat (added after a scope review)
These experiments evolve the two intended levers (generator **prompt** = `planner_prompt`/briefs;
**harness** = `decomposition`) and show an evolved harness beats naive baselines — but they do **not**
hold the per-bot **LLM-call budget fixed**, so they do not cleanly answer the original objective: *given
a fixed budget (e.g. 8 LLM calls), what is the most efficient allocation to write one bot?*
(best-of-8 ≈ 16 calls; a 5-specialist harness ≈ 9; a lean one ≈ 3–6 — uncontrolled.) The GEPA/CORE outer
loop is also a heavy meta-optimiser (hundreds of calls), a second-order question distinct from per-bot
allocation. A faithful next experiment fixes B calls, scores cleanly (quality only), and compares
allocations head-to-head: best-of-B vs revision-chain vs decomposition vs hybrid, with the prompt as a
cross-cutting lever — optionally sweeping B for compute-vs-quality curves.
