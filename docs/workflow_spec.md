# Workflow: Single-Level Evolution of a Nested Multi-Agent CodeClash Harness (BattleSnake)

> Paste everything below the line into Claude Code (run by Opus — the orchestrator). It begins with "workflow" to trigger Dynamic Workflows. The **nesting lives in harness execution** (a planner that fans out specialist coders, a referee, a tester, refute-until-converge debugging) — that is the Dynamic Workflows showcase. The **optimization is flat**: one evolutionary loop over harness genotypes, anchored to a fixed opponent ladder, with every accepted edit verified. Reuse CodeClash's BattleSnake rules engine — do not rebuild it. Edit the **Knobs** block first.

---

Create and run a **workflow** that evolves a nested multi-agent coding harness so that a **fixed Haiku model** produces a stronger BattleSnake bot, then proves the gain against a fixed opponent ladder and a simple-refinement ablation. Run it end to end autonomously and report back.

**This design deliberately changes five things from the prior run** (which produced a null/negative outer result): fitness is anchored to a **fixed opponent ladder**, not relative tournament rank; mutations are **admitted only when verified** to improve held-out ladder fitness over the parent; the outer population is **powered** (large, few survivors, many offspring); mutations are **incremental single-aspect edits**; and **all reflection lenses actually fire**. There is **no optimize-the-optimizer / nested GEPA** — a single optimization level only.

## Model policy (strict — do not deviate)
- **Inner (all harness execution → Haiku, `CODER_MODEL`).** The planner, every specialist coder, the referee/integrator, the tester, the debugger, and all refinement rounds run on Haiku. The produced bot and everything that builds it is Haiku. Sonnet *designs* the scaffold offline; Haiku *executes* it online.
- **Outer (harness evolution → Sonnet, `REFLECT_MODEL`).** Reflection, mutation, optional crossover, and the vetting critics run on Sonnet.
- **Sonnet ladder rung:** Sonnet is used **once** to produce the top ladder bot via the simple-refinement pipeline (then frozen). A yardstick, not part of the evolving population.
- **Never call Opus anywhere inside the workflow.** Opus only orchestrates this file.

## The core idea

A **harness** is a nested multi-agent pipeline that produces one BattleSnake bot. Running a harness is *not* a population search — it is decomposed synthesis plus a few verified self-refinement rounds (the most reliable way to improve code). A single **evolutionary loop** (Sonnet) then improves the harness across generations; fitness is the produced bot's win-rate against a **fixed opponent ladder**. So nesting (Workflows depth) is in execution; optimization is flat — which is what makes the result defensible.

The headline claim to earn: *a nested multi-agent harness, run on Dynamic Workflows and evolved at one level with every accepted edit verified to beat its parent, makes a fixed Haiku model measurably better at competitive BattleSnake — beating the unoptimized baseline, beating a simple iterative-refinement ablation, and climbing a fixed ladder that tops out with a Sonnet-produced bot.*

## Knobs (set these)
- `OUTER_GENERATIONS = 6`
- `OUTER_POP = 12`, `SURVIVORS = 4` (so ~8 **new** offspring per generation — ~48 mutation trials over the run)
- `REFINE_ROUNDS = 4` (verified write→test→fix rounds inside one harness run)
- `SIMS_EVOLVE = 120` (per ladder rung, for fitness during evolution — token-free)
- `SIMS_ADMIT = 200` (paired common-seed games for the verified-acceptance gate)
- `SIMS_FINAL = 1500` (per rung, for the headline numbers only)
- `CODER_MODEL` = a Haiku-class model (inner — see model policy)
- `REFLECT_MODEL` = a Sonnet-class model (outer + the frozen Sonnet ladder rung)
- `MUTATION = incremental` (single-aspect edits only — one decomposition change OR one localized planner-prompt edit per mutation)
- `SEED = 0`, `OUTER_DIR = ./cc_decomp_evo/`
- Token envelope for these defaults: **~10–13M in-workflow model tokens** (Haiku-heavy harness execution, a slice of Sonnet for evolution + the Sonnet rung + ablations). The Opus orchestration is separate and not counted. **Halt and report** if in-workflow tokens would exceed **15M**. (Cost scales as `OUTER_POP` at gen 0 + `OUTER_GENERATIONS × offspring × per-harness-run`; `REFINE_ROUNDS` and the specialist count drive the per-run cost — trim those first.)

## The genotype — exactly two evolvable components
Keep the search small for statistical power. Two components evolve; everything else is a fixed template.

1. **`planner_prompt`** (the prompt component) — the top-level strategy framing and how the planner briefs/decomposes the work for the specialists.
2. **`decomposition`** (the harness component — the nested multi-agent structure) — a JSON spec: which **specialists** are active from the fixed menu `{space_control, combat, food, endgame, hazard}` (the planner spawns one Haiku coder per active specialist), the **`referee_policy`** for integrating their code `{priority_order | weighted_vote | planner_merge}`, whether the **`tester`** (adversarial-board generator) is active, and `REFINE_ROUNDS`.

