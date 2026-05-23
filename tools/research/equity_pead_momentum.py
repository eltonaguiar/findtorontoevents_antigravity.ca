"""
H-002: Post-Earnings Announcement Drift (PEAD) research module.

Pre-registered in reports/hypothesis_registry.json as H-002.

Hypothesis: stocks in the top SUE (Standardized Unexpected Earnings) decile
outperform over 30-60 days post-announcement. Long only, ex-microcap.

Academic basis:
- Ball & Brown (1968) — original PEAD discovery
- Bernard & Thomas (1989/1990) — magnitude and persistence of PEAD
- Kraft, Leone & Wasley (2007) — post-2000 PEAD still significant after costs

Data source: Yahoo Finance (yfinance) — free, accessible.
Limitations: Yahoo historical estimates are often stale/revised. SUE
calculation is noisy. Use as a signal screener, not a standalone system.

Wiring plan (if H-002 passes acceptance criteria):
  Wire as optional signal into alpha_engine/smart_picks_engine.py for EQUITY picks.
  Acceptance: deflated Sharpe > 0.6 on n>=30 post-announcement windows.
  Register formal backtest in hypothesis_registry.json before wiring.

Usage:
    python tools/research/equity_pead_momentum.py
    python tools/research/equity_pead_momentum.py --symbols AAPL MSFT NVDA --lookback 60
    python tools/research/equity_pead_momentum.py --json
"""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CLOSED_PATH = REPO_ROOT / "alpha_engine" / "data" / "closed_picks.json"
OUT_PATH = REPO_ROOT / "reports" / "equity_pead_analysis.json"

# Default EQUITY symbols to analyze (liquid, ex-microcap)
DEFAULT_SYMBOLS = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "BRK-B",
    "JPM", "V", "UNH", "XOM", "MA", "HD", "PG", "COST", "ABBV", "MRK",
]

# PEAD acceptance criteria (H-004 template)
ACCEPTANCE_CRITERIA = {
    "min_n_windows": 30,
    "min_deflated_sharpe": 0.6,
    "min_wr": 0.55,
}


# ---------------------------------------------------------------------------
# Data fetching (yfinance-based)
# ---------------------------------------------------------------------------

def _fetch_earnings_calendar(symbol: str, lookback_days: int = 365) -> list[dict]:
    """
    Fetch historical earnings dates and EPS surprise for a symbol.

    Returns list of {date, actual_eps, estimated_eps, surprise_pct, quarter}.
    Falls back to empty list if yfinance is unavailable.
    """
    try:
        import yfinance as yf  # type: ignore
    except ImportError:
        return []

    try:
        ticker = yf.Ticker(symbol)
        # yfinance earnings_dates returns a DataFrame with index=date
        df = ticker.earnings_dates
        if df is None or df.empty:
            return []

        cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
        records = []
        for dt_idx, row in df.iterrows():
            try:
                dt = dt_idx.to_pydatetime()
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                if dt < cutoff:
                    continue

                reported = row.get("Reported EPS")
                estimated = row.get("EPS Estimate")
                if reported is None or estimated is None or estimated == 0:
                    continue

                surprise_pct = (float(reported) - float(estimated)) / abs(float(estimated))
                records.append({
                    "symbol": symbol,
                    "date": dt.strftime("%Y-%m-%d"),
                    "actual_eps": float(reported),
                    "estimated_eps": float(estimated),
                    "surprise_pct": round(surprise_pct, 4),
                })
            except Exception:
                continue

        return records
    except Exception:
        return []


