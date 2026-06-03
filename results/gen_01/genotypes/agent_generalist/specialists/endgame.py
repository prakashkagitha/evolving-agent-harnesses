def score(game_state):
    try:
        you = game_state.get("you", {})
        board = game_state.get("board", {})

        my_head = you.get("body", [{}])[0]
        my_length = you.get("length", 0)
        width = board.get("width", 11)
        height = board.get("height", 11)

        if not isinstance(my_head, dict) or "x" not in my_head or "y" not in my_head:
            return {d: 0.0 for d in ["up", "down", "left", "right"]}

        hx, hy = my_head["x"], my_head["y"]

        # Convert to tuple sets for efficient checking
        my_body_set = set()
        for seg in you.get("body", []):
            if isinstance(seg, dict) and "x" in seg and "y" in seg:
                my_body_set.add((seg["x"], seg["y"]))

        # Find max opponent length
        max_opp_len = 0
        for snake in board.get("snakes", []):
            if snake.get("id") != you.get("id"):
                max_opp_len = max(max_opp_len, snake.get("length", 0))

        is_longer = my_length > max_opp_len
        center_x, center_y = width / 2.0, height / 2.0

        moves = {
            "up": (hx, hy + 1),
            "down": (hx, hy - 1),
            "left": (hx - 1, hy),
            "right": (hx + 1, hy)
        }

        scores = {}
        for direction, (nx, ny) in moves.items():
            # Hard veto: walls and body cells
            if nx < 0 or nx >= width or ny < 0 or ny >= height or (nx, ny) in my_body_set:
                scores[direction] = -1e9
                continue

            # Center preference (strong in endgame)
            center_dist = abs(nx - center_x) + abs(ny - center_y)
            center_bonus = 5.0 - center_dist * 0.5

            # Strategy based on length
            if is_longer:
                # Longer: aggressive, maintain central control, pressure opponent
                edge_penalty = 0.0
                if nx in [0, width - 1] or ny in [0, height - 1]:
                    edge_penalty = -2.0
                scores[direction] = center_bonus + 2.0 + edge_penalty
            else:
                # Shorter: stall, prefer inner board, avoid edges
                edge_bonus = 0.0
                min_edge_dist = min(nx, ny, width - 1 - nx, height - 1 - ny)
                if min_edge_dist >= 3:
                    edge_bonus = 2.0
                elif min_edge_dist < 1:
                    edge_bonus = -3.0
                scores[direction] = center_bonus + edge_bonus

        return scores
    except:
        return {d: 0.0 for d in ["up", "down", "left", "right"]}
