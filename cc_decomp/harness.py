"""The decomposition adapter — turns a genotype into one BattleSnake bot.

A genotype's `decomposition` names a subset of specialists from a fixed menu, a
`referee_policy`, a `tester` flag, and `refine_rounds`. Each specialist (written
by a Haiku coder, fixed-template prompt) is a self-contained scoring function:

    def score(game_state) -> dict   # {"up":f,"down":f,"left":f,"right":f}; -1e9 = hard veto

The referee combines the active specialists' scores into one move. We embed each
specialist's source base64-encoded and `exec` it in its OWN namespace, so helper
names never collide between specialists and a crashing specialist is isolated
(contributes nothing). The produced `main.py` is fully self-contained.

This module is deterministic (no LLM, no network). It provides:
  - the fixed specialist/referee/coder CONTRACTS (text injected into agent prompts),
  - `assemble_decomp()` / `assemble_simple()` to build the produced bot,
  - an adversarial-board generator + in-process board evaluator (the "tester"),
  - the per-round non-regression "refine score".
"""
import base64
import json
import typing
from pathlib import Path

from . import store

# ----------------------------------------------------------------- fixed contracts (prompt text)

BOT_RULES = r"""BATTLESNAKE RULES (11x11 'standard'). game_state["you"]={"id","health"(0-100),
"body":[{"x","y"}...head first],"length"}. game_state["board"]={"width":11,"height":11,
"food":[{"x","y"}...],"hazards":[...],"snakes":[{"id","health","body":[...],"length"}...]}.
x in [0,10] left->right; y in [0,10] bottom->top. up=+y down=-y left=-x right=+x.
You die if your head leaves the board, enters ANY snake body cell, or health hits 0. Eating food
(stepping onto it) sets health=100 and grows you +1; otherwise health -1/turn. Head-to-head: the
STRICTLY LONGER snake survives (equal length = both die). A snake's tail cell frees next turn UNLESS
it just ate (engine duplicates the last segment that turn: body[-1]==body[-2]). Last snake alive wins.
COORDINATES ARE UNHASHABLE DICTS {"x":int,"y":int} — NEVER put one in a set / use as a dict key /
compare with ==,in. ALWAYS convert to (x,y) tuples first."""

# Per-specialist concern (the FIXED, non-evolved part of each specialist coder's brief).
SPECIALIST_CONCERNS = {
    "space_control":
        "SPACE CONTROL. Your concern is reachable open space (flood-fill / Voronoi). Score each move "
        "by how much open area remains reachable from the resulting head cell (treat your own tail as "
        "free unless you just ate). Strongly prefer moves that keep the most room; HARD-VETO (-1e9) "
        "any move into a pocket smaller than your length (a likely self-trap) and any move into a wall "
        "or a snake body cell.",
    "combat":
        "COMBAT / HEAD-TO-HEAD. Your concern is snake-vs-snake interactions. HARD-VETO (-1e9) any move "
        "into a cell an EQUAL-or-LONGER enemy head could also enter next turn (you would lose/tie the "
        "head-to-head) and any move into a snake body cell. Give a positive bonus to a move that enters "
        "a cell a STRICTLY-SHORTER enemy head could enter (you win that head-to-head) or that cuts off "
        "an enemy's escape space.",
    "food":
        "FOOD & HEALTH. Your concern is growth and not starving. Score moves by progress toward the "
        "nearest reachable food, but only seek food when it matters (health low, or you are not the "
        "longest snake); when healthy and long, prefer holding position over greedily eating. HARD-VETO "
        "(-1e9) a move into a wall or snake body. Never path into food that sits in a dead-end.",
    "endgame":
        "ENDGAME / DUEL CONTROL. Your concern is the late game when few snakes remain. When you are "
        "longer, score moves that pressure the opponent and shrink its space; when shorter, score moves "
        "that stall safely and wait for the opponent to err. Prefer the board center and your own open "
        "side. HARD-VETO (-1e9) walls and body cells.",
    "hazard":
        "HAZARD & EDGE SAFETY. Your concern is avoiding damage and bad terrain. Penalize moves into "
        "hazard cells (game_state['board']['hazards']) and moves that hug the wall/corner when a more "
        "central option exists (edges reduce escape routes). HARD-VETO (-1e9) walls and body cells.",
}

