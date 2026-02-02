#!/usr/bin/env python3
"""
Check whether the FavCreators API on port 5173 returns JSON (serve_local) or not.
Run from project root. If you see "OK: API returns JSON" then serve_local is running.
If you see "NOT OK" then another server is on 5173 — stop it and run: python tools/serve_local.py
"""
import urllib.request
import sys

PORT = 5173
URL = f"http://127.0.0.1:{PORT}/fc/api/get_notes.php?user_id=0"

def main():
    try:
        with urllib.request.urlopen(URL, timeout=5) as r:
            body = r.read().decode("utf-8", "replace")
    except Exception as e:
        print(f"NOT OK: Could not reach {URL}")
        print(f"  Error: {e}")
        print("  -> Start the API server: python tools/serve_local.py (from project root)")
        sys.exit(1)

    if body.strip().startswith("<?php") or body.strip().startswith("<"):
        print("NOT OK: Server on port 5173 returned PHP/HTML, not JSON.")
        print("  -> Another server is on 5173 (e.g. npx serve, Vite). Stop it.")
        print("  -> Then run: python tools/serve_local.py (from project root)")
        sys.exit(1)

    try:
        import json
        data = json.loads(body)
        if isinstance(data, dict) and "6" in data:
            print("OK: API returns JSON. Starfireara note entry present.")
            print(f"  body['6'] = {data['6'][:50]}...")
        else:
            print("OK: API returns JSON (serve_local or compatible backend).")
    except json.JSONDecodeError:
        print("NOT OK: Response is not valid JSON.")
        print("  -> Run: python tools/serve_local.py (from project root)")
        sys.exit(1)

if __name__ == "__main__":
    main()
