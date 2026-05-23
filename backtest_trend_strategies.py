#!/usr/bin/env python3
"""
Backtest Trend Strategies (6-9) — SuperTrend, VWAP Deviation, Triple EMA, Ichimoku
Tests across 10 crypto symbols, 3 timeframes, with Binance API failover.
"""

import json
import time
import sys
import os
from datetime import datetime

try:
    import requests
    import numpy as np
except ImportError:
    print("Installing required packages...")
    os.system(f"{sys.executable} -m pip install requests numpy --quiet")
    import requests
    import numpy as np

# ── Configuration ──────────────────────────────────────────────────────────
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "AVAXUSDT",
           "LINKUSDT", "DOGEUSDT", "LTCUSDT", "ADAUSDT", "XRPUSDT"]
TIMEFRAMES = ["1h", "4h", "1d"]
COMMISSION = 0.0005  # 0.05%
KLINES_LIMIT = 1000

BINANCE_MIRRORS = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
]

OUTPUT_FILE = "e:/findtorontoevents_antigravity.ca/backtest_trend_strategy_results.json"


# ── Data Fetching with Failover ────────────────────────────────────────────
def fetch_klines(symbol, interval, limit=KLINES_LIMIT):
    """Fetch klines from Binance with 4-mirror failover."""
    for base_url in BINANCE_MIRRORS:
        try:
            url = f"{base_url}/api/v3/klines"
            params = {"symbol": symbol, "interval": interval, "limit": limit}
            resp = requests.get(url, params=params, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                if len(data) > 0:
                    return data
        except Exception:
            continue
    print(f"  [WARN] All Binance mirrors failed for {symbol} {interval}")
    return None


def parse_klines(raw):
    """Parse Binance klines into numpy arrays."""
    opens, highs, lows, closes, volumes = [], [], [], [], []
    for k in raw:
        opens.append(float(k[1]))
        highs.append(float(k[2]))
        lows.append(float(k[3]))
        closes.append(float(k[4]))
        volumes.append(float(k[5]))
    return (np.array(opens), np.array(highs), np.array(lows),
            np.array(closes), np.array(volumes))


# ── Indicator Helpers ──────────────────────────────────────────────────────
def calc_atr(highs, lows, closes, period=14):
    """Average True Range."""
    n = len(closes)
    tr = np.zeros(n)
    tr[0] = highs[0] - lows[0]
    for i in range(1, n):
        tr[i] = max(highs[i] - lows[i],
                     abs(highs[i] - closes[i-1]),
                     abs(lows[i] - closes[i-1]))
    atr = np.zeros(n)
    atr[:period] = np.nan
    atr[period-1] = np.mean(tr[:period])
    for i in range(period, n):
        atr[i] = (atr[i-1] * (period - 1) + tr[i]) / period
    return atr


def calc_ema(data, period):
    """Exponential Moving Average."""
    ema = np.full(len(data), np.nan)
    if len(data) < period:
        return ema
    ema[period-1] = np.mean(data[:period])
    mult = 2.0 / (period + 1)
    for i in range(period, len(data)):
        ema[i] = data[i] * mult + ema[i-1] * (1 - mult)
    return ema


def calc_highest(data, period):
    """Rolling highest."""
    n = len(data)
    result = np.full(n, np.nan)
    for i in range(period - 1, n):
        result[i] = np.max(data[i - period + 1:i + 1])
    return result


def calc_lowest(data, period):
    """Rolling lowest."""
    n = len(data)
    result = np.full(n, np.nan)
    for i in range(period - 1, n):
        result[i] = np.min(data[i - period + 1:i + 1])
    return result


def calc_stdev(data, period):
    """Rolling standard deviation."""
    n = len(data)
    result = np.full(n, np.nan)
    for i in range(period - 1, n):
        result[i] = np.std(data[i - period + 1:i + 1])
    return result


# ── Trade Simulation ───────────────────────────────────────────────────────
def simulate_trades(closes, highs, lows, signals, atr, tp_mult, sl_mult, max_hold):
    """
    Simulate trades given entry signals.
    signals: list of (bar_index, direction) where direction is 1 (long) or -1 (short)
    Returns list of trade dicts.
    """
    trades = []
    in_trade = False
    entry_bar = 0
    entry_price = 0.0
    direction = 0
    tp_price = 0.0
    sl_price = 0.0

    # Build signal map
    signal_map = {}
    for bar, d in signals:
        if bar not in signal_map:
            signal_map[bar] = d

    for i in range(len(closes)):
        if in_trade:
            # Check exit conditions
            bars_held = i - entry_bar
            exit_price = None
            exit_reason = None

            if direction == 1:  # Long
                if lows[i] <= sl_price:
                    exit_price = sl_price
                    exit_reason = "SL"
                elif highs[i] >= tp_price:
                    exit_price = tp_price
                    exit_reason = "TP"
                elif bars_held >= max_hold:
                    exit_price = closes[i]
                    exit_reason = "MAX_HOLD"
            else:  # Short
                if highs[i] >= sl_price:
                    exit_price = sl_price
                    exit_reason = "SL"
                elif lows[i] <= tp_price:
                    exit_price = tp_price
                    exit_reason = "TP"
                elif bars_held >= max_hold:
                    exit_price = closes[i]
                    exit_reason = "MAX_HOLD"

            if exit_price is not None:
                pnl = direction * (exit_price - entry_price) / entry_price
                pnl -= 2 * COMMISSION  # entry + exit commission
                trades.append({
                    "entry_bar": entry_bar,
                    "exit_bar": i,
                    "direction": "LONG" if direction == 1 else "SHORT",
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "pnl_pct": round(pnl * 100, 4),
                    "exit_reason": exit_reason,
                })
                in_trade = False

        if not in_trade and i in signal_map:
            d = signal_map[i]
            atr_val = atr[i]
            if np.isnan(atr_val) or atr_val <= 0:
                continue
            entry_price = closes[i]
            direction = d
            entry_bar = i
            if d == 1:
                tp_price = entry_price + tp_mult * atr_val
                sl_price = entry_price - sl_mult * atr_val
            else:
                tp_price = entry_price - tp_mult * atr_val
                sl_price = entry_price + sl_mult * atr_val
            in_trade = True

    return trades


# ── Strategy Implementations ──────────────────────────────────────────────

def strategy_supertrend(opens, highs, lows, closes, volumes):
    """Strategy 6: SuperTrend Breakout."""
    n = len(closes)
    st_period = 10
    st_mult = 3.0
    atr_st = calc_atr(highs, lows, closes, st_period)
    atr_exit = calc_atr(highs, lows, closes, 14)

    # SuperTrend calculation
    mid = (highs + lows) / 2.0
    upper_band = mid + st_mult * atr_st
    lower_band = mid - st_mult * atr_st

    # Final bands with trailing logic
    final_upper = np.copy(upper_band)
    final_lower = np.copy(lower_band)
    direction = np.zeros(n)  # 1 = bullish, -1 = bearish

    for i in range(1, n):
        if np.isnan(atr_st[i]):
            direction[i] = 0
            continue

        # Trailing upper band
        if final_upper[i] < final_upper[i-1] or closes[i-1] > final_upper[i-1]:
            final_upper[i] = upper_band[i]
        else:
            final_upper[i] = min(upper_band[i], final_upper[i-1])

        # Trailing lower band
        if final_lower[i] > final_lower[i-1] or closes[i-1] < final_lower[i-1]:
            final_lower[i] = lower_band[i]
        else:
            final_lower[i] = max(lower_band[i], final_lower[i-1])

        # Direction
        if direction[i-1] <= 0:  # was bearish or neutral
            if closes[i] > final_upper[i-1]:
                direction[i] = 1
            else:
                direction[i] = -1
        else:  # was bullish
            if closes[i] < final_lower[i-1]:
                direction[i] = -1
            else:
                direction[i] = 1

    signals = []
    for i in range(1, n):
        if direction[i] == 1 and direction[i-1] != 1:
            signals.append((i, 1))  # Flip to bullish → LONG
        elif direction[i] == -1 and direction[i-1] != -1:
            signals.append((i, -1))  # Flip to bearish → SHORT

    return simulate_trades(closes, highs, lows, signals, atr_exit,
                           tp_mult=2.5, sl_mult=1.5, max_hold=20)


def strategy_vwap_deviation(opens, highs, lows, closes, volumes):
    """Strategy 7: VWAP Deviation Reversion."""
    n = len(closes)
    period = 20
    atr = calc_atr(highs, lows, closes, 14)

    # Rolling VWAP approximation (20-bar)
    typical = (highs + lows + closes) / 3.0
    vwap = np.full(n, np.nan)
    for i in range(period - 1, n):
        window_tp = typical[i - period + 1:i + 1]
        window_vol = volumes[i - period + 1:i + 1]
        vol_sum = np.sum(window_vol)
        if vol_sum > 0:
            vwap[i] = np.sum(window_tp * window_vol) / vol_sum
        else:
            vwap[i] = np.mean(window_tp)

    # Deviation bands: VWAP +/- 2 * stdev(close, 20)
    stdev = calc_stdev(closes, period)
    upper_band = vwap + 2.0 * stdev
    lower_band = vwap - 2.0 * stdev

    signals = []
    for i in range(period, n):
        if np.isnan(vwap[i]) or np.isnan(stdev[i]):
            continue
        # Cross below lower band → LONG (reversion)
        if closes[i] < lower_band[i] and closes[i-1] >= lower_band[i-1]:
            signals.append((i, 1))
        # Cross above upper band → SHORT (reversion)
        elif closes[i] > upper_band[i] and closes[i-1] <= upper_band[i-1]:
            signals.append((i, -1))

    return simulate_trades(closes, highs, lows, signals, atr,
                           tp_mult=1.5, sl_mult=1.0, max_hold=8)


def strategy_triple_ema(opens, highs, lows, closes, volumes):
    """Strategy 8: Triple EMA Momentum."""
    n = len(closes)
    ema5 = calc_ema(closes, 5)
    ema10 = calc_ema(closes, 10)
    ema20 = calc_ema(closes, 20)
    atr = calc_atr(highs, lows, closes, 14)

    signals = []
    for i in range(21, n):
        if any(np.isnan([ema5[i], ema10[i], ema20[i], ema5[i-1], ema10[i-1], ema20[i-1]])):
            continue

        # Current alignment
        long_aligned = (ema5[i] > ema10[i] > ema20[i]) and (closes[i] > ema5[i])
        short_aligned = (ema5[i] < ema10[i] < ema20[i]) and (closes[i] < ema5[i])

        # Previous alignment
        prev_long = (ema5[i-1] > ema10[i-1] > ema20[i-1]) and (closes[i-1] > ema5[i-1])
        prev_short = (ema5[i-1] < ema10[i-1] < ema20[i-1]) and (closes[i-1] < ema5[i-1])

        # Fresh alignment only
        if long_aligned and not prev_long:
            signals.append((i, 1))
        elif short_aligned and not prev_short:
            signals.append((i, -1))

    return simulate_trades(closes, highs, lows, signals, atr,
                           tp_mult=2.0, sl_mult=1.0, max_hold=15)


def strategy_ichimoku(opens, highs, lows, closes, volumes):
    """Strategy 9: Ichimoku Cloud Breakout."""
    n = len(closes)
    atr = calc_atr(highs, lows, closes, 14)

    # Ichimoku components
    tenkan = (calc_highest(highs, 9) + calc_lowest(lows, 9)) / 2.0
    kijun = (calc_highest(highs, 26) + calc_lowest(lows, 26)) / 2.0
    senkou_a = (tenkan + kijun) / 2.0
    senkou_b = (calc_highest(highs, 52) + calc_lowest(lows, 52)) / 2.0

    cloud_top = np.maximum(senkou_a, senkou_b)
    cloud_bottom = np.minimum(senkou_a, senkou_b)

    signals = []
    for i in range(53, n):
        if any(np.isnan([tenkan[i], kijun[i], senkou_a[i], senkou_b[i],
                         cloud_top[i-1], cloud_bottom[i-1]])):
            continue

        above_cloud = closes[i] > cloud_top[i]
        below_cloud = closes[i] < cloud_bottom[i]
        tk_bull = tenkan[i] > kijun[i]
        tk_bear = tenkan[i] < kijun[i]

        # Previous bar position relative to cloud
        prev_above = closes[i-1] > cloud_top[i-1]
        prev_below = closes[i-1] < cloud_bottom[i-1]

        # Fresh breakout: was NOT above cloud before, now is
        if above_cloud and tk_bull and not prev_above:
            signals.append((i, 1))
        elif below_cloud and tk_bear and not prev_below:
            signals.append((i, -1))

    return simulate_trades(closes, highs, lows, signals, atr,
                           tp_mult=3.0, sl_mult=1.5, max_hold=25)


# ── Metrics Calculation ────────────────────────────────────────────────────
def calc_metrics(trades):
    """Calculate performance metrics from trade list."""
    if not trades:
        return None
    total = len(trades)
    pnls = [t["pnl_pct"] for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    gross_profit = sum(wins) if wins else 0.0
    gross_loss = abs(sum(losses)) if losses else 0.0
    pf = gross_profit / gross_loss if gross_loss > 0 else (999.0 if gross_profit > 0 else 0.0)
    wr = len(wins) / total * 100
    avg_win = np.mean(wins) if wins else 0.0
    avg_loss = np.mean(losses) if losses else 0.0
    net_pnl = sum(pnls)
    max_dd = 0.0
    cum = 0.0
    peak = 0.0
    for p in pnls:
        cum += p
        if cum > peak:
            peak = cum
        dd = peak - cum
        if dd > max_dd:
            max_dd = dd

    longs = [t for t in trades if t["direction"] == "LONG"]
    shorts = [t for t in trades if t["direction"] == "SHORT"]

    return {
        "trades": total,
        "win_rate": round(wr, 2),
        "profit_factor": round(pf, 3),
        "net_pnl_pct": round(net_pnl, 2),
        "avg_win_pct": round(avg_win, 3),
        "avg_loss_pct": round(avg_loss, 3),
        "max_drawdown_pct": round(max_dd, 2),
        "long_trades": len(longs),
        "short_trades": len(shorts),
        "tp_exits": len([t for t in trades if t["exit_reason"] == "TP"]),
        "sl_exits": len([t for t in trades if t["exit_reason"] == "SL"]),
        "maxhold_exits": len([t for t in trades if t["exit_reason"] == "MAX_HOLD"]),
    }


# ── Main Execution ─────────────────────────────────────────────────────────
STRATEGIES = {
    "S6_SuperTrend_Breakout": strategy_supertrend,
    "S7_VWAP_Deviation_Reversion": strategy_vwap_deviation,
    "S8_Triple_EMA_Momentum": strategy_triple_ema,
    "S9_Ichimoku_Cloud_Breakout": strategy_ichimoku,
}


def main():
    print("=" * 90)
    print("  BACKTEST: Trend Strategies 6-9 (SuperTrend / VWAP / Triple EMA / Ichimoku)")
    print(f"  Symbols: {len(SYMBOLS)} | Timeframes: {TIMEFRAMES} | Commission: {COMMISSION*100}%")
    print(f"  Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 90)

    all_results = []
    total_combos = len(SYMBOLS) * len(TIMEFRAMES) * len(STRATEGIES)
    done = 0

    for symbol in SYMBOLS:
        for tf in TIMEFRAMES:
            # Fetch data once per symbol/tf
            raw = fetch_klines(symbol, tf)
            if raw is None or len(raw) < 100:
                print(f"  [SKIP] {symbol} {tf} — insufficient data")
                done += len(STRATEGIES)
                continue

            opens, highs, lows, closes, volumes = parse_klines(raw)
            bars = len(closes)

            for strat_name, strat_func in STRATEGIES.items():
                done += 1
                try:
                    trades = strat_func(opens, highs, lows, closes, volumes)
                    metrics = calc_metrics(trades)
                    if metrics:
                        result = {
                            "strategy": strat_name,
                            "symbol": symbol,
                            "timeframe": tf,
                            "bars": bars,
                            **metrics,
                        }
                        all_results.append(result)
                except Exception as e:
                    print(f"  [ERR] {strat_name} {symbol} {tf}: {e}")

                if done % 20 == 0:
                    print(f"  Progress: {done}/{total_combos} combos tested...")

            # Small delay to avoid rate limiting
            time.sleep(0.15)

    # ── Save JSON ──────────────────────────────────────────────────────────
    with open(OUTPUT_FILE, "w") as f:
        json.dump({
            "generated": datetime.utcnow().isoformat(),
            "config": {
                "symbols": SYMBOLS,
                "timeframes": TIMEFRAMES,
                "commission": COMMISSION,
                "bars_per_symbol": KLINES_LIMIT,
            },
            "results": all_results,
        }, f, indent=2)
    print(f"\n  Results saved to: {OUTPUT_FILE}")

    # ── Display Results ────────────────────────────────────────────────────
    # Filter: PF > 1.0 and trades >= 10
    qualified = [r for r in all_results if r["profit_factor"] > 1.0 and r["trades"] >= 10]
    qualified.sort(key=lambda x: x["profit_factor"], reverse=True)

    print("\n" + "=" * 120)
    print("  RANKED RESULTS — PF > 1.0 AND Trades >= 10 (sorted by Profit Factor)")
    print("=" * 120)
    header = f"{'Rank':<5} {'Strategy':<30} {'Symbol':<10} {'TF':<5} {'Trades':>7} {'WR%':>7} {'PF':>8} {'Net%':>9} {'AvgW%':>8} {'AvgL%':>8} {'MaxDD%':>8} {'TP':>4} {'SL':>4} {'MH':>4}"
    print(header)
    print("-" * 120)

    for idx, r in enumerate(qualified, 1):
        print(f"{idx:<5} {r['strategy']:<30} {r['symbol']:<10} {r['timeframe']:<5} "
              f"{r['trades']:>7} {r['win_rate']:>7.1f} {r['profit_factor']:>8.3f} "
              f"{r['net_pnl_pct']:>9.2f} {r['avg_win_pct']:>8.3f} {r['avg_loss_pct']:>8.3f} "
              f"{r['max_drawdown_pct']:>8.2f} {r['tp_exits']:>4} {r['sl_exits']:>4} {r['maxhold_exits']:>4}")

    if not qualified:
        print("  (No combos met the PF>1.0 AND trades>=10 threshold)")

    # ── Recommended ────────────────────────────────────────────────────────
    recommended = [r for r in all_results
                   if r["win_rate"] > 50 and r["profit_factor"] > 1.2 and r["trades"] >= 15]
    recommended.sort(key=lambda x: x["profit_factor"], reverse=True)

    print("\n" + "=" * 120)
    print("  RECOMMENDED — WR > 50% AND PF > 1.2 AND Trades >= 15")
    print("=" * 120)
    print(header)
    print("-" * 120)

    for idx, r in enumerate(recommended, 1):
        print(f"{idx:<5} {r['strategy']:<30} {r['symbol']:<10} {r['timeframe']:<5} "
              f"{r['trades']:>7} {r['win_rate']:>7.1f} {r['profit_factor']:>8.3f} "
              f"{r['net_pnl_pct']:>9.2f} {r['avg_win_pct']:>8.3f} {r['avg_loss_pct']:>8.3f} "
              f"{r['max_drawdown_pct']:>8.2f} {r['tp_exits']:>4} {r['sl_exits']:>4} {r['maxhold_exits']:>4}")

    if not recommended:
        print("  (No combos met the RECOMMENDED threshold)")

    # ── Summary by Strategy ────────────────────────────────────────────────
    print("\n" + "=" * 90)
    print("  SUMMARY BY STRATEGY")
    print("=" * 90)
    for strat_name in STRATEGIES:
        strat_results = [r for r in all_results if r["strategy"] == strat_name]
        if not strat_results:
            print(f"  {strat_name}: No results")
            continue
        total_trades = sum(r["trades"] for r in strat_results)
        avg_pf = np.mean([r["profit_factor"] for r in strat_results])
        avg_wr = np.mean([r["win_rate"] for r in strat_results])
        avg_net = np.mean([r["net_pnl_pct"] for r in strat_results])
        profitable = len([r for r in strat_results if r["profit_factor"] > 1.0])
        rec_count = len([r for r in recommended if r["strategy"] == strat_name])
        print(f"  {strat_name:<35} | Combos: {len(strat_results):>3} | "
              f"Total Trades: {total_trades:>5} | Avg PF: {avg_pf:>6.3f} | "
              f"Avg WR: {avg_wr:>5.1f}% | Avg Net: {avg_net:>7.2f}% | "
              f"Profitable: {profitable:>3}/{len(strat_results)} | Recommended: {rec_count}")

    print(f"\n  Total combos tested: {len(all_results)}")
    print(f"  Qualified (PF>1, T>=10): {len(qualified)}")
    print(f"  Recommended (WR>50%, PF>1.2, T>=15): {len(recommended)}")
    print("=" * 90)


if __name__ == "__main__":
    main()
