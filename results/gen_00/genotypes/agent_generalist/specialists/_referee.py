def referee(scores, game_state, legal) -> str:
    try:
        if not legal:
            return ""
        vetoed = set()
        for specialist, move_scores in scores.items():
            for move, score in move_scores.items():
                if score <= -5e8:
                    vetoed.add(move)
        candidates = [m for m in legal if m not in vetoed]
        if not candidates:
            return legal[0]
        length = len(game_state.get('you', {}).get('body', []))
        max_length = game_state.get('board', {}).get('height', 11) * game_state.get('board', {}).get('width', 11)
        phase = 0.0 if max_length == 0 else length / max_length
        best_move = candidates[0]
        best_score = float('-inf')
        for move in candidates:
            space_val = scores.get('space_control', {}).get(move, 0.0)
            combat_val = scores.get('combat', {}).get(move, 0.0)
            food_val = scores.get('food', {}).get(move, 0.0)
            endgame_val = scores.get('endgame', {}).get(move, 0.0)
            hazard_val = scores.get('hazard', {}).get(move, 0.0)
            if phase < 0.5:
                score = 0.35 * space_val + 0.25 * hazard_val + 0.20 * food_val + 0.10 * combat_val + 0.10 * endgame_val
            else:
                score = 0.25 * space_val + 0.30 * combat_val + 0.20 * endgame_val + 0.15 * food_val + 0.10 * hazard_val
            if score > best_score:
                best_score = score
                best_move = move
        return best_move
    except:
        return legal[0]
