def score(game_state):
    try:
        you = game_state["you"]
        board = game_state["board"]
        width, height = board["width"], board["height"]
        head = you["body"][0]
        my_length = you["length"]
        just_ate = len(you["body"]) > 1 and you["body"][-1] == you["body"][-2]

        body_set = set((seg["x"], seg["y"]) for seg in you["body"])
        if not just_ate and body_set:
            body_set.discard((you["body"][-1]["x"], you["body"][-1]["y"]))

        snake_bodies = set()
        for snake in board["snakes"]:
            if snake["id"] != you["id"]:
                for seg in snake["body"]:
                    snake_bodies.add((seg["x"], seg["y"]))

        def flood_fill(start_x, start_y, avoid_set):
            visited = set()
            stack = [(start_x, start_y)]
            while stack:
                x, y = stack.pop()
                if (x, y) in visited:
                    continue
                if x < 0 or x >= width or y < 0 or y >= height:
                    continue
                if (x, y) in avoid_set:
                    continue
                visited.add((x, y))
                for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                    stack.append((x + dx, y + dy))
            return len(visited)

        moves = {"up": 0.0, "down": 0.0, "left": 0.0, "right": 0.0}
        deltas = {"up": (0, 1), "down": (0, -1), "left": (-1, 0), "right": (1, 0)}

        for direction, (dx, dy) in deltas.items():
            new_x, new_y = head["x"] + dx, head["y"] + dy

            if new_x < 0 or new_x >= width or new_y < 0 or new_y >= height:
                moves[direction] = -1e9
                continue

            if (new_x, new_y) in body_set or (new_x, new_y) in snake_bodies:
                moves[direction] = -1e9
                continue

            avoid_set = body_set | snake_bodies
            reachable = flood_fill(new_x, new_y, avoid_set)

            if reachable < my_length:
                moves[direction] = -1e9
            else:
                moves[direction] = float(reachable) * 0.95

        return moves
    except:
        return {"up": 0.0, "down": 0.0, "left": 0.0, "right": 0.0}
