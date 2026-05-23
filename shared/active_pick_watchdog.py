#!/usr/bin/env python3
"""
Active Pick Watchdog — monitors systems for zero-pick conditions.

Checks all registered pick sources and reports systems that have been
producing 0 active picks for more than a configurable threshold.

Usage:
    python shared/active_pick_watchdog.py [--threshold-hours 2] [--json]

Called by GitHub Actions (audit-dashboard.yml) to ensure pipeline health.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ── Pick source registry (mirrors dashboard_generator.py) ──────────
PICK_SOURCES = [
    ("battleground", "battleground/data/active_picks.json"),
    ("alpha_engine", "alpha_engine/data/active_picks.json"),
    ("mercury2", "mercury2/data/active_picks.json"),
    ("paper_trading", "paper_trading/data/active_picks.json"),
    ("ml_bg_system_a", "ml_battleground/system_a_filter/data/active_picks.json"),
    ("ml_bg_system_b", "ml_battleground/system_b_regime/data/active_picks.json"),
    ("ml_bg_system_c", "ml_battleground/system_c_deeplearn/data/active_picks.json"),
    ("ml_bg_system_d", "ml_battleground/system_d_carry/data/active_picks.json"),
    ("ml_bg_system_e", "ml_battleground/system_e_momentum/data/active_picks.json"),
    ("ml_bg_system_f", "ml_battleground/system_f_clawsofdoom/data/active_picks.json"),
    ("ml_bg_ensemble", "ml_battleground/ensemble_data/active_picks.json"),
    ("breakout_a_sr", "breakout_arena/approach_a_sr_breakout/data/active_picks.json"),
    ("breakout_b_ml", "breakout_arena/approach_b_ml_breakout/data/active_picks.json"),
    ("breakout_c_spike", "breakout_arena/approach_c_spike_reverse/data/active_picks.json"),
    ("crypto_signal_engine", "crypto_signal_engine/data/active_picks.json"),
    ("claude_gainer_ml", "claude_gainer_ml/tracker/claude_live_picks.json"),
    ("kimi_live", "KIMI_FEB172026/data/latest_signals.json"),
    ("kimi_riseoftheclaw", "KIMI_RISEOFTHECLAW/data/live_signals_now.json"),
    ("genetic_programmer", "genome/data/gp_active_picks.json"),
    ("rapid_fire", "rapid_fire_data/active_picks.json"),
]

# Systems expected to generate picks (not performance trackers)
PICK_GENERATORS = {
    "battleground", "alpha_engine", "mercury2", "paper_trading",
    "ml_bg_system_a", "ml_bg_system_f", "breakout_b_ml",
    "crypto_signal_engine", "claude_gainer_ml",
    "kimi_live", "genetic_programmer", "rapid_fire",
}


def _count_picks(path: Path) -> int:
    """Count active picks in a JSON file."""
    if not path.exists():
        return 0
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return len(data)
        if isinstance(data, dict):
            # Handle formats like {"signals": [...]} or {"picks": [...]}
            for key in ("signals", "picks", "active", "active_picks"):
                if key in data and isinstance(data[key], list):
                    return len(data[key])
            # Handle {"total_active": N}
            if "total_active" in data:
                return int(data["total_active"])
        return 0
    except Exception:
        return 0


def _file_age_hours(path: Path) -> float | None:
    """Return file age in hours, or None if file doesn't exist."""
    if not path.exists():
        return None
    try:
        mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        return (datetime.now(timezone.utc) - mtime).total_seconds() / 3600
    except Exception:
        return None


def check_systems(threshold_hours: float = 2.0) -> dict:
    """Check all systems and return health report."""
    now = datetime.now(timezone.utc)
    results = {
        "timestamp": now.isoformat(),
        "threshold_hours": threshold_hours,
        "systems": [],
        "alerts": [],
        "summary": {"total": 0, "healthy": 0, "warning": 0, "critical": 0, "missing": 0},
    }

    for sys_name, rel_path in PICK_SOURCES:
        path = ROOT / rel_path
        picks = _count_picks(path)
        age = _file_age_hours(path)
        is_generator = sys_name in PICK_GENERATORS

        status = "healthy"
        reason = ""

        if not path.exists():
            status = "missing"
            reason = f"File not found: {rel_path}"
        elif age is not None and age > threshold_hours * 3:
            status = "critical"
            reason = f"File is {age:.1f}h old (stale)"
        elif picks == 0 and is_generator:
            if age is not None and age > threshold_hours:
                status = "critical"
                reason = f"0 picks for {age:.1f}h (expected to generate picks)"
            else:
                status = "warning"
                reason = f"0 picks (file updated {age:.1f}h ago)" if age else "0 picks"
        elif picks == 0 and not is_generator:
            status = "ok"
            reason = "Not a primary pick generator"

        entry = {
            "system": sys_name,
            "path": rel_path,
            "picks": picks,
            "file_age_hours": round(age, 1) if age else None,
            "is_generator": is_generator,
            "status": status,
            "reason": reason,
        }
        results["systems"].append(entry)
        results["summary"]["total"] += 1
        if status == "healthy":
            results["summary"]["healthy"] += 1
        elif status == "warning":
            results["summary"]["warning"] += 1
        elif status in ("critical", "missing"):
            results["summary"]["critical"] += 1
            if is_generator:
                results["alerts"].append(
                    f"ALERT: {sys_name} has {picks} active picks "
                    f"({'file missing' if status == 'missing' else reason})"
                )

    return results


def main():
    parser = argparse.ArgumentParser(description="Active Pick Watchdog")
    parser.add_argument("--threshold-hours", type=float, default=2.0,
                        help="Hours before zero-pick systems are flagged critical")
    parser.add_argument("--json", action="store_true", help="Output JSON format")
    parser.add_argument("--fail-on-alert", action="store_true",
                        help="Exit with code 1 if any alerts (for CI)")
    args = parser.parse_args()

    report = check_systems(args.threshold_hours)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        s = report["summary"]
        print(f"\n{'='*60}")
        print(f"  ACTIVE PICK WATCHDOG — {report['timestamp'][:19]}")
        print(f"{'='*60}")
        print(f"  Total systems: {s['total']}  |  Healthy: {s['healthy']}  "
              f"|  Warning: {s['warning']}  |  Critical: {s['critical']}")
        print()

        for sys in report["systems"]:
            icon = {"healthy": "[OK]", "ok": "[--]", "warning": "[!!]", "critical": "[XX]", "missing": "[??]"}.get(sys["status"], "[??]")
            gen = " [GEN]" if sys["is_generator"] else ""
            age_str = f" ({sys['file_age_hours']}h old)" if sys["file_age_hours"] else ""
            print(f"  {icon} {sys['system']:30s}  picks={sys['picks']:4d}{gen}{age_str}")
            if sys["reason"]:
                print(f"    -> {sys['reason']}")

        if report["alerts"]:
            print(f"\n{'-'*60}")
            for alert in report["alerts"]:
                print(f"  >> {alert}")

    if args.fail_on_alert and report["alerts"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
