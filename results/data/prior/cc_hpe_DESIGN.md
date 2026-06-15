# Harness-prompt evolution — GEPA vs CORE over a multi-prompt harness

## Goal
Phase 1 (cc_prompt) proved the **prompt is the lever with real headroom** (evolution climbs), unlike the
small allocation space (cc_alloc). Phase 2 keeps the multi-agent **harness** (the project's theme) but
makes its search space large by evolving **every role-prompt at once**.

## The harness (fixed structure)
A decomposition harness with a fixed, strong 3-specialist set: **space_control, combat, food** →
assembled by a **referee/integrator** (the cc_decomp scaffold: each specialist is a `score()` exec'd in
its own namespace; the referee combines them; a non-suicidal floor). Structure is FIXED so the search is
purely over prompts.

## Genotype — FOUR evolvable prompts (the large search space)
```
brief_space_control   — how to implement the space_control specialist's score()
brief_combat          — how to implement the combat specialist's score()
brief_food            — how to implement the food specialist's score()
referee_prompt        — how the referee integrates the three specialists into one move
```
All four are free-text and evolve together → a far larger space than one prompt, and much larger than
the 4-integer allocation. (The per-specialist *concern* and the bot contract are fixed and injected
separately; only the brief/referee wording evolves.)

## Phenotype (R replicates → mean)
A genotype is realized R=3 times. Each replicate: 3 specialist coders (Haiku, each reads its evolving
brief + fixed concern + contract) write the three `score()` modules, and a referee coder (Haiku, reads
the evolving referee_prompt) writes the integrator; the cc_decomp scaffold assembles one `main.py`.
Fitness = mean ladder win-rate over the R assembled bots (Haiku realization variance control).

## Scoring / gate / optimizers — identical to cc_prompt
Clean scoring (MAXW≤16); fitness = mean over R bots vs the fixed ladder (weak/moderate/strong); verified
gate = two-sample bootstrap over child vs parent pooled per-(bot,game) outcomes. One workflow, optimizer
∈ {gepa, core}:
- **GEPA** lenses target ONE role-prompt each (space / combat / food / referee): reflect on where the
  bots lose, rewrite that one brief/referee prompt.
- **CORE** contrastive reflection on winner-prompt-set vs loser-prompt-set → insights about briefing
  specialists & integration → utility-weighted bank → lesson-conditioned rewrite of one role-prompt.

Baseline = best gen-0 seed prompt-set. Headline: does evolving the harness's prompts beat the best seed
harness, and GEPA vs CORE on this larger space?

## Reuse
cc_prompt.control_prompt (cmd_admit two-sample, cmd_score_pop, _two_sample_boot, _representative,
_SAFE_BOT), cc_alloc.recipe.assemble_decomp_candidate (assembly), cc_decomp.control
(select/finalize/population-summary/scoring helpers) + harness contracts, cc_core (bank/ingest/credit).
Heavy-bot note: score at sims_eval≤100 and read champion/gen0 fitness from run metrics — do NOT run the
offline high-sim final-compare (it hangs on occasionally-slow Haiku bots).
