"""Budget-constrained allocation search: evolve (not enumerate) the best way to spend a fixed budget
of B LLM calls to write one BattleSnake bot. The genotype is a budget-B allocation (drafts /
specialists+merge / revisions) + the generator prompt; GEPA and CORE both search this space, and the
naive best-of-B allocation is the baseline they must beat. See DESIGN.md."""
