def score(game_state):
    try:
        you = game_state["you"]
        board = game_state["board"]
        head = tuple((you["body"][0]["x"], you["body"][0]["y"]))
        health = you["health"]
        length = you["length"]
        width, height = board["width"], board["height"]
        food_list = [(f["x"], f["y"]) for f in board["food"]]
        hazards = {(h["x"], h["y"]) for h in board["hazards"]}
        snake_bodies = set()
        for snake in board["snakes"]:
            for segment in snake["body"]:
                snake_bodies.add((segment["x"], segment["y"]))
        snake_bodies.discard(head)
        tail = tuple((you["body"][-1]["x"], you["body"][-1]["y"]))
        if len(you["body"]) > 1:
            snake_bodies.discard(tail)

        longest_length = max([s["length"] for s in board["snakes"]], default=0)
        is_longest = length >= longest_length
        should_seek_food = health < 40 or not is_longest

        def bfs_reachable(start, avoid_cells, max_steps=100):
            from collections import deque
            visited, queue = {start}, deque([(start, 0)])
            while queue:
                (x, y), dist = queue.popleft()
                if dist >= max_steps:
                    continue
                for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < width and 0 <= ny < height and (nx, ny) not in visited and (nx, ny) not in avoid_cells:
                        visited.add((nx, ny))
                        queue.append(((nx, ny), dist + 1))
            return visited

        def nearest_food_distance(start, food_cells, avoid):
            from collections import deque
            visited, queue = {start}, deque([(start, 0)])
            while queue:
                (x, y), dist = queue.popleft()
                if (x, y) in food_cells:
                    return dist
                for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < width and 0 <= ny < height and (nx, ny) not in visited and (nx, ny) not in avoid:
                        visited.add((nx, ny))
                        queue.append(((nx, ny), dist + 1))
            return float('inf')

        def is_dead_end(cell, avoid):
            reachable = bfs_reachable(cell, avoid, max_steps=length + 5)
            return len(reachable) < length

        scores = {"up": 0.0, "down": 0.0, "left": 0.0, "right": 0.0}
        moves = {"up": (0, 1), "down": (0, -1), "left": (-1, 0), "right": (1, 0)}

        for direction, (dx, dy) in moves.items():
            nx, ny = head[0] + dx, head[1] + dy
            if not (0 <= nx < width and 0 <= ny < height):
                scores[direction] = -1e9
                continue
            if (nx, ny) in snake_bodies:
                scores[direction] = -1e9
                continue

            new_avoid = snake_bodies.copy()
            if (nx, ny) != tail:
                new_avoid.add(tail)

            if not should_seek_food:
                scores[direction] = 0.0
            elif not food_list:
                scores[direction] = 0.0
            else:
                closest_dist = float('inf')
                for fx, fy in food_list:
                    if is_dead_end((fx, fy), new_avoid):
                        continue
                    dist = nearest_food_distance((nx, ny), {(fx, fy)}, new_avoid)
                    closest_dist = min(closest_dist, dist)
                if closest_dist == float('inf'):
                    scores[direction] = -0.5
                else:
                    scores[direction] = max(0.0, 10.0 - closest_dist * 0.5)

        return scores
    except Exception:
        return {"up": 0.0, "down": 0.0, "left": 0.0, "right": 0.0}
