"""Risk metrics library — PSR, Sortino, and other quant-standard stats.

Standalone module (no external deps) that complements tools/skill_vs_luck_filter.py.
PR #300 added DSR; this adds:
  - Probabilistic Sharpe Ratio (PSR)       : simpler than DSR, no n_trials needed
  - Sortino                                : Sharpe using downside-only deviation
  - Calmar                                 : return / max drawdown
  - Max drawdown                           : largest peak-to-trough
  - Ulcer index                            : depth + duration of drawdown

All metrics operate on a list[float] of per-trade returns (percent units).
"""
from __future__ import annotations

import math
import statistics


def _safe_stdev(xs: list[float]) -> float:
    if len(xs) < 2:
        return 0.0
    try:
        return statistics.stdev(xs)
    except statistics.StatisticsError:
        return 0.0


def _normal_cdf(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def _skew_kurtosis(returns: list[float]) -> tuple[float, float]:
    n = len(returns)
    if n < 4:
        return 0.0, 0.0
    mu = sum(returns) / n
    sd = _safe_stdev(returns)
    if sd == 0.0:
        return 0.0, 0.0
    m3 = sum((x - mu) ** 3 for x in returns) / n
    m4 = sum((x - mu) ** 4 for x in returns) / n
    return m3 / (sd ** 3), m4 / (sd ** 4) - 3.0


def sortino(returns: list[float], target: float = 0.0) -> float:
    """Mean-excess-return / downside deviation.

    Downside deviation uses only returns below target. Better than Sharpe
    for strategies with positive skew (e.g. high TP:SL ratios — our
    forex_rsi2_mean_reversion with PF 3.71 but WR 28%).
    """
    n = len(returns)
    if n < 2:
        return 0.0
    mu = sum(returns) / n
    below = [(r - target) for r in returns if r < target]
    if not below:
        return 0.0
    downside_var = sum(x * x for x in below) / n
    if downside_var == 0.0:
        return 0.0
    return (mu - target) / math.sqrt(downside_var)


def probabilistic_sharpe_ratio(returns: list[float], target_sr: float = 0.0) -> float:
    """PSR (Bailey-Prado 2012): probability the TRUE Sharpe > target_sr.

    No n_trials parameter. Returns in [0, 1].
    """
    n = len(returns)
    if n < 4:
        return 0.0
    sd = _safe_stdev(returns)
    if sd == 0.0:
        return 0.0
    mu = sum(returns) / n
    sr = mu / sd
    skew, kurt = _skew_kurtosis(returns)
    denom_sq = 1.0 - skew * sr + (kurt - 1.0) / 4.0 * sr ** 2
    if denom_sq <= 0:
        denom_sq = 1.0 + 0.5 * sr ** 2  # i.i.d. Gaussian fallback
    z = (sr - target_sr) * math.sqrt(n - 1) / math.sqrt(denom_sq)
    return _normal_cdf(z)


def max_drawdown(returns: list[float]) -> dict:
    """Peak-to-trough drawdown on the cumulative return series.

    Returns {'max_drawdown_pct': float, 'peak_idx': int, 'trough_idx': int,
             'recovery_idx': int | None}.
    """
    if not returns:
        return {"max_drawdown_pct": 0.0, "peak_idx": None, "trough_idx": None, "recovery_idx": None}
    cum = []
    running = 0.0
    for r in returns:
        running += r
        cum.append(running)
    peak_so_far = cum[0]
    peak_idx = 0
    max_dd = 0.0
    dd_peak_idx = 0
    dd_trough_idx = 0
    for i, v in enumerate(cum):
        if v > peak_so_far:
            peak_so_far = v
            peak_idx = i
        dd = v - peak_so_far  # negative or zero
        if dd < max_dd:
            max_dd = dd
            dd_peak_idx = peak_idx
            dd_trough_idx = i
    # recovery: first index after trough where cum >= peak-so-far at trough
    peak_value = cum[dd_peak_idx]
    recovery = None
    for i in range(dd_trough_idx + 1, len(cum)):
        if cum[i] >= peak_value:
            recovery = i
            break
    return {
        "max_drawdown_pct": round(max_dd, 4),
        "peak_idx": dd_peak_idx,
        "trough_idx": dd_trough_idx,
        "recovery_idx": recovery,
        "recovered": recovery is not None,
    }


def calmar(returns: list[float]) -> float:
    """Calmar = cumulative return / abs(max drawdown).

    Hedge-fund-standard DD-adjusted return. Higher is better.
    """
    if not returns:
        return 0.0
    dd = max_drawdown(returns)["max_drawdown_pct"]
    if dd == 0.0:
        return 0.0
    return sum(returns) / abs(dd)


def ulcer_index(returns: list[float]) -> float:
    """Ulcer index: RMS of percent drawdown from running peak.

    Penalizes depth AND duration of drawdowns. Lower is better.
    """
    if not returns:
        return 0.0
    running = 0.0
    cum = []
    for r in returns:
        running += r
        cum.append(running)
    peak = cum[0]
    pct_dds = []
    for v in cum:
        if v > peak:
            peak = v
        if peak == 0:
            pct_dds.append(0.0)
        else:
            pct_dds.append((v - peak) / abs(peak) * 100.0 if abs(peak) > 0 else 0.0)
    rms = math.sqrt(sum(x * x for x in pct_dds) / len(pct_dds))
    return rms


def compute_all(returns: list[float], n_trials: int = 1, target_sr: float = 0.0) -> dict:
    """Aggregate risk metrics for a single return series."""
    if not returns:
        return {"n": 0}
    n = len(returns)
    mu = sum(returns) / n
    sd = _safe_stdev(returns)
    sr = (mu / sd) if sd > 0 else 0.0
    dd = max_drawdown(returns)
    return {
        "n": n,
        "mean_return_pct": round(mu, 4),
        "stdev_pct": round(sd, 4),
        "sharpe_per_trade": round(sr, 4),
        "sortino": round(sortino(returns), 4),
        "psr_vs_sr0": round(probabilistic_sharpe_ratio(returns, 0.0), 4),
        "psr_vs_sr_target": round(probabilistic_sharpe_ratio(returns, target_sr), 4),
        "calmar": round(calmar(returns), 4),
        "max_drawdown_pct": dd["max_drawdown_pct"],
        "recovered_from_dd": dd["recovered"],
        "ulcer_index_pct": round(ulcer_index(returns), 4),
        "cum_return_pct": round(sum(returns), 4),
    }


if __name__ == "__main__":
    import argparse
    import json
    from collections import defaultdict

    ap = argparse.ArgumentParser(description="Risk metrics for our strategies.")
    ap.add_argument("--dashboard", default="audit_trail/data/dashboard_payload.json")
    ap.add_argument("--group-by", choices=["strategy", "source_system", "asset_class"], default="asset_class")
    ap.add_argument("--min-n", type=int, default=20)
    args = ap.parse_args()

    dp = json.load(open(args.dashboard, "r", encoding="utf-8"))
    closed = [p for p in dp["picks"]["recent_closed"] if p.get("pnl_pct") is not None]

    bs = defaultdict(list)
    for p in closed:
        if args.group_by == "strategy":
            k = p.get("strategy") or p.get("source_system") or "unk"
        elif args.group_by == "source_system":
            k = p.get("source_system") or "unk"
        else:
            k = (p.get("asset_class") or "UNKNOWN").upper()
        bs[k].append(float(p["pnl_pct"]))

    out = {}
    for k, rs in bs.items():
        if len(rs) < args.min_n:
            continue
        out[k] = compute_all(rs)
    print(json.dumps(out, indent=2))
