#!/usr/bin/env python3
"""Publish RESEARCH_EDGE_SCANNERS_V1 ship notice to alpha_engine_bus.

Announces completion of the three research-backed scanners:
  - crypto_rvol_1h_momentum_scanner
  - forex_carry_unwind_jpy_short
  - london_session_breakout (GBP-only + SMA50 fix)

Usage:
  python tools/bus_post_research_edge_scanners.py
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FROM_ID = "cursor-composer"
TOPIC = "RESEARCH_EDGE_SCANNERS_V1"


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
    scanners = {
        "crypto_rvol_1h_momentum_scanner": {
            "module": "alpha_engine/research_edge_scanners.py",
            "rules": "Binance 1H: RVOL>=3 vs 20-bar mean, taker buy/volume>=0.65, RSI(14)>50; top 40 USDT by 24h quote volume",
        },
        "forex_carry_unwind_jpy_short": {
            "module": "alpha_engine/forex_strategies.py",
            "rules": "VIX>20, FX vol_ratio(20d/60d) in (1.5,2.0], price<SMA50 on JPY-quote pairs; SELL; not session-gated",
        },
        "london_session_breakout": {
            "module": "alpha_engine/forex_strategies.py",
            "rules": "GBPUSD=X + GBPJPY=X only; Asia compression breakout; long requires close>SMA50, short requires close<SMA50",
        },
    }
    summary = (
        "Research edge scanners v1 shipped: RVOL 1H crypto + JPY carry-unwind SHORT + GBP London breakout fix | git %s"
        % _git_head()
    )
    envelope = {
        "schema_version": 1,
        "from": FROM_ID,
        "topic": TOPIC,
        "timestamp_utc": ts,
        "summary": summary[:1200],
        "doc_path_repo_relative": "tools/bus_post_research_edge_scanners.py",
        "related_artifacts": [
            "alpha_engine/research_edge_scanners.py",
            "alpha_engine/forex_strategies.py",
            "alpha_engine/scanner.py",
            "alpha_engine/smart_picks_engine.py",
            "alpha_engine/non_crypto_quality_gate.py",
            "alpha_engine/config.py",
        ],
        "scanners": scanners,
    }
    body = json.dumps(envelope, ensure_ascii=False)

    try:
        import redis  # noqa: WPS433
    except ImportError:
        print(body[:3000], file=sys.stderr)
        return 0

    try:
        r = redis.Redis(host="localhost", port=6379, decode_responses=True)
        r.ping()
    except Exception as exc:
        print("Redis unavailable (%s)" % exc, file=sys.stderr)
        print(body[:3000], file=sys.stderr)
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
