#!/usr/bin/env python3
"""Fail if a dossier cites a repository path that does not resolve at a git ref.

The audit-review dossier set (docs/audit_review_2026-11-22/) cites source
artefacts as ``[SRC: path:line]`` spans, markdown links and bare backticked
paths.  When a cited file is missing from the ref a reader clones, the
citation cannot be followed and the dossier set cannot be independently
audited.  This is the same class of defect as a phantom code citation.

The checker parses every markdown file under ``--docs-dir`` *at the given ref*
(via ``git show``), extracts repository-path citations, and verifies each one
with ``git cat-file -e <ref>:<path>``.  A citation is allowed to be missing
only when explicitly exempted with ``--allow-missing`` (a path, or a file of
paths, optionally with a reason after ``#`` or a tab).  Exemptions are always
printed, never hidden.

Usage:
    python3 tools/check_dossier_citations.py
    python3 tools/check_dossier_citations.py --ref HEAD \\
        --allow-missing tools/dossier_citation_allowlist.txt

Exit codes: 0 = all citations resolve or are allowlisted, 1 = unresolvable
citation, 2 = bad usage / ref not found.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# [SRC: ...] spans, markdown link targets, and bare `backticked` tokens.
SRC_RE = re.compile(r"\[SRC:\s*([^\]]+)\]")
LINK_RE = re.compile(r"\]\(([^)\s]+)\)")
BACKTICK_RE = re.compile(r"`([^`\n]+)`")
# A token is a plausible repository file only if it ends in a known extension.
EXT_RE = re.compile(r"\.(py|json|jsonl|md|yml|yaml|html|js|ts|tsx|txt|csv|sh|ipynb|pine)$")
LINE_SUFFIX_RE = re.compile(r":\d+$")


def _git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(("git",) + args, cwd=str(root), capture_output=True, text=True)


def _clean(token: str) -> str:
    token = token.strip().strip("`").strip()
    token = token.rstrip(".,;:")
    return LINE_SUFFIX_RE.sub("", token)


GLOB_CHARS = set("*|[]{}<>")


def is_repo_path(token: str) -> bool:
    """True for tokens that name one concrete repository file.

    Rejected: URLs, anchors, absolute or dot-relative paths (live-server
    surfaces such as /audit/data/x.json), manifest keys (manifest:entries),
    glob patterns (*.py, _raw/audit*_page.html), and bare filenames with no
    directory component (audit2.js) -- a bare name in prose may be a live
    surface, so it is not a verifiable repository citation.
    """
    if not token or " " in token:
        return False
    if token.startswith(("http://", "https://", "#", "./", "../", "/")):
        return False
    if ":" in token:  # manifest:entries, still-unstripped path:line, scheme
        return False
    if GLOB_CHARS & set(token):
        return False
    if "/" not in token:
        return False
    if not EXT_RE.search(token):
        return False
    return True


def extract_citations(text: str) -> set[str]:
    tokens: set[str] = set()
    for match in SRC_RE.finditer(text):
        for raw in re.split(r"[\s,]+", match.group(1)):
            token = _clean(raw)
            if is_repo_path(token):
                tokens.add(token)
    for match in LINK_RE.finditer(text):
        token = _clean(match.group(1))
        if is_repo_path(token):
            tokens.add(token)
    for match in BACKTICK_RE.finditer(text):
        token = _clean(match.group(1))
        if is_repo_path(token):
            tokens.add(token)
    return tokens


def resolve(root: Path, ref: str, docs_dir: str, citing_file: str, token: str) -> str | None:
    """Return the path that resolves at ``ref``, or None.

    A citation may be written repo-relative, relative to the citing file, or
    relative to the docs directory root (``_raw/...`` style).  All three are
    followable by a reader, so all three are accepted.
    """
    candidates = [
        os.path.normpath(token),
        os.path.normpath(os.path.join(os.path.dirname(citing_file), token)),
        os.path.normpath(os.path.join(docs_dir, token)),
    ]
    seen: set[str] = set()
    for candidate in candidates:
        if candidate in seen or candidate.startswith(".."):
            continue
        seen.add(candidate)
        if _git(root, "cat-file", "-e", f"{ref}:{candidate}").returncode == 0:
            return candidate
    return None


def load_allowlist(entries: list[str], root: Path) -> dict[str, str]:
    """Expand --allow-missing values into {path: reason}.

    Each value is either ``path``, ``path#reason``, or a file containing one
    ``path[#reason]`` per line.  ``#`` lines in a file are comments.
    """
    allowed: dict[str, str] = {}
    for entry in entries:
        entry = entry.strip()
        if not entry:
            continue
        if "#" in entry:
            path, reason = entry.split("#", 1)
            allowed[_clean(path.strip())] = reason.strip()
            continue
        candidate = Path(entry)
        if not candidate.is_absolute():
            candidate = root / entry
        if candidate.is_file() and candidate.suffix not in EXT_RE.pattern:
            for line in candidate.read_text(encoding="utf-8", errors="replace").splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "#" in line:
                    path, reason = line.split("#", 1)
                elif "\t" in line:
                    path, reason = line.split("\t", 1)
                else:
                    path, reason = line, ""
                allowed[_clean(path.strip())] = reason.strip()
        else:
            allowed[_clean(entry)] = ""
    return allowed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--ref", default="origin/main", help="git ref to resolve citations against (default: origin/main)")
    parser.add_argument("--docs-dir", default="docs/audit_review_2026-11-22", help="dossier directory at --ref")
    parser.add_argument("--allow-missing", action="append", default=[], metavar="FILE_OR_PATH",
                        help="exempt a path, or a file of paths, from the check (repeatable; reason after '#'). "
                             "tools/dossier_citation_allowlist.txt is loaded automatically when present.")
    parser.add_argument("--root", default=str(REPO_ROOT), help="repository root (default: this tool's repo)")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()

    if _git(root, "rev-parse", "--verify", "--quiet", args.ref + "^{commit}").returncode != 0:
        print(f"[dossier-citations] ERROR: ref not found: {args.ref}", file=sys.stderr)
        print("  In a depth-1 CI checkout origin/main may not exist; pass --ref HEAD.", file=sys.stderr)
        return 2

    listing = _git(root, "ls-tree", "-r", "--name-only", args.ref, args.docs_dir)
    if listing.returncode != 0:
        print(f"[dossier-citations] ERROR: cannot list {args.docs_dir} at {args.ref}", file=sys.stderr)
        return 2
    files = [f for f in listing.stdout.splitlines() if f.endswith(".md")]
    if not files:
        print(f"[dossier-citations] WARNING: no markdown files under {args.docs_dir} at {args.ref}")
        return 0

    allow_entries = list(args.allow_missing)
    default_allowlist = root / "tools" / "dossier_citation_allowlist.txt"
    if default_allowlist.is_file():
        allow_entries.append(str(default_allowlist))
    allowed = load_allowlist(allow_entries, root)
    cited_in: dict[str, set[str]] = {}
    for path in files:
        text = _git(root, "show", f"{args.ref}:{path}").stdout
        for token in extract_citations(text):
            cited_in.setdefault(token, set()).add(path)

    resolved: dict[str, str] = {}
    missing: dict[str, set[str]] = {}
    for token, sources in cited_in.items():
        hit = None
        for source in sorted(sources):
            hit = resolve(root, args.ref, args.docs_dir, source, token)
            if hit:
                break
        if hit:
            resolved[token] = hit
        else:
            missing[token] = sources

    exempt = {t: s for t, s in missing.items() if t in allowed}
    unresolved = {t: s for t, s in missing.items() if t not in allowed}

    print(f"[dossier-citations] ref={args.ref} docs-dir={args.docs_dir}")
    print(f"  files scanned:      {len(files)}")
    print(f"  distinct cited paths: {len(cited_in)}")
    print(f"  resolved:           {len(resolved)}")
    print(f"  allowlisted:        {len(exempt)}")
    print(f"  UNRESOLVED:         {len(unresolved)}")
    for token in sorted(exempt):
        reason = allowed[token] or "(no reason given)"
        print(f"  allowed: {token}  [{reason}]")
    for token in sorted(unresolved):
        print(f"  MISSING: {token}")
        for source in sorted(unresolved[token]):
            print(f"      cited in {source}")
    if unresolved:
        print(f"[dossier-citations] FAIL - {len(unresolved)} unresolvable citation(s) at {args.ref}")
        return 1
    print(f"[dossier-citations] PASS - every citation resolves at {args.ref} or is allowlisted")
    return 0


if __name__ == "__main__":
    sys.exit(main())
