"""
OmegaRatioGate - Strategy #NEW-17
====================================
UNIQUE: Uses Omega ratio (probability-weighted gains / losses above threshold)
as a quality gate. Only enters when rolling Omega > 1.5 (strong positive asymmetry).

LONG: Omega > 1.5 + RSI pullback to 40-55 range → high-quality pullback buy
SHORT: Omega(inverted) > 1.5 + RSI rally to 45-60 range → high-quality rally short
Multi-TF: Omega ratio is return-distribution-based, scale-invariant.
"""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float
    take_profit: float; stop_loss: float; reason: str

class OmegaRatioGateStrategy:
    def __init__(self, p: Optional[dict] = None):
        self.p = p or {}
        self.omega_lb = self.p.get('omega_lookback', 40)
        self.omega_th = self.p.get('omega_threshold', 1.5)
        self.threshold_ret = self.p.get('threshold_return', 0.0)
        self.rsi_period = self.p.get('rsi_period', 14)
        self.atr_period = self.p.get('atr_period', 14)
        self.tp_atr = self.p.get('tp_atr', 2.5)
        self.sl_atr = self.p.get('sl_atr', 1.2)

    def _omega_ratio(self, returns: pd.Series, threshold: float = 0.0) -> float:
        excess = returns - threshold
        gains = excess[excess > 0].sum()
        losses = abs(excess[excess < 0].sum())
        return gains / losses if losses > 0 else 10.0

    def _rsi(self, p, n):
        d = p.diff(); g = d.where(d > 0, 0).rolling(n).mean(); l = (-d.where(d < 0, 0)).rolling(n).mean()
        return 100 - (100 / (1 + g / l))

    def _atr(self, d):
        tr = pd.concat([d['high']-d['low'], abs(d['high']-d['close'].shift()), abs(d['low']-d['close'].shift())], axis=1).max(axis=1)
        return tr.rolling(self.atr_period).mean()

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.omega_lb + 20:
            return []
        ret = data['close'].pct_change().dropna()
        if len(ret) < self.omega_lb:
            return []
        omega_bull = self._omega_ratio(ret.iloc[-self.omega_lb:], self.threshold_ret)
        omega_bear = self._omega_ratio(-ret.iloc[-self.omega_lb:], self.threshold_ret)
        rsi = self._rsi(data['close'], self.rsi_period)
        atr = self._atr(data)
        cp, cr, ca = data['close'].iloc[-1], rsi.iloc[-1], atr.iloc[-1]
        if pd.isna(cr) or pd.isna(ca) or ca <= 0:
            return []
        signals = []
        if omega_bull > self.omega_th and 40 < cr < 55:
            conf = min(0.72 + (omega_bull - self.omega_th) * 0.1, 0.93)
            signals.append(Signal(symbol, "BUY", round(conf, 2), round(cp, 2),
                round(cp + ca * self.tp_atr, 2), round(cp - ca * self.sl_atr, 2),
                f"Omega={omega_bull:.2f} RSI={cr:.0f} LONG"))
        if omega_bear > self.omega_th and 45 < cr < 60:
            conf = min(0.72 + (omega_bear - self.omega_th) * 0.1, 0.93)
            signals.append(Signal(symbol, "SELL", round(conf, 2), round(cp, 2),
                round(cp - ca * self.tp_atr, 2), round(cp + ca * self.sl_atr, 2),
                f"OmegaBear={omega_bear:.2f} RSI={cr:.0f} SHORT"))
        return signals

if __name__ == "__main__":
    np.random.seed(42); n = 300
    p = 50000 * np.exp(np.random.normal(0.0003, 0.02, n).cumsum())
    d = pd.DataFrame({'open': p * 0.999, 'high': p * 1.006, 'low': p * 0.994,
                       'close': p, 'volume': np.random.uniform(100, 1000, n)})
    print(f"Signals: {len(OmegaRatioGateStrategy().generate_signals(d))}")
