"""Retest Support Level - #67. Buys on successful retest of prior support (resistance becomes support)."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional
@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str
class RetestSupportLevelStrategy:
    def __init__(self,p=None):
        self.p=p or {};self.level_lb=self.p.get('level_lookback',30);self.atr_period=self.p.get('atr_period',14)
        self.tp_atr=self.p.get('tp_atr',2.2);self.sl_atr=self.p.get('sl_atr',1.3)
    def generate_signals(self, data: pd.DataFrame, symbol="BTCUSDT") -> List[Signal]:
        if len(data)<self.level_lb+10: return []
        atr=self._atr(data);prior_res=data['high'].iloc[-self.level_lb:-5].max()
        cp,cl,ca=data['close'].iloc[-1],data['low'].iloc[-1],atr.iloc[-1]
        near_level=abs(cl-prior_res)/ca<0.5 if ca>0 else False
        held=cp>prior_res
        if near_level and held:
            return [Signal(symbol,"BUY",0.81,round(cp,2),round(cp+ca*self.tp_atr,2),round(cp-ca*self.sl_atr,2),f"Retest support={prior_res:.0f}")]
        return []
    def _atr(self,d):
        tr=pd.concat([d['high']-d['low'],abs(d['high']-d['close'].shift()),abs(d['low']-d['close'].shift())],axis=1).max(axis=1);return tr.rolling(self.atr_period).mean()
if __name__=="__main__":
    np.random.seed(42);n=300;p=50000*np.exp(np.random.normal(0.0002,0.02,n).cumsum())
    d=pd.DataFrame({'open':p,'high':p*1.008,'low':p*0.992,'close':p,'volume':np.random.uniform(100,1000,n)});print(f"Signals: {len(RetestSupportLevelStrategy().generate_signals(d))}")
