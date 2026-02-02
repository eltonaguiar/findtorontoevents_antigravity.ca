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

  To use REAL MySQL (not mock): set FAVCREATORS_API_PROXY to your live site so /fc/api/
  is proxied to the live PHP (which reads from the real database).
  Example: FAVCREATORS_API_PROXY=https://findtorontoevents.ca python tools/serve_local.py
  The live site must have working MySQL (db_config.php / MYSQL_* env on server).
"""
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, unquote
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import os
import json
from pathlib import Path

PORT = int(os.environ.get("PORT", "5173"))  # Main site at http://localhost:PORT/ ; FavCreators at /fc/

# When set, proxy /fc/api/ and /favcreators/api/ to this host so the app uses REAL MySQL (live PHP).
# Example: FAVCREATORS_API_PROXY=https://findtorontoevents.ca
API_PROXY = os.environ.get("FAVCREATORS_API_PROXY", "").strip().rstrip("/")

# Favcreators built app: absolute path so it works regardless of cwd
_SCRIPT_DIR = Path(__file__).resolve().parent
_WORKSPACE_ROOT = _SCRIPT_DIR.parent
FAVCREATORS_DOCS_ROOT = _WORKSPACE_ROOT / "favcreators" / "docs"
FAVCREATORS_CREATORS_JSON = _WORKSPACE_ROOT / "data" / "favcreators_creators.json"

def _send_json(handler, obj):
    out = json.dumps(obj).encode("utf-8")
    handler.send_response(200)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(out)))
    handler.end_headers()
    handler.wfile.write(out)


def _proxy_to_remote(handler, method, path, query_string, body=None):
    """Proxy request to API_PROXY so the app gets real MySQL data from live PHP."""
    url = f"{API_PROXY}{path}"
    if query_string:
        url += "?" + query_string
    try:
        req_headers = {"User-Agent": "findtorontoevents-serve_local/1"}
        if body and method == "POST":
            req_headers["Content-Type"] = "application/json"
        req = Request(url, data=body.encode("utf-8") if body else None, method=method, headers=req_headers)
        with urlopen(req, timeout=15) as resp:
            handler.send_response(resp.status)
            ct = resp.headers.get("Content-Type")
            if ct:
                handler.send_header("Content-Type", ct)
            data = resp.read()
            handler.send_header("Content-Length", str(len(data)))
            handler.end_headers()
            handler.wfile.write(data)
    except HTTPError as e:
        handler.send_response(e.code)
        handler.send_header("Content-Type", "application/json")
        body_err = json.dumps({"error": str(e)}).encode("utf-8")
        handler.send_header("Content-Length", str(len(body_err)))
        handler.end_headers()
        handler.wfile.write(body_err)
    except (URLError, OSError) as e:
        handler.send_response(502)
        handler.send_header("Content-Type", "application/json")
        body_err = json.dumps({"error": f"Proxy failed: {e}"}).encode("utf-8")
        handler.send_header("Content-Length", str(len(body_err)))
        handler.end_headers()
        handler.wfile.write(body_err)

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
        parsed = urlparse(self.path)
        raw = (parsed.path or "/").strip()
        path = (unquote(raw).rstrip("/") or "/")
        query_string = parsed.query or ""

        def consume_body():
            try:
                length = int(self.headers.get("Content-Length", 0))
                if length:
                    return self.rfile.read(length).decode("utf-8", "replace")
            except Exception:
                pass
            return None

        # Proxy to live site so app uses REAL MySQL (not mock)
        if API_PROXY and (path.startswith("/fc/api/") or path.startswith("/favcreators/api/")):
            body = consume_body() if "Content-Length" in self.headers else None
            if body is None and self.headers.get("Content-Length"):
                try:
                    body = self.rfile.read(int(self.headers.get("Content-Length", 0))).decode("utf-8", "replace")
                except Exception:
                    body = None
            _proxy_to_remote(self, "POST", path, query_string, body=body)
            return

        def consume_body_only():
            try:
                length = int(self.headers.get("Content-Length", 0))
                if length:
                    self.rfile.read(length)
            except Exception:
                pass

        # Mock save_note.php (no PHP locally) – return JSON so "Save" note doesn't throw
        if "save_note" in path or path.endswith("save_note.php"):
            consume_body_only()
            _send_json(self, {"status": "success", "message": "Note saved (local mock)"})
            return

        # Mock save_creators.php – persist creators per user_id to JSON file (admin=0, guests see it)
        if "save_creators" in path or path.endswith("save_creators.php"):
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length).decode("utf-8", "replace") if length else "{}"
                data = json.loads(body) if body else {}
                user_id = int(data.get("user_id", 0))
                creators = data.get("creators", [])
                # Load existing, update one user's list, write back
                all_data = {}
                if FAVCREATORS_CREATORS_JSON.is_file():
                    try:
                        all_data = json.loads(FAVCREATORS_CREATORS_JSON.read_text(encoding="utf-8"))
                    except (json.JSONDecodeError, OSError):
                        pass
                all_data[str(user_id)] = creators
                FAVCREATORS_CREATORS_JSON.parent.mkdir(parents=True, exist_ok=True)
                FAVCREATORS_CREATORS_JSON.write_text(json.dumps(all_data, indent=2), encoding="utf-8")
            except Exception:
                pass
            _send_json(self, {"status": "success"})
            return

        # Mock creators/bulk – admin bulk update (no backend locally)
        if "creators/bulk" in path or path.rstrip("/").endswith("creators/bulk"):
            consume_body_only()
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
        query_string = parsed.query or ""

        # Proxy to live site so app retrieves from REAL MySQL (not mock)
        if API_PROXY and (path.startswith("/fc/api/") or path.startswith("/favcreators/api/")):
            _proxy_to_remote(self, "GET", path, query_string)
            return

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
            if "status.php" in path:
                _send_json(self, {
                    "ok": True,
                    "db": "connected",
                    "read_ok": True,
                    "notes_count": 1,
                    "starfireara_note": "Guest default note for Starfireara (local mock)",
                    "get_notes_sample": {"6": "Guest default note for Starfireara (local mock)"},
                })
                return
            if "get_me.php" in path:
                _send_json(self, {"user": {"id": 0, "email": "admin", "role": "admin", "provider": "admin", "display_name": "Admin"}})
                return
            if "get_my_creators.php" in path:
                qs = parse_qs(parsed.query)
                user_id = int(qs.get("user_id", [0])[0]) if qs else 0
                creators = []
                if FAVCREATORS_CREATORS_JSON.is_file():
                    try:
                        all_data = json.loads(FAVCREATORS_CREATORS_JSON.read_text(encoding="utf-8"))
                        creators = all_data.get(str(user_id), [])
                    except (json.JSONDecodeError, OSError):
                        pass
                _send_json(self, {"creators": creators})
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
    if API_PROXY:
        print(f"  API PROXY: /fc/api/ -> {API_PROXY} (REAL MySQL from live site)")
    else:
        print(f"  API mocks (notes, list, login): /fc/api/ get_me, get_notes, get_my_creators, save_note, save_creators, creators/bulk")
    print(f"  Main page (index.html):  http://localhost:{PORT}/")
    print(f"  FavCreators:             http://localhost:{PORT}/fc/  or  http://localhost:{PORT}/fc/#/guest")
    print(f"  Serving from:            {workspace_root}")
    if not API_PROXY:
        print(f"  To use REAL MySQL: set FAVCREATORS_API_PROXY=https://findtorontoevents.ca then restart.")
    print(f"  Verify API: open http://localhost:{PORT}/fc/api/get_notes.php?user_id=0 — you should see JSON.")
    print("Press Ctrl+C to stop.")
    print()

    try:
        server = HTTPServer(('127.0.0.1', PORT), CORSRequestHandler)
    except OSError as e:
        if e.errno == 98 or "Address already in use" in str(e) or "WinError 10048" in str(e):
            print(f"ERROR: Port {PORT} is already in use. Another server is running on {PORT}.")
            print("  Stop that server (e.g. npx serve, Vite, or another Python process), then run this script again.")
            print(f"  Or use a different port: PORT=5174 python tools/serve_local.py")
            raise SystemExit(1) from e
        raise

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.server_close()

if __name__ == "__main__":
    main()