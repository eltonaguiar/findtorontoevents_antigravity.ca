#!/usr/bin/env python3
"""
circuit_breaker_aggregator.py — Unified circuit breaker decision layer.

Reads three breaker state files:
  * drawdown_circuit_breaker.json
  * circuit_breaker_state.json   (portfolio)
  * macro_circuit_breaker.json

Returns a single unified decision so production_scanner.py only needs one call.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data"

DRAWDOWN_CB_PATH = DATA_DIR / "drawdown_circuit_breaker.json"
PORTFOLIO_CB_PATH = DATA_DIR / "circuit_breaker_state.json"
MACRO_CB_PATH = DATA_DIR / "macro_circuit_breaker.json"

LEVEL_ORDER = {"GREEN": 0, "YELLOW": 1, "RED": 2, "HALT": 3}

CATASTROPHIC_KEYWORDS = (
    "recession",
    "crash",
    "black swan",
    "liquidity crisis",
    "systemic failure",
    "contagion",
    "depression",
)


def _load_json(path: Path) -> dict:
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _state_age_hours(path: Path) -> float:
    state = _load_json(path)
    ts = state.get("timestamp", "") or state.get("activated_at", "")
    if not ts:
        return 999.0
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - dt).total_seconds() / 3600.0
    except Exception:
        return 999.0


def _level_from_drawdown(state: dict) -> str:
    level = state.get("level", "CLEAR")
    if level == "CIRCUIT_BREAKER_CRITICAL":
        return "HALT"
    if level == "CIRCUIT_BREAKER_ACTIVE":
        return "RED"
    return "GREEN"


def _level_from_portfolio(state: dict) -> str:
    return state.get("level", "GREEN")


def _level_from_macro(state: dict) -> str:
    if not state.get("active", False):
        return "GREEN"
    reason = str(state.get("reason", "")).lower()
    level = state.get("level", "YELLOW")
    if any(kw in reason for kw in CATASTROPHIC_KEYWORDS):
        return "HALT"
    if level in ("RED", "HALT"):
        return level
    if level == "YELLOW":
        return "YELLOW"
    # Default active macro breaker to RED so it triggers restrictions
    return "RED"


def get_unified_breaker_state() -> dict:
    """
    Return unified circuit breaker decision across drawdown, portfolio, and macro.

    Returns:
        {
            "level": "GREEN|YELLOW|RED|HALT",
            "max_picks": int,
            "min_confidence": float,
            "reasons": [str],
            "details": {
                "drawdown_level": str,
                "portfolio_level": str,
                "macro_level": str,
                "drawdown_state": dict,
                "portfolio_state": dict,
                "macro_state": dict,
            },
        }
    """
    dd_state = _load_json(DRAWDOWN_CB_PATH)
    pf_state = _load_json(PORTFOLIO_CB_PATH)
    macro_state = _load_json(MACRO_CB_PATH)

    dd_level = _level_from_drawdown(dd_state)
    pf_level = _level_from_portfolio(pf_state)
    macro_level = _level_from_macro(macro_state)

    # Ignore stale states (>2 hours old). 2026-04-27 fix: previously ONLY the
    # `*_level` was reset to GREEN here while the per-breaker overrides
    # (`pf_state["max_picks"]`, `min_confidence`) were still applied below via
    # min()/max() — so a 5-week-stale `circuit_breaker_state.json` with
    # level=HALT, max_picks=0, min_confidence=1.0 silently kept production
    # locked even though the aggregator reported level=GREEN. Symptom on
    # 2026-04-27: alpha_engine_fast workflow ran every 30 min successfully but
    # produced 0 new picks for ~115h; log line: "[CIRCUIT BREAKER AGGREGATOR]
    # Level: GREEN | max_picks=0 | min_conf=1.00".
    # Fix: when a state file is stale, treat it as an empty `{}` so its keys
    # don't leak into the per-breaker override step below.
    if _state_age_hours(DRAWDOWN_CB_PATH) > 2.0:
        dd_level, dd_state = "GREEN", {}
    if _state_age_hours(PORTFOLIO_CB_PATH) > 2.0:
        pf_level, pf_state = "GREEN", {}
    if _state_age_hours(MACRO_CB_PATH) > 2.0:
        macro_level, macro_state = "GREEN", {}

    levels = [dd_level, pf_level, macro_level]
    worst_level = max(levels, key=lambda x: LEVEL_ORDER.get(x, 0))

    reasons = []
    if dd_level != "GREEN":
        reasons.append(f"Drawdown: {dd_state.get('reason', dd_level)}")
    if pf_level != "GREEN":
        reasons.append(f"Portfolio: {pf_state.get('reason', pf_level)}")
    if macro_level != "GREEN":
        reasons.append(f"Macro: {macro_state.get('reason', macro_level)}")

    # Base actions by worst level
    if worst_level == "GREEN":
        max_picks, min_conf = 100, 0.55
    elif worst_level == "YELLOW":
        max_picks, min_conf = 50, 0.70
    elif worst_level == "RED":
        max_picks, min_conf = 20, 0.85
    else:  # HALT
        max_picks, min_conf = 0, 1.0

    # Apply most restrictive settings from individual breakers (stale state
    # was reset to {} above, so its overrides no longer leak in here).
    max_picks = min(
        max_picks,
        pf_state.get("max_picks", max_picks),
        macro_state.get("max_picks", max_picks),
    )
    min_conf = max(
        min_conf,
        pf_state.get("min_confidence", min_conf),
        macro_state.get("min_confidence", min_conf),
    )

    return {
        "level": worst_level,
        "max_picks": int(max_picks),
        "min_confidence": float(min_conf),
        "reasons": reasons,
        "details": {
            "drawdown_level": dd_level,
            "portfolio_level": pf_level,
            "macro_level": macro_level,
            "drawdown_state": dd_state,
            "portfolio_state": pf_state,
            "macro_state": macro_state,
        },
    }


# ──────────────────────────────────────────────────────────────────────────────
# 4-Tier Circuit Breaker (swarm Round C synthesis 2026-05-14)
# Integrates: drift gate + open-bloat + WR decay + existing GREEN/YELLOW/RED/HALT
# ──────────────────────────────────────────────────────────────────────────────
def four_tier_circuit_check(
    active_picks: list[dict] | None = None,
    closed_picks: list[dict] | None = None,
) -> dict:
    """Unified 4-tier circuit breaker integrating all monitoring checks.

    Tiers (swarm Round C design):
      T1 (ALERT):  Warn but take no automatic action
      T2 (REDUCE): Reduce new sizing to 50% of normal
      T3 (PAUSE):  Pause per-class emissions (CRYPTO/FOREX) or global pause
      T4 (HALT):   Global pause — manual human review required for resume

    Triggers:
      Drift ratio (KS_D/critical):
        > 3.0  → T3 PAUSE CRYPTO/FOREX
        > 6.0  → T4 HALT all classes
      Open-bloat ratio:
        > 90%  → T1 ALERT
        > 95%  → T3 PAUSE per affected class
      System WR (last 50):
        < 40%  → T2 REDUCE
        < 35%  → T4 HALT
      Existing GREEN/YELLOW/RED/HALT aggregator:
        YELLOW → T1 ALERT
        RED    → T2 REDUCE
        HALT   → T4 HALT

    Returns:
        {
            "tier": 1|2|3|4,
            "action": "ALERT|REDUCE|PAUSE|HALT",
            "scope": "global|class_list",
            "paused_classes": ["CRYPTO", "FOREX"],
            "reasons": [...],
            "drift_ratio": float,
            "open_bloat_pct": float,
            "auto_resume": str,  # condition for T1-T3; "MANUAL_ONLY" for T4
        }
    """
    active_picks = active_picks or []
    closed_picks = closed_picks or []
    reasons: list[str] = []
    tier = 0  # start at no action
    paused_classes: list[str] = []

    # --- Check 1: Concept drift ratio ---
    drift_ratio = 0.0
    try:
        import sys, os
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "audit_trail"))
        from quality_gates import _get_concept_drift_ratio
        drift_ratio = _get_concept_drift_ratio()
    except Exception:
        pass

    if drift_ratio > 6.0:
        tier = max(tier, 4)
        reasons.append(f"SEVERE drift: KS_D/critical={drift_ratio:.1f}x > 6.0 — all classes at risk")
    elif drift_ratio > 3.0:
        tier = max(tier, 3)
        paused_classes = list(set(paused_classes + ["CRYPTO", "FOREX"]))
        reasons.append(f"Drift pause: KS_D/critical={drift_ratio:.1f}x > 3.0 — CRYPTO+FOREX paused")

    # --- Check 2: Open-bloat ratio ---
    open_bloat_pct = 0.0
    try:
        from quality_gates import check_open_bloat_health
        if active_picks:
            bloat = check_open_bloat_health(active_picks)
            open_bloat_pct = bloat.get("open_pct", 0.0)
            if bloat["status"] == "pause":
                tier = max(tier, 3)
                # Pause worst offender classes
                for cls, cd in bloat.get("by_class", {}).items():
                    if cd.get("open_pct", 0) >= 0.95:
                        paused_classes = list(set(paused_classes + [cls]))
                reasons.append(f"Open bloat {open_bloat_pct:.0%}: WR data unreliable")
            elif bloat["status"] == "warn":
                tier = max(tier, 1)
                reasons.append(f"Open bloat {open_bloat_pct:.0%}: approaching pause threshold")
    except Exception:
        pass

    # --- Check 3: Recent WR (last 50 closed picks) ---
    recent_wr = None
    if len(closed_picks) >= 20:
        try:
            recent = closed_picks[-50:]
            wins = sum(1 for p in recent if float(p.get("pnl_pct", 0) or 0) > 0)
            recent_wr = wins / len(recent)
            if recent_wr < 0.35:
                tier = max(tier, 4)
                reasons.append(f"System WR {recent_wr:.1%} < 35% (last {len(recent)} trades) — HALT")
            elif recent_wr < 0.40:
                tier = max(tier, 2)
                reasons.append(f"System WR {recent_wr:.1%} < 40% — reduce sizing 50%")
        except Exception:
            pass

    # --- Check 4: Existing aggregator (GREEN/YELLOW/RED/HALT) ---
    try:
        agg = get_unified_circuit_state()
        agg_level = agg.get("level", "GREEN")
        if agg_level == "HALT":
            tier = max(tier, 4)
            reasons.append(f"Portfolio/drawdown breaker: HALT — {'; '.join(agg.get('reasons', []))[:80]}")
        elif agg_level == "RED":
            tier = max(tier, 2)
            reasons.append(f"Portfolio/drawdown breaker: RED — reduce sizing")
        elif agg_level == "YELLOW":
            tier = max(tier, 1)
            reasons.append(f"Portfolio/drawdown breaker: YELLOW — alert")
    except Exception:
        pass

    # --- Map tier to action / scope ---
    tier_map = {
        0: ("HEALTHY", "global", "OK"),
        1: ("ALERT", "global", "resolve_on_next_clean_scan"),
        2: ("REDUCE", "global", "auto_resume_when_WR>45pct"),
        3: ("PAUSE", f"classes:{','.join(paused_classes) or 'affected'}", "auto_resume_when_ratio<2.0"),
        4: ("HALT", "global", "MANUAL_ONLY"),
    }
    action, scope, auto_resume = tier_map.get(tier, tier_map[0])

    return {
        "tier": tier,
        "action": action,
        "scope": scope,
        "paused_classes": paused_classes,
        "reasons": reasons,
        "drift_ratio": round(drift_ratio, 3),
        "open_bloat_pct": round(open_bloat_pct, 4),
        "recent_wr": round(recent_wr, 3) if recent_wr is not None else None,
        "auto_resume": auto_resume,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
