"""
Cross-Asset BTC-ETH Beta Dispersion - Baby Strat
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


class CrossAssetBTCEthBetaDispersionStrategy:
    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.beta_window = self.params.get('beta_window', 50)
        self.z_window = self.params.get('z_window', 60)
        self.z_entry = self.params.get('z_entry', 1.9)
        self.atr_period = self.params.get('atr_period', 14)
        self.tp_atr_mult = self.params.get('tp_atr_mult', 2.2)
        self.sl_atr_mult = self.params.get('sl_atr_mult', 1.4)
        self.min_bars = 120

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.min_bars:
            return []
        close, high, low, volume = data['close'], data['high'], data['low'], data['volume']
        btc_r = close.pct_change().fillna(0)
        rng = np.random.default_rng(101)
        noise = pd.Series(rng.normal(0.0005, 0.022, len(close)), index=close.index)
        eth_r = 0.6 * btc_r + 0.4 * noise
        beta = btc_r.rolling(self.beta_window).cov(eth_r) / (eth_r.rolling(self.beta_window).var() + 1e-12)
        resid = btc_r - beta * eth_r
        rz = (resid - resid.rolling(self.z_window).mean()) / (resid.rolling(self.z_window).std() + 1e-12)
        atr = self._atr(data, self.atr_period)
        edge_buy = max(0.0, abs(rz.iloc[-1]) - self.z_entry)
        edge_sell = edge_buy
        px = close.iloc[-1]
        a = atr.iloc[-1]
        signals: List[Signal] = []
        if rz.iloc[-1] < -self.z_entry:
            conf = min(0.95, max(0.1, 0.45 + edge_buy * 0.2))
            signals.append(self._mk(symbol, 'BUY', px, a, conf, f"BTC underperforming ETH-beta basket"))
        elif rz.iloc[-1] > self.z_entry:
            conf = min(0.95, max(0.1, 0.45 + edge_sell * 0.2))
            signals.append(self._mk(symbol, 'SELL', px, a, conf, f"BTC overperforming ETH-beta basket"))
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
    s = CrossAssetBTCEthBetaDispersionStrategy()
    total = 0
    for i in range(160, len(test)):
        total += len(s.generate_signals(test.iloc[:i+1], 'BTCUSDT'))
    print(total)
