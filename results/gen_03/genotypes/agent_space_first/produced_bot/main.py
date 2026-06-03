# AUTO-ASSEMBLED decomposition bot (genotype space_first, gen 0).
# referee_policy=weighted_vote | specialists=['space_control', 'food'] | tester=True | refine_rounds=2
# Each specialist is exec'd in its own namespace (base64) so helpers never collide.
import base64
import typing

_SPEC_B64 = {'space_control': 'ZGVmIHNjb3JlKGdhbWVfc3RhdGUpOgogICAgdHJ5OgogICAgICAgIHlvdSA9IGdhbWVfc3RhdGUuZ2V0KCJ5b3UiLCB7fSkKICAgICAgICBib2FyZCA9IGdhbWVfc3RhdGUuZ2V0KCJib2FyZCIsIHt9KQoKICAgICAgICB5b3VyX2lkID0geW91LmdldCgiaWQiKQogICAgICAgIHlvdXJfYm9keSA9IHlvdS5nZXQoImJvZHkiLCBbXSkKICAgICAgICB5b3VyX2hlYWx0aCA9IHlvdS5nZXQoImhlYWx0aCIsIDApCiAgICAgICAgYm9hcmRfd2lkdGggPSBib2FyZC5nZXQoIndpZHRoIiwgMTEpCiAgICAgICAgYm9hcmRfaGVpZ2h0ID0gYm9hcmQuZ2V0KCJoZWlnaHQiLCAxMSkKICAgICAgICBhbGxfc25ha2VzID0gYm9hcmQuZ2V0KCJzbmFrZXMiLCBbXSkKCiAgICAgICAgaWYgbm90IHlvdXJfYm9keToKICAgICAgICAgICAgcmV0dXJuIHsidXAiOiAwLjAsICJkb3duIjogMC4wLCAibGVmdCI6IDAuMCwgInJpZ2h0IjogMC4wfQoKICAgICAgICBoZWFkID0geW91cl9ib2R5WzBdCiAgICAgICAgaGVhZF94LCBoZWFkX3kgPSBoZWFkLmdldCgieCIpLCBoZWFkLmdldCgieSIpCiAgICAgICAgaWYgaGVhZF94IGlzIE5vbmUgb3IgaGVhZF95IGlzIE5vbmU6CiAgICAgICAgICAgIHJldHVybiB7InVwIjogMC4wLCAiZG93biI6IDAuMCwgImxlZnQiOiAwLjAsICJyaWdodCI6IDAuMH0KCiAgICAgICAgIyBDaGVjayBpZiBzbmFrZSBqdXN0IGF0ZQogICAgICAgIGp1c3RfYXRlID0gbGVuKHlvdXJfYm9keSkgPiAxIGFuZCB5b3VyX2JvZHlbLTFdID09IHlvdXJfYm9keVstMl0KCiAgICAgICAgIyBCdWlsZCBvY2N1cGllZCBjZWxscyAoYWxsIHNuYWtlIGJvZGllcyBleGNlcHQgeW91ciB0YWlsIGlmIG5vdCBqdXN0IGF0ZSkKICAgICAgICBvY2N1cGllZCA9IHNldCgpCiAgICAgICAgZm9yIHNuYWtlIGluIGFsbF9zbmFrZXM6CiAgICAgICAgICAgIHNuYWtlX2JvZHkgPSBzbmFrZS5nZXQoImJvZHkiLCBbXSkKICAgICAgICAgICAgc25ha2VfaWQgPSBzbmFrZS5nZXQoImlkIikKCiAgICAgICAgICAgIGlmIHNuYWtlX2lkID09IHlvdXJfaWQ6CiAgICAgICAgICAgICAgICAjIFlvdXIgYm9keTogZXhjbHVkZSB0YWlsIHVubGVzcyBqdXN0IGF0ZQogICAgICAgICAgICAgICAgZm9yIGksIHNlZ21lbnQgaW4gZW51bWVyYXRlKHNuYWtlX2JvZHkpOgogICAgICAgICAgICAgICAgICAgIGlmIGkgPT0gbGVuKHNuYWtlX2JvZHkpIC0gMSBhbmQgbm90IGp1c3RfYXRlOgogICAgICAgICAgICAgICAgICAgICAgICBjb250aW51ZQogICAgICAgICAgICAgICAgICAgIG9jY3VwaWVkLmFkZCgoc2VnbWVudFsieCJdLCBzZWdtZW50WyJ5Il0pKQogICAgICAgICAgICBlbHNlOgogICAgICAgICAgICAgICAgIyBPdGhlciBzbmFrZXM6IGFsbCBzZWdtZW50cwogICAgICAgICAgICAgICAgZm9yIHNlZ21lbnQgaW4gc25ha2VfYm9keToKICAgICAgICAgICAgICAgICAgICBvY2N1cGllZC5hZGQoKHNlZ21lbnRbIngiXSwgc2VnbWVudFsieSJdKSkKCiAgICAgICAgZGVmIGZsb29kX2ZpbGwoc3RhcnRfeCwgc3RhcnRfeSk6CiAgICAgICAgICAgICIiIkZsb29kLWZpbGwgdG8gY291bnQgcmVhY2hhYmxlIGNlbGxzLiIiIgogICAgICAgICAgICBpZiAoc3RhcnRfeCwgc3RhcnRfeSkgaW4gb2NjdXBpZWQ6CiAgICAgICAgICAgICAgICByZXR1cm4gMAogICAgICAgICAgICBpZiBzdGFydF94IDwgMCBvciBzdGFydF94ID49IGJvYXJkX3dpZHRoIG9yIHN0YXJ0X3kgPCAwIG9yIHN0YXJ0X3kgPj0gYm9hcmRfaGVpZ2h0OgogICAgICAgICAgICAgICAgcmV0dXJuIDAKCiAgICAgICAgICAgIHZpc2l0ZWQgPSBzZXQoKQogICAgICAgICAgICBzdGFjayA9IFsoc3RhcnRfeCwgc3RhcnRfeSldCgogICAgICAgICAgICB3aGlsZSBzdGFjazoKICAgICAgICAgICAgICAgIHgsIHkgPSBzdGFjay5wb3AoKQogICAgICAgICAgICAgICAgaWYgKHgsIHkpIGluIHZpc2l0ZWQ6CiAgICAgICAgICAgICAgICAgICAgY29udGludWUKICAgICAgICAgICAgICAgIGlmIHggPCAwIG9yIHggPj0gYm9hcmRfd2lkdGggb3IgeSA8IDAgb3IgeSA+PSBib2FyZF9oZWlnaHQ6CiAgICAgICAgICAgICAgICAgICAgY29udGludWUKICAgICAgICAgICAgICAgIGlmICh4LCB5KSBpbiBvY2N1cGllZDoKICAgICAgICAgICAgICAgICAgICBjb250aW51ZQoKICAgICAgICAgICAgICAgIHZpc2l0ZWQuYWRkKCh4LCB5KSkKICAgICAgICAgICAgICAgIHN0YWNrLmV4dGVuZChbKHgrMSwgeSksICh4LTEsIHkpLCAoeCwgeSsxKSwgKHgsIHktMSldKQoKICAgICAgICAgICAgcmV0dXJuIGxlbih2aXNpdGVkKQoKICAgICAgICAjIFNjb3JlIGVhY2ggbW92ZQogICAgICAgIHJlc3VsdCA9IHt9CiAgICAgICAgbW92ZXMgPSBbCiAgICAgICAgICAgICgidXAiLCAoaGVhZF94LCBoZWFkX3kgKyAxKSksCiAgICAgICAgICAgICgiZG93biIsIChoZWFkX3gsIGhlYWRfeSAtIDEpKSwKICAgICAgICAgICAgKCJsZWZ0IiwgKGhlYWRfeCAtIDEsIGhlYWRfeSkpLAogICAgICAgICAgICAoInJpZ2h0IiwgKGhlYWRfeCArIDEsIGhlYWRfeSkpCiAgICAgICAgXQoKICAgICAgICBmb3IgZGlyZWN0aW9uLCAobmV3X3gsIG5ld195KSBpbiBtb3ZlczoKICAgICAgICAgICAgIyBDaGVjayB3YWxsCiAgICAgICAgICAgIGlmIG5ld194IDwgMCBvciBuZXdfeCA+PSBib2FyZF93aWR0aCBvciBuZXdfeSA8IDAgb3IgbmV3X3kgPj0gYm9hcmRfaGVpZ2h0OgogICAgICAgICAgICAgICAgcmVzdWx0W2RpcmVjdGlvbl0gPSAtMWU5CiAgICAgICAgICAgICAgICBjb250aW51ZQoKICAgICAgICAgICAgIyBDaGVjayBzbmFrZSBib2R5CiAgICAgICAgICAgIGlmIChuZXdfeCwgbmV3X3kpIGluIG9jY3VwaWVkOgogICAgICAgICAgICAgICAgcmVzdWx0W2RpcmVjdGlvbl0gPSAtMWU5CiAgICAgICAgICAgICAgICBjb250aW51ZQoKICAgICAgICAgICAgIyBGbG9vZC1maWxsIGZyb20gbmV3IHBvc2l0aW9uCiAgICAgICAgICAgIHJlYWNoYWJsZSA9IGZsb29kX2ZpbGwobmV3X3gsIG5ld195KQoKICAgICAgICAgICAgIyBWZXRvIGlmIHBvY2tldCBpcyBzbWFsbGVyIHRoYW4geW91ciBsZW5ndGgKICAgICAgICAgICAgaWYgcmVhY2hhYmxlIDwgbGVuKHlvdXJfYm9keSk6CiAgICAgICAgICAgICAgICByZXN1bHRbZGlyZWN0aW9uXSA9IC0xZTkKICAgICAgICAgICAgZWxzZToKICAgICAgICAgICAgICAgIHJlc3VsdFtkaXJlY3Rpb25dID0gZmxvYXQocmVhY2hhYmxlKQoKICAgICAgICByZXR1cm4gcmVzdWx0CiAgICBleGNlcHQ6CiAgICAgICAgcmV0dXJuIHsidXAiOiAwLjAsICJkb3duIjogMC4wLCAibGVmdCI6IDAuMCwgInJpZ2h0IjogMC4wfQo=', 'food': 'ZnJvbSBjb2xsZWN0aW9ucyBpbXBvcnQgZGVxdWUKCmRlZiBzY29yZShnYW1lX3N0YXRlKToKICAgIHlvdSA9IGdhbWVfc3RhdGVbInlvdSJdCiAgICBib2FyZCA9IGdhbWVfc3RhdGVbImJvYXJkIl0KICAgIGhlYWQgPSB0dXBsZSgoeW91WyJib2R5Il1bMF1bIngiXSwgeW91WyJib2R5Il1bMF1bInkiXSkpCiAgICBoZWFsdGggPSB5b3VbImhlYWx0aCJdCiAgICBsZW5ndGggPSB5b3VbImxlbmd0aCJdCgogICAgYm9keV9zZXQgPSB7KGNlbGxbIngiXSwgY2VsbFsieSJdKSBmb3IgY2VsbCBpbiB5b3VbImJvZHkiXX0KICAgIHRhaWwgPSAoeW91WyJib2R5Il1bLTFdWyJ4Il0sIHlvdVsiYm9keSJdWy0xXVsieSJdKQogICAgZm9vZF9saXN0ID0gWyhmWyJ4Il0sIGZbInkiXSkgZm9yIGYgaW4gYm9hcmRbImZvb2QiXV0KCiAgICBhbGxfc25ha2VzID0gYm9hcmRbInNuYWtlcyJdCiAgICBtYXhfZW5lbXlfbGVuZ3RoID0gbWF4KChzWyJsZW5ndGgiXSBmb3IgcyBpbiBhbGxfc25ha2VzIGlmIHNbImlkIl0gIT0geW91WyJpZCJdKSwgZGVmYXVsdD0wKQoKICAgIHdpZHRoLCBoZWlnaHQgPSBib2FyZFsid2lkdGgiXSwgYm9hcmRbImhlaWdodCJdCiAgICBtb3ZlcyA9IHsidXAiOiAoMCwgMSksICJkb3duIjogKDAsIC0xKSwgImxlZnQiOiAoLTEsIDApLCAicmlnaHQiOiAoMSwgMCl9CiAgICBzY29yZXMgPSB7fQoKICAgIGRlZiBpc19pbl9kZWFkX2VuZChwb3MsIGV4Y2x1ZGVfZm9vZD1Ob25lKToKICAgICAgICB2aXNpdGVkID0ge3Bvc30KICAgICAgICBxdWV1ZSA9IGRlcXVlKFtwb3NdKQogICAgICAgIGV4aXRzID0gMAogICAgICAgIHdoaWxlIHF1ZXVlIGFuZCBleGl0cyA8PSAxOgogICAgICAgICAgICB4LCB5ID0gcXVldWUucG9wbGVmdCgpCiAgICAgICAgICAgIGZvciBkeCwgZHkgaW4gWygwLCAxKSwgKDAsIC0xKSwgKDEsIDApLCAoLTEsIDApXToKICAgICAgICAgICAgICAgIG54LCBueSA9IHggKyBkeCwgeSArIGR5CiAgICAgICAgICAgICAgICBpZiAwIDw9IG54IDwgd2lkdGggYW5kIDAgPD0gbnkgPCBoZWlnaHQgYW5kIChueCwgbnkpIG5vdCBpbiB2aXNpdGVkOgogICAgICAgICAgICAgICAgICAgIGlmIChueCwgbnkpIGluIGJvZHlfc2V0IGFuZCAobngsIG55KSAhPSB0YWlsOgogICAgICAgICAgICAgICAgICAgICAgICBjb250aW51ZQogICAgICAgICAgICAgICAgICAgIGlmIGV4Y2x1ZGVfZm9vZCBhbmQgKG54LCBueSkgPT0gZXhjbHVkZV9mb29kOgogICAgICAgICAgICAgICAgICAgICAgICBjb250aW51ZQogICAgICAgICAgICAgICAgICAgIHZpc2l0ZWQuYWRkKChueCwgbnkpKQogICAgICAgICAgICAgICAgICAgIGlmIChueCwgbnkpIG5vdCBpbiBmb29kX2xpc3Q6CiAgICAgICAgICAgICAgICAgICAgICAgIHF1ZXVlLmFwcGVuZCgobngsIG55KSkKICAgICAgICAgICAgICAgICAgICAgICAgaWYgbGVuKHZpc2l0ZWQpID4gbGVuZ3RoICsgMjoKICAgICAgICAgICAgICAgICAgICAgICAgICAgIGV4aXRzICs9IDEKICAgICAgICByZXR1cm4gZXhpdHMgPD0gMQoKICAgIGRlZiBuZWFyZXN0X2Zvb2QocG9zKToKICAgICAgICB2aXNpdGVkID0ge3Bvc30KICAgICAgICBxdWV1ZSA9IGRlcXVlKFsocG9zLCAwKV0pCiAgICAgICAgd2hpbGUgcXVldWU6CiAgICAgICAgICAgICh4LCB5KSwgZGlzdCA9IHF1ZXVlLnBvcGxlZnQoKQogICAgICAgICAgICBpZiAoeCwgeSkgaW4gZm9vZF9saXN0OgogICAgICAgICAgICAgICAgcmV0dXJuIGRpc3QKICAgICAgICAgICAgZm9yIGR4LCBkeSBpbiBbKDAsIDEpLCAoMCwgLTEpLCAoMSwgMCksICgtMSwgMCldOgogICAgICAgICAgICAgICAgbngsIG55ID0geCArIGR4LCB5ICsgZHkKICAgICAgICAgICAgICAgIGlmIDAgPD0gbnggPCB3aWR0aCBhbmQgMCA8PSBueSA8IGhlaWdodCBhbmQgKG54LCBueSkgbm90IGluIHZpc2l0ZWQ6CiAgICAgICAgICAgICAgICAgICAgaWYgKG54LCBueSkgbm90IGluIGJvZHlfc2V0IG9yIChueCwgbnkpID09IHRhaWw6CiAgICAgICAgICAgICAgICAgICAgICAgIHZpc2l0ZWQuYWRkKChueCwgbnkpKQogICAgICAgICAgICAgICAgICAgICAgICBxdWV1ZS5hcHBlbmQoKChueCwgbnkpLCBkaXN0ICsgMSkpCiAgICAgICAgcmV0dXJuIGZsb2F0KCdpbmYnKQoKICAgIGRlZiBpc19oZWFkX29uX2NvbGxpc2lvbihuZXh0X3Bvcyk6CiAgICAgICAgIiIiQ2hlY2sgaWYgbmV4dF9wb3Mgd291bGQgY29sbGlkZSBoZWFkLW9uIHdpdGggYSBsb25nZXIvZXF1YWwgc25ha2UuIiIiCiAgICAgICAgZm9yIHNuYWtlIGluIGFsbF9zbmFrZXM6CiAgICAgICAgICAgIGlmIHNuYWtlWyJpZCJdID09IHlvdVsiaWQiXToKICAgICAgICAgICAgICAgIGNvbnRpbnVlCiAgICAgICAgICAgIGVuZW15X2hlYWQgPSAoc25ha2VbImJvZHkiXVswXVsieCJdLCBzbmFrZVsiYm9keSJdWzBdWyJ5Il0pCiAgICAgICAgICAgIGVuZW15X2xlbmd0aCA9IHNuYWtlWyJsZW5ndGgiXQogICAgICAgICAgICBpZiBsZW5ndGggPD0gZW5lbXlfbGVuZ3RoOgogICAgICAgICAgICAgICAgZm9yIGR4LCBkeSBpbiBbKDAsIDEpLCAoMCwgLTEpLCAoMSwgMCksICgtMSwgMCldOgogICAgICAgICAgICAgICAgICAgIHBvdGVudGlhbF9lbmVteV9uZXh0ID0gKGVuZW15X2hlYWRbMF0gKyBkeCwgZW5lbXlfaGVhZFsxXSArIGR5KQogICAgICAgICAgICAgICAgICAgIGlmIHBvdGVudGlhbF9lbmVteV9uZXh0ID09IG5leHRfcG9zOgogICAgICAgICAgICAgICAgICAgICAgICByZXR1cm4gVHJ1ZQogICAgICAgIHJldHVybiBGYWxzZQoKICAgIHNob3VsZF9zZWVrID0gaGVhbHRoIDw9IDQwIG9yIGxlbmd0aCA8PSBtYXhfZW5lbXlfbGVuZ3RoCgogICAgZm9yIG1vdmVfbmFtZSwgKGR4LCBkeSkgaW4gbW92ZXMuaXRlbXMoKToKICAgICAgICBueCwgbnkgPSBoZWFkWzBdICsgZHgsIGhlYWRbMV0gKyBkeQoKICAgICAgICBpZiBub3QgKDAgPD0gbnggPCB3aWR0aCBhbmQgMCA8PSBueSA8IGhlaWdodCk6CiAgICAgICAgICAgIHNjb3Jlc1ttb3ZlX25hbWVdID0gLTFlOQogICAgICAgICAgICBjb250aW51ZQoKICAgICAgICBpZiAobngsIG55KSBpbiBib2R5X3NldCBhbmQgKG54LCBueSkgIT0gdGFpbDoKICAgICAgICAgICAgc2NvcmVzW21vdmVfbmFtZV0gPSAtMWU5CiAgICAgICAgICAgIGNvbnRpbnVlCgogICAgICAgIGlmIGlzX2hlYWRfb25fY29sbGlzaW9uKChueCwgbnkpKToKICAgICAgICAgICAgc2NvcmVzW21vdmVfbmFtZV0gPSAtMWU5CiAgICAgICAgICAgIGNvbnRpbnVlCgogICAgICAgIGlmIG5vdCBzaG91bGRfc2VlazoKICAgICAgICAgICAgc2NvcmVzW21vdmVfbmFtZV0gPSAwLjAKICAgICAgICBlbHNlOgogICAgICAgICAgICBmb29kX2Rpc3QgPSBuZWFyZXN0X2Zvb2QoKG54LCBueSkpCiAgICAgICAgICAgIGlmIGZvb2RfZGlzdCA9PSBmbG9hdCgnaW5mJyk6CiAgICAgICAgICAgICAgICBzY29yZXNbbW92ZV9uYW1lXSA9IC01LjAKICAgICAgICAgICAgZWxpZiBpc19pbl9kZWFkX2VuZCgobngsIG55KSk6CiAgICAgICAgICAgICAgICBzY29yZXNbbW92ZV9uYW1lXSA9IC04LjAKICAgICAgICAgICAgZWxzZToKICAgICAgICAgICAgICAgIHNjb3Jlc1ttb3ZlX25hbWVdID0gbWF4KDEwLjAgLSBmb29kX2Rpc3QgKiAwLjUsIDAuMSkKCiAgICByZXR1cm4gc2NvcmVzCg=='}
_PRIORITY = ['space_control', 'food']
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
