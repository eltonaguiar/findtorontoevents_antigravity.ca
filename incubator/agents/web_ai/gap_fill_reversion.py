"""Gap Fill Reversion - Baby Strat #20. Buys when price gaps down >1% from prior close and fills back toward gap."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str

class GapFillReversionStrategy:
    def __init__(self, p: Optional[dict] = None):
        self.p = p or {}
        self.gap_th = self.p.get('gap_threshold', -1.0)
        self.atr_period = self.p.get('atr_period', 14)
        self.tp_atr = self.p.get('tp_atr', 1.8)
        self.sl_atr = self.p.get('sl_atr', 1.2)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.atr_period + 10: return []
        atr = self._atr(data)
        prev_close = data['close'].iloc[-2]
        curr_low = data['low'].iloc[-1]
        curr_close = data['close'].iloc[-1]
        gap_pct = (curr_low / prev_close - 1) * 100
        # Gap down and recovery (close > low, filling the gap)
        recovery = curr_close > curr_low and curr_close > (prev_close + curr_low) / 2
        if gap_pct < self.gap_th and recovery:
            ca = atr.iloc[-1]
            conf = min(0.7 + abs(gap_pct) * 0.05, 0.90)
            return [Signal(symbol, "BUY", round(conf, 2), round(curr_close, 2), round(curr_close + ca * self.tp_atr, 2), round(curr_close - ca * self.sl_atr, 2), f"GapDown={gap_pct:.1f}% Fill")]
        return []

    def _atr(self, d):
        tr = pd.concat([d['high']-d['low'], abs(d['high']-d['close'].shift()), abs(d['low']-d['close'].shift())], axis=1).max(axis=1)
        return tr.rolling(self.atr_period).mean()

if __name__ == "__main__":
    np.random.seed(42); n=300; p=50000*np.exp(np.random.normal(0,0.02,n).cumsum())
    d=pd.DataFrame({'open':p*0.999,'high':p*1.005,'low':p*0.995,'close':p,'volume':np.random.uniform(100,1000,n)})
    print(f"Signals: {len(GapFillReversionStrategy().generate_signals(d))}")
