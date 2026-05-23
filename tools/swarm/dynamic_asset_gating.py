"""
Dynamic Asset Gating Controller

Production-grade module for per-asset-class signal clearance and position scaling
based on statistical edge (expected value) and Kelly criterion sizing.

Intended for use within the swarm risk-management layer (PR-2).
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("swarm.gating")


class DynamicAssetGatingController:
    """Controls signal execution clearance and position sizing per asset class.

    The controller evaluates whether a trading signal should be permitted to execute
    based on the current expected value (EV) of the asset class relative to a
    configurable hurdle rate. It also applies Kelly-criterion-based position scaling
    with a quarter-Kelly safety cap.

    Emergency kill-switch support allows instant global shutdown of all signal
    routing, e.g. during market stress or operational incidents.

    Parameters
    ----------
    target_asset_class:
        The asset class this controller instance manages (e.g. ``"equities"``,
        ``"crypto"``, ``"fixed_income"``).
    hurdle_rate_ev:
        Minimum expected-value threshold a signal must clear before execution is
        permitted.  Default ``0.005`` (50 bps).
    emergency_kill_switch:
        If ``True``, *all* signals are blocked regardless of EV.  Default ``False``.
    """

    # Safety cap on Kelly fraction — quarter-Kelly to avoid overbetting.
    _KELLY_CAP: float = 0.25

    # Default number of days without edge before auto-kill engages.
    _DEFAULT_STALE_DAYS: int = 30

    def __init__(
        self,
        target_asset_class: str,
        hurdle_rate_ev: float = 0.005,
        emergency_kill_switch: bool = False,
    ) -> None:
        self.target_asset_class: str = target_asset_class
        self.hurdle_rate_ev: float = hurdle_rate_ev
        self.emergency_kill_switch: bool = emergency_kill_switch

        # Per-asset-class mutable state
        self._last_edge_timestamp: datetime | None = None
        self._days_without_edge: int = 0
        self._gating_rules: dict[str, Any] = {}
        self._kill_history: list[dict[str, str]] = []

        logger.info(
            "DynamicAssetGatingController initialised for asset_class=%s "
            "hurdle_rate_ev=%.4f kill_switch=%s",
            target_asset_class,
            hurdle_rate_ev,
            emergency_kill_switch,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def evaluate_signal_clearance(
        self,
        current_ev: float,
        signal: dict[str, Any],
    ) -> dict[str, Any]:
        """Evaluate whether *signal* is cleared for execution.

        The decision tree is:

        1. If the global emergency kill switch is active → **reject**.
        2. If the asset class has been stale (no edge) for too long → **reject**.
        3. If *current_ev* < *hurdle_rate_ev* → **reject**.
        4. Otherwise → **permit**.

        Parameters
        ----------
        current_ev:
            The latest expected-value estimate for the asset class.
        signal:
            A dict describing the incoming signal.  Must contain at least a
            ``"ticker"`` key.

        Returns
        -------
        dict
            ``{"ticker": str, "execution_permitted": bool,
            "allocated_capital_fraction": float,
            "routing_rejection_reason": str | None}``
        """
        ticker: str = signal.get("ticker", "UNKNOWN")
        result: dict[str, Any] = {
            "ticker": ticker,
            "execution_permitted": False,
            "allocated_capital_fraction": 0.0,
            "routing_rejection_reason": None,
        }

        # 1. Emergency kill switch
        if self.emergency_kill_switch:
            result["routing_rejection_reason"] = (
                "GLOBAL_EMERGENCY_KILL_SWITCH_ACTIVE"
            )
            logger.warning(
                "Signal %s rejected: emergency kill switch is active", ticker
            )
            return result

        # 2. Stale-edge auto-kill
        if self._is_stale():
            result["routing_rejection_reason"] = (
                f"STALE_EDGE_AUTO_KILL_{self._days_without_edge}D"
            )
            logger.warning(
                "Signal %s rejected: no edge for %d days",
                ticker,
                self._days_without_edge,
            )
            return result

        # 3. Hurdle-rate gate
        if current_ev < self.hurdle_rate_ev:
            result["routing_rejection_reason"] = (
                f"EV_BELOW_HURDLE|ev={current_ev:.6f}"
                f"|hurdle={self.hurdle_rate_ev:.6f}"
            )
            self._days_without_edge += 1
            logger.info(
                "Signal %s rejected: EV %.6f below hurdle %.6f",
                ticker,
                current_ev,
                self.hurdle_rate_ev,
            )
            return result

        # 4. Signal permitted
        result["execution_permitted"] = True
        self._last_edge_timestamp = datetime.now(timezone.utc)
        self._days_without_edge = 0

        # Compute capital fraction via Kelly scaling
        edge_metrics = signal.get("edge_metrics", {})
        base_allocation = signal.get("base_allocation", 1.0)
        result["allocated_capital_fraction"] = self.scale_position_size(
            edge_metrics, base_allocation
        )

        logger.info(
            "Signal %s cleared: fraction=%.4f ev=%.6f",
            ticker,
            result["allocated_capital_fraction"],
            current_ev,
        )
        return result

    def scale_position_size(
        self,
        edge_metrics: dict[str, float],
        base_allocation: float,
    ) -> float:
        """Kelly-adjusted position sizing capped at quarter-Kelly.

        The simplified Kelly fraction is computed as::

            kelly = edge / odds

        where *edge* is the expected return advantage and *odds* represent the
        average win/loss payoff ratio.  The result is multiplied by
        *base_allocation* and hard-capped at ``0.25``.

        Parameters
        ----------
        edge_metrics:
            Dict expected to contain ``"edge"`` (float) and optionally
            ``"odds"`` (float, default ``1.0``).
        base_allocation:
            The baseline capital allocation for this signal (0.0‑1.0 scale).

        Returns
        -------
        float
            Final fractional position size in ``[0.0, 0.25]``.
        """
        edge: float = edge_metrics.get("edge", 0.0)
        odds: float = edge_metrics.get("odds", 1.0)

        if odds <= 0:
            logger.warning("Invalid odds=%.4f; defaulting to 1.0", odds)
            odds = 1.0

        if edge <= 0:
            logger.debug("Non-positive edge=%.6f → zero sizing", edge)
            return 0.0

        kelly_fraction: float = edge / odds
        # Quarter-Kelly safety cap
        safe_fraction: float = min(kelly_fraction, self._KELLY_CAP)
        scaled_size: float = safe_fraction * base_allocation

        logger.debug(
            "scale_position_size: edge=%.4f odds=%.4f kelly=%.4f "
            "safe=%.4f base=%.4f final=%.4f",
            edge,
            odds,
            kelly_fraction,
            safe_fraction,
            base_allocation,
            scaled_size,
        )
        return scaled_size

    def emergency_kill_all(self, reason: str) -> None:
        """Activate the global emergency kill switch.

        Once engaged, :py:meth:`evaluate_signal_clearance` will reject **all**
        subsequent signals until the switch is manually reset.

        Parameters
        ----------
        reason:
            Human-readable explanation for the kill (stored in history).
        """
        self.emergency_kill_switch = True
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "reason": reason,
            "asset_class": self.target_asset_class,
        }
        self._kill_history.append(entry)
        logger.critical(
            "EMERGENCY KILL activated for %s | reason=%s",
            self.target_asset_class,
            reason,
        )

    def load_gating_rules(
        self,
        rules_path: str | None = None,
    ) -> dict[str, Any]:
        """Load per-asset-class gating rules from a JSON file.

        If *rules_path* is not provided, the method looks for a file named
        ``gating_rules.json`` in the same directory as this module.

        Parameters
        ----------
        rules_path:
            Absolute or relative path to the JSON rules file.

        Returns
        -------
        dict
            The loaded rules dictionary (empty if file missing or malformed).
        """
        if rules_path is None:
            rules_path = os.path.join(
                os.path.dirname(__file__), "gating_rules.json"
            )

        try:
            with open(rules_path, "r", encoding="utf-8") as fh:
                self._gating_rules = json.load(fh)
            logger.info(
                "Gating rules loaded from %s (%d top-level keys)",
                rules_path,
                len(self._gating_rules),
            )
        except FileNotFoundError:
            logger.warning("Gating rules file not found: %s", rules_path)
            self._gating_rules = {}
        except json.JSONDecodeError as exc:
            logger.error("Invalid JSON in %s: %s", rules_path, exc)
            self._gating_rules = {}

        return self._gating_rules

    def save_gating_state(self, state_path: str) -> None:
        """Persist the current controller state to disk.

        The saved state includes kill-switch status, last-edge timestamp,
        days-without-edge counter, and kill history.

        Parameters
        ----------
        state_path:
            Destination file path (JSON).
        """
        state: dict[str, Any] = {
            "target_asset_class": self.target_asset_class,
            "hurdle_rate_ev": self.hurdle_rate_ev,
            "emergency_kill_switch": self.emergency_kill_switch,
            "last_edge_timestamp": (
                self._last_edge_timestamp.isoformat()
                if self._last_edge_timestamp
                else None
            ),
            "days_without_edge": self._days_without_edge,
            "kill_history": self._kill_history,
        }

        os.makedirs(os.path.dirname(state_path), exist_ok=True)
        with open(state_path, "w", encoding="utf-8") as fh:
            json.dump(state, fh, indent=2)

        logger.info("Gating state saved to %s", state_path)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _is_stale(self) -> bool:
        """Return ``True`` if edge has been missing longer than the stale threshold."""
        return self._days_without_edge >= self._DEFAULT_STALE_DAYS
