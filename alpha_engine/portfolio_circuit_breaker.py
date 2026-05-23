#!/usr/bin/env python3
"""
Portfolio-Level Circuit Breaker — Institutional Risk Control
=============================================================
Monitors portfolio-level risk metrics and automatically reduces exposure
when thresholds are breached. This is the MISSING piece for institutional
grade — individual strategy gates exist, but no portfolio-level protection.

Levels:
  GREEN:  Normal operation. All picks flow through.
  YELLOW: Elevated risk. Reduce new pick count by 50%, raise confidence floor.
  RED:    Critical. Only HIGH tier picks with conf >= 0.85 pass.
  HALT:   Emergency. No new picks generated. Existing picks trail-stopped.

Triggers (any ONE trips the level):
  YELLOW: Portfolio DD > -10% OR loss streak >= 8 OR daily loss > -3%
  RED:    Portfolio DD > -20% OR loss streak >= 15 OR daily loss > -5%
  HALT:   Portfolio DD > -30% OR loss streak >= 25

Reads from:
  - alpha_engine/data/closed_picks.json (recent PnL)
  - alpha_engine/data/drawdown_report.json (DD metrics)
  - alpha_engine/data/advanced_risk_metrics.json (CVaR, streaks)

Outputs:
  - alpha_engine/data/circuit_breaker_state.json
  - Returns (level, max_picks, min_confidence) for production_scanner

Integration:
  Called at START of production_scanner.py before generating picks.
  If level >= RED, scanner reduces output. If HALT, scanner skips entirely.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data"

CLOSED_PICKS_PATH = DATA_DIR / "closed_picks.json"
DRAWDOWN_PATH = DATA_DIR / "drawdown_report.json"
RISK_METRICS_PATH = DATA_DIR / "advanced_risk_metrics.json"
STATE_PATH = DATA_DIR / "circuit_breaker_state.json"

# Thresholds
THRESHOLDS = {
    "YELLOW": {
        "max_dd_pct": -10.0,
        "max_loss_streak": 8,
        "max_daily_loss_pct": -3.0,
    },
    "RED": {
        "max_dd_pct": -20.0,
        "max_loss_streak": 15,
        "max_daily_loss_pct": -5.0,
    },
    "HALT": {
        "max_dd_pct": -30.0,
        "max_loss_streak": 25,
        "max_daily_loss_pct": -8.0,
    },
}

# What each level does to pick generation
LEVEL_ACTIONS = {
    "GREEN": {"max_picks": 20, "min_confidence": 0.70, "description": "Normal operation"},
    "YELLOW": {"max_picks": 10, "min_confidence": 0.75, "description": "Elevated risk — reduced exposure"},
    "RED": {"max_picks": 5, "min_confidence": 0.85, "description": "Critical — HIGH tier only"},
    "HALT": {"max_picks": 0, "min_confidence": 1.0, "description": "Emergency halt — no new picks"},
}


def _load_json(path: Path) -> dict | list | None:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _compute_recent_loss_streak(closed_picks: list) -> int:
    """Count consecutive losses from most recent pick backwards."""
    resolved = [p for p in closed_picks if p.get("status") in ("WON", "LOST")]
    resolved.sort(key=lambda p: p.get("exit_date", p.get("closed_at", "")), reverse=True)

    streak = 0
    for p in resolved:
        if p["status"] == "LOST":
            streak += 1
        else:
            break
    return streak


def _compute_daily_pnl(closed_picks: list) -> float:
    """Sum PnL of picks closed in the last 24 hours."""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=24)
    daily_pnl = 0.0

    for p in closed_picks:
        exit_date = p.get("exit_date", p.get("closed_at", ""))
        if not exit_date:
            continue
        try:
            dt = datetime.fromisoformat(exit_date.replace("Z", "+00:00"))
            if dt >= cutoff:
                daily_pnl += float(p.get("pnl_pct", 0) or 0)
        except Exception:
            continue

    return daily_pnl


def _get_portfolio_dd(drawdown_report: dict | None) -> float:
    """Extract portfolio max drawdown from drawdown_report.json."""
    if not drawdown_report:
        return 0.0
    portfolio = drawdown_report.get("portfolio", {})
    return float(portfolio.get("max_drawdown_pct", 0) or 0)


def check_circuit_breaker() -> dict:
    """
    Check portfolio risk levels and return circuit breaker state.

    Returns:
        {
            "level": "GREEN" | "YELLOW" | "RED" | "HALT",
            "max_picks": int,
            "min_confidence": float,
            "triggers": [list of reasons],
            "metrics": {current metric values},
            "timestamp": iso string,
        }
    """
    triggers = []

    # Load data
    closed_picks = _load_json(CLOSED_PICKS_PATH) or []
    drawdown_report = _load_json(DRAWDOWN_PATH)
    risk_metrics = _load_json(RISK_METRICS_PATH)

    # Compute metrics
    loss_streak = _compute_recent_loss_streak(closed_picks)
    daily_pnl = _compute_daily_pnl(closed_picks)
    portfolio_dd = _get_portfolio_dd(drawdown_report)

    # Also check advanced risk metrics for streak
    if risk_metrics:
        dd_info = risk_metrics.get("drawdown_duration", {})
        adv_streak = int(dd_info.get("max_consecutive_losses", 0) or 0)
        # Use the worse of the two streak measurements
        loss_streak = max(loss_streak, adv_streak)

    metrics = {
        "portfolio_dd_pct": portfolio_dd,
        "loss_streak": loss_streak,
        "daily_pnl_pct": daily_pnl,
        "closed_picks_count": len(closed_picks),
    }

    # Determine level (check from most severe to least)
    level = "GREEN"

    for check_level in ("HALT", "RED", "YELLOW"):
        thresh = THRESHOLDS[check_level]
        if portfolio_dd < thresh["max_dd_pct"]:
            triggers.append(f"Portfolio DD {portfolio_dd:.1f}% < {thresh['max_dd_pct']}%")
            if check_level == "HALT" or (check_level == "RED" and level != "HALT") or (check_level == "YELLOW" and level == "GREEN"):
                level = check_level
        if loss_streak >= thresh["max_loss_streak"]:
            triggers.append(f"Loss streak {loss_streak} >= {thresh['max_loss_streak']}")
            if check_level == "HALT" or (check_level == "RED" and level != "HALT") or (check_level == "YELLOW" and level == "GREEN"):
                level = check_level
        if daily_pnl < thresh["max_daily_loss_pct"]:
            triggers.append(f"Daily PnL {daily_pnl:.1f}% < {thresh['max_daily_loss_pct']}%")
            if check_level == "HALT" or (check_level == "RED" and level != "HALT") or (check_level == "YELLOW" and level == "GREEN"):
                level = check_level

    actions = LEVEL_ACTIONS[level]

    state = {
        "level": level,
        "max_picks": actions["max_picks"],
        "min_confidence": actions["min_confidence"],
        "description": actions["description"],
        "triggers": triggers,
        "metrics": metrics,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Save state
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(STATE_PATH, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception:
        pass

    # Print status
    level_emoji = {"GREEN": "OK", "YELLOW": "!!", "RED": "!!!", "HALT": "XXXX"}
    print(f"  [CIRCUIT BREAKER] Level: {level_emoji.get(level, '?')} {level} — {actions['description']}")
    if triggers:
        for t in triggers:
            print(f"    Trigger: {t}")
    print(f"    Metrics: DD={portfolio_dd:.1f}%, streak={loss_streak}, daily={daily_pnl:.1f}%")
    print(f"    Action: max_picks={actions['max_picks']}, min_conf={actions['min_confidence']}")

    return state


if __name__ == "__main__":
    state = check_circuit_breaker()
    print(f"\nCircuit breaker: {state['level']}")
    print(f"Triggers: {state['triggers']}")
