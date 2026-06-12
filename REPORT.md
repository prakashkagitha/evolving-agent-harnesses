# Evolving coding harnesses with GEPA vs CORE — what we learned

A study of two reflective optimizers — **GEPA** (reflect-and-mutate) and **CORE** (contrastive
reflection into a utility-weighted *insight bank*) — applied to the same task: make a small fixed model
(**Haiku**) write a stronger BattleSnake bot by evolving its *harness* (the prompts / multi-agent
structure that produce the bot). A larger model (**Sonnet**) does the reflecting/mutating; every accepted
change must **verifiably** beat its parent (paired / two-sample bootstrap, 95% CI) on a fixed opponent
ladder. The game engine, ladder, and verified-acceptance gate are shared across all experiments.

**One-line thesis:** *evolution helps only where there is **headroom** — a large search space is
necessary but not sufficient; the optimizer choice (GEPA ≥ CORE) matters less than picking a regime where
a weak baseline leaves room to climb.*

---

## The five experiments

| package | what evolves | search space | headroom (gen-0 baseline) | did evolution climb? |
|---|---|---|---|---|
| `cc_decomp` | decomposition harness: planner prompt + which specialists + referee | medium | mid | **yes** (GEPA) |
| `cc_core` | same harness, CORE breeder | medium | mid | partial (frontier-blind) |
| `cc_alloc` | how to spend a fixed 8-LLM-call budget (best-of-N / revise / decompose) | **small** (4 integers) | — | **no** |
| `cc_prompt` | the single bot-generation prompt | **large** (free text) | **high** (weak ~0.2 single-shot) | **yes, strongly** |
| `cc_hpe` | 4 role-prompts of a decomposition harness | **large** (4 prompts) | **low** (strong ~0.5) | **no** |

All numbers are mean ladder win-rate, scored at low concurrency (MAXW≤16) to avoid CPU-contention
artifacts. Ladders differ slightly between families (cc_decomp/cc_core include a Sonnet rung; the others
are weak/moderate/strong), so absolute values are comparable *within* a family, not across.

---

## Results

### 1. Original harness evolution — `cc_decomp` (GEPA) vs `cc_core` (CORE)
- **GEPA** evolved a Haiku decomposition harness to a champion **0.617** ladder-mean, beating both
  ablations (best-of-8 0.214, single simple-refine 0.076) and the frozen Sonnet-simple-refinement rung.
  The winning verified edit: **add a `combat` specialist**.
- **CORE** plateaued ~**0.45**. Its *breeder* was more productive (6/16 admitted vs GEPA's 5/16, larger
  mean verified Δ, a rich interpretable lesson bank), but it is **structurally frontier-blind**:
  contrastive reflection learns from winner-vs-loser pairs, and the best harness is never the *loser*, so
  no lessons target improving it. A frontier-reflection fix (treat the champion's own losses as the
  negative trace) let CORE improve the champion in a probe, but Haiku code-realization variance dominated
  at n=1. Both optimizers independently rediscovered "add combat".

### 2. Budget-allocation search — `cc_alloc`
At a fixed 8-LLM-call budget, **allocation barely matters relative to Haiku variance**: the same
allocation swung 0.0–0.55 across runs, and *both* optimizers' champions were **seed** allocations
(evolution never beat the best seed). The allocation space (a few integers) is too small for reflective
search to pay off. **This redirected the project to evolving prompts.**

### 3. Pure prompt evolution — `cc_prompt` (the cleanest result)
Evolving just the bot-generation prompt (cheapest 1-call harness) **clearly works** — both optimizers
climb, and champions are *evolved* prompts, not seeds. Decisive **K=3-seed × 6-generation** comparison
(within-run improvement = champion − gen-0-best):

| | mean improvement | abs. champion (peak) |
|---|---|---|
| **GEPA** | **+0.246 ± 0.099** | 0.50 (0.61) |
| **CORE** | **+0.165 ± 0.076** | 0.39 (0.44) |

**GEPA is the better optimizer here (moderate confidence):** ~1.5× the gain, higher ceiling, wins 2/3
seeds by large margins. *Not* a statistical blowout (n=3 distributions overlap, Welch t≈1.1, p≈0.3; the
large Haiku realization variance makes p<0.05 infeasible without ~20 runs/arm). Both *always* improve, and
both independently discover **"add explicit head-to-head rules."** Style: **GEPA front-loads** big gains
early then plateaus; **CORE climbs gradually** as its insight bank compounds (gens 3–5) and so benefits
more from extra generations.

