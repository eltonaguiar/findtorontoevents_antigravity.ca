"""
ALPHA_ENGINE -- Market Microstructure Backtester (Wave 16)
===========================================================
Hybrid backtester for the 4 Wave 16 Market Microstructure strategies.
Part 1: Live Signal Validation  -- calls real APIs right now
Part 2: Historical Proxy Backtests -- uses yfinance + Binance funding history

Run from alpha_engine/:
    py backtest_microstructure.py

Output saved to: alpha_engine/data/backtest_microstructure.json
"""

import os
import sys

os.environ["PYTHONIOENCODING"] = "utf-8"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import json
import math
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

# -- yfinance import ---------------------------------------------------
try:
    import yfinance as yf
    HAS_YF = True
except ImportError:
    HAS_YF = False
    print("[WARN] yfinance not installed -- Part 2 proxy backtests will be skipped")

# -- scipy for p-value -------------------------------------------------
try:
    from scipy.stats import binomtest
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

# -- Alpha Engine path setup -------------------------------------------
ALPHA_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ALPHA_DIR))

from market_microstructure_strategies import (
    options_25delta_skew,
    coinbase_premium_index,
    order_book_imbalance,
    perpetual_basis_strategy,
    MICROSTRUCTURE_STRATEGIES,
)

# -- Output paths ------------------------------------------------------
DATA_DIR = ALPHA_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
OUTPUT_FILE = DATA_DIR / "backtest_microstructure.json"

REQUIRED_SIGNAL_KEYS = {
    "strategy", "symbol", "signal_type", "direction",
    "entry_price", "take_profit", "stop_loss",
    "confidence", "risk_reward", "reason", "timestamp",
}

# ══════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════

def _fetch_json(url: str, timeout: int = 10) -> Optional[dict | list]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ALPHA_BACKTEST/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return None


def _binomial_pvalue(wins: int, total: int, null_prob: float = 0.5) -> float:
    """Two-sided binomial p-value.  Falls back to manual calculation."""
    if total == 0:
        return 1.0
    if HAS_SCIPY:
        try:
            result = binomtest(wins, total, null_prob, alternative="greater")
            return float(result.pvalue)
        except Exception:
            pass
    # Manual CDF: P(X >= wins) under Binomial(total, null_prob)
    # Using normal approximation for speed
    p = null_prob
    mu = total * p
    sigma = math.sqrt(total * p * (1 - p))
    if sigma == 0:
        return 1.0
    z = (wins - mu - 0.5) / sigma  # continuity correction
    # Approx 1-sided CDF via error function
    from math import erfc
    pval = 0.5 * erfc(z / math.sqrt(2))
    return float(pval)


def _sharpe(returns: list[float], periods_per_year: int = 252) -> float:
    if len(returns) < 2:
        return 0.0
    arr = np.array(returns, dtype=float)
    mu = np.mean(arr)
    sd = np.std(arr, ddof=1)
    if sd == 0:
        return 0.0
    return float(mu / sd * math.sqrt(periods_per_year))


def _trade_stats(pnl_pcts: list[float]) -> dict:
    """Return win_rate, avg_pnl, sharpe, p_value, best, worst."""
    if not pnl_pcts:
        return {
            "total_trades": 0, "win_rate": 0.0, "avg_pnl_pct": 0.0,
            "sharpe": 0.0, "p_value": 1.0, "best_trade": 0.0, "worst_trade": 0.0,
        }
    wins = sum(1 for x in pnl_pcts if x > 0)
    total = len(pnl_pcts)
    wr = wins / total
    avg = float(np.mean(pnl_pcts))
    sh = _sharpe(pnl_pcts)
    pval = _binomial_pvalue(wins, total)
    return {
        "total_trades": total,
        "win_rate": round(wr, 4),
        "avg_pnl_pct": round(avg, 4),
        "sharpe": round(sh, 3),
        "p_value": round(pval, 6),
        "best_trade": round(max(pnl_pcts), 4),
        "worst_trade": round(min(pnl_pcts), 4),
    }


