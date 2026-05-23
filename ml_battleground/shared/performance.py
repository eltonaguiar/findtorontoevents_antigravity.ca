"""
Performance metrics for ML Battleground.
Sharpe, Sortino, Calmar, DSR, Monte Carlo, equity curve.
"""
import numpy as np
from scipy import stats
from typing import Optional


def sharpe_ratio(returns: list[float], risk_free: float = 0.0, annualize: float = 252.0) -> float:
    """Annualized Sharpe ratio."""
    if not returns or len(returns) < 2:
        return 0.0
    arr = np.array(returns)
    excess = arr - risk_free / annualize
    if np.std(excess) == 0:
        return 0.0
    return float(np.mean(excess) / np.std(excess) * np.sqrt(annualize))


def sortino_ratio(returns: list[float], risk_free: float = 0.0, annualize: float = 252.0) -> float:
    """Annualized Sortino ratio (downside deviation only)."""
    if not returns or len(returns) < 2:
        return 0.0
    arr = np.array(returns)
    excess = arr - risk_free / annualize
    downside = excess[excess < 0]
    if len(downside) == 0:
        return 10.0  # cap
    downside_std = np.std(downside)
    if downside_std == 0:
        return 10.0
    return float(np.mean(excess) / downside_std * np.sqrt(annualize))


def calmar_ratio(total_return: float, max_drawdown: float, years: float = 1.0) -> float:
    """Calmar ratio: annualized return / max drawdown."""
    if max_drawdown <= 0 or years <= 0:
        return 0.0
    annual_return = total_return / years
    return float(annual_return / max_drawdown)


def max_drawdown(equity_curve: list[float]) -> tuple[float, int]:
    """Returns (max_dd_fraction, duration_in_periods)."""
    if not equity_curve or len(equity_curve) < 2:
        return 0.0, 0
    arr = np.array(equity_curve)
    peak = np.maximum.accumulate(arr)
    dd = (peak - arr) / np.where(peak > 0, peak, 1)
    max_dd = float(np.max(dd))
    # Duration: longest streak below peak
    below_peak = dd > 0
    max_dur = 0
    cur_dur = 0
    for b in below_peak:
        if b:
            cur_dur += 1
            max_dur = max(max_dur, cur_dur)
        else:
            cur_dur = 0
    return max_dd, max_dur


def profit_factor(wins: list[float], losses: list[float]) -> float:
    """Sum of wins / abs(sum of losses)."""
    total_wins = sum(wins) if wins else 0
    total_losses = abs(sum(losses)) if losses else 0
    if total_losses == 0:
        return 10.0 if total_wins > 0 else 0.0
    return float(total_wins / total_losses)


def deflated_sharpe_ratio(
    observed_sharpe: float,
    n_trials: int,
    n_observations: int,
    skewness: float = 0.0,
    kurtosis: float = 3.0,
) -> float:
    """Bailey & Lopez de Prado (2014). Returns probability true Sharpe > 0."""
    if n_trials <= 1 or n_observations <= 1:
        return 0.5
    e_max_sharpe = np.sqrt(2 * np.log(n_trials)) * (1 - np.euler_gamma / (2 * np.log(n_trials)))
    se = np.sqrt((1 - skewness * observed_sharpe + (kurtosis - 1) / 4 * observed_sharpe ** 2) / (n_observations - 1))
    if se <= 0:
        return 0.5
    z = (observed_sharpe - e_max_sharpe) / se
    return float(stats.norm.cdf(z))


def monte_carlo_test(
    trade_pnls: list[float],
    n_permutations: int = 1000,
    metric: str = "sharpe",
) -> tuple[float, float]:
    """
    Permutation test. Returns (p_value, observed_metric).
    Shuffles trade order to test if sequence matters.
    """
    if not trade_pnls or len(trade_pnls) < 5:
        return 1.0, 0.0

    arr = np.array(trade_pnls)
    observed = sharpe_ratio(list(arr)) if metric == "sharpe" else float(np.mean(arr))

    count_better = 0
    rng = np.random.default_rng(42)
    for _ in range(n_permutations):
        shuffled = rng.permutation(arr)
        shuffled_metric = sharpe_ratio(list(shuffled)) if metric == "sharpe" else float(np.mean(shuffled))
        if shuffled_metric >= observed:
            count_better += 1

    p_value = (count_better + 1) / (n_permutations + 1)
    return float(p_value), float(observed)


