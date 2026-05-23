#!/usr/bin/env python3
"""
ALPHA_ENGINE -- Drawdown Tracker
==================================
Computes max drawdown tracking per strategy and portfolio-level.

Tracks per strategy and portfolio:
  - Max drawdown % (peak to trough)
  - Max drawdown $ amount
  - Recovery time (number of trades to recover)
  - Current drawdown (distance from peak)
  - Longest losing streak
  - Max consecutive loss amount

Usage:
  from drawdown_tracker import (
      compute_all_drawdowns,
      get_strategy_drawdown,
      is_in_drawdown,
  )
"""

import json
import os
from datetime import datetime, timezone
from collections import defaultdict

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
CLOSED_PICKS_PATH = os.path.join(DATA_DIR, "closed_picks.json")
DRAWDOWN_REPORT_PATH = os.path.join(DATA_DIR, "drawdown_report.json")

STARTING_EQUITY = 10_000.0


def _load_closed_picks():
    """Load closed picks sorted by exit_date (chronological)."""
    if not os.path.exists(CLOSED_PICKS_PATH):
        return []
    with open(CLOSED_PICKS_PATH, "r", encoding="utf-8") as f:
        picks = json.load(f)
    # Sort by exit_date then entry_date as tiebreaker
    picks.sort(key=lambda p: (p.get("exit_date", ""), p.get("entry_date", "")))
    return picks


def _compute_drawdown_metrics(picks, starting_equity=STARTING_EQUITY):
    """
    Compute drawdown metrics from an ordered list of picks.

    Returns dict with:
      - max_drawdown_pct, max_drawdown_dollar
      - recovery_trades (trades from max-dd trough back to peak; None if not recovered)
      - current_drawdown_pct, current_drawdown_dollar
      - longest_losing_streak, max_consecutive_loss_dollar
      - total_trades, total_pnl_pct, equity_final
    """
    if not picks:
        return {
            "max_drawdown_pct": 0.0,
            "max_drawdown_dollar": 0.0,
            "recovery_trades": 0,
            "current_drawdown_pct": 0.0,
            "current_drawdown_dollar": 0.0,
            "longest_losing_streak": 0,
            "max_consecutive_loss_dollar": 0.0,
            "total_trades": 0,
            "total_pnl_pct": 0.0,
            "equity_final": starting_equity,
        }

    equity = starting_equity
    peak_equity = starting_equity

    max_dd_pct = 0.0
    max_dd_dollar = 0.0

    # Track the trough index for recovery calculation
    max_dd_trough_idx = -1
    max_dd_peak_equity = starting_equity
    recovered_from_max_dd = True
    recovery_trades = 0

    # Losing streak tracking
    current_losing_streak = 0
    longest_losing_streak = 0
    current_consec_loss = 0.0
    max_consec_loss = 0.0

    total_pnl_pct = 0.0

    for i, pick in enumerate(picks):
        pnl_pct = pick.get("pnl_pct", 0.0) or 0.0
        total_pnl_pct += pnl_pct

        # Update equity: apply pnl_pct to current equity
        trade_pnl_dollar = equity * (pnl_pct / 100.0)
        equity += trade_pnl_dollar

        # Prevent equity going below zero
        if equity < 0:
            equity = 0.0

        # Update peak
        if equity >= peak_equity:
            peak_equity = equity

        # Compute current drawdown from peak
        if peak_equity > 0:
            dd_pct = ((peak_equity - equity) / peak_equity) * 100.0
            dd_dollar = peak_equity - equity
        else:
            dd_pct = 0.0
            dd_dollar = 0.0

        # Check if this is a new max drawdown
        if dd_pct > max_dd_pct:
            max_dd_pct = dd_pct
            max_dd_dollar = dd_dollar
            max_dd_trough_idx = i
            max_dd_peak_equity = peak_equity
            recovered_from_max_dd = False
            recovery_trades = 0

        # Track recovery from max drawdown
        if not recovered_from_max_dd and i > max_dd_trough_idx:
            recovery_trades += 1
            if equity >= max_dd_peak_equity:
                recovered_from_max_dd = True

        # Losing streak tracking
        is_loss = pnl_pct < 0
        if is_loss:
            current_losing_streak += 1
            current_consec_loss += abs(trade_pnl_dollar)
            if current_losing_streak > longest_losing_streak:
                longest_losing_streak = current_losing_streak
            if current_consec_loss > max_consec_loss:
                max_consec_loss = current_consec_loss
        else:
            current_losing_streak = 0
            current_consec_loss = 0.0

    # Current drawdown (distance from current peak)
    if peak_equity > 0:
        current_dd_pct = ((peak_equity - equity) / peak_equity) * 100.0
        current_dd_dollar = peak_equity - equity
    else:
        current_dd_pct = 0.0
        current_dd_dollar = 0.0

    return {
        "max_drawdown_pct": round(max_dd_pct, 4),
        "max_drawdown_dollar": round(max_dd_dollar, 2),
        "recovery_trades": recovery_trades if recovered_from_max_dd else None,
        "current_drawdown_pct": round(current_dd_pct, 4),
        "current_drawdown_dollar": round(current_dd_dollar, 2),
        "longest_losing_streak": longest_losing_streak,
        "max_consecutive_loss_dollar": round(max_consec_loss, 2),
        "total_trades": len(picks),
        "total_pnl_pct": round(total_pnl_pct, 4),
        "equity_final": round(equity, 2),
    }