def _print_header(title: str):
    w = 72
    print()
    print("=" * w)
    print(f"  {title}")
    print("=" * w)


def _print_section(title: str):
    print()
    print(f"--- {title} " + "-" * max(0, 68 - len(title)))


# ══════════════════════════════════════════════════════════════════════
# PART 1: LIVE SIGNAL VALIDATION
# ══════════════════════════════════════════════════════════════════════

def run_live_validation() -> dict[str, int]:
    """
    Fetch recent OHLCV from yfinance, call each strategy, validate format.
    Returns dict: strategy_name -> signal count.
    """
    _print_header("PART 1: LIVE SIGNAL VALIDATION (Real API calls)")
    live_counts: dict[str, int] = {}

    if not HAS_YF:
        print("[SKIP] yfinance not available -- skipping live validation")
        for name in MICROSTRUCTURE_STRATEGIES:
            live_counts[name] = 0
        return live_counts

    # Fetch OHLCV
    symbols = ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD",
               "ADA-USD", "DOGE-USD", "XRP-USD", "AVAX-USD",
               "LINK-USD", "DOT-USD"]
    print(f"\nFetching OHLCV from yfinance for {len(symbols)} symbols...")
    data: dict[str, pd.DataFrame] = {}
    for sym in symbols:
        try:
            df = yf.download(sym, period="60d", interval="1d", progress=False, auto_adjust=True)
            if df is not None and len(df) >= 20:
                df.columns = [c if isinstance(c, str) else c[0] for c in df.columns]
                data[sym] = df
                print(f"  [OK] {sym}: {len(df)} bars")
            else:
                print(f"  [WARN] {sym}: insufficient data")
        except Exception as e:
            print(f"  [ERR] {sym}: {e}")

    if not data:
        print("[ERR] No OHLCV data fetched -- aborting live validation")
        for name in MICROSTRUCTURE_STRATEGIES:
            live_counts[name] = 0
        return live_counts

    # Run each strategy
    _print_section("Running strategies against live APIs")
    strategy_functions = {
        "options_25delta_skew": options_25delta_skew,
        "coinbase_premium_index": coinbase_premium_index,
        "order_book_imbalance": order_book_imbalance,
        "perpetual_basis": perpetual_basis_strategy,
    }

    for name, func in strategy_functions.items():
        print(f"\n[{name}]")
        try:
            signals = func(data)
            count = len(signals)
            live_counts[name] = count
            print(f"  Signals generated: {count}")

            if count == 0:
                print("  (No signal at current market conditions -- normal)")
            else:
                for sig in signals[:3]:  # Show first 3
                    missing = REQUIRED_SIGNAL_KEYS - set(sig.keys())
                    valid = "VALID" if not missing else f"MISSING: {missing}"
                    print(f"  Signal: {sig.get('symbol')} {sig.get('direction')} "
                          f"@ {sig.get('entry_price')} | {valid}")
                    print(f"    Reason: {sig.get('reason', '')[:80]}")
        except Exception as e:
            print(f"  [ERR] Strategy raised exception: {e}")
            live_counts[name] = 0

    return live_counts


# ══════════════════════════════════════════════════════════════════════
# PART 2a: COINBASE PREMIUM PROXY BACKTEST
# ══════════════════════════════════════════════════════════════════════

