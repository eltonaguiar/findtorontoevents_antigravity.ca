"""
Risk & Regime Validation -- Criteria 4 & 5
==========================================
Proves: Max DD <30%, Calmar >1.0, profitable in both regimes.

Loads closed_picks.json, builds equity curve, computes risk metrics,
splits by regime and direction, and projects post-quality-gate performance.
"""

import json
import math
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from alpha_engine import config as _ae_config  # SSO for FOREX kill-switch

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
CLOSED_PICKS_PATH = os.path.join(DATA_DIR, "closed_picks.json")
INITIAL_CAPITAL = 10_000.0


# -- helpers ------------------------------------------------------------------

def _load_closed_picks():
    """Load and return closed picks sorted by exit date (earliest first)."""
    with open(CLOSED_PICKS_PATH, "r") as f:
        picks = json.load(f)
    # Sort by exit_date (then entry_date as tiebreaker)
    def sort_key(p):
        ed = p.get("exit_date") or p.get("entry_date") or "2099-01-01"
        ent = p.get("entry_date") or "2099-01-01"
        return (ed, ent)
    picks.sort(key=sort_key)
    return picks


def _safe_float(val, default=0.0):
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _parse_extra(pick):
    """Parse extra_json field into a dict."""
    raw = pick.get("extra_json", "{}")
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}


# -- Part 1: Risk metrics ----------------------------------------------------

def build_equity_curve(picks):
    """Build equity curve from sequential trades, return (equity_values, daily_returns)."""
    equity = INITIAL_CAPITAL
    curve = [equity]
    for p in picks:
        pnl_pct = _safe_float(p.get("pnl_pct"), 0.0)
        # pnl_pct is already fractional (e.g. -0.107 = -10.7%)
        # Apply PnL as fraction of current equity (position sizing is embedded)
        # Use a conservative 10% allocation per trade for equity curve
        allocation = 0.10
        equity *= (1.0 + pnl_pct * allocation)
        curve.append(equity)
    return curve


def compute_max_drawdown(curve):
    """Compute max drawdown as a percentage (positive number)."""
    peak = curve[0]
    max_dd = 0.0
    for val in curve:
        if val > peak:
            peak = val
        dd = (peak - val) / peak if peak > 0 else 0.0
        if dd > max_dd:
            max_dd = dd
    return max_dd * 100.0  # as percentage


def compute_daily_returns(curve):
    """Compute step-by-step returns from equity curve."""
    returns = []
    for i in range(1, len(curve)):
        if curve[i - 1] > 0:
            returns.append((curve[i] - curve[i - 1]) / curve[i - 1])
        else:
            returns.append(0.0)
    return returns


def compute_sharpe(returns, risk_free_annual=0.04):
    """Annualized Sharpe ratio. Treats each return as a 'period' (~1 trade)."""
    if len(returns) < 2:
        return 0.0
    mean_r = sum(returns) / len(returns)
    std_r = _std(returns)
    if std_r == 0:
        return 0.0
    # Annualize assuming ~250 trading periods per year (approximate)
    periods_per_year = min(250, len(returns))
    rf_per_period = risk_free_annual / periods_per_year
    sharpe = (mean_r - rf_per_period) / std_r * math.sqrt(periods_per_year)
    return sharpe


def compute_sortino(returns, risk_free_annual=0.04):
    """Annualized Sortino ratio (downside deviation only)."""
    if len(returns) < 2:
        return 0.0
    mean_r = sum(returns) / len(returns)
    downside = [r for r in returns if r < 0]
    if not downside:
        return float("inf") if mean_r > 0 else 0.0
    downside_std = _std(downside)
    if downside_std == 0:
        return 0.0
    periods_per_year = min(250, len(returns))
    rf_per_period = risk_free_annual / periods_per_year
    sortino = (mean_r - rf_per_period) / downside_std * math.sqrt(periods_per_year)
    return sortino


def _std(values):
    """Population standard deviation."""
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    return math.sqrt(variance)


def compute_calmar(curve, num_days=None):
    """Calmar ratio = annualized return / max drawdown."""
    if len(curve) < 2:
        return 0.0
    total_return = (curve[-1] - curve[0]) / curve[0]
    max_dd = compute_max_drawdown(curve) / 100.0  # as fraction
    if max_dd == 0:
        return float("inf") if total_return > 0 else 0.0
    # Estimate trading days from curve length or provided num_days
    if num_days is None or num_days <= 0:
        num_days = max(len(curve), 1)
    # Annualize
    years = max(num_days / 365.0, 0.01)
    annualized = (1 + total_return) ** (1.0 / years) - 1
    return annualized / max_dd


