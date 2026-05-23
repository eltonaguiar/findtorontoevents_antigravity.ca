#!/usr/bin/env python3
"""
Comprehensive Backtest: Trusted Genome Mutations
==================================================
Runs all 5 trusted genome mutation strategies against the full 21-symbol
universe using 500 bars of 1h OHLCV data from Binance.

Walk-forward: signals generated from bar 200..500, ATR-based TP/SL,
24h max hold, commission + slippage deducted.

Outputs:
  - genome/data/trusted_genome_backtest.json   (full structured results)
  - genome/data/trusted_genome_backtest_report.md (readable report)
"""

from __future__ import annotations

import json
import sys
import time
import traceback
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

# ── Config ───────────────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = ROOT / "genome" / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

FULL_UNIVERSE = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "LTCUSDT",
    "ADAUSDT", "TAOUSDT", "AVAXUSDT", "LINKUSDT", "NEARUSDT",
    "SUIUSDT", "APTUSDT", "DOGEUSDT", "ARBUSDT", "OPUSDT", "INJUSDT",
    "FETUSDT", "TIAUSDT", "SEIUSDT", "FILUSDT",
]

KLINE_LIMIT = 500
KLINE_INTERVAL = "1h"
LOOKBACK_START = 200  # Start rolling signals from bar 200

INITIAL_CAPITAL = 10_000.0
POSITION_SIZE_PCT = 0.10
COMMISSION_PCT = 0.001
SLIPPAGE_PCT = 0.0005
MAX_HOLD_BARS = 24
DEFAULT_TP_ATR = 2.0
DEFAULT_SL_ATR = 1.5

BINANCE_MIRRORS = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
    "https://data-api.binance.vision",
]

REQUEST_DELAY = 0.25


# ── Indicators ────────────────────────────────────────────────────────────────

def sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(period).mean()

def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()

def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).fillna(50.0)

def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs()
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

def bollinger_bands(close: pd.Series, period: int = 20, std_mult: float = 2.0):
    mid = close.rolling(period).mean()
    std = close.rolling(period).std()
    return mid + std_mult * std, mid, mid - std_mult * std


# ── Data Fetching ─────────────────────────────────────────────────────────────

def fetch_klines(symbol: str, interval: str = KLINE_INTERVAL, limit: int = KLINE_LIMIT):
    for base in BINANCE_MIRRORS:
        url = f"{base}/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "TrustedGenomeBacktest/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
            if data and isinstance(data, list) and len(data) > 50:
                df = pd.DataFrame(data, columns=[
                    "open_time", "Open", "High", "Low", "Close", "Volume",
                    "close_time", "qav", "num_trades", "taker_buy_base",
                    "taker_buy_quote", "ignore"
                ])
                for col in ["Open", "High", "Low", "Close", "Volume"]:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
                df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
                df.set_index("open_time", inplace=True)
                return df[["Open", "High", "Low", "Close", "Volume"]]
        except Exception:
            continue
    return None


def fetch_all_data() -> dict:
    data = {}
    print(f"\nFetching {KLINE_LIMIT} bars of {KLINE_INTERVAL} data for {len(FULL_UNIVERSE)} symbols...")
    for i, symbol in enumerate(FULL_UNIVERSE):
        df = fetch_klines(symbol)
        if df is not None and len(df) >= LOOKBACK_START:
            data[symbol] = df
            print(f"  [{i+1:2d}/{len(FULL_UNIVERSE)}] {symbol}: {len(df)} bars OK")
        else:
            bars = len(df) if df is not None else 0
            print(f"  [{i+1:2d}/{len(FULL_UNIVERSE)}] {symbol}: {bars} bars -- SKIP")
        time.sleep(REQUEST_DELAY)
    print(f"\nLoaded {len(data)}/{len(FULL_UNIVERSE)} symbols\n")
    return data


# ── Signal Helpers ────────────────────────────────────────────────────────────

def _signal(bar_index: int, direction: str, confidence: float,
            tp_atr_mult: float = DEFAULT_TP_ATR, sl_atr_mult: float = DEFAULT_SL_ATR,
            reason: str = "") -> dict:
    return {
        "bar_index": bar_index,
        "direction": direction,
        "confidence": round(min(0.95, confidence), 4),
        "tp_atr_mult": tp_atr_mult,
        "sl_atr_mult": sl_atr_mult,
        "reason": reason,
    }


