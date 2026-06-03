def score(game_state):
    """Space control specialist: maximize reachable open area via flood-fill."""
    try:
        you = game_state.get("you", {})
        board = game_state.get("board", {})

        if not you or not board:
            return {m: 0.0 for m in ["up", "down", "left", "right"]}

        head = you["body"][0]
        your_length = you["length"]
        just_ate = len(you["body"]) > 1 and you["body"][-1] == you["body"][-2] if you["body"] else False

        width = board.get("width", 11)
        height = board.get("height", 11)

        # Build set of occupied cells (all snake bodies, excluding tails that will move)
        occupied = set()
        all_snake_bodies = {}
        for snake in board.get("snakes", []):
            body = snake.get("body", [])
            all_snake_bodies[snake["id"]] = body
            for i, segment in enumerate(body):
                cell = (segment["x"], segment["y"])
                # Exclude tail of other snakes (they will move away)
                if snake["id"] == you["id"]:
                    # For your snake: exclude tail only if you didn't just eat
                    if i < len(body) - 1 or just_ate:
                        occupied.add(cell)
                else:
                    # Other snakes: always exclude their tail (it moves away next turn)
                    if i < len(body) - 1:
                        occupied.add(cell)

        # Hazard cells
        hazards = set((h["x"], h["y"]) for h in board.get("hazards", []))

        def flood_fill(start_x, start_y):
            """Count reachable cells from start position via BFS."""
            if not (0 <= start_x < width and 0 <= start_y < height):
                return 0
            if (start_x, start_y) in occupied:
                return 0

            visited = set()
            queue = [(start_x, start_y)]
            visited.add((start_x, start_y))

            while queue:
                x, y = queue.pop(0)
                for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < width and 0 <= ny < height and (nx, ny) not in visited and (nx, ny) not in occupied:
                        visited.add((nx, ny))
                        queue.append((nx, ny))

            return len(visited)

        moves = {
            "up": (head["x"], head["y"] + 1),
            "down": (head["x"], head["y"] - 1),
            "left": (head["x"] - 1, head["y"]),
            "right": (head["x"] + 1, head["y"]),
        }

        result = {}
        for direction, (next_x, next_y) in moves.items():
            # Hard veto: wall
            if not (0 <= next_x < width and 0 <= next_y < height):
                result[direction] = -1e9
                continue

            # Hard veto: snake body (including other heads)
            if (next_x, next_y) in occupied:
                result[direction] = -1e9
                continue

            # Hard veto: moving into hazard
            if (next_x, next_y) in hazards:
                result[direction] = -1e9
                continue

            # Conservative: penalize moving adjacent to enemy heads (they can attack next turn)
            penalty = 0.0
            for snake in board.get("snakes", []):
                if snake["id"] != you["id"]:
                    enemy_head = snake["body"][0]
                    enemy_pos = (enemy_head["x"], enemy_head["y"])
                    enemy_length = snake["length"]
                    # If enemy is longer and adjacent, heavily penalize
                    if abs(enemy_pos[0] - next_x) + abs(enemy_pos[1] - next_y) == 1:
                        if enemy_length >= your_length:
                            penalty = -500.0
                            break

            if penalty < -100:
                result[direction] = penalty
                continue

            # Calculate reachable space from this move
            reachable = flood_fill(next_x, next_y)

            # Hard veto: pocket smaller than your length (self-trap)
            if reachable < your_length:
                result[direction] = -1e9
                continue

            # Score: number of reachable cells (higher is better) plus penalty
            result[direction] = float(reachable) + penalty

        return result
    except:
        return {m: 0.0 for m in ["up", "down", "left", "right"]}
