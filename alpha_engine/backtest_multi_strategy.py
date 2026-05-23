#!/usr/bin/env python3
"""
Multi-Strategy Vectorized Backtest Engine
==========================================
Runs vectorized backtests across 8 symbols x 5 strategies (+ inverse).
Includes forward (OOS 7-day) validation.

Usage: python alpha_engine/backtest_multi_strategy.py
"""

import json
import os
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

try:
    import requests
except ImportError:
    print("ERROR: requests library required. pip install requests")
    sys.exit(1)


# -- Configuration ----------------------------------------------------------

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "DOGEUSDT", "XRPUSDT", "AVAXUSDT", "LINKUSDT"]
INTERVAL = "1h"
LIMIT = 720  # ~30 days of 1h candles
OOS_HOURS = 168  # last 7 days for forward test
COMMISSION_BPS = 10  # 0.10% per trade
ANNUALIZE_FACTOR = np.sqrt(365 * 24)  # hourly data annualized

DATA_DIR = Path(__file__).parent / "data"
RESULTS_FILE = DATA_DIR / "vectorized_backtest_results.json"


# -- Data Fetching (4-API fallback chain) -----------------------------------

def fetch_binance_klines(symbol, interval, limit):
    """Fetch from Binance with mirror fallback."""
    urls = [
        f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}",
        f"https://api1.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}",
        f"https://api2.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}",
        f"https://api3.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}",
    ]
    for url in urls:
        try:
            r = requests.get(url, timeout=15)
            if r.status_code == 200:
                data = r.json()
                if len(data) > 50:
                    arr = np.array([[float(c[1]), float(c[2]), float(c[3]), float(c[4]), float(c[5])] for c in data])
                    return arr  # shape (N, 5): O H L C V
        except Exception:
            continue
    return None


def fetch_coingecko_klines(symbol, limit):
    """Fallback: CoinGecko market chart."""
    cg_map = {
        "BTCUSDT": "bitcoin", "ETHUSDT": "ethereum", "SOLUSDT": "solana",
        "BNBUSDT": "binancecoin", "DOGEUSDT": "dogecoin", "XRPUSDT": "ripple",
        "AVAXUSDT": "avalanche-2", "LINKUSDT": "chainlink",
    }
    cg_id = cg_map.get(symbol)
    if not cg_id:
        return None
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{cg_id}/market_chart?vs_currency=usd&days=30"
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            data = r.json()
            prices = np.array([p[1] for p in data.get("prices", [])])
            if len(prices) > 50:
                ohlcv = np.column_stack([prices, prices, prices, prices, np.ones(len(prices))])
                return ohlcv
    except Exception:
        pass
    return None


def fetch_kucoin_klines(symbol, interval, limit):
    """Fallback: KuCoin klines."""
    kc_symbol = symbol.replace("USDT", "-USDT")
    try:
        end = int(time.time())
        start = end - limit * 3600
        url = f"https://api.kucoin.com/api/v1/market/candles?type=1hour&symbol={kc_symbol}&startAt={start}&endAt={end}"
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            data = r.json().get("data", [])
            if len(data) > 50:
                arr = np.array([[float(c[1]), float(c[3]), float(c[4]), float(c[2]), float(c[5])] for c in data])
                return arr[::-1]  # KuCoin returns newest first
    except Exception:
        pass
    return None


def fetch_ohlcv(symbol):
    """4-API fallback chain: Binance mirrors -> CoinGecko -> KuCoin."""
    data = fetch_binance_klines(symbol, INTERVAL, LIMIT)
    if data is not None:
        return data
    print(f"  [!] Binance failed for {symbol}, trying CoinGecko...")
    data = fetch_coingecko_klines(symbol, LIMIT)
    if data is not None:
        return data
    print(f"  [!] CoinGecko failed for {symbol}, trying KuCoin...")
    data = fetch_kucoin_klines(symbol, INTERVAL, LIMIT)
    return data


# -- Indicator Functions (vectorized) ---------------------------------------

