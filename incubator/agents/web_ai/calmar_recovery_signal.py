"""Calmar Recovery Signal - #31. Buys when rolling Calmar ratio (return/maxDD) recovers above 0.5 after being negative."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional
@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str

class CalmarRecoverySignalStrategy:
    def __init__(self, p: Optional[dict] = None):
        self.p = p or {}
        self.calmar_lb = self.p.get('calmar_lookback', 30)
        self.calmar_th = self.p.get('calmar_threshold', 0.5)
        self.atr_period = self.p.get('atr_period', 14)
        self.tp_atr = self.p.get('tp_atr', 2.0); self.sl_atr = self.p.get('sl_atr', 1.5)
    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.calmar_lb + 20: return []
        close = data['close']
        ret_total = close.pct_change(self.calmar_lb)
        rolling_max = close.rolling(self.calmar_lb).max()
        dd = (close / rolling_max - 1).abs()
        max_dd = dd.rolling(self.calmar_lb).max()
        calmar = ret_total / max_dd
        atr = self._atr(data)
        cc, cp, ca = calmar.iloc[-1], close.iloc[-1], atr.iloc[-1]
        prev_calmar = calmar.iloc[-2] if len(calmar) > 1 else 0
        if not pd.isna(cc) and not pd.isna(prev_calmar) and cc > self.calmar_th and prev_calmar < self.calmar_th:
            conf = min(0.7 + (cc - self.calmar_th) * 0.2, 0.90)
            return [Signal(symbol,"BUY",round(conf,2),round(cp,2),round(cp+ca*self.tp_atr,2),round(cp-ca*self.sl_atr,2),f"Calmar={cc:.2f} crossed")]
        return []
    def _atr(self, d):
        tr=pd.concat([d['high']-d['low'],abs(d['high']-d['close'].shift()),abs(d['low']-d['close'].shift())],axis=1).max(axis=1); return tr.rolling(self.atr_period).mean()
if __name__=="__main__":
    np.random.seed(42);n=300;p=50000*np.exp(np.random.normal(0.0002,0.02,n).cumsum())
    d=pd.DataFrame({'open':p,'high':p*1.006,'low':p*0.994,'close':p,'volume':np.random.uniform(100,1000,n)})
    print(f"Signals: {len(CalmarRecoverySignalStrategy().generate_signals(d))}")
