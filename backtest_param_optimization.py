#!/usr/bin/env python3
"""
Parameter Optimization for Top 3 Winning Strategies
Optimizes SuperTrend, Keltner+ADX, EMA Cross+Volume on best symbol+TF combos.
"""

import json
import time
import itertools
import requests
import numpy as np
from datetime import datetime

# ── Binance API failover ──
BINANCE_MIRRORS = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
]

COMMISSION = 0.0005  # 0.05%

INTERVAL_MS = {
    "1h": 3600000,
    "4h": 14400000,
    "1d": 86400000,
}


def fetch_klines(symbol: str, interval: str, limit: int = 1000):
    """Fetch klines with Binance mirror failover."""
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    for mirror in BINANCE_MIRRORS:
        try:
            r = requests.get(f"{mirror}/api/v3/klines", params=params, timeout=15)
            if r.status_code == 200:
                data = r.json()
                arr = np.array(
                    [[float(c[1]), float(c[2]), float(c[3]), float(c[4]), float(c[5])] for c in data],
                    dtype=np.float64,
                )
                return arr  # columns: open, high, low, close, volume
        except Exception:
            continue
    raise RuntimeError(f"All Binance mirrors failed for {symbol} {interval}")


# ── Indicator helpers ──

def calc_atr(highs, lows, closes, period):
    n = len(closes)
    tr = np.empty(n)
    tr[0] = highs[0] - lows[0]
    for i in range(1, n):
        tr[i] = max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
    atr = np.empty(n)
    atr[:period] = np.nan
    atr[period] = np.mean(tr[1 : period + 1])
    for i in range(period + 1, n):
        atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period
    return atr


def calc_ema(src, period):
    ema = np.empty_like(src)
    ema[:] = np.nan
    k = 2.0 / (period + 1)
    start = period - 1
    ema[start] = np.mean(src[:period])
    for i in range(start + 1, len(src)):
        ema[i] = src[i] * k + ema[i - 1] * (1 - k)
    return ema


def calc_supertrend(highs, lows, closes, atr_period, multiplier):
    atr = calc_atr(highs, lows, closes, atr_period)
    n = len(closes)
    upper = np.empty(n)
    lower = np.empty(n)
    st = np.empty(n)
    direction = np.ones(n)  # 1=up (bullish), -1=down

    hl2 = (highs + lows) / 2.0
    for i in range(n):
        if np.isnan(atr[i]):
            upper[i] = lower[i] = st[i] = np.nan
            continue
        basic_upper = hl2[i] + multiplier * atr[i]
        basic_lower = hl2[i] - multiplier * atr[i]
        if i == 0 or np.isnan(upper[i - 1]):
            upper[i] = basic_upper
            lower[i] = basic_lower
            st[i] = basic_lower
            direction[i] = 1
            continue
        upper[i] = basic_upper if basic_upper < upper[i - 1] or closes[i - 1] > upper[i - 1] else upper[i - 1]
        lower[i] = basic_lower if basic_lower > lower[i - 1] or closes[i - 1] < lower[i - 1] else lower[i - 1]

        if direction[i - 1] == 1:
            if closes[i] < lower[i]:
                direction[i] = -1
                st[i] = upper[i]
            else:
                direction[i] = 1
                st[i] = lower[i]
        else:
            if closes[i] > upper[i]:
                direction[i] = 1
                st[i] = lower[i]
            else:
                direction[i] = -1
                st[i] = upper[i]
    return st, direction, atr


