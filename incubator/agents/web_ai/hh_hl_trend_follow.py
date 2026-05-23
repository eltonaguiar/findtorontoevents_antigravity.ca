"""HH HL Trend Follow - Baby Strat #21. Buys on pullback to EMA when making higher highs and higher lows."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str

class HHHLTrendFollowStrategy:
    def __init__(self, p: Optional[dict] = None):
        self.p = p or {}
        self.swing_lb = self.p.get('swing_lookback', 10)
        self.ema_period = self.p.get('ema_period', 20)
        self.atr_period = self.p.get('atr_period', 14)
        self.tp_atr = self.p.get('tp_atr', 2.5)
        self.sl_atr = self.p.get('sl_atr', 1.3)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.swing_lb * 3 + self.ema_period + 10: return []
        ema = data['close'].ewm(span=self.ema_period).mean()
        atr = self._atr(data)
        h, l = data['high'], data['low']
        # Rolling swing highs and lows
        sh1 = h.rolling(self.swing_lb).max().iloc[-1]
        sh2 = h.rolling(self.swing_lb).max().iloc[-1 - self.swing_lb]
        sl1 = l.rolling(self.swing_lb).min().iloc[-1]
        sl2 = l.rolling(self.swing_lb).min().iloc[-1 - self.swing_lb]
        hh = sh1 > sh2; hl = sl1 > sl2
        cp, ce, ca = data['close'].iloc[-1], ema.iloc[-1], atr.iloc[-1]
        near_ema = abs(cp - ce) / ca < 0.5
        if hh and hl and near_ema and cp > ce:
            return [Signal(symbol, "BUY", 0.80, round(cp, 2), round(cp + ca * self.tp_atr, 2), round(cp - ca * self.sl_atr, 2), "HH+HL EMA pullback")]
        return []

    def _atr(self, d):
        tr = pd.concat([d['high']-d['low'], abs(d['high']-d['close'].shift()), abs(d['low']-d['close'].shift())], axis=1).max(axis=1)
        return tr.rolling(self.atr_period).mean()

if __name__ == "__main__":
    np.random.seed(42); n=300; p=50000*np.exp(np.random.normal(0.0002,0.02,n).cumsum())
    d=pd.DataFrame({'open':p,'high':p*1.008,'low':p*0.992,'close':p,'volume':np.random.uniform(100,1000,n)})
    print(f"Signals: {len(HHHLTrendFollowStrategy().generate_signals(d))}")
