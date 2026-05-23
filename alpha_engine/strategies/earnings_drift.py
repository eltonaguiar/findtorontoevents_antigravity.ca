"""
Earnings Drift Strategy (PEAD)

Post-Earnings Announcement Drift is one of the most robust anomalies in finance.
Stocks that beat earnings and raise guidance continue drifting upward for 6-8 weeks.
"""
from typing import List
import numpy as np
import pandas as pd
from .base import BaseStrategy, StrategyConfig, StrategyType, HoldingPeriod, Signal


class EarningsDriftStrategy(BaseStrategy):
    """
    PEAD (Post-Earnings Announcement Drift) strategy.
    
    Buy stocks that beat earnings by >5% + raised guidance.
    Hold for 6-8 weeks (42 trading days).
    
    Edge source: Structural (slow information diffusion, analyst lag).
    One of the most statistically robust anomalies.
    """

    def _default_config(self) -> StrategyConfig:
        return StrategyConfig(
            name="earnings_drift_pead",
            description="Buy post-earnings beat stocks, drift for 6-8 weeks",
            strategy_type=StrategyType.LONG_ONLY,
            holding_period=HoldingPeriod.SWING,
            max_positions=15,
            top_k=15,
            rebalance_frequency="weekly",
            stop_loss_pct=0.08,
            take_profit_pct=0.20,
            tags=["earnings", "pead", "anomaly"],
        )

    def generate_signals(self, features: pd.DataFrame, date: pd.Timestamp, universe: List[str]) -> List[Signal]:
        signals = []

        pead = self._get_feature(features, date, "earn_pead_signal", universe)
        beats = self._get_feature(features, date, "earn_consecutive_beats", universe)
        safe_bet = self._get_feature(features, date, "earn_is_safe_bet", universe)
        revision = self._get_feature(features, date, "earn_revision_momentum", universe)

        if pead is None and beats is None:
            return signals

        for ticker in universe:
            try:
                score = 0.0
                drivers = {}

                # PEAD signal (strongest component)
                if pead is not None:
                    p = pead.get(ticker, 0)
                    if p > 0:
                        score += p * 2  # Scale up
                        drivers["pead_signal"] = float(p)

                # Consecutive beats bonus
                if beats is not None:
                    b = beats.get(ticker, 0)
                    if b >= 3:
                        score += 0.3
                        drivers["consecutive_beats"] = float(b)
                    elif b >= 1:
                        score += 0.1

                # Safe bet flag (3+ beats of 5%+)
                if safe_bet is not None:
                    sb = safe_bet.get(ticker, 0)
                    if sb:
                        score += 0.2
                        drivers["safe_bet"] = True

                # Revision momentum bonus
                if revision is not None:
                    r = revision.get(ticker, 0)
                    if r > 0:
                        score += r * 0.3
                        drivers["revision_momentum"] = float(r)

                score = min(score, 1.0)
                if score > 0.2:
                    signals.append(Signal(
                        ticker=ticker, date=date, score=score,
                        direction=1, confidence=min(score * 0.8, 0.9),
                        holding_period=42,  # 6 weeks
                        drivers=drivers,
                        category="earnings_drift",
                    ))
            except Exception:
                continue

        return sorted(signals, key=lambda s: s.score, reverse=True)[:self.config.top_k]

    def _get_feature(self, features, date, col, universe):
        try:
            if isinstance(features.index, pd.MultiIndex) and date in features.index.get_level_values(0):
                return features.loc[date].get(col)
        except Exception:
            pass
        return None


class ConsecutiveBeatsStrategy(BaseStrategy):
    """
    The "Safe Bet" strategy: buy stocks with 3+ consecutive earnings beats.
    
    These are the boring, reliable compounders. Lower turnover, longer holds.
    Combined with positive revision momentum for extra confirmation.
    """

    def _default_config(self) -> StrategyConfig:
        return StrategyConfig(
            name="consecutive_beats_safe_bet",
            description="Buy stocks with 3+ consecutive EPS beats >5% (Safe Bets)",
            strategy_type=StrategyType.LONG_ONLY,
            holding_period=HoldingPeriod.MEDIUM,
            max_positions=20,
            top_k=20,
            rebalance_frequency="monthly",
            max_position_pct=0.05,
            stop_loss_pct=0.12,
            take_profit_pct=0.30,
            tags=["earnings", "safe_bet", "quality"],
        )

    def generate_signals(self, features: pd.DataFrame, date: pd.Timestamp, universe: List[str]) -> List[Signal]:
        signals = []

        beats = self._get_feature(features, date, "earn_consecutive_beats", universe)
        quality = self._get_feature(features, date, "earn_beat_streak_quality", universe)
        revision = self._get_feature(features, date, "earn_revision_momentum", universe)

        if beats is None:
            return signals

        for ticker in universe:
            try:
                b = beats.get(ticker, 0)
                if b < 3:  # Must have 3+ consecutive beats
                    continue

                q = quality.get(ticker, 0) if quality is not None else 0
                r = revision.get(ticker, 0) if revision is not None else 0

                score = min(b / 6, 0.5)  # Up to 0.5 from beats
                score += min(q / 3, 0.3)  # Up to 0.3 from quality
                if r > 0:
                    score += r * 0.2  # Up to 0.2 from revision
                score = min(score, 1.0)

                signals.append(Signal(
                    ticker=ticker, date=date, score=score,
                    direction=1, confidence=min(score * 0.85, 0.95),
                    holding_period=self.config.holding_period.value,
                    drivers={"consecutive_beats": float(b), "quality": float(q), "revision": float(r)},
                    category="safe_bet",
                ))
            except Exception:
                continue

        return sorted(signals, key=lambda s: s.score, reverse=True)[:self.config.top_k]

    def _get_feature(self, features, date, col, universe):
        try:
            if isinstance(features.index, pd.MultiIndex) and date in features.index.get_level_values(0):
                return features.loc[date].get(col)
        except Exception:
            pass
        return None
