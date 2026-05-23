"""Body Ratio Reversal - Baby Strat #19. Buys when bearish candle body is >80% of range (capitulation) followed by bullish close."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str

class BodyRatioReversalStrategy:
    def __init__(self, p: Optional[dict] = None):
        self.p = p or {}
        self.body_th = self.p.get('body_threshold', 0.80)
        self.atr_period = self.p.get('atr_period', 14)
        self.tp_atr = self.p.get('tp_atr', 2.2)
        self.sl_atr = self.p.get('sl_atr', 1.3)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.atr_period + 10: return []
        atr = self._atr(data)
        # Previous candle: bearish with large body ratio
        prev_range = data['high'].iloc[-2] - data['low'].iloc[-2]
        prev_body = abs(data['close'].iloc[-2] - data['open'].iloc[-2]) if 'open' in data else prev_range * 0.5
        prev_bearish = data['close'].iloc[-2] < data['open'].iloc[-2] if 'open' in data else data['close'].iloc[-2] < data['close'].iloc[-3]
        body_ratio = prev_body / prev_range if prev_range > 0 else 0
        # Current candle: bullish recovery
        curr_bullish = data['close'].iloc[-1] > data['close'].iloc[-2]
        if prev_bearish and body_ratio > self.body_th and curr_bullish:
            cp, ca = data['close'].iloc[-1], atr.iloc[-1]
            conf = min(0.7 + body_ratio * 0.2, 0.90)
            return [Signal(symbol, "BUY", round(conf, 2), round(cp, 2), round(cp + ca * self.tp_atr, 2), round(cp - ca * self.sl_atr, 2), f"BodyRatio={body_ratio:.2f} Reversal")]
        return []

    def _atr(self, d):
        tr = pd.concat([d['high']-d['low'], abs(d['high']-d['close'].shift()), abs(d['low']-d['close'].shift())], axis=1).max(axis=1)
        return tr.rolling(self.atr_period).mean()

if __name__ == "__main__":
    np.random.seed(42); n=300; p=50000*np.exp(np.random.normal(0,0.02,n).cumsum())
    d=pd.DataFrame({'open':p*0.999,'high':p*1.005,'low':p*0.995,'close':p,'volume':np.random.uniform(100,1000,n)})
    print(f"Signals: {len(BodyRatioReversalStrategy().generate_signals(d))}")
