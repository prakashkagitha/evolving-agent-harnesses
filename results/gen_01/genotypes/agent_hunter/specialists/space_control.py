from collections import deque

def score(game_state):
    try:
        you = game_state["you"]
        board = game_state["board"]
        width, height = board["width"], board["height"]
        your_length = you["length"]
        your_head = (you["body"][0]["x"], you["body"][0]["y"])
        your_body = [(cell["x"], cell["y"]) for cell in you["body"]]
        your_tail = your_body[-1]
        just_ate = len(you["body"]) > 1 and you["body"][-1]["x"] == you["body"][-2]["x"] and you["body"][-1]["y"] == you["body"][-2]["y"]

        occupied = set()
        for snake in board["snakes"]:
            for cell in snake["body"]:
                occupied.add((cell["x"], cell["y"]))
        if not just_ate:
            occupied.discard(your_tail)

        def flood_fill(start_x, start_y):
            if start_x < 0 or start_x >= width or start_y < 0 or start_y >= height:
                return 0
            if (start_x, start_y) in occupied:
                return 0
            visited = {(start_x, start_y)}
            queue = deque([(start_x, start_y)])
            while queue:
                x, y = queue.popleft()
                for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < width and 0 <= ny < height and (nx, ny) not in visited and (nx, ny) not in occupied:
                        visited.add((nx, ny))
                        queue.append((nx, ny))
            return len(visited)

        result = {}
        board_area = width * height
        min_space_threshold = max(your_length * 0.8, 5)

        for direction, (dx, dy) in [("up", (0, 1)), ("down", (0, -1)), ("left", (-1, 0)), ("right", (1, 0))]:
            new_x, new_y = your_head[0] + dx, your_head[1] + dy
            if new_x < 0 or new_x >= width or new_y < 0 or new_y >= height or (new_x, new_y) in occupied:
                result[direction] = -1e9
            else:
                reachable = flood_fill(new_x, new_y)
                if reachable < min_space_threshold:
                    result[direction] = -1e9
                else:
                    result[direction] = float(reachable)
        return result
    except:
        return {"up": 0.0, "down": 0.0, "left": 0.0, "right": 0.0}
