#!/usr/bin/env python3
"""
HF-Grade Statistical Toolbox
=========================
Unified, asset-class-aware metrics engine for the Antigravity audit dashboard.
All metrics are computed from a list of pick dicts with fields:
  pnl_pct, closed_at, asset_class, symbol, strategy

Metrics computed:
  - Sharpe (annualized, per-trade)
  - Sortino (annualized, downside-dev-only)
  - Net Sharpe (after fees per trade)
  - VaR (95%, historical + parametric t-distribution)
  - CVaR / Expected Shortfall (95%, 99%)
  - Calmar Ratio
  - Max Drawdown (% equity) + duration (days)
  - Ulcer Index (William Hammer)
  - Rolling 30d/90d Sharpe, Sortino, MaxDD, CVaR (calendar-aligned windows)
  - Concept drift: two-sample KS test (early vs late window)
  - Per-asset-class breakdown

All rolling metrics use calendar-aligned windows.
VaR uses t-distribution (scipy) — accounts for fat tails in crypto.
Pure-Python fallback (Hill rational approx) when scipy unavailable.

Usage:
    python tools/hf_stats.py [--dashboard path/to/dashboard_data.json]
    from tools.hf_stats import compute_metrics, compute_rolling, compute_ac_metrics
"""
from __future__ import annotations

import argparse
import bisect
import json
import math
import statistics
import sys
from collections import defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

TRADING_DAYS = 252

_SCIPY = False
try:
    from scipy.stats import norm, t as t_dist
    _SCIPY = True
except ImportError:
    pass


def _float(x: Any) -> Optional[float]:
    try:
        if x is None:
            return None
        v = float(x)
        return None if v != v else v
    except (TypeError, ValueError):
        return None


def _parse_ts(raw: Any) -> Optional[float]:
    if not raw:
        return None
    s = str(raw).strip()
    if not s:
        return None
    try:
        s = s.replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except ValueError:
        return None


def log_returns(prices: list[float]) -> list[float]:
    """Convert price series to log returns. Input: close prices. Output: log-returns."""
    if len(prices) < 2:
        return []
    return [math.log(prices[i] / prices[i - 1]) for i in range(1, len(prices))]


# ---------------------------------------------------------------------------
# VaR: parametric (t-distribution or normal)
# ---------------------------------------------------------------------------

def _z_quantile(p: float) -> float:
    if _SCIPY:
        return float(norm.ppf(p))
    p = max(1e-10, min(1.0 - 1e-10, p))
    if p < 0.5:
        return -_z_quantile(1.0 - p)
    q = 2.0 * (1.0 - p)
    t = math.sqrt(-2.0 * math.log(q))
    c0, c1, c2, c3 = 2.5050117, 0.802853, 0.010328, 0.000048
    d1, d2, d3, d4 = 1.433138, 0.050273, 0.003953, 2.90419
    num = ((c3 * t + c2) * t + c1) * t + c0
    den = ((d4 * t + d3) * t + d2) * t + d1 * t + 1.0
    return t - num / den


def _t_quantile(df: float, p: float) -> float:
    if _SCIPY:
        return float(t_dist.ppf(p, df))
    z = _z_quantile(p)
    df = max(4.0, df)
    n = df
    n2 = max(n - 2.0, 2.0)
    return z + (z**2 - 1.0) * z / (4.0 * n) + (z**3 - 3.0 * z) * z / (24.0 * n * n2)


# ---------------------------------------------------------------------------
# Core metrics (single window)
# ---------------------------------------------------------------------------

@dataclass
class HfMetrics:
    n: int = 0
    sharpe: Optional[float] = None
    sortino: Optional[float] = None
    net_sharpe: Optional[float] = None
    var_95: Optional[float] = None
    cvar_95: Optional[float] = None
    cvar_99: Optional[float] = None
    max_drawdown_pct: Optional[float] = None
    max_drawdown_days: Optional[int] = None
    calmar: Optional[float] = None
    ulcer_index: Optional[float] = None
    win_rate: Optional[float] = None
    profit_factor: Optional[float] = None
    mean_pnl: Optional[float] = None
    downside_dev: Optional[float] = None
    psr: Optional[float] = None
    var_t_df: Optional[float] = None


