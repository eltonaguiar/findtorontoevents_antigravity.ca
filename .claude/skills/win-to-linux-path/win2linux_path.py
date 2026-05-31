#!/usr/bin/env python3
"""
win2linux_path.py — Resolve Windows path(s) to their equivalent Linux file(s) in this repo.

The Windows checkout lives at  E:\\findtorontoevents_antigravity.ca\\...
The Linux  checkout lives at  /home/eaguiar2015/findtorontoevents_antigravity.ca/...

This tool maps a pasted Windows path (or a whole list of them) to the on-disk Linux
path, VERIFIES the file/dir actually exists, and falls back intelligently when it does
not (worktree copies that only exist on one OS, basename fuzzy search, external paths
like Program Files / AppData that have no repo equivalent).

Lives inside the skill dir (not tools/) because the shared working tree is hot — peers
stash/branch-switch in tools/ and a fresh untracked file there gets swept into a stash.

Usage:
    # One or more paths as args
    python3 win2linux_path.py 'E:\\findtorontoevents_antigravity.ca\\reports\\SUPREME_PLAN_90days.md'

    # A newline-delimited list (also accepts the raw multi-line blob a user pastes)
    python3 win2linux_path.py --from-file /tmp/winpaths.txt
    pbpaste | python3 win2linux_path.py --from-stdin

    # Only print the resolved Linux paths that exist (one per line) — good for piping
    python3 win2linux_path.py --from-stdin --exists-only

    # JSON for downstream tooling
    python3 win2linux_path.py --from-file /tmp/winpaths.txt --json

Resolution order per input:
    1. DIRECT      REPO_ROOT/<relpath>                         (exact translate, exists)
    2. WORKTREE    strip .claude|.qwen/worktrees/<id>/ prefix  -> main-tree copy exists
    3. WT_SWAP     swap .claude<->.qwen worktrees, existing id -> exists
    4. FUZZY       search repo by basename                     -> candidate(s)
    5. EXTERNAL    path is outside the repo (Program Files, AppData, other drive) -> no equiv
    6. MISSING     translated cleanly but nothing on disk

Exit codes:
    0 every input resolved to an existing path
    3 at least one input did not resolve (MISSING/EXTERNAL/FUZZY-only)
"""

import argparse
import json
import os
import re
import sys

REPO_ROOT = "/home/eaguiar2015/findtorontoevents_antigravity.ca"
REPO_DIR_NAME = "findtorontoevents_antigravity.ca"
WORKTREE_RE = re.compile(r"^\.(?:claude|qwen)/worktrees/[^/]+/(.*)$")


def split_blob(text: str):
    """Split a pasted blob into individual paths. One per line; tolerant of CRLF and quotes."""
    out = []
    for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = line.strip().strip('"').strip("'")
        if line:
            out.append(line)
    return out


def to_relpath(p: str):
    """Translate a Windows (or already-POSIX) path to a repo-relative POSIX path.

    Returns (relpath, is_external):
      relpath     repo-relative POSIX path (None if external/unmappable)
      is_external True when the path lives outside the repo (other drive, Program Files, AppData...)
    """
    raw = p.strip().strip('"').strip("'")
    norm = raw.replace("\\", "/")
    # Strip a leading drive letter:  E:/foo -> /foo
    m = re.match(r"^[a-zA-Z]:/(.*)$", norm)
    drive_rooted = m is not None
    if m:
        norm = "/" + m.group(1)

    # If the repo dir name appears, everything after the FIRST occurrence is the relpath.
    marker = REPO_DIR_NAME + "/"
    idx = norm.find(marker)
    if idx != -1:
        rel = norm[idx + len(marker):]
        return rel.strip("/"), False
    # Exactly the repo root itself (no trailing component)
    if norm.rstrip("/").endswith(REPO_DIR_NAME):
        return "", False

    # Already a POSIX path under the real Linux repo root?
    if norm.startswith(REPO_ROOT):
        rel = os.path.relpath(norm, REPO_ROOT)
        if not rel.startswith(".."):
            return rel, False

    # Drive-rooted but not in the repo (E:\Program Files..., C:\Users\...\AppData...) => external.
    if drive_rooted or re.match(r"^[a-zA-Z]:", raw):
        return None, True
    # Bare relative path the user pasted — treat as repo-relative.
    if not norm.startswith("/"):
        return norm.strip("/"), False
    return None, True


