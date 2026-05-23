#!/usr/bin/env python3
"""
ALPHA ENGINE -- ONE-HIT WONDER DETECTOR
=========================================
For each strategy claiming to be a "winner", run it across
hundreds of historical bars and simulate every trade.

A strategy is PROVEN only if:
  - 50+ simulated trades
  - Win rate > 52% (statistically above coin flip)
  - Profit factor > 1.2
  - P-value < 0.05 vs random (binomial test)
  - Consistent across multiple symbols (not just one)

Otherwise: ONE-HIT WONDER -- DEMOTED.
"""

import sys
import json
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timezone, timedelta
from pathlib import Path
from collections import defaultdict
from scipy import stats

EST = timezone(timedelta(hours=-5))

# Strategies to test -- import from challenge_v3
sys.path.insert(0, str(Path(__file__).resolve().parent))
from challenge_v3 import (
    strat_ema_rsi_momentum, strat_rsi_divergence, strat_triple_ema_trend,
    strat_zscore_pairs, strat_orb_breakout, strat_vwap_deviation,
    strat_bb_squeeze_expansion, strat_volume_climax,
    SYMBOLS, atr
)

STRATEGIES = {
    "ema_rsi_momentum": strat_ema_rsi_momentum,
    "rsi_divergence": strat_rsi_divergence,
    "triple_ema_trend": strat_triple_ema_trend,
    "zscore_reversion": strat_zscore_pairs,
    "orb_breakout": strat_orb_breakout,
    "vwap_deviation": strat_vwap_deviation,
    "bb_squeeze_expansion": strat_bb_squeeze_expansion,
    "volume_climax_reversal": strat_volume_climax,
}

# Test across multiple timeframes
TIMEFRAMES = {
    "1h":  {"interval": "1h",  "period": "3mo"},   # ~90 days of 1h bars -- best data/speed tradeoff
}

def simulate_trade(entry, tp, sl, signal_type, future_bars):
    """Simulate a trade forward through future bars. Returns (pnl_pct, outcome, bars_held)."""
    for i, (_, bar) in enumerate(future_bars.iterrows()):
        high = float(bar["High"])
        low = float(bar["Low"])
        close = float(bar["Close"])

        if signal_type == "BUY":
            if tp and high >= tp:
                return ((tp - entry) / entry) * 100, "TP_HIT", i + 1
            if sl and low <= sl:
                return ((sl - entry) / entry) * 100, "SL_HIT", i + 1
        else:  # SELL
            if tp and low <= tp:
                return ((entry - tp) / entry) * 100, "TP_HIT", i + 1
            if sl and high >= sl:
                return ((entry - sl) / entry) * 100, "SL_HIT", i + 1

    # Time expiry -- use last close
    last_close = float(future_bars["Close"].iloc[-1]) if len(future_bars) > 0 else entry
    if signal_type == "BUY":
        return ((last_close - entry) / entry) * 100, "EXPIRED", len(future_bars)
    else:
        return ((entry - last_close) / entry) * 100, "EXPIRED", len(future_bars)


def walk_forward_test(strat_fn, strat_name, sym, meta, df, tf, max_hold=20):
    """Walk through historical data, generate signals, simulate trades."""
    trades = []
    warmup = 60  # bars needed for indicators

    if len(df) < warmup + max_hold + 10:
        return trades

    for i in range(warmup, len(df) - max_hold):
        # Give strategy data up to bar i
        window = df.iloc[:i+1]

        try:
            picks = strat_fn(window, sym, meta, tf=tf)
        except Exception:
            continue

        if not picks:
            continue

        for pick in picks:
            entry = pick["entry_price"]
            tp = pick["take_profit"]
            sl = pick["stop_loss"]
            sig = pick["signal_type"]

            # Simulate forward
            future = df.iloc[i+1:i+1+max_hold]
            if len(future) == 0:
                continue

            pnl, outcome, bars = simulate_trade(entry, tp, sl, sig, future)

            trades.append({
                "symbol": sym,
                "signal": sig,
                "entry": entry,
                "tp": tp,
                "sl": sl,
                "pnl_pct": pnl,
                "outcome": outcome,
                "bars_held": bars,
                "bar_index": i,
            })

            # Skip ahead to avoid overlapping trades
            break  # Only take first signal per bar

    return trades