def compute_all_drawdowns():
    """
    Compute drawdown metrics for every strategy and the portfolio overall.

    Returns dict: {
        "portfolio": {...metrics...},
        "per_strategy": {"strategy_name": {...metrics...}, ...},
        "computed_at": "ISO timestamp"
    }
    Also saves to drawdown_report.json.
    """
    picks = _load_closed_picks()

    # Group picks by strategy
    by_strategy = defaultdict(list)
    for pick in picks:
        strategy = pick.get("strategy", "unknown")
        by_strategy[strategy].append(pick)

    # Per-strategy drawdown
    per_strategy = {}
    for strategy_name, strategy_picks in sorted(by_strategy.items()):
        per_strategy[strategy_name] = _compute_drawdown_metrics(strategy_picks)

    # Portfolio-level drawdown (all picks combined, sorted chronologically)
    portfolio_metrics = _compute_drawdown_metrics(picks)

    report = {
        "portfolio": portfolio_metrics,
        "per_strategy": per_strategy,
        "strategy_count": len(per_strategy),
        "total_closed_picks": len(picks),
        "computed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    # Save report
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(DRAWDOWN_REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    return report


def get_strategy_drawdown(strategy_name):
    """
    Get drawdown metrics for a specific strategy.

    Returns dict with metrics, or None if strategy not found.
    Loads from cached report if available, otherwise computes fresh.
    """
    # Try cached report first
    if os.path.exists(DRAWDOWN_REPORT_PATH):
        with open(DRAWDOWN_REPORT_PATH, "r", encoding="utf-8") as f:
            report = json.load(f)
        per_strategy = report.get("per_strategy", {})
        if strategy_name in per_strategy:
            return per_strategy[strategy_name]

    # Recompute if not cached
    report = compute_all_drawdowns()
    return report.get("per_strategy", {}).get(strategy_name, None)


def is_in_drawdown(strategy_name, threshold=0.15):
    """
    Check if a strategy is currently in drawdown exceeding threshold.

    Args:
        strategy_name: Name of the strategy to check.
        threshold: Drawdown percentage threshold (0.15 = 15%).

    Returns:
        True if current drawdown exceeds threshold, False otherwise.
    """
    metrics = get_strategy_drawdown(strategy_name)
    if metrics is None:
        return False
    # current_drawdown_pct is stored as percentage (e.g., 15.0 for 15%)
    current_dd = metrics.get("current_drawdown_pct", 0.0)
    return current_dd > (threshold * 100.0)


if __name__ == "__main__":
    report = compute_all_drawdowns()
    print(f"Drawdown report computed for {report['strategy_count']} strategies, "
          f"{report['total_closed_picks']} closed picks.")
    print(f"Portfolio max drawdown: {report['portfolio']['max_drawdown_pct']:.2f}%")
    print(f"Saved to: {DRAWDOWN_REPORT_PATH}")
