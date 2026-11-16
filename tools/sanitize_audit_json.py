"""Force every audit data sidecar into strict JSON before it is published.

Why this exists
---------------
Python's `json` module emits bare `NaN` / `Infinity` / `-Infinity` by default.
Those are valid to `json.loads` but **fatal to the browser**: `JSON.parse` (and
`response.json()`) rejects the WHOLE document, so the panel renders "no data"
while the file returns HTTP 200 with a non-zero byte count. That is how the
Strategy-IC panel (`strategy_ic_analysis.json`, `"pf": Infinity`) and the
Money-Ready panel (`money_ready_verdict.json`, `"dsr_score": NaN`) died even
though both files parsed fine in Python. A leading UTF-8 BOM breaks `JSON.parse`
the same way.

`tools/deploy_audit_files.py` sanitizes the sidecars it uploads, but the hourly
`audit-dashboard.yml` deploy FTP-globs `audit_dashboard/data/*.json` straight to
the live site without going through that script. Anything a producer leaks
reaches production verbatim. This tool closes that gap.

Contract
--------
* A file that is already strict JSON is **never rewritten** — byte-identical, so
  running this over the data directory produces no diff.
* Non-finite floats become `null` (absent measurement), never a fake `0`.
* A leading BOM is stripped.
* An unparseable file is left untouched and reported (exit 1).

Usage
-----
    python3 tools/sanitize_audit_json.py                 # rewrite non-strict files
    python3 tools/sanitize_audit_json.py --report        # same, chatty for CI
    python3 tools/sanitize_audit_json.py --check         # exit 1 if any non-strict
    python3 tools/sanitize_audit_json.py path/a.json ... # explicit files
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DEFAULT_GLOB_DIR = REPO / "audit_dashboard" / "data"
BOM = b"\xef\xbb\xbf"


def _reject(tok: str):
    """json.loads hook: any non-finite literal means the file is not strict JSON."""
    raise ValueError(tok)


def _null_constant(_tok: str):
    """json.loads hook: map NaN/Infinity tokens to None instead of a float."""
    return None


def _dumps(data) -> str:
    return json.dumps(data, indent=2, allow_nan=False) + "\n"


def sanitize_file(path: Path) -> tuple[str, str | None]:
    """Return (status, detail) with status in clean|rewritten|broken."""
    try:
        raw = path.read_bytes()
    except OSError as e:
        return "broken", f"unreadable: {e}"
    has_bom = raw.startswith(BOM)
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as e:
        return "broken", f"not UTF-8: {e}"

    strict = True
    try:
        json.loads(text, parse_constant=_reject)
    except ValueError:
        strict = False
    except json.JSONDecodeError as e:
        # Truncated/garbage sidecar: rebuilding it would invent data. Leave it and
        # report loudly -- a 404-equivalent panel beats fabricated values.
        return "broken", f"unparseable JSON: {e}"

    if strict and not has_bom:
        return "clean", None

    try:
        data = json.loads(text, parse_constant=_null_constant)
        out = _dumps(data)
    except ValueError as e:  # pragma: no cover - defensive
        return "broken", f"could not sanitize: {e}"
    try:
        path.write_text(out, encoding="utf-8")  # utf-8 (no sig) drops the BOM
    except OSError as e:
        return "broken", f"unwritable: {e}"
    return "rewritten", "stripped UTF-8 BOM" if strict else "nulled non-finite tokens"


def _inspect(path: Path) -> tuple[str, str | None]:
    """Read-only twin of sanitize_file() for --check."""
    try:
        raw = path.read_bytes()
    except OSError as e:
        return "broken", f"unreadable: {e}"
    if raw.startswith(BOM):
        return "rewritten", "leading UTF-8 BOM"
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as e:
        return "broken", f"not UTF-8: {e}"
    try:
        json.loads(text, parse_constant=_reject)
    except ValueError as e:
        return "rewritten", f"non-strict token {e}"
    except json.JSONDecodeError as e:
        return "broken", f"unparseable JSON: {e}"
    return "clean", None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("paths", nargs="*", help="explicit JSON files (default: audit_dashboard/data/*.json)")
    ap.add_argument("--check", action="store_true", help="do not write; exit 1 if any file is non-strict")
    ap.add_argument("--report", action="store_true", help="print every file, not just problems")
    args = ap.parse_args()

    files = [Path(p) for p in args.paths] if args.paths else sorted(DEFAULT_GLOB_DIR.glob("*.json"))
    if not files:
        print(f"sanitize_audit_json: no files under {DEFAULT_GLOB_DIR}", file=sys.stderr)
        return 0

    counts = {"clean": 0, "rewritten": 0, "broken": 0}
    for f in files:
        status, detail = _inspect(f) if args.check else sanitize_file(f)
        counts[status] = counts.get(status, 0) + 1
        if status != "clean" or args.report:
            try:
                shown: str = str(f.relative_to(REPO))
            except ValueError:
                shown = str(f)
            print(f"  [{status}] {shown}{' — ' + detail if detail else ''}")

    verb = "non-strict" if args.check else "rewritten"
    print(
        f"sanitize_audit_json: {len(files)} files — "
        f"{counts['clean']} clean, {counts['rewritten']} {verb}, {counts['broken']} broken"
    )
    if counts["broken"]:
        return 1
    if args.check and counts["rewritten"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
