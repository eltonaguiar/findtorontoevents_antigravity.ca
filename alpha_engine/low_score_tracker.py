#!/usr/bin/env python3
"""
ALPHA ENGINE -- Low-Score Winner Tracker
============================================
Runs hourly to track picks with score < 50 that are currently winning.
Builds evidence for scoring system improvements by logging snapshots of
hidden winners that would be missed by score-based filters.

Outputs:
  - alpha_engine/data/low_score_tracking.json  (rolling snapshots)
  - Updates CHATWITHIT.MD with latest anomaly data

Usage:
  python -m alpha_engine.low_score_tracker       # standalone
  python alpha_engine/low_score_tracker.py        # direct
"""
from __future__ import annotations

import json
import logging
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

# ── Windows UTF-8 fix ──
if sys.platform == "win32":
    os.environ.setdefault("PYTHONUTF8", "1")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent
PAYLOAD_PATH = ROOT / "audit_trail" / "data" / "dashboard_payload.json"
TRACKING_PATH = ROOT / "alpha_engine" / "data" / "low_score_tracking.json"
CHATWITHIT_PATH = ROOT / "CHATWITHIT.MD"

SCORE_THRESHOLD = 50
MAX_SNAPSHOTS = 168  # 7 days of hourly snapshots
MAX_TOP_PICKS = 25

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger("low_score_tracker")


def _float(v) -> float:
    """Safe float conversion."""
    try:
        return float(v or 0)
    except (ValueError, TypeError):
        return 0.0


def _classify_strategy_family(pick: dict) -> str:
    """Classify a pick into a broad strategy family for aggregation."""
    strategy = (pick.get("strategy") or "").lower()
    source = (pick.get("source_system") or "").lower()
    source_systems = pick.get("source_systems", [])
    agreeing = pick.get("agreeing_systems", [])

    combined = strategy + "|" + source
    for s in source_systems:
        combined += "|" + (s or "").lower()
    for ag in agreeing:
        combined += "|" + (ag.get("system", "") or "").lower()

    # Order matters: more specific families first
    families = [
        ("copy_trader_highscore", ["copy_trader_highscore", "highscore", "hs_"]),
        ("copy_trader_clones", ["copy_trader_clones", "clone_hl_"]),
        ("copy_trader_intel", ["copy_trader_intel", "copy_hl_", "copy_trader"]),
        ("kimi_signal_tracking", ["kimi_signal_tracking"]),
        ("rapid_fire", ["rapid_fire", "macd_crossover", "stochrsi_"]),
        ("binance_smart_money", ["binance_smart_money"]),
        ("luxalgo", ["luxalgo"]),
        ("super_signals", ["super_signals", "super consensus", "strong consensus"]),
        ("alpha_engine", ["alpha_engine"]),
    ]

    for family, tags in families:
        for tag in tags:
            if tag in combined:
                return family

    # Default: use source_system or strategy name
    if source:
        return source
    if strategy:
        return strategy.split("_")[0] if "_" in strategy else strategy
    return "unknown"


