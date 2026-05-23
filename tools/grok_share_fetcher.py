#!/usr/bin/env python3
"""Fetch grok.com/share/<id> conversations via Playwright (auth-gated content).

Why this exists: grok.com share URLs (bGVnYWN5LWNvcHk_*) are 403 to anonymous
clients and the conversation body is client-rendered via authenticated API.
WebFetch + urllib + grok CLI all fail to retrieve message bodies.

Usage (one-time interactive login):

    pip install playwright && python -m playwright install chromium
    python tools/grok_share_fetcher.py login

  → A Chromium window opens at https://grok.com/. Sign in normally.
  → Press Enter in this terminal once you're signed in.
  → Session is persisted at .grok_session/ (gitignored).

Usage (headless fetch, any future share):

    python tools/grok_share_fetcher.py fetch <share_url> [-o out.md]

  → Loads share URL with persisted auth, waits for messages to render,
    extracts conversation, dumps as markdown to stdout or -o file.

Notes:
- Stores session at .grok_session/ — add to .gitignore.
- One re-login required if grok.com rotates session tokens.
- Refuses to print any cookie / token value.
"""
from __future__ import annotations
import argparse
import json
import sys
import time
from pathlib import Path

SESSION_DIR = Path(__file__).parent.parent / ".grok_session"


def _ensure_playwright():
    try:
        from playwright.sync_api import sync_playwright  # noqa
        return True
    except ImportError:
        print("ERROR: playwright not installed. Run:", file=sys.stderr)
        print("  pip install playwright && python -m playwright install chromium", file=sys.stderr)
        return False


def cmd_login() -> int:
    if not _ensure_playwright():
        return 1
    from playwright.sync_api import sync_playwright
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        ctx = pw.chromium.launch_persistent_context(
            user_data_dir=str(SESSION_DIR),
            headless=False,
            args=["--no-sandbox"],
        )
        page = ctx.new_page()
        page.goto("https://grok.com/", wait_until="domcontentloaded")
        print("\n[grok_share_fetcher] A Chromium window has opened.")
        print("[grok_share_fetcher] Sign in to grok.com in that window.")
        print("[grok_share_fetcher] Press Enter here once you're signed in...")
        try:
            input()
        except EOFError:
            pass
        ctx.close()
    print(f"[grok_share_fetcher] Session persisted at {SESSION_DIR}")
    return 0


def cmd_fetch(url: str, out: str | None) -> int:
    if not _ensure_playwright():
        return 1
    if not SESSION_DIR.exists():
        print(f"ERROR: no session at {SESSION_DIR}. Run `login` first.", file=sys.stderr)
        return 2
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        ctx = pw.chromium.launch_persistent_context(
            user_data_dir=str(SESSION_DIR),
            headless=True,
            args=["--no-sandbox"],
        )
        page = ctx.new_page()
        page.goto(url, wait_until="networkidle", timeout=60_000)
        # Give the React tree time to fully render conversation
        page.wait_for_timeout(3000)

        # Heuristic extraction: grok.com renders user/assistant turns in
        # role-tagged blocks. Pull text content of the main conversation pane.
        # If grok.com markup changes, update selectors here.
        body_md = page.evaluate("""() => {
            const sels = [
                'main',
                '[data-testid="conversation-turn"]',
                'article',
                '.conversation',
                'body',
            ];
            for (const s of sels) {
                const el = document.querySelector(s);
                if (el && el.innerText && el.innerText.length > 500) return el.innerText;
            }
            return document.body.innerText;
        }""")
        title = page.title()
        ctx.close()

    md = f"# {title}\n\n*Fetched via tools/grok_share_fetcher.py from {url}*\n\n---\n\n{body_md}\n"
    if out:
        Path(out).write_text(md, encoding="utf-8")
        print(f"[grok_share_fetcher] Wrote {len(md)} bytes to {out}")
    else:
        sys.stdout.write(md)
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("login")
    f = sub.add_parser("fetch")
    f.add_argument("url")
    f.add_argument("-o", "--out", default=None)
    args = p.parse_args()
    if args.cmd == "login":
        return cmd_login()
    if args.cmd == "fetch":
        return cmd_fetch(args.url, args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
