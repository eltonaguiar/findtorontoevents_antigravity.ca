#!/usr/bin/env python3
"""Fail if the live /audit page still shows claims this branch removed.

Run after audit-dashboard.yml has deployed main. Exit 0 when the live HTML
matches the honesty invariants. Exit 1 when it still has the old claims.
"""
from __future__ import annotations

import sys
import urllib.request

URL = "https://findtorontoevents.ca/audit/"
FORBIDDEN = (
    "5/5 checks pass",
    "PF2.6",
    "PF2.4",
    "DB health GREEN: ghost rows 0",
)
REQUIRED = (
    "ghost-row check fails",
    "Prediction markets stay shadow",
)


def main() -> int:
    req = urllib.request.Request(URL, headers={"User-Agent": "audit-honesty-check"})
    html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
    bad = [s for s in FORBIDDEN if s in html]
    missing = [s for s in REQUIRED if s not in html]
    if bad or missing:
        print("LIVE_STALE", URL)
        for s in bad:
            print("forbidden", s)
        for s in missing:
            print("missing", s)
        return 1
    print("LIVE_OK", URL)
    return 0


if __name__ == "__main__":
    sys.exit(main())