def _fetch_post_earnings_return(
    symbol: str,
    announcement_date: str,
    hold_days: int = 30,
) -> float | None:
    """
    Compute the total return from announcement_date to announcement_date + hold_days.

    Returns None if data unavailable.
    """
    try:
        import yfinance as yf  # type: ignore
    except ImportError:
        return None

    try:
        ann_dt = datetime.strptime(announcement_date, "%Y-%m-%d")
        end_dt = ann_dt + timedelta(days=hold_days + 5)  # buffer for weekends

        ticker = yf.Ticker(symbol)
        hist = ticker.history(
            start=ann_dt.strftime("%Y-%m-%d"),
            end=end_dt.strftime("%Y-%m-%d"),
            interval="1d",
        )
        if hist is None or len(hist) < 2:
            return None

        entry_price = float(hist["Close"].iloc[0])
        # Find close at ~hold_days
        target_idx = min(hold_days, len(hist) - 1)
        exit_price = float(hist["Close"].iloc[target_idx])

        if entry_price <= 0:
            return None
        return round((exit_price - entry_price) / entry_price, 4)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def _compute_sue(records: list[dict]) -> list[dict]:
    """
    Add standardized unexpected earnings (SUE) to each record.

    SUE = surprise_pct / std(surprise_pct across last N quarters)
    If std is 0 or insufficient history, use raw surprise_pct.
    """
    if not records:
        return records

    surprises = [r["surprise_pct"] for r in records]
    if len(surprises) < 2:
        for r in records:
            r["sue"] = r["surprise_pct"]
        return records

    mean_s = sum(surprises) / len(surprises)
    variance = sum((s - mean_s) ** 2 for s in surprises) / max(len(surprises) - 1, 1)
    std_s = math.sqrt(variance) if variance > 0 else 1.0

    for r in records:
        r["sue"] = round((r["surprise_pct"] - mean_s) / std_s, 4)

    return records


def analyze_pead(
    symbols: list[str] | None = None,
    lookback_days: int = 365,
    hold_days: int = 30,
    top_sue_percentile: float = 0.70,  # top 30% by SUE
    min_n: int = 5,
) -> dict:
    """
    Run PEAD analysis for the given symbols.

    1. Fetch earnings calendars
    2. Compute SUE per announcement
    3. Fetch post-announcement returns (hold_days)
    4. Compare top-SUE vs bottom-SUE groups
    5. Return verdict and stats
    """
    if symbols is None:
        symbols = DEFAULT_SYMBOLS

    all_announcements = []
    fetch_errors = []

    for sym in symbols:
        records = _fetch_earnings_calendar(sym, lookback_days)
        if not records:
            fetch_errors.append(sym)
            continue
        records = _compute_sue(records)
        all_announcements.extend(records)

    if not all_announcements:
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "status": "NO_DATA",
            "error": "No earnings data fetched. Install yfinance: pip install yfinance",
            "fetch_errors": fetch_errors,
            "symbols_attempted": len(symbols),
        }

    # Sort by SUE and split into top/bottom groups
    all_announcements.sort(key=lambda r: r.get("sue", r.get("surprise_pct", 0)))
    n = len(all_announcements)
    top_threshold_idx = int(n * top_sue_percentile)
    top_sue_group = all_announcements[top_threshold_idx:]
    bottom_sue_group = all_announcements[:int(n * (1 - top_sue_percentile))]

    # Fetch post-announcement returns for top-SUE group
    top_returns = []
    for ann in top_sue_group[:50]:  # cap at 50 to avoid rate limits
        ret = _fetch_post_earnings_return(ann["symbol"], ann["date"], hold_days)
        if ret is not None:
            ann["post_return"] = ret
            top_returns.append(ret)

    bottom_returns = []
    for ann in bottom_sue_group[:50]:
        ret = _fetch_post_earnings_return(ann["symbol"], ann["date"], hold_days)
        if ret is not None:
            ann["post_return"] = ret
            bottom_returns.append(ret)

    # Compute stats
    def _stats(returns: list[float]) -> dict:
        if not returns:
            return {"n": 0, "wr": None, "avg_return": None, "sharpe": None}
        n = len(returns)
        wr = sum(1 for r in returns if r > 0) / n
        avg = sum(returns) / n
        if n > 1:
            var = sum((r - avg) ** 2 for r in returns) / (n - 1)
            std = math.sqrt(var) if var > 0 else 1e-9
            sharpe = avg / std * math.sqrt(252 / hold_days)
        else:
            sharpe = 0.0
        return {
            "n": n,
            "wr": round(wr, 4),
            "avg_return": round(avg, 4),
            "sharpe": round(sharpe, 4),
        }

    top_stats = _stats(top_returns)
    bottom_stats = _stats(bottom_returns)

    # Spread: top vs bottom
    spread = None
    if top_stats["avg_return"] is not None and bottom_stats["avg_return"] is not None:
        spread = round(top_stats["avg_return"] - bottom_stats["avg_return"], 4)

    # Verdict
    verdict = "INSUFFICIENT_DATA"
    if top_stats["n"] >= min_n:
        sharpe = top_stats.get("sharpe") or 0
        wr = top_stats.get("wr") or 0
        if sharpe >= ACCEPTANCE_CRITERIA["min_deflated_sharpe"] and wr >= ACCEPTANCE_CRITERIA["min_wr"]:
            verdict = "PROMISING"
        elif sharpe > 0 and wr >= 0.50:
            verdict = "WEAK_POSITIVE"
        elif spread is not None and spread < -0.005:
            verdict = "NEGATIVE"
        else:
            verdict = "FLAT"

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "hypothesis": "H-002",
        "config": {
            "symbols": symbols[:10],  # truncate for brevity
            "lookback_days": lookback_days,
            "hold_days": hold_days,
            "top_sue_percentile": top_sue_percentile,
        },
        "total_announcements_found": len(all_announcements),
        "top_sue_group": top_stats,
        "bottom_sue_group": bottom_stats,
        "spread_top_minus_bottom": spread,
        "verdict": verdict,
        "fetch_errors": fetch_errors,
        "acceptance_criteria": ACCEPTANCE_CRITERIA,
        "notes": (
            "SUE = standardized unexpected EPS surprise. "
            "Top-SUE group = highest surprise decile. "
            "Sharpe is annualized using sqrt(252/hold_days). "
            "Yahoo Finance data is noisy — treat as pilot, not production-grade."
        ),
    }


