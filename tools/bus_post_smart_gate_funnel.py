#!/usr/bin/env python3
"""Publish SMART_GATE_FUNNEL_STATS to alpha_engine_bus + durable broadcast log.

Reads ``picks.active`` from dashboard JSON (default: audit_dashboard/data/dashboard_data.json),
runs ``summarize_smart_gate_funnel``, writes ``tools/data/smart_gate_funnel_snapshot.json``,
then PUBLISH + LPUSH so peers can see first-failure histograms without running the dashboard.

Usage:
  python tools/bus_post_smart_gate_funnel.py
  python tools/bus_post_smart_gate_funnel.py path/to/dashboard_data.json
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

DEFAULT_DASH = REPO / "audit_dashboard" / "data" / "dashboard_data.json"
SNAPSHOT_OUT = REPO / "tools" / "data" / "smart_gate_funnel_snapshot.json"
FROM_ID = "cursor-composer"
TOPIC = "SMART_GATE_FUNNEL_STATS"


def main() -> int:
    ap = argparse.ArgumentParser(description="Post smart gate funnel stats to Redis bus")
    ap.add_argument(
        "dashboard",
        nargs="?",
        default=str(DEFAULT_DASH),
        help="Path to dashboard_data.json",
    )
    args = ap.parse_args()
    path = Path(args.dashboard)
    if not path.is_file():
        print("missing dashboard: %s" % path, file=sys.stderr)
        return 1

    from audit_trail.quality_gates import summarize_smart_gate_funnel  # noqa: E402

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    picks = data.get("picks") or {}
    active = picks.get("active") or []
    funnel = summarize_smart_gate_funnel(active)

    SNAPSHOT_OUT.parent.mkdir(parents=True, exist_ok=True)
    snap_blob = {
        "dashboard_path": str(path),
        "dashboard_generated_at": (data.get("summary") or {}).get("generated_at")
        or data.get("generated_at"),
        **funnel,
    }
    SNAPSHOT_OUT.write_text(json.dumps(snap_blob, indent=2), encoding="utf-8")
    print("wrote %s" % SNAPSHOT_OUT)

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    counts = funnel.get("first_failure_counts") or {}
    top3 = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:3]
    top_s = ", ".join("%s=%s" % (k, v) for k, v in top3) if top3 else "n/a"
    summary = (
        "Smart gate funnel: active=%s passed=%s | top %s | run: python tools/audit_smart_gate_funnel.py"
        % (funnel.get("active_count"), funnel.get("passed"), top_s)
    )

    envelope = {
        "schema_version": 1,
        "from": FROM_ID,
        "topic": TOPIC,
        "timestamp_utc": ts,
        "summary": summary[:1200],
        "doc_path_repo_relative": "tools/audit_smart_gate_funnel.py",
        "related_artifacts": [
            "audit_trail/quality_gates.py",
            str(SNAPSHOT_OUT.relative_to(REPO)).replace("\\", "/"),
        ],
        "smart_gate_funnel": funnel,
    }
    body = json.dumps(envelope, ensure_ascii=False)

    try:
        import redis  # noqa: WPS433
    except ImportError:
        print("redis not installed; snapshot only", file=sys.stderr)
        return 0

    try:
        r = redis.Redis(host="localhost", port=6379, decode_responses=True)
        r.ping()
    except Exception as exc:
        print("Redis unavailable (%s); snapshot only" % exc, file=sys.stderr)
        return 0

    r.publish("alpha_engine_bus", body)
    r.lpush(
        "bus:alpha_engine_bus:log",
        body,
    )
    r.ltrim("bus:alpha_engine_bus:log", 0, 199)
    brief = json.dumps(
        {"from": FROM_ID, "timestamp": ts, "topic": TOPIC, "summary": summary[:500]},
        ensure_ascii=False,
    )
    r.lpush("bus:broadcast:log", brief)
    r.ltrim("bus:broadcast:log", 0, 99)
    print("[OK] PUBLISH alpha_engine_bus %s" % TOPIC)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
