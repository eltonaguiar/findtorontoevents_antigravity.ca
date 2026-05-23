"""Trix Zero Cross - #94. Buys when TRIX (triple EMA ROC) crosses above zero."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional
@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str
class TrixZeroCrossStrategy:
    def __init__(self,p=None):
        self.p=p or {};self.trix_period=self.p.get('trix_period',15);self.atr_period=self.p.get('atr_period',14)
        self.tp_atr=self.p.get('tp_atr',2.3);self.sl_atr=self.p.get('sl_atr',1.3)
    def generate_signals(self, data: pd.DataFrame, symbol="BTCUSDT") -> List[Signal]:
        if len(data)<self.trix_period*3+10: return []
        e1=data['close'].ewm(span=self.trix_period).mean()
        e2=e1.ewm(span=self.trix_period).mean();e3=e2.ewm(span=self.trix_period).mean()
        trix=e3.pct_change()*100;atr=self._atr(data)
        ct,pt=trix.iloc[-1],trix.iloc[-2];cp,ca=data['close'].iloc[-1],atr.iloc[-1]
        if not pd.isna(pt) and pt<0 and ct>0:
            return [Signal(symbol,"BUY",0.79,round(cp,2),round(cp+ca*self.tp_atr,2),round(cp-ca*self.sl_atr,2),"TRIX cross 0")]
        return []
    def _atr(self,d):
        tr=pd.concat([d['high']-d['low'],abs(d['high']-d['close'].shift()),abs(d['low']-d['close'].shift())],axis=1).max(axis=1);return tr.rolling(self.atr_period).mean()
if __name__=="__main__":
    np.random.seed(42);n=300;p=50000*np.exp(np.random.normal(0.0001,0.02,n).cumsum())
    d=pd.DataFrame({'open':p,'high':p*1.006,'low':p*0.994,'close':p,'volume':np.random.uniform(100,1000,n)});print(f"Signals: {len(TrixZeroCrossStrategy().generate_signals(d))}")
