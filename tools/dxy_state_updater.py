"""DXY state updater — fetches DXY (US Dollar Index) and writes trend state.

Reads DX-Y.NYB from yfinance, computes 20-day SMA, and writes
alpha_engine/data/dxy_state.json with trend direction.

Trend logic:
  WEAK:    DXY close < SMA20 AND 5-day change < -0.5% (USD weakening)
  STRONG:  DXY close > SMA20 AND 5-day change > +0.5% (USD strengthening)
  NEUTRAL: otherwise

Run:
    python tools/dxy_state_updater.py [--dry-run]

Scheduled by: .github/workflows/dxy-state-update.yml (daily at 13:30 UTC = 9:30 AM ET)
"""
from __future__ import annotations

import argparse
import json
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = ROOT / "alpha_engine" / "data" / "dxy_state.json"


def compute_dxy_state() -> dict:
    import yfinance as yf
    import pandas as pd

    ticker = yf.Ticker("DX-Y.NYB")
    hist = ticker.history(period="40d")
    if hist.empty or len(hist) < 25:
        raise ValueError(f"Insufficient DXY data: {len(hist)} bars (need ≥25 for SMA20+5d)")

    close = hist["Close"]
    sma20 = close.rolling(20).mean()

    last_close = float(close.iloc[-1])
    last_sma20 = float(sma20.iloc[-1])
    change_5d_pct = float((close.iloc[-1] / close.iloc[-6] - 1) * 100) if len(close) >= 6 else 0.0

    # Trend classification
    if last_close < last_sma20 and change_5d_pct < -0.5:
        trend = "WEAK"
    elif last_close > last_sma20 and change_5d_pct > 0.5:
        trend = "STRONG"
    else:
        trend = "NEUTRAL"

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ticker": "DX-Y.NYB",
        "dxy_close": round(last_close, 4),
        "dxy_sma20": round(last_sma20, 4),
        "change_5d_pct": round(change_5d_pct, 3),
        "trend": trend,
        "methodology": "DXY close vs 20-day SMA + 5-day momentum. WEAK=below SMA20 and 5d<-0.5%, STRONG=above SMA20 and 5d>+0.5%, else NEUTRAL.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="DXY state updater")
    parser.add_argument("--dry-run", action="store_true", help="Print state without writing file")
    args = parser.parse_args()

    try:
        state = compute_dxy_state()
    except Exception as exc:
        print(f"[dxy-state-updater] ERROR: {exc}", file=sys.stderr)
        traceback.print_exc()
        return 1

    print(f"[dxy-state-updater] DXY={state['dxy_close']:.3f} SMA20={state['dxy_sma20']:.3f} "
          f"5d={state['change_5d_pct']:+.2f}% → trend={state['trend']}")

    if args.dry_run:
        print("[dxy-state-updater] DRY-RUN — not writing state file")
        print(json.dumps(state, indent=2))
        return 0

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")
    print(f"[dxy-state-updater] Wrote {OUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
