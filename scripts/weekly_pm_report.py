#!/usr/bin/env python3
"""
Weekly PM Report Generator — Performance Manager Dashboard
===========================================================
Mercury AI / Inception Labs Recommendation §3.5:
  Weekly PM-style dashboard monitoring component health.

Generates:
  1. Component-level expectancy, WR, max DD, turnover, slippage
  2. Family-level aggregation
  3. Direction analysis (long vs. short)
  4. Alert conditions flagged per Mercury AI thresholds
  5. Output: weekly_pm_report.json + weekly_pm_report.md (human-readable)

Created: 2026-03-03 18:27 EST
Source: Mercury AI Feedback (ANTIGRAVITY_PLAN_MERCURYFEEDBACK.MD)
"""

import json
import logging
import pathlib
import math
from datetime import datetime, timezone, timedelta

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("weekly_pm_report")

# ── Paths ──────────────────────────────────────────────────
BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

REPORT_JSON_PATH = DATA_DIR / "weekly_pm_report.json"
REPORT_MD_PATH = BASE_DIR / "WEEKLY_PM_REPORT.md"
COMPONENT_PERF_PATH = DATA_DIR / "component_perf_daily.json"

# ── Mercury AI Alert Thresholds ────────────────────────────
ALERT_THRESHOLDS = {
    "expectancy_demote": 0.0,       # < 0% → demote to Incubator or kill
    "win_rate_demote": 0.30,        # < 30% → demote
    "max_dd_demote_pct": 0.05,      # > 5% of allocation → demote
    "turnover_review_pct": 0.30,    # > 30% of allocation → review
    "slippage_drift_pct": 0.002,    # > 0.2% per trade → tighten RR gate
}


def _load_json(path: pathlib.Path):
    """Load JSON file safely."""
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log.warning("Failed to load %s: %s", path, e)
        return None


