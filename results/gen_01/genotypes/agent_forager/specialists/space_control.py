def score(game_state):
    try:
        you = game_state["you"]
        board = game_state["board"]
        width, height = board["width"], board["height"]
        head = you["body"][0]
        your_length = you["length"]
        your_health = you.get("health", 100)
        just_ate = len(you["body"]) > 1 and you["body"][-2] == you["body"][-1]

        occupied = set()
        enemy_heads = []
        enemy_lengths = []
        for snake in board["snakes"]:
            if snake["id"] != you["id"]:
                enemy_heads.append((snake["body"][0]["x"], snake["body"][0]["y"]))
                enemy_lengths.append(snake["length"])
            for segment in snake["body"]:
                occupied.add((segment["x"], segment["y"]))

        tail = (you["body"][-1]["x"], you["body"][-1]["y"])
        if not just_ate:
            occupied.discard(tail)

        def flood_fill(start_x, start_y):
            if start_x < 0 or start_x >= width or start_y < 0 or start_y >= height:
                return 0
            if (start_x, start_y) in occupied:
                return 0
            visited = set()
            stack = [(start_x, start_y)]
            while stack:
                x, y = stack.pop()
                if (x, y) in visited or x < 0 or x >= width or y < 0 or y >= height or (x, y) in occupied:
                    continue
                visited.add((x, y))
                for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                    stack.append((x + dx, y + dy))
            return len(visited)

        scores = {}
        moves = [("up", 0, 1), ("down", 0, -1), ("left", -1, 0), ("right", 1, 0)]

        for move_name, dx, dy in moves:
            nx, ny = head["x"] + dx, head["y"] + dy

            if nx < 0 or nx >= width or ny < 0 or ny >= height or (nx, ny) in occupied:
                scores[move_name] = -1e9
            else:
                space = flood_fill(nx, ny)
                space_penalty = 0.0
                if space < your_length:
                    space_penalty = -500.0

                head_danger = 0.0
                for i, (ex, ey) in enumerate(enemy_heads):
                    dist_to_enemy = abs(nx - ex) + abs(ny - ey)
                    enemy_len = enemy_lengths[i]

                    if dist_to_enemy == 0:
                        head_danger = -1000.0
                    elif dist_to_enemy == 1:
                        if your_length <= enemy_len:
                            head_danger = -200.0
                        else:
                            head_danger = -50.0
                    elif dist_to_enemy == 2 and your_health < 50:
                        if your_length <= enemy_len:
                            head_danger = -100.0
                        else:
                            head_danger = -30.0

                scores[move_name] = float(space) + space_penalty + head_danger

        return scores
    except:
        return {"up": 0.0, "down": 0.0, "left": 0.0, "right": 0.0}
