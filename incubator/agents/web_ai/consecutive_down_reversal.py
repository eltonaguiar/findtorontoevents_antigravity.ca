"""Consecutive Down Reversal - #25. Buys after 4+ consecutive down closes followed by first up close."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional
@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str

class ConsecutiveDownReversalStrategy:
    def __init__(self, p: Optional[dict] = None):
        self.p = p or {}
        self.min_down = self.p.get('min_down_bars', 4)
        self.atr_period = self.p.get('atr_period', 14)
        self.tp_atr = self.p.get('tp_atr', 2.0); self.sl_atr = self.p.get('sl_atr', 1.5)
    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.min_down + self.atr_period + 5: return []
        close = data['close']
        atr = self._atr(data)
        # Count consecutive down closes before current bar
        down_count = 0
        for i in range(2, self.min_down + 3):
            if len(close) > i and close.iloc[-i] < close.iloc[-i-1]: down_count += 1
            else: break
        curr_up = close.iloc[-1] > close.iloc[-2]
        if down_count >= self.min_down and curr_up:
            cp, ca = close.iloc[-1], atr.iloc[-1]
            conf = min(0.65 + down_count * 0.05, 0.90)
            return [Signal(symbol, "BUY", round(conf,2), round(cp,2), round(cp+ca*self.tp_atr,2), round(cp-ca*self.sl_atr,2), f"{down_count}DownBars+Reversal")]
        return []
    def _atr(self, d):
        tr=pd.concat([d['high']-d['low'],abs(d['high']-d['close'].shift()),abs(d['low']-d['close'].shift())],axis=1).max(axis=1); return tr.rolling(self.atr_period).mean()
if __name__=="__main__":
    np.random.seed(42);n=300;p=50000*np.exp(np.random.normal(-0.001,0.02,n).cumsum())
    d=pd.DataFrame({'open':p,'high':p*1.006,'low':p*0.994,'close':p,'volume':np.random.uniform(100,1000,n)})
    print(f"Signals: {len(ConsecutiveDownReversalStrategy().generate_signals(d))}")
