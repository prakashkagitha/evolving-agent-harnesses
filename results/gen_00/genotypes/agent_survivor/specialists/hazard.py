def score(game_state):
    try:
        you = game_state.get("you", {})
        board = game_state.get("board", {})
        if not you or not board:
            return {m: 0.0 for m in ["up", "down", "left", "right"]}

        head = you["body"][0] if you.get("body") else {"x": 0, "y": 0}
        hx, hy = head["x"], head["y"]
        board_w = board.get("width", 11)
        board_h = board.get("height", 11)

        hazard_set = set((h["x"], h["y"]) for h in board.get("hazards", []))
        body_set = set((b["x"], b["y"]) for b in you.get("body", []))
        all_snakes_body = set()
        enemy_heads = set()
        for snake in board.get("snakes", []):
            if snake.get("id") != you.get("id"):
                for i, cell in enumerate(snake.get("body", [])):
                    cell_pos = (cell["x"], cell["y"])
                    all_snakes_body.add(cell_pos)
                    if i == 0:
                        enemy_heads.add(cell_pos)

        moves = {
            "up": (hx, hy + 1),
            "down": (hx, hy - 1),
            "left": (hx - 1, hy),
            "right": (hx + 1, hy)
        }

        scores = {}
        for move_name, (nx, ny) in moves.items():
            if nx < 0 or nx >= board_w or ny < 0 or ny >= board_h:
                scores[move_name] = -1e9
                continue

            if (nx, ny) in all_snakes_body and (nx, ny) not in enemy_heads:
                scores[move_name] = -1e9
                continue

            score_val = 0.0

            if (nx, ny) in hazard_set:
                score_val -= 5.0

            dist_from_edge = min(nx, ny, board_w - 1 - nx, board_h - 1 - ny)
            if dist_from_edge == 0:
                score_val -= 3.0
            elif dist_from_edge == 1:
                score_val -= 1.0

            center_x = board_w / 2.0
            center_y = board_h / 2.0
            dist_to_center = abs(nx - center_x) + abs(ny - center_y)
            score_val += (10.0 - dist_to_center) * 0.2

            scores[move_name] = score_val

        return scores
    except:
        return {m: 0.0 for m in ["up", "down", "left", "right"]}
