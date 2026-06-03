import math
from collections import deque


def info():
    return {
        "apiversion": "1",
        "author": "sonnet-strong",
        "color": "#1a1a2e",
        "head": "default",
        "tail": "default",
    }


def start(game_state):
    pass


def end(game_state):
    pass


def move(game_state):
    try:
        return _move(game_state)
    except Exception:
        return {"move": "up"}


def _move(game_state):
    board = game_state["board"]
    me = game_state["you"]
    width = board["width"]
    height = board["height"]

    head = me["body"][0]
    hx, hy = head["x"], head["y"]
    my_length = me["length"]
    my_health = me["health"]
    my_id = me["id"]

    direction_map = {
        "up": (0, 1),
        "down": (0, -1),
        "left": (-1, 0),
        "right": (1, 0),
    }

    def in_bounds(x, y):
        return 0 <= x < width and 0 <= y < height

    # Build time-aware occupancy: for each cell, how many turns until it's free
    cell_free_at = {}  # (x,y) -> turn at which cell becomes free (0 = already free)
    snakes = board["snakes"]
    for snake in snakes:
        body = snake["body"]
        n = len(body)
        tail_stays = (n >= 2 and body[-1]["x"] == body[-2]["x"] and body[-1]["y"] == body[-2]["y"])
        for i, seg in enumerate(body):
            pos = (seg["x"], seg["y"])
            idx_from_tail = n - 1 - i
            free_turn = idx_from_tail
            if i == n - 1 and tail_stays:
                free_turn = idx_from_tail + 1
            if pos not in cell_free_at or cell_free_at[pos] > free_turn:
                cell_free_at[pos] = free_turn

    # Standard occupied set (cells blocked at turn 0 / next turn)
    occupied = set()
    for pos, ft in cell_free_at.items():
        if ft >= 1:  # still occupied next turn
            occupied.add(pos)

    food_set = set()
    for f in board["food"]:
        food_set.add((f["x"], f["y"]))

    # Gather enemy heads for head-to-head analysis
    enemy_heads = []
    for snake in snakes:
        if snake["id"] == my_id:
            continue
        eh = snake["body"][0]
        enemy_heads.append((eh["x"], eh["y"], snake["length"]))

    # Cells where an enemy head could move next turn (dangerous if we are <= their length)
    enemy_next_dangerous = set()
    for (ex, ey, elen) in enemy_heads:
        if elen >= my_length:
            for dx, dy in direction_map.values():
                nx, ny = ex + dx, ey + dy
                if in_bounds(nx, ny):
                    enemy_next_dangerous.add((nx, ny))

    # Cells where enemy heads of equal/larger size could reach in 2 steps (zone of concern)
    enemy_2step_dangerous = set()
    for (ex, ey, elen) in enemy_heads:
        if elen >= my_length:
            for dx1, dy1 in direction_map.values():
                nx1, ny1 = ex + dx1, ey + dy1
                if not in_bounds(nx1, ny1):
                    continue
                for dx2, dy2 in direction_map.values():
                    nx2, ny2 = nx1 + dx2, ny1 + dy2
                    if in_bounds(nx2, ny2):
                        enemy_2step_dangerous.add((nx2, ny2))

    # Cells where an enemy head could move for opportunistic kill
    enemy_next_killable = set()
    for (ex, ey, elen) in enemy_heads:
        if elen < my_length:
            for dx, dy in direction_map.values():
                nx, ny = ex + dx, ey + dy
                if in_bounds(nx, ny):
                    enemy_next_killable.add((nx, ny))

    def time_aware_flood_fill(start_x, start_y, blocked_initial):
        """BFS flood fill that accounts for snake bodies freeing over time.
        Returns (count, steps_to_nearest_food).
        """
        visited = set()
        visited.add((start_x, start_y))
        q = deque()
        q.append((start_x, start_y, 1))  # (x, y, turn_we_arrive)
        count = 0
        nearest_food = None
        while q:
            cx, cy, turn = q.popleft()
            count += 1
            if (cx, cy) in food_set and nearest_food is None:
                nearest_food = turn - 1
            for dx, dy in direction_map.values():
                nx, ny = cx + dx, cy + dy
                if not in_bounds(nx, ny):
                    continue
                if (nx, ny) in visited:
                    continue
                pos = (nx, ny)
                free_turn = cell_free_at.get(pos, 0)
                next_turn = turn + 1
                if free_turn >= next_turn and pos in blocked_initial:
                    continue
                if free_turn >= next_turn:
                    continue
                visited.add(pos)
                q.append((nx, ny, next_turn))
        return count, nearest_food

    # Evaluate each candidate move
    candidates = []
    for direction, (dx, dy) in direction_map.items():
        nx, ny = hx + dx, hy + dy

        # Hard filter: out of bounds
        if not in_bounds(nx, ny):
            continue

        # Hard filter: body collision
        if (nx, ny) in occupied:
            continue

        # Will we eat at this move?
        will_eat = (nx, ny) in food_set

        # Update cell_free_at for flood fill after our move
        my_body = me["body"]
        my_tail = (my_body[-1]["x"], my_body[-1]["y"])
        my_second_last = (my_body[-2]["x"], my_body[-2]["y"]) if len(my_body) >= 2 else None
        my_tail_stays = (my_second_last is not None and my_tail == my_second_last)

        # Build modified blocked for this move
        new_blocked = set(occupied)
        if not will_eat and not my_tail_stays:
            new_blocked.discard(my_tail)
        new_blocked.add((nx, ny))

        space, food_dist = time_aware_flood_fill(nx, ny, new_blocked)

        # Danger level from head-to-head
        is_dangerous = (nx, ny) in enemy_next_dangerous
        is_killable = (nx, ny) in enemy_next_killable
        is_2step_danger = (nx, ny) in enemy_2step_dangerous

        candidates.append({
            "direction": direction,
            "nx": nx,
            "ny": ny,
            "space": space,
            "food_dist": food_dist,
            "is_dangerous": is_dangerous,
            "is_killable": is_killable,
            "is_2step_danger": is_2step_danger,
            "will_eat": will_eat,
        })

    if not candidates:
        return {"move": "up"}

    # Hard filter: remove head-to-head dangerous moves if safe alternatives exist
    safe_candidates = [c for c in candidates if not c["is_dangerous"]]
    if safe_candidates:
        # Use only safe candidates
        eval_candidates = safe_candidates
    else:
        # All moves are dangerous — pick least bad
        eval_candidates = candidates

    # Scoring function
    def score(c):
        s = 0.0

        # Space control is primary — prefer larger reachable area
        s += c["space"] * 10.0

        # Head-to-head: seek kills (dangerous already filtered out above)
        if c["is_killable"]:
            s += 200.0

        # Mild penalty for 2-step danger zones (prefer to stay away from large enemies)
        if c["is_2step_danger"]:
            s -= 30.0

        # Food: seek it when health is low, be neutral when healthy
        health_urgency = max(0.0, (50 - my_health) / 50.0)  # 0 at health>=50, 1 at health=0
        if c["food_dist"] is not None:
            # Closer food is better when urgent
            food_score = health_urgency * (30.0 / (c["food_dist"] + 1))
            s += food_score
        elif health_urgency > 0.5:
            # No food reachable but we need it badly
            s -= 100.0 * health_urgency

        # Slight preference for eating if very low health
        if c["will_eat"] and my_health < 30:
            s += 150.0
        elif c["will_eat"] and my_health < 60:
            s += 30.0

        # Penalize very small space (potential trap)
        if c["space"] < my_length:
            s -= 300.0
        elif c["space"] < my_length * 1.5:
            s -= 50.0

        return s

    eval_candidates.sort(key=score, reverse=True)
    best = eval_candidates[0]
    return {"move": best["direction"]}
