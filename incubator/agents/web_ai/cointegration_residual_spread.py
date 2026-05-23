"""
CointegrationResidualSpread - Strategy #NEW-20
================================================
UNIQUE: Self-cointegration — measures deviation of price from its own long-term
log-linear trend. When residual exceeds ±2σ, trade the mean reversion.
Combines with half-life estimation for optimal entry timing.

LONG: Residual < -2σ (below trend) + half-life < 15 bars (quick reversion expected)
SHORT: Residual > +2σ (above trend) + half-life < 15 bars
Multi-TF: Log-linear regression adapts to any timeframe.
"""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float
    take_profit: float; stop_loss: float; reason: str

class CointegrationResidualSpreadStrategy:
    def __init__(self, p: Optional[dict] = None):
        self.p = p or {}
        self.trend_lb = self.p.get('trend_lookback', 60)
        self.sigma_th = self.p.get('sigma_threshold', 2.0)
        self.hl_max = self.p.get('halflife_max', 15)
        self.atr_period = self.p.get('atr_period', 14)
        self.tp_atr = self.p.get('tp_atr', 2.0)
        self.sl_atr = self.p.get('sl_atr', 1.5)

    def _half_life(self, residuals: np.ndarray) -> float:
        """Estimate Ornstein-Uhlenbeck half-life from residuals."""
        if len(residuals) < 10:
            return 999
        y = np.diff(residuals)
        x = residuals[:-1]
        if np.std(x) == 0:
            return 999
        beta = np.cov(x, y)[0, 1] / np.var(x)
        if beta >= 0:
            return 999
        return -np.log(2) / beta

    def _atr(self, d):
        tr = pd.concat([d['high']-d['low'], abs(d['high']-d['close'].shift()), abs(d['low']-d['close'].shift())], axis=1).max(axis=1)
        return tr.rolling(self.atr_period).mean()

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.trend_lb + 10:
            return []
        prices = data['close'].iloc[-self.trend_lb:].values
        log_prices = np.log(prices)
        x = np.arange(len(log_prices))
        # Fit log-linear trend
        coeffs = np.polyfit(x, log_prices, 1)
        trend = np.polyval(coeffs, x)
        residuals = log_prices - trend
        res_std = np.std(residuals)
        res_now = residuals[-1]
        z_score = res_now / res_std if res_std > 0 else 0
        hl = self._half_life(residuals)
        atr = self._atr(data)
        cp, ca = data['close'].iloc[-1], atr.iloc[-1]
        if pd.isna(ca) or ca <= 0:
            return []
        signals = []
        # Below trend → LONG
        if z_score < -self.sigma_th and hl < self.hl_max:
            conf = min(0.72 + abs(z_score) * 0.05 + (self.hl_max - hl) * 0.005, 0.93)
            signals.append(Signal(symbol, "BUY", round(conf, 2), round(cp, 2),
                round(cp + ca * self.tp_atr, 2), round(cp - ca * self.sl_atr, 2),
                f"Coint z={z_score:.1f}σ HL={hl:.0f} LONG"))
        # Above trend → SHORT
        if z_score > self.sigma_th and hl < self.hl_max:
            conf = min(0.72 + abs(z_score) * 0.05 + (self.hl_max - hl) * 0.005, 0.93)
            signals.append(Signal(symbol, "SELL", round(conf, 2), round(cp, 2),
                round(cp - ca * self.tp_atr, 2), round(cp + ca * self.sl_atr, 2),
                f"Coint z={z_score:.1f}σ HL={hl:.0f} SHORT"))
        return signals

if __name__ == "__main__":
    np.random.seed(42); n = 300
    p = 50000 * np.exp(np.random.normal(0.0001, 0.02, n).cumsum())
    d = pd.DataFrame({'open': p * 0.999, 'high': p * 1.008, 'low': p * 0.992,
                       'close': p, 'volume': np.random.uniform(100, 1000, n)})
    print(f"Signals: {len(CointegrationResidualSpreadStrategy().generate_signals(d))}")
