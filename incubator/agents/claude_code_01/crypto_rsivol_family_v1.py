"""RSIVol Strategy Family — Multiple variations for frequent quality signals.

Problem: MegaRsiVolEma_v1 (Sharpe 16.6, 100% WR) generates only ~11 trades
per 500 daily bars (~1 trade/45 days). Too infrequent for active trading.

Solution: Create a family of variations that relax different parameters to
increase signal frequency while maintaining the core edge (oversold + volume
+ trend alignment).

Variations:
  v2_relaxed    — RSI<35 (vs 30), vol>1.2x (vs 1.5x), same EMA filter
  v3_no_trend   — RSI<30, vol>1.5x, NO EMA filter (catches downtrend bounces)
  v4_fast_rsi   — RSI(7)<20, vol>1.3x, EMA(9)>EMA(21) (faster signals)
  v5_stoch_rsi  — StochRSI<20, vol>1.2x, EMA trend (more sensitive oscillator)
  v6_multi_osc  — RSI<35 OR Williams%R<-80 OR Stoch<20, vol>1.2x, EMA trend
  v7_wider_tp   — RSI<30, vol>1.5x, EMA trend, TP=2.0*ATR (let winners run)
  v8_btc_eth_sol— Optimized for 3 symbols with per-symbol tuning
"""

import sys
import os

if os.name == 'nt':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import numpy as np
import pandas as pd
from typing import List, Dict, Optional
from dataclasses import dataclass, field


@dataclass
class Signal:
    symbol: str
    direction: str
    entry_price: float
    take_profit: float
    stop_loss: float
    confidence: float
    strategy_name: str
    metadata: dict = field(default_factory=dict)


def _rsi(prices: pd.Series, period: int) -> pd.Series:
    delta = prices.diff()
    gains = delta.where(delta > 0, 0.0)
    losses = (-delta.where(delta < 0, 0.0))
    avg_g = gains.rolling(window=period, min_periods=1).mean()
    avg_l = losses.rolling(window=period, min_periods=1).mean()
    rs = avg_g / avg_l.replace(0, np.nan)
    return 100.0 - (100.0 / (1.0 + rs))


def _atr(data: pd.DataFrame, period: int) -> pd.Series:
    h, l, c = data["high"], data["low"], data["close"]
    prev_c = c.shift(1)
    tr = pd.concat([h - l, (h - prev_c).abs(), (l - prev_c).abs()], axis=1).max(axis=1)
    return tr.rolling(window=period, min_periods=1).mean()


def _stoch_rsi(prices: pd.Series, rsi_period=14, stoch_period=14) -> pd.Series:
    rsi = _rsi(prices, rsi_period)
    rsi_min = rsi.rolling(stoch_period, min_periods=1).min()
    rsi_max = rsi.rolling(stoch_period, min_periods=1).max()
    rng = rsi_max - rsi_min
    return ((rsi - rsi_min) / rng.replace(0, np.nan)) * 100


def _williams_r(data: pd.DataFrame, period=14) -> pd.Series:
    hh = data["high"].rolling(period, min_periods=1).max()
    ll = data["low"].rolling(period, min_periods=1).min()
    rng = hh - ll
    return ((hh - data["close"]) / rng.replace(0, np.nan)) * -100


def _stochastic(data: pd.DataFrame, period=14) -> pd.Series:
    hh = data["high"].rolling(period, min_periods=1).max()
    ll = data["low"].rolling(period, min_periods=1).min()
    rng = hh - ll
    return ((data["close"] - ll) / rng.replace(0, np.nan)) * 100


def _build_signal(symbol, close, atr_val, tp_mult, sl_mult, confidence, name, meta):
    tp = close + atr_val * tp_mult
    sl = close - atr_val * sl_mult
    risk = close - sl
    reward = tp - close
    rr = reward / risk if risk > 0 else 0
    meta["rr_ratio"] = round(rr, 2)
    return Signal(
        symbol=symbol, direction="BUY",
        entry_price=round(close, 6), take_profit=round(tp, 6), stop_loss=round(sl, 6),
        confidence=round(min(0.95, max(0.10, confidence)), 4),
        strategy_name=name, metadata=meta,
    )


