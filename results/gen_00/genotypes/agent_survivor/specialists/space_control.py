def score(game_state):
    try:
        you = game_state.get("you", {})
        board = game_state.get("board", {})

        if not you or not board:
            return {"up": 0.0, "down": 0.0, "left": 0.0, "right": 0.0}

        width = board.get("width", 11)
        height = board.get("height", 11)
        your_body = [tuple(seg.values()) for seg in you.get("body", [])]
        your_length = you.get("length", 1)
        your_health = you.get("health", 100)
        just_ate = len(your_body) > 1 and your_body[-1] == your_body[-2]

        all_snakes = board.get("snakes", [])
        other_bodies = set()
        for snake in all_snakes:
            if snake.get("id") != you.get("id"):
                for seg in snake.get("body", []):
                    other_bodies.add(tuple(seg.values()))

        hazards = set(tuple(h.values()) for h in board.get("hazards", []))

        def is_valid(x, y):
            return 0 <= x < width and 0 <= y < height

        def get_reachable(head_x, head_y, body_tuple, length):
            visited = set()
            stack = [(head_x, head_y)]
            visited.add((head_x, head_y))
            tail_pos = body_tuple[-1] if body_tuple else None
            occupied = set(body_tuple[:-1]) if not just_ate else set(body_tuple)
            if just_ate and tail_pos:
                occupied.add(tail_pos)

            while stack:
                x, y = stack.pop()
                for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                    nx, ny = x + dx, y + dy
                    if is_valid(nx, ny) and (nx, ny) not in visited:
                        if (nx, ny) not in occupied and (nx, ny) not in other_bodies and (nx, ny) not in hazards:
                            visited.add((nx, ny))
                            stack.append((nx, ny))

            return len(visited)

        head_x, head_y = your_body[0]
        moves = {"up": (head_x, head_y + 1), "down": (head_x, head_y - 1), "left": (head_x - 1, head_y), "right": (head_x + 1, head_y)}
        scores = {}

        for move, (nx, ny) in moves.items():
            if not is_valid(nx, ny):
                scores[move] = -1e9
            elif (nx, ny) in other_bodies or (nx, ny) in hazards:
                scores[move] = -1e9
            else:
                new_body = [(nx, ny)] + your_body[:-1]
                reachable = get_reachable(nx, ny, tuple(new_body), your_length)
                if reachable < your_length:
                    scores[move] = -1e9
                else:
                    scores[move] = float(reachable)

        return scores
    except:
        return {"up": 0.0, "down": 0.0, "left": 0.0, "right": 0.0}
