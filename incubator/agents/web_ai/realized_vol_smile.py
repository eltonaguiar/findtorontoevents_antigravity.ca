"""
RealizedVolSmile - Strategy #NEW-11
=====================================
UNIQUE: Computes realized vol "smile" — compares upside realized vol vs downside realized vol.
When downside vol >> upside vol, fear is priced in → buy. When upside vol >> downside, greed → sell.

LONG: Down-vol / up-vol ratio > 2.0 (fear premium) + price stabilizing
SHORT: Up-vol / down-vol ratio > 2.0 (greed premium) + price rolling over
Multi-TF: Ratio-based, works on any bar size.
"""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float
    take_profit: float; stop_loss: float; reason: str

class RealizedVolSmileStrategy:
    def __init__(self, p: Optional[dict] = None):
        self.p = p or {}
        self.lb = self.p.get('lookback', 30)
        self.ratio_th = self.p.get('ratio_threshold', 2.0)
        self.atr_period = self.p.get('atr_period', 14)
        self.tp_atr = self.p.get('tp_atr', 2.3)
        self.sl_atr = self.p.get('sl_atr', 1.3)

    def _atr(self, d):
        tr = pd.concat([d['high']-d['low'], abs(d['high']-d['close'].shift()), abs(d['low']-d['close'].shift())], axis=1).max(axis=1)
        return tr.rolling(self.atr_period).mean()

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.lb + 10:
            return []
        ret = data['close'].pct_change()
        up_vol = ret.where(ret > 0).rolling(self.lb).std()
        dn_vol = ret.where(ret < 0).rolling(self.lb).std()
        atr = self._atr(data)
        cp, ca = data['close'].iloc[-1], atr.iloc[-1]
        cuv, cdv = up_vol.iloc[-1], dn_vol.iloc[-1]
        if pd.isna(cuv) or pd.isna(cdv) or cuv <= 0 or cdv <= 0 or pd.isna(ca) or ca <= 0:
            return []
        stabilizing = data['close'].iloc[-1] > data['close'].iloc[-3]
        rolling_over = data['close'].iloc[-1] < data['close'].iloc[-3]
        signals = []
        dn_up_ratio = cdv / cuv
        if dn_up_ratio > self.ratio_th and stabilizing:
            conf = min(0.72 + (dn_up_ratio - self.ratio_th) * 0.1, 0.92)
            signals.append(Signal(symbol, "BUY", round(conf, 2), round(cp, 2),
                round(cp + ca * self.tp_atr, 2), round(cp - ca * self.sl_atr, 2),
                f"VolSmile fear ratio={dn_up_ratio:.1f} LONG"))
        up_dn_ratio = cuv / cdv
        if up_dn_ratio > self.ratio_th and rolling_over:
            conf = min(0.72 + (up_dn_ratio - self.ratio_th) * 0.1, 0.92)
            signals.append(Signal(symbol, "SELL", round(conf, 2), round(cp, 2),
                round(cp - ca * self.tp_atr, 2), round(cp + ca * self.sl_atr, 2),
                f"VolSmile greed ratio={up_dn_ratio:.1f} SHORT"))
        return signals

if __name__ == "__main__":
    np.random.seed(42); n = 300
    p = 50000 * np.exp(np.random.normal(0, 0.02, n).cumsum())
    d = pd.DataFrame({'open': p * 0.999, 'high': p * 1.008, 'low': p * 0.992,
                       'close': p, 'volume': np.random.uniform(100, 1000, n)})
    print(f"Signals: {len(RealizedVolSmileStrategy().generate_signals(d))}")
