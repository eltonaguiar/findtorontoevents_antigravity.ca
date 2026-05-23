#!/usr/bin/env python3
"""
Simpleton CURSOR Backtesting Tool
==================================
Tests all 12 strategies from Simpletonv0.01_CURSOR.pine against crypto pairs.
Finds optimal strategy + timeframe combinations per symbol.
Saves results to JSON for the Pine Script performance table.

Usage:
    python backtest_cursor.py                    # Run all strategies on all pairs
    python backtest_cursor.py --symbol BTCUSDT   # Single pair
    python backtest_cursor.py --strategy rsi2    # Single strategy
    python backtest_cursor.py --timeframe 4h     # Single timeframe
    python backtest_cursor.py --save-best        # Save best strategy per symbol
    python backtest_cursor.py --fetch            # Download data via ccxt if missing
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "AVAXUSDT", "DOGEUSDT", "ADAUSDT", "LINKUSDT", "MATICUSDT",
]
TIMEFRAMES = ["15m", "1h", "4h", "1d"]
RESULTS_DIR = Path("backtest_results")

# ---------------------------------------------------------------------------
# Indicator helpers
# ---------------------------------------------------------------------------

def rsi(close: pd.Series, period: int = 2) -> pd.Series:
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(period).mean()


def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    h, l, c = df["high"], df["low"], df["close"]
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def wma(series: pd.Series, period: int) -> pd.Series:
    weights = np.arange(1, period + 1, dtype=float)
    return series.rolling(period).apply(lambda x: np.dot(x, weights) / weights.sum(), raw=True)


def linreg(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(period).apply(
        lambda y: np.polyfit(np.arange(len(y)), y, 1)[0] * (len(y) - 1) + np.polyfit(np.arange(len(y)), y, 1)[1],
        raw=True,
    )


# ---------------------------------------------------------------------------
# Strategy signal generators
# Each returns a DataFrame with columns: signal (+1 long, -1 short, 0 none)
# ---------------------------------------------------------------------------

def strat_connors_rsi2(df: pd.DataFrame, params: dict) -> pd.Series:
    rsi_period = params.get("rsi_period", 2)
    entry_th = params.get("entry_th", 10)
    exit_th = params.get("exit_th", 70)
    trend_period = params.get("trend_period", 200)

    r = rsi(df["close"], rsi_period)
    trend = sma(df["close"], trend_period)
    sig = pd.Series(0, index=df.index)
    sig[(r < entry_th) & (df["close"] > trend)] = 1
    sig[(r > (100 - entry_th)) & (df["close"] < trend)] = -1
    return sig


def strat_zscore_mr(df: pd.DataFrame, params: dict) -> pd.Series:
    period = params.get("period", 20)
    entry = params.get("entry", 2.0)
    mean = sma(df["close"], period)
    std = df["close"].rolling(period).std()
    z = (df["close"] - mean) / std.replace(0, np.nan)
    sig = pd.Series(0, index=df.index)
    sig[z < -entry] = 1
    sig[z > entry] = -1
    return sig


def strat_ema_rsi(df: pd.DataFrame, params: dict) -> pd.Series:
    fast = ema(df["close"], params.get("fast", 9))
    slow = ema(df["close"], params.get("slow", 21))
    r = rsi(df["close"], 14)
    cross_up = (fast > slow) & (fast.shift() <= slow.shift())
    cross_dn = (fast < slow) & (fast.shift() >= slow.shift())
    sig = pd.Series(0, index=df.index)
    sig[cross_up & (r < 70)] = 1
    sig[cross_dn & (r > 30)] = -1
    return sig


def strat_macd_rsi(df: pd.DataFrame, params: dict) -> pd.Series:
    fast_p = params.get("fast", 12)
    slow_p = params.get("slow", 26)
    sig_p = params.get("signal", 9)
    fast_e = ema(df["close"], fast_p)
    slow_e = ema(df["close"], slow_p)
    macd_line = fast_e - slow_e
    signal_line = ema(macd_line, sig_p)
    hist = macd_line - signal_line
    r = rsi(df["close"], 14)
    cross_up = (macd_line > signal_line) & (macd_line.shift() <= signal_line.shift())
    cross_dn = (macd_line < signal_line) & (macd_line.shift() >= signal_line.shift())
    sig = pd.Series(0, index=df.index)
    sig[cross_up & (r < 50) & (hist > hist.shift())] = 1
    sig[cross_dn & (r > 50) & (hist < hist.shift())] = -1
    return sig


def strat_bollinger_squeeze(df: pd.DataFrame, params: dict) -> pd.Series:
    bb_mid = sma(df["close"], 20)
    bb_std = df["close"].rolling(20).std() * 2
    bb_up = bb_mid + bb_std
    bb_lo = bb_mid - bb_std
    kc_mid = ema(df["close"], 20)
    kc_r = atr(df, 10) * 1.5
    kc_up = kc_mid + kc_r
    kc_lo = kc_mid - kc_r
    squeeze = (bb_lo > kc_lo) & (bb_up < kc_up)
    release = ~squeeze & squeeze.shift().fillna(False)
    mom = df["close"] - bb_mid
    sig = pd.Series(0, index=df.index)
    sig[release & (mom > 0)] = 1
    sig[release & (mom < 0)] = -1
    return sig


def strat_vwap_reversion(df: pd.DataFrame, params: dict) -> pd.Series:
    if "volume" not in df.columns or df["volume"].sum() == 0:
        return pd.Series(0, index=df.index)
    cum_vol = df["volume"].cumsum()
    cum_vp = (df["close"] * df["volume"]).cumsum()
    vwap = cum_vp / cum_vol.replace(0, np.nan)
    a = atr(df, 14)
    z = (df["close"] - vwap) / a.replace(0, np.nan)
    sig = pd.Series(0, index=df.index)
    sig[z < -1.5] = 1
    sig[z > 1.5] = -1
    return sig


def strat_supertrend(df: pd.DataFrame, params: dict) -> pd.Series:
    factor = params.get("factor", 3.0)
    atr_p = params.get("atr_period", 10)
    a = atr(df, atr_p)
    hl2 = (df["high"] + df["low"]) / 2
    upper = hl2 + factor * a
    lower = hl2 - factor * a
    st = pd.Series(np.nan, index=df.index)
    direction = pd.Series(1, index=df.index)
    for i in range(1, len(df)):
        if df["close"].iloc[i] > upper.iloc[i - 1]:
            direction.iloc[i] = 1
        elif df["close"].iloc[i] < lower.iloc[i - 1]:
            direction.iloc[i] = -1
        else:
            direction.iloc[i] = direction.iloc[i - 1]
    cross_up = (direction == 1) & (direction.shift() == -1)
    cross_dn = (direction == -1) & (direction.shift() == 1)
    sig = pd.Series(0, index=df.index)
    sig[cross_up] = 1
    sig[cross_dn] = -1
    return sig


def strat_ichimoku(df: pd.DataFrame, params: dict) -> pd.Series:
    tenkan = (df["high"].rolling(9).max() + df["low"].rolling(9).min()) / 2
    kijun = (df["high"].rolling(26).max() + df["low"].rolling(26).min()) / 2
    span_a = ((tenkan + kijun) / 2).shift(26)
    span_b = ((df["high"].rolling(52).max() + df["low"].rolling(52).min()) / 2).shift(26)
    cloud_top = pd.concat([span_a, span_b], axis=1).max(axis=1)
    cloud_bot = pd.concat([span_a, span_b], axis=1).min(axis=1)
    tk_cross_up = (tenkan > kijun) & (tenkan.shift() <= kijun.shift())
    tk_cross_dn = (tenkan < kijun) & (tenkan.shift() >= kijun.shift())
    sig = pd.Series(0, index=df.index)
    sig[tk_cross_up & (df["close"] > cloud_top)] = 1
    sig[tk_cross_dn & (df["close"] < cloud_bot)] = -1
    return sig


def strat_hma_trend(df: pd.DataFrame, params: dict) -> pd.Series:
    n = 50
    half = wma(df["close"], n // 2)
    full = wma(df["close"], n)
    diff = 2 * half - full
    hma_val = wma(diff, int(np.floor(np.sqrt(n))))
    sma50 = sma(df["close"], 50)
    r = rsi(df["close"], 14)
    hma_up = (hma_val > hma_val.shift()) & (hma_val.shift() <= hma_val.shift(2))
    hma_dn = (hma_val < hma_val.shift()) & (hma_val.shift() >= hma_val.shift(2))
    sig = pd.Series(0, index=df.index)
    sig[hma_up & (df["close"] > sma50) & (r < 75)] = 1
    sig[hma_dn & (df["close"] < sma50) & (r > 25)] = -1
    return sig


def strat_sfp(df: pd.DataFrame, params: dict) -> pd.Series:
    swing_hi = df["high"].rolling(20).max().shift(1)
    swing_lo = df["low"].rolling(20).min().shift(1)
    rng = df["high"] - df["low"]
    wick_below = swing_lo - df["low"]
    wick_above = df["high"] - swing_hi
    bull = (df["low"] < swing_lo) & (df["close"] > swing_lo) & (df["close"] > df["open"]) & (rng > 0) & (wick_below / rng >= 0.25)
    bear = (df["high"] > swing_hi) & (df["close"] < swing_hi) & (df["close"] < df["open"]) & (rng > 0) & (wick_above / rng >= 0.25)
    sig = pd.Series(0, index=df.index)
    sig[bull] = 1
    sig[bear] = -1
    return sig


def strat_liquidity_sweep(df: pd.DataFrame, params: dict) -> pd.Series:
    swing_lo = df["low"].rolling(20).min().shift(5)
    swing_hi = df["high"].rolling(20).max().shift(5)
    ema50 = ema(df["close"], 50)
    rng = df["high"] - df["low"]
    lo_sweep = (df["low"] < swing_lo * 0.997) & (df["close"] > swing_lo)
    lo_wick = (df["close"] - df["low"]) > rng * 0.6
    hi_sweep = (df["high"] > swing_hi * 1.003) & (df["close"] < swing_hi)
    hi_wick = (df["high"] - df["close"]) > rng * 0.6
    sig = pd.Series(0, index=df.index)
    sig[lo_sweep & lo_wick & (df["close"] > ema50)] = 1
    sig[hi_sweep & hi_wick & (df["close"] < ema50)] = -1
    return sig


def strat_consensus(df: pd.DataFrame, params: dict) -> pd.Series:
    min_agree = params.get("min_agree", 3)
    strats = [
        strat_connors_rsi2, strat_zscore_mr, strat_ema_rsi,
        strat_macd_rsi, strat_bollinger_squeeze, strat_vwap_reversion,
        strat_supertrend, strat_ichimoku, strat_hma_trend,
        strat_sfp, strat_liquidity_sweep,
    ]
    long_sum = pd.Series(0, index=df.index)
    short_sum = pd.Series(0, index=df.index)
    for fn in strats:
        try:
            s = fn(df, {})
            long_sum += (s == 1).astype(int)
            short_sum += (s == -1).astype(int)
        except Exception:
            pass
    sig = pd.Series(0, index=df.index)
    sig[long_sum >= min_agree] = 1
    sig[short_sum >= min_agree] = -1
    return sig


STRATEGIES = {
    "ConnorsRSI2": (strat_connors_rsi2, {}),
    "ZScoreMR": (strat_zscore_mr, {}),
    "EMARSI": (strat_ema_rsi, {}),
    "MACDRSI": (strat_macd_rsi, {}),
    "BollingerSqueeze": (strat_bollinger_squeeze, {}),
    "VWAPReversion": (strat_vwap_reversion, {}),
    "Supertrend": (strat_supertrend, {}),
    "Ichimoku": (strat_ichimoku, {}),
    "HMATrend": (strat_hma_trend, {}),
    "SFP": (strat_sfp, {}),
    "LiquiditySweep": (strat_liquidity_sweep, {}),
    "Consensus": (strat_consensus, {"min_agree": 3}),
}

STRATEGY_ALIASES = {
    "rsi2": "ConnorsRSI2", "connors": "ConnorsRSI2",
    "zscore": "ZScoreMR", "zmr": "ZScoreMR",
    "ema": "EMARSI", "emarsi": "EMARSI",
    "macd": "MACDRSI", "macd_rsi": "MACDRSI",
    "bb": "BollingerSqueeze", "bollinger": "BollingerSqueeze",
    "vwap": "VWAPReversion",
    "supertrend": "Supertrend", "st": "Supertrend",
    "ichimoku": "Ichimoku", "ichi": "Ichimoku",
    "hma": "HMATrend",
    "sfp": "SFP", "swing": "SFP",
    "liq": "LiquiditySweep", "sweep": "LiquiditySweep",
    "consensus": "Consensus", "multi": "Consensus",
}


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_data(symbol: str, tf: str) -> Optional[pd.DataFrame]:
    """Try multiple paths to find OHLCV data."""
    base = symbol.replace("USDT", "").replace("USD", "")
    candidates = [
        Path(f"tmp/Binance_{symbol}_{tf}.csv"),
        Path(f"data/crypto/{tf}/{symbol}.csv"),
        Path(f"data/crypto/{tf}/{base}.csv"),
        Path(f"tmp/Binance_{symbol}_{tf.upper()}.csv"),
    ]
    for p in candidates:
        if p.exists():
            try:
                df = pd.read_csv(p)
                cols = {c: c.lower().strip() for c in df.columns}
                df.rename(columns=cols, inplace=True)
                for alias, target in [("date", "timestamp"), ("time", "timestamp"), ("datetime", "timestamp")]:
                    if alias in df.columns and target not in df.columns:
                        df.rename(columns={alias: target}, inplace=True)
                if "timestamp" in df.columns:
                    df["timestamp"] = pd.to_datetime(df["timestamp"])
                    df.set_index("timestamp", inplace=True)
                df.sort_index(inplace=True)
                needed = {"open", "high", "low", "close"}
                if not needed.issubset(set(df.columns)):
                    continue
                if "volume" not in df.columns:
                    df["volume"] = 0.0
                return df
            except Exception:
                continue
    return None


def fetch_data(symbol: str, tf: str) -> Optional[pd.DataFrame]:
    """Download via ccxt (Binance). Requires: pip install ccxt"""
    try:
        import ccxt
    except ImportError:
        print(f"  [!] ccxt not installed. Run: pip install ccxt")
        return None
    try:
        exchange = ccxt.binance({"enableRateLimit": True})
        tf_map = {"15m": "15m", "1h": "1h", "4h": "4h", "1d": "1d"}
        ohlcv = exchange.fetch_ohlcv(symbol.replace("USDT", "/USDT"), tf_map.get(tf, tf), limit=1000)
        df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("timestamp", inplace=True)
        out = Path(f"tmp/Binance_{symbol}_{tf}.csv")
        out.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(out)
        print(f"  [+] Downloaded {symbol} {tf} -> {out}")
        return df
    except Exception as e:
        print(f"  [!] Failed to fetch {symbol} {tf}: {e}")
        return None


# ---------------------------------------------------------------------------
# Backtesting engine (simple vectorized)
# ---------------------------------------------------------------------------

def backtest(df: pd.DataFrame, signals: pd.Series, tp_pct: float = 3.0, sl_pct: float = 1.5,
             max_hold: int = 20, commission_pct: float = 0.075) -> Dict:
    """Simple vectorized backtest. Returns metrics dict."""
    trades = []
    position = 0  # 0=flat, 1=long, -1=short
    entry_price = 0.0
    entry_bar = 0

    for i in range(len(df)):
        sig = signals.iloc[i]
        close_price = df["close"].iloc[i]

        if position != 0:
            bars_held = i - entry_bar
            pnl_pct = (close_price / entry_price - 1) * position * 100

            hit_tp = pnl_pct >= tp_pct
            hit_sl = pnl_pct <= -sl_pct
            hit_time = bars_held >= max_hold
            flip = (sig == 1 and position == -1) or (sig == -1 and position == 1)

            if hit_tp or hit_sl or hit_time or flip:
                net_pnl = pnl_pct - commission_pct * 2
                trades.append({
                    "entry_bar": entry_bar,
                    "exit_bar": i,
                    "direction": "LONG" if position == 1 else "SHORT",
                    "pnl_pct": net_pnl,
                    "bars_held": bars_held,
                    "exit_reason": "TP" if hit_tp else "SL" if hit_sl else "TIME" if hit_time else "FLIP",
                })
                position = 0

        if position == 0 and sig != 0:
            position = int(sig)
            entry_price = close_price
            entry_bar = i

    if not trades:
        return {
            "num_trades": 0, "win_rate": 0.0, "profit_factor": 0.0,
            "sharpe_ratio": 0.0, "avg_pnl": 0.0, "total_return": 0.0,
            "max_drawdown": 0.0, "avg_bars_held": 0.0,
        }

    pnls = [t["pnl_pct"] for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    gross_profit = sum(wins) if wins else 0.0
    gross_loss = abs(sum(losses)) if losses else 0.001

    equity = np.cumsum(pnls)
    peak = np.maximum.accumulate(equity)
    dd = equity - peak
    max_dd = abs(dd.min()) if len(dd) > 0 else 0.0

    pnl_arr = np.array(pnls)
    sharpe = (pnl_arr.mean() / pnl_arr.std() * np.sqrt(252)) if pnl_arr.std() > 0 else 0.0

    return {
        "num_trades": len(trades),
        "win_rate": len(wins) / len(trades) * 100 if trades else 0.0,
        "profit_factor": gross_profit / gross_loss if gross_loss > 0 else 0.0,
        "sharpe_ratio": round(float(sharpe), 3),
        "avg_pnl": round(float(np.mean(pnls)), 3),
        "total_return": round(float(sum(pnls)), 3),
        "max_drawdown": round(float(max_dd), 3),
        "avg_bars_held": round(float(np.mean([t["bars_held"] for t in trades])), 1),
    }


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------

def run_single(symbol: str, tf: str, strat_name: str, strat_fn, params: dict,
               do_fetch: bool = False, verbose: bool = False) -> Optional[Dict]:
    df = load_data(symbol, tf)
    if df is None and do_fetch:
        df = fetch_data(symbol, tf)
    if df is None:
        return None
    if len(df) < 200:
        return None

    try:
        signals = strat_fn(df, params)
    except Exception as e:
        if verbose:
            print(f"  [!] {strat_name} error on {symbol}/{tf}: {e}")
        return None

    metrics = backtest(df, signals)
    if metrics["num_trades"] == 0:
        return None

    return {
        "symbol": symbol,
        "timeframe": tf,
        "strategy": strat_name,
        **metrics,
    }


def composite_score(r: Dict, min_trades: int = 20) -> float:
    if r["num_trades"] < min_trades:
        return -1.0
    wr_norm = r["win_rate"] / 100.0
    pf_norm = min(r["profit_factor"] / 5.0, 1.0)
    sh_norm = min(max(r["sharpe_ratio"], 0) / 3.0, 1.0)
    tr_norm = min(r["num_trades"] / 200.0, 1.0)
    return 0.4 * wr_norm + 0.3 * pf_norm + 0.2 * sh_norm + 0.1 * tr_norm


def main():
    parser = argparse.ArgumentParser(description="Simpleton CURSOR Backtesting Tool -- test 12 strategies on crypto pairs.")
    parser.add_argument("--symbol", type=str, help="Single symbol (e.g. BTCUSDT)")
    parser.add_argument("--strategy", type=str, help="Single strategy (e.g. rsi2, macd_rsi, zscore)")
    parser.add_argument("--timeframe", type=str, help="Single timeframe (e.g. 4h)")
    parser.add_argument("--save-best", action="store_true", help="Save best strategy per symbol")
    parser.add_argument("--fetch", action="store_true", help="Download data via ccxt if not cached")
    parser.add_argument("--min-trades", type=int, default=20, help="Min trades for valid result")
    parser.add_argument("--verbose", action="store_true", help="Show detailed trade log")
    args = parser.parse_args()

    symbols = [args.symbol] if args.symbol else SYMBOLS
    timeframes = [args.timeframe] if args.timeframe else TIMEFRAMES

    strat_filter = None
    if args.strategy:
        key = args.strategy.lower()
        strat_filter = STRATEGY_ALIASES.get(key, args.strategy)

    strategies_to_run = {}
    for name, (fn, params) in STRATEGIES.items():
        if strat_filter and name != strat_filter:
            continue
        strategies_to_run[name] = (fn, params)

    if not strategies_to_run:
        print(f"[!] Unknown strategy: {args.strategy}")
        print(f"    Available: {', '.join(STRATEGY_ALIASES.keys())}")
        sys.exit(1)

    print("=" * 80)
    print("SIMPLETON CURSOR BACKTESTING TOOL")
    print(f"Symbols: {len(symbols)} | Timeframes: {len(timeframes)} | Strategies: {len(strategies_to_run)}")
    print("=" * 80)

    results = []
    total = len(symbols) * len(timeframes) * len(strategies_to_run)
    done = 0

    for symbol in symbols:
        for tf in timeframes:
            for strat_name, (fn, params) in strategies_to_run.items():
                done += 1
                r = run_single(symbol, tf, strat_name, fn, params, args.fetch, args.verbose)
                if r:
                    results.append(r)
                    if args.verbose:
                        print(f"  [{done}/{total}] {symbol} {tf} {strat_name}: {r['num_trades']} trades, {r['win_rate']:.1f}% WR, PF {r['profit_factor']:.2f}")
                else:
                    if args.verbose:
                        print(f"  [{done}/{total}] {symbol} {tf} {strat_name}: no data or no trades")

    if not results:
        print("\n[!] No results. Check that data files exist in tmp/ or data/crypto/.")
        print("    Run with --fetch to download via ccxt, or place CSV files manually.")
        sys.exit(0)

    # Sort by composite score
    for r in results:
        r["score"] = round(composite_score(r, args.min_trades) * 100, 1)
    results.sort(key=lambda x: x["score"], reverse=True)

    # Print table
    print(f"\n{'Symbol':<10} {'TF':<5} {'Strategy':<20} {'Trades':>7} {'WR%':>7} {'PF':>7} {'Sharpe':>8} {'Score':>7}")
    print("-" * 80)
    for r in results:
        if r["score"] < 0:
            continue
        print(f"{r['symbol']:<10} {r['timeframe']:<5} {r['strategy']:<20} {r['num_trades']:>7} {r['win_rate']:>6.1f}% {r['profit_factor']:>7.2f} {r['sharpe_ratio']:>8.3f} {r['score']:>6.1f}")

    # Find best per symbol
    best = {}
    for r in results:
        sym = r["symbol"]
        if r["score"] <= 0:
            continue
        if sym not in best or r["score"] > best[sym]["score"]:
            best[sym] = r

    if best:
        print(f"\n{'=' * 80}")
        print("OPTIMAL STRATEGIES PER SYMBOL:")
        print(f"{'=' * 80}")
        for sym, r in sorted(best.items()):
            print(f"  {sym}: {r['strategy']} @ {r['timeframe']} ({r['win_rate']:.1f}% WR, PF {r['profit_factor']:.2f}, Sharpe {r['sharpe_ratio']:.3f})")

    # Save results
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    def sanitize(obj):
        if isinstance(obj, float) and (np.isnan(obj) or np.isinf(obj)):
            return None
        return obj

    clean_results = [{k: sanitize(v) for k, v in r.items()} for r in results]

    results_path = RESULTS_DIR / "cursor_results.json"
    with open(results_path, "w") as f:
        json.dump({
            "generated": datetime.utcnow().isoformat() + "Z",
            "tool": "backtest_cursor.py",
            "results": clean_results,
        }, f, indent=2, default=str)
    print(f"\nResults saved to {results_path}")

    if args.save_best and best:
        best_path = RESULTS_DIR / "cursor_best.json"
        clean_best = {k: {kk: sanitize(vv) for kk, vv in v.items()} for k, v in best.items()}
        with open(best_path, "w") as f:
            json.dump({
                "generated": datetime.utcnow().isoformat() + "Z",
                "tool": "backtest_cursor.py",
                "best_per_symbol": clean_best,
            }, f, indent=2, default=str)
        print(f"Best strategies saved to {best_path}")


if __name__ == "__main__":
    main()
