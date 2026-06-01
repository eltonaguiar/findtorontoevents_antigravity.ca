#!/usr/bin/env python3
"""dedup_files.py — find duplicate / near-duplicate files before reviewing them.

Use case: you're handed a set of files (reports, MD docs, generated artifacts)
to review. Reviewing two byte-identical or near-identical files twice is wasted
effort. This groups them so you review one representative per cluster.

Two modes:
  exact   (default) — SHA-256 of raw bytes. Byte-for-byte identical only.
  similar (--similar) — normalized-text Jaccard token overlap >= --threshold
                        (default 0.90). Catches reformatted / lightly-edited dups.

Zero dependencies (stdlib only). Cross-platform.

Examples:
    # exact-dup groups among all reports
    python tools/dedup_files.py reports/*.md

    # near-dup clusters at 85% token overlap, machine-readable
    python tools/dedup_files.py --similar --threshold 0.85 --json docs/ reports/

    # recurse a dir, only show clusters with >1 file (the default)
    python tools/dedup_files.py --recurse updates/

Exit code: 0 if no duplicate groups found, 1 if at least one group found
(so it can gate a review step in CI / a pre-commit hook).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------- file gathering


def gather(inputs: list[str], recurse: bool) -> list[Path]:
    """Expand inputs (files, dirs, globs) into a deduped sorted list of files."""
    seen: dict[str, Path] = {}
    for item in inputs:
        p = Path(item)
        candidates: list[Path] = []
        if p.is_dir():
            it = p.rglob("*") if recurse else p.glob("*")
            # skip symlinks: avoids traversal cycles + double-counting link+target
            candidates = [c for c in it if c.is_file() and not c.is_symlink()]
        elif p.is_file():
            candidates = [p]
        else:
            # treat as a glob relative to cwd
            candidates = [c for c in Path().glob(item) if c.is_file()]
        for c in candidates:
            key = str(c.resolve())
            seen.setdefault(key, c)
    return sorted(seen.values(), key=lambda x: str(x))


def shortest_path(paths: list[str]) -> str:
    """Pick the canonical file: fewest path components, then shortest string.

    For 80 copies of TESTING_PROTOCOL.MD scattered across worktrees, this
    returns the repo-root copy (E:\\repo\\TESTING_PROTOCOL.MD) over the deep
    .worktrees/agent-xxxx/ copies.
    """
    return min(paths, key=lambda p: (len(Path(p).parts), len(p), p))


# ---------------------------------------------------------------- exact mode


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def exact_groups(files: list[Path]) -> list[dict]:
    by_size: dict[int, list[Path]] = {}
    for f in files:
        try:
            by_size.setdefault(f.stat().st_size, []).append(f)
        except OSError:
            continue
    by_hash: dict[str, list[Path]] = {}
    for size, group in by_size.items():
        if len(group) < 2:
            continue  # unique size -> can't be an exact dup, skip hashing
        for f in group:
            try:
                by_hash.setdefault(sha256(f), []).append(f)
            except OSError:
                continue
    out = []
    for digest, group in by_hash.items():
        if len(group) > 1:
            out.append({"key": digest[:16], "files": [str(f) for f in group]})
    return out


# ---------------------------------------------------------------- similar mode

_WS = re.compile(r"\s+")
_TOKEN = re.compile(r"[a-z0-9]+")


def tokens(path: Path):
    """Token set for text files, or None for binary/unreadable (excluded from
    similar clustering so two binaries don't both collapse to the empty set
    and falsely match at Jaccard 1.0)."""
    try:
        raw = path.read_bytes()
    except OSError:
        return None
    if b"\x00" in raw[:8192]:  # null byte in head -> treat as binary, skip
        return None
    text = _WS.sub(" ", raw.decode("utf-8", errors="replace").lower())
    return set(_TOKEN.findall(text))


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def similar_groups(files: list[Path], threshold: float) -> list[dict]:
    # exclude binary/unreadable (tokens()==None) from clustering
    toks = {f: t for f in files if (t := tokens(f)) is not None}
    files = [f for f in files if f in toks]
    # union-find over pairs above threshold
    parent = {f: f for f in files}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        parent[find(x)] = find(y)

    fl = files
    sims: dict[tuple, float] = {}
    for i in range(len(fl)):
        for j in range(i + 1, len(fl)):
            s = jaccard(toks[fl[i]], toks[fl[j]])
            if s >= threshold:
                union(fl[i], fl[j])
                sims[(str(fl[i]), str(fl[j]))] = round(s, 4)
    clusters: dict[Path, list[Path]] = {}
    for f in fl:
        clusters.setdefault(find(f), []).append(f)
    out = []
    for root, group in clusters.items():
        if len(group) > 1:
            out.append(
                {
                    "key": f"~{threshold:g}",
                    "files": [str(f) for f in group],
                    "pair_scores": {
                        f"{a} | {b}": v
                        for (a, b), v in sims.items()
                        if a in {str(x) for x in group}
                    },
                }
            )
    return out


# ---------------------------------------------------------------- main


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Find duplicate/near-duplicate files.")
    ap.add_argument("inputs", nargs="*", help="files, dirs, or globs")
    ap.add_argument("--from-file", metavar="PATH",
                    help="read newline-delimited paths from a file ('-' = stdin)")
    ap.add_argument("--similar", action="store_true", help="near-dup mode (token Jaccard)")
    ap.add_argument("--threshold", type=float, default=0.90, help="similar-mode min overlap 0-1 (default 0.90)")
    ap.add_argument("--max-similar", type=int, default=2000,
                    help="refuse --similar over this many files (O(n^2)); raise to override (default 2000)")
    ap.add_argument("--recurse", action="store_true", help="recurse into directory inputs")
    ap.add_argument("--json", action="store_true", help="machine-readable JSON output")
    ap.add_argument("--review-set", action="store_true",
                    help="print ONLY the minimal review list: shortest path per "
                         "duplicate group + every unique file (one per line)")
    args = ap.parse_args(argv)

    inputs = list(args.inputs)
    if args.from_file:
        src = sys.stdin if args.from_file == "-" else open(args.from_file, encoding="utf-8")
        with src as fh:
            inputs += [ln.strip() for ln in fh if ln.strip()]
    if not inputs:
        ap.error("no inputs (pass files/dirs/globs or --from-file)")

    files = gather(inputs, args.recurse)
    if not files:
        print("No files matched.", file=sys.stderr)
        return 0

    if args.similar:
        if len(files) > args.max_similar:
            ap.error(f"--similar on {len(files)} files is O(n^2); cap is "
                     f"--max-similar={args.max_similar}. Narrow inputs or raise the cap.")
        groups = similar_groups(files, args.threshold)
        mode = f"similar (>= {args.threshold:g})"
    else:
        groups = exact_groups(files)
        mode = "exact (sha256)"

    dup_count = sum(len(g["files"]) for g in groups)
    uniques = len(files) - dup_count + len(groups)  # one survivor per group

    # canonical = shortest path per group; review_set = canonicals + singletons
    grouped = set()
    for g in groups:
        g["canonical"] = shortest_path(g["files"])
        grouped.update(g["files"])
    singletons = [str(f) for f in files if str(f) not in grouped]
    review_set = sorted(
        [g["canonical"] for g in groups] + singletons,
        key=lambda p: (len(Path(p).parts), len(p), p),
    )

    if args.review_set:
        for p in review_set:
            print(p)
        return 1 if groups else 0

    if args.json:
        print(json.dumps(
            {"mode": mode, "scanned": len(files), "groups": groups,
             "review_set": review_set,
             "review_savings": dup_count - len(groups)},
            indent=2))
    else:
        print(f"# dedup_files -- {mode}")
        print(f"scanned {len(files)} files -> {len(groups)} duplicate group(s)")
        if not groups:
            print("\nNo duplicates. Review all files.")
        for i, g in enumerate(groups, 1):
            print(f"\n[{i}] {g['key']}  ({len(g['files'])} files)")
            for f in g["files"]:
                tag = "  <- canonical (shortest path)" if f == g["canonical"] else ""
                print(f"    {f}{tag}")
            for pair, score in g.get("pair_scores", {}).items():
                print(f"      ~ {score}  {pair}")
        if groups:
            saved = dup_count - len(groups)
            print(f"\nReview {uniques} files instead of {len(files)} "
                  f"(skip {saved} duplicate(s)).")
            print("\n# minimal review set (shortest path per group + uniques):")
            for p in review_set:
                print(f"  {p}")

    return 1 if groups else 0


if __name__ == "__main__":
    raise SystemExit(main())
