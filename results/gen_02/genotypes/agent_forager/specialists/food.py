from collections import deque

def score(game_state):
    try:
        you = game_state.get("you", {})
        board = game_state.get("board", {})
        if not you or not board:
            return {m: 0.0 for m in ["up", "down", "left", "right"]}

        head_dict = you.get("body", [{}])[0]
        head = (head_dict.get("x", -1), head_dict.get("y", -1))
        health = you.get("health", 100)
        length = you.get("length", 0)
        your_id = you.get("id", "")

        width, height = board.get("width", 11), board.get("height", 11)
        food_list = [(f.get("x"), f.get("y")) for f in board.get("food", [])]

        body_set = {(b.get("x"), b.get("y")) for b in you.get("body", [])}
        if len(you.get("body", [])) > 1:
            last_seg = you["body"][-1]
            prev_seg = you["body"][-2]
            ate_recently = last_seg.get("x") == prev_seg.get("x") and last_seg.get("y") == prev_seg.get("y")
            if not ate_recently:
                body_set.discard((last_seg.get("x"), last_seg.get("y")))

        all_snake_bodies = set()
        for snake in board.get("snakes", []):
            for segment in snake.get("body", []):
                all_snake_bodies.add((segment.get("x"), segment.get("y")))

        longest_length = max((s.get("length", 0) for s in board.get("snakes", [])), default=1)
        is_longest = length >= longest_length
        should_seek_food = health < 50 or not is_longest

        def bfs_distance(sx, sy, tx, ty):
            visited = {(sx, sy)}
            queue = deque([(sx, sy, 0)])
            while queue:
                x, y, dist = queue.popleft()
                if x == tx and y == ty:
                    return dist
                for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < width and 0 <= ny < height and (nx, ny) not in visited and (nx, ny) not in all_snake_bodies:
                        visited.add((nx, ny))
                        queue.append((nx, ny, dist + 1))
            return float('inf')

        def is_food_in_deadend(fx, fy):
            visited = {(fx, fy)}
            queue = deque([(fx, fy)])
            escape_count = 0
            while queue and escape_count < 2:
                x, y = queue.popleft()
                for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < width and 0 <= ny < height and (nx, ny) not in visited:
                        if (nx, ny) not in all_snake_bodies:
                            visited.add((nx, ny))
                            if (nx, ny) not in food_list:
                                escape_count += 1
                            queue.append((nx, ny))
            return escape_count < 2

        scores = {"up": 0.0, "down": 0.0, "left": 0.0, "right": 0.0}
        moves = {"up": (0, 1), "down": (0, -1), "left": (-1, 0), "right": (1, 0)}

        nearest_food = None
        nearest_dist = float('inf')
        if food_list:
            for fx, fy in food_list:
                if not is_food_in_deadend(fx, fy):
                    d = bfs_distance(head[0], head[1], fx, fy)
                    if d < nearest_dist:
                        nearest_dist = d
                        nearest_food = (fx, fy)

        for direction, (dx, dy) in moves.items():
            nx, ny = head[0] + dx, head[1] + dy
            if not (0 <= nx < width and 0 <= ny < height) or (nx, ny) in all_snake_bodies:
                scores[direction] = -1e9
            elif not should_seek_food:
                scores[direction] = 0.0
            elif nearest_food is None:
                scores[direction] = 0.0
            else:
                old_dist = nearest_dist
                new_dist = bfs_distance(nx, ny, nearest_food[0], nearest_food[1])
                if new_dist < old_dist:
                    scores[direction] = 5.0 + (old_dist - new_dist) * 1.5
                else:
                    scores[direction] = -2.0

        return scores
    except Exception:
        return {m: 0.0 for m in ["up", "down", "left", "right"]}