def backtest_coinbase_premium() -> dict:
    """
    Proxy: BTC-USD close-to-close momentum as premium proxy.
    When 1-day return exceeds +0.5% threshold, simulate premium > 0.5% -> BUY.
    When 1-day return is below -0.3%, simulate premium < -0.3% -> SELL.
    Exit: 2% TP / 1.5% SL over next N bars.
    """
    _print_section("2a. Coinbase Premium Proxy Backtest")
    if not HAS_YF:
        print("  [SKIP] yfinance not available")
        return {"error": "yfinance not available"}

    try:
        df = yf.download("BTC-USD", period="2y", interval="1d", progress=False, auto_adjust=True)
        df.columns = [c if isinstance(c, str) else c[0] for c in df.columns]
        if len(df) < 50:
            return {"error": "Insufficient historical data"}

        close = df["Close"].astype(float)
        # Daily return as proxy for Coinbase premium
        daily_ret = close.pct_change()

        pnl_list = []
        hold_bars = 3  # hold up to 3 days

        for i in range(1, len(close) - hold_bars):
            ret = float(daily_ret.iloc[i])
            entry = float(close.iloc[i])

            direction = None
            if ret > 0.005:       # > +0.5% -> simulate premium -> BUY
                direction = "LONG"
                tp = entry * 1.02
                sl = entry * 0.985
            elif ret < -0.003:    # < -0.3% -> simulate negative premium -> SELL
                direction = "SHORT"
                tp = entry * 0.98
                sl = entry * 1.015

            if direction is None:
                continue

            # Simulate exit over next hold_bars days
            trade_pnl = None
            for j in range(i + 1, min(i + hold_bars + 1, len(close))):
                hi = float(df["High"].iloc[j])
                lo = float(df["Low"].iloc[j])

                if direction == "LONG":
                    if hi >= tp:
                        trade_pnl = (tp - entry) / entry
                        break
                    elif lo <= sl:
                        trade_pnl = (sl - entry) / entry
                        break
                else:  # SHORT
                    if lo <= tp:
                        trade_pnl = (entry - tp) / entry
                        break
                    elif hi >= sl:
                        trade_pnl = (entry - sl) / entry
                        break

            if trade_pnl is None:
                # Close at last bar
                exit_price = float(close.iloc[min(i + hold_bars, len(close) - 1)])
                if direction == "LONG":
                    trade_pnl = (exit_price - entry) / entry
                else:
                    trade_pnl = (entry - exit_price) / entry

            pnl_list.append(trade_pnl * 100)  # as percent

        stats = _trade_stats(pnl_list)
        print(f"  Total trades: {stats['total_trades']}")
        print(f"  Win rate:     {stats['win_rate']*100:.1f}%")
        print(f"  Avg PnL:      {stats['avg_pnl_pct']:+.3f}%")
        print(f"  Sharpe:       {stats['sharpe']:.3f}")
        print(f"  p-value:      {stats['p_value']:.6f}")
        return stats

    except Exception as e:
        print(f"  [ERR] {e}")
        return {"error": str(e)}


# ══════════════════════════════════════════════════════════════════════
# PART 2b: PERPETUAL BASIS PROXY BACKTEST
# ══════════════════════════════════════════════════════════════════════

