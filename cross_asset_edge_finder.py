#!/usr/bin/env python3
"""
CROSS-ASSET EDGE FINDER
=======================
Reuses the 6 combination strategies from backtest_edge_finder.py but scans
them across EQUITY / FOREX / COMMODITY / ETF universes via yfinance public API.

Strategies:
  A: SuperTrend + VWMA Confluence (dual confirmation)
  B: Keltner Squeeze + RSI2 Oversold (squeeze breakout)
  C: Triple Confirmation (SuperTrend + ADX + Volume)
  D: Mean Reversion with Trend Guard (double oversold + trend)
  E: Momentum Persistence (breakout continuation)
  F: SHORT-Only Fear/Greed Contrarian

Data source: Yahoo Finance v8 chart API (no key, no install).
Output: cross_asset_edge_finder_results.json

Usage: python cross_asset_edge_finder.py
"""
import json
import time
import os
import sys
import statistics
from datetime import datetime, timezone
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

# Reuse strategies + helpers from backtest_edge_finder
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from backtest_edge_finder import (
    STRATEGIES, calc_stats,
)

# ─── Asset-Class Universes ──────────────────────────────────────────
UNIVERSES = {
    "EQUITY": [
        # Mega caps + sector ETFs
        "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA",
        "JPM", "V", "WMT", "XOM", "JNJ", "PG", "HD",
        "SPY", "QQQ", "IWM",  # Index ETFs
    ],
    "FOREX": [
        # Majors (Yahoo format with =X)
        "EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X",
        "USDCHF=X", "NZDUSD=X", "USDCAD=X", "EURJPY=X",
    ],
    "COMMODITY": [
        # Gold, silver, oil, copper, nat gas (futures continuous contracts)
        "GC=F", "SI=F", "CL=F", "HG=F", "NG=F", "ZC=F", "ZW=F",
    ],
    "ETF_LEVERAGED": [
        # Sector ETFs (non-leveraged for signal testing)
        "XLE", "XLF", "XLK", "XLV", "XLP", "XLY", "XLI", "XLU",
    ],
    "INDEX": [
        # Broad index futures
        "ES=F", "NQ=F", "YM=F", "RTY=F",
    ],
}

TIMEFRAMES_MAP = {
    "1h": "60m",
    "4h": None,  # yfinance doesn't have native 4h — skip
    "1d": "1d",
}

BARS = 400  # yfinance returns less history at hourly
RESULTS_PATH = "cross_asset_edge_finder_results.json"


def fetch_yahoo_klines(symbol, interval, limit=BARS):
    """Fetch OHLCV from Yahoo Finance v8 chart API."""
    yf_int = TIMEFRAMES_MAP.get(interval)
    if yf_int is None:
        return None
    # Date range — use "range" param for simplicity
    if yf_int == "60m":
        rng = "730d"  # 2y max for 1h
    else:
        rng = "5y"  # 5y for 1d
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
           f"?interval={yf_int}&range={rng}")
    try:
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=20) as resp:
            raw = json.loads(resp.read().decode())
        chart = raw.get("chart", {}).get("result")
        if not chart:
            return None
        data = chart[0]
        ts = data.get("timestamp", [])
        q = data.get("indicators", {}).get("quote", [{}])[0]
        o_arr = q.get("open", [])
        h_arr = q.get("high", [])
        l_arr = q.get("low", [])
        c_arr = q.get("close", [])
        v_arr = q.get("volume", [])
        candles = []
        for i in range(len(ts)):
            # Skip bars with None OHLC (market closed gaps)
            if (i >= len(o_arr) or i >= len(h_arr) or i >= len(l_arr)
                    or i >= len(c_arr) or i >= len(v_arr)):
                continue
            o, h, l, c, v = o_arr[i], h_arr[i], l_arr[i], c_arr[i], v_arr[i]
            if o is None or h is None or l is None or c is None:
                continue
            candles.append({
                "open": float(o),
                "high": float(h),
                "low": float(l),
                "close": float(c),
                "volume": float(v) if v is not None else 0.0,
            })
        # Take last `limit` candles
        return candles[-limit:] if len(candles) > limit else candles
    except Exception as e:
        print(f"    fetch failed for {symbol}/{interval}: {e}", file=sys.stderr)
        return None


