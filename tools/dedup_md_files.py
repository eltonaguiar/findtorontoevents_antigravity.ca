#!/usr/bin/env python3
"""
dedup_md_files.py — Content-dedup a list of files; pick the shortest path per dupe group.

Useful when the same .md exists across many `.claude/worktrees/agent-*/reports/...`
copies plus a canonical `reports/...`. Outputs the canonical (shortest-path) set so
reviewers don't read the same content N times.

Usage:
    # Auto-discover (default: scan repo + worktrees for .md under reports/)
    python3 tools/dedup_md_files.py --glob 'reports/**/*.md' --glob '.claude/worktrees/**/reports/**/*.md'

    # From explicit list (one path per line, also accepts Windows backslash paths — auto-normalized)
    python3 tools/dedup_md_files.py --from-file /tmp/paths.txt

    # JSON output (for piping to another tool)
    python3 tools/dedup_md_files.py --from-file /tmp/paths.txt --json

Output (text mode):
    CANONICAL (N unique of M total):
      reports/asset_class_90day_plan_BOND_2026-05-15.md   (12 copies, saved 11 reads)
      reports/asset_class_90day_plan_CRYPTO_2026-05-15.md (12 copies, saved 11 reads)
      ...
    DUPLICATES SUPPRESSED: M - N = X

Exit codes:
    0 ok    1 no inputs    2 file read error on >50% of inputs
"""

import argparse
import glob
import hashlib
import json
import os
import pathlib
import re
import sys
from collections import defaultdict


def normalize(p: str, repo_root: str) -> str:
    """Convert Windows backslash, drive-letter, or absolute-paths to a relative POSIX path under repo_root if possible."""
    if not p:
        return p
    p = p.strip().strip('"').strip("'")
    # Windows drive letter -> POSIX. E:\foo\bar -> /foo/bar but we want relative to repo_root.
    m = re.match(r"^[a-zA-Z]:[\\/](.+)$", p)
    if m:
        p = m.group(1)
    p = p.replace("\\", "/")
    # Strip a leading 'findtorontoevents_antigravity.ca/' if present (Windows-style absolute that contained the repo dir name)
    if p.startswith("findtorontoevents_antigravity.ca/"):
        p = p[len("findtorontoevents_antigravity.ca/"):]
    # Make relative to repo_root if absolute
    if p.startswith("/"):
        try:
            p = os.path.relpath(p, repo_root)
        except Exception:
            pass
    return p


def hash_file(path: str) -> str | None:
    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except (OSError, IOError):
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--glob", action="append", default=[],
                    help="Glob pattern (repeatable). Eg --glob 'reports/**/*.md'")
    ap.add_argument("--from-file", help="Read newline-delimited path list from this file")
    ap.add_argument("--from-stdin", action="store_true", help="Read newline-delimited path list from stdin")
    ap.add_argument("--repo-root", default=os.getcwd(), help="Repo root for path normalization")
    ap.add_argument("--json", action="store_true", help="Emit JSON instead of human text")
    ap.add_argument("--show-dupes", action="store_true", help="Also print the suppressed paths under each canonical")
    args = ap.parse_args()

    paths: list[str] = []
    if args.glob:
        for pat in args.glob:
            paths.extend(glob.glob(pat, recursive=True))
    if args.from_file:
        with open(args.from_file) as f:
            paths.extend(line for line in (l.strip() for l in f) if line and not line.startswith("#"))
    if args.from_stdin:
        paths.extend(line for line in (l.strip() for l in sys.stdin) if line and not line.startswith("#"))

    if not paths:
        print("ERROR: no input paths (use --glob, --from-file, or --from-stdin)", file=sys.stderr)
        return 1

    # Normalize + dedupe identical strings
    normalized = []
    seen_str = set()
    for p in paths:
        np = normalize(p, args.repo_root)
        if np in seen_str:
            continue
        seen_str.add(np)
        normalized.append(np)

    # Hash each — group by content
    groups: dict[str, list[str]] = defaultdict(list)
    missing: list[str] = []
    for p in normalized:
        full = p if os.path.isabs(p) else os.path.join(args.repo_root, p)
        h = hash_file(full)
        if h is None:
            missing.append(p)
            continue
        groups[h].append(p)

    if not groups:
        print(f"ERROR: 0/{len(normalized)} paths readable. Sample: {normalized[:3]}", file=sys.stderr)
        return 2

    # For each group, pick the shortest path; tiebreak by lexical
    canonical: list[dict] = []
    for h, members in groups.items():
        members_sorted = sorted(members, key=lambda x: (len(x), x))
        winner = members_sorted[0]
        canonical.append({
            "canonical": winner,
            "hash": h,
            "copies": len(members),
            "suppressed": members_sorted[1:],
        })
    # Sort canonical alphabetically for stable output
    canonical.sort(key=lambda d: d["canonical"])

    total_input = len(normalized)
    total_unique = len(canonical)
    total_dupes = total_input - total_unique - len(missing)

    if args.json:
        out = {
            "input_count": total_input,
            "unique_count": total_unique,
            "duplicate_count": total_dupes,
            "missing_count": len(missing),
            "missing": missing,
            "canonical": canonical if args.show_dupes else [
                {"canonical": c["canonical"], "copies": c["copies"]} for c in canonical
            ],
        }
        print(json.dumps(out, indent=2))
    else:
        print(f"CANONICAL ({total_unique} unique of {total_input} input):")
        for c in canonical:
            print(f"  {c['canonical']}  ({c['copies']} cop{'y' if c['copies']==1 else 'ies'})")
            if args.show_dupes and c["suppressed"]:
                for s in c["suppressed"]:
                    print(f"      -- dupe: {s}")
        print(f"\nDUPLICATES SUPPRESSED: {total_dupes}")
        if missing:
            print(f"MISSING/UNREADABLE: {len(missing)}")
            for m in missing[:5]:
                print(f"  - {m}")
            if len(missing) > 5:
                print(f"  ... and {len(missing) - 5} more")

    return 0


if __name__ == "__main__":
    sys.exit(main())
