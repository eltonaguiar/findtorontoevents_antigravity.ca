"""Stochastic Divergence - #42. Buys when price makes lower low but stoch %K makes higher low."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional
@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str
class StochasticDivergenceStrategy:
    def __init__(self, p=None):
        self.p = p or {};self.k_period=self.p.get('k_period',14);self.div_lb=self.p.get('div_lookback',10)
        self.atr_period=self.p.get('atr_period',14);self.tp_atr=self.p.get('tp_atr',2.2);self.sl_atr=self.p.get('sl_atr',1.4)
    def generate_signals(self, data: pd.DataFrame, symbol="BTCUSDT") -> List[Signal]:
        if len(data) < self.k_period + self.div_lb + 10: return []
        lo_n=data['low'].rolling(self.k_period).min();hi_n=data['high'].rolling(self.k_period).max()
        k = (data['close']-lo_n)/(hi_n-lo_n)*100
        atr=self._atr(data);cp,ca=data['close'].iloc[-1],atr.iloc[-1]
        p_low_now=data['low'].iloc[-1];p_low_prev=data['low'].iloc[-1-self.div_lb]
        k_now=k.iloc[-1];k_prev=k.iloc[-1-self.div_lb]
        if not pd.isna(k_prev) and p_low_now<p_low_prev and k_now>k_prev and k_now<30:
            return [Signal(symbol,"BUY",0.82,round(cp,2),round(cp+ca*self.tp_atr,2),round(cp-ca*self.sl_atr,2),f"StochDiv K={k_now:.0f}")]
        return []
    def _atr(self,d):
        tr=pd.concat([d['high']-d['low'],abs(d['high']-d['close'].shift()),abs(d['low']-d['close'].shift())],axis=1).max(axis=1);return tr.rolling(self.atr_period).mean()
if __name__=="__main__":
    np.random.seed(42);n=300;p=50000*np.exp(np.random.normal(-0.0003,0.02,n).cumsum())
    d=pd.DataFrame({'open':p,'high':p*1.008,'low':p*0.992,'close':p,'volume':np.random.uniform(100,1000,n)});print(f"Signals: {len(StochasticDivergenceStrategy().generate_signals(d))}")
