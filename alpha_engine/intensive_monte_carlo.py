#!/usr/bin/env python3
"""
Intensive Monte Carlo Backtesting Suite
========================================
Rigorous statistical validation of the Alpha Engine trading system.
10,000 simulations per test. 5 comprehensive test batteries.

Tests:
  1. Strategy-Level Monte Carlo (per strategy, 10k sims)
  2. Portfolio-Level Monte Carlo (10k sims)
  3. Regime-Conditional Monte Carlo (5k sims per regime)
  4. Filter Combination Stress Test (1k sims each)
  5. Worst-Case Scenario Analysis

Output:
  - alpha_engine/data/intensive_monte_carlo_report.json
  - docs/MONTE_CARLO_VALIDATION.md
"""

import json
import os
import sys
import math
import time
from collections import Counter, defaultdict
from datetime import datetime

import numpy as np

# ---------------------------------------------------------------------------
# PATHS
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLOSED_PICKS_PATH = os.path.join(BASE_DIR, "alpha_engine", "data", "closed_picks.json")
DASHBOARD_PATH = os.path.join(BASE_DIR, "audit_trail", "data", "dashboard_payload.json")
REPORT_PATH = os.path.join(BASE_DIR, "alpha_engine", "data", "intensive_monte_carlo_report.json")
MD_PATH = os.path.join(BASE_DIR, "docs", "MONTE_CARLO_VALIDATION.md")

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
STRATEGY_SIMS = 10_000
PORTFOLIO_SIMS = 10_000
REGIME_SIMS = 5_000
FILTER_SIMS = 1_000
MIN_TRADES_STRATEGY = 10
INITIAL_EQUITY = 10_000.0
RUIN_DRAWDOWN_THRESHOLD = 0.20   # -20%
SEED = 42

np.random.seed(SEED)

# ---------------------------------------------------------------------------
# DATA LOADING & NORMALIZATION
# ---------------------------------------------------------------------------

def load_and_combine():
    """Load closed picks from both sources, deduplicate, normalize PnL."""
    all_trades = []
    seen_ids = set()

    # Source 1: closed_picks.json
    if os.path.exists(CLOSED_PICKS_PATH):
        with open(CLOSED_PICKS_PATH, "r") as f:
            picks = json.load(f)
        for p in picks:
            if p.get("status") in ("OPEN",):
                continue
            tid = p.get("id", "")
            pnl = p.get("pnl_pct", 0.0)
            if pnl is None:
                pnl = 0.0
            # Normalize: closed_picks stores pnl_pct as fraction (0.01 = 1%)
            # Check range to auto-detect
            if abs(pnl) < 1.0:
                pnl_pct = pnl * 100.0  # convert fraction to percent
            else:
                pnl_pct = pnl
            trade = _normalize_trade(p, pnl_pct, source="closed_picks")
            if tid and tid not in seen_ids:
                seen_ids.add(tid)
            all_trades.append(trade)

    # Source 2: dashboard_payload.json recent_closed
    if os.path.exists(DASHBOARD_PATH):
        with open(DASHBOARD_PATH, "r") as f:
            payload = json.load(f)
        recent = payload.get("picks", {}).get("recent_closed", [])
        for p in recent:
            if p.get("status") in ("OPEN",):
                continue
            # Build a dedup key from strategy+symbol+entry_price+direction
            tid = f"{p.get('strategy','')}::{p.get('symbol','')}::{p.get('entry_price','')}::{p.get('direction','')}"
            if tid in seen_ids:
                continue
            seen_ids.add(tid)
            pnl = p.get("pnl_pct", 0.0)
            if pnl is None:
                pnl = 0.0
            # Dashboard stores pnl_pct as percentage already (e.g. 8.36 = 8.36%)
            # closed_picks stores as fraction. Detect: if all dashboard values > 1, it's percentage.
            pnl_pct = float(pnl)
            trade = _normalize_trade(p, pnl_pct, source="dashboard")
            all_trades.append(trade)

    return all_trades


def _normalize_trade(raw, pnl_pct, source):
    """Normalize a trade record to a consistent format."""
    strategy = raw.get("strategy", "unknown") or "unknown"
    status = raw.get("status", "CLOSED")
    # Determine win/loss
    if status == "WON":
        won = True
    elif status == "LOST":
        won = False
    else:
        won = pnl_pct > 0

    # Regime detection
    regime = _detect_regime(raw)

    # Category / asset class
    category = (raw.get("category") or raw.get("asset_class") or "unknown").lower()

    # Filters
    confidence = raw.get("confidence", 0.0) or 0.0
    direction = raw.get("signal_type") or raw.get("direction") or "LONG"
    rr = raw.get("risk_reward") or raw.get("rr_ratio") or 0.0
    ml_score = raw.get("ml_score", 0.0) or 0.0
    source_system = raw.get("source_system", "")
    elite_grade = raw.get("elite_grade", "")
    symbol = raw.get("symbol", "")

    # Determine if copy trader
    is_copy = "copy" in strategy.lower() or "clone" in strategy.lower()

    # Determine tier (large cap)
    tier1_symbols = {
        "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
        "ADAUSDT", "DOGEUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT",
        "BTC-USD", "ETH-USD", "BNB-USD", "SOL-USD", "XRP-USD",
    }
    is_tier1 = any(t in symbol.upper() for t in ["BTC", "ETH", "BNB", "SOL", "XRP", "ADA", "DOGE", "AVAX", "DOT", "LINK"])

    # ML-enhanced strategies (the 4 proven)
    ml_strategies = {"ml_enhanced_BNBUSDT_15m_B_lightgbm", "ml_enhanced_FETUSDT_1d_B_lightgbm",
                     "ml_enhanced_RENDERUSDT_1h_D_ensemble_stack", "ml_enhanced_BTCUSDT_15m_D_ensemble_stack",
                     "ml_enhanced_ADAUSDT_15m_D_ensemble_stack", "ml_enhanced_RENDERUSDT_4h_D_ensemble_stack"}
    is_ml_enhanced = strategy in ml_strategies

    return {
        "pnl_pct": pnl_pct,
        "won": won,
        "strategy": strategy,
        "symbol": symbol,
        "regime": regime,
        "category": category,
        "confidence": float(confidence),
        "direction": direction.upper() if direction else "LONG",
        "risk_reward": float(rr) if rr else 0.0,
        "ml_score": float(ml_score),
        "is_copy": is_copy,
        "is_tier1": is_tier1,
        "is_ml_enhanced": is_ml_enhanced,
        "elite_grade": elite_grade,
        "source": source,
    }


