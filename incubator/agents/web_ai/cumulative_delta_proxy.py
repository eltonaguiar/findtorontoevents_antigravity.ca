"""Cumulative Delta Proxy - #51. Buys when cumulative (close-open) flips positive after negative streak."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional
@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str
class CumulativeDeltaProxyStrategy:
    def __init__(self, p=None):
        self.p=p or {};self.delta_lb=self.p.get('delta_lookback',10);self.atr_period=self.p.get('atr_period',14)
        self.tp_atr=self.p.get('tp_atr',2.0);self.sl_atr=self.p.get('sl_atr',1.4)
    def generate_signals(self, data: pd.DataFrame, symbol="BTCUSDT") -> List[Signal]:
        if len(data) < self.delta_lb + self.atr_period + 10: return []
        if 'open' in data: delta=data['close']-data['open']
        else: delta=data['close'].diff()
        cum_delta=delta.rolling(self.delta_lb).sum()
        atr=self._atr(data);cd,pd_=cum_delta.iloc[-1],cum_delta.iloc[-2]
        cp,ca=data['close'].iloc[-1],atr.iloc[-1]
        if not pd.isna(pd_) and pd_<0 and cd>0:
            conf=min(0.72+abs(pd_)/(abs(pd_)+cd)*0.2,0.90)
            return [Signal(symbol,"BUY",round(conf,2),round(cp,2),round(cp+ca*self.tp_atr,2),round(cp-ca*self.sl_atr,2),f"CumDelta flip {pd_:.0f}->{cd:.0f}")]
        return []
    def _atr(self,d):
        tr=pd.concat([d['high']-d['low'],abs(d['high']-d['close'].shift()),abs(d['low']-d['close'].shift())],axis=1).max(axis=1);return tr.rolling(self.atr_period).mean()
if __name__=="__main__":
    np.random.seed(42);n=300;p=50000*np.exp(np.random.normal(0,0.02,n).cumsum())
    d=pd.DataFrame({'open':p*0.999,'high':p*1.006,'low':p*0.994,'close':p,'volume':np.random.uniform(100,1000,n)});print(f"Signals: {len(CumulativeDeltaProxyStrategy().generate_signals(d))}")
