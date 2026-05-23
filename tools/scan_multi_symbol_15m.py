#!/usr/bin/env python3
"""
Multi-symbol 15m technical scan: TA-Lib patterns, EMA stack, pivot S/R.
Uses one ccxt exchange instance; TA-Lib returns ndarrays (use [-1], not .iloc[-1]).

EMA crossovers compare the last *closed* bar to the prior closed bar ([-2] vs [-3]);
the final OHLCV row is often the still-forming candle, so we do not use [-1] for crosses.

  python tools/scan_multi_symbol_15m.py
  set SCAN_MARKET_TYPE=swap     # Bybit linear perps; symbols auto-get :USDT
  set SCAN_SLEEP=0.5            # seconds between symbols (default 0.5)

Requires: pip install ccxt pandas numpy TA-Lib
"""

from __future__ import annotations

import os
import time

import ccxt
import numpy as np
import pandas as pd
import talib

# --- Configuration ---
# Compact default list (original scanner set).
SYMBOLS_COMPACT = [
    "XRP/USDT",
    "ALGO/USDT",
    "HBAR/USDT",
    "INJ/USDT",
    "FET/USDT",
    "SOL/USDT",
    "BNB/USDT",
    "ETH/USDT",
]

# Union of symbols visible on Active Picks / multi-scanner screenshots (deduped).
SYMBOLS_DASHBOARD = [
    "APT/USDT",
    "ATOM/USDT",
    "ALGO/USDT",
    "BNB/USDT",
    "BTC/USDT",
    "DOGE/USDT",
    "DOT/USDT",
    "ETC/USDT",
    "ETH/USDT",
    "FET/USDT",
    "HBAR/USDT",
    "INJ/USDT",
    "NEAR/USDT",
    "RENDER/USDT",  # dashboard used RNDRUSDT; Bybit spot uses RENDER
    "SHIB/USDT",
    "SOL/USDT",
    "SUI/USDT",
    "TIA/USDT",
    "WLD/USDT",
    "XRP/USDT",
    "ZEC/USDT",
    "ZIL/USDT",
]

_scan_universe = os.environ.get("SCAN_UNIVERSE", "compact").strip().lower()
SYMBOLS = SYMBOLS_DASHBOARD if _scan_universe in ("dashboard", "dash", "all") else SYMBOLS_COMPACT

TIMEFRAME = "15m"
LOOKBACK = 500

# Bybit: "spot" or "swap" (linear perps). Symbols for swap often need :USDT suffix.
EXCHANGE_ID = os.environ.get("SCAN_EXCHANGE", "bybit").lower()
MARKET_TYPE = os.environ.get("SCAN_MARKET_TYPE", "spot").lower()  # or "swap"

SCAN_SLEEP_SEC = float(os.environ.get("SCAN_SLEEP", "0.5"))

# --- Candlestick Patterns ---
PATTERNS = {
    "Hammer": "CDLHAMMER",
    "Inverted Hammer": "CDLINVERTEDHAMMER",
    "Engulfing (Bullish)": "CDLENGULFING",
    "Doji": "CDLDOJI",
    "Morning Star": "CDLMORNINGSTAR",
    "Evening Star": "CDLEVENINGSTAR",
    "Three White Soldiers": "CDL3WHITESOLDIERS",
    "Three Black Crows": "CDL3BLACKCROWS",
    "Hanging Man": "CDLHANGINGMAN",
    "Shooting Star": "CDLSHOOTINGSTAR",
    "Piercing Line": "CDLPIERCING",
    "Dark Cloud Cover": "CDLDARKCLOUDCOVER",
    "Harami (Bullish)": "CDLHARAMI",
    "Harami Cross": "CDLHARAMICROSS",
    "Abandoned Baby": "CDLABANDONEDBABY",
    "Three Inside Up": "CDL3INSIDE",
    "Three Outside Up": "CDL3OUTSIDE",
    "Marubozu": "CDLMARUBOZU",
}

MA_FAST = 9
MA_MID = 21
MA_SLOW = 50
MA_TREND = 200

SR_WINDOW = 20
SR_CLUSTER_TOLERANCE = 0.005
SR_LOOKBACK = 200

_EXCHANGE: ccxt.Exchange | None = None


def get_exchange() -> ccxt.Exchange:
    global _EXCHANGE
    if _EXCHANGE is not None:
        return _EXCHANGE
    opts: dict = {"enableRateLimit": True}
    if EXCHANGE_ID == "bybit":
        opts["options"] = {"defaultType": MARKET_TYPE}
        _EXCHANGE = ccxt.bybit(opts)
    elif EXCHANGE_ID == "binance":
        opts["options"] = {"defaultType": "spot"}
        _EXCHANGE = ccxt.binance(opts)
    else:
        _EXCHANGE = getattr(ccxt, EXCHANGE_ID)(opts)
    _EXCHANGE.load_markets()
    return _EXCHANGE