def compute_hf_metrics(pnls: list[float], fee_bps: float = 20.0, pnl_cap: float = 50.0) -> HfMetrics:
    """
    Compute all HF-grade metrics from a list of PnL percentages.

    Args:
        pnls: List of PnL% per trade (capped to ±pnl_cap to handle mixed
               per-trade and cumulative-series data)
        fee_bps: Fee/slippage cost in basis points (default 20bp = 0.20%)
        pnl_cap: Cap each PnL at this magnitude to prevent cumulative outliers
                from distorting per-trade metrics (default 50%)
    """
    # Detect series type: cumulative-series have extreme values,
    # per-trade series are bounded. Cap at ±50% to handle whichever.
    pnls_capped = [max(-50.0, min(50.0, p)) for p in pnls]
    m = HfMetrics(n=len(pnls_capped))

    if len(pnls_capped) < 2:
        return m

    mu = statistics.mean(pnls_capped)
    m.mean_pnl = mu

    wins = [x for x in pnls_capped if x > 0]
    losses = [x for x in pnls_capped if x < 0]
    m.win_rate = len(wins) / len(pnls_capped) if pnls_capped else None

    gross = sum(wins) if wins else 0.0
    gl = abs(sum(losses)) if losses else 0.0
    # All-wins case (gl == 0 and gross > 0) is reported as None rather than
    # float("inf"). Strict-JSON parsers (browsers fetching the GitHub-raw /
    # jsDelivr fallback mirrors of dashboard_data.json) reject the literal
    # `Infinity` token with `Unexpected token 'I'`. The "all wins" signal is
    # still recoverable from win_rate=1.0 with n>0 in any consumer that needs it.
    m.profit_factor = gross / gl if gl > 0 else None

    std = statistics.stdev(pnls_capped)
    downside = [x for x in pnls_capped if x < 0]
    dd = sum(x * x for x in downside) / len(pnls_capped) if downside else 0.0
    m.downside_dev = math.sqrt(dd) if dd > 0 else 0.0

    annual_mu = mu * TRADING_DAYS
    annual_std = std * math.sqrt(TRADING_DAYS)
    annual_downside = m.downside_dev * math.sqrt(TRADING_DAYS)

    m.sharpe = round(annual_mu / annual_std, 4) if annual_std > 0 else None
    m.sortino = round(annual_mu / annual_downside, 4) if annual_downside > 0 else None

    net_mu = mu - fee_bps / 10000.0  # fee_bps in bps (20bp = 0.20%)
    m.net_sharpe = round(net_mu * math.sqrt(TRADING_DAYS) / std, 4) if std > 0 else None

    total_ret = sum(pnls_capped)
    mdd, _ = _max_drawdown(pnls_capped)
    m.max_drawdown_pct = mdd
    m.calmar = round(total_ret / abs(mdd or 1.0), 4) if mdd else None

    m.var_95 = _compute_var95(pnls_capped)
    m.cvar_95 = _compute_cvar(pnls_capped, 0.95)
    m.cvar_99 = _compute_cvar(pnls_capped, 0.99)
    m.var_t_df = _fit_t_df(pnls_capped)
    if m.var_t_df is not None and m.var_t_df > 2 and m.var_95 is not None and std > 0:
        t_var = _t_quantile(m.var_t_df, 0.05) * std
        m.var_95 = round(t_var, 4)

    m.max_drawdown_days = _max_drawdown_days(pnls_capped)
    m.ulcer_index = _ulcer_index(pnls_capped)

    m.psr = _probabilistic_sharpe_ratio(pnls_capped, 0.0)

    return m


