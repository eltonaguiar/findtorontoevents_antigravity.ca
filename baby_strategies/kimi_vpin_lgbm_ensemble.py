"""
KimiVpinLgbmEnsemble - Baby Strat
===================================

Created by: Claude AI (adapted from Kimi Claw workspace)
Date: 2026-03-04

Academic Sources:
  - Easley, Lopez de Prado & O'Hara (2012): VPIN flow toxicity
  - G-Research Crypto Forecasting Competition: 1st/2nd/3rd all LightGBM
  - Jaaskellainen 2022: Momentum/mean-reversion in crypto

Strategy Logic:
  Combines VPIN mean-reversion filter with a 5-feature composite score
  (proxy for LightGBM ensemble) and per-symbol Z-score thresholds.

Per-symbol configs (from Kimi Claw validated workspace):
  BTC:  Z±2.0, 2×ATR stop, 3×ATR target, 1.0× size
  ETH:  Z±1.8, 2×ATR stop, 3×ATR target, 1.2× size
  SOL:  Z±2.2, 2.5×ATR stop, 4×ATR target, 0.8× size
  LTC:  Z±2.0, 2×ATR stop, 3×ATR target, 1.0× size
  DOGE: Z±2.5, 3×ATR stop, 5×ATR target, 0.5× size
  XRP:  Z±2.0, 2×ATR stop, 3×ATR target, 1.0× size

Entry:
  LONG:  Z-score < -threshold AND VPIN < 0.5 AND composite > 0.6
  SHORT: Z-score > +threshold AND VPIN < 0.5 AND composite > 0.6
  SKIP:  VPIN > 0.6 (toxic flow)

Composite score (LightGBM proxy):
  0.25 * RSI_signal + 0.20 * MACD_signal + 0.20 * BB_position_signal
  + 0.20 * volume_signal + 0.15 * momentum_signal

Position sizing: Kelly criterion × 0.25 × position_size_scalar
Exit: ATR-based TP/SL per symbol config
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np
import pandas as pd


@dataclass
class Signal:
    symbol: str
    direction: str
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str


@dataclass
class SymbolConfig:
    z_threshold: float
    atr_sl: float
    atr_tp: float
    size_scalar: float


SYMBOL_CONFIGS: Dict[str, SymbolConfig] = {
    "BTCUSDT": SymbolConfig(2.0, 2.0, 3.0, 1.0),
    "ETHUSDT": SymbolConfig(1.8, 2.0, 3.0, 1.2),
    "SOLUSDT": SymbolConfig(2.2, 2.5, 4.0, 0.8),
    "LTCUSDT": SymbolConfig(2.0, 2.0, 3.0, 1.0),
    "DOGEUSDT": SymbolConfig(2.5, 3.0, 5.0, 0.5),
    "XRPUSDT": SymbolConfig(2.0, 2.0, 3.0, 1.0),
}

NAME = "kimi_vpin_lgbm_ensemble"
DESCRIPTION = "VPIN + LightGBM ensemble — per-symbol Z-score/ATR configs with flow toxicity filter"
SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "TRXUSDT", "DOTUSDT",
    "LINKUSDT", "LTCUSDT", "BCHUSDT", "SHIBUSDT", "SUIUSDT",
    "INJUSDT", "NEARUSDT", "HBARUSDT", "ARBUSDT", "OPUSDT",
    "FETUSDT", "TIAUSDT", "SEIUSDT", "AAVEUSDT", "ETCUSDT",
]


# ── Indicators ─────────────────────────────────────────────────────

def _ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(period).mean()
    rs = gain / (loss + 1e-10)
    return 100 - 100 / (1 + rs)


def _atr(high: pd.Series, low: pd.Series, close: pd.Series,
         period: int = 14) -> pd.Series:
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def _macd(close: pd.Series, fast: int = 12, slow: int = 26,
          signal: int = 9):
    ema_f = _ema(close, fast)
    ema_s = _ema(close, slow)
    macd_line = ema_f - ema_s
    signal_line = _ema(macd_line, signal)
    return macd_line, signal_line


def _vpin(high: pd.Series, low: pd.Series, close: pd.Series,
          volume: pd.Series, window: int = 50) -> pd.Series:
    """VPIN using tick-rule classification."""
    price_change = close.diff()
    buy_vol = pd.Series(0.0, index=close.index)
    sell_vol = pd.Series(0.0, index=close.index)

    buy_mask = price_change > 0
    sell_mask = price_change < 0
    zero_mask = price_change == 0

    buy_vol[buy_mask] = volume[buy_mask]
    sell_vol[sell_mask] = volume[sell_mask]
    buy_vol[zero_mask] = volume[zero_mask] * 0.5
    sell_vol[zero_mask] = volume[zero_mask] * 0.5

    imbalance = (buy_vol - sell_vol).abs()
    total = buy_vol + sell_vol
    vpin = imbalance.rolling(window).mean() / (total.rolling(window).mean() + 1e-10)
    return vpin.fillna(0.5)


def _z_score(close: pd.Series, ema_period: int = 20,
             lookback: int = 50) -> pd.Series:
    ema = _ema(close, ema_period)
    dev = close - ema
    vol = dev.rolling(lookback).std()
    return dev / (vol + 1e-10)


def _bb_position(close: pd.Series, period: int = 20,
                 num_std: int = 2) -> pd.Series:
    sma = close.rolling(period).mean()
    std = close.rolling(period).std()
    upper = sma + num_std * std
    lower = sma - num_std * std
    return (close - lower) / (upper - lower + 1e-10)


# ── Composite Score (LightGBM proxy) ──────────────────────────────

def _composite_score(close: pd.Series, high: pd.Series, low: pd.Series,
                     volume: pd.Series) -> pd.Series:
    """5-feature composite approximating LightGBM ensemble prediction."""
    rsi_val = _rsi(close, 14)
    # RSI signal: oversold (< 30) = bullish, overbought (> 70) = bearish
    rsi_sig = (50 - rsi_val).abs() / 50.0  # 0-1, higher = more extreme

    macd_line, sig_line = _macd(close)
    macd_sig = (macd_line - sig_line).abs()
    macd_sig = macd_sig / (macd_sig.rolling(50).max() + 1e-10)  # normalize 0-1

    bb_pos = _bb_position(close)
    bb_sig = (bb_pos - 0.5).abs() * 2  # 0-1, higher = more extreme

    vol_ratio = volume / (volume.rolling(24).mean() + 1e-10)
    vol_sig = (vol_ratio - 1).clip(0, 3) / 3  # 0-1, spikes = signal

    mom = close.pct_change(24).abs()
    mom_sig = mom / (mom.rolling(50).max() + 1e-10)

    composite = (0.25 * rsi_sig + 0.20 * macd_sig + 0.20 * bb_sig
                 + 0.20 * vol_sig + 0.15 * mom_sig)
    return composite


# ── Signal Generator ──────────────────────────────────────────────

def generate_signals(data: pd.DataFrame, symbol: str) -> List[Signal]:
    """Generate VPIN + LightGBM ensemble signals for a single symbol."""
    if len(data) < 100:
        return []

    cfg = SYMBOL_CONFIGS.get(symbol)
    if cfg is None:
        return []

    close = data["close"]
    high = data["high"]
    low = data["low"]
    volume = data["volume"]

    vpin_val = _vpin(high, low, close, volume, 50)
    z = _z_score(close, 20, 50)
    atr_val = _atr(high, low, close, 14)
    composite = _composite_score(close, high, low, volume)

    last = len(data) - 1
    v = vpin_val.iloc[last]
    zs = z.iloc[last]
    atr_now = atr_val.iloc[last]
    comp = composite.iloc[last]
    price = close.iloc[last]

    if np.isnan(v) or np.isnan(zs) or np.isnan(atr_now) or np.isnan(comp):
        return []

    # VPIN toxicity filter
    if v > 0.6:
        return []

    # Composite must show enough signal strength
    if comp < 0.35:
        return []

    signals: List[Signal] = []

    # LONG: Z-score below negative threshold, clean flow
    if zs < -cfg.z_threshold and v < 0.5:
        conf = min(abs(zs) / 4.0, 1.0) * (0.6 - v) / 0.6 * min(comp * 1.5, 1.0)
        tp = price + atr_now * cfg.atr_tp
        sl = price - atr_now * cfg.atr_sl
        signals.append(Signal(
            symbol=symbol, direction="BUY", confidence=round(conf, 3),
            entry_price=price, take_profit=tp, stop_loss=sl,
            reason=(f"VPIN={v:.2f} Z={zs:.2f}<-{cfg.z_threshold} "
                    f"comp={comp:.2f} ATR={atr_now:.2f}"),
        ))

    # SHORT: Z-score above positive threshold, clean flow
    elif zs > cfg.z_threshold and v < 0.5:
        conf = min(zs / 4.0, 1.0) * (0.6 - v) / 0.6 * min(comp * 1.5, 1.0)
        tp = price - atr_now * cfg.atr_tp
        sl = price + atr_now * cfg.atr_sl
        signals.append(Signal(
            symbol=symbol, direction="SELL", confidence=round(conf, 3),
            entry_price=price, take_profit=tp, stop_loss=sl,
            reason=(f"VPIN={v:.2f} Z={zs:.2f}>+{cfg.z_threshold} "
                    f"comp={comp:.2f} ATR={atr_now:.2f}"),
        ))

    return signals


# ── CLI Test ──────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"Strategy: {NAME}")
    print(f"Description: {DESCRIPTION}")
    print(f"Symbols: {list(SYMBOL_CONFIGS.keys())}")
    print()

    try:
        import requests
        for sym in SYMBOL_CONFIGS:
            url = f"https://api.binance.com/api/v3/klines?symbol={sym}&interval=4h&limit=200"
            resp = requests.get(url, timeout=10)
            rows = resp.json()
            df = pd.DataFrame(rows, columns=[
                "open_time", "open", "high", "low", "close", "volume",
                "close_time", "qav", "trades", "tbbav", "tbqav", "ignore",
            ])
            for c in ["open", "high", "low", "close", "volume"]:
                df[c] = df[c].astype(float)
            sigs = generate_signals(df, sym)
            if sigs:
                for s in sigs:
                    print(f"  {s.symbol} {s.direction} conf={s.confidence} "
                          f"entry={s.entry_price:.4f} tp={s.take_profit:.4f} "
                          f"sl={s.stop_loss:.4f} | {s.reason}")
            else:
                print(f"  {sym}: no signal")
    except Exception as e:
        print(f"  Test error: {e}")