def _detect_regime(raw):
    """Detect regime from various fields."""
    # Direct regime field
    regime = raw.get("regime_at_entry")
    if regime and regime not in (None, "unknown", "Unknown"):
        r = regime.upper()
        if r in ("BULL", "BULLISH"):
            return "BULL"
        elif r in ("BEAR", "BEARISH"):
            return "BEAR"
        elif r in ("TRENDING",):
            return "BULL"  # trending often bullish context
        elif r in ("TRANSITIONAL", "CHOPPY", "MOMENTUM"):
            return "CHOPPY"
        elif r == "ACCUMULATION":
            return "CHOPPY"
        return "CHOPPY"

    # Try HMM regime
    hmm = raw.get("hmm_regime", "")
    if hmm:
        h = hmm.upper()
        if "BULL" in h or "MARKUP" in h:
            return "BULL"
        elif "BEAR" in h or "DISTRIBUTION" in h:
            return "BEAR"
        elif "ACCUMULATION" in h:
            return "CHOPPY"

    # Try sentinel
    sentinel = raw.get("sentinel_regime", "")
    if sentinel:
        s = sentinel.upper()
        if "BULL" in s or "MARKUP" in s:
            return "BULL"
        elif "BEAR" in s or "DISTRIBUTION" in s:
            return "BEAR"
        return "CHOPPY"

    # Try regime_trend_direction
    trend = raw.get("regime_trend_direction", "")
    if trend:
        t = trend.upper()
        if "BULL" in t:
            return "BULL"
        elif "BEAR" in t:
            return "BEAR"

    return "UNKNOWN"


# ---------------------------------------------------------------------------
# STATISTICAL HELPERS
# ---------------------------------------------------------------------------

def compute_equity_curve(pnl_sequence, initial=INITIAL_EQUITY):
    """Compute cumulative equity curve from PnL percentages."""
    equity = np.empty(len(pnl_sequence) + 1)
    equity[0] = initial
    for i, pnl in enumerate(pnl_sequence):
        equity[i + 1] = equity[i] * (1.0 + pnl / 100.0)
    return equity


def max_drawdown(equity_curve):
    """Compute maximum drawdown from equity curve."""
    peak = equity_curve[0]
    max_dd = 0.0
    for val in equity_curve:
        if val > peak:
            peak = val
        dd = (peak - val) / peak if peak > 0 else 0.0
        if dd > max_dd:
            max_dd = dd
    return max_dd


def sharpe_ratio(pnl_array, risk_free_annual=0.04):
    """Annualized Sharpe ratio. Assume ~252 trading days, 1 trade/day avg."""
    if len(pnl_array) < 2:
        return 0.0
    mean_r = np.mean(pnl_array)
    std_r = np.std(pnl_array, ddof=1)
    if std_r < 1e-10:
        return 0.0
    # Daily risk-free rate approx
    rf_daily = risk_free_annual / 252.0
    daily_excess = mean_r - rf_daily
    return (daily_excess / std_r) * math.sqrt(252)


def calmar_ratio(pnl_array, initial=INITIAL_EQUITY):
    """Calmar ratio = annualized return / max drawdown."""
    eq = compute_equity_curve(pnl_array, initial)
    dd = max_drawdown(eq)
    if dd < 1e-10:
        return 99.0  # no drawdown
    total_return = (eq[-1] / eq[0]) - 1.0
    n_trades = len(pnl_array)
    if n_trades == 0:
        return 0.0
    # Annualize assuming ~1 trade/day
    ann_return = total_return * (252.0 / max(n_trades, 1))
    return ann_return / dd


def max_consecutive(wins_losses, target=False):
    """Max consecutive streak of losses (target=False) or wins (target=True)."""
    max_streak = 0
    current = 0
    for w in wins_losses:
        if w == target:
            current += 1
            max_streak = max(max_streak, current)
        else:
            current = 0
    return max_streak


def percentiles(values, pcts=(1, 5, 25, 50, 75, 95, 99)):
    """Compute percentiles from array."""
    arr = np.array(values)
    return {f"p{p}": float(np.percentile(arr, p)) for p in pcts}


def p_value_vs_zero(actual_sharpe, sim_sharpes):
    """P-value: fraction of simulated Sharpes >= actual (under null of random)."""
    arr = np.array(sim_sharpes)
    return float(np.mean(arr >= actual_sharpe))


# ---------------------------------------------------------------------------
# TEST 1: STRATEGY-LEVEL MONTE CARLO
# ---------------------------------------------------------------------------

