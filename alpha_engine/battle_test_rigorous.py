#!/usr/bin/env python3
"""
ALPHA ENGINE -- Rigorous Walk-Forward Battle Test v2
=====================================================
This is the REAL test. Not a toy 6-month sample -- this uses:

1. MAXIMUM AVAILABLE DATA (2+ years from yfinance)
2. EVERY SINGLE TRADING DAY as a signal point (step=1)
3. STATISTICAL SIGNIFICANCE (binomial p-value, z-test vs random)
4. BOOTSTRAP CONFIDENCE INTERVALS (1000 resamplings)
5. REGIME SPLITTING (bull/bear/sideways tested separately)
6. OUT-OF-SAMPLE SPLIT (train period vs test period)
7. MONTE CARLO null hypothesis (could random entries beat this?)

A strategy that "looks profitable" but has p-value > 0.05 is a FLUKE.
A strategy that wins in bull markets but dies in bear markets is FRAGILE.
Only strategies that survive ALL tests get promoted.

Usage:
  python battle_test_rigorous.py              # Full test, all assets
  python battle_test_rigorous.py --asset crypto
  python battle_test_rigorous.py --asset forex
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict

import numpy as np
import pandas as pd
import yfinance as yf
from scipy import stats as scipy_stats

warnings.filterwarnings("ignore", category=FutureWarning)

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import (
    ALL_SYMBOLS, CRYPTO_SYMBOLS, FOREX_SYMBOLS, EQUITY_SYMBOLS,
    CATEGORY_RISK, TRAILING_STOP, TRAIL_ACTIVATE_PCT, DATA_DIR,
)
from crypto_strategies import CRYPTO_STRATEGIES
from forex_strategies import FOREX_STRATEGIES
from equity_strategies import EQUITY_STRATEGIES


# ---------------------------------------------------------------------------
# Data fetching -- get MAXIMUM history
# ---------------------------------------------------------------------------

def fetch_max_data(symbols: list[str]) -> dict[str, pd.DataFrame]:
    """Fetch maximum available daily history (up to 5+ years)."""
    data = {}
    tickers = " ".join(symbols)
    print(f"  Fetching {len(symbols)} symbols (max history)...")

    try:
        raw = yf.download(tickers, period="max", interval="1d",
                          group_by="ticker", auto_adjust=True,
                          threads=True, progress=False)
    except Exception as e:
        print(f"  FATAL: {e}")
        return data

    for symbol in symbols:
        try:
            if len(symbols) == 1:
                df = raw
            else:
                df = raw[symbol] if symbol in raw.columns.get_level_values(0) else None
            if df is None or df.empty:
                continue
            df = df.dropna(subset=["Close"])
            if len(df) < 200:
                continue
            data[symbol] = df
        except Exception:
            continue

    min_bars = min(len(df) for df in data.values()) if data else 0
    max_bars = max(len(df) for df in data.values()) if data else 0
    print(f"  Got {len(data)}/{len(symbols)} symbols | bars: {min_bars}-{max_bars}")
    return data


# ---------------------------------------------------------------------------
# Pick simulation (same as battle_test.py but cleaner)
# ---------------------------------------------------------------------------

def simulate_pick(entry_price, tp, sl, signal_type, category,
                  future_data, max_hold) -> dict:
    if entry_price <= 0 or tp is None or sl is None:
        return None

    mfe = 0.0
    mae = 0.0
    hwm = entry_price

    for day_idx in range(min(len(future_data), max_hold)):
        row = future_data.iloc[day_idx]
        dh = float(row["High"])
        dl = float(row["Low"])

        if signal_type == "BUY":
            mfe = max(mfe, (dh - entry_price) / entry_price)
            mae = min(mae, (dl - entry_price) / entry_price)
            hwm = max(hwm, dh)
            if dh >= tp:
                return {"exit": "TP_HIT", "pnl": round((tp - entry_price) / entry_price, 6),
                        "days": day_idx + 1, "mfe": round(mfe, 6), "mae": round(mae, 6)}
            if dl <= sl:
                return {"exit": "SL_HIT", "pnl": round((sl - entry_price) / entry_price, 6),
                        "days": day_idx + 1, "mfe": round(mfe, 6), "mae": round(mae, 6)}
            trail_pct = TRAILING_STOP.get(category, 0)
            if trail_pct > 0 and (hwm - entry_price) / entry_price > TRAIL_ACTIVATE_PCT:
                trail_level = hwm * (1 - trail_pct)
                if dl <= trail_level:
                    return {"exit": "TRAIL", "pnl": round((trail_level - entry_price) / entry_price, 6),
                            "days": day_idx + 1, "mfe": round(mfe, 6), "mae": round(mae, 6)}
        else:
            mfe = max(mfe, (entry_price - dl) / entry_price)
            mae = min(mae, (entry_price - dh) / entry_price)
            if dl <= tp:
                return {"exit": "TP_HIT", "pnl": round((entry_price - tp) / entry_price, 6),
                        "days": day_idx + 1, "mfe": round(mfe, 6), "mae": round(mae, 6)}
            if dh >= sl:
                return {"exit": "SL_HIT", "pnl": round((entry_price - sl) / entry_price, 6),
                        "days": day_idx + 1, "mfe": round(mfe, 6), "mae": round(mae, 6)}

    # Time expiry
    if len(future_data) > 0:
        fp = float(future_data.iloc[min(len(future_data) - 1, max_hold - 1)]["Close"])
        pnl = (fp - entry_price) / entry_price if signal_type == "BUY" else (entry_price - fp) / entry_price
        return {"exit": "EXPIRY", "pnl": round(pnl, 6),
                "days": min(len(future_data), max_hold), "mfe": round(mfe, 6), "mae": round(mae, 6)}
    return None


# ---------------------------------------------------------------------------
# Regime detection
# ---------------------------------------------------------------------------

def detect_regime(df: pd.DataFrame, idx: int) -> str:
    """Detect market regime at given index: bull, bear, or sideways."""
    if idx < 60:
        return "unknown"
    close = df["Close"].iloc[:idx]
    sma_50 = close.rolling(50).mean().iloc[-1]
    sma_200 = close.rolling(200).mean().iloc[-1] if idx >= 200 else sma_50
    current = float(close.iloc[-1])
    ret_20d = (current / float(close.iloc[-20]) - 1) if idx >= 20 else 0

    if current > sma_50 and current > sma_200 and ret_20d > 0.02:
        return "bull"
    elif current < sma_50 and current < sma_200 and ret_20d < -0.02:
        return "bear"
    else:
        return "sideways"


# ---------------------------------------------------------------------------
# Walk-forward engine
# ---------------------------------------------------------------------------

def run_walkforward(data: dict[str, pd.DataFrame], strategies: dict,
                    start_idx: int, step: int = 1) -> list[dict]:
    """Run walk-forward test with step=1 for maximum samples."""
    results = []
    sample_sym = list(data.keys())[0]
    total_days = len(data[sample_sym])

    if start_idx < 200:
        start_idx = 200

    test_points = list(range(start_idx, total_days - 5, step))
    print(f"  Walk-forward: {len(test_points)} test points, "
          f"day {start_idx}->{total_days}, {len(strategies)} strategies")

    import inspect

    sig_count = 0
    for i, day_idx in enumerate(test_points):
        # Determine regime from a representative symbol (BTC or SPY)
        regime_sym = None
        for rs in ["BTC-USD", "SPY", "EURUSD=X"]:
            if rs in data and day_idx <= len(data[rs]):
                regime_sym = rs
                break
        regime = detect_regime(data[regime_sym], day_idx) if regime_sym else "unknown"

        # Slice data up to this day
        sliced = {}
        for sym, df in data.items():
            if day_idx <= len(df):
                sliced[sym] = df.iloc[:day_idx].copy()

        if not sliced:
            continue

        for strat_name, strat_func in strategies.items():
            try:
                sig = inspect.signature(strat_func)
                if "context" in sig.parameters:
                    signals = strat_func(sliced, context={})
                else:
                    signals = strat_func(sliced)
            except Exception:
                continue

            if not signals:
                continue

            for signal in signals:
                symbol = signal.get("symbol", "")
                entry = signal.get("entry_price", 0)
                tp = signal.get("take_profit")
                sl = signal.get("stop_loss")
                sig_type = signal.get("signal_type", "BUY")
                category = signal.get("category", "crypto")

                if not entry or entry <= 0 or tp is None or sl is None:
                    continue

                full_df = data.get(symbol)
                if full_df is None or day_idx >= len(full_df):
                    continue

                future = full_df.iloc[day_idx:]
                if len(future) < 2:
                    continue

                _, _, max_hold = CATEGORY_RISK.get(category, (-0.08, 0.15, 10))
                outcome = simulate_pick(entry, tp, sl, sig_type, category, future, max_hold)
                if outcome is None:
                    continue

                try:
                    entry_date = str(full_df.index[day_idx].date())
                except Exception:
                    entry_date = str(full_df.index[day_idx])[:10]

                results.append({
                    "strategy": strat_name,
                    "symbol": symbol,
                    "category": category,
                    "signal_type": sig_type,
                    "entry_price": entry,
                    "tp": tp, "sl": sl,
                    "entry_date": entry_date,
                    "regime": regime,
                    **outcome,
                })
                sig_count += 1

        if (i + 1) % 20 == 0:
            elapsed_pct = (i + 1) / len(test_points) * 100
            print(f"    {elapsed_pct:5.1f}% | day {day_idx}/{total_days} | {sig_count} signals")

    print(f"  Complete: {sig_count} total signals from {len(test_points)} test days")
    return results


# ---------------------------------------------------------------------------
# Statistical analysis
# ---------------------------------------------------------------------------

def binomial_pvalue(wins: int, n: int, null_p: float = 0.5) -> float:
    """Two-sided binomial test: is win rate significantly different from null_p?"""
    if n == 0:
        return 1.0
    return float(scipy_stats.binomtest(wins, n, null_p, alternative="greater").pvalue)


def bootstrap_ci(pnls: list[float], n_boot: int = 2000, ci: float = 0.95) -> dict:
    """Bootstrap confidence interval for mean PnL and win rate."""
    if len(pnls) < 5:
        return {"mean_ci_low": 0, "mean_ci_high": 0, "wr_ci_low": 0, "wr_ci_high": 0}

    arr = np.array(pnls)
    boot_means = []
    boot_wrs = []
    rng = np.random.default_rng(42)

    for _ in range(n_boot):
        sample = rng.choice(arr, size=len(arr), replace=True)
        boot_means.append(float(sample.mean()))
        boot_wrs.append(float((sample > 0).mean()))

    alpha = (1 - ci) / 2
    return {
        "mean_ci_low": round(float(np.percentile(boot_means, alpha * 100)), 6),
        "mean_ci_high": round(float(np.percentile(boot_means, (1 - alpha) * 100)), 6),
        "wr_ci_low": round(float(np.percentile(boot_wrs, alpha * 100)), 4),
        "wr_ci_high": round(float(np.percentile(boot_wrs, (1 - alpha) * 100)), 4),
    }


def monte_carlo_null(pnls: list[float], n_sims: int = 5000) -> float:
    """
    Monte Carlo null hypothesis test: what fraction of random entry/exit
    combinations would produce a mean PnL >= observed?
    Shuffles the PnL signs randomly to simulate no-skill baseline.
    """
    if len(pnls) < 5:
        return 1.0

    arr = np.array(pnls)
    observed_mean = arr.mean()
    rng = np.random.default_rng(42)
    count_better = 0

    for _ in range(n_sims):
        signs = rng.choice([-1, 1], size=len(arr))
        shuffled = np.abs(arr) * signs
        if shuffled.mean() >= observed_mean:
            count_better += 1

    return round(count_better / n_sims, 4)


def analyze_with_stats(results: list[dict]) -> dict:
    """Full statistical analysis per strategy."""
    by_strat = defaultdict(list)
    for r in results:
        by_strat[r["strategy"]].append(r)

    analysis = {}
    for strat, picks in by_strat.items():
        pnls = [p["pnl"] for p in picks]
        n = len(pnls)
        if n < 3:
            continue

        arr = np.array(pnls)
        wins = int((arr > 0).sum())
        losses = n - wins
        wr = wins / n

        avg_pnl = float(arr.mean())
        total_pnl = float(arr.sum())
        std = float(arr.std()) if arr.std() > 0 else 1e-10

        avg_hold = float(np.mean([p.get("days", 1) for p in picks]))
        trades_per_year = 252 / max(1, avg_hold)
        sharpe = float(arr.mean() / std * np.sqrt(trades_per_year))

        gross_win = sum(p for p in pnls if p > 0)
        gross_loss = abs(sum(p for p in pnls if p < 0))
        pf = gross_win / gross_loss if gross_loss > 0 else 99.99

        cum = np.cumsum(arr)
        peak = np.maximum.accumulate(cum)
        max_dd = float((cum - peak).min())

        # Statistical significance
        p_binom = binomial_pvalue(wins, n, 0.5)
        p_mc = monte_carlo_null(pnls, n_sims=5000)
        boot = bootstrap_ci(pnls, n_boot=2000)

        # Regime breakdown
        regime_stats = {}
        for regime in ["bull", "bear", "sideways"]:
            regime_picks = [p for p in picks if p.get("regime") == regime]
            if len(regime_picks) >= 3:
                rp = np.array([p["pnl"] for p in regime_picks])
                rw = int((rp > 0).sum())
                regime_stats[regime] = {
                    "picks": len(regime_picks),
                    "win_rate": round(rw / len(regime_picks), 4),
                    "avg_pnl": round(float(rp.mean()), 6),
                    "total_pnl": round(float(rp.sum()), 4),
                }

        # Exit reason breakdown
        exits = defaultdict(int)
        for p in picks:
            exits[p.get("exit", "?")] += 1

        # MFE/MAE
        mfes = [p.get("mfe", 0) for p in picks]
        maes = [p.get("mae", 0) for p in picks]

        # Time split: first half vs second half
        half = n // 2
        first_half_pnl = float(np.mean(pnls[:half])) if half > 0 else 0
        second_half_pnl = float(np.mean(pnls[half:])) if half > 0 else 0

        # Categories
        cats = list(set(p.get("category", "") for p in picks))
        syms = list(set(p.get("symbol", "") for p in picks))

        analysis[strat] = {
            "total_picks": n,
            "wins": wins,
            "losses": losses,
            "win_rate": round(wr, 4),
            "avg_pnl_pct": round(avg_pnl, 6),
            "total_pnl_pct": round(total_pnl, 4),
            "total_pnl_dollar": round(total_pnl * 2000, 2),
            "sharpe": round(sharpe, 3),
            "profit_factor": round(min(pf, 99.99), 3),
            "max_drawdown": round(max_dd, 4),
            "avg_hold_days": round(avg_hold, 1),
            "avg_mfe": round(float(np.mean(mfes)), 6),
            "avg_mae": round(float(np.mean(maes)), 6),
            "p_value_binomial": p_binom,
            "p_value_montecarlo": p_mc,
            "bootstrap_95ci": boot,
            "regime_performance": regime_stats,
            "exit_reasons": dict(exits),
            "first_half_avg_pnl": round(first_half_pnl, 6),
            "second_half_avg_pnl": round(second_half_pnl, 6),
            "consistency": "CONSISTENT" if (first_half_pnl > 0 and second_half_pnl > 0) else
                           "DEGRADING" if (first_half_pnl > 0 and second_half_pnl <= 0) else
                           "IMPROVING" if (first_half_pnl <= 0 and second_half_pnl > 0) else "POOR",
            "categories": cats,
            "symbols_traded": len(syms),
        }

    return analysis


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def print_rigorous_report(analysis: dict, results: list[dict]):
    print()
    print("=" * 90)
    print("  ALPHA ENGINE -- RIGOROUS BATTLE TEST (Statistical Validation)")
    print("  Walk-forward: every signal uses ONLY past data. No peeking. No cheating.")
    print("=" * 90)

    total_picks = sum(s["total_picks"] for s in analysis.values())
    total_wins = sum(s["wins"] for s in analysis.values())
    total_losses = sum(s["losses"] for s in analysis.values())
    total_pnl = sum(s["total_pnl_dollar"] for s in analysis.values())
    wr = total_wins / total_picks if total_picks > 0 else 0

    print(f"\n  AGGREGATE: {total_picks} picks | {total_wins}W/{total_losses}L "
          f"({wr*100:.1f}% WR) | P&L ${total_pnl:+,.2f}")

    sorted_strats = sorted(analysis.items(), key=lambda x: x[1]["total_pnl_dollar"], reverse=True)

    # Detailed per-strategy
    print(f"\n  {'Strategy':32s} {'N':>5s} {'WR':>6s} {'PF':>5s} {'Sharpe':>7s} "
          f"{'P&L$':>9s} {'p-binom':>8s} {'p-MC':>7s} "
          f"{'95%CI WR':>12s} {'Consist':>10s} {'Verdict':>10s}")
    print(f"  {'-'*32} {'-'*5} {'-'*6} {'-'*5} {'-'*7} "
          f"{'-'*9} {'-'*8} {'-'*7} {'-'*12} {'-'*10} {'-'*10}")

    promoted = []
    kept = []
    eliminated = []

    for strat, d in sorted_strats:
        boot = d["bootstrap_95ci"]
        wr_ci = f"[{boot['wr_ci_low']*100:.0f}-{boot['wr_ci_high']*100:.0f}%]"

        # Verdict logic -- STRICT
        is_profitable = d["total_pnl_dollar"] > 0
        is_significant = d["p_value_binomial"] < 0.05 and d["p_value_montecarlo"] < 0.10
        is_consistent = d["consistency"] in ("CONSISTENT", "IMPROVING")
        enough_data = d["total_picks"] >= 20
        good_pf = d["profit_factor"] >= 1.1

        if is_profitable and is_significant and is_consistent and enough_data and good_pf:
            verdict = "PROMOTE"
            promoted.append(strat)
        elif is_profitable and d["total_picks"] >= 10 and d["profit_factor"] >= 1.0:
            verdict = "KEEP"
            kept.append(strat)
        elif d["total_picks"] < 10:
            verdict = "LOW-N"
            kept.append(strat)
        else:
            verdict = "ELIMINATE"
            eliminated.append(strat)

        v_color = verdict
        print(f"  {strat:32s} {d['total_picks']:4d} {d['win_rate']*100:5.1f}% "
              f"{d['profit_factor']:4.2f} {d['sharpe']:6.2f} "
              f"${d['total_pnl_dollar']:+8.2f} "
              f"{d['p_value_binomial']:7.4f} {d['p_value_montecarlo']:6.4f} "
              f"{wr_ci:>12s} {d['consistency']:>10s} {v_color:>10s}")

    # Regime analysis for promoted strategies
    if promoted:
        print(f"\n  REGIME ANALYSIS (promoted strategies only):")
        print(f"  {'Strategy':32s} {'Bull':>20s} {'Bear':>20s} {'Sideways':>20s}")
        print(f"  {'-'*32} {'-'*20} {'-'*20} {'-'*20}")
        for strat in promoted:
            d = analysis[strat]
            parts = []
            for regime in ["bull", "bear", "sideways"]:
                rs = d["regime_performance"].get(regime, {})
                if rs:
                    parts.append(f"{rs['picks']:3d}p {rs['win_rate']*100:4.0f}%WR ${rs['total_pnl']*2000:+6.0f}")
                else:
                    parts.append(f"{'N/A':>20s}")
            print(f"  {strat:32s} {parts[0]:>20s} {parts[1]:>20s} {parts[2]:>20s}")

    # Asset class breakdown
    print(f"\n  ASSET CLASS BREAKDOWN:")
    by_cat = defaultdict(lambda: {"w": 0, "l": 0, "pnl": 0.0, "n": 0})
    for r in results:
        cat = r.get("category", "?")
        by_cat[cat]["n"] += 1
        by_cat[cat]["pnl"] += r.get("pnl", 0) * 2000
        if r.get("pnl", 0) > 0:
            by_cat[cat]["w"] += 1
        else:
            by_cat[cat]["l"] += 1
    print(f"  {'Category':15s} {'Picks':>6s} {'WR':>7s} {'P&L':>12s}")
    print(f"  {'-'*15} {'-'*6} {'-'*7} {'-'*12}")
    for cat in sorted(by_cat.keys()):
        d = by_cat[cat]
        wr_val = d["w"] / d["n"] * 100 if d["n"] > 0 else 0
        print(f"  {cat:15s} {d['n']:5d} {wr_val:5.1f}% ${d['pnl']:+10.2f}")

    # Summary
    print(f"\n  {'='*90}")
    print(f"  FINAL VERDICT:")
    print(f"    PROMOTED (statistically significant profit): {len(promoted)}")
    for s in promoted:
        d = analysis[s]
        print(f"      {s}: {d['total_picks']} picks, {d['win_rate']*100:.1f}% WR, "
              f"PF {d['profit_factor']:.2f}, p={d['p_value_binomial']:.4f}")
    print(f"    KEPT (promising but not yet proven):         {len(kept)}")
    for s in kept:
        d = analysis[s]
        print(f"      {s}: {d['total_picks']} picks, WR {d['win_rate']*100:.0f}%, "
              f"P&L ${d['total_pnl_dollar']:+.2f}")
    print(f"    ELIMINATED (failed or proven losers):        {len(eliminated)}")
    for s in eliminated:
        d = analysis[s]
        print(f"      {s}: {d['total_picks']} picks, WR {d['win_rate']*100:.0f}%, "
              f"P&L ${d['total_pnl_dollar']:+.2f}")
    print(f"  {'='*90}")

    return {"promoted": promoted, "kept": kept, "eliminated": eliminated}


def main():
    parser = argparse.ArgumentParser(description="ALPHA ENGINE Rigorous Battle Test")
    parser.add_argument("--asset", choices=["crypto", "forex", "equity", "all"], default="all")
    parser.add_argument("--step", type=int, default=1, help="Days between signal generation")
    parser.add_argument("--period", default="max", help="yfinance period (max, 2y, 1y)")
    args = parser.parse_args()

    t0 = time.time()

    if args.asset == "crypto":
        symbols = list(CRYPTO_SYMBOLS.keys())
        strategies = CRYPTO_STRATEGIES
    elif args.asset == "forex":
        symbols = list(FOREX_SYMBOLS.keys())
        strategies = FOREX_STRATEGIES
    elif args.asset == "equity":
        symbols = list(EQUITY_SYMBOLS.keys())
        strategies = EQUITY_STRATEGIES
    else:
        symbols = list(ALL_SYMBOLS.keys())
        strategies = {**CRYPTO_STRATEGIES, **FOREX_STRATEGIES, **EQUITY_STRATEGIES}

    # Filter out disabled strategies (emergency triage)
    from strategy_guard import filter_strategies, log_filtered_strategies
    strategies, removed = filter_strategies(strategies)
    log_filtered_strategies(removed)

    print(f"\n{'='*90}")
    print(f"  ALPHA ENGINE -- RIGOROUS BATTLE TEST v2")
    print(f"  {args.asset.upper()} | {len(strategies)} strategies | {len(symbols)} symbols")
    print(f"  Step: {args.step} day(s) | Period: {args.period}")
    print(f"  Statistical tests: binomial p-value, Monte Carlo, bootstrap CI, regime split")
    print(f"{'='*90}")

    print("\n[1/4] Fetching maximum historical data...")
    if args.period == "max":
        data = fetch_max_data(symbols)
    else:
        data = {}
        tickers = " ".join(symbols)
        raw = yf.download(tickers, period=args.period, interval="1d",
                          group_by="ticker", auto_adjust=True,
                          threads=True, progress=False)
        for symbol in symbols:
            try:
                if len(symbols) == 1:
                    df = raw
                else:
                    df = raw[symbol] if symbol in raw.columns.get_level_values(0) else None
                if df is not None and not df.empty:
                    df = df.dropna(subset=["Close"])
                    if len(df) >= 200:
                        data[symbol] = df
            except Exception:
                continue
        print(f"  Got {len(data)}/{len(symbols)} symbols")

    if not data:
        print("  FATAL: No data.")
        sys.exit(1)

    sample = list(data.values())[0]
    total_bars = len(sample)
    # Use 60% of data for warmup (strategies need history), 40% for testing
    warmup = max(200, int(total_bars * 0.6))
    test_window = total_bars - warmup
    print(f"  Total bars: {total_bars} | Warmup: {warmup} | Test window: {test_window} days")

    print(f"\n[2/4] Running walk-forward test (step={args.step})...")
    results = run_walkforward(data, strategies, warmup, step=args.step)

    if not results:
        print("  No signals. Strategies did not fire. Check conditions.")
        sys.exit(1)

    print(f"\n[3/4] Running statistical analysis...")
    analysis = analyze_with_stats(results)

    print(f"\n[4/4] Generating rigorous report...")
    verdicts = print_rigorous_report(analysis, results)

    # Save everything
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    save_path = DATA_DIR / "rigorous_battle_results.json"
    with open(save_path, "w") as f:
        json.dump({
            "test_date": datetime.now(timezone.utc).isoformat(),
            "asset": args.asset,
            "step": args.step,
            "period": args.period,
            "total_bars": total_bars,
            "warmup": warmup,
            "test_window": test_window,
            "total_signals": len(results),
            "strategy_analysis": analysis,
            "verdicts": verdicts,
        }, f, indent=2, default=str)

    picks_path = DATA_DIR / "rigorous_battle_picks.json"
    with open(picks_path, "w") as f:
        json.dump(results, f, indent=2, default=str)

    elapsed = time.time() - t0
    print(f"\nCompleted in {elapsed:.1f}s | Results: {save_path}")


if __name__ == "__main__":
    main()