SPECIALIST_CONTRACT = (
    "Write a Python module that defines EXACTLY one entry point:\n"
    "    def score(game_state) -> dict\n"
    "returning {\"up\": float, \"down\": float, \"left\": float, \"right\": float}. Higher = your "
    "concern prefers that move. Return -1e9 for a move your concern considers UNSAFE (a hard veto). "
    "Finite preferences should stay in roughly [-10, 10].\n"
    "score() MUST be a PURE function of game_state (no global mutable state — many games run "
    "concurrently), MUST NEVER raise (wrap risky logic; on any error return {m:0.0 for the 4 moves}), "
    "and may use ONLY the Python standard library. You MAY define helper functions/constants at module "
    "top level (this file is exec'd in its OWN namespace, so names never collide with other specialists).\n"
    + BOT_RULES
)

REFEREE_CONTRACT = (
    "Write a Python module defining EXACTLY:\n"
    "    def referee(scores, game_state, legal) -> str\n"
    "`scores` is {specialist_name: {move: float}} where a value <= -5e8 means that specialist VETOES "
    "the move. `legal` is the list of in-bounds move strings. Return ONE move string from `legal` that "
    "best integrates the specialists per the planner's strategy (e.g. drop vetoed moves, then weigh the "
    "specialists). referee() MUST be PURE, NEVER raise (on error return legal[0]), stdlib only."
)

# The simple-refinement coder writes a WHOLE main.py (no decomposition). Used for the ablation and the
# Sonnet rung. Contract = the full bot contract.
SIMPLE_BOT_CONTRACT = (
    "Write a single self-contained Python file `main.py` controlling one BattleSnake. It MUST define "
    "exactly: info()->dict, start(game_state)->None, end(game_state)->None, "
    "move(game_state)->{\"move\": \"up\"|\"down\"|\"left\"|\"right\"} (do not change signatures). "
    "move() MUST be a PURE function of game_state (no cross-turn globals; many games run concurrently), "
    "use ONLY the stdlib, run fast (<300ms: small flood-fill / shallow lookahead at most), NEVER raise, "
    "and ALWAYS return a legal-looking move.\n" + BOT_RULES
)

# ----------------------------------------------------------------- produced-bot scaffold