def compute_trade_stats(picks):
    """Compute win rate, profit factor, avg win/loss, streaks."""
    wins = []
    losses = []
    streak_w = 0
    streak_l = 0
    max_streak_w = 0
    max_streak_l = 0

    for p in picks:
        pnl = _safe_float(p.get("pnl_pct"), 0.0)
        status = p.get("status", "")
        if status == "WON" or pnl > 0:
            wins.append(pnl)
            streak_w += 1
            max_streak_l = max(max_streak_l, streak_l)
            streak_l = 0
        else:
            losses.append(pnl)
            streak_l += 1
            max_streak_w = max(max_streak_w, streak_w)
            streak_w = 0

    max_streak_w = max(max_streak_w, streak_w)
    max_streak_l = max(max_streak_l, streak_l)

    total = len(picks)
    win_rate = len(wins) / total * 100.0 if total else 0.0
    avg_win = sum(wins) / len(wins) * 100.0 if wins else 0.0
    avg_loss = sum(losses) / len(losses) * 100.0 if losses else 0.0
    gross_profit = sum(wins) if wins else 0.0
    gross_loss = abs(sum(losses)) if losses else 0.0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

    return {
        "total": total,
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": win_rate,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "profit_factor": profit_factor,
        "max_win_streak": max_streak_w,
        "max_loss_streak": max_streak_l,
    }


# -- Part 2: Regime classification -------------------------------------------

def classify_regime(pick):
    """Classify a trade's market regime at entry into bull/bear/choppy.

    Priority:
    1. regime_at_entry field (trending/ranging/transitional/backfill)
    2. extra_json sentinel_regime or regime_trend_direction
    3. extra_json sentinel_fng (Fear & Greed index)
    4. Default to 'unknown'
    """
    regime_raw = pick.get("regime_at_entry")
    extra = _parse_extra(pick)

    # Direct regime field
    if regime_raw and regime_raw != "backfill":
        if regime_raw == "trending":
            direction = extra.get("regime_trend_direction", "")
            if direction == "bearish":
                return "bear"
            return "bull"  # trending + bullish or unspecified
        elif regime_raw == "ranging":
            return "choppy"
        elif regime_raw == "transitional":
            return "choppy"

    # Sentinel regime from extra
    sentinel = extra.get("sentinel_regime", "")
    if sentinel:
        sentinel_upper = sentinel.upper()
        if sentinel_upper in ("ACCUMULATION", "MARKUP", "BULL"):
            return "bull"
        elif sentinel_upper in ("DISTRIBUTION", "MARKDOWN", "BEAR", "CRISIS"):
            return "bear"
        elif sentinel_upper in ("RANGING", "CHOPPY", "SIDEWAYS"):
            return "choppy"

    # Trend direction from extra
    trend_dir = extra.get("regime_trend_direction", "")
    if trend_dir == "bullish":
        return "bull"
    elif trend_dir == "bearish":
        return "bear"

    # Fear & Greed from extra
    fng = extra.get("sentinel_fng")
    if fng is not None:
        fng = _safe_float(fng, 50)
        if fng >= 55:
            return "bull"
        elif fng <= 30:
            return "bear"
        else:
            return "choppy"

    return "unknown"


def regime_analysis(picks):
    """Split picks by regime and compute stats for each."""
    buckets = defaultdict(list)
    for p in picks:
        regime = classify_regime(p)
        buckets[regime].append(p)

    results = {}
    for regime, rpicks in sorted(buckets.items()):
        stats = compute_trade_stats(rpicks)
        pnls = [_safe_float(p.get("pnl_pct"), 0.0) for p in rpicks]
        avg_pnl = sum(pnls) / len(pnls) * 100.0 if pnls else 0.0
        curve = build_equity_curve(rpicks)
        daily_ret = compute_daily_returns(curve)
        sharpe = compute_sharpe(daily_ret)
        results[regime] = {
            "count": len(rpicks),
            "win_rate": stats["win_rate"],
            "avg_pnl": avg_pnl,
            "sharpe": sharpe,
            "profit_factor": stats["profit_factor"],
            "positive_expectancy": avg_pnl > 0,
        }
    return results


