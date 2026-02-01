#!/usr/bin/env python3
"""
Verify Toronto events loading before declaring nav/index/chunk work done.

Run after any change to:
- index.html
- next/_next/static/chunks/a2ac3a6616d60872.js (or patch_nav_js.py)
- events.json paths

Checks:
1. Nav chunk parses (npx acorn) - SyntaxError here breaks React → no events.
2. Optional: events-loading Playwright test (requires serve_local.py on 9000).

Usage:
  python tools/verify_events_loading.py              # chunk syntax only
  python tools/verify_events_loading.py --playwright # chunk + Playwright (server must be running)
"""
import subprocess
import sys
import os

CHUNK = "next/_next/static/chunks/a2ac3a6616d60872.js"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def check_chunk_syntax():
    """Run acorn on nav chunk. Return True if parse OK."""
    path = os.path.join(ROOT, CHUNK)
    if not os.path.exists(path):
        print(f"FAIL: Chunk not found: {CHUNK}")
        return False
    try:
        # Use shell on Windows so npx is found in PATH
        cmd = f'npx acorn "{path}"' if os.name == "nt" else ["npx", "acorn", path]
        out = subprocess.run(
            cmd,
            cwd=ROOT,
            capture_output=True,
            timeout=15,
            shell=(os.name == "nt"),
        )
        stderr = (out.stderr or b"").decode("utf-8", "replace")
        stdout = (out.stdout or b"").decode("utf-8", "replace")
        if out.returncode != 0:
            err = (stderr or stdout or "acorn failed").encode("ascii", "replace").decode("ascii")
            print("FAIL: Nav chunk has JS syntax error (React will not load; no events):")
            print(err)
            return False
        print("OK: Nav chunk parses (acorn).")
        return True
    except Exception as e:
        msg = str(e).encode("ascii", "replace").decode("ascii")
        print(f"FAIL: Could not run acorn: {msg}")
        return False


def check_playwright():
    """Run events-loading.spec.ts. Return True if all pass."""
    spec = os.path.join(ROOT, "events-loading.spec.ts")
    if not os.path.exists(spec):
        print("SKIP: events-loading.spec.ts not found")
        return True
    try:
        out = subprocess.run(
            ["npx", "playwright", "test", "events-loading.spec.ts", "--reporter=line"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=60000,
        )
        if out.returncode != 0:
            print("FAIL: Events loading Playwright tests failed:")
            print(out.stdout or out.stderr or "")
            return False
        print("OK: Events loading tests passed.")
        return True
    except Exception as e:
        print(f"FAIL: Playwright run failed: {e}")
        return False


def main():
    os.chdir(ROOT)
    run_playwright = "--playwright" in sys.argv
    ok = check_chunk_syntax()
    if ok and run_playwright:
        ok = check_playwright()
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
