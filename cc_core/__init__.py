"""CORE (Contrastive Reflection) as a drop-in alternative to GEPA for evolving the
nested BattleSnake decomposition harness.

Everything about the EXPERIMENT is shared with cc_decomp (genotype, harness assembly, fixed
opponent ladder, ablations, verified-acceptance gate, scoring, final eval) so the GEPA-vs-CORE
comparison is apples-to-apples. ONLY the breeding operator differs:

  GEPA  : reflect on ONE parent's failures through 4 fixed lenses -> direct mutation (stateless).
  CORE  : CONTRASTIVE reflection on winner-vs-loser harness pairs from the tournament -> distil
          compact natural-language LESSONS (specific/meta) into a persistent, utility-weighted
          LESSON BANK; each mutation is conditioned on the top-K lessons retrieved for the
          parent's weakness; verified-acceptance outcomes credit the lessons that were used
          (admitted -> win, rejected -> use), which drives UCB retrieval. Memory compounds.
"""
