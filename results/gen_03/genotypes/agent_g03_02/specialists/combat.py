def score(game_state):
    try:
        you = game_state.get("you", {})
        board = game_state.get("board", {})
        your_head = tuple((you.get("body", [{}])[0].get("x"), you.get("body", [{}])[0].get("y")))
        your_length = you.get("length", 0)
        your_body_set = {(seg["x"], seg["y"]) for seg in you.get("body", [])}

        snakes = board.get("snakes", [])
        enemy_heads = []
        for snake in snakes:
            if snake.get("id") != you.get("id"):
                head = snake.get("body", [{}])[0]
                enemy_heads.append({"pos": (head.get("x"), head.get("y")), "length": snake.get("length", 0)})

        moves = {"up": (0, 1), "down": (0, -1), "left": (-1, 0), "right": (1, 0)}
        scores = {}

        for direction, (dx, dy) in moves.items():
            new_x, new_y = your_head[0] + dx, your_head[1] + dy
            new_head = (new_x, new_y)

            if new_x < 0 or new_x >= 11 or new_y < 0 or new_y >= 11:
                scores[direction] = -1e9
                continue

            if new_head in your_body_set:
                scores[direction] = -1e9
                continue

            veto = False
            bonus = 0.0

            for enemy in enemy_heads:
                enemy_pos = enemy["pos"]
                enemy_length = enemy["length"]
                enemy_x, enemy_y = enemy_pos

                can_reach = abs(enemy_x - new_x) + abs(enemy_y - new_y) == 1

                if can_reach:
                    if enemy_length >= your_length:
                        veto = True
                        break
                    else:
                        bonus += 2.0

            if veto:
                scores[direction] = -1e9
            else:
                scores[direction] = bonus

        return scores
    except:
        return {"up": 0.0, "down": 0.0, "left": 0.0, "right": 0.0}
