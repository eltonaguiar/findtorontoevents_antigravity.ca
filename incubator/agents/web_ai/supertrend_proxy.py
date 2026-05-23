"""Supertrend Proxy - #29. Simple supertrend using ATR bands. Buys on flip from below to above."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional
@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str

class SupertrendProxyStrategy:
    def __init__(self, p: Optional[dict] = None):
        self.p = p or {}
        self.atr_period = self.p.get('atr_period', 10)
        self.multiplier = self.p.get('multiplier', 2.0)
        self.tp_atr = self.p.get('tp_atr', 2.5); self.sl_atr = self.p.get('sl_atr', 1.2)
    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.atr_period + 20: return []
        hl2 = (data['high'] + data['low']) / 2
        atr = self._atr(data)
        upper = hl2 + self.multiplier * atr
        lower = hl2 - self.multiplier * atr
        # Simplified supertrend: if close > upper_prev, trend = up
        cp = data['close'].iloc[-1]
        prev_cp = data['close'].iloc[-2]
        curr_lower = lower.iloc[-1]
        prev_upper = upper.iloc[-2]
        ca = atr.iloc[-1]
        # Flip detection: prev close was below upper band, now above
        was_below = prev_cp < prev_upper
        now_above = cp > upper.iloc[-1]
        if was_below and cp > lower.iloc[-1] and cp > prev_cp:
            return [Signal(symbol,"BUY",0.77,round(cp,2),round(cp+ca*self.tp_atr,2),round(cp-ca*self.sl_atr,2),"Supertrend flip UP")]
        return []
    def _atr(self, d):
        tr=pd.concat([d['high']-d['low'],abs(d['high']-d['close'].shift()),abs(d['low']-d['close'].shift())],axis=1).max(axis=1); return tr.rolling(self.atr_period).mean()
if __name__=="__main__":
    np.random.seed(42);n=300;p=50000*np.exp(np.random.normal(0.0001,0.02,n).cumsum())
    d=pd.DataFrame({'open':p,'high':p*1.008,'low':p*0.992,'close':p,'volume':np.random.uniform(100,1000,n)})
    print(f"Signals: {len(SupertrendProxyStrategy().generate_signals(d))}")