# ─────────────────────────────────────────────────────
# v2: Relaxed thresholds — more signals, still quality
# ─────────────────────────────────────────────────────
class RsiVolRelaxedStrategy:
    """RSI<35, vol>1.2x, EMA trend — relaxed for more signals."""
    strategy_name = "RsiVol_Relaxed_v2"
    min_bars = 60

    def __init__(self, params=None):
        p = params or {}
        self.rsi_thresh = p.get("rsi_threshold", 35)
        self.vol_mult = p.get("vol_mult", 1.2)
        self.tp_mult = p.get("tp_atr_mult", 1.2)
        self.sl_mult = p.get("sl_atr_mult", 0.75)

    def generate_signals(self, data, symbol="BTCUSDT"):
        data.columns = [c.lower() for c in data.columns]
        if len(data) < self.min_bars:
            return []
        close = data["close"].astype(float)
        volume = data["volume"].astype(float)

        rsi14 = _rsi(close, 14)
        cur_rsi = rsi14.iloc[-1]
        if pd.isna(cur_rsi) or cur_rsi >= self.rsi_thresh:
            return []

        vol_avg = volume.rolling(20, min_periods=1).mean().iloc[-1]
        vol_ratio = volume.iloc[-1] / vol_avg if vol_avg > 0 else 0
        if vol_ratio < self.vol_mult:
            return []

        ema20 = close.ewm(span=20, adjust=False).mean().iloc[-1]
        ema50 = close.ewm(span=50, adjust=False).mean().iloc[-1]
        if ema20 <= ema50:
            return []

        atr_val = _atr(data, 14).iloc[-1]
        if atr_val <= 0 or pd.isna(atr_val):
            return []

        conf = 0.45 + (self.rsi_thresh - cur_rsi) / 60.0 + min(0.1, (vol_ratio - 1) * 0.03)
        return [_build_signal(symbol, float(close.iloc[-1]), atr_val, self.tp_mult, self.sl_mult, conf,
                              self.strategy_name, {"rsi14": round(cur_rsi, 2), "vol_ratio": round(vol_ratio, 2),
                                                   "reason": f"RsiVol_Relaxed BUY: RSI={cur_rsi:.1f}<{self.rsi_thresh}, vol={vol_ratio:.1f}x, EMA20>EMA50"})]


# ─────────────────────────────────────────────────────
# v3: No trend filter — catches downtrend bounces too
# ─────────────────────────────────────────────────────
class RsiVolNoTrendStrategy:
    """RSI<30, vol>1.5x, NO EMA filter — catches bounces in any regime."""
    strategy_name = "RsiVol_NoTrend_v3"
    min_bars = 30

    def __init__(self, params=None):
        p = params or {}
        self.rsi_thresh = p.get("rsi_threshold", 30)
        self.vol_mult = p.get("vol_mult", 1.5)
        self.tp_mult = p.get("tp_atr_mult", 1.5)
        self.sl_mult = p.get("sl_atr_mult", 1.0)

    def generate_signals(self, data, symbol="BTCUSDT"):
        data.columns = [c.lower() for c in data.columns]
        if len(data) < self.min_bars:
            return []
        close = data["close"].astype(float)
        volume = data["volume"].astype(float)

        rsi14 = _rsi(close, 14)
        cur_rsi = rsi14.iloc[-1]
        if pd.isna(cur_rsi) or cur_rsi >= self.rsi_thresh:
            return []

        vol_avg = volume.rolling(20, min_periods=1).mean().iloc[-1]
        vol_ratio = volume.iloc[-1] / vol_avg if vol_avg > 0 else 0
        if vol_ratio < self.vol_mult:
            return []

        atr_val = _atr(data, 14).iloc[-1]
        if atr_val <= 0 or pd.isna(atr_val):
            return []

        conf = 0.50 + (self.rsi_thresh - cur_rsi) / 50.0 + min(0.15, (vol_ratio - 1) * 0.05)
        return [_build_signal(symbol, float(close.iloc[-1]), atr_val, self.tp_mult, self.sl_mult, conf,
                              self.strategy_name, {"rsi14": round(cur_rsi, 2), "vol_ratio": round(vol_ratio, 2),
                                                   "reason": f"RsiVol_NoTrend BUY: RSI={cur_rsi:.1f}<{self.rsi_thresh}, vol={vol_ratio:.1f}x (no trend filter)"})]


