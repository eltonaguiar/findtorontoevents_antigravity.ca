"""
FractalDimensionRegime - Strategy #NEW-2
=========================================
UNIQUE: Computes fractal dimension via Higuchi's method to classify market regime.
FD ~1.5 = random walk (no edge), FD < 1.4 = trending (trade trend), FD > 1.6 = mean-reverting.

LONG: Trend regime (FD < 1.4) + price above EMA → ride trend
SHORT: Trend regime (FD < 1.4) + price below EMA → ride downtrend
LONG: Mean-revert regime (FD > 1.6) + oversold → buy dip
SHORT: Mean-revert regime (FD > 1.6) + overbought → sell rip

Works across ALL timeframes — fractal dimension is scale-invariant.
"""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float
    take_profit: float; stop_loss: float; reason: str

class FractalDimensionRegimeStrategy:
    def __init__(self, p: Optional[dict] = None):
        self.p = p or {}
        self.fd_lookback = self.p.get('fd_lookback', 50)
        self.k_max = self.p.get('k_max', 10)
        self.trend_th = self.p.get('trend_threshold', 1.4)
        self.mr_th = self.p.get('mean_revert_threshold', 1.6)
        self.ema_period = self.p.get('ema_period', 20)
        self.rsi_period = self.p.get('rsi_period', 14)
        self.atr_period = self.p.get('atr_period', 14)
        self.tp_atr = self.p.get('tp_atr', 2.3)
        self.sl_atr = self.p.get('sl_atr', 1.3)

    def _higuchi_fd(self, series: np.ndarray) -> float:
        """Higuchi fractal dimension estimator."""
        n = len(series)
        if n < self.k_max * 2:
            return 1.5
        lk = []
        ks = range(1, self.k_max + 1)
        for k in ks:
            lengths = []
            for m in range(1, k + 1):
                idx = np.arange(m - 1, n, k)
                if len(idx) < 2:
                    continue
                s = series[idx]
                length = np.sum(np.abs(np.diff(s))) * (n - 1) / (k * len(idx) * k)
                lengths.append(length)
            if lengths:
                lk.append(np.mean(lengths))
            else:
                lk.append(1e-10)
        lk = np.array(lk)
        lk[lk <= 0] = 1e-10
        ks_arr = np.array(list(ks), dtype=float)
        # Linear regression in log space
        coeffs = np.polyfit(np.log(1.0 / ks_arr), np.log(lk), 1)
        return coeffs[0]

    def _rsi(self, prices, n):
        d = prices.diff()
        g = d.where(d > 0, 0).rolling(n).mean()
        l = (-d.where(d < 0, 0)).rolling(n).mean()
        return 100 - (100 / (1 + g / l))

    def _atr(self, d):
        tr = pd.concat([d['high']-d['low'], abs(d['high']-d['close'].shift()), abs(d['low']-d['close'].shift())], axis=1).max(axis=1)
        return tr.rolling(self.atr_period).mean()

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.fd_lookback + 20:
            return []

        prices = data['close'].values
        fd = self._higuchi_fd(prices[-self.fd_lookback:])

        ema = data['close'].ewm(span=self.ema_period).mean()
        rsi = self._rsi(data['close'], self.rsi_period)
        atr = self._atr(data)

        cp = data['close'].iloc[-1]
        ce = ema.iloc[-1]
        cr = rsi.iloc[-1]
        ca = atr.iloc[-1]

        if pd.isna(cr) or pd.isna(ca) or ca <= 0:
            return []

        signals = []

        if fd < self.trend_th:
            # TRENDING regime — follow the trend
            if cp > ce:
                conf = min(0.7 + (self.trend_th - fd) * 2, 0.92)
                signals.append(Signal(symbol, "BUY", round(conf, 2), round(cp, 2),
                    round(cp + ca * self.tp_atr, 2), round(cp - ca * self.sl_atr, 2),
                    f"FD={fd:.2f} TREND regime LONG"))
            else:
                conf = min(0.7 + (self.trend_th - fd) * 2, 0.92)
                signals.append(Signal(symbol, "SELL", round(conf, 2), round(cp, 2),
                    round(cp - ca * self.tp_atr, 2), round(cp + ca * self.sl_atr, 2),
                    f"FD={fd:.2f} TREND regime SHORT"))

        elif fd > self.mr_th:
            # MEAN-REVERTING regime — fade extremes
            if cr < 30:
                conf = min(0.7 + (fd - self.mr_th) * 1.5, 0.90)
                signals.append(Signal(symbol, "BUY", round(conf, 2), round(cp, 2),
                    round(cp + ca * self.tp_atr, 2), round(cp - ca * self.sl_atr, 2),
                    f"FD={fd:.2f} MR regime LONG RSI={cr:.0f}"))
            elif cr > 70:
                conf = min(0.7 + (fd - self.mr_th) * 1.5, 0.90)
                signals.append(Signal(symbol, "SELL", round(conf, 2), round(cp, 2),
                    round(cp - ca * self.tp_atr, 2), round(cp + ca * self.sl_atr, 2),
                    f"FD={fd:.2f} MR regime SHORT RSI={cr:.0f}"))

        return signals

if __name__ == "__main__":
    np.random.seed(42); n = 300
    p = 50000 * np.exp(np.random.normal(0.0002, 0.02, n).cumsum())
    d = pd.DataFrame({'open': p * 0.999, 'high': p * 1.008, 'low': p * 0.992,
                       'close': p, 'volume': np.random.uniform(100, 1000, n)})
    s = FractalDimensionRegimeStrategy()
    sigs = s.generate_signals(d)
    print(f"Signals: {len(sigs)} | {[(s.direction, s.reason[:30]) for s in sigs]}")
