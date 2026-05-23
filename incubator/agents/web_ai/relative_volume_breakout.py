"""Relative Volume Breakout - #61. Buys when relative volume (current/avg) > 2.5 with price above prior high."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional
@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str
class RelativeVolumeBreakoutStrategy:
    def __init__(self, p=None):
        self.p=p or {};self.vol_lb=self.p.get('vol_lookback',20);self.rvol_th=self.p.get('rvol_threshold',2.5)
        self.atr_period=self.p.get('atr_period',14);self.tp_atr=self.p.get('tp_atr',2.3);self.sl_atr=self.p.get('sl_atr',1.2)
    def generate_signals(self, data: pd.DataFrame, symbol="BTCUSDT") -> List[Signal]:
        if len(data) < self.vol_lb + 10 or 'volume' not in data: return []
        vol_ma=data['volume'].rolling(self.vol_lb).mean();atr=self._atr(data)
        cv,cvm=data['volume'].iloc[-1],vol_ma.iloc[-1]
        rvol=cv/cvm if cvm>0 else 1.0
        cp,ph,ca=data['close'].iloc[-1],data['high'].iloc[-2],atr.iloc[-1]
        if rvol>self.rvol_th and cp>ph:
            conf=min(0.75+(rvol-self.rvol_th)*0.05,0.92)
            return [Signal(symbol,"BUY",round(conf,2),round(cp,2),round(cp+ca*self.tp_atr,2),round(cp-ca*self.sl_atr,2),f"RVOL={rvol:.1f}x break")]
        return []
    def _atr(self,d):
        tr=pd.concat([d['high']-d['low'],abs(d['high']-d['close'].shift()),abs(d['low']-d['close'].shift())],axis=1).max(axis=1);return tr.rolling(self.atr_period).mean()
if __name__=="__main__":
    np.random.seed(42);n=300;p=50000*np.exp(np.random.normal(0.0002,0.02,n).cumsum())
    d=pd.DataFrame({'open':p,'high':p*1.006,'low':p*0.994,'close':p,'volume':np.random.uniform(100,1000,n)});print(f"Signals: {len(RelativeVolumeBreakoutStrategy().generate_signals(d))}")
