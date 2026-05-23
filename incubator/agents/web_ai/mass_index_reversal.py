"""Mass Index Reversal - #91. Buys when mass index (range EMA ratio) exceeds 27 then drops below 26.5."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional
@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str
class MassIndexReversalStrategy:
    def __init__(self,p=None):
        self.p=p or {};self.ema1=self.p.get('ema1',9);self.ema2=self.p.get('ema2',9);self.mi_period=self.p.get('mi_period',25)
        self.atr_period=self.p.get('atr_period',14);self.tp_atr=self.p.get('tp_atr',2.2);self.sl_atr=self.p.get('sl_atr',1.3)
    def generate_signals(self, data: pd.DataFrame, symbol="BTCUSDT") -> List[Signal]:
        if len(data)<self.mi_period+self.ema1+self.ema2+10: return []
        rng=data['high']-data['low'];e1=rng.ewm(span=self.ema1).mean();e2=e1.ewm(span=self.ema2).mean()
        ratio=e1/e2;mi=ratio.rolling(self.mi_period).sum()
        atr=self._atr(data);cm,pm=mi.iloc[-1],mi.iloc[-2]
        cp,ca=data['close'].iloc[-1],atr.iloc[-1]
        if not pd.isna(pm) and pm>27 and cm<26.5:
            return [Signal(symbol,"BUY",0.81,round(cp,2),round(cp+ca*self.tp_atr,2),round(cp-ca*self.sl_atr,2),f"MassIdx reversal={cm:.1f}")]
        return []
    def _atr(self,d):
        tr=pd.concat([d['high']-d['low'],abs(d['high']-d['close'].shift()),abs(d['low']-d['close'].shift())],axis=1).max(axis=1);return tr.rolling(self.atr_period).mean()
if __name__=="__main__":
    np.random.seed(42);n=300;p=50000*np.exp(np.random.normal(0,0.02,n).cumsum())
    d=pd.DataFrame({'open':p,'high':p*1.008,'low':p*0.992,'close':p,'volume':np.random.uniform(100,1000,n)});print(f"Signals: {len(MassIndexReversalStrategy().generate_signals(d))}")
