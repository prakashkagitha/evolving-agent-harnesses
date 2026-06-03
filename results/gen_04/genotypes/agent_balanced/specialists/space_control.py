from collections import deque

def score(game_state):
    you = game_state["you"]
    board = game_state["board"]
    head = you["body"][0]
    tail = you["body"][-1]
    your_length = you["length"]
    head_pos = (head["x"], head["y"])
    tail_pos = (tail["x"], tail["y"])
    just_ate = len(you["body"]) > 1 and you["body"][-1] == you["body"][-2]
    occupied = set()
    for snake in board["snakes"]:
        for segment in snake["body"]:
            occupied.add((segment["x"], segment["y"]))
    if not just_ate and tail_pos in occupied:
        occupied.discard(tail_pos)

    def flood_fill(start_pos):
        if start_pos[0] < 0 or start_pos[0] >= board["width"] or start_pos[1] < 0 or start_pos[1] >= board["height"]:
            return 0
        if start_pos in occupied:
            return 0
        visited = {start_pos}
        q = deque([start_pos])
        while q:
            x, y = q.popleft()
            for dx, dy in [(0, 1), (0, -1), (-1, 0), (1, 0)]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < board["width"] and 0 <= ny < board["height"] and (nx, ny) not in visited and (nx, ny) not in occupied:
                    visited.add((nx, ny))
                    q.append((nx, ny))
        return len(visited)

    moves = {"up": 0.0, "down": 0.0, "left": 0.0, "right": 0.0}
    directions = {"up": (0, 1), "down": (0, -1), "left": (-1, 0), "right": (1, 0)}
    for move_name, (dx, dy) in directions.items():
        new_x, new_y = head_pos[0] + dx, head_pos[1] + dy
        new_pos = (new_x, new_y)
        if new_x < 0 or new_x >= board["width"] or new_y < 0 or new_y >= board["height"]:
            moves[move_name] = -1e9
            continue
        if new_pos in occupied:
            moves[move_name] = -1e9
            continue
        blocked = occupied | {new_pos}
        if not just_ate:
            blocked.discard(tail_pos)
        space = flood_fill(new_pos)
        if space < your_length:
            moves[move_name] = -1e9
        else:
            moves[move_name] = float(space)
    return moves
