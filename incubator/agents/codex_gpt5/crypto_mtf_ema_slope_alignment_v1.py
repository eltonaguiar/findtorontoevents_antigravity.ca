"""
Crypto MTF EMA Slope Alignment - Baby Strat
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


class CryptoMTFEMASlopeAlignmentStrategy:
    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.fast = self.params.get('fast', 12)
        self.mid = self.params.get('mid', 48)
        self.slow = self.params.get('slow', 120)
        self.slope_bars = self.params.get('slope_bars', 5)
        self.pullback_mult = self.params.get('pullback_mult', 0.35)
        self.atr_period = self.params.get('atr_period', 14)
        self.tp_atr_mult = self.params.get('tp_atr_mult', 2.1)
        self.sl_atr_mult = self.params.get('sl_atr_mult', 1.2)
        self.min_bars = 140

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.min_bars:
            return []
        close, high, low, volume = data['close'], data['high'], data['low'], data['volume']
        ef = close.ewm(span=self.fast, adjust=False).mean()
        em = close.ewm(span=self.mid, adjust=False).mean()
        es = close.ewm(span=self.slow, adjust=False).mean()
        atr = self._atr(data, self.atr_period)
        sf = ef.iloc[-1] - ef.iloc[-1-self.slope_bars]
        sm = em.iloc[-1] - em.iloc[-1-self.slope_bars]
        ss = es.iloc[-1] - es.iloc[-1-self.slope_bars]
        edge_buy = max(0.0, sf / (atr.iloc[-1] + 1e-12))
        edge_sell = max(0.0, -sf / (atr.iloc[-1] + 1e-12))
        px = close.iloc[-1]
        a = atr.iloc[-1]
        signals: List[Signal] = []
        if ef.iloc[-1] > em.iloc[-1] > es.iloc[-1] and sf > 0 and sm > 0 and ss > 0 and close.iloc[-1] <= ef.iloc[-1] + self.pullback_mult * atr.iloc[-1]:
            conf = min(0.95, max(0.1, 0.45 + edge_buy * 0.2))
            signals.append(self._mk(symbol, 'BUY', px, a, conf, f"MTF EMA aligned long"))
        elif ef.iloc[-1] < em.iloc[-1] < es.iloc[-1] and sf < 0 and sm < 0 and ss < 0 and close.iloc[-1] >= ef.iloc[-1] - self.pullback_mult * atr.iloc[-1]:
            conf = min(0.95, max(0.1, 0.45 + edge_sell * 0.2))
            signals.append(self._mk(symbol, 'SELL', px, a, conf, f"MTF EMA aligned short"))
        return signals

    def _mk(self, s: str, d: str, px: float, a: float, conf: float, reason: str) -> Signal:
        tp = px + self.tp_atr_mult * a if d == 'BUY' else px - self.tp_atr_mult * a
        sl = px - self.sl_atr_mult * a if d == 'BUY' else px + self.sl_atr_mult * a
        return Signal(s, d, round(conf, 3), round(px, 2), round(tp, 2), round(sl, 2), reason)

    def _atr(self, data: pd.DataFrame, p: int) -> pd.Series:
        h, l, c = data['high'], data['low'], data['close']
        tr = pd.concat([(h - l), (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
        return tr.rolling(p, min_periods=1).mean()


if __name__ == '__main__':
    np.random.seed(42)
    n = 320
    returns = np.random.normal(0.0003, 0.02, n)
    prices = 50000 * np.exp(np.cumsum(returns))
    test = pd.DataFrame({
        'open': prices * (1 + np.random.normal(0, 0.001, n)),
        'high': prices * (1 + np.abs(np.random.normal(0, 0.011, n))),
        'low': prices * (1 - np.abs(np.random.normal(0, 0.011, n))),
        'close': prices,
        'volume': np.random.lognormal(7, 0.6, n)
    })
    s = CryptoMTFEMASlopeAlignmentStrategy()
    total = 0
    for i in range(160, len(test)):
        total += len(s.generate_signals(test.iloc[:i+1], 'BTCUSDT'))
    print(total)
