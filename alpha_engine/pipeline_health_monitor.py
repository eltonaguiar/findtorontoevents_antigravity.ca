#!/usr/bin/env python3
"""
pipeline_health_monitor.py
==========================
Comprehensive pipeline health monitor for the trading ecosystem.
Runs automated checks across all signal sources, flags outliers,
and appends red-flag alerts to chatwithit.MD for agent handoff.

Usage:
  python alpha_engine/pipeline_health_monitor.py
  python alpha_engine/pipeline_health_monitor.py --write-flags
  python alpha_engine/pipeline_health_monitor.py --json
"""

import json
import os
import sys
import time
import argparse
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(REPO_ROOT))

try:
    from audit_trail.dashboard_generator import JSON_PICK_SOURCES, _HIDDEN_SYSTEMS
except ImportError:
    JSON_PICK_SOURCES = []
    _HIDDEN_SYSTEMS = set()

# ── Config ──
CRYPTO_STALE_HOURS = 24
NON_CRYPTO_STALE_HOURS = 72
CRITICAL_PNL_THRESHOLD = -15.0
MAX_SINGLE_SYMBOL_PCT = 40.0

CRITICAL_SYSTEMS = {
    "alpha_engine", "copy_trader_intel", "ml_crypto_pred",
    "genome", "multi_asset", "rapid_fire",
}

EVO_SYSTEMS = {
    "genome", "genetic_programmer", "mape_evolver", "ensemble_evolver",
    "audit_ensemble", "neat_neural", "hyperparam_dna", "failure_evolver",
    "momentum_evolver", "multitf_evolver", "contrarian_evolver",
    "universal_picks",
}


class HealthCheck:
    def __init__(self, category, severity, message, details=None):
        self.category = category
        self.severity = severity
        self.message = message
        self.details = details or {}
        self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self):
        return {"category": self.category, "severity": self.severity,
                "message": self.message, "details": self.details,
                "timestamp": self.timestamp}

    def __str__(self):
        return f"  {self.severity} [{self.category}] {self.message}"


def _load_picks(path):
    """Load picks from a JSON file, handling dict/list formats."""
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for key in ["picks", "active_picks", "activePicks", "signals", "active_signals"]:
                if key in data and isinstance(data[key], list):
                    return data[key]
        return []
    except Exception:
        return []


def check_staleness():
    alerts = []
    now = time.time()
    for sys_name, active_rel, closed_rel in JSON_PICK_SOURCES:
        if sys_name in _HIDDEN_SYSTEMS or not active_rel:
            continue
        file_path = REPO_ROOT / active_rel
        if not file_path.exists():
            if sys_name in CRITICAL_SYSTEMS:
                alerts.append(HealthCheck("MISSING", "\U0001f534 CRITICAL",
                    f"{sys_name}: data file missing ({active_rel})",
                    {"system": sys_name, "path": active_rel}))
            continue
        age_hours = (now - os.path.getmtime(file_path)) / 3600
        threshold = CRYPTO_STALE_HOURS if sys_name in CRITICAL_SYSTEMS else NON_CRYPTO_STALE_HOURS
        if age_hours > threshold:
            sev = "\U0001f534 CRITICAL" if sys_name in CRITICAL_SYSTEMS else "\U0001f7e1 WARNING"
            alerts.append(HealthCheck("STALE", sev,
                f"{sys_name}: {age_hours:.1f}h old (>{threshold}h limit)",
                {"system": sys_name, "hours_stale": round(age_hours, 1)}))
    return alerts


def check_pnl_outliers():
    alerts = []
    for sys_name, active_rel, _ in JSON_PICK_SOURCES:
        if not active_rel or sys_name in _HIDDEN_SYSTEMS:
            continue
        picks = _load_picks(REPO_ROOT / active_rel)
        for p in picks:
            if not isinstance(p, dict):
                continue
            pnl = p.get("unrealized_pnl_pct") or p.get("pnl_pct") or p.get("pnl") or 0
            try:
                pnl = float(pnl)
            except (TypeError, ValueError):
                continue
            if pnl < CRITICAL_PNL_THRESHOLD:
                alerts.append(HealthCheck("PNL_OUTLIER", "\U0001f534 CRITICAL",
                    f"{sys_name}/{p.get('symbol','?')}: {pnl:.1f}% PnL (circuit breaker level)",
                    {"system": sys_name, "symbol": p.get("symbol"), "pnl": round(pnl, 2),
                     "strategy": p.get("strategy", "?")}))
    return alerts


