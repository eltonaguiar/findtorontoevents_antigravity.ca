"""Skewness Gate - #45. Buys when return skewness flips from negative to positive (sentiment shift)."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional
@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str
class SkewnessGateStrategy:
    def __init__(self, p=None):
        self.p=p or {};self.skew_lb=self.p.get('skew_lookback',30);self.atr_period=self.p.get('atr_period',14)
        self.tp_atr=self.p.get('tp_atr',2.0);self.sl_atr=self.p.get('sl_atr',1.5)
    def generate_signals(self, data: pd.DataFrame, symbol="BTCUSDT") -> List[Signal]:
        if len(data) < self.skew_lb + 20: return []
        ret=data['close'].pct_change();skew=ret.rolling(self.skew_lb).skew()
        atr=self._atr(data);cs,ps=skew.iloc[-1],skew.iloc[-2]
        cp,ca=data['close'].iloc[-1],atr.iloc[-1]
        if not pd.isna(ps) and ps<-0.5 and cs>0:
            conf=min(0.7+abs(ps)*0.1,0.90)
            return [Signal(symbol,"BUY",round(conf,2),round(cp,2),round(cp+ca*self.tp_atr,2),round(cp-ca*self.sl_atr,2),f"Skew flip {ps:.2f}->{cs:.2f}")]
        return []
    def _atr(self,d):
        tr=pd.concat([d['high']-d['low'],abs(d['high']-d['close'].shift()),abs(d['low']-d['close'].shift())],axis=1).max(axis=1);return tr.rolling(self.atr_period).mean()
if __name__=="__main__":
    np.random.seed(42);n=300;p=50000*np.exp(np.random.normal(-0.0003,0.025,n).cumsum())
    d=pd.DataFrame({'open':p,'high':p*1.006,'low':p*0.994,'close':p,'volume':np.random.uniform(100,1000,n)});print(f"Signals: {len(SkewnessGateStrategy().generate_signals(d))}")