def ema(prices, period):
    """Exponential moving average."""
    alpha = 2.0 / (period + 1)
    out = np.empty_like(prices)
    out[0] = prices[0]
    for i in range(1, len(prices)):
        out[i] = alpha * prices[i] + (1 - alpha) * out[i - 1]
    return out


def sma(prices, period):
    """Simple moving average using cumsum."""
    ret = np.cumsum(prices)
    ret[period:] = ret[period:] - ret[:-period]
    out = np.full_like(prices, np.nan)
    out[period - 1:] = ret[period - 1:] / period
    return out


def rolling_std(prices, period):
    """Rolling standard deviation using cumsum trick."""
    cs1 = np.cumsum(prices)
    cs2 = np.cumsum(prices ** 2)
    cs1_w = np.copy(cs1)
    cs2_w = np.copy(cs2)
    cs1_w[period:] = cs1[period:] - cs1[:-period]
    cs2_w[period:] = cs2[period:] - cs2[:-period]
    out = np.full_like(prices, np.nan)
    mean = cs1_w[period - 1:] / period
    var = cs2_w[period - 1:] / period - mean ** 2
    var = np.clip(var, 0, None)
    out[period - 1:] = np.sqrt(var)
    return out


def rsi(prices, period=14):
    """RSI using Wilder's smoothing."""
    delta = np.diff(prices, prepend=prices[0])
    gain = np.where(delta > 0, delta, 0.0)
    loss = np.where(delta < 0, -delta, 0.0)
    avg_gain = np.empty_like(prices)
    avg_loss = np.empty_like(prices)
    avg_gain[:period + 1] = np.nan
    avg_loss[:period + 1] = np.nan
    if period + 1 <= len(prices):
        avg_gain[period] = np.mean(gain[1:period + 1])
        avg_loss[period] = np.mean(loss[1:period + 1])
    for i in range(period + 1, len(prices)):
        avg_gain[i] = (avg_gain[i - 1] * (period - 1) + gain[i]) / period
        avg_loss[i] = (avg_loss[i - 1] * (period - 1) + loss[i]) / period
    rs = avg_gain / np.where(avg_loss == 0, 1e-10, avg_loss)
    out = 100.0 - 100.0 / (1.0 + rs)
    out[:period + 1] = np.nan
    return out


def bollinger_bands(prices, period=20, num_std=2.0):
    """Returns (middle, upper, lower)."""
    mid = sma(prices, period)
    std = rolling_std(prices, period)
    return mid, mid + num_std * std, mid - num_std * std


def macd_indicator(prices, fast=12, slow=26, signal_period=9):
    """MACD line, signal line, histogram."""
    ema_fast = ema(prices, fast)
    ema_slow = ema(prices, slow)
    macd_line = ema_fast - ema_slow
    signal_line = ema(macd_line, signal_period)
    return macd_line, signal_line, macd_line - signal_line


# -- Strategy Signal Generators ---------------------------------------------

def strategy_ema_crossover(close):
    """EMA 9/21 crossover: +1 long, -1 short."""
    ema9 = ema(close, 9)
    ema21 = ema(close, 21)
    signal = np.where(ema9 > ema21, 1.0, -1.0)
    signal[:21] = 0
    return signal


def strategy_rsi_mean_reversion(close):
    """RSI<30 buy, RSI>70 sell."""
    r = rsi(close, 14)
    signal = np.zeros(len(close))
    pos = 0.0
    for i in range(15, len(close)):
        if np.isnan(r[i]):
            continue
        if r[i] < 30 and pos <= 0:
            pos = 1.0
        elif r[i] > 70 and pos >= 0:
            pos = -1.0
        signal[i] = pos
    return signal


