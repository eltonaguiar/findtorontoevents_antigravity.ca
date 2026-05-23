"""
DispersionMeanReversion - Strategy #NEW-16
============================================
UNIQUE: Measures intra-bar price dispersion (high-low range as % of close) and its
rolling z-score. Extreme dispersion = panic/euphoria = reversion opportunity.

LONG: Dispersion z-score > 2 (panic bar) + close in upper half → absorption
SHORT: Dispersion z-score > 2 (euphoria bar) + close in lower half → rejection
Multi-TF: Dispersion is percentage-based, works on any bar.
"""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float
    take_profit: float; stop_loss: float; reason: str

class DispersionMeanReversionStrategy:
    def __init__(self, p: Optional[dict] = None):
        self.p = p or {}
        self.disp_lb = self.p.get('dispersion_lookback', 40)
        self.z_th = self.p.get('z_threshold', 2.0)
        self.atr_period = self.p.get('atr_period', 14)
        self.tp_atr = self.p.get('tp_atr', 2.0)
        self.sl_atr = self.p.get('sl_atr', 1.5)

    def _atr(self, d):
        tr = pd.concat([d['high']-d['low'], abs(d['high']-d['close'].shift()), abs(d['low']-d['close'].shift())], axis=1).max(axis=1)
        return tr.rolling(self.atr_period).mean()

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.disp_lb + 10:
            return []
        disp = (data['high'] - data['low']) / data['close']
        disp_mean = disp.rolling(self.disp_lb).mean()
        disp_std = disp.rolling(self.disp_lb).std()
        disp_z = (disp - disp_mean) / disp_std
        # Close location within bar
        bar_loc = (data['close'] - data['low']) / (data['high'] - data['low'] + 1e-10)
        atr = self._atr(data)
        cp, ca = data['close'].iloc[-1], atr.iloc[-1]
        cz, cl = disp_z.iloc[-1], bar_loc.iloc[-1]
        if pd.isna(cz) or pd.isna(ca) or ca <= 0:
            return []
        signals = []
        # High dispersion + close in upper half = buying absorbed selling → LONG
        if cz > self.z_th and cl > 0.6:
            conf = min(0.72 + (cz - self.z_th) * 0.1, 0.92)
            signals.append(Signal(symbol, "BUY", round(conf, 2), round(cp, 2),
                round(cp + ca * self.tp_atr, 2), round(cp - ca * self.sl_atr, 2),
                f"Disp z={cz:.1f} loc={cl:.2f} LONG absorption"))
        # High dispersion + close in lower half = selling absorbed buying → SHORT
        if cz > self.z_th and cl < 0.4:
            conf = min(0.72 + (cz - self.z_th) * 0.1, 0.92)
            signals.append(Signal(symbol, "SELL", round(conf, 2), round(cp, 2),
                round(cp - ca * self.tp_atr, 2), round(cp + ca * self.sl_atr, 2),
                f"Disp z={cz:.1f} loc={cl:.2f} SHORT rejection"))
        return signals

if __name__ == "__main__":
    np.random.seed(42); n = 300
    p = 50000 * np.exp(np.random.normal(0, 0.02, n).cumsum())
    d = pd.DataFrame({'open': p * 0.999, 'high': p * 1.01, 'low': p * 0.99,
                       'close': p, 'volume': np.random.uniform(100, 1000, n)})
    print(f"Signals: {len(DispersionMeanReversionStrategy().generate_signals(d))}")
