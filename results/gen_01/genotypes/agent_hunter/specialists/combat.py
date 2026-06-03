from collections import deque

def score(game_state):
    try:
        board = game_state.get("board", {})
        you = game_state.get("you", {})
        width, height = board.get("width", 11), board.get("height", 11)
        your_head = you.get("body", [{}])[0]
        your_length = you.get("length", 0)
        your_body = {(s["x"], s["y"]) for s in you.get("body", [])[1:]}

        moves = {"up": (0, 1), "down": (0, -1), "left": (-1, 0), "right": (1, 0)}
        scores = {}

        # Build occupied set excluding our tail (we can move into it)
        occupied = set()
        for snake in board.get("snakes", []):
            for segment in snake.get("body", []):
                occupied.add((segment.get("x", 0), segment.get("y", 0)))
        occupied.discard((you.get("body", [{}])[-1].get("x", 0), you.get("body", [{}])[-1].get("y", 0)))

        def has_escape_space(pos, min_space=5):
            """BFS to check if position has enough reachable space."""
            if pos in occupied:
                return False
            visited = {pos}
            queue = deque([pos])
            while queue:
                x, y = queue.popleft()
                for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < width and 0 <= ny < height and (nx, ny) not in visited and (nx, ny) not in occupied:
                        visited.add((nx, ny))
                        queue.append((nx, ny))
            return len(visited) >= min_space

        for direction, (dx, dy) in moves.items():
            nx = your_head.get("x", 0) + dx
            ny = your_head.get("y", 0) + dy

            if nx < 0 or nx >= width or ny < 0 or ny >= height:
                scores[direction] = -1e9
                continue

            if (nx, ny) in your_body:
                scores[direction] = -1e9
                continue

            threat = False
            win = False
            for snake in board.get("snakes", []):
                if snake.get("id") == you.get("id"):
                    continue
                head = snake.get("body", [{}])[0]
                hx, hy = head.get("x", 0), head.get("y", 0)
                enemy_len = snake.get("length", 0)

                for edx, edy in [(0, 1), (0, -1), (-1, 0), (1, 0)]:
                    enx, eny = hx + edx, hy + edy
                    if enx == nx and eny == ny:
                        if enemy_len >= your_length:
                            threat = True
                        elif enemy_len < your_length:
                            win = True

            if threat:
                scores[direction] = -1e9
            elif win:
                # Only encourage win if we have escape space after the move
                if has_escape_space((nx, ny), min_space=4):
                    scores[direction] = 5.0
                else:
                    scores[direction] = 0.0
            else:
                scores[direction] = 0.0

        return scores
    except:
        return {"up": 0.0, "down": 0.0, "left": 0.0, "right": 0.0}
