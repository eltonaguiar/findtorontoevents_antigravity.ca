"""Dual ATR Regime - #28. Buys when short ATR(7) < long ATR(21) indicating vol compression, plus price above VWAP proxy."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional
@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str

class DualATRRegimeStrategy:
    def __init__(self, p: Optional[dict] = None):
        self.p = p or {}
        self.atr_short = self.p.get('atr_short', 7)
        self.atr_long = self.p.get('atr_long', 21)
        self.ratio_th = self.p.get('ratio_threshold', 0.7)
        self.vwap_lb = self.p.get('vwap_lookback', 20)
        self.tp_atr = self.p.get('tp_atr', 2.2); self.sl_atr = self.p.get('sl_atr', 1.4)
    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.vwap_lb + self.atr_long + 10: return []
        atr_s = self._atr(data, self.atr_short)
        atr_l = self._atr(data, self.atr_long)
        # VWAP proxy: volume-weighted average price
        if 'volume' in data:
            vwap = (data['close'] * data['volume']).rolling(self.vwap_lb).sum() / data['volume'].rolling(self.vwap_lb).sum()
        else:
            vwap = data['close'].rolling(self.vwap_lb).mean()
        cas, cal = atr_s.iloc[-1], atr_l.iloc[-1]
        ratio = cas / cal if cal > 0 else 1.0
        cp, cv = data['close'].iloc[-1], vwap.iloc[-1]
        if ratio < self.ratio_th and cp > cv:
            conf = min(0.72 + (self.ratio_th - ratio) * 0.5, 0.91)
            return [Signal(symbol,"BUY",round(conf,2),round(cp,2),round(cp+cal*self.tp_atr,2),round(cp-cal*self.sl_atr,2),f"DualATR={ratio:.2f} >VWAP")]
        return []
    def _atr(self, d, n):
        tr=pd.concat([d['high']-d['low'],abs(d['high']-d['close'].shift()),abs(d['low']-d['close'].shift())],axis=1).max(axis=1); return tr.rolling(n).mean()
if __name__=="__main__":
    np.random.seed(42);n=300;p=50000*np.exp(np.random.normal(0.0001,0.02,n).cumsum())
    d=pd.DataFrame({'open':p,'high':p*1.006,'low':p*0.994,'close':p,'volume':np.random.uniform(100,1000,n)})
    print(f"Signals: {len(DualATRRegimeStrategy().generate_signals(d))}")
