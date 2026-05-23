"""Health check for the trading engine.

Reads the feature-flag snapshot and returns a diagnostic dict:

    {
        "status": "healthy" | "degraded" | "unhealthy",
        "policy_version": "...",
        "last_policy_change_at": "...",
        "active_flags": ["flag_a", "flag_b"],
        "payload_lag_hours": 1.5 | None,
        "last_check": "2026-04-10T03:21:00+08:00",
    }

Thread-safe: every call re-reads flags through FeatureFlagManager
(which holds an RLock internally).
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any, Callable, Dict, List, Optional

from alpha_engine.feature_flags import FeatureFlagManager

# ── constants ───────────────────────────────────────────────────────

_TZ = timezone(timedelta(hours=8))

# Meta keys present in the flags JSON that are NOT boolean toggles
META_KEYS = {"policy_version", "last_policy_change_at"}

# Thresholds
_MAX_ACTIVE_FLAGS_HEALTHY = 1   # 0-1 flags → healthy
_MAX_ACTIVE_FLAGS_DEGRADED = 2  # 2 flags → degraded; ≥3 → degraded unless unhealthy
DEFAULT_MAX_LAG_HOURS = 24.0    # lag > this → unhealthy


# ── HealthChecker ───────────────────────────────────────────────────

class HealthChecker:
    """Stateless health-check runner.

    Parameters
    ----------
    flags : FeatureFlagManager
        The live flag manager.
    payload_lag_provider : callable, optional
        ``() -> float`` returning payload lag in hours.
        If *None*, lag is reported as ``None`` and does not affect status.
    max_lag_hours : float
        Lag threshold (hours) for *unhealthy* status.
    """

    def __init__(
        self,
        flags: FeatureFlagManager,
        *,
        payload_lag_provider: Optional[Callable[[], float]] = None,
        max_lag_hours: float = DEFAULT_MAX_LAG_HOURS,
    ) -> None:
        self._flags = flags
        self._lag_provider = payload_lag_provider
        self._max_lag = max_lag_hours

    # ── public API ──────────────────────────────────────────────────

    def check(self) -> Dict[str, Any]:
        """Run a health check and return the result dict."""
        now = datetime.now(_TZ)

        # Collect active (enabled) boolean flags
        all_flags = self._flags.list_flags()
        active: List[str] = sorted(
            k for k, v in all_flags.items()
            if k not in META_KEYS and v is True
        )

        # Payload lag
        lag = self._get_lag()

        # Status
        status = self._determine_status(active, lag)

        return {
            "status": status,
            "policy_version": self._flags.get("policy_version"),
            "last_policy_change_at": self._flags.get("last_policy_change_at"),
            "active_flags": active,
            "payload_lag_hours": lag,
            "last_check": now.isoformat(),
        }

    # ── internals ───────────────────────────────────────────────────

    def _get_lag(self) -> Optional[float]:
        if self._lag_provider is None:
            return None
        try:
            return float(self._lag_provider())
        except Exception:
            return None

    def _determine_status(
        self, active: List[str], lag: Optional[float]
    ) -> str:
        # Unhealthy: excessive payload lag
        if lag is not None and lag > self._max_lag:
            return "unhealthy"

        # Degraded: several flags active (engine in partial mode)
        if len(active) > _MAX_ACTIVE_FLAGS_DEGRADED:
            return "degraded"

        return "healthy"