def backtest_perpetual_basis() -> dict:
    """
    Proxy: Binance historical funding rates (free API).
    funding_rate > 0.001 -> expect mean-reversion SHORT
    funding_rate < -0.0005 -> expect bounce LONG
    Validate against next-8h price move from yfinance 1h bars.
    """
    _print_section("2b. Perpetual Basis (Funding Rate) Proxy Backtest")

    # Fetch historical funding rates from Binance Futures
    print("  Fetching Binance BTCUSDT funding rate history...")
    url = "https://fapi.binance.com/fapi/v1/fundingRate?symbol=BTCUSDT&limit=500"
    raw = _fetch_json(url)
    if not raw or not isinstance(raw, list):
        print("  [ERR] Could not fetch Binance funding data")
        return {"error": "Binance funding API unavailable"}

    print(f"  Fetched {len(raw)} funding rate records")

    if not HAS_YF:
        print("  [SKIP] yfinance not available -- cannot validate price moves")
        return {"error": "yfinance not available"}

    # Get BTC-USD hourly data for the same period
    df = yf.download("BTC-USD", period="1y", interval="1h", progress=False, auto_adjust=True)
    df.columns = [c if isinstance(c, str) else c[0] for c in df.columns]
    if len(df) < 50:
        return {"error": "Insufficient hourly data"}

    # Convert funding records to DataFrame
    funding_records = []
    for rec in raw:
        try:
            ts = int(rec["fundingTime"]) / 1000  # ms -> s
            rate = float(rec["fundingRate"])
            funding_records.append((ts, rate))
        except (KeyError, ValueError, TypeError):
            continue

    if not funding_records:
        return {"error": "No valid funding records"}

    # Build lookup: timestamp -> price from hourly df
    df_ts = df.copy()
    df_ts.index = pd.to_datetime(df_ts.index)
    if df_ts.index.tz is None:
        df_ts.index = df_ts.index.tz_localize("UTC")
    else:
        df_ts.index = df_ts.index.tz_convert("UTC")

    pnl_list = []
    HOLD_HOURS = 8  # hold 8 hours after funding event
    TP_PCT = 0.01   # 1% TP
    SL_PCT = 0.008  # 0.8% SL

    for ts, rate in funding_records:
        direction = None
        if rate > 0.001:
            direction = "SHORT"
        elif rate < -0.0005:
            direction = "LONG"

        if direction is None:
            continue

        # Find the hourly bar at this timestamp
        event_dt = pd.Timestamp(ts, unit="s", tz="UTC")
        try:
            # Find nearest bar
            idx_pos = df_ts.index.get_indexer([event_dt], method="nearest")[0]
            if idx_pos < 0 or idx_pos >= len(df_ts) - HOLD_HOURS:
                continue

            entry = float(df_ts["Close"].iloc[idx_pos])
            if entry <= 0:
                continue

            tp = entry * (1 + TP_PCT) if direction == "LONG" else entry * (1 - TP_PCT)
            sl = entry * (1 - SL_PCT) if direction == "LONG" else entry * (1 + SL_PCT)

            trade_pnl = None
            for j in range(idx_pos + 1, min(idx_pos + HOLD_HOURS + 1, len(df_ts))):
                hi = float(df_ts["High"].iloc[j])
                lo = float(df_ts["Low"].iloc[j])

                if direction == "LONG":
                    if hi >= tp:
                        trade_pnl = TP_PCT
                        break
                    elif lo <= sl:
                        trade_pnl = -SL_PCT
                        break
                else:
                    if lo <= tp:
                        trade_pnl = TP_PCT
                        break
                    elif hi >= sl:
                        trade_pnl = -SL_PCT
                        break

            if trade_pnl is None:
                exit_px = float(df_ts["Close"].iloc[min(idx_pos + HOLD_HOURS, len(df_ts) - 1)])
                if direction == "LONG":
                    trade_pnl = (exit_px - entry) / entry
                else:
                    trade_pnl = (entry - exit_px) / entry

            pnl_list.append(trade_pnl * 100)

        except Exception:
            continue

    stats = _trade_stats(pnl_list)
    print(f"  Total trades: {stats['total_trades']}")
    print(f"  Win rate:     {stats['win_rate']*100:.1f}%")
    print(f"  Avg PnL:      {stats['avg_pnl_pct']:+.3f}%")
    print(f"  Sharpe:       {stats['sharpe']:.3f}")
    print(f"  p-value:      {stats['p_value']:.6f}")
    return stats


# ══════════════════════════════════════════════════════════════════════
# PART 2c: ORDER BOOK IMBALANCE PROXY BACKTEST
# ══════════════════════════════════════════════════════════════════════

