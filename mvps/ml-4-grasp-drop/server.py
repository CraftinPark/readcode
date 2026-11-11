"""Case server for ml-4-grasp-drop: runs the hidden engine and talks JSON on localhost.

    C:\\Python314\\python server.py          # 127.0.0.1:8791 (or pass a port)

The player's folder holds only README.md and case.py, which calls this server, so the
engine never sits in their folder. Each session's actions and report go to .sessions/.
Same split as cases/server.py on danny-v1.
"""
import json
import secrets
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import engine  # noqa: E402

SESSIONS_DIR = ROOT / ".sessions"
_sessions = {}


def save(sid):
    s = _sessions[sid]
    SESSIONS_DIR.mkdir(exist_ok=True)
    (SESSIONS_DIR / f"{sid}.json").write_text(json.dumps({
        "session": sid, "minutes": s.minutes, "clock": s.clock(),
        "actions": [{"minute": m, "action": a, "args": g} for m, a, g in s.log],
        "report": s.done}, indent=2), encoding="utf-8")


def handle(path, body):
    if path == "/start":
        sid = secrets.token_hex(4)
        _sessions[sid] = engine.Session(seed=body.get("seed", 1))
        save(sid)
        return {"session": sid, "intro": engine.intro(), "status": _sessions[sid].status()}
    sid = body.get("session")
    if sid not in _sessions:
        raise KeyError("unknown session (the server was restarted?). Run: python case.py start")
    s = _sessions[sid]
    if path == "/actions":
        return {"actions": {k: {"minutes": c, "what": w} for k, (c, w) in engine.ACTIONS.items()}}
    if path == "/causes":
        return {"causes": engine.CAUSES, "segments": engine.SEGMENTS}
    if path == "/status":
        return {"status": s.status()}
    if path == "/act":
        out = s.act(body["action"], body.get("args", []))
        save(sid)
        return {"output": out}
    if path == "/submit":
        report = s.submit(body.get("answer", {}))
        save(sid)
        return {"report": report}
    raise KeyError(f"unknown endpoint {path}")


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            reply, code = handle(self.path, body), 200
        except KeyError as e:
            reply, code = {"error": str(e).strip("'\"")}, 400
        data = json.dumps(reply).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


def main(port=8791):
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"ml-4-grasp-drop case server on http://127.0.0.1:{port}  (Ctrl+C to stop)", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 8791)
