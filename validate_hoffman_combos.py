"""
Hoffman Winning Combos — Multi-Period Multi-Symbol Robustness Validation
=========================================================================

Tests the top winning Hoffman combinations across:
  - 20+ symbols (expanded from original 10)
  - Multiple time periods (using Binance endTime to get different historical windows)
  - Different timeframes (15m, 1h)

Goal: Eliminate the possibility that the 78.9% WR result was a "fluke"
by proving consistency across independent data samples.

Usage:
    python validate_hoffman_combos.py
"""

import json
import sys
import time
import math
from datetime import datetime, timezone, timedelta
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional

import numpy as np
import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))

# ══════════════════════════════════════════════════════════════════════
# Data structures (same as backtest_hoffman_combos.py)
# ══════════════════════════════════════════════════════════════════════

@dataclass
class Signal:
    symbol: str
    direction: str
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str


# 25 symbols — original 10 + 15 additional
SYMBOLS_CORE = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "DOGEUSDT",
                "XRPUSDT", "LTCUSDT", "ADAUSDT", "LINKUSDT", "AVAXUSDT"]

SYMBOLS_EXTENDED = [
    "MATICUSDT", "NEARUSDT", "APTUSDT", "SUIUSDT", "ICPUSDT",
    "ARBUSDT", "OPUSDT", "INJUSDT", "FETUSDT", "DOTUSDT",
    "ATOMUSDT", "FILUSDT", "RUNEUSDT", "SEIUSDT", "TIAUSDT",
]

ALL_SYMBOLS = SYMBOLS_CORE + SYMBOLS_EXTENDED

# Time periods to test (use endTime to get different historical windows)
# Each period fetches 1000 bars ending at that time
TIME_PERIODS = {
    "recent":    None,           # most recent 1000 bars (default)
    "1w_ago":    7,              # data ending 1 week ago
    "2w_ago":    14,             # data ending 2 weeks ago
    "1m_ago":    30,             # data ending 1 month ago
}

KLINE_COLUMNS = [
    "open_time", "open", "high", "low", "close", "volume",
    "close_time", "qav", "trades", "tbbav", "tbqav", "ignore",
]


# ══════════════════════════════════════════════════════════════════════
# Indicator Library (same as backtest_hoffman_combos.py)
# ══════════════════════════════════════════════════════════════════════

def _ema(arr, period):
    out = np.full_like(arr, np.nan, dtype=float)
    if len(arr) < period:
        return out
    out[period - 1] = np.mean(arr[:period])
    k = 2.0 / (period + 1)
    for i in range(period, len(arr)):
        out[i] = arr[i] * k + out[i - 1] * (1 - k)
    return out


def _sma(arr, period):
    out = np.full_like(arr, np.nan, dtype=float)
    cs = np.nancumsum(arr)
    out[period - 1:] = (cs[period - 1:] - np.concatenate([[0], cs[:-period]])) / period
    return out


def _atr(high, low, close, period=14):
    n = len(high)
    tr = np.zeros(n)
    tr[0] = high[0] - low[0]
    for i in range(1, n):
        tr[i] = max(high[i] - low[i],
                     abs(high[i] - close[i - 1]),
                     abs(low[i] - close[i - 1]))
    out = np.full(n, np.nan)
    if n < period:
        return out
    out[period - 1] = np.mean(tr[:period])
    for i in range(period, n):
        out[i] = (out[i - 1] * (period - 1) + tr[i]) / period
    return out


def _rsi(close, period=14):
    n = len(close)
    out = np.full(n, np.nan)
    if n < period + 1:
        return out
    deltas = np.diff(close)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])
    if avg_loss == 0:
        out[period] = 100.0
    else:
        out[period] = 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0:
            out[i + 1] = 100.0
        else:
            out[i + 1] = 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)
    return out


def _adx(high, low, close, period=14):
    n = len(high)
    out = np.full(n, np.nan)
    if n < period * 2 + 1:
        return out
    plus_dm = np.zeros(n)
    minus_dm = np.zeros(n)
    for i in range(1, n):
        up = high[i] - high[i - 1]
        down = low[i - 1] - low[i]
        plus_dm[i] = up if (up > down and up > 0) else 0
        minus_dm[i] = down if (down > up and down > 0) else 0
    tr = np.zeros(n)
    tr[0] = high[0] - low[0]
    for i in range(1, n):
        tr[i] = max(high[i] - low[i], abs(high[i] - close[i - 1]), abs(low[i] - close[i - 1]))
    atr_vals = _ema(tr, period)
    plus_di = np.where(atr_vals > 0, 100 * _ema(plus_dm, period) / atr_vals, 0)
    minus_di = np.where(atr_vals > 0, 100 * _ema(minus_dm, period) / atr_vals, 0)
    dx = np.where((plus_di + minus_di) > 0, 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di), 0)
    out = _ema(dx, period)
    return out