# ═══════════════════════════════════════════════════════════════════════════
# STRATEGY SIGNAL GENERATORS (bar-by-bar for backtesting)
# ═══════════════════════════════════════════════════════════════════════════

def signals_regime_switch(df: pd.DataFrame, symbol: str) -> list:
    """Regime-adaptive: trend-follow in high-vol, mean-revert in low-vol."""
    signals = []
    close = df["Close"]
    high = df["High"]
    low = df["Low"]

    returns = close.pct_change()
    vol_20 = returns.rolling(20).std()
    vol_pctile = vol_20.rank(pct=True)
    atr_s = atr(high, low, close, 14)
    rsi_s = rsi(close, 14)
    macd_l, macd_sig, macd_h = macd(close)
    ema_9 = ema(close, 9)
    ema_21 = ema(close, 21)
    ema_50 = ema(close, 50)
    bb_upper, bb_mid, bb_lower = bollinger_bands(close, 20, 2.0)

    for i in range(LOOKBACK_START, len(df)):
        current = float(close.iloc[i])
        if current <= 0:
            continue
        atr_now = float(atr_s.iloc[i])
        if np.isnan(atr_now) or atr_now <= 0:
            continue

        vp = float(vol_pctile.iloc[i]) if not np.isnan(vol_pctile.iloc[i]) else 0.5
        r = float(rsi_s.iloc[i])
        h = float(macd_h.iloc[i])
        is_high_vol = vp > 0.65

        if is_high_vol:
            # TREND mode
            ef = float(ema_9.iloc[i])
            es = float(ema_21.iloc[i])
            et = float(ema_50.iloc[i])
            if ef > es > et and h > 0 and r < 70:
                conf = 0.55 + min(0.25, (ef - es) / atr_now * 0.1)
                signals.append(_signal(i, "BUY", conf, 2.5, 1.5,
                    f"TREND regime (vp={vp:.0%}): EMA stack bull, RSI={r:.0f}"))
            elif ef < es < et and h < 0 and r > 30:
                conf = 0.55 + min(0.25, (es - ef) / atr_now * 0.1)
                signals.append(_signal(i, "SELL", conf, 2.5, 1.5,
                    f"TREND regime (vp={vp:.0%}): EMA stack bear, RSI={r:.0f}"))
        else:
            # MEANREV mode
            bb_lo = float(bb_lower.iloc[i])
            bb_up = float(bb_upper.iloc[i])
            if r < 30 and current <= bb_lo * 1.01:
                conf = 0.60 + min(0.20, (30 - r) / 30 * 0.2)
                signals.append(_signal(i, "BUY", conf, 2.0, 1.2,
                    f"MEANREV regime (vp={vp:.0%}): RSI={r:.0f} at BB lower"))
            elif r > 70 and current >= bb_up * 0.99:
                conf = 0.60 + min(0.20, (r - 70) / 30 * 0.2)
                signals.append(_signal(i, "SELL", conf, 2.0, 1.2,
                    f"MEANREV regime (vp={vp:.0%}): RSI={r:.0f} at BB upper"))

    return signals