def strategy_bollinger_breakout(close):
    """Buy above upper BB, sell on mean reversion."""
    mid, upper, lower = bollinger_bands(close, 20, 2.0)
    signal = np.zeros(len(close))
    pos = 0.0
    for i in range(20, len(close)):
        if np.isnan(upper[i]):
            continue
        if close[i] > upper[i] and pos <= 0:
            pos = 1.0
        elif close[i] < mid[i] and pos > 0:
            pos = -1.0
        elif close[i] < lower[i] and pos >= 0:
            pos = -1.0
        elif close[i] > mid[i] and pos < 0:
            pos = 0.0
        signal[i] = pos
    return signal


def strategy_momentum_roc(close):
    """14-period Rate of Change: >2% long, <-2% short."""
    period = 14
    roc = np.zeros(len(close))
    roc[period:] = (close[period:] - close[:-period]) / close[:-period] * 100.0
    signal = np.where(roc > 2.0, 1.0, np.where(roc < -2.0, -1.0, 0.0))
    signal[:period] = 0
    return signal


def strategy_macd_cross(close):
    """MACD/Signal crossover."""
    macd_line, signal_line, _ = macd_indicator(close)
    signal = np.where(macd_line > signal_line, 1.0, -1.0)
    signal[:26] = 0
    return signal


STRATEGIES = {
    "EMA_Cross_9_21": strategy_ema_crossover,
    "RSI_MeanRevert": strategy_rsi_mean_reversion,
    "BB_Breakout": strategy_bollinger_breakout,
    "Momentum_ROC14": strategy_momentum_roc,
    "MACD_Cross": strategy_macd_cross,
}


# -- Backtest Engine --------------------------------------------------------

def compute_metrics(signals, close):
    """Compute strategy metrics from signal array and close prices."""
    n = len(close)
    if n < 10:
        return {"error": "insufficient data"}

    # Pct returns bar-to-bar
    pct_ret = np.zeros(n)
    pct_ret[1:] = (close[1:] - close[:-1]) / close[:-1]

    # Strategy returns = position[i-1] * return[i]
    strat_ret = np.zeros(n)
    strat_ret[1:] = signals[:-1] * pct_ret[1:]

    # Commission on position changes
    pos_changes = np.abs(np.diff(signals, prepend=0))
    commission = pos_changes * (COMMISSION_BPS / 10000.0)
    strat_ret -= commission

    # Identify trades (position changes)
    change_idx = np.where(np.diff(signals, prepend=0) != 0)[0]
    trades_pnl = []
    for i in range(len(change_idx) - 1):
        s = change_idx[i]
        e = change_idx[i + 1]
        trade_ret = np.sum(strat_ret[s:e])
        trades_pnl.append(trade_ret)

    trades_pnl = np.array(trades_pnl) if trades_pnl else np.array([0.0])
    wins = trades_pnl[trades_pnl > 0]
    losses = trades_pnl[trades_pnl <= 0]

    # Equity curve
    equity = np.cumprod(1.0 + strat_ret)
    running_max = np.maximum.accumulate(equity)
    dd = (equity - running_max) / np.where(running_max == 0, 1, running_max)
    max_dd = float(np.min(dd))

    # Sharpe
    mean_r = np.mean(strat_ret)
    std_r = np.std(strat_ret)
    sharpe = (mean_r / max(std_r, 1e-10)) * float(ANNUALIZE_FACTOR)

    # Profit factor
    gross_profit = float(np.sum(wins)) if len(wins) > 0 else 0.0
    gross_loss = float(np.abs(np.sum(losses))) if len(losses) > 0 else 1e-10
    pf = gross_profit / max(gross_loss, 1e-10)

    total_ret = float(equity[-1] - 1.0) * 100

    return {
        "total_trades": int(len(trades_pnl)),
        "win_rate": round(float(len(wins) / max(len(trades_pnl), 1) * 100), 2),
        "avg_pnl_pct": round(float(np.mean(trades_pnl) * 100), 4),
        "total_return_pct": round(total_ret, 4),
        "max_drawdown_pct": round(max_dd * 100, 4),
        "sharpe_ratio": round(sharpe, 4),
        "profit_factor": round(pf, 4),
        "best_trade_pct": round(float(np.max(trades_pnl) * 100), 4),
        "worst_trade_pct": round(float(np.min(trades_pnl) * 100), 4),
    }


