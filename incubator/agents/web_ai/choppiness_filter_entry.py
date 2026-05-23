"""Choppiness Filter Entry - #53. Only buys when choppiness index < 38 (trending) + RSI pullback."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional
@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str
class ChoppinessFilterEntryStrategy:
    def __init__(self, p=None):
        self.p=p or {};self.ci_period=self.p.get('ci_period',14);self.ci_th=self.p.get('ci_threshold',38)
        self.rsi_period=self.p.get('rsi_period',14);self.rsi_lo=self.p.get('rsi_lo',40);self.rsi_hi=self.p.get('rsi_hi',60)
        self.atr_period=self.p.get('atr_period',14);self.tp_atr=self.p.get('tp_atr',2.5);self.sl_atr=self.p.get('sl_atr',1.2)
    def generate_signals(self, data: pd.DataFrame, symbol="BTCUSDT") -> List[Signal]:
        if len(data) < self.ci_period + 20: return []
        atr=self._atr(data)
        hi_n=data['high'].rolling(self.ci_period).max();lo_n=data['low'].rolling(self.ci_period).min()
        atr_sum=atr.rolling(self.ci_period).sum()
        ci=100*np.log10(atr_sum/(hi_n-lo_n).replace(0,np.nan))/np.log10(self.ci_period)
        rsi=self._rsi(data['close'],self.rsi_period)
        cc,cr=ci.iloc[-1],rsi.iloc[-1];cp,ca=data['close'].iloc[-1],atr.iloc[-1]
        if not pd.isna(cc) and cc<self.ci_th and self.rsi_lo<cr<self.rsi_hi:
            return [Signal(symbol,"BUY",0.81,round(cp,2),round(cp+ca*self.tp_atr,2),round(cp-ca*self.sl_atr,2),f"Chop={cc:.0f} RSI={cr:.0f}")]
        return []
    def _rsi(self,p,n):
        d=p.diff();g=d.where(d>0,0).rolling(n).mean();l=(-d.where(d<0,0)).rolling(n).mean();return 100-(100/(1+g/l))
    def _atr(self,d):
        tr=pd.concat([d['high']-d['low'],abs(d['high']-d['close'].shift()),abs(d['low']-d['close'].shift())],axis=1).max(axis=1);return tr.rolling(self.atr_period).mean()
if __name__=="__main__":
    np.random.seed(42);n=300;p=50000*np.exp(np.random.normal(0.0002,0.02,n).cumsum())
    d=pd.DataFrame({'open':p,'high':p*1.008,'low':p*0.992,'close':p,'volume':np.random.uniform(100,1000,n)});print(f"Signals: {len(ChoppinessFilterEntryStrategy().generate_signals(d))}")