def _fit_t_df(pnls: list[float]) -> Optional[float]:
    """Fit t-distribution degrees of freedom via kurtosis."""
    if len(pnls) < 4:
        return None
    n = len(pnls)
    mu = statistics.mean(pnls)
    m2 = statistics.variance(pnls)
    m4 = sum((x - mu) ** 4 for x in pnls) / n
    k = m4 / m2**2 if m2 > 0 else 0
    df = max(4.0, 6.0 / (k - 3.0)) if k > 3 else None
    return df


def _compute_var95(pnls: list[float]) -> Optional[float]:
    """Historical VaR at 95% confidence (left tail)."""
    if len(pnls) < 2:
        return None
    sorted_pnls = sorted(pnls)
    idx = int(len(sorted_pnls) * 0.05)
    return round(sorted_pnls[max(0, min(idx, len(sorted_pnls) - 1))], 4)


def _compute_cvar(pnls: list[float], conf: float = 0.95) -> Optional[float]:
    """Historical CVaR / Expected Shortfall at given confidence."""
    if len(pnls) < 5:
        return None
    sorted_pnls = sorted(pnls)
    cutoff = max(1, int(len(sorted_pnls) * (1 - conf)))
    tail = sorted_pnls[:cutoff] if cutoff > 0 else sorted_pnls[:1]
    return round(sum(tail) / len(tail), 4) if tail else None


def _max_drawdown(pnls: list[float]) -> tuple[Optional[float], int]:
    """Peak-to-trough drawdown on cumulative PnL series.
    
    Input: per-trade PnL percentages (NOT cumulative PnL).
    E.g., [2.3, -1.5, 0.8, -3.2] means four individual trades.
    Returns max peak-to-trough drawdown as a positive %.
    """
    if not pnls:
        return None, 0
    cum = []
    running = 0.0
    peak = 0.0
    max_dd = 0.0
    for p in pnls:
        running += p
        if running > peak:
            peak = running
        dd = peak - running
        if dd > max_dd:
            max_dd = dd
    return round(max_dd, 4), 0


def _max_drawdown_days(pnls: list[float]) -> Optional[int]:
    """Days in longest drawdown (counting losing sub-sequence)."""
    if not pnls:
        return None
    max_streak = 0
    current = 0
    for p in pnls:
        if p < 0:
            current += 1
            max_streak = max(max_streak, current)
        else:
            current = 0
    return max_streak


def _ulcer_index(pnls: list[float]) -> Optional[float]:
    """Ulcer Index: RMS of drawdown from running peak (on per-trade PnL series).
    
    Works on per-trade returns: computes cumulative PnL from trade 1, tracks
    peak equity, and measures drawdown from peak at each step.
    Input: per-trade PnL percentages (NOT already-cumulative).
    """
    if len(pnls) < 2:
        return None
    running = 0.0
    peak = 0.0
    dd_squares = []
    for p in pnls:
        running += p
        if running > peak:
            peak = running
        dd = peak - running
        if dd > 0:
            dd_squares.append(dd**2)
    if not dd_squares:
        return 0.0
    return round(math.sqrt(sum(dd_squares) / len(dd_squares)), 4)


def _probabilistic_sharpe_ratio(pnls: list[float], target_sr: float = 0.0) -> Optional[float]:
    """Probabilistic Sharpe Ratio (Lo, 2002)."""
    if len(pnls) < 2:
        return None
    n = len(pnls)
    mu = statistics.mean(pnls)
    sigma = statistics.stdev(pnls)
    if sigma == 0:
        return None
    sr = mu / sigma
    skew = _skewness(pnls)
    kurt = _kurtosis(pnls)
    skew_correction = (skew * sr / 6.0) if skew is not None else 0.0
    kurt_correction = ((kurt - 1) * sr**2 / 24.0) if kurt is not None else 0.0
    adj_sr = sr - skew_correction - kurt_correction
    var_sr = (1.0 / (n - 1.0)) if n > 1 else 1.0
    psr = (adj_sr - target_sr) / math.sqrt(var_sr) if var_sr > 0 else None
    return round(psr, 4) if psr is not None else None