# -- Part 3: Quality gate filter ---------------------------------------------

def apply_quality_gates(picks):
    """Filter picks through the quality gates:
    - confidence >= 0.70
    - NOT forex
    - NOT SELL in non-bearish regime
    - volume_ratio <= 5.0
    """
    filtered = []
    for p in picks:
        # Gate 1: confidence
        conf = _safe_float(p.get("confidence"), 0.0)
        if conf < 0.70:
            continue

        # Gate 2: no forex (lifted when FOREX_HARD_DISABLE=0)
        cat = (p.get("category") or "").lower()
        if cat == "forex" and _ae_config.FOREX_HARD_DISABLE:
            continue

        # Gate 3: no SELL in non-bearish regime
        sig = (p.get("signal_type") or "").upper()
        if sig == "SELL":
            regime = classify_regime(p)
            if regime != "bear":
                continue

        # Gate 4: volume_ratio <= 5.0 (None passes -- only reject extreme spikes)
        vr = p.get("volume_ratio")
        if vr is not None and _safe_float(vr, 0.0) > 5.0:
            continue

        filtered.append(p)
    return filtered


# -- Part 4: Direction analysis -----------------------------------------------

def direction_analysis(picks):
    """Split by BUY vs SELL, compute stats and P/L contribution."""
    buy_picks = [p for p in picks if (p.get("signal_type") or "").upper() == "BUY"]
    sell_picks = [p for p in picks if (p.get("signal_type") or "").upper() == "SELL"]

    buy_stats = compute_trade_stats(buy_picks) if buy_picks else None
    sell_stats = compute_trade_stats(sell_picks) if sell_picks else None

    buy_total_pnl = sum(_safe_float(p.get("pnl_pct"), 0.0) for p in buy_picks)
    sell_total_pnl = sum(_safe_float(p.get("pnl_pct"), 0.0) for p in sell_picks)
    total_pnl = buy_total_pnl + sell_total_pnl

    return {
        "buy": {
            "count": len(buy_picks),
            "stats": buy_stats,
            "total_pnl": buy_total_pnl * 100.0,
            "pct_of_total": (buy_total_pnl / total_pnl * 100.0) if total_pnl != 0 else 0.0,
        },
        "sell": {
            "count": len(sell_picks),
            "stats": sell_stats,
            "total_pnl": sell_total_pnl * 100.0,
            "pct_of_total": (sell_total_pnl / total_pnl * 100.0) if total_pnl != 0 else 0.0,
        },
    }


# -- Estimate calendar days span ---------------------------------------------

def _estimate_days_span(picks):
    """Estimate the number of calendar days the picks span."""
    dates = []
    for p in picks:
        for key in ("entry_date", "exit_date"):
            d = p.get(key)
            if d:
                try:
                    dates.append(datetime.strptime(d[:10], "%Y-%m-%d"))
                except ValueError:
                    pass
    if len(dates) < 2:
        return 30
    return max((max(dates) - min(dates)).days, 1)


# -- Report printer -----------------------------------------------------------

def _pass_fail(condition):
    return "PASS" if condition else "FAIL"


def print_report():
    """Run all analyses and print the full report."""
    picks = _load_closed_picks()
    if not picks:
        print("ERROR: No closed picks found.")
        sys.exit(1)

    print(f"\nLoaded {len(picks)} closed picks from {CLOSED_PICKS_PATH}\n")

    # -- Part 1: Risk Metrics ---------------------------------------------
    curve = build_equity_curve(picks)
    daily_ret = compute_daily_returns(curve)
    max_dd = compute_max_drawdown(curve)
    num_days = _estimate_days_span(picks)
    calmar = compute_calmar(curve, num_days)
    sharpe = compute_sharpe(daily_ret)
    sortino = compute_sortino(daily_ret)
    stats = compute_trade_stats(picks)
    total_return = (curve[-1] - curve[0]) / curve[0] * 100.0

    print("=" * 60)
    print("     RISK & REGIME VALIDATION REPORT")
    print("=" * 60)

    print("\nCRITERION 4: Risk Metrics")
    print("-" * 40)
    print(f"  Total trades:         {stats['total']}")
    print(f"  Total return:         {total_return:+.2f}%")
    print(f"  Final equity:         ${curve[-1]:,.2f} (from ${INITIAL_CAPITAL:,.2f})")
    print(f"  Max Drawdown:         {max_dd:.2f}% (target: <30%)  [{_pass_fail(max_dd < 30)}]")
    print(f"  Calmar Ratio:         {calmar:.2f} (target: >1.0)   [{_pass_fail(calmar > 1.0)}]")
    print(f"  Sharpe Ratio:         {sharpe:.2f}")
    print(f"  Sortino Ratio:        {sortino:.2f}")
    print(f"  Win Rate:             {stats['win_rate']:.1f}%")
    print(f"  Profit Factor:        {stats['profit_factor']:.2f}")
    print(f"  Avg Win:              {stats['avg_win']:+.2f}%")
    print(f"  Avg Loss:             {stats['avg_loss']:+.2f}%")
    print(f"  Max Win Streak:       {stats['max_win_streak']}")
    print(f"  Max Loss Streak:      {stats['max_loss_streak']}")
    print(f"  Trading days span:    ~{num_days}")

    c4_pass = max_dd < 30 and calmar > 1.0
    print(f"\n  >>> CRITERION 4 OVERALL: [{_pass_fail(c4_pass)}]")

    # -- Part 2: Regime Analysis ------------------------------------------
    print(f"\nCRITERION 5: Regime Analysis")
    print("-" * 40)

    regimes = regime_analysis(picks)
    bull_ok = False
    bear_ok = False

    for regime, data in sorted(regimes.items()):
        positive = data["positive_expectancy"]
        label = _pass_fail(positive) if regime in ("bull", "bear") else "INFO"
        pf_str = f"{data['profit_factor']:.2f}" if data["profit_factor"] != float("inf") else "inf"
        print(f"  {regime.capitalize():12s}: {data['count']:3d} trades | "
              f"{data['win_rate']:.1f}% WR | {data['avg_pnl']:+.2f}% avg PnL | "
              f"PF {pf_str} | Sharpe {data['sharpe']:.2f}  [{label}]")
        if regime == "bull" and positive:
            bull_ok = True
        if regime == "bear" and positive:
            bear_ok = True

    both_ok = bull_ok and bear_ok
    print(f"\n  Positive expectancy in bull?  [{_pass_fail(bull_ok)}]")
    print(f"  Positive expectancy in bear?  [{_pass_fail(bear_ok)}]")
    print(f"  >>> CRITERION 5 OVERALL: [{_pass_fail(both_ok)}]")

    # -- Part 3: Post-Gate Projection -------------------------------------
    print(f"\nPOST-QUALITY-GATE PROJECTION")
    print("-" * 40)

    gated = apply_quality_gates(picks)
    if gated:
        g_curve = build_equity_curve(gated)
        g_dd = compute_max_drawdown(g_curve)
        g_stats = compute_trade_stats(gated)
        g_ret = compute_daily_returns(g_curve)
        g_sharpe = compute_sharpe(g_ret)
        g_days = _estimate_days_span(gated)
        g_calmar = compute_calmar(g_curve, g_days)
        g_total_return = (g_curve[-1] - g_curve[0]) / g_curve[0] * 100.0

        print(f"  Picks surviving gates: {len(gated)} / {len(picks)} ({len(gated)/len(picks)*100:.1f}%)")
        print(f"  Gates applied: confidence>=0.70, no forex, no SELL in non-bear, vol_ratio<=5.0")
        print()
        print(f"  {'Metric':<24s} {'Before Gates':>14s} {'After Gates':>14s} {'Delta':>14s}")
        print(f"  {'-'*24} {'-'*14} {'-'*14} {'-'*14}")

        def _fmt(v, fmt=".1f"):
            return f"{v:{fmt}}"

        wr_delta = g_stats["win_rate"] - stats["win_rate"]
        dd_delta = g_dd - max_dd
        pf_before = f"{stats['profit_factor']:.2f}" if stats["profit_factor"] != float("inf") else "inf"
        pf_after = f"{g_stats['profit_factor']:.2f}" if g_stats["profit_factor"] != float("inf") else "inf"
        calmar_delta = g_calmar - calmar

        print(f"  {'Win Rate':<24s} {stats['win_rate']:>13.1f}% {g_stats['win_rate']:>13.1f}% {wr_delta:>+13.1f}%")
        print(f"  {'Max Drawdown':<24s} {max_dd:>13.2f}% {g_dd:>13.2f}% {dd_delta:>+13.2f}%")
        print(f"  {'Profit Factor':<24s} {pf_before:>14s} {pf_after:>14s}")
        print(f"  {'Sharpe Ratio':<24s} {sharpe:>14.2f} {g_sharpe:>14.2f} {g_sharpe-sharpe:>+14.2f}")
        print(f"  {'Calmar Ratio':<24s} {calmar:>14.2f} {g_calmar:>14.2f} {calmar_delta:>+14.2f}")
        print(f"  {'Total Return':<24s} {total_return:>13.2f}% {g_total_return:>13.2f}% {g_total_return-total_return:>+13.2f}%")
        print(f"  {'Avg Win':<24s} {stats['avg_win']:>13.2f}% {g_stats['avg_win']:>13.2f}% {g_stats['avg_win']-stats['avg_win']:>+13.2f}%")
        print(f"  {'Avg Loss':<24s} {stats['avg_loss']:>13.2f}% {g_stats['avg_loss']:>13.2f}% {g_stats['avg_loss']-stats['avg_loss']:>+13.2f}%")

        # Gated regime analysis
        print(f"\n  Post-gate regime breakdown:")
        g_regimes = regime_analysis(gated)
        for regime, data in sorted(g_regimes.items()):
            pf_str = f"{data['profit_factor']:.2f}" if data["profit_factor"] != float("inf") else "inf"
            print(f"    {regime.capitalize():12s}: {data['count']:3d} trades | "
                  f"{data['win_rate']:.1f}% WR | {data['avg_pnl']:+.2f}% avg PnL | PF {pf_str}")
    else:
        print("  WARNING: No picks survived the quality gates!")

    # -- Part 4: Direction Analysis ---------------------------------------
    print(f"\nDIRECTION ANALYSIS")
    print("-" * 40)

    dirs = direction_analysis(picks)
    for direction in ("buy", "sell"):
        d = dirs[direction]
        s = d["stats"]
        if s and d["count"] > 0:
            pf_str = f"{s['profit_factor']:.2f}" if s["profit_factor"] != float("inf") else "inf"
            print(f"  {direction.upper():<6s}: {d['count']:3d} trades | "
                  f"{s['win_rate']:.1f}% WR | {s['avg_win']:+.2f}% avg W | "
                  f"{s['avg_loss']:+.2f}% avg L | PF {pf_str}")
            print(f"          Total PnL contribution: {d['total_pnl']:+.2f}% ({d['pct_of_total']:.1f}% of total)")
        else:
            print(f"  {direction.upper():<6s}: 0 trades")

    # Post-gate direction
    if gated:
        print(f"\n  Post-gate direction analysis:")
        g_dirs = direction_analysis(gated)
        for direction in ("buy", "sell"):
            d = g_dirs[direction]
            s = d["stats"]
            if s and d["count"] > 0:
                pf_str = f"{s['profit_factor']:.2f}" if s["profit_factor"] != float("inf") else "inf"
                print(f"    {direction.upper():<6s}: {d['count']:3d} trades | "
                      f"{s['win_rate']:.1f}% WR | PF {pf_str} | "
                      f"{d['total_pnl']:+.2f}% total PnL ({d['pct_of_total']:.1f}%)")
            else:
                print(f"    {direction.upper():<6s}: 0 trades")

    print("\n" + "=" * 60)
    overall = c4_pass and both_ok
    print(f"  OVERALL VERDICT: [{_pass_fail(overall)}]")
    if overall:
        print("  Max DD <30%, Calmar >1.0, profitable in both bull & bear.")
    else:
        reasons = []
        if not c4_pass:
            reasons.append("Risk metrics below threshold")
        if not both_ok:
            missing = []
            if not bull_ok:
                missing.append("bull")
            if not bear_ok:
                missing.append("bear")
            reasons.append(f"Negative expectancy in: {', '.join(missing)}")
        print(f"  Issues: {'; '.join(reasons)}")
    print("=" * 60)

    return {
        "criterion_4_pass": c4_pass,
        "criterion_5_pass": both_ok,
        "max_drawdown": max_dd,
        "calmar": calmar,
        "sharpe": sharpe,
        "sortino": sortino,
        "win_rate": stats["win_rate"],
        "total_trades": stats["total"],
        "gated_trades": len(gated) if gated else 0,
    }


if __name__ == "__main__":
    print_report()