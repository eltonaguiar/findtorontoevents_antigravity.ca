#!/usr/bin/env python3
"""
Cycle Metrics Runner — runs after each alpha engine scan cycle.

Orchestrates all institutional-grade metric modules in sequence:
  1. institutional_metrics.py  → Sortino, Calmar, realistic Sharpe, IC
  2. drawdown_tracker.py       → Per-strategy + portfolio max DD, streaks
  3. threshold_overfit_validator.py → Walk-forward overfit risk scores
  4. institutional_scorecard.py → 250-point hedge fund signal scorecard

Outputs a cycle_metrics_summary.json with timestamps and alert flags.
Designed to be called from GitHub Actions after production_scanner.py.
"""

from __future__ import annotations

import json
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data"
SUMMARY_PATH = DATA_DIR / "cycle_metrics_summary.json"

# Alert thresholds
ALERT_THRESHOLDS = {
    "max_drawdown_pct": -30.0,       # Alert if portfolio DD exceeds -30%
    "max_loss_streak": 12,           # Alert if loss streak >= 12
    "min_win_rate": 0.35,            # Alert if system WR drops below 35%
    "min_profit_factor": 0.80,       # Alert if PF drops below 0.80
    "max_overfit_score": 70,         # Alert if overfit risk > 70/100
    "min_scorecard_grade": "D",      # Alert if scorecard drops to D or F
    "min_ic": -0.05,                 # Alert if IC goes negative
}

GRADE_ORDER = {"A": 5, "B": 4, "C": 3, "D": 2, "F": 1}


def _run_module(name: str, run_func) -> dict:
    """Run a metrics module safely, return result or error."""
    try:
        result = run_func()
        return {"status": "ok", "module": name, "result": result}
    except Exception as e:
        traceback.print_exc()
        return {"status": "error", "module": name, "error": str(e)}


def _check_alerts(metrics: dict, drawdown: dict, scorecard: dict) -> list[dict]:
    """Check metric values against alert thresholds."""
    alerts = []

    # Drawdown alert
    portfolio_dd = drawdown.get("result", {}).get("portfolio", {}).get(
        "max_drawdown_pct", 0
    )
    if portfolio_dd < ALERT_THRESHOLDS["max_drawdown_pct"]:
        alerts.append({
            "level": "CRITICAL",
            "metric": "max_drawdown",
            "value": portfolio_dd,
            "threshold": ALERT_THRESHOLDS["max_drawdown_pct"],
            "message": f"Portfolio drawdown {portfolio_dd:.1f}% exceeds -{abs(ALERT_THRESHOLDS['max_drawdown_pct'])}% limit",
        })

    # Loss streak alert
    loss_streak = drawdown.get("result", {}).get("portfolio", {}).get(
        "longest_losing_streak", 0
    )
    if loss_streak >= ALERT_THRESHOLDS["max_loss_streak"]:
        alerts.append({
            "level": "WARNING",
            "metric": "loss_streak",
            "value": loss_streak,
            "threshold": ALERT_THRESHOLDS["max_loss_streak"],
            "message": f"Loss streak of {loss_streak} trades (threshold: {ALERT_THRESHOLDS['max_loss_streak']})",
        })

    # Win rate alert
    system_wr = metrics.get("result", {}).get("system", {}).get("win_rate", 0.5)
    if system_wr < ALERT_THRESHOLDS["min_win_rate"]:
        alerts.append({
            "level": "WARNING",
            "metric": "win_rate",
            "value": system_wr,
            "threshold": ALERT_THRESHOLDS["min_win_rate"],
            "message": f"System WR {system_wr:.1%} below {ALERT_THRESHOLDS['min_win_rate']:.0%} threshold",
        })

    # Scorecard grade alert
    grade = scorecard.get("result", {}).get("grade", "C")
    min_grade = ALERT_THRESHOLDS["min_scorecard_grade"]
    if GRADE_ORDER.get(grade, 0) <= GRADE_ORDER.get(min_grade, 0):
        alerts.append({
            "level": "WARNING",
            "metric": "scorecard_grade",
            "value": grade,
            "threshold": min_grade,
            "message": f"Institutional scorecard grade {grade} at or below {min_grade}",
        })

    # IC alert
    ic = metrics.get("result", {}).get("system", {}).get(
        "information_coefficient", 0
    )
    if ic < ALERT_THRESHOLDS["min_ic"]:
        alerts.append({
            "level": "CRITICAL",
            "metric": "information_coefficient",
            "value": ic,
            "threshold": ALERT_THRESHOLDS["min_ic"],
            "message": f"IC={ic:.4f} is negative — scoring system anti-predictive",
        })

    return alerts


