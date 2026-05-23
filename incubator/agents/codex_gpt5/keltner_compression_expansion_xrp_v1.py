"""
Keltner Compression Expansion XRP - Baby Strat
"""
import numpy as np
import pandas as pd
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class Signal:
    symbol: str
    direction: str
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str
    position_scale: float = 1.0
    high_volatility_regime: bool = False
    atr_ratio: float = 1.0


class KeltnerCompressionExpansionXRPStrategy:
    TARGET_PAIR = "XRP/USDT"
    TARGET_SYMBOL = "XRPUSDT"

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.ema_period = self.params.get("ema_period", 30)
        self.atr_period = self.params.get("atr_period", 20)
        self.channel_mult = self.params.get("channel_mult", 1.9)
        self.comp_window = self.params.get("comp_window", 80)
        # R:R widened 2026-03-16: was 2.4, now 3.0 (target R:R >= 2.0; was 1.85, now 2.31)
        self.tp_atr_mult = self.params.get("tp_atr_mult", 3.0)
        self.sl_atr_mult = self.params.get("sl_atr_mult", 1.3)
        self.min_bars = 120

    def _hma(self, series: pd.Series, period: int = 21) -> pd.Series:
        """Hull Moving Average -- lag-reduced trend filter."""
        half = max(1, period // 2)
        sqrt_n = max(1, int(period ** 0.5))
        wma_half = series.ewm(span=half, adjust=False).mean()
        wma_full = series.ewm(span=period, adjust=False).mean()
        raw = 2 * wma_half - wma_full
        return raw.ewm(span=sqrt_n, adjust=False).mean()

    def _atr_volatility_gate(self, atr_series: pd.Series, mean_period: int = 30) -> dict:
        """ATR volatility regime gate (v93/v95 crash stress test)."""
        if len(atr_series) < mean_period + 1:
            return {"atr_ratio": 1.0, "high_vol": False, "extreme": False, "scale": 1.0}
        atr_now = float(atr_series.iloc[-1])
        atr_mean = float(atr_series.rolling(mean_period).mean().iloc[-1])
        ratio = atr_now / atr_mean if atr_mean > 0 else 1.0
        extreme = ratio > 3.0
        high_vol = ratio > 2.0
        scale = 0.0 if extreme else (0.5 if high_vol else 1.0)
        return {"atr_ratio": round(ratio, 3), "high_vol": high_vol, "extreme": extreme, "scale": scale}

    def generate_signals(self, data: pd.DataFrame, symbol: str = "XRPUSDT") -> List[Signal]:
        if len(data) < self.min_bars:
            return []
        close, high, low, volume = data["close"], data["high"], data["low"], data["volume"]
        ema = close.ewm(span=self.ema_period, adjust=False).mean()
        atr = self._atr(data, self.atr_period)

        # ── ATR volatility regime gate ──
        vol_gate = self._atr_volatility_gate(atr)
        if vol_gate["extreme"]:
            print(f"    [keltner_compress] {symbol}: SKIP — extreme volatility "
                  f"(ATR ratio {vol_gate['atr_ratio']:.2f}x > 3x mean)")
            return []

        width = self.channel_mult * atr / (ema + 1e-12)
        comp = width.iloc[-2] < width.rolling(self.comp_window).quantile(0.25).iloc[-2]
        upper = ema + self.channel_mult * atr
        lower = ema - self.channel_mult * atr
        edge_buy = max(0.0, (close.iloc[-1] - upper.iloc[-1]) / (atr.iloc[-1] + 1e-12))
        edge_sell = max(0.0, (lower.iloc[-1] - close.iloc[-1]) / (atr.iloc[-1] + 1e-12))
        px = close.iloc[-1]
        a = atr.iloc[-1]
        # HMA trend filter: only trade in direction of trend
        hma_val = self._hma(close, 21)
        hma_rising = hma_val.iloc[-1] > hma_val.iloc[-2]
        signals: List[Signal] = []
        if comp and close.iloc[-1] > upper.iloc[-1] and hma_rising:
            conf = min(0.95, max(0.1, 0.45 + edge_buy * 0.2))
            if vol_gate["high_vol"]:
                conf *= 0.85
                print(f"    [keltner_compress] {symbol}: HIGH VOL regime "
                      f"(ATR {vol_gate['atr_ratio']:.2f}x) — conf reduced, half size")
            sig = self._mk(symbol, "BUY", px, a, conf, "Post-compression upside expansion (HMA trend-aligned)")
            sig.position_scale = vol_gate["scale"]
            sig.high_volatility_regime = vol_gate["high_vol"]
            sig.atr_ratio = vol_gate["atr_ratio"]
            signals.append(sig)
        elif comp and close.iloc[-1] < lower.iloc[-1] and not hma_rising:
            conf = min(0.95, max(0.1, 0.45 + edge_sell * 0.2))
            if vol_gate["high_vol"]:
                conf *= 0.85
                print(f"    [keltner_compress] {symbol}: HIGH VOL regime "
                      f"(ATR {vol_gate['atr_ratio']:.2f}x) — conf reduced, half size")
            sig = self._mk(symbol, "SELL", px, a, conf, "Post-compression downside expansion (HMA trend-aligned)")
            sig.position_scale = vol_gate["scale"]
            sig.high_volatility_regime = vol_gate["high_vol"]
            sig.atr_ratio = vol_gate["atr_ratio"]
            signals.append(sig)
        return signals

    def _mk(self, s: str, d: str, px: float, a: float, conf: float, reason: str) -> Signal:
        tp = px + self.tp_atr_mult * a if d == "BUY" else px - self.tp_atr_mult * a
        sl = px - self.sl_atr_mult * a if d == "BUY" else px + self.sl_atr_mult * a
        return Signal(s, d, round(conf, 3), round(px, 2), round(tp, 2), round(sl, 2), reason)

    def _atr(self, data: pd.DataFrame, p: int) -> pd.Series:
        h, l, c = data["high"], data["low"], data["close"]
        tr = pd.concat([(h - l), (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
        return tr.rolling(p, min_periods=1).mean()
