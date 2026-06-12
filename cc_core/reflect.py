"""Deterministic CORE breeding helpers: contrastive-pair formation, weakness-profile text, and a
lenient parser for the lessons a Sonnet reflection agent writes to disk.

These are the token-free pieces the controller owns; the actual contrastive reflection (read a
winner + loser harness, distil lessons) and the lesson-conditioned mutation are LLM agents in the
workflow, exactly mirroring cc_decomp's "agents write files, the controller reads them" split.
"""
import json
import re

from cc_decomp import harness, store

# The four rungs, ordered weak->hard, for describing where a harness is weak.
RUNGS = ["weak", "moderate", "strong", "sonnet"]


def weakness_text(planner_prompt, per_rung):
    """A compact natural-language profile of a harness: its strategy framing + the rungs it loses
    to (lowest win-rates first). This is the 'problem' a lesson is indexed against and the query a
    mutation retrieves lessons for."""
    parts = []
    rw = [(r, per_rung[r]) for r in RUNGS if r in per_rung]
    rw.sort(key=lambda t: t[1])
    if rw:
        weak = ", ".join(f"weak vs {r} rung (win-rate {wr:.2f})" for r, wr in rw[:2])
        parts.append(weak)
    pp = (planner_prompt or "").strip().replace("\n", " ")
    if pp:
        parts.append("strategy: " + pp[:400])
    return ". ".join(parts) if parts else "no profile"


def specialists_of(decomp):
    return harness.canonical_specialists(decomp or {})


def form_pairs(ranking, n_pairs, margin=0.03):
    """Form contrastive (winner, loser) pairs from a scored generation. Each of the `n_pairs`
    lowest-fitness harnesses (the losers) is paired with a distinct high-fitness harness (a winner)
    whose fitness clearly exceeds it. Returns a list of pair dicts. This is the tournament's native
    contrastive signal that GEPA cannot use."""
    rows = sorted(ranking, key=lambda r: r.get("ladder_fitness", 0.0), reverse=True)
    if len(rows) < 2:
        return []
    winners = rows[: max(1, len(rows) // 2)]
    losers = list(reversed(rows))           # worst first
    pairs = []
    used_loser = set()
    for i in range(min(n_pairs, len(losers))):
        loser = losers[i]
        if loser["id"] in used_loser:
            continue
        # pick the highest-fitness winner that is clearly better than this loser and isn't the loser
        winner = next((w for w in winners
                       if w["id"] != loser["id"]
                       and w.get("ladder_fitness", 0.0) > loser.get("ladder_fitness", 0.0) + margin), None)
        if winner is None:
            continue
        used_loser.add(loser["id"])
        pairs.append({
            "winner_id": winner["id"], "loser_id": loser["id"],
            "winner_fitness": winner.get("ladder_fitness", 0.0),
            "loser_fitness": loser.get("ladder_fitness", 0.0),
            "loser_per_rung": loser.get("per_rung", {}),
            "winner_per_rung": winner.get("per_rung", {}),
        })
    return pairs


# ----------------------------------------------------------------- lenient lesson parsing
# Ported from the reference repo's parse_reflection: tolerate code fences, smart quotes, trailing
# commas, or a bare JSON array, and fall back to "- " bullet lines.
_FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)
_TRAILING_COMMA = re.compile(r",\s*([}\]])")
_BULLET = re.compile(r"^[-*]+\s*(.+)")
_SMART = {"“": '"', "”": '"', "‘": "'", "’": "'"}


def _loads_lenient(s):
    s = (s or "").strip()
    if not s:
        return None
    for attempt in (s, _TRAILING_COMMA.sub(r"\1", "".join(_SMART.get(c, c) for c in s))):
        try:
            return json.loads(attempt)
        except Exception:
            pass
    return None


def parse_lessons(raw, max_lessons=4):
    """Parse a reflection agent's output into [(text, label)] with label in {specific, meta}."""
    raw = (raw or "").strip()
    if not raw:
        return []
    m = _FENCE.findall(raw)
    body = m[-1] if m else raw
    data = _loads_lenient(body)
    if isinstance(data, dict):
        data = data.get("lessons") or data.get("rules") or [data]
    out = []
    if isinstance(data, list):
        for item in data:
            if not isinstance(item, dict):
                continue
            text = (item.get("lesson") or item.get("rule") or "").strip()
            if not text:
                continue
            label = str(item.get("label", "specific")).strip().lower()
            if label not in ("specific", "meta"):
                label = "specific"
            out.append((text, label))
    if not out:                              # bullet fallback
        for line in raw.splitlines():
            mm = _BULLET.match(line.strip())
            if mm and mm.group(1).strip():
                out.append((mm.group(1).strip(), "specific"))
    return out[: max(1, max_lessons)]
