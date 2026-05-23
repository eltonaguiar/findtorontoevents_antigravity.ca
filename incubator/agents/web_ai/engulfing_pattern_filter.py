"""Engulfing Pattern Filter - #48. Buys on bullish engulfing candle in low-vol ATR regime."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional
@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str
class EngulfingPatternFilterStrategy:
    def __init__(self, p=None):
        self.p=p or {};self.atr_period=self.p.get('atr_period',14);self.regime_lb=self.p.get('regime_lookback',50)
        self.vol_th=self.p.get('vol_threshold',1.1);self.tp_atr=self.p.get('tp_atr',2.2);self.sl_atr=self.p.get('sl_atr',1.3)
    def generate_signals(self, data: pd.DataFrame, symbol="BTCUSDT") -> List[Signal]:
        if len(data) < self.regime_lb + self.atr_period + 5: return []
        atr=self._atr(data);atr_ma=atr.rolling(self.regime_lb).mean()
        ca,cam=atr.iloc[-1],atr_ma.iloc[-1]
        if pd.isna(cam): cam=ca
        low_vol=(ca/cam)<self.vol_th if cam>0 else False
        # Bullish engulfing: prev bearish, curr bullish and covers prev body
        if 'open' in data:
            po,pc=data['open'].iloc[-2],data['close'].iloc[-2]
            co,cc=data['open'].iloc[-1],data['close'].iloc[-1]
            prev_bear=pc<po;curr_bull=cc>co;engulf=cc>po and co<pc
        else:
            prev_bear=data['close'].iloc[-2]<data['close'].iloc[-3]
            curr_bull=data['close'].iloc[-1]>data['close'].iloc[-2]
            engulf=curr_bull and (data['high'].iloc[-1]-data['low'].iloc[-1])>(data['high'].iloc[-2]-data['low'].iloc[-2])
        if low_vol and prev_bear and engulf:
            cp=data['close'].iloc[-1]
            return [Signal(symbol,"BUY",0.83,round(cp,2),round(cp+ca*self.tp_atr,2),round(cp-ca*self.sl_atr,2),"Engulfing+LowVol")]
        return []
    def _atr(self,d):
        tr=pd.concat([d['high']-d['low'],abs(d['high']-d['close'].shift()),abs(d['low']-d['close'].shift())],axis=1).max(axis=1);return tr.rolling(self.atr_period).mean()
if __name__=="__main__":
    np.random.seed(42);n=300;p=50000*np.exp(np.random.normal(0,0.02,n).cumsum())
    d=pd.DataFrame({'open':p*0.999,'high':p*1.008,'low':p*0.992,'close':p,'volume':np.random.uniform(100,1000,n)});print(f"Signals: {len(EngulfingPatternFilterStrategy().generate_signals(d))}")
