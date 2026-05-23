"""
Data Quality Audit for Audit Dashboard — Mercury 2 Section 4

Detects and reports data quality issues:
- Blank/missing values
- Mismatched types
- Duplicate rows
- Stale timestamps
- Score/PnL inconsistencies
"""

import json
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from typing import Optional


def _float(val, default=0.0):
    """Safe float conversion."""
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def audit_pick_quality(picks: list[dict]) -> dict:
    """
    Comprehensive data quality audit of picks.

    Returns dict with issues identified and statistics.
    """
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_picks": len(picks),
        "issues": {
            "missing_fields": [],
            "mismatched_types": [],
            "duplicate_rows": [],
            "stale_timestamps": [],
            "score_pnl_inconsistency": [],
            "null_values": [],
        },
        "statistics": {
            "picks_with_nulls": 0,
            "null_field_count": 0,
            "duplicate_symbols": {},
            "stale_threshold_hours": 24,
            "stale_picks": 0,
            "score_pnl_divergence_count": 0,
        },
        "health_score": 100,
    }

    critical_fields = ["symbol", "direction", "entry_price", "confidence", "score", "timestamp"]
    type_fields = {"score": (int, float), "pnl_pct": (int, float), "confidence": (int, float)}

    seen = {}  # For duplicate detection
    stale_threshold = datetime.now(timezone.utc) - timedelta(hours=24)

    for i, pick in enumerate(picks):
        pick_id = pick.get("id", f"pick_{i}")

        # 1. Check for missing critical fields
        for field in critical_fields:
            if field not in pick or pick[field] is None or pick[field] == "":
                report["issues"]["missing_fields"].append(
                    {"pick_id": pick_id, "field": field, "value": pick.get(field)}
                )

        # 2. Check for null values in any field
        null_count = 0
        for key, val in pick.items():
            if val is None or val == "":
                null_count += 1
        if null_count > 0:
            report["statistics"]["picks_with_nulls"] += 1
            report["statistics"]["null_field_count"] += null_count

        # 3. Type mismatches
        for field, expected_types in type_fields.items():
            if field in pick and pick[field] is not None:
                val = pick[field]
                if not isinstance(val, expected_types):
                    try:
                        float(val)  # Try conversion
                    except (ValueError, TypeError):
                        report["issues"]["mismatched_types"].append(
                            {
                                "pick_id": pick_id,
                                "field": field,
                                "expected": str(expected_types),
                                "got": type(val).__name__,
                                "value": val,
                            }
                        )

        # 4. Duplicates (same symbol + direction + timestamp)
        key = (pick.get("symbol"), pick.get("direction"), pick.get("timestamp"))
        if key[0]:  # Only check if symbol exists
            if key in seen:
                report["issues"]["duplicate_rows"].append(
                    {
                        "symbol": key[0],
                        "direction": key[1],
                        "timestamp": key[2],
                        "count": 2,
                        "pick_ids": [seen[key], pick_id],
                    }
                )
                if key[0] not in report["statistics"]["duplicate_symbols"]:
                    report["statistics"]["duplicate_symbols"][key[0]] = 0
                report["statistics"]["duplicate_symbols"][key[0]] += 1
            else:
                seen[key] = pick_id

        # 5. Stale timestamps
        try:
            ts_str = pick.get("timestamp", "")
            if ts_str:
                ts_clean = ts_str.strip()
                for tz_suffix in (" EST", " EDT", " UTC", " GMT", " PST", " PDT", " CST", " CDT"):
                    if ts_clean.endswith(tz_suffix):
                        ts_clean = ts_clean[: -len(tz_suffix)]
                        break
                pick_dt = datetime.fromisoformat(ts_clean.replace("Z", "+00:00"))
                if pick_dt.tzinfo is None:
                    pick_dt = pick_dt.replace(tzinfo=timezone.utc)

                if pick_dt < stale_threshold:
                    age_days = (datetime.now(timezone.utc) - pick_dt).total_seconds() / 86400
                    report["issues"]["stale_timestamps"].append(
                        {
                            "pick_id": pick_id,
                            "symbol": pick.get("symbol"),
                            "timestamp": ts_str,
                            "age_days": round(age_days, 1),
                        }
                    )
                    report["statistics"]["stale_picks"] += 1
        except Exception:
            pass

        # 6. Score/PnL inconsistency
        score = _float(pick.get("score"), 50.0)
        pnl_pct = _float(pick.get("pnl_pct"), 0.0)
        pnl_score = max(0, min((pnl_pct + 50) * 2, 100))
        divergence = abs(score - pnl_score)

        if divergence > 30:
            report["issues"]["score_pnl_inconsistency"].append(
                {
                    "pick_id": pick_id,
                    "symbol": pick.get("symbol"),
                    "score": score,
                    "pnl_pct": pnl_pct,
                    "divergence": round(divergence, 1),
                    "severity": "HIGH" if divergence > 50 else "MEDIUM",
                }
            )
            report["statistics"]["score_pnl_divergence_count"] += 1

    # Calculate health score
    # Start at 100, deduct for each category of issues
    health_penalties = {
        "missing_fields": len(report["issues"]["missing_fields"]) * 2,
        "mismatched_types": len(report["issues"]["mismatched_types"]) * 1.5,
        "duplicate_rows": len(report["issues"]["duplicate_rows"]) * 3,
        "stale_timestamps": min(report["statistics"]["stale_picks"] * 0.1, 10),
        "score_pnl_inconsistency": min(report["statistics"]["score_pnl_divergence_count"] * 0.5, 10),
    }

    total_penalties = sum(health_penalties.values())
    report["health_score"] = max(0, 100 - total_penalties)

    # Limit issue lists to first 100 each
    for category in report["issues"]:
        if isinstance(report["issues"][category], list):
            report["issues"][category] = report["issues"][category][:100]

    return report


