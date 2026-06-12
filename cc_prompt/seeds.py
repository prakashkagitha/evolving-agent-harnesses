"""Seed generation prompts for pure prompt evolution.

Each seed is a complete instruction to a small model (Haiku) to write ONE single-file BattleSnake bot.
They span distinct strategy framings (space-first, aggressive, growth, balanced, survival, minimal,
endgame, adaptive) so the population starts diverse and there is headroom to climb. Only this text
evolves; the bot contract is fixed (injected separately at generation time).
"""


def _g(pid, prompt):
    return {"id": pid, "prompt": prompt.strip(),
            "lineage": {"parent_id": None, "origin": "seed", "lens": None,
                        "changed_components": [], "diff": ""}}


def seed_prompts():
    return [
        _g("space_first",
           "Write a BattleSnake bot whose first priority is SPACE: every turn, estimate the reachable "
           "open area (flood-fill) after each candidate move and strongly prefer the move that keeps the "
           "most room; never enter a region smaller than your own length (a self-trap). Treat food as a "
           "top-up only when health is low. Above all, never move into a wall or any snake body."),

        _g("aggressive",
           "Write a BattleSnake bot that plays to ELIMINATE opponents. Predict enemy head moves; when you "
           "are strictly longer, move to contest the cell an enemy head could enter (you win that "
           "head-to-head); cut off enemies' escape routes. Never take a losing or tying head-to-head, and "
           "never move into a wall or body. Grow just enough to stay longer than rivals."),

        _g("forager",
           "Write a BattleSnake bot focused on GROWTH and health: path efficiently to the nearest safe "
           "food when health is not high, keep health comfortable, and use a length lead to survive late. "
           "Avoid pathing into dead-ends or food that sits in a pocket. Never move into a wall or body."),

        _g("balanced",
           "Write a BattleSnake bot that balances three concerns every move: keep reachable space "
           "(flood-fill), avoid losing head-to-heads (and take winning ones when strictly longer), and "
           "manage food/health. Weigh them together; let space and safety dominate early and combat/"
           "pressure matter more late. Never move into a wall or body."),

        _g("survivor",
           "Write a BattleSnake bot that wins by OUTLASTING everyone. Play maximally safe: keep the most "
           "open space, strictly avoid dead-ends, hug the center over edges/corners, and take no "
           "unnecessary risks — let opponents make the fatal mistake. Eat only when health forces it. "
           "Never move into a wall or body."),

        _g("minimal",
           "Write a simple, robust BattleSnake bot: each turn pick any move that does not hit a wall or a "
           "snake body, preferring moves that head toward open space and toward food when health is low. "
           "Keep it short and crash-proof."),

        _g("endgame",
           "Write a BattleSnake bot built for the late-game duel: early, keep space and grow safely; once "
           "few snakes remain, when you are longer, pressure the opponent and shrink its space, and when "
           "shorter, stall safely toward the center and wait for it to err. Never move into a wall or body."),

        _g("adaptive",
           "Write a BattleSnake bot that adapts to the board: do a shallow look-ahead, estimate reachable "
           "space after each move, avoid losing head-to-heads, seek food only when behind on length or low "
           "on health, and avoid edges/corners and hazard cells that cut escape routes. Never move into a "
           "wall or body; always return a legal move fast."),
    ]
