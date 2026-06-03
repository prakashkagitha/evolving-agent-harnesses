# AUTO-ASSEMBLED decomposition bot (genotype minimal_space, gen 0).
# referee_policy=weighted_vote | specialists=['space_control'] | tester=False | refine_rounds=2
# Each specialist is exec'd in its own namespace (base64) so helpers never collide.
import base64
import typing

_SPEC_B64 = {'space_control': 'ZGVmIHNjb3JlKGdhbWVfc3RhdGUpOgogICAgdHJ5OgogICAgICAgIG15X2hlYWQgPSB0dXBsZShnYW1lX3N0YXRlWyJ5b3UiXVsiYm9keSJdWzBdLnZhbHVlcygpKQogICAgICAgIG15X2xlbmd0aCA9IGdhbWVfc3RhdGVbInlvdSJdWyJsZW5ndGgiXQogICAgICAgIG15X3RhaWwgPSB0dXBsZShnYW1lX3N0YXRlWyJ5b3UiXVsiYm9keSJdWy0xXS52YWx1ZXMoKSkKICAgICAgICBib2FyZCA9IGdhbWVfc3RhdGVbImJvYXJkIl0KICAgICAgICB3aWR0aCwgaGVpZ2h0ID0gYm9hcmRbIndpZHRoIl0sIGJvYXJkWyJoZWlnaHQiXQoKICAgICAgICBib2R5X2NlbGxzID0gc2V0KCkKICAgICAgICBvcHBvbmVudF9oZWFkcyA9IFtdCiAgICAgICAgZm9yIHNuYWtlIGluIGJvYXJkWyJzbmFrZXMiXToKICAgICAgICAgICAgc25ha2VfaWQgPSBzbmFrZS5nZXQoImlkIikKICAgICAgICAgICAgaWYgc25ha2VfaWQgIT0gZ2FtZV9zdGF0ZVsieW91Il0uZ2V0KCJpZCIpOgogICAgICAgICAgICAgICAgaGVhZCA9IHR1cGxlKHNuYWtlWyJib2R5Il1bMF0udmFsdWVzKCkpCiAgICAgICAgICAgICAgICBvcHBvbmVudF9oZWFkcy5hcHBlbmQoaGVhZCkKICAgICAgICAgICAgZm9yIHNlZ21lbnQgaW4gc25ha2VbImJvZHkiXToKICAgICAgICAgICAgICAgIGJvZHlfY2VsbHMuYWRkKHR1cGxlKHNlZ21lbnQudmFsdWVzKCkpKQoKICAgICAgICB0YWlsX2lzX2ZyZWUgPSAobGVuKGdhbWVfc3RhdGVbInlvdSJdWyJib2R5Il0pIDwgMiBvcgogICAgICAgICAgICAgICAgICAgICAgIGdhbWVfc3RhdGVbInlvdSJdWyJib2R5Il1bLTFdICE9IGdhbWVfc3RhdGVbInlvdSJdWyJib2R5Il1bLTJdKQogICAgICAgIGlmIHRhaWxfaXNfZnJlZToKICAgICAgICAgICAgYm9keV9jZWxscy5kaXNjYXJkKG15X3RhaWwpCgogICAgICAgIG1vdmVzID0geyJ1cCI6IDAuMCwgImRvd24iOiAwLjAsICJsZWZ0IjogMC4wLCAicmlnaHQiOiAwLjB9CiAgICAgICAgZGVsdGFzID0geyJ1cCI6ICgwLCAxKSwgImRvd24iOiAoMCwgLTEpLCAibGVmdCI6ICgtMSwgMCksICJyaWdodCI6ICgxLCAwKX0KCiAgICAgICAgZm9yIG1vdmUsIChkeCwgZHkpIGluIGRlbHRhcy5pdGVtcygpOgogICAgICAgICAgICBuZXdfeCwgbmV3X3kgPSBteV9oZWFkWzBdICsgZHgsIG15X2hlYWRbMV0gKyBkeQoKICAgICAgICAgICAgaWYgbmV3X3ggPCAwIG9yIG5ld194ID49IHdpZHRoIG9yIG5ld195IDwgMCBvciBuZXdfeSA+PSBoZWlnaHQ6CiAgICAgICAgICAgICAgICBtb3Zlc1ttb3ZlXSA9IC0xZTkKICAgICAgICAgICAgICAgIGNvbnRpbnVlCgogICAgICAgICAgICBuZXdfaGVhZCA9IChuZXdfeCwgbmV3X3kpCiAgICAgICAgICAgIGlmIG5ld19oZWFkIGluIGJvZHlfY2VsbHM6CiAgICAgICAgICAgICAgICBtb3Zlc1ttb3ZlXSA9IC0xZTkKICAgICAgICAgICAgICAgIGNvbnRpbnVlCgogICAgICAgICAgICB0ZW1wX2JvZHkgPSBib2R5X2NlbGxzLmNvcHkoKQogICAgICAgICAgICB0ZW1wX2JvZHkuZGlzY2FyZChteV90YWlsKQogICAgICAgICAgICB0ZW1wX2JvZHkuYWRkKG5ld19oZWFkKQoKICAgICAgICAgICAgdmlzaXRlZCA9IHNldCgpCiAgICAgICAgICAgIHN0YWNrID0gW25ld19oZWFkXQogICAgICAgICAgICB3aGlsZSBzdGFjazoKICAgICAgICAgICAgICAgIGNlbGwgPSBzdGFjay5wb3AoKQogICAgICAgICAgICAgICAgaWYgY2VsbCBpbiB2aXNpdGVkIG9yIGNlbGxbMF0gPCAwIG9yIGNlbGxbMF0gPj0gd2lkdGggb3IgY2VsbFsxXSA8IDAgb3IgY2VsbFsxXSA+PSBoZWlnaHQ6CiAgICAgICAgICAgICAgICAgICAgY29udGludWUKICAgICAgICAgICAgICAgIGlmIGNlbGwgaW4gdGVtcF9ib2R5OgogICAgICAgICAgICAgICAgICAgIGNvbnRpbnVlCiAgICAgICAgICAgICAgICB2aXNpdGVkLmFkZChjZWxsKQogICAgICAgICAgICAgICAgZm9yIG54LCBueSBpbiBbKGNlbGxbMF0rMSxjZWxsWzFdKSwgKGNlbGxbMF0tMSxjZWxsWzFdKSwgKGNlbGxbMF0sY2VsbFsxXSsxKSwgKGNlbGxbMF0sY2VsbFsxXS0xKV06CiAgICAgICAgICAgICAgICAgICAgaWYgKG54LCBueSkgbm90IGluIHZpc2l0ZWQgYW5kIDAgPD0gbnggPCB3aWR0aCBhbmQgMCA8PSBueSA8IGhlaWdodCBhbmQgKG54LCBueSkgbm90IGluIHRlbXBfYm9keToKICAgICAgICAgICAgICAgICAgICAgICAgc3RhY2suYXBwZW5kKChueCwgbnkpKQoKICAgICAgICAgICAgcmVhY2hhYmxlID0gbGVuKHZpc2l0ZWQpCiAgICAgICAgICAgIGlmIHJlYWNoYWJsZSA8IG15X2xlbmd0aDoKICAgICAgICAgICAgICAgIG1vdmVzW21vdmVdID0gLTFlOQogICAgICAgICAgICBlbHNlOgogICAgICAgICAgICAgICAgc2NvcmVfdmFsID0gZmxvYXQocmVhY2hhYmxlKQoKICAgICAgICAgICAgICAgIG1pbl9kaXN0X3RvX29wcG9uZW50ID0gbWluKFthYnMobmV3X3ggLSBvaFswXSkgKyBhYnMobmV3X3kgLSBvaFsxXSkgZm9yIG9oIGluIG9wcG9uZW50X2hlYWRzXSwgZGVmYXVsdD0xMDApCiAgICAgICAgICAgICAgICBpZiBtaW5fZGlzdF90b19vcHBvbmVudCA9PSAxOgogICAgICAgICAgICAgICAgICAgIHNjb3JlX3ZhbCAtPSAxMDAwCiAgICAgICAgICAgICAgICBlbGlmIG1pbl9kaXN0X3RvX29wcG9uZW50IDw9IDI6CiAgICAgICAgICAgICAgICAgICAgc2NvcmVfdmFsIC09IDEwMAoKICAgICAgICAgICAgICAgIG1vdmVzW21vdmVdID0gc2NvcmVfdmFsCgogICAgICAgIHJldHVybiBtb3ZlcwogICAgZXhjZXB0OgogICAgICAgIHJldHVybiB7InVwIjogMC4wLCAiZG93biI6IDAuMCwgImxlZnQiOiAwLjAsICJyaWdodCI6IDAuMH0K'}
_PRIORITY = ['space_control']
_POLICY = 'weighted_vote'
_MERGE_B64 = ''

_SPECIALISTS = {}
for _n, _b in _SPEC_B64.items():
    _ns = {}
    try:
        exec(base64.b64decode(_b).decode("utf-8"), _ns)
        _f = _ns.get("score")
        _SPECIALISTS[_n] = _f if callable(_f) else None
    except Exception:
        _SPECIALISTS[_n] = None

_MERGE = None
if _MERGE_B64:
    _mns = {}
    try:
        exec(base64.b64decode(_MERGE_B64).decode("utf-8"), _mns)
        _f = _mns.get("referee")
        _MERGE = _f if callable(_f) else None
    except Exception:
        _MERGE = None

_MOVES = {"up": (0, 1), "down": (0, -1), "left": (-1, 0), "right": (1, 0)}
_VETO = -5e8


def info() -> dict:
    return {"apiversion": "1", "author": "decomp", "color": "#22aa88", "head": "default", "tail": "default"}


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
    scores = {}
    for name, fn in _SPECIALISTS.items():
        if fn is None:
            continue
        try:
            s = fn(game_state)
            if isinstance(s, dict):
                scores[name] = {m: float(s.get(m, 0.0)) for m in _MOVES}
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
        return {"move": choice}
    except Exception:
        return {"move": "up"}