def test_strategy_level(trades, n_sims=STRATEGY_SIMS):
    """Per-strategy bootstrap Monte Carlo."""
    print(f"\n{'='*60}")
    print(f"TEST 1: STRATEGY-LEVEL MONTE CARLO ({n_sims:,} sims each)")
    print(f"{'='*60}")

    # Group by strategy
    strat_trades = defaultdict(list)
    for t in trades:
        strat_trades[t["strategy"]].append(t["pnl_pct"])

    results = {}
    qualifying = {s: pnls for s, pnls in strat_trades.items() if len(pnls) >= MIN_TRADES_STRATEGY}
    print(f"Strategies with {MIN_TRADES_STRATEGY}+ trades: {len(qualifying)}")

    for strat_name, pnl_list in sorted(qualifying.items(), key=lambda x: -len(x[1])):
        pnl_arr = np.array(pnl_list)
        n = len(pnl_arr)

        # Actual metrics
        actual_eq = compute_equity_curve(pnl_arr)
        actual_sharpe = sharpe_ratio(pnl_arr)
        actual_dd = max_drawdown(actual_eq)
        actual_final = float(actual_eq[-1])
        actual_return = (actual_final / INITIAL_EQUITY - 1.0) * 100.0
        actual_wr = float(np.mean(pnl_arr > 0)) * 100.0

        # Bootstrap simulations
        sim_finals = np.empty(n_sims)
        sim_sharpes = np.empty(n_sims)
        sim_dds = np.empty(n_sims)
        sim_profitable = 0
        sim_ruin = 0

        for i in range(n_sims):
            # Resample with replacement
            boot = np.random.choice(pnl_arr, size=n, replace=True)
            eq = compute_equity_curve(boot)
            sim_finals[i] = eq[-1]
            sim_sharpes[i] = sharpe_ratio(boot)
            dd = max_drawdown(eq)
            sim_dds[i] = dd
            if eq[-1] > INITIAL_EQUITY:
                sim_profitable += 1
            if dd >= RUIN_DRAWDOWN_THRESHOLD:
                sim_ruin += 1

        pct_profitable = sim_profitable / n_sims * 100.0
        pct_ruin = sim_ruin / n_sims * 100.0

        # P-value: generate zero-mean simulations
        zero_mean_pnl = pnl_arr - np.mean(pnl_arr)
        null_sharpes = np.empty(n_sims)
        for i in range(n_sims):
            boot = np.random.choice(zero_mean_pnl, size=n, replace=True)
            null_sharpes[i] = sharpe_ratio(boot)
        p_val = p_value_vs_zero(actual_sharpe, null_sharpes)

        edge_status = "EDGE" if pct_profitable >= 60 and p_val < 0.05 else "WEAK" if pct_profitable >= 50 else "NO_EDGE"

        result = {
            "n_trades": n,
            "actual_return_pct": round(actual_return, 2),
            "actual_sharpe": round(actual_sharpe, 3),
            "actual_max_dd": round(actual_dd * 100, 2),
            "actual_win_rate": round(actual_wr, 1),
            "pct_sims_profitable": round(pct_profitable, 1),
            "pct_sims_ruin_20dd": round(pct_ruin, 1),
            "p_value": round(p_val, 4),
            "edge_status": edge_status,
            "final_equity_percentiles": percentiles(sim_finals),
            "sharpe_percentiles": percentiles(sim_sharpes),
            "max_dd_percentiles": percentiles(sim_dds * 100),
        }
        results[strat_name] = result

        status_icon = "+" if edge_status == "EDGE" else "~" if edge_status == "WEAK" else "-"
        print(f"  [{status_icon}] {strat_name} ({n} trades): "
              f"profitable={pct_profitable:.0f}% ruin={pct_ruin:.0f}% "
              f"p={p_val:.3f} sharpe={actual_sharpe:.2f} [{edge_status}]")

    # Summary
    edge_count = sum(1 for r in results.values() if r["edge_status"] == "EDGE")
    weak_count = sum(1 for r in results.values() if r["edge_status"] == "WEAK")
    no_edge_count = sum(1 for r in results.values() if r["edge_status"] == "NO_EDGE")
    print(f"\n  Summary: {edge_count} EDGE, {weak_count} WEAK, {no_edge_count} NO_EDGE "
          f"out of {len(results)} strategies")

    return results


# ---------------------------------------------------------------------------
# TEST 2: PORTFOLIO-LEVEL MONTE CARLO
# ---------------------------------------------------------------------------

def test_portfolio_level(trades, n_sims=PORTFOLIO_SIMS):
    """Full portfolio Monte Carlo with shuffling, subsetting, and noise."""
    print(f"\n{'='*60}")
    print(f"TEST 2: PORTFOLIO-LEVEL MONTE CARLO ({n_sims:,} sims)")
    print(f"{'='*60}")

    pnl_arr = np.array([t["pnl_pct"] for t in trades])
    wins = np.array([t["won"] for t in trades])
    n = len(pnl_arr)

    # Actual metrics
    actual_eq = compute_equity_curve(pnl_arr)
    actual_sharpe = sharpe_ratio(pnl_arr)
    actual_dd = max_drawdown(actual_eq)
    actual_calmar = calmar_ratio(pnl_arr)
    actual_final = float(actual_eq[-1])
    actual_max_win_streak = max_consecutive(wins, True)
    actual_max_loss_streak = max_consecutive(wins, False)

    print(f"  Portfolio: {n} trades, final equity=${actual_final:,.2f}, "
          f"Sharpe={actual_sharpe:.2f}, MaxDD={actual_dd*100:.1f}%")

    results = {
        "shuffle": _portfolio_sim_shuffle(pnl_arr, n_sims),
        "subset_80pct": _portfolio_sim_subset(pnl_arr, n_sims, fraction=0.80),
        "noise_1pct": _portfolio_sim_noise(pnl_arr, n_sims, noise_std=1.0),
    }

    results["actual"] = {
        "n_trades": n,
        "final_equity": round(actual_final, 2),
        "sharpe": round(actual_sharpe, 3),
        "max_dd_pct": round(actual_dd * 100, 2),
        "calmar": round(actual_calmar, 3),
        "max_win_streak": int(actual_max_win_streak),
        "max_loss_streak": int(actual_max_loss_streak),
        "total_return_pct": round((actual_final / INITIAL_EQUITY - 1) * 100, 2),
    }

    return results


def _portfolio_sim_shuffle(pnl_arr, n_sims):
    """Test: does trade ordering matter?"""
    print(f"  [Shuffle] Running {n_sims:,} order-shuffled simulations...")
    n = len(pnl_arr)
    finals = np.empty(n_sims)
    sharpes = np.empty(n_sims)
    dds = np.empty(n_sims)
    calmars = np.empty(n_sims)
    win_streaks = np.empty(n_sims)
    loss_streaks = np.empty(n_sims)

    for i in range(n_sims):
        shuffled = np.random.permutation(pnl_arr)
        eq = compute_equity_curve(shuffled)
        finals[i] = eq[-1]
        sharpes[i] = sharpe_ratio(shuffled)
        dds[i] = max_drawdown(eq)
        calmars[i] = calmar_ratio(shuffled)
        w = shuffled > 0
        win_streaks[i] = max_consecutive(w, True)
        loss_streaks[i] = max_consecutive(w, False)

    pct_profitable = float(np.mean(finals > INITIAL_EQUITY)) * 100.0
    print(f"    Profitable: {pct_profitable:.1f}%, "
          f"Median final: ${np.median(finals):,.2f}, "
          f"Median DD: {np.median(dds)*100:.1f}%")

    return {
        "pct_profitable": round(pct_profitable, 1),
        "final_equity": percentiles(finals),
        "sharpe": percentiles(sharpes),
        "max_dd_pct": percentiles(dds * 100),
        "calmar": percentiles(calmars),
        "max_win_streak": percentiles(win_streaks),
        "max_loss_streak": percentiles(loss_streaks),
    }


