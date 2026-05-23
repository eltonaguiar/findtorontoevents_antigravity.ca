"""
CorrelationBreakdownAlpha - Strategy #NEW-10
=============================================
UNIQUE: Detects when rolling correlation between returns and their own lag
breaks down. In normal markets, lag-1 autocorrelation is near zero.
When it deviates significantly, market microstructure has shifted.

LONG: Autocorrelation goes very negative (mean-reverting) + oversold → buy dip
SHORT: Autocorrelation goes very positive (trending) + overbought → short the crowd
Also detects correlation regime transitions for both directions.
Multi-TF: Autocorrelation is dimensionless, works on any bar size.
"""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float
    take_profit: float; stop_loss: float; reason: str

class CorrelationBreakdownAlphaStrategy:
    def __init__(self, p: Optional[dict] = None):
        self.p = p or {}
        self.ac_lb = self.p.get('ac_lookback', 30)
        self.ac_mr_th = self.p.get('ac_mr_threshold', -0.3)  # Mean-reverting
        self.ac_trend_th = self.p.get('ac_trend_threshold', 0.3)  # Trending
        self.rsi_period = self.p.get('rsi_period', 14)
        self.atr_period = self.p.get('atr_period', 14)
        self.tp_atr = self.p.get('tp_atr', 2.0)
        self.sl_atr = self.p.get('sl_atr', 1.4)

    def _rsi(self, p, n):
        d = p.diff(); g = d.where(d > 0, 0).rolling(n).mean(); l = (-d.where(d < 0, 0)).rolling(n).mean()
        return 100 - (100 / (1 + g / l))

    def _atr(self, d):
        tr = pd.concat([d['high']-d['low'], abs(d['high']-d['close'].shift()), abs(d['low']-d['close'].shift())], axis=1).max(axis=1)
        return tr.rolling(self.atr_period).mean()

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.ac_lb + 20:
            return []

        ret = data['close'].pct_change()
        ac = ret.rolling(self.ac_lb).apply(lambda x: x.autocorr(lag=1), raw=False)
        rsi = self._rsi(data['close'], self.rsi_period)
        atr = self._atr(data)

        cac, cr = ac.iloc[-1], rsi.iloc[-1]
        pac = ac.iloc[-3] if len(ac) > 3 else 0
        cp, ca = data['close'].iloc[-1], atr.iloc[-1]

        if pd.isna(cac) or pd.isna(cr) or pd.isna(ca) or ca <= 0:
            return []

        signals = []

        # Mean-reverting regime (negative AC) + oversold → LONG
        if cac < self.ac_mr_th and cr < 35:
            conf = min(0.72 + abs(cac) * 0.3, 0.92)
            signals.append(Signal(symbol, "BUY", round(conf, 2), round(cp, 2),
                round(cp + ca * self.tp_atr, 2), round(cp - ca * self.sl_atr, 2),
                f"AC={cac:.2f} MR regime RSI={cr:.0f} LONG"))

        # Mean-reverting regime + overbought → SHORT
        if cac < self.ac_mr_th and cr > 65:
            conf = min(0.72 + abs(cac) * 0.3, 0.92)
            signals.append(Signal(symbol, "SELL", round(conf, 2), round(cp, 2),
                round(cp - ca * self.tp_atr, 2), round(cp + ca * self.sl_atr, 2),
                f"AC={cac:.2f} MR regime RSI={cr:.0f} SHORT"))

        # Trending regime (positive AC) with momentum → ride it
        if cac > self.ac_trend_th and cr > 55 and cr < 75:
            conf = min(0.7 + cac * 0.4, 0.90)
            signals.append(Signal(symbol, "BUY", round(conf, 2), round(cp, 2),
                round(cp + ca * self.tp_atr, 2), round(cp - ca * self.sl_atr, 2),
                f"AC={cac:.2f} TREND regime LONG"))

        if cac > self.ac_trend_th and cr < 45 and cr > 25:
            conf = min(0.7 + cac * 0.4, 0.90)
            signals.append(Signal(symbol, "SELL", round(conf, 2), round(cp, 2),
                round(cp - ca * self.tp_atr, 2), round(cp + ca * self.sl_atr, 2),
                f"AC={cac:.2f} TREND regime SHORT"))

        return signals

if __name__ == "__main__":
    np.random.seed(42); n = 300
    p = 50000 * np.exp(np.random.normal(-0.0002, 0.02, n).cumsum())
    d = pd.DataFrame({'open': p * 0.999, 'high': p * 1.006, 'low': p * 0.994,
                       'close': p, 'volume': np.random.uniform(100, 1000, n)})
    print(f"Signals: {len(CorrelationBreakdownAlphaStrategy().generate_signals(d))}")
