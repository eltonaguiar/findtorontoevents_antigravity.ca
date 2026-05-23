"""Range Expansion Alert - #50. Buys when range expands 2x from 10-bar avg after contraction period."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional
@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str
class RangeExpansionAlertStrategy:
    def __init__(self, p=None):
        self.p=p or {};self.rng_lb=self.p.get('range_lookback',10);self.exp_mult=self.p.get('expansion_mult',2.0)
        self.contract_lb=self.p.get('contract_lookback',5);self.atr_period=self.p.get('atr_period',14)
        self.tp_atr=self.p.get('tp_atr',2.5);self.sl_atr=self.p.get('sl_atr',1.2)
    def generate_signals(self, data: pd.DataFrame, symbol="BTCUSDT") -> List[Signal]:
        if len(data) < self.rng_lb + self.contract_lb + 10: return []
        rng=data['high']-data['low'];rng_ma=rng.rolling(self.rng_lb).mean()
        atr=self._atr(data);cr,crm=rng.iloc[-1],rng_ma.iloc[-1]
        cp,ca=data['close'].iloc[-1],atr.iloc[-1]
        # Was contracting (prev bars had small range)
        prev_contracted=all(rng.iloc[-i]<crm for i in range(2,min(self.contract_lb+2,len(rng))))
        expansion=cr>crm*self.exp_mult
        bullish=data['close'].iloc[-1]>data['close'].iloc[-2]
        if prev_contracted and expansion and bullish:
            conf=min(0.75+(cr/crm-self.exp_mult)*0.1,0.92)
            return [Signal(symbol,"BUY",round(conf,2),round(cp,2),round(cp+ca*self.tp_atr,2),round(cp-ca*self.sl_atr,2),f"RangeExp={cr/crm:.1f}x")]
        return []
    def _atr(self,d):
        tr=pd.concat([d['high']-d['low'],abs(d['high']-d['close'].shift()),abs(d['low']-d['close'].shift())],axis=1).max(axis=1);return tr.rolling(self.atr_period).mean()
if __name__=="__main__":
    np.random.seed(42);n=300;p=50000*np.exp(np.random.normal(0.0001,0.02,n).cumsum())
    d=pd.DataFrame({'open':p,'high':p*1.008,'low':p*0.992,'close':p,'volume':np.random.uniform(100,1000,n)});print(f"Signals: {len(RangeExpansionAlertStrategy().generate_signals(d))}")