def _portfolio_sim_subset(pnl_arr, n_sims, fraction=0.80):
    """Test: is the edge robust to removing 20% of trades?"""
    n = len(pnl_arr)
    subset_size = int(n * fraction)
    print(f"  [Subset {fraction*100:.0f}%] Running {n_sims:,} simulations with {subset_size}/{n} trades...")

    finals = np.empty(n_sims)
    sharpes = np.empty(n_sims)
    dds = np.empty(n_sims)

    for i in range(n_sims):
        indices = np.random.choice(n, size=subset_size, replace=False)
        subset = pnl_arr[indices]
        eq = compute_equity_curve(subset)
        finals[i] = eq[-1]
        sharpes[i] = sharpe_ratio(subset)
        dds[i] = max_drawdown(eq)

    pct_profitable = float(np.mean(finals > INITIAL_EQUITY)) * 100.0
    print(f"    Profitable: {pct_profitable:.1f}%, "
          f"Median final: ${np.median(finals):,.2f}")

    return {
        "pct_profitable": round(pct_profitable, 1),
        "subset_size": subset_size,
        "final_equity": percentiles(finals),
        "sharpe": percentiles(sharpes),
        "max_dd_pct": percentiles(dds * 100),
    }


def _portfolio_sim_noise(pnl_arr, n_sims, noise_std=1.0):
    """Test: is the edge robust to +/- slippage noise?"""
    n = len(pnl_arr)
    print(f"  [Noise ±{noise_std}%] Running {n_sims:,} simulations with PnL perturbation...")

    finals = np.empty(n_sims)
    sharpes = np.empty(n_sims)
    dds = np.empty(n_sims)

    for i in range(n_sims):
        noise = np.random.normal(0, noise_std, size=n)
        noisy = pnl_arr + noise
        eq = compute_equity_curve(noisy)
        finals[i] = eq[-1]
        sharpes[i] = sharpe_ratio(noisy)
        dds[i] = max_drawdown(eq)

    pct_profitable = float(np.mean(finals > INITIAL_EQUITY)) * 100.0
    print(f"    Profitable: {pct_profitable:.1f}%, "
          f"Median final: ${np.median(finals):,.2f}")

    return {
        "pct_profitable": round(pct_profitable, 1),
        "noise_std_pct": noise_std,
        "final_equity": percentiles(finals),
        "sharpe": percentiles(sharpes),
        "max_dd_pct": percentiles(dds * 100),
    }


# ---------------------------------------------------------------------------
# TEST 3: REGIME-CONDITIONAL MONTE CARLO
# ---------------------------------------------------------------------------

def test_regime_conditional(trades, n_sims=REGIME_SIMS):
    """Split by regime, run Monte Carlo per regime."""
    print(f"\n{'='*60}")
    print(f"TEST 3: REGIME-CONDITIONAL MONTE CARLO ({n_sims:,} sims/regime)")
    print(f"{'='*60}")

    regime_trades = defaultdict(list)
    for t in trades:
        regime_trades[t["regime"]].append(t["pnl_pct"])

    print(f"  Regimes found: {dict(Counter(t['regime'] for t in trades))}")

    results = {}
    for regime, pnl_list in sorted(regime_trades.items()):
        pnl_arr = np.array(pnl_list)
        n = len(pnl_arr)
        if n < 5:
            print(f"  [{regime}] Only {n} trades, skipping.")
            continue

        actual_eq = compute_equity_curve(pnl_arr)
        actual_sharpe = sharpe_ratio(pnl_arr)
        actual_wr = float(np.mean(pnl_arr > 0)) * 100.0

        sim_finals = np.empty(n_sims)
        sim_sharpes = np.empty(n_sims)
        sim_profitable = 0

        for i in range(n_sims):
            boot = np.random.choice(pnl_arr, size=n, replace=True)
            eq = compute_equity_curve(boot)
            sim_finals[i] = eq[-1]
            sim_sharpes[i] = sharpe_ratio(boot)
            if eq[-1] > INITIAL_EQUITY:
                sim_profitable += 1

        pct_profitable = sim_profitable / n_sims * 100.0
        has_edge = pct_profitable >= 55

        print(f"  [{regime}] {n} trades: WR={actual_wr:.1f}%, Sharpe={actual_sharpe:.2f}, "
              f"Sims profitable={pct_profitable:.1f}% {'[EDGE]' if has_edge else '[NO EDGE]'}")

        results[regime] = {
            "n_trades": n,
            "actual_win_rate": round(actual_wr, 1),
            "actual_sharpe": round(actual_sharpe, 3),
            "actual_mean_pnl": round(float(np.mean(pnl_arr)), 3),
            "pct_sims_profitable": round(pct_profitable, 1),
            "has_edge": has_edge,
            "final_equity": percentiles(sim_finals),
            "sharpe": percentiles(sim_sharpes),
        }

    # Check if edge only in BULL
    bull_edge = results.get("BULL", {}).get("has_edge", False)
    bear_edge = results.get("BEAR", {}).get("has_edge", False)
    choppy_edge = results.get("CHOPPY", {}).get("has_edge", False)

    if bull_edge and not bear_edge and not choppy_edge:
        verdict = "BULL_ONLY_EDGE"
        print("\n  WARNING: Edge only exists in BULL regime — may just be 'be long in a bull market'")
    elif bull_edge and bear_edge:
        verdict = "ALL_REGIME_EDGE"
        print("\n  STRONG: Edge persists across BULL and BEAR regimes")
    elif not bull_edge and not bear_edge:
        verdict = "NO_REGIME_EDGE"
        print("\n  WARNING: No clear edge in any regime")
    else:
        verdict = "PARTIAL_EDGE"
        print(f"\n  Partial edge: BULL={bull_edge}, BEAR={bear_edge}, CHOPPY={choppy_edge}")

    results["_verdict"] = verdict
    return results


