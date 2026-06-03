from collections import deque

def score(game_state):
    try:
        you = game_state["you"]
        board = game_state["board"]
        head = tuple((you["body"][0]["x"], you["body"][0]["y"]))
        health = you["health"]
        length = you["length"]
        width, height = board["width"], board["height"]

        all_bodies = set()
        for snake in board["snakes"]:
            for cell in snake["body"]:
                all_bodies.add(tuple((cell["x"], cell["y"])))

        tail = tuple((you["body"][-1]["x"], you["body"][-1]["y"]))
        tail_free = len(you["body"]) > 1 and you["body"][-1] != you["body"][-2]

        body_set = set((seg["x"], seg["y"]) for seg in you["body"])
        if tail_free:
            body_set.discard(tail)

        food_list = [tuple((f["x"], f["y"])) for f in board["food"]]
        if not food_list:
            return {m: 0.0 for m in ["up", "down", "left", "right"]}

        max_enemy_len = max((s["length"] for s in board["snakes"] if s["id"] != you["id"]), default=0)
        seek_food = health <= 40 or length < max_enemy_len

        nearest_food = min(food_list, key=lambda f: abs(f[0] - head[0]) + abs(f[1] - head[1]))

        def is_dead_end(pos):
            visited = {pos}
            q = deque([pos])
            exit_count = 0
            while q:
                curr = q.popleft()
                cx, cy = curr
                for dx, dy in [(0, 1), (0, -1), (-1, 0), (1, 0)]:
                    nx, ny = cx + dx, cy + dy
                    if not (0 <= nx < width and 0 <= ny < height):
                        continue
                    npos = (nx, ny)
                    if npos not in visited and npos not in all_bodies:
                        visited.add(npos)
                        q.append(npos)
                        if len(visited) > length:
                            return False
            return len(visited) <= length

        scores = {}
        for move, (dx, dy) in [("up", (0, 1)), ("down", (0, -1)), ("left", (-1, 0)), ("right", (1, 0))]:
            nx, ny = head[0] + dx, head[1] + dy

            if not (0 <= nx < width and 0 <= ny < height):
                scores[move] = -1e9
                continue

            next_cell = (nx, ny)
            if next_cell in all_bodies and next_cell != tail:
                scores[move] = -1e9
                continue

            if not seek_food:
                scores[move] = 0.0
            else:
                if next_cell == nearest_food and is_dead_end(nearest_food):
                    scores[move] = -1e9
                    continue

                curr_dist = abs(head[0] - nearest_food[0]) + abs(head[1] - nearest_food[1])
                next_dist = abs(nx - nearest_food[0]) + abs(ny - nearest_food[1])
                progress = curr_dist - next_dist

                if next_cell == nearest_food:
                    scores[move] = 10.0 + progress
                else:
                    scores[move] = float(progress) if progress > 0 else 0.0

        return scores
    except:
        return {"up": 0.0, "down": 0.0, "left": 0.0, "right": 0.0}
