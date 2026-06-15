"""cc_pipe — a TYPED SELF-CORRECTION PIPELINE as the evolvable harness, and the Haiku->Sonnet PoC.

Genotype = a pipeline of N steps (budget = N LLM calls): each step has a role in {draft, critique, fix}
(step 0 is always draft) and a free-text prompt per role. BOTH the structure (the role sequence) and
the prompts evolve. Execution is a keep-best chain: draft/fix produce a scored candidate (the best is
tracked); critique reads the current best + ENGINE FEEDBACK (in-process rule checks via
harness.eval_on_boards: out-of-bounds / body-collision / losing head-to-head / crash) and writes a
diagnosis the next fix consumes. Fitness = mean ladder win-rate of the final (best) bot over R
replicate executions; verified two-sample gate (reused from cc_prompt).

The point: a harness's value over best-of-N is *targeted self-correction using engine feedback*. The
PoC asks whether an evolved pipeline lets Haiku reach single-shot Sonnet at a fixed call budget, and
beat the naive same-budget baselines (best-of-N, blind refinement). See DESIGN.md.
"""
