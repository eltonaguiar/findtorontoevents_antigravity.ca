#!/usr/bin/env python3
"""
Ensure STRATEGY_TRACK_ALIASES (alpha_engine/config.py) matches
LEADERBOARD_STRATEGY_ALIASES in audit_dashboard/template.html.

Drift causes split leaderboard vs pipeline track stats. Run in CI after
editing either map.

Usage:
  python tools/validate_strategy_alias_parity.py
  python tools/validate_strategy_alias_parity.py --template path/to/template.html
  python tools/validate_strategy_alias_parity.py --skip-index   # only Python vs template
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from alpha_engine.config import STRATEGY_TRACK_ALIASES  # noqa: E402

_MARKER = "const LEADERBOARD_STRATEGY_ALIASES = {"


def extract_js_leaderboard_aliases(html: str) -> dict[str, str]:
    """Parse flat `key: 'value'` entries inside LEADERBOARD_STRATEGY_ALIASES object."""
    start = html.find(_MARKER)
    if start < 0:
        raise ValueError("LEADERBOARD_STRATEGY_ALIASES block not found in template")

    brace0 = html.find("{", start)
    if brace0 < 0:
        raise ValueError("Malformed LEADERBOARD_STRATEGY_ALIASES (no opening brace)")

    depth = 0
    i = brace0
    while i < len(html):
        c = html[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                body = html[brace0 + 1 : i]
                return _parse_js_alias_body(body)
        i += 1
    raise ValueError("Unclosed LEADERBOARD_STRATEGY_ALIASES object")


def _parse_js_alias_body(body: str) -> dict[str, str]:
    out: dict[str, str] = {}
    line_pat = re.compile(
        r"^\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*'([^']*)'\s*,?\s*$"
    )
    for raw_line in body.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("//"):
            continue
        if "//" in line:
            line = line[: line.index("//")].strip()
        line = line.rstrip(",").strip()
        if not line:
            continue
        m = line_pat.match(line)
        if not m:
            raise ValueError("Unparsed LEADERBOARD_STRATEGY_ALIASES line: %r" % raw_line.strip())
        out[m.group(1)] = m.group(2)
    return out


def compare_maps(py_map: dict[str, str], js_map: dict[str, str]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    py_keys = set(py_map)
    js_keys = set(js_map)
    for k in sorted(py_keys - js_keys):
        errors.append("Only in Python STRATEGY_TRACK_ALIASES: %r -> %r" % (k, py_map[k]))
    for k in sorted(js_keys - py_keys):
        errors.append("Only in JS LEADERBOARD_STRATEGY_ALIASES: %r -> %r" % (k, js_map[k]))
    for k in sorted(py_keys & js_keys):
        if py_map[k] != js_map[k]:
            errors.append(
                "Value mismatch for %r: Python %r vs JS %r"
                % (k, py_map[k], js_map[k])
            )
    return len(errors) == 0, errors


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--template",
        type=Path,
        default=_REPO / "audit_dashboard" / "template.html",
    )
    ap.add_argument(
        "--index",
        type=Path,
        default=_REPO / "audit_dashboard" / "index.html",
        help="Built dashboard; LEADERBOARD_STRATEGY_ALIASES must match template.",
    )
    ap.add_argument(
        "--skip-index",
        action="store_true",
        help="Skip template vs index.html check (e.g. index not checked in yet).",
    )
    args = ap.parse_args()

    if not args.template.is_file():
        print("Missing template: %s" % args.template, file=sys.stderr)
        return 1

    html = args.template.read_text(encoding="utf-8", errors="replace")
    try:
        js_template = extract_js_leaderboard_aliases(html)
    except ValueError as e:
        print("ERROR: %s" % e, file=sys.stderr)
        return 1

    ok, errs = compare_maps(dict(STRATEGY_TRACK_ALIASES), js_template)
    if not ok:
        print("FAIL  Python vs template:", file=sys.stderr)
        for line in errs:
            print("  %s" % line, file=sys.stderr)
        return 1

    if not args.skip_index and args.index.is_file():
        idx_html = args.index.read_text(encoding="utf-8", errors="replace")
        try:
            js_index = extract_js_leaderboard_aliases(idx_html)
        except ValueError as e:
            print("ERROR (index): %s" % e, file=sys.stderr)
            return 1
        ok_i, errs_i = compare_maps(js_template, js_index)
        if not ok_i:
            print("FAIL  template vs index.html LEADERBOARD_STRATEGY_ALIASES:", file=sys.stderr)
            for line in errs_i:
                print("  %s" % line, file=sys.stderr)
            return 1
    elif not args.skip_index and not args.index.is_file():
        print("WARN index.html missing — skipped template/index parity (%s)" % args.index, file=sys.stderr)

    if args.skip_index:
        msg = "OK  STRATEGY_TRACK_ALIASES matches template (%d keys); index check skipped" % len(js_template)
    elif not args.index.is_file():
        msg = "OK  STRATEGY_TRACK_ALIASES matches template (%d keys); index missing" % len(js_template)
    else:
        msg = "OK  STRATEGY_TRACK_ALIASES matches template (%d keys); template matches index" % len(js_template)
    print(msg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
