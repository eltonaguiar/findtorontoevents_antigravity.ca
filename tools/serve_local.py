#!/usr/bin/env python3
"""
Local HTTP server for testing events loading.

IMPORTANT: Use THIS script for local testing. Do NOT use `python -m http.server`.

Why: The live site serves JS chunks via js-proxy-v2.php (PHP). Python cannot run PHP,
so a plain http.server would return PHP source code for chunk URLs → SyntaxError →
React never loads → events never load. This script MIMICS the proxy: requests to
/js-proxy-v2.php?file=next/_next/static/chunks/XXX.js are served with the actual
JS/CSS file from disk.

  python tools/serve_local.py   # correct – proxy mimic active
  python -m http.server 9000   # wrong – returns PHP source, site broken
"""
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, unquote
import os
import json
from pathlib import Path

PORT = 5173  # Main site at http://localhost:5173/ ; FavCreators at http://localhost:5173/fc/

# Favcreators built app: absolute path so it works regardless of cwd
_SCRIPT_DIR = Path(__file__).resolve().parent
_WORKSPACE_ROOT = _SCRIPT_DIR.parent
FAVCREATORS_DOCS_ROOT = _WORKSPACE_ROOT / "favcreators" / "docs"

def _send_json(handler, obj):
    out = json.dumps(obj).encode("utf-8")
    handler.send_response(200)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(out)))
    handler.end_headers()
    handler.wfile.write(out)

class CORSRequestHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        return super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def do_POST(self):
        raw = (self.path.split("?")[0] if "?" in self.path else self.path).strip()
        path = (unquote(raw).rstrip("/") or "/")

        def consume_body():
            try:
                length = int(self.headers.get("Content-Length", 0))
                if length:
                    self.rfile.read(length)
            except Exception:
                pass

        # Mock save_note.php (no PHP locally) – return JSON so "Save" note doesn't throw
        if "save_note" in path or path.endswith("save_note.php"):
            consume_body()
            _send_json(self, {"status": "success", "message": "Note saved (local mock)"})
            return

        # Mock save_creators.php – admin/guest list persistence (no MySQL locally)
        if "save_creators" in path or path.endswith("save_creators.php"):
            consume_body()
            _send_json(self, {"status": "success"})
            return

        # Mock creators/bulk – admin bulk update (no backend locally)
        if "creators/bulk" in path or path.rstrip("/").endswith("creators/bulk"):
            consume_body()
            _send_json(self, {"status": "success"})
            return

        # Handle login.php (same path as live PHP)
        if path not in ("/favcreators/api/login.php", "/fc/api/login.php") and not path.endswith("api/login.php"):
            self.send_response(404)
            self.end_headers()
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8", "replace") if length else "{}"
            try:
                data = json.loads(body) if body else {}
            except json.JSONDecodeError:
                data = {}
            if data.get("email") == "admin" and data.get("password") == "admin":
                out = json.dumps({
                    "user": {
                        "id": 0,
                        "email": "admin",
                        "role": "admin",
                        "provider": "admin",
                        "display_name": "Admin",
                    }
                }).encode("utf-8")
            else:
                out = json.dumps({"error": "Invalid credentials"}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(out)))
            self.end_headers()
            self.wfile.write(out)
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(str(e).encode("utf-8"))

    def do_GET(self):
        parsed = urlparse(self.path)
        raw_path = parsed.path
        path = (unquote(raw_path).rstrip("/") or "/")

        # Handle get_notes.php first (any path containing it) so Starfireara note is retrievable in tests
        if "get_notes.php" in path:
            qs = parse_qs(parsed.query)
            user_id = int(qs.get("user_id", [0])[0]) if qs else 0
            if user_id == 0:
                _send_json(self, {"6": "Guest default note for Starfireara (local mock)"})
            else:
                _send_json(self, {})
            return

        # Intercept other API paths so we never serve PHP as static files
        is_favcreators_api = path.startswith("/fc/api/") or path.startswith("/favcreators/api/")
        if is_favcreators_api and (path.endswith(".php") or "creators/" in path):
            if "get_me.php" in path:
                _send_json(self, {"user": {"id": 0, "email": "admin", "role": "admin", "provider": "admin", "display_name": "Admin"}})
                return
            if "get_my_creators.php" in path:
                qs = parse_qs(parsed.query)
                # Return empty list so app can merge with INITIAL_DATA; or could read from a local file
                _send_json(self, {"creators": []})
                return
            if "login.php" in path:
                _send_json(self, {"error": "Use POST to login"})
                return

        # Root only: serve main site index.html (Toronto Events). Do not match /fc or /favcreators.
        if (raw_path == "/" or raw_path == "" or raw_path == "/index.html") and not raw_path.startswith("/fc") and not raw_path.startswith("/favcreators"):
            index_html = (_WORKSPACE_ROOT / "index.html").resolve()
            if index_html.is_file() and str(index_html).startswith(str(_WORKSPACE_ROOT.resolve())):
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(index_html.read_bytes())
                return

        # FavCreators (built): serve from favcreators/docs at /fc/ and /favcreators/ for local
        docs_index = FAVCREATORS_DOCS_ROOT / "index.html"
        for prefix in ("/fc", "/favcreators"):
            if raw_path == prefix or raw_path == prefix + "/" or raw_path.startswith(prefix + "/"):
                if raw_path == prefix or raw_path == prefix + "/":
                    if docs_index.is_file():
                        self.send_response(200)
                        self.send_header("Content-Type", "text/html; charset=utf-8")
                        self.end_headers()
                        self.wfile.write(docs_index.read_bytes())
                        return
                else:
                    # /fc/xxx or /favcreators/xxx → serve from docs/xxx (except api/* – handled above)
                    sub = raw_path[len(prefix + "/"):].lstrip("/")
                if sub.startswith("api/"):
                    # API paths are mocked above; do not serve PHP files
                    pass
                elif ".." not in sub:
                    try:
                        local = (FAVCREATORS_DOCS_ROOT / sub.replace("/", os.sep)).resolve()
                        local.relative_to(FAVCREATORS_DOCS_ROOT.resolve())
                    except (ValueError, OSError):
                        pass
                    else:
                        if local.is_file():
                            suf = sub[sub.rfind("."):].lower() if "." in sub else ""
                            ct = {
                                ".js": "application/javascript; charset=utf-8",
                                ".css": "text/css; charset=utf-8",
                                ".svg": "image/svg+xml",
                                ".ico": "image/x-icon",
                                ".json": "application/json",
                                ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                                ".png": "image/png", ".webp": "image/webp",
                            }.get(suf, "application/octet-stream")
                            self.send_response(200)
                            self.send_header("Content-Type", ct)
                            self.end_headers()
                            self.wfile.write(local.read_bytes())
                            return
                        if local.is_dir() and (local / "index.html").is_file():
                            self.send_response(200)
                            self.send_header("Content-Type", "text/html; charset=utf-8")
                            self.end_headers()
                            self.wfile.write((local / "index.html").read_bytes())
                            return
                # fallback: serve docs index (e.g. SPA route)
                if docs_index.is_file():
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(docs_index.read_bytes())
                    return

        if parsed.path == '/js-proxy-v2.php' and parsed.query:
            qs = parse_qs(parsed.query)
            file_param = qs.get('file', [None])[0]
            if file_param and '..' not in file_param:
                # file_param is e.g. next/_next/static/chunks/a2ac3a6616d60872.js
                local_path = Path(os.getcwd()) / file_param.replace('/', os.sep)
                if local_path.is_file():
                    suffix = local_path.suffix.lower()
                    if suffix == '.js':
                        self.send_response(200)
                        self.send_header('Content-Type', 'application/javascript; charset=utf-8')
                        self.end_headers()
                        self.wfile.write(local_path.read_bytes())
                        return
                    if suffix == '.css':
                        self.send_response(200)
                        self.send_header('Content-Type', 'text/css; charset=utf-8')
                        self.end_headers()
                        self.wfile.write(local_path.read_bytes())
                        return

        # /next/_next/ static assets: set correct MIME (avoid wrong guess e.g. font/woff2 for .js)
        if raw_path.startswith("/next/_next/"):
            local_path = Path(os.getcwd()) / raw_path.lstrip("/").replace("/", os.sep)
            if local_path.is_file():
                suffix = local_path.suffix.lower()
                ct = None
                if suffix == ".js":
                    ct = "application/javascript; charset=utf-8"
                elif suffix == ".css":
                    ct = "text/css; charset=utf-8"
                elif suffix == ".json":
                    ct = "application/json; charset=utf-8"
                if ct:
                    self.send_response(200)
                    self.send_header("Content-Type", ct)
                    self.end_headers()
                    self.wfile.write(local_path.read_bytes())
                    return

        # Never let default handler serve /favcreators (it would serve dev index.html with /src/main.tsx)
        if raw_path == "/favcreators" or raw_path == "/favcreators/" or raw_path.startswith("/favcreators/"):
            if docs_index.is_file():
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(docs_index.read_bytes())
                return

        return super().do_GET()

def main():
    workspace_root = Path(__file__).parent.parent
    os.chdir(workspace_root)

    print("=" * 60)
    print("Local server: main site at root, FavCreators at /fc/")
    print("Do NOT use 'python -m http.server' – it returns PHP source.")
    print("=" * 60)
    print(f"  Main page (index.html):  http://localhost:{PORT}/")
    print(f"  FavCreators:            http://localhost:{PORT}/fc/  or  http://localhost:{PORT}/fc/#/guest")
    print(f"  Serving from:           {workspace_root}")
    print("Press Ctrl+C to stop.")
    print()

    server = HTTPServer(('127.0.0.1', PORT), CORSRequestHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.server_close()

if __name__ == "__main__":
    main()