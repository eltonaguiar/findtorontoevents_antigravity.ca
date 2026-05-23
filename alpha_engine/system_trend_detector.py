#!/usr/bin/env python3
"""System Performance Trend Detector.

Compares short-term vs long-term performance for each trading system,
detecting hot/cold streaks and trend reversals.

Output: alpha_engine/data/system_trends.json
"""
import sys, os, io

# Windows UTF-8 fix
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

PAYLOAD_PATH = Path(__file__).resolve().parent.parent / "audit_trail" / "data" / "dashboard_payload.json"
OUTPUT_PATH = Path(__file__).resolve().parent / "data" / "system_trends.json"

WINDOWS = [
    ("4h", timedelta(hours=4)),
    ("8h", timedelta(hours=8)),
    ("24h", timedelta(hours=24)),
]


def load_closed_picks():
    """Load recent_closed picks from dashboard payload."""
    if not PAYLOAD_PATH.exists():
        print(f"[trend] Payload not found: {PAYLOAD_PATH}")
        return []
    with open(PAYLOAD_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    picks = data.get("picks", {}).get("recent_closed", [])
    print(f"[trend] Loaded {len(picks)} closed picks")
    return picks


def parse_ts(ts_str):
    """Parse ISO timestamp to datetime, tolerant of various formats."""
    if not ts_str:
        return None
    try:
        ts_str = ts_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(ts_str)
        # Ensure timezone-aware (UTC)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def compute_window_stats(picks, now, window_td=None):
    """Compute WR and PnL for picks within a time window (None = all time)."""
    if window_td is not None:
        cutoff = now - window_td
        subset = [p for p in picks if p["_ts"] and p["_ts"] >= cutoff]
    else:
        subset = picks

    if not subset:
        return {"trades": 0, "wr": 0.0, "pnl": 0.0}

    wins = sum(1 for p in subset if (p.get("pnl_pct") or 0) > 0)
    total = len(subset)
    pnl = sum(p.get("pnl_pct") or 0 for p in subset)
    wr = round((wins / total) * 100, 1) if total > 0 else 0.0
    return {"trades": total, "wr": wr, "pnl": round(pnl, 2)}


def detect_trend(stats):
    """Detect trend type based on window stats.

    Returns (trend_type, detail_message).
    """
    s4h = stats.get("4h", {})
    s8h = stats.get("8h", {})
    s24h = stats.get("24h", {})
    s_all = stats.get("all", {})

    wr_4h = s4h.get("wr", 0)
    wr_8h = s8h.get("wr", 0)
    wr_24h = s24h.get("wr", 0)
    wr_all = s_all.get("wr", 0)
    trades_4h = s4h.get("trades", 0)
    trades_24h = s24h.get("trades", 0)

    # Need minimum trades for meaningful detection
    if s_all.get("trades", 0) < 3:
        return "INSUFFICIENT_DATA", "Too few trades for trend detection"

    # HOT STREAK: 4h WR 20+ points above all-time (min 2 trades in 4h)
    if trades_4h >= 2 and wr_4h - wr_all >= 20:
        diff = round(wr_4h - wr_all, 1)
        return "HOT_STREAK", f"Currently {wr_4h}% WR (4h) vs {wr_all}% all-time = +{diff}pp improvement. On fire!"

    # COLD STREAK: 4h WR 20+ points below all-time (min 2 trades in 4h)
    if trades_4h >= 2 and wr_all - wr_4h >= 20:
        diff = round(wr_all - wr_4h, 1)
        return "COLD_STREAK", f"Currently {wr_4h}% WR (4h) vs {wr_all}% all-time = -{diff}pp decline. Struggling!"

    # NEWLY BROKEN: all-time >= 50% but last 24h < 35% (min 3 trades in 24h)
    if trades_24h >= 3 and wr_all >= 50 and wr_24h < 35:
        return "NEWLY_BROKEN", f"Was {wr_all}% all-time but only {wr_24h}% in last 24h ({trades_24h} trades). Something changed!"

    # NEWLY FIXED: all-time < 40% but last 24h >= 60% (min 3 trades in 24h)
    if trades_24h >= 3 and wr_all < 40 and wr_24h >= 60:
        return "NEWLY_FIXED", f"Was only {wr_all}% all-time but {wr_24h}% in last 24h ({trades_24h} trades). Improvement detected!"

    # TRENDING UP: each shorter window better than longer (need data in all windows)
    if trades_4h >= 2 and wr_4h > wr_8h > wr_24h:
        return "TRENDING_UP", f"Improving: {wr_24h}% (24h) -> {wr_8h}% (8h) -> {wr_4h}% (4h)"

    # TRENDING DOWN: each shorter window worse than longer
    if trades_4h >= 2 and wr_4h < wr_8h < wr_24h:
        return "TRENDING_DOWN", f"Declining: {wr_24h}% (24h) -> {wr_8h}% (8h) -> {wr_4h}% (4h)"

    return "STABLE", f"{wr_4h}% (4h) vs {wr_all}% all-time — no significant trend"


def main():
    picks = load_closed_picks()
    if not picks:
        print("[trend] No picks to analyze")
        return

    now = datetime.now(timezone.utc)

    # Parse timestamps once
    for p in picks:
        p["_ts"] = parse_ts(p.get("timestamp"))

    # Group by source_system
    by_system = {}
    for p in picks:
        sys_name = p.get("source_system", "unknown")
        by_system.setdefault(sys_name, []).append(p)

    systems_output = {}
    alerts = []

    for sys_name, sys_picks in sorted(by_system.items()):
        stats = {}
        for label, td in WINDOWS:
            stats[label] = compute_window_stats(sys_picks, now, td)
        stats["all"] = compute_window_stats(sys_picks, now, None)

        trend, detail = detect_trend(stats)
        systems_output[sys_name] = {
            **stats,
            "trend": trend,
            "trend_detail": detail,
        }

        # Generate alerts for actionable trends
        if trend in ("HOT_STREAK", "COLD_STREAK", "NEWLY_BROKEN", "NEWLY_FIXED", "TRENDING_UP", "TRENDING_DOWN"):
            alerts.append({
                "system": sys_name,
                "type": trend,
                "msg": detail,
            })

    # Sort alerts: critical first
    priority = {"NEWLY_BROKEN": 0, "COLD_STREAK": 1, "HOT_STREAK": 2, "NEWLY_FIXED": 3, "TRENDING_DOWN": 4, "TRENDING_UP": 5}
    alerts.sort(key=lambda a: priority.get(a["type"], 99))

    output = {
        "generated_at": now.isoformat(),
        "total_systems_analyzed": len(systems_output),
        "alert_count": len(alerts),
        "systems": systems_output,
        "alerts": alerts,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"[trend] Analyzed {len(systems_output)} systems, {len(alerts)} alerts")
    print(f"[trend] Output: {OUTPUT_PATH}")
    for a in alerts[:10]:
        icon = {"HOT_STREAK": "🔥", "COLD_STREAK": "🧊", "NEWLY_BROKEN": "💔", "NEWLY_FIXED": "🔧", "TRENDING_UP": "📈", "TRENDING_DOWN": "📉"}.get(a["type"], "")
        print(f"  {icon} [{a['type']}] {a['system']}: {a['msg']}")


if __name__ == "__main__":
    main()
