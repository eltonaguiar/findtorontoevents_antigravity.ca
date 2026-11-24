#!/usr/bin/env python3
"""Provenance lint for the fund report: every number in a table must exist in a
tracked source.

Why this exists
---------------
Three separate defects in this report were NOT arithmetic errors - they were
labelling and provenance errors:

  * `cagr_pct` (gross) read as `net_cagr_pct` (net) -> a false
    "non-deterministic CAGRs" bug report on my part
  * `merblend` documented as charging the fee when it charged nothing
  * a trailing DISTRIBUTION yield reported as "yield-to-maturity"

In all three the maths was fine and the NAME attached to the number was wrong.
A human reading the table cannot catch that; comparing the table against the
payload mechanically can.

What it does
------------
Collects every numeric token from markdown table rows in the report, and checks
whether that number can be found in a source file (the generated payload, the
anchor snapshot). Numbers that appear in no source are printed with their line
number so they can be traced by hand.

Advisory by default; `--strict` exits 1 if anything is unsourced.

    python3 tools/fund_doc_lint.py
    python3 tools/fund_doc_lint.py --strict
"""
import argparse
import json
import pathlib
import re
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = REPO_ROOT / "docs" / "edge_research" / "FUNDS_WHAT_TO_BUY_2026-11-23_CORRECTED.md"
SOURCES = [
    REPO_ROOT / "reports" / "fund_deep_dive.json",
    REPO_ROOT / "reports" / "fund_forward_anchors.json",
    REPO_ROOT / "reports" / "fund_glide_path.json",
    REPO_ROOT / "reports" / "fund_block_sensitivity.json",
    REPO_ROOT / "reports" / "fund_cad_view.json",
    REPO_ROOT / "reports" / "fund_withholding.json",
]

# numbers that legitimately have no JSON source: dates, plan item ids, spans,
# and explanatory arithmetic in prose. Kept deliberately narrow.
IGNORE_LINE = re.compile(
    r"(\b(19|20)\d\d\b"          # years / dates
    r"|Item \d|E\d|D\d|F\d|B\d|A\d"   # plan item references
    r"|US\$|\\$)"                # money amounts
)

NUM = re.compile(r"[-\u2212]?\d+(?:\.\d+)?")


def source_numbers():
    """Every numeric leaf in the sources, rounded to 1-3 dp, both signs."""
    vals = set()

    def walk(x):
        if isinstance(x, dict):
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
        elif isinstance(x, (int, float)) and not isinstance(x, bool):
            for dp in (1, 2, 3):
                vals.add(f"{abs(round(float(x), dp)):.{dp}f}")
            vals.add(str(int(x)) if float(x).is_integer() else f"{abs(float(x)):.4f}")
        elif isinstance(x, str):
            for m in NUM.findall(x):
                vals.add(m.lstrip("-\u2212"))

    missing = [p for p in SOURCES if not p.exists()]
    if missing:
        print("  WARNING: missing source(s): " + ", ".join(str(p.name) for p in missing))
    for p in SOURCES:
        if p.exists():
            walk(json.loads(p.read_text()))

    # Expense ratios are quoted in the doc as percentages but live in the tool's
    # config, not in any payload. Import them rather than transcribing.
    try:
        sys.path.insert(0, str(REPO_ROOT))
        from tools import fund_deep_dive as fd  # noqa: PLC0415
        for mer in fd.MER.values():
            pct = mer * 100.0
            for dp in (0, 1, 2, 3, 4):
                vals.add(f"{abs(pct):.{dp}f}")
    except Exception as exc:  # noqa: BLE001
        print(f"  WARNING: could not import MER table ({exc})")

    return vals


# labels that look numeric but are not measurements
LABEL = re.compile(
    r"(\d+/\d+)"        # 60/40, 90/10, 100/0 allocation labels
    r"|(\d+%\s*CI)"     # confidence level
    r"|(\(\d+d\))"      # quarterly (63d), monthly (21d)
    r"|(\d+\(k\))"      # 401(k)
    r"|(Item \d+)"
)


def _section_of(lines, idx):
    """Which top-level '## ' section a line belongs to (1-based line number)."""
    name = ""
    for j in range(idx - 1):
        line = lines[j]
        if line.startswith("## "):
            name = line[3:].strip()
    return name


def doc_table_numbers():
    """(line_no, token, line) for every number inside a markdown table row.

    Numbers inside an Errata section are historical by design: they quote the
    wrong figures on purpose, so they are not expected to be in a source.
    """
    lines = DOC.read_text().splitlines()
    out = []
    for i, line in enumerate(lines, 1):
        if not line.strip().startswith("|"):
            continue
        if IGNORE_LINE.search(line):
            continue
        section = _section_of(lines, i)
        if section.startswith("Errata"):
            continue
        scrubbed = LABEL.sub("", line)
        for tok in NUM.findall(scrubbed):
            out.append((i, tok.lstrip("-\u2212"), line.strip()[:90]))
    return out


def main(argv=None):
    global DOC
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--strict", action="store_true",
                    help="exit 1 if any table number has no source")
    ap.add_argument("--doc", default=str(DOC),
                    help="report to lint (defaults to the corrected fund report)")
    args = ap.parse_args(argv)
    DOC = pathlib.Path(args.doc)
    if not DOC.exists():
        print(f"  no report at {DOC}")
        return 2

    src = source_numbers()
    rows = doc_table_numbers()

    unsourced = []
    for line_no, tok, line in rows:
        # Compare at the token's OWN precision. Normalising up to coarser
        # roundings creates false matches: "99.99" becomes "100.0" at 1dp, and
        # 100.0 is a common portfolio weight in the payload.
        candidates = {tok}
        try:
            f = float(tok)
            dec = len(tok.split(".")[1]) if "." in tok else 0
            for dp in range(dec, 4):
                candidates.add(f"{f:.{dp}f}")
        except ValueError:
            pass
        if not (candidates & src):
            unsourced.append((line_no, tok, line))

    print(f"  table numbers checked : {len(rows)}")
    print(f"  distinct sources       : {len(src)}")
    print(f"  unsourced              : {len(unsourced)}")
    if unsourced:
        print("\n  Numbers in tables with no matching value in a tracked source:")
        seen = set()
        for line_no, tok, line in unsourced:
            key = (line_no, tok)
            if key in seen:
                continue
            seen.add(key)
            print(f"   line {line_no:>4}  {tok:>8}  | {line}")

    if args.strict and unsourced:
        print("\nFAIL: unsourced table numbers (trace or regenerate)")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