_SCAFFOLD = '''# AUTO-ASSEMBLED decomposition bot (genotype {aid}, gen {gen}).
# referee_policy={policy} | specialists={specs} | tester={tester} | refine_rounds={rounds}
# Each specialist is exec'd in its own namespace (base64) so helpers never collide.
import base64
import typing

_SPEC_B64 = {spec_b64!r}
_PRIORITY = {priority!r}
_POLICY = {policy!r}
_MERGE_B64 = {merge_b64!r}

_SPECIALISTS = {{}}
for _n, _b in _SPEC_B64.items():
    _ns = {{}}
    try:
        exec(base64.b64decode(_b).decode("utf-8"), _ns)
        _f = _ns.get("score")
        _SPECIALISTS[_n] = _f if callable(_f) else None
    except Exception:
        _SPECIALISTS[_n] = None

_MERGE = None
if _MERGE_B64:
    _mns = {{}}
    try:
        exec(base64.b64decode(_MERGE_B64).decode("utf-8"), _mns)
        _f = _mns.get("referee")
        _MERGE = _f if callable(_f) else None
    except Exception:
        _MERGE = None

_MOVES = {{"up": (0, 1), "down": (0, -1), "left": (-1, 0), "right": (1, 0)}}
_VETO = -5e8


def info() -> dict:
    return {{"apiversion": "1", "author": "decomp", "color": "#22aa88", "head": "default", "tail": "default"}}


def start(game_state: dict) -> None:
    pass


def end(game_state: dict) -> None:
    pass


def _legal_moves(game_state):
    b = game_state["board"]
    w, h = b["width"], b["height"]
    head = game_state["you"]["body"][0]
    hx, hy = head["x"], head["y"]
    out = []
    for mv, (dx, dy) in _MOVES.items():
        x, y = hx + dx, hy + dy
        if 0 <= x < w and 0 <= y < h:
            out.append(mv)
    return out or list(_MOVES.keys())


def _collect(game_state):
    scores = {{}}
    for name, fn in _SPECIALISTS.items():
        if fn is None:
            continue
        try:
            s = fn(game_state)
            if isinstance(s, dict):
                scores[name] = {{m: float(s.get(m, 0.0)) for m in _MOVES}}
        except Exception:
            pass
    return scores


def _weighted_vote(scores, legal):
    best, bv = None, None
    for mv in legal:
        tot = 0.0
        for sc in scores.values():
            v = sc.get(mv, 0.0)
            tot += -1e6 if v <= _VETO else max(-50.0, min(50.0, v))
        if bv is None or tot > bv:
            bv, best = tot, mv
    return best or legal[0]


def _priority_order(scores, legal):
    vetoed = set()
    for sc in scores.values():
        for mv in legal:
            if sc.get(mv, 0.0) <= _VETO:
                vetoed.add(mv)
    pool = [m for m in legal if m not in vetoed] or list(legal)
    order = [n for n in _PRIORITY if n in scores]

    def key(mv):
        return tuple(-scores[n].get(mv, 0.0) for n in order)
    pool.sort(key=key)
    return pool[0]


def _occupied(game_state):
    occ = set()
    for s in game_state["board"]["snakes"]:
        body = [(c["x"], c["y"]) for c in s["body"]]
        ate = len(body) >= 2 and body[-1] == body[-2]
        for p in (body if ate else body[:-1]):  # tail vacates next turn unless it just ate
            occ.add(p)
    return occ


def _safe_moves(game_state, legal):
    """Legal moves that do NOT step into a snake body cell. The referee picks among these
    when any exist, so the bot never suicides into a body when a safe option is available
    (over-vetoing specialists must not be able to force a fatal move). Strategy still decides
    among the safe options."""
    occ = _occupied(game_state)
    head = game_state["you"]["body"][0]
    hx, hy = head["x"], head["y"]
    out = []
    for mv in legal:
        dx, dy = _MOVES[mv]
        if (hx + dx, hy + dy) not in occ:
            out.append(mv)
    return out


def move(game_state: dict) -> dict:
    try:
        legal = _legal_moves(game_state)
        safe = _safe_moves(game_state, legal)
        pool = safe if safe else legal
        scores = _collect(game_state)
        if not scores:
            choice = pool[0]
        elif _MERGE is not None:
            choice = _MERGE(scores, game_state, pool)
            if choice not in pool:
                choice = _weighted_vote(scores, pool)
        elif _POLICY == "priority_order":
            choice = _priority_order(scores, pool)
        else:
            choice = _weighted_vote(scores, pool)
        if choice not in _MOVES:
            choice = pool[0]
        return {{"move": choice}}
    except Exception:
        return {{"move": "up"}}
'''


def clean_code(text):
    """Strip markdown code fences an LLM may have wrapped around the file (a known silent
    failure mode: fenced code won't compile when exec'd in isolation)."""
    if not text:
        return text
    t = text.strip()
    if t.startswith("```"):
        lines = t.splitlines()
        # drop the opening fence line (``` or ```python) and a trailing fence line
        lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        t = "\n".join(lines)
    return t + ("\n" if not t.endswith("\n") else "")


def _b64(text):
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