# ---------------------------------------------------------------------------
# TEST 4: FILTER COMBINATION STRESS TEST
# ---------------------------------------------------------------------------

def test_filter_combinations(trades, n_sims=FILTER_SIMS):
    """Test key filters under Monte Carlo."""
    print(f"\n{'='*60}")
    print(f"TEST 4: FILTER COMBINATION STRESS TEST ({n_sims:,} sims each)")
    print(f"{'='*60}")

    filters = {
        "GAMMA_proxy": lambda t: t["confidence"] >= 0.60 and t["elite_grade"] in ("A", "B", "C"),
        "Golden": lambda t: t["confidence"] >= 0.75 and t["direction"] == "LONG" and 1.0 <= t["risk_reward"] <= 1.5,
        "ML_enhanced": lambda t: t["is_ml_enhanced"],
        "Large_cap_TIER1": lambda t: t["is_tier1"],
        "Copy_trader": lambda t: t["is_copy"],
        "High_confidence_80": lambda t: t["confidence"] >= 0.80,
        "Crypto_only": lambda t: t["category"] in ("crypto",),
        "Forex_only": lambda t: t["category"] in ("forex",),
        "Low_RR_safe": lambda t: 0.5 <= t["risk_reward"] <= 1.5,
        "High_ML_score": lambda t: t["ml_score"] >= 0.5,
    }

    results = {}
    for filter_name, filter_fn in filters.items():
        filtered = [t for t in trades if filter_fn(t)]
        n = len(filtered)
        if n < 5:
            print(f"  [{filter_name}] Only {n} trades, skipping.")
            results[filter_name] = {"n_trades": n, "skipped": True}
            continue

        pnl_arr = np.array([t["pnl_pct"] for t in filtered])
        actual_wr = float(np.mean(pnl_arr > 0)) * 100.0
        actual_sharpe = sharpe_ratio(pnl_arr)
        actual_mean = float(np.mean(pnl_arr))

        sim_finals = np.empty(n_sims)
        sim_sharpes = np.empty(n_sims)
        sim_profitable = 0
        sim_ruin = 0

        for i in range(n_sims):
            boot = np.random.choice(pnl_arr, size=n, replace=True)
            eq = compute_equity_curve(boot)
            sim_finals[i] = eq[-1]
            sim_sharpes[i] = sharpe_ratio(boot)
            if eq[-1] > INITIAL_EQUITY:
                sim_profitable += 1
            if max_drawdown(eq) >= RUIN_DRAWDOWN_THRESHOLD:
                sim_ruin += 1

        pct_profitable = sim_profitable / n_sims * 100.0
        pct_ruin = sim_ruin / n_sims * 100.0

        print(f"  [{filter_name}] {n} trades: WR={actual_wr:.1f}%, mean={actual_mean:.2f}%, "
              f"Sharpe={actual_sharpe:.2f}, profitable_sims={pct_profitable:.1f}%, ruin={pct_ruin:.1f}%")

        results[filter_name] = {
            "n_trades": n,
            "actual_win_rate": round(actual_wr, 1),
            "actual_mean_pnl": round(actual_mean, 3),
            "actual_sharpe": round(actual_sharpe, 3),
            "pct_sims_profitable": round(pct_profitable, 1),
            "pct_sims_ruin_20dd": round(pct_ruin, 1),
            "final_equity": percentiles(sim_finals),
            "sharpe": percentiles(sim_sharpes),
        }

    # Rank filters by robustness
    ranked = sorted(
        [(k, v) for k, v in results.items() if not v.get("skipped")],
        key=lambda x: -x[1]["pct_sims_profitable"]
    )
    print(f"\n  Filter Ranking (by % profitable simulations):")
    for i, (name, data) in enumerate(ranked, 1):
        print(f"    {i}. {name}: {data['pct_sims_profitable']:.1f}% profitable, "
              f"Sharpe={data['actual_sharpe']:.2f}")

    results["_ranking"] = [{"filter": k, "pct_profitable": v["pct_sims_profitable"],
                            "sharpe": v["actual_sharpe"]} for k, v in ranked]
    return results


# ---------------------------------------------------------------------------
# TEST 5: WORST-CASE SCENARIO ANALYSIS
# ---------------------------------------------------------------------------

