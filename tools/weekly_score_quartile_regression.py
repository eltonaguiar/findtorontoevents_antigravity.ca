#!/usr/bin/env python3
"""
Weekly drift check: runs tools/analyze_audit_scores_vs_pnl.py (score vs PnL on
closed picks). Intended for cron; review tools/data/score_pnl_analysis.json.

Optional: ``--with-weekly-report`` runs ``tools/generate_hf_weekly_audit_report.py``
afterward (HF action plan §6).

Exit code is the subprocess exit code from the analyzer (0 if script succeeds),
unless the report step fails when requested.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    ap = argparse.ArgumentParser(description="Weekly score–PnL drift + optional HF audit JSON")
    ap.add_argument(
        "--with-weekly-report",
        action="store_true",
        help="After analyzer, write alpha_engine/data/hf_weekly_audit_report.json",
    )
    args = ap.parse_args()

    script = ROOT / "tools" / "analyze_audit_scores_vs_pnl.py"
    if not script.is_file():
        print("weekly_score_quartile_regression: missing analyze_audit_scores_vs_pnl.py", file=sys.stderr)
        return 1
    r = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(ROOT),
    )
    print("weekly_score_quartile_regression: see tools/data/score_pnl_analysis.json")
    if r.returncode != 0:
        return r.returncode
    if args.with_weekly_report:
        rep = ROOT / "tools" / "generate_hf_weekly_audit_report.py"
        if not rep.is_file():
            print("weekly_score_quartile_regression: missing generate_hf_weekly_audit_report.py", file=sys.stderr)
            return 1
        r2 = subprocess.run([sys.executable, str(rep)], cwd=str(ROOT))
        if r2.returncode != 0:
            return r2.returncode
    return 0


if __name__ == "__main__":
    sys.exit(main())
