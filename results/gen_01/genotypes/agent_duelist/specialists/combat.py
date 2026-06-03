def score(game_state):
    try:
        you = game_state["you"]
        board = game_state["board"]
        my_head = tuple([you["body"][0]["x"], you["body"][0]["y"]])
        my_length = you["length"]
        my_body_set = {(seg["x"], seg["y"]) for seg in you["body"]}
        my_tail = tuple([you["body"][-1]["x"], you["body"][-1]["y"]])
        just_ate = len(you["body"]) > 1 and you["body"][-1]["x"] == you["body"][-2]["x"] and you["body"][-1]["y"] == you["body"][-2]["y"]

        result = {}
        moves = [("up", 0, 1), ("down", 0, -1), ("left", -1, 0), ("right", 1, 0)]

        for direction, dx, dy in moves:
            next_x, next_y = my_head[0] + dx, my_head[1] + dy
            next_head = (next_x, next_y)

            if not (0 <= next_x < board["width"] and 0 <= next_y < board["height"]):
                result[direction] = -1e9
                continue

            if next_head in my_body_set and not (not just_ate and next_head == my_tail):
                result[direction] = -1e9
                continue

            score_val = 0.0
            veto = False

            for enemy in board["snakes"]:
                if enemy["id"] == you["id"]:
                    continue

                enemy_head = tuple([enemy["body"][0]["x"], enemy["body"][0]["y"]])
                enemy_length = enemy["length"]

                if enemy_length == 0:
                    continue

                enemy_body_set = {(seg["x"], seg["y"]) for seg in enemy["body"]}

                if next_head in enemy_body_set:
                    veto = True
                    break

                enemy_can_reach = set()
                for emove in [("up", 0, 1), ("down", 0, -1), ("left", -1, 0), ("right", 1, 0)]:
                    ex, ey = enemy_head[0] + emove[1], enemy_head[1] + emove[2]
                    if 0 <= ex < board["width"] and 0 <= ey < board["height"]:
                        enemy_can_reach.add((ex, ey))

                if next_head in enemy_can_reach:
                    if enemy_length >= my_length:
                        veto = True
                        break
                    else:
                        score_val += 5.0

            if veto:
                result[direction] = -1e9
            elif direction not in result:
                result[direction] = score_val

        return result
    except:
        return {"up": 0.0, "down": 0.0, "left": 0.0, "right": 0.0}
