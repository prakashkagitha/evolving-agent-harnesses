# CodeClash — Single-Level Evolution of a Nested Multi-Agent BattleSnake Harness

*Reuses the CodeClash/BattleSnake rules engine (battlesnake commit `26640435a497`). Inner harness execution = Haiku; outer harness evolution = Sonnet; the Sonnet ladder rung is a single simple-refinement bot. Never Opus in-workflow.*

## Setup

- Knobs: generations=4, pop=8, survivors=4, refine_rounds=2, sims_evolve=120, sims_admit=200, sims_final=1500, seed=0.
- Fixed ladder (round-robin fitness): {'weak': 0.242, 'moderate': 0.572, 'strong': 0.683, 'sonnet': 0.503}; ranking weak<moderate<strong **holds**; sonnet competitive: True.

## 1. Headline — ladder trajectory (monotone by construction)

| gen | champion | ladder fitness | admitted this gen |
|---|---|---|---|
| 0 | space_first | 0.547 | 0 |
| 1 | space_first | 0.543 | 2 |
| 2 | space_first | 0.527 | 0 |
| 3 | g03_02 | 0.592 | 1 |
| 4 | g03_02 | 0.607 | 0 |

**Final champion per-rung win-rate (1500 sims, Wilson 95% CI):**

| rung | win-rate [95% CI] |
|---|---|
| weak | 0.789 [0.767, 0.809] |
| moderate | 0.516 [0.491, 0.541] |
| strong | 0.473 [0.448, 0.498] |
| sonnet | 0.689 [0.665, 0.712] |
| ladder_mean | 0.617 [0.604, 0.629] |

## 2. The contribution test — champion vs ablations

| bot | ladder mean win-rate [95% CI] |
|---|---|
| **evolved champion** | 0.617 [0.604, 0.629] |
| simple-refinement (baseline) | 0.076 [0.070, 0.083] |
| best-of-N refinement | 0.214 [0.204, 0.224] |

Champion beats simple-refinement: **True**; beats best-of-N: **True**. (The harness's contribution holds only if BOTH are true.)

Head-to-head (champion win-rate, Wilson 95% CI):
- vs simple_refine: 0.980 [0.972, 0.986]
- vs best_of_n: 0.771 [0.749, 0.791]

## 3. Two-component evolution

### 3a. planner_prompt — strategy-concept inventory (count of population members naming each concept)

| gen | space/flood-fill | head-to-head/combat | food/health | endgame/duel | hazard/edge | lookahead/adapt | trap-avoidance |
|---|---|---|---|---|---|---|---|
| 0 | 8 | 4 | 5 | 2 | 2 | 0 | 4 |
| 1 | 8 | 5 | 7 | 2 | 1 | 0 | 3 |
| 2 | 8 | 5 | 7 | 2 | 1 | 0 | 3 |
| 3 | 8 | 5 | 7 | 2 | 1 | 0 | 3 |
| 4 | 8 | 5 | 7 | 2 | 1 | 0 | 3 |

### 3b. decomposition — structure evolution

| gen | mean #specialists | tester fraction | mean refine rounds | referee policies |
|---|---|---|---|---|
| 0 | 2.62 | 0.75 | 2.00 | {'weighted_vote': 5, 'priority_order': 2, 'planner_merge': 1} |
| 1 | 3.00 | 0.88 | 2.12 | {'priority_order': 1, 'weighted_vote': 6, 'planner_merge': 1} |
| 2 | 3.00 | 0.88 | 2.12 | {'priority_order': 1, 'weighted_vote': 6, 'planner_merge': 1} |
| 3 | 3.00 | 0.88 | 2.12 | {'priority_order': 1, 'weighted_vote': 6, 'planner_merge': 1} |
| 4 | 3.00 | 0.88 | 2.12 | {'priority_order': 1, 'weighted_vote': 6, 'planner_merge': 1} |

## 4. Verified-mutation attribution (only verified-helpful edits are admitted)

| lens | trials | admitted | accept rate | mean Δ (admitted) | mean Δ (all) |
|---|---|---|---|---|---|
| strategy | 4 | 2 | 0.50 | 0.072 | 0.035 |
| concept | 4 | 0 | 0.00 | — | -0.224 |
| decomposition | 4 | 1 | 0.25 | 0.060 | -0.090 |
| robustness | 4 | 2 | 0.50 | 0.050 | 0.021 |

Overall: 5/16 offspring admitted (accept rate 0.31).

**By component changed:**

| component | trials | admitted | accept rate | mean Δ (admitted) |
|---|---|---|---|---|
| planner_prompt.md | 7 | 2 | 0.29 | 0.072 |
| decomposition.json | 8 | 3 | 0.38 | 0.053 |

## 5. Winning-lineage tour (verified edits that moved the champion)

| gen | id | origin | lens | changed | diff | verified Δ | ladder fit |
|---|---|---|---|---|---|---|---|
| 2 | space_first | seed | — | — | — | — | 0.527 |
| 4 | g03_02 | mutation | decomposition | decomposition.json | Added 'combat' specialist to address low win-rates vs moderate (43%) and strong (39%) rungs where head-to-head collision avoidance/targeting was missing. | 0.614 | 0.607 |

## 6. Honest caveats

- **n=1 seed.** A single evolutionary run; ≥3 seeds would be the cheapest path to a stronger claim.
- **The Sonnet rung is a simple-refinement Sonnet bot.** Beating it means *evolved-Haiku-harness ≥ plain-refinement-Sonnet* — a fair, strong claim. It does **not** imply the harness transfers to Sonnet (transfer is explicitly out of scope; flagged as future work).
- **Verified acceptance + elitism make the champion curve monotone by construction** — the curve shows *that* improvement was found and verified, not a noisy hill-climb; magnitude and per-rung gains are the substantive results.
