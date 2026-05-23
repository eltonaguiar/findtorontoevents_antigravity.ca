"""Range Contraction Revert - Baby Strat #15. Buys when daily range (H-L) contracts to 20th percentile and close near range low."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str

class RangeContractionRevertStrategy:
    def __init__(self, p: Optional[dict] = None):
        self.p = p or {}
        self.range_lb = self.p.get('range_lookback', 50)
        self.pct_th = self.p.get('pct_threshold', 0.20)
        self.close_pos_th = self.p.get('close_pos_threshold', 0.30)
        self.atr_period = self.p.get('atr_period', 14)
        self.tp_atr = self.p.get('tp_atr', 2.0)
        self.sl_atr = self.p.get('sl_atr', 1.3)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.range_lb + 10: return []
        rng = data['high'] - data['low']
        rng_pct = rng.rolling(self.range_lb).rank(pct=True)
        atr = self._atr(data)
        cp, ch, cl, ca = data['close'].iloc[-1], data['high'].iloc[-1], data['low'].iloc[-1], atr.iloc[-1]
        rp = rng_pct.iloc[-1] if not pd.isna(rng_pct.iloc[-1]) else 0.5
        r = ch - cl
        cpos = (cp - cl) / r if r > 0 else 0.5
        if rp < self.pct_th and cpos < self.close_pos_th:
            conf = min(0.7 + (self.pct_th - rp) * 2, 0.90)
            return [Signal(symbol, "BUY", round(conf, 2), round(cp, 2), round(cp + ca * self.tp_atr, 2), round(cp - ca * self.sl_atr, 2), f"RangePct={rp:.2f} ClosePos={cpos:.2f}")]
        return []

    def _atr(self, d):
        tr = pd.concat([d['high']-d['low'], abs(d['high']-d['close'].shift()), abs(d['low']-d['close'].shift())], axis=1).max(axis=1)
        return tr.rolling(self.atr_period).mean()

if __name__ == "__main__":
    np.random.seed(42); n=300; p=50000*np.exp(np.random.normal(0,0.02,n).cumsum())
    d=pd.DataFrame({'open':p,'high':p*1.005,'low':p*0.995,'close':p,'volume':np.random.uniform(100,1000,n)})
    print(f"Signals: {len(RangeContractionRevertStrategy().generate_signals(d))}")
