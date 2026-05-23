"""
Crypto Bayesian Regime Transition Momentum - Baby Strat
=======================================================

Created by: codex_gpt5
Date: 2026-02-26

Reference mindset:
- Bayesian transition matrices for regime persistence
- CTA-style momentum only when transition odds flip
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class Signal:
    symbol: str
    direction: str
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str


class CryptoBayesianRegimeTransitionMomentumStrategy:
    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.transition_window = self.params.get("transition_window", 80)
        self.mom_window = self.params.get("mom_window", 12)
        self.transition_edge = self.params.get("transition_edge", 0.57)
        self.atr_period = self.params.get("atr_period", 14)
        self.tp_atr_mult = self.params.get("tp_atr_mult", 2.2)
        self.sl_atr_mult = self.params.get("sl_atr_mult", 1.3)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        min_bars = max(self.transition_window, self.mom_window, self.atr_period) + 10
        if len(data) < min_bars:
            return []

        close = data["close"]
        ret = close.pct_change().fillna(0.0)
        states = (ret > 0).astype(int)  # 1=up, 0=down
        window_states = states.iloc[-self.transition_window:]

        up_to_up = 1
        up_to_dn = 1
        dn_to_up = 1
        dn_to_dn = 1
        for i in range(1, len(window_states)):
            prev_s = window_states.iloc[i - 1]
            cur_s = window_states.iloc[i]
            if prev_s == 1 and cur_s == 1:
                up_to_up += 1
            elif prev_s == 1 and cur_s == 0:
                up_to_dn += 1
            elif prev_s == 0 and cur_s == 1:
                dn_to_up += 1
            else:
                dn_to_dn += 1

        p_up_given_up = up_to_up / (up_to_up + up_to_dn)
        p_up_given_dn = dn_to_up / (dn_to_up + dn_to_dn)
        p_dn_given_up = up_to_dn / (up_to_up + up_to_dn)
        p_dn_given_dn = dn_to_dn / (dn_to_up + dn_to_dn)

        mom = close.pct_change(self.mom_window).iloc[-1]
        prev_state = states.iloc[-1]
        atr = self._atr(data, self.atr_period)
        px, a = close.iloc[-1], atr.iloc[-1]

        signals: List[Signal] = []
        if prev_state == 0 and p_up_given_dn > self.transition_edge and mom > 0:
            edge = min(1.0, (p_up_given_dn - self.transition_edge) / 0.3 + mom / 0.06)
            conf = min(0.95, max(0.1, 0.44 + 0.3 * edge))
            signals.append(self._mk(symbol, "BUY", px, a, conf, f"Bayesian up-transition edge (P={p_up_given_dn:.2f})"))
        elif prev_state == 1 and p_dn_given_up > self.transition_edge and mom < 0:
            edge = min(1.0, (p_dn_given_up - self.transition_edge) / 0.3 + abs(mom) / 0.06)
            conf = min(0.95, max(0.1, 0.44 + 0.3 * edge))
            signals.append(self._mk(symbol, "SELL", px, a, conf, f"Bayesian down-transition edge (P={p_dn_given_up:.2f})"))
        return signals

    def _mk(self, symbol: str, direction: str, px: float, atr: float, conf: float, reason: str) -> Signal:
        if direction == "BUY":
            tp, sl = px + self.tp_atr_mult * atr, px - self.sl_atr_mult * atr
        else:
            tp, sl = px - self.tp_atr_mult * atr, px + self.sl_atr_mult * atr
        return Signal(symbol, direction, round(conf, 3), round(px, 2), round(tp, 2), round(sl, 2), reason)

    def _atr(self, data: pd.DataFrame, period: int) -> pd.Series:
        h, l, c = data["high"], data["low"], data["close"]
        tr = pd.concat([(h - l), (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
        return tr.rolling(period, min_periods=1).mean()


if __name__ == "__main__":
    np.random.seed(33)
    n = 360
    returns = np.random.normal(0.0003, 0.021, n)
    prices = 50000 * np.exp(np.cumsum(returns))
    test = pd.DataFrame({
        "open": prices * (1 + np.random.normal(0, 0.001, n)),
        "high": prices * (1 + np.abs(np.random.normal(0, 0.011, n))),
        "low": prices * (1 - np.abs(np.random.normal(0, 0.011, n))),
        "close": prices,
        "volume": np.random.lognormal(7.0, 0.55, n),
    })
    strat = CryptoBayesianRegimeTransitionMomentumStrategy()
    total = 0
    for i in range(170, len(test)):
        total += len(strat.generate_signals(test.iloc[: i + 1], "BTCUSDT"))
    print(total)