def calc_adx(highs, lows, closes, period=14):
    n = len(closes)
    plus_dm = np.zeros(n)
    minus_dm = np.zeros(n)
    tr = np.zeros(n)

    for i in range(1, n):
        up = highs[i] - highs[i - 1]
        down = lows[i - 1] - lows[i]
        plus_dm[i] = up if up > down and up > 0 else 0
        minus_dm[i] = down if down > up and down > 0 else 0
        tr[i] = max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))

    atr_s = np.empty(n)
    plus_di_s = np.empty(n)
    minus_di_s = np.empty(n)
    adx = np.empty(n)
    atr_s[:] = plus_di_s[:] = minus_di_s[:] = adx[:] = np.nan

    atr_s[period] = np.sum(tr[1 : period + 1])
    sm_plus = np.sum(plus_dm[1 : period + 1])
    sm_minus = np.sum(minus_dm[1 : period + 1])

    for i in range(period + 1, n):
        atr_s[i] = atr_s[i - 1] - atr_s[i - 1] / period + tr[i]
        sm_plus = sm_plus - sm_plus / period + plus_dm[i]
        sm_minus = sm_minus - sm_minus / period + minus_dm[i]
        if atr_s[i] > 0:
            plus_di_s[i] = 100 * sm_plus / atr_s[i]
            minus_di_s[i] = 100 * sm_minus / atr_s[i]
        else:
            plus_di_s[i] = plus_di_s[i - 1] if not np.isnan(plus_di_s[i - 1]) else 0
            minus_di_s[i] = minus_di_s[i - 1] if not np.isnan(minus_di_s[i - 1]) else 0

    # ADX = EMA of DX
    dx = np.zeros(n)
    for i in range(period + 1, n):
        s = plus_di_s[i] + minus_di_s[i]
        dx[i] = 100 * abs(plus_di_s[i] - minus_di_s[i]) / s if s > 0 else 0

    # Smooth ADX
    start = 2 * period
    if start < n:
        adx[start] = np.mean(dx[period + 1 : start + 1])
        for i in range(start + 1, n):
            adx[i] = (adx[i - 1] * (period - 1) + dx[i]) / period

    return adx, plus_di_s, minus_di_s


# ── Backtest engines ──

def backtest_supertrend(data, atr_period, multiplier, tp_mult, sl_mult):
    o, h, l, c, v = data[:, 0], data[:, 1], data[:, 2], data[:, 3], data[:, 4]
    st, direction, atr = calc_supertrend(h, l, c, atr_period, multiplier)
    trades = []
    pos = 0  # 0=flat, 1=long
    entry = 0.0
    tp = sl = 0.0

    warmup = max(atr_period + 2, 20)
    for i in range(warmup, len(c)):
        if np.isnan(atr[i]) or np.isnan(st[i]):
            continue
        if pos == 0:
            # Enter long on direction flip to bullish
            if direction[i] == 1 and direction[i - 1] == -1:
                entry = c[i] * (1 + COMMISSION)
                tp = entry + tp_mult * atr[i]
                sl = entry - sl_mult * atr[i]
                pos = 1
        else:
            # Check exit
            if h[i] >= tp:
                pnl = (tp / entry - 1) - COMMISSION
                trades.append(pnl)
                pos = 0
            elif l[i] <= sl:
                pnl = (sl / entry - 1) - COMMISSION
                trades.append(pnl)
                pos = 0
            elif direction[i] == -1:
                pnl = (c[i] / entry - 1) - COMMISSION
                trades.append(pnl)
                pos = 0

            # Early stopping: first 5 trades all losses
            if len(trades) == 5 and all(t <= 0 for t in trades):
                return trades
    return trades


def backtest_keltner_adx(data, kelt_ema_period, kelt_atr_mult, adx_thresh, tp_mult, sl_mult):
    o, h, l, c, v = data[:, 0], data[:, 1], data[:, 2], data[:, 3], data[:, 4]
    ema = calc_ema(c, kelt_ema_period)
    atr = calc_atr(h, l, c, kelt_ema_period)
    adx, plus_di, minus_di = calc_adx(h, l, c, 14)

    trades = []
    pos = 0
    entry = tp = sl = 0.0

    warmup = max(kelt_ema_period, 30)
    for i in range(warmup, len(c)):
        if np.isnan(ema[i]) or np.isnan(atr[i]) or np.isnan(adx[i]):
            continue
        upper_band = ema[i] + kelt_atr_mult * atr[i]
        lower_band = ema[i] - kelt_atr_mult * atr[i]

        if pos == 0:
            # Long: close breaks above upper Keltner + ADX strong + +DI > -DI
            if c[i] > upper_band and adx[i] >= adx_thresh:
                if not np.isnan(plus_di[i]) and not np.isnan(minus_di[i]) and plus_di[i] > minus_di[i]:
                    entry = c[i] * (1 + COMMISSION)
                    tp = entry + tp_mult * atr[i]
                    sl = entry - sl_mult * atr[i]
                    pos = 1
        else:
            if h[i] >= tp:
                pnl = (tp / entry - 1) - COMMISSION
                trades.append(pnl)
                pos = 0
            elif l[i] <= sl:
                pnl = (sl / entry - 1) - COMMISSION
                trades.append(pnl)
                pos = 0
            elif c[i] < ema[i]:
                pnl = (c[i] / entry - 1) - COMMISSION
                trades.append(pnl)
                pos = 0

            if len(trades) == 5 and all(t <= 0 for t in trades):
                return trades
    return trades


