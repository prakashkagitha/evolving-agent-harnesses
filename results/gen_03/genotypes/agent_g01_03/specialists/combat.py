def score(game_state):
    moves = {"up": 0.0, "down": 0.0, "left": 0.0, "right": 0.0}
    try:
        you = game_state.get("you", {})
        board = game_state.get("board", {})
        your_body = you.get("body", [])
        your_length = you.get("length", 0)
        your_health = you.get("health", 0)

        if not your_body:
            return moves

        head = your_body[0]
        your_head = (head["x"], head["y"])
        your_tail = (your_body[-1]["x"], your_body[-1]["y"]) if your_body else None
        just_ate = len(your_body) > 1 and your_body[-1]["x"] == your_body[-2]["x"] and your_body[-1]["y"] == your_body[-2]["y"]

        width = board.get("width", 11)
        height = board.get("height", 11)

        your_body_set = set((b["x"], b["y"]) for b in your_body)
        if not just_ate and your_tail:
            your_body_set.discard(your_tail)

        enemy_heads = []
        for snake in board.get("snakes", []):
            if snake.get("id") != you.get("id"):
                snake_body = snake.get("body", [])
                if snake_body:
                    enemy_heads.append({
                        "head": (snake_body[0]["x"], snake_body[0]["y"]),
                        "length": snake.get("length", 0)
                    })

        hazards = set((h["x"], h["y"]) for h in board.get("hazards", []))

        directions = {
            "up": (0, 1),
            "down": (0, -1),
            "left": (-1, 0),
            "right": (1, 0)
        }

        for direction, (dx, dy) in directions.items():
            next_x = your_head[0] + dx
            next_y = your_head[1] + dy
            next_pos = (next_x, next_y)

            if next_x < 0 or next_x >= width or next_y < 0 or next_y >= height:
                moves[direction] = -1e9
                continue

            if next_pos in your_body_set:
                moves[direction] = -1e9
                continue

            if next_pos in hazards:
                moves[direction] = -1e9
                continue

            score_val = 0.0
            is_safe = True

            for enemy in enemy_heads:
                enemy_head = enemy["head"]
                enemy_length = enemy["length"]

                enemy_can_reach = False
                adjacent_moves = [
                    (enemy_head[0] + dx2, enemy_head[1] + dy2)
                    for dx2, dy2 in [(0, 1), (0, -1), (-1, 0), (1, 0)]
                ]
                for adj in adjacent_moves:
                    if adj == next_pos:
                        enemy_can_reach = True
                        break

                if enemy_can_reach:
                    if enemy_length >= your_length:
                        is_safe = False
                        break
                    else:
                        score_val += 5.0

            if not is_safe:
                moves[direction] = -1e9
            else:
                moves[direction] = score_val

        return moves
    except Exception:
        return {m: 0.0 for m in ["up", "down", "left", "right"]}
