from collections import deque

def score(game_state) -> dict:
    try:
        you = game_state["you"]
        board = game_state["board"]
        my_head = tuple(you["body"][0].values()) if you["body"] else None
        my_health = you["health"]
        my_length = you["length"]
        if not my_head:
            return {m: 0.0 for m in ["up", "down", "left", "right"]}
        width, height = board["width"], board["height"]

        occupied = set()
        for snake in board["snakes"]:
            for segment in snake["body"]:
                occupied.add(tuple(segment.values()))
        occupied.discard((you["body"][-1]["x"], you["body"][-1]["y"]))

        food_set = {tuple(f.values()) for f in board["food"]}
        longest_enemy = max((len(s["body"]) for s in board["snakes"] if s["id"] != you["id"]), default=0)
        should_seek_food = my_health < 40 or my_length <= longest_enemy

        def is_dead_end(food_pos):
            visited = {food_pos}
            queue = deque([food_pos])
            count = 1
            while queue:
                x, y = queue.popleft()
                for dx, dy in [(0, 1), (0, -1), (-1, 0), (1, 0)]:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < width and 0 <= ny < height and (nx, ny) not in occupied and (nx, ny) not in visited:
                        visited.add((nx, ny))
                        queue.append((nx, ny))
                        count += 1
            return count < my_length

        moves = {"up": (0, 1), "down": (0, -1), "left": (-1, 0), "right": (1, 0)}
        scores = {}
        for move_name, (dx, dy) in moves.items():
            nx, ny = my_head[0] + dx, my_head[1] + dy
            if not (0 <= nx < width and 0 <= ny < height) or (nx, ny) in occupied:
                scores[move_name] = -1e9
                continue
            new_head = (nx, ny)

            if should_seek_food:
                safe_food = [f for f in food_set if not is_dead_end(f)]
                if safe_food:
                    distances = [(abs(f[0] - new_head[0]) + abs(f[1] - new_head[1]), f) for f in safe_food]
                    min_dist = min(d[0] for d in distances)
                    if (nx, ny) in food_set:
                        scores[move_name] = 8.0
                    else:
                        scores[move_name] = max(0.0, 10.0 - min_dist)
                else:
                    scores[move_name] = 0.0
            else:
                scores[move_name] = 0.0
        return scores
    except Exception:
        return {m: 0.0 for m in ["up", "down", "left", "right"]}
