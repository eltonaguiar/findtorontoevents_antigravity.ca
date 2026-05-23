#!/usr/bin/env python3
"""
===============================================================================
daily_pnl_builder.py
===============================================================================
Build REAL daily mark-to-market PnL return series for each strategy from the
resolved picks data.

Why this matters
----------------
The current pipeline computes Sharpe by treating each trade's pnl_pct as a
single observation, then annualizing by sqrt(trades_per_year). This inflates
Sharpe to absurd levels (10-148) because:

  - A trade held for 2 hours at +2% becomes: (0.02 / σ) × √(365×12) ≈ 50+
  - There's no concept of "time" between trades — gaps of days are ignored

This tool produces a proper DAILY return series per strategy:
    - Each trade's full pnl_pct attributed to its EXIT DAY only
    - Days with no exits = 0% return (opportunity cost of capital)
    - Each day's return = equal-weighted mean PnL of all exits that day
    - Sharpe = mean(daily_returns) / std(daily_returns) × √252
      →  realistic 0.5-3.0 (not inflated 10-148)
    - More conservative than spreading across hold days (avoids artificially
      smooth returns from uniform allocation)

Usage:
    python3 tools/daily_pnl_builder.py
    python3 tools/daily_pnl_builder.py --min-trades 30
    python3 tools/daily_pnl_builder.py --output reports/daily_pnl_series.json
===============================================================================
"""
import json
import logging
import sys
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DATA_PATH = ROOT / "audit_trail" / "data" / "universal_resolved_picks.json"
OUTPUT_DIR = ROOT / "reports"
DEFAULT_MIN_TRADES = 20

EXCLUDE_REASONS = {"TIME_EXIT"}
EXCLUDE_PNL_ABS_MAX = 100.0

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stderr,
)
log = logging.getLogger("daily_pnl_builder")


# ---------------------------------------------------------------------------
# Date parsing helpers
# ---------------------------------------------------------------------------

def _parse_date(s: str):
    """Parse ISO timestamp string to calendar date (timezone-naive)."""
    if not s:
        return None
    try:
        cleaned = s.replace("Z", "").replace("+00:00", "").strip()
        dt = datetime.fromisoformat(cleaned)
        return dt.date()
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Daily PnL construction
# ---------------------------------------------------------------------------