def signals_basket_corr_gate(df: pd.DataFrame, symbol: str,
                              btc_returns: pd.Series = None) -> list:
    """Correlation-gated: only trade when alt corr with BTC > 0.4."""
    signals = []
    if symbol == "BTCUSDT" or btc_returns is None:
        return signals

    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    alt_returns = close.pct_change()

    atr_s = atr(high, low, close, 14)
    rsi_s = rsi(close, 14)
    ema_9 = ema(close, 9)
    ema_21 = ema(close, 21)
    macd_l, _, macd_h = macd(close)

    for i in range(LOOKBACK_START, len(df)):
        current = float(close.iloc[i])
        if current <= 0:
            continue
        atr_now = float(atr_s.iloc[i])
        if np.isnan(atr_now) or atr_now <= 0:
            continue

        # Rolling 30-bar correlation
        if i < 30:
            continue
        try:
            btc_slice = btc_returns.iloc[i-30:i].values
            alt_slice = alt_returns.iloc[i-30:i].values
            if len(btc_slice) < 30 or len(alt_slice) < 30:
                continue
            # Remove NaN
            mask = ~(np.isnan(btc_slice) | np.isnan(alt_slice))
            if mask.sum() < 20:
                continue
            corr = float(np.corrcoef(btc_slice[mask], alt_slice[mask])[0, 1])
        except Exception:
            continue

        if np.isnan(corr) or corr < 0.4:
            continue

        r = float(rsi_s.iloc[i])
        e9 = float(ema_9.iloc[i])
        e21 = float(ema_21.iloc[i])
        h = float(macd_h.iloc[i])

        if e9 > e21 and h > 0 and 35 < r < 65:
            conf = 0.55 + min(0.25, corr * 0.2)
            signals.append(_signal(i, "BUY", conf, 2.0, 1.5,
                f"Corr-gated (BTC corr={corr:.2f}): EMA bull, RSI={r:.0f}"))
        elif e9 < e21 and h < 0 and 35 < r < 65:
            conf = 0.55 + min(0.25, corr * 0.2)
            signals.append(_signal(i, "SELL", conf, 2.0, 1.5,
                f"Corr-gated (BTC corr={corr:.2f}): EMA bear, RSI={r:.0f}"))

    return signals


def signals_vol_scaler_size(df: pd.DataFrame, symbol: str) -> list:
    """Inverse vol-scaled entries: lower confidence in high-vol."""
    signals = []
    close = df["Close"]
    high = df["High"]
    low = df["Low"]

    atr_s = atr(high, low, close, 14)
    avg_atr_s = atr_s.rolling(50).mean()
    rsi_s = rsi(close, 14)
    ema_9 = ema(close, 9)
    ema_21 = ema(close, 21)
    ema_50 = ema(close, 50)
    _, _, macd_h = macd(close)

    for i in range(LOOKBACK_START, len(df)):
        current = float(close.iloc[i])
        if current <= 0:
            continue
        atr_now = float(atr_s.iloc[i])
        avg_atr = float(avg_atr_s.iloc[i])
        if any(np.isnan(v) or v <= 0 for v in [atr_now, avg_atr]):
            continue

        vol_ratio = atr_now / avg_atr
        vol_scale = np.clip(1.0 / vol_ratio, 0.5, 1.5)

        r = float(rsi_s.iloc[i])
        e9 = float(ema_9.iloc[i])
        e21 = float(ema_21.iloc[i])
        e50 = float(ema_50.iloc[i])
        h = float(macd_h.iloc[i])

        if e9 > e21 > e50 and h > 0 and r < 65:
            scaled_conf = 0.60 * vol_scale
            tp_mult = 2.0 * vol_scale
            signals.append(_signal(i, "BUY", scaled_conf, tp_mult, 1.5,
                f"Vol-scaled (ratio={vol_ratio:.2f}): EMA bull, RSI={r:.0f}"))
        elif e9 < e21 < e50 and h < 0 and r > 35:
            scaled_conf = 0.60 * vol_scale
            tp_mult = 2.0 * vol_scale
            signals.append(_signal(i, "SELL", scaled_conf, tp_mult, 1.5,
                f"Vol-scaled (ratio={vol_ratio:.2f}): EMA bear, RSI={r:.0f}"))

    return signals