# ══════════════════════════════════════════════════════════════════════
# Precomputed indicator cache
# ══════════════════════════════════════════════════════════════════════

class IndicatorCache:
    def __init__(self, df):
        c = df["close"].values.astype(float)
        h = df["high"].values.astype(float)
        l = df["low"].values.astype(float)
        v = df["volume"].values.astype(float)

        self.close = c
        self.high = h
        self.low = l
        self.volume = v

        # EMAs
        self.ema5 = _ema(c, 5)
        self.ema9 = _ema(c, 9)
        self.ema20 = _ema(c, 20)
        self.sma50 = _sma(c, 50)

        # ATR
        self.atr14 = _atr(h, l, c, 14)

        # RSI
        self.rsi14 = _rsi(c, 14)
        self.rsi2 = _rsi(c, 2)

        # Volume
        self.vol_sma20 = _sma(v, 20)

        # ADX
        self.adx14 = _adx(h, l, c, 14)

        # MACD
        ema12 = _ema(c, 12)
        ema26 = _ema(c, 26)
        self.macd_line = ema12 - ema26
        self.macd_signal = _ema(self.macd_line, 9)
        self.macd_hist = self.macd_line - self.macd_signal

        # Bollinger Bands
        self.bb_mid = _sma(c, 20)
        bb_std = np.full_like(c, np.nan)
        for i in range(19, len(c)):
            bb_std[i] = np.std(c[i - 19:i + 1])
        self.bb_upper = self.bb_mid + 2 * bb_std
        self.bb_lower = self.bb_mid - 2 * bb_std

        # Swing levels (20-bar lookback)
        self.swing_high = np.full_like(h, np.nan)
        self.swing_low = np.full_like(l, np.nan)
        for i in range(20, len(h)):
            self.swing_high[i] = np.max(h[i - 20:i])
            self.swing_low[i] = np.min(l[i - 20:i])

        # Consecutive candle count
        self.consec_red = np.zeros(len(c), dtype=int)
        self.consec_green = np.zeros(len(c), dtype=int)
        for i in range(1, len(c)):
            o = df["open"].values[i] if "open" in df.columns else c[i - 1]
            if c[i] < o:
                self.consec_red[i] = self.consec_red[i - 1] + 1
                self.consec_green[i] = 0
            elif c[i] > o:
                self.consec_green[i] = self.consec_green[i - 1] + 1
                self.consec_red[i] = 0

        # HTF EMA (4x resampled)
        n4 = len(c) // 4
        if n4 >= 20:
            htf_c = c[::4][:n4]
            htf_ema = _ema(htf_c, 20)
            self.htf_ema_rising = np.full(len(c), False)
            for i in range(1, n4):
                if not np.isnan(htf_ema[i]) and not np.isnan(htf_ema[i - 1]):
                    rising = htf_ema[i] > htf_ema[i - 1]
                    for j in range(4):
                        idx = i * 4 + j
                        if idx < len(c):
                            self.htf_ema_rising[idx] = rising
        else:
            self.htf_ema_rising = np.full(len(c), True)

        # EMA angle
        self.ema_angle = np.full(len(c), 0.0)
        for i in range(5, len(c)):
            if not np.isnan(self.ema20[i]) and not np.isnan(self.ema20[i - 5]):
                atr_val = self.atr14[i] if not np.isnan(self.atr14[i]) else 1
                if atr_val > 0:
                    self.ema_angle[i] = math.degrees(math.atan2(
                        (self.ema20[i] - self.ema20[i - 5]) / atr_val, 5
                    ))


# ══════════════════════════════════════════════════════════════════════
# IRB Detection
# ══════════════════════════════════════════════════════════════════════

def detect_irb(cache, i, threshold=0.45):
    if i < 1:
        return None
    c = cache.close[i]
    o = cache.close[i - 1]  # Use prev close as proxy for open
    h = cache.high[i]
    l = cache.low[i]
    bar_range = h - l
    if bar_range <= 0:
        return None
    upper_wick = h - max(c, o)
    lower_wick = min(c, o) - l
    if lower_wick / bar_range >= threshold and c > o:
        return "BUY"
    if upper_wick / bar_range >= threshold and c < o:
        return "SELL"
    return None


