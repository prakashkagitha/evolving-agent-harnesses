from collections import deque

def score(game_state):
    try:
        you = game_state["you"]
        board = game_state["board"]
        head = tuple(you["body"][0].values())
        your_health = you["health"]
        your_length = you["length"]
        width, height = board["width"], board["height"]

        food_list = [tuple(f.values()) for f in board["food"]]
        hazards = {tuple(h.values()) for h in board["hazards"]}
        all_snake_bodies = set()
        max_other_length = 0
        for snake in board["snakes"]:
            if snake["id"] != you["id"]:
                max_other_length = max(max_other_length, snake["length"])
                for seg in snake["body"]:
                    all_snake_bodies.add(tuple(seg.values()))

        tail = tuple(you["body"][-1].values())
        your_body_set = {tuple(seg.values()) for seg in you["body"][:-1]}

        should_seek_food = your_health < 40 or your_length <= max_other_length

        def is_valid(x, y):
            if x < 0 or x >= width or y < 0 or y >= height:
                return False
            if (x, y) in all_snake_bodies:
                return False
            return True

        def is_dead_end(pos, food_pos):
            queue = deque([pos])
            visited = {pos}
            path_found = pos == food_pos
            while queue and not path_found:
                x, y = queue.popleft()
                for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                    nx, ny = x + dx, y + dy
                    if is_valid(nx, ny) and (nx, ny) not in visited:
                        visited.add((nx, ny))
                        if (nx, ny) == food_pos:
                            path_found = True
                            break
                        queue.append((nx, ny))
            if not path_found:
                return True
            wall_count = sum(1 for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)] if not is_valid(food_pos[0] + dx, food_pos[1] + dy))
            return wall_count >= 3

        def bfs_distance(start, target):
            queue = deque([(start, 0)])
            visited = {start}
            while queue:
                pos, dist = queue.popleft()
                if pos == target:
                    return dist
                x, y = pos
                for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                    nx, ny = x + dx, y + dy
                    if is_valid(nx, ny) and (nx, ny) not in visited:
                        visited.add((nx, ny))
                        queue.append(((nx, ny), dist + 1))
            return float('inf')

        nearest_food = None
        min_dist = float('inf')
        for f in food_list:
            if not is_dead_end((head[0], head[1]), f):
                d = bfs_distance(head, f)
                if d < min_dist:
                    min_dist = d
                    nearest_food = f

        scores = {"up": 0.0, "down": 0.0, "left": 0.0, "right": 0.0}
        moves = {"up": (0, 1), "down": (0, -1), "left": (-1, 0), "right": (1, 0)}

        for move_name, (dx, dy) in moves.items():
            nx, ny = head[0] + dx, head[1] + dy

            if not is_valid(nx, ny):
                scores[move_name] = -1e9
                continue

            if should_seek_food and nearest_food:
                move_dist = bfs_distance((nx, ny), nearest_food)
                if move_dist < min_dist:
                    scores[move_name] = max(10.0, 5.0 - move_dist * 0.5)
                elif move_dist == min_dist:
                    scores[move_name] = 2.0
                else:
                    scores[move_name] = -1.0
            else:
                scores[move_name] = 0.5

        return scores
    except:
        return {m: 0.0 for m in ["up", "down", "left", "right"]}
