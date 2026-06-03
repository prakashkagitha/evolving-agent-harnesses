# Ladder rung 0 (WEAK): a naive food-seeker. Avoids only immediate death
# (out-of-bounds and any snake-body cell, tails included = conservative/naive)
# and walks greedily toward the nearest food. NO flood-fill, NO head-to-head
# awareness, so it readily traps itself in confined space and loses head-on
# exchanges. Provides a bottom gradient so even weak harnesses score > 0.
# Fixed yardstick — never part of the evolving population.
import typing


def info() -> typing.Dict:
    return {"apiversion": "1", "author": "ladder-weak", "color": "#aaaaaa", "head": "default", "tail": "default"}


def start(game_state: typing.Dict):
    pass


def end(game_state: typing.Dict):
    pass


def move(game_state: typing.Dict) -> typing.Dict:
    board = game_state["board"]
    w, h = board["width"], board["height"]
    me = game_state["you"]
    head = (me["body"][0]["x"], me["body"][0]["y"])

    blocked = set()
    for s in board["snakes"]:
        for c in s["body"]:  # naive: treats every body cell (incl. tails) as solid
            blocked.add((c["x"], c["y"]))

    opts = {"up": (head[0], head[1] + 1), "down": (head[0], head[1] - 1),
            "left": (head[0] - 1, head[1]), "right": (head[0] + 1, head[1])}
    safe = {mv: c for mv, c in opts.items()
            if 0 <= c[0] < w and 0 <= c[1] < h and c not in blocked}
    if not safe:
        return {"move": "up"}

    foods = [(f["x"], f["y"]) for f in board.get("food", [])]
    if foods:
        def d2food(c):
            return min(abs(c[0] - fx) + abs(c[1] - fy) for fx, fy in foods)
        best = min(safe.items(), key=lambda kv: d2food(kv[1]))
        return {"move": best[0]}
    return {"move": next(iter(safe))}