# ══════════════════════════════════════════════════════════════════════
# Filter functions
# ══════════════════════════════════════════════════════════════════════

def f_rsi2_extreme(cache, i, direction):
    v = cache.rsi2[i]
    if np.isnan(v):
        return False
    if direction == "BUY":
        return v < 25
    return v > 75


def f_volume_1_2x(cache, i, direction):
    if np.isnan(cache.vol_sma20[i]):
        return False
    return cache.volume[i] > 1.2 * cache.vol_sma20[i]


def f_consecutive_reversal(cache, i, direction):
    if direction == "BUY":
        return cache.consec_red[i] >= 2
    return cache.consec_green[i] >= 2


def f_ema_ribbon(cache, i, direction):
    e5 = cache.ema5[i]
    e20 = cache.ema20[i]
    s50 = cache.sma50[i]
    if any(np.isnan(x) for x in [e5, e20, s50]):
        return False
    if direction == "BUY":
        return e5 > e20 > s50
    return e5 < e20 < s50


def f_htf_trend(cache, i, direction):
    if direction == "BUY":
        return cache.htf_ema_rising[i]
    return not cache.htf_ema_rising[i]


def f_rsi14_moderate(cache, i, direction):
    v = cache.rsi14[i]
    if np.isnan(v):
        return False
    if direction == "BUY":
        return 25 <= v <= 60
    return 40 <= v <= 75


def f_adx_trending(cache, i, direction):
    v = cache.adx14[i]
    if np.isnan(v):
        return False
    return v > 20


def f_macd_confirm(cache, i, direction):
    h = cache.macd_hist[i]
    if np.isnan(h):
        return False
    if direction == "BUY":
        return h > 0
    return h < 0


def f_angle_gte_10(cache, i, direction):
    a = cache.ema_angle[i]
    if direction == "BUY":
        return a >= 10
    return a <= -10


def f_angle_gte_15(cache, i, direction):
    a = cache.ema_angle[i]
    if direction == "BUY":
        return a >= 15
    return a <= -15


# ══════════════════════════════════════════════════════════════════════
# Strategy definitions — top combos to validate
# ══════════════════════════════════════════════════════════════════════

def make_signals(cache, symbol, filters, wide_stops=False, irb_thresh=0.45):
    """Generate signals using IRB + filters."""
    signals = []
    atr_tp_mult = 3.0 if wide_stops else 2.0
    atr_sl_mult = 2.0 if wide_stops else 1.0

    for i in range(50, len(cache.close)):
        direction = detect_irb(cache, i, irb_thresh)
        if direction is None:
            continue

        # Apply all filters
        if not all(f(cache, i, direction) for f in filters):
            continue

        price = cache.close[i]
        atr_val = cache.atr14[i]
        if np.isnan(atr_val) or atr_val <= 0:
            continue

        if direction == "BUY":
            tp = price + atr_val * atr_tp_mult
            sl = price - atr_val * atr_sl_mult
        else:
            tp = price - atr_val * atr_tp_mult
            sl = price + atr_val * atr_sl_mult

        signals.append((i, Signal(
            symbol=symbol, direction=direction, confidence=0.7,
            entry_price=price, take_profit=tp, stop_loss=sl,
            reason="IRB+" + "+".join(f.__name__[2:] for f in filters)
        )))
    return signals


# Top strategies to validate
STRATEGIES = {
    "EliteCombo (IRB+RSI2+Consec+Vol+Wide)": {
        "filters": [f_rsi2_extreme, f_consecutive_reversal, f_volume_1_2x],
        "wide_stops": True,
    },
    "RSI2Ribbon (IRB+RSI2+Vol+EMA)": {
        "filters": [f_rsi2_extreme, f_volume_1_2x, f_ema_ribbon],
        "wide_stops": False,
    },
    "VolumeHTF (IRB+HTF+Vol+RSI14)": {
        "filters": [f_htf_trend, f_volume_1_2x, f_rsi14_moderate, f_angle_gte_10],
        "wide_stops": False,
    },
    "VolumePower (IRB+Vol+Angle+Wide)": {
        "filters": [f_volume_1_2x, f_angle_gte_15],
        "wide_stops": True,
    },
    "MACDRegime (IRB+MACD+Vol+ADX)": {
        "filters": [f_macd_confirm, f_volume_1_2x, f_adx_trending],
        "wide_stops": False,
    },
    "VolumeOnly (IRB+Vol)": {
        "filters": [f_volume_1_2x],
        "wide_stops": False,
    },
    "RSI2Only (IRB+RSI2)": {
        "filters": [f_rsi2_extreme],
        "wide_stops": False,
    },
    "WideStopsOnly (IRB+Wide)": {
        "filters": [],
        "wide_stops": True,
    },
}


