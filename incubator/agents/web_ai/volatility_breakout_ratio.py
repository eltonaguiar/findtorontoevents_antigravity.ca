"""Volatility Breakout Ratio - #76. Buys when close breaks above yesterday high by > 1 ATR."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional
@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str
class VolatilityBreakoutRatioStrategy:
    def __init__(self,p=None):
        self.p=p or {};self.atr_mult=self.p.get('atr_mult',1.0);self.atr_period=self.p.get('atr_period',14)
        self.tp_atr=self.p.get('tp_atr',2.5);self.sl_atr=self.p.get('sl_atr',1.2)
    def generate_signals(self, data: pd.DataFrame, symbol="BTCUSDT") -> List[Signal]:
        if len(data)<self.atr_period+10: return []
        atr=self._atr(data);cp,ph,ca=data['close'].iloc[-1],data['high'].iloc[-2],atr.iloc[-1]
        breakout_dist=(cp-ph)/ca if ca>0 else 0
        if breakout_dist>self.atr_mult:
            conf=min(0.75+breakout_dist*0.05,0.92)
            return [Signal(symbol,"BUY",round(conf,2),round(cp,2),round(cp+ca*self.tp_atr,2),round(cp-ca*self.sl_atr,2),f"VolBreak={breakout_dist:.1f}ATR")]
        return []
    def _atr(self,d):
        tr=pd.concat([d['high']-d['low'],abs(d['high']-d['close'].shift()),abs(d['low']-d['close'].shift())],axis=1).max(axis=1);return tr.rolling(self.atr_period).mean()
if __name__=="__main__":
    np.random.seed(42);n=300;p=50000*np.exp(np.random.normal(0.0002,0.025,n).cumsum())
    d=pd.DataFrame({'open':p,'high':p*1.008,'low':p*0.992,'close':p,'volume':np.random.uniform(100,1000,n)});print(f"Signals: {len(VolatilityBreakoutRatioStrategy().generate_signals(d))}")
