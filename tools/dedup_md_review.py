#!/usr/bin/env python3
"""Walk the repo finding all .md files, group by SHA256 hash, surface duplicates."""

import argparse
import hashlib
import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def find_md_files(root: str) -> list[str]:
    """Return all .md file paths under root (case-insensitive extension)."""
    matches: list[str] = []
    for dirpath, _dirnames, filenames in os.walk(root):
        for fn in filenames:
            if fn.lower().endswith(".md"):
                full = os.path.join(dirpath, fn)
                matches.append(full)
    return matches


def content_hash(filepath: str) -> str | None:
    """Return hex SHA256 of file content, or None if unreadable."""
    try:
        h = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except (OSError, PermissionError):
        return None


def fallback_key(filepath: str) -> tuple[str, int]:
    """(basename, size) when content is inaccessible."""
    try:
        sz = os.path.getsize(filepath)
    except OSError:
        sz = 0
    return os.path.basename(filepath), sz


def group_key(filepath: str) -> str:
    """Primary: SHA256. Fallback: 'basename|size'."""
    h = content_hash(filepath)
    if h is not None:
        return h
    bname, sz = fallback_key(filepath)
    return f"__FALLBACK__{bname}|{sz}"


def path_priority(path: str) -> int:
    """Lower = better. Prefer shortest path; prefer reports/ root over worktree copies."""
    parts = path.replace(os.sep, "/").split("/")
    # Worktree paths score higher (worse)
    for p in parts:
        if p == ".claude":
            return 2
    return 1


def keep_best(group: list[str]) -> str:
    """From a list of equivalent file paths, return the canonical one."""
    return min(group, key=lambda p: (path_priority(p), len(p), p))


def collect_groups(files: list[str]) -> dict[str, list[str]]:
    """Return dict keyed by content hash -> list of matching file paths."""
    groups: dict[str, list[str]] = {}
    for fp in files:
        k = group_key(fp)
        groups.setdefault(k, []).append(fp)
    return groups


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Review duplicate .md files in the repo by content hash."
    )
    parser.add_argument("--list", action="store_true", help="List unique file paths")
    parser.add_argument("--report", action="store_true", help="Show duplicate groups")
    parser.add_argument(
        "--dupes-only", action="store_true", help="Show only files with duplicates"
    )
    args = parser.parse_args()

    files = find_md_files(_REPO_ROOT)
    groups = collect_groups(files)

    if not (args.list or args.report or args.dupes_only):
        parser.print_help()
        sys.exit(1)

    if args.list:
        uniques: list[str] = []
        for members in groups.values():
            uniques.append(keep_best(members))
        uniques.sort()
        sys.stdout.write("\n".join(uniques) + "\n")

    if args.report:
        dedup_count = sum(1 for m in groups.values() if len(m) > 1)
        print(f"Total .md files found: {len(files)}")
        print(f"Unique content hashes:  {len(groups)}")
        print(f"Groups with duplicates: {dedup_count}")
        print()
        for h, members in sorted(groups.items(), key=lambda kv: -len(kv[1])):
            tag = ""
            if h.startswith("__FALLBACK__"):
                tag = " [FALLBACK KEY]"
            print(f"SHA256: {h}{tag}")
            print(f"  Count:  {len(members)}")
            best = keep_best(members)
            for m in sorted(members):
                marker = "  (canonical)" if m == best else ""
                print(f"    {m}{marker}")
            print()

    if args.dupes_only:
        dupes: list[str] = []
        for members in groups.values():
            if len(members) > 1:
                best = keep_best(members)
                dupes.append(best)
        dupes.sort()
        sys.stdout.write("\n".join(dupes) + "\n")


if __name__ == "__main__":
    main()