def check_feed_hygiene():
    alerts = []
    for sys_name, active_rel, _ in JSON_PICK_SOURCES:
        if not active_rel or sys_name in _HIDDEN_SYSTEMS or sys_name in EVO_SYSTEMS:
            continue
        picks = _load_picks(REPO_ROOT / active_rel)
        zero_count = 0
        for p in picks:
            if not isinstance(p, dict):
                continue
            try:
                entry = float(p.get("entry_price") or 0)
            except (TypeError, ValueError):
                entry = 0
            if entry <= 0:
                zero_count += 1
        if zero_count > 0:
            sev = "\U0001f534 CRITICAL" if zero_count > 5 else "\U0001f7e1 WARNING"
            alerts.append(HealthCheck("FEED_HYGIENE", sev,
                f"{sys_name}: {zero_count} picks with entry_price=0",
                {"system": sys_name, "zero_entry_count": zero_count}))
    return alerts


def check_concentration():
    alerts = []
    symbol_counts = defaultdict(int)
    active_path = REPO_ROOT / "alpha_engine/data/active_picks.json"
    picks = _load_picks(active_path)
    total = len(picks)
    if total > 5:
        for p in picks:
            if isinstance(p, dict) and p.get("symbol"):
                symbol_counts[p["symbol"]] += 1
        for sym, count in sorted(symbol_counts.items(), key=lambda x: -x[1]):
            pct = count / total * 100
            if pct > MAX_SINGLE_SYMBOL_PCT:
                alerts.append(HealthCheck("CONCENTRATION", "\U0001f534 CRITICAL",
                    f"{sym}: {pct:.0f}% of portfolio ({count}/{total} picks)",
                    {"symbol": sym, "count": count, "pct": round(pct, 1)}))
    return alerts


def check_consensus_health():
    alerts = []
    uni_path = REPO_ROOT / "genome/data/universal_picks.json"
    if not uni_path.exists():
        return alerts
    try:
        with open(uni_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        consensus_count = data.get("consensus_count", 0)
        engines_run = data.get("engines_run", [])
        picks_by_engine = data.get("picks_by_engine", {})
        if consensus_count == 0 and len(engines_run) >= 2:
            alerts.append(HealthCheck("CONSENSUS", "\U0001f7e1 WARNING",
                f"Universal Evolver: 0 consensus from {len(engines_run)} engines",
                {"engines": engines_run, "total_picks": data.get("total_picks", 0)}))
        for eng in engines_run:
            if len(picks_by_engine.get(eng, [])) == 0:
                alerts.append(HealthCheck("ENGINE_DEAD", "\U0001f7e1 WARNING",
                    f"Genome engine '{eng}' produced 0 picks", {"engine": eng}))
    except Exception:
        pass
    return alerts


def check_score_distribution():
    alerts = []
    picks = _load_picks(REPO_ROOT / "alpha_engine/data/active_picks.json")
    if len(picks) > 10:
        scored = zero = 0
        for p in picks:
            if not isinstance(p, dict):
                continue
            score = p.get("elite_score") or p.get("score") or p.get("smart_score")
            if score is not None:
                scored += 1
                try:
                    if float(score) <= 0:
                        zero += 1
                except (TypeError, ValueError):
                    zero += 1
        if scored > 0 and (zero / scored * 100) > 50:
            alerts.append(HealthCheck("SCORING", "\U0001f7e1 WARNING",
                f"Scoring anomaly: {zero}/{scored} picks have score=0",
                {"zero_count": zero, "scored_total": scored}))
        elif scored == 0 and len(picks) > 20:
            alerts.append(HealthCheck("SCORING", "\U0001f7e1 WARNING",
                f"No scored picks among {len(picks)} active — elite_scorer may be offline",
                {"total_picks": len(picks)}))
    return alerts


def check_institutional():
    alerts = []
    inst_path = REPO_ROOT / "multi_asset/data/institutional_picks.json"
    picks = _load_picks(inst_path)
    if not picks:
        return alerts
    classes = defaultdict(int)
    now = datetime.now(timezone.utc)
    for p in picks:
        if not isinstance(p, dict):
            continue
        classes[p.get("asset_class", "UNKNOWN")] += 1
        ts = p.get("timestamp", "")
        if ts:
            try:
                created = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                days = (now - created).days
                if days > 30:
                    alerts.append(HealthCheck("STALE_POSITION", "\U0001f7e1 WARNING",
                        f"Institutional: {p.get('symbol','?')} open {days}d (>30d)",
                        {"symbol": p.get("symbol"), "days": days}))
            except Exception:
                pass
    if len(classes) < 2 and sum(classes.values()) > 0:
        alerts.append(HealthCheck("DIVERSITY", "\U0001f7e1 WARNING",
            f"Institutional: only {len(classes)} asset class(es) ({dict(classes)})",
            {"classes": dict(classes)}))
    return alerts


def check_dashboard():
    alerts = []
    for name in ["audit_trail/data/dashboard_payload.json", "audit_dashboard/data/dashboard_data.json"]:
        p = REPO_ROOT / name
        if not p.exists():
            continue
        age_h = (time.time() - os.path.getmtime(p)) / 3600
        if age_h > 4:
            alerts.append(HealthCheck("DASHBOARD", "\U0001f7e1 WARNING",
                f"{p.name}: {age_h:.1f}h old (>4h)", {"file": p.name, "hours": round(age_h, 1)}))
        size_mb = os.path.getsize(p) / (1024 * 1024)
        if size_mb > 15:
            alerts.append(HealthCheck("DASHBOARD", "\U0001f7e1 WARNING",
                f"{p.name}: {size_mb:.1f}MB (>15MB)", {"file": p.name, "mb": round(size_mb, 1)}))
    return alerts


def run_all_checks():
    all_alerts = []
    checks = [
        ("Staleness", check_staleness),
        ("PnL Outliers", check_pnl_outliers),
        ("Feed Hygiene", check_feed_hygiene),
        ("Concentration", check_concentration),
        ("Consensus", check_consensus_health),
        ("Scoring", check_score_distribution),
        ("Institutional", check_institutional),
        ("Dashboard", check_dashboard),
    ]
    for name, fn in checks:
        try:
            all_alerts.extend(fn())
        except Exception as e:
            all_alerts.append(HealthCheck("ERROR", "\U0001f534 CRITICAL", f"{name} crashed: {e}"))

    crit = sum(1 for a in all_alerts if "CRITICAL" in a.severity)
    warn = sum(1 for a in all_alerts if "WARNING" in a.severity)
    status = "\U0001f534 DEGRADED" if crit > 0 else ("\U0001f7e1 WARNINGS" if warn > 0 else "\U0001f7e2 HEALTHY")

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_checks": len(checks),
        "total_alerts": len(all_alerts),
        "critical": crit, "warnings": warn,
        "status": status,
        "alerts": [a.to_dict() for a in all_alerts],
    }
    return report, all_alerts