def backtest_order_book_imbalance() -> dict:
    """
    Proxy: Volume-based imbalance signal.
    When volume > 2x 20-period SMA AND price rising -> simulate bid imbalance -> BUY
    When volume > 2x 20-period SMA AND price falling -> simulate ask imbalance -> SELL
    """
    _print_section("2c. Order Book Imbalance Proxy Backtest (Volume Proxy)")
    if not HAS_YF:
        print("  [SKIP] yfinance not available")
        return {"error": "yfinance not available"}

    try:
        # Use 4h bars for more data points
        df = yf.download("BTC-USD", period="2y", interval="1h", progress=False, auto_adjust=True)
        df.columns = [c if isinstance(c, str) else c[0] for c in df.columns]
        if len(df) < 50:
            return {"error": "Insufficient data"}

        close = df["Close"].astype(float)
        volume = df["Volume"].astype(float)

        vol_sma = volume.rolling(20).mean()
        price_change = close.pct_change()

        pnl_list = []
        HOLD_HOURS = 4
        TP_PCT = 0.02   # 2% TP (tighter microstructure trade)
        SL_PCT = 0.015  # 1.5% SL

        for i in range(20, len(close) - HOLD_HOURS - 1):
            vol_i = float(volume.iloc[i])
            avg_vol = float(vol_sma.iloc[i])
            if avg_vol <= 0:
                continue
            vol_ratio = vol_i / avg_vol

            if vol_ratio < 2.0:
                continue  # Not a high-volume bar

            ret = float(price_change.iloc[i])
            entry = float(close.iloc[i])

            direction = None
            if ret > 0:    # Price rising + high vol -> bid imbalance
                direction = "LONG"
            elif ret < 0:  # Price falling + high vol -> ask imbalance
                direction = "SHORT"

            if direction is None:
                continue

            tp = entry * (1 + TP_PCT) if direction == "LONG" else entry * (1 - TP_PCT)
            sl = entry * (1 - SL_PCT) if direction == "LONG" else entry * (1 + SL_PCT)

            trade_pnl = None
            for j in range(i + 1, min(i + HOLD_HOURS + 1, len(close))):
                hi = float(df["High"].iloc[j])
                lo = float(df["Low"].iloc[j])

                if direction == "LONG":
                    if hi >= tp:
                        trade_pnl = TP_PCT
                        break
                    elif lo <= sl:
                        trade_pnl = -SL_PCT
                        break
                else:
                    if lo <= tp:
                        trade_pnl = TP_PCT
                        break
                    elif hi >= sl:
                        trade_pnl = -SL_PCT
                        break

            if trade_pnl is None:
                exit_px = float(close.iloc[min(i + HOLD_HOURS, len(close) - 1)])
                if direction == "LONG":
                    trade_pnl = (exit_px - entry) / entry
                else:
                    trade_pnl = (entry - exit_px) / entry

            pnl_list.append(trade_pnl * 100)

        stats = _trade_stats(pnl_list)
        print(f"  Total trades: {stats['total_trades']}")
        print(f"  Win rate:     {stats['win_rate']*100:.1f}%")
        print(f"  Avg PnL:      {stats['avg_pnl_pct']:+.3f}%")
        print(f"  Sharpe:       {stats['sharpe']:.3f}")
        print(f"  p-value:      {stats['p_value']:.6f}")
        return stats

    except Exception as e:
        print(f"  [ERR] {e}")
        return {"error": str(e)}


# ══════════════════════════════════════════════════════════════════════
# PART 2d: OPTIONS SKEW PROXY BACKTEST (VIX)
# ══════════════════════════════════════════════════════════════════════

