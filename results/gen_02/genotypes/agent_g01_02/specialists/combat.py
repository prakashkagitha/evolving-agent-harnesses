def score(game_state):
    try:
        you = game_state["you"]
        board = game_state["board"]
        your_head = (you["body"][0]["x"], you["body"][0]["y"])
        your_length = you["length"]

        moves = {"up": 0.0, "down": 0.0, "left": 0.0, "right": 0.0}
        directions = {"up": (0, 1), "down": (0, -1), "left": (-1, 0), "right": (1, 0)}
        your_body_cells = set((b["x"], b["y"]) for b in you["body"])

        for move, (dx, dy) in directions.items():
            new_x, new_y = your_head[0] + dx, your_head[1] + dy
            new_head = (new_x, new_y)

            if new_x < 0 or new_x >= board["width"] or new_y < 0 or new_y >= board["height"]:
                moves[move] = -1e9
                continue

            if new_head in your_body_cells:
                moves[move] = -1e9
                continue

            dangerous = False
            win_bonus = 0.0
            vulnerability_penalty = 0.0

            for enemy in board["snakes"]:
                if enemy["id"] == you["id"]:
                    continue

                enemy_head = (enemy["body"][0]["x"], enemy["body"][0]["y"])
                enemy_length = enemy["length"]
                enemy_body_cells = set((b["x"], b["y"]) for b in enemy["body"])

                if new_head in enemy_body_cells:
                    moves[move] = -1e9
                    dangerous = True
                    break

                enemy_reachable = set()
                for em, (edx, edy) in directions.items():
                    next_x, next_y = enemy_head[0] + edx, enemy_head[1] + edy
                    if 0 <= next_x < board["width"] and 0 <= next_y < board["height"]:
                        enemy_reachable.add((next_x, next_y))

                if new_head in enemy_reachable:
                    if enemy_length >= your_length:
                        dangerous = True
                        break
                    else:
                        win_bonus += 2.0
                else:
                    if enemy_length > your_length:
                        two_move_reach = enemy_reachable.copy()
                        for nx, ny in list(enemy_reachable):
                            for edx, edy in directions.values():
                                next_x, next_y = nx + edx, ny + edy
                                if 0 <= next_x < board["width"] and 0 <= next_y < board["height"]:
                                    two_move_reach.add((next_x, next_y))
                        if new_head in two_move_reach:
                            vulnerability_penalty -= 1.0

            if dangerous:
                moves[move] = -1e9
            else:
                moves[move] += win_bonus + vulnerability_penalty

        return moves
    except:
        return {m: 0.0 for m in ["up", "down", "left", "right"]}
