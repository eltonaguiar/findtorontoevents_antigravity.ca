"""
CrossTimeframeDivergence - Strategy #NEW-13
=============================================
UNIQUE: Compares momentum across 3 synthetic timeframes (fast/medium/slow) within same data.
Detects when short-term diverges from long-term — leading to snap-back or breakout.

LONG: Short TF bearish but medium+long TF bullish → temporary dip in uptrend
SHORT: Short TF bullish but medium+long TF bearish → temporary rally in downtrend
Multi-TF: Creates synthetic TFs from any input data via different lookback windows.
"""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float
    take_profit: float; stop_loss: float; reason: str

class CrossTimeframeDivergenceStrategy:
    def __init__(self, p: Optional[dict] = None):
        self.p = p or {}
        self.fast_lb = self.p.get('fast_lookback', 5)
        self.med_lb = self.p.get('medium_lookback', 15)
        self.slow_lb = self.p.get('slow_lookback', 40)
        self.rsi_period = self.p.get('rsi_period', 14)
        self.atr_period = self.p.get('atr_period', 14)
        self.tp_atr = self.p.get('tp_atr', 2.3)
        self.sl_atr = self.p.get('sl_atr', 1.3)

    def _atr(self, d):
        tr = pd.concat([d['high']-d['low'], abs(d['high']-d['close'].shift()), abs(d['low']-d['close'].shift())], axis=1).max(axis=1)
        return tr.rolling(self.atr_period).mean()

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.slow_lb + 20:
            return []
        # Momentum on 3 synthetic timeframes
        fast_mom = data['close'].pct_change(self.fast_lb).iloc[-1]
        med_mom = data['close'].pct_change(self.med_lb).iloc[-1]
        slow_mom = data['close'].pct_change(self.slow_lb).iloc[-1]
        # EMA slopes
        fast_ema = data['close'].ewm(span=self.fast_lb).mean()
        med_ema = data['close'].ewm(span=self.med_lb).mean()
        slow_ema = data['close'].ewm(span=self.slow_lb).mean()
        atr = self._atr(data)
        cp, ca = data['close'].iloc[-1], atr.iloc[-1]
        if pd.isna(fast_mom) or pd.isna(med_mom) or pd.isna(slow_mom) or pd.isna(ca) or ca <= 0:
            return []
        signals = []
        # Short TF bearish, medium+long bullish → buy the dip
        if fast_mom < -0.005 and med_mom > 0 and slow_mom > 0:
            strength = abs(fast_mom) * 10
            conf = min(0.72 + strength * 0.05, 0.92)
            signals.append(Signal(symbol, "BUY", round(conf, 2), round(cp, 2),
                round(cp + ca * self.tp_atr, 2), round(cp - ca * self.sl_atr, 2),
                f"XTF div F={fast_mom:.3f} M={med_mom:.3f} S={slow_mom:.3f} LONG"))
        # Short TF bullish, medium+long bearish → short the rally
        if fast_mom > 0.005 and med_mom < 0 and slow_mom < 0:
            strength = abs(fast_mom) * 10
            conf = min(0.72 + strength * 0.05, 0.92)
            signals.append(Signal(symbol, "SELL", round(conf, 2), round(cp, 2),
                round(cp - ca * self.tp_atr, 2), round(cp + ca * self.sl_atr, 2),
                f"XTF div F={fast_mom:.3f} M={med_mom:.3f} S={slow_mom:.3f} SHORT"))
        return signals

if __name__ == "__main__":
    np.random.seed(42); n = 300
    p = 50000 * np.exp(np.random.normal(-0.0002, 0.02, n).cumsum())
    d = pd.DataFrame({'open': p * 0.999, 'high': p * 1.006, 'low': p * 0.994,
                       'close': p, 'volume': np.random.uniform(100, 1000, n)})
    print(f"Signals: {len(CrossTimeframeDivergenceStrategy().generate_signals(d))}")
