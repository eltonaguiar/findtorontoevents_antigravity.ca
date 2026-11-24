#!/usr/bin/env python3
"""P0.0c — Point-in-time audit: scan Python files for look-ahead bias.

Scans for patterns that indicate future data usage in signal/feature generation:
  - .shift(-N) or .shift(-N) in non-training code
  - .pct_change(-N) or .pct_change(-N)
  - future_return, next_ret, lookahead variables in signal paths
  - .iloc[i+1:] or .iloc[i+1] (forward indexing)
  - COT data without lag correction
  - Earnings data without publication lag

Usage:
    python3 tools/point_in_time_audit.py
    python3 tools/point_in_time_audit.py --path alpha_engine/
    python3 tools/point_in_time_audit.py --json
    python3 tools/point_in_time_audit.py --report
"""
import argparse
import json
import re
import sys
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parent.parent

# Patterns that indicate potential look-ahead bias
PATTERNS = [
    (r"\.shift\(-\d+\)", "negative_shift", "Uses future data via .shift(-N)"),
    (r"\.pct_change\(-\d+\)", "negative_pct_change", "Uses future returns via .pct_change(-N)"),
    (r"future_return|next_ret|lookahead|look_ahead|look-ahead", "future_variable", "Variable name suggests future data usage"),
    (r"\.iloc\[\s*\w+\s*\+\s*\d+", "forward_index", "Forward indexing via .iloc[i+N]"),
    (r"shift\(-horizon\)|shift\(-target", "target_leak", "Target variable leaking into features"),
]

# Files/dirs to skip
SKIP_DIRS = {".venv", "node_modules", "__pycache__", ".git", "tests", "venv", ".worktrees"}
SKIP_FILES = {"conftest.py"}

# Training-only files where shift(-N) is expected (target variable creation)
TRAINING_FILES = {
    "mercury2/features.py",
    "mercury2/trainer.py",
    "alpha_engine/ml_engine_v2.py",
}

# Backtest-only files (look-ahead is expected in backtest simulation)
BACKTEST_PATTERNS = {"backtest", "backtester", "backtest_", "_backtest"}

# Pattern detection files (looking ahead is correct for finding pivots/divergence)
PATTERN_PATTERNS = {"pattern", "divergence", "pivot", "zigzag", "swing", "trendline",
                    "confluence", "ichimoku", "fib_"}

# Comment-only findings (not actual code issues)
COMMENT_KEYWORDS = {"look-ahead", "lookahead", "look_ahead", "no look-ahead", "prevent look-ahead",
                    "avoid look-ahead", "possible look-ahead", "look-ahead bias", "look-ahead risk",
                    "look-ahead leakage"}


def _classify_finding(finding: dict) -> str:
    """Classify a finding as TRAINING, PATTERN, BACKTEST, or SIGNAL."""
    fname = finding["file"]
    code = finding["code"].lower()
    pattern = finding["pattern"]

    # Comments are not issues
    if finding["is_comment"]:
        return "COMMENT"

    # Training files
    if fname in TRAINING_FILES:
        if "target" in pattern or "future_return" in code or "next_ret" in code:
            return "TRAINING"
        return "TRAINING"

    # Check if file is backtest-related
    basename = Path(fname).name.lower()
    if any(p in basename for p in BACKTEST_PATTERNS):
        return "BACKTEST"

    # Check if file is pattern detection
    if any(p in basename for p in PATTERN_PATTERNS):
        return "PATTERN"

    # Check if in incubator/baby_strategies
    if "incubator" in fname or "baby_strategies" in fname:
        return "INCUBATOR"

    # Check if in tools (not production signal path)
    if fname.startswith("tools/"):
        return "TOOL"

    # Everything else in alpha_engine is potentially production signal
    if fname.startswith("alpha_engine/"):
        # Check if it's a strategy file
        if "strateg" in basename:
            return "SIGNAL"
        # Check if it's a harness or test
        if "harness" in basename or "test" in basename:
            return "BACKTEST"
        # Default for alpha_engine production code
        return "SIGNAL"

    return "OTHER"


def scan_file(path: Path) -> list:
    """Scan a single file for look-ahead patterns."""
    try:
        text = path.read_text(errors="replace")
    except Exception:
        return []
    lines = text.splitlines()
    findings = []
    for i, line in enumerate(lines, 1):
        for pattern, tag, desc in PATTERNS:
            if re.search(pattern, line):
                rel = str(path.relative_to(ROOT))
                is_training = rel in TRAINING_FILES
                stripped = line.strip()
                is_comment = stripped.startswith("#") or stripped.startswith("//") or \
                    any(kw in stripped.lower() for kw in COMMENT_KEYWORDS)
                # Check if the pattern is in a string literal (docstring/comment)
                if '"' in stripped or "'" in stripped:
                    # Could be in a string — check if the pattern is inside quotes
                    pass
                findings.append({
                    "file": rel,
                    "line": i,
                    "pattern": tag,
                    "description": desc,
                    "code": stripped[:120],
                    "is_training": is_training,
                    "is_comment": is_comment,
                    "classification": _classify_finding({
                        "file": rel, "code": stripped, "pattern": tag,
                        "is_training": is_training, "is_comment": is_comment,
                    }),
                })
    return findings


