"""Relative Strength vs MA - #73. Buys when price-to-50SMA ratio hits lowest 15th percentile then recovers."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional
@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str
class RelativeStrengthMAStrategy:
    def __init__(self,p=None):
        self.p=p or {};self.ma_period=self.p.get('ma_period',50);self.pct_lb=self.p.get('pct_lookback',60)
        self.pct_th=self.p.get('pct_threshold',0.15);self.atr_period=self.p.get('atr_period',14)
        self.tp_atr=self.p.get('tp_atr',2.0);self.sl_atr=self.p.get('sl_atr',1.5)
    def generate_signals(self, data: pd.DataFrame, symbol="BTCUSDT") -> List[Signal]:
        if len(data)<self.pct_lb+self.ma_period+10: return []
        ma=data['close'].rolling(self.ma_period).mean();ratio=data['close']/ma
        ratio_pct=ratio.rolling(self.pct_lb).rank(pct=True)
        atr=self._atr(data);rp=ratio_pct.iloc[-1];pr=ratio_pct.iloc[-2]
        cp,ca=data['close'].iloc[-1],atr.iloc[-1]
        if not pd.isna(pr) and pr<self.pct_th and rp>pr:
            conf=min(0.72+(self.pct_th-pr)*2,0.91)
            return [Signal(symbol,"BUY",round(conf,2),round(cp,2),round(cp+ca*self.tp_atr,2),round(cp-ca*self.sl_atr,2),f"RS/MA pct={pr:.2f}")]
        return []
    def _atr(self,d):
        tr=pd.concat([d['high']-d['low'],abs(d['high']-d['close'].shift()),abs(d['low']-d['close'].shift())],axis=1).max(axis=1);return tr.rolling(self.atr_period).mean()
if __name__=="__main__":
    np.random.seed(42);n=300;p=50000*np.exp(np.random.normal(-0.0003,0.02,n).cumsum())
    d=pd.DataFrame({'open':p,'high':p*1.006,'low':p*0.994,'close':p,'volume':np.random.uniform(100,1000,n)});print(f"Signals: {len(RelativeStrengthMAStrategy().generate_signals(d))}")
