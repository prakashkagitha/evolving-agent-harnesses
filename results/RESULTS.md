# Results reference — GEPA vs CORE for evolving a Haiku coding harness

Durable record of experiment results (the run output dirs are gitignored/transient). Raw machine-readable
artifacts are in `results/data/`. This file is the **honest, de-inflated** record; the public-facing
`REPORT.md` still carries some pre-correction (R=3) numbers and should be reconciled against this before sharing.

Task throughout: a fixed small model (**Haiku**) writes a BattleSnake bot; **Sonnet** does reflection/mutation;
fitness = mean ladder win-rate (weak/moderate/strong rungs) via a native Go engine; every accepted change must
beat its parent on a verified two-sample bootstrap (95% CI). Two reflective optimizers compared: **GEPA**
(reflect-and-mutate, stateless lenses) vs **CORE** (contrastive winner/loser reflection → utility-weighted
insight bank).

---

## ⚠ The headline correction (this session): R=3 champion fitnesses were selection-inflated

The evolution selects the offspring with the best **R=3** (3-replicate) fitness and reports that as the champion.
With Haiku's enormous realization variance, that max-over-noisy-estimates is biased **upward** (optimizer's
curse). A confirmatory **re-eval at higher R** (fresh draws; `results/data/cc_pipe_reeval_report.json`) shows
the *unselected* baselines stay stable while the *selected* champions regress — some a lot. Confirmed **not**
contention (standalone maxw=1 re-scores matched the parallel ones). **Always de-inflate champions with an
independent higher-R re-eval before claiming anything.**

---

## cc_pipe — the Haiku→Sonnet/Opus PoC (main result)

Genotype = a budget-N **self-correction pipeline**: role sequence in {draft, critique, fix} (step0=draft) + a
free-text prompt per role; BOTH structure and prompts evolve. Keep-best chain with in-process engine feedback
feeding critique→fix. Runs: gen 5 · pop 6 · R=3 (original). Dirs: `cc_pipe_evo_{gepa,core}` (4×),
`cc_pipe_evo_8x_{gepa,core}` (8×), gate `cc_pipe_8x_base`, re-eval `cc_pipe_reeval`.

### Robust reference bars (honest, higher-R)
| Bar | fitness | replicate-CI | source |
|---|---|---|---|
| single-shot **Opus** | **0.522** | [0.455, 0.595] | re-eval R=12 |
| single-shot **Sonnet** | **0.442** | [0.405, 0.475] | re-eval R=12 |
| **best-of-8** (Haiku) | **0.449** | [0.351, 0.526] | re-eval R=8 |
| refine-8 (Haiku) | 0.272 | — | gate R=5 |
| best-of-4 / refine-4 (Haiku) | 0.278 / 0.186 | — | gate R=5 |
| single-shot **Haiku** | 0.148 | [0.075, 0.226] | re-eval R=12 |

(The first 4× gate mislabeled the 1-shots — a bug padded `["draft"]` up to N, so "single-shot Sonnet 0.483"
was actually Sonnet-refine-4; fixed. True single-shot bars above are budget-independent. Buggy file kept as
`results/data/cc_pipe_4x_baselines_BUGGY.json` for the record.)

### Evolved champions — original R=3 → honest higher-R
| Champion (shape) | R=3 reported | honest R=7/8 | repl-CI | vs Opus 0.522 | vs best-of-8 0.449 |
|---|---|---|---|---|---|
| **8× GEPA g04_00** (`D→D→D→D→F→F→F→F`) | 0.704 | **0.719** | [0.69, 0.74] | **+0.197 ✓** | **+0.270 ✓** |
| 8× GEPA g05_00 (crowned champ) | 0.809 | 0.598 | [0.48, 0.72] | +0.077 ✓(pooled) | +0.150 ✓ |
| 8× GEPA g03_00 | 0.574 | 0.527 | [0.41, 0.62] | +0.005 (≈tie) | +0.078 ✓ |
| **8× CORE g04_00** (`D→D→C→F→C→F→C→F`) | 0.631 | **0.346** | [0.20, 0.48] | −0.176 ✗ | −0.103 ✗ |
| 8× CORE gen0 (balanced_crit) | 0.407 | 0.302 | [0.20, 0.40] | ✗ | ✗ |
| **4× GEPA g04_02** (`D→F→F→F`) | 0.504 | **0.231** | [0.11, 0.37] | −0.291 ✗ | −0.218 ✗ |
| 4× CORE g02_02 (`D→D→D→F`) | 0.437 | 0.393 | [0.29, 0.48] | −0.129 ✗ | −0.056 ✗ |

✓ = champion's CI beats the bar; ✗ = below it. R=8 for all except the 3 GEPA-8x finalized at R=7 (the re-eval's
8th replicate stalled; 7 reps already robust).

### Bottom line (honest)
- **At 8×, the evolved Haiku pipeline genuinely beats the frontier.** Best champion `g04_00` = **0.719 [0.69,
  0.74]** — its CI lower bound (0.693) sits *above* Opus's CI upper bound (0.595), so it robustly beats
  single-shot **Opus** (0.522), **Sonnet** (0.442), and **best-of-8** (0.449). Two GEPA-8x champions clear Opus.
  Won via **draft-prompt** evolution (articulation-point/cut-vertex trap detection + pessimistic flood-fill) on
  a 4-drafts-then-4-fixes structure.
- **At 4×, evolved Haiku does NOT reach the frontier** once de-inflated (0.231) — the R=3 "parity" was an
  artifact. Original R=3 champion was `D→F→F→F` with an evolved fix prompt incl. a no-op regression guard.
