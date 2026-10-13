#!/usr/bin/env python3
"""Local live dashboard server — free data, no keys.

  .venv/bin/python app/server.py          # → http://127.0.0.1:8765

Endpoints:
  GET /                 → app/index.html (live mode auto-enabled)
  GET /data.js          → baked research snapshot
  GET /api/today        → live daily snapshot (price, flows, bias, who-is-winning)
  GET /api/history      → last N enriched daily rows (?days=90)
  GET /api/refresh      → force refetch (ignore cache)
  GET /api/cache        → cache ages
"""
from __future__ import annotations

import contextlib
import json
import os
import sys
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from app import live_fetch  # noqa: E402

APP_DIR = os.path.join(ROOT, "app")
PORT = int(os.environ.get("KFLOW_DASH_PORT", "8765"))
_HOST = "127.0.0.1"

# simple in-process lock so concurrent /api/today don't stampede fetches
_fetch_lock = {"busy": False, "last_ok": 0.0, "last_payload": None, "last_err": None}


class Handler(BaseHTTPRequestHandler):
    server_version = "BTCResearchDash/1.0"

    def log_message(self, fmt, *args):  # quieter logs
        sys.stderr.write(f"{self.address_string()} - {fmt % args}\n")

    # ---- helpers
    def _json(self, obj, status=200):
        body = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _file(self, path, ctype):
        if not os.path.isfile(path):
            self.send_error(404, "not found")
            return
        with open(path, "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _today(self, force=False):
        now = time.time()
        # reuse fresh in-process payload if < 30s old (unless force)
        if (not force and _fetch_lock["last_payload"]
                and now - _fetch_lock["last_ok"] < 30):
            self._json(_fetch_lock["last_payload"])
            return
        if _fetch_lock["busy"]:
            # another request is fetching — return stale if we have it, else wait briefly
            if _fetch_lock["last_payload"]:
                payload = dict(_fetch_lock["last_payload"])
                payload["note"] = "refreshing in background — showing recent snapshot"
                self._json(payload)
                return
            time.sleep(0.5)
        _fetch_lock["busy"] = True
        try:
            if force:
                for name in ("daily", "hourly", "funding", "premium", "oi",
                             "oi_hist", "taker_ratio", "global_ls", "top_ls"):
                    live_fetch.cache_set(name, live_fetch.cache_get(name, 10**9) or [])
                # simpler: just bypass TTL by clearing timestamps via re-fetch path
            snap = live_fetch.build_snapshot()
            _fetch_lock["last_payload"] = snap
            _fetch_lock["last_ok"] = time.time()
            _fetch_lock["last_err"] = None
            self._json(snap)
        except Exception as e:  # noqa: BLE001
            _fetch_lock["last_err"] = str(e)
            if _fetch_lock["last_payload"]:
                payload = dict(_fetch_lock["last_payload"])
                payload["note"] = f"live refresh failed ({e}) — showing last good snapshot"
                payload["stale"] = True
                self._json(payload)
            else:
                self._json({"error": str(e), "trace": traceback.format_exc()[-800:]}, status=502)
        finally:
            _fetch_lock["busy"] = False

    # ---- routes
    def do_GET(self):  # noqa: N802
        try:
            u = urlparse(self.path)
            path = u.path
            qs = parse_qs(u.query)

            if path in ("/", "/index.html"):
                self._file(os.path.join(APP_DIR, "index.html"),
                           "text/html; charset=utf-8")
            elif path == "/data.js":
                self._file(os.path.join(APP_DIR, "data.js"),
                           "application/javascript; charset=utf-8")
            elif path == "/api/today":
                force = qs.get("force", ["0"])[0] in ("1", "true", "yes")
                self._today(force=force)
            elif path == "/api/history":
                days = int(qs.get("days", ["90"])[0])
                days = max(7, min(days, 400))
                rows = live_fetch.history_panel(days)
                self._json({"days": days, "rows": rows})
            elif path == "/api/cache":
                names = ["daily", "hourly", "funding", "premium", "oi", "oi_hist",
                         "taker_ratio", "global_ls", "top_ls", "etf", "cot"]
                self._json({n: live_fetch.cache_meta(n) for n in names})
            elif path == "/api/refresh":
                self._today(force=True)
            else:
                # static fallback inside app/
                safe = os.path.normpath(path).lstrip("/")
                full = os.path.join(APP_DIR, safe)
                if full.startswith(APP_DIR) and os.path.isfile(full):
                    ctype = "text/plain"
                    if full.endswith(".js"):
                        ctype = "application/javascript"
                    elif full.endswith(".css"):
                        ctype = "text/css"
                    elif full.endswith(".html"):
                        ctype = "text/html; charset=utf-8"
                    self._file(full, ctype)
                else:
                    self.send_error(404, "not found")
        except BrokenPipeError:
            pass
        except Exception:  # noqa: BLE001
            traceback.print_exc()
            with contextlib.suppress(Exception):
                self._json({"error": "internal", "trace": traceback.format_exc()[-800:]}, 500)


def main():
    # pre-warm cache in background so first page load is fast
    import threading
    def warm():
        try:
            live_fetch.build_snapshot()
            print("[warm] snapshot ready", flush=True)
        except Exception as e:  # noqa: BLE001
            print("[warm] failed:", e, flush=True)
    threading.Thread(target=warm, daemon=True).start()

    # allow immediate rebind after Ctrl-C / kill (avoids "Address already in use")
    ThreadingHTTPServer.allow_reuse_address = True

    port = PORT
    httpd = None
    for attempt in range(5):
        try:
            httpd = ThreadingHTTPServer((_HOST, port), Handler)
            break
        except OSError as e:
            if e.errno in (48, 98):  # Address already in use
                if attempt == 0:
                    print(f"Port {port} is busy — a previous server may still be running.")
                    print(f"  Kill it:  lsof -ti :{port} | xargs kill -9")
                    print("  Or try the next port automatically…", flush=True)
                port += 1
            else:
                raise
    if httpd is None:
        print(f"Could not bind any port from {PORT}–{port}. Kill old servers first.")
        sys.exit(1)

    print(f"BTC Smart-Money live dashboard → http://{_HOST}:{port}")
    print("Ctrl-C to stop  (do NOT use Ctrl-Z — that suspends and keeps the port)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")
        httpd.server_close()


if __name__ == "__main__":
    main()
