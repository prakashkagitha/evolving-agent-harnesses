def score(game_state) -> dict:
    try:
        you = game_state.get("you", {})
        board = game_state.get("board", {})
        your_head = you.get("body", [{}])[0]
        your_length = you.get("length", 0)
        your_health = you.get("health", 100)

        if not your_head or "x" not in your_head or "y" not in your_head:
            return {m: 0.0 for m in ["up", "down", "left", "right"]}

        width = board.get("width", 11)
        height = board.get("height", 11)
        snakes = board.get("snakes", [])
        your_body_set = set((seg["x"], seg["y"]) for seg in you.get("body", []))
        your_tail = (you.get("body", [{}])[-1].get("x"), you.get("body", [{}])[-1].get("y"))
        just_ate = len(you.get("body", [])) >= 2 and you.get("body", [])[-1] == you.get("body", [])[-2]

        moves = {
            "up": (your_head["x"], your_head["y"] + 1),
            "down": (your_head["x"], your_head["y"] - 1),
            "left": (your_head["x"] - 1, your_head["y"]),
            "right": (your_head["x"] + 1, your_head["y"])
        }

        scores = {}
        for direction, (nx, ny) in moves.items():
            if nx < 0 or nx >= width or ny < 0 or ny >= height:
                scores[direction] = -1e9
                continue

            cell = (nx, ny)
            forbidden = your_body_set - {your_tail} if not just_ate else your_body_set
            if cell in forbidden:
                scores[direction] = -1e9
                continue

            lose_collision = False
            win_collision = False
            enemy_body_threat = False
            threat_count = 0

            for enemy in snakes:
                if enemy.get("id") == you.get("id"):
                    continue
                enemy_head = enemy.get("body", [{}])[0]
                enemy_length = enemy.get("length", 0)
                enemy_body = set((seg["x"], seg["y"]) for seg in enemy.get("body", []))

                if not enemy_head or "x" not in enemy_head or "y" not in enemy_head:
                    continue

                if cell in enemy_body:
                    enemy_body_threat = True
                    continue

                enemy_moves = [
                    (enemy_head["x"], enemy_head["y"] + 1),
                    (enemy_head["x"], enemy_head["y"] - 1),
                    (enemy_head["x"] - 1, enemy_head["y"]),
                    (enemy_head["x"] + 1, enemy_head["y"])
                ]

                if cell in enemy_moves:
                    if enemy_length >= your_length:
                        lose_collision = True
                    elif enemy_length < your_length:
                        win_collision = True
                        threat_count += 1

            if enemy_body_threat or lose_collision:
                scores[direction] = -1e9
            elif win_collision:
                scores[direction] = 10.0 + threat_count
            else:
                scores[direction] = 0.0

        return scores
    except:
        return {m: 0.0 for m in ["up", "down", "left", "right"]}
