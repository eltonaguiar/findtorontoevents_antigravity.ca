"""Williams %R Extreme - #66. Buys when Williams %R < -90 (extreme oversold) + ATR contraction."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional
@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str
class WilliamsRExtremeStrategy:
    def __init__(self,p=None):
        self.p=p or {};self.wr_period=self.p.get('wr_period',14);self.wr_th=self.p.get('wr_threshold',-90)
        self.atr_period=self.p.get('atr_period',14);self.regime_lb=self.p.get('regime_lookback',50)
        self.tp_atr=self.p.get('tp_atr',2.0);self.sl_atr=self.p.get('sl_atr',1.5)
    def generate_signals(self, data: pd.DataFrame, symbol="BTCUSDT") -> List[Signal]:
        if len(data)<self.regime_lb+10: return []
        hh=data['high'].rolling(self.wr_period).max();ll=data['low'].rolling(self.wr_period).min()
        wr=(data['close']-hh)/(hh-ll)*100
        atr=self._atr(data);atr_ma=atr.rolling(self.regime_lb).mean()
        cw,ca,cam=wr.iloc[-1],atr.iloc[-1],atr_ma.iloc[-1]
        cp=data['close'].iloc[-1];low_vol=(ca/cam)<1.0 if cam>0 else False
        if not pd.isna(cw) and cw<self.wr_th and low_vol:
            conf=min(0.72+abs(cw+90)*0.02,0.91)
            return [Signal(symbol,"BUY",round(conf,2),round(cp,2),round(cp+ca*self.tp_atr,2),round(cp-ca*self.sl_atr,2),f"WR={cw:.0f} lowVol")]
        return []
    def _atr(self,d):
        tr=pd.concat([d['high']-d['low'],abs(d['high']-d['close'].shift()),abs(d['low']-d['close'].shift())],axis=1).max(axis=1);return tr.rolling(self.atr_period).mean()
if __name__=="__main__":
    np.random.seed(42);n=300;p=50000*np.exp(np.random.normal(-0.0005,0.025,n).cumsum())
    d=pd.DataFrame({'open':p,'high':p*1.008,'low':p*0.992,'close':p,'volume':np.random.uniform(100,1000,n)});print(f"Signals: {len(WilliamsRExtremeStrategy().generate_signals(d))}")
