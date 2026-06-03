def score(game_state):
    try:
        board = game_state["board"]
        you = game_state["you"]
        width, height = board["width"], board["height"]
        your_body = you["body"]
        your_length = you["length"]
        your_head = tuple((your_body[0]["x"], your_body[0]["y"]))
        your_tail = tuple((your_body[-1]["x"], your_body[-1]["y"]))

        body_set = set((seg["x"], seg["y"]) for seg in your_body)
        all_snake_cells = set()
        for snake in board["snakes"]:
            for seg in snake["body"]:
                all_snake_cells.add((seg["x"], seg["y"]))

        hazard_set = set((h["x"], h["y"]) for h in board.get("hazards", []))

        def flood_fill(start):
            visited = set()
            queue = [start]
            visited.add(start)
            count = 0
            while queue:
                x, y = queue.pop(0)
                count += 1
                for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < width and 0 <= ny < height and (nx, ny) not in visited:
                        if (nx, ny) not in all_snake_cells or (nx, ny) == your_tail:
                            visited.add((nx, ny))
                            queue.append((nx, ny))
            return count

        result = {}
        moves = [("up", 0, 1), ("down", 0, -1), ("left", -1, 0), ("right", 1, 0)]

        for move_name, dx, dy in moves:
            nx, ny = your_head[0] + dx, your_head[1] + dy

            if not (0 <= nx < width and 0 <= ny < height):
                result[move_name] = -1e9
                continue

            if (nx, ny) in all_snake_cells and (nx, ny) != your_tail:
                result[move_name] = -1e9
                continue

            reachable = flood_fill((nx, ny))

            if reachable < your_length:
                result[move_name] = -1e9
            else:
                result[move_name] = float(reachable)

        return result
    except:
        return {"up": 0.0, "down": 0.0, "left": 0.0, "right": 0.0}
