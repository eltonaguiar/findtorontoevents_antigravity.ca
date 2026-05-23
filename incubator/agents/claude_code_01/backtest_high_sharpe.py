"""
Backtest runner for High-Sharpe strategies against Binance crypto pairs.
Fetches 6 months of daily candles and evaluates each strategy.

Usage: python backtest_high_sharpe.py
"""

import json
import sys
import importlib.util
import traceback
from pathlib import Path
from datetime import datetime, timezone
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError
from dataclasses import asdict

# Strategies to test
STRATEGIES = {
    "VolScaledTsmom": {
        "file": "crypto_volscaled_tsmom_v1.py",
        "class": "VolScaledTsmomStrategy",
        "academic_sharpe": "2.0-3.5",
    },
    "CointegrationPairs": {
        "file": "crypto_cointegration_pairs_v1.py",
        "class": "CointegrationPairsStrategy",
        "academic_sharpe": "1.6-2.5",
    },
    "BettingAgainstBeta": {
        "file": "crypto_betting_against_beta_v1.py",
        "class": "BettingAgainstBetaStrategy",
        "academic_sharpe": "0.8-1.5",
    },
    "MlEnsemble": {
        "file": "crypto_ml_ensemble_v1.py",
        "class": "MlEnsembleStrategy",
        "academic_sharpe": "1.8-4.5",
    },
    "RotationalMomentum": {
        "file": "crypto_rotational_momentum_v1.py",
        "class": "RotationalMomentumStrategy",
        "academic_sharpe": "1.5+",
    },
}

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
KLINE_LIMIT = 500  # Need 500+ bars for strategies with long lookbacks (EMA200 + window)
SCRIPT_DIR = Path(__file__).parent


def fetch_binance_klines(symbol: str, interval: str = "1d", limit: int = KLINE_LIMIT):
    """Fetch OHLCV data from Binance public API."""
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urlopen(req, timeout=15) as resp:
            raw = json.loads(resp.read().decode())
    except (HTTPError, URLError) as e:
        print(f"  [ERROR] Failed to fetch {symbol}: {e}")
        return None

    # Build list of dicts (pandas-free for import, convert later)
    rows = []
    for k in raw:
        rows.append({
            "timestamp": k[0],
            "open": float(k[1]),
            "high": float(k[2]),
            "low": float(k[3]),
            "close": float(k[4]),
            "volume": float(k[5]),
        })
    return rows


def load_strategy_class(file_name: str, class_name: str):
    """Dynamically load a strategy class from a file."""
    file_path = SCRIPT_DIR / file_name
    spec = importlib.util.spec_from_file_location(class_name, file_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, class_name)


def simple_backtest(signals_history, prices):
    """
    Simple backtest: for each signal, check if TP or SL was hit first
    in subsequent bars. Returns stats.
    """
    wins = 0
    losses = 0
    total_pnl = 0.0
    trades = []

    for sig_idx, sig in signals_history:
        entry = sig.entry_price
        tp = sig.take_profit
        sl = sig.stop_loss
        direction = sig.direction

        # Walk forward from signal bar
        outcome = None
        exit_price = entry
        for j in range(sig_idx + 1, min(sig_idx + 30, len(prices))):  # max 30 bars hold
            bar = prices[j]
            if direction == "BUY":
                if bar["high"] >= tp:
                    outcome = "WIN"
                    exit_price = tp
                    break
                if bar["low"] <= sl:
                    outcome = "LOSS"
                    exit_price = sl
                    break
            else:  # SELL
                if bar["low"] <= tp:
                    outcome = "WIN"
                    exit_price = tp
                    break
                if bar["high"] >= sl:
                    outcome = "LOSS"
                    exit_price = sl
                    break

        if outcome is None:
            # Timeout - close at last bar's close
            exit_price = prices[min(sig_idx + 29, len(prices) - 1)]["close"]
            if direction == "BUY":
                outcome = "WIN" if exit_price > entry else "LOSS"
            else:
                outcome = "WIN" if exit_price < entry else "LOSS"

        if direction == "BUY":
            pnl_pct = (exit_price - entry) / entry * 100
        else:
            pnl_pct = (entry - exit_price) / entry * 100

        if outcome == "WIN":
            wins += 1
        else:
            losses += 1
        total_pnl += pnl_pct
        trades.append({"outcome": outcome, "pnl_pct": pnl_pct, "direction": direction})

    total = wins + losses
    win_rate = (wins / total * 100) if total > 0 else 0
    avg_pnl = (total_pnl / total) if total > 0 else 0

    # Compute Sharpe-like ratio from trade PnLs
    if len(trades) >= 2:
        pnls = [t["pnl_pct"] for t in trades]
        import math
        mean_pnl = sum(pnls) / len(pnls)
        var_pnl = sum((p - mean_pnl) ** 2 for p in pnls) / (len(pnls) - 1)
        std_pnl = math.sqrt(var_pnl) if var_pnl > 0 else 0.001
        if std_pnl < 0.001:
            sharpe_annual = 0
        else:
            sharpe_per_trade = mean_pnl / std_pnl
            # Annualize assuming ~1 trade per week on average
            trades_per_year = max(len(trades) * (365 / 200), 1)
            sharpe_annual = sharpe_per_trade * math.sqrt(trades_per_year)
            sharpe_annual = max(-99.99, min(99.99, sharpe_annual))
    else:
        sharpe_annual = 0

    return {
        "total_trades": total,
        "wins": wins,
        "losses": losses,
        "win_rate": round(win_rate, 1),
        "total_pnl_pct": round(total_pnl, 2),
        "avg_pnl_pct": round(avg_pnl, 2),
        "sharpe_est": round(sharpe_annual, 2),
    }


