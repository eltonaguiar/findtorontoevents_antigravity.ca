"""
VPINToxicityFlow - Strategy #NEW-7
====================================
UNIQUE: Volume-synchronized Probability of Informed Trading (VPIN) proxy.
Measures order flow toxicity. High VPIN = smart money active = adverse selection risk.

LONG: VPIN drops from high (toxicity clearing) + bullish structure
SHORT: VPIN drops from high + bearish structure
Fade: When VPIN spikes high, wait for it to normalize then enter.
Multi-TF: Volume-clock based, naturally adapts to any timeframe.
"""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float
    take_profit: float; stop_loss: float; reason: str

class VPINToxicityFlowStrategy:
    def __init__(self, p: Optional[dict] = None):
        self.p = p or {}
        self.vpin_lb = self.p.get('vpin_lookback', 30)
        self.vpin_hi = self.p.get('vpin_high', 0.7)
        self.vpin_drop = self.p.get('vpin_drop_threshold', 0.4)
        self.ema_period = self.p.get('ema_period', 20)
        self.atr_period = self.p.get('atr_period', 14)
        self.tp_atr = self.p.get('tp_atr', 2.3)
        self.sl_atr = self.p.get('sl_atr', 1.3)

    def _vpin_proxy(self, data: pd.DataFrame) -> pd.Series:
        """Approximate VPIN using absolute return / volume ratio."""
        abs_ret = data['close'].pct_change().abs()
        if 'volume' in data and data['volume'].sum() > 0:
            vol_norm = data['volume'] / data['volume'].rolling(self.vpin_lb).mean()
            vpin = (abs_ret * vol_norm).rolling(self.vpin_lb).mean()
        else:
            vpin = abs_ret.rolling(self.vpin_lb).mean()
        # Normalize to 0-1 range via percentile
        return vpin.rolling(self.vpin_lb * 2).rank(pct=True)

    def _atr(self, d):
        tr = pd.concat([d['high']-d['low'], abs(d['high']-d['close'].shift()), abs(d['low']-d['close'].shift())], axis=1).max(axis=1)
        return tr.rolling(self.atr_period).mean()

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.vpin_lb * 3 + 10:
            return []

        vpin = self._vpin_proxy(data)
        ema = data['close'].ewm(span=self.ema_period).mean()
        atr = self._atr(data)

        cv, pv = vpin.iloc[-1], vpin.iloc[-3]
        cp, ce, ca = data['close'].iloc[-1], ema.iloc[-1], atr.iloc[-1]

        if pd.isna(cv) or pd.isna(pv) or pd.isna(ca) or ca <= 0:
            return []

        signals = []
        # Toxicity was high, now dropping = smart money done, safe to enter
        if pv > self.vpin_hi and cv < self.vpin_drop:
            if cp > ce:
                conf = min(0.72 + (pv - cv) * 0.3, 0.92)
                signals.append(Signal(symbol, "BUY", round(conf, 2), round(cp, 2),
                    round(cp + ca * self.tp_atr, 2), round(cp - ca * self.sl_atr, 2),
                    f"VPIN drop {pv:.2f}→{cv:.2f} LONG"))
            elif cp < ce:
                conf = min(0.72 + (pv - cv) * 0.3, 0.92)
                signals.append(Signal(symbol, "SELL", round(conf, 2), round(cp, 2),
                    round(cp - ca * self.tp_atr, 2), round(cp + ca * self.sl_atr, 2),
                    f"VPIN drop {pv:.2f}→{cv:.2f} SHORT"))

        return signals

if __name__ == "__main__":
    np.random.seed(42); n = 300
    p = 50000 * np.exp(np.random.normal(0, 0.02, n).cumsum())
    d = pd.DataFrame({'open': p * 0.999, 'high': p * 1.008, 'low': p * 0.992,
                       'close': p, 'volume': np.random.uniform(100, 1000, n)})
    print(f"Signals: {len(VPINToxicityFlowStrategy().generate_signals(d))}")
