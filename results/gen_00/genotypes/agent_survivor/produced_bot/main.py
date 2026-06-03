# AUTO-ASSEMBLED decomposition bot (genotype survivor, gen 0).
# referee_policy=priority_order | specialists=['space_control', 'hazard'] | tester=True | refine_rounds=2
# Each specialist is exec'd in its own namespace (base64) so helpers never collide.
import base64
import typing

_SPEC_B64 = {'space_control': 'ZGVmIHNjb3JlKGdhbWVfc3RhdGUpOgogICAgdHJ5OgogICAgICAgIHlvdSA9IGdhbWVfc3RhdGUuZ2V0KCJ5b3UiLCB7fSkKICAgICAgICBib2FyZCA9IGdhbWVfc3RhdGUuZ2V0KCJib2FyZCIsIHt9KQoKICAgICAgICBpZiBub3QgeW91IG9yIG5vdCBib2FyZDoKICAgICAgICAgICAgcmV0dXJuIHsidXAiOiAwLjAsICJkb3duIjogMC4wLCAibGVmdCI6IDAuMCwgInJpZ2h0IjogMC4wfQoKICAgICAgICB3aWR0aCA9IGJvYXJkLmdldCgid2lkdGgiLCAxMSkKICAgICAgICBoZWlnaHQgPSBib2FyZC5nZXQoImhlaWdodCIsIDExKQogICAgICAgIHlvdXJfYm9keSA9IFt0dXBsZShzZWcudmFsdWVzKCkpIGZvciBzZWcgaW4geW91LmdldCgiYm9keSIsIFtdKV0KICAgICAgICB5b3VyX2xlbmd0aCA9IHlvdS5nZXQoImxlbmd0aCIsIDEpCiAgICAgICAgeW91cl9oZWFsdGggPSB5b3UuZ2V0KCJoZWFsdGgiLCAxMDApCiAgICAgICAganVzdF9hdGUgPSBsZW4oeW91cl9ib2R5KSA+IDEgYW5kIHlvdXJfYm9keVstMV0gPT0geW91cl9ib2R5Wy0yXQoKICAgICAgICBhbGxfc25ha2VzID0gYm9hcmQuZ2V0KCJzbmFrZXMiLCBbXSkKICAgICAgICBvdGhlcl9ib2RpZXMgPSBzZXQoKQogICAgICAgIGZvciBzbmFrZSBpbiBhbGxfc25ha2VzOgogICAgICAgICAgICBpZiBzbmFrZS5nZXQoImlkIikgIT0geW91LmdldCgiaWQiKToKICAgICAgICAgICAgICAgIGZvciBzZWcgaW4gc25ha2UuZ2V0KCJib2R5IiwgW10pOgogICAgICAgICAgICAgICAgICAgIG90aGVyX2JvZGllcy5hZGQodHVwbGUoc2VnLnZhbHVlcygpKSkKCiAgICAgICAgaGF6YXJkcyA9IHNldCh0dXBsZShoLnZhbHVlcygpKSBmb3IgaCBpbiBib2FyZC5nZXQoImhhemFyZHMiLCBbXSkpCgogICAgICAgIGRlZiBpc192YWxpZCh4LCB5KToKICAgICAgICAgICAgcmV0dXJuIDAgPD0geCA8IHdpZHRoIGFuZCAwIDw9IHkgPCBoZWlnaHQKCiAgICAgICAgZGVmIGdldF9yZWFjaGFibGUoaGVhZF94LCBoZWFkX3ksIGJvZHlfdHVwbGUsIGxlbmd0aCk6CiAgICAgICAgICAgIHZpc2l0ZWQgPSBzZXQoKQogICAgICAgICAgICBzdGFjayA9IFsoaGVhZF94LCBoZWFkX3kpXQogICAgICAgICAgICB2aXNpdGVkLmFkZCgoaGVhZF94LCBoZWFkX3kpKQogICAgICAgICAgICB0YWlsX3BvcyA9IGJvZHlfdHVwbGVbLTFdIGlmIGJvZHlfdHVwbGUgZWxzZSBOb25lCiAgICAgICAgICAgIG9jY3VwaWVkID0gc2V0KGJvZHlfdHVwbGVbOi0xXSkgaWYgbm90IGp1c3RfYXRlIGVsc2Ugc2V0KGJvZHlfdHVwbGUpCiAgICAgICAgICAgIGlmIGp1c3RfYXRlIGFuZCB0YWlsX3BvczoKICAgICAgICAgICAgICAgIG9jY3VwaWVkLmFkZCh0YWlsX3BvcykKCiAgICAgICAgICAgIHdoaWxlIHN0YWNrOgogICAgICAgICAgICAgICAgeCwgeSA9IHN0YWNrLnBvcCgpCiAgICAgICAgICAgICAgICBmb3IgZHgsIGR5IGluIFsoMCwgMSksICgwLCAtMSksICgxLCAwKSwgKC0xLCAwKV06CiAgICAgICAgICAgICAgICAgICAgbngsIG55ID0geCArIGR4LCB5ICsgZHkKICAgICAgICAgICAgICAgICAgICBpZiBpc192YWxpZChueCwgbnkpIGFuZCAobngsIG55KSBub3QgaW4gdmlzaXRlZDoKICAgICAgICAgICAgICAgICAgICAgICAgaWYgKG54LCBueSkgbm90IGluIG9jY3VwaWVkIGFuZCAobngsIG55KSBub3QgaW4gb3RoZXJfYm9kaWVzIGFuZCAobngsIG55KSBub3QgaW4gaGF6YXJkczoKICAgICAgICAgICAgICAgICAgICAgICAgICAgIHZpc2l0ZWQuYWRkKChueCwgbnkpKQogICAgICAgICAgICAgICAgICAgICAgICAgICAgc3RhY2suYXBwZW5kKChueCwgbnkpKQoKICAgICAgICAgICAgcmV0dXJuIGxlbih2aXNpdGVkKQoKICAgICAgICBoZWFkX3gsIGhlYWRfeSA9IHlvdXJfYm9keVswXQogICAgICAgIG1vdmVzID0geyJ1cCI6IChoZWFkX3gsIGhlYWRfeSArIDEpLCAiZG93biI6IChoZWFkX3gsIGhlYWRfeSAtIDEpLCAibGVmdCI6IChoZWFkX3ggLSAxLCBoZWFkX3kpLCAicmlnaHQiOiAoaGVhZF94ICsgMSwgaGVhZF95KX0KICAgICAgICBzY29yZXMgPSB7fQoKICAgICAgICBmb3IgbW92ZSwgKG54LCBueSkgaW4gbW92ZXMuaXRlbXMoKToKICAgICAgICAgICAgaWYgbm90IGlzX3ZhbGlkKG54LCBueSk6CiAgICAgICAgICAgICAgICBzY29yZXNbbW92ZV0gPSAtMWU5CiAgICAgICAgICAgIGVsaWYgKG54LCBueSkgaW4gb3RoZXJfYm9kaWVzIG9yIChueCwgbnkpIGluIGhhemFyZHM6CiAgICAgICAgICAgICAgICBzY29yZXNbbW92ZV0gPSAtMWU5CiAgICAgICAgICAgIGVsc2U6CiAgICAgICAgICAgICAgICBuZXdfYm9keSA9IFsobngsIG55KV0gKyB5b3VyX2JvZHlbOi0xXQogICAgICAgICAgICAgICAgcmVhY2hhYmxlID0gZ2V0X3JlYWNoYWJsZShueCwgbnksIHR1cGxlKG5ld19ib2R5KSwgeW91cl9sZW5ndGgpCiAgICAgICAgICAgICAgICBpZiByZWFjaGFibGUgPCB5b3VyX2xlbmd0aDoKICAgICAgICAgICAgICAgICAgICBzY29yZXNbbW92ZV0gPSAtMWU5CiAgICAgICAgICAgICAgICBlbHNlOgogICAgICAgICAgICAgICAgICAgIHNjb3Jlc1ttb3ZlXSA9IGZsb2F0KHJlYWNoYWJsZSkKCiAgICAgICAgcmV0dXJuIHNjb3JlcwogICAgZXhjZXB0OgogICAgICAgIHJldHVybiB7InVwIjogMC4wLCAiZG93biI6IDAuMCwgImxlZnQiOiAwLjAsICJyaWdodCI6IDAuMH0K', 'hazard': 'ZGVmIHNjb3JlKGdhbWVfc3RhdGUpOgogICAgdHJ5OgogICAgICAgIHlvdSA9IGdhbWVfc3RhdGUuZ2V0KCJ5b3UiLCB7fSkKICAgICAgICBib2FyZCA9IGdhbWVfc3RhdGUuZ2V0KCJib2FyZCIsIHt9KQogICAgICAgIGlmIG5vdCB5b3Ugb3Igbm90IGJvYXJkOgogICAgICAgICAgICByZXR1cm4ge206IDAuMCBmb3IgbSBpbiBbInVwIiwgImRvd24iLCAibGVmdCIsICJyaWdodCJdfQoKICAgICAgICBoZWFkID0geW91WyJib2R5Il1bMF0gaWYgeW91LmdldCgiYm9keSIpIGVsc2UgeyJ4IjogMCwgInkiOiAwfQogICAgICAgIGh4LCBoeSA9IGhlYWRbIngiXSwgaGVhZFsieSJdCiAgICAgICAgYm9hcmRfdyA9IGJvYXJkLmdldCgid2lkdGgiLCAxMSkKICAgICAgICBib2FyZF9oID0gYm9hcmQuZ2V0KCJoZWlnaHQiLCAxMSkKCiAgICAgICAgaGF6YXJkX3NldCA9IHNldCgoaFsieCJdLCBoWyJ5Il0pIGZvciBoIGluIGJvYXJkLmdldCgiaGF6YXJkcyIsIFtdKSkKICAgICAgICBib2R5X3NldCA9IHNldCgoYlsieCJdLCBiWyJ5Il0pIGZvciBiIGluIHlvdS5nZXQoImJvZHkiLCBbXSkpCiAgICAgICAgYWxsX3NuYWtlc19ib2R5ID0gc2V0KCkKICAgICAgICBlbmVteV9oZWFkcyA9IHNldCgpCiAgICAgICAgZm9yIHNuYWtlIGluIGJvYXJkLmdldCgic25ha2VzIiwgW10pOgogICAgICAgICAgICBpZiBzbmFrZS5nZXQoImlkIikgIT0geW91LmdldCgiaWQiKToKICAgICAgICAgICAgICAgIGZvciBpLCBjZWxsIGluIGVudW1lcmF0ZShzbmFrZS5nZXQoImJvZHkiLCBbXSkpOgogICAgICAgICAgICAgICAgICAgIGNlbGxfcG9zID0gKGNlbGxbIngiXSwgY2VsbFsieSJdKQogICAgICAgICAgICAgICAgICAgIGFsbF9zbmFrZXNfYm9keS5hZGQoY2VsbF9wb3MpCiAgICAgICAgICAgICAgICAgICAgaWYgaSA9PSAwOgogICAgICAgICAgICAgICAgICAgICAgICBlbmVteV9oZWFkcy5hZGQoY2VsbF9wb3MpCgogICAgICAgIG1vdmVzID0gewogICAgICAgICAgICAidXAiOiAoaHgsIGh5ICsgMSksCiAgICAgICAgICAgICJkb3duIjogKGh4LCBoeSAtIDEpLAogICAgICAgICAgICAibGVmdCI6IChoeCAtIDEsIGh5KSwKICAgICAgICAgICAgInJpZ2h0IjogKGh4ICsgMSwgaHkpCiAgICAgICAgfQoKICAgICAgICBzY29yZXMgPSB7fQogICAgICAgIGZvciBtb3ZlX25hbWUsIChueCwgbnkpIGluIG1vdmVzLml0ZW1zKCk6CiAgICAgICAgICAgIGlmIG54IDwgMCBvciBueCA+PSBib2FyZF93IG9yIG55IDwgMCBvciBueSA+PSBib2FyZF9oOgogICAgICAgICAgICAgICAgc2NvcmVzW21vdmVfbmFtZV0gPSAtMWU5CiAgICAgICAgICAgICAgICBjb250aW51ZQoKICAgICAgICAgICAgaWYgKG54LCBueSkgaW4gYWxsX3NuYWtlc19ib2R5IGFuZCAobngsIG55KSBub3QgaW4gZW5lbXlfaGVhZHM6CiAgICAgICAgICAgICAgICBzY29yZXNbbW92ZV9uYW1lXSA9IC0xZTkKICAgICAgICAgICAgICAgIGNvbnRpbnVlCgogICAgICAgICAgICBzY29yZV92YWwgPSAwLjAKCiAgICAgICAgICAgIGlmIChueCwgbnkpIGluIGhhemFyZF9zZXQ6CiAgICAgICAgICAgICAgICBzY29yZV92YWwgLT0gNS4wCgogICAgICAgICAgICBkaXN0X2Zyb21fZWRnZSA9IG1pbihueCwgbnksIGJvYXJkX3cgLSAxIC0gbngsIGJvYXJkX2ggLSAxIC0gbnkpCiAgICAgICAgICAgIGlmIGRpc3RfZnJvbV9lZGdlID09IDA6CiAgICAgICAgICAgICAgICBzY29yZV92YWwgLT0gMy4wCiAgICAgICAgICAgIGVsaWYgZGlzdF9mcm9tX2VkZ2UgPT0gMToKICAgICAgICAgICAgICAgIHNjb3JlX3ZhbCAtPSAxLjAKCiAgICAgICAgICAgIGNlbnRlcl94ID0gYm9hcmRfdyAvIDIuMAogICAgICAgICAgICBjZW50ZXJfeSA9IGJvYXJkX2ggLyAyLjAKICAgICAgICAgICAgZGlzdF90b19jZW50ZXIgPSBhYnMobnggLSBjZW50ZXJfeCkgKyBhYnMobnkgLSBjZW50ZXJfeSkKICAgICAgICAgICAgc2NvcmVfdmFsICs9ICgxMC4wIC0gZGlzdF90b19jZW50ZXIpICogMC4yCgogICAgICAgICAgICBzY29yZXNbbW92ZV9uYW1lXSA9IHNjb3JlX3ZhbAoKICAgICAgICByZXR1cm4gc2NvcmVzCiAgICBleGNlcHQ6CiAgICAgICAgcmV0dXJuIHttOiAwLjAgZm9yIG0gaW4gWyJ1cCIsICJkb3duIiwgImxlZnQiLCAicmlnaHQiXX0K'}
_PRIORITY = ['space_control', 'hazard']
_POLICY = 'priority_order'
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