def generate_health_summary(report: dict) -> str:
    """Generate a human-readable health summary."""
    lines = []
    lines.append("=" * 60)
    lines.append("AUDIT DASHBOARD DATA QUALITY REPORT")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"Total Picks: {report['total_picks']}")
    lines.append(f"Health Score: {report['health_score']:.1f}/100")
    lines.append(f"Timestamp: {report['timestamp']}")
    lines.append("")

    # Issue summary
    lines.append("ISSUES DETECTED:")
    lines.append("-" * 60)
    issues = report["issues"]
    for category, items in issues.items():
        count = len(items) if isinstance(items, list) else 0
        if count > 0:
            lines.append(f"  ❌ {category}: {count}")

    stats = report["statistics"]
    if stats.get("picks_with_nulls", 0) > 0:
        lines.append(f"  ❌ Picks with null values: {stats['picks_with_nulls']}")
    if stats.get("stale_picks", 0) > 0:
        lines.append(f"  ⚠️  Stale picks (>24h): {stats['stale_picks']}")
    if stats.get("score_pnl_divergence_count", 0) > 0:
        lines.append(f"  ⚠️  Score/PnL divergence: {stats['score_pnl_divergence_count']}")

    lines.append("")
    lines.append("RECOMMENDATIONS:")
    lines.append("-" * 60)

    if report["health_score"] < 70:
        lines.append("  🔴 CRITICAL: Data quality below 70% — immediate action needed")
    elif report["health_score"] < 85:
        lines.append("  🟡 WARNING: Data quality below 85% — address soon")
    else:
        lines.append("  🟢 OK: Data quality acceptable")

    if stats.get("picks_with_nulls", 0) > len(report["total_picks"]) * 0.1:
        lines.append("  → Many picks with null values — check upstream data sources")

    if stats.get("stale_picks", 0) > len(report["total_picks"]) * 0.2:
        lines.append("  → Many stale picks — implement better cleanup/archival")

    if stats.get("score_pnl_divergence_count", 0) > len(report["total_picks"]) * 0.15:
        lines.append("  → Many score/PnL mismatches — recalibrate scoring logic")

    lines.append("")
    return "\n".join(lines)
