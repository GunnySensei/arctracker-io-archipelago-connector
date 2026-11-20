"""Tiny HTTP server for the in-game overlay page. Runs in a background thread; all client state is read and
changed on the asyncio loop via run_coroutine_threadsafe. Serves:
  GET  /            the overlay page
  GET  /state.json  current overlay state
  POST /action      {"kind": "done"|"spend"|"undo", "name": "..."}"""
import asyncio
import json
import pkgutil
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .. import data as D


def start(ctx, loop: asyncio.AbstractEventLoop, port: int, lan: bool):
    page = pkgutil.get_data(D.__name__.rsplit(".", 1)[0], "assets/overlay.html")

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):  # keep the client log clean
            pass

        def _send(self, code: int, body: bytes, ctype: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _on_loop(self, fn, *args):
            async def run():
                return fn(*args)
            return asyncio.run_coroutine_threadsafe(run(), loop).result(timeout=3)

        def do_GET(self):
            path = self.path.split("?", 1)[0]
            if path in ("/", "/overlay", "/overlay.html"):
                self._send(200, page, "text/html; charset=utf-8")
            elif path == "/state.json":
                import time
                from urllib.parse import parse_qs, urlparse
                since = parse_qs(urlparse(self.path).query).get("since", [None])[0]
                if since is not None:
                    deadline = time.monotonic() + 20
                    while str(getattr(ctx, "state_version", 0)) == since and time.monotonic() < deadline:
                        time.sleep(0.25)
                try:
                    state = self._on_loop(ctx.overlay_state)
                except Exception as e:  # noqa: BLE001
                    state = {"connected": False, "error": str(e)}
                self._send(200, json.dumps(state).encode(), "application/json")
            else:
                self._send(404, b"not found", "text/plain")

        def do_POST(self):
            if self.path.split("?", 1)[0] != "/action":
                self._send(404, b"not found", "text/plain")
                return
            try:
                length = min(int(self.headers.get("Content-Length") or 0), 4096)
                req = json.loads(self.rfile.read(length) or b"{}")
                ok = self._on_loop(ctx.overlay_action, str(req.get("kind", "")), str(req.get("name", "")))
            except Exception:  # noqa: BLE001
                ok = False
            self._send(200, json.dumps({"ok": bool(ok)}).encode(), "application/json")

    host = "0.0.0.0" if lan else "127.0.0.1"
    server = ThreadingHTTPServer((host, port), Handler)
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, name="arc overlay", daemon=True).start()
    return server