def canonical_specialists(decomp):
    """Active specialists in canonical (priority) order, restricted to the fixed menu."""
    specs = [s for s in decomp.get("specialists", []) if s in store.SPECIALIST_MENU]
    # de-dup, preserve order; ensure at least one
    seen, out = set(), []
    for s in specs:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out or ["space_control"]


def assemble_decomp(out, gen, aid):
    """Read the genotype's specialist files + decomposition, write produced_bot/main.py.
    Returns (ok, info_dict). Missing/empty specialist files are skipped (logged)."""
    d = store.agent_dir(out, gen, aid)
    decomp = store.read_json(d / "decomposition.json", {})
    specs = canonical_specialists(decomp)
    policy = decomp.get("referee_policy", "weighted_vote")
    if policy not in store.REFEREE_POLICIES:
        policy = "weighted_vote"
    spec_b64, loaded, missing = {}, [], []
    for name in specs:
        src = clean_code(store.read_text(d / "specialists" / f"{name}.py", ""))
        if src.strip():
            store.write_text(d / "specialists" / f"{name}.py", src)  # persist the cleaned source
            spec_b64[name] = _b64(src)
            loaded.append(name)
        else:
            missing.append(name)
    merge_b64 = ""
    if policy == "planner_merge":
        msrc = clean_code(store.read_text(d / "specialists" / "_referee.py", ""))
        if msrc.strip():
            store.write_text(d / "specialists" / "_referee.py", msrc)
            merge_b64 = _b64(msrc)
    code = _SCAFFOLD.format(
        aid=aid, gen=gen, policy=policy, specs=loaded,
        tester=bool(decomp.get("tester", False)),
        rounds=int(decomp.get("refine_rounds", 0)),
        spec_b64=spec_b64, priority=loaded, merge_b64=merge_b64,
    )
    bot = d / "produced_bot" / "main.py"
    store.write_text(bot, code)
    return True, {"loaded": loaded, "missing": missing, "policy": policy,
                  "planner_merge_code": bool(merge_b64), "bot": str(bot)}


def assemble_simple(src_text, dest_path):
    """Simple-refinement / Sonnet-rung path: the coder wrote a whole main.py directly."""
    store.write_text(dest_path, src_text)
    return True


# ----------------------------------------------------------------- the tester (adversarial boards)

def _gs(width, height, you_body, you_health, snakes, food, hazards=None):
    """Build a minimal valid game_state. you_body/snakes bodies are lists of (x,y) tuples,
    head first. The 'you' snake is included in board['snakes'] too (engine semantics)."""
    def mk(sid, body, health):
        return {"id": sid, "health": health, "length": len(body),
                "head": {"x": body[0][0], "y": body[0][1]},
                "body": [{"x": x, "y": y} for x, y in body]}
    you = mk("you", you_body, you_health)
    board_snakes = [you] + [mk(f"e{i}", b, hh) for i, (b, hh) in enumerate(snakes)]
    return {
        "turn": 30,
        "you": you,
        "board": {"width": width, "height": height,
                  "food": [{"x": x, "y": y} for x, y in (food or [])],
                  "hazards": [{"x": x, "y": y} for x, y in (hazards or [])],
                  "snakes": board_snakes},
    }