def run_tracker(payload_path: Path | None = None) -> dict:
    """
    Main entry point. Scans active picks for low-score winners and
    appends a snapshot to the tracking file.

    Returns the current snapshot.
    """
    if payload_path is None:
        payload_path = PAYLOAD_PATH

    if not payload_path.exists():
        log.error("Dashboard payload not found: %s", payload_path)
        return {"error": "payload_not_found"}

    log.info("=== Low-Score Winner Tracker v1.0 ===")

    with open(payload_path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    active_picks = payload.get("picks", {}).get("active", [])
    log.info("Total active picks: %d", len(active_picks))

    # ── Find low-score winners ──
    low_score_winners = []
    for pick in active_picks:
        score = _float(pick.get("score", 0))
        pnl = _float(pick.get("pnl_pct", 0))
        if score < SCORE_THRESHOLD and pnl > 0:
            low_score_winners.append(pick)

    log.info("Low-score winners (score<%d, PnL>0): %d", SCORE_THRESHOLD, len(low_score_winners))

    # ── Aggregate by strategy family ──
    by_strategy = defaultdict(lambda: {"count": 0, "pnl": 0.0, "scores": [], "symbols": []})
    for pick in low_score_winners:
        family = _classify_strategy_family(pick)
        pnl = _float(pick.get("pnl_pct", 0))
        score = _float(pick.get("score", 0))
        symbol = pick.get("symbol", "???")

        by_strategy[family]["count"] += 1
        by_strategy[family]["pnl"] += pnl
        by_strategy[family]["scores"].append(score)
        by_strategy[family]["symbols"].append(symbol)

    # Convert to serializable format
    strategy_summary = {}
    for family, data in sorted(by_strategy.items(), key=lambda x: x[1]["pnl"], reverse=True):
        avg_score = sum(data["scores"]) / len(data["scores"]) if data["scores"] else 0
        strategy_summary[family] = {
            "count": data["count"],
            "pnl": round(data["pnl"], 2),
            "avg_score": round(avg_score, 1),
        }

    # ── Top individual picks ──
    top_picks = sorted(low_score_winners, key=lambda p: _float(p.get("pnl_pct", 0)), reverse=True)[:MAX_TOP_PICKS]
    top_picks_data = []
    for pick in top_picks:
        top_picks_data.append({
            "symbol": pick.get("symbol", "???"),
            "pnl": round(_float(pick.get("pnl_pct", 0)), 2),
            "score": int(_float(pick.get("score", 0))),
            "strategy": pick.get("strategy", ""),
            "source_system": pick.get("source_system", ""),
            "family": _classify_strategy_family(pick),
            "direction": pick.get("direction", ""),
            "boosted": bool(pick.get("_score_boosted")),
            "original_score": pick.get("_original_score"),
        })

    total_missed_pnl = sum(_float(p.get("pnl_pct", 0)) for p in low_score_winners)

    # ── Build snapshot ──
    snapshot = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_active": len(active_picks),
        "total_low_score_winners": len(low_score_winners),
        "total_missed_pnl_pct": round(total_missed_pnl, 2),
        "score_threshold": SCORE_THRESHOLD,
        "by_strategy": strategy_summary,
        "top_picks": top_picks_data,
    }

    # ── Score revision recommendations ──
    recommendations = {}
    for family, data in strategy_summary.items():
        if data["count"] >= 3 and data["pnl"] > 5:
            # This family consistently wins with low scores
            current_avg = data["avg_score"]
            # Recommend boost to get average score to at least 55
            recommended_boost = max(10, int(55 - current_avg))
            recommended_boost = min(45, recommended_boost)  # Cap at 45

            reasons = []
            if data["count"] >= 10:
                reasons.append(f"{data['count']} active winners")
            else:
                reasons.append(f"{data['count']} winners")
            reasons.append(f"+{data['pnl']:.1f}% PnL")
            reasons.append(f"avg score {current_avg:.0f}")

            recommendations[family] = {
                "current_avg_score": round(current_avg, 1),
                "recommended_boost": recommended_boost,
                "reason": ", ".join(reasons),
            }

    # ── Load existing tracking data and append ──
    tracking_data = {"snapshots": [], "score_revision_recommendations": {}}
    if TRACKING_PATH.exists():
        try:
            with open(TRACKING_PATH, "r", encoding="utf-8") as f:
                tracking_data = json.load(f)
        except (json.JSONDecodeError, Exception) as e:
            log.warning("Failed to load existing tracking data: %s", e)

    # Append new snapshot (keep last MAX_SNAPSHOTS)
    tracking_data["snapshots"].append(snapshot)
    if len(tracking_data["snapshots"]) > MAX_SNAPSHOTS:
        tracking_data["snapshots"] = tracking_data["snapshots"][-MAX_SNAPSHOTS:]

    # Update recommendations (latest always wins)
    tracking_data["score_revision_recommendations"] = recommendations

    # Add trend data: compare with previous snapshot
    if len(tracking_data["snapshots"]) >= 2:
        prev = tracking_data["snapshots"][-2]
        trend = {
            "low_score_winners_delta": snapshot["total_low_score_winners"] - prev.get("total_low_score_winners", 0),
            "missed_pnl_delta": round(snapshot["total_missed_pnl_pct"] - prev.get("total_missed_pnl_pct", 0), 2),
            "improving": snapshot["total_low_score_winners"] < prev.get("total_low_score_winners", 0),
        }
        tracking_data["trend"] = trend

    # ── Save tracking data ──
    TRACKING_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(TRACKING_PATH, "w", encoding="utf-8") as f:
        json.dump(tracking_data, f, indent=2)
    log.info("Saved tracking data to %s (%d snapshots)", TRACKING_PATH, len(tracking_data["snapshots"]))

    # ── Update CHATWITHIT.MD ──
    _update_chatwithit(snapshot, recommendations)

    return snapshot


