"""BattleSnake simulation runner — reuses CodeClash's game semantics natively.

We reuse the pieces of CodeClash's BattleSnake arena that constitute the *game*:
  - the official BattleSnake rules engine (`./battlesnake play`, built from the
    vendored github.com/BattlesnakeOfficial/rules in the CodeClash starter repo),
  - the HTTP bot protocol (info/start/move/end), and
  - the JSONL result format (`isDraw`/`winnerName`) and CodeClash's win-tally logic.

What we DON'T reuse: CodeClash's Docker `DockerEnvironment` sandbox (no docker
access on this shared host) and its hard-coded ports (the host is busy). Instead we
serve bots with `cc_gepa.botserver` on OS-assigned free ports and run games as local
subprocesses with high parallelism. This is a faithful adaptation: the bots are real
BattleSnake HTTP bots and the game is the official engine — only the isolation layer
differs. (Documented as a caveat in the analysis.)

This module is a library (used by cc_gepa.gepa) plus a thin CLI for the Phase-0
verification gate.
"""
import json
import os
import socket
import subprocess
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # codeclash-evolution/
BIN = ROOT / "BattleSnake" / "game" / "battlesnake"
PYBIN = sys.executable

# ----------------------------------------------------------------- bot servers


class BotServer:
    """A running bot HTTP server on an OS-assigned free port."""

    def __init__(self, name, bot_path, crashlog):
        self.name = name
        self.bot_path = str(bot_path)
        self.crashlog = str(crashlog)
        self.proc = None
        self.port = None

    def start(self):
        self.proc = subprocess.Popen(
            [PYBIN, "-m", "cc_gepa.botserver", self.bot_path, "--crashlog", self.crashlog],
            cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
        )
        # read the LISTENING <port> line (generous deadline: under concurrent load many
        # interpreters start at once and can be slow to print LISTENING)
        deadline = time.time() + 90
        while time.time() < deadline:
            line = self.proc.stdout.readline()
            if not line:
                if self.proc.poll() is not None:
                    return False
                continue
            if line.startswith("LISTENING "):
                self.port = int(line.split()[1])
                return True
        return False

    def wait_ready(self, timeout=20):
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                with socket.create_connection(("127.0.0.1", self.port), timeout=1):
                    return True
            except OSError:
                time.sleep(0.05)
        return False

    def stop(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.proc.kill()


def crash_count(crashlog):
    try:
        with open(crashlog) as f:
            return sum(1 for _ in f)
    except FileNotFoundError:
        return 0


# ----------------------------------------------------------------- telemetry


def _flood_control(frame):
    """Voronoi board-control: fraction of free cells each snake's head reaches
    first (multi-source BFS). Returns {name: fraction_of_free_cells}."""
    board = frame["board"]
    W, H = board["width"], board["height"]
    snakes = board["snakes"]
    occ = set()
    for s in snakes:
        for c in s["body"]:
            occ.add((c["x"], c["y"]))
    # multi-source BFS from heads
    dist = {}
    owner = {}
    frontier = []
    for s in snakes:
        h = s["body"][0]
        hp = (h["x"], h["y"])
        dist[hp] = 0
        owner[hp] = s["name"]
        frontier.append(hp)
    head_cells = set(dist.keys())  # depth-0 head cells (not free territory)
    d = 0
    contested = set()
    while frontier:
        nxt = []
        d += 1
        reached = defaultdict(set)  # cell -> set of owners reaching at this depth
        for (x, y) in frontier:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if not (0 <= nx < W and 0 <= ny < H):
                    continue
                np = (nx, ny)
                if np in occ or np in dist:
                    continue
                reached[np].add(owner[(x, y)])
        for np, owners in reached.items():
            dist[np] = d
            if len(owners) == 1:
                owner[np] = next(iter(owners))
                nxt.append(np)
            else:
                contested.add(np)  # equidistant: nobody owns, don't expand
        frontier = nxt
    free_total = W * H - len(occ)
    counts = defaultdict(int)
    for c, o in owner.items():
        if c in head_cells:
            continue  # exclude depth-0 heads; count reachable free territory only
        counts[o] += 1
    return {s["name"]: (counts[s["name"]] / free_total if free_total else 0.0) for s in snakes}


def _read_frames(path):
    frames = []
    result = None
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if "winnerName" in obj or "isDraw" in obj:
                result = obj
            elif "board" in obj and "turn" in obj:
                frames.append(obj)
    return frames, result


def game_telemetry(path, names):
    """Parse one game's JSONL → winner + per-snake telemetry."""
    frames, result = _read_frames(path)
    if result is None or not frames:
        return None
    winner = "Tie" if result.get("isDraw") else result.get("winnerName")
    last_turn = frames[-1]["turn"]
    per = {n: {"survival_turns": 0, "length_at_death": 0, "final_health": 0,
               "max_length": 0, "control_sum": 0.0, "control_n": 0,
               "last_head": None, "last_body": None, "alive_end": False} for n in names}
    for fr in frames:
        ctrl = _flood_control(fr) if len(fr["board"]["snakes"]) >= 1 else {}
        alive = {s["name"] for s in fr["board"]["snakes"]}
        for s in fr["board"]["snakes"]:
            n = s["name"]
            if n not in per:
                continue
            per[n]["survival_turns"] = fr["turn"]
            per[n]["length_at_death"] = s.get("length", len(s["body"]))
            per[n]["max_length"] = max(per[n]["max_length"], s.get("length", len(s["body"])))
            per[n]["final_health"] = s["health"]
            per[n]["last_head"] = s["body"][0]
            per[n]["last_body"] = s["body"]
            if n in ctrl:
                per[n]["control_sum"] += ctrl[n]
                per[n]["control_n"] += 1
    end_alive = {s["name"] for s in frames[-1]["board"]["snakes"]}
    for n in names:
        per[n]["alive_end"] = n in end_alive
        per[n]["board_control"] = (per[n]["control_sum"] / per[n]["control_n"]
                                   if per[n]["control_n"] else 0.0)
        per[n]["cause_of_death"] = _infer_cause(per[n], frames, names, end_alive)
        del per[n]["control_sum"], per[n]["control_n"], per[n]["last_body"]
    return {"winner": winner, "turns": last_turn, "per": per}


def _infer_cause(snake_stat, frames, names, end_alive):
    """Heuristic cause-of-death from the last frame the snake appears in."""
    name = None
    for n in names:
        pass
    # find the snake name owning these stats by matching last_head/body identity is hard;
    # caller computes per-snake, so we infer from the snake_stat directly.
    if snake_stat["alive_end"]:
        return "survived"
    if snake_stat["final_health"] <= 1:
        return "starvation"
    head = snake_stat["last_head"]
    if head is None:
        return "unknown"
    # reconstruct board occupancy at the snake's last frame
    last_turn_idx = None
    for i, fr in enumerate(frames):
        present = any(s["body"][0] == head for s in fr["board"]["snakes"])
        if present:
            last_turn_idx = i
    if last_turn_idx is None:
        return "unknown"
    fr = frames[last_turn_idx]
    W, H = fr["board"]["width"], fr["board"]["height"]
    occ = set()
    heads = []
    me_len = 0
    for s in fr["board"]["snakes"]:
        for c in s["body"]:
            occ.add((c["x"], c["y"]))
        heads.append((s["name"], (s["body"][0]["x"], s["body"][0]["y"]), s.get("length", len(s["body"]))))
        if s["body"][0] == head:
            me_len = s.get("length", len(s["body"]))
    hx, hy = head["x"], head["y"]
    nbrs = [(hx + dx, hy + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))]
    safe = [p for p in nbrs if 0 <= p[0] < W and 0 <= p[1] < H and p not in occ]
    in_bounds = [p for p in nbrs if 0 <= p[0] < W and 0 <= p[1] < H]
    if len(in_bounds) < 4 and not safe:
        return "wall_or_trapped"
    if not safe:
        # surrounded by bodies -> collision; check for adjacent longer head (head-to-head)
        for (nm, hp, ln) in heads:
            if hp != (hx, hy) and abs(hp[0] - hx) + abs(hp[1] - hy) <= 2 and ln >= me_len:
                return "head_to_head"
        return "body_collision"
    return "collision"  # had a safe option but engine eliminated it (head-to-head/contested)


