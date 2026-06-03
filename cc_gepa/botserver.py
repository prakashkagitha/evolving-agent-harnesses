"""Lightweight BattleSnake bot HTTP server (stdlib only).

Protocol-identical to CodeClash's Flask `server.py` (endpoints: GET / -> info,
POST /start, POST /move, POST /end) but uses the stdlib ThreadingHTTPServer for
fast startup and binds to an OS-assigned free port (this is a shared, busy host,
so hard-coded ports collide). The bot's `main.py` (the evolved genotype/phenotype)
still defines info/start/move/end exactly as in the BattleSnake starter kit.

Usage:  python -m cc_gepa.botserver <bot_main.py> [--crashlog PATH]
On bind it prints a single line `LISTENING <port>` to stdout (the sim runner reads
this to learn the port), then serves until killed.

Robustness: a move() that raises is caught, logged to the crash log (one JSON line
per crash), and a safe fallback move is returned so a single buggy turn does not
desync the whole game. A persistently-crashing bot therefore plays near-randomly
and loses on its own merits, while we still get an explicit crash count for the
inner-GEPA feedback. move() MUST be a pure function of game_state (no cross-turn
mutable globals) because many games run concurrently against one server.
"""
import json
import os
import sys
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

_FALLBACK = {"move": "up"}


def _load_bot(path):
    ns = {"__name__": "_bot", "__file__": path}
    with open(path) as f:
        src = f.read()
    code = compile(src, path, "exec")
    exec(code, ns)  # noqa: S102 - trusted-in-this-PoC LLM bot code
    return ns


def main():
    argv = sys.argv[1:]
    bot_path = argv[0]
    crashlog = None
    if "--crashlog" in argv:
        crashlog = argv[argv.index("--crashlog") + 1]

    ns = _load_bot(bot_path)
    info_fn = ns.get("info", lambda: {"apiversion": "1"})
    start_fn = ns.get("start", lambda gs: None)
    move_fn = ns.get("move")
    end_fn = ns.get("end", lambda gs: None)
    if move_fn is None:
        sys.stderr.write("bot has no move()\n")
        sys.exit(2)

    crash_count = {"n": 0}

    def record_crash(kind, exc):
        crash_count["n"] += 1
        if crashlog:
            try:
                with open(crashlog, "a") as cf:
                    cf.write(json.dumps({
                        "t": time.time(), "kind": kind,
                        "err": f"{type(exc).__name__}: {exc}",
                        "tb": traceback.format_exc()[-1500:],
                    }) + "\n")
            except Exception:
                pass

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *a):
            pass

        def _send(self, obj, code=200):
            body = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _read_json(self):
            n = int(self.headers.get("Content-Length", 0) or 0)
            raw = self.rfile.read(n) if n else b"{}"
            try:
                return json.loads(raw or b"{}")
            except Exception:
                return {}

        def do_GET(self):
            try:
                self._send(info_fn())
            except Exception as e:
                record_crash("info", e)
                self._send({"apiversion": "1"})

        def do_POST(self):
            gs = self._read_json()
            if self.path.startswith("/move"):
                try:
                    out = move_fn(gs)
                    if not isinstance(out, dict) or "move" not in out:
                        raise ValueError(f"move() returned {out!r}")
                    self._send(out)
                except Exception as e:
                    record_crash("move", e)
                    self._send(dict(_FALLBACK))
            elif self.path.startswith("/start"):
                try:
                    start_fn(gs)
                except Exception as e:
                    record_crash("start", e)
                self._send({"ok": True})
            elif self.path.startswith("/end"):
                try:
                    end_fn(gs)
                except Exception as e:
                    record_crash("end", e)
                self._send({"ok": True})
            else:
                self._send({"ok": True})

    class Server(ThreadingHTTPServer):
        request_queue_size = 256  # large listen backlog: many concurrent games share one server
        allow_reuse_address = True
        daemon_threads = True

    httpd = Server(("0.0.0.0", 0), Handler)
    port = httpd.server_address[1]
    sys.stdout.write(f"LISTENING {port}\n")
    sys.stdout.flush()
    try:
        httpd.serve_forever(poll_interval=0.2)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
