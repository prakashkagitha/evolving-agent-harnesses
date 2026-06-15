# Pure prompt evolution — the simplest GEPA vs CORE study

**Goal:** isolate the optimizer. Evolve ONLY the generator prompt, with the cheapest harness (one LLM
call writes the whole bot), and compare GEPA vs CORE on that single lever. No allocation/harness
search — that comes later.

## Genotype
`prompt` — a single natural-language prompt that instructs a small model (Haiku) to write a complete
single-file BattleSnake bot. All strategy / tactics / insights live in this text. That's the only
thing that evolves.

## Phenotype (cheapest harness = 1 call/bot)
A prompt is realized by **1 Haiku call → one `main.py`**. Because one bot is a noisy sample of a
prompt's quality (Haiku realization variance is large), a prompt's FITNESS is the **mean over R
independent single-shot generations** (R=5 by default) scored on the fixed ladder. This is the
"average over replicates" estimate — variance is intrinsic to LLM code-gen, so we measure the prompt's
*expected* bot quality, not one lucky/unlucky draw.

## Scoring — clean
All scoring at low concurrency (MAXW=16); fitness = mean ladder win-rate over the R bots vs the fixed
opponent ladder (weak/moderate/strong). No latency/contention contamination.

## Verified gate — two-sample (the replicate test)
A child prompt is admitted over its parent only if a **two-sample bootstrap** over the pooled
per-(bot,game) outcomes shows the child's mean strictly above the parent's (95% CI lower bound > 0).
This is exactly "compare the two prompts' bot distributions with replicates," not a single-bot fluke.

## Optimizers (identical except the breeder)
- **GEPA**: reflect on where the prompt's bots lose (per-rung), rewrite the prompt through a lens
  (reframe strategy / add a missing concept / sharpen specificity / target the weakest rung).
- **CORE**: contrastive reflection on winner-prompt vs loser-prompt → compact INSIGHTS about how to
  prompt a bot-writer → a utility-weighted bank → lesson-conditioned prompt rewrite. Same gate.

Baseline = the best gen-0 seed prompt (no evolution). Headline: did evolving the prompt beat the best
starting prompt, and GEPA vs CORE?

## Reuse
`cc_gepa.sim`, `cc_decomp.ladder` + `harness.SIMPLE_BOT_CONTRACT`, `cc_decomp.control` scoring/select/
finalize, `cc_core.bank`. New: the prompt genotype, the R-replicate evaluation, the two-sample gate,
and prompt-focused mutation/reflection.
