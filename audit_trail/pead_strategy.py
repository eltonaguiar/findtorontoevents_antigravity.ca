"""
PEAD (post-earnings announcement drift) signal builder — Downloads/pead_strategy.py aligned.

Requires real `earnings_data` and `prices` dicts from caller (e.g. Yahoo/DB pipeline).
"""

from __future__ import annotations

from typing import Any, Optional


class PEADStrategy:
    MIN_SURPRISE_STD = 2.0
    ENTRY_WINDOW_DAYS = (1, 5)
    BASE_SCORE = 40
    MAX_SCORE = 100

    def __init__(self, earnings_data: dict[str, dict], prices: dict[str, float]):
        self.earnings = earnings_data or {}
        self.prices = prices or {}

    def generate_signals(self, universe: Optional[list[str]] = None) -> list[dict[str, Any]]:
        if universe is None:
            universe = list(self.earnings.keys())
        signals = []
        for symbol in universe:
            sig = self._evaluate_symbol(symbol)
            if sig:
                signals.append(sig)
        signals.sort(key=lambda s: s["score"], reverse=True)
        return signals

    def _evaluate_symbol(self, symbol: str) -> Optional[dict[str, Any]]:
        edata = self.earnings.get(symbol)
        if not edata:
            return None
        surprise = edata.get("last_surprise_pct")
        if surprise is None:
            return None
        surprise_std = float(edata.get("surprise_std_history", 5.0) or 5.0)
        days_since = edata.get("days_since_announcement")
        if days_since is None:
            return None
        if abs(float(surprise)) < self.MIN_SURPRISE_STD * surprise_std:
            return None
        lo, hi = self.ENTRY_WINDOW_DAYS
        if int(days_since) < lo or int(days_since) > hi:
            return None
        price = self.prices.get(symbol)
        if not price or float(price) <= 0:
            return None

        direction = "LONG" if float(surprise) > 0 else "SHORT"
        consec = int(edata.get("consecutive_beats", 0) or 0)
        revision_mom = float(edata.get("revision_momentum_7d", 0) or 0)

        score = float(self.BASE_SCORE)
        surprise_points = min(30.0, abs(float(surprise)) * 3.0)
        score += surprise_points
        consec_points = min(15.0, float(consec * 5))
        score += consec_points
        revision_points = min(15.0, abs(revision_mom) * 15.0)
        score += revision_points
        score = min(float(self.MAX_SCORE), score)

        tp_20d = self._calc_target(float(price), float(surprise), 20, direction)
        tp_60d = self._calc_target(float(price), float(surprise), 60, direction)
        sl = self._calc_stop(float(price), direction)
        rr = abs(tp_20d - price) / abs(price - sl) if sl != price else 0.0

        return {
            "symbol": symbol,
            "strategy": "pead_earnings_drift",
            "direction": direction,
            "score": round(score, 1),
            "entry": price,
            "tp": tp_20d,
            "tp_extended": tp_60d,
            "sl": sl,
            "rr": round(rr, 2),
            "hold_period_days": 20,
            "max_hold_days": 60,
            "surprise_pct": surprise,
            "consecutive_beats": consec,
            "revision_momentum": revision_mom,
            "asset_class": "EQUITY",
            "signal_type": "PEAD",
            "breakdown": {
                "base": self.BASE_SCORE,
                "surprise_magnitude": round(surprise_points, 1),
                "consecutive_beats": consec_points,
                "revision_momentum": round(revision_points, 1),
            },
        }

    def _calc_target(self, price: float, surprise: float, days: int, direction: str) -> float:
        drift_pct = abs(surprise) * 0.005 * (days / 60.0)
        drift_pct = min(drift_pct, 0.10)
        if direction == "LONG":
            return round(price * (1 + drift_pct), 2)
        return round(price * (1 - drift_pct), 2)

    def _calc_stop(self, price: float, direction: str) -> float:
        stop_pct = 0.05
        if direction == "LONG":
            return round(price * (1 - stop_pct), 2)
        return round(price * (1 + stop_pct), 2)