def normalize_symbol(symbol: str) -> str:
    """Map spot symbols to linear swap form when using Bybit swap."""
    if EXCHANGE_ID == "bybit" and MARKET_TYPE == "swap":
        if ":" not in symbol and symbol.endswith("/USDT"):
            return f"{symbol}:USDT"
    return symbol


def fetch_data(symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
    ex = get_exchange()
    sym = normalize_symbol(symbol)
    ohlcv = ex.fetch_ohlcv(sym, timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    return df


def scan_patterns(df: pd.DataFrame) -> list[str]:
    results: list[str] = []
    o = df["open"].astype(float).values
    h = df["high"].astype(float).values
    low = df["low"].astype(float).values
    c = df["close"].astype(float).values
    for name, func_name in PATTERNS.items():
        func = getattr(talib, func_name)
        signal = func(o, h, low, c)
        last = int(np.asarray(signal).flat[-1])
        if last != 0:
            direction = "BULLISH" if last > 0 else "BEARISH"
            results.append(f"  [{direction}] {name} (signal: {last})")
    return results


def _append_last_closed_crossover(
    results: list[str],
    label_a: str,
    label_b: str,
    arr_a: np.ndarray,
    arr_b: np.ndarray,
) -> None:
    """Detect EMA cross on the last *closed* bar: compare [-3] vs [-2] (not [-1], forming)."""
    if len(arr_a) < 4 or len(arr_b) < 4:
        return
    pa, pb = arr_a[-3], arr_b[-3]
    ca, cb = arr_a[-2], arr_b[-2]
    if np.isnan(pa) or np.isnan(pb) or np.isnan(ca) or np.isnan(cb):
        return
    if pa <= pb and ca > cb:
        results.append(f"  [BULLISH] {label_a} crossed ABOVE {label_b} (last closed bar)")
    elif pa >= pb and ca < cb:
        results.append(f"  [BEARISH] {label_a} crossed BELOW {label_b} (last closed bar)")


def analyze_moving_averages(df: pd.DataFrame) -> list[str]:
    results: list[str] = []
    close = df["close"].astype(float).values
    if len(close) < MA_TREND + 5:
        results.append("  [TREND] Insufficient history for full MA analysis")
        return results

    ema_fast_s = talib.EMA(close, timeperiod=MA_FAST)
    ema_mid_s = talib.EMA(close, timeperiod=MA_MID)
    ema_slow_s = talib.EMA(close, timeperiod=MA_SLOW)
    sma_trend_s = talib.SMA(close, timeperiod=MA_TREND)

    price = float(close[-1])
    ema_fast = float(ema_fast_s[-1])
    ema_mid = float(ema_mid_s[-1])
    ema_slow = float(ema_slow_s[-1])
    sma_trend = float(sma_trend_s[-1])

    _append_last_closed_crossover(results, f"EMA{MA_FAST}", f"EMA{MA_MID}", ema_fast_s, ema_mid_s)
    _append_last_closed_crossover(results, f"EMA{MA_FAST}", f"EMA{MA_SLOW}", ema_fast_s, ema_slow_s)
    _append_last_closed_crossover(results, f"EMA{MA_MID}", f"EMA{MA_SLOW}", ema_mid_s, ema_slow_s)

    if ema_fast > ema_mid > ema_slow:
        results.append(f"  [TREND] Bullish stack: EMA{MA_FAST} > EMA{MA_MID} > EMA{MA_SLOW}")
    elif ema_fast < ema_mid < ema_slow:
        results.append(f"  [TREND] Bearish stack: EMA{MA_FAST} < EMA{MA_MID} < EMA{MA_SLOW}")
    else:
        results.append("  [TREND] Mixed/Choppy MA alignment")

    if price > sma_trend:
        results.append(f"  [TREND] Price ABOVE SMA{MA_TREND} ({sma_trend:.6f}) - macro bullish")
    else:
        results.append(f"  [TREND] Price BELOW SMA{MA_TREND} ({sma_trend:.6f}) - macro bearish")

    for label, val in [
        ("EMA" + str(MA_FAST), ema_fast),
        ("EMA" + str(MA_MID), ema_mid),
        ("EMA" + str(MA_SLOW), ema_slow),
        ("SMA" + str(MA_TREND), sma_trend),
    ]:
        dist_pct = ((price - val) / val) * 100
        results.append(f"  [DIST] Price is {dist_pct:+.2f}% from {label} ({val:.6f})")

    return results


def cluster_levels(levels: list[float], tolerance: float) -> list[tuple[float, int]]:
    if not levels:
        return []
    levels = sorted(levels)
    clusters: list[list[float]] = [[levels[0]]]
    for lvl in levels[1:]:
        if (lvl - clusters[-1][-1]) / clusters[-1][-1] < tolerance:
            clusters[-1].append(lvl)
        else:
            clusters.append([lvl])
    return [(float(np.mean(c)), len(c)) for c in clusters]


def find_support_resistance(df: pd.DataFrame) -> list[str]:
    results: list[str] = []

    highs = df["high"].values[-SR_LOOKBACK:]
    lows = df["low"].values[-SR_LOOKBACK:]
    price = float(df["close"].iloc[-1])

    resistances: list[float] = []
    supports: list[float] = []

    for i in range(SR_WINDOW, len(highs) - SR_WINDOW):
        if highs[i] == max(highs[i - SR_WINDOW : i + SR_WINDOW + 1]):
            resistances.append(float(highs[i]))
        if lows[i] == min(lows[i - SR_WINDOW : i + SR_WINDOW + 1]):
            supports.append(float(lows[i]))

    res_clusters = cluster_levels(resistances, SR_CLUSTER_TOLERANCE)
    sup_clusters = cluster_levels(supports, SR_CLUSTER_TOLERANCE)

    res_clusters.sort(key=lambda x: abs(x[0] - price))
    sup_clusters.sort(key=lambda x: abs(x[0] - price))

    nearby_res = [(lvl, touches) for lvl, touches in res_clusters if lvl > price][:5]
    nearby_sup = [(lvl, touches) for lvl, touches in sup_clusters if lvl < price][:5]

    strong_res = sorted(res_clusters, key=lambda x: x[1], reverse=True)[:3]
    strong_sup = sorted(sup_clusters, key=lambda x: x[1], reverse=True)[:3]

    results.append(f"  Current price: {price:.6f}")

    if nearby_res:
        results.append("  RESISTANCE levels above price:")
        for lvl, touches in nearby_res:
            dist_pct = ((lvl - price) / price) * 100
            results.append(f"    -> {lvl:.6f} ({dist_pct:+.2f}%) - {touches} touches")
    else:
        results.append("  No significant resistance levels detected above price.")

    if nearby_sup:
        results.append("  SUPPORT levels below price:")
        for lvl, touches in nearby_sup:
            dist_pct = ((lvl - price) / price) * 100
            results.append(f"    -> {lvl:.6f} ({dist_pct:+.2f}%) - {touches} touches")
    else:
        results.append("  No significant support levels detected below price.")

    results.append("  STRONGEST levels (most touches):")
    if strong_res:
        best_res = strong_res[0]
        results.append(f"    Resistance: {best_res[0]:.6f} - {best_res[1]} touches")
    if strong_sup:
        best_sup = strong_sup[0]
        results.append(f"    Support:    {best_sup[0]:.6f} - {best_sup[1]} touches")

    return results


def scan_symbol(symbol: str) -> dict:
    try:
        df = fetch_data(symbol, TIMEFRAME, LOOKBACK)
        output: dict = {}

        pattern_hits = scan_patterns(df)
        output["patterns"] = pattern_hits if pattern_hits else ["  No patterns detected on latest candle."]

        output["moving_averages"] = analyze_moving_averages(df)
        output["support_resistance"] = find_support_resistance(df)

        return output
    except Exception as e:
        return {"error": [f"  Error: {e}"]}


def main() -> int:
    print("=" * 60)
    print(f"Full Technical Scan - {TIMEFRAME} - {EXCHANGE_ID} ({MARKET_TYPE})")
    print(time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()))
    print(f"Scanning: {', '.join(SYMBOLS)}")
    print("=" * 60)

    for sym in SYMBOLS:
        print(f"\n{'-' * 60}")
        print(f" {sym}")
        print(f"{'-' * 60}")

        result = scan_symbol(sym)

        if "error" in result:
            print("\n".join(result["error"]))
            continue

        print("\n CANDLESTICK PATTERNS:")
        print("\n".join(result["patterns"]))

        print("\n MOVING AVERAGES:")
        print("\n".join(result["moving_averages"]))

        print("\n SUPPORT & RESISTANCE:")
        print("\n".join(result["support_resistance"]))

        if SCAN_SLEEP_SEC > 0:
            time.sleep(SCAN_SLEEP_SEC)

    print(f"\n{'=' * 60}")
    print("Scan complete.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
