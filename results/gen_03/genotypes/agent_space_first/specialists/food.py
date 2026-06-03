from collections import deque

def score(game_state):
    you = game_state["you"]
    board = game_state["board"]
    head = tuple((you["body"][0]["x"], you["body"][0]["y"]))
    health = you["health"]
    length = you["length"]

    body_set = {(cell["x"], cell["y"]) for cell in you["body"]}
    tail = (you["body"][-1]["x"], you["body"][-1]["y"])
    food_list = [(f["x"], f["y"]) for f in board["food"]]

    all_snakes = board["snakes"]
    max_enemy_length = max((s["length"] for s in all_snakes if s["id"] != you["id"]), default=0)

    width, height = board["width"], board["height"]
    moves = {"up": (0, 1), "down": (0, -1), "left": (-1, 0), "right": (1, 0)}
    scores = {}

    def is_in_dead_end(pos, exclude_food=None):
        visited = {pos}
        queue = deque([pos])
        exits = 0
        while queue and exits <= 1:
            x, y = queue.popleft()
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < width and 0 <= ny < height and (nx, ny) not in visited:
                    if (nx, ny) in body_set and (nx, ny) != tail:
                        continue
                    if exclude_food and (nx, ny) == exclude_food:
                        continue
                    visited.add((nx, ny))
                    if (nx, ny) not in food_list:
                        queue.append((nx, ny))
                        if len(visited) > length + 2:
                            exits += 1
        return exits <= 1

    def nearest_food(pos):
        visited = {pos}
        queue = deque([(pos, 0)])
        while queue:
            (x, y), dist = queue.popleft()
            if (x, y) in food_list:
                return dist
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < width and 0 <= ny < height and (nx, ny) not in visited:
                    if (nx, ny) not in body_set or (nx, ny) == tail:
                        visited.add((nx, ny))
                        queue.append(((nx, ny), dist + 1))
        return float('inf')

    def is_head_on_collision(next_pos):
        """Check if next_pos would collide head-on with a longer/equal snake."""
        for snake in all_snakes:
            if snake["id"] == you["id"]:
                continue
            enemy_head = (snake["body"][0]["x"], snake["body"][0]["y"])
            enemy_length = snake["length"]
            if length <= enemy_length:
                for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                    potential_enemy_next = (enemy_head[0] + dx, enemy_head[1] + dy)
                    if potential_enemy_next == next_pos:
                        return True
        return False

    should_seek = health <= 40 or length <= max_enemy_length

    for move_name, (dx, dy) in moves.items():
        nx, ny = head[0] + dx, head[1] + dy

        if not (0 <= nx < width and 0 <= ny < height):
            scores[move_name] = -1e9
            continue

        if (nx, ny) in body_set and (nx, ny) != tail:
            scores[move_name] = -1e9
            continue

        if is_head_on_collision((nx, ny)):
            scores[move_name] = -1e9
            continue

        if not should_seek:
            scores[move_name] = 0.0
        else:
            food_dist = nearest_food((nx, ny))
            if food_dist == float('inf'):
                scores[move_name] = -5.0
            elif is_in_dead_end((nx, ny)):
                scores[move_name] = -8.0
            else:
                scores[move_name] = max(10.0 - food_dist * 0.5, 0.1)

    return scores
