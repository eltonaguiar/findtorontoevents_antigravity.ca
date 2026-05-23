"""Chandelier Exit Reversal - #74. Buys when Chandelier exit (ATR trailing from high) is breached then recovered."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional
@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str
class ChandelierExitReversalStrategy:
    def __init__(self,p=None):
        self.p=p or {};self.ce_period=self.p.get('ce_period',22);self.ce_mult=self.p.get('ce_mult',3.0)
        self.atr_period=self.p.get('atr_period',14);self.tp_atr=self.p.get('tp_atr',2.3);self.sl_atr=self.p.get('sl_atr',1.2)
    def generate_signals(self, data: pd.DataFrame, symbol="BTCUSDT") -> List[Signal]:
        if len(data)<self.ce_period+10: return []
        atr=self._atr(data);hi=data['high'].rolling(self.ce_period).max()
        ce=hi-self.ce_mult*atr
        cp,cc=data['close'].iloc[-1],ce.iloc[-1];pp,pc=data['close'].iloc[-2],ce.iloc[-2]
        ca=atr.iloc[-1]
        if pp<pc and cp>cc:  # Was below chandelier, now above
            return [Signal(symbol,"BUY",0.80,round(cp,2),round(cp+ca*self.tp_atr,2),round(cp-ca*self.sl_atr,2),"Chandelier reclaim")]
        return []
    def _atr(self,d):
        tr=pd.concat([d['high']-d['low'],abs(d['high']-d['close'].shift()),abs(d['low']-d['close'].shift())],axis=1).max(axis=1);return tr.rolling(self.atr_period).mean()
if __name__=="__main__":
    np.random.seed(42);n=300;p=50000*np.exp(np.random.normal(0.0001,0.02,n).cumsum())
    d=pd.DataFrame({'open':p,'high':p*1.008,'low':p*0.992,'close':p,'volume':np.random.uniform(100,1000,n)});print(f"Signals: {len(ChandelierExitReversalStrategy().generate_signals(d))}")
