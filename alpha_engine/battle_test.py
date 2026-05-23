#!/usr/bin/env python3
"""
ALPHA ENGINE -- Walk-Forward Battle Test
=========================================
Real battle test: runs every strategy against REAL historical data.
Walk-forward = each signal uses ONLY past data, then validated against
actual future prices. No peeking, no cheating.

For each trading day in the test window:
  1. Generate signals using ONLY data available up to that day
  2. Record entry price, TP, SL
  3. Walk forward day-by-day checking if TP/SL was hit using actual OHLC
  4. Record outcome (WIN/LOSS/EXPIRED)

This is identical to live trading with a time machine -- real data, real signals,
real outcomes. Strategies that can't make money here get ELIMINATED.

Usage:
  python battle_test.py                    # Full 6-month test, all assets
  python battle_test.py --months 3         # 3-month test
  python battle_test.py --crypto-only      # Crypto strategies only
  python battle_test.py --forex-only       # Forex strategies only
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from collections import defaultdict

import numpy as np
import pandas as pd
import yfinance as yf

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import (
    ALL_SYMBOLS, CRYPTO_SYMBOLS, FOREX_SYMBOLS, EQUITY_SYMBOLS,
    CATEGORY_RISK, TRAILING_STOP, TRAIL_ACTIVATE_PCT, DATA_DIR,
)
from crypto_strategies import CRYPTO_STRATEGIES
from forex_strategies import FOREX_STRATEGIES
from equity_strategies import EQUITY_STRATEGIES


def fetch_historical_data(symbols: list[str], period: str = "1y") -> dict[str, pd.DataFrame]:
    """Fetch full historical OHLCV for all symbols."""
    data = {}
    tickers = " ".join(symbols)
    print(f"  Fetching {len(symbols)} symbols ({period})...")

    try:
        raw = yf.download(tickers, period=period, interval="1d",
                          group_by="ticker", auto_adjust=True,
                          threads=True, progress=False)
    except Exception as e:
        print(f"  FATAL: yfinance download failed: {e}")
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
            if len(df) < 50:
                continue
            data[symbol] = df
        except Exception:
            continue

    print(f"  Got data for {len(data)}/{len(symbols)} symbols")
    return data


def simulate_pick(entry_price: float, tp: float, sl: float,
                  signal_type: str, category: str,
                  future_data: pd.DataFrame, max_hold: int) -> dict:
    """
    Simulate a single pick against actual future OHLC data.
    Returns outcome dict with exit_reason, pnl, hold_days, mfe, mae.
    """
    if entry_price <= 0 or tp is None or sl is None:
        return {"exit_reason": "INVALID", "pnl_pct": 0, "hold_days": 0}

    mfe = 0.0
    mae = 0.0
    hwm = entry_price

    for day_idx in range(min(len(future_data), max_hold)):
        row = future_data.iloc[day_idx]
        day_high = float(row["High"])
        day_low = float(row["Low"])
        day_close = float(row["Close"])

        if signal_type == "BUY":
            mfe = max(mfe, (day_high - entry_price) / entry_price)
            mae = min(mae, (day_low - entry_price) / entry_price)
            hwm = max(hwm, day_high)

            if day_high >= tp:
                pnl = (tp - entry_price) / entry_price
                return {"exit_reason": "TP_HIT", "pnl_pct": round(pnl, 6),
                        "hold_days": day_idx + 1, "mfe": round(mfe, 6),
                        "mae": round(mae, 6), "exit_price": tp}
            if day_low <= sl:
                pnl = (sl - entry_price) / entry_price
                return {"exit_reason": "SL_HIT", "pnl_pct": round(pnl, 6),
                        "hold_days": day_idx + 1, "mfe": round(mfe, 6),
                        "mae": round(mae, 6), "exit_price": sl}

            # Trailing stop
            trail_pct = TRAILING_STOP.get(category, 0)
            if trail_pct > 0:
                profit_from_hwm = (hwm - entry_price) / entry_price
                if profit_from_hwm > TRAIL_ACTIVATE_PCT:
                    trail_level = hwm * (1 - trail_pct)
                    if day_low <= trail_level:
                        pnl = (trail_level - entry_price) / entry_price
                        return {"exit_reason": "TRAILING_STOP", "pnl_pct": round(pnl, 6),
                                "hold_days": day_idx + 1, "mfe": round(mfe, 6),
                                "mae": round(mae, 6), "exit_price": round(trail_level, 8)}

        elif signal_type == "SELL":
            mfe = max(mfe, (entry_price - day_low) / entry_price)
            mae = min(mae, (entry_price - day_high) / entry_price)
            hwm = min(hwm, day_low)

            if day_low <= tp:
                pnl = (entry_price - tp) / entry_price
                return {"exit_reason": "TP_HIT", "pnl_pct": round(pnl, 6),
                        "hold_days": day_idx + 1, "mfe": round(mfe, 6),
                        "mae": round(mae, 6), "exit_price": tp}
            if day_high >= sl:
                pnl = (entry_price - sl) / entry_price
                return {"exit_reason": "SL_HIT", "pnl_pct": round(pnl, 6),
                        "hold_days": day_idx + 1, "mfe": round(mfe, 6),
                        "mae": round(mae, 6), "exit_price": sl}

    # Time expiry
    if len(future_data) > 0:
        final_price = float(future_data.iloc[min(len(future_data) - 1, max_hold - 1)]["Close"])
        if signal_type == "BUY":
            pnl = (final_price - entry_price) / entry_price
        else:
            pnl = (entry_price - final_price) / entry_price
        return {"exit_reason": "TIME_EXPIRY", "pnl_pct": round(pnl, 6),
                "hold_days": min(len(future_data), max_hold),
                "mfe": round(mfe, 6), "mae": round(mae, 6),
                "exit_price": round(final_price, 8)}

    return {"exit_reason": "NO_DATA", "pnl_pct": 0, "hold_days": 0}


def run_battle_test(data: dict[str, pd.DataFrame], strategies: dict,
                    test_start_idx: int, step_days: int = 5) -> list[dict]:
    """
    Walk-forward battle test.
    For every `step_days` trading days starting from test_start_idx:
      - Slice data up to that day (strategies see only past)
      - Run all strategies
      - Simulate each signal against actual future data
    """
    all_results = []
    sample_sym = list(data.keys())[0]
    total_days = len(data[sample_sym])

    # We need at least 200 bars of history for strategies + some future for validation
    if test_start_idx < 200:
        test_start_idx = 200

    print(f"\n  Walk-forward: day {test_start_idx} to {total_days}, step={step_days}")
    print(f"  Testing {len(strategies)} strategies across {len(data)} symbols")

    signal_count = 0
    test_days = list(range(test_start_idx, total_days - 5, step_days))

    for i, day_idx in enumerate(test_days):
        # Slice data: strategies see only up to day_idx
        sliced_data = {}
        for sym, df in data.items():
            if day_idx <= len(df):
                sliced_data[sym] = df.iloc[:day_idx].copy()

        if not sliced_data:
            continue

        # Run each strategy
        for strat_name, strat_func in strategies.items():
            try:
                import inspect
                sig = inspect.signature(strat_func)
                if "context" in sig.parameters:
                    signals = strat_func(sliced_data, context={})
                else:
                    signals = strat_func(sliced_data)
            except Exception:
                continue

            if not signals:
                continue

            for signal in signals:
                symbol = signal.get("symbol", "")
                entry_price = signal.get("entry_price", 0)
                tp = signal.get("take_profit")
                sl = signal.get("stop_loss")
                signal_type = signal.get("signal_type", "BUY")
                category = signal.get("category", "crypto")

                if not entry_price or entry_price <= 0:
                    continue
                if tp is None or sl is None:
                    continue

                # Get future data for this symbol
                full_df = data.get(symbol)
                if full_df is None or day_idx >= len(full_df):
                    continue

                future = full_df.iloc[day_idx:]
                if len(future) < 2:
                    continue

                _, _, max_hold = CATEGORY_RISK.get(category, (-0.08, 0.15, 10))
                outcome = simulate_pick(entry_price, tp, sl, signal_type,
                                        category, future, max_hold)

                entry_date = str(full_df.index[day_idx].date()) if hasattr(full_df.index[day_idx], 'date') else str(full_df.index[day_idx])[:10]

                result = {
                    "strategy": strat_name,
                    "symbol": symbol,
                    "category": category,
                    "signal_type": signal_type,
                    "entry_price": entry_price,
                    "take_profit": tp,
                    "stop_loss": sl,
                    "entry_date": entry_date,
                    "confidence": signal.get("confidence", 0),
                    "rsi_at_entry": signal.get("rsi_at_entry"),
                    "reason": signal.get("reason", ""),
                    **outcome,
                }
                all_results.append(result)
                signal_count += 1

        if (i + 1) % 10 == 0:
            print(f"    Day {day_idx}/{total_days}: {signal_count} total signals so far...")

    print(f"  Battle test complete: {signal_count} signals tested")
    return all_results


def analyze_results(results: list[dict]) -> dict:
    """Analyze battle test results per strategy."""
    by_strategy = defaultdict(list)
    for r in results:
        by_strategy[r["strategy"]].append(r)

    analysis = {}
    for strat, picks in by_strategy.items():
        pnls = [p["pnl_pct"] for p in picks]
        wins = sum(1 for p in pnls if p > 0)
        losses = sum(1 for p in pnls if p <= 0)
        n = len(pnls)
        if n == 0:
            continue

        arr = np.array(pnls)
        win_rate = wins / n
        avg_pnl = float(arr.mean())
        total_pnl = float(arr.sum())
        std = float(arr.std()) if arr.std() > 0 else 1e-10
        sharpe = float(arr.mean() / std * np.sqrt(252 / max(1, np.mean([p.get("hold_days", 1) for p in picks]))))

        gross_profit = sum(p for p in pnls if p > 0)
        gross_loss = abs(sum(p for p in pnls if p < 0))
        pf = gross_profit / gross_loss if gross_loss > 0 else 99.99

        cum = np.cumsum(arr)
        peak = np.maximum.accumulate(cum)
        max_dd = float((cum - peak).min()) if len(cum) > 0 else 0

        exit_reasons = defaultdict(int)
        for p in picks:
            exit_reasons[p.get("exit_reason", "UNKNOWN")] += 1

        mfes = [p.get("mfe", 0) for p in picks]
        maes = [p.get("mae", 0) for p in picks]

        # Categories involved
        cats = set(p.get("category", "") for p in picks)
        symbols_traded = set(p.get("symbol", "") for p in picks)

        analysis[strat] = {
            "total_picks": n,
            "wins": wins,
            "losses": losses,
            "win_rate": round(win_rate, 4),
            "avg_pnl_pct": round(avg_pnl, 6),
            "total_pnl_pct": round(total_pnl, 4),
            "total_pnl_dollar": round(total_pnl * 2000, 2),
            "sharpe": round(sharpe, 3),
            "profit_factor": round(min(pf, 99.99), 3),
            "max_drawdown_pct": round(max_dd, 4),
            "avg_mfe": round(float(np.mean(mfes)), 6) if mfes else 0,
            "avg_mae": round(float(np.mean(maes)), 6) if maes else 0,
            "exit_reasons": dict(exit_reasons),
            "categories": list(cats),
            "symbols_traded": len(symbols_traded),
            "avg_hold_days": round(float(np.mean([p.get("hold_days", 0) for p in picks])), 1),
        }

    return analysis


def print_battle_report(analysis: dict, results: list[dict]):
    """Print the full battle test report with elimination recommendations."""
    print()
    print("=" * 80)
    print("  ALPHA ENGINE -- WALK-FORWARD BATTLE TEST RESULTS")
    print("  All signals generated using ONLY past data, validated against real future prices")
    print("=" * 80)

    total_picks = sum(s["total_picks"] for s in analysis.values())
    total_wins = sum(s["wins"] for s in analysis.values())
    total_losses = sum(s["losses"] for s in analysis.values())
    total_pnl = sum(s["total_pnl_dollar"] for s in analysis.values())
    overall_wr = total_wins / total_picks if total_picks > 0 else 0

    print(f"\n  OVERALL: {total_picks} picks | {total_wins}W/{total_losses}L "
          f"({overall_wr*100:.1f}% WR) | ${total_pnl:+,.2f} P&L")

    # Sort strategies by total P&L
    sorted_strats = sorted(analysis.items(), key=lambda x: x[1]["total_pnl_dollar"], reverse=True)

    # Winners
    winners = [(s, d) for s, d in sorted_strats if d["total_pnl_dollar"] > 0 and d["total_picks"] >= 3]
    losers = [(s, d) for s, d in sorted_strats if d["total_pnl_dollar"] <= 0 and d["total_picks"] >= 3]
    insufficient = [(s, d) for s, d in sorted_strats if d["total_picks"] < 3]

    print(f"\n  WINNERS ({len(winners)} strategies making money):")
    print(f"  {'Strategy':35s} {'Picks':>5s} {'WR':>6s} {'PF':>6s} {'Sharpe':>7s} "
          f"{'P&L':>10s} {'MaxDD':>7s} {'AvgMFE':>7s}")
    print(f"  {'-'*35} {'-'*5} {'-'*6} {'-'*6} {'-'*7} {'-'*10} {'-'*7} {'-'*7}")
    for s, d in winners:
        print(f"  {s:35s} {d['total_picks']:4d} {d['win_rate']*100:5.1f}% "
              f"{d['profit_factor']:5.2f} {d['sharpe']:6.2f} "
              f"${d['total_pnl_dollar']:+8.2f} {d['max_drawdown_pct']*100:5.1f}% "
              f"{d['avg_mfe']*100:5.1f}%")

    print(f"\n  LOSERS ({len(losers)} strategies losing money -- ELIMINATE THESE):")
    print(f"  {'Strategy':35s} {'Picks':>5s} {'WR':>6s} {'PF':>6s} {'Sharpe':>7s} "
          f"{'P&L':>10s} {'MaxDD':>7s} {'AvgMAE':>7s}")
    print(f"  {'-'*35} {'-'*5} {'-'*6} {'-'*6} {'-'*7} {'-'*10} {'-'*7} {'-'*7}")
    for s, d in losers:
        print(f"  {s:35s} {d['total_picks']:4d} {d['win_rate']*100:5.1f}% "
              f"{d['profit_factor']:5.2f} {d['sharpe']:6.2f} "
              f"${d['total_pnl_dollar']:+8.2f} {d['max_drawdown_pct']*100:5.1f}% "
              f"{d['avg_mae']*100:5.1f}%")

    if insufficient:
        print(f"\n  INSUFFICIENT DATA ({len(insufficient)} strategies -- too few signals):")
        for s, d in insufficient:
            print(f"    {s:35s} {d['total_picks']} picks -- need more data")

    # Asset class breakdown
    print(f"\n  ASSET CLASS BREAKDOWN:")
    by_cat = defaultdict(lambda: {"wins": 0, "losses": 0, "pnl": 0, "picks": 0})
    for r in results:
        cat = r.get("category", "unknown")
        by_cat[cat]["picks"] += 1
        by_cat[cat]["pnl"] += r.get("pnl_pct", 0) * 2000
        if r.get("pnl_pct", 0) > 0:
            by_cat[cat]["wins"] += 1
        else:
            by_cat[cat]["losses"] += 1

    print(f"  {'Category':15s} {'Picks':>6s} {'WR':>7s} {'P&L':>12s}")
    print(f"  {'-'*15} {'-'*6} {'-'*7} {'-'*12}")
    for cat in sorted(by_cat.keys()):
        d = by_cat[cat]
        wr = d["wins"] / d["picks"] * 100 if d["picks"] > 0 else 0
        print(f"  {cat:15s} {d['picks']:5d} {wr:5.1f}% ${d['pnl']:+10.2f}")

    # Elimination list
    print(f"\n  {'='*80}")
    print(f"  ELIMINATION RECOMMENDATIONS:")
    print(f"  {'='*80}")

    eliminate = []
    keep = []
    promote = []

    for s, d in sorted_strats:
        if d["total_picks"] < 3:
            continue
        if d["win_rate"] < 0.35 or d["profit_factor"] < 0.8 or d["total_pnl_dollar"] < -50:
            eliminate.append(s)
            print(f"  ELIMINATE: {s} (WR={d['win_rate']*100:.0f}%, PF={d['profit_factor']:.2f}, "
                  f"P&L=${d['total_pnl_dollar']:+.2f})")
        elif d["win_rate"] >= 0.55 and d["profit_factor"] >= 1.3 and d["total_pnl_dollar"] > 100:
            promote.append(s)
            print(f"  PROMOTE:   {s} (WR={d['win_rate']*100:.0f}%, PF={d['profit_factor']:.2f}, "
                  f"P&L=${d['total_pnl_dollar']:+.2f})")
        else:
            keep.append(s)

    if keep:
        print(f"\n  KEEP ({len(keep)}): {', '.join(keep)}")

    print(f"\n  FINAL VERDICT:")
    print(f"    Promoted: {len(promote)} strategies")
    print(f"    Kept:     {len(keep)} strategies")
    print(f"    Eliminated: {len(eliminate)} strategies")
    print("=" * 80)

    return {"eliminate": eliminate, "keep": keep, "promote": promote}


def main():
    parser = argparse.ArgumentParser(description="ALPHA ENGINE Walk-Forward Battle Test")
    parser.add_argument("--months", type=int, default=6, help="Months of history to test")
    parser.add_argument("--crypto-only", action="store_true")
    parser.add_argument("--forex-only", action="store_true")
    parser.add_argument("--equity-only", action="store_true")
    parser.add_argument("--step", type=int, default=5, help="Days between signal generation attempts")
    args = parser.parse_args()

    start_time = time.time()

    # Select symbols and strategies
    if args.crypto_only:
        symbols = list(CRYPTO_SYMBOLS.keys())
        strategies = CRYPTO_STRATEGIES
        label = "CRYPTO"
    elif args.forex_only:
        symbols = list(FOREX_SYMBOLS.keys())
        strategies = FOREX_STRATEGIES
        label = "FOREX"
    elif args.equity_only:
        symbols = list(EQUITY_SYMBOLS.keys())
        strategies = EQUITY_STRATEGIES
        label = "EQUITY"
    else:
        symbols = list(ALL_SYMBOLS.keys())
        strategies = {**CRYPTO_STRATEGIES, **FOREX_STRATEGIES, **EQUITY_STRATEGIES}
        label = "ALL ASSETS"

    # Filter out disabled strategies (emergency triage)
    from strategy_guard import filter_strategies, log_filtered_strategies
    strategies, removed = filter_strategies(strategies)
    log_filtered_strategies(removed)

    print(f"\n{'='*80}")
    print(f"  ALPHA ENGINE -- WALK-FORWARD BATTLE TEST")
    print(f"  {label} | {len(strategies)} strategies | {len(symbols)} symbols")
    print(f"  Test window: {args.months} months | Step: every {args.step} trading days")
    print(f"{'='*80}")

    # Fetch data
    print("\n[1/4] Fetching historical data...")
    data = fetch_historical_data(symbols, period="1y")
    if not data:
        print("  FATAL: No data. Aborting.")
        sys.exit(1)

    # Calculate test start (skip first N months for strategy warmup)
    sample = list(data.values())[0]
    total_bars = len(sample)
    test_months_bars = int(args.months * 21)
    warmup_bars = total_bars - test_months_bars
    if warmup_bars < 200:
        warmup_bars = 200
    print(f"  Total bars: {total_bars}, warmup: {warmup_bars}, test window: {total_bars - warmup_bars}")

    # Run battle test
    print("\n[2/4] Running walk-forward battle test...")
    results = run_battle_test(data, strategies, warmup_bars, step_days=args.step)

    if not results:
        print("  No signals generated. Strategies may need more data or conditions not met.")
        sys.exit(1)

    # Analyze
    print("\n[3/4] Analyzing results...")
    analysis = analyze_results(results)

    # Report
    print("\n[4/4] Generating report...")
    verdicts = print_battle_report(analysis, results)

    # Save full results
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    results_path = DATA_DIR / "battle_test_results.json"
    with open(results_path, "w") as f:
        json.dump({
            "test_date": datetime.now(timezone.utc).isoformat(),
            "test_months": args.months,
            "step_days": args.step,
            "total_signals": len(results),
            "strategy_analysis": analysis,
            "verdicts": verdicts,
            "asset_label": label,
        }, f, indent=2)

    # Save individual pick results
    picks_path = DATA_DIR / "battle_test_picks.json"
    with open(picks_path, "w") as f:
        json.dump(results, f, indent=2)

    elapsed = time.time() - start_time
    print(f"\nBattle test completed in {elapsed:.1f}s")
    print(f"Results saved to {results_path}")
    print(f"Individual picks saved to {picks_path}")


if __name__ == "__main__":
    main()