def run_backtest(close, signal_fn, inverse=False):
    """Run backtest on full in-sample data."""
    signals = signal_fn(close)
    if inverse:
        signals = -signals
    return compute_metrics(signals, close)


def run_forward_test(close, signal_fn, inverse=False):
    """Forward test on last OOS_HOURS bars."""
    if len(close) <= OOS_HOURS + 50:
        return {"error": "insufficient data for OOS"}
    # Generate signals on full data, then evaluate only OOS portion
    signals = signal_fn(close)
    if inverse:
        signals = -signals
    oos_signals = signals[-OOS_HOURS:]
    oos_close = close[-OOS_HOURS:]
    return compute_metrics(oos_signals, oos_close)


# -- Main -------------------------------------------------------------------

def main():
    print("=" * 100)
    print("  MULTI-STRATEGY VECTORIZED BACKTEST ENGINE")
    print(f"  {len(SYMBOLS)} symbols x {len(STRATEGIES)} strategies x 2 (normal + inverse) = {len(SYMBOLS)*len(STRATEGIES)*2} tests")
    print(f"  Period: 30 days 1h candles | OOS: 7 days | Commission: {COMMISSION_BPS} bps")
    print(f"  Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 100)

    all_results = {}
    summary_rows = []

    for sym in SYMBOLS:
        print(f"\n[*] Fetching {sym}...", end=" ", flush=True)
        ohlcv = fetch_ohlcv(sym)
        if ohlcv is None:
            print("FAILED (all APIs)")
            continue
        close = ohlcv[:, 3]  # Close price column
        print(f"OK ({len(close)} bars, last=${close[-1]:.4f})")

        all_results[sym] = {}

        for strat_name, strat_fn in STRATEGIES.items():
            try:
                bt = run_backtest(close, strat_fn, inverse=False)
                ft = run_forward_test(close, strat_fn, inverse=False)
                bt_inv = run_backtest(close, strat_fn, inverse=True)
                ft_inv = run_forward_test(close, strat_fn, inverse=True)
            except Exception as e:
                print(f"  [!] {strat_name} error: {e}")
                bt = ft = bt_inv = ft_inv = {"error": str(e)}

            all_results[sym][strat_name] = {
                "backtest": bt,
                "forward_test": ft,
                "inverse_backtest": bt_inv,
                "inverse_forward_test": ft_inv,
            }

            for direction, res, fwd in [("NORM", bt, ft), ("INV", bt_inv, ft_inv)]:
                if "error" not in res:
                    summary_rows.append({
                        "symbol": sym,
                        "strategy": strat_name,
                        "dir": direction,
                        "return": res["total_return_pct"],
                        "sharpe": res["sharpe_ratio"],
                        "wr": res["win_rate"],
                        "mdd": res["max_drawdown_pct"],
                        "trades": res["total_trades"],
                        "pf": res["profit_factor"],
                        "oos_ret": fwd.get("total_return_pct", "N/A"),
                        "best": res["best_trade_pct"],
                        "worst": res["worst_trade_pct"],
                    })

    # -- Print Summary ------------------------------------------------------
    summary_rows.sort(key=lambda x: x["sharpe"], reverse=True)

    print("\n" + "=" * 140)
    print("  FULL RESULTS -- sorted by Sharpe ratio")
    print("=" * 140)
    hdr = f"{'Symbol':<10} {'Strategy':<16} {'Dir':<5} {'Return%':>9} {'Sharpe':>8} {'WR%':>7} {'MDD%':>9} {'Trades':>7} {'PF':>7} {'Best%':>8} {'Worst%':>9} {'OOS%':>9}"
    print(hdr)
    print("-" * 140)

    for row in summary_rows:
        oos = f"{row['oos_ret']:.2f}" if isinstance(row['oos_ret'], (int, float)) else "N/A"
        print(f"{row['symbol']:<10} {row['strategy']:<16} {row['dir']:<5} "
              f"{row['return']:>9.2f} {row['sharpe']:>8.2f} {row['wr']:>7.1f} "
              f"{row['mdd']:>9.2f} {row['trades']:>7} {row['pf']:>7.2f} "
              f"{row['best']:>8.2f} {row['worst']:>9.2f} {oos:>9}")

    # -- Top 10 by Sharpe ---------------------------------------------------
    print("\n" + "=" * 90)
    print("  TOP 10 BY SHARPE RATIO")
    print("=" * 90)
    for i, r in enumerate(summary_rows[:10]):
        oos = f"{r['oos_ret']:.2f}%" if isinstance(r['oos_ret'], (int, float)) else "N/A"
        print(f"  {i+1:>2}. {r['symbol']:<9} {r['strategy']:<16} ({r['dir']}) "
              f"Sharpe={r['sharpe']:>6.2f}  Ret={r['return']:>7.2f}%  WR={r['wr']:.0f}%  OOS={oos}")

    # -- Worst 5 (inverse candidates) --------------------------------------
    print(f"\n  WORST 5 (inverse/mutation candidates):")
    for i, r in enumerate(summary_rows[-5:]):
        print(f"  {i+1:>2}. {r['symbol']:<9} {r['strategy']:<16} ({r['dir']}) "
              f"Sharpe={r['sharpe']:>6.2f}  Ret={r['return']:>7.2f}%")

    # -- OOS leaders --------------------------------------------------------
    oos_valid = [r for r in summary_rows if isinstance(r.get("oos_ret"), (int, float))]
    oos_valid.sort(key=lambda x: x["oos_ret"], reverse=True)
    print(f"\n  TOP 10 BY OUT-OF-SAMPLE RETURN (7-day forward test):")
    for i, r in enumerate(oos_valid[:10]):
        print(f"  {i+1:>2}. {r['symbol']:<9} {r['strategy']:<16} ({r['dir']}) "
              f"OOS={r['oos_ret']:>7.2f}%  IS_Sharpe={r['sharpe']:>6.2f}")

    # -- Per-strategy aggregate ---------------------------------------------
    print(f"\n  STRATEGY AVERAGES (across all symbols, normal direction only):")
    print(f"  {'Strategy':<16} {'Avg Ret%':>10} {'Avg Sharpe':>12} {'Avg WR%':>10} {'Avg MDD%':>10}")
    print(f"  {'-'*60}")
    for sname in STRATEGIES:
        rows = [r for r in summary_rows if r["strategy"] == sname and r["dir"] == "NORM"]
        if rows:
            avg_ret = np.mean([r["return"] for r in rows])
            avg_sh = np.mean([r["sharpe"] for r in rows])
            avg_wr = np.mean([r["wr"] for r in rows])
            avg_mdd = np.mean([r["mdd"] for r in rows])
            print(f"  {sname:<16} {avg_ret:>10.2f} {avg_sh:>12.2f} {avg_wr:>10.1f} {avg_mdd:>10.2f}")

    # -- Save ---------------------------------------------------------------
    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "config": {
            "symbols": SYMBOLS,
            "interval": INTERVAL,
            "candles": LIMIT,
            "oos_hours": OOS_HOURS,
            "commission_bps": COMMISSION_BPS,
            "strategies": list(STRATEGIES.keys()),
        },
        "results_by_symbol": all_results,
        "rankings": {
            "by_sharpe": [{"rank": i + 1, **r} for i, r in enumerate(summary_rows[:20])],
            "by_oos_return": [{"rank": i + 1, **r} for i, r in enumerate(oos_valid[:20])],
        },
        "total_tests": len(summary_rows),
    }

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_FILE, "w") as f:
        json.dump(output, f, indent=2, default=str)

    print(f"\n[+] Results saved to {RESULTS_FILE}")
    print(f"[+] Total tests: {len(summary_rows)} | Symbols: {len(all_results)} | Strategies: {len(STRATEGIES)}")
    return output


if __name__ == "__main__":
    main()