def compute_institutional_metrics(closed_picks: list) -> dict:
    """
    Compute the full 8-check institutional validation metrics.
    Based on KIMI METHODOLOGY_AUDIT_TRAIL.md framework.

    The 8 checks:
    1. Sample Size >= 30 (minimum for statistical significance)
    2. Win Rate >= 50% (basic profitability)
    3. Statistical Significance: p-value < 0.05 (binomial test vs 50%)
    4. Sharpe Ratio >= 1.0 (risk-adjusted return)
    5. Profit Factor >= 1.3 (gross profit / gross loss)
    6. Max Drawdown <= 15% (capital preservation)
    7. Expectancy > 0 (expected value per trade)
    8. Calmar Ratio >= 1.0 (annual return / max drawdown)
    """
    metrics = {
        "sample_size": 0,
        "win_rate": 0.0,
        "p_value": 1.0,
        "sharpe_ratio": 0.0,
        "profit_factor": 0.0,
        "max_drawdown_pct": 0.0,
        "expectancy": 0.0,
        "calmar_ratio": 0.0,
        "checks_passed": 0,
        "total_checks": 8,
        "status": "COLLECTING",  # COLLECTING | TESTING | MARGINAL | PROVEN | ELITE
        "check_details": {},
    }

    if not closed_picks:
        return metrics

    # Extract P&L from closed picks
    pnls = []
    for p in closed_picks:
        pnl = p.get("net_pnl_pct", p.get("pnl_pct", p.get("gross_pnl_pct", p.get("unrealized_pnl_pct", 0))))
        if pnl is not None:
            pnls.append(float(pnl))

    n = len(pnls)
    metrics["sample_size"] = n

    if n == 0:
        return metrics

    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]

    # Check 1: Sample Size
    check1 = n >= 15
    metrics["check_details"]["sample_size"] = {"value": n, "threshold": 15, "passed": check1}

    # Check 2: Win Rate
    wr = len(wins) / n if n > 0 else 0
    metrics["win_rate"] = round(wr * 100, 2)
    check2 = wr >= 0.50
    metrics["check_details"]["win_rate"] = {"value": round(wr * 100, 2), "threshold": 50, "passed": check2}

    # Check 3: Statistical Significance (binomial test)
    # p-value: probability of observing this many wins or more by chance (vs 50%)
    from math import comb
    k = len(wins)
    p_value = sum(comb(n, i) * (0.5 ** n) for i in range(k, n + 1))
    metrics["p_value"] = round(p_value, 6)
    check3 = p_value < 0.05
    metrics["check_details"]["p_value"] = {"value": round(p_value, 6), "threshold": 0.05, "passed": check3}

    # Check 4: Sharpe Ratio
    pnl_arr = np.array(pnls)
    mean_ret = float(np.mean(pnl_arr))
    std_ret = float(np.std(pnl_arr, ddof=1)) if n > 1 else 1.0
    # Annualized assuming estimated trades per year from holding time
    trades_per_year = min(n * (365 * 24 / max(1, _estimate_holding_hours(closed_picks))), 730)
    inst_sharpe = (mean_ret / std_ret) * np.sqrt(trades_per_year) if std_ret > 0 else 0
    metrics["sharpe_ratio"] = round(float(inst_sharpe), 2)
    check4 = inst_sharpe >= 1.0
    metrics["check_details"]["sharpe_ratio"] = {"value": round(float(inst_sharpe), 2), "threshold": 1.0, "passed": check4}

    # Check 5: Profit Factor
    gross_profit = sum(wins) if wins else 0
    gross_loss = abs(sum(losses)) if losses else 1
    pf = gross_profit / gross_loss if gross_loss > 0 else 0
    metrics["profit_factor"] = round(pf, 2)
    check5 = pf >= 1.3
    metrics["check_details"]["profit_factor"] = {"value": round(pf, 2), "threshold": 1.3, "passed": check5}

    # Check 6: Max Drawdown
    equity = 10000.0
    peak = equity
    max_dd = 0.0
    for pnl in pnls:
        equity *= (1 + pnl / 100)
        peak = max(peak, equity)
        dd = (peak - equity) / peak * 100
        max_dd = max(max_dd, dd)
    metrics["max_drawdown_pct"] = round(max_dd, 2)
    check6 = max_dd <= 15.0
    metrics["check_details"]["max_drawdown"] = {"value": round(max_dd, 2), "threshold": 15.0, "passed": check6}

    # Check 7: Expectancy (average P&L per trade, must be positive)
    expectancy = mean_ret
    metrics["expectancy"] = round(expectancy, 4)
    check7 = expectancy > 0
    metrics["check_details"]["expectancy"] = {"value": round(expectancy, 4), "threshold": 0, "passed": check7}

    # Check 8: Calmar Ratio (annualized return / max drawdown)
    total_return = (equity / 10000 - 1) * 100
    # Annualize by calendar days, not trade count
    avg_hold_hours = _estimate_holding_hours(closed_picks)
    total_days = max(1, n * avg_hold_hours / 24)  # estimate calendar span from trades * avg hold
    annualized = total_return * (365 / total_days)
    calmar = annualized / max_dd if max_dd > 0 else 0
    metrics["calmar_ratio"] = round(calmar, 2)
    check8 = calmar >= 1.0
    metrics["check_details"]["calmar_ratio"] = {"value": round(calmar, 2), "threshold": 1.0, "passed": check8}

    # Count checks passed
    checks = [check1, check2, check3, check4, check5, check6, check7, check8]
    metrics["checks_passed"] = sum(checks)

    # Determine status
    passed = sum(checks)
    if n < 30:
        metrics["status"] = "COLLECTING"
    elif passed >= 7:
        metrics["status"] = "ELITE"
    elif passed >= 5:
        metrics["status"] = "PROVEN"
    elif passed >= 3:
        metrics["status"] = "MARGINAL"
    else:
        metrics["status"] = "TESTING"

    return metrics


