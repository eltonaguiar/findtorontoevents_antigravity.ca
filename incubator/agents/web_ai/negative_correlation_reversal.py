"""Negative Correlation Reversal - #79. Buys when 20-bar return correlation with prior 20-bar returns flips from <-0.5 to >0."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional
@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str
class NegativeCorrelationReversalStrategy:
    def __init__(self,p=None):
        self.p=p or {};self.corr_lb=self.p.get('corr_lookback',20);self.corr_th=self.p.get('corr_threshold',-0.5)
        self.atr_period=self.p.get('atr_period',14);self.tp_atr=self.p.get('tp_atr',2.0);self.sl_atr=self.p.get('sl_atr',1.5)
    def generate_signals(self, data: pd.DataFrame, symbol="BTCUSDT") -> List[Signal]:
        if len(data)<self.corr_lb*3+10: return []
        ret=data['close'].pct_change()
        corr=ret.rolling(self.corr_lb).corr(ret.shift(self.corr_lb))
        atr=self._atr(data);cc,pc=corr.iloc[-1],corr.iloc[-2]
        cp,ca=data['close'].iloc[-1],atr.iloc[-1]
        if not pd.isna(pc) and pc<self.corr_th and cc>0:
            return [Signal(symbol,"BUY",0.80,round(cp,2),round(cp+ca*self.tp_atr,2),round(cp-ca*self.sl_atr,2),f"CorrFlip {pc:.2f}->{cc:.2f}")]
        return []
    def _atr(self,d):
        tr=pd.concat([d['high']-d['low'],abs(d['high']-d['close'].shift()),abs(d['low']-d['close'].shift())],axis=1).max(axis=1);return tr.rolling(self.atr_period).mean()
if __name__=="__main__":
    np.random.seed(42);n=300;p=50000*np.exp(np.random.normal(0,0.02,n).cumsum())
    d=pd.DataFrame({'open':p,'high':p*1.006,'low':p*0.994,'close':p,'volume':np.random.uniform(100,1000,n)});print(f"Signals: {len(NegativeCorrelationReversalStrategy().generate_signals(d))}")
