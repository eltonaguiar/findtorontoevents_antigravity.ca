"""
WaveletTrendNoise - Strategy #NEW-4
=====================================
UNIQUE: Decomposes price into trend + noise using Haar wavelet-like smoothing.
Trades when trend component is strong but noise component is low (high SNR).

LONG: Trend component rising + noise ratio low + price above trend
SHORT: Trend component falling + noise ratio low + price below trend
Multi-TF: Works on any bar size — wavelet is scale-adaptive.
"""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float
    take_profit: float; stop_loss: float; reason: str

class WaveletTrendNoiseStrategy:
    def __init__(self, p: Optional[dict] = None):
        self.p = p or {}
        self.trend_period = self.p.get('trend_period', 32)
        self.noise_lb = self.p.get('noise_lookback', 20)
        self.snr_th = self.p.get('snr_threshold', 2.0)
        self.atr_period = self.p.get('atr_period', 14)
        self.tp_atr = self.p.get('tp_atr', 2.5)
        self.sl_atr = self.p.get('sl_atr', 1.2)

    def _wavelet_decompose(self, prices: pd.Series):
        """Haar wavelet-like decomposition: iterative averaging."""
        trend = prices.rolling(self.trend_period).mean()
        noise = prices - trend
        return trend, noise

    def _atr(self, d):
        tr = pd.concat([d['high']-d['low'], abs(d['high']-d['close'].shift()), abs(d['low']-d['close'].shift())], axis=1).max(axis=1)
        return tr.rolling(self.atr_period).mean()

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.trend_period + self.noise_lb + 10:
            return []

        trend, noise = self._wavelet_decompose(data['close'])
        atr = self._atr(data)

        # Signal-to-noise ratio: trend change vs noise magnitude
        trend_delta = trend.diff(5).abs()
        noise_mag = noise.abs().rolling(self.noise_lb).mean()
        snr = trend_delta / noise_mag

        trend_dir = trend.diff(5)
        cp, ca = data['close'].iloc[-1], atr.iloc[-1]
        ct, cd, csnr = trend.iloc[-1], trend_dir.iloc[-1], snr.iloc[-1]

        if pd.isna(csnr) or pd.isna(ca) or ca <= 0:
            return []

        signals = []

        if csnr > self.snr_th:
            if cd > 0 and cp > ct:
                conf = min(0.72 + (csnr - self.snr_th) * 0.08, 0.93)
                signals.append(Signal(symbol, "BUY", round(conf, 2), round(cp, 2),
                    round(cp + ca * self.tp_atr, 2), round(cp - ca * self.sl_atr, 2),
                    f"Wavelet LONG SNR={csnr:.1f} trend↑"))
            elif cd < 0 and cp < ct:
                conf = min(0.72 + (csnr - self.snr_th) * 0.08, 0.93)
                signals.append(Signal(symbol, "SELL", round(conf, 2), round(cp, 2),
                    round(cp - ca * self.tp_atr, 2), round(cp + ca * self.sl_atr, 2),
                    f"Wavelet SHORT SNR={csnr:.1f} trend↓"))

        return signals

if __name__ == "__main__":
    np.random.seed(42); n = 300
    p = 50000 * np.exp(np.random.normal(0.0003, 0.02, n).cumsum())
    d = pd.DataFrame({'open': p * 0.999, 'high': p * 1.008, 'low': p * 0.992,
                       'close': p, 'volume': np.random.uniform(100, 1000, n)})
    print(f"Signals: {len(WaveletTrendNoiseStrategy().generate_signals(d))}")
