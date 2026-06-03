from collections import deque

def score(game_state):
    try:
        you = game_state["you"]
        board = game_state["board"]
        your_head = (you["body"][0]["x"], you["body"][0]["y"])
        your_length = you["length"]
        width, height = board["width"], board["height"]

        your_body_set = set((seg["x"], seg["y"]) for seg in you["body"])
        your_tail = (you["body"][-1]["x"], you["body"][-1]["y"])

        enemy_snakes = [s for s in board["snakes"] if s["id"] != you["id"]]

        def flood_fill(start, exclude):
            visited = set([start])
            q = deque([start])
            while q:
                x, y = q.popleft()
                for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < width and 0 <= ny < height and (nx, ny) not in visited and (nx, ny) not in exclude:
                        visited.add((nx, ny))
                        q.append((nx, ny))
            return visited

        def reachable_after(head, is_growing):
            future_body = set((seg["x"], seg["y"]) for seg in you["body"][:-1]) if not is_growing else your_body_set
            if head in future_body:
                return set()
            return flood_fill(head, future_body)

        result = {}
        moves = {"up": (0, 1), "down": (0, -1), "left": (-1, 0), "right": (1, 0)}

        for move_name, (dx, dy) in moves.items():
            nx, ny = your_head[0] + dx, your_head[1] + dy

            if not (0 <= nx < width and 0 <= ny < height):
                result[move_name] = -1e9
                continue

            if (nx, ny) in your_body_set:
                result[move_name] = -1e9
                continue

            new_head = (nx, ny)

            if any(s["length"] >= your_length and any((s["body"][0]["x"] + ddx, s["body"][0]["y"] + ddy) == new_head for ddx, ddy in [(0, 1), (0, -1), (1, 0), (-1, 0)]) for s in enemy_snakes):
                result[move_name] = -1e9
                continue

            is_eating = any(new_head == (f["x"], f["y"]) for f in board.get("food", []))
            reachable = reachable_after(new_head, is_eating)

            if len(reachable) < your_length:
                result[move_name] = -1e9
                continue

            score_val = 0.0

            center_x, center_y = width / 2.0, height / 2.0
            dist_to_center = abs(nx - center_x) + abs(ny - center_y)
            score_val -= dist_to_center * 0.15

            if len(enemy_snakes) >= 1:
                enemy = enemy_snakes[0]
                enemy_length = enemy["length"]

                if your_length > enemy_length:
                    score_val += 8.0
                    opponent_body = set((seg["x"], seg["y"]) for seg in enemy["body"])
                    opponent_reachable = flood_fill((enemy["body"][0]["x"], enemy["body"][0]["y"]), opponent_body)
                    space_shrink = 50.0 - len(opponent_reachable) * 0.3
                    score_val += max(0, space_shrink)
                else:
                    score_val -= 2.0
                    score_val += len(reachable) * 0.1

            result[move_name] = score_val

        return result
    except:
        return {"up": 0.0, "down": 0.0, "left": 0.0, "right": 0.0}