def signals_mtf_align(df: pd.DataFrame, symbol: str) -> list:
    """Multi-timeframe alignment: 1h + 4h + daily must agree."""
    signals = []
    close = df["Close"]
    high = df["High"]
    low = df["Low"]

    # Pre-compute 1h indicators
    ema9_1h = ema(close, 9)
    ema21_1h = ema(close, 21)
    rsi_1h = rsi(close, 14)
    atr_s = atr(high, low, close, 14)

    # Build 4h resampled data
    n = len(df)
    trim_4h = n - (n % 4)
    if trim_4h < 100:
        return signals
    sliced_4h = df.iloc[-trim_4h:].copy()
    groups_4h = np.arange(len(sliced_4h)) // 4
    df_4h = sliced_4h.groupby(groups_4h).agg(
        {"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"})
    ema9_4h = ema(df_4h["Close"], 9)
    ema21_4h = ema(df_4h["Close"], 21)
    rsi_4h = rsi(df_4h["Close"], 14)

    # Build daily resampled data
    trim_1d = n - (n % 24)
    if trim_1d < 240:
        return signals
    sliced_1d = df.iloc[-trim_1d:].copy()
    groups_1d = np.arange(len(sliced_1d)) // 24
    df_1d = sliced_1d.groupby(groups_1d).agg(
        {"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"})
    ema9_1d = ema(df_1d["Close"], 9)
    ema21_1d = ema(df_1d["Close"], 21)

    for i in range(LOOKBACK_START, len(df)):
        current = float(close.iloc[i])
        if current <= 0:
            continue
        atr_now = float(atr_s.iloc[i])
        if np.isnan(atr_now) or atr_now <= 0:
            continue

        # 1h signal
        e9_1h = float(ema9_1h.iloc[i])
        e21_1h = float(ema21_1h.iloc[i])
        sig_1h = 1 if e9_1h > e21_1h else (-1 if e9_1h < e21_1h else 0)

        # Map 1h bar index to 4h bar index
        offset_4h = n - trim_4h
        if i < offset_4h:
            continue
        idx_4h = (i - offset_4h) // 4
        if idx_4h >= len(df_4h) or idx_4h < 10:
            continue
        e9_4h_val = float(ema9_4h.iloc[idx_4h])
        e21_4h_val = float(ema21_4h.iloc[idx_4h])
        sig_4h = 1 if e9_4h_val > e21_4h_val else (-1 if e9_4h_val < e21_4h_val else 0)

        # Map to daily bar index
        offset_1d = n - trim_1d
        if i < offset_1d:
            continue
        idx_1d = (i - offset_1d) // 24
        if idx_1d >= len(df_1d) or idx_1d < 5:
            continue
        e9_1d_val = float(ema9_1d.iloc[idx_1d])
        e21_1d_val = float(ema21_1d.iloc[idx_1d])
        sig_1d = 1 if e9_1d_val > e21_1d_val else (-1 if e9_1d_val < e21_1d_val else 0)

        if sig_1h == 0 or sig_4h == 0 or sig_1d == 0:
            continue
        if not (sig_1h == sig_4h == sig_1d):
            continue

        r_1h = float(rsi_1h.iloc[i])
        r_4h = float(rsi_4h.iloc[idx_4h])
        rsi_boost = 0.0
        if sig_1h == 1 and r_1h < 60 and r_4h < 60:
            rsi_boost = 0.10
        elif sig_1h == -1 and r_1h > 40 and r_4h > 40:
            rsi_boost = 0.10

        if sig_1h == 1:
            signals.append(_signal(i, "BUY", 0.65 + rsi_boost, 2.5, 1.5,
                f"3TF aligned LONG: RSI 1h={r_1h:.0f} 4h={r_4h:.0f}"))
        else:
            signals.append(_signal(i, "SELL", 0.65 + rsi_boost, 2.5, 1.5,
                f"3TF aligned SHORT: RSI 1h={r_1h:.0f} 4h={r_4h:.0f}"))

    return signals


def signals_vol_adaptive_thresh(df: pd.DataFrame, symbol: str) -> list:
    """ATR-adaptive RSI thresholds: widen in high-vol, tighten in low-vol."""
    signals = []
    close = df["Close"]
    high = df["High"]
    low = df["Low"]

    atr_s = atr(high, low, close, 14)
    avg_atr_s = atr_s.rolling(50).mean()
    rsi_s = rsi(close, 14)
    ema_21 = ema(close, 21)
    _, _, macd_h = macd(close)

    for i in range(LOOKBACK_START, len(df)):
        current = float(close.iloc[i])
        if current <= 0:
            continue
        atr_now = float(atr_s.iloc[i])
        avg_atr = float(avg_atr_s.iloc[i])
        if any(np.isnan(v) or v <= 0 for v in [atr_now, avg_atr]):
            continue

        vol_ratio = atr_now / avg_atr
        oversold = np.clip(30 - (vol_ratio - 1.0) * 10, 20, 40)
        overbought = np.clip(70 + (vol_ratio - 1.0) * 10, 60, 80)

        r = float(rsi_s.iloc[i])
        e21 = float(ema_21.iloc[i])
        h_now = float(macd_h.iloc[i])
        h_prev = float(macd_h.iloc[i - 1]) if i > 0 else 0

        if r < oversold and h_now > h_prev and current > e21:
            extremity = (oversold - r) / oversold
            conf = 0.55 + min(0.25, extremity * 0.3)
            signals.append(_signal(i, "BUY", conf, 2.0, 1.3,
                f"Adaptive RSI: thresh={oversold:.0f}/{overbought:.0f}, RSI={r:.0f}, MACD turning up"))

        elif r > overbought and h_now < h_prev and current < e21:
            extremity = (r - overbought) / (100 - overbought)
            conf = 0.55 + min(0.25, extremity * 0.3)
            signals.append(_signal(i, "SELL", conf, 2.0, 1.3,
                f"Adaptive RSI: thresh={oversold:.0f}/{overbought:.0f}, RSI={r:.0f}, MACD turning down"))

    return signals


