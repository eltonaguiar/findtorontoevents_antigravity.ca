#!/usr/bin/env python3
"""Publish UNIQUE_EDGE_STRATEGIES_INTEGRATED to alpha_engine_bus.

Announces LSR/OBB/VDR/VRM/SMC wiring: alpha_engine/unique_edge_live.py + scanner registry.
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FROM_ID = "cursor-composer"
TOPIC = "UNIQUE_EDGE_STRATEGIES_INTEGRATED"


def _git_head() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(REPO),
            stderr=subprocess.DEVNULL,
            text=True,
        )
        return out.strip()
    except Exception:
        return "unknown"


def main() -> int:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    bt = REPO / "alpha_engine" / "data" / "unique_edge_backtest_results.json"
    meta = {}
    if bt.is_file():
        try:
            blob = json.loads(bt.read_text(encoding="utf-8"))
            meta = {
                "symbols_tested": blob.get("symbols_tested"),
                "total_trades": (blob.get("aggregate") or {}).get("total_trades"),
                "avg_win_rate": (blob.get("aggregate") or {}).get("avg_win_rate"),
                "avg_profit_factor": (blob.get("aggregate") or {}).get("avg_profit_factor"),
                "best_strategy": (blob.get("aggregate") or {}).get("best_strategy"),
                "best_symbol": (blob.get("aggregate") or {}).get("best_symbol"),
            }
        except Exception:
            pass

    summary = (
        "Unique Edge integrated: LSR OBB VDR VRM SMC → CRYPTO_STRATEGIES + config + dashboard | git %s"
        % _git_head()
    )
    envelope = {
        "schema_version": 1,
        "from": FROM_ID,
        "topic": TOPIC,
        "timestamp_utc": ts,
        "summary": summary[:1200],
        "doc_path_repo_relative": "alpha_engine/unique_edge_live.py",
        "related_artifacts": [
            "unique_edge_strategies.py",
            "alpha_engine/data/unique_edge_backtest_results.json",
            "alpha_engine/crypto_strategies.py",
        ],
        "strategies": ["unique_edge_lsr", "unique_edge_obb", "unique_edge_vdr", "unique_edge_vrm", "unique_edge_smc"],
        "backtest_file_meta": meta,
        "planned_from_bus": [
            "Strategy optimization",
            "Live paper trading deployment",
            "Multi-timeframe enhancement",
            "Portfolio integration",
        ],
    }
    body = json.dumps(envelope, ensure_ascii=False)

    try:
        import redis  # noqa: WPS433
    except ImportError:
        print(body[:3500], file=sys.stderr)
        return 0

    try:
        r = redis.Redis(host="localhost", port=6379, decode_responses=True)
        r.ping()
    except Exception as exc:
        print("Redis unavailable (%s)" % exc, file=sys.stderr)
        print(body[:3500], file=sys.stderr)
        return 0

    r.publish("alpha_engine_bus", body)
    r.lpush("bus:alpha_engine_bus:log", body)
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