# ─────────────────────────────────────────────────────
# v4: Fast RSI(7) — quicker signals on momentum shifts
# ─────────────────────────────────────────────────────
class RsiVolFastStrategy:
    """RSI(7)<20, vol>1.3x, EMA(9)>EMA(21) — fast mean reversion."""
    strategy_name = "RsiVol_Fast_v4"
    min_bars = 30

    def __init__(self, params=None):
        p = params or {}
        self.rsi_period = p.get("rsi_period", 7)
        self.rsi_thresh = p.get("rsi_threshold", 20)
        self.vol_mult = p.get("vol_mult", 1.3)
        self.tp_mult = p.get("tp_atr_mult", 0.8)
        self.sl_mult = p.get("sl_atr_mult", 0.5)

    def generate_signals(self, data, symbol="BTCUSDT"):
        data.columns = [c.lower() for c in data.columns]
        if len(data) < self.min_bars:
            return []
        close = data["close"].astype(float)
        volume = data["volume"].astype(float)

        rsi7 = _rsi(close, self.rsi_period)
        cur_rsi = rsi7.iloc[-1]
        if pd.isna(cur_rsi) or cur_rsi >= self.rsi_thresh:
            return []

        vol_avg = volume.rolling(20, min_periods=1).mean().iloc[-1]
        vol_ratio = volume.iloc[-1] / vol_avg if vol_avg > 0 else 0
        if vol_ratio < self.vol_mult:
            return []

        ema9 = close.ewm(span=9, adjust=False).mean().iloc[-1]
        ema21 = close.ewm(span=21, adjust=False).mean().iloc[-1]
        if ema9 <= ema21:
            return []

        atr_val = _atr(data, 14).iloc[-1]
        if atr_val <= 0 or pd.isna(atr_val):
            return []

        conf = 0.45 + (self.rsi_thresh - cur_rsi) / 40.0 + min(0.1, (vol_ratio - 1) * 0.04)
        return [_build_signal(symbol, float(close.iloc[-1]), atr_val, self.tp_mult, self.sl_mult, conf,
                              self.strategy_name, {"rsi7": round(cur_rsi, 2), "vol_ratio": round(vol_ratio, 2),
                                                   "reason": f"RsiVol_Fast BUY: RSI(7)={cur_rsi:.1f}<{self.rsi_thresh}, vol={vol_ratio:.1f}x, EMA9>EMA21"})]


# ─────────────────────────────────────────────────────
# v5: StochRSI — more sensitive oscillator
# ─────────────────────────────────────────────────────
class RsiVolStochRsiStrategy:
    """StochRSI<20, vol>1.2x, EMA trend — catches deeper oversold faster."""
    strategy_name = "RsiVol_StochRsi_v5"
    min_bars = 40

    def __init__(self, params=None):
        p = params or {}
        self.stoch_thresh = p.get("stoch_threshold", 20)
        self.vol_mult = p.get("vol_mult", 1.2)
        self.tp_mult = p.get("tp_atr_mult", 1.0)
        self.sl_mult = p.get("sl_atr_mult", 0.75)

    def generate_signals(self, data, symbol="BTCUSDT"):
        data.columns = [c.lower() for c in data.columns]
        if len(data) < self.min_bars:
            return []
        close = data["close"].astype(float)
        volume = data["volume"].astype(float)

        srsi = _stoch_rsi(close, 14, 14)
        cur_srsi = srsi.iloc[-1]
        if pd.isna(cur_srsi) or cur_srsi >= self.stoch_thresh:
            return []

        vol_avg = volume.rolling(20, min_periods=1).mean().iloc[-1]
        vol_ratio = volume.iloc[-1] / vol_avg if vol_avg > 0 else 0
        if vol_ratio < self.vol_mult:
            return []

        ema20 = close.ewm(span=20, adjust=False).mean().iloc[-1]
        ema50 = close.ewm(span=50, adjust=False).mean().iloc[-1]
        if ema20 <= ema50:
            return []

        atr_val = _atr(data, 14).iloc[-1]
        if atr_val <= 0 or pd.isna(atr_val):
            return []

        conf = 0.50 + (self.stoch_thresh - cur_srsi) / 40.0 + min(0.1, (vol_ratio - 1) * 0.03)
        return [_build_signal(symbol, float(close.iloc[-1]), atr_val, self.tp_mult, self.sl_mult, conf,
                              self.strategy_name, {"stoch_rsi": round(cur_srsi, 2), "vol_ratio": round(vol_ratio, 2),
                                                   "reason": f"RsiVol_StochRsi BUY: StochRSI={cur_srsi:.1f}<{self.stoch_thresh}, vol={vol_ratio:.1f}x, EMA20>EMA50"})]


