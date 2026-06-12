"""The LESSON BANK — CORE's non-parametric memory.

A faithful port of the essential CORE memory mechanism (src/memory/{lesson,localized_ucb}.py):
each lesson is a short natural-language insight with a label ("specific" | "meta"), an embedding
of the WEAKNESS/problem it addresses, and utility statistics (uses/wins). Retrieval ranks lessons
for a query problem by  relevance(cosine) x Beta-smoothed-utility  +  a UCB exploration bonus, and
near-duplicate lessons are merged (support++). Verified-acceptance outcomes update wins/uses, so
lessons that lead to admitted mutations are retrieved more often. This is the compounding,
context-efficient memory the paper contrasts against GEPA's stateless reflection.

The ONE faithful simplification vs the reference repo: CORE uses a neural sentence embedder; we use
a deterministic, dependency-free domain embedding (a fixed BattleSnake-strategy vocabulary plus
hashed buckets for out-of-vocabulary tokens). The retrieval MECHANISM (cosine similarity + utility +
UCB + dedup) is identical; only the embedding backend is local. This keeps the bank reproducible and
token-free (it powers the offline mock test), and matches this repo's stdlib+numpy footprint.
"""
import hashlib
import json
import math
import re
from pathlib import Path

import numpy as np

# ----------------------------------------------------------------- deterministic domain embedding
# A curated vocabulary of BattleSnake-harness strategy concepts. Each lesson/weakness text is
# embedded as an L2-normalised bag-of-vocab-counts vector, augmented with hashed buckets so that
# out-of-vocabulary tokens still contribute (and unrelated texts stay near-orthogonal). cosine
# similarity over this space is meaningful for "does this lesson address this weakness?".
_VOCAB = [
    # space / territory
    "space", "control", "flood", "fill", "floodfill", "voronoi", "reachable", "room", "open",
    "area", "territory", "territorial", "region", "pocket",
    # combat / head-to-head
    "combat", "head", "headtohead", "h2h", "collision", "longer", "shorter", "eliminate",
    "kill", "cutoff", "cut", "escape", "aggressive", "aggression", "attack", "fight", "pressure",
    "contest", "opportunism", "duel",
    # food / health
    "food", "health", "starve", "starving", "grow", "growth", "length", "race", "forage",
    "eat", "hungry", "feed",
    # endgame
    "endgame", "late", "lategame", "stall", "stalling", "shrink", "center", "wait",
    # hazard / edge / safety
    "hazard", "edge", "corner", "wall", "safe", "safety", "defensive", "survive", "survival",
    "outlast", "risk", "cautious", "trap", "deadend", "selftrap", "entomb",
    # structure / harness
    "specialist", "referee", "policy", "vote", "weighted", "priority", "merge", "veto", "tester",
    "refine", "robust", "robustness", "lookahead", "predict", "anticipate", "adapt",
    # rungs / outcomes
    "weak", "moderate", "strong", "sonnet", "winrate", "lose", "losing", "win", "winning",
    "fitness", "ladder", "opponent",
]
_VOCAB_INDEX = {w: i for i, w in enumerate(_VOCAB)}
_NBUCKETS = 48
_DIM = len(_VOCAB) + _NBUCKETS

_WORD = re.compile(r"[a-z]+")


def _tokens(text):
    return _WORD.findall((text or "").lower())


def embed(text):
    """Deterministic L2-normalised embedding of `text` over the domain vocab + hashed buckets."""
    v = np.zeros(_DIM, dtype=float)
    for tok in _tokens(text):
        idx = _VOCAB_INDEX.get(tok)
        if idx is not None:
            v[idx] += 1.0
        else:
            h = int(hashlib.sha1(tok.encode("utf-8")).hexdigest(), 16) % _NBUCKETS
            v[len(_VOCAB) + h] += 1.0
    n = float(np.linalg.norm(v))
    return (v / n) if n > 0 else v


