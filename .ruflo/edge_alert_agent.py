"""
Edge Alert Agent — monitors edge metrics and sends alerts when degradation
or concentration risk is detected.

This agent plugs into the .ruflo orchestrator's continuous swarm pipeline
to provide real-time alerting on trading edge health, win-rate decay,
drawdown breaches, and portfolio concentration.
"""

from __future__ import annotations

import copy
import logging
from collections import Counter
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("ruflo.alerts")


class EdgeAlertAgent:
    """Agent that monitors edge metrics and emits structured alerts.

    Alert levels
    ------------
    INFO
        Informational — no action required.
    WARNING
        Caution — reduce risk or investigate.
    CRITICAL
        Immediate action required — stop trading or close positions.
    EMERGENCY
        Catastrophic — halt all strategies, escalate to human.

    Default thresholds
    ------------------
    - EV < 0           → CRITICAL
    - EV < 0.002       → WARNING
    - Win rate < 45% (≥20 trades) → WARNING
    - Profit factor < 1.0           → WARNING
    - Max drawdown > 20%            → CRITICAL
    - HHI > 0.30                    → WARNING
    """

    DEFAULT_THRESHOLDS: dict[str, dict[str, Any]] = {
        "ev": {"critical": 0.0, "warning": 0.002},
        "win_rate": {"warning": 0.45, "min_trades": 20},
        "profit_factor": {"warning": 1.0},
        "max_drawdown": {"critical": 0.20},
        "hhi": {"warning": 0.30},
    }

    # In-memory buffer of active alerts for digest generation
    _active_alerts: list[dict[str, Any]] = []

    def __init__(self, alert_thresholds: dict[str, Any] | None = None) -> None:
        """Initialize the alert agent.

        Parameters
        ----------
        alert_thresholds:
            Override defaults. Expected shape mirrors
            ``DEFAULT_THRESHOLDS``.
        """
        self._thresholds: dict[str, Any] = copy.deepcopy(self.DEFAULT_THRESHOLDS)
        if alert_thresholds:
            for metric, levels in alert_thresholds.items():
                if metric in self._thresholds:
                    self._thresholds[metric].update(levels)
                else:
                    self._thresholds[metric] = levels
        logger.info("EdgeAlertAgent initialized — thresholds=%s", self._thresholds)

    # ------------------------------------------------------------------
    # Core alert engine
    # ------------------------------------------------------------------

    def check_edge_status(self, metrics: dict[str, Any]) -> list[dict[str, Any]]:
        """Evaluate a bundle of edge metrics and return any alerts.

        Parameters
        ----------
        metrics:
            Expected keys: ``asset_class`` (str), ``ev`` (float),
            ``win_rate`` (float), ``profit_factor`` (float),
            ``max_drawdown`` (float), ``trade_count`` (int, optional).

        Returns
        -------
        list[dict]
            Each alert carries: ``timestamp``, ``asset_class``,
            ``metric_name``, ``current_value``, ``threshold``,
            ``level``, ``recommended_action``.
        """
        alerts: list[dict[str, Any]] = []
        asset_class: str = metrics.get("asset_class", "unknown")
        ts = datetime.now(timezone.utc).isoformat()

        # --- Expected Value ---
        ev: float | None = metrics.get("ev")
        if ev is not None:
            ev_critical = self._thresholds["ev"]["critical"]
            ev_warning = self._thresholds["ev"]["warning"]
            if ev < ev_critical:
                alerts.append({
                    "timestamp": ts,
                    "asset_class": asset_class,
                    "metric_name": "expected_value",
                    "current_value": round(ev, 6),
                    "threshold": ev_critical,
                    "level": "CRITICAL",
                    "recommended_action": f"Stop trading {asset_class} — edge is negative",
                })
            elif ev < ev_warning:
                alerts.append({
                    "timestamp": ts,
                    "asset_class": asset_class,
                    "metric_name": "expected_value",
                    "current_value": round(ev, 6),
                    "threshold": ev_warning,
                    "level": "WARNING",
                    "recommended_action": f"Reduce position size for {asset_class}",
                })

        # --- Win Rate ---
        win_rate: float | None = metrics.get("win_rate")
        trade_count: int = metrics.get("trade_count", 0)
        if win_rate is not None and trade_count >= self._thresholds["win_rate"]["min_trades"]:
            wr_threshold = self._thresholds["win_rate"]["warning"]
            if win_rate < wr_threshold:
                alerts.append({
                    "timestamp": ts,
                    "asset_class": asset_class,
                    "metric_name": "win_rate",
                    "current_value": round(win_rate, 4),
                    "threshold": wr_threshold,
                    "level": "WARNING",
                    "recommended_action": (
                        f"Review {asset_class} strategy — win rate below "
                        f"{wr_threshold * 100:.0f}% over {trade_count} trades"
                    ),
                })

        # --- Profit Factor ---
        pf: float | None = metrics.get("profit_factor")
        if pf is not None:
            pf_threshold = self._thresholds["profit_factor"]["warning"]
            if pf < pf_threshold:
                alerts.append({
                    "timestamp": ts,
                    "asset_class": asset_class,
                    "metric_name": "profit_factor",
                    "current_value": round(pf, 4),
                    "threshold": pf_threshold,
                    "level": "WARNING",
                    "recommended_action": (
                        f"{asset_class} profit factor below 1.0 — gross losses "
                        f"exceed gross profits"
                    ),
                })

        # --- Max Drawdown ---
        mdd: float | None = metrics.get("max_drawdown")
        if mdd is not None:
            mdd_threshold = self._thresholds["max_drawdown"]["critical"]
            if mdd > mdd_threshold:
                level = "EMERGENCY" if mdd > 0.35 else "CRITICAL"
                alerts.append({
                    "timestamp": ts,
                    "asset_class": asset_class,
                    "metric_name": "max_drawdown",
                    "current_value": round(mdd, 4),
                    "threshold": mdd_threshold,
                    "level": level,
                    "recommended_action": (
                        f"HALT {asset_class} — drawdown {mdd * 100:.1f}% exceeds "
                        f"{mdd_threshold * 100:.0f}% limit"
                    ),
                })

        # Persist to active buffer
        self._active_alerts.extend(alerts)
        if alerts:
            logger.warning("EdgeAlertAgent produced %d alert(s) for %s", len(alerts), asset_class)
        return alerts

    def check_concentration_risk(self, picks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Check portfolio concentration using the Herfindahl–Hirschman Index.

        Parameters
        ----------
        picks:
            List of pick dicts, each with at least ``ticker`` and
            optionally ``notional`` or ``weight``.

        Returns
        -------
        list[dict]
            Alert dicts when HHI exceeds the warning threshold.
        """
        alerts: list[dict[str, Any]] = []
        if not picks:
            return alerts

        ts = datetime.now(timezone.utc).isoformat()

        # Compute weights by ticker
        tickers = [p.get("ticker", "UNKNOWN") for p in picks]
        counts = Counter(tickers)
        total = len(tickers)
        weights = {t: c / total for t, c in counts.items()}

        hhi = sum(w**2 for w in weights.values())
        hhi_threshold = self._thresholds["hhi"]["warning"]

        if hhi > hhi_threshold:
            top_3 = counts.most_common(3)
            alerts.append({
                "timestamp": ts,
                "asset_class": "portfolio",
                "metric_name": "concentration_hhi",
                "current_value": round(hhi, 4),
                "threshold": hhi_threshold,
                "level": "WARNING",
                "recommended_action": (
                    f"Portfolio over-concentrated (HHI={hhi:.3f}). "
                    f"Top holdings: {top_3}. Diversify or apply risk parity."
                ),
            })

        self._active_alerts.extend(alerts)
        if alerts:
            logger.warning("Concentration risk detected — HHI=%.3f", hhi)
        return alerts

    def format_alert_message(self, alert: dict[str, Any]) -> str:
        """Render a single alert as a human-readable string.

        Parameters
        ----------
        alert:
            Alert dict produced by this agent.

        Returns
        -------
        str
            Multi-line formatted alert message.
        """
        lines = [
            f"[{alert.get('level', 'INFO')}] {alert.get('asset_class', 'unknown').upper()}",
            f"  Metric      : {alert.get('metric_name', 'N/A')}",
            f"  Value       : {alert.get('current_value', 'N/A')}",
            f"  Threshold   : {alert.get('threshold', 'N/A')}",
            f"  Action      : {alert.get('recommended_action', 'N/A')}",
            f"  Time        : {alert.get('timestamp', 'N/A')}",
        ]
        return "\n".join(lines)

    def should_escalate(self, alert_history: list[dict[str, Any]]) -> bool:
        """Determine whether an alert should be escalated.

        Escalation triggers when the same ``(asset_class, metric_name)`` pair
        appears ≥ 3 times within the last 24 hours.

        Parameters
        ----------
        alert_history:
            Chronological list of alert dicts.

        Returns
        -------
        bool
            *True* if repeated critical conditions warrant escalation.
        """
        if not alert_history:
            return False

        # Count occurrences of (asset, metric) in recent history
        from collections import Counter as _Counter
        pairs = [
            (a.get("asset_class"), a.get("metric_name"))
            for a in alert_history[-50:]  # last 50 alerts
        ]
        counts = _Counter(pairs)
        most_common = counts.most_common(1)

        if most_common and most_common[0][1] >= 3:
            logger.critical(
                "Escalation triggered — %s repeated %d times",
                most_common[0][0],
                most_common[0][1],
            )
            return True

        return False

    def generate_alert_digest(self) -> str:
        """Generate a Markdown digest of all current active alerts.

        Returns
        -------
        str
            Markdown-formatted summary.
        """
        if not self._active_alerts:
            return "# Edge Alert Digest\n\n✅ No active alerts.\n"

        lines: list[str] = [
            "# Edge Alert Digest",
            f"\n*Generated: {datetime.now(timezone.utc).isoformat()}*\n",
        ]

        grouped: dict[str, list[dict[str, Any]]] = {}
        for alert in self._active_alerts:
            level = alert.get("level", "INFO")
            grouped.setdefault(level, []).append(alert)

        for level in ("EMERGENCY", "CRITICAL", "WARNING", "INFO"):
            alerts = grouped.get(level, [])
            if not alerts:
                continue
            icon = {"EMERGENCY": "🔴", "CRITICAL": "🟠", "WARNING": "🟡", "INFO": "🔵"}.get(level, "⚪")
            lines.append(f"\n## {icon} {level} ({len(alerts)})\n")
            for alert in alerts:
                lines.append(f"**{alert.get('asset_class', 'unknown').upper()}** — ")
                lines.append(f"`{alert.get('metric_name')}` = {alert.get('current_value')}")
                lines.append(f"  *{alert.get('recommended_action')}*  ")
                lines.append(f"  _{alert.get('timestamp')}_\n")

        # Check for escalation
        if self.should_escalate(self._active_alerts):
            lines.append("\n---\n")
            lines.append(
                "## ⬆️ ESCALATION REQUIRED\n"
                "Repeated alerts detected. Manual review and intervention recommended.\n"
            )

        return "\n".join(lines)