def build_daily_series(strategy_picks: list[dict], min_trades: int = DEFAULT_MIN_TRADES):
    """Build a daily return series for one strategy using exit-day attribution.

    Methodology
    -----------
    Each trade's full pnl_pct is recorded on its EXIT DAY only.
    Days with no exits get 0% return.
    Daily return = equal-weighted mean PnL of all exits that day.
    Sharpe = mean(daily_returns) / std(daily_returns) * sqrt(252).

    Parameters
    ----------
    strategy_picks : list[dict]
        All resolved picks for this strategy (pre-filtered).
    min_trades : int
        Minimum valid trades to build a series (default: 20).

    Returns
    -------
    dict or None
    """
    # Filter problematic picks
    valid = []
    for p in strategy_picks:
        reason = p.get("exit_reason", "")
        if reason in EXCLUDE_REASONS:
            continue
        pnl = p.get("pnl_pct")
        if pnl is None or abs(float(pnl)) >= EXCLUDE_PNL_ABS_MAX:
            continue

        ts = str(p.get("timestamp", "") or "")
        ra = str(p.get("resolved_at", "") or "")
        entry_date = _parse_date(ts)
        exit_date = _parse_date(ra)

        if entry_date is None or exit_date is None:
            continue
        if exit_date <= entry_date:
            continue

        valid.append({
            "entry_date": entry_date,
            "exit_date": exit_date,
            "pnl_pct": float(pnl),
        })

    if len(valid) < min_trades:
        return None

    # Date range across ALL valid picks
    all_dates = set()
    for v in valid:
        all_dates.add(v["entry_date"])
        all_dates.add(v["exit_date"])
    if not all_dates:
        return None

    min_date = min(all_dates)
    max_date = max(all_dates)
    total_days = (max_date - min_date).days + 1

    # Build daily timeline — exit-day attribution only
    daily_returns = []
    dates_list = []
    n_exits_per_day = []
    current_date = min_date

    while current_date <= max_date:
        dates_list.append(current_date.isoformat())

        # Picks that EXITED on this calendar day
        exits_today = [v for v in valid if v["exit_date"] == current_date]

        if not exits_today:
            daily_returns.append(0.0)
            n_exits_per_day.append(0)
        else:
            # Equal-weighted mean PnL of all picks exiting today
            pnls_today = [v["pnl_pct"] for v in exits_today]
            day_return = float(np.mean(pnls_today))
            daily_returns.append(day_return)
            n_exits_per_day.append(len(exits_today))

        current_date += timedelta(days=1)

    daily_arr = np.array(daily_returns, dtype=np.float64)

    # Metrics
    mean_daily = float(np.mean(daily_arr))
    std_daily = float(np.std(daily_arr, ddof=1))
    sharpe = (mean_daily / std_daily * np.sqrt(252)) if std_daily > 1e-10 else 0.0

    # Cumulative return (compounded)
    cum_ret = float(np.prod(1 + daily_arr / 100.0) - 1) * 100  # %

    # Max drawdown
    equity = np.cumprod(1 + daily_arr / 100.0)
    peak = np.maximum.accumulate(equity)
    dd = (equity - peak) / peak
    max_dd = float(dd.min())

    # Win rate on days with non-zero returns
    non_zero = daily_arr[daily_arr != 0]
    win_rate_days = float((non_zero > 0).mean()) if len(non_zero) > 0 else 0.0

    # Profit factor on daily returns
    wins = daily_arr[daily_arr > 0]
    losses = daily_arr[daily_arr < 0]
    pf = abs(wins.sum() / losses.sum()) if losses.sum() != 0 else (99.0 if wins.sum() > 0 else 0.0)

    # Avg hold days
    hold_days = [(v["exit_date"] - v["entry_date"]).days for v in valid]
    avg_hold = float(np.mean(hold_days)) if hold_days else 0.0

    return {
        "strategy": strategy_picks[0].get("strategy", "unknown"),
        "n_trades": len(valid),
        "n_days": total_days,
        "daily_returns": [round(x, 6) for x in daily_returns],
        "dates": dates_list,
        "n_exits_per_day": n_exits_per_day,
        "mean_daily_pnl_pct": round(mean_daily, 6),
        "std_daily_pnl_pct": round(std_daily, 6),
        "annualized_sharpe": round(sharpe, 4),
        "cumulative_return_pct": round(cum_ret, 4),
        "max_drawdown": round(max_dd, 4),
        "win_rate_days": round(win_rate_days, 4),
        "profit_factor_daily": round(pf, 4),
        "avg_hold_days": round(avg_hold, 2),
        "n_dates": len(dates_list),
        "n_nonzero_days": int((daily_arr != 0).sum()),
        "_note": (
            "Daily PnL series via EXIT-DAY attribution: each trade's full "
            "pnl_pct recorded on its exit day. Days with no exits = 0%. "
            "More conservative than spreading across hold days — produces "
            "realistic return variance."
        ),
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Build daily PnL series per strategy")
    parser.add_argument(
        "--min-trades", type=int, default=DEFAULT_MIN_TRADES,
        help=f"Minimum trades per strategy (default: {DEFAULT_MIN_TRADES})",
    )
    parser.add_argument(
        "--output", type=str, default="per_strategy_daily_pnl.json",
        help="Output JSON (default: per_strategy_daily_pnl.json)",
    )
    args = parser.parse_args()

    log.info("=" * 60)
    log.info("DAILY PnL SERIES BUILDER — exit-day attribution")
    log.info("=" * 60)

    # 1. Load data
    if not DATA_PATH.exists():
        log.error("File not found: %s", DATA_PATH)
        return

    picks = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    if not isinstance(picks, list):
        log.error("Expected list, got %s", type(picks).__name__)
        return
    log.info("Loaded %d resolved picks", len(picks))

    # 2. Group by strategy
    by_strategy = defaultdict(list)
    for p in picks:
        strategy = str(p.get("strategy", "unknown") or "unknown").strip()
        by_strategy[strategy].append(p)
    log.info("Found %d unique strategies", len(by_strategy))

    # 3. Build daily series for each strategy
    results = []
    skipped = 0
    for strategy, strategy_picks in sorted(
        by_strategy.items(), key=lambda x: len(x[1]), reverse=True
    ):
        log.info("Processing: %s (%d picks)", strategy, len(strategy_picks))
        series = build_daily_series(strategy_picks, min_trades=args.min_trades)
        if series is None:
            log.info("  Skipped (insufficient valid picks after filtering)")
            skipped += 1
            continue

        results.append(series)
        log.info(
            "  Trades=%d Days=%d NonZeroDays=%d Sharpe=%.2f CumRet=%.1f%% DD=%.2f%%",
            series["n_trades"], series["n_days"],
            series["n_nonzero_days"], series["annualized_sharpe"],
            series["cumulative_return_pct"], series["max_drawdown"] * 100,
        )

    log.info("")
    log.info("=" * 60)
    log.info("SUMMARY")
    log.info("=" * 60)
    log.info("Total strategies: %d", len(by_strategy))
    log.info("Built daily series: %d", len(results))
    log.info("Skipped (insufficient trades): %d", skipped)

    # 4. Sharpe distribution
    sharpes = [r["annualized_sharpe"] for r in results]
    if sharpes:
        sharpe_arr = np.array(sharpes)
        log.info("")
        log.info("Daily Sharpe distribution:")
        log.info("  Mean:   %.2f", sharpe_arr.mean())
        log.info("  Median: %.2f", float(np.median(sharpe_arr)))
        log.info("  Min:    %.2f", sharpe_arr.min())
        log.info("  Max:    %.2f", sharpe_arr.max())
        log.info("  Std:    %.2f", sharpe_arr.std(ddof=1))
        log.info("  Pct >= 1.0: %.1f%%", (sharpe_arr >= 1.0).mean() * 100)
        log.info("  Pct >= 2.0: %.1f%%", (sharpe_arr >= 2.0).mean() * 100)
        log.info("  Pct >= 3.0: %.1f%%", (sharpe_arr >= 3.0).mean() * 100)
        log.info("  Pct >= 5.0: %.1f%%", (sharpe_arr >= 5.0).mean() * 100)

    # 5. Top strategies
    log.info("")
    log.info("Top 10 by daily Sharpe:")
    for r in sorted(results, key=lambda x: x["annualized_sharpe"], reverse=True)[:10]:
        log.info(
            "  %-40s Sharpe=%6.2f Days=%d CumRet=%+.1f%% DD=%.2f%% HoldAvg=%.1fd",
            r["strategy"][:40], r["annualized_sharpe"],
            r["n_days"], r["cumulative_return_pct"],
            r["max_drawdown"] * 100, r["avg_hold_days"],
        )

    # 6. Save output
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / args.output

    full_report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_data": str(DATA_PATH),
        "method": (
            "exit-day attribution: each trade's full pnl_pct recorded on its "
            "exit day. Days with no exits = 0%. Equal-weighted mean across "
            "exits per day."
        ),
        "min_trades_threshold": args.min_trades,
        "n_total_picks": len(picks),
        "n_strategies_total": len(by_strategy),
        "n_strategies_built": len(results),
        "n_strategies_skipped": skipped,
        "sharpe_stats": {
            "mean": round(float(np.mean(sharpes)), 4) if sharpes else 0.0,
            "median": round(float(np.median(sharpes)), 4) if sharpes else 0.0,
            "min": round(float(np.min(sharpes)), 4) if sharpes else 0.0,
            "max": round(float(np.max(sharpes)), 4) if sharpes else 0.0,
            "n_above_1": int((np.array(sharpes) >= 1.0).sum()) if sharpes else 0,
            "n_above_2": int((np.array(sharpes) >= 2.0).sum()) if sharpes else 0,
            "n_above_3": int((np.array(sharpes) >= 3.0).sum()) if sharpes else 0,
        },
        "strategies": results,
    }

    out_path.write_text(
        json.dumps(full_report, indent=2, default=str), encoding="utf-8"
    )
    log.info("")
    log.info("Report written to: %s (%d bytes)", out_path, out_path.stat().st_size)
    log.info("=" * 60)
    log.info("Done")


if __name__ == "__main__":
    main()
