"""Volume Profile POC - #58. Buys when price returns to Point of Control (most traded price level)."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional
@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str
class VolumeProfilePOCStrategy:
    def __init__(self, p=None):
        self.p=p or {};self.vp_lb=self.p.get('vp_lookback',30);self.n_bins=self.p.get('n_bins',20)
        self.atr_period=self.p.get('atr_period',14);self.tp_atr=self.p.get('tp_atr',2.0);self.sl_atr=self.p.get('sl_atr',1.5)
    def generate_signals(self, data: pd.DataFrame, symbol="BTCUSDT") -> List[Signal]:
        if len(data) < self.vp_lb + 10: return []
        recent=data.iloc[-self.vp_lb:]
        prices=recent['close'].values
        if 'volume' in data: weights=recent['volume'].values
        else: weights=np.ones(len(prices))
        bins=np.linspace(prices.min(),prices.max(),self.n_bins+1)
        hist,_=np.histogram(prices,bins=bins,weights=weights)
        poc_idx=hist.argmax();poc=(bins[poc_idx]+bins[poc_idx+1])/2
        atr=self._atr(data);cp,ca=data['close'].iloc[-1],atr.iloc[-1]
        near_poc=abs(cp-poc)/ca<0.5 if ca>0 else False
        came_from_above=data['close'].iloc[-2]>poc
        if near_poc and came_from_above and cp>poc:
            return [Signal(symbol,"BUY",0.79,round(cp,2),round(cp+ca*self.tp_atr,2),round(cp-ca*self.sl_atr,2),f"POC={poc:.0f} bounce")]
        return []
    def _atr(self,d):
        tr=pd.concat([d['high']-d['low'],abs(d['high']-d['close'].shift()),abs(d['low']-d['close'].shift())],axis=1).max(axis=1);return tr.rolling(self.atr_period).mean()
if __name__=="__main__":
    np.random.seed(42);n=300;p=50000*np.exp(np.random.normal(0,0.02,n).cumsum())
    d=pd.DataFrame({'open':p,'high':p*1.006,'low':p*0.994,'close':p,'volume':np.random.uniform(100,1000,n)});print(f"Signals: {len(VolumeProfilePOCStrategy().generate_signals(d))}")