def scan_directory(path: Path) -> list:
    """Scan all Python files in a directory."""
    findings = []
    for pyfile in path.rglob("*.py"):
        if any(part in SKIP_DIRS for part in pyfile.parts):
            continue
        if pyfile.name in SKIP_FILES:
            continue
        findings.extend(scan_file(pyfile))
    return findings


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", default=".", help="Directory to scan (default: repo root)")
    ap.add_argument("--json", action="store_true", help="Output as JSON")
    ap.add_argument("--report", action="store_true", help="Write report to reports/")
    args = ap.parse_args()

    scan_path = ROOT / args.path if args.path != "." else ROOT
    findings = scan_directory(scan_path)

    # Filter out comments and training-only
    prod_findings = [f for f in findings if f["classification"] not in ("COMMENT", "TRAINING")]

    # Group by classification
    by_class = defaultdict(list)
    for f in prod_findings:
        by_class[f["classification"]].append(f)

    # Group by file
    by_file = defaultdict(list)
    for f in prod_findings:
        by_file[f["file"]].append(f)

    if args.json:
        print(json.dumps({
            "total_findings": len(findings),
            "production_findings": len(prod_findings),
            "by_classification": {k: len(v) for k, v in by_class.items()},
            "by_file": {k: len(v) for k, v in by_file.items()},
            "findings": findings,
        }, indent=2))
        return

    print(f"Point-in-time audit: scanned {args.path}")
    print(f"Total findings: {len(findings)}")
    print(f"Production (non-training, non-comment): {len(prod_findings)}")
    print()
    print("=== BY CLASSIFICATION ===")
    for cls, fs in sorted(by_class.items(), key=lambda x: -len(x[1])):
        print(f"  {cls}: {len(fs)}")
    print()

    # SIGNAL findings are the most important
    signal_findings = by_class.get("SIGNAL", [])
    if signal_findings:
        print(f"=== SIGNAL FINDINGS ({len(signal_findings)}) — potential look-ahead in production ===")
        by_f = defaultdict(list)
        for f in signal_findings:
            by_f[f["file"]].append(f)
        for fname, fs in sorted(by_f.items()):
            print(f"\n  {fname} ({len(fs)}):")
            for f in fs:
                print(f"    L{f['line']}: [{f['pattern']}] {f['code']}")
        print()

    # Check for COT-related code
    print("=== COT LEAKAGE CHECK ===")
    cot_files = []
    for pyfile in scan_path.rglob("*.py"):
        if any(part in SKIP_DIRS for part in pyfile.parts):
            continue
        try:
            text = pyfile.read_text(errors="replace")
        except Exception:
            continue
        if "cot" in text.lower() or "commitment of traders" in text.lower():
            rel = str(pyfile.relative_to(ROOT))
            has_lag = "lag" in text.lower() or "shift(" in text or "publication" in text.lower()
            cot_files.append((rel, has_lag))
    if cot_files:
        for f, has_lag in cot_files:
            status = "has lag correction" if has_lag else "NO lag correction found"
            print(f"  {f}: {status}")
    else:
        print("  No COT-related files found.")

    # Check for earnings-related code without publication lag
    print("\n=== EARNINGS LEAKAGE CHECK ===")
    earnings_files = []
    for pyfile in scan_path.rglob("*.py"):
        if any(part in SKIP_DIRS for part in pyfile.parts):
            continue
        try:
            text = pyfile.read_text(errors="replace")
        except Exception:
            continue
        if "earnings" in text.lower() or "sue" in text.lower():
            rel = str(pyfile.relative_to(ROOT))
            has_lag = "lag" in text.lower() or "publication" in text.lower() or "report_date" in text.lower()
            earnings_files.append((rel, has_lag))
    if earnings_files:
        for f, has_lag in earnings_files:
            status = "has lag/pub-date handling" if has_lag else "NO lag/pub-date handling found"
            print(f"  {f}: {status}")
    else:
        print("  No earnings-related files found.")

    print("\n=== AUDIT COMPLETE ===")

    if args.report:
        report_path = ROOT / "reports" / "point_in_time_audit_report.json"
        report_path.parent.mkdir(exist_ok=True)
        report_path.write_text(json.dumps({
            "generated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
            "scan_path": str(scan_path),
            "total_findings": len(findings),
            "production_findings": len(prod_findings),
            "by_classification": {k: len(v) for k, v in by_class.items()},
            "by_file": {k: len(v) for k, v in by_file.items()},
            "signal_findings": [{"file": f["file"], "line": f["line"], "pattern": f["pattern"], "code": f["code"]} for f in signal_findings],
            "findings": findings,
        }, indent=2))
        print(f"Report written: {report_path}")


if __name__ == "__main__":
    main()