def backtest_ema_cross_vol(data, fast_period, slow_period, vol_mult, tp_mult, sl_mult):
    o, h, l, c, v = data[:, 0], data[:, 1], data[:, 2], data[:, 3], data[:, 4]
    if fast_period >= slow_period:
        return []
    fast_ema = calc_ema(c, fast_period)
    slow_ema = calc_ema(c, slow_period)
    atr = calc_atr(h, l, c, 14)
    vol_sma = np.empty_like(v)
    vol_sma[:] = np.nan
    vp = 20
    for i in range(vp - 1, len(v)):
        vol_sma[i] = np.mean(v[i - vp + 1 : i + 1])

    trades = []
    pos = 0
    entry = tp = sl = 0.0

    warmup = max(slow_period + 2, 25)
    for i in range(warmup, len(c)):
        if np.isnan(fast_ema[i]) or np.isnan(slow_ema[i]) or np.isnan(atr[i]) or np.isnan(vol_sma[i]):
            continue
        if pos == 0:
            # Golden cross + volume spike
            if fast_ema[i] > slow_ema[i] and fast_ema[i - 1] <= slow_ema[i - 1]:
                if v[i] >= vol_mult * vol_sma[i]:
                    entry = c[i] * (1 + COMMISSION)
                    tp = entry + tp_mult * atr[i]
                    sl = entry - sl_mult * atr[i]
                    pos = 1
        else:
            if h[i] >= tp:
                pnl = (tp / entry - 1) - COMMISSION
                trades.append(pnl)
                pos = 0
            elif l[i] <= sl:
                pnl = (sl / entry - 1) - COMMISSION
                trades.append(pnl)
                pos = 0
            elif fast_ema[i] < slow_ema[i]:
                pnl = (c[i] / entry - 1) - COMMISSION
                trades.append(pnl)
                pos = 0

            if len(trades) == 5 and all(t <= 0 for t in trades):
                return trades
    return trades


# ── Metrics ──

def calc_metrics(trades):
    if len(trades) < 3:
        return None
    trades = np.array(trades)
    wins = trades[trades > 0]
    losses = trades[trades <= 0]
    wr = len(wins) / len(trades) * 100
    gross_profit = np.sum(wins) if len(wins) > 0 else 0
    gross_loss = abs(np.sum(losses)) if len(losses) > 0 else 0.0001
    pf = gross_profit / gross_loss if gross_loss > 0 else gross_profit / 0.0001
    net_pnl = np.sum(trades) * 100  # percentage
    # Sharpe (per-trade)
    sharpe = np.mean(trades) / np.std(trades) if np.std(trades) > 0 else 0
    # Max drawdown
    equity = np.cumsum(trades)
    peak = np.maximum.accumulate(equity)
    dd = peak - equity
    max_dd = np.max(dd) * 100 if len(dd) > 0 else 0
    return {
        "trades": int(len(trades)),
        "win_rate": round(wr, 1),
        "profit_factor": round(pf, 2),
        "net_pnl_pct": round(net_pnl, 2),
        "sharpe": round(sharpe, 3),
        "max_dd_pct": round(max_dd, 2),
    }


# ── Main optimization ──