Specialist coder prompts and the tester/debugger prompts are **fixed templates** this run (not evolved), so the only moving parts are the planner's framing and the multi-agent shape.

## The nested multi-agent harness (how one bot is produced) — the Workflows showcase
For a given genotype, one harness run is a nested Workflows pipeline (all Haiku):
1. **Planner** reads `planner_prompt` and emits a brief per active specialist.
2. **Specialist coders** run **in parallel** (fan-out), each writing the code for its skill (space-control via flood-fill, combat / head-to-head, food/pathing, endgame, hazard).
3. **Referee/integrator** merges the specialists' code into one bot per `referee_policy`.
4. **Refine loop ×`REFINE_ROUNDS`** (refute-until-converge): if `tester` is active it generates adversarial board states and runs the bot against them / the moderate ladder rung; a **debugger** fixes the failures the tester surfaces. Each refinement is **verified** — keep the round's edit only if the bot's score on the test set does not regress.
5. The final bot is the harness's phenotype. (Run the inner coder at low temperature; single run per harness — verified acceptance at the outer level is conservative and tolerates occasional unlucky productions.)

## The fixed opponent ladder + fitness
Build a fixed, held-out ladder (the evolving population is never an opponent):
- **Rung 0 — weak:** a simple safe/random-ish or naive food-seeker (so weak harnesses still score; provides a bottom gradient).
- **Rung 1 — moderate:** a greedy + basic-safety heuristic.
- **Rung 2 — strong:** a genuinely good hand-written bot (flood-fill space control + head-to-head avoidance + food logic). **This rung supplies the headroom the prior run lacked** — do not let round-0 bots sit at the ceiling.
- **Rung 3 — Sonnet:** a bot produced **once** by Sonnet via the simple-refinement pipeline (`REFINE_ROUNDS`), then frozen. The aspirational top rung.

**Fitness(harness) = mean win-rate of its produced bot across the four rungs** (`SIMS_EVOLVE` per rung). Report per-rung win-rates too (especially vs the strong rung and the Sonnet rung).

## Phase 0 — Recon and setup (reuse CodeClash)
1. Clone CodeClash (`github.com/CodeClash-ai/CodeClash`, MIT) and read its README + docs. Reuse its **BattleSnake rules engine and HTTP bot protocol**; run natively (no Docker, dynamic ports) if the host lacks Docker, as in the prior run — game semantics unchanged. Confirm a game runs end to end before anything else.
2. Build a thin **decomposition adapter** that turns a genotype into the nested harness above: spawns specialist sub-agents per `decomposition`, integrates per `referee_policy`, runs the verified refine loop. The sub-agents are spawned per the evolved spec.
3. Build the **fixed ladder** (hand-code rungs 0–2; produce rung 3 once with Sonnet) and a **simple-refinement pipeline** (a single Haiku coder doing write→test→fix for `REFINE_ROUNDS`, no decomposition, no evolution) — used both for the ablation and to produce the Sonnet rung.
4. Make all feedback **code-generated** (win/loss, cause of death, length-at-death, board-control proxy). Use **common seeds** for any paired comparison.
5. **Verification gate:** confirm (a) the adapter spawns the specialists named in `decomposition`, (b) the produced bot reflects `planner_prompt`, (c) all ladder rungs run and rank sanely (strong beats moderate beats weak; Sonnet rung is competitive), (d) the verified-acceptance harness computes a paired CI, (e) the ablation pipeline runs. Do not proceed until these pass.

## Phase 1 — Seed population, ladder, ablations
1. Create `OUTER_POP` **diverse seed harnesses**, varying both components — different `planner_prompt` personas (space-control-first, aggression-first, balanced) and different `decomposition`s (specialist subsets, referee policies, tester on/off). **Include a few deliberately weak seeds** (e.g. one specialist, no tester) so there is room to climb.
2. Freeze the ladder (Phase 0). Produce the ablation bots: the **simple-refinement** bot (Haiku, primary baseline to beat) and a **best-of-N simple-refinement** bot (run simple refinement `N≈8` times, keep the best by ladder fitness — controls for "the harness is just more sampling").