def _skewness(pnls: list[float]) -> Optional[float]:
    n = len(pnls)
    if n < 3:
        return None
    mu = statistics.mean(pnls)
    s = statistics.stdev(pnls)
    if s == 0:
        return None
    m3 = sum((x - mu) ** 3 for x in pnls) / n
    return round(m3 / s**3, 4)


def _kurtosis(pnls: list[float]) -> Optional[float]:
    n = len(pnls)
    if n < 4:
        return None
    mu = statistics.mean(pnls)
    s = statistics.stdev(pnls)
    if s == 0:
        return None
    m4 = sum((x - mu) ** 4 for x in pnls) / n
    return round(m4 / s**4 - 3.0, 4)


# ---------------------------------------------------------------------------
# Rolling metrics
# ---------------------------------------------------------------------------

@dataclass
class RollingMetrics:
    window_days: int = 0
    n_trades: int = 0
    sharpe: Optional[float] = None
    sortino: Optional[float] = None
    max_drawdown_pct: Optional[float] = None
    cvar_95: Optional[float] = None
    win_rate: Optional[float] = None
    end_date: Optional[str] = None


@dataclass
class ConceptDriftReport:
    ks_D: float = 0.0
    ks_critical_05: float = 0.0
    distribution_shift: bool = False
    early_n: int = 0
    late_n: int = 0
    var_ratio: float = 0.0
    drift_alert: bool = False


def compute_rolling_metrics(
    dated_pnls: list[tuple[float, float]], window_days: int = 30
) -> list[dict]:
    """
    Compute rolling metrics over time-ordered (ts, pnl_pct) pairs.
    window_days: size of each rolling window in calendar days.
    """
    if len(dated_pnls) < 4:
        return []

    by_date: dict[str, list[float]] = defaultdict(list)
    for ts, pnl in dated_pnls:
        d = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
        by_date[d].append(pnl)

    dates = sorted(by_date.keys())
    if not dates:
        return []

    start_ts = _parse_ts(dates[0]) or dated_pnls[0][0]
    end_ts = _parse_ts(dates[-1]) or dated_pnls[-1][0]
    total_days = (end_ts - start_ts) / 86400.0

    results: list[dict] = []
    for i in range(len(dates)):
        window_end_ts = _parse_ts(dates[i]) or (start_ts + i * 86400)
        window_start_ts = window_end_ts - window_days * 86400

        window_pnls: list[float] = []
        for d in dates[: i + 1]:
            d_ts = _parse_ts(d) or 0
            if d_ts >= window_start_ts and d_ts <= window_end_ts:
                window_pnls.extend(by_date[d])

        if len(window_pnls) < 5:
            continue

        m = compute_hf_metrics(window_pnls)
        results.append({
            "window_days": window_days,
            "end_date": dates[i],
            "n_trades": len(window_pnls),
            "sharpe": m.sharpe,
            "sortino": m.sortino,
            "net_sharpe": m.net_sharpe,
            "max_drawdown_pct": m.max_drawdown_pct,
            "cvar_95": m.cvar_95,
            "cvar_99": m.cvar_99,
            "win_rate": m.win_rate,
            "ulcer_index": m.ulcer_index,
        })

    return results


def compute_concept_drift(
    dated_pnls: list[tuple[float, float]], mode: str = "half"
) -> ConceptDriftReport:
    """
    Two-sample KS test: early window vs late window.
    Detects distribution shift in PnL outcomes.
    """
    n = len(dated_pnls)
    if n < 20:
        return ConceptDriftReport()

    pnls = [p for _, p in dated_pnls]
    if mode == "half":
        mid = n // 2
        early = pnls[:mid]
        late = pnls[mid:]
    else:
        q = n // 4
        early = pnls[:q]
        late = pnls[n - q:]

    ks_d = _ks_two_sample(early, late)
    ks_crit = 1.36 * math.sqrt((len(early) + len(late)) / (len(early) * len(late)))

    r = ConceptDriftReport(
        ks_D=round(ks_d, 6),
        ks_critical_05=round(ks_crit, 6),
        distribution_shift=ks_d > ks_crit,
        early_n=len(early),
        late_n=len(late),
        var_ratio=round(_variance_ratio(early, late), 4),
        drift_alert=ks_d > ks_crit or _variance_ratio(early, late) > 2.5 or _variance_ratio(early, late) < 0.4,
    )
    return r


