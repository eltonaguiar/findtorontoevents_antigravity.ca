"""Bollinger Width Percentile - #33. Buys when BB width at 10th percentile + price near lower band."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional
@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str

class BollingerWidthPercentileStrategy:
    def __init__(self, p: Optional[dict] = None):
        self.p = p or {}
        self.bb_period = self.p.get('bb_period', 20); self.bb_std = self.p.get('bb_std', 2.0)
        self.pct_lb = self.p.get('pct_lookback', 60); self.pct_th = self.p.get('pct_threshold', 0.10)
        self.atr_period = self.p.get('atr_period', 14)
        self.tp_atr = self.p.get('tp_atr', 2.2); self.sl_atr = self.p.get('sl_atr', 1.3)
    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.pct_lb + self.bb_period + 10: return []
        ma = data['close'].rolling(self.bb_period).mean()
        std = data['close'].rolling(self.bb_period).std()
        lower = ma - self.bb_std * std
        width = (self.bb_std * 2 * std) / ma
        wp = width.rolling(self.pct_lb).rank(pct=True)
        atr = self._atr(data)
        cp, lb, ca = data['close'].iloc[-1], lower.iloc[-1], atr.iloc[-1]
        cwp = wp.iloc[-1] if not pd.isna(wp.iloc[-1]) else 0.5
        near_lower = (cp - lb) / ca < 0.5 if ca > 0 else False
        if cwp < self.pct_th and near_lower:
            conf = min(0.75 + (self.pct_th - cwp) * 3, 0.93)
            return [Signal(symbol,"BUY",round(conf,2),round(cp,2),round(cp+ca*self.tp_atr,2),round(cp-ca*self.sl_atr,2),f"BBwidth pct={cwp:.2f}")]
        return []
    def _atr(self, d):
        tr=pd.concat([d['high']-d['low'],abs(d['high']-d['close'].shift()),abs(d['low']-d['close'].shift())],axis=1).max(axis=1);return tr.rolling(self.atr_period).mean()
if __name__=="__main__":
    np.random.seed(42);n=300;p=50000*np.exp(np.random.normal(0,0.02,n).cumsum())
    d=pd.DataFrame({'open':p,'high':p*1.006,'low':p*0.994,'close':p,'volume':np.random.uniform(100,1000,n)})
    print(f"Signals: {len(BollingerWidthPercentileStrategy().generate_signals(d))}")
