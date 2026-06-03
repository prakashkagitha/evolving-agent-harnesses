def score(game_state):
    try:
        you = game_state.get("you", {})
        board = game_state.get("board", {})

        your_id = you.get("id")
        your_body = you.get("body", [])
        your_health = you.get("health", 0)
        board_width = board.get("width", 11)
        board_height = board.get("height", 11)
        all_snakes = board.get("snakes", [])

        if not your_body:
            return {"up": 0.0, "down": 0.0, "left": 0.0, "right": 0.0}

        head = your_body[0]
        head_x, head_y = head.get("x"), head.get("y")
        if head_x is None or head_y is None:
            return {"up": 0.0, "down": 0.0, "left": 0.0, "right": 0.0}

        # Check if snake just ate
        just_ate = len(your_body) > 1 and your_body[-1] == your_body[-2]

        # Build occupied cells (all snake bodies except your tail if not just ate)
        occupied = set()
        for snake in all_snakes:
            snake_body = snake.get("body", [])
            snake_id = snake.get("id")

            if snake_id == your_id:
                # Your body: exclude tail unless just ate
                for i, segment in enumerate(snake_body):
                    if i == len(snake_body) - 1 and not just_ate:
                        continue
                    occupied.add((segment["x"], segment["y"]))
            else:
                # Other snakes: all segments
                for segment in snake_body:
                    occupied.add((segment["x"], segment["y"]))

        def flood_fill(start_x, start_y):
            """Flood-fill to count reachable cells."""
            if (start_x, start_y) in occupied:
                return 0
            if start_x < 0 or start_x >= board_width or start_y < 0 or start_y >= board_height:
                return 0

            visited = set()
            stack = [(start_x, start_y)]

            while stack:
                x, y = stack.pop()
                if (x, y) in visited:
                    continue
                if x < 0 or x >= board_width or y < 0 or y >= board_height:
                    continue
                if (x, y) in occupied:
                    continue

                visited.add((x, y))
                stack.extend([(x+1, y), (x-1, y), (x, y+1), (x, y-1)])

            return len(visited)

        # Score each move
        result = {}
        moves = [
            ("up", (head_x, head_y + 1)),
            ("down", (head_x, head_y - 1)),
            ("left", (head_x - 1, head_y)),
            ("right", (head_x + 1, head_y))
        ]

        for direction, (new_x, new_y) in moves:
            # Check wall
            if new_x < 0 or new_x >= board_width or new_y < 0 or new_y >= board_height:
                result[direction] = -1e9
                continue

            # Check snake body
            if (new_x, new_y) in occupied:
                result[direction] = -1e9
                continue

            # Flood-fill from new position
            reachable = flood_fill(new_x, new_y)

            # Veto if pocket is smaller than your length
            if reachable < len(your_body):
                result[direction] = -1e9
            else:
                result[direction] = float(reachable)

        return result
    except:
        return {"up": 0.0, "down": 0.0, "left": 0.0, "right": 0.0}
