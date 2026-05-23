"""
AdaptiveKellyRegime - Strategy #NEW-9
=======================================
UNIQUE: Dynamic Kelly criterion position sizing integrated into signal generation.
Only generates signals when Kelly fraction is positive (expected edge exists).
Embeds risk management directly into the signal.

LONG: Rolling win rate > 55% + pos Kelly + price momentum positive
SHORT: Rolling win rate > 55% + pos Kelly + price momentum negative
Multi-TF: Uses rolling statistics, adapts to any bar size.
"""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float
    take_profit: float; stop_loss: float; reason: str

class AdaptiveKellyRegimeStrategy:
    def __init__(self, p: Optional[dict] = None):
        self.p = p or {}
        self.stats_lb = self.p.get('stats_lookback', 50)
        self.wr_th = self.p.get('win_rate_threshold', 0.55)
        self.kelly_th = self.p.get('kelly_threshold', 0.05)
        self.mom_period = self.p.get('mom_period', 10)
        self.atr_period = self.p.get('atr_period', 14)
        self.tp_atr = self.p.get('tp_atr', 2.0)
        self.sl_atr = self.p.get('sl_atr', 1.0)

    def _atr(self, d):
        tr = pd.concat([d['high']-d['low'], abs(d['high']-d['close'].shift()), abs(d['low']-d['close'].shift())], axis=1).max(axis=1)
        return tr.rolling(self.atr_period).mean()

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.stats_lb + 20:
            return []

        ret = data['close'].pct_change()
        # Rolling win/loss statistics
        wins = (ret > 0).rolling(self.stats_lb).mean()
        avg_win = ret.where(ret > 0).rolling(self.stats_lb).mean()
        avg_loss = ret.where(ret < 0).rolling(self.stats_lb).mean().abs()

        # Kelly fraction = W - (1-W)/R where R = avg_win/avg_loss
        cw, caw, cal = wins.iloc[-1], avg_win.iloc[-1], avg_loss.iloc[-1]
        mom = data['close'].pct_change(self.mom_period).iloc[-1]
        atr = self._atr(data)
        cp, ca = data['close'].iloc[-1], atr.iloc[-1]

        if pd.isna(cw) or pd.isna(caw) or pd.isna(cal) or cal <= 0 or pd.isna(ca) or ca <= 0:
            return []

        R = caw / cal
        kelly = cw - (1 - cw) / R if R > 0 else 0

        signals = []

        if kelly > self.kelly_th and cw > self.wr_th:
            # Scale TP/SL by Kelly fraction (higher Kelly = more aggressive)
            kelly_scale = min(kelly * 5, 1.5)  # Cap at 1.5x
            if mom > 0:
                conf = min(0.7 + kelly * 2, 0.93)
                signals.append(Signal(symbol, "BUY", round(conf, 2), round(cp, 2),
                    round(cp + ca * self.tp_atr * kelly_scale, 2),
                    round(cp - ca * self.sl_atr, 2),
                    f"Kelly={kelly:.2f} WR={cw:.0%} LONG"))
            elif mom < 0:
                conf = min(0.7 + kelly * 2, 0.93)
                signals.append(Signal(symbol, "SELL", round(conf, 2), round(cp, 2),
                    round(cp - ca * self.tp_atr * kelly_scale, 2),
                    round(cp + ca * self.sl_atr, 2),
                    f"Kelly={kelly:.2f} WR={cw:.0%} SHORT"))

        return signals

if __name__ == "__main__":
    np.random.seed(42); n = 300
    p = 50000 * np.exp(np.random.normal(0.0003, 0.02, n).cumsum())
    d = pd.DataFrame({'open': p * 0.999, 'high': p * 1.006, 'low': p * 0.994,
                       'close': p, 'volume': np.random.uniform(100, 1000, n)})
    print(f"Signals: {len(AdaptiveKellyRegimeStrategy().generate_signals(d))}")
