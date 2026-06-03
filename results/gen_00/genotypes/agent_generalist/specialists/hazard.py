def score(game_state):
    try:
        board = game_state.get("board", {})
        you = game_state.get("you", {})
        width = board.get("width", 11)
        height = board.get("height", 11)
        your_head = you.get("body", [{}])[0]
        head_x, head_y = your_head.get("x"), your_head.get("y")
        hazards = set((h["x"], h["y"]) for h in board.get("hazards", []))
        snake_bodies = set()
        for snake in board.get("snakes", []):
            for segment in snake.get("body", []):
                snake_bodies.add((segment["x"], segment["y"]))
        your_body_set = set((seg["x"], seg["y"]) for seg in you.get("body", []))
        your_tail = (you.get("body", [{}])[-1].get("x"), you.get("body", [{}])[-1].get("y")) if you.get("body") else (head_x, head_y)
        if you.get("health", 0) < 100:
            your_body_set.discard(your_tail)
        moves = {"up": (0, 1), "down": (0, -1), "left": (-1, 0), "right": (1, 0)}
        scores = {}
        for move_name, (dx, dy) in moves.items():
            nx, ny = head_x + dx, head_y + dy
            if nx < 0 or nx >= width or ny < 0 or ny >= height:
                scores[move_name] = -1e9
            elif (nx, ny) in snake_bodies and (nx, ny) != your_tail:
                scores[move_name] = -1e9
            else:
                penalty = 0.0
                if (nx, ny) in hazards:
                    penalty -= 5.0
                min_dist_to_edge = min(nx, ny, width - 1 - nx, height - 1 - ny)
                if min_dist_to_edge == 0:
                    penalty -= 3.0
                elif min_dist_to_edge == 1:
                    penalty -= 1.5
                scores[move_name] = penalty
        return scores
    except:
        return {m: 0.0 for m in ["up", "down", "left", "right"]}