def test_worst_case(trades, n_sims=PORTFOLIO_SIMS):
    """Worst-case scenario analysis with Monte Carlo."""
    print(f"\n{'='*60}")
    print(f"TEST 5: WORST-CASE SCENARIO ANALYSIS ({n_sims:,} sims)")
    print(f"{'='*60}")

    pnl_arr = np.array([t["pnl_pct"] for t in trades])
    wins = np.array([t["won"] for t in trades])
    n = len(pnl_arr)
    overall_wr = float(np.mean(wins))

    results = {}

    # 5a: Worst outcomes over N trades
    for horizon in [50, 100, 200]:
        sim_finals = np.empty(n_sims)
        sim_dds = np.empty(n_sims)
        for i in range(n_sims):
            boot = np.random.choice(pnl_arr, size=min(horizon, n), replace=True)
            eq = compute_equity_curve(boot)
            sim_finals[i] = eq[-1]
            sim_dds[i] = max_drawdown(eq)

        worst_1pct = float(np.percentile(sim_finals, 1))
        worst_5pct = float(np.percentile(sim_finals, 5))
        median_final = float(np.median(sim_finals))

        print(f"  Over {horizon} trades: Worst 1%=${worst_1pct:,.2f}, "
              f"Worst 5%=${worst_5pct:,.2f}, Median=${median_final:,.2f}")

        results[f"horizon_{horizon}_trades"] = {
            "worst_1pct_equity": round(worst_1pct, 2),
            "worst_5pct_equity": round(worst_5pct, 2),
            "median_equity": round(median_final, 2),
            "worst_1pct_return_pct": round((worst_1pct / INITIAL_EQUITY - 1) * 100, 2),
            "worst_5pct_return_pct": round((worst_5pct / INITIAL_EQUITY - 1) * 100, 2),
            "max_dd_percentiles": percentiles(sim_dds * 100),
        }

    # 5b: Consecutive loss expectations
    print(f"\n  Consecutive loss analysis (WR={overall_wr*100:.1f}%):")
    sim_max_losses = np.empty(n_sims)
    for i in range(n_sims):
        boot = np.random.choice(pnl_arr, size=200, replace=True)
        w = boot > 0
        sim_max_losses[i] = max_consecutive(w, False)

    p95_consec = float(np.percentile(sim_max_losses, 95))
    p99_consec = float(np.percentile(sim_max_losses, 99))
    median_consec = float(np.median(sim_max_losses))
    print(f"    Over 200 trades: Median max consecutive losses={median_consec:.0f}, "
          f"95th={p95_consec:.0f}, 99th={p99_consec:.0f}")

    # Theoretical: geometric distribution
    if overall_wr > 0 and overall_wr < 1:
        p_loss = 1.0 - overall_wr
        # P(N consecutive losses) = p_loss^N
        # At 95% confidence over T trades: N where 1-(1-p^N)^T < 0.05
        # Approximate: N ≈ log(0.05/T) / log(p_loss)
        for T in [50, 100, 200]:
            if p_loss > 0:
                n_consec = math.ceil(math.log(0.05 / T) / math.log(p_loss)) if p_loss < 1 else T
                n_consec = max(1, n_consec)
                print(f"    Theoretical 95% CI for {T} trades: up to {n_consec} consecutive losses")

    results["consecutive_losses"] = {
        "over_200_trades": {
            "median": round(median_consec, 0),
            "p95": round(p95_consec, 0),
            "p99": round(p99_consec, 0),
        }
    }

    # 5c: $10K account probability scenarios
    print(f"\n  $10,000 Account Scenarios:")
    scenarios = {}
    for trade_count, label in [(50, "~30 days"), (150, "~90 days"), (300, "~180 days")]:
        sim_finals = np.empty(n_sims)
        for i in range(n_sims):
            boot = np.random.choice(pnl_arr, size=trade_count, replace=True)
            eq = compute_equity_curve(boot, INITIAL_EQUITY)
            sim_finals[i] = eq[-1]

        prob_lose_10 = float(np.mean(sim_finals < INITIAL_EQUITY * 0.90)) * 100
        prob_lose_20 = float(np.mean(sim_finals < INITIAL_EQUITY * 0.80)) * 100
        prob_lose_50 = float(np.mean(sim_finals < INITIAL_EQUITY * 0.50)) * 100
        prob_profitable = float(np.mean(sim_finals > INITIAL_EQUITY)) * 100
        prob_double = float(np.mean(sim_finals >= INITIAL_EQUITY * 2.0)) * 100

        print(f"    After {trade_count} trades ({label}):")
        print(f"      Profitable: {prob_profitable:.1f}% | Lose 10%: {prob_lose_10:.1f}% | "
              f"Lose 20%: {prob_lose_20:.1f}% | Lose 50%: {prob_lose_50:.1f}% | Double: {prob_double:.1f}%")

        scenarios[f"{trade_count}_trades_{label.replace(' ','_').replace('~','')}"] = {
            "trade_count": trade_count,
            "prob_profitable": round(prob_profitable, 1),
            "prob_lose_10pct": round(prob_lose_10, 1),
            "prob_lose_20pct": round(prob_lose_20, 1),
            "prob_lose_50pct": round(prob_lose_50, 1),
            "prob_double": round(prob_double, 1),
            "final_equity_percentiles": percentiles(sim_finals),
        }

    results["account_scenarios_10K"] = scenarios
    return results


# ---------------------------------------------------------------------------
# FINAL VERDICT
# ---------------------------------------------------------------------------

def compute_verdict(strat_results, portfolio_results, regime_results, filter_results, worst_case):
    """Compute overall verdict."""
    # Strategy-level
    edge_strats = sum(1 for r in strat_results.values() if isinstance(r, dict) and r.get("edge_status") == "EDGE")
    total_strats = sum(1 for r in strat_results.values() if isinstance(r, dict) and "edge_status" in r)
    strat_edge_pct = edge_strats / max(total_strats, 1) * 100

    # Portfolio-level
    shuffle_profitable = portfolio_results.get("shuffle", {}).get("pct_profitable", 0)
    subset_profitable = portfolio_results.get("subset_80pct", {}).get("pct_profitable", 0)
    noise_profitable = portfolio_results.get("noise_1pct", {}).get("pct_profitable", 0)
    portfolio_robust = min(shuffle_profitable, subset_profitable, noise_profitable)

    # Regime
    regime_verdict = regime_results.get("_verdict", "UNKNOWN")

    # Account scenarios
    scenarios = worst_case.get("account_scenarios_10K", {})
    medium_term = None
    for key in scenarios:
        if "150" in key or "90" in key:
            medium_term = scenarios[key]
            break

    prob_profitable_90d = medium_term.get("prob_profitable", 0) if medium_term else 0
    prob_lose_20_90d = medium_term.get("prob_lose_20pct", 0) if medium_term else 100

    # Scoring
    score = 0
    reasons = []

    if strat_edge_pct >= 30:
        score += 2
        reasons.append(f"{edge_strats}/{total_strats} strategies show real edge")
    elif strat_edge_pct >= 15:
        score += 1
        reasons.append(f"{edge_strats}/{total_strats} strategies show edge (mediocre)")
    else:
        reasons.append(f"Only {edge_strats}/{total_strats} strategies show edge (poor)")

    if portfolio_robust >= 60:
        score += 2
        reasons.append(f"Portfolio robust: {portfolio_robust:.0f}% profitable across all tests")
    elif portfolio_robust >= 50:
        score += 1
        reasons.append(f"Portfolio marginal: {portfolio_robust:.0f}% profitable")
    else:
        reasons.append(f"Portfolio NOT robust: {portfolio_robust:.0f}% profitable")

    if regime_verdict == "ALL_REGIME_EDGE":
        score += 2
        reasons.append("Edge persists across all market regimes")
    elif regime_verdict == "BULL_ONLY_EDGE":
        score += 0
        reasons.append("WARNING: Edge only in BULL regime (possibly not a real edge)")
    elif regime_verdict == "PARTIAL_EDGE":
        score += 1
        reasons.append("Partial edge across regimes")
    else:
        reasons.append("No regime edge detected")

    if prob_profitable_90d >= 65:
        score += 2
        reasons.append(f"{prob_profitable_90d:.0f}% chance of profit after 90 days")
    elif prob_profitable_90d >= 50:
        score += 1
        reasons.append(f"{prob_profitable_90d:.0f}% chance of profit after 90 days (coin-flip)")
    else:
        reasons.append(f"Only {prob_profitable_90d:.0f}% chance of profit after 90 days")

    if prob_lose_20_90d <= 10:
        score += 1
        reasons.append(f"Low ruin risk: {prob_lose_20_90d:.0f}% chance of -20% in 90 days")
    elif prob_lose_20_90d >= 30:
        score -= 1
        reasons.append(f"HIGH ruin risk: {prob_lose_20_90d:.0f}% chance of -20% in 90 days")

    # Final verdict
    if score >= 7:
        verdict = "EDGE_CONFIRMED"
    elif score >= 4:
        verdict = "EDGE_WEAK"
    elif score >= 2:
        verdict = "NO_EDGE"
    else:
        verdict = "OVERFIT"

    return {
        "verdict": verdict,
        "score": score,
        "max_score": 9,
        "reasons": reasons,
        "details": {
            "strategy_edge_pct": round(strat_edge_pct, 1),
            "portfolio_robust_min_profitable": round(portfolio_robust, 1),
            "regime_verdict": regime_verdict,
            "prob_profitable_90d": round(prob_profitable_90d, 1),
            "prob_ruin_90d": round(prob_lose_20_90d, 1),
        }
    }