def _ks_two_sample(x: list[float], y: list[float]) -> float:
    xs, ys = sorted(x), sorted(y)
    n, m = len(xs), len(ys)
    knots = sorted(set(xs + ys))
    best = 0.0
    for t in knots:
        fn = bisect.bisect_right(xs, t) / n
        gm = bisect.bisect_right(ys, t) / m
        best = max(best, abs(fn - gm))
    return best


def _variance_ratio(x: list[float], y: list[float]) -> float:
    vx = statistics.variance(x) if len(x) > 1 else 0.0
    vy = statistics.variance(y) if len(y) > 1 else 0.0
    return (vy + 1e-12) / (vx + 1e-12)


# ---------------------------------------------------------------------------
# Per-asset-class metrics
# ---------------------------------------------------------------------------

def compute_ac_metrics(picks: list[dict]) -> dict[str, dict]:
    """Compute HF metrics broken down by asset class."""
    by_ac: dict[str, list[float]] = defaultdict(list)
    for p in picks:
        pnl = _float(p.get("pnl_pct"))
        if pnl is not None:
            ac = str(p.get("asset_class") or "UNKNOWN").upper()
            by_ac[ac].append(pnl)

    results: dict[str, dict] = {}
    for ac, pnls in by_ac.items():
        if len(pnls) < 3:
            continue
        m = compute_hf_metrics(pnls)
        results[ac] = {
            "n": len(pnls),
            "sharpe": m.sharpe,
            "sortino": m.sortino,
            "net_sharpe": m.net_sharpe,
            "var_95": m.var_95,
            "cvar_95": m.cvar_95,
            "max_drawdown_pct": m.max_drawdown_pct,
            "calmar": m.calmar,
            "ulcer_index": m.ulcer_index,
            "win_rate": m.win_rate,
            "profit_factor": m.profit_factor,
        }
    return results


# ---------------------------------------------------------------------------
# Master compute function
# ---------------------------------------------------------------------------

