#!/usr/bin/env python3
"""Rewrite dashboard payloads as strict JSON (NaN/Infinity -> null).

One-off repair for payloads already committed with bare non-finite tokens. It
re-parses each file leniently (parse_constant -> None) and re-serialises with
allow_nan=False, so the output is guaranteed parseable by a browser and by
ci.yml's gate. Producers are fixed separately (tools/strict_json.py), so this
should not need to run again.

Usage:
    python tools/strictify_payloads.py                    # audit_dashboard/data/*.json
    python tools/strictify_payloads.py --check            # report only, exit 1 if any dirty
    python tools/strictify_payloads.py path/a.json ...    # specific files
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# Mirrors PAYLOAD_DIRS in tests/test_dashboard_payload_strict_json.py: the CI gate
# checks both dashboard payload trees, so the repair must cover both.
DEFAULT_DIRS = [ROOT / "audit_dashboard" / "data", ROOT / "multi_asset" / "data"]

# Only files that actually carry a bare non-finite token are touched. Without
# this guard the tool rewrites every payload (whitespace/newline differences),
# producing a 350-file diff for a two-file defect.
# POSIX character classes are not supported by Python's re, so list the
# delimiters explicitly: a non-finite token only counts when it follows a JSON
# value separator, never when it appears inside a string.
_NON_FINITE = re.compile(r'[:,\[]\s*(?:-?Infinity|NaN)')

sys.path.insert(0, str(ROOT))
from tools.strict_json import dumps_strict  # noqa: E402


def _reject(token):
    return None  # NaN / Infinity / -Infinity -> JSON null


def strictify(path: Path, check_only: bool) -> str:
    raw = path.read_text(encoding="utf-8")
    if not _NON_FINITE.search(raw):
        return "clean"
    try:
        obj = json.loads(raw, parse_constant=_reject)
    except json.JSONDecodeError as e:
        return f"SKIP (invalid): {e}"
    text = dumps_strict(obj) + "\n"
    if text == raw:
        return "clean"
    if check_only:
        return "DIRTY"
    path.write_text(text, encoding="utf-8")
    return "rewritten"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    files = [Path(p) for p in args.paths] if args.paths else sorted(
        f for d in DEFAULT_DIRS if d.is_dir() for f in d.glob("*.json"))
    dirty = 0
    for f in files:
        status = strictify(f, args.check)
        if status in ("DIRTY", "rewritten"):
            dirty += 1
        print(f"{status:9s} {f.relative_to(ROOT) if f.is_absolute() and ROOT in f.parents else f}")
    print(f"\n{len(files)} file(s) scanned, {dirty} needed strictification")
    if args.check and dirty:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
