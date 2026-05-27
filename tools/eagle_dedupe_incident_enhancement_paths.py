#!/usr/bin/env python3
"""
EAGLE helper: collect all incident/enhancement markdown references in the repo,
dedupe them by canonical path, and prefer the shortest path representation.

Usage:
  python tools/eagle_dedupe_incident_enhancement_paths.py \
    --root . \
    --out deduped_paths.txt

Heuristics:
- Looks for strings ending in ".md" within incident/enhancement contexts:
  - updates/*.md (QUICK_WINS_*/EAGLE links)
  - audit_dashboard/incidents.html (links to incidents/enhancements md)
  - ENHANCEMENTS*.md and ENHANCEMENTS*.*
- Extracts both relative and absolute-looking paths, normalizes to repo-relative
  when possible, then dedupes.
"""

from __future__ import annotations

import argparse
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional


MD_REF_RE = re.compile(
    r"""
    (?:
      (?P<winpath>[A-Za-z]:\\[^\s'")]+?\.md)
      |
      (?P<unixpath>/(?:[^\s'")]+?\.md))
      |
      (?P<relpath>(?:\./)?[A-Za-z0-9_\-./]+?\.md)
    )
    """,
    re.VERBOSE,
)

def iter_text_files(root: Path) -> Iterable[Path]:
    # Avoid node_modules/.venv/.git to keep it fast.
    blacklist = {".git", "node_modules", ".venv", "__pycache__", "dist", "build", ".next"}
    for p in root.rglob("*"):
        if any(part in blacklist for part in p.parts):
            continue
        if p.is_file():
            # We only scan text-like files.
            if p.suffix.lower() in {".md", ".html", ".py", ".js", ".ts", ".json"} or p.name.endswith(".yml"):
                yield p

def normalize_to_repo_relative(root: Path, raw: str) -> Optional[Path]:
    raw = raw.strip()

    # Windows absolute path like C:\foo\bar.md -> try to match tail parts.
    if re.match(r"^[A-Za-z]:\\", raw):
        # Convert backslashes to slashes, then strip to last occurrence of repo marker if any.
        candidate = raw.replace("\\", "/")
        parts = candidate.split("/")
        # Prefer the last segment(s) that look like repo-relative: start at "findtorontoevents_antigravity.ca"
        if "findtorontoevents_antigravity.ca" in parts:
            idx = parts.index("findtorontoevents_antigravity.ca") + 1
            rel = Path(*parts[idx:])
            return rel
        # Otherwise just return path relative-ish by taking tail after "reports/" or "updates/" etc.
        for marker in ("reports", "audit_dashboard", "audit_trail", "tools", "updates", "alpha_engine", "models", "src", ".claude"):
            if marker in parts:
                idx = parts.index(marker)
                return Path(*parts[idx:])
        return None

    # Unix absolute path like /home/.../repo/xxx.md -> strip to last known repo folder name
    if raw.startswith("/"):
        candidate = raw
        parts = candidate.strip("/").split("/")
        if "findtorontoevents_antigravity.ca" in parts:
            idx = parts.index("findtorontoevents_antigravity.ca") + 1
            rel = Path(*parts[idx:])
            return rel
        # Otherwise attempt last ".md" tail
        return None

    # Relative path
    if raw.startswith("./"):
        raw = raw[2:]
    rel = Path(raw)
    if rel.parts and not rel.is_absolute():
        return rel

    return None

@dataclass
class Choice:
    path: Path
    raw_len: int

def pick_best_path(candidates: list[Path]) -> Path:
    # Prefer shortest string length, then lexicographic.
    return sorted(candidates, key=lambda p: (len(str(p)), str(p)))[0]

def extract_md_refs(text: str) -> list[str]:
    return [m.group(0) for m in MD_REF_RE.finditer(text)]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".", help="Repo root to scan")
    ap.add_argument("--out", default="deduped_paths.txt", help="Output file for deduped paths")
    ap.add_argument("--min-context", default=1, type=int, help="(unused) reserved for future")
    args = ap.parse_args()

    root = Path(args.root).resolve()

    # Only consider "incident/enhancement" related files/contexts to reduce noise.
    relevant_keywords = [
        "INCIDENT_", "ENHANCEMENT_", "incidents", "enhancements",
        "audit_dashboard/incidents.html",
        "ENHANCEMENTS.md",
    ]

    # Gather candidates by normalized relative path.
    seen: dict[str, list[Path]] = {}

    for p in iter_text_files(root):
        try:
            txt = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        if not any(k.lower() in (p.name.lower() + " " + txt[:5000].lower()) for k in relevant_keywords):
            # Still allow generic scanning for md refs if file itself is incident/enhancement.
            if "INCIDENT_" not in p.name.upper() and "ENHANCEMENT_" not in p.name.upper() and "incidents" not in p.name.lower():
                continue

        raw_refs = extract_md_refs(txt)
        for raw in raw_refs:
            rel = normalize_to_repo_relative(root, raw)
            if rel is None:
                continue
            # Only keep .md
            if rel.suffix.lower() != ".md":
                continue
            key = str(rel).replace("\\", "/")
            seen.setdefault(key, []).append(rel)

    # Deduplicate by key (already normalized), but keep shortest representation per key.
    deduped: list[Path] = []
    for key, candidates in seen.items():
        best = pick_best_path(candidates)
        deduped.append(best)

    deduped_sorted = sorted(deduped, key=lambda p: (len(str(p)), str(p)))

    out_path = (root / args.out).resolve()
    out_path.write_text("\n".join(str(p).replace("\\", "/") for p in deduped_sorted) + "\n", encoding="utf-8")

    print(f"[eagle] Scanned repo: {root}")
    print(f"[eagle] Found normalized unique md refs: {len(deduped_sorted)}")
    print(f"[eagle] Wrote: {out_path}")

if __name__ == "__main__":
    main()
