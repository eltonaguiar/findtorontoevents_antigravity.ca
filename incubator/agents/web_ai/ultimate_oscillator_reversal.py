"""Ultimate Oscillator Reversal - #100. Buys when Ultimate Oscillator (7/14/28 weighted) < 30 then rises."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional
@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str
class UltimateOscillatorReversalStrategy:
    def __init__(self,p=None):
        self.p=p or {};self.p1=self.p.get('period1',7);self.p2=self.p.get('period2',14);self.p3=self.p.get('period3',28)
        self.uo_th=self.p.get('uo_threshold',30);self.atr_period=self.p.get('atr_period',14)
        self.tp_atr=self.p.get('tp_atr',2.0);self.sl_atr=self.p.get('sl_atr',1.5)
    def generate_signals(self, data: pd.DataFrame, symbol="BTCUSDT") -> List[Signal]:
        if len(data)<self.p3+10: return []
        bp=data['close']-pd.concat([data['low'],data['close'].shift()],axis=1).min(axis=1)
        tr=pd.concat([data['high']-data['low'],abs(data['high']-data['close'].shift()),abs(data['low']-data['close'].shift())],axis=1).max(axis=1)
        avg1=bp.rolling(self.p1).sum()/tr.rolling(self.p1).sum()
        avg2=bp.rolling(self.p2).sum()/tr.rolling(self.p2).sum()
        avg3=bp.rolling(self.p3).sum()/tr.rolling(self.p3).sum()
        uo=100*(4*avg1+2*avg2+avg3)/7
        atr=self._atr(data);cu,pu=uo.iloc[-1],uo.iloc[-2]
        cp,ca=data['close'].iloc[-1],atr.iloc[-1]
        if not pd.isna(pu) and pu<self.uo_th and cu>pu:
            conf=min(0.72+(self.uo_th-pu)*0.02,0.92)
            return [Signal(symbol,"BUY",round(conf,2),round(cp,2),round(cp+ca*self.tp_atr,2),round(cp-ca*self.sl_atr,2),f"UO={cu:.0f} rising")]
        return []
    def _atr(self,d):
        tr=pd.concat([d['high']-d['low'],abs(d['high']-d['close'].shift()),abs(d['low']-d['close'].shift())],axis=1).max(axis=1);return tr.rolling(self.atr_period).mean()
if __name__=="__main__":
    np.random.seed(42);n=300;p=50000*np.exp(np.random.normal(-0.0005,0.025,n).cumsum())
    d=pd.DataFrame({'open':p,'high':p*1.006,'low':p*0.994,'close':p,'volume':np.random.uniform(100,1000,n)});print(f"Signals: {len(UltimateOscillatorReversalStrategy().generate_signals(d))}")
