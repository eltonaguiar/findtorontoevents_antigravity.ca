"""Momentum Divergence RSI - #71. Buys when momentum (10-bar ROC) diverges bullishly from price."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional
@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str
class MomentumDivergenceRSIStrategy:
    def __init__(self,p=None):
        self.p=p or {};self.roc_period=self.p.get('roc_period',10);self.div_lb=self.p.get('div_lookback',15)
        self.rsi_period=self.p.get('rsi_period',14);self.atr_period=self.p.get('atr_period',14)
        self.tp_atr=self.p.get('tp_atr',2.0);self.sl_atr=self.p.get('sl_atr',1.4)
    def generate_signals(self, data: pd.DataFrame, symbol="BTCUSDT") -> List[Signal]:
        if len(data)<self.div_lb+self.roc_period+10: return []
        roc=data['close'].pct_change(self.roc_period)*100
        rsi=self._rsi(data['close'],self.rsi_period);atr=self._atr(data)
        cp,ca=data['close'].iloc[-1],atr.iloc[-1]
        p_now,p_prev=cp,data['close'].iloc[-1-self.div_lb]
        r_now,r_prev=roc.iloc[-1],roc.iloc[-1-self.div_lb]
        cr=rsi.iloc[-1]
        if not pd.isna(r_prev) and p_now<p_prev and r_now>r_prev and cr<45:
            return [Signal(symbol,"BUY",0.82,round(cp,2),round(cp+ca*self.tp_atr,2),round(cp-ca*self.sl_atr,2),f"MomDiv RSI={cr:.0f}")]
        return []
    def _rsi(self,p,n):
        d=p.diff();g=d.where(d>0,0).rolling(n).mean();l=(-d.where(d<0,0)).rolling(n).mean();return 100-(100/(1+g/l))
    def _atr(self,d):
        tr=pd.concat([d['high']-d['low'],abs(d['high']-d['close'].shift()),abs(d['low']-d['close'].shift())],axis=1).max(axis=1);return tr.rolling(self.atr_period).mean()
if __name__=="__main__":
    np.random.seed(42);n=300;p=50000*np.exp(np.random.normal(-0.0003,0.02,n).cumsum())
    d=pd.DataFrame({'open':p,'high':p*1.006,'low':p*0.994,'close':p,'volume':np.random.uniform(100,1000,n)});print(f"Signals: {len(MomentumDivergenceRSIStrategy().generate_signals(d))}")