- **CORE was selection-inflated and collapses below best-of-N** at both budgets (8× 0.631→0.346; 4× 0.437→0.393).
- **GEPA ≫ CORE** under honest evaluation, consistent with the rest of the study.
- Original (inflated) R=3 curves for reference: GEPA-8x 0.448·0.448·0.481·0.574·0.704·0.809; CORE-8x
  0.407·0.407·0.407·0.407·0.631.

### Decoupled-admit re-runs (IN PROGRESS — to be appended)
Re-running 4× GEPA then CORE with a **decoupled gate** (explore offspring at R=3, re-evaluate parent-beaters at
R=8 fresh, admit only on the robust R=8 comparison; gen0 seeds at R=4) — directly removes the selection
inflation, and gives CORE reliable contrastive pairs (its `form_pairs` then runs on R=8 fitnesses, not noise).
Dirs `cc_pipe_dec_{gepa,core}`. Results pending; append champion R=8 fitness + whether robust selection yields
genuinely-better champions than the inflated runs.

---

## Prior experiments (headline numbers; details in `results/data/prior/`)

| Experiment | Setup | Result |
|---|---|---|
| `cc_decomp` (GEPA) vs `cc_core` (CORE) | evolve a nested multi-agent decomposition harness (planner + specialists + referee); 4-rung ladder incl. a Sonnet-refinement rung; champion scored at sims=1500 | GEPA champion `g03_02`: weak **0.789** / moderate **0.516** / strong **0.473** / sonnet-rung **0.689** (3-rung ladder ≈ 0.59). CORE ~0.45 — but **confounded** by CPU-contention scoring + Haiku variance. *Full analyzed output preserved at `results/` top-level (gen_00–04, `analysis.md`, `final/headline.json`).* Note: different ladder + fitness definition than cc_pipe — not directly comparable. |
| `cc_alloc` | evolve a budget-B typed-call allocation (best-of-N / revise / decompose) | small search space → **no climb** |
| `cc_prompt` | evolve a single generator prompt (cheapest harness) | weak ~0.2 baseline → **big climb (+0.25)**; GEPA **+0.246** > CORE **+0.165** (gen6, K=3) — the cleanest GEPA>CORE result |
| `cc_hpe` | evolve 4 role-prompts of a decomposition harness | large space but **strong ~0.5 baseline → ~no climb** (+0.00–0.01) |

---

## Methodological findings (the transferable lessons)
1. **Headroom, not search-space size, predicts whether reflective evolution climbs.** Weak baseline (high
   headroom) → big climb (`cc_prompt`, 4× pipe); strong baseline (low headroom) → little (`cc_hpe`).
2. **Budget raises the achievable ceiling.** The single-shot frontier (~0.50) is not the ceiling — the ladder
   admits ~0.7+ with a strong bot, and 8 calls give evolution enough refinement headroom to exceed the frontier;
   4 calls top out lower.
3. **Selection inflation (optimizer's curse) is large with noisy fitness.** R=3 champions inflated by ~0.1–0.3;
   de-inflate with an independent higher-R re-eval. Prefer a **decoupled admit** (cheap explore + robust
   re-eval of parent-beaters).
4. **Haiku realization variance dominates.** A single pipeline's output ranges ~0.0–0.86 across fresh draws;
   tight-looking R=3 spreads can still be lucky. Use R≥7 for any claim.
5. **GEPA ≥ CORE wherever there's a climb.** GEPA is natively a prompt/system-evolution method (home turf for
   harness evolution); CORE (a test-time contrastive-reasoning *memory*) is repurposed here, and its contrastive
   signal is degraded by noisy fitness. CORE's truer native use is at the *inner* (bot-writing) level — a future
   experiment.
6. **Engineering:** clean low-concurrency scoring (heavy bots miss the 500 ms deadline under contention →
   spurious 0.0s); workflows are capped at 1000 agents (run sequentially / chunk, don't fan out 11 heavy
   genotypes at once); catch-and-retry transient StructuredOutput flakes.

---

## Layout of `results/`
- `RESULTS.md` — this consolidated, honest cross-experiment reference (the thing to read).
- **Top-level `gen_00`–`gen_04/`, `ladder/`, `analysis.md`, `config.json`, `final/headline.json`** — the *pre-existing* full output of the **`cc_decomp`** decomposition-harness run (champion `g03_02`; from `codeclash-evolution/cc_decomp_evo`). This was already here; left in place.
- `data/` — preserved machine-readable artifacts from the cc_pipe study (copied out of the gitignored/transient run dirs):
  - `cc_pipe_reeval_report.json` — the de-inflation re-eval (all champions + bars at R=7/8/12, with comparisons).
  - `cc_pipe_8x_baselines.json` — 8× gate (R=5): true single-shot Haiku/Sonnet/Opus + best-of-8 + refine-8.
  - `cc_pipe_4x_baselines_BUGGY.json` — the mislabeled 4× gate (1-shots ran as refine-4; kept for the record).
  - `cc_pipe_evo_{gepa,core}_final.json`, `cc_pipe_evo_8x_{gepa,core}_final.json` — per-run final-compare (R=3, pre-de-inflation).
  - `data/prior/` — COMPARISON.md / DESIGN.md from the earlier cc_core / cc_prompt / cc_hpe / cc_alloc experiments.
- *(to append)* decoupled-admit re-run artifacts (`cc_pipe_dec_{gepa,core}`) once those finish.

## What's NOT yet captured here (pending)
- The decoupled-admit 4× re-runs (in progress) — append their final-compare + champion R=8 fitness.
- The cc_pipe **champion genotypes themselves** (the evolved roles.json + prompts/*.md) — if you want to share
  the actual evolved pipelines, copy `cc_pipe_evo_8x_gepa/gen_04/genotypes/agent_g04_00/` (the 0.719 champion:
  D⁴F⁴ + its evolved draft prompt) into `results/data/`. Say the word and I'll stage the champion artifacts too.
