"""
Institutional-grade risk metrics for Alpha Engine.

Computes per-strategy AND system-wide:
  - Sortino Ratio (downside deviation, annualized)
  - Calmar Ratio (annualized return / max drawdown)
  - Realistic Sharpe (subtracts 0.1% per trade for slippage + fees)
  - Max Drawdown (peak-to-trough %)
  - Recovery Time (trades to recover from max DD)
  - Information Coefficient (correlation between predicted score and actual PnL)

Input:
  - alpha_engine/data/closed_picks.json

Output:
  - alpha_engine/data/institutional_metrics.json
"""

from __future__ import annotations

import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data"
CLOSED_PICKS_PATH = DATA_DIR / "closed_picks.json"
OUTPUT_PATH = DATA_DIR / "institutional_metrics.json"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SLIPPAGE_FEE_PER_TRADE_PCT = 0.1  # 0.1% round-trip cost per trade
ANNUALIZATION_FACTOR = math.sqrt(365)  # daily -> annual (crypto trades ~365 days/yr)
RISK_FREE_RATE_DAILY = 0.0  # assume 0 for crypto; adjust if needed


# ---------------------------------------------------------------------------
# Data Loading
# ---------------------------------------------------------------------------

def load_closed_picks(path: Path | None = None) -> list[dict]:
    """Load closed picks from JSON. Returns list of pick dicts."""
    p = path or CLOSED_PICKS_PATH
    if not p.exists():
        print(f"[institutional_metrics] WARNING: {p} not found")
        return []
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            print("[institutional_metrics] WARNING: closed_picks.json is not a list")
            return []
        return data
    except Exception as e:
        print(f"[institutional_metrics] ERROR loading closed picks: {e}")
        return []


def _filter_valid_picks(picks: list[dict]) -> list[dict]:
    """Keep only picks with a numeric pnl_pct and a known status."""
    valid = []
    for p in picks:
        pnl = p.get("pnl_pct")
        if pnl is None:
            continue
        try:
            float(pnl)
        except (TypeError, ValueError):
            continue
        if p.get("status") not in ("WON", "LOST"):
            continue
        valid.append(p)
    return valid


# ---------------------------------------------------------------------------
# Core Metric Computations
# ---------------------------------------------------------------------------

def _compute_max_drawdown(pnl_series: np.ndarray) -> tuple[float, int]:
    """Compute max drawdown (%) and recovery time (number of trades).

    Simulates an equity curve starting at 100, applying each trade's PnL
    sequentially, then finds the largest peak-to-trough decline.

    Returns:
        (max_drawdown_pct, recovery_trades)
        recovery_trades = number of trades from trough to full recovery (or
        trades-since-trough if not yet recovered).
    """
    if len(pnl_series) == 0:
        return 0.0, 0

    # Build equity curve
    equity = np.empty(len(pnl_series) + 1)
    equity[0] = 100.0
    for i, ret in enumerate(pnl_series):
        equity[i + 1] = equity[i] * (1.0 + ret / 100.0)

    # Running peak
    running_peak = np.maximum.accumulate(equity)
    drawdowns = (equity - running_peak) / np.where(running_peak != 0, running_peak, 1.0)

    max_dd_idx = int(np.argmin(drawdowns))
    max_dd_pct = abs(float(drawdowns[max_dd_idx]) * 100.0)

    # Recovery time: trades from trough until equity >= peak-at-trough
    peak_val = running_peak[max_dd_idx]
    recovery_trades = 0
    for j in range(max_dd_idx, len(equity)):
        if equity[j] >= peak_val:
            recovery_trades = j - max_dd_idx
            break
    else:
        # Not yet recovered
        recovery_trades = len(equity) - 1 - max_dd_idx

    return round(max_dd_pct, 4), recovery_trades


def _compute_sortino(pnl_series: np.ndarray) -> tuple[float, float]:
    """Compute Sortino ratio (per-trade and annualized).

    Sortino = (mean return - Rf) / downside deviation
    Downside deviation uses only negative returns.
    """
    if len(pnl_series) < 2:
        return 0.0, 0.0

    mean_ret = float(np.mean(pnl_series))
    downside = pnl_series[pnl_series < 0]
    if len(downside) == 0:
        # No losing trades -> infinite Sortino, cap at 99
        return 99.0, 99.0

    downside_dev = float(np.sqrt(np.mean(downside ** 2)))
    if downside_dev == 0:
        return 99.0, 99.0

    sortino = (mean_ret - RISK_FREE_RATE_DAILY) / downside_dev
    sortino_annual = sortino * ANNUALIZATION_FACTOR
    return round(sortino, 4), round(sortino_annual, 4)


