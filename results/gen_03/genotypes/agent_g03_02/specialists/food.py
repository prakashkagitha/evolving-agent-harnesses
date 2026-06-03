def score(game_state) -> dict:
    try:
        board = game_state.get("board", {})
        you = game_state.get("you", {})
        your_head = tuple(you["body"][0].values())
        your_length = you.get("length", 1)
        your_health = you.get("health", 100)
        width, height = board.get("width", 11), board.get("height", 11)
        food = [tuple(f.values()) for f in board.get("food", [])]
        snakes = board.get("snakes", [])
        max_enemy_length = max([s["length"] for s in snakes if s["id"] != you["id"]], default=0)
        is_behind = your_length <= max_enemy_length
        should_eat = your_health < 40 or is_behind
        veto = -1e9
        moves = {"up": 0.0, "down": 0.0, "left": 0.0, "right": 0.0}
        deltas = {"up": (0, 1), "down": (0, -1), "left": (-1, 0), "right": (1, 0)}

        for direction, (dx, dy) in deltas.items():
            nx, ny = your_head[0] + dx, your_head[1] + dy
            if nx < 0 or nx >= width or ny < 0 or ny >= height:
                moves[direction] = veto
                continue
            next_pos = (nx, ny)
            if any(next_pos == tuple(seg.values()) for s in snakes if s["id"] != you["id"] for seg in s["body"][:-1]):
                moves[direction] = veto
                continue
            if should_eat:
                nearest_dist = float("inf")
                in_dead_end = False
                for f in food:
                    dist = abs(f[0] - nx) + abs(f[1] - ny)
                    if dist < nearest_dist:
                        nearest_dist = dist
                        if next_pos == f:
                            reachable = set()
                            stack = [f]
                            visited = {f}
                            while stack:
                                cx, cy = stack.pop()
                                reachable.add((cx, cy))
                                for ndx, ndy in [(0, 1), (0, -1), (-1, 0), (1, 0)]:
                                    nc, nr = cx + ndx, cy + ndy
                                    if 0 <= nc < width and 0 <= nr < height and (nc, nr) not in visited and not any((nc, nr) == tuple(seg.values()) for s in snakes if s["id"] != you["id"] for seg in s["body"][:-1]):
                                        visited.add((nc, nr))
                                        stack.append((nc, nr))
                            if len(reachable) < your_length:
                                in_dead_end = True
                                break
                if in_dead_end or nearest_dist == float("inf"):
                    moves[direction] = veto
                else:
                    moves[direction] = max(0.0, 10.0 - nearest_dist * 0.5)
            else:
                nearest_dist = float("inf")
                for f in food:
                    dist = abs(f[0] - nx) + abs(f[1] - ny)
                    if dist < nearest_dist:
                        nearest_dist = dist
                if nearest_dist == float("inf"):
                    moves[direction] = 0.0
                else:
                    moves[direction] = -0.5 + (10.0 - nearest_dist * 0.1)
        return moves
    except:
        return {m: 0.0 for m in ["up", "down", "left", "right"]}
