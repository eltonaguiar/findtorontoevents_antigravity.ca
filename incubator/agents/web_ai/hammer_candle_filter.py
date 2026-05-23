"""Hammer Candle Filter - #65. Buys on hammer candle (lower wick > 2x body) in downtrend."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional
@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str
class HammerCandleFilterStrategy:
    def __init__(self,p=None):
        self.p=p or {};self.wick_mult=self.p.get('wick_multiplier',2.0);self.trend_lb=self.p.get('trend_lookback',10)
        self.atr_period=self.p.get('atr_period',14);self.tp_atr=self.p.get('tp_atr',2.0);self.sl_atr=self.p.get('sl_atr',1.3)
    def generate_signals(self, data: pd.DataFrame, symbol="BTCUSDT") -> List[Signal]:
        if len(data)<self.trend_lb+self.atr_period+5: return []
        atr=self._atr(data);cp,co=data['close'].iloc[-1],data['open'].iloc[-1] if 'open' in data else data['close'].iloc[-2]
        ch,cl=data['high'].iloc[-1],data['low'].iloc[-1]
        body=abs(cp-co);lower_wick=min(cp,co)-cl;upper_wick=ch-max(cp,co)
        is_hammer=lower_wick>body*self.wick_mult and upper_wick<body*0.5 and body>0
        downtrend=data['close'].iloc[-1]<data['close'].iloc[-self.trend_lb]
        ca=atr.iloc[-1]
        if is_hammer and downtrend:
            return [Signal(symbol,"BUY",0.80,round(cp,2),round(cp+ca*self.tp_atr,2),round(cp-ca*self.sl_atr,2),"Hammer in downtrend")]
        return []
    def _atr(self,d):
        tr=pd.concat([d['high']-d['low'],abs(d['high']-d['close'].shift()),abs(d['low']-d['close'].shift())],axis=1).max(axis=1);return tr.rolling(self.atr_period).mean()
if __name__=="__main__":
    np.random.seed(42);n=300;p=50000*np.exp(np.random.normal(-0.001,0.02,n).cumsum())
    d=pd.DataFrame({'open':p*0.999,'high':p*1.005,'low':p*0.99,'close':p,'volume':np.random.uniform(100,1000,n)});print(f"Signals: {len(HammerCandleFilterStrategy().generate_signals(d))}")