def cosine(a, b):
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    na, nb = float(np.linalg.norm(a)), float(np.linalg.norm(b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


# ----------------------------------------------------------------- the bank
DEDUPE_THRESHOLD = 0.92   # cosine over lesson-TEXT embeddings -> merge (support++)
UCB_BETA = 0.30           # exploration weight (CORE's ucb_beta)
REL_FLOOR = 0.05          # a "specific" lesson needs at least this relevance to a query to be retrievable


class Bank:
    """A growing set of utility-weighted lessons, persisted as JSON."""

    def __init__(self):
        self.lessons = []                 # list of dicts (see _new_lesson)
        self.total_retrieval_events = 0.0
        self._next = 0

    # ----- persistence -----
    @classmethod
    def load(cls, path):
        b = cls()
        p = Path(path)
        if p.exists():
            d = json.loads(p.read_text())
            b.lessons = d.get("lessons", [])
            b.total_retrieval_events = float(d.get("total_retrieval_events", 0.0))
            b._next = int(d.get("next_id", len(b.lessons)))
        return b

    def save(self, path):
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({
            "lessons": self.lessons,
            "total_retrieval_events": self.total_retrieval_events,
            "next_id": self._next,
        }, indent=2))

    # ----- mutation -----
    def _new_id(self):
        self._next += 1
        return f"L{self._next:03d}"

    def add(self, text, label, weakness_text, gen, source=None):
        """Add a lesson, merging near-duplicates (by lesson-text embedding) into the existing one
        (support++). `weakness_text` is the loser's weakness profile the lesson addresses -> its
        retrieval key (origin embedding). Returns (lesson_id, merged: bool)."""
        text = (text or "").strip()
        if not text:
            return None, False
        label = label if label in ("specific", "meta") else "specific"
        temb = embed(text)
        for ls in self.lessons:
            if cosine(temb, ls["text_emb"]) >= DEDUPE_THRESHOLD:
                ls["support"] += 1
                # blend the origin (weakness) embedding toward the new evidence
                oe = (np.asarray(ls["origin_emb"]) * (ls["support"] - 1) + embed(weakness_text)) / ls["support"]
                ls["origin_emb"] = oe.tolist()
                if source and source not in ls.get("sources", []):
                    ls.setdefault("sources", []).append(source)
                return ls["id"], True
        lid = self._new_id()
        self.lessons.append({
            "id": lid, "text": text, "label": label,
            "text_emb": temb.tolist(), "origin_emb": embed(weakness_text).tolist(),
            "uses": 0, "wins": 0, "support": 1, "gen_added": gen,
            "sources": [source] if source else [],
        })
        return lid, False

    def utility(self, ls):
        """Beta(1,1)-smoothed verified success rate of mutations that used this lesson."""
        return (ls["wins"] + 1.0) / (ls["uses"] + 2.0)

    def score(self, ls, query_emb, deterministic):
        rel = max(0.0, cosine(query_emb, ls["origin_emb"]))
        util = self.utility(ls)
        # Relevance dominates: a highly-relevant "specific" lesson should outrank a loosely-relevant
        # "meta" one. "meta" lessons get no additive bonus but stay retrievable via the floor
        # exemption in retrieve() (they are broadly applicable when nothing specific fits).
        base = (0.25 + 0.75 * rel) * util
        if not deterministic:                        # UCB exploration (CORE's ucb_bonus)
            base += UCB_BETA * math.sqrt(
                math.log(self.total_retrieval_events + 1.0) / (ls["uses"] + 1.0))
        return base, rel

    def retrieve(self, weakness_text, K, deterministic=False, mark=True):
        """Return up to K lessons most useful for a parent with this weakness profile."""
        q = embed(weakness_text)
        scored = []
        for ls in self.lessons:
            s, rel = self.score(ls, q, deterministic)
            if rel >= REL_FLOOR or ls["label"] == "meta":
                scored.append((s, ls))
        scored.sort(key=lambda t: (-t[0], t[1]["id"]))
        chosen = [ls for _, ls in scored[:K]]
        if mark:
            self.total_retrieval_events += 1.0
        return chosen

    def credit(self, lesson_ids, admitted):
        """Verified-acceptance outcome: every used lesson gets a use; admitted ones also get a win."""
        idset = set(lesson_ids or [])
        for ls in self.lessons:
            if ls["id"] in idset:
                ls["uses"] += 1
                if admitted:
                    ls["wins"] += 1

    # ----- reporting -----
    def snapshot_row(self, gen):
        rows = sorted(({
            "id": ls["id"], "text": ls["text"], "label": ls["label"],
            "uses": ls["uses"], "wins": ls["wins"], "support": ls["support"],
            "utility": round(self.utility(ls), 4), "gen_added": ls["gen_added"],
        } for ls in self.lessons), key=lambda r: (-r["utility"], r["id"]))
        return {"gen": gen, "n_lessons": len(self.lessons),
                "n_meta": sum(1 for l in self.lessons if l["label"] == "meta"),
                "lessons": rows}
