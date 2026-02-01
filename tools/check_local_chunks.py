"""
Apply chunk checks against a local or remote base URL.
Verifies that JS chunks return real JavaScript (not HTML) to avoid
"Uncaught SyntaxError: Unexpected token '('" or "Unexpected token '<'".
"""
import urllib.request
import sys

# Chunks referenced in index.html (same list as check_js_files.py)
CHUNKS = [
    "628f1cf8c6948755.js",
    "806bdb8e4a6a9b95.js",
    "43a0077a15b1a098.js",
    "dde2c8e6322d1671.js",
    "turbopack-03e217c852f3e99c.js",
    "a2ac3a6616d60872.js",
    "ff1a16fafef87110.js",
    "7c4eddd014120b50.js",
    "f1a9dd578dc871d3.js",
    "afe53b3593ec888c.js",
    "1bbf7aa8dcc742fe.js",
]

CHUNK_PATH = "/next/_next/static/chunks/"


def check_url(base_url: str, path: str, expect_js: bool) -> tuple[bool, str]:
    """Fetch URL; return (ok, message). expect_js=True means we expect JavaScript (for chunks)."""
    url = base_url.rstrip("/") + path
    try:
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; rv:109.0) Gecko/20100101 Firefox/115.0")
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read().decode("utf-8", errors="replace")
            content_type = resp.headers.get("Content-Type", "")
            status = getattr(resp, "status", 200)
            if status != 200:
                return False, f"status {status}"
            if expect_js:
                if "text/html" in content_type or content.strip().startswith("<"):
                    return False, f"HTML response (first 120 chars): {content[:120]!r}"
                if content.startswith("(globalThis") or content.startswith("!function") or "(globalThis.TURBOPACK" in content[:80]:
                    return True, f"OK JavaScript ({len(content)} chars)"
                return False, f"unexpected content (starts with): {content[:80]!r}"
            # Index page: expect HTML
            if content.strip().startswith("<") and "html" in content[:200].lower():
                return True, f"OK HTML ({len(content)} chars)"
            return False, f"unexpected content (starts with): {content[:80]!r}"
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}: {e.reason}"
    except urllib.error.URLError as e:
        return False, f"URL error: {e.reason}"
    except Exception as e:
        return False, str(e)


def main():
    base = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:9000").rstrip("/")
    print(f"Base URL: {base}")
    print()

    # Check index page (expect HTML)
    ok, msg = check_url(base, "/", expect_js=False)
    if ok:
        print(f"[ / ] OK: {msg}")
    else:
        print(f"[ / ] FAIL: {msg}")
    print()

    # Check each chunk (focus on a2ac3a6616d60872.js first)
    focus = "a2ac3a6616d60872.js"
    ordered = [focus] if focus in CHUNKS else []
    ordered += [c for c in CHUNKS if c != focus]

    all_ok = True
    for js_file in ordered:
        path = CHUNK_PATH + js_file
        ok, msg = check_url(base, path, expect_js=True)
        if ok:
            print(f"[ {js_file} ] OK: {msg}")
        else:
            print(f"[ {js_file} ] FAIL: {msg}")
            all_ok = False
    print()
    if all_ok:
        print("All chunk checks passed. No SyntaxError from HTML responses expected.")
    else:
        print("Some chunks failed. Fix server/proxy so these URLs return JavaScript, not HTML.")
        sys.exit(1)


if __name__ == "__main__":
    main()
