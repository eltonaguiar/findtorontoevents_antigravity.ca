"""
Anti-Overfit Validation — 8 Checks
====================================
Every strategy must pass ALL 8 checks before going live.
Based on walk-forward WindowResult data.
"""
import logging
import numpy as np
from typing import List, Tuple
from scipy import stats

from quan_engine import config
from quan_engine.backtest.walk_forward import WindowResult

logger = logging.getLogger("QuanEngine.AntiOverfit")


def check_all(windows: List[WindowResult], strategy_name: str) -> Tuple[bool, dict]:
    """Run all 8 anti-overfit checks. Returns (passed, details)."""
    results = {}
    all_pass = True

    checks = [
        ("oos_sharpe_ratio", check_oos_sharpe),
        ("oos_win_rate_tolerance", check_oos_win_rate),
        ("profit_factor_all_windows", check_profit_factor),
        ("max_consecutive_losses", check_max_consec_losses),
        ("max_drawdown", check_max_drawdown),
        ("max_single_trade", check_max_single_trade),
        ("ks_test_is_vs_oos", check_ks_distribution),
        ("profitable_windows", check_profitable_windows),
    ]

    for name, fn in checks:
        passed, detail = fn(windows)
        results[name] = {"passed": passed, "detail": detail}
        if not passed:
            all_pass = False
            logger.warning(f"[{strategy_name}] FAILED: {name} — {detail}")
        else:
            logger.info(f"[{strategy_name}] PASSED: {name}")

    return all_pass, results


def check_oos_sharpe(windows: List[WindowResult]) -> Tuple[bool, str]:
    """Check 1: OOS Sharpe ≥ 70% of IS Sharpe."""
    if not windows:
        return False, "No windows"

    for w in windows:
        if w.is_sharpe > 0 and w.oos_sharpe < w.is_sharpe * config.OOS_SHARPE_RATIO:
            return False, (
                f"Window {w.window_id}: OOS Sharpe {w.oos_sharpe:.2f} < "
                f"70% of IS Sharpe {w.is_sharpe:.2f} (threshold {w.is_sharpe * config.OOS_SHARPE_RATIO:.2f})"
            )

    avg_is = np.mean([w.is_sharpe for w in windows])
    avg_oos = np.mean([w.oos_sharpe for w in windows])
    return True, f"Avg IS Sharpe={avg_is:.2f}, Avg OOS Sharpe={avg_oos:.2f}"


def check_oos_win_rate(windows: List[WindowResult]) -> Tuple[bool, str]:
    """Check 2: OOS WR within 10pp of IS WR."""
    tolerance = config.OOS_WR_TOLERANCE_PP / 100

    for w in windows:
        diff = abs(w.oos_win_rate - w.is_win_rate)
        if diff > tolerance:
            return False, (
                f"Window {w.window_id}: |OOS WR {w.oos_win_rate:.1%} - "
                f"IS WR {w.is_win_rate:.1%}| = {diff:.1%} > {tolerance:.1%}"
            )

    return True, "All windows within tolerance"


def check_profit_factor(windows: List[WindowResult]) -> Tuple[bool, str]:
    """Check 3: Profit factor > 1.5 in all OOS windows."""
    for w in windows:
        if w.oos_profit_factor < config.MIN_PROFIT_FACTOR:
            return False, (
                f"Window {w.window_id}: OOS PF {w.oos_profit_factor:.2f} < "
                f"{config.MIN_PROFIT_FACTOR}"
            )

    avg_pf = np.mean([w.oos_profit_factor for w in windows])
    return True, f"Avg OOS PF={avg_pf:.2f}"


def check_max_consec_losses(windows: List[WindowResult]) -> Tuple[bool, str]:
    """Check 4: Max consecutive losses ≤ 5."""
    for w in windows:
        if w.oos_max_consecutive_losses > config.MAX_CONSECUTIVE_LOSSES:
            return False, (
                f"Window {w.window_id}: {w.oos_max_consecutive_losses} consecutive losses "
                f"> {config.MAX_CONSECUTIVE_LOSSES}"
            )

    return True, "All windows OK"


def check_max_drawdown(windows: List[WindowResult]) -> Tuple[bool, str]:
    """Check 5: Max drawdown ≤ 15%."""
    for w in windows:
        if w.oos_max_drawdown > config.MAX_DRAWDOWN_PCT:
            return False, (
                f"Window {w.window_id}: OOS DD {w.oos_max_drawdown:.1f}% > "
                f"{config.MAX_DRAWDOWN_PCT}%"
            )

    max_dd = max(w.oos_max_drawdown for w in windows)
    return True, f"Max OOS DD={max_dd:.1f}%"


def check_max_single_trade(windows: List[WindowResult]) -> Tuple[bool, str]:
    """Check 6: No single trade > 20% of total P&L."""
    for w in windows:
        if w.oos_max_single_trade_pct > config.MAX_SINGLE_TRADE_PNL_PCT:
            return False, (
                f"Window {w.window_id}: single trade = {w.oos_max_single_trade_pct:.1f}% "
                f"of total P&L > {config.MAX_SINGLE_TRADE_PNL_PCT}%"
            )

    return True, "No oversized trades"


def check_ks_distribution(windows: List[WindowResult]) -> Tuple[bool, str]:
    """Check 7: Win distribution passes KS test (IS vs OOS).

    We compare IS win rates and OOS win rates across windows.
    If the distributions are significantly different (p < 0.05),
    the strategy is likely overfit.
    """
    if len(windows) < 3:
        return True, "Too few windows for KS test (skipped)"

    is_wrs = [w.is_win_rate for w in windows]
    oos_wrs = [w.oos_win_rate for w in windows]

    statistic, p_value = stats.ks_2samp(is_wrs, oos_wrs)

    if p_value < 0.05:
        return False, f"KS test: p={p_value:.4f} < 0.05 (distributions differ)"

    return True, f"KS test: p={p_value:.4f} (distributions similar)"


def check_profitable_windows(windows: List[WindowResult]) -> Tuple[bool, str]:
    """Check 8: Strategy must be profitable in ≥ 4 of 6 rolling OOS windows."""
    profitable = sum(1 for w in windows if w.oos_profitable)
    total = len(windows)

    if total == 0:
        return False, "No windows"

    # Scale threshold proportionally if fewer than 6 windows
    required = min(config.MIN_PROFITABLE_WINDOWS, max(1, int(total * 0.67)))

    if profitable < required:
        return False, f"Only {profitable}/{total} windows profitable (need {required})"

    return True, f"{profitable}/{total} windows profitable"
