"""
Equity Tracker — live equity curve recording and risk metrics.

Records timestamped portfolio snapshots to data/equity_history.json
and computes drawdown, Sharpe, daily P&L, and streak metrics.

stdlib only. Safe to call from scanner.py after each scan cycle.
"""

import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Resolve data directory relative to this file
_THIS_DIR = Path(__file__).resolve().parent
DATA_DIR = _THIS_DIR / "data"

EQUITY_HISTORY_PATH = DATA_DIR / "equity_history.json"

PORTFOLIO_FILES = [
    "portfolio_1x.json",
    "portfolio_20x.json",
    "portfolio_copytrader.json",
]


def _load_json(path):
    """Load JSON file, return None on any error."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _safe_float(val, default=0.0):
    """Convert to float safely, handling None/NaN/Inf."""
    try:
        v = float(val)
        if math.isnan(v) or math.isinf(v):
            return default
        return v
    except (TypeError, ValueError):
        return default


def _load_equity_history():
    """Load existing equity history or return empty structure."""
    data = _load_json(EQUITY_HISTORY_PATH)
    if isinstance(data, dict) and "timestamps" in data and "equity" in data:
        return data
    return {
        "timestamps": [],
        "equity": [],
        "daily_pnl": [],
        "drawdown": [],
        "metadata": {
            "max_equity": 0.0,
            "max_drawdown_pct": 0.0,
            "current_streak": 0,
            "max_consecutive_losses": 0,
            "sharpe_ratio": None,
        },
    }


def _save_equity_history(data):
    """Atomically write equity history to disk."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp_path = EQUITY_HISTORY_PATH.with_suffix(".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    # Atomic rename (works on same filesystem)
    if sys.platform == "win32":
        # Windows: os.replace is atomic
        os.replace(str(tmp_path), str(EQUITY_HISTORY_PATH))
    else:
        os.replace(str(tmp_path), str(EQUITY_HISTORY_PATH))


def _compute_portfolio_equity():
    """
    Read all portfolio files and compute total equity.

    Total equity = sum of (current_balance + unrealized P&L from open positions)
    for each portfolio that exists.

    Returns (total_equity, portfolio_count) or (None, 0) if no portfolios found.
    """
    total_equity = 0.0
    portfolio_count = 0

    for pf_name in PORTFOLIO_FILES:
        pf_path = DATA_DIR / pf_name
        pf_data = _load_json(pf_path)
        if not isinstance(pf_data, dict):
            continue

        portfolio_count += 1
        balance = _safe_float(pf_data.get("current_balance", 0))

        # Sum unrealized P&L from open positions
        positions = pf_data.get("positions", {})
        unrealized_pnl = 0.0
        if isinstance(positions, dict):
            for _key, pos in positions.items():
                if isinstance(pos, dict):
                    unrealized_pnl += _safe_float(pos.get("current_pnl_usdt", 0))

        total_equity += balance + unrealized_pnl

    if portfolio_count == 0:
        return None, 0

    return total_equity, portfolio_count


def record_snapshot():
    """
    Record a single equity snapshot with timestamp.

    Reads portfolio state, computes equity, appends to history,
    and recalculates all derived metrics.

    Returns dict with current snapshot info, or None if no portfolios found.
    """
    equity, pf_count = _compute_portfolio_equity()
    if equity is None:
        return None

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    history = _load_equity_history()

    # Append new data point
    history["timestamps"].append(now)
    history["equity"].append(round(equity, 2))

    # Compute daily P&L (vs previous snapshot)
    if len(history["equity"]) >= 2:
        daily_pnl = round(history["equity"][-1] - history["equity"][-2], 2)
    else:
        daily_pnl = 0.0
    history["daily_pnl"].append(daily_pnl)

    # Compute drawdown from rolling max
    max_equity = max(history["equity"])
    if max_equity > 0:
        dd_pct = round((equity - max_equity) / max_equity * 100, 4)
    else:
        dd_pct = 0.0
    history["drawdown"].append(dd_pct)

    # Update metadata
    history["metadata"] = compute_metrics(history)

    _save_equity_history(history)

    return {
        "timestamp": now,
        "equity": round(equity, 2),
        "daily_pnl": daily_pnl,
        "drawdown_pct": dd_pct,
        "portfolios": pf_count,
        "total_snapshots": len(history["equity"]),
    }