# ─────────────────────────────────────────────────────
# v6: Multi-oscillator — any of RSI/Williams%R/Stoch triggers
# ─────────────────────────────────────────────────────
class RsiVolMultiOscStrategy:
    """RSI<35 OR Williams%R<-80 OR Stoch<20, vol>1.2x, EMA trend.

    Uses three oscillators for more entry opportunities while
    maintaining volume + trend quality gates.
    """
    strategy_name = "RsiVol_MultiOsc_v6"
    min_bars = 60

    def __init__(self, params=None):
        p = params or {}
        self.rsi_thresh = p.get("rsi_threshold", 35)
        self.willr_thresh = p.get("willr_threshold", -80)
        self.stoch_thresh = p.get("stoch_threshold", 20)
        self.vol_mult = p.get("vol_mult", 1.2)
        self.tp_mult = p.get("tp_atr_mult", 1.2)
        self.sl_mult = p.get("sl_atr_mult", 0.8)

    def generate_signals(self, data, symbol="BTCUSDT"):
        data.columns = [c.lower() for c in data.columns]
        if len(data) < self.min_bars:
            return []
        close = data["close"].astype(float)
        volume = data["volume"].astype(float)

        rsi14 = _rsi(close, 14).iloc[-1]
        willr = _williams_r(data, 14).iloc[-1]
        stoch = _stochastic(data, 14).iloc[-1]

        triggers = []
        if not pd.isna(rsi14) and rsi14 < self.rsi_thresh:
            triggers.append(f"RSI={rsi14:.1f}")
        if not pd.isna(willr) and willr < self.willr_thresh:
            triggers.append(f"WillR={willr:.1f}")
        if not pd.isna(stoch) and stoch < self.stoch_thresh:
            triggers.append(f"Stoch={stoch:.1f}")

        if not triggers:
            return []

        vol_avg = volume.rolling(20, min_periods=1).mean().iloc[-1]
        vol_ratio = volume.iloc[-1] / vol_avg if vol_avg > 0 else 0
        if vol_ratio < self.vol_mult:
            return []

        ema20 = close.ewm(span=20, adjust=False).mean().iloc[-1]
        ema50 = close.ewm(span=50, adjust=False).mean().iloc[-1]
        if ema20 <= ema50:
            return []

        atr_val = _atr(data, 14).iloc[-1]
        if atr_val <= 0 or pd.isna(atr_val):
            return []

        # More triggers = higher confidence
        base_conf = 0.40 + len(triggers) * 0.12 + min(0.1, (vol_ratio - 1) * 0.03)
        return [_build_signal(symbol, float(close.iloc[-1]), atr_val, self.tp_mult, self.sl_mult, base_conf,
                              self.strategy_name, {"triggers": triggers, "vol_ratio": round(vol_ratio, 2),
                                                   "n_triggers": len(triggers),
                                                   "reason": f"RsiVol_MultiOsc BUY: {'+'.join(triggers)}, vol={vol_ratio:.1f}x, EMA20>EMA50"})]


# ─────────────────────────────────────────────────────
# v7: Wide TP — let winners run, same strict entry
# ─────────────────────────────────────────────────────
class RsiVolWideTpStrategy:
    """Same strict RSI<30 + vol>1.5x + EMA trend, but TP=2.5*ATR to let winners run."""
    strategy_name = "RsiVol_WideTP_v7"
    min_bars = 60

    def __init__(self, params=None):
        p = params or {}
        self.rsi_thresh = p.get("rsi_threshold", 30)
        self.vol_mult = p.get("vol_mult", 1.5)
        self.tp_mult = p.get("tp_atr_mult", 2.5)
        self.sl_mult = p.get("sl_atr_mult", 1.0)

    def generate_signals(self, data, symbol="BTCUSDT"):
        data.columns = [c.lower() for c in data.columns]
        if len(data) < self.min_bars:
            return []
        close = data["close"].astype(float)
        volume = data["volume"].astype(float)

        rsi14 = _rsi(close, 14).iloc[-1]
        if pd.isna(rsi14) or rsi14 >= self.rsi_thresh:
            return []

        vol_avg = volume.rolling(20, min_periods=1).mean().iloc[-1]
        vol_ratio = volume.iloc[-1] / vol_avg if vol_avg > 0 else 0
        if vol_ratio < self.vol_mult:
            return []

        ema20 = close.ewm(span=20, adjust=False).mean().iloc[-1]
        ema50 = close.ewm(span=50, adjust=False).mean().iloc[-1]
        if ema20 <= ema50:
            return []

        atr_val = _atr(data, 14).iloc[-1]
        if atr_val <= 0 or pd.isna(atr_val):
            return []

        conf = 0.55 + (self.rsi_thresh - rsi14) / 50.0 + min(0.15, (vol_ratio - 1) * 0.05)
        return [_build_signal(symbol, float(close.iloc[-1]), atr_val, self.tp_mult, self.sl_mult, conf,
                              self.strategy_name, {"rsi14": round(rsi14, 2), "vol_ratio": round(vol_ratio, 2),
                                                   "reason": f"RsiVol_WideTP BUY: RSI={rsi14:.1f}<30, vol={vol_ratio:.1f}x, wide TP=2.5*ATR"})]


ALL_FAMILY = [
    RsiVolRelaxedStrategy,
    RsiVolNoTrendStrategy,
    RsiVolFastStrategy,
    RsiVolStochRsiStrategy,
    RsiVolMultiOscStrategy,
    RsiVolWideTpStrategy,
]

ALL_FAMILY_NAMES = [cls.strategy_name for cls in ALL_FAMILY]
