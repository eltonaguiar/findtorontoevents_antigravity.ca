"""
SpectralCycleDetector - Strategy #NEW-8
=========================================
UNIQUE: Uses FFT to detect dominant price cycle period, then trades at cycle extremes.
If dominant cycle = 20 bars, buy at cycle trough, sell at cycle peak.

LONG: At cycle trough (phase near -π) + cycle amplitude significant
SHORT: At cycle peak (phase near +π) + cycle amplitude significant
Multi-TF: FFT adapts to whatever data frequency is provided.
"""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float
    take_profit: float; stop_loss: float; reason: str

class SpectralCycleDetectorStrategy:
    def __init__(self, p: Optional[dict] = None):
        self.p = p or {}
        self.fft_lb = self.p.get('fft_lookback', 64)
        self.min_cycle = self.p.get('min_cycle_period', 8)
        self.max_cycle = self.p.get('max_cycle_period', 40)
        self.amp_th = self.p.get('amplitude_threshold', 0.5)
        self.atr_period = self.p.get('atr_period', 14)
        self.tp_atr = self.p.get('tp_atr', 2.0)
        self.sl_atr = self.p.get('sl_atr', 1.5)

    def _atr(self, d):
        tr = pd.concat([d['high']-d['low'], abs(d['high']-d['close'].shift()), abs(d['low']-d['close'].shift())], axis=1).max(axis=1)
        return tr.rolling(self.atr_period).mean()

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.fft_lb + 10:
            return []

        # Detrend prices
        prices = data['close'].iloc[-self.fft_lb:].values
        detrended = prices - np.linspace(prices[0], prices[-1], len(prices))

        # FFT
        fft_vals = np.fft.fft(detrended)
        freqs = np.fft.fftfreq(len(detrended))
        magnitudes = np.abs(fft_vals)

        # Find dominant cycle in valid range
        valid = (1 / np.abs(freqs + 1e-10) >= self.min_cycle) & (1 / np.abs(freqs + 1e-10) <= self.max_cycle) & (freqs > 0)
        if not valid.any():
            return []

        valid_idx = np.where(valid)[0]
        dom_idx = valid_idx[magnitudes[valid_idx].argmax()]
        dom_period = int(round(1 / freqs[dom_idx]))
        dom_amp = magnitudes[dom_idx] / len(detrended) * 2
        dom_phase = np.angle(fft_vals[dom_idx])

        # Amplitude relative to price range
        price_range = prices.max() - prices.min()
        rel_amp = dom_amp / price_range if price_range > 0 else 0

        atr = self._atr(data)
        cp, ca = data['close'].iloc[-1], atr.iloc[-1]

        if pd.isna(ca) or ca <= 0 or rel_amp < self.amp_th:
            return []

        signals = []

        # Phase near -π (trough) → LONG
        if dom_phase < -2.0 or dom_phase > 2.8:
            conf = min(0.7 + rel_amp * 0.3, 0.90)
            signals.append(Signal(symbol, "BUY", round(conf, 2), round(cp, 2),
                round(cp + ca * self.tp_atr, 2), round(cp - ca * self.sl_atr, 2),
                f"Cycle T={dom_period} phase={dom_phase:.1f} LONG trough"))

        # Phase near 0 to π (peak) → SHORT
        elif 0.3 < dom_phase < 1.5:
            conf = min(0.7 + rel_amp * 0.3, 0.90)
            signals.append(Signal(symbol, "SELL", round(conf, 2), round(cp, 2),
                round(cp - ca * self.tp_atr, 2), round(cp + ca * self.sl_atr, 2),
                f"Cycle T={dom_period} phase={dom_phase:.1f} SHORT peak"))

        return signals

if __name__ == "__main__":
    np.random.seed(42); n = 300
    # Add a deliberate cycle for testing
    t = np.arange(n)
    cycle = 500 * np.sin(2 * np.pi * t / 25)
    p = 50000 + np.cumsum(np.random.normal(0, 100, n)) + cycle
    p = np.maximum(p, 1000)
    d = pd.DataFrame({'open': p * 0.999, 'high': p * 1.005, 'low': p * 0.995,
                       'close': p, 'volume': np.random.uniform(100, 1000, n)})
    print(f"Signals: {len(SpectralCycleDetectorStrategy().generate_signals(d))}")
