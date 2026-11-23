#!/usr/bin/env python3
"""lint_no_overclaim.py — CI lint: fail if a doc asserts a retracted/overclaimed statement.

Greps edge_research docs for banned active phrasings:
  - "zero alpha" unless the same file contains a correction/withdrawal marker
  - "mutual fund beats" / "beats its own ETF" unless marked retracted/withdrawn
Exit 1 on a violation so the claim cannot silently reappear.
"""
import glob, re, sys

BANNED = [
    (re.compile(r"\bzero alpha\b", re.I), re.compile(r"withdraw|retract|correct|power statement|not.*prove", re.I)),
    (re.compile(r"mutual fund beats|beats its own etf", re.I), re.compile(r"retract|withdraw|withdrawn", re.I)),
]

def main():
    viol = []
    for f in glob.glob("docs/edge_research/*.md"):
        txt = open(f, encoding="utf-8", errors="ignore").read()
        for banned, exculpatory in BANNED:
            if banned.search(txt) and not exculpatory.search(txt):
                viol.append((f, banned.pattern))
    if viol:
        for f, p in viol:
            print(f"OVERCLAIM: {f} contains /{p}/ without a retraction/correction marker", file=sys.stderr)
        return 1
    print("OK: no unchecked overclaims in docs/edge_research")
    return 0

if __name__ == "__main__":
    sys.exit(main())