def print_report(report, alerts):
    print("=" * 70)
    print(f"  PIPELINE HEALTH MONITOR - {report['status']}")
    print(f"  {report['timestamp']}")
    print("=" * 70)
    print(f"  Checks: {report['total_checks']} | Alerts: {report['total_alerts']} "
          f"(critical={report['critical']}, warnings={report['warnings']})")
    print("-" * 70)
    if not alerts:
        print("\n  All systems healthy.\n")
        return
    by_cat = defaultdict(list)
    for a in alerts:
        by_cat[a.category].append(a)
    for cat, items in sorted(by_cat.items()):
        print(f"\n  [{cat}]")
        for a in items:
            print(str(a))
    print("\n" + "=" * 70)


def write_flags_to_chatwithit(report, alerts):
    path = REPO_ROOT / "chatwithit.MD"
    if not path.exists():
        print("[WARN] chatwithit.MD not found")
        return

    crits = [a for a in alerts if "CRITICAL" in a.severity]
    warns = [a for a in alerts if "WARNING" in a.severity]
    if not crits and not warns:
        print("[INFO] No flags to write.")
        return

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        f"\n---\n",
        f"\n## AUTOMATED HEALTH MONITOR - {now_str}\n\n",
        f"**Status:** {report['status']} | Critical: {report['critical']} | Warnings: {report['warnings']}\n\n",
    ]
    if crits:
        lines.append("### CRITICAL RED FLAGS\n\n")
        lines.append("| System | Category | Issue |\n")
        lines.append("|--------|----------|-------|\n")
        for a in crits:
            s = a.details.get("system", a.details.get("symbol", "-"))
            lines.append(f"| {s} | {a.category} | {a.message} |\n")
        lines.append("\n")
    if warns:
        lines.append("### WARNINGS\n\n")
        lines.append("| System | Category | Issue |\n")
        lines.append("|--------|----------|-------|\n")
        for a in warns:
            s = a.details.get("system", a.details.get("symbol", "-"))
            lines.append(f"| {s} | {a.category} | {a.message} |\n")
        lines.append("\n")
    lines.append("*Auto-generated by `alpha_engine/pipeline_health_monitor.py`*\n")

    content = path.read_text(encoding="utf-8")
    block = "".join(lines)
    first_sep = content.find("\n---\n", 1)
    if first_sep > 0:
        new_content = content[:first_sep] + block + content[first_sep:]
    else:
        new_content = content + block
    path.write_text(new_content, encoding="utf-8")
    print(f"[OK] Wrote {len(crits)} critical + {len(warns)} warnings to chatwithit.MD")


def save_json_report(report):
    out = REPO_ROOT / "alpha_engine/data/pipeline_health.json"
    os.makedirs(out.parent, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"[OK] JSON report: {out}")


def main():
    parser = argparse.ArgumentParser(description="Pipeline Health Monitor")
    parser.add_argument("--write-flags", action="store_true", help="Append red flags to chatwithit.MD")
    parser.add_argument("--json", action="store_true", help="Save JSON report")
    parser.add_argument("--fail-on-critical", action="store_true", help="Exit 1 on critical (for CI)")
    args = parser.parse_args()

    report, alerts = run_all_checks()
    print_report(report, alerts)

    if args.json:
        save_json_report(report)
    if args.write_flags:
        write_flags_to_chatwithit(report, alerts)
    if args.fail_on_critical and report["critical"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