def backtest_options_skew() -> dict:
    """
    Proxy: ^VIX as fear/greed proxy for options skew.
    VIX > 30 = extreme put skew (fear) -> contrarian BUY BTC
    VIX < 15 = low skew (complacency) -> contrarian SELL BTC
    Hold 5 days, 5% TP / 3% SL.
    """
    _print_section("2d. Options 25-Delta Skew Proxy Backtest (VIX Proxy)")
    if not HAS_YF:
        print("  [SKIP] yfinance not available")
        return {"error": "yfinance not available"}

    try:
        # Fetch VIX and BTC-USD daily data
        vix = yf.download("^VIX", period="5y", interval="1d", progress=False, auto_adjust=True)
        btc = yf.download("BTC-USD", period="5y", interval="1d", progress=False, auto_adjust=True)

        vix.columns = [c if isinstance(c, str) else c[0] for c in vix.columns]
        btc.columns = [c if isinstance(c, str) else c[0] for c in btc.columns]

        if len(vix) < 50 or len(btc) < 50:
            return {"error": "Insufficient VIX or BTC data"}

        # Align indices
        vix_close = vix["Close"].astype(float)
        btc_close = btc["Close"].astype(float)
        btc_high  = btc["High"].astype(float)
        btc_low   = btc["Low"].astype(float)

        # Reindex VIX to BTC dates
        combined = pd.DataFrame({"vix": vix_close, "btc": btc_close,
                                  "hi": btc_high, "lo": btc_low})
        combined.dropna(inplace=True)

        if len(combined) < 50:
            return {"error": "Insufficient aligned data"}

        pnl_list = []
        HOLD_DAYS = 5
        TP_PCT = 0.05
        SL_PCT = 0.03

        for i in range(len(combined) - HOLD_DAYS - 1):
            vix_val = float(combined["vix"].iloc[i])
            entry   = float(combined["btc"].iloc[i])

            direction = None
            if vix_val > 30:    # Extreme fear -> contrarian BUY
                direction = "LONG"
            elif vix_val < 15:  # Complacency -> contrarian SELL
                direction = "SHORT"

            if direction is None:
                continue

            tp = entry * (1 + TP_PCT) if direction == "LONG" else entry * (1 - TP_PCT)
            sl = entry * (1 - SL_PCT) if direction == "LONG" else entry * (1 + SL_PCT)

            trade_pnl = None
            for j in range(i + 1, min(i + HOLD_DAYS + 1, len(combined))):
                hi = float(combined["hi"].iloc[j])
                lo = float(combined["lo"].iloc[j])

                if direction == "LONG":
                    if hi >= tp:
                        trade_pnl = TP_PCT
                        break
                    elif lo <= sl:
                        trade_pnl = -SL_PCT
                        break
                else:
                    if lo <= tp:
                        trade_pnl = TP_PCT
                        break
                    elif hi >= sl:
                        trade_pnl = -SL_PCT
                        break

            if trade_pnl is None:
                exit_px = float(combined["btc"].iloc[min(i + HOLD_DAYS, len(combined) - 1)])
                if direction == "LONG":
                    trade_pnl = (exit_px - entry) / entry
                else:
                    trade_pnl = (entry - exit_px) / entry

            pnl_list.append(trade_pnl * 100)

        stats = _trade_stats(pnl_list)
        print(f"  Total trades: {stats['total_trades']}")
        print(f"  Win rate:     {stats['win_rate']*100:.1f}%")
        print(f"  Avg PnL:      {stats['avg_pnl_pct']:+.3f}%")
        print(f"  Sharpe:       {stats['sharpe']:.3f}")
        print(f"  p-value:      {stats['p_value']:.6f}")
        return stats

    except Exception as e:
        print(f"  [ERR] {e}")
        return {"error": str(e)}


# ══════════════════════════════════════════════════════════════════════
# SUMMARY TABLE
# ══════════════════════════════════════════════════════════════════════

def _strategy_status(stats: dict) -> str:
    """Determine ENABLED/DISABLED based on performance metrics."""
    if "error" in stats:
        return "UNKNOWN"
    if stats.get("total_trades", 0) < 5:
        return "INSUFFICIENT_DATA"
    wr = stats.get("win_rate", 0)
    pval = stats.get("p_value", 1.0)
    avg = stats.get("avg_pnl_pct", 0)
    sharpe = stats.get("sharpe", 0)
    if wr >= 0.55 and pval <= 0.10 and avg > 0 and sharpe > 0.5:
        return "ENABLED"
    elif wr >= 0.52 and avg > 0:
        return "ENABLED"
    else:
        return "DISABLED"


