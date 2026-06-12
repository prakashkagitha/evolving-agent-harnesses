"""Harness-prompt evolution (cc_hpe): evolve ALL the role-prompts of a multi-agent decomposition
harness at once — a brief per specialist + a referee/integration prompt — for a fixed strong
3-specialist structure (space_control, combat, food). The genotype is FOUR large free-text prompts
(a genuinely large search space, vs the single prompt in cc_prompt and the tiny integer allocation in
cc_alloc). GEPA vs CORE. See DESIGN.md. Reuses cc_prompt (R-replicate eval + two-sample gate),
cc_alloc.recipe (decomposition assembly), cc_decomp (scoring/select/finalize) and cc_core (bank)."""
