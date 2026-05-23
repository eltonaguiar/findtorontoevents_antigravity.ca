#!/usr/bin/env python3
"""
Run Hyro extended + Batch 2 backtest grids back-to-back (same symbols/months/risk).

From repo root:
  python tools/hyro_backtest_sweep.py
  python tools/hyro_backtest_sweep.py --symbols BTCUSDT ETHUSDT SOLUSDT AVAXUSDT BNBUSDT --months 6
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_PY = sys.executable


def main() -> None:
    p = argparse.ArgumentParser(description="Hyro extended + Batch2 full sweeps")
    p.add_argument(
        "--symbols",
        nargs="+",
        default=[
            "BTCUSDT",
            "ETHUSDT",
            "SOLUSDT",
            "AVAXUSDT",
            "BNBUSDT",
            "XRPUSDT",
            "ADAUSDT",
        ],
    )
    p.add_argument("--months", type=int, default=6)
    p.add_argument("--risk", type=float, default=0.75)
    args = p.parse_args()
    common = [
        "--symbols",
        *args.symbols,
        "--months",
        str(args.months),
        "--risk",
        str(args.risk),
        "--save",
    ]
    ext = [_PY, str(_ROOT / "tools" / "hyro_backtest_extended.py"), *common]
    b2 = [_PY, str(_ROOT / "tools" / "hyro_backtest_batch2.py"), *common]
    print("=== hyro_backtest_extended ===", flush=True)
    r1 = subprocess.call(ext, cwd=str(_ROOT))
    print("\n=== hyro_backtest_batch2 ===", flush=True)
    r2 = subprocess.call(b2, cwd=str(_ROOT))
    raise SystemExit(0 if r1 == 0 and r2 == 0 else 1)


if __name__ == "__main__":
    main()