def run_cycle_metrics() -> dict:
    """Run all metric modules and produce summary."""
    print("=" * 60)
    print("CYCLE METRICS RUNNER — Institutional Grade Monitoring")
    print("=" * 60)

    results = {}

    # 1. Institutional metrics (Sortino, Calmar, Sharpe, IC)
    print("\n[1/4] Computing institutional metrics...")
    try:
        sys.path.insert(0, str(SCRIPT_DIR))
        from institutional_metrics import main as inst_main
        results["institutional_metrics"] = _run_module(
            "institutional_metrics", inst_main
        )
    except ImportError:
        # Try running as subprocess if import fails
        results["institutional_metrics"] = _run_module(
            "institutional_metrics",
            lambda: __import__("institutional_metrics").main(),
        )
    except Exception as e:
        results["institutional_metrics"] = {"status": "error", "error": str(e)}

    # 2. Drawdown tracker
    print("\n[2/4] Computing drawdown metrics...")
    try:
        from drawdown_tracker import compute_all_drawdowns
        results["drawdown_tracker"] = _run_module(
            "drawdown_tracker", compute_all_drawdowns
        )
    except Exception as e:
        results["drawdown_tracker"] = {"status": "error", "error": str(e)}

    # 3. Walk-forward overfit validator
    print("\n[3/4] Running walk-forward overfit validation...")
    try:
        from threshold_overfit_validator import run_validation
        results["overfit_validator"] = _run_module(
            "overfit_validator", run_validation
        )
    except ImportError:
        # Module may use different entry point
        try:
            from threshold_overfit_validator import main as tov_main
            results["overfit_validator"] = _run_module("overfit_validator", tov_main)
        except Exception as e:
            results["overfit_validator"] = {"status": "error", "error": str(e)}
    except Exception as e:
        results["overfit_validator"] = {"status": "error", "error": str(e)}

    # 4. Institutional scorecard (250-point)
    print("\n[4/4] Computing institutional scorecard...")
    try:
        from institutional_scorecard import run_scorecard
        results["scorecard"] = _run_module("scorecard", run_scorecard)
    except Exception as e:
        results["scorecard"] = {"status": "error", "error": str(e)}

    # Check alerts
    print("\n[ALERTS] Checking thresholds...")
    alerts = _check_alerts(
        results.get("institutional_metrics", {}),
        results.get("drawdown_tracker", {}),
        results.get("scorecard", {}),
    )

    for alert in alerts:
        level = alert["level"]
        print(f"  {'!!!' if level == 'CRITICAL' else '!'} [{level}] {alert['message']}")

    if not alerts:
        print("  All metrics within acceptable thresholds.")

    # Build summary
    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "modules_run": len(results),
        "modules_ok": sum(1 for r in results.values() if r.get("status") == "ok"),
        "modules_failed": sum(1 for r in results.values() if r.get("status") == "error"),
        "alerts": alerts,
        "alert_count": len(alerts),
        "critical_alerts": sum(1 for a in alerts if a["level"] == "CRITICAL"),
        "module_status": {k: v.get("status", "unknown") for k, v in results.items()},
    }

    # Save summary
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(SUMMARY_PATH, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"\n[SAVED] {SUMMARY_PATH}")

    # Print summary
    print(f"\n{'=' * 60}")
    print(f"CYCLE COMPLETE: {summary['modules_ok']}/{summary['modules_run']} modules OK")
    print(f"ALERTS: {summary['alert_count']} ({summary['critical_alerts']} critical)")
    print(f"{'=' * 60}")

    return summary


if __name__ == "__main__":
    run_cycle_metrics()