### 4. Harness-prompt evolution — `cc_hpe` (largest search space)
Evolving **four** role-prompts of a real multi-agent decomposition harness (a brief per specialist
{space_control, combat, food} + a referee prompt). gen-6 result:

| | gen-0 best | final champion | improvement |
|---|---|---|---|
| **GEPA** | `phase_referee` 0.481 | `g02_02` 0.487 | **+0.006** |
| **CORE** | `concrete` 0.520 | `concrete` 0.520 | **+0.000** |

**Neither optimizer meaningfully improved the champion** — the opposite of Phase 3. CORE reproduced the
frontier-blindness exactly (admitted 4 weaker-lineage offspring, none beat the strong incumbent). The
4-prompt space is *large* but *near-ceiling*: the decomposition harness already makes strong bots, so
there is little for prompt-tuning to recover.

---

## The central finding — headroom, not search-space size

Lining up all five: a large search space is necessary but **not** sufficient. What predicts whether
reflective evolution climbs is **headroom** — how far the gen-0 baseline sits below the ceiling.

- `cc_alloc` — small space → no climb.
- `cc_hpe` — **large** space but **strong** ~0.5 baseline (low headroom) → ~no climb (+0.00–0.01).
- `cc_prompt` — **large** space and **weak** ~0.2 baseline (high headroom) → big climb (+0.25).

Single-shot prompt evolution worked not because "prompts," but because the cheapest harness makes *weak*
bots → lots of room to improve. Strengthen the harness and the same prompt-evolution stalls.

## GEPA vs CORE — settled across the whole study
- **GEPA ≥ CORE wherever there is any climb** — it front-loads big verified gains and is more efficient.
- **CORE is structurally frontier-blind** (confirmed twice: original harness + cc_hpe) — it cannot improve
  a strong incumbent because the incumbent is never the contrastive "loser." Its distinctive value is the
  **interpretable, compounding insight bank** (e.g. *"name the exact metric — flood-fill reachable cells,"*
  *"give concrete numerical thresholds,"* *"limit prompt complexity to what a small model can reliably
  implement"*), and it benefits more from extra generations.
- **Both keep rediscovering the same domain truth** (head-to-head / combat is BattleSnake's key lever),
  from opposite mechanisms.

## Engineering lessons (hard-won)
- **Clean low-concurrency scoring is essential** — CPU contention makes heavy bots miss the 500 ms move
  deadline, silently corrupting fitness (the spurious-0.0s that motivated a sequential `reeval`).
- **Offline high-sim re-scoring hangs** on occasionally-slow Haiku bots (a stalled BotServer makes every
  move wait out the deadline); read fitness from the run's own clean scores instead, or cap + timeout.
- **Transient "StructuredOutput" flakes must be caught-and-retried**, not allowed to throw and kill a
  multi-hour workflow (a real bug we hit and fixed in the harness workflow's `runPy`).
- **Haiku realization variance is the dominant noise source** — decisive optimizer comparisons need
  multiple seeds; single-run champion-quality gaps are confounded.

---

## The open question this sets up — can Haiku reach Sonnet via harness optimization?

The natural PoC: fix a compute multiple (**4× / 8×** Haiku calls) and ask whether an **evolved** Haiku
harness reaches a **single-shot Sonnet** bar — *and* whether it beats the naive same-budget baselines
(**best-of-N**, **revision chain**). If those baselines already close the Haiku→Sonnet gap, harness
*optimization* adds little and the framing needs rethinking. Early hints are encouraging (the evolved
Haiku decomposition harness in `cc_decomp` beat the Sonnet-refinement rung), but it must be shown in a
single, clean, compute-controlled comparison — in a **high-headroom** regime, per the central finding.

## Layout
```
cc_decomp/  original decomposition-harness evolution (GEPA) + the shared sim/ladder/contracts
cc_core/    CORE (contrastive reflection + lesson bank) breeder for the same harness
cc_alloc/   budget-constrained allocation search (best-of-N / revise / decompose at fixed B calls)
cc_prompt/  pure single-prompt evolution (the cleanest GEPA-vs-CORE result)
cc_hpe/     harness-prompt evolution (4 role-prompts of a decomposition harness)
```
Each package ships a token-free `_mocktest`, a `DESIGN.md`, and a `COMPARISON.md` with the raw numbers.
The large per-run output directories are gitignored — rebuild them by launching the workflows.