# ── Registry ──────────────────────────────────────────────────────────────────

STRATEGIES = {
    "regime_switch_mut": {
        "fn": signals_regime_switch,
        "description": "Trend-follow in high-vol regime, mean-revert in low-vol regime",
        "needs_btc": False,
    },
    "basket_corr_gate_mut": {
        "fn": signals_basket_corr_gate,
        "description": "BTC correlation gate: only trade alts correlated > 0.4 with BTC",
        "needs_btc": True,
    },
    "vol_scaler_size_mut": {
        "fn": signals_vol_scaler_size,
        "description": "Inverse volatility-scaled confidence/position sizing",
        "needs_btc": False,
    },
    "mtf_align_mut": {
        "fn": signals_mtf_align,
        "description": "3-timeframe confluence: 1h + 4h + daily must all agree",
        "needs_btc": False,
    },
    "vol_adaptive_thresh_mut": {
        "fn": signals_vol_adaptive_thresh,
        "description": "ATR-scaled RSI thresholds: widen in high-vol, tighten in low-vol",
        "needs_btc": False,
    },
}


# ── Trade Simulator ──────────────────────────────────────────────────────────

def simulate_trades(df: pd.DataFrame, signals: list) -> list:
    trades = []
    position = None

    for i in range(len(df)):
        row = df.iloc[i]
        h = float(row["High"])
        l = float(row["Low"])
        c = float(row["Close"])

        if position is not None:
            bars_held = i - position["entry_bar"]
            exit_price = None
            exit_reason = None

            if position["direction"] == "BUY":
                if l <= position["sl"]:
                    exit_price = position["sl"] * (1 - SLIPPAGE_PCT)
                    exit_reason = "SL"
                elif h >= position["tp"]:
                    exit_price = position["tp"] * (1 - SLIPPAGE_PCT)
                    exit_reason = "TP"
                elif bars_held >= MAX_HOLD_BARS:
                    exit_price = c * (1 - SLIPPAGE_PCT)
                    exit_reason = "TIME"
            else:
                if h >= position["sl"]:
                    exit_price = position["sl"] * (1 + SLIPPAGE_PCT)
                    exit_reason = "SL"
                elif l <= position["tp"]:
                    exit_price = position["tp"] * (1 + SLIPPAGE_PCT)
                    exit_reason = "TP"
                elif bars_held >= MAX_HOLD_BARS:
                    exit_price = c * (1 + SLIPPAGE_PCT)
                    exit_reason = "TIME"

            if exit_price is not None and exit_price > 0:
                if position["direction"] == "BUY":
                    pnl_pct = (exit_price - position["entry"]) / position["entry"]
                else:
                    pnl_pct = (position["entry"] - exit_price) / position["entry"]
                pnl_pct -= 2 * COMMISSION_PCT

                trades.append({
                    "entry_bar": position["entry_bar"],
                    "exit_bar": i,
                    "bars_held": bars_held,
                    "direction": position["direction"],
                    "entry_price": position["entry"],
                    "exit_price": exit_price,
                    "pnl_pct": round(pnl_pct, 6),
                    "exit_reason": exit_reason,
                    "confidence": position["conf"],
                })
                position = None

        if position is None:
            for sig in signals:
                if sig["bar_index"] == i:
                    entry = float(c)
                    if entry <= 0:
                        break
                    atr_val = float(atr(df["High"], df["Low"], df["Close"], 14).iloc[i])
                    if np.isnan(atr_val) or atr_val <= 0:
                        break

                    if sig["direction"] == "BUY":
                        entry_price = entry * (1 + SLIPPAGE_PCT)
                        tp = entry_price + sig["tp_atr_mult"] * atr_val
                        sl = entry_price - sig["sl_atr_mult"] * atr_val
                    else:
                        entry_price = entry * (1 - SLIPPAGE_PCT)
                        tp = entry_price - sig["tp_atr_mult"] * atr_val
                        sl = entry_price + sig["sl_atr_mult"] * atr_val

                    position = {
                        "direction": sig["direction"],
                        "entry": entry_price,
                        "tp": tp,
                        "sl": sl,
                        "entry_bar": i,
                        "conf": sig["confidence"],
                    }
                    break

    return trades


