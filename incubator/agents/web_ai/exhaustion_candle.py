"""Exhaustion Candle - #44. Buys after 3+ bars trending down with decreasing range (exhaustion pattern)."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional
@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str
class ExhaustionCandleStrategy:
    def __init__(self, p=None):
        self.p=p or {};self.min_bars=self.p.get('min_bars',3);self.atr_period=self.p.get('atr_period',14)
        self.tp_atr=self.p.get('tp_atr',2.0);self.sl_atr=self.p.get('sl_atr',1.3)
    def generate_signals(self, data: pd.DataFrame, symbol="BTCUSDT") -> List[Signal]:
        if len(data) < self.min_bars + self.atr_period + 5: return []
        atr=self._atr(data);rng=data['high']-data['low']
        # Check: last N bars all down with decreasing range
        all_down=all(data['close'].iloc[-i]<data['close'].iloc[-i-1] for i in range(1,self.min_bars+1))
        shrinking=all(rng.iloc[-i]<rng.iloc[-i-1] for i in range(1,self.min_bars))
        curr_up=data['close'].iloc[-1]>data['close'].iloc[-2]
        if all_down and shrinking and curr_up:
            cp,ca=data['close'].iloc[-1],atr.iloc[-1]
            return [Signal(symbol,"BUY",0.79,round(cp,2),round(cp+ca*self.tp_atr,2),round(cp-ca*self.sl_atr,2),"Exhaustion+reversal")]
        return []
    def _atr(self,d):
        tr=pd.concat([d['high']-d['low'],abs(d['high']-d['close'].shift()),abs(d['low']-d['close'].shift())],axis=1).max(axis=1);return tr.rolling(self.atr_period).mean()
if __name__=="__main__":
    np.random.seed(42);n=300;p=50000*np.exp(np.random.normal(-0.001,0.02,n).cumsum())
    d=pd.DataFrame({'open':p,'high':p*1.008,'low':p*0.992,'close':p,'volume':np.random.uniform(100,1000,n)});print(f"Signals: {len(ExhaustionCandleStrategy().generate_signals(d))}")