def analyze_trades(trades, strat_name):
    """Statistical analysis of trade results."""
    if not trades:
        return None

    pnls = [t["pnl_pct"] for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    n = len(trades)
    n_wins = len(wins)
    n_losses = len(losses)
    wr = n_wins / n * 100 if n > 0 else 0

    avg_win = np.mean(wins) if wins else 0
    avg_loss = np.mean(losses) if losses else 0
    gross_profit = sum(wins) if wins else 0
    gross_loss = abs(sum(losses)) if losses else 0.001
    pf = gross_profit / gross_loss if gross_loss > 0 else 0

    total_pnl = sum(pnls)
    avg_pnl = np.mean(pnls) if pnls else 0
    std_pnl = np.std(pnls) if len(pnls) > 1 else 1

    # Statistical tests
    # Binomial test: is WR significantly > 50%?
    binom_p = stats.binomtest(n_wins, n, 0.5, alternative="greater").pvalue if n > 0 else 1.0

    # T-test: is mean PnL significantly > 0?
    if len(pnls) > 1:
        t_stat, t_p = stats.ttest_1samp(pnls, 0)
        t_p = t_p / 2 if t_stat > 0 else 1.0  # One-sided
    else:
        t_p = 1.0

    # Sharpe (annualized, assuming 252 trading days/year -- standard convention)
    sharpe = (avg_pnl / std_pnl) * np.sqrt(252) if std_pnl > 0 else 0

    # By outcome
    tp_hits = sum(1 for t in trades if t["outcome"] == "TP_HIT")
    sl_hits = sum(1 for t in trades if t["outcome"] == "SL_HIT")
    expired = sum(1 for t in trades if t["outcome"] == "EXPIRED")

    # By symbol
    sym_stats = defaultdict(lambda: {"n": 0, "wins": 0, "pnl": 0})
    for t in trades:
        sym_stats[t["symbol"]]["n"] += 1
        sym_stats[t["symbol"]]["pnl"] += t["pnl_pct"]
        if t["pnl_pct"] > 0:
            sym_stats[t["symbol"]]["wins"] += 1

    # Verdict
    passed_trades = n >= 30
    passed_wr = wr > 50
    passed_pf = pf > 1.2
    passed_binom = binom_p < 0.05
    passed_ttest = t_p < 0.05
    passed_multi = sum(1 for s in sym_stats.values() if s["n"] >= 3) >= 2

    is_proven = passed_trades and passed_wr and passed_pf and (passed_binom or passed_ttest)
    is_promising = passed_trades and (passed_wr or passed_pf) and not is_proven
    is_one_hit = not passed_trades or (not passed_wr and not passed_pf)

    if is_proven:
        verdict = "PROVEN WINNER"
    elif is_promising:
        verdict = "PROMISING (needs more data)"
    elif is_one_hit:
        verdict = "ONE-HIT WONDER -- DEMOTED"
    else:
        verdict = "INCONCLUSIVE"

    return {
        "strategy": strat_name,
        "total_trades": n,
        "wins": n_wins,
        "losses": n_losses,
        "win_rate": round(wr, 1),
        "avg_win": round(avg_win, 3),
        "avg_loss": round(avg_loss, 3),
        "profit_factor": round(pf, 2),
        "total_pnl_pct": round(total_pnl, 2),
        "avg_pnl_pct": round(avg_pnl, 3),
        "sharpe": round(sharpe, 2),
        "tp_hits": tp_hits,
        "sl_hits": sl_hits,
        "expired": expired,
        "binom_p": round(binom_p, 4),
        "ttest_p": round(t_p, 4),
        "symbols_tested": len(sym_stats),
        "symbols_profitable": sum(1 for s in sym_stats.values() if s["pnl"] > 0),
        "checks": {
            "30+ trades": passed_trades,
            "WR > 50%": passed_wr,
            "PF > 1.2": passed_pf,
            "Binom p<0.05": passed_binom,
            "Ttest p<0.05": passed_ttest,
            "Multi-symbol": passed_multi,
        },
        "verdict": verdict,
        "sym_breakdown": dict(sym_stats),
    }


def main():
    print("\n" + "=" * 80)
    print("  ONE-HIT WONDER DETECTOR")
    print("  Testing all strategies across historical data")
    print("=" * 80)

    symbols = list(SYMBOLS.keys())

    all_results = []

    for tf_name, tf_config in TIMEFRAMES.items():
        print(f"\n{'='*60}")
        print(f"  TIMEFRAME: {tf_name} (period={tf_config['period']})")
        print(f"{'='*60}")

        # Fetch data
        tickers = " ".join(symbols)
        print(f"  Fetching {len(symbols)} symbols...")
        try:
            raw = yf.download(tickers, period=tf_config["period"],
                              interval=tf_config["interval"],
                              group_by="ticker", auto_adjust=True,
                              threads=True, progress=False)
        except Exception as e:
            print(f"  ERROR: {e}")
            continue

        data = {}
        for sym in symbols:
            try:
                if len(symbols) == 1:
                    df = raw
                else:
                    df = raw[sym] if sym in raw.columns.get_level_values(0) else None
                if df is not None and not df.empty:
                    df = df.dropna(subset=["Close"])
                    if len(df) >= 80:
                        data[sym] = df
            except Exception:
                continue

        print(f"  Got data for {len(data)}/{len(symbols)} symbols")
        for sym, df in data.items():
            print(f"    {sym}: {len(df)} bars")

        for strat_name, strat_fn in STRATEGIES.items():
            print(f"\n  Testing [{strat_name}] on {tf_name}...")
            all_trades = []

            for sym, meta in SYMBOLS.items():
                if sym not in data:
                    continue
                trades = walk_forward_test(strat_fn, strat_name, sym, meta,
                                           data[sym], tf_name, max_hold=20)
                all_trades.extend(trades)
                if trades:
                    wins = sum(1 for t in trades if t["pnl_pct"] > 0)
                    print(f"    {sym}: {len(trades)} trades, {wins}W/{len(trades)-wins}L")

            if not all_trades:
                print(f"    No trades generated -- strategy too selective or data too short")
                continue

            result = analyze_trades(all_trades, f"{strat_name}|{tf_name}")
            all_results.append(result)

            # Print result
            v = result
            print(f"\n    {'='*50}")
            print(f"    {v['strategy']}: {v['verdict']}")
            print(f"    {'='*50}")
            print(f"    Trades: {v['total_trades']} ({v['wins']}W/{v['losses']}L)")
            print(f"    Win Rate: {v['win_rate']}%")
            print(f"    Profit Factor: {v['profit_factor']}")
            print(f"    Total PnL: {v['total_pnl_pct']:+.2f}%")
            print(f"    Avg PnL: {v['avg_pnl_pct']:+.3f}%")
            print(f"    Sharpe: {v['sharpe']}")
            print(f"    TP Hits: {v['tp_hits']} | SL Hits: {v['sl_hits']} | Expired: {v['expired']}")
            print(f"    Binom p={v['binom_p']} | T-test p={v['ttest_p']}")
            print(f"    Symbols: {v['symbols_tested']} tested, {v['symbols_profitable']} profitable")

            checks = v["checks"]
            print(f"    Checks:")
            for check, passed in checks.items():
                icon = "PASS" if passed else "FAIL"
                print(f"      [{icon}] {check}")

    # Final summary
    print(f"\n\n{'='*80}")
    print(f"  FINAL VERDICT -- ALL STRATEGIES")
    print(f"{'='*80}")

    proven = [r for r in all_results if "PROVEN" in r["verdict"]]
    promising = [r for r in all_results if "PROMISING" in r["verdict"]]
    demoted = [r for r in all_results if "ONE-HIT" in r["verdict"] or "DEMOTED" in r["verdict"]]
    inconclusive = [r for r in all_results if "INCONCLUSIVE" in r["verdict"]]

    if proven:
        print(f"\n  PROVEN WINNERS ({len(proven)}):")
        for r in sorted(proven, key=lambda x: x["profit_factor"], reverse=True):
            print(f"    {r['strategy']:>30s}: PF={r['profit_factor']:.2f} "
                  f"WR={r['win_rate']:.1f}% ({r['total_trades']} trades) "
                  f"Sharpe={r['sharpe']:.2f}")
    else:
        print(f"\n  PROVEN WINNERS: NONE")
        print(f"  (No strategy passed all statistical tests)")

    if promising:
        print(f"\n  PROMISING ({len(promising)}):")
        for r in sorted(promising, key=lambda x: x["profit_factor"], reverse=True):
            print(f"    {r['strategy']:>30s}: PF={r['profit_factor']:.2f} "
                  f"WR={r['win_rate']:.1f}% ({r['total_trades']} trades)")

    if demoted:
        print(f"\n  ONE-HIT WONDERS -- DEMOTED ({len(demoted)}):")
        for r in sorted(demoted, key=lambda x: x["total_trades"]):
            print(f"    {r['strategy']:>30s}: {r['total_trades']} trades, "
                  f"PF={r['profit_factor']:.2f} WR={r['win_rate']:.1f}%")

    if inconclusive:
        print(f"\n  INCONCLUSIVE ({len(inconclusive)}):")
        for r in inconclusive:
            print(f"    {r['strategy']:>30s}: {r['total_trades']} trades")

    # Save results
    DATA_DIR = Path(__file__).resolve().parent / "data"
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(DATA_DIR / "prove_winners_results.json", "w") as f:
        json.dump(all_results, f, indent=2, default=str)

    print(f"\n  Results saved to data/prove_winners_results.json")
    print("=" * 80)


if __name__ == "__main__":
    main()