# ----------------------------------------------------------------- running games


def _play_one(port_a, name_a, port_b, name_b, out_path, seed, width, height, timeout_ms):
    cmd = [str(BIN), "play", "-W", str(width), "-H", str(height),
           "--url", f"http://0.0.0.0:{port_a}", "-n", name_a,
           "--url", f"http://0.0.0.0:{port_b}", "-n", name_b,
           "-o", str(out_path), "--seed", str(seed), "-t", str(timeout_ms)]
    try:
        subprocess.run(cmd, cwd=str(BIN.parent), stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, timeout=180)
    except subprocess.TimeoutExpired:
        return None
    return out_path


def run_matches(matchups, games, seed, workdir, width=11, height=11, timeout_ms=500,
                max_workers=None, keep_frames=False):
    """Run many independent 2-player matchups, each with its OWN dedicated server
    pair (so games across matchups run truly in parallel — no shared-server CPU
    bottleneck). All games across all matchups share one thread pool.

    matchups: list of {"id": str, "a": {name,path}, "b": {name,path}}.
    Returns {matchup_id: aggregate_result}.
    """
    # MUST be absolute: games run with cwd=BattleSnake/game, so a relative -o frame path
    # would resolve against the wrong dir and silently write no frames (=> spurious 0 win-rates).
    workdir = Path(workdir).resolve()
    (workdir / "frames").mkdir(parents=True, exist_ok=True)
    if max_workers is None:
        max_workers = min(32, max(8, games * len(matchups)))

    # start one server per (matchup, side)
    srv_of = {}   # (mid, side) -> BotServer
    for m in matchups:
        mid = m["id"]
        for side in ("a", "b"):
            b = m[side]
            cl = workdir / f"crash_{mid}_{side}.jsonl"
            if cl.exists():
                cl.unlink()
            srv = BotServer(b["name"], b["path"], cl)
            srv.start()
            srv_of[(mid, side)] = srv
    # readiness — RECORD it (a bound-but-not-accepting server under load must NOT receive games,
    # else its games silently produce no frames => spurious 0.0 win-rates). Generous timeout so
    # heavy concurrent load doesn't spuriously mark a healthy server "not ready".
    ready = {k: bool(srv.port is not None and srv.wait_ready(timeout=90)) for k, srv in srv_of.items()}

    def _play(t):  # t = (mid, gi, out, port_a, na, port_b, nb)
        return _play_one(t[3], t[4], t[5], t[6], t[2], seed + t[1], width, height, timeout_ms)

    def _run(task_list):
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            futs = [ex.submit(_play, t) for t in task_list]
            for f in as_completed(futs):
                f.result()

    def _no_frames(out):
        if not out.exists():
            return True
        try:
            _, res = _read_frames(out)
            return res is None
        except Exception:
            return True

    try:
        results = {}
        tasks = []  # (mid, gi, out, port_a, na, port_b, nb)
        for m in matchups:
            mid = m["id"]
            sa, sb = srv_of[(mid, "a")], srv_of[(mid, "b")]
            na, nb = m["a"]["name"], m["b"]["name"]
            ra, rb = ready[(mid, "a")], ready[(mid, "b")]
            if not (ra and rb):  # one/both servers never became ready
                if ra and not rb:
                    results[mid] = _empty_result([na, nb], games, winner_all=na, failed=[nb])
                elif rb and not ra:
                    results[mid] = _empty_result([na, nb], games, winner_all=nb, failed=[na])
                else:
                    results[mid] = _empty_result([na, nb], games, failed=[na, nb])
                continue
            for gi in range(games):
                out = workdir / "frames" / f"{mid}_g{gi}.jsonl"
                if out.exists():
                    out.unlink()
                tasks.append((mid, gi, out, sa.port, na, sb.port, nb))

        _run(tasks)
        # retry games that produced no parseable result (transient sim/HTTP hiccups) — up to 2x
        for _ in range(2):
            retry = [t for t in tasks if _no_frames(t[2])]
            if not retry:
                break
            _run(retry)

        done = {}
        for t in tasks:
            done.setdefault(t[0], []).append((t[2], t[4], t[6]))
        for m in matchups:
            mid = m["id"]
            if mid in results:
                continue
            na, nb = m["a"]["name"], m["b"]["name"]
            results[mid] = _aggregate(mid, na, nb, done.get(mid, []),
                                      srv_of[(mid, "a")].crashlog, srv_of[(mid, "b")].crashlog,
                                      games, keep_frames)
        return results
    finally:
        for srv in srv_of.values():
            srv.stop()


