"""
MicrostructurSpreadProxy - Strategy #NEW-14
=============================================
UNIQUE: Estimates effective bid-ask spread using Corwin-Schultz (2012) high-low estimator.
Wide spread = illiquid/toxic. Narrowing spread after wide = opportunity.

LONG: Spread was wide (>90th pct), now narrowing + bullish momentum
SHORT: Spread was wide, now narrowing + bearish momentum
Multi-TF: High-low spread estimator works on any OHLC data.
"""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float
    take_profit: float; stop_loss: float; reason: str

class MicrostructureSpreadProxyStrategy:
    def __init__(self, p: Optional[dict] = None):
        self.p = p or {}
        self.spread_lb = self.p.get('spread_lookback', 30)
        self.pct_hi = self.p.get('pct_high', 0.90)
        self.pct_lo = self.p.get('pct_low', 0.50)
        self.mom_period = self.p.get('mom_period', 5)
        self.atr_period = self.p.get('atr_period', 14)
        self.tp_atr = self.p.get('tp_atr', 2.5)
        self.sl_atr = self.p.get('sl_atr', 1.2)

    def _corwin_schultz_spread(self, data: pd.DataFrame) -> pd.Series:
        """Corwin-Schultz high-low spread estimator."""
        log_hl = np.log(data['high'] / data['low'])
        log_hl_sq = log_hl ** 2
        # 2-period high-low
        h2 = data['high'].rolling(2).max()
        l2 = data['low'].rolling(2).min()
        log_hl2_sq = np.log(h2 / l2) ** 2
        beta = log_hl_sq.rolling(2).sum()
        gamma = log_hl2_sq
        alpha = (np.sqrt(2 * beta) - np.sqrt(beta)) / (3 - 2 * np.sqrt(2)) - np.sqrt(gamma / (3 - 2 * np.sqrt(2)))
        spread = 2 * (np.exp(alpha) - 1) / (1 + np.exp(alpha))
        return spread.clip(lower=0)

    def _atr(self, d):
        tr = pd.concat([d['high']-d['low'], abs(d['high']-d['close'].shift()), abs(d['low']-d['close'].shift())], axis=1).max(axis=1)
        return tr.rolling(self.atr_period).mean()

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.spread_lb * 2 + 10:
            return []
        spread = self._corwin_schultz_spread(data)
        spread_pct = spread.rolling(self.spread_lb * 2).rank(pct=True)
        atr = self._atr(data)
        mom = data['close'].pct_change(self.mom_period)
        cp, ca = data['close'].iloc[-1], atr.iloc[-1]
        cs_now, cs_prev = spread_pct.iloc[-1], spread_pct.iloc[-3]
        cm = mom.iloc[-1]
        if pd.isna(cs_now) or pd.isna(cs_prev) or pd.isna(ca) or ca <= 0 or pd.isna(cm):
            return []
        signals = []
        # Was wide, now narrowing
        if cs_prev > self.pct_hi and cs_now < self.pct_lo:
            if cm > 0:
                conf = min(0.72 + (cs_prev - cs_now) * 0.4, 0.92)
                signals.append(Signal(symbol, "BUY", round(conf, 2), round(cp, 2),
                    round(cp + ca * self.tp_atr, 2), round(cp - ca * self.sl_atr, 2),
                    f"Spread narrowing {cs_prev:.2f}→{cs_now:.2f} LONG"))
            elif cm < 0:
                conf = min(0.72 + (cs_prev - cs_now) * 0.4, 0.92)
                signals.append(Signal(symbol, "SELL", round(conf, 2), round(cp, 2),
                    round(cp - ca * self.tp_atr, 2), round(cp + ca * self.sl_atr, 2),
                    f"Spread narrowing {cs_prev:.2f}→{cs_now:.2f} SHORT"))
        return signals

if __name__ == "__main__":
    np.random.seed(42); n = 300
    p = 50000 * np.exp(np.random.normal(0, 0.02, n).cumsum())
    d = pd.DataFrame({'open': p * 0.999, 'high': p * 1.008, 'low': p * 0.992,
                       'close': p, 'volume': np.random.uniform(100, 1000, n)})
    print(f"Signals: {len(MicrostructureSpreadProxyStrategy().generate_signals(d))}")
