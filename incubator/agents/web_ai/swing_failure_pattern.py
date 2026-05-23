"""Swing Failure Pattern - #62. Buys when price fails to hold below prior swing low (SFP reversal)."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional
@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str
class SwingFailurePatternStrategy:
    def __init__(self,p=None):
        self.p=p or {};self.swing_lb=self.p.get('swing_lookback',15);self.atr_period=self.p.get('atr_period',14)
        self.tp_atr=self.p.get('tp_atr',2.3);self.sl_atr=self.p.get('sl_atr',1.2)
    def generate_signals(self, data: pd.DataFrame, symbol="BTCUSDT") -> List[Signal]:
        if len(data)<self.swing_lb+10: return []
        atr=self._atr(data);prev_swing_lo=data['low'].iloc[-self.swing_lb:-1].min()
        cl,cc,ca=data['low'].iloc[-1],data['close'].iloc[-1],atr.iloc[-1]
        if cl<prev_swing_lo and cc>prev_swing_lo:
            return [Signal(symbol,"BUY",0.83,round(cc,2),round(cc+ca*self.tp_atr,2),round(cc-ca*self.sl_atr,2),"SFP below swing low")]
        return []
    def _atr(self,d):
        tr=pd.concat([d['high']-d['low'],abs(d['high']-d['close'].shift()),abs(d['low']-d['close'].shift())],axis=1).max(axis=1);return tr.rolling(self.atr_period).mean()
if __name__=="__main__":
    np.random.seed(42);n=300;p=50000*np.exp(np.random.normal(0,0.02,n).cumsum())
    d=pd.DataFrame({'open':p,'high':p*1.008,'low':p*0.992,'close':p,'volume':np.random.uniform(100,1000,n)});print(f"Signals: {len(SwingFailurePatternStrategy().generate_signals(d))}")
