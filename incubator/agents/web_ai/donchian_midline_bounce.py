"""Donchian Midline Bounce - #22. Buys pullback to Donchian channel midline in uptrend."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional
@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str

class DonchianMidlineBounceStrategy:
    def __init__(self, p: Optional[dict] = None):
        self.p = p or {}
        self.dc_period = self.p.get('dc_period', 20)
        self.atr_period = self.p.get('atr_period', 14)
        self.tp_atr = self.p.get('tp_atr', 2.3)
        self.sl_atr = self.p.get('sl_atr', 1.3)
    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.dc_period + 20: return []
        dc_hi = data['high'].rolling(self.dc_period).max()
        dc_lo = data['low'].rolling(self.dc_period).min()
        dc_mid = (dc_hi + dc_lo) / 2
        atr = self._atr(data)
        cp, cm, ca = data['close'].iloc[-1], dc_mid.iloc[-1], atr.iloc[-1]
        uptrend = cp > dc_mid.iloc[-5]
        near_mid = abs(cp - cm) < ca * 0.5
        if uptrend and near_mid and cp > cm:
            return [Signal(symbol, "BUY", 0.78, round(cp,2), round(cp+ca*self.tp_atr,2), round(cp-ca*self.sl_atr,2), f"DonchMid bounce")]
        return []
    def _atr(self, d):
        tr = pd.concat([d['high']-d['low'], abs(d['high']-d['close'].shift()), abs(d['low']-d['close'].shift())], axis=1).max(axis=1)
        return tr.rolling(self.atr_period).mean()
if __name__=="__main__":
    np.random.seed(42);n=300;p=50000*np.exp(np.random.normal(0.0002,0.02,n).cumsum())
    d=pd.DataFrame({'open':p,'high':p*1.006,'low':p*0.994,'close':p,'volume':np.random.uniform(100,1000,n)})
    print(f"Signals: {len(DonchianMidlineBounceStrategy().generate_signals(d))}")
