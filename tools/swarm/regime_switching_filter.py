"""
Regime-Switching Volatility Filter

Regime-aware signal filter that classifies the current market environment using
volatility / ATR analysis and drops or adjusts signals that are mismatched to
the detected regime.

Part of the swarm risk-management layer (PR-2).
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("swarm.regime")


class RegimeSwitchingVolatilityFilter:
    """Filters and adapts trading signals based on detected market regime.

    Regime detection combines ATR ratio analysis, optional VIX level, and a
    trend-strength score to classify the market into one of seven canonical
    regimes.  Signals are then dropped when their directional bias conflicts
    with the regime, and take-profit / stop-loss levels are widened or
    tightened accordingly.

    Parameters
    ----------
    historical_window:
        Look-back period (in bars) for computing the historical ATR mean.
        Default ``20``.
    volatility_threshold_coefficient:
        Multiplier applied to the historical mean ATR when deciding whether
        current volatility is elevated.  Default ``1.5``.
    """

    # Regime identifiers
    TRENDING_UP: str = "TRENDING_UP"
    TRENDING_DOWN: str = "TRENDING_DOWN"
    MEAN_REVERTING: str = "MEAN_REVERTING"
    HIGH_VOLATILITY: str = "HIGH_VOLATILITY"
    LOW_VOLATILITY: str = "LOW_VOLATILITY"
    CHOPPY: str = "CHOPPY"
    UNKNOWN: str = "UNKNOWN"

    # VIX threshold for forced high-volatility classification
    _VIX_HIGH_THRESHOLD: float = 30.0

    # ATR ratio boundaries
    _ATR_LOW_MULTIPLIER: float = 0.5
    _ATR_HIGH_MULTIPLIER: float = 1.5
    _CHOPPY_ATR_LOW: float = 0.8
    _CHOPPY_ATR_HIGH: float = 1.2

    # Trend-strength boundaries
    _TREND_STRONG: float = 0.5
    _CHOPPY_TREND_MAX: float = 0.3

    # TP / SL regime adjustment coefficients
    _TP_SL_ADJUSTMENTS: dict[str, dict[str, float]] = {
        HIGH_VOLATILITY: {"tp": 0.85, "sl": 1.40},
        LOW_VOLATILITY: {"tp": 1.20, "sl": 0.75},
        CHOPPY: {"tp": 0.90, "sl": 1.15},
        MEAN_REVERTING: {"tp": 1.10, "sl": 0.90},
        TRENDING_UP: {"tp": 1.25, "sl": 0.85},
        TRENDING_DOWN: {"tp": 1.25, "sl": 0.85},
        UNKNOWN: {"tp": 1.00, "sl": 1.00},
    }

    def __init__(
        self,
        historical_window: int = 20,
        volatility_threshold_coefficient: float = 1.5,
    ) -> None:
        self.historical_window: int = historical_window
        self.volatility_threshold_coefficient: float = volatility_threshold_coefficient

        logger.info(
            "RegimeSwitchingVolatilityFilter initialised: window=%d coeff=%.2f",
            historical_window,
            volatility_threshold_coefficient,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def filter_predictions(
        self,
        raw_predictions: list[dict[str, Any]],
        historical_atr: list[float],
        current_atr: float,
    ) -> list[dict[str, Any]]:
        """Drop signals that are incompatible with the current market regime.

        Each prediction dict should contain at least:

        * ``"ticker"`` (str)
        * ``"direction"`` (``"LONG"`` | ``"SHORT"``)
        * ``"signal_type"`` (``"momentum"`` | ``"mean_reversion"`` | ...)

        Parameters
        ----------
        raw_predictions:
            Unfiltered list of prediction dictionaries.
        historical_atr:
            Historical ATR series used to compute the mean.
        current_atr:
            The latest ATR reading.

        Returns
        -------
        list[dict]
            Predictions that survive regime filtering.
        """
        if not raw_predictions:
            return []

        mean_atr: float = self._mean_atr(historical_atr)
        atr_ratio: float = current_atr / mean_atr if mean_atr > 0 else 1.0

        # Extract trend strength from predictions if available; otherwise neutral.
        trend_strength: float = 0.0
        for pred in raw_predictions:
            ts = pred.get("trend_strength")
            if isinstance(ts, (int, float)):
                trend_strength = float(ts)
                break

        regime: str = self.detect_regime(None, atr_ratio, trend_strength, current_atr)
        passed: list[dict[str, Any]] = []

        for pred in raw_predictions:
            direction: str = pred.get("direction", "UNKNOWN")
            signal_type: str = pred.get("signal_type", "unknown")

            if not self.is_favorable_for_direction(regime, direction):
                logger.debug(
                    "Dropping %s %s signal: regime=%s unfavorable",
                    pred.get("ticker", "?"),
                    direction,
                    regime,
                )
                continue

            # In CHOPPY / MEAN_REVERTING regimes: drop momentum, keep mean-reversion
            if regime in (self.CHOPPY, self.MEAN_REVERTING) and signal_type == "momentum":
                logger.debug(
                    "Dropping %s momentum signal in %s regime",
                    pred.get("ticker", "?"),
                    regime,
                )
                continue

            passed.append(pred)

        logger.info(
            "Regime %s: %d/%d predictions passed filter",
            regime,
            len(passed),
            len(raw_predictions),
        )
        return passed

    def detect_regime(
        self,
        vix: float | None,
        atr_ratio: float,
        trend_strength: float,
        current_atr: float | None = None,
    ) -> str:
        """Detect the current market regime from volatility and trend inputs.

        Parameters
        ----------
        vix:
            Optional VIX index level.  If > 30 the regime is forced to
            ``HIGH_VOLATILITY`` regardless of other inputs.
        atr_ratio:
            Ratio of current ATR to historical mean ATR
            (``current_atr / mean(historical_atr)``).
        trend_strength:
            Normalised trend-strength score in ``[0.0, 1.0]``.
        current_atr:
            Optional raw current ATR value (used only for logging).

        Returns
        -------
        str
            One of the seven canonical regime identifiers.
        """
        # 1. VIX override
        if vix is not None and vix > self._VIX_HIGH_THRESHOLD:
            logger.debug("VIX=%.2f > %.0f → HIGH_VOLATILITY", vix, self._VIX_HIGH_THRESHOLD)
            return self.HIGH_VOLATILITY

        # 2. ATR-based volatility classification
        if atr_ratio < self._ATR_LOW_MULTIPLIER:
            regime = self.LOW_VOLATILITY
        elif atr_ratio > self._ATR_HIGH_MULTIPLIER:
            regime = self.HIGH_VOLATILITY
        elif self._CHOPPY_ATR_LOW <= atr_ratio <= self._CHOPPY_ATR_HIGH:
            # ATR is in the "normal" band — decide between CHOPPY and TRENDING
            if trend_strength < self._CHOPPY_TREND_MAX:
                regime = self.CHOPPY
            elif trend_strength > self._TREND_STRONG:
                # Direction determined by sign of trend_strength (caller provides
                # signed strength for TRENDING_UP vs TRENDING_DOWN).
                regime = self.TRENDING_UP if trend_strength > 0 else self.TRENDING_DOWN
            else:
                regime = self.MEAN_REVERTING
        else:
            # ATR ratio between low/high boundaries but outside choppy band
            if trend_strength > self._TREND_STRONG:
                regime = self.TRENDING_UP if trend_strength > 0 else self.TRENDING_DOWN
            else:
                regime = self.MEAN_REVERTING

        logger.debug(
            "detect_regime: vix=%s atr_ratio=%.3f trend=%.3f current_atr=%s → %s",
            vix,
            atr_ratio,
            trend_strength,
            current_atr,
            regime,
        )
        return regime

    def is_favorable_for_direction(
        self,
        regime: str,
        direction: str,
    ) -> bool:
        """Return whether *regime* supports the given trade *direction*.

        Parameters
        ----------
        regime:
            Regime identifier (one of the class constants).
        direction:
            ``"LONG"`` or ``"SHORT"``.

        Returns
        -------
        bool
            ``True`` if the regime is directionally compatible.
        """
        direction = direction.upper().strip()

        # HIGH_VOLATILITY and CHOPPY are hostile to *all* directional bets.
        if regime in (self.HIGH_VOLATILITY, self.CHOPPY):
            return False

        if regime == self.TRENDING_UP and direction == "SHORT":
            return False
        if regime == self.TRENDING_DOWN and direction == "LONG":
            return False

        # MEAN_REVERTING, LOW_VOLATILITY, UNKNOWN are neutral.
        return True

    def adjust_tp_sl_for_regime(
        self,
        base_tp: float,
        base_sl: float,
        regime: str,
        atr: float,
    ) -> tuple[float, float]:
        """Adapt take-profit and stop-loss levels to the current regime.

        Adjustments are multiplicative and optionally ATR-scaled:

        * **HIGH_VOLATILITY** → tighten TP, widen SL.
        * **LOW_VOLATILITY**  → widen TP, tighten SL.
        * **CHOPPY**          → moderate tightening of both.

        Parameters
        ----------
        base_tp:
            Base take-profit distance (price or ATR multiple).
        base_sl:
            Base stop-loss distance (price or ATR multiple).
        regime:
            Detected regime identifier.
        atr:
            Current ATR value (used as a sanity bound).

        Returns
        -------
        tuple[float, float]
            ``(adjusted_tp, adjusted_sl)`` — both strictly positive.
        """
        adj = self._TP_SL_ADJUSTMENTS.get(regime, self._TP_SL_ADJUSTMENTS[self.UNKNOWN])

        adjusted_tp: float = base_tp * adj["tp"]
        adjusted_sl: float = base_sl * adj["sl"]

        # ATR sanity floor — SL must be at least 0.5× ATR to avoid noise stops.
        min_sl: float = 0.5 * atr
        if adjusted_sl < min_sl:
            adjusted_sl = min_sl

        # TP must be at least 0.5× ATR to avoid microscopic targets.
        min_tp: float = 0.5 * atr
        if adjusted_tp < min_tp:
            adjusted_tp = min_tp

        logger.debug(
            "adjust_tp_sl: regime=%s base_tp=%.4f base_sl=%.4f "
            "adj_tp=%.4f adj_sl=%.4f atr=%.4f",
            regime,
            base_tp,
            base_sl,
            adjusted_tp,
            adjusted_sl,
            atr,
        )
        return adjusted_tp, adjusted_sl

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _mean_atr(historical_atr: list[float]) -> float:
        """Return the arithmetic mean of the historical ATR series.

        Falls back to ``1.0`` for empty series to avoid division by zero.
        """
        if not historical_atr:
            return 1.0
        return sum(historical_atr) / len(historical_atr)
