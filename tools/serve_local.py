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
from urllib.parse import urlparse, parse_qs
import os
import json
from pathlib import Path

PORT = 9000

# Favcreators built app: absolute path so it works regardless of cwd
_SCRIPT_DIR = Path(__file__).resolve().parent
_WORKSPACE_ROOT = _SCRIPT_DIR.parent
FAVCREATORS_DOCS_ROOT = _WORKSPACE_ROOT / "favcreators" / "docs"

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
        # Handle login.php (same path as live PHP); Python 3 calls this for POST
        path = (self.path.split("?")[0] if "?" in self.path else self.path).rstrip("/") or "/"
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
        path = (raw_path.rstrip("/") or "/")

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
                    # /fc/xxx or /favcreators/xxx → serve from docs/xxx
                    sub = raw_path[len(prefix + "/"):].lstrip("/")
                if ".." not in sub:
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
    print("Local server with PROXY MIMIC (chunk URLs -> real JS/CSS)")
    print("Do NOT use 'python -m http.server' – it returns PHP source.")
    print("=" * 60)
    print(f"Starting server at http://127.0.0.1:{PORT} and http://localhost:{PORT}")
    print(f"Serving from: {workspace_root}")
    print(f"FavCreators (built): /favcreators/ and /favcreators/#/guest -> {FAVCREATORS_DOCS_ROOT}")
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