def _aggregate(mid, na, nb, game_outputs, crashlog_a, crashlog_b, games, keep_frames):
    names = [na, nb]
    wins = defaultdict(int)
    agg = {n: defaultdict(float) for n in names}
    agg_n = {n: 0 for n in names}
    for out, _, _ in game_outputs:
        if not out.exists():
            continue
        tel = game_telemetry(out, names)
        if not keep_frames:
            out.unlink(missing_ok=True)
        if tel is None:
            continue
        wins[tel["winner"]] += 1
        for n in names:
            p = tel["per"][n]
            for k in ("survival_turns", "length_at_death", "final_health", "max_length", "board_control"):
                agg[n][k] += p[k]
            agg[n]["alive_end"] += 1 if p["alive_end"] else 0
            agg[n][f"cod_{p['cause_of_death']}"] += 1
            agg_n[n] += 1
    played = sum(wins.values())
    result = {"id": mid, "names": names, "games_requested": games, "games_played": played,
              "wins": dict(wins), "draws": wins.get("Tie", 0)}
    crashlogs = {na: crashlog_a, nb: crashlog_b}
    for n in names:
        nn = max(agg_n[n], 1)
        tele = {k: (v / nn) for k, v in agg[n].items()
                if not k.startswith("cod_") and k != "alive_end"}
        tele["alive_end_rate"] = agg[n]["alive_end"] / nn
        tele["win_rate"] = wins.get(n, 0) / max(played, 1)
        tele["crashes"] = crash_count(crashlogs[n])
        tele["cause_of_death"] = {k[4:]: int(v) for k, v in agg[n].items() if k.startswith("cod_")}
        result[n] = tele
    return result


