"""
Quality & Value Strategies

Quality: high ROIC, stable margins, low accruals (the "boring winners").
Value: cheap stocks by fundamentals (with quality filter to avoid traps).
Dividend Aristocrats: 25+ years of consecutive dividend increases.
"""
from typing import List
import numpy as np
import pandas as pd
from .base import BaseStrategy, StrategyConfig, StrategyType, HoldingPeriod, Signal


class QualityCompoundersStrategy(BaseStrategy):
    """
    Buy "compounding machines": high ROE/ROIC + stable margins + low leverage.
    
    This is the "Compounding Quality" sleeve: lower turnover, long horizon.
    NOT mixed with short-term momentum.
    
    Edge source: Behavioral (investors overpay for exciting stories,
    underpay for boring consistency).
    """

    def _default_config(self) -> StrategyConfig:
        return StrategyConfig(
            name="quality_compounders",
            description="Buy high-quality compounders: ROIC, margins, FCF, low debt",
            strategy_type=StrategyType.LONG_ONLY,
            holding_period=HoldingPeriod.LONG,
            max_positions=25,
            top_k=25,
            rebalance_frequency="monthly",
            max_position_pct=0.05,
            stop_loss_pct=0.15,
            take_profit_pct=999,  # Let winners ride
            tags=["quality", "compounders", "long_term"],
        )

    def generate_signals(self, features: pd.DataFrame, date: pd.Timestamp, universe: List[str]) -> List[Signal]:
        signals = []

        quality = self._get_feature(features, date, "fund_quality_composite", universe)
        piotroski = self._get_feature(features, date, "fund_piotroski_proxy", universe)
        resilience = self._get_feature(features, date, "fund_balance_sheet_resilience", universe)
        roe_rank = self._get_feature(features, date, "fund_roe_rank", universe)

        if quality is None:
            return signals

        for ticker in universe:
            try:
                q = quality.get(ticker, 0)
                p = piotroski.get(ticker, 0) if piotroski is not None else 3
                r = resilience.get(ticker, 0.5) if resilience is not None else 0.5
                roe_r = roe_rank.get(ticker, 0.5) if roe_rank is not None else 0.5

                score = q * 0.4 + (p / 6) * 0.2 + r * 0.2 + roe_r * 0.2
                score = min(score, 1.0)

                if score > 0.5:
                    signals.append(Signal(
                        ticker=ticker, date=date, score=score,
                        direction=1, confidence=min(score * 0.9, 0.95),
                        holding_period=self.config.holding_period.value,
                        drivers={"quality": float(q), "piotroski": float(p),
                                 "resilience": float(r), "roe_rank": float(roe_r)},
                        category="quality",
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


class ValueQualityStrategy(BaseStrategy):
    """
    Value investing with quality filter (avoid value traps).
    
    Buy cheap stocks (low P/E, P/B) BUT only if quality is decent.
    This avoids the classic value trap: cheap because it deserves to be cheap.
    """

    def _default_config(self) -> StrategyConfig:
        return StrategyConfig(
            name="value_quality",
            description="Buy undervalued stocks with quality filter (no value traps)",
            strategy_type=StrategyType.LONG_ONLY,
            holding_period=HoldingPeriod.MEDIUM,
            max_positions=20,
            top_k=20,
            rebalance_frequency="monthly",
            tags=["value", "quality"],
        )

    def generate_signals(self, features: pd.DataFrame, date: pd.Timestamp, universe: List[str]) -> List[Signal]:
        signals = []

        val_composite = self._get_feature(features, date, "val_value_composite", universe)
        val_quality = self._get_feature(features, date, "val_value_quality_combo", universe)
        sector_neutral = self._get_feature(features, date, "val_sector_neutral_value", universe)

        if val_composite is None:
            return signals

        for ticker in universe:
            try:
                vc = val_composite.get(ticker, 0.5)
                vq = val_quality.get(ticker, 0.5) if val_quality is not None else 0.5
                sn = sector_neutral.get(ticker, 0.5) if sector_neutral is not None else 0.5

                # Require minimum quality (>40th percentile)
                if vq < 0.4:
                    continue

                score = vc * 0.3 + vq * 0.4 + sn * 0.3
                score = min(score, 1.0)

                if score > 0.5:
                    signals.append(Signal(
                        ticker=ticker, date=date, score=score,
                        direction=1, confidence=min(score * 0.8, 0.9),
                        holding_period=self.config.holding_period.value,
                        drivers={"value_composite": float(vc), "value_quality": float(vq),
                                 "sector_neutral": float(sn)},
                        category="value",
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


class DividendAristocratsStrategy(BaseStrategy):
    """
    Dividend Aristocrats: companies with 25+ years of consecutive dividend increases.
    
    "Safe Bet" sleeve: during market downturns, these act as alpha
    because everyone flees to quality.
    """

    def _default_config(self) -> StrategyConfig:
        return StrategyConfig(
            name="dividend_aristocrats",
            description="Buy Dividend Aristocrats (25+ years of consecutive increases)",
            strategy_type=StrategyType.LONG_ONLY,
            holding_period=HoldingPeriod.BUY_AND_HOLD,
            max_positions=30,
            top_k=30,
            rebalance_frequency="monthly",
            max_position_pct=0.05,
            stop_loss_pct=0.20,
            take_profit_pct=999,
            tags=["dividend", "aristocrats", "safe_bet", "income"],
        )

    def generate_signals(self, features: pd.DataFrame, date: pd.Timestamp, universe: List[str]) -> List[Signal]:
        from .. import config as cfg

        signals = []
        aristocrats = set(cfg.DIVIDEND_ARISTOCRATS)

        div_yield = self._get_feature(features, date, "val_div_yield_rank", universe)
        quality = self._get_feature(features, date, "fund_quality_composite", universe)

        for ticker in universe:
            if ticker not in aristocrats:
                continue

            try:
                dy = div_yield.get(ticker, 0.5) if div_yield is not None else 0.5
                q = quality.get(ticker, 0.5) if quality is not None else 0.5

                score = 0.5  # Base score for being an aristocrat
                score += dy * 0.25  # Dividend yield contribution
                score += q * 0.25  # Quality contribution
                score = min(score, 1.0)

                signals.append(Signal(
                    ticker=ticker, date=date, score=score,
                    direction=1, confidence=0.85,
                    holding_period=self.config.holding_period.value,
                    drivers={"is_aristocrat": True, "div_yield_rank": float(dy), "quality": float(q)},
                    category="dividend_aristocrat",
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
