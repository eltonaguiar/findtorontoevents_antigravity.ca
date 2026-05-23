"""High Low Midpoint Reversion - #78. Buys when price drops below rolling midpoint then recovers."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional
@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str
class HighLowMidpointReversionStrategy:
    def __init__(self,p=None):
        self.p=p or {};self.lb=self.p.get('lookback',20);self.atr_period=self.p.get('atr_period',14)
        self.tp_atr=self.p.get('tp_atr',2.0);self.sl_atr=self.p.get('sl_atr',1.4)
    def generate_signals(self, data: pd.DataFrame, symbol="BTCUSDT") -> List[Signal]:
        if len(data)<self.lb+10: return []
        hi=data['high'].rolling(self.lb).max();lo=data['low'].rolling(self.lb).min()
        mid=(hi+lo)/2;atr=self._atr(data)
        cp,cm,ca=data['close'].iloc[-1],mid.iloc[-1],atr.iloc[-1]
        pp,pm=data['close'].iloc[-2],mid.iloc[-2]
        if pp<pm and cp>cm:
            return [Signal(symbol,"BUY",0.78,round(cp,2),round(cp+ca*self.tp_atr,2),round(cp-ca*self.sl_atr,2),"Midpoint reclaim")]
        return []
    def _atr(self,d):
        tr=pd.concat([d['high']-d['low'],abs(d['high']-d['close'].shift()),abs(d['low']-d['close'].shift())],axis=1).max(axis=1);return tr.rolling(self.atr_period).mean()
if __name__=="__main__":
    np.random.seed(42);n=300;p=50000*np.exp(np.random.normal(0,0.02,n).cumsum())
    d=pd.DataFrame({'open':p,'high':p*1.006,'low':p*0.994,'close':p,'volume':np.random.uniform(100,1000,n)});print(f"Signals: {len(HighLowMidpointReversionStrategy().generate_signals(d))}")
