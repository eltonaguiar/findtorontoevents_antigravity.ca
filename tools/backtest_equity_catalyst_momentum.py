#!/usr/bin/env python3
"""
Rolling equity catalyst / momentum backtest (scaffold).

**Targets (when real OHLCV + earnings calendar are wired):** Sharpe >= 1.5,
win-rate >= 55%% on a 30-day rolling window.

This module does **not** fabricate prices or returns. Use --dry-run to verify CLI.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    ap = argparse.ArgumentParser(description="Equity catalyst momentum backtest (scaffold)")
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Print requirements and exit 0 without loading fabricated data",
    )
    ap.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        help="Future: directory of real OHLCV + calendar Parquet/CSV inputs",
    )
    args = ap.parse_args()
    if args.dry_run:
        print(
            "backtest_equity_catalyst_momentum: scaffold OK.\n"
            "Next: ingest Polygon/Yahoo equity bars + catalyst timestamps; "
            "emit rolling 30d metrics; compare to Sharpe>=1.5 / WR>=55%."
        )
        return 0
    if args.data_dir and args.data_dir.is_dir():
        print("Data dir provided but pipeline not implemented in this scaffold — use --dry-run.")
        return 2
    print("No --data-dir and not --dry-run: nothing to run.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
