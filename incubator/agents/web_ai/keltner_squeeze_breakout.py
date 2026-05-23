"""Keltner Squeeze Breakout - Baby Strat #14. Buys when Keltner channel width contracts to lowest 20% then price breaks upper band."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str

class KeltnerSqueezeBreakoutStrategy:
    def __init__(self, p: Optional[dict] = None):
        self.p = p or {}
        self.ema_period = self.p.get('ema_period', 20)
        self.atr_period = self.p.get('atr_period', 14)
        self.atr_mult = self.p.get('atr_mult', 1.5)
        self.width_lb = self.p.get('width_lookback', 50)
        self.pct_th = self.p.get('pct_threshold', 0.20)
        self.tp_atr = self.p.get('tp_atr', 2.5)
        self.sl_atr = self.p.get('sl_atr', 1.3)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.width_lb + self.ema_period + 10: return []
        ema = data['close'].ewm(span=self.ema_period).mean()
        atr = self._atr(data)
        upper = ema + atr * self.atr_mult
        width = (atr * self.atr_mult * 2) / ema
        width_pct = width.rolling(self.width_lb).rank(pct=True)
        cp, ca = data['close'].iloc[-1], atr.iloc[-1]
        wp = width_pct.iloc[-1] if not pd.isna(width_pct.iloc[-1]) else 0.5
        if wp < self.pct_th and cp > upper.iloc[-1]:
            conf = min(0.75 + (self.pct_th - wp) * 2, 0.93)
            return [Signal(symbol, "BUY", round(conf, 2), round(cp, 2), round(cp + ca * self.tp_atr, 2), round(cp - ca * self.sl_atr, 2), f"KeltSqueeze pct={wp:.2f}")]
        return []

    def _atr(self, d):
        tr = pd.concat([d['high']-d['low'], abs(d['high']-d['close'].shift()), abs(d['low']-d['close'].shift())], axis=1).max(axis=1)
        return tr.rolling(self.atr_period).mean()

if __name__ == "__main__":
    np.random.seed(42); n=300; p=50000*np.exp(np.random.normal(0.0001,0.02,n).cumsum())
    d=pd.DataFrame({'open':p,'high':p*1.005,'low':p*0.995,'close':p,'volume':np.random.uniform(100,1000,n)})
    print(f"Signals: {len(KeltnerSqueezeBreakoutStrategy().generate_signals(d))}")