def compute_metrics(
    picks: list[dict],
    window_days: int = 30,
    fee_bps: float = 20.0,
) -> dict[str, Any]:
    """
    Master entry point. Computes all HF metrics from a list of picks.
    Returns a dict ready to be merged into dashboard_data.json summary.
    """
    dated_pnls: list[tuple[float, float]] = []
    all_pnls: list[float] = []
    by_ac: dict[str, list[float]] = defaultdict(list)

    for p in picks:
        pnl = _float(p.get("pnl_pct"))
        if pnl is None:
            continue
        all_pnls.append(pnl)
        ts = _parse_ts(p.get("closed_at") or p.get("timestamp") or p.get("opened_at"))
        if ts is not None:
            dated_pnls.append((ts, pnl))
        ac = str(p.get("asset_class") or "UNKNOWN").upper()
        by_ac[ac].append(pnl)

    dated_pnls.sort(key=lambda r: r[0])

    m = compute_hf_metrics(all_pnls, fee_bps)
    rolling = compute_rolling_metrics(dated_pnls, window_days)
    drift = compute_concept_drift(dated_pnls, "half")
    ac_metrics = compute_ac_metrics(picks)

    return {
        "hf_metrics": {
            "n": m.n,
            "sharpe": m.sharpe,
            "sortino": m.sortino,
            "net_sharpe": m.net_sharpe,
            "var_95": m.var_95,
            "cvar_95": m.cvar_95,
            "cvar_99": m.cvar_99,
            "var_t_df": m.var_t_df,
            "max_drawdown_pct": m.max_drawdown_pct,
            "max_drawdown_days": m.max_drawdown_days,
            "calmar": m.calmar,
            "ulcer_index": m.ulcer_index,
            "win_rate": m.win_rate,
            "profit_factor": m.profit_factor,
            "mean_pnl": m.mean_pnl,
            "psr": m.psr,
        },
        "rolling_metrics": rolling[-14:] if len(rolling) >= 14 else rolling,
        "rolling_current": rolling[-1] if rolling else None,
        "concept_drift": asdict(drift),
        "by_asset_class": ac_metrics,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--dashboard", default="audit_dashboard/data/dashboard_data.json")
    ap.add_argument("--output", default="tools/data/hf_stats_summary.json")
    ap.add_argument("--window", type=int, default=30)
    ap.add_argument("--fees", type=float, default=20.0, help="Fee/slippage in bps (default 20)")
    args = ap.parse_args()

    repo = Path(__file__).resolve().parents[1]
    dash = repo / args.dashboard
    if not dash.is_file():
        print(f"ERROR: dashboard not found: {dash}")
        return 1

    with open(dash, encoding="utf-8") as f:
        data = json.load(f)

    picks = data.get("picks", {}).get("recent_closed") or []
    print(f"Computing HF metrics for {len(picks)} closed picks...")

    result = compute_metrics(picks, window_days=args.window, fee_bps=args.fees)
    result["generated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    result["source_picks"] = len(picks)

    out_path = repo / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, default=lambda x: None)
    print(f"Wrote {out_path}")

    hf = result["hf_metrics"]
    ac = result["by_asset_class"]
    roll = result["rolling_current"]
    drift = result["concept_drift"]

    print("\n=== HF Metrics ===")
    print(f"  N trades:          {hf['n']}")
    print(f"  Sharpe:           {hf['sharpe']}")
    print(f"  Sortino:          {hf['sortino']}")
    print(f"  Net Sharpe:       {hf['net_sharpe']}")
    print(f"  VaR 95%:          {hf['var_95']}%")
    print(f"  CVaR 95%:         {hf['cvar_95']}%")
    print(f"  CVaR 99%:         {hf['cvar_99']}%")
    print(f"  Max Drawdown:     {hf['max_drawdown_pct']}%")
    print(f"  Calmar:           {hf['calmar']}")
    print(f"  Ulcer Index:      {hf['ulcer_index']}")
    print(f"  Win Rate:         {hf['win_rate']:.1%}" if hf["win_rate"] else "  Win Rate:         n/a")
    print(f"  Profit Factor:    {hf['profit_factor']:.2f}" if hf["profit_factor"] else "  Profit Factor:    n/a")

    if roll:
        print(f"\n=== Rolling {args.window}d ===")
        print(f"  Date:             {roll['end_date']}")
        print(f"  Sharpe:           {roll['sharpe']}")
        print(f"  Sortino:          {roll['sortino']}")
        print(f"  Max Drawdown:     {roll['max_drawdown_pct']}%")
        print(f"  CVaR 95%:         {roll['cvar_95']}%")

    if ac:
        print("\n=== Per Asset Class ===")
        for ac_name, ac_m in sorted(ac.items()):
            pf = ac_m.get("profit_factor")
            pf_str = f"{pf:.2f}" if pf and pf != float("inf") else "inf"
            print(
                f"  {ac_name:<10} n={ac_m['n']:>4}  "
                f"SR={str(ac_m.get('sharpe') or 0)[:6]}  "
                f"PF={pf_str:<6}  "
                f"WR={ac_m.get('win_rate', 0):.0%}  "
                f"DD={str(ac_m.get('max_drawdown_pct') or 0)[:7]}%  "
                f"CVaR={ac_m.get('cvar_95') or 0:+.2f}%"
            )

    print("\n=== Concept Drift ===")
    print(f"  KS D-stat:        {drift['ks_D']:.4f}")
    print(f"  KS critical 5%:  {drift['ks_critical_05']:.4f}")
    print(f"  Distribution shift: {drift['distribution_shift']}")
    print(f"  Variance ratio:     {drift['var_ratio']:.4f}")
    print(f"  Drift alert:      {drift['drift_alert']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())