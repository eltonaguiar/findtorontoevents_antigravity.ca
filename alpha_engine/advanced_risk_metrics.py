#!/usr/bin/env python3
"""
Advanced Crypto Hedge Fund Risk Metrics Framework
==================================================
Computes 8 institutional-grade risk metrics from closed trade data
and produces an Institutional Readiness Score (0-100).

Metrics:
  1. Expected Shortfall (CVaR) at 95% and 99%
  2. Omega Ratio
  3. Gain-Loss Ratio
  4. Skewness of returns
  5. Kurtosis of returns
  6. Drawdown Duration (consecutive losing streak + time)
  7. Correlation Concentration (top 10 symbols)
  8. Regime Performance Split

Stdlib only. Windows UTF-8 safe.
"""

import json
import math
import os
import sys
from collections import defaultdict
from datetime import datetime

# ── Windows UTF-8 fix ────────────────────────────────────────────────
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
PAYLOAD_PATH = os.path.join(os.path.dirname(BASE_DIR), "audit_trail", "data", "dashboard_payload.json")
OUTPUT_PATH = os.path.join(DATA_DIR, "advanced_risk_metrics.json")


# ── Helpers ───────────────────────────────────────────────────────────

def _load_closed_picks():
    """Load closed picks from dashboard_payload.json -> picks.recent_closed."""
    with open(PAYLOAD_PATH, "r", encoding="utf-8") as f:
        payload = json.load(f)
    picks_section = payload.get("picks", payload)
    closed = picks_section.get("recent_closed", [])
    if not closed:
        print("[WARN] No closed picks found in dashboard_payload.json")
    return closed, payload.get("summary", {})


def _extract_returns(picks):
    """Extract pnl_pct values from closed picks, filtering nulls."""
    returns = []
    for p in picks:
        pnl = p.get("pnl_pct")
        if pnl is not None:
            returns.append(float(pnl))
    return returns


def _mean(values):
    if not values:
        return 0.0
    return sum(values) / len(values)


def _std(values, mean_val=None):
    if len(values) < 2:
        return 0.0
    m = mean_val if mean_val is not None else _mean(values)
    return math.sqrt(sum((x - m) ** 2 for x in values) / (len(values) - 1))


# ── Metric 1: Expected Shortfall (CVaR) ──────────────────────────────

def compute_cvar(returns, confidence=0.95):
    """Average loss beyond the VaR threshold."""
    if not returns:
        return {"VaR": 0.0, "CVaR": 0.0, "n_tail": 0}
    sorted_r = sorted(returns)
    n = len(sorted_r)
    cutoff_idx = int(math.floor(n * (1.0 - confidence)))
    if cutoff_idx < 1:
        cutoff_idx = 1
    tail = sorted_r[:cutoff_idx]
    var_val = sorted_r[cutoff_idx] if cutoff_idx < n else sorted_r[-1]
    cvar_val = _mean(tail) if tail else 0.0
    return {"VaR": round(var_val, 4), "CVaR": round(cvar_val, 4), "n_tail": len(tail)}


# ── Metric 2: Omega Ratio ────────────────────────────────────────────

def compute_omega(returns, threshold=0.0):
    """Sum of gains above threshold / sum of losses below threshold."""
    gains_sum = sum(r - threshold for r in returns if r > threshold)
    losses_sum = sum(threshold - r for r in returns if r < threshold)
    if losses_sum == 0:
        return float("inf") if gains_sum > 0 else 1.0
    return round(gains_sum / losses_sum, 4)


# ── Metric 3: Gain-Loss Ratio ────────────────────────────────────────

def compute_gain_loss_ratio(returns):
    """Average win / average loss (absolute)."""
    wins = [r for r in returns if r > 0]
    losses = [r for r in returns if r < 0]
    avg_win = _mean(wins) if wins else 0.0
    avg_loss = abs(_mean(losses)) if losses else 0.0
    if avg_loss == 0:
        ratio = float("inf") if avg_win > 0 else 0.0
    else:
        ratio = round(avg_win / avg_loss, 4)
    return {
        "ratio": ratio,
        "avg_win": round(avg_win, 4),
        "avg_loss": round(avg_loss, 4),
        "win_count": len(wins),
        "loss_count": len(losses),
    }


# ── Metric 4: Skewness ───────────────────────────────────────────────

def compute_skewness(returns):
    """Sample skewness (Fisher). Negative = more extreme losses."""
    n = len(returns)
    if n < 3:
        return 0.0
    m = _mean(returns)
    s = _std(returns, m)
    if s == 0:
        return 0.0
    skew = (n / ((n - 1) * (n - 2))) * sum(((x - m) / s) ** 3 for x in returns)
    return round(skew, 4)


# ── Metric 5: Kurtosis ───────────────────────────────────────────────

def compute_kurtosis(returns):
    """Excess kurtosis. >3 from normal means fat tails (we report excess, so >0 = fat)."""
    n = len(returns)
    if n < 4:
        return 0.0
    m = _mean(returns)
    s = _std(returns, m)
    if s == 0:
        return 0.0
    m4 = sum(((x - m) / s) ** 4 for x in returns) / n
    # Excess kurtosis (subtract 3 so normal = 0, report as kurtosis value = m4)
    # But user says >3 = fat tails, so report raw kurtosis (not excess)
    return round(m4, 4)


# ── Metric 6: Drawdown Duration ──────────────────────────────────────

def compute_drawdown_duration(picks):
    """Longest consecutive losing streak in trades AND time (hours)."""
    current_streak = 0
    max_streak = 0
    max_streak_start = None
    max_streak_end = None
    streak_start_ts = None

    for p in picks:
        status = p.get("status", "")
        ts_str = p.get("timestamp", "") or p.get("closed_at", "")

        if status in ("LOST", "STOPPED"):
            current_streak += 1
            if current_streak == 1:
                streak_start_ts = ts_str
            if current_streak > max_streak:
                max_streak = current_streak
                max_streak_start = streak_start_ts
                max_streak_end = ts_str
        else:
            current_streak = 0

    # Calculate time duration of max streak
    duration_hours = 0.0
    if max_streak_start and max_streak_end:
        try:
            fmt_patterns = ["%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S+00:00",
                            "%Y-%m-%dT%H:%M:%S"]
            t_start = t_end = None
            for fmt in fmt_patterns:
                try:
                    t_start = datetime.strptime(max_streak_start.replace("+00:00", ""), "%Y-%m-%dT%H:%M:%S")
                    t_end = datetime.strptime(max_streak_end.replace("+00:00", ""), "%Y-%m-%dT%H:%M:%S")
                    break
                except ValueError:
                    continue
            if t_start and t_end:
                duration_hours = abs((t_end - t_start).total_seconds()) / 3600.0
        except Exception:
            pass

    return {
        "max_consecutive_losses": max_streak,
        "max_streak_duration_hours": round(duration_hours, 2),
        "max_streak_start": max_streak_start or "",
        "max_streak_end": max_streak_end or "",
    }


# ── Metric 7: Correlation Concentration ──────────────────────────────

def compute_correlation_concentration(picks):
    """Pairwise return correlation across top 10 symbols by trade count."""
    # Group returns by symbol
    symbol_returns = defaultdict(list)
    for p in picks:
        sym = p.get("symbol", "")
        pnl = p.get("pnl_pct")
        if sym and pnl is not None:
            symbol_returns[sym].append(float(pnl))

    # Top 10 by trade count
    sorted_syms = sorted(symbol_returns.keys(), key=lambda s: len(symbol_returns[s]), reverse=True)
    top_syms = sorted_syms[:10]

    if len(top_syms) < 2:
        return {
            "top_symbols": top_syms,
            "avg_correlation": 0.0,
            "max_correlation": 0.0,
            "max_corr_pair": [],
            "correlation_matrix": {},
        }

    # Compute pairwise Pearson correlation
    def _pearson(a, b):
        """Pearson correlation between two lists (truncated to min length)."""
        n = min(len(a), len(b))
        if n < 3:
            return 0.0
        a, b = a[:n], b[:n]
        ma, mb = _mean(a), _mean(b)
        sa, sb = _std(a, ma), _std(b, mb)
        if sa == 0 or sb == 0:
            return 0.0
        cov = sum((a[i] - ma) * (b[i] - mb) for i in range(n)) / (n - 1)
        return cov / (sa * sb)

    correlations = []
    max_corr = 0.0
    max_pair = []
    found_any = False
    corr_matrix = {}

    for i, s1 in enumerate(top_syms):
        corr_matrix[s1] = {}
        for j, s2 in enumerate(top_syms):
            if i == j:
                corr_matrix[s1][s2] = 1.0
                continue
            if j < i:
                corr_matrix[s1][s2] = corr_matrix[s2][s1]
                continue
            r = _pearson(symbol_returns[s1], symbol_returns[s2])
            r = round(r, 4)
            corr_matrix[s1][s2] = r
            correlations.append(r)
            if not found_any or abs(r) > abs(max_corr):
                max_corr = r
                max_pair = [s1, s2]
                found_any = True

    avg_corr = _mean(correlations) if correlations else 0.0

    return {
        "top_symbols": top_syms,
        "avg_correlation": round(avg_corr, 4),
        "max_correlation": round(max_corr, 4),
        "max_corr_pair": max_pair,
        "n_pairs": len(correlations),
        "correlation_matrix": corr_matrix,
    }


# ── Metric 8: Regime Performance Split ───────────────────────────────

def compute_regime_split(picks, summary):
    """Split performance by detected regime. Uses strategy name heuristics + summary data."""
    # Classify regime from strategy name and trade characteristics
    regime_buckets = defaultdict(lambda: {"wins": 0, "losses": 0, "pnl": 0.0, "trades": 0})

    for p in picks:
        pnl = p.get("pnl_pct")
        if pnl is None:
            continue
        pnl = float(pnl)
        status = p.get("status", "")
        strategy = (p.get("strategy", "") or "").lower()
        timeframe = (p.get("trade_timeframe", "") or "").upper()

        # Heuristic regime detection from strategy name
        if any(k in strategy for k in ["momentum", "breakout", "trend", "acceleration", "surge"]):
            regime = "TRENDING"
        elif any(k in strategy for k in ["range", "mean_rev", "rsi_bounce", "bollinger", "grid"]):
            regime = "RANGING"
        elif any(k in strategy for k in ["volatility", "squeeze", "cascade", "liquidation"]):
            regime = "HIGH_VOLATILITY"
        elif any(k in strategy for k in ["carry", "funding", "arbitrage"]):
            regime = "LOW_VOLATILITY"
        else:
            regime = "UNCLASSIFIED"

        regime_buckets[regime]["trades"] += 1
        regime_buckets[regime]["pnl"] += pnl
        if status == "WON":
            regime_buckets[regime]["wins"] += 1
        elif status in ("LOST", "STOPPED"):
            regime_buckets[regime]["losses"] += 1

    # Compute WR and PF per regime
    result = {}
    for regime, data in regime_buckets.items():
        total = data["wins"] + data["losses"]
        wr = (data["wins"] / total * 100.0) if total > 0 else 0.0
        # Profit factor approximation from wins/losses ratio
        wins_list = []
        losses_list = []
        for p in picks:
            strat = (p.get("strategy", "") or "").lower()
            pnl_v = p.get("pnl_pct")
            if pnl_v is None:
                continue
            pnl_v = float(pnl_v)
            # Re-classify to match
            if any(k in strat for k in ["momentum", "breakout", "trend", "acceleration", "surge"]):
                r = "TRENDING"
            elif any(k in strat for k in ["range", "mean_rev", "rsi_bounce", "bollinger", "grid"]):
                r = "RANGING"
            elif any(k in strat for k in ["volatility", "squeeze", "cascade", "liquidation"]):
                r = "HIGH_VOLATILITY"
            elif any(k in strat for k in ["carry", "funding", "arbitrage"]):
                r = "LOW_VOLATILITY"
            else:
                r = "UNCLASSIFIED"
            if r == regime:
                if pnl_v > 0:
                    wins_list.append(pnl_v)
                elif pnl_v < 0:
                    losses_list.append(abs(pnl_v))
        gross_profit = sum(wins_list)
        gross_loss = sum(losses_list)
        pf = (gross_profit / gross_loss) if gross_loss > 0 else (float("inf") if gross_profit > 0 else 0.0)

        result[regime] = {
            "trades": data["trades"],
            "wins": data["wins"],
            "losses": data["losses"],
            "win_rate": round(wr, 2),
            "profit_factor": round(pf, 4) if pf != float("inf") else 999.0,
            "total_pnl_pct": round(data["pnl"], 2),
        }

    # Merge summary regime data if available
    summary_regimes = summary.get("regime_win_rates", {})
    if summary_regimes:
        result["_summary_regimes"] = summary_regimes

    return result


# ── Institutional Readiness Score ─────────────────────────────────────

def compute_readiness_score(cvar_95, omega, skewness, kurtosis, dd_duration,
                            avg_correlation, regime_split, gain_loss_ratio):
    """0-100 composite score measuring institutional readiness."""
    score = 0
    breakdown = {}

    # ES < 10% (CVaR magnitude)
    es_pass = abs(cvar_95) < 10.0
    pts = 15 if es_pass else 0
    score += pts
    breakdown["expected_shortfall_lt_10pct"] = {"points": pts, "max": 15, "value": round(cvar_95, 4), "pass": es_pass}

    # Omega > 1.2
    omega_pass = omega > 1.2
    pts = 15 if omega_pass else 0
    score += pts
    breakdown["omega_gt_1.2"] = {"points": pts, "max": 15, "value": round(omega, 4), "pass": omega_pass}

    # Skewness > -0.5
    skew_pass = skewness > -0.5
    pts = 10 if skew_pass else 0
    score += pts
    breakdown["skewness_gt_neg0.5"] = {"points": pts, "max": 10, "value": round(skewness, 4), "pass": skew_pass}

    # Kurtosis < 5
    kurt_pass = kurtosis < 5.0
    pts = 10 if kurt_pass else 0
    score += pts
    breakdown["kurtosis_lt_5"] = {"points": pts, "max": 10, "value": round(kurtosis, 4), "pass": kurt_pass}

    # Max DD duration < 50 trades
    dd_pass = dd_duration < 50
    pts = 10 if dd_pass else 0
    score += pts
    breakdown["max_dd_duration_lt_50"] = {"points": pts, "max": 10, "value": dd_duration, "pass": dd_pass}

    # Avg correlation < 0.5
    corr_pass = avg_correlation < 0.5
    pts = 10 if corr_pass else 0
    score += pts
    breakdown["avg_correlation_lt_0.5"] = {"points": pts, "max": 10, "value": round(avg_correlation, 4), "pass": corr_pass}

    # Regime WR > 40% in ALL regimes
    regime_all_pass = True
    regime_details = {}
    for regime, data in regime_split.items():
        if regime.startswith("_"):
            continue
        wr = data.get("win_rate", 0)
        regime_details[regime] = wr
        if wr < 40.0 and data.get("trades", 0) >= 10:  # Only count regimes with 10+ trades
            regime_all_pass = False
    pts = 15 if regime_all_pass else 0
    score += pts
    breakdown["regime_wr_gt_40pct_all"] = {"points": pts, "max": 15, "details": regime_details, "pass": regime_all_pass}

    # Gain-Loss > 1.5
    gl_pass = gain_loss_ratio > 1.5
    pts = 15 if gl_pass else 0
    score += pts
    breakdown["gain_loss_gt_1.5"] = {"points": pts, "max": 15, "value": round(gain_loss_ratio, 4), "pass": gl_pass}

    return {"score": score, "max_score": 100, "breakdown": breakdown}