def main():
    print("=" * 80)
    print("  CROSS-ASSET EDGE FINDER")
    print(f"  {sum(len(v) for v in UNIVERSES.values())} symbols x 2 timeframes x {len(STRATEGIES)} strategies")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 80)

    all_results = {}
    timeframes = ["1h", "1d"]
    total_combos = sum(len(syms) * len(timeframes) * len(STRATEGIES)
                       for syms in UNIVERSES.values())
    done = 0
    fetch_failures = 0

    for asset_class, symbols in UNIVERSES.items():
        print(f"\n--- {asset_class} ({len(symbols)} symbols) ---")
        for sym in symbols:
            for tf in timeframes:
                candles = fetch_yahoo_klines(sym, tf, BARS)
                if candles is None or len(candles) < 100:
                    done += len(STRATEGIES)
                    fetch_failures += 1
                    print(f"  [{done}/{total_combos}] {sym}/{tf}: insufficient data "
                          f"({0 if not candles else len(candles)} bars)")
                    continue

                for strat_name, strat_fn in STRATEGIES.items():
                    done += 1
                    combo_key = f"{asset_class}|{strat_name}|{sym}|{tf}"
                    try:
                        trades = strat_fn(candles)
                        stats = calc_stats(trades)
                        all_results[combo_key] = stats
                        marker = ""
                        if stats["trades"] >= 10 and stats["win_rate"] > 55 and stats["pf"] > 1.5:
                            marker = " <<<RECOMMENDED>>>"
                        elif stats["sharpe"] > 1.5 and stats["trades"] >= 8:
                            marker = " <<<EDGE>>>"
                        elif stats["trades"] >= 8 and stats["pf"] > 1.2:
                            marker = " *"
                        if marker:
                            print(f"  [{done}/{total_combos}] {strat_name} | {sym}/{tf}: "
                                  f"{stats['trades']}t WR={stats['win_rate']}% PF={stats['pf']} "
                                  f"Sharpe={stats['sharpe']}{marker}")
                    except Exception as e:
                        all_results[combo_key] = {"trades": 0, "error": str(e)}

                time.sleep(0.1)  # rate-limit yfinance

    # ─── Analysis ─────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("  CROSS-ASSET ANALYSIS")
    print("=" * 80)
    print(f"Total combos tested: {done}")
    print(f"Fetch failures: {fetch_failures * len(STRATEGIES)}")

    # Recommended: WR>55% AND PF>1.5 AND trades>=10
    recommended = {k: v for k, v in all_results.items()
                   if v.get("trades", 0) >= 10
                   and v.get("win_rate", 0) > 55
                   and v.get("pf", 0) > 1.5}
    rec_sorted = sorted(recommended.items(), key=lambda x: x[1].get("sharpe", 0), reverse=True)
    print(f"\n=== RECOMMENDED COMBOS (WR>55%, PF>1.5, trades>=10): {len(rec_sorted)} ===")
    for k, v in rec_sorted[:30]:
        parts = k.split("|")
        print(f"  [{parts[0]:10s}] {parts[1]:25s} {parts[2]:10s} {parts[3]:3s} | "
              f"n={v['trades']:3d} WR={v['win_rate']:5.1f}% PF={v['pf']:5.2f} "
              f"PnL={v['total_pnl']:+7.2f}% Sharpe={v['sharpe']:+5.2f}")

    # Group by asset class and strategy
    by_class_strat = {}
    for k, v in all_results.items():
        if v.get("trades", 0) < 8 or v.get("pf", 0) <= 1.0:
            continue
        parts = k.split("|")
        asset_class, strat_name = parts[0], parts[1]
        key = f"{asset_class}|{strat_name}"
        by_class_strat.setdefault(key, []).append((parts[2], parts[3], v))

    print(f"\n=== WINNING STRATEGIES BY ASSET CLASS ===")
    for key, combos in sorted(by_class_strat.items()):
        if len(combos) < 2:
            continue
        asset_class, strat_name = key.split("|")
        total_pnl = sum(c[2]["total_pnl"] for c in combos)
        avg_pf = sum(c[2]["pf"] for c in combos) / len(combos)
        avg_wr = sum(c[2]["win_rate"] for c in combos) / len(combos)
        print(f"  [{asset_class:10s}] {strat_name:25s}: {len(combos)} profitable combos | "
              f"avg WR={avg_wr:5.1f}% avg PF={avg_pf:.2f} total PnL={total_pnl:+.1f}%")

    # Save results
    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "strategies": list(STRATEGIES.keys()),
        "universes": UNIVERSES,
        "timeframes": timeframes,
        "bars": BARS,
        "total_combos_tested": done,
        "fetch_failures": fetch_failures,
        "recommended_count": len(rec_sorted),
        "recommended": dict(rec_sorted[:50]),
        "all_results": all_results,
    }
    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
    print(f"\n=> Results saved to {RESULTS_PATH}")


if __name__ == "__main__":
    main()
