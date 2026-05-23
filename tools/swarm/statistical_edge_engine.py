"""
Statistical Edge Engine — Compute edge metrics per asset class.

This module evaluates trading performance across asset classes and derives
quantitative edge indicators: win-rate, expected-value, profit-factor,
Sharpe ratio (simplified), Kelly fraction, and drawdown.

Typical usage::

    from mysql_pick_adapter import MySQLPickAdapter
    from statistical_edge_engine import StatisticalEdgeEngine

    adapter = MySQLPickAdapter()
    picks   = adapter.fetch_all_closed()
    engine  = StatisticalEdgeEngine(picks)
    metrics = engine.compute_all_metrics()
"""

from __future__ import annotations

import logging
import math
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Tuple

logger = logging.getLogger("swarm.edge")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RISK_FREE_RATE: float = float(os.getenv("RISK_FREE_RATE", "0.0"))

EdgeStatus = Literal["STRONG_EDGE", "WEAK_EDGE", "NO_EDGE"]

# Thresholds used to classify edge strength
_EV_STRONG: float = 0.005
_PF_STRONG: float = 1.25


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class EdgeMetrics:
    """Aggregated performance metrics for a single asset class (or portfolio).

    Attributes
    ----------
    asset_class:
        Human-readable label, e.g. ``'crypto'`` or ``'portfolio'``.
    total_trades:
        Number of closed trades included in the sample.
    win_rate:
        Proportion of winning trades (0.0 – 1.0).
    avg_win:
        Average profit on winning trades (in price units or R-multiple).
    avg_loss:
        Average loss on losing trades (positive value).
    expected_value:
        Per-trade expected return (``win_rate * avg_win - (1-win_rate) * avg_loss``).
    profit_factor:
        Gross profit / gross loss.  ``math.inf`` when there are no losses.
    sharpe_ratio:
        Simplified Sharpe using the configured risk-free rate.
    kelly_fraction:
        Optimal position sizing fraction per Kelly criterion.
    max_drawdown_pct:
        Maximum peak-to-trough decline (percentage, 0-100).
    status_assessment:
        ``STRONG_EDGE``, ``WEAK_EDGE``, or ``NO_EDGE``.
    """

    asset_class: str
    total_trades: int = 0
    win_rate: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    expected_value: float = 0.0
    profit_factor: float = 0.0
    sharpe_ratio: float = 0.0
    kelly_fraction: float = 0.0
    max_drawdown_pct: float = 0.0
    status_assessment: EdgeStatus = "NO_EDGE"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a plain dictionary (JSON-friendly)."""
        return {
            "asset_class": self.asset_class,
            "total_trades": self.total_trades,
            "win_rate": round(self.win_rate, 6),
            "avg_win": round(self.avg_win, 6),
            "avg_loss": round(self.avg_loss, 6),
            "expected_value": round(self.expected_value, 6),
            "profit_factor": round(self.profit_factor, 6) if math.isfinite(self.profit_factor) else None,
            "sharpe_ratio": round(self.sharpe_ratio, 6),
            "kelly_fraction": round(self.kelly_fraction, 6),
            "max_drawdown_pct": round(self.max_drawdown_pct, 6),
            "status_assessment": self.status_assessment,
        }


@dataclass
class ConcentrationMetrics:
    """Portfolio-concentration diagnostics.

    Attributes
    ----------
    asset_class_shares:
        Mapping of asset class → proportion of total trades.
    herfindahl_index:
        Sum of squared shares (0 = perfectly diversified, 1 = concentrated).
    gini_coefficient:
        Gini coefficient of the trade-count distribution across asset classes.
    """

    asset_class_shares: Dict[str, float] = field(default_factory=dict)
    herfindahl_index: float = 0.0
    gini_coefficient: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "asset_class_shares": {
                k: round(v, 6) for k, v in self.asset_class_shares.items()
            },
            "herfindahl_index": round(self.herfindahl_index, 6),
            "gini_coefficient": round(self.gini_coefficient, 6),
        }


# ---------------------------------------------------------------------------
# Core engine
# ---------------------------------------------------------------------------

class StatisticalEdgeEngine:
    """Compute edge analytics from a list of pick dictionaries.

    Parameters
    ----------
    picks:
        Raw pick rows, e.g. as returned by
        :meth:`mysql_pick_adapter.MySQLPickAdapter.fetch_picks`.
    risk_free_rate:
        Annualised risk-free rate used in the simplified Sharpe calculation.
        Overrides the ``RISK_FREE_RATE`` environment variable.
    """

    def __init__(
        self,
        picks: List[Dict[str, Any]],
        risk_free_rate: Optional[float] = None,
    ) -> None:
        self._raw_picks: List[Dict[str, Any]] = picks
        self._risk_free_rate: float = (
            risk_free_rate if risk_free_rate is not None else RISK_FREE_RATE
        )
        logger.info(
            "StatisticalEdgeEngine initialised with %d pick(s), rf=%.4f",
            len(picks),
            self._risk_free_rate,
        )

    # -- internal helpers --------------------------------------------------

    @staticmethod
    def _trade_pnl(pick: Dict[str, Any]) -> Optional[float]:
        """Compute the realised PnL for a closed pick.

        Returns *None* when required price fields are missing.
        """
        entry: Optional[float] = pick.get("entry_price")
        exit_price: Optional[float] = pick.get("exit_price")
        direction: str = (pick.get("direction") or "").upper()
        qty: Optional[float] = pick.get("qty")

        if entry is None or exit_price is None:
            return None

        size = qty if qty is not None else 1.0
        if direction == "LONG":
            return (exit_price - entry) * size
        if direction == "SHORT":
            return (entry - exit_price) * size
        # Unknown direction — treat as simple delta
        return (exit_price - entry) * size

    @classmethod
    def _classify_status(
        cls, ev: float, pf: float
    ) -> EdgeStatus:
        """Classify edge strength based on EV and Profit-Factor thresholds."""
        if ev > _EV_STRONG and pf > _PF_STRONG:
            return "STRONG_EDGE"
        if ev > 0:
            return "WEAK_EDGE"
        return "NO_EDGE"

    @classmethod
    def _compute_for_subset(
        cls,
        label: str,
        picks: List[Dict[str, Any]],
        risk_free_rate: float,
    ) -> EdgeMetrics:
        """Derive :class:`EdgeMetrics` from a list of pick dicts."""
        logger.debug("Computing metrics for '%s' (%d picks)", label, len(picks))

        if not picks:
            logger.debug("Empty subset for '%s' — returning zeroed metrics", label)
            return EdgeMetrics(asset_class=label)

        pnls: List[float] = []
        wins: List[float] = []
        losses: List[float] = []

        for pick in picks:
            pnl = cls._trade_pnl(pick)
            if pnl is None:
                continue
            pnls.append(pnl)
            if pnl > 0:
                wins.append(pnl)
            elif pnl < 0:
                losses.append(abs(pnl))  # store as positive

        total_trades: int = len(pnls)
        if total_trades == 0:
            return EdgeMetrics(asset_class=label)

        win_rate: float = len(wins) / total_trades
        avg_win: float = sum(wins) / len(wins) if wins else 0.0
        avg_loss: float = sum(losses) / len(losses) if losses else 0.0
        gross_profit: float = sum(wins)
        gross_loss: float = sum(losses)

        expected_value: float = win_rate * avg_win - (1.0 - win_rate) * avg_loss

        profit_factor: float = (
            gross_profit / gross_loss if gross_loss > 0 else math.inf
        )

        # Sharpe (simplified) — mean excess return / std-dev of returns
        if len(pnls) >= 2:
            mean_pnl: float = sum(pnls) / len(pnls)
            variance: float = sum((x - mean_pnl) ** 2 for x in pnls) / (len(pnls) - 1)
            std_pnl: float = math.sqrt(variance) if variance > 0 else 0.0
            # Annualisation factor omitted — we treat each pick as one period
            sharpe_ratio: float = (
                (mean_pnl - risk_free_rate) / std_pnl if std_pnl > 0 else 0.0
            )
        else:
            sharpe_ratio = 0.0

        # Kelly fraction
        if avg_win > 0:
            kelly: float = (win_rate * avg_win - (1.0 - win_rate) * avg_loss) / avg_win
            kelly = max(0.0, kelly)  # clamp negative → 0
        else:
            kelly = 0.0

        # Max drawdown (running equity curve)
        max_drawdown_pct = cls._max_drawdown_pct(pnls)

        status = cls._classify_status(expected_value, profit_factor)

        return EdgeMetrics(
            asset_class=label,
            total_trades=total_trades,
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            expected_value=expected_value,
            profit_factor=profit_factor,
            sharpe_ratio=sharpe_ratio,
            kelly_fraction=kelly,
            max_drawdown_pct=max_drawdown_pct,
            status_assessment=status,
        )

    @staticmethod
    def _max_drawdown_pct(pnls: List[float]) -> float:
        """Compute maximum drawdown as a percentage of peak equity.

        Parameters
        ----------
        pnls:
            Ordered list of per-trade PnL values.

        Returns
        -------
        float
            Maximum drawdown in percent (0 – 100).
        """
        peak = 0.0
        equity = 0.0
        max_dd = 0.0
        for pnl in pnls:
            equity += pnl
            if equity > peak:
                peak = equity
            if peak > 0:
                dd = (peak - equity) / peak
                if dd > max_dd:
                    max_dd = dd
        return max_dd * 100.0

    # -- public API --------------------------------------------------------

    def compute_all_metrics(self) -> Dict[str, EdgeMetrics]:
        """Compute :class:`EdgeMetrics` for every asset class.

        Returns
        -------
        dict[str, EdgeMetrics]
            Mapping ``asset_class → EdgeMetrics``.
        """
        logger.info("compute_all_metrics() — %d raw pick(s)", len(self._raw_picks))

        # Group picks by asset_class
        buckets: Dict[str, List[Dict[str, Any]]] = {}
        for pick in self._raw_picks:
            ac: str = (pick.get("asset_class") or "unknown").lower()
            buckets.setdefault(ac, []).append(pick)

        result: Dict[str, EdgeMetrics] = {}
        for ac, subset in buckets.items():
            result[ac] = self._compute_for_subset(
                ac, subset, self._risk_free_rate
            )
            logger.info(
                "%s — trades=%d ev=%.4f pf=%.4f status=%s",
                ac,
                result[ac].total_trades,
                result[ac].expected_value,
                result[ac].profit_factor,
                result[ac].status_assessment,
            )
        return result

    def compute_portfolio_metrics(self) -> EdgeMetrics:
        """Compute aggregate metrics across **all** picks.

        Returns
        -------
        EdgeMetrics
            Portfolio-level statistics with ``asset_class='portfolio'``.
        """
        logger.info("compute_portfolio_metrics()")
        return self._compute_for_subset(
            "portfolio", self._raw_picks, self._risk_free_rate
        )

    def compute_concentration_index(self) -> ConcentrationMetrics:
        """Calculate Herfindahl index and Gini coefficient.

        Both metrics are computed on the **trade-count** distribution across
        asset classes.

        Returns
        -------
        ConcentrationMetrics
        """
        logger.info("compute_concentration_index()")
        counts: Dict[str, int] = {}
        for pick in self._raw_picks:
            ac: str = (pick.get("asset_class") or "unknown").lower()
            counts[ac] = counts.get(ac, 0) + 1

        total = sum(counts.values())
        if total == 0:
            return ConcentrationMetrics()

        shares: Dict[str, float] = {
            k: v / total for k, v in counts.items()
        }
        hhi: float = sum(s ** 2 for s in shares.values())

        # Gini coefficient (discrete form)
        sorted_shares: List[float] = sorted(shares.values())
        n = len(sorted_shares)
        cumsum: float = 0.0
        for i, s in enumerate(sorted_shares, start=1):
            cumsum += (2 * i - n - 1) * s
        gini: float = cumsum / (n * sum(sorted_shares)) if sum(sorted_shares) > 0 else 0.0

        logger.info(
            "Concentration — HHI=%.4f Gini=%.4f classes=%d",
            hhi,
            gini,
            n,
        )
        return ConcentrationMetrics(
            asset_class_shares=shares,
            herfindahl_index=hhi,
            gini_coefficient=gini,
        )

    def alert_on_degradation(
        self, threshold_ev: float = 0.005
    ) -> List[Dict[str, Any]]:
        """Flag asset classes whose expected value has fallen below *threshold_ev*.

        Parameters
        ----------
        threshold_ev:
            Minimum acceptable expected value.

        Returns
        -------
        list[dict]
            Each dict contains ``asset_class``, ``expected_value``,
            ``status_assessment``, and ``severity`` (``'critical'`` or
            ``'warning'``).
        """
        logger.info("alert_on_degradation(threshold_ev=%.4f)", threshold_ev)
        all_metrics = self.compute_all_metrics()
        alerts: List[Dict[str, Any]] = []

        for ac, metrics in all_metrics.items():
            if metrics.expected_value < threshold_ev:
                severity: str = (
                    "critical"
                    if metrics.status_assessment == "NO_EDGE"
                    else "warning"
                )
                alerts.append(
                    {
                        "asset_class": ac,
                        "expected_value": round(metrics.expected_value, 6),
                        "status_assessment": metrics.status_assessment,
                        "severity": severity,
                    }
                )
                logger.warning(
                    "Degradation alert — %s: EV=%.4f [%s]",
                    ac,
                    metrics.expected_value,
                    severity,
                )
        return alerts

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"picks={len(self._raw_picks)}, "
            f"rf={self._risk_free_rate})"
        )