# ---------------------------------------------------------------------------
# MARKDOWN REPORT
# ---------------------------------------------------------------------------

def generate_markdown(report):
    """Generate human-readable markdown summary."""
    verdict = report["verdict"]
    v = verdict["verdict"]
    lines = []
    lines.append("# Monte Carlo Validation Report")
    lines.append(f"\n**Generated:** {report['metadata']['generated_at']}")
    lines.append(f"**Total trades analyzed:** {report['metadata']['total_trades']:,}")
    lines.append(f"**Simulations per test:** {report['metadata']['sims_per_test']:,}")
    lines.append(f"**Random seed:** {SEED}")
    lines.append("")

    # Verdict banner
    icon = {"EDGE_CONFIRMED": "PASS", "EDGE_WEAK": "MARGINAL",
            "NO_EDGE": "FAIL", "OVERFIT": "DANGER"}
    lines.append(f"## VERDICT: {v} [{icon.get(v, '?')}]")
    lines.append(f"\n**Score:** {verdict['score']}/{verdict['max_score']}")
    lines.append("")
    for r in verdict["reasons"]:
        lines.append(f"- {r}")
    lines.append("")

    # Test 1: Strategy-Level
    lines.append("---")
    lines.append("## Test 1: Strategy-Level Monte Carlo")
    lines.append("")
    strat = report.get("test1_strategy_level", {})
    edge_count = sum(1 for r in strat.values() if isinstance(r, dict) and r.get("edge_status") == "EDGE")
    weak_count = sum(1 for r in strat.values() if isinstance(r, dict) and r.get("edge_status") == "WEAK")
    no_edge_count = sum(1 for r in strat.values() if isinstance(r, dict) and r.get("edge_status") == "NO_EDGE")
    lines.append(f"**{edge_count} EDGE** | {weak_count} WEAK | {no_edge_count} NO_EDGE")
    lines.append("")
    lines.append("| Strategy | Trades | WR% | Sharpe | %Profitable Sims | %Ruin | p-value | Verdict |")
    lines.append("|----------|--------|-----|--------|-------------------|-------|---------|---------|")
    for name, data in sorted(strat.items(), key=lambda x: -x[1].get("pct_sims_profitable", 0) if isinstance(x[1], dict) else 0):
        if not isinstance(data, dict) or "edge_status" not in data:
            continue
        lines.append(f"| {name} | {data['n_trades']} | {data['actual_win_rate']}% | "
                     f"{data['actual_sharpe']} | {data['pct_sims_profitable']}% | "
                     f"{data['pct_sims_ruin_20dd']}% | {data['p_value']} | {data['edge_status']} |")
    lines.append("")

    # Test 2: Portfolio-Level
    lines.append("---")
    lines.append("## Test 2: Portfolio-Level Monte Carlo")
    lines.append("")
    port = report.get("test2_portfolio_level", {})
    actual = port.get("actual", {})
    lines.append(f"**Actual:** {actual.get('n_trades',0)} trades, "
                 f"Final ${actual.get('final_equity',0):,.2f}, "
                 f"Return {actual.get('total_return_pct',0)}%, "
                 f"Sharpe {actual.get('sharpe',0)}, "
                 f"MaxDD {actual.get('max_dd_pct',0)}%")
    lines.append("")
    for test_name in ["shuffle", "subset_80pct", "noise_1pct"]:
        data = port.get(test_name, {})
        if not data:
            continue
        lines.append(f"### {test_name.replace('_', ' ').title()}")
        lines.append(f"- Profitable simulations: **{data.get('pct_profitable',0)}%**")
        feq = data.get("final_equity", {})
        lines.append(f"- Median final equity: ${feq.get('p50',0):,.2f}")
        lines.append(f"- 5th percentile: ${feq.get('p5',0):,.2f}")
        lines.append(f"- 95th percentile: ${feq.get('p95',0):,.2f}")
        lines.append("")

    # Test 3: Regime
    lines.append("---")
    lines.append("## Test 3: Regime-Conditional Monte Carlo")
    lines.append("")
    regime = report.get("test3_regime_conditional", {})
    regime_verdict = regime.get("_verdict", "UNKNOWN")
    lines.append(f"**Regime Verdict:** {regime_verdict}")
    lines.append("")
    lines.append("| Regime | Trades | WR% | Mean PnL | Sharpe | %Profitable Sims | Edge? |")
    lines.append("|--------|--------|-----|----------|--------|-------------------|-------|")
    for name, data in sorted(regime.items()):
        if name.startswith("_") or not isinstance(data, dict) or "n_trades" not in data:
            continue
        lines.append(f"| {name} | {data['n_trades']} | {data['actual_win_rate']}% | "
                     f"{data['actual_mean_pnl']}% | {data['actual_sharpe']} | "
                     f"{data['pct_sims_profitable']}% | {'YES' if data['has_edge'] else 'NO'} |")
    lines.append("")

    # Test 4: Filters
    lines.append("---")
    lines.append("## Test 4: Filter Combination Stress Test")
    lines.append("")
    filt = report.get("test4_filter_combinations", {})
    ranking = filt.get("_ranking", [])
    lines.append("| Rank | Filter | Trades | WR% | Mean PnL | Sharpe | %Profitable Sims | %Ruin |")
    lines.append("|------|--------|--------|-----|----------|--------|-------------------|-------|")
    for i, entry in enumerate(ranking, 1):
        fname = entry["filter"]
        data = filt.get(fname, {})
        lines.append(f"| {i} | {fname} | {data.get('n_trades','-')} | "
                     f"{data.get('actual_win_rate','-')}% | {data.get('actual_mean_pnl','-')}% | "
                     f"{entry['sharpe']} | {entry['pct_profitable']}% | "
                     f"{data.get('pct_sims_ruin_20dd','-')}% |")
    lines.append("")

    # Test 5: Worst Case
    lines.append("---")
    lines.append("## Test 5: Worst-Case Scenario Analysis")
    lines.append("")
    wc = report.get("test5_worst_case", {})

    lines.append("### Worst outcomes by trade horizon")
    lines.append("")
    lines.append("| Trades | Worst 1% | Worst 5% | Median |")
    lines.append("|--------|----------|----------|--------|")
    for key in ["horizon_50_trades", "horizon_100_trades", "horizon_200_trades"]:
        data = wc.get(key, {})
        if data:
            lines.append(f"| {key.split('_')[1]} | ${data['worst_1pct_equity']:,.2f} | "
                         f"${data['worst_5pct_equity']:,.2f} | ${data['median_equity']:,.2f} |")
    lines.append("")

    # Consecutive losses
    cl = wc.get("consecutive_losses", {}).get("over_200_trades", {})
    if cl:
        lines.append("### Consecutive Loss Expectations (over 200 trades)")
        lines.append(f"- Median max consecutive losses: **{cl.get('median', 0):.0f}**")
        lines.append(f"- 95th percentile: **{cl.get('p95', 0):.0f}**")
        lines.append(f"- 99th percentile: **{cl.get('p99', 0):.0f}**")
        lines.append("")

    # $10K scenarios
    scenarios = wc.get("account_scenarios_10K", {})
    if scenarios:
        lines.append("### $10,000 Account Probability Scenarios")
        lines.append("")
        lines.append("| Timeframe | Profitable | Lose 10% | Lose 20% | Lose 50% | Double |")
        lines.append("|-----------|------------|----------|----------|----------|--------|")
        for key, data in scenarios.items():
            label = key.replace("_trades_", " trades (~").replace("_", " ") + ")"
            lines.append(f"| {data['trade_count']} trades | {data['prob_profitable']}% | "
                         f"{data['prob_lose_10pct']}% | {data['prob_lose_20pct']}% | "
                         f"{data['prob_lose_50pct']}% | {data['prob_double']}% |")
        lines.append("")

    lines.append("---")
    lines.append(f"*Report generated {report['metadata']['generated_at']} | "
                 f"{report['metadata']['total_trades']:,} trades | "
                 f"{report['metadata']['sims_per_test']:,} simulations per test*")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    t0 = time.time()
    print("=" * 60)
    print("INTENSIVE MONTE CARLO BACKTESTING SUITE")
    print("=" * 60)

    # Load data
    print("\nLoading and combining trade data...")
    trades = load_and_combine()
    print(f"  Total trades loaded: {len(trades)}")
    print(f"  Win rate: {sum(1 for t in trades if t['won'])/len(trades)*100:.1f}%")
    print(f"  Mean PnL: {np.mean([t['pnl_pct'] for t in trades]):.3f}%")
    print(f"  Strategies: {len(set(t['strategy'] for t in trades))}")
    print(f"  Regimes: {dict(Counter(t['regime'] for t in trades))}")

    # Run all tests
    test1 = test_strategy_level(trades, STRATEGY_SIMS)
    test2 = test_portfolio_level(trades, PORTFOLIO_SIMS)
    test3 = test_regime_conditional(trades, REGIME_SIMS)
    test4 = test_filter_combinations(trades, FILTER_SIMS)
    test5 = test_worst_case(trades, PORTFOLIO_SIMS)

    # Compute verdict
    verdict = compute_verdict(test1, test2, test3, test4, test5)

    elapsed = time.time() - t0
    print(f"\n{'='*60}")
    print(f"FINAL VERDICT: {verdict['verdict']} (score {verdict['score']}/{verdict['max_score']})")
    for r in verdict["reasons"]:
        print(f"  - {r}")
    print(f"\nCompleted in {elapsed:.1f}s")
    print(f"{'='*60}")

    # Build report
    report = {
        "metadata": {
            "generated_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "total_trades": len(trades),
            "sims_per_test": STRATEGY_SIMS,
            "seed": SEED,
            "elapsed_seconds": round(elapsed, 1),
        },
        "verdict": verdict,
        "test1_strategy_level": test1,
        "test2_portfolio_level": test2,
        "test3_regime_conditional": test3,
        "test4_filter_combinations": test4,
        "test5_worst_case": test5,
    }

    # Save JSON report
    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\nJSON report saved: {REPORT_PATH}")

    # Save Markdown report
    os.makedirs(os.path.dirname(MD_PATH), exist_ok=True)
    md = generate_markdown(report)
    with open(MD_PATH, "w") as f:
        f.write(md)
    print(f"Markdown report saved: {MD_PATH}")

    return report


if __name__ == "__main__":
    main()