def generate_weekly_report(lookback_days: int = 7) -> dict:
    """
    Generate a comprehensive weekly PM report.

    Reads from component_perf_daily.json (from post_trade_attribution.py)
    and generates a PM-style dashboard.
    """
    now = datetime.now(timezone.utc)

    # Load component performance data
    perf_data = _load_json(COMPONENT_PERF_PATH)
    if not perf_data:
        log.warning("No component_perf_daily.json found — run post_trade_attribution.py first")
        perf_data = {"components": {}}

    components = perf_data.get("components", {})

    # Build the report
    alerts = []
    family_aggregation = {}
    component_summaries = []

    for comp_id, comp in components.items():
        wr = comp.get("win_rate", 0)
        expectancy = comp.get("avg_pnl_usdt", 0)
        total_trades = comp.get("total_trades", 0)
        total_pnl = comp.get("total_pnl_usdt", 0)
        max_dd = comp.get("max_drawdown_usdt", 0)
        recommendation = comp.get("recommendation", "MONITOR")
        family = comp.get("family", "Unknown")

        # Check alert conditions
        comp_alerts = []
        if wr < ALERT_THRESHOLDS["win_rate_demote"] and total_trades >= 10:
            comp_alerts.append(f"⚠️ WR {wr:.0%} < {ALERT_THRESHOLDS['win_rate_demote']:.0%} threshold")
        if expectancy < ALERT_THRESHOLDS["expectancy_demote"] and total_trades >= 10:
            comp_alerts.append(f"🔴 Negative expectancy: ${expectancy:.2f}/trade")
        if comp_alerts:
            alerts.extend([f"[{comp_id}] {a}" for a in comp_alerts])

        # Component summary
        component_summaries.append({
            "id": comp_id,
            "strategy": comp.get("strategy", comp_id),
            "system": comp.get("system", "Unknown"),
            "family": family,
            "total_trades": total_trades,
            "win_rate": wr,
            "expectancy_usdt": round(expectancy, 2),
            "total_pnl_usdt": round(total_pnl, 2),
            "max_dd_usdt": round(max_dd, 2),
            "sharpe": comp.get("sharpe_annualized", 0),
            "long_wr": comp.get("long_wr", 0),
            "short_wr": comp.get("short_wr", 0),
            "recommendation": recommendation,
            "alerts": comp_alerts,
        })

        # Family aggregation
        if family not in family_aggregation:
            family_aggregation[family] = {
                "total_trades": 0, "wins": 0, "total_pnl": 0.0,
                "components": 0, "strategies": [],
            }
        fam = family_aggregation[family]
        fam["total_trades"] += total_trades
        fam["wins"] += comp.get("wins", 0)
        fam["total_pnl"] += total_pnl
        fam["components"] += 1
        fam["strategies"].append(comp_id)

    # Finalize family metrics
    for fam_name, fam in family_aggregation.items():
        fam["win_rate"] = round(fam["wins"] / fam["total_trades"], 4) if fam["total_trades"] > 0 else 0
        fam["avg_pnl"] = round(fam["total_pnl"] / fam["total_trades"], 2) if fam["total_trades"] > 0 else 0

    # Sort components by expectancy (best first)
    component_summaries.sort(key=lambda x: x["expectancy_usdt"], reverse=True)

    report = {
        "generated_at": now.isoformat(),
        "report_period": f"Last {lookback_days} days (from {(now - timedelta(days=lookback_days)).date()} to {now.date()})",
        "overview": {
            "total_components": len(component_summaries),
            "total_trades": sum(c["total_trades"] for c in component_summaries),
            "total_pnl": round(sum(c["total_pnl_usdt"] for c in component_summaries), 2),
            "overall_wr": round(
                sum(c["win_rate"] * c["total_trades"] for c in component_summaries) /
                max(1, sum(c["total_trades"] for c in component_summaries)),
                4
            ),
            "active_alerts": len(alerts),
        },
        "alerts": alerts,
        "family_breakdown": family_aggregation,
        "components": component_summaries,
        "thresholds_used": ALERT_THRESHOLDS,
    }

    # Save JSON report
    with open(REPORT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    log.info("JSON report saved to %s", REPORT_JSON_PATH)

    # Generate Markdown report
    _generate_markdown_report(report)

    return report


def _generate_markdown_report(report: dict):
    """Generate a human-readable Markdown report."""
    now = datetime.now(timezone.utc)
    lines = []

    lines.append(f"# 📊 Weekly PM Report — {now.strftime('%Y-%m-%d')}")
    lines.append("")
    lines.append(f"> **Generated:** {now.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    lines.append(f"> **Period:** {report['report_period']}")
    lines.append(f"> **Source:** Mercury AI PM Framework")
    lines.append("")

    # Overview
    ov = report["overview"]
    lines.append("## 📈 Overview")
    lines.append("")
    lines.append(f"| Metric | Value |")
    lines.append(f"|---|---|")
    lines.append(f"| **Total Components** | {ov['total_components']} |")
    lines.append(f"| **Total Trades** | {ov['total_trades']} |")
    lines.append(f"| **Total PnL** | ${ov['total_pnl']:,.2f} |")
    lines.append(f"| **Overall WR** | {ov['overall_wr']:.1%} |")
    lines.append(f"| **Active Alerts** | {ov['active_alerts']} |")
    lines.append("")

    # Alerts
    if report["alerts"]:
        lines.append("## 🚨 Active Alerts")
        lines.append("")
        for alert in report["alerts"]:
            lines.append(f"- {alert}")
        lines.append("")

    # Family breakdown
    lines.append("## 👨‍👩‍👧‍👦 Family Breakdown")
    lines.append("")
    lines.append("| Family | Components | Trades | WR | Avg PnL | Total PnL |")
    lines.append("|---|---|---|---|---|---|")
    for fam_name, fam in sorted(report["family_breakdown"].items(), key=lambda x: x[1]["total_pnl"], reverse=True):
        lines.append(
            f"| **{fam_name}** | {fam['components']} | {fam['total_trades']} | "
            f"{fam['win_rate']:.0%} | ${fam['avg_pnl']:.2f} | ${fam['total_pnl']:,.2f} |"
        )
    lines.append("")

    # Top performers
    lines.append("## 🏆 Top Performers")
    lines.append("")
    lines.append("| Strategy | System | Trades | WR | Expectancy | Total PnL | Sharpe | Action |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for comp in report["components"][:10]:
        icon = "✅" if comp["recommendation"] == "CORE_QUALIFIED" else "🟡"
        lines.append(
            f"| {icon} {comp['strategy']} | {comp['system']} | {comp['total_trades']} | "
            f"{comp['win_rate']:.0%} | ${comp['expectancy_usdt']:.2f} | "
            f"${comp['total_pnl_usdt']:,.2f} | {comp['sharpe']:.1f} | {comp['recommendation']} |"
        )
    lines.append("")

    # Bottom performers
    bottom = [c for c in report["components"] if c["recommendation"] in ("KILL", "DEMOTE_TO_INCUBATOR")]
    if bottom:
        lines.append("## ⚠️ Flagged Components")
        lines.append("")
        lines.append("| Strategy | System | Trades | WR | Expectancy | Total PnL | Action |")
        lines.append("|---|---|---|---|---|---|---|")
        for comp in bottom:
            icon = "☠️" if comp["recommendation"] == "KILL" else "🔻"
            lines.append(
                f"| {icon} {comp['strategy']} | {comp['system']} | {comp['total_trades']} | "
                f"{comp['win_rate']:.0%} | ${comp['expectancy_usdt']:.2f} | "
                f"${comp['total_pnl_usdt']:,.2f} | **{comp['recommendation']}** |"
            )
        lines.append("")

    # Direction analysis
    dir_anomalies = [c for c in report["components"] if c.get("long_wr", 1) < 0.30 and c["total_trades"] >= 5]
    if dir_anomalies:
        lines.append("## 📉 Direction Asymmetry")
        lines.append("")
        lines.append("| Strategy | Long WR | Short WR | Recommendation |")
        lines.append("|---|---|---|---|")
        for comp in dir_anomalies:
            lines.append(
                f"| {comp['strategy']} | {comp['long_wr']:.0%} | {comp['short_wr']:.0%} | SHORT ONLY |"
            )
        lines.append("")

    # Mercury AI thresholds
    lines.append("## 📏 Mercury AI Thresholds (Reference)")
    lines.append("")
    lines.append("| Metric | Alert Condition | Frequency |")
    lines.append("|---|---|---|")
    lines.append("| Component Expectancy | < 0% → demote/kill | Weekly |")
    lines.append("| Win Rate | < 30% → demote | Weekly |")
    lines.append("| Max DD | > 5% of allocation → demote | Weekly |")
    lines.append("| Turnover | > 30% of allocation → review | Weekly |")
    lines.append("| Slippage Drift | > 0.2% per trade → tighten RR | Weekly |")
    lines.append("| Regime Decay | Regime flag flip → pause | Real-time |")
    lines.append("")

    lines.append("---")
    lines.append(f"*Report generated by Weekly PM Report Generator • {now.strftime('%Y-%m-%d %H:%M UTC')}*")

    md_content = "\n".join(lines)
    with open(REPORT_MD_PATH, "w", encoding="utf-8") as f:
        f.write(md_content)
    log.info("Markdown report saved to %s", REPORT_MD_PATH)


def main():
    """Generate the weekly PM report."""
    report = generate_weekly_report(lookback_days=7)
    print(f"\n✅ Weekly PM Report generated with {report['overview']['total_components']} components")
    print(f"   Active alerts: {report['overview']['active_alerts']}")
    print(f"   JSON: {REPORT_JSON_PATH}")
    print(f"   MD:   {REPORT_MD_PATH}")


if __name__ == "__main__":
    main()