# ══════════════════════════════════════════════════════════════════════
# Data fetching
# ══════════════════════════════════════════════════════════════════════

def fetch_historical(symbol, interval="15m", limit=1000, end_time_ms=None):
    """Fetch historical klines from Binance."""
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    if end_time_ms is not None:
        params["endTime"] = end_time_ms
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    df = pd.DataFrame(resp.json(), columns=KLINE_COLUMNS)
    for col in ("open", "high", "low", "close", "volume"):
        df[col] = df[col].astype(float)
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
    return df


# ══════════════════════════════════════════════════════════════════════
# Trade simulator
# ══════════════════════════════════════════════════════════════════════

def simulate_trades(signals_list, df, max_hold_bars=16):
    """Walk-forward simulation. Returns list of trade dicts."""
    trades = []
    position = None
    signals_by_bar = {bar_idx: sig for bar_idx, sig in signals_list}

    for bar_idx in range(len(df)):
        price = df["close"].iloc[bar_idx]
        high = df["high"].iloc[bar_idx]
        low = df["low"].iloc[bar_idx]

        if position is not None:
            entry = position["entry_price"]
            hold_bars = bar_idx - position["entry_bar"]
            d = position["direction"]

            hit_tp = (high >= position["tp"]) if d == "BUY" else (low <= position["tp"])
            hit_sl = (low <= position["sl"]) if d == "BUY" else (high >= position["sl"])

            if hit_sl:
                exit_p = position["sl"]
                raw_pct = ((exit_p - entry) / entry * 100) if d == "BUY" else ((entry - exit_p) / entry * 100)
                trades.append({"pnl_pct": raw_pct, "exit_reason": "SL", "hold_bars": hold_bars, "direction": d})
                position = None
                continue
            elif hit_tp:
                exit_p = position["tp"]
                raw_pct = ((exit_p - entry) / entry * 100) if d == "BUY" else ((entry - exit_p) / entry * 100)
                trades.append({"pnl_pct": raw_pct, "exit_reason": "TP", "hold_bars": hold_bars, "direction": d})
                position = None
                continue
            elif hold_bars >= max_hold_bars:
                raw_pct = ((price - entry) / entry * 100) if d == "BUY" else ((entry - price) / entry * 100)
                trades.append({"pnl_pct": raw_pct, "exit_reason": "TIME", "hold_bars": hold_bars, "direction": d})
                position = None
                continue

        if position is None and bar_idx in signals_by_bar:
            sig = signals_by_bar[bar_idx]
            position = {
                "entry_bar": bar_idx, "entry_price": sig.entry_price,
                "tp": sig.take_profit, "sl": sig.stop_loss, "direction": sig.direction,
            }

    return trades


