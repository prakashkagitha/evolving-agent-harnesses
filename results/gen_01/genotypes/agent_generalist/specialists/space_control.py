from collections import deque

def score(game_state):
    try:
        you = game_state["you"]
        board = game_state["board"]
        your_head = (you["body"][0]["x"], you["body"][0]["y"])
        your_body = [(c["x"], c["y"]) for c in you["body"]]
        your_length = you["length"]
        just_ate = you["health"] == 100 if len(you["body"]) > 1 else False
        if not just_ate and len(you["body"]) > 1:
            just_ate = you["body"][-1]["x"] == you["body"][-2]["x"] and you["body"][-1]["y"] == you["body"][-2]["y"]
        tail = your_body[-1] if not just_ate else None

        obstacles = set()
        for snake in board["snakes"]:
            for segment in snake["body"]:
                obstacles.add((segment["x"], segment["y"]))

        all_snakes_body = obstacles.copy()

        def flood_fill(start_pos, start_obstacles):
            if start_pos[0] < 0 or start_pos[0] >= board["width"] or start_pos[1] < 0 or start_pos[1] >= board["height"]:
                return 0
            if start_pos in start_obstacles:
                return 0
            visited = {start_pos}
            queue = deque([start_pos])
            while queue:
                x, y = queue.popleft()
                for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < board["width"] and 0 <= ny < board["height"] and (nx, ny) not in visited and (nx, ny) not in start_obstacles:
                        visited.add((nx, ny))
                        queue.append((nx, ny))
            return len(visited)

        scores = {}
        moves = [(0, 1, "up"), (0, -1, "down"), (-1, 0, "left"), (1, 0, "right")]

        for dx, dy, move_name in moves:
            new_head = (your_head[0] + dx, your_head[1] + dy)

            if new_head[0] < 0 or new_head[0] >= board["width"] or new_head[1] < 0 or new_head[1] >= board["height"]:
                scores[move_name] = -1e9
                continue

            if new_head in all_snakes_body:
                scores[move_name] = -1e9
                continue

            blocked = all_snakes_body.copy()
            if tail and tail != your_head:
                blocked.discard(tail)
            blocked.discard(your_head)
            blocked.add(new_head)

            reachable = flood_fill(new_head, blocked)

            if reachable < your_length:
                scores[move_name] = -1e9
            else:
                scores[move_name] = float(reachable)

        return scores
    except:
        return {"up": 0.0, "down": 0.0, "left": 0.0, "right": 0.0}