def compute_metrics(history=None):
    """
    Compute risk/performance metrics from equity history.

    Args:
        history: equity history dict (loaded from file if None)

    Returns dict with:
        - max_equity: highest equity recorded
        - max_drawdown_pct: worst peak-to-trough drawdown (negative %)
        - current_streak: consecutive positive (>0) or negative (<0) P&L count
        - max_consecutive_losses: longest losing streak
        - sharpe_ratio: annualized Sharpe (if >= 5 data points, else None)
    """
    if history is None:
        history = _load_equity_history()

    equity_series = history.get("equity", [])
    pnl_series = history.get("daily_pnl", [])

    # Max equity
    max_eq = max(equity_series) if equity_series else 0.0

    # Max drawdown (worst value in drawdown series)
    dd_series = history.get("drawdown", [])
    max_dd = min(dd_series) if dd_series else 0.0

    # Current streak (positive = wins, negative = losses)
    current_streak = 0
    for pnl in reversed(pnl_series):
        if pnl > 0:
            if current_streak < 0:
                break
            current_streak += 1
        elif pnl < 0:
            if current_streak > 0:
                break
            current_streak -= 1
        else:
            break  # zero P&L breaks streak

    # Max consecutive losses
    max_consec_loss = 0
    consec_loss = 0
    for pnl in pnl_series:
        if pnl < 0:
            consec_loss += 1
            max_consec_loss = max(max_consec_loss, consec_loss)
        else:
            consec_loss = 0

    # Rolling Sharpe ratio (annualized, assuming ~48 snapshots/day at 30-min intervals)
    sharpe = None
    if len(pnl_series) >= 5:
        mean_pnl = sum(pnl_series) / len(pnl_series)
        variance = sum((p - mean_pnl) ** 2 for p in pnl_series) / len(pnl_series)
        std_pnl = math.sqrt(variance) if variance > 0 else 0
        if std_pnl > 0:
            # Annualize: 48 snapshots/day * 365 days
            annualization = math.sqrt(48 * 365)
            sharpe = round((mean_pnl / std_pnl) * annualization, 4)

    return {
        "max_equity": round(max_eq, 2),
        "max_drawdown_pct": round(max_dd, 4),
        "current_streak": current_streak,
        "max_consecutive_losses": max_consec_loss,
        "sharpe_ratio": sharpe,
    }


def print_summary(snapshot=None):
    """Print a human-readable summary of the current equity state."""
    history = _load_equity_history()
    metrics = compute_metrics(history)
    n = len(history.get("equity", []))

    print("=" * 50)
    print("  EQUITY TRACKER SUMMARY")
    print("=" * 50)

    if snapshot:
        print(f"  Equity:        ${snapshot['equity']:,.2f}")
        print(f"  Daily P&L:     ${snapshot['daily_pnl']:+,.2f}")
        print(f"  Drawdown:      {snapshot['drawdown_pct']:+.2f}%")
        print(f"  Portfolios:    {snapshot['portfolios']}")
    elif n > 0:
        print(f"  Latest Equity: ${history['equity'][-1]:,.2f}")
        print(f"  Latest P&L:    ${history['daily_pnl'][-1]:+,.2f}")
        print(f"  Drawdown:      {history['drawdown'][-1]:+.2f}%")

    print(f"  Snapshots:     {n}")
    print(f"  Max Equity:    ${metrics['max_equity']:,.2f}")
    print(f"  Max Drawdown:  {metrics['max_drawdown_pct']:+.2f}%")
    print(f"  Streak:        {metrics['current_streak']:+d}")
    print(f"  Max Consec Loss: {metrics['max_consecutive_losses']}")
    if metrics["sharpe_ratio"] is not None:
        print(f"  Sharpe Ratio:  {metrics['sharpe_ratio']:.4f}")
    else:
        print(f"  Sharpe Ratio:  N/A (need >= 5 snapshots)")
    print("=" * 50)


if __name__ == "__main__":
    snap = record_snapshot()
    if snap is None:
        print("No portfolio files found in", DATA_DIR)
        sys.exit(1)
    print_summary(snap)
