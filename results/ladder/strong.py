# Ladder rung 2 (STRONG): a genuinely good hand-written bot — tail-aware
# flood-fill space control + head-to-head modeling (avoid losing/tying exchanges,
# take winning ones when strictly longer) + a space>=length trap guard + measured
# food/health logic. This rung supplies the HEADROOM the prior run lacked: round-0
# evolved bots should sit well below it. Clearly stronger than the greedy moderate
# rung. Fixed yardstick — never part of the evolving population.
import typing

_DIRS = {"up": (0, 1), "down": (0, -1), "left": (-1, 0), "right": (1, 0)}


def info() -> typing.Dict:
    return {"apiversion": "1", "author": "ladder-strong", "color": "#cc2222", "head": "evil", "tail": "bolt"}


def start(game_state: typing.Dict):
    pass


def end(game_state: typing.Dict):
    pass


def _blocked_cells(board):
    """Solid cells next turn. A snake's tail vacates unless it just ate
    (engine duplicates the last segment the turn after eating: body[-1]==body[-2])."""
    blocked = set()
    for s in board["snakes"]:
        body = s["body"]
        pts = [(c["x"], c["y"]) for c in body]
        just_ate = len(pts) >= 2 and pts[-1] == pts[-2]
        keep = pts if just_ate else pts[:-1]  # drop the tail if it will move
        for p in keep:
            blocked.add(p)
    return blocked


def _flood(start_cell, blocked, w, h, cap=121):
    if not (0 <= start_cell[0] < w and 0 <= start_cell[1] < h) or start_cell in blocked:
        return 0
    seen = {start_cell}
    stack = [start_cell]
    n = 0
    while stack and n < cap:
        x, y = stack.pop()
        n += 1
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            c = (x + dx, y + dy)
            if 0 <= c[0] < w and 0 <= c[1] < h and c not in blocked and c not in seen:
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

    blocked = _blocked_cells(board)

    # head-to-head risk map: cells an equal-or-longer enemy head could step into
    # next turn (we lose or tie if we also move there). Strictly-shorter enemies
    # are not a threat — stepping onto their projected cell would win for us.
    threat = set()
    enemy_heads_shorter = set()
    for s in board["snakes"]:
        if s["id"] == me["id"]:
            continue
        ehead = (s["body"][0]["x"], s["body"][0]["y"])
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            c = (ehead[0] + dx, ehead[1] + dy)
            if s["length"] >= mylen:
                threat.add(c)
            else:
                enemy_heads_shorter.add(c)

    foods = [(f["x"], f["y"]) for f in board.get("food", [])]
    longest_other = max((s["length"] for s in board["snakes"] if s["id"] != me["id"]), default=0)
    want_food = health < 45 or mylen <= longest_other or mylen <= 4

    def d2food(c):
        if not foods:
            return 99
        return min(abs(c[0] - fx) + abs(c[1] - fy) for fx, fy in foods)

    cands = []
    for mv, (dx, dy) in _DIRS.items():
        c = (head[0] + dx, head[1] + dy)
        if not (0 <= c[0] < w and 0 <= c[1] < h) or c in blocked:
            continue
        space = _flood(c, blocked, w, h)
        risky = c in threat
        kill = c in enemy_heads_shorter  # we could win a head-to-head here
        cands.append({"mv": mv, "cell": c, "space": space, "risky": risky,
                      "kill": kill, "food": d2food(c)})

    if not cands:
        for mv, (dx, dy) in _DIRS.items():
            c = (head[0] + dx, head[1] + dy)
            if 0 <= c[0] < w and 0 <= c[1] < h:
                return {"move": mv}
        return {"move": "up"}

    # prefer non-risky moves with enough room (space >= our length avoids self-traps)
    safe = [c for c in cands if not c["risky"]]
    pool = safe or cands
    roomy = [c for c in pool if c["space"] >= mylen]
    pool = roomy or pool

    max_space = max(c["space"] for c in pool)

    def rank(c):
        # 1) win a head-to-head when it's also roomy; 2) maximize reachable space
        # (trap-avoidance); 3) approach food when we want it.
        space_ok = c["space"] >= 0.6 * max_space
        if want_food:
            return (-(1 if c["kill"] and space_ok else 0), c["food"], -c["space"])
        return (-(1 if c["kill"] and space_ok else 0), -c["space"], c["food"])

    pool.sort(key=rank)
    return {"move": pool[0]["mv"]}
