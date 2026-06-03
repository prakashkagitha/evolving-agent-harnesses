def score(game_state):
    try:
        you = game_state["you"]
        board = game_state["board"]
        your_head = tuple((you["body"][0]["x"], you["body"][0]["y"]))
        your_length = you["length"]
        just_ate = len(you["body"]) > 1 and you["body"][-1]["x"] == you["body"][-2]["x"] and you["body"][-1]["y"] == you["body"][-2]["y"]
        your_body_set = {tuple((seg["x"], seg["y"])) for seg in you["body"][:-1]} if not just_ate else {tuple((seg["x"], seg["y"])) for seg in you["body"]}

        enemy_heads = {}
        enemy_bodies = set()
        enemy_tails = set()
        for snake in board["snakes"]:
            if snake["id"] != you["id"]:
                head = tuple((snake["body"][0]["x"], snake["body"][0]["y"]))
                enemy_heads[head] = snake["length"]
                tail = tuple((snake["body"][-1]["x"], snake["body"][-1]["y"]))
                enemy_tails.add(tail)
                for seg in snake["body"]:
                    enemy_bodies.add(tuple((seg["x"], seg["y"])))

        moves = {"up": 0.0, "down": 0.0, "left": 0.0, "right": 0.0}
        deltas = {"up": (0, 1), "down": (0, -1), "left": (-1, 0), "right": (1, 0)}

        for direction, (dx, dy) in deltas.items():
            next_x, next_y = your_head[0] + dx, your_head[1] + dy
            next_pos = (next_x, next_y)

            if next_x < 0 or next_x >= board["width"] or next_y < 0 or next_y >= board["height"]:
                moves[direction] = -1e9
                continue

            if next_pos in your_body_set:
                moves[direction] = -1e9
                continue

            if next_pos in enemy_bodies and next_pos not in enemy_tails:
                moves[direction] = -1e9
                continue

            threat = False
            for enemy_head, enemy_length in enemy_heads.items():
                enemy_x, enemy_y = enemy_head
                dist_to_enemy = abs(enemy_x - next_x) + abs(enemy_y - next_y)

                # Direct threat: enemy can reach us in 1 move and is >= our length
                if dist_to_enemy == 1 and enemy_length >= your_length:
                    threat = True
                    break

                # 2-move threat: if we move to next_pos and enemy moves once, can they hit us and are they >= our length?
                if dist_to_enemy == 2 and enemy_length >= your_length:
                    threat = True
                    break

            if threat:
                moves[direction] = -1e9
                continue

            bonus = 0.0
            for enemy_head, enemy_length in enemy_heads.items():
                enemy_x, enemy_y = enemy_head
                can_reach = abs(enemy_x - next_x) + abs(enemy_y - next_y) == 1
                if can_reach and enemy_length < your_length:
                    bonus += 5.0

            moves[direction] = bonus

        return moves
    except:
        return {"up": 0.0, "down": 0.0, "left": 0.0, "right": 0.0}