def main():
    import os
    if os.name == 'nt':
        import sys
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')

    try:
        import pandas as pd
        import numpy as np
    except ImportError:
        print("ERROR: pandas/numpy required. Install with: pip install pandas numpy")
        sys.exit(1)

    print(f"\n{'='*70}")
    print(f"HIGH-SHARPE STRATEGY BACKTEST — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*70}")
    print(f"Symbols: {', '.join(SYMBOLS)}")
    print(f"Period: ~{KLINE_LIMIT} daily bars (~{KLINE_LIMIT/30:.0f} months)")
    print(f"Strategies: {len(STRATEGIES)}")
    print()

    # Fetch data for all symbols
    market_data = {}
    for sym in SYMBOLS:
        print(f"Fetching {sym} daily data...")
        rows = fetch_binance_klines(sym, "1d", KLINE_LIMIT)
        if rows:
            market_data[sym] = rows
            print(f"  Got {len(rows)} bars")
        else:
            print(f"  FAILED - skipping")

    if not market_data:
        print("No market data fetched. Exiting.")
        sys.exit(1)

    # Results table
    results = []

    for strat_name, strat_info in STRATEGIES.items():
        print(f"\n{'─'*70}")
        print(f"Strategy: {strat_name} (Academic Sharpe: {strat_info['academic_sharpe']})")
        print(f"{'─'*70}")

        try:
            StratClass = load_strategy_class(strat_info["file"], strat_info["class"])
            strategy = StratClass()
        except Exception as e:
            print(f"  [ERROR] Failed to load: {e}")
            traceback.print_exc()
            continue

        for sym, rows in market_data.items():
            try:
                df = pd.DataFrame(rows)
                # Generate signals for each bar (sliding window)
                # Start at 280 to accommodate strategies needing EMA(200)+window
                signals_with_idx = []
                start_bar = min(280, len(df) - 20)
                for i in range(start_bar, len(df)):
                    window = df.iloc[:i+1].copy().reset_index(drop=True)
                    sigs = strategy.generate_signals(window, sym)
                    if sigs:
                        signals_with_idx.append((i, sigs[-1]))

                if not signals_with_idx:
                    print(f"  {sym}: No signals generated")
                    continue

                # Backtest
                stats = simple_backtest(signals_with_idx, rows)
                print(f"  {sym}: {stats['total_trades']} trades | "
                      f"WR {stats['win_rate']}% | "
                      f"PnL {stats['total_pnl_pct']:+.1f}% | "
                      f"Avg {stats['avg_pnl_pct']:+.2f}% | "
                      f"Sharpe {stats['sharpe_est']:.2f}")

                results.append({
                    "strategy": strat_name,
                    "symbol": sym,
                    "academic_sharpe": strat_info["academic_sharpe"],
                    **stats,
                })

            except Exception as e:
                print(f"  {sym}: ERROR - {e}")
                traceback.print_exc()

    # Summary
    print(f"\n{'='*70}")
    print("BACKTEST SUMMARY — RANKED BY SHARPE")
    print(f"{'='*70}")
    print(f"{'Strategy':<25} {'Symbol':<10} {'Trades':>6} {'WR%':>6} {'PnL%':>8} {'Sharpe':>8}")
    print("─" * 70)

    results.sort(key=lambda x: x["sharpe_est"], reverse=True)
    worthy = []
    for r in results:
        flag = ""
        if r["sharpe_est"] >= 1.5 and r["win_rate"] >= 55:
            flag = " ★★★"
            worthy.append(r)
        elif r["sharpe_est"] >= 1.0 and r["win_rate"] >= 50:
            flag = " ★★"
            worthy.append(r)
        elif r["sharpe_est"] >= 0.5:
            flag = " ★"

        print(f"{r['strategy']:<25} {r['symbol']:<10} {r['total_trades']:>6} "
              f"{r['win_rate']:>5.1f}% {r['total_pnl_pct']:>+7.1f}% "
              f"{r['sharpe_est']:>7.2f}{flag}")

    print(f"\n{'='*70}")
    print(f"WORTHY CANDIDATES (Sharpe >= 1.0 AND WR >= 50%):")
    if worthy:
        for w in worthy:
            print(f"  ★ {w['strategy']} on {w['symbol']}: Sharpe {w['sharpe_est']}, WR {w['win_rate']}%")
    else:
        print("  None met the threshold on this sample. Consider parameter tuning.")
    print(f"{'='*70}\n")

    # Save results
    output_file = SCRIPT_DIR / "backtest_high_sharpe_results.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Results saved to: {output_file}")

    return results


if __name__ == "__main__":
    main()
