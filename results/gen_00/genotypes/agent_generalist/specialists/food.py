from collections import deque

def score(game_state):
    try:
        you = game_state["you"]
        board = game_state["board"]
        head = (you["body"][0]["x"], you["body"][0]["y"])
        health = you["health"]
        length = you["length"]

        width, height = board["width"], board["height"]

        body_set = set((seg["x"], seg["y"]) for seg in you["body"][:-1])
        all_bodies = set()
        for s in board["snakes"]:
            for seg in s["body"]:
                all_bodies.add((seg["x"], seg["y"]))

        is_longest = all(s["length"] <= length for s in board["snakes"] if s["id"] != you["id"])
        should_seek = health <= 40 or not is_longest

        def bfs_nearest_food():
            visited = {head}
            queue = deque([(head, 0)])
            nearest = None
            while queue:
                (x, y), dist = queue.popleft()
                if (x, y) in [(f["x"], f["y"]) for f in board["food"]]:
                    return (x, y), dist
                for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < width and 0 <= ny < height and (nx, ny) not in visited and (nx, ny) not in all_bodies:
                        visited.add((nx, ny))
                        queue.append(((nx, ny), dist + 1))
            return None, float('inf')

        def count_reachable(pos):
            visited = {pos}
            queue = deque([pos])
            while queue:
                x, y = queue.popleft()
                for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < width and 0 <= ny < height and (nx, ny) not in visited and (nx, ny) not in all_bodies:
                        visited.add((nx, ny))
                        queue.append((nx, ny))
            return len(visited)

        nearest_food, min_dist = bfs_nearest_food()

        scores = {"up": 0.0, "down": 0.0, "left": 0.0, "right": 0.0}
        moves = {"up": (0, 1), "down": (0, -1), "left": (-1, 0), "right": (1, 0)}

        for move, (dx, dy) in moves.items():
            nx, ny = head[0] + dx, head[1] + dy
            if not (0 <= nx < width and 0 <= ny < height) or (nx, ny) in all_bodies:
                scores[move] = -1e9
                continue

            if should_seek and nearest_food:
                dist_before = abs(nearest_food[0] - head[0]) + abs(nearest_food[1] - head[1])
                dist_after = abs(nearest_food[0] - nx) + abs(nearest_food[1] - ny)
                if dist_after < dist_before:
                    scores[move] += 5.0
                elif (nx, ny) == nearest_food:
                    if count_reachable((nx, ny)) >= length:
                        scores[move] += 8.0
                    else:
                        scores[move] = -1e9
                else:
                    scores[move] += 0.5
            elif is_longest and health > 50:
                scores[move] -= 1.0
            else:
                scores[move] += 1.0

        return scores
    except:
        return {"up": 0.0, "down": 0.0, "left": 0.0, "right": 0.0}
