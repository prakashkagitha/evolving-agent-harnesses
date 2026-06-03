def score(game_state):
    try:
        my_head = tuple(game_state["you"]["body"][0].values())
        my_length = game_state["you"]["length"]
        my_tail = tuple(game_state["you"]["body"][-1].values())
        board = game_state["board"]
        width, height = board["width"], board["height"]

        body_cells = set()
        opponent_heads = []
        for snake in board["snakes"]:
            snake_id = snake.get("id")
            if snake_id != game_state["you"].get("id"):
                head = tuple(snake["body"][0].values())
                opponent_heads.append(head)
            for segment in snake["body"]:
                body_cells.add(tuple(segment.values()))

        tail_is_free = (len(game_state["you"]["body"]) < 2 or
                       game_state["you"]["body"][-1] != game_state["you"]["body"][-2])
        if tail_is_free:
            body_cells.discard(my_tail)

        moves = {"up": 0.0, "down": 0.0, "left": 0.0, "right": 0.0}
        deltas = {"up": (0, 1), "down": (0, -1), "left": (-1, 0), "right": (1, 0)}

        for move, (dx, dy) in deltas.items():
            new_x, new_y = my_head[0] + dx, my_head[1] + dy

            if new_x < 0 or new_x >= width or new_y < 0 or new_y >= height:
                moves[move] = -1e9
                continue

            new_head = (new_x, new_y)
            if new_head in body_cells:
                moves[move] = -1e9
                continue

            temp_body = body_cells.copy()
            temp_body.discard(my_tail)
            temp_body.add(new_head)

            visited = set()
            stack = [new_head]
            while stack:
                cell = stack.pop()
                if cell in visited or cell[0] < 0 or cell[0] >= width or cell[1] < 0 or cell[1] >= height:
                    continue
                if cell in temp_body:
                    continue
                visited.add(cell)
                for nx, ny in [(cell[0]+1,cell[1]), (cell[0]-1,cell[1]), (cell[0],cell[1]+1), (cell[0],cell[1]-1)]:
                    if (nx, ny) not in visited and 0 <= nx < width and 0 <= ny < height and (nx, ny) not in temp_body:
                        stack.append((nx, ny))

            reachable = len(visited)
            if reachable < my_length:
                moves[move] = -1e9
            else:
                score_val = float(reachable)

                min_dist_to_opponent = min([abs(new_x - oh[0]) + abs(new_y - oh[1]) for oh in opponent_heads], default=100)
                if min_dist_to_opponent == 1:
                    score_val -= 1000
                elif min_dist_to_opponent <= 2:
                    score_val -= 100

                moves[move] = score_val

        return moves
    except:
        return {"up": 0.0, "down": 0.0, "left": 0.0, "right": 0.0}