def adversarial_boards():
    """Hand-built tricky positions. Each returns (name, game_state, expected_check) where
    expected_check(move, gs) -> (ok, reason) verifies the move is at least non-suicidal."""
    boards = []

    # 1. head in a corner, body trailing right; food top — must not go out of bounds.
    gs = _gs(11, 11, [(0, 0), (1, 0), (2, 0)], 80, [], [(0, 10)])
    boards.append(("corner", gs))

    # 2. boxed: head at (5,5), body wraps so only "up" is open.
    body = [(5, 5), (5, 4), (4, 4), (4, 5), (4, 6)]
    gs = _gs(11, 11, body, 70, [], [(5, 0)])
    boards.append(("boxed_one_exit", gs))

    # 3. low health, food two cells up — should head toward it / stay alive.
    gs = _gs(11, 11, [(5, 5), (5, 4), (5, 3)], 3, [], [(5, 7)])
    boards.append(("starving", gs))

    # 4. equal-length enemy head adjacent above — moving up would tie (both die).
    gs = _gs(11, 11, [(5, 5), (5, 4), (5, 3)], 80,
             [([(5, 7), (5, 8), (5, 9)], 80)], [(9, 9)])
    boards.append(("h2h_equal", gs))

    # 5. longer enemy head two cells away; tight space.
    gs = _gs(11, 11, [(1, 1), (1, 2), (1, 3)], 80,
             [([(3, 1), (4, 1), (5, 1), (6, 1), (7, 1)], 90)], [(0, 10)])
    boards.append(("longer_enemy", gs))

    # 6. near-full board corridor: head at (10,5), only down/up along the edge open.
    occ = [(x, y) for x in range(9) for y in range(11)]  # left 9 columns full of a giant enemy
    enemy_body = occ[:60]
    gs = _gs(11, 11, [(10, 5), (10, 4), (10, 3)], 60, [(enemy_body, 60)], [(10, 10)])
    boards.append(("corridor", gs))

    return boards


def eval_on_boards(bot_path, boards):
    """Load the bot in-process and call move() on each adversarial board. Returns a list of
    findings: which boards crashed or produced a clearly-suicidal move (out of bounds / into a
    known body cell / a losing head-to-head). This is the deterministic tester signal."""
    import importlib.util
    ns = {"__name__": "_advbot"}
    try:
        with open(bot_path) as f:
            exec(compile(f.read(), str(bot_path), "exec"), ns)  # noqa: S102 trusted LLM bot
        move_fn = ns.get("move")
        if not callable(move_fn):
            return [{"board": "load", "ok": False, "reason": "no move() function"}]
    except Exception as e:  # bot doesn't even import
        return [{"board": "load", "ok": False, "reason": f"import error: {type(e).__name__}: {e}"}]

    findings = []
    for name, gs in boards:
        b = gs["board"]
        w, h = b["width"], b["height"]
        head = gs["you"]["body"][0]
        occ = set()
        enemy_heads = []
        mylen = gs["you"]["length"]
        for s in b["snakes"]:
            pts = [(c["x"], c["y"]) for c in s["body"]]
            ja = len(pts) >= 2 and pts[-1] == pts[-2]
            for p in (pts if ja else pts[:-1]):
                occ.add(p)
            if s["id"] != "you":
                enemy_heads.append(((s["body"][0]["x"], s["body"][0]["y"]), s["length"]))
        deltas = {"up": (0, 1), "down": (0, -1), "left": (-1, 0), "right": (1, 0)}
        try:
            out = move_fn(gs)
            mv = out.get("move") if isinstance(out, dict) else None
        except Exception as e:
            findings.append({"board": name, "ok": False, "reason": f"crash: {type(e).__name__}: {e}"})
            continue
        if mv not in deltas:
            findings.append({"board": name, "ok": False, "reason": f"illegal return {out!r}"})
            continue
        dx, dy = deltas[mv]
        nx, ny = head["x"] + dx, head["y"] + dy
        if not (0 <= nx < w and 0 <= ny < h):
            findings.append({"board": name, "ok": False, "reason": f"moved {mv} OUT OF BOUNDS"})
        elif (nx, ny) in occ:
            findings.append({"board": name, "ok": False, "reason": f"moved {mv} into a SNAKE BODY cell"})
        elif any(abs(eh[0] - nx) + abs(eh[1] - ny) == 0 and el >= mylen for eh, el in enemy_heads):
            findings.append({"board": name, "ok": False, "reason": f"moved {mv} into a LOSING head-to-head"})
        else:
            findings.append({"board": name, "ok": True, "reason": f"moved {mv} (safe)"})
    return findings