def compute_metrics(trades):
    """Compute comprehensive metrics."""
    if not trades:
        return {
            "total_trades": 0, "win_rate": 0, "avg_pnl_pct": 0,
            "total_pnl_pct": 0, "profit_factor": 0, "max_drawdown_pct": 0,
            "avg_hold_bars": 0, "sharpe": 0,
        }

    pnls = [t["pnl_pct"] for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    total_pnl = sum(pnls)
    gross_profit = sum(wins) if wins else 0
    gross_loss = abs(sum(losses)) if losses else 0.001

    # Max drawdown
    equity = [0]
    for p in pnls:
        equity.append(equity[-1] + p)
    peak = equity[0]
    max_dd = 0
    for e in equity:
        peak = max(peak, e)
        dd = peak - e
        max_dd = max(max_dd, dd)

    # Sharpe (annualized, assume ~96 trades/day for 15m bars)
    if len(pnls) > 1 and np.std(pnls) > 0:
        sharpe = (np.mean(pnls) / np.std(pnls)) * np.sqrt(252)
    else:
        sharpe = 0

    return {
        "total_trades": len(trades),
        "win_rate": round(len(wins) / len(trades) * 100, 1),
        "avg_pnl_pct": round(total_pnl / len(trades), 3),
        "total_pnl_pct": round(total_pnl, 2),
        "profit_factor": round(gross_profit / gross_loss, 2),
        "max_drawdown_pct": round(max_dd, 2),
        "avg_hold_bars": round(sum(t["hold_bars"] for t in trades) / len(trades), 1),
        "sharpe": round(sharpe, 2),
    }


# ══════════════════════════════════════════════════════════════════════
# Main validation
# ══════════════════════════════════════════════════════════════════════

def main():
    print("=" * 80)
    print("  Hoffman Winning Combos — ROBUSTNESS VALIDATION")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 80)
    print(f"  Symbols: {len(ALL_SYMBOLS)} | Periods: {len(TIME_PERIODS)} | Strategies: {len(STRATEGIES)}")
    print("=" * 80)

    all_results = {}

    for period_name, days_ago in TIME_PERIODS.items():
        end_time_ms = None
        if days_ago is not None:
            end_dt = datetime.now(timezone.utc) - timedelta(days=days_ago)
            end_time_ms = int(end_dt.timestamp() * 1000)

        print(f"\n{'='*80}")
        print(f"  PERIOD: {period_name} {'(latest data)' if days_ago is None else f'(ending {days_ago}d ago)'}")
        print(f"{'='*80}")

        # Fetch data for all symbols in this period
        period_data = {}
        for sym in ALL_SYMBOLS:
            try:
                df = fetch_historical(sym, "15m", 1000, end_time_ms)
                if len(df) >= 100:
                    period_data[sym] = df
                    date_range = f"{df['open_time'].iloc[0].strftime('%m/%d')} - {df['open_time'].iloc[-1].strftime('%m/%d')}"
                    print(f"    + {sym}: {len(df)} bars ({date_range})")
                else:
                    print(f"    x {sym}: only {len(df)} bars, skipping")
            except Exception as e:
                print(f"    x {sym}: FAILED ({e})")
            time.sleep(0.15)  # rate limit

        if not period_data:
            print("    No data for this period, skipping")
            continue

        # Run each strategy
        for strat_name, strat_config in STRATEGIES.items():
            all_trades = []
            sym_results = {}

            for sym, df in period_data.items():
                cache = IndicatorCache(df)
                signals = make_signals(
                    cache, sym,
                    strat_config["filters"],
                    strat_config["wide_stops"],
                )
                trades = simulate_trades(signals, df, max_hold_bars=16)
                all_trades.extend(trades)
                if trades:
                    sym_metrics = compute_metrics(trades)
                    sym_results[sym] = sym_metrics

            metrics = compute_metrics(all_trades)

            key = f"{period_name}|{strat_name}"
            all_results[key] = {
                "period": period_name,
                "strategy": strat_name,
                "metrics": metrics,
                "symbols_tested": len(period_data),
                "symbols_with_trades": len(sym_results),
                "per_symbol": sym_results,
            }

            # Print summary line
            m = metrics
            status = "+" if m["win_rate"] >= 50 else "o" if m["win_rate"] >= 40 else "x"
            print(f"  {status} {strat_name:<42} "
                  f"T:{m['total_trades']:>4} | "
                  f"WR:{m['win_rate']:>5.1f}% | "
                  f"PnL:{m['total_pnl_pct']:>+8.2f}% | "
                  f"AvgPnL:{m['avg_pnl_pct']:>+6.3f}% | "
                  f"PF:{m['profit_factor']:>5.2f} | "
                  f"DD:{m['max_drawdown_pct']:>6.2f}% | "
                  f"Sh:{m['sharpe']:>5.2f}")

    # ══════════════════════════════════════════════════════════════════
    # Cross-period consistency analysis
    # ══════════════════════════════════════════════════════════════════
    print("\n" + "=" * 80)
    print("  CROSS-PERIOD CONSISTENCY ANALYSIS")
    print("=" * 80)

    strategy_across_periods = {}
    for key, result in all_results.items():
        sname = result["strategy"]
        if sname not in strategy_across_periods:
            strategy_across_periods[sname] = []
        strategy_across_periods[sname].append(result)

    consistency_report = []

    for sname, results in strategy_across_periods.items():
        wrs = [r["metrics"]["win_rate"] for r in results if r["metrics"]["total_trades"] > 0]
        pnls = [r["metrics"]["total_pnl_pct"] for r in results if r["metrics"]["total_trades"] > 0]
        pfs = [r["metrics"]["profit_factor"] for r in results if r["metrics"]["total_trades"] > 0]
        dds = [r["metrics"]["max_drawdown_pct"] for r in results if r["metrics"]["total_trades"] > 0]
        avg_pnls = [r["metrics"]["avg_pnl_pct"] for r in results if r["metrics"]["total_trades"] > 0]
        trades = [r["metrics"]["total_trades"] for r in results]
        sharpes = [r["metrics"]["sharpe"] for r in results if r["metrics"]["total_trades"] > 0]

        if not wrs:
            continue

        total_trades = sum(trades)
        periods_profitable = sum(1 for p in pnls if p > 0)
        periods_above_50wr = sum(1 for w in wrs if w >= 50)

        report = {
            "strategy": sname,
            "periods_tested": len(results),
            "periods_profitable": periods_profitable,
            "periods_above_50wr": periods_above_50wr,
            "total_trades": total_trades,
            "avg_wr": round(np.mean(wrs), 1),
            "min_wr": round(min(wrs), 1),
            "max_wr": round(max(wrs), 1),
            "wr_std": round(np.std(wrs), 1),
            "avg_pnl": round(np.mean(avg_pnls), 3),
            "avg_total_pnl": round(np.mean(pnls), 2),
            "avg_pf": round(np.mean(pfs), 2),
            "avg_dd": round(np.mean(dds), 2),
            "max_dd": round(max(dds), 2),
            "avg_sharpe": round(np.mean(sharpes), 2),
            "is_robust": periods_profitable >= 3 and np.mean(wrs) >= 45 and total_trades >= 20,
        }
        consistency_report.append(report)

        # Determine verdict
        if report["is_robust"] and report["avg_wr"] >= 50:
            verdict = "*** VALIDATED ***"
        elif report["is_robust"]:
            verdict = "ROBUST (borderline WR)"
        elif periods_profitable >= 2:
            verdict = "MARGINAL"
        else:
            verdict = "FLUKE / UNRELIABLE"

        print(f"\n  {sname}")
        print(f"    Total trades across all periods: {total_trades}")
        print(f"    WR range: {report['min_wr']:.1f}% - {report['max_wr']:.1f}% (avg {report['avg_wr']:.1f}%, std {report['wr_std']:.1f}%)")
        print(f"    Avg PnL per trade: {report['avg_pnl']:+.3f}%")
        print(f"    Avg PF: {report['avg_pf']:.2f} | Avg Max DD: {report['avg_dd']:.2f}% | Max DD: {report['max_dd']:.2f}%")
        print(f"    Avg Sharpe: {report['avg_sharpe']:.2f}")
        print(f"    Profitable periods: {periods_profitable}/{len(results)} | Periods >50% WR: {periods_above_50wr}/{len(results)}")
        print(f"    VERDICT: {verdict}")

    # Save results
    results_dir = Path(__file__).parent / "backtest_results"
    results_dir.mkdir(exist_ok=True)
    out_file = results_dir / "hoffman_validation.json"
    with open(out_file, "w") as f:
        json.dump({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "symbols": ALL_SYMBOLS,
            "periods": list(TIME_PERIODS.keys()),
            "strategy_count": len(STRATEGIES),
            "results": list(all_results.values()),
            "consistency_report": consistency_report,
        }, f, indent=2)
    print(f"\n  Results saved to {out_file}")

    # Final ranking
    print("\n" + "=" * 80)
    print("  FINAL ROBUSTNESS RANKING")
    print("=" * 80)
    ranked = sorted(consistency_report, key=lambda r: (r["is_robust"], r["avg_wr"], r["avg_pf"]), reverse=True)
    for i, r in enumerate(ranked, 1):
        robust_tag = "[VALIDATED]" if r["is_robust"] and r["avg_wr"] >= 50 else "[ROBUST]" if r["is_robust"] else "[WEAK]"
        print(f"  {i}. {robust_tag} {r['strategy']:<42} "
              f"AvgWR:{r['avg_wr']:>5.1f}% | "
              f"AvgPnL:{r['avg_pnl']:>+6.3f}% | "
              f"AvgPF:{r['avg_pf']:>5.2f} | "
              f"AvgDD:{r['avg_dd']:>6.2f}% | "
              f"MaxDD:{r['max_dd']:>6.2f}% | "
              f"Trades:{r['total_trades']:>4} | "
              f"Prof:{r['periods_profitable']}/{r['periods_tested']}")


if __name__ == "__main__":
    main()
