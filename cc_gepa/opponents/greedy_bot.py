# Moderate-skill fixed benchmark opponent for inner-GEPA fitness.
# Survives (avoids walls, self, other bodies), prefers the move with the most
# reachable space (flood fill), and heads toward the nearest food when hungry.
# Deterministic given board state (no randomness) so the inner learning curve is
# a clean signal. NOT part of the evolving population — a fixed yardstick.
import typing


def info() -> typing.Dict:
    return {"apiversion": "1", "author": "bench", "color": "#3344cc", "head": "default", "tail": "default"}


def start(game_state: typing.Dict):
    pass


def end(game_state: typing.Dict):
    pass


def _neighbors(p):
    x, y = p
    return {"up": (x, y + 1), "down": (x, y - 1), "left": (x - 1, y), "right": (x + 1, y)}


def _flood(start_cell, blocked, w, h, cap=200):
    if start_cell in blocked or not (0 <= start_cell[0] < w and 0 <= start_cell[1] < h):
        return 0
    seen = {start_cell}
    stack = [start_cell]
    n = 0
    while stack and n < cap:
        cx, cy = stack.pop()
        n += 1
        for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
            c = (nx, ny)
            if 0 <= nx < w and 0 <= ny < h and c not in blocked and c not in seen:
                seen.add(c)
                stack.append(c)
    return n


def move(game_state: typing.Dict) -> typing.Dict:
    board = game_state["board"]
    w, h = board["width"], board["height"]
    me = game_state["you"]
    head = (me["body"][0]["x"], me["body"][0]["y"])
    health = me["health"]
    mylen = me["length"]

    blocked = set()
    for s in board["snakes"]:
        body = s["body"]
        for c in body[:-1]:  # tail will move (unless it just ate); treat body[:-1] as solid
            blocked.add((c["x"], c["y"]))
        blocked.add((body[-1]["x"], body[-1]["y"]))
        # avoid squares adjacent to equal/longer enemy heads (head-to-head risk)
        if s["id"] != me["id"] and s["length"] >= mylen:
            ehx, ehy = body[0]["x"], body[0]["y"]
            for ax, ay in ((ehx + 1, ehy), (ehx - 1, ehy), (ehx, ehy + 1), (ehx, ehy - 1)):
                blocked.add((ax, ay))

    nbrs = _neighbors(head)
    candidates = []
    for mv, cell in nbrs.items():
        if not (0 <= cell[0] < w and 0 <= cell[1] < h):
            continue
        if cell in blocked:
            continue
        space = _flood(cell, blocked, w, h)
        candidates.append((mv, cell, space))

    if not candidates:
        # no safe move; try any in-bounds (better than guaranteed wall)
        for mv, cell in nbrs.items():
            if 0 <= cell[0] < w and 0 <= cell[1] < h:
                return {"move": mv}
        return {"move": "up"}

    foods = [(f["x"], f["y"]) for f in board.get("food", [])]
    want_food = (health < 50 or mylen <= 4) and foods

    def dist_to_food(cell):
        if not foods:
            return 0
        return min(abs(cell[0] - fx) + abs(cell[1] - fy) for fx, fy in foods)

    max_space = max(c[2] for c in candidates)
    # keep moves whose reachable space is at least 70% of the best (don't trap self)
    viable = [c for c in candidates if c[2] >= 0.7 * max_space]
    if want_food:
        viable.sort(key=lambda c: (dist_to_food(c[1]), -c[2]))
    else:
        viable.sort(key=lambda c: (-c[2], dist_to_food(c[1])))
    return {"move": viable[0][0]}


if __name__ == "__main__":
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from cc_gepa.botserver import main
    main()
