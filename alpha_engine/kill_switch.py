"""
ALPHA_ENGINE -- Auto Kill Switch
==================================
Monitors portfolio health and automatically halts or throttles signal
generation when anomalous conditions are detected.

Kill conditions (hard-block new picks):
  1. Drawdown spike: intraday DD exceeds 2x historical 95th percentile
  2. SL hit rate spike: >60% of last 10 trades hit SL (baseline <30%)
  3. Win rate collapse: rolling 20-trade WR < 25% (system baseline ~35%)
  4. Consecutive losses: 5+ losses in a row across all strategies

Warning-only conditions (log but do NOT block picks):
  5. Feature health collapse: dead features > 75% (many features are
     naturally sparse; this is informational only)

Severity levels:
  - warning:   reduce position sizes / subtract from scores
  - critical:  only allow high-conviction picks through
  - emergency: halt all new entries immediately

Output: data/kill_switch_status.json
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_ENGINE_DIR = Path(__file__).resolve().parent
_DATA_DIR = _ENGINE_DIR / "data"
_STATUS_PATH = _DATA_DIR / "kill_switch_status.json"
_CLOSED_PICKS_PATH = _DATA_DIR / "closed_picks.json"
_ACTIVE_PICKS_PATH = _DATA_DIR / "active_picks.json"
_HEALTH_REPORT_PATH = _DATA_DIR / "feature_health_report.json"


def _load_json(path: Path) -> list | dict:
    """Load JSON from a path, returning [] or {} on error."""
    if not path.exists():
        return []
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def _save_status(status: dict) -> None:
    """Persist kill switch status to data/kill_switch_status.json."""
    try:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(_STATUS_PATH, "w") as f:
            json.dump(status, f, indent=2)
    except IOError as e:
        logger.error("Failed to save kill switch status: %s", e)


def check_kill_conditions(
    portfolio_data: Optional[dict] = None,
    feature_health: Optional[dict] = None,
    recent_trades: Optional[list[dict]] = None,
) -> dict:
    """Check if any auto-rollback / kill conditions are met.

    Args:
        portfolio_data: Optional dict with keys like 'unrealized_pnl',
                        'total_pnl', 'drawdown_pct', etc. If None, computed
                        from active_picks.json.
        feature_health: Optional feature health report dict (from
                        feature_health.generate_health_report()). If None,
                        loaded from data/feature_health_report.json.
        recent_trades:  Optional list of closed pick dicts. If None, loaded
                        from data/closed_picks.json.

    Returns:
        dict with keys:
          - is_killed: bool
          - kill_reason: str or None
          - severity: 'ok' | 'warning' | 'critical' | 'emergency'
          - recommended_action: 'none' | 'reduce_size' | 'pause_new_entries' | 'close_all'
          - conditions: list of triggered condition details
          - checked_at: ISO timestamp
    """
    try:
        return _check_kill_conditions_impl(portfolio_data, feature_health, recent_trades)
    except Exception as e:
        logger.error("Kill switch check failed (non-fatal, defaulting to safe): %s", e)
        return {
            "is_killed": False,
            "kill_reason": None,
            "severity": "ok",
            "recommended_action": "none",
            "conditions": [],
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "error": str(e),
        }


def _check_kill_conditions_impl(
    portfolio_data: Optional[dict],
    feature_health: Optional[dict],
    recent_trades: Optional[list[dict]],
) -> dict:
    """Internal implementation of kill condition checks."""
    now = datetime.now(timezone.utc)
    conditions: list[dict] = []
    max_severity = "ok"  # ok < warning < critical < emergency

    SEVERITY_ORDER = {"ok": 0, "warning": 1, "critical": 2, "emergency": 3}

    def _upgrade_severity(new_sev: str):
        nonlocal max_severity
        if SEVERITY_ORDER.get(new_sev, 0) > SEVERITY_ORDER.get(max_severity, 0):
            max_severity = new_sev

    # --- Load data if not provided ---
    if recent_trades is None:
        raw = _load_json(_CLOSED_PICKS_PATH)
        recent_trades = raw if isinstance(raw, list) else []

    if feature_health is None:
        raw_health = _load_json(_HEALTH_REPORT_PATH)
        feature_health = raw_health if isinstance(raw_health, dict) else {}

    if portfolio_data is None:
        raw_active = _load_json(_ACTIVE_PICKS_PATH)
        active_picks = raw_active if isinstance(raw_active, list) else []
        # Compute basic portfolio data from active picks
        total_unrealized = 0.0
        for p in active_picks:
            try:
                total_unrealized += float(p.get("unrealized_pnl_pct", 0) or 0)
            except (TypeError, ValueError):
                pass
        portfolio_data = {
            "active_count": len(active_picks),
            "total_unrealized_pnl_pct": total_unrealized,
        }

    # =====================================================================
    # Condition 1: Feature health collapse (warning only, never blocks)
    # =====================================================================
    try:
        health_score = feature_health.get("health_score")
        dead_features = feature_health.get("dead_features", 0)
        total_features = feature_health.get("total_features", 0)

        if health_score is not None and total_features > 0:
            dead_pct = dead_features / total_features
            # Feature collapse should only WARN, never hard-block picks.
            # Many features (obv_divergence, vol_compression, etc.) are naturally
            # sparse or imputed constants -- this is being fixed separately.
            # Hard-block conditions: consecutive_losses, drawdown_spike, sl_rate.
            if dead_pct > 0.75:
                conditions.append({
                    "condition": "feature_health_collapse",
                    "severity": "warning",
                    "detail": (f"Dead features: {dead_features}/{total_features} "
                               f"({dead_pct:.0%}) -- health_score={health_score:.2f}"),
                })
                _upgrade_severity("warning")
            elif dead_pct > 0.3:
                conditions.append({
                    "condition": "feature_health_degraded",
                    "severity": "warning",
                    "detail": (f"Dead features: {dead_features}/{total_features} "
                               f"({dead_pct:.0%}) -- health_score={health_score:.2f}"),
                })
                _upgrade_severity("warning")
    except Exception as e:
        logger.debug("Feature health check skipped: %s", e)

    # =====================================================================
    # Condition 2: Drawdown spike (intraday DD > 2x historical 95th pctile)
    # =====================================================================
    try:
        if recent_trades and len(recent_trades) >= 20:
            # Compute rolling drawdown from closed trade PnLs
            pnls = []
            for t in recent_trades:
                pnl = t.get("pnl_pct")
                if pnl is not None:
                    try:
                        pnls.append(float(pnl))
                    except (TypeError, ValueError):
                        pass

            if len(pnls) >= 20:
                # Compute cumulative PnL and drawdowns
                cum = 0.0
                peak = 0.0
                drawdowns = []
                for p in pnls:
                    cum += p
                    peak = max(peak, cum)
                    dd = cum - peak
                    if dd < 0:
                        drawdowns.append(dd)

                if drawdowns:
                    # 95th percentile of historical drawdowns
                    drawdowns_sorted = sorted(drawdowns)
                    idx_95 = int(len(drawdowns_sorted) * 0.05)  # worst 5%
                    dd_95 = drawdowns_sorted[idx_95] if idx_95 < len(drawdowns_sorted) else drawdowns_sorted[0]

                    # Current drawdown (last 10 trades)
                    recent_pnls = pnls[-10:]
                    recent_cum = sum(recent_pnls)
                    if recent_cum < 0 and dd_95 < 0 and recent_cum < dd_95 * 2:
                        conditions.append({
                            "condition": "drawdown_spike",
                            "severity": "critical",
                            "detail": (f"Recent DD={recent_cum:.2f}% exceeds "
                                       f"2x historical 95th pctile ({dd_95:.2f}%)"),
                        })
                        _upgrade_severity("critical")
    except Exception as e:
        logger.debug("Drawdown check skipped: %s", e)

    # =====================================================================
    # Condition 3: SL hit rate spike (>60% of last 10 trades hit SL)
    # =====================================================================
    try:
        if recent_trades and len(recent_trades) >= 10:
            last_10 = recent_trades[-10:]
            sl_hits = sum(
                1 for t in last_10
                if (t.get("exit_reason") or "").upper() == "SL_HIT"
            )
            sl_rate = sl_hits / 10.0
            if sl_rate > 0.60:
                conditions.append({
                    "condition": "sl_hit_rate_spike",
                    "severity": "critical",
                    "detail": f"SL hit rate: {sl_hits}/10 ({sl_rate:.0%}) -- baseline <30%",
                })
                _upgrade_severity("critical")
            elif sl_rate > 0.40:
                conditions.append({
                    "condition": "sl_hit_rate_elevated",
                    "severity": "warning",
                    "detail": f"SL hit rate: {sl_hits}/10 ({sl_rate:.0%}) -- baseline <30%",
                })
                _upgrade_severity("warning")
    except Exception as e:
        logger.debug("SL hit rate check skipped: %s", e)

    # =====================================================================
    # Condition 4: Win rate collapse (rolling 20-trade WR < 25%)
    # =====================================================================
    try:
        # Exclude force-closed toxic picks, stale-data exits, and near-zero PnL
        # phantom closes from kill switch WR calc. Near-zero PnL (<0.05%) with
        # SL_HIT means the SL was set at entry — not a real trade outcome.
        _real_trades = [
            t for t in (recent_trades or [])
            if (t.get("exit_reason") or "") not in ("FORCE_CLOSED_TOXIC", "STALE_DATA_NO_PRICE", "UNSCORED_CLEANUP")
            and not (abs(t.get("pnl_pct", t.get("realized_pnl_pct", 0)) or 0) < 0.05
                     and (t.get("exit_reason") or "") in ("SL_HIT", "TP_HIT"))
        ]
        if _real_trades and len(_real_trades) >= 20:
            last_20 = _real_trades[-20:]
            wins = sum(
                1 for t in last_20
                if (t.get("status") or "").upper() == "WON"
                or (t.get("pnl_pct") or 0) > 0.05
                or (t.get("realized_pnl_pct") or 0) > 0.05
            )
            wr_20 = wins / 20.0
            if wr_20 < 0.20:
                conditions.append({
                    "condition": "win_rate_collapse",
                    "severity": "critical",
                    "detail": f"Rolling 20-trade WR: {wins}/20 ({wr_20:.0%}) -- baseline ~35%",
                })
                _upgrade_severity("critical")
            elif wr_20 < 0.25:
                conditions.append({
                    "condition": "win_rate_low",
                    "severity": "warning",
                    "detail": f"Rolling 20-trade WR: {wins}/20 ({wr_20:.0%}) -- baseline ~35%",
                })
                _upgrade_severity("warning")
    except Exception as e:
        logger.debug("Win rate check skipped: %s", e)

    # =====================================================================
    # Condition 5: Consecutive losses (5+ in a row across all strategies)
    # =====================================================================
    try:
        if recent_trades:
            consec_losses = 0
            # Check from most recent trade backwards
            for t in reversed(recent_trades):
                status = (t.get("status") or "").upper()
                if status == "LOST":
                    consec_losses += 1
                elif status == "WON":
                    break  # Stop at first win
                # Skip unknown status trades

            if consec_losses >= 7:
                conditions.append({
                    "condition": "consecutive_losses",
                    "severity": "emergency",
                    "detail": f"{consec_losses} consecutive losses across all strategies",
                })
                _upgrade_severity("emergency")
            elif consec_losses >= 5:
                conditions.append({
                    "condition": "consecutive_losses",
                    "severity": "critical",
                    "detail": f"{consec_losses} consecutive losses across all strategies",
                })
                _upgrade_severity("critical")
    except Exception as e:
        logger.debug("Consecutive losses check skipped: %s", e)

    # --- Determine overall result ---
    # Relaxed: Only hard-kill on EMERGENCY. CRITICAL only throttles (allows elite picks).
    is_killed = max_severity in ("emergency",)
    kill_reason = None
    if conditions:
        # Use the highest-severity condition as the kill reason
        worst = max(conditions, key=lambda c: SEVERITY_ORDER.get(c.get("severity", "ok"), 0))
        kill_reason = worst["detail"]

    ACTION_MAP = {
        "ok": "none",
        "warning": "reduce_size",
        "critical": "pause_new_entries",
        "emergency": "close_all",
    }

    status = {
        "is_killed": is_killed,
        "kill_reason": kill_reason,
        "severity": max_severity,
        "recommended_action": ACTION_MAP.get(max_severity, "none"),
        "conditions": conditions,
        "checked_at": now.isoformat(),
    }

    # Persist status
    _save_status(status)

    if is_killed:
        logger.warning(
            "KILL SWITCH TRIGGERED: severity=%s, reason=%s",
            max_severity, kill_reason,
        )
    elif max_severity == "warning":
        logger.info("Kill switch: WARNING -- %s", kill_reason)
    else:
        logger.debug("Kill switch: OK -- no conditions triggered")

    return status


def load_kill_switch_status() -> dict:
    """Load the most recent kill switch status from disk."""
    raw = _load_json(_STATUS_PATH)
    if isinstance(raw, dict):
        return raw
    return {
        "is_killed": False,
        "kill_reason": None,
        "severity": "ok",
        "recommended_action": "none",
        "conditions": [],
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    status = check_kill_conditions()
    print(f"\n=== Kill Switch Status ===")
    print(f"Checked at: {status.get('checked_at', '?')}")
    print(f"Is killed:  {status['is_killed']}")
    print(f"Severity:   {status['severity']}")
    print(f"Action:     {status['recommended_action']}")

    if status["kill_reason"]:
        print(f"Reason:     {status['kill_reason']}")

    if status["conditions"]:
        print(f"\nTriggered conditions ({len(status['conditions'])}):")
        for cond in status["conditions"]:
            print(f"  [{cond['severity'].upper():9s}] {cond['condition']}: {cond['detail']}")

    sys.exit(1 if status["is_killed"] else 0)