# ── Pretty Print ──────────────────────────────────────────────────────

def print_report(metrics):
    """Print formatted table of all metrics with institutional benchmarks."""
    print("\n" + "=" * 80)
    print("  ADVANCED CRYPTO HEDGE FUND RISK METRICS")
    print("=" * 80)

    def _row(label, value, benchmark, status):
        v_str = str(value).rjust(12)
        return f"  {label:<35} {v_str}  {benchmark:<25} {status}"

    print(f"\n  {'METRIC':<35} {'VALUE':>12}  {'BENCHMARK':<25} STATUS")
    print("  " + "-" * 76)

    cvar95 = metrics["expected_shortfall"]["95%"]["CVaR"]
    cvar99 = metrics["expected_shortfall"]["99%"]["CVaR"]
    omega = metrics["omega_ratio"]
    gl = metrics["gain_loss_ratio"]["ratio"]
    skew = metrics["skewness"]
    kurt = metrics["kurtosis"]
    dd = metrics["drawdown_duration"]["max_consecutive_losses"]
    corr = metrics["correlation_concentration"]["avg_correlation"]

    rows = [
        ("CVaR 95%", f"{cvar95:.2f}%", "> -10%", "PASS" if abs(cvar95) < 10 else "FAIL"),
        ("CVaR 99%", f"{cvar99:.2f}%", "> -15%", "PASS" if abs(cvar99) < 15 else "FAIL"),
        ("Omega Ratio", f"{omega:.4f}", "> 1.20", "PASS" if omega > 1.2 else "FAIL"),
        ("Gain-Loss Ratio", f"{gl:.4f}", "> 1.50", "PASS" if gl > 1.5 else "FAIL"),
        ("Skewness", f"{skew:.4f}", "> -0.50", "PASS" if skew > -0.5 else "FAIL"),
        ("Kurtosis", f"{kurt:.4f}", "< 5.00", "PASS" if kurt < 5 else "FAIL"),
        ("Max Losing Streak", f"{dd} trades", "< 50 trades", "PASS" if dd < 50 else "FAIL"),
        ("DD Streak Duration", f"{metrics['drawdown_duration']['max_streak_duration_hours']:.1f}h", "< 168h (1w)", ""),
        ("Avg Symbol Correlation", f"{corr:.4f}", "< 0.50", "PASS" if corr < 0.5 else "FAIL"),
        ("Max Symbol Correlation", f"{metrics['correlation_concentration']['max_correlation']:.4f}", "< 0.80", ""),
    ]

    for label, value, bench, status in rows:
        s_icon = "[OK]" if status == "PASS" else ("[!!]" if status == "FAIL" else "    ")
        print(f"  {label:<35} {value:>12}  {bench:<25} {s_icon}")

    # Regime split
    print(f"\n  {'REGIME PERFORMANCE SPLIT':<35}")
    print("  " + "-" * 76)
    print(f"  {'Regime':<25} {'Trades':>8} {'WR%':>8} {'PF':>8} {'PnL%':>10}")
    print("  " + "-" * 76)
    for regime, data in metrics["regime_split"].items():
        if regime.startswith("_"):
            continue
        print(f"  {regime:<25} {data['trades']:>8} {data['win_rate']:>7.1f}% {data['profit_factor']:>8.2f} {data['total_pnl_pct']:>+10.2f}")

    # Correlation top pair
    corr_data = metrics["correlation_concentration"]
    if corr_data["max_corr_pair"]:
        print(f"\n  Max correlated pair: {corr_data['max_corr_pair'][0]} / {corr_data['max_corr_pair'][1]} = {corr_data['max_correlation']:.4f}")

    # Readiness score
    rs = metrics["institutional_readiness"]
    print(f"\n  {'=' * 50}")
    print(f"  INSTITUTIONAL READINESS SCORE: {rs['score']} / {rs['max_score']}")
    print(f"  {'=' * 50}")

    grade = "A+" if rs["score"] >= 90 else "A" if rs["score"] >= 80 else "B" if rs["score"] >= 65 else "C" if rs["score"] >= 50 else "D" if rs["score"] >= 35 else "F"
    print(f"  Grade: {grade}")

    print("\n  Score Breakdown:")
    for criterion, info in rs["breakdown"].items():
        icon = "[OK]" if info["pass"] else "[!!]"
        val = info.get("value", "")
        if val == "":
            val = str(info.get("details", ""))[:40]
        print(f"    {icon} {criterion:<35} {info['points']:>2}/{info['max']}  (value: {val})")

    print("\n" + "=" * 80)


