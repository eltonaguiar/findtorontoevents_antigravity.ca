#!/usr/bin/env python3
"""verify_live_claim.py — refuse to call a feature "live" until it is on origin/main.

Why this exists (2026-11-22): the forward paper book was built, pushed, and
reported as deployed. origin/main had no tools/forward_book.py, so the workflow
step could never run and two URLs 404'd. The scheduler was green the whole time —
it was running main's older code. Pushed is not merged; merged is not deployed.

Two claims, two checks:

  --path P   P exists on the remote ref (default origin/main) — the tree the
             workflow actually checks out, not the working copy
  --url U    U answers HTTP 200, and contains --expect text if given

Exit 0 = every claim supported. Exit 1 = at least one is not, with a line per
claim saying which and why, so "it's live" cannot be asserted on a branch-only file.

Usage:
  python3 tools/verify_live_claim.py \
      --path tools/forward_book.py \
      --url https://findtorontoevents.ca/audit3/forward_book.json \
      --expect forward_book
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import urllib.error
import urllib.request

DEFAULT_REF = "origin/main"


def path_on_ref(path: str, ref: str = DEFAULT_REF, cwd: str | None = None) -> tuple[bool, str]:
    """(ok, detail) for `path` existing on `ref` in the repo at cwd."""
    try:
        r = subprocess.run(["git", "cat-file", "-e", f"{ref}:{path}"],
                           cwd=cwd, capture_output=True, text=True)
    except FileNotFoundError:
        return False, "git not available"
    if r.returncode == 0:
        return True, f"present on {ref}"
    return False, (f"ABSENT on {ref} — exists only on a branch or in the working "
                   f"tree, so no workflow and no deploy can be using it")


def url_ok(url: str, expect: str | None = None, timeout: int = 25) -> tuple[bool, str]:
    req = urllib.request.Request(url, headers={"User-Agent": "verify-live-claim/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            code, body = r.getcode(), r.read(300_000).decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return False, f"HTTP {exc.code}"
    except Exception as exc:  # noqa: BLE001 - any transport failure is a failed claim
        return False, f"{type(exc).__name__}: {exc}"
    if code != 200:
        return False, f"HTTP {code}"
    if expect and expect not in body:
        return False, f"HTTP 200 but the body does not contain {expect!r}"
    return True, f"HTTP 200{' and contains ' + repr(expect) if expect else ''}"


def verdict(rows: list[tuple[bool, str, str]]) -> int:
    """Print every claim, then refuse loudly if any is unsupported."""
    for ok, claim, detail in rows:
        print(f"{'OK  ' if ok else 'FAIL'}  {claim}  --  {detail}")
    bad = [r for r in rows if not r[0]]
    if bad:
        print(f"\nREFUSING: {len(bad)} of {len(rows)} claim(s) are unsupported. "
              f"This feature is NOT live — do not report it as shipped.",
              file=sys.stderr)
        return 1
    print(f"\nAll {len(rows)} claim(s) supported.")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--path", action="append", default=[], help="file that must be on the ref")
    ap.add_argument("--url", action="append", default=[], help="URL that must answer 200")
    ap.add_argument("--expect", default=None, help="substring the URL body must contain")
    ap.add_argument("--ref", default=DEFAULT_REF)
    ap.add_argument("--no-fetch", action="store_true", help="skip git fetch before checking")
    a = ap.parse_args(argv)

    if not a.path and not a.url:
        ap.error("give at least one --path or --url claim to verify")

    if not a.no_fetch:
        remote, _, branch = a.ref.partition("/")
        subprocess.run(["git", "fetch", remote, branch or "main"], capture_output=True)

    rows: list[tuple[bool, str, str]] = []
    for p in a.path:
        ok, detail = path_on_ref(p, a.ref)
        rows.append((ok, f"path {p}", detail))
    for u in a.url:
        ok, detail = url_ok(u, a.expect)
        rows.append((ok, f"url  {u}", detail))
    return verdict(rows)


if __name__ == "__main__":
    sys.exit(main())