def _estimate_holding_hours(picks: list) -> float:
    """Estimate average holding time in hours from closed picks."""
    from datetime import datetime
    durations = []
    for p in picks:
        opened = p.get("opened_at", p.get("timestamp", ""))
        closed = p.get("closed_at", p.get("closed_at_est", ""))
        if opened and closed:
            try:
                t_open = datetime.fromisoformat(opened.replace("Z", "+00:00"))
                t_close = datetime.fromisoformat(closed.replace("Z", "+00:00"))
                hours = (t_close - t_open).total_seconds() / 3600
                if hours > 0:
                    durations.append(hours)
            except Exception:
                pass
    return float(np.mean(durations)) if durations else 24.0


def compute_stats(closed_picks: list[dict]) -> dict:
    """Compute comprehensive stats from closed picks."""
    if not closed_picks:
        return {"trades": 0, "win_rate": 0, "sharpe": 0, "max_dd": 0, "pf": 0}

    pnls = [p.get("net_pnl_pct", float(p.get("pnl_pct", 0) or 0)) for p in closed_picks]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]

    equity = [10000.0]
    for pnl in pnls:
        equity.append(equity[-1] * (1 + pnl / 100))

    dd, dd_dur = max_drawdown(equity)

    return {
        "trades": len(closed_picks),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": len(wins) / len(closed_picks) if closed_picks else 0,
        "avg_win_pct": float(np.mean(wins)) if wins else 0,
        "avg_loss_pct": float(np.mean(losses)) if losses else 0,
        "total_pnl_pct": sum(pnls),
        "sharpe": sharpe_ratio(pnls),
        "sortino": sortino_ratio(pnls),
        "max_dd": dd,
        "max_dd_duration": dd_dur,
        "profit_factor": profit_factor(wins, losses),
        "expectancy": float(np.mean(pnls)) if pnls else 0,
        "equity_curve": equity,
    }