def _update_chatwithit(snapshot: dict, recommendations: dict) -> None:
    """Update CHATWITHIT.MD with latest tracking data."""
    try:
        if not CHATWITHIT_PATH.exists():
            log.warning("CHATWITHIT.MD not found, skipping update")
            return

        content = CHATWITHIT_PATH.read_text(encoding="utf-8")

        # Build the new section
        ts = snapshot["timestamp"][:19].replace("T", " ")
        lines = [
            "",
            "### LOW-SCORE TRACKER SNAPSHOT (auto-updated)",
            f"**Last scan:** {ts} UTC",
            f"**Low-score winners:** {snapshot['total_low_score_winners']} picks with score <{snapshot['score_threshold']} and PnL > 0",
            f"**Total missed PnL:** +{snapshot['total_missed_pnl_pct']:.2f}%",
            "",
            "| Strategy Family | Winners | Total PnL% | Avg Score | Recommended Boost |",
            "|-----------------|---------|------------|-----------|-------------------|",
        ]

        for family, data in sorted(snapshot["by_strategy"].items(), key=lambda x: x[1]["pnl"], reverse=True):
            rec = recommendations.get(family, {})
            boost_str = f"+{rec['recommended_boost']}" if rec else "-"
            lines.append(f"| {family} | {data['count']} | +{data['pnl']:.1f}% | {data['avg_score']:.0f} | {boost_str} |")

        lines.append("")
        if snapshot.get("top_picks"):
            lines.append("**Top 10 hidden winners:**")
            lines.append("")
            lines.append("| Symbol | PnL% | Score | Family |")
            lines.append("|--------|-------|-------|--------|")
            for pick in snapshot["top_picks"][:10]:
                boosted_marker = " (boosted)" if pick.get("boosted") else ""
                lines.append(f"| {pick['symbol']} | +{pick['pnl']:.2f}% | {pick['score']}{boosted_marker} | {pick['family']} |")
            lines.append("")

        new_section = "\n".join(lines)

        # Replace existing auto-updated section or append
        marker_start = "### LOW-SCORE TRACKER SNAPSHOT (auto-updated)"
        marker_end = "### "  # Next section header

        if marker_start in content:
            # Find and replace the existing section
            start_idx = content.index(marker_start)
            # Find the start of the next section after our section
            rest = content[start_idx + len(marker_start):]
            # Look for next ### that isn't our own
            next_section_idx = rest.find("\n### ")
            if next_section_idx >= 0:
                end_idx = start_idx + len(marker_start) + next_section_idx
                content = content[:start_idx] + new_section.lstrip("\n") + "\n" + content[end_idx + 1:]
            else:
                # Our section is at the end
                content = content[:start_idx] + new_section.lstrip("\n") + "\n"
        else:
            # Append after the RECOMMENDED SCORING CHANGES section
            content = content.rstrip() + "\n" + new_section + "\n"

        CHATWITHIT_PATH.write_text(content, encoding="utf-8")
        log.info("Updated CHATWITHIT.MD with latest snapshot")

    except Exception as e:
        log.warning("Failed to update CHATWITHIT.MD: %s", e)


if __name__ == "__main__":
    result = run_tracker()
    if "error" in result:
        print(f"ERROR: {result['error']}")
        sys.exit(1)

    print(f"\n=== Low-Score Winner Tracker Complete ===")
    print(f"Total active picks: {result.get('total_active', 0)}")
    print(f"Low-score winners (score<{SCORE_THRESHOLD}, PnL>0): {result['total_low_score_winners']}")
    print(f"Total missed PnL: +{result['total_missed_pnl_pct']:.2f}%")

    print(f"\nBy strategy family:")
    for family, data in sorted(result.get("by_strategy", {}).items(), key=lambda x: x[1]["pnl"], reverse=True):
        print(f"  {family}: {data['count']} winners, +{data['pnl']:.1f}% PnL, avg score {data['avg_score']:.0f}")

    if result.get("top_picks"):
        print(f"\nTop hidden winners:")
        for pick in result["top_picks"][:10]:
            print(f"  {pick['symbol']}: +{pick['pnl']:.2f}% (score {pick['score']}, {pick['family']})")
