"""Connors RSI - #96. Buys when composite RSI (RSI + streak RSI + percentile rank) < 15."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional
@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str
class ConnorsRSIStrategy:
    def __init__(self,p=None):
        self.p=p or {};self.rsi_period=self.p.get('rsi_period',3);self.streak_period=self.p.get('streak_period',2)
        self.pct_lb=self.p.get('pct_lookback',100);self.crsi_th=self.p.get('crsi_threshold',15)
        self.atr_period=self.p.get('atr_period',14);self.tp_atr=self.p.get('tp_atr',2.0);self.sl_atr=self.p.get('sl_atr',1.5)
    def generate_signals(self, data: pd.DataFrame, symbol="BTCUSDT") -> List[Signal]:
        if len(data)<self.pct_lb+20: return []
        rsi=self._rsi(data['close'],self.rsi_period)
        # Streak: consecutive up/down days
        diff=data['close'].diff().apply(lambda x: 1 if x>0 else (-1 if x<0 else 0))
        streak=diff.rolling(5).sum();streak_rsi=self._rsi(streak,self.streak_period)
        # Percentile rank of return
        ret=data['close'].pct_change();pct_rank=ret.rolling(self.pct_lb).rank(pct=True)*100
        crsi=(rsi+streak_rsi+pct_rank)/3;atr=self._atr(data)
        cc,cp,ca=crsi.iloc[-1],data['close'].iloc[-1],atr.iloc[-1]
        if not pd.isna(cc) and cc<self.crsi_th:
            conf=min(0.75+(self.crsi_th-cc)*0.02,0.92)
            return [Signal(symbol,"BUY",round(conf,2),round(cp,2),round(cp+ca*self.tp_atr,2),round(cp-ca*self.sl_atr,2),f"CRSI={cc:.0f}")]
        return []
    def _rsi(self,p,n):
        d=p.diff();g=d.where(d>0,0).rolling(n).mean();l=(-d.where(d<0,0)).rolling(n).mean();return 100-(100/(1+g/l))
    def _atr(self,d):
        tr=pd.concat([d['high']-d['low'],abs(d['high']-d['close'].shift()),abs(d['low']-d['close'].shift())],axis=1).max(axis=1);return tr.rolling(self.atr_period).mean()
if __name__=="__main__":
    np.random.seed(42);n=300;p=50000*np.exp(np.random.normal(-0.0005,0.025,n).cumsum())
    d=pd.DataFrame({'open':p,'high':p*1.006,'low':p*0.994,'close':p,'volume':np.random.uniform(100,1000,n)});print(f"Signals: {len(ConnorsRSIStrategy().generate_signals(d))}")
