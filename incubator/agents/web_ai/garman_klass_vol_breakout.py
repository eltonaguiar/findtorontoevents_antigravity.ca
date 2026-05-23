"""
GarmanKlassVolBreakout - Strategy #NEW-1
=========================================
UNIQUE: Uses Garman-Klass volatility estimator (more efficient than close-close)
to detect vol regime shifts. LONG when GK vol drops to 20th pct then price breaks
out upward. SHORT when GK vol drops then price breaks downward.

Works across ALL timeframes (1m to 1W) — uses relative percentile, not absolute values.
"""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float
    take_profit: float; stop_loss: float; reason: str

class GarmanKlassVolBreakoutStrategy:
    def __init__(self, p: Optional[dict] = None):
        self.p = p or {}
        self.gk_period = self.p.get('gk_period', 14)
        self.pct_lb = self.p.get('pct_lookback', 60)
        self.pct_th = self.p.get('pct_threshold', 0.20)
        self.break_lb = self.p.get('breakout_lookback', 10)
        self.atr_period = self.p.get('atr_period', 14)
        self.tp_atr = self.p.get('tp_atr', 2.5)
        self.sl_atr = self.p.get('sl_atr', 1.2)

    def _garman_klass(self, data: pd.DataFrame) -> pd.Series:
        """Garman-Klass volatility: more efficient estimator using OHLC."""
        log_hl = np.log(data['high'] / data['low']) ** 2
        log_co = np.log(data['close'] / data['open']) ** 2 if 'open' in data else 0
        gk = np.sqrt((0.5 * log_hl - (2 * np.log(2) - 1) * log_co).rolling(self.gk_period).mean())
        return gk

    def _atr(self, d):
        tr = pd.concat([d['high']-d['low'], abs(d['high']-d['close'].shift()), abs(d['low']-d['close'].shift())], axis=1).max(axis=1)
        return tr.rolling(self.atr_period).mean()

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.pct_lb + self.gk_period + 10:
            return []

        gk = self._garman_klass(data)
        gk_pct = gk.rolling(self.pct_lb).rank(pct=True)
        atr = self._atr(data)

        hi_break = data['high'].rolling(self.break_lb).max()
        lo_break = data['low'].rolling(self.break_lb).min()

        cp = data['close'].iloc[-1]
        ca = atr.iloc[-1]
        gp = gk_pct.iloc[-1]

        if pd.isna(gp) or pd.isna(ca) or ca <= 0:
            return []

        signals = []

        # LONG: Vol compressed + price breaks above recent highs
        if gp < self.pct_th and cp > hi_break.iloc[-2]:
            conf = min(0.75 + (self.pct_th - gp) * 2, 0.93)
            signals.append(Signal(symbol, "BUY", round(conf, 2), round(cp, 2),
                round(cp + ca * self.tp_atr, 2), round(cp - ca * self.sl_atr, 2),
                f"GK vol pct={gp:.2f} LONG breakout"))

        # SHORT: Vol compressed + price breaks below recent lows
        if gp < self.pct_th and cp < lo_break.iloc[-2]:
            conf = min(0.75 + (self.pct_th - gp) * 2, 0.93)
            signals.append(Signal(symbol, "SELL", round(conf, 2), round(cp, 2),
                round(cp - ca * self.tp_atr, 2), round(cp + ca * self.sl_atr, 2),
                f"GK vol pct={gp:.2f} SHORT breakdown"))

        return signals

if __name__ == "__main__":
    np.random.seed(42); n = 300
    p = 50000 * np.exp(np.random.normal(0.0001, 0.02, n).cumsum())
    d = pd.DataFrame({'open': p * 0.999, 'high': p * 1.008, 'low': p * 0.992,
                       'close': p, 'volume': np.random.uniform(100, 1000, n)})
    s = GarmanKlassVolBreakoutStrategy()
    sigs = s.generate_signals(d)
    print(f"Signals: {len(sigs)} | Directions: {[s.direction for s in sigs]}")