def _compute_realistic_sharpe(pnl_series: np.ndarray) -> float:
    """Sharpe ratio after subtracting slippage + fees per trade.

    Each trade's return is reduced by SLIPPAGE_FEE_PER_TRADE_PCT before
    computing the standard Sharpe ratio.
    """
    if len(pnl_series) < 2:
        return 0.0

    adjusted = pnl_series - SLIPPAGE_FEE_PER_TRADE_PCT
    mean_adj = float(np.mean(adjusted))
    std_adj = float(np.std(adjusted, ddof=1))
    if std_adj == 0:
        return 0.0

    sharpe = mean_adj / std_adj
    sharpe_annual = sharpe * ANNUALIZATION_FACTOR
    return round(sharpe_annual, 4)


def _compute_calmar(pnl_series: np.ndarray, max_dd_pct: float) -> float:
    """Calmar ratio = annualized return / max drawdown.

    Annualized return estimated from cumulative return over trade count.
    """
    if max_dd_pct == 0 or len(pnl_series) == 0:
        return 0.0

    cumulative = float(np.sum(pnl_series))
    # Rough annualization: assume ~2 trades/day average
    trades_per_year = 365 * 2
    n = len(pnl_series)
    annualized_return = cumulative * (trades_per_year / n) if n > 0 else 0.0

    calmar = annualized_return / max_dd_pct
    return round(calmar, 4)


def _compute_information_coefficient(picks: list[dict]) -> float:
    """IC = Pearson correlation between predicted score and actual PnL.

    Uses ml_score or confidence as the predicted score.
    """
    scores = []
    pnls = []
    for p in picks:
        pnl = p.get("pnl_pct")
        # Prefer ml_score, fallback to confidence
        score = p.get("ml_score")
        if score is None:
            score = p.get("confidence")
        if score is None or pnl is None:
            continue
        try:
            scores.append(float(score))
            pnls.append(float(pnl))
        except (TypeError, ValueError):
            continue

    if len(scores) < 5:
        return 0.0

    scores_arr = np.array(scores)
    pnls_arr = np.array(pnls)

    # Pearson correlation
    s_std = np.std(scores_arr)
    p_std = np.std(pnls_arr)
    if s_std == 0 or p_std == 0:
        return 0.0

    corr = float(np.corrcoef(scores_arr, pnls_arr)[0, 1])
    if np.isnan(corr):
        return 0.0
    return round(corr, 4)


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def compute_metrics_for_group(picks: list[dict]) -> dict[str, Any]:
    """Compute all institutional metrics for a group of picks."""
    if not picks:
        return _empty_metrics()

    pnl_values = np.array([float(p["pnl_pct"]) for p in picks], dtype=np.float64)

    sortino, sortino_annual = _compute_sortino(pnl_values)
    max_dd, recovery_trades = _compute_max_drawdown(pnl_values)
    calmar = _compute_calmar(pnl_values, max_dd)
    realistic_sharpe = _compute_realistic_sharpe(pnl_values)
    ic = _compute_information_coefficient(picks)

    win_count = sum(1 for p in picks if p.get("status") == "WON")
    total = len(picks)

    return {
        "total_trades": total,
        "win_rate": round(win_count / total * 100, 2) if total > 0 else 0.0,
        "mean_pnl_pct": round(float(np.mean(pnl_values)), 4),
        "total_pnl_pct": round(float(np.sum(pnl_values)), 4),
        "sortino_ratio": sortino,
        "sortino_ratio_annual": sortino_annual,
        "calmar_ratio": calmar,
        "realistic_sharpe_annual": realistic_sharpe,
        "max_drawdown_pct": max_dd,
        "recovery_trades": recovery_trades,
        "information_coefficient": ic,
    }


def _empty_metrics() -> dict[str, Any]:
    """Return zeroed-out metrics dict."""
    return {
        "total_trades": 0,
        "win_rate": 0.0,
        "mean_pnl_pct": 0.0,
        "total_pnl_pct": 0.0,
        "sortino_ratio": 0.0,
        "sortino_ratio_annual": 0.0,
        "calmar_ratio": 0.0,
        "realistic_sharpe_annual": 0.0,
        "max_drawdown_pct": 0.0,
        "recovery_trades": 0,
        "information_coefficient": 0.0,
    }


# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------