# ── Main ──────────────────────────────────────────────────────────────

def run():
    """Main entry point."""
    print("[advanced_risk_metrics] Loading closed picks...")
    picks, summary = _load_closed_picks()
    print(f"[advanced_risk_metrics] Loaded {len(picks)} closed picks")

    returns = _extract_returns(picks)
    print(f"[advanced_risk_metrics] {len(returns)} picks with valid pnl_pct")

    if not returns:
        print("[ERROR] No returns data available. Exiting.")
        return

    # Compute all 8 metrics
    print("[advanced_risk_metrics] Computing metrics...")

    # 1. CVaR
    cvar_95 = compute_cvar(returns, 0.95)
    cvar_99 = compute_cvar(returns, 0.99)

    # 2. Omega
    omega = compute_omega(returns)

    # 3. Gain-Loss
    gl = compute_gain_loss_ratio(returns)

    # 4. Skewness
    skew = compute_skewness(returns)

    # 5. Kurtosis
    kurt = compute_kurtosis(returns)

    # 6. Drawdown Duration
    dd = compute_drawdown_duration(picks)

    # 7. Correlation Concentration
    corr = compute_correlation_concentration(picks)

    # 8. Regime Split
    regime = compute_regime_split(picks, summary)

    # Institutional Readiness Score
    readiness = compute_readiness_score(
        cvar_95=cvar_95["CVaR"],
        omega=omega,
        skewness=skew,
        kurtosis=kurt,
        dd_duration=dd["max_consecutive_losses"],
        avg_correlation=corr["avg_correlation"],
        regime_split=regime,
        gain_loss_ratio=gl["ratio"],
    )

    # Assemble output
    metrics = {
        "generated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_closed_picks": len(picks),
        "total_valid_returns": len(returns),
        "expected_shortfall": {
            "95%": cvar_95,
            "99%": cvar_99,
        },
        "omega_ratio": omega,
        "gain_loss_ratio": gl,
        "skewness": skew,
        "kurtosis": kurt,
        "drawdown_duration": dd,
        "correlation_concentration": {
            k: v for k, v in corr.items() if k != "correlation_matrix"
        },
        "correlation_matrix": corr.get("correlation_matrix", {}),
        "regime_split": regime,
        "institutional_readiness": readiness,
        "return_stats": {
            "mean": round(_mean(returns), 4),
            "std": round(_std(returns), 4),
            "min": round(min(returns), 4),
            "max": round(max(returns), 4),
            "median": round(sorted(returns)[len(returns) // 2], 4),
            "count": len(returns),
        },
    }

    # Save
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, default=str)
    print(f"[advanced_risk_metrics] Saved to {OUTPUT_PATH}")

    # Print report
    print_report(metrics)

    return metrics


if __name__ == "__main__":
    run()
