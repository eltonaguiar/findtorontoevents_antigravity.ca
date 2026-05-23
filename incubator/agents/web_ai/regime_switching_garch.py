"""
RegimeSwitchingGARCH - Strategy #NEW-12
=========================================
UNIQUE: Simplified GARCH(1,1) vol forecast. Trades when forecasted vol diverges from realized.
If GARCH predicts vol expansion but current vol is low → breakout imminent.
If GARCH predicts vol contraction but current vol is high → reversion imminent.

LONG: Vol forecast < realized + price above EMA (calm continuation)
SHORT: Vol forecast < realized + price below EMA (calm continuation down)
LONG: Vol forecast > realized + oversold (pre-breakout dip buy)
SHORT: Vol forecast > realized + overbought (pre-breakdown fade)
"""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float
    take_profit: float; stop_loss: float; reason: str

class RegimeSwitchingGARCHStrategy:
    def __init__(self, p: Optional[dict] = None):
        self.p = p or {}
        self.omega = self.p.get('omega', 0.00001)
        self.alpha = self.p.get('alpha', 0.1)
        self.beta = self.p.get('beta', 0.85)
        self.rv_lb = self.p.get('rv_lookback', 20)
        self.diverge_th = self.p.get('divergence_threshold', 1.5)
        self.ema_period = self.p.get('ema_period', 20)
        self.rsi_period = self.p.get('rsi_period', 14)
        self.atr_period = self.p.get('atr_period', 14)
        self.tp_atr = self.p.get('tp_atr', 2.5)
        self.sl_atr = self.p.get('sl_atr', 1.2)

    def _garch_forecast(self, returns: np.ndarray) -> float:
        sigma2 = np.var(returns[:20]) if len(returns) >= 20 else np.var(returns)
        for r in returns:
            sigma2 = self.omega + self.alpha * r ** 2 + self.beta * sigma2
        return np.sqrt(sigma2)

    def _rsi(self, p, n):
        d = p.diff(); g = d.where(d > 0, 0).rolling(n).mean(); l = (-d.where(d < 0, 0)).rolling(n).mean()
        return 100 - (100 / (1 + g / l))

    def _atr(self, d):
        tr = pd.concat([d['high']-d['low'], abs(d['high']-d['close'].shift()), abs(d['low']-d['close'].shift())], axis=1).max(axis=1)
        return tr.rolling(self.atr_period).mean()

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.rv_lb + 30:
            return []
        ret = data['close'].pct_change().dropna().values
        if len(ret) < 30:
            return []
        garch_vol = self._garch_forecast(ret[-60:])
        realized_vol = np.std(ret[-self.rv_lb:])
        ema = data['close'].ewm(span=self.ema_period).mean()
        rsi = self._rsi(data['close'], self.rsi_period)
        atr = self._atr(data)
        cp, ce, cr, ca = data['close'].iloc[-1], ema.iloc[-1], rsi.iloc[-1], atr.iloc[-1]
        if pd.isna(cr) or pd.isna(ca) or ca <= 0 or realized_vol <= 0:
            return []
        vol_ratio = garch_vol / realized_vol
        signals = []
        if vol_ratio < 1.0 / self.diverge_th:  # GARCH says calm
            if cp > ce:
                signals.append(Signal(symbol, "BUY", 0.80, round(cp, 2),
                    round(cp + ca * self.tp_atr, 2), round(cp - ca * self.sl_atr, 2),
                    f"GARCH calm ratio={vol_ratio:.2f} LONG"))
            elif cp < ce:
                signals.append(Signal(symbol, "SELL", 0.80, round(cp, 2),
                    round(cp - ca * self.tp_atr, 2), round(cp + ca * self.sl_atr, 2),
                    f"GARCH calm ratio={vol_ratio:.2f} SHORT"))
        elif vol_ratio > self.diverge_th:  # GARCH says storm coming
            if cr < 30:
                signals.append(Signal(symbol, "BUY", 0.78, round(cp, 2),
                    round(cp + ca * self.tp_atr * 1.3, 2), round(cp - ca * self.sl_atr, 2),
                    f"GARCH storm ratio={vol_ratio:.2f} RSI={cr:.0f} LONG"))
            elif cr > 70:
                signals.append(Signal(symbol, "SELL", 0.78, round(cp, 2),
                    round(cp - ca * self.tp_atr * 1.3, 2), round(cp + ca * self.sl_atr, 2),
                    f"GARCH storm ratio={vol_ratio:.2f} RSI={cr:.0f} SHORT"))
        return signals

if __name__ == "__main__":
    np.random.seed(42); n = 300
    p = 50000 * np.exp(np.random.normal(0.0002, 0.02, n).cumsum())
    d = pd.DataFrame({'open': p * 0.999, 'high': p * 1.008, 'low': p * 0.992,
                       'close': p, 'volume': np.random.uniform(100, 1000, n)})
    print(f"Signals: {len(RegimeSwitchingGARCHStrategy().generate_signals(d))}")
