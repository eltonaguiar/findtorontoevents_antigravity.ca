"""
Crypto ADX Pullback Trend Resume - Baby Strat
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


class CryptoADXPullbackTrendResumeStrategy:
    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.ema_fast = self.params.get('ema_fast', 20)
        self.ema_slow = self.params.get('ema_slow', 50)
        self.adx_period = self.params.get('adx_period', 14)
        self.adx_threshold = self.params.get('adx_threshold', 22)
        self.atr_period = self.params.get('atr_period', 14)
        self.tp_atr_mult = self.params.get('tp_atr_mult', 2.2)
        self.sl_atr_mult = self.params.get('sl_atr_mult', 1.3)
        self.min_bars = 90

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.min_bars:
            return []
        close, high, low, volume = data['close'], data['high'], data['low'], data['volume']
        emaf = close.ewm(span=self.ema_fast, adjust=False).mean()
        emas = close.ewm(span=self.ema_slow, adjust=False).mean()
        up = high.diff()
        dn = -low.diff()
        plus_dm = np.where((up > dn) & (up > 0), up, 0.0)
        minus_dm = np.where((dn > up) & (dn > 0), dn, 0.0)
        atr = self._atr(data, self.atr_period)
        plus_di = 100 * pd.Series(plus_dm, index=data.index).rolling(self.adx_period, min_periods=1).mean() / (atr + 1e-12)
        minus_di = 100 * pd.Series(minus_dm, index=data.index).rolling(self.adx_period, min_periods=1).mean() / (atr + 1e-12)
        adx = (100 * (plus_di - minus_di).abs() / (plus_di + minus_di + 1e-12)).rolling(self.adx_period, min_periods=1).mean()
        edge_buy = max(0.0, (adx.iloc[-1] - self.adx_threshold) / 20)
        edge_sell = edge_buy
        px = close.iloc[-1]
        a = atr.iloc[-1]
        signals: List[Signal] = []
        if emaf.iloc[-1] > emas.iloc[-1] and close.iloc[-2] < emaf.iloc[-2] and close.iloc[-1] > emaf.iloc[-1] and adx.iloc[-1] > self.adx_threshold:
            conf = min(0.95, max(0.1, 0.45 + edge_buy * 0.2))
            signals.append(self._mk(symbol, 'BUY', px, a, conf, f"ADX trend pullback long"))
        elif emaf.iloc[-1] < emas.iloc[-1] and close.iloc[-2] > emaf.iloc[-2] and close.iloc[-1] < emaf.iloc[-1] and adx.iloc[-1] > self.adx_threshold:
            conf = min(0.95, max(0.1, 0.45 + edge_sell * 0.2))
            signals.append(self._mk(symbol, 'SELL', px, a, conf, f"ADX trend pullback short"))
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
    s = CryptoADXPullbackTrendResumeStrategy()
    total = 0
    for i in range(160, len(test)):
        total += len(s.generate_signals(test.iloc[:i+1], 'BTCUSDT'))
    print(total)