## Phase 2 — Single-level evolution loop (repeat `OUTER_GENERATIONS` times)
1. **Score the population vs the ladder** (`SIMS_EVOLVE` per rung) → ladder fitness per harness.
2. **Select** the top `SURVIVORS` by ladder fitness; the champion is always retained (**elitism**).
3. **Produce ~8 offspring (Sonnet, all lenses fire).** Assign each offspring exactly one **lens**, cycling through all four so each is exercised ~twice per generation: `strategy` → edit `planner_prompt`; `concept` → add a missing strategy concept to `planner_prompt`; `decomposition` → one structural edit (add/remove a specialist, change `referee_policy`); `robustness` → toggle/strengthen the tester or `REFINE_ROUNDS` in `decomposition`. Each mutation is **incremental** (single aspect). Reflective mutation is the primary operator; if you use crossover, **only winner×winner** (recombine two high-fitness parents, never winner×loser).
4. **Run each offspring's harness** → child bot.
5. **Verified-acceptance gate.** Compute the child's and the parent's ladder fitness on **common seeds** (`SIMS_ADMIT` paired). Admit the child only if the paired difference (child − parent) has a **95% CI strictly above 0**. Otherwise discard it. (This is the central fix — regressions are never admitted, so the champion's ladder fitness is monotone non-decreasing.)
6. **Refill** to `OUTER_POP` with admitted children (plus survivors); if too few children are admitted, carry survivors / re-seed a weak harness. **Save everything** (schema below).

## Data schema
Write to `OUTER_DIR`: `config.json` (knobs, model-per-level, seed, CodeClash commit, ladder definition), `ladder/` (the four fixed bots + pairwise sanity results), `ablations/` (simple-refinement and best-of-N bots + their ladder fitness), and per generation `gen_NN/`:
- `genotypes/agent_<id>/`
  - `planner_prompt.md`, `decomposition.json`
  - `lineage.json` — `parent_id`, `origin`, the **lens**, the **component(s) changed with the diff**
  - `produced_bot/` — final bot code + the **refine trace** (each round's edit + tester findings)
  - `metrics.json` — ladder fitness (mean) + **per-rung win-rates** (incl. vs strong rung and vs Sonnet rung), and the **verified-vs-parent result** (paired delta + CI + admitted?)
- `admissions.json` — every offspring this generation: `parent_id`, lens, component(s), diff, paired child−parent ladder-fitness delta + CI, **admitted?**
- `population_summary.json` — **champion ladder fitness** (the monotone curve), population fitness distribution, **decomposition-structure distribution** (specialist sets, referee policies, tester fraction), and the **planner-prompt concept inventory**

## Phase 3 — Analysis
Write `analysis.md` and a self-contained `report.html`:
1. **Headline — ladder trajectory.** The champion's ladder fitness across generations (monotone by construction — that's the point), and at `SIMS_FINAL` the per-rung win-rates vs weak / moderate / **strong** / **Sonnet** rungs with 95% CIs.
2. **The contribution test — ablation comparison.** Champion vs the **simple-refinement** bot and the **best-of-N** bot, ladder fitness with CIs. The claim only holds if the evolved harness beats both ablations.
3. **Two-component evolution timelines.** (a) `planner_prompt` strategy-concept emergence across generations; (b) `decomposition`-structure evolution (specialists added/removed, referee policy, tester) — each annotated with the **verified** fitness gain that admitted it.
4. **Verified-mutation attribution (real this time).** Per lens and per component: number of **admitted** (verified-helpful) mutations and mean verified delta. This is the legitimate "how different agents help" result, because all lenses fired and only verified edits were kept.
5. **Winning-lineage tour.** The verified edit at each ancestral step that moved the champion.
6. **Honest caveats.** n=1 single seed (recommend ≥3 seeds if budget remains — it's the cheapest path to a stronger claim); the Sonnet rung is a *simple-refinement* Sonnet bot, so beating it means *evolved-Haiku-harness ≥ plain-refinement-Sonnet* (a fair, strong claim — do **not** claim the harness transfers to Sonnet, given the prior run's transfer asymmetry; flag transfer as future work).

## Constraints (cost + rigor)
- Model policy is strict: Haiku inner, Sonnet outer, Sonnet for the rung/ablation reference only, never Opus in-workflow.
- Reuse CodeClash's BattleSnake engine; keep two evolvable components only; incremental single-aspect mutations; winner×winner crossover if any.
- **Verified acceptance + elitism are mandatory** — never admit a child that does not verifiably beat its parent on the ladder.
- Fitness is **ladder-anchored** (fixed held-out opponents), never relative tournament rank.
- Prompt-cache the planner/specialist templates and stable code context across rounds and candidates (largest Haiku saving).
- `SIMS_EVOLVE`/`SIMS_ADMIT` modest, `SIMS_FINAL` large; common seeds for all paired tests.
- Reproducibility: honor `SEED`, save genotypes + diffs + refine traces, single re-runnable entry point. **Halt and report past 15M in-workflow tokens.**

## Dynamic Workflows usage (nested execution, flat optimization, model per level)
- **Nested execution (Haiku):** each harness run is a planner that fans out parallel specialist coders → referee → tester → debugger refute-until-converge loop. This is where the multi-agent depth and the Workflows showcase live.
- **Flat optimization (Sonnet):** one evolutionary loop fans out the ~8 offspring harness runs in parallel, runs the four reflection lenses and the vetting critics, and applies the verified-acceptance gate. No nested optimization.

## Deliverables (report these back)
The forked CodeClash with the decomposition adapter, the populated `OUTER_DIR`, `report.html` with the ladder trajectory + per-rung (incl. Sonnet) win-rates + the **ablation comparison** + the two-component evolution timelines + the verified-mutation attribution, `analysis.md`, and a short summary of how the `planner_prompt` and the `decomposition` improved, with the final champion's win-rates against every ladder rung and against both ablations.