def compute_institutional_metrics(closed_picks_path: Path | None = None) -> dict[str, Any]:
    """Compute all institutional metrics, save to JSON, return results.

    Can be imported and called from production_scanner.py:
        from institutional_metrics import compute_institutional_metrics
        metrics = compute_institutional_metrics()
    """
    picks = load_closed_picks(closed_picks_path)
    valid = _filter_valid_picks(picks)

    if not valid:
        print("[institutional_metrics] No valid closed picks found. Writing empty metrics.")
        result: dict[str, Any] = {
            "system": _empty_metrics(),
            "per_strategy": {},
            "computed_at": datetime.now(timezone.utc).isoformat(),
        }
        _save(result)
        return result

    print(f"[institutional_metrics] Computing metrics for {len(valid)} closed picks...")

    # System-wide metrics
    system_metrics = compute_metrics_for_group(valid)

    # Per-strategy metrics
    by_strategy: dict[str, list[dict]] = {}
    for p in valid:
        strat = p.get("strategy", "unknown")
        by_strategy.setdefault(strat, []).append(p)

    per_strategy: dict[str, dict] = {}
    for strat_name, strat_picks in sorted(by_strategy.items()):
        if len(strat_picks) < 2:
            # Need at least 2 trades for meaningful metrics
            m = _empty_metrics()
            m["total_trades"] = len(strat_picks)
            per_strategy[strat_name] = m
            continue
        per_strategy[strat_name] = compute_metrics_for_group(strat_picks)

    result = {
        "system": system_metrics,
        "per_strategy": per_strategy,
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }

    _save(result)

    # Console summary
    _print_summary(system_metrics, per_strategy)

    return result


def _save(data: dict) -> None:
    """Write metrics to JSON file."""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"[institutional_metrics] Saved to {OUTPUT_PATH}")


def _print_summary(system: dict, per_strategy: dict) -> None:
    """Print a concise console summary."""
    print()
    print("=" * 60)
    print("  INSTITUTIONAL METRICS SUMMARY")
    print("=" * 60)
    print(f"  Trades analyzed:        {system['total_trades']}")
    print(f"  Win Rate:               {system['win_rate']}%")
    print(f"  Mean PnL:               {system['mean_pnl_pct']}%")
    print(f"  Sortino (annual):       {system['sortino_ratio_annual']}")
    print(f"  Calmar Ratio:           {system['calmar_ratio']}")
    print(f"  Realistic Sharpe (ann): {system['realistic_sharpe_annual']}")
    print(f"  Max Drawdown:           {system['max_drawdown_pct']}%")
    print(f"  Recovery Trades:        {system['recovery_trades']}")
    print(f"  Information Coefficient: {system['information_coefficient']}")
    print("=" * 60)

    # Top 5 strategies by Sortino
    ranked = sorted(
        [(name, m) for name, m in per_strategy.items() if m["total_trades"] >= 5],
        key=lambda x: x[1]["sortino_ratio_annual"],
        reverse=True,
    )
    if ranked:
        print("\n  TOP 5 STRATEGIES (by Sortino, min 5 trades):")
        print(f"  {'Strategy':<35} {'Trades':>6} {'WR%':>6} {'Sortino':>8} {'Sharpe':>8} {'MaxDD':>7}")
        print("  " + "-" * 72)
        for name, m in ranked[:5]:
            print(
                f"  {name:<35} {m['total_trades']:>6} "
                f"{m['win_rate']:>5.1f}% {m['sortino_ratio_annual']:>8.3f} "
                f"{m['realistic_sharpe_annual']:>8.3f} {m['max_drawdown_pct']:>6.2f}%"
            )

    # Bottom 5 strategies by Sortino
    if ranked and len(ranked) > 5:
        print("\n  BOTTOM 5 STRATEGIES (by Sortino, min 5 trades):")
        print(f"  {'Strategy':<35} {'Trades':>6} {'WR%':>6} {'Sortino':>8} {'Sharpe':>8} {'MaxDD':>7}")
        print("  " + "-" * 72)
        for name, m in ranked[-5:]:
            print(
                f"  {name:<35} {m['total_trades']:>6} "
                f"{m['win_rate']:>5.1f}% {m['sortino_ratio_annual']:>8.3f} "
                f"{m['realistic_sharpe_annual']:>8.3f} {m['max_drawdown_pct']:>6.2f}%"
            )
    print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    """Module entry point for `from institutional_metrics import main` callers."""
    return compute_institutional_metrics()


if __name__ == "__main__":
    main()
