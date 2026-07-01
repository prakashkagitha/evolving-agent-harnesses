# Self-Harness on SWE-bench Verified

**A fixed Haiku model improved its own agent harness — with no weight updates and no stronger model — lifting resolution from 18/28 to 23/28 (+28%) by rebuilding its own scaffold from a single draft into a `draft → write_test → fix` loop.**

This is an instantiation of *Self-Harness* (Zhang et al. 2026, [arXiv:2606.09498](https://arxiv.org/abs/2606.09498)) on SWE-bench Verified using our Apptainer backend and TRUE `FAIL_TO_PASS + PASS_TO_PASS` resolution. Unlike our GEPA runs — where a **stronger** external model (Sonnet) mutates Haiku's harness (the paper's *Meta-Harness* baseline) — here the **same fixed Haiku model** improves the harness it runs inside.

All numbers and artifacts below are reproduced from the run in `cc_swe_selfharness/`; curated receipts are in [`results/self_harness/`](results/self_harness/).

---

## Headline result

Starting from a **minimal harness (a single `draft` step = 1-shot Haiku)**, three rounds of self-improvement produced:

| Round | Harness | Resolved (held-in, 28 issues) | The model's own change |
|---|---|---|---|
| h₀ | `draft` | 18/28 (64%) | — (minimal seed) |
| h₁ | `draft → fix` | 18/28 (64%) | added a refine step + a root-cause runtime policy |
| **h₂** | `draft → write_test → fix` | **23/28 (82%)** | added an independent reproduction-test step |
| h₃ | `draft → write_test → fix` | 23/28 (82%) | (round-3 candidates all rejected → carried forward) |

**+5 issues resolved (+28% relative), from harness self-edits alone — no fine-tuning, no gradient updates, no stronger model.**

---

## Why it works: correct self-diagnosis → correct self-repair

The result is not a lucky walk. Each round, Haiku (a) runs the current harness, (b) **clusters its own execution failures** into verifier-grounded patterns, and (c) **proposes bounded edits** that a two-split non-regression gate then accepts or rejects. The mined diagnosis in each round correctly motivates the next structural addition — *in the order a human designer would add them*:

(Rounds are 0-indexed to match the receipt filenames; round *t* mines `hₜ` and produces `hₜ₊₁`.)

- **Round 0 — mines `h₀` (single draft).** Dominant failure cluster (support **5**): *"fixes the symptom, not the root cause; fixes one component but misses others."* → The model adds a **`fix` step** and authors a root-cause runtime doctrine. → `h₁`.
- **Round 1 — mines `h₁` (`draft→fix`).** Dominant cluster (support **6**): *"patches pass without a reproduction test; verification doesn't enforce test creation."* → The model adds a **`write_test` step**. → `h₂`, the 18→23 jump.
- **Round 2 — mines `h₂` (`draft→write_test→fix`).** Cluster (support **2**): *"the reproduction test's coverage is incomplete."* → The model proposes test-quality refinements, but none beat `h₂`'s raised bar → all rejected → `h₃ = h₂`.

In sequence the model recognized, unaided: *I need to refine → I need an independent test to refine against → my test coverage is now the bottleneck.* It converged on the same `draft → write_test → fix` structure we had previously hand-designed.

Full per-round evidence bundles, candidate proposals (with the model's own `expected_effect` / `regression_risk`), and gate verdicts: [`results/self_harness/round{0,1,2}_mining.json`](results/self_harness/) and [`round{0,1,2}_proposals.json`](results/self_harness/).

---

## What actually evolved

### Structure
`draft` → `draft→fix` → `draft→write_test→fix`  ([`roles_evolution.json`](results/self_harness/roles_evolution.json))

### Runtime policy & instructions (`harness.json`, authored from empty)
The largest share of the improvement was **non-prompt**: the model wrote an entire root-cause discipline into the declared runtime surface.

- **`system_preamble`** — *"incomplete fixes that address symptoms without root causes will fail hidden tests … identify ALL affected code locations."*
- **`bootstrap`** — a 5-step pre-edit protocol (read full scope → search ALL affected locations → single vs coordinated change → outline root-cause changes → then minimal edits).
- **`verification`** (added at `h₂`) — *"Write an independent reproduction test … import and exercise the real public API, assert the specific behavioral contract, fail on incomplete fixes."*
- **`failure_recovery`** + **`error_middleware`** — on a test/tool error, re-examine symptom-vs-root-cause and look for other affected locations.
- **`runtime_policy`** — `max_tool_calls=100` (added at `h₁`), `redirect_after_calls=35` (added at `h₂`) to bound unproductive exploration.

Snapshots: [`harness_h{0,1,2}.json`](results/self_harness/).

### Prompts
Surgical: only `draft.md` and `fix.md` received one appended root-cause clause each; `write_test.md` and `critique.md` were left unchanged. Most of the model's "intelligence" went into **structure + runtime policy**, not prose. ([`prompt_evolution.json`](results/self_harness/prompt_evolution.json))

---

## How the loop is implemented

- **Controller:** `cc_swe/control_selfharness.py` — minimal-harness init, genotype cloning, the two-split non-regression gate (`accept iff d_in≥0 ∧ d_ho≥0 ∧ max>0`), disjoint-surface merge, round status.
- **Orchestration:** `cc_swe/workflow_swe_selfharness.js` — the 3-stage loop (Haiku miner → K=3 Haiku proposers → dual-split solve → gate → merge), resumable + cap-guarded.
- **Solving/scoring:** reuses `cc_swe/control_swe.py` (Apptainer, TRUE resolution). The editable surface (`harness.json`) is injected by pointing each agent at the file.

Reproduce: `Workflow(cc_swe/workflow_swe_selfharness.js, {proposer:"haiku", N:4, rounds:3, K:3, reuse_split:...})`.

---

## Caveats (scope of the claim)

- **The +5 is on the held-in set.** On a separately-curated held-out set, the evolved champion does **not** separate from 1-shot Haiku — so this is a demonstration of the **mechanism** (correct self-diagnosis → correct self-repair, unaided), not a generalization or frontier-beating result.
- **The in-loop gate ran at R=1.** The *structural* trajectory (D → D→F → D→W→F) is robust and legible; individual per-round resolution deltas carry single-draw noise (one accepted candidate's held-out delta was partly noise).
- **Held-in overfitting is visible:** train climbs 18→23 while a held-out measure stays flat — expected, and the reason the claim is scoped to the mechanism.