def optimize_strategy(strategy_name, symbols_tf, param_grid, backtest_fn, data_cache):
    """Run grid search for one strategy across symbols."""
    results = {}
    keys = list(param_grid.keys())
    combos = list(itertools.product(*param_grid.values()))
    total_combos = len(combos) * len(symbols_tf)

    print(f"\n{'='*70}")
    print(f"  {strategy_name}: {len(combos)} combos x {len(symbols_tf)} symbols = {total_combos} backtests")
    print(f"{'='*70}")

    for sym, tf in symbols_tf:
        label = f"{sym}_{tf}"
        print(f"\n  [{label}] Fetching data...", end=" ", flush=True)
        cache_key = f"{sym}_{tf}"
        if cache_key not in data_cache:
            data_cache[cache_key] = fetch_klines(sym, tf, 1000)
            time.sleep(0.2)
        data = data_cache[cache_key]
        print(f"{len(data)} bars. Running {len(combos)} combos...", flush=True)

        sym_results = []
        skipped = 0
        for idx, vals in enumerate(combos):
            params = dict(zip(keys, vals))
            trades = backtest_fn(data, **params)
            m = calc_metrics(trades)
            if m is None:
                skipped += 1
                continue
            m["params"] = {k: v for k, v in params.items()}
            sym_results.append(m)

            if (idx + 1) % 100 == 0:
                print(f"    {idx+1}/{len(combos)} done ({skipped} skipped)", flush=True)

        print(f"    Completed: {len(sym_results)} valid, {skipped} skipped (too few trades/early stop)")

        # Sort by Sharpe
        sym_results.sort(key=lambda x: x["sharpe"], reverse=True)
        results[label] = sym_results[:20]  # top 20

        if sym_results:
            best = sym_results[0]
            print(f"    BEST: Sharpe={best['sharpe']}, PF={best['profit_factor']}, "
                  f"WR={best['win_rate']}%, Trades={best['trades']}, "
                  f"Net={best['net_pnl_pct']}%, MaxDD={best['max_dd_pct']}%")
            print(f"    Params: {best['params']}")
    return results


def main():
    print("=" * 70)
    print("  PARAMETER OPTIMIZATION — Top 3 Winning Strategies")
    print(f"  Started: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 70)

    data_cache = {}
    all_results = {}

    # ── Strategy 1: SuperTrend Breakout ──
    st_grid = {
        "atr_period": [7, 10, 14, 20],
        "multiplier": [2.0, 2.5, 3.0, 3.5, 4.0],
        "tp_mult": [1.5, 2.0, 2.5, 3.0],
        "sl_mult": [1.0, 1.5, 2.0],
    }
    st_symbols = [("ADAUSDT", "1h"), ("AVAXUSDT", "4h"), ("BTCUSDT", "1h")]
    st_results = optimize_strategy(
        "SuperTrend Breakout", st_symbols, st_grid, backtest_supertrend, data_cache
    )
    all_results["SuperTrend_Breakout"] = st_results

    # ── Strategy 2: Keltner+ADX ──
    ka_grid = {
        "kelt_ema_period": [10, 15, 20, 25],
        "kelt_atr_mult": [1.0, 1.5, 2.0, 2.5],
        "adx_thresh": [20, 25, 30, 35],
        "tp_mult": [1.5, 2.0, 2.5],
        "sl_mult": [0.75, 1.0, 1.5],
    }
    ka_symbols = [("LINKUSDT", "1h"), ("ADAUSDT", "1h")]
    ka_results = optimize_strategy(
        "Keltner+ADX", ka_symbols, ka_grid, backtest_keltner_adx, data_cache
    )
    all_results["Keltner_ADX"] = ka_results

    # ── Strategy 3: EMA Cross+Volume ──
    ev_grid = {
        "fast_period": [5, 8, 9, 12],
        "slow_period": [15, 18, 21, 26],
        "vol_mult": [1.2, 1.5, 2.0, 2.5],
        "tp_mult": [1.5, 2.0, 2.5, 3.0],
        "sl_mult": [1.0, 1.5, 2.0],
    }
    ev_symbols = [("ADAUSDT", "1h"), ("DOGEUSDT", "1d")]
    ev_results = optimize_strategy(
        "EMA Cross+Volume", ev_symbols, ev_grid, backtest_ema_cross_vol, data_cache
    )
    all_results["EMA_Cross_Volume"] = ev_results

    # ── Save results ──
    out_path = "e:/findtorontoevents_antigravity.ca/backtest_optimized_params.json"
    with open(out_path, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nResults saved to {out_path}")

    # ── Final summary ──
    print("\n" + "=" * 70)
    print("  DEPLOYMENT-READY PARAMETERS (Best by Sharpe)")
    print("=" * 70)
    for strat_name, strat_data in all_results.items():
        print(f"\n  >> {strat_name}")
        for label, top20 in strat_data.items():
            if top20:
                b = top20[0]
                print(f"     {label}: Sharpe={b['sharpe']} | PF={b['profit_factor']} | "
                      f"WR={b['win_rate']}% | Trades={b['trades']} | "
                      f"Net={b['net_pnl_pct']}% | MaxDD={b['max_dd_pct']}%")
                print(f"       Params: {b['params']}")
            else:
                print(f"     {label}: No valid results")

    print(f"\nCompleted: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")


if __name__ == "__main__":
    main()