def compute_metrics(trades: list) -> dict:
    if not trades:
        return {
            "num_trades": 0, "wins": 0, "losses": 0,
            "win_rate": 0.0, "avg_pnl_pct": 0.0,
            "total_return_pct": 0.0, "profit_factor": 0.0,
            "max_drawdown_pct": 0.0, "sharpe_ratio": 0.0,
            "avg_bars_held": 0.0, "tp_exits": 0, "sl_exits": 0, "time_exits": 0,
            "best_trade_pct": 0.0, "worst_trade_pct": 0.0,
        }

    pnls = [t["pnl_pct"] for t in trades]
    wins = sum(1 for p in pnls if p > 0)
    losses = len(pnls) - wins
    gross_profit = sum(p for p in pnls if p > 0)
    gross_loss = abs(sum(p for p in pnls if p <= 0))

    equity = INITIAL_CAPITAL
    peak = equity
    max_dd = 0.0
    for p in pnls:
        equity += equity * POSITION_SIZE_PCT * p
        peak = max(peak, equity)
        dd = (peak - equity) / peak if peak > 0 else 0
        max_dd = max(max_dd, dd)

    total_return = (equity - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
    avg_pnl = float(np.mean(pnls))
    std_pnl = float(np.std(pnls)) if len(pnls) > 1 else 1.0
    sharpe = (avg_pnl / std_pnl) * np.sqrt(8760 / MAX_HOLD_BARS) if std_pnl > 0 else 0.0

    return {
        "num_trades": len(trades),
        "wins": wins,
        "losses": losses,
        "win_rate": round(wins / len(trades), 4),
        "avg_pnl_pct": round(avg_pnl * 100, 4),
        "total_return_pct": round(total_return, 2),
        "profit_factor": round(gross_profit / gross_loss, 2) if gross_loss > 0 else (10.0 if gross_profit > 0 else 0.0),
        "max_drawdown_pct": round(max_dd * 100, 2),
        "sharpe_ratio": round(sharpe, 2),
        "avg_bars_held": round(float(np.mean([t["bars_held"] for t in trades])), 1),
        "tp_exits": sum(1 for t in trades if t["exit_reason"] == "TP"),
        "sl_exits": sum(1 for t in trades if t["exit_reason"] == "SL"),
        "time_exits": sum(1 for t in trades if t["exit_reason"] == "TIME"),
        "best_trade_pct": round(max(pnls) * 100, 4),
        "worst_trade_pct": round(min(pnls) * 100, 4),
    }


# ── Main Backtest Runner ────────────────────────────────────────────────────

def run_backtest():
    print("=" * 70)
    print("TRUSTED GENOME MUTATIONS -- COMPREHENSIVE BACKTEST")
    print(f"Universe: {len(FULL_UNIVERSE)} symbols | {KLINE_LIMIT} bars of {KLINE_INTERVAL}")
    print(f"Rolling window: bar {LOOKBACK_START}..{KLINE_LIMIT}")
    print(f"TP/SL: ATR-based (per-strategy defaults) | Max hold: {MAX_HOLD_BARS} bars")
    print(f"Commission: {COMMISSION_PCT*100:.1f}% | Slippage: {SLIPPAGE_PCT*100:.2f}%")
    print("=" * 70)

    market_data = fetch_all_data()
    if not market_data:
        print("FATAL: No market data fetched. Aborting.")
        sys.exit(1)

    # Pre-compute BTC returns for basket_corr_gate
    btc_returns = None
    if "BTCUSDT" in market_data:
        btc_returns = market_data["BTCUSDT"]["Close"].pct_change()

    results = {}
    all_strategy_metrics = {}

    for strat_name, strat_info in STRATEGIES.items():
        print(f"\n{'-'*60}")
        print(f"STRATEGY: {strat_name}")
        print(f"  {strat_info['description']}")
        print(f"{'-'*60}")

        per_symbol = {}
        all_trades = []

        for symbol, df in market_data.items():
            try:
                if strat_info.get("needs_btc"):
                    sigs = strat_info["fn"](df, symbol, btc_returns)
                else:
                    sigs = strat_info["fn"](df, symbol)

                if not sigs:
                    per_symbol[symbol] = {"signals": 0, "trades": [], "metrics": compute_metrics([])}
                    continue

                trades = simulate_trades(df, sigs)
                metrics = compute_metrics(trades)
                per_symbol[symbol] = {"signals": len(sigs), "trades": trades, "metrics": metrics}
                all_trades.extend(trades)

                if trades:
                    wr = metrics["win_rate"] * 100
                    ret = metrics["total_return_pct"]
                    print(f"  {symbol:10s}: {len(sigs):3d} signals -> {len(trades):3d} trades | "
                          f"WR={wr:5.1f}% | Ret={ret:+6.2f}% | PF={metrics['profit_factor']:.2f}")
                else:
                    print(f"  {symbol:10s}: {len(sigs):3d} signals -> 0 trades")
            except Exception as e:
                print(f"  {symbol:10s}: ERROR - {e}")
                traceback.print_exc()
                per_symbol[symbol] = {"signals": 0, "trades": [], "metrics": compute_metrics([])}

        agg = compute_metrics(all_trades)
        agg["symbols_scanned"] = len(market_data)
        agg["symbols_with_trades"] = sum(1 for s in per_symbol.values() if s["metrics"]["num_trades"] > 0)
        agg["profitable_symbols"] = sum(1 for s in per_symbol.values() if s["metrics"]["total_return_pct"] > 0)
        agg["total_signals"] = sum(s["signals"] for s in per_symbol.values())

        symbol_summary = {sym: {"signals": info["signals"], "metrics": info["metrics"]}
                         for sym, info in per_symbol.items()}

        results[strat_name] = {
            "description": strat_info["description"],
            "aggregate": agg,
            "per_symbol": symbol_summary,
        }
        all_strategy_metrics[strat_name] = agg

        print(f"\n  AGGREGATE: {agg['num_trades']} trades | "
              f"WR={agg['win_rate']*100:.1f}% | Ret={agg['total_return_pct']:+.2f}% | "
              f"PF={agg['profit_factor']:.2f} | MaxDD={agg['max_drawdown_pct']:.1f}% | "
              f"Sharpe={agg['sharpe_ratio']:.2f}")

    # Quality gates
    print(f"\n{'='*70}")
    print("QUALITY GATE ASSESSMENT")
    print(f"{'='*70}")

    gate_results = {}
    for name, m in all_strategy_metrics.items():
        gates = {
            "wr_45": m["win_rate"] >= 0.45,
            "sharpe_050": m["sharpe_ratio"] >= 0.50,
            "pf_100": m["profit_factor"] >= 1.0,
            "trades_5": m["num_trades"] >= 5,
            "maxdd_20": m["max_drawdown_pct"] <= 20.0,
            "positive_expectancy": m["avg_pnl_pct"] > 0,
        }
        passed = all(gates.values())
        gates["PASSED"] = passed
        gate_results[name] = gates

        status = "PASS" if passed else "FAIL"
        fails = [k for k, v in gates.items() if not v and k != "PASSED"]
        print(f"  [{status}] {name}")
        if fails:
            print(f"         Failed: {', '.join(fails)}")

    # Build output
    output = {
        "metadata": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "system": "trusted_genome_mutations",
            "universe": FULL_UNIVERSE,
            "symbols_loaded": len(market_data),
            "kline_interval": KLINE_INTERVAL,
            "kline_limit": KLINE_LIMIT,
            "lookback_start": LOOKBACK_START,
            "max_hold_bars": MAX_HOLD_BARS,
            "commission_pct": COMMISSION_PCT,
            "slippage_pct": SLIPPAGE_PCT,
            "position_size_pct": POSITION_SIZE_PCT,
        },
        "strategy_results": results,
        "quality_gates": gate_results,
        "ranking": sorted(
            [{"strategy": k, **v} for k, v in all_strategy_metrics.items()],
            key=lambda x: x.get("total_return_pct", -999),
            reverse=True,
        ),
    }

    # Save JSON
    json_path = DATA_DIR / "trusted_genome_backtest.json"
    with open(json_path, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\nSaved JSON: {json_path}")

    # Generate markdown report
    md = generate_report(output, all_strategy_metrics, gate_results, results)
    md_path = DATA_DIR / "trusted_genome_backtest_report.md"
    with open(md_path, "w") as f:
        f.write(md)
    print(f"Saved report: {md_path}")

    return output


def generate_report(output, metrics, gates, results):
    ts = output["metadata"]["timestamp"]
    lines = [
        "# Trusted Genome Mutations -- Backtest Report",
        "",
        f"**Run:** {ts}",
        f"**Universe:** {len(output['metadata']['universe'])} symbols | "
        f"{output['metadata']['kline_interval']} interval | "
        f"{output['metadata']['kline_limit']} bars",
        f"**Window:** Bar {output['metadata']['lookback_start']}..{output['metadata']['kline_limit']}",
        f"**Costs:** {output['metadata']['commission_pct']*100:.1f}% commission + "
        f"{output['metadata']['slippage_pct']*100:.2f}% slippage per side",
        "",
        "---",
        "",
        "## Summary Table",
        "",
        "| Strategy | Trades | Win Rate | Avg PnL | Total Ret | PF | MaxDD | Sharpe | Gate |",
        "|----------|--------|----------|---------|-----------|-----|-------|--------|------|",
    ]

    for name in STRATEGIES:
        m = metrics[name]
        g = gates[name]
        gate_str = "PASS" if g["PASSED"] else "FAIL"
        lines.append(
            f"| {name} | {m['num_trades']} | {m['win_rate']*100:.1f}% | "
            f"{m['avg_pnl_pct']:+.3f}% | {m['total_return_pct']:+.2f}% | "
            f"{m['profit_factor']:.2f} | {m['max_drawdown_pct']:.1f}% | "
            f"{m['sharpe_ratio']:.2f} | {gate_str} |"
        )

    lines.extend(["", "---", "", "## Per-Strategy Detail", ""])

    for name, info in results.items():
        m = info["aggregate"]
        lines.extend([
            f"### {name}",
            f"> {info['description']}",
            "",
            f"- **Trades:** {m['num_trades']} ({m['wins']}W / {m['losses']}L)",
            f"- **Win Rate:** {m['win_rate']*100:.1f}%",
            f"- **Avg PnL:** {m['avg_pnl_pct']:+.4f}%",
            f"- **Total Return:** {m['total_return_pct']:+.2f}%",
            f"- **Profit Factor:** {m['profit_factor']:.2f}",
            f"- **Max Drawdown:** {m['max_drawdown_pct']:.1f}%",
            f"- **Sharpe Ratio:** {m['sharpe_ratio']:.2f}",
            f"- **Avg Hold:** {m['avg_bars_held']:.1f} bars",
            f"- **Exit Mix:** TP={m['tp_exits']} | SL={m['sl_exits']} | TIME={m['time_exits']}",
            f"- **Best Trade:** {m['best_trade_pct']:+.3f}% | Worst: {m['worst_trade_pct']:+.3f}%",
            "",
        ])

        lines.extend([
            "| Symbol | Signals | Trades | WR | Return | PF |",
            "|--------|---------|--------|-----|--------|-----|",
        ])
        for sym in FULL_UNIVERSE:
            sym_info = info["per_symbol"].get(sym)
            if sym_info is None:
                continue
            sm = sym_info["metrics"]
            if sm["num_trades"] == 0 and sym_info["signals"] == 0:
                continue
            lines.append(
                f"| {sym} | {sym_info['signals']} | {sm['num_trades']} | "
                f"{sm['win_rate']*100:.0f}% | {sm['total_return_pct']:+.2f}% | "
                f"{sm['profit_factor']:.2f} |"
            )
        lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    run_backtest()
