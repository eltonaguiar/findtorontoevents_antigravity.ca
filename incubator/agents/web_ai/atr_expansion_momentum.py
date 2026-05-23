"""ATR Expansion Momentum - #59. Buys when ATR expands 1.5x from average with bullish direction."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional
@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str
class ATRExpansionMomentumStrategy:
    def __init__(self, p=None):
        self.p=p or {};self.atr_period=self.p.get('atr_period',14);self.regime_lb=self.p.get('regime_lookback',30)
        self.exp_th=self.p.get('expansion_threshold',1.5);self.tp_atr=self.p.get('tp_atr',2.0);self.sl_atr=self.p.get('sl_atr',1.5)
    def generate_signals(self, data: pd.DataFrame, symbol="BTCUSDT") -> List[Signal]:
        if len(data) < self.regime_lb + self.atr_period + 10: return []
        atr=self._atr(data);atr_ma=atr.rolling(self.regime_lb).mean()
        ca,cam=atr.iloc[-1],atr_ma.iloc[-1]
        cp=data['close'].iloc[-1];bullish=cp>data['close'].iloc[-2]
        ratio=ca/cam if cam>0 else 1.0
        if ratio>self.exp_th and bullish:
            conf=min(0.72+(ratio-self.exp_th)*0.15,0.90)
            return [Signal(symbol,"BUY",round(conf,2),round(cp,2),round(cp+ca*self.tp_atr,2),round(cp-ca*self.sl_atr,2),f"ATRexp={ratio:.1f}x bull")]
        return []
    def _atr(self,d):
        tr=pd.concat([d['high']-d['low'],abs(d['high']-d['close'].shift()),abs(d['low']-d['close'].shift())],axis=1).max(axis=1);return tr.rolling(self.atr_period).mean()
if __name__=="__main__":
    np.random.seed(42);n=300;p=50000*np.exp(np.random.normal(0.0002,0.025,n).cumsum())
    d=pd.DataFrame({'open':p,'high':p*1.01,'low':p*0.99,'close':p,'volume':np.random.uniform(100,1000,n)});print(f"Signals: {len(ATRExpansionMomentumStrategy().generate_signals(d))}")