def resolve(relpath: str):
    """Given a repo-relative POSIX path, find the existing Linux file. Returns (method, abspath_or_candidates)."""
    direct = os.path.join(REPO_ROOT, relpath) if relpath else REPO_ROOT
    if os.path.exists(direct):
        return "DIRECT", direct

    # Worktree copy that doesn't exist here -> try the main-tree equivalent.
    m = WORKTREE_RE.match(relpath)
    if m:
        sub = m.group(1)
        main_candidate = os.path.join(REPO_ROOT, sub)
        if os.path.exists(main_candidate):
            return "WORKTREE", main_candidate
        # Try the same relative path under any worktree that actually exists on this box
        for base in (".claude/worktrees", ".qwen/worktrees"):
            wt_root = os.path.join(REPO_ROOT, base)
            if os.path.isdir(wt_root):
                for wid in os.listdir(wt_root):
                    cand = os.path.join(wt_root, wid, sub)
                    if os.path.exists(cand):
                        return "WT_SWAP", cand
        relpath = sub  # fall through to fuzzy on the inner subpath

    # Fuzzy: match by basename anywhere in the repo (skip heavy/vendor dirs).
    base = os.path.basename(relpath)
    if base:
        hits = fuzzy_find(base)
        if hits:
            return "FUZZY", hits
    return "MISSING", direct


_SKIP_DIRS = {".git", "node_modules", "__pycache__", ".next", "build", "dist", ".venv", "venv"}


def fuzzy_find(basename: str, limit: int = 12):
    hits = []
    for dirpath, dirnames, filenames in os.walk(REPO_ROOT):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        if basename in filenames or basename in dirnames:
            hits.append(os.path.join(dirpath, basename))
            if len(hits) >= limit:
                break
    # Prefer shortest path (canonical main-tree copy over worktree copies).
    hits.sort(key=lambda x: (x.count("/"), len(x)))
    return hits


def main():
    ap = argparse.ArgumentParser(description="Resolve Windows path(s) to equivalent Linux file(s).")
    ap.add_argument("paths", nargs="*", help="Windows path(s) to resolve")
    ap.add_argument("--from-file", help="Read newline-delimited path list from this file")
    ap.add_argument("--from-stdin", action="store_true", help="Read newline-delimited path list from stdin")
    ap.add_argument("--exists-only", action="store_true", help="Print only resolved paths that exist, one per line")
    ap.add_argument("--json", action="store_true", help="Emit JSON")
    args = ap.parse_args()

    inputs = list(args.paths)
    if args.from_file:
        with open(args.from_file, encoding="utf-8", errors="replace") as f:
            inputs += split_blob(f.read())
    if args.from_stdin:
        inputs += split_blob(sys.stdin.read())
    inputs = [p for p in inputs if p.strip()]

    if not inputs:
        ap.error("no input paths (pass args, --from-file, or --from-stdin)")

    results = []
    all_ok = True
    for p in inputs:
        rel, external = to_relpath(p)
        if external or rel is None:
            results.append({"input": p, "method": "EXTERNAL", "resolved": None,
                            "exists": False, "note": "outside the repo — no Linux equivalent"})
            all_ok = False
            continue
        method, val = resolve(rel)
        if method == "FUZZY":
            results.append({"input": p, "method": "FUZZY", "relpath": rel,
                            "resolved": val[0], "candidates": val, "exists": True})
            all_ok = False  # not an exact translation
        elif method == "MISSING":
            results.append({"input": p, "method": "MISSING", "relpath": rel,
                            "resolved": val, "exists": False})
            all_ok = False
        else:
            results.append({"input": p, "method": method, "relpath": rel,
                            "resolved": val, "exists": True})

    if args.json:
        print(json.dumps(results, indent=2))
    elif args.exists_only:
        for r in results:
            if r.get("exists") and r.get("resolved"):
                print(r["resolved"])
    else:
        width = {"DIRECT": "✓", "WORKTREE": "✓~", "WT_SWAP": "✓~", "FUZZY": "≈", "MISSING": "✗", "EXTERNAL": "—"}
        n_ok = sum(1 for r in results if r.get("exists"))
        for r in results:
            tag = width.get(r["method"], "?")
            if r["method"] == "FUZZY":
                print(f"{tag} {r['input']}")
                for c in r["candidates"]:
                    print(f"     candidate: {c}")
            elif r["method"] == "EXTERNAL":
                print(f"{tag} {r['input']}\n     EXTERNAL — no Linux equivalent in repo")
            elif r["method"] == "MISSING":
                print(f"{tag} {r['input']}\n     would be: {r['resolved']}  (does not exist)")
            else:
                note = "" if r["method"] == "DIRECT" else f"  [{r['method']}: worktree copy not present; mapped to main tree]"
                print(f"{tag} {r['resolved']}{note}")
        print(f"\n{n_ok}/{len(results)} resolved to an existing path.")

    sys.exit(0 if all_ok else 3)


if __name__ == "__main__":
    main()
