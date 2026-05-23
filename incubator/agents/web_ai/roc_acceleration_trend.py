"""ROC Acceleration Trend - Baby Strat #12. Buys when Rate of Change is accelerating (ROC of ROC > 0) in low-vol regime."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str

class ROCAccelerationTrendStrategy:
    def __init__(self, p: Optional[dict] = None):
        self.p = p or {}
        self.roc1 = self.p.get('roc_period', 12)
        self.roc2 = self.p.get('roc2_period', 6)
        self.atr_period = self.p.get('atr_period', 14)
        self.regime_lb = self.p.get('regime_lookback', 50)
        self.vol_th = self.p.get('vol_threshold', 1.1)
        self.tp_atr = self.p.get('tp_atr', 2.2)
        self.sl_atr = self.p.get('sl_atr', 1.4)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.regime_lb + self.roc1 + self.roc2 + 10: return []
        close = data['close']
        roc = close.pct_change(self.roc1) * 100
        roc_accel = roc.diff(self.roc2)
        atr = self._atr(data)
        atr_ma = atr.rolling(self.regime_lb).mean()
        c_atr, c_atr_ma = atr.iloc[-1], atr_ma.iloc[-1]
        if pd.isna(c_atr_ma): c_atr_ma = c_atr
        low_vol = (c_atr / c_atr_ma) < self.vol_th if c_atr_ma > 0 else False
        c_accel = roc_accel.iloc[-1]
        c_roc = roc.iloc[-1]
        if low_vol and c_accel > 0 and c_roc > 0:
            conf = min(0.6 + c_accel / 10 * 0.3, 0.92)
            cp = close.iloc[-1]
            return [Signal(symbol, "BUY", round(conf, 2), round(cp, 2), round(cp + c_atr * self.tp_atr, 2), round(cp - c_atr * self.sl_atr, 2), f"ROCaccel={c_accel:.2f} ROC={c_roc:.1f}")]
        return []

    def _atr(self, d):
        tr = pd.concat([d['high']-d['low'], abs(d['high']-d['close'].shift()), abs(d['low']-d['close'].shift())], axis=1).max(axis=1)
        return tr.rolling(self.atr_period).mean()

if __name__ == "__main__":
    np.random.seed(42); n=300; p=50000*np.exp(np.random.normal(0.0002,0.02,n).cumsum())
    d=pd.DataFrame({'open':p,'high':p*1.005,'low':p*0.995,'close':p,'volume':np.random.uniform(100,1000,n)})
    print(f"Signals: {len(ROCAccelerationTrendStrategy().generate_signals(d))}")
