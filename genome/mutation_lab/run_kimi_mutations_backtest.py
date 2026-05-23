#!/usr/bin/env python3
"""
Comprehensive Backtest: KIMI Supplemental Mutations
====================================================
Runs all 5 KIMI supplemental mutation strategies against the full 21-symbol
universe using 500 bars of 1h OHLCV data from Binance.

For each strategy, simulates BUY/SELL entries on a rolling window (bar 200..500)
using ATR-based TP/SL (defaults: 2x ATR for TP, 1.5x ATR for SL), with
commission and slippage deducted.

Outputs:
  - genome/data/kimi_mutations_backtest.json   (full structured results)
  - genome/data/kimi_mutations_backtest_report.md (readable report)
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
from typing import Optional

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

# Trade simulation
INITIAL_CAPITAL = 10_000.0
POSITION_SIZE_PCT = 0.10    # 10% of equity per trade
COMMISSION_PCT = 0.001      # 0.1% per side (Binance taker)
SLIPPAGE_PCT = 0.0005       # 0.05% slippage
MAX_HOLD_BARS = 24          # Max 24h hold on 1h bars
DEFAULT_TP_ATR = 2.0
DEFAULT_SL_ATR = 1.5

BINANCE_MIRRORS = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
    "https://data-api.binance.vision",
]

REQUEST_DELAY = 0.25  # 250ms between requests for rate limiting


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


# ── Data Fetching ─────────────────────────────────────────────────────────────

def fetch_klines(symbol: str, interval: str = KLINE_INTERVAL, limit: int = KLINE_LIMIT) -> Optional[pd.DataFrame]:
    """Fetch OHLCV from Binance with mirror rotation."""
    for base in BINANCE_MIRRORS:
        url = f"{base}/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "KIMIBacktest/1.0"})
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


def fetch_all_data() -> dict[str, pd.DataFrame]:
    """Fetch klines for all symbols with rate limiting."""
    data = {}
    print(f"\nFetching {KLINE_LIMIT} bars of {KLINE_INTERVAL} data for {len(FULL_UNIVERSE)} symbols...")
    for i, symbol in enumerate(FULL_UNIVERSE):
        df = fetch_klines(symbol)
        if df is not None and len(df) >= LOOKBACK_START:
            data[symbol] = df
            print(f"  [{i+1:2d}/{len(FULL_UNIVERSE)}] {symbol}: {len(df)} bars OK")
        else:
            bars = len(df) if df is not None else 0
            print(f"  [{i+1:2d}/{len(FULL_UNIVERSE)}] {symbol}: {bars} bars -- SKIP (need {LOOKBACK_START}+)")
        time.sleep(REQUEST_DELAY)
    print(f"\nLoaded {len(data)}/{len(FULL_UNIVERSE)} symbols\n")
    return data


# ── Strategy Signal Generators (adapted for backtesting) ─────────────────────
# Each returns a list of signal dicts with 'bar_index', 'direction', 'tp_atr', 'sl_atr'
# They operate on a single symbol's full DataFrame.

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


def signals_volume_profile_funding_snap(df: pd.DataFrame, symbol: str) -> list[dict]:
    """Strategy 1: Volume Profile + Funding Alignment (no live funding in backtest,
    so we simulate funding direction from price momentum as proxy)."""
    signals = []
    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    volume = df["Volume"]
    atr_s = atr(high, low, close, 14)
    lookback = 50

    for i in range(max(LOOKBACK_START, lookback + 10), len(df)):
        current = float(close.iloc[i])
        prev = float(close.iloc[i - 1])
        if current <= 0 or prev <= 0:
            continue

        atr_now = float(atr_s.iloc[i])
        if np.isnan(atr_now) or atr_now <= 0:
            continue

        # Volume-weighted POC over lookback
        typical = (high.iloc[i - lookback:i] + low.iloc[i - lookback:i] + close.iloc[i - lookback:i]) / 3
        vol_slice = volume.iloc[i - lookback:i]
        vol_sum = float(vol_slice.sum())
        if vol_sum <= 0:
            continue
        poc = float((typical * vol_slice).sum() / vol_sum)
        value_std = float(np.sqrt(((typical - poc) ** 2 * vol_slice).sum() / vol_sum))
        va_high = poc + 1.0 * value_std
        va_low = poc - 1.0 * value_std

        # Simulate funding direction from 8-bar momentum as proxy
        mom_8 = float(close.iloc[i] - close.iloc[i - 8]) / float(close.iloc[i - 8]) if i >= 8 else 0
        funding_bullish = mom_8 > 0.005
        funding_bearish = mom_8 < -0.005

        broke_above = prev <= va_high and current > va_high
        broke_below = prev >= va_low and current < va_low

        if broke_above and funding_bullish:
            conf = 0.55 + min(0.20, abs(mom_8) * 10)
            signals.append(_signal(i, "BUY", conf, 2.5, 1.5,
                                   f"VP breakout above POC={poc:.2f}"))
        elif broke_below and funding_bearish:
            conf = 0.55 + min(0.20, abs(mom_8) * 10)
            signals.append(_signal(i, "SELL", conf, 2.5, 1.5,
                                   f"VP breakdown below POC={poc:.2f}"))

    return signals


def signals_cross_agg_battleground_hybrid(df: pd.DataFrame, symbol: str) -> list[dict]:
    """Strategy 2: Cross-Aggregation Consensus + Battleground Momentum."""
    signals = []
    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    volume = df["Volume"]

    rsi_7 = rsi(close, 7)
    rsi_14 = rsi(close, 14)
    rsi_21 = rsi(close, 21)
    vol_avg = volume.rolling(20).mean()
    ma_20 = close.rolling(20).mean()
    ma_50 = close.rolling(50).mean()
    atr_s = atr(high, low, close, 14)

    for i in range(LOOKBACK_START, len(df)):
        current = float(close.iloc[i])
        if current <= 0:
            continue

        r7 = float(rsi_7.iloc[i])
        r14 = float(rsi_14.iloc[i])
        r21 = float(rsi_21.iloc[i])
        if any(np.isnan(v) for v in [r7, r14, r21]):
            continue

        atr_now = float(atr_s.iloc[i])
        if np.isnan(atr_now) or atr_now <= 0:
            continue

        oversold_consensus = r7 < 40 and r14 < 45 and r21 < 50
        overbought_consensus = r7 > 60 and r14 > 55 and r21 > 50

        va = float(vol_avg.iloc[i])
        vn = float(volume.iloc[i])
        vol_confirmed = (vn / va > 1.5) if va > 0 else False

        mom_1 = float(close.pct_change(1).iloc[i]) if i > 0 else 0

        if oversold_consensus and vol_confirmed and mom_1 > 0:
            conf = min(0.80, 0.50 + 0.15)
            signals.append(_signal(i, "BUY", conf, 2.0, 1.5,
                                   f"Consensus BUY: RSI {r7:.0f}/{r14:.0f}/{r21:.0f}"))
        elif overbought_consensus and vol_confirmed and mom_1 < 0:
            conf = min(0.80, 0.50 + 0.15)
            signals.append(_signal(i, "SELL", conf, 2.0, 1.5,
                                   f"Consensus SELL: RSI {r7:.0f}/{r14:.0f}/{r21:.0f}"))

    return signals


def signals_drawdown_volatility_expansion(df: pd.DataFrame, symbol: str) -> list[dict]:
    """Strategy 3: Drawdown Recovery + Volatility Expansion."""
    signals = []
    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    volume = df["Volume"]

    atr_s = atr(high, low, close, 14)
    rsi_14 = rsi(close, 14)
    high_20 = close.rolling(20).max()
    vol_avg = volume.rolling(20).mean()
    changes = close.diff()

    for i in range(LOOKBACK_START, len(df)):
        current = float(close.iloc[i])
        if current <= 0:
            continue

        h20 = float(high_20.iloc[i])
        if h20 <= 0:
            continue
        drawdown = (current - h20) / h20

        # Require meaningful drawdown (>5%)
        if drawdown > -0.05:
            continue

        # Recovery: last 2 bars positive
        if i < 2:
            continue
        c1 = float(changes.iloc[i])
        c2 = float(changes.iloc[i - 1])
        if not (c1 > 0 and c2 > 0):
            continue

        atr_now = float(atr_s.iloc[i])
        atr_prev = float(atr_s.iloc[i - 5]) if i >= 5 else atr_now
        if np.isnan(atr_now) or atr_now <= 0 or np.isnan(atr_prev) or atr_prev <= 0:
            continue

        # ATR expanding by 10%+
        if atr_now <= atr_prev * 1.1:
            continue

        r14 = float(rsi_14.iloc[i])
        if np.isnan(r14) or r14 > 50:
            continue

        va = float(vol_avg.iloc[i])
        vn = float(volume.iloc[i])
        vol_ratio = vn / va if va > 0 else 1.0

        recovery_strength = abs(drawdown) * 10
        vol_boost = min(0.1, (vol_ratio - 1.0) * 0.05)
        conf = min(0.75, 0.50 + recovery_strength + vol_boost)

        signals.append(_signal(i, "BUY", conf, 2.5, 1.5,
                               f"DD recovery: {drawdown:.1%} from high, RSI={r14:.0f}"))

    return signals


def signals_ema_ribbon_macd_divergence(df: pd.DataFrame, symbol: str) -> list[dict]:
    """Strategy 4: EMA Ribbon + MACD Histogram Divergence."""
    signals = []
    close = df["Close"]
    high = df["High"]
    low = df["Low"]

    ema_9 = ema(close, 9)
    ema_21 = ema(close, 21)
    ema_50 = ema(close, 50)

    ema_12 = ema(close, 12)
    ema_26 = ema(close, 26)
    macd_line = ema_12 - ema_26
    signal_line = ema(macd_line, 9)
    histogram = macd_line - signal_line

    atr_s = atr(high, low, close, 14)

    for i in range(LOOKBACK_START, len(df)):
        current = float(close.iloc[i])
        if current <= 0:
            continue

        e9 = float(ema_9.iloc[i])
        e21 = float(ema_21.iloc[i])
        e50 = float(ema_50.iloc[i])
        if any(np.isnan(v) for v in [e9, e21, e50]):
            continue

        atr_now = float(atr_s.iloc[i])
        if np.isnan(atr_now) or atr_now <= 0:
            continue

        bullish_ribbon = e9 > e21 > e50
        bearish_ribbon = e9 < e21 < e50

        if i < 3:
            continue
        hist_now = float(histogram.iloc[i])
        hist_prev = float(histogram.iloc[i - 1])
        hist_prev2 = float(histogram.iloc[i - 2])
        if any(np.isnan(v) for v in [hist_now, hist_prev, hist_prev2]):
            continue

        hist_turning_up = hist_now > hist_prev and hist_prev <= hist_prev2
        hist_turning_down = hist_now < hist_prev and hist_prev >= hist_prev2

        if bullish_ribbon and hist_turning_up:
            conf = 0.60 + min(0.20, (e9 - e50) / e50 * 100)
            # SL at EMA21 or 1.5x ATR
            sl_price = e21
            sl_atr_equiv = (current - sl_price) / atr_now if (current - sl_price) > 0 else 1.5
            signals.append(_signal(i, "BUY", conf, 2.5, max(sl_atr_equiv, 0.5),
                                   f"EMA ribbon bull + MACD hist turn"))
        elif bearish_ribbon and hist_turning_down:
            conf = 0.60 + min(0.20, (e50 - e9) / e50 * 100)
            sl_price = e21
            sl_atr_equiv = (sl_price - current) / atr_now if (sl_price - current) > 0 else 1.5
            signals.append(_signal(i, "SELL", conf, 2.5, max(sl_atr_equiv, 0.5),
                                   f"EMA ribbon bear + MACD hist turn"))

    return signals


def signals_vwap_bollinger_squeeze(df: pd.DataFrame, symbol: str) -> list[dict]:
    """Strategy 5: VWAP + Bollinger Squeeze Combo."""
    signals = []
    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    volume = df["Volume"]

    typical = (high + low + close) / 3
    vwap = (typical * volume).rolling(20).sum() / volume.rolling(20).sum()

    sma_20 = close.rolling(20).mean()
    std_20 = close.rolling(20).std()
    bb_upper = sma_20 + 2 * std_20
    bb_lower = sma_20 - 2 * std_20
    bandwidth = (bb_upper - bb_lower) / sma_20
    bw_avg = bandwidth.rolling(20).mean()

    rsi_14 = rsi(close, 14)
    atr_s = atr(high, low, close, 14)

    for i in range(LOOKBACK_START, len(df)):
        current = float(close.iloc[i])
        if current <= 0:
            continue

        vwap_now = float(vwap.iloc[i])
        bw_now = float(bandwidth.iloc[i])
        bw_avg_now = float(bw_avg.iloc[i])
        r14 = float(rsi_14.iloc[i])
        atr_now = float(atr_s.iloc[i])

        if any(np.isnan(v) for v in [vwap_now, bw_now, bw_avg_now, r14, atr_now]):
            continue
        if vwap_now <= 0 or atr_now <= 0 or bw_avg_now <= 0:
            continue

        in_squeeze = bw_now < bw_avg_now * 0.9
        was_in_squeeze = False
        if i >= 2:
            bw_prev = float(bandwidth.iloc[i - 1])
            was_in_squeeze = not np.isnan(bw_prev) and bw_prev < bw_avg_now * 0.9

        vwap_deviation = (current - vwap_now) / vwap_now

        # BUY: Price below VWAP during/after squeeze + RSI < 45
        if vwap_deviation < -0.005 and (in_squeeze or was_in_squeeze) and r14 < 45:
            squeeze_strength = (bw_avg_now - bw_now) / bw_avg_now
            conf = 0.55 + min(0.25, abs(vwap_deviation) * 20 + squeeze_strength * 0.1)
            signals.append(_signal(i, "BUY", conf, 2.0, 1.5,
                                   f"VWAP squeeze buy: {vwap_deviation:.2%} dev, RSI={r14:.0f}"))

        # SELL: Price above VWAP during/after squeeze + RSI > 55
        elif vwap_deviation > 0.005 and (in_squeeze or was_in_squeeze) and r14 > 55:
            squeeze_strength = (bw_avg_now - bw_now) / bw_avg_now
            conf = 0.55 + min(0.25, vwap_deviation * 20 + squeeze_strength * 0.1)
            signals.append(_signal(i, "SELL", conf, 2.0, 1.5,
                                   f"VWAP squeeze sell: {vwap_deviation:.2%} dev, RSI={r14:.0f}"))

    return signals


# ── Registry ──────────────────────────────────────────────────────────────────

STRATEGIES = {
    "volume_profile_funding_snap": {
        "fn": signals_volume_profile_funding_snap,
        "description": "Volume Profile POC breakout + funding rate alignment",
    },
    "cross_agg_battleground_hybrid": {
        "fn": signals_cross_agg_battleground_hybrid,
        "description": "Multi-system RSI consensus + volume + momentum",
    },
    "drawdown_volatility_expansion": {
        "fn": signals_drawdown_volatility_expansion,
        "description": "Drawdown recovery with ATR expansion + RSI filter",
    },
    "ema_ribbon_macd_divergence": {
        "fn": signals_ema_ribbon_macd_divergence,
        "description": "EMA 9/21/50 ribbon + MACD histogram divergence",
    },
    "vwap_bollinger_squeeze": {
        "fn": signals_vwap_bollinger_squeeze,
        "description": "VWAP mean reversion during Bollinger Band squeeze",
    },
}


# ── Trade Simulator ──────────────────────────────────────────────────────────

def simulate_trades(df: pd.DataFrame, signals: list[dict]) -> list[dict]:
    """Simulate trades from signals on OHLCV data.

    Returns list of closed trade dicts with pnl info.
    """
    trades = []
    position = None  # {direction, entry, tp, sl, entry_bar, conf}

    for i in range(len(df)):
        row = df.iloc[i]
        h = float(row["High"])
        l = float(row["Low"])
        c = float(row["Close"])

        # Check exit on open position
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
            else:  # SELL
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

                # Deduct commission (both sides)
                pnl_pct -= 2 * COMMISSION_PCT

                trades.append({
                    "entry_bar": position["entry_bar"],
                    "exit_bar": i,
                    "bars_held": bars_held,
                    "direction": position["direction"],
                    "entry_price": position["entry"],
                    "exit_price": exit_price,
                    "tp": position["tp"],
                    "sl": position["sl"],
                    "pnl_pct": round(pnl_pct, 6),
                    "exit_reason": exit_reason,
                    "confidence": position["conf"],
                })
                position = None

        # Check for new entry (only if flat)
        if position is None:
            # Find signal for this bar
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


def compute_metrics(trades: list[dict]) -> dict:
    """Compute performance metrics from trades list."""
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

    # Equity curve for drawdown + Sharpe
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

    # Annualized Sharpe (1h bars, ~8760 bars/year)
    sharpe = (avg_pnl / std_pnl) * np.sqrt(8760 / MAX_HOLD_BARS) if std_pnl > 0 else 0.0

    tp_exits = sum(1 for t in trades if t["exit_reason"] == "TP")
    sl_exits = sum(1 for t in trades if t["exit_reason"] == "SL")
    time_exits = sum(1 for t in trades if t["exit_reason"] == "TIME")

    return {
        "num_trades": len(trades),
        "wins": wins,
        "losses": losses,
        "win_rate": round(wins / len(trades), 4) if trades else 0,
        "avg_pnl_pct": round(avg_pnl * 100, 4),
        "total_return_pct": round(total_return, 2),
        "profit_factor": round(gross_profit / gross_loss, 2) if gross_loss > 0 else (10.0 if gross_profit > 0 else 0.0),
        "max_drawdown_pct": round(max_dd * 100, 2),
        "sharpe_ratio": round(sharpe, 2),
        "avg_bars_held": round(float(np.mean([t["bars_held"] for t in trades])), 1),
        "tp_exits": tp_exits,
        "sl_exits": sl_exits,
        "time_exits": time_exits,
        "best_trade_pct": round(max(pnls) * 100, 4),
        "worst_trade_pct": round(min(pnls) * 100, 4),
    }


# ── Main Backtest Runner ────────────────────────────────────────────────────

def run_backtest():
    """Run comprehensive backtest of all 5 KIMI mutations across full universe."""
    print("=" * 70)
    print("KIMI SUPPLEMENTAL MUTATIONS — COMPREHENSIVE BACKTEST")
    print(f"Universe: {len(FULL_UNIVERSE)} symbols | {KLINE_LIMIT} bars of {KLINE_INTERVAL}")
    print(f"Rolling window: bar {LOOKBACK_START}..{KLINE_LIMIT}")
    print(f"TP/SL: ATR-based (per-strategy defaults) | Max hold: {MAX_HOLD_BARS} bars")
    print(f"Commission: {COMMISSION_PCT*100:.1f}% | Slippage: {SLIPPAGE_PCT*100:.2f}%")
    print("=" * 70)

    # 1. Fetch data
    market_data = fetch_all_data()
    if not market_data:
        print("FATAL: No market data fetched. Aborting.")
        sys.exit(1)

    # Pre-compute ATR for all symbols (optimization: avoid recomputing in sim)
    # (atr is still computed per-bar in simulate_trades, but this is fine for 500 bars)

    # 2. Run each strategy across all symbols
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
                signals = strat_info["fn"](df, symbol)
                if not signals:
                    per_symbol[symbol] = {"signals": 0, "trades": [], "metrics": compute_metrics([])}
                    continue

                trades = simulate_trades(df, signals)
                metrics = compute_metrics(trades)
                per_symbol[symbol] = {
                    "signals": len(signals),
                    "trades": trades,
                    "metrics": metrics,
                }
                all_trades.extend(trades)

                if trades:
                    wr = metrics["win_rate"] * 100
                    ret = metrics["total_return_pct"]
                    print(f"  {symbol:10s}: {len(signals):3d} signals -> {len(trades):3d} trades | "
                          f"WR={wr:5.1f}% | Ret={ret:+6.2f}% | PF={metrics['profit_factor']:.2f}")
                else:
                    print(f"  {symbol:10s}: {len(signals):3d} signals -> 0 trades (no fills)")
            except Exception as e:
                print(f"  {symbol:10s}: ERROR - {e}")
                traceback.print_exc()
                per_symbol[symbol] = {"signals": 0, "trades": [], "metrics": compute_metrics([])}

        # Aggregate metrics
        agg_metrics = compute_metrics(all_trades)
        symbols_with_trades = sum(1 for s in per_symbol.values() if s["metrics"]["num_trades"] > 0)
        profitable_symbols = sum(1 for s in per_symbol.values() if s["metrics"]["total_return_pct"] > 0)
        total_signals = sum(s["signals"] for s in per_symbol.values())

        agg_metrics["symbols_scanned"] = len(market_data)
        agg_metrics["symbols_with_trades"] = symbols_with_trades
        agg_metrics["profitable_symbols"] = profitable_symbols
        agg_metrics["total_signals"] = total_signals

        # Per-symbol summary (without trades list for JSON brevity)
        symbol_summary = {}
        for sym, info in per_symbol.items():
            symbol_summary[sym] = {
                "signals": info["signals"],
                "metrics": info["metrics"],
            }

        results[strat_name] = {
            "description": strat_info["description"],
            "aggregate": agg_metrics,
            "per_symbol": symbol_summary,
        }
        all_strategy_metrics[strat_name] = agg_metrics

        print(f"\n  AGGREGATE: {agg_metrics['num_trades']} trades | "
              f"WR={agg_metrics['win_rate']*100:.1f}% | "
              f"Ret={agg_metrics['total_return_pct']:+.2f}% | "
              f"PF={agg_metrics['profit_factor']:.2f} | "
              f"MaxDD={agg_metrics['max_drawdown_pct']:.1f}% | "
              f"Sharpe={agg_metrics['sharpe_ratio']:.2f}")
        print(f"  Symbols: {symbols_with_trades}/{len(market_data)} traded | "
              f"{profitable_symbols} profitable")

    # 3. Quality gates
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

    # 4. Build output
    output = {
        "metadata": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
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

    # 5. Save JSON
    json_path = DATA_DIR / "kimi_mutations_backtest.json"
    with open(json_path, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\nSaved JSON: {json_path}")

    # 6. Generate markdown report
    md = generate_report(output, all_strategy_metrics, gate_results, results)
    md_path = DATA_DIR / "kimi_mutations_backtest_report.md"
    with open(md_path, "w") as f:
        f.write(md)
    print(f"Saved report: {md_path}")

    return output


def generate_report(output: dict, metrics: dict, gates: dict, results: dict) -> str:
    """Generate a readable markdown backtest report."""
    ts = output["metadata"]["timestamp"]
    lines = [
        "# KIMI Supplemental Mutations — Backtest Report",
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
            f"- **Symbols Active:** {m.get('symbols_with_trades', 0)} / {m.get('symbols_scanned', 0)}",
            "",
        ])

        # Per-symbol breakdown table
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

    # Quality gates
    lines.extend(["---", "", "## Quality Gates", ""])
    lines.extend([
        "| Strategy | WR>=45% | Sharpe>=0.5 | PF>=1.0 | Trades>=5 | DD<=20% | +E[PnL] | RESULT |",
        "|----------|---------|-------------|---------|-----------|---------|---------|--------|",
    ])
    for name, g in gates.items():
        def _check(v):
            return "Y" if v else "N"
        lines.append(
            f"| {name} | {_check(g['wr_45'])} | {_check(g['sharpe_050'])} | "
            f"{_check(g['pf_100'])} | {_check(g['trades_5'])} | "
            f"{_check(g['maxdd_20'])} | {_check(g['positive_expectancy'])} | "
            f"**{'PASS' if g['PASSED'] else 'FAIL'}** |"
        )

    # Ranking
    lines.extend(["", "---", "", "## Ranking (by Total Return)", ""])
    ranking = output["ranking"]
    for i, r in enumerate(ranking, 1):
        lines.append(f"{i}. **{r['strategy']}** — Ret={r['total_return_pct']:+.2f}% | "
                     f"WR={r['win_rate']*100:.1f}% | Sharpe={r['sharpe_ratio']:.2f}")

    lines.extend(["", "---", f"*Generated {ts}*", ""])
    return "\n".join(lines)


if __name__ == "__main__":
    run_backtest()
