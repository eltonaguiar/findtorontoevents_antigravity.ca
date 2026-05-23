"""
EntropyWeightedMomentum - Strategy #NEW-19
============================================
UNIQUE: Weights momentum signal by inverse Shannon entropy of return distribution.
Low entropy = predictable regime = stronger signal. High entropy = noisy = stand aside.

LONG: Low entropy + positive momentum → confident trend-follow long
SHORT: Low entropy + negative momentum → confident trend-follow short
Multi-TF: Entropy is distribution-based, adapts to any timeframe.
"""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float
    take_profit: float; stop_loss: float; reason: str

class EntropyWeightedMomentumStrategy:
    def __init__(self, p: Optional[dict] = None):
        self.p = p or {}
        self.entropy_lb = self.p.get('entropy_lookback', 40)
        self.n_bins = self.p.get('n_bins', 10)
        self.entropy_th = self.p.get('entropy_threshold', 0.7)  # Normalized 0-1
        self.mom_period = self.p.get('mom_period', 10)
        self.mom_th = self.p.get('mom_threshold', 0.01)
        self.atr_period = self.p.get('atr_period', 14)
        self.tp_atr = self.p.get('tp_atr', 2.5)
        self.sl_atr = self.p.get('sl_atr', 1.2)

    def _shannon_entropy(self, returns: np.ndarray) -> float:
        hist, _ = np.histogram(returns, bins=self.n_bins, density=True)
        hist = hist[hist > 0]
        if len(hist) == 0:
            return 1.0
        probs = hist / hist.sum()
        entropy = -np.sum(probs * np.log2(probs))
        max_entropy = np.log2(self.n_bins)
        return entropy / max_entropy if max_entropy > 0 else 1.0

    def _atr(self, d):
        tr = pd.concat([d['high']-d['low'], abs(d['high']-d['close'].shift()), abs(d['low']-d['close'].shift())], axis=1).max(axis=1)
        return tr.rolling(self.atr_period).mean()

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.entropy_lb + 20:
            return []
        ret = data['close'].pct_change().dropna()
        if len(ret) < self.entropy_lb:
            return []
        entropy = self._shannon_entropy(ret.iloc[-self.entropy_lb:].values)
        mom = data['close'].pct_change(self.mom_period).iloc[-1]
        atr = self._atr(data)
        cp, ca = data['close'].iloc[-1], atr.iloc[-1]
        if pd.isna(mom) or pd.isna(ca) or ca <= 0:
            return []
        signals = []
        if entropy < self.entropy_th:
            inv_entropy = 1.0 - entropy
            if mom > self.mom_th:
                conf = min(0.72 + inv_entropy * 0.2 + mom * 5, 0.93)
                signals.append(Signal(symbol, "BUY", round(conf, 2), round(cp, 2),
                    round(cp + ca * self.tp_atr, 2), round(cp - ca * self.sl_atr, 2),
                    f"Entropy={entropy:.2f} mom={mom:.3f} LONG"))
            elif mom < -self.mom_th:
                conf = min(0.72 + inv_entropy * 0.2 + abs(mom) * 5, 0.93)
                signals.append(Signal(symbol, "SELL", round(conf, 2), round(cp, 2),
                    round(cp - ca * self.tp_atr, 2), round(cp + ca * self.sl_atr, 2),
                    f"Entropy={entropy:.2f} mom={mom:.3f} SHORT"))
        return signals

if __name__ == "__main__":
    np.random.seed(42); n = 300
    p = 50000 * np.exp(np.random.normal(0.0003, 0.02, n).cumsum())
    d = pd.DataFrame({'open': p * 0.999, 'high': p * 1.006, 'low': p * 0.994,
                       'close': p, 'volume': np.random.uniform(100, 1000, n)})
    print(f"Signals: {len(EntropyWeightedMomentumStrategy().generate_signals(d))}")
