"""
PowerLawTailRisk - Strategy #NEW-18
=====================================
UNIQUE: Estimates power-law tail exponent (Hill estimator) of return distribution.
Fat tails (low exponent) = extreme moves more likely. Uses this for position entry.

LONG: Tail exponent decreasing (fatter tails) + recent large down move → buy panic
SHORT: Tail exponent decreasing + recent large up move → sell euphoria
Thin tails (high exponent) = calm → trend-follow with tighter stops.
Multi-TF: Distribution-based, works on any bar size.
"""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float
    take_profit: float; stop_loss: float; reason: str

class PowerLawTailRiskStrategy:
    def __init__(self, p: Optional[dict] = None):
        self.p = p or {}
        self.hill_lb = self.p.get('hill_lookback', 60)
        self.hill_k = self.p.get('hill_k', 10)  # Use top-k extremes
        self.fat_th = self.p.get('fat_tail_threshold', 2.5)
        self.thin_th = self.p.get('thin_tail_threshold', 4.0)
        self.extreme_pct = self.p.get('extreme_pct', 0.03)
        self.ema_period = self.p.get('ema_period', 20)
        self.atr_period = self.p.get('atr_period', 14)
        self.tp_atr = self.p.get('tp_atr', 2.0)
        self.sl_atr = self.p.get('sl_atr', 1.5)

    def _hill_estimator(self, abs_returns: np.ndarray, k: int) -> float:
        """Hill estimator for tail exponent."""
        sorted_r = np.sort(abs_returns)[::-1]
        if len(sorted_r) < k + 1 or sorted_r[k] <= 0:
            return 3.0  # Default: moderate tails
        log_ratios = np.log(sorted_r[:k] / sorted_r[k])
        return k / np.sum(log_ratios) if np.sum(log_ratios) > 0 else 3.0

    def _atr(self, d):
        tr = pd.concat([d['high']-d['low'], abs(d['high']-d['close'].shift()), abs(d['low']-d['close'].shift())], axis=1).max(axis=1)
        return tr.rolling(self.atr_period).mean()

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.hill_lb + 10:
            return []
        ret = data['close'].pct_change().dropna()
        if len(ret) < self.hill_lb:
            return []
        abs_ret = np.abs(ret.iloc[-self.hill_lb:].values)
        alpha = self._hill_estimator(abs_ret, self.hill_k)
        ema = data['close'].ewm(span=self.ema_period).mean()
        atr = self._atr(data)
        cp, ce, ca = data['close'].iloc[-1], ema.iloc[-1], atr.iloc[-1]
        recent_ret = ret.iloc[-1]
        if pd.isna(ca) or ca <= 0:
            return []
        signals = []
        # Fat tails regime
        if alpha < self.fat_th:
            if recent_ret < -self.extreme_pct:
                conf = min(0.72 + (self.fat_th - alpha) * 0.15, 0.90)
                signals.append(Signal(symbol, "BUY", round(conf, 2), round(cp, 2),
                    round(cp + ca * self.tp_atr, 2), round(cp - ca * self.sl_atr, 2),
                    f"FatTail α={alpha:.2f} panic ret={recent_ret:.2%} LONG"))
            elif recent_ret > self.extreme_pct:
                conf = min(0.72 + (self.fat_th - alpha) * 0.15, 0.90)
                signals.append(Signal(symbol, "SELL", round(conf, 2), round(cp, 2),
                    round(cp - ca * self.tp_atr, 2), round(cp + ca * self.sl_atr, 2),
                    f"FatTail α={alpha:.2f} euphoria ret={recent_ret:.2%} SHORT"))
        # Thin tails regime → trend follow
        elif alpha > self.thin_th:
            if cp > ce:
                signals.append(Signal(symbol, "BUY", 0.78, round(cp, 2),
                    round(cp + ca * self.tp_atr * 0.8, 2), round(cp - ca * self.sl_atr * 0.7, 2),
                    f"ThinTail α={alpha:.2f} calm trend LONG"))
            elif cp < ce:
                signals.append(Signal(symbol, "SELL", 0.78, round(cp, 2),
                    round(cp - ca * self.tp_atr * 0.8, 2), round(cp + ca * self.sl_atr * 0.7, 2),
                    f"ThinTail α={alpha:.2f} calm trend SHORT"))
        return signals

if __name__ == "__main__":
    np.random.seed(42); n = 300
    p = 50000 * np.exp(np.random.normal(0, 0.02, n).cumsum())
    d = pd.DataFrame({'open': p * 0.999, 'high': p * 1.008, 'low': p * 0.992,
                       'close': p, 'volume': np.random.uniform(100, 1000, n)})
    print(f"Signals: {len(PowerLawTailRiskStrategy().generate_signals(d))}")
