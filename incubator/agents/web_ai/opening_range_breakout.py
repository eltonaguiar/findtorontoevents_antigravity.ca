"""Opening Range Breakout - #83. Buys when price breaks above the high of the first 3 bars in a session."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional
@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str
class OpeningRangeBreakoutStrategy:
    def __init__(self,p=None):
        self.p=p or {};self.orb_bars=self.p.get('orb_bars',3);self.atr_period=self.p.get('atr_period',14)
        self.tp_atr=self.p.get('tp_atr',2.5);self.sl_atr=self.p.get('sl_atr',1.2)
    def generate_signals(self, data: pd.DataFrame, symbol="BTCUSDT") -> List[Signal]:
        if len(data)<self.orb_bars+self.atr_period+5: return []
        orb_high=data['high'].iloc[-self.orb_bars-1:-1].max()
        atr=self._atr(data);cp,ca=data['close'].iloc[-1],atr.iloc[-1]
        if cp>orb_high:
            return [Signal(symbol,"BUY",0.78,round(cp,2),round(cp+ca*self.tp_atr,2),round(cp-ca*self.sl_atr,2),f"ORB break>{orb_high:.0f}")]
        return []
    def _atr(self,d):
        tr=pd.concat([d['high']-d['low'],abs(d['high']-d['close'].shift()),abs(d['low']-d['close'].shift())],axis=1).max(axis=1);return tr.rolling(self.atr_period).mean()
if __name__=="__main__":
    np.random.seed(42);n=300;p=50000*np.exp(np.random.normal(0.0002,0.02,n).cumsum())
    d=pd.DataFrame({'open':p,'high':p*1.006,'low':p*0.994,'close':p,'volume':np.random.uniform(100,1000,n)});print(f"Signals: {len(OpeningRangeBreakoutStrategy().generate_signals(d))}")
