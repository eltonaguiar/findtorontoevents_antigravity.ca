"""
InformationRatioMomentum - Strategy #NEW-6
============================================
UNIQUE: Only trades when rolling Information Ratio (excess return / tracking error vs benchmark)
exceeds threshold. Uses self-benchmark (rolling mean) for universal applicability.

LONG: IR > +1.0 + pullback to EMA → quality momentum buy
SHORT: IR < -1.0 + rally to EMA → quality momentum sell
Multi-TF: IR is scale-independent.
"""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float
    take_profit: float; stop_loss: float; reason: str

class InformationRatioMomentumStrategy:
    def __init__(self, p: Optional[dict] = None):
        self.p = p or {}
        self.ir_lb = self.p.get('ir_lookback', 30)
        self.ir_th = self.p.get('ir_threshold', 1.0)
        self.ema_period = self.p.get('ema_period', 10)
        self.atr_period = self.p.get('atr_period', 14)
        self.tp_atr = self.p.get('tp_atr', 2.5)
        self.sl_atr = self.p.get('sl_atr', 1.2)

    def _atr(self, d):
        tr = pd.concat([d['high']-d['low'], abs(d['high']-d['close'].shift()), abs(d['low']-d['close'].shift())], axis=1).max(axis=1)
        return tr.rolling(self.atr_period).mean()

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.ir_lb + 20:
            return []

        ret = data['close'].pct_change()
        # IR = mean(excess return) / std(excess return) * sqrt(annualize)
        ir = ret.rolling(self.ir_lb).mean() / ret.rolling(self.ir_lb).std() * np.sqrt(252)
        ema = data['close'].ewm(span=self.ema_period).mean()
        atr = self._atr(data)

        cp, ce, ca = data['close'].iloc[-1], ema.iloc[-1], atr.iloc[-1]
        cir = ir.iloc[-1]

        if pd.isna(cir) or pd.isna(ca) or ca <= 0:
            return []

        near_ema = abs(cp - ce) / ca < 0.6
        signals = []

        # Positive IR + pullback to EMA → LONG
        if cir > self.ir_th and near_ema and cp > ce:
            conf = min(0.72 + (cir - self.ir_th) * 0.08, 0.93)
            signals.append(Signal(symbol, "BUY", round(conf, 2), round(cp, 2),
                round(cp + ca * self.tp_atr, 2), round(cp - ca * self.sl_atr, 2),
                f"IR={cir:.2f} LONG pullback"))

        # Negative IR + rally to EMA → SHORT
        if cir < -self.ir_th and near_ema and cp < ce:
            conf = min(0.72 + (abs(cir) - self.ir_th) * 0.08, 0.93)
            signals.append(Signal(symbol, "SELL", round(conf, 2), round(cp, 2),
                round(cp - ca * self.tp_atr, 2), round(cp + ca * self.sl_atr, 2),
                f"IR={cir:.2f} SHORT rally"))

        return signals

if __name__ == "__main__":
    np.random.seed(42); n = 300
    p = 50000 * np.exp(np.random.normal(0.0003, 0.02, n).cumsum())
    d = pd.DataFrame({'open': p * 0.999, 'high': p * 1.006, 'low': p * 0.994,
                       'close': p, 'volume': np.random.uniform(100, 1000, n)})
    print(f"Signals: {len(InformationRatioMomentumStrategy().generate_signals(d))}")
