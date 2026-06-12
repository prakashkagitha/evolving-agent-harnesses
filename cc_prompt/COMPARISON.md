# Pure prompt evolution — GEPA vs CORE

The simplest study of the optimizer: evolve ONLY the bot-generation prompt; the cheapest harness (one
Haiku call writes the whole bot); a prompt's fitness = mean ladder win-rate over R=5 single-shot bots
(variance control); verified gate = two-sample bootstrap over child-prompt vs parent-prompt bot
distributions. Same fixed ladder (weak/moderate/strong), clean scoring (MAXW≤16), pop 8 × 4 gens.

## Headline: prompt evolution WORKS (unlike allocation search)

Within-run, R=5 @ 100 sims (the runs' own clean scoring):

| | gen-0 best prompt | evolved champion | improvement | per-rung (champion) |
|---|---|---|---|---|
| **GEPA** | `minimal` 0.207 | `g02_01` **0.308** | **+0.101 (+49%)** | weak 0.54 / mod 0.20 / strong 0.18 |
| **CORE** | `aggressive` 0.238 | `g04_01` **0.273** | **+0.035 (+15%)** | weak 0.49 / mod 0.17 / strong 0.15 |

**Both optimizers verifiably improved the prompt** — and the champion is an *evolved* prompt, not a
seed. This is the cleanest evolutionary result in the project: the prompt is a large search space with
real headroom, so reflection-driven search genuinely climbs (contrast the allocation experiment, where
the space was small + variance-dominated and champions were seeds).

GEPA's gains land hardest exactly where the winning edit aimed — moderate and **strong** (0.064 → 0.182,
~3×) — the rungs where head-to-head play decides games.

## Both converged on the SAME key insight: explicit head-to-head rules

- **GEPA** (gen 2, `concept` lens, +0.10): *"Added head-to-head collision avoidance: exclude moves into
  cells reachable by an equal-or-longer enemy snake next turn."* (gen 1 was a `strategy` reframe, +0.07.)
- **CORE** (gen 4, applying bank insights L038+L040): *"added explicit head-to-head safety rule (avoid
  enemy-head cells unless strictly longer) and offensive win condition."*

Independently, from opposite mechanisms, both found that **telling the small model the concrete
head-to-head rule** is the single most valuable prompt change. (In the harness experiments the analogous
convergence was "add a combat specialist" — same underlying truth, surfaced again.)

## How each optimizer behaved

- **GEPA**: climbed early and decisively (gen 1 → gen 2), then plateaued (gen 3–4 admitted nothing).
  1/4 admitted in gen 1 (`strategy`) and gen 2 (`concept`); the other lenses regressed. Stateless,
  efficient, found the win fast.
- **CORE**: flat for three generations, then admitted 2/4 in gen 4 — slower to convert, but accumulated
  a **rich, interpretable insight bank** (63 insights, 9 verified wins). The highest-utility insights are
  genuine prompt-engineering wisdom: *"name the exact metric to compute (flood-fill reachable cells),"*
  *"give a concrete numerical threshold,"* *"name the offensive win condition explicitly,"* and the meta
  insight *"limit prompt complexity to what one small model can reliably implement."* The bank is a
  reusable artifact GEPA does not produce.

## Verdict (honest)

- **Prompt evolution is effective for both optimizers** — the headline positive result.
- **GEPA climbed more here (+0.101 vs +0.035), and earlier.** But this is **n=1 run per optimizer** and
  Haiku realization variance is large — the two even started from *different* gen-0 champions (0.207 vs
  0.238). So the magnitude gap is **confounded**, not a clean "GEPA > CORE." What is robust: both
  verifiably improved the prompt, and both found the same head-to-head insight.
- **CORE's distinctive value is the interpretable, reusable bank**; GEPA's is speed/efficiency. This
  mirrors the harness findings.

### Caveats
- n=1 evolutionary run each; ≥3 seeds needed to put CIs on the GEPA-vs-CORE gap (variance is large).
- Absolute fitness is low (~0.2–0.3) because the harness is the cheapest possible (1 call/bot, no
  revision) — single-shot Haiku bots are weak. The clean result is the *evolutionary climb* (relative).
- The offline high-sim `final-compare` hangs (an occasionally-slow Haiku `move()` stalls its BotServer
  past the 500 ms deadline, so high game counts crawl); the within-run R=5 @ 100-sim scores above are
  clean and sufficient. Cap any re-scoring at ≤~400 sims with a timeout.

### Next
This was the planned first step (prompt only). Next: harness evolution — add a small amount of compute
(e.g. 1 draft + a few revisions, or the budget-allocation genotype) on top of the prompt, and study
whether GEPA/CORE can spend that compute well — now that we know the prompt lever alone gives a clean,
climbing signal.

---
## DECISIVE multi-seed result (K=3 seeds × 6 generations)

Within-run improvement (champion − gen-0-best):

| seed | GEPA Δ | CORE Δ |
|---|---|---|
| 0 | +0.243 (0.216→0.459) | +0.097 (0.215→0.312) |
| 1 | +0.346 (0.266→0.612) | +0.152 (0.259→0.411) |
| 2 | +0.148 (0.285→0.433) | +0.247 (0.194→0.441) |
| **mean ± sd** | **+0.246 ± 0.099** | **+0.165 ± 0.076** |

Absolute champion fitness: GEPA mean **0.50** (0.46/0.61/0.43) vs CORE mean **0.39** (0.31/0.41/0.44).

**Verdict: GEPA is the better optimizer here (moderate confidence)** — ~1.5× higher mean improvement,
higher ceiling, wins 2/3 seeds by large margins (CORE's seed-2 win is modest). NOT a statistical blowout:
n=3 distributions overlap (Welch t≈1.1, p≈0.3); the large Haiku realization variance makes p<0.05
infeasible without ~20 runs/arm. GEPA front-loads big gains early (gen 1–2 + a late jump); CORE climbs
gradually as its insight bank compounds (gens 3–5) and so benefits more from extra generations. Both
ALWAYS improve (all 6 runs +0.10 to +0.35) and both converge on "add explicit head-to-head rules."