def play_matchup(bots, games, seed, workdir, **kw):
    """Single 2-bot matchup (kept for the Phase-0 CLI gate)."""
    res = run_matches([{"id": "m", "a": bots[0], "b": bots[1]}], games, seed, workdir, **kw)
    return res["m"]


def per_game_results(matchups, games, seed, workdir, width=11, height=11, timeout_ms=500,
                     max_workers=None):
    """Like run_matches but returns the PER-GAME winner of side 'a' (the candidate) for each
    matchup — needed for PAIRED, common-seed acceptance tests. Game i of every matchup uses
    seed `seed+i`, so two matchups that share an opponent+seed face identical board luck.
    Returns {matchup_id: [1|0 per game]} where 1 = side-'a' won game i (0 = lost/tied/no-result)."""
    workdir = Path(workdir).resolve()
    (workdir / "frames").mkdir(parents=True, exist_ok=True)
    if max_workers is None:
        max_workers = min(64, max(8, games * len(matchups)))
    srv_of = {}
    for m in matchups:
        for side in ("a", "b"):
            b = m[side]
            cl = workdir / f"crash_{m['id']}_{side}.jsonl"
            if cl.exists():
                cl.unlink()
            srv = BotServer(b["name"], b["path"], cl)
            srv.start()
            srv_of[(m["id"], side)] = srv
    ready = {k: bool(s.port is not None and s.wait_ready(timeout=90)) for k, s in srv_of.items()}
    try:
        tasks = []  # (mid, gi, out, pa, na, pb, nb)
        results = {}
        for m in matchups:
            mid = m["id"]
            sa, sb = srv_of[(mid, "a")], srv_of[(mid, "b")]
            na, nb = m["a"]["name"], m["b"]["name"]
            if not (ready[(mid, "a")] and ready[(mid, "b")]):
                results[mid] = [1 if ready[(mid, "a")] and not ready[(mid, "b")] else 0] * games
                continue
            for gi in range(games):
                out = workdir / "frames" / f"{mid}_g{gi}.jsonl"
                if out.exists():
                    out.unlink()
                tasks.append((mid, gi, out, sa.port, na, sb.port, nb))

        def _play(t):
            return _play_one(t[3], t[4], t[5], t[6], t[2], seed + t[1], width, height, timeout_ms)

        def _run(tl):
            with ThreadPoolExecutor(max_workers=max_workers) as ex:
                for f in as_completed([ex.submit(_play, t) for t in tl]):
                    f.result()

        def _no(out):
            if not out.exists():
                return True
            try:
                _, r = _read_frames(out)
                return r is None
            except Exception:
                return True

        _run(tasks)
        for _ in range(2):
            retry = [t for t in tasks if _no(t[2])]
            if not retry:
                break
            _run(retry)

        per = {}
        for t in tasks:
            mid, gi, out, _, na, _, nb = t
            win = 0
            if out.exists():
                tel = game_telemetry(out, [na, nb])
                if tel is not None and tel["winner"] == na:
                    win = 1
                out.unlink(missing_ok=True)
            per.setdefault(mid, {})[gi] = win
        for mid, gmap in per.items():
            results[mid] = [gmap.get(i, 0) for i in range(games)]
        return results
    finally:
        for s in srv_of.values():
            s.stop()


