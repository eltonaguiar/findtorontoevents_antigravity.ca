"""Volume Weighted RSI - #68. Buys when volume-weighted RSI < 30 (heavy selling exhaustion)."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional
@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str
class VolumeWeightedRSIStrategy:
    def __init__(self,p=None):
        self.p=p or {};self.rsi_period=self.p.get('rsi_period',14);self.vwrsi_th=self.p.get('vwrsi_threshold',30)
        self.atr_period=self.p.get('atr_period',14);self.tp_atr=self.p.get('tp_atr',2.0);self.sl_atr=self.p.get('sl_atr',1.5)
    def generate_signals(self, data: pd.DataFrame, symbol="BTCUSDT") -> List[Signal]:
        if len(data)<self.rsi_period+10 or 'volume' not in data: return []
        delta=data['close'].diff()*data['volume']
        gain=delta.where(delta>0,0).rolling(self.rsi_period).sum()
        loss=(-delta.where(delta<0,0)).rolling(self.rsi_period).sum()
        rs=gain/loss;vwrsi=100-(100/(1+rs))
        atr=self._atr(data);cv,cp,ca=vwrsi.iloc[-1],data['close'].iloc[-1],atr.iloc[-1]
        if not pd.isna(cv) and cv<self.vwrsi_th:
            conf=min(0.72+(self.vwrsi_th-cv)*0.02,0.92)
            return [Signal(symbol,"BUY",round(conf,2),round(cp,2),round(cp+ca*self.tp_atr,2),round(cp-ca*self.sl_atr,2),f"VWRSI={cv:.0f}")]
        return []
    def _atr(self,d):
        tr=pd.concat([d['high']-d['low'],abs(d['high']-d['close'].shift()),abs(d['low']-d['close'].shift())],axis=1).max(axis=1);return tr.rolling(self.atr_period).mean()
if __name__=="__main__":
    np.random.seed(42);n=300;p=50000*np.exp(np.random.normal(-0.0005,0.025,n).cumsum())
    d=pd.DataFrame({'open':p,'high':p*1.006,'low':p*0.994,'close':p,'volume':np.random.uniform(100,1000,n)});print(f"Signals: {len(VolumeWeightedRSIStrategy().generate_signals(d))}")
