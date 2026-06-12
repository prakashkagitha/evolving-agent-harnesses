"""Seed prompt-sets for harness-prompt evolution. Each seed is FOUR prompts: a brief for each of the
three fixed specialists (space_control, combat, food) + a referee/integration prompt. Seeds vary from
vague to concrete and use different integration strategies, so the population starts diverse with
headroom. Only this wording evolves; the per-specialist concern and the bot contract are fixed.
"""

CONCERNS = ["space_control", "combat", "food"]
ROLES = CONCERNS + ["referee"]


def _g(pid, space, combat, food, referee):
    return {"id": pid,
            "prompts": {"space_control": space.strip(), "combat": combat.strip(),
                        "food": food.strip(), "referee": referee.strip()},
            "lineage": {"parent_id": None, "origin": "seed", "lens": None,
                        "changed_components": [], "diff": ""}}


def seed_prompt_sets():
    return [
        _g("concrete",
           "Score each move by the number of reachable open cells from the resulting head (flood-fill, "
           "treating your tail as free unless you just ate). Hard-veto (-1e9) any move into a wall, a body, "
           "or a pocket smaller than your length.",
           "Hard-veto (-1e9) any move into a cell an equal-or-longer enemy head could also enter next turn. "
           "Give a positive bonus to a move that enters a cell only a strictly-shorter enemy head could "
           "enter (a winning head-to-head) or that cuts off an enemy's escape.",
           "Prefer moves toward the nearest safe food only when health < 50 or you are not the longest "
           "snake; otherwise stay neutral. Hard-veto walls/bodies and food sitting in a dead-end.",
           "Drop any move a specialist vetoes (score <= -5e8); among the rest, take the weighted sum of "
           "the specialists' scores and pick the highest, breaking ties toward more open space."),

        _g("vague",
           "Try to keep space and don't get trapped.",
           "Avoid bad head-to-heads and attack when you can.",
           "Eat food when you need to.",
           "Combine the specialists sensibly and pick a good safe move."),

        _g("space_heavy",
           "Maximise reachable open area with a careful flood-fill; veto self-trapping moves into pockets "
           "smaller than your length; strongly prefer the move that keeps the largest region.",
           "Veto only clearly-losing head-to-heads; otherwise stay out of the combat specialist's way.",
           "Only seek food when health is low; never path into a dead-end for food.",
           "Prioritise the space_control specialist's preference; use combat only to break ties and to "
           "veto losing head-to-heads; drop vetoed moves first."),

        _g("combat_heavy",
           "Keep enough room to survive (flood-fill); veto self-traps.",
           "Play to eliminate: predict enemy head moves, veto losing/tying head-to-heads, and aggressively "
           "contest cells a shorter enemy could enter or that cut its escape routes.",
           "Grow just enough to stay longer than rivals; seek food when behind on length.",
           "Lead with combat: take winning head-to-heads, then prefer space; drop any vetoed move."),

        _g("phase_referee",
           "Flood-fill reachable cells; veto pockets smaller than your length.",
           "Veto losing head-to-heads; bonus for winning ones.",
           "Seek nearest safe food when health<50 or not longest.",
           "Integrate by game phase: early, weight space and food; late (few snakes left), weight combat "
           "and space denial. Always drop vetoed moves and never pick a move into a body if a safe one exists."),

        _g("priority_referee",
           "Score reachable open space via flood-fill; veto self-traps and walls/bodies.",
           "Veto equal-or-longer head-to-heads; reward strictly-winning ones and cutting off escape.",
           "Path to nearest safe food when hungry/behind; veto dead-ends.",
           "Use a strict priority order: first drop vetoed moves, then pick by combat safety, then space, "
           "then food. Return the first surviving move in that order."),

        _g("growth",
           "Avoid trapping yourself; keep some open space via a quick reachable-area estimate.",
           "Avoid losing head-to-heads.",
           "Win the length race: path efficiently to safe food, keep health high, and use a length lead "
           "to dominate head-to-heads later.",
           "Favor the food specialist early to build a length lead, then weight space and combat; drop "
           "vetoed moves."),

        _g("balanced",
           "Estimate reachable space (flood-fill) and prefer roomy moves; veto self-traps.",
           "Veto losing head-to-heads, take winning ones, contest enemy escape.",
           "Manage food/health: seek food when low or behind, hold otherwise.",
           "Weighted vote across all three with roughly equal weight, leaning slightly to space and safety; "
           "always drop vetoed moves and never suicide into a body when a safe move exists."),
    ]
