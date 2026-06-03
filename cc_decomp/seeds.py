"""Seed harness genotypes for the single-level decomposition evolution.

A genotype has exactly TWO evolvable components:
  1. planner_prompt  — top-level strategy framing + how the planner briefs/decomposes
                       the work for the specialists.
  2. decomposition   — {specialists: subset of the fixed menu, referee_policy, tester, refine_rounds}.

Specialist coder prompts and the tester/debugger templates are FIXED (see harness.py); only the
two components above evolve. The 12 seeds vary BOTH components and span all three referee policies,
specialist subset sizes 1..5, tester on/off, and refine depth. A few are DELIBERATELY WEAK
(one specialist, no tester, shallow refine) so there is headroom to climb.
"""


def _g(aid, planner_prompt, specialists, referee_policy, tester, refine_rounds):
    return {
        "id": aid,
        "planner_prompt": planner_prompt.strip(),
        "decomposition": {
            "specialists": specialists,
            "referee_policy": referee_policy,
            "tester": tester,
            "refine_rounds": refine_rounds,
        },
        "lineage": {"parent_id": None, "origin": "seed", "lens": None,
                    "changed_components": [], "diff": ""},
    }


# REFINE depth for full seeds = the spec's REFINE_ROUNDS (4). Weak seeds use less.
def seed_genotypes(refine_rounds=4):
    R = refine_rounds
    return [
        _g("space_first",
           "Strategy: win by controlling space and never trapping yourself; survival over greed. "
           "Brief the space_control specialist to maximize reachable open area (flood-fill) and veto "
           "self-trapping moves; brief the food specialist to eat ONLY when health is low or you are "
           "behind on length, never into a dead-end. Space is the priority; food is a top-up.",
           ["space_control", "food"], "weighted_vote", True, R),

        _g("hunter",
           "Strategy: play aggressively to eliminate the opponent. Brief the combat specialist to win "
           "head-to-heads when strictly longer and to cut off the enemy's escape routes, while vetoing "
           "losing/tying exchanges; brief space_control to keep your own room; brief food to grow just "
           "enough to stay longer than the enemy. Combat decisions take priority over the rest.",
           ["combat", "space_control", "food"], "priority_order", True, R),

        _g("balanced",
           "Strategy: a balanced bot that weighs space, combat safety, and growth together. Brief "
           "space_control for flood-fill room, combat for head-to-head safety and opportunism, and food "
           "for measured growth. No single concern dominates — integrate them by weighted vote.",
           ["space_control", "combat", "food"], "weighted_vote", True, R),

        _g("forager",
           "Strategy: win length races. Brief the food specialist to path efficiently to the nearest "
           "safe food and keep health comfortable; brief space_control to avoid trapping yourself while "
           "foraging. Use a length lead to survive late. Growth-first, space as a guard.",
           ["food", "space_control"], "weighted_vote", False, max(2, R - 1)),

        _g("survivor",
           "Strategy: outlast everyone by playing safe. Brief space_control to strictly avoid dead-ends "
           "and keep maximum room; brief hazard to avoid edges/corners and hazard cells that cut escape "
           "routes. Take no unnecessary risks; let opponents make the fatal mistakes. Safety is priority.",
           ["space_control", "hazard"], "priority_order", True, R),

        _g("generalist",
           "Strategy: a complete bot using every concern. Brief space_control (room), combat (head-to-"
           "head), food (growth/health), endgame (late-game duel control), and hazard (edge/hazard "
           "safety). Have the planner_merge referee integrate all five intelligently: drop vetoed moves, "
           "then favor space and safe growth early, combat/endgame pressure late.",
           ["space_control", "combat", "food", "endgame", "hazard"], "planner_merge", True, R),

        _g("duelist",
           "Strategy: built for the 1v1 endgame. Brief combat for head-to-head dominance, endgame for "
           "shrinking the opponent's space when you are longer (and stalling safely when shorter), and "
           "space_control to keep your own room. Weigh them so late-game pressure is decisive.",
           ["combat", "endgame", "space_control"], "weighted_vote", True, R),

        # ---- deliberately WEAK seeds (headroom) ----
        _g("minimal_space",
           "Strategy: just don't trap yourself. Brief the single space_control specialist to keep the "
           "most reachable open space and veto self-traps. Nothing else.",
           ["space_control"], "weighted_vote", False, 2),

        _g("minimal_food",
           "Strategy: just chase food and stay alive. Brief the single food specialist to head to the "
           "nearest food while avoiding walls and bodies. Nothing else.",
           ["food"], "priority_order", False, 2),

        _g("reckless",
           "Strategy: grab food and fight, worry less about space. Brief combat to contest the enemy and "
           "food to grow fast. Accept some risk to apply pressure.",
           ["combat", "food"], "weighted_vote", False, 1),

        # ---- more full seeds ----
        _g("cartographer",
           "Strategy: dominate the board by territory. Brief space_control for maximal Voronoi room and "
           "endgame for converting a space advantage into a win late. Have the planner_merge referee "
           "prefer the move that keeps the largest safe region while denying the opponent room.",
           ["space_control", "endgame"], "planner_merge", True, R),

        _g("tactician",
           "Strategy: adapt to the board with a wide view. Brief space_control (room), combat (head-to-"
           "head safety/opportunity), food (measured growth), and hazard (avoid edge/hazard traps). "
           "Integrate by weighted vote, leaning on space and safety but taking winning fights.",
           ["space_control", "combat", "food", "hazard"], "weighted_vote", True, R),
    ]


# Generic planner prompt for the simple-refinement ablation + the Sonnet rung (NO decomposition).
SIMPLE_PLANNER_PROMPT = (
    "Write the strongest single-file BattleSnake bot you can: combine flood-fill space control, "
    "head-to-head avoidance (and opportunism when strictly longer), and measured food/health "
    "management into one fast, crash-proof move() function."
)
