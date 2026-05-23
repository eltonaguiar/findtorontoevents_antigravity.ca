"""Double Bottom Detector - #70. Buys when price forms W-bottom (two lows within 1 ATR) with higher close."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional
@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str
class DoubleBottomDetectorStrategy:
    def __init__(self,p=None):
        self.p=p or {};self.lb=self.p.get('lookback',20);self.match_atr=self.p.get('match_atr',1.0)
        self.atr_period=self.p.get('atr_period',14);self.tp_atr=self.p.get('tp_atr',2.3);self.sl_atr=self.p.get('sl_atr',1.3)
    def generate_signals(self, data: pd.DataFrame, symbol="BTCUSDT") -> List[Signal]:
        if len(data)<self.lb+10: return []
        atr=self._atr(data);lows=data['low'].iloc[-self.lb:]
        low1_idx=lows.idxmin();low1=lows[low1_idx]
        # Find second low (not adjacent, within ATR distance)
        ca=atr.iloc[-1];cp=data['close'].iloc[-1]
        recent_low=data['low'].iloc[-1]
        dist=abs(recent_low-low1)/ca if ca>0 else 99
        if dist<self.match_atr and cp>data['close'].iloc[-2] and cp>low1:
            return [Signal(symbol,"BUY",0.82,round(cp,2),round(cp+ca*self.tp_atr,2),round(cp-ca*self.sl_atr,2),f"DBL bottom={low1:.0f}")]
        return []
    def _atr(self,d):
        tr=pd.concat([d['high']-d['low'],abs(d['high']-d['close'].shift()),abs(d['low']-d['close'].shift())],axis=1).max(axis=1);return tr.rolling(self.atr_period).mean()
if __name__=="__main__":
    np.random.seed(42);n=300;p=50000*np.exp(np.random.normal(-0.0003,0.02,n).cumsum())
    d=pd.DataFrame({'open':p,'high':p*1.008,'low':p*0.992,'close':p,'volume':np.random.uniform(100,1000,n)});print(f"Signals: {len(DoubleBottomDetectorStrategy().generate_signals(d))}")
