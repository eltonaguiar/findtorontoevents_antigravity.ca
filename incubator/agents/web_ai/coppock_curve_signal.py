"""Coppock Curve Signal - #99. Buys when Coppock curve (weighted ROC combo) crosses above zero."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional
@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str
class CoppockCurveSignalStrategy:
    def __init__(self,p=None):
        self.p=p or {};self.roc1=self.p.get('roc1_period',14);self.roc2=self.p.get('roc2_period',11)
        self.wma_period=self.p.get('wma_period',10);self.atr_period=self.p.get('atr_period',14)
        self.tp_atr=self.p.get('tp_atr',2.3);self.sl_atr=self.p.get('sl_atr',1.3)
    def generate_signals(self, data: pd.DataFrame, symbol="BTCUSDT") -> List[Signal]:
        if len(data)<max(self.roc1,self.roc2)+self.wma_period+10: return []
        roc_l=data['close'].pct_change(self.roc1)*100;roc_s=data['close'].pct_change(self.roc2)*100
        combined=roc_l+roc_s
        # Weighted MA
        weights=np.arange(1,self.wma_period+1);coppock=combined.rolling(self.wma_period).apply(lambda x: np.dot(x,weights)/weights.sum(),raw=True)
        atr=self._atr(data);cc,pc=coppock.iloc[-1],coppock.iloc[-2]
        cp,ca=data['close'].iloc[-1],atr.iloc[-1]
        if not pd.isna(pc) and pc<0 and cc>0:
            return [Signal(symbol,"BUY",0.82,round(cp,2),round(cp+ca*self.tp_atr,2),round(cp-ca*self.sl_atr,2),"Coppock cross 0")]
        return []
    def _atr(self,d):
        tr=pd.concat([d['high']-d['low'],abs(d['high']-d['close'].shift()),abs(d['low']-d['close'].shift())],axis=1).max(axis=1);return tr.rolling(self.atr_period).mean()
if __name__=="__main__":
    np.random.seed(42);n=300;p=50000*np.exp(np.random.normal(0.0001,0.02,n).cumsum())
    d=pd.DataFrame({'open':p,'high':p*1.006,'low':p*0.994,'close':p,'volume':np.random.uniform(100,1000,n)});print(f"Signals: {len(CoppockCurveSignalStrategy().generate_signals(d))}")
