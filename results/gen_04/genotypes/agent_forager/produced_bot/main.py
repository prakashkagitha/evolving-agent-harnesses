# AUTO-ASSEMBLED decomposition bot (genotype forager, gen 0).
# referee_policy=weighted_vote | specialists=['food', 'space_control'] | tester=False | refine_rounds=2
# Each specialist is exec'd in its own namespace (base64) so helpers never collide.
import base64
import typing

_SPEC_B64 = {'food': 'ZnJvbSBjb2xsZWN0aW9ucyBpbXBvcnQgZGVxdWUKCmRlZiBzY29yZShnYW1lX3N0YXRlKToKICAgIHRyeToKICAgICAgICB5b3UgPSBnYW1lX3N0YXRlLmdldCgieW91Iiwge30pCiAgICAgICAgYm9hcmQgPSBnYW1lX3N0YXRlLmdldCgiYm9hcmQiLCB7fSkKICAgICAgICBpZiBub3QgeW91IG9yIG5vdCBib2FyZDoKICAgICAgICAgICAgcmV0dXJuIHttOiAwLjAgZm9yIG0gaW4gWyJ1cCIsICJkb3duIiwgImxlZnQiLCAicmlnaHQiXX0KCiAgICAgICAgaGVhZF9kaWN0ID0geW91LmdldCgiYm9keSIsIFt7fV0pWzBdCiAgICAgICAgaGVhZCA9IChoZWFkX2RpY3QuZ2V0KCJ4IiwgLTEpLCBoZWFkX2RpY3QuZ2V0KCJ5IiwgLTEpKQogICAgICAgIGhlYWx0aCA9IHlvdS5nZXQoImhlYWx0aCIsIDEwMCkKICAgICAgICBsZW5ndGggPSB5b3UuZ2V0KCJsZW5ndGgiLCAwKQogICAgICAgIHlvdXJfaWQgPSB5b3UuZ2V0KCJpZCIsICIiKQoKICAgICAgICB3aWR0aCwgaGVpZ2h0ID0gYm9hcmQuZ2V0KCJ3aWR0aCIsIDExKSwgYm9hcmQuZ2V0KCJoZWlnaHQiLCAxMSkKICAgICAgICBmb29kX2xpc3QgPSBbKGYuZ2V0KCJ4IiksIGYuZ2V0KCJ5IikpIGZvciBmIGluIGJvYXJkLmdldCgiZm9vZCIsIFtdKV0KCiAgICAgICAgYm9keV9zZXQgPSB7KGIuZ2V0KCJ4IiksIGIuZ2V0KCJ5IikpIGZvciBiIGluIHlvdS5nZXQoImJvZHkiLCBbXSl9CiAgICAgICAgaWYgbGVuKHlvdS5nZXQoImJvZHkiLCBbXSkpID4gMToKICAgICAgICAgICAgbGFzdF9zZWcgPSB5b3VbImJvZHkiXVstMV0KICAgICAgICAgICAgcHJldl9zZWcgPSB5b3VbImJvZHkiXVstMl0KICAgICAgICAgICAgYXRlX3JlY2VudGx5ID0gbGFzdF9zZWcuZ2V0KCJ4IikgPT0gcHJldl9zZWcuZ2V0KCJ4IikgYW5kIGxhc3Rfc2VnLmdldCgieSIpID09IHByZXZfc2VnLmdldCgieSIpCiAgICAgICAgICAgIGlmIG5vdCBhdGVfcmVjZW50bHk6CiAgICAgICAgICAgICAgICBib2R5X3NldC5kaXNjYXJkKChsYXN0X3NlZy5nZXQoIngiKSwgbGFzdF9zZWcuZ2V0KCJ5IikpKQoKICAgICAgICBhbGxfc25ha2VfYm9kaWVzID0gc2V0KCkKICAgICAgICBmb3Igc25ha2UgaW4gYm9hcmQuZ2V0KCJzbmFrZXMiLCBbXSk6CiAgICAgICAgICAgIGZvciBzZWdtZW50IGluIHNuYWtlLmdldCgiYm9keSIsIFtdKToKICAgICAgICAgICAgICAgIGFsbF9zbmFrZV9ib2RpZXMuYWRkKChzZWdtZW50LmdldCgieCIpLCBzZWdtZW50LmdldCgieSIpKSkKCiAgICAgICAgbG9uZ2VzdF9sZW5ndGggPSBtYXgoKHMuZ2V0KCJsZW5ndGgiLCAwKSBmb3IgcyBpbiBib2FyZC5nZXQoInNuYWtlcyIsIFtdKSksIGRlZmF1bHQ9MSkKICAgICAgICBpc19sb25nZXN0ID0gbGVuZ3RoID49IGxvbmdlc3RfbGVuZ3RoCiAgICAgICAgc2hvdWxkX3NlZWtfZm9vZCA9IGhlYWx0aCA8IDUwIG9yIG5vdCBpc19sb25nZXN0CgogICAgICAgIGRlZiBiZnNfZGlzdGFuY2Uoc3gsIHN5LCB0eCwgdHkpOgogICAgICAgICAgICB2aXNpdGVkID0geyhzeCwgc3kpfQogICAgICAgICAgICBxdWV1ZSA9IGRlcXVlKFsoc3gsIHN5LCAwKV0pCiAgICAgICAgICAgIHdoaWxlIHF1ZXVlOgogICAgICAgICAgICAgICAgeCwgeSwgZGlzdCA9IHF1ZXVlLnBvcGxlZnQoKQogICAgICAgICAgICAgICAgaWYgeCA9PSB0eCBhbmQgeSA9PSB0eToKICAgICAgICAgICAgICAgICAgICByZXR1cm4gZGlzdAogICAgICAgICAgICAgICAgZm9yIGR4LCBkeSBpbiBbKDAsIDEpLCAoMCwgLTEpLCAoMSwgMCksICgtMSwgMCldOgogICAgICAgICAgICAgICAgICAgIG54LCBueSA9IHggKyBkeCwgeSArIGR5CiAgICAgICAgICAgICAgICAgICAgaWYgMCA8PSBueCA8IHdpZHRoIGFuZCAwIDw9IG55IDwgaGVpZ2h0IGFuZCAobngsIG55KSBub3QgaW4gdmlzaXRlZCBhbmQgKG54LCBueSkgbm90IGluIGFsbF9zbmFrZV9ib2RpZXM6CiAgICAgICAgICAgICAgICAgICAgICAgIHZpc2l0ZWQuYWRkKChueCwgbnkpKQogICAgICAgICAgICAgICAgICAgICAgICBxdWV1ZS5hcHBlbmQoKG54LCBueSwgZGlzdCArIDEpKQogICAgICAgICAgICByZXR1cm4gZmxvYXQoJ2luZicpCgogICAgICAgIGRlZiBpc19mb29kX2luX2RlYWRlbmQoZngsIGZ5KToKICAgICAgICAgICAgdmlzaXRlZCA9IHsoZngsIGZ5KX0KICAgICAgICAgICAgcXVldWUgPSBkZXF1ZShbKGZ4LCBmeSldKQogICAgICAgICAgICBlc2NhcGVfY291bnQgPSAwCiAgICAgICAgICAgIHdoaWxlIHF1ZXVlIGFuZCBlc2NhcGVfY291bnQgPCAyOgogICAgICAgICAgICAgICAgeCwgeSA9IHF1ZXVlLnBvcGxlZnQoKQogICAgICAgICAgICAgICAgZm9yIGR4LCBkeSBpbiBbKDAsIDEpLCAoMCwgLTEpLCAoMSwgMCksICgtMSwgMCldOgogICAgICAgICAgICAgICAgICAgIG54LCBueSA9IHggKyBkeCwgeSArIGR5CiAgICAgICAgICAgICAgICAgICAgaWYgMCA8PSBueCA8IHdpZHRoIGFuZCAwIDw9IG55IDwgaGVpZ2h0IGFuZCAobngsIG55KSBub3QgaW4gdmlzaXRlZDoKICAgICAgICAgICAgICAgICAgICAgICAgaWYgKG54LCBueSkgbm90IGluIGFsbF9zbmFrZV9ib2RpZXM6CiAgICAgICAgICAgICAgICAgICAgICAgICAgICB2aXNpdGVkLmFkZCgobngsIG55KSkKICAgICAgICAgICAgICAgICAgICAgICAgICAgIGlmIChueCwgbnkpIG5vdCBpbiBmb29kX2xpc3Q6CiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgZXNjYXBlX2NvdW50ICs9IDEKICAgICAgICAgICAgICAgICAgICAgICAgICAgIHF1ZXVlLmFwcGVuZCgobngsIG55KSkKICAgICAgICAgICAgcmV0dXJuIGVzY2FwZV9jb3VudCA8IDIKCiAgICAgICAgc2NvcmVzID0geyJ1cCI6IDAuMCwgImRvd24iOiAwLjAsICJsZWZ0IjogMC4wLCAicmlnaHQiOiAwLjB9CiAgICAgICAgbW92ZXMgPSB7InVwIjogKDAsIDEpLCAiZG93biI6ICgwLCAtMSksICJsZWZ0IjogKC0xLCAwKSwgInJpZ2h0IjogKDEsIDApfQoKICAgICAgICBuZWFyZXN0X2Zvb2QgPSBOb25lCiAgICAgICAgbmVhcmVzdF9kaXN0ID0gZmxvYXQoJ2luZicpCiAgICAgICAgaWYgZm9vZF9saXN0OgogICAgICAgICAgICBmb3IgZngsIGZ5IGluIGZvb2RfbGlzdDoKICAgICAgICAgICAgICAgIGlmIG5vdCBpc19mb29kX2luX2RlYWRlbmQoZngsIGZ5KToKICAgICAgICAgICAgICAgICAgICBkID0gYmZzX2Rpc3RhbmNlKGhlYWRbMF0sIGhlYWRbMV0sIGZ4LCBmeSkKICAgICAgICAgICAgICAgICAgICBpZiBkIDwgbmVhcmVzdF9kaXN0OgogICAgICAgICAgICAgICAgICAgICAgICBuZWFyZXN0X2Rpc3QgPSBkCiAgICAgICAgICAgICAgICAgICAgICAgIG5lYXJlc3RfZm9vZCA9IChmeCwgZnkpCgogICAgICAgIGZvciBkaXJlY3Rpb24sIChkeCwgZHkpIGluIG1vdmVzLml0ZW1zKCk6CiAgICAgICAgICAgIG54LCBueSA9IGhlYWRbMF0gKyBkeCwgaGVhZFsxXSArIGR5CiAgICAgICAgICAgIGlmIG5vdCAoMCA8PSBueCA8IHdpZHRoIGFuZCAwIDw9IG55IDwgaGVpZ2h0KSBvciAobngsIG55KSBpbiBhbGxfc25ha2VfYm9kaWVzOgogICAgICAgICAgICAgICAgc2NvcmVzW2RpcmVjdGlvbl0gPSAtMWU5CiAgICAgICAgICAgIGVsaWYgbm90IHNob3VsZF9zZWVrX2Zvb2Q6CiAgICAgICAgICAgICAgICBzY29yZXNbZGlyZWN0aW9uXSA9IDAuMAogICAgICAgICAgICBlbGlmIG5lYXJlc3RfZm9vZCBpcyBOb25lOgogICAgICAgICAgICAgICAgc2NvcmVzW2RpcmVjdGlvbl0gPSAwLjAKICAgICAgICAgICAgZWxzZToKICAgICAgICAgICAgICAgIG9sZF9kaXN0ID0gbmVhcmVzdF9kaXN0CiAgICAgICAgICAgICAgICBuZXdfZGlzdCA9IGJmc19kaXN0YW5jZShueCwgbnksIG5lYXJlc3RfZm9vZFswXSwgbmVhcmVzdF9mb29kWzFdKQogICAgICAgICAgICAgICAgaWYgbmV3X2Rpc3QgPCBvbGRfZGlzdDoKICAgICAgICAgICAgICAgICAgICBzY29yZXNbZGlyZWN0aW9uXSA9IDUuMCArIChvbGRfZGlzdCAtIG5ld19kaXN0KSAqIDEuNQogICAgICAgICAgICAgICAgZWxzZToKICAgICAgICAgICAgICAgICAgICBzY29yZXNbZGlyZWN0aW9uXSA9IC0yLjAKCiAgICAgICAgcmV0dXJuIHNjb3JlcwogICAgZXhjZXB0IEV4Y2VwdGlvbjoKICAgICAgICByZXR1cm4ge206IDAuMCBmb3IgbSBpbiBbInVwIiwgImRvd24iLCAibGVmdCIsICJyaWdodCJdfQo=', 'space_control': 'ZGVmIHNjb3JlKGdhbWVfc3RhdGUpOgogICAgdHJ5OgogICAgICAgIHlvdSA9IGdhbWVfc3RhdGVbInlvdSJdCiAgICAgICAgYm9hcmQgPSBnYW1lX3N0YXRlWyJib2FyZCJdCiAgICAgICAgd2lkdGgsIGhlaWdodCA9IGJvYXJkWyJ3aWR0aCJdLCBib2FyZFsiaGVpZ2h0Il0KICAgICAgICBoZWFkID0geW91WyJib2R5Il1bMF0KICAgICAgICB5b3VyX2xlbmd0aCA9IHlvdVsibGVuZ3RoIl0KICAgICAgICB5b3VyX2hlYWx0aCA9IHlvdS5nZXQoImhlYWx0aCIsIDEwMCkKICAgICAgICBqdXN0X2F0ZSA9IGxlbih5b3VbImJvZHkiXSkgPiAxIGFuZCB5b3VbImJvZHkiXVstMl0gPT0geW91WyJib2R5Il1bLTFdCgogICAgICAgIG9jY3VwaWVkID0gc2V0KCkKICAgICAgICBlbmVteV9oZWFkcyA9IFtdCiAgICAgICAgZW5lbXlfbGVuZ3RocyA9IFtdCiAgICAgICAgZm9yIHNuYWtlIGluIGJvYXJkWyJzbmFrZXMiXToKICAgICAgICAgICAgaWYgc25ha2VbImlkIl0gIT0geW91WyJpZCJdOgogICAgICAgICAgICAgICAgZW5lbXlfaGVhZHMuYXBwZW5kKChzbmFrZVsiYm9keSJdWzBdWyJ4Il0sIHNuYWtlWyJib2R5Il1bMF1bInkiXSkpCiAgICAgICAgICAgICAgICBlbmVteV9sZW5ndGhzLmFwcGVuZChzbmFrZVsibGVuZ3RoIl0pCiAgICAgICAgICAgIGZvciBzZWdtZW50IGluIHNuYWtlWyJib2R5Il06CiAgICAgICAgICAgICAgICBvY2N1cGllZC5hZGQoKHNlZ21lbnRbIngiXSwgc2VnbWVudFsieSJdKSkKCiAgICAgICAgdGFpbCA9ICh5b3VbImJvZHkiXVstMV1bIngiXSwgeW91WyJib2R5Il1bLTFdWyJ5Il0pCiAgICAgICAgaWYgbm90IGp1c3RfYXRlOgogICAgICAgICAgICBvY2N1cGllZC5kaXNjYXJkKHRhaWwpCgogICAgICAgIGRlZiBmbG9vZF9maWxsKHN0YXJ0X3gsIHN0YXJ0X3kpOgogICAgICAgICAgICBpZiBzdGFydF94IDwgMCBvciBzdGFydF94ID49IHdpZHRoIG9yIHN0YXJ0X3kgPCAwIG9yIHN0YXJ0X3kgPj0gaGVpZ2h0OgogICAgICAgICAgICAgICAgcmV0dXJuIDAKICAgICAgICAgICAgaWYgKHN0YXJ0X3gsIHN0YXJ0X3kpIGluIG9jY3VwaWVkOgogICAgICAgICAgICAgICAgcmV0dXJuIDAKICAgICAgICAgICAgdmlzaXRlZCA9IHNldCgpCiAgICAgICAgICAgIHN0YWNrID0gWyhzdGFydF94LCBzdGFydF95KV0KICAgICAgICAgICAgd2hpbGUgc3RhY2s6CiAgICAgICAgICAgICAgICB4LCB5ID0gc3RhY2sucG9wKCkKICAgICAgICAgICAgICAgIGlmICh4LCB5KSBpbiB2aXNpdGVkIG9yIHggPCAwIG9yIHggPj0gd2lkdGggb3IgeSA8IDAgb3IgeSA+PSBoZWlnaHQgb3IgKHgsIHkpIGluIG9jY3VwaWVkOgogICAgICAgICAgICAgICAgICAgIGNvbnRpbnVlCiAgICAgICAgICAgICAgICB2aXNpdGVkLmFkZCgoeCwgeSkpCiAgICAgICAgICAgICAgICBmb3IgZHgsIGR5IGluIFsoMCwgMSksICgwLCAtMSksICgxLCAwKSwgKC0xLCAwKV06CiAgICAgICAgICAgICAgICAgICAgc3RhY2suYXBwZW5kKCh4ICsgZHgsIHkgKyBkeSkpCiAgICAgICAgICAgIHJldHVybiBsZW4odmlzaXRlZCkKCiAgICAgICAgc2NvcmVzID0ge30KICAgICAgICBtb3ZlcyA9IFsoInVwIiwgMCwgMSksICgiZG93biIsIDAsIC0xKSwgKCJsZWZ0IiwgLTEsIDApLCAoInJpZ2h0IiwgMSwgMCldCgogICAgICAgIGZvciBtb3ZlX25hbWUsIGR4LCBkeSBpbiBtb3ZlczoKICAgICAgICAgICAgbngsIG55ID0gaGVhZFsieCJdICsgZHgsIGhlYWRbInkiXSArIGR5CgogICAgICAgICAgICBpZiBueCA8IDAgb3IgbnggPj0gd2lkdGggb3IgbnkgPCAwIG9yIG55ID49IGhlaWdodCBvciAobngsIG55KSBpbiBvY2N1cGllZDoKICAgICAgICAgICAgICAgIHNjb3Jlc1ttb3ZlX25hbWVdID0gLTFlOQogICAgICAgICAgICBlbHNlOgogICAgICAgICAgICAgICAgc3BhY2UgPSBmbG9vZF9maWxsKG54LCBueSkKICAgICAgICAgICAgICAgIHNwYWNlX3BlbmFsdHkgPSAwLjAKICAgICAgICAgICAgICAgIGlmIHNwYWNlIDwgeW91cl9sZW5ndGg6CiAgICAgICAgICAgICAgICAgICAgc3BhY2VfcGVuYWx0eSA9IC01MDAuMAoKICAgICAgICAgICAgICAgIGhlYWRfZGFuZ2VyID0gMC4wCiAgICAgICAgICAgICAgICBmb3IgaSwgKGV4LCBleSkgaW4gZW51bWVyYXRlKGVuZW15X2hlYWRzKToKICAgICAgICAgICAgICAgICAgICBkaXN0X3RvX2VuZW15ID0gYWJzKG54IC0gZXgpICsgYWJzKG55IC0gZXkpCiAgICAgICAgICAgICAgICAgICAgZW5lbXlfbGVuID0gZW5lbXlfbGVuZ3Roc1tpXQoKICAgICAgICAgICAgICAgICAgICBpZiBkaXN0X3RvX2VuZW15ID09IDA6CiAgICAgICAgICAgICAgICAgICAgICAgIGhlYWRfZGFuZ2VyID0gLTEwMDAuMAogICAgICAgICAgICAgICAgICAgIGVsaWYgZGlzdF90b19lbmVteSA9PSAxOgogICAgICAgICAgICAgICAgICAgICAgICBpZiB5b3VyX2xlbmd0aCA8PSBlbmVteV9sZW46CiAgICAgICAgICAgICAgICAgICAgICAgICAgICBoZWFkX2RhbmdlciA9IC0yMDAuMAogICAgICAgICAgICAgICAgICAgICAgICBlbHNlOgogICAgICAgICAgICAgICAgICAgICAgICAgICAgaGVhZF9kYW5nZXIgPSAtNTAuMAogICAgICAgICAgICAgICAgICAgIGVsaWYgZGlzdF90b19lbmVteSA9PSAyIGFuZCB5b3VyX2hlYWx0aCA8IDUwOgogICAgICAgICAgICAgICAgICAgICAgICBpZiB5b3VyX2xlbmd0aCA8PSBlbmVteV9sZW46CiAgICAgICAgICAgICAgICAgICAgICAgICAgICBoZWFkX2RhbmdlciA9IC0xMDAuMAogICAgICAgICAgICAgICAgICAgICAgICBlbHNlOgogICAgICAgICAgICAgICAgICAgICAgICAgICAgaGVhZF9kYW5nZXIgPSAtMzAuMAoKICAgICAgICAgICAgICAgIHNjb3Jlc1ttb3ZlX25hbWVdID0gZmxvYXQoc3BhY2UpICsgc3BhY2VfcGVuYWx0eSArIGhlYWRfZGFuZ2VyCgogICAgICAgIHJldHVybiBzY29yZXMKICAgIGV4Y2VwdDoKICAgICAgICByZXR1cm4geyJ1cCI6IDAuMCwgImRvd24iOiAwLjAsICJsZWZ0IjogMC4wLCAicmlnaHQiOiAwLjB9Cg=='}
_PRIORITY = ['food', 'space_control']
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
