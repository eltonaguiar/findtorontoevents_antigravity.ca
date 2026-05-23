"""
Crypto Choppiness Regime Switch - Baby Strat
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


class CryptoChoppinessRegimeSwitchStrategy:
    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.lookback = self.params.get('lookback', 28)
        self.trend_chop = self.params.get('trend_chop', 45)
        self.range_chop = self.params.get('range_chop', 60)
        self.atr_period = self.params.get('atr_period', 14)
        self.tp_atr_mult = self.params.get('tp_atr_mult', 2.1)
        self.sl_atr_mult = self.params.get('sl_atr_mult', 1.3)
        self.min_bars = 80

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.min_bars:
            return []
        close, high, low, volume = data['close'], data['high'], data['low'], data['volume']
        atr = self._atr(data, 1)
        tr_sum = atr.rolling(self.lookback).sum()
        hh = high.rolling(self.lookback).max()
        ll = low.rolling(self.lookback).min()
        chop = 100 * np.log10(tr_sum / (hh - ll + 1e-12)) / np.log10(self.lookback)
        h1 = high.rolling(self.lookback).max().shift(1)
        l1 = low.rolling(self.lookback).min().shift(1)
        atr = self._atr(data, self.atr_period)
        edge_buy = max(0.0, (self.trend_chop - chop.iloc[-1]) / 20)
        edge_sell = edge_buy
        px = close.iloc[-1]
        a = atr.iloc[-1]
        signals: List[Signal] = []
        if (chop.iloc[-1] < self.trend_chop and close.iloc[-1] > h1.iloc[-1]) or (chop.iloc[-1] > self.range_chop and close.iloc[-1] < l1.iloc[-1] + 0.25*(h1.iloc[-1]-l1.iloc[-1])):
            conf = min(0.95, max(0.1, 0.45 + edge_buy * 0.2))
            signals.append(self._mk(symbol, 'BUY', px, a, conf, f"Adaptive regime long"))
        elif (chop.iloc[-1] < self.trend_chop and close.iloc[-1] < l1.iloc[-1]) or (chop.iloc[-1] > self.range_chop and close.iloc[-1] > h1.iloc[-1] - 0.25*(h1.iloc[-1]-l1.iloc[-1])):
            conf = min(0.95, max(0.1, 0.45 + edge_sell * 0.2))
            signals.append(self._mk(symbol, 'SELL', px, a, conf, f"Adaptive regime short"))
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
    s = CryptoChoppinessRegimeSwitchStrategy()
    total = 0
    for i in range(160, len(test)):
        total += len(s.generate_signals(test.iloc[:i+1], 'BTCUSDT'))
    print(total)