def print_results_table(results: dict):
    _print_header("FINAL RESULTS SUMMARY")
    col_w = [28, 6, 8, 8, 6, 8, 8, 10]
    headers = ["Strategy", "Trades", "WinRate", "AvgPnL%", "Sharpe", "p-val", "Live#", "Status"]

    # Header
    line = ""
    for h, w in zip(headers, col_w):
        line += h.ljust(w)
    print(line)
    print("-" * sum(col_w))

    for name, data in results.items():
        stats = data.get("stats", {})
        live_n = data.get("live_signals", 0)
        status = data.get("status", "UNKNOWN")

        trades = stats.get("total_trades", 0)
        wr_str = f"{stats.get('win_rate', 0)*100:.1f}%" if trades else "N/A"
        pnl_str = f"{stats.get('avg_pnl_pct', 0):+.3f}" if trades else "N/A"
        sh_str = f"{stats.get('sharpe', 0):.3f}" if trades else "N/A"
        pv_str = f"{stats.get('p_value', 1.0):.4f}" if trades else "N/A"

        row = [
            name[:27], str(trades), wr_str, pnl_str,
            sh_str, pv_str, str(live_n), status
        ]
        line = ""
        for v, w in zip(row, col_w):
            line += str(v).ljust(w)
        print(line)

    print("-" * sum(col_w))


# ══════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════

def main():
    print()
    print("=" * 72)
    print("  ALPHA ENGINE -- WAVE 16 MARKET MICROSTRUCTURE BACKTESTER")
    print(f"  Run date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 72)

    # Part 1: Live validation
    live_counts = run_live_validation()

    # Part 2: Historical proxy backtests
    _print_header("PART 2: HISTORICAL PROXY BACKTESTS")

    cb_stats   = backtest_coinbase_premium()
    perp_stats = backtest_perpetual_basis()
    obi_stats  = backtest_order_book_imbalance()
    opt_stats  = backtest_options_skew()

    # Assemble results
    results = {
        "options_25delta_skew": {
            "stats": opt_stats,
            "live_signals": live_counts.get("options_25delta_skew", 0),
            "proxy_method": "VIX > 30 = extreme fear -> BUY; VIX < 15 = complacency -> SELL",
            "backtest_note": "VIX daily proxy, BTC 5yr, 5d hold, 5% TP / 3% SL",
        },
        "coinbase_premium_index": {
            "stats": cb_stats,
            "live_signals": live_counts.get("coinbase_premium_index", 0),
            "proxy_method": "1d return > 0.5% -> BUY (premium proxy); < -0.3% -> SELL",
            "backtest_note": "BTC-USD daily 2yr, 3d hold, 2% TP / 1.5% SL",
        },
        "order_book_imbalance": {
            "stats": obi_stats,
            "live_signals": live_counts.get("order_book_imbalance", 0),
            "proxy_method": "Volume > 2x SMA + price up -> BUY; vol > 2x + price down -> SELL",
            "backtest_note": "BTC-USD 1h bars 2yr, 4h hold, 2% TP / 1.5% SL",
        },
        "perpetual_basis": {
            "stats": perp_stats,
            "live_signals": live_counts.get("perpetual_basis", 0),
            "proxy_method": "Funding > 0.1% -> SHORT mean-reversion; funding < -0.05% -> LONG",
            "backtest_note": "Binance 500 funding records + BTC 1h price, 8h hold, 1% TP / 0.8% SL",
        },
    }

    # Add status to each
    for name, data in results.items():
        data["status"] = _strategy_status(data["stats"])

    # Print summary table
    print_results_table(results)

    # Build output JSON
    output = {
        "run_date": datetime.now(timezone.utc).isoformat(),
        "strategies": {},
    }
    for name, data in results.items():
        stats = data["stats"]
        output["strategies"][name] = {
            "total_trades": stats.get("total_trades", 0),
            "win_rate": stats.get("win_rate", 0.0),
            "avg_pnl_pct": stats.get("avg_pnl_pct", 0.0),
            "sharpe": stats.get("sharpe", 0.0),
            "p_value": stats.get("p_value", 1.0),
            "best_trade": stats.get("best_trade", 0.0),
            "worst_trade": stats.get("worst_trade", 0.0),
            "live_signals": data.get("live_signals", 0),
            "status": data.get("status", "UNKNOWN"),
            "proxy_method": data.get("proxy_method", ""),
            "backtest_note": data.get("backtest_note", ""),
        }

    OUTPUT_FILE.write_text(json.dumps(output, indent=2))
    print(f"\n[OK] Results saved to: {OUTPUT_FILE}")
    print()

    # Print JSON summary inline
    print("JSON Output:")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