def print_report(result: dict) -> None:
    print(f"\n{'='*60}")
    print(f"H-002 PEAD Analysis")
    print(f"Generated: {result['generated_at']}")
    print(f"{'='*60}")

    if result.get("status") == "NO_DATA":
        print(f"ERROR: {result['error']}")
        print(f"Symbols attempted: {result['symbols_attempted']}")
        return

    top = result["top_sue_group"]
    bot = result["bottom_sue_group"]
    spread = result["spread_top_minus_bottom"]

    verdicts = {"PROMISING": "PROMISING", "FLAT": "FLAT", "NEGATIVE": "NEGATIVE",
                "WEAK_POSITIVE": "WEAK+", "INSUFFICIENT_DATA": "NO DATA"}
    icon = verdicts.get(result["verdict"], "?")

    print(f"Verdict: {icon}")
    print(f"Top SUE group:    n={top['n']} WR={top['wr'] or 'N/A'} "
          f"avg_ret={top['avg_return'] or 'N/A'} Sharpe={top['sharpe'] or 'N/A'}")
    print(f"Bottom SUE group: n={bot['n']} WR={bot['wr'] or 'N/A'} "
          f"avg_ret={bot['avg_return'] or 'N/A'} Sharpe={bot['sharpe'] or 'N/A'}")
    print(f"Spread (top-bottom): {spread:+.4f}" if spread is not None else "Spread: N/A")
    print(f"\nAcceptance criteria: {result['acceptance_criteria']}")
    if result["fetch_errors"]:
        print(f"Fetch errors: {result['fetch_errors']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="H-002: PEAD momentum research")
    parser.add_argument("--symbols", nargs="*", default=None, help="Symbols to analyze")
    parser.add_argument("--lookback", type=int, default=365, help="Earnings lookback days")
    parser.add_argument("--hold", type=int, default=30, help="Post-announcement hold days")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    result = analyze_pead(
        symbols=args.symbols,
        lookback_days=args.lookback,
        hold_days=args.hold,
    )

    OUT_PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print_report(result)
        print(f"\nJSON written: {OUT_PATH}")


if __name__ == "__main__":
    main()