def score_pool(candidates, opponent, games, seed, workdir, **kw):
    """Inner-GEPA fitness: score each candidate vs a fixed opponent bot.
    Each candidate gets its own dedicated opponent instance (no shared bottleneck).
    candidates: list of {name, path}; opponent: {name, path}.
    Returns {candidate_name: {win_rate, telemetry...}}.
    """
    matchups = [{"id": c["name"], "a": c,
                 "b": {"name": opponent["name"], "path": opponent["path"]}} for c in candidates]
    res = run_matches(matchups, games, seed, workdir, **kw)
    out = {}
    for c in candidates:
        r = res[c["name"]]
        cand = dict(r[c["name"]])
        cand["games_played"] = r["games_played"]
        cand["opp_win_rate"] = r[opponent["name"]]["win_rate"] if opponent["name"] in r else None
        out[c["name"]] = cand
    return out


def round_robin(bots, games, seed, workdir, **kw):
    """All unordered pairs among `bots` (list of {name,path}). Returns
    {"matrix": {a: {b: a_win_rate}}, "wins": {name: total_wins}, "matchups": {...}}."""
    pairs = []
    for i in range(len(bots)):
        for j in range(i + 1, len(bots)):
            pairs.append({"id": f"{bots[i]['name']}__vs__{bots[j]['name']}",
                          "a": bots[i], "b": bots[j]})
    res = run_matches(pairs, games, seed, workdir, **kw)
    names = [b["name"] for b in bots]
    matrix = {n: {} for n in names}
    total_wins = {n: 0.0 for n in names}
    total_games = {n: 0 for n in names}
    for p in pairs:
        r = res[p["id"]]
        na, nb = p["a"]["name"], p["b"]["name"]
        wa, wb = r["wins"].get(na, 0), r["wins"].get(nb, 0)
        played = max(r["games_played"], 1)
        matrix[na][nb] = wa / played
        matrix[nb][na] = wb / played
        total_wins[na] += wa + 0.5 * r["draws"]
        total_wins[nb] += wb + 0.5 * r["draws"]
        total_games[na] += r["games_played"]
        total_games[nb] += r["games_played"]
    fitness = {n: (total_wins[n] / total_games[n] if total_games[n] else 0.0) for n in names}
    return {"matrix": matrix, "fitness": fitness, "total_wins": total_wins,
            "total_games": total_games, "matchups": res}


def _empty_result(names, games, winner_all=None, failed=None):
    res = {"names": names, "games_requested": games,
           "games_played": games if winner_all else 0,
           "wins": {winner_all: games} if winner_all else {}, "draws": 0,
           "failed_to_start": failed or []}
    for n in names:
        res[n] = {"win_rate": 1.0 if n == winner_all else 0.0, "crashes": 0,
                  "survival_turns": 0, "length_at_death": 0, "final_health": 0,
                  "max_length": 0, "board_control": 0.0, "alive_end_rate": 0.0,
                  "cause_of_death": {"failed_to_start": games} if n in (failed or []) else {}}
    return res


# ----------------------------------------------------------------- CLI (Phase-0 gate)


def _cli():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["match"])
    ap.add_argument("--a", required=True, help="name=path")
    ap.add_argument("--b", required=True, help="name=path")
    ap.add_argument("--games", type=int, default=10)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--workdir", default="/tmp/cc_sim_test")
    ap.add_argument("--keep-frames", action="store_true")
    args = ap.parse_args()
    na, pa = args.a.split("=", 1)
    nb, pb = args.b.split("=", 1)
    res = play_matchup([{"name": na, "path": pa}, {"name": nb, "path": pb}],
                       args.games, args.seed, args.workdir, keep_frames=args.keep_frames)
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    _cli()
