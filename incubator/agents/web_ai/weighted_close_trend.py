"""Weighted Close Trend - #84. Buys when weighted close (H+L+2C)/4 crosses above SMA."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional
@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str
class WeightedCloseTrendStrategy:
    def __init__(self,p=None):
        self.p=p or {};self.sma_period=self.p.get('sma_period',20);self.atr_period=self.p.get('atr_period',14)
        self.tp_atr=self.p.get('tp_atr',2.3);self.sl_atr=self.p.get('sl_atr',1.3)
    def generate_signals(self, data: pd.DataFrame, symbol="BTCUSDT") -> List[Signal]:
        if len(data)<self.sma_period+10: return []
        wc=(data['high']+data['low']+2*data['close'])/4;sma=wc.rolling(self.sma_period).mean()
        atr=self._atr(data);cw,cs=wc.iloc[-1],sma.iloc[-1]
        pw,ps_=wc.iloc[-2],sma.iloc[-2];cp,ca=data['close'].iloc[-1],atr.iloc[-1]
        if pw<ps_ and cw>cs:
            return [Signal(symbol,"BUY",0.78,round(cp,2),round(cp+ca*self.tp_atr,2),round(cp-ca*self.sl_atr,2),"WClose>SMA cross")]
        return []
    def _atr(self,d):
        tr=pd.concat([d['high']-d['low'],abs(d['high']-d['close'].shift()),abs(d['low']-d['close'].shift())],axis=1).max(axis=1);return tr.rolling(self.atr_period).mean()
if __name__=="__main__":
    np.random.seed(42);n=300;p=50000*np.exp(np.random.normal(0.0001,0.02,n).cumsum())
    d=pd.DataFrame({'open':p,'high':p*1.006,'low':p*0.994,'close':p,'volume':np.random.uniform(100,1000,n)});print(f"Signals: {len(WeightedCloseTrendStrategy().generate_signals(d))}")
