#!/usr/bin/env python3
"""Publish CRYPTO_TV_PICK_UNIVERSE_BACKTEST to alpha_engine_bus + broadcast log.

Reads ``alpha_engine/data/crypto_tv_pick_universe_backtest.json`` (from
``python -m alpha_engine.backtest.crypto_tv_universe_runner``), then PUBLISH +
LPUSH so peers can consume the artifact summary without re-running downloads.

Usage:
  python tools/bus_post_tv_crypto_backtest.py
  python tools/bus_post_tv_crypto_backtest.py path/to/crypto_tv_pick_universe_backtest.json
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

DEFAULT_JSON = REPO / "alpha_engine" / "data" / "crypto_tv_pick_universe_backtest.json"
FROM_ID = "cursor-composer"
TOPIC = "CRYPTO_TV_PICK_UNIVERSE_BACKTEST"


def main() -> int:
    ap = argparse.ArgumentParser(description="Post TV crypto universe backtest JSON to Redis bus")
    ap.add_argument(
        "json_path",
        nargs="?",
        default=str(DEFAULT_JSON),
        help="Path to crypto_tv_pick_universe_backtest.json",
    )
    args = ap.parse_args()
    path = Path(args.json_path)
    if not path.is_file():
        print("missing backtest json: %s" % path, file=sys.stderr)
        return 1

    blob = json.loads(path.read_text(encoding="utf-8"))
    rows = blob.get("rows") or []
    errs = blob.get("errors") or []
    n_picks = blob.get("tv_picks_n")
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    summary = (
        "TV crypto universe backtest: rows=%s errors=%s picks_n=%s | artifact: %s"
        % (len(rows), len(errs), n_picks, path.name)
    )

    envelope = {
        "schema_version": 1,
        "from": FROM_ID,
        "topic": TOPIC,
        "timestamp_utc": ts,
        "summary": summary[:1200],
        "doc_path_repo_relative": "alpha_engine/backtest/crypto_tv_universe_runner.py",
        "related_artifacts": [
            str(path.relative_to(REPO)).replace("\\", "/"),
            "config/institutional_strategy_matrix.json",
            "alpha_engine/strategies/institutional_vector_signals.py",
        ],
        "crypto_tv_pick_universe_backtest": {
            "generated_at": blob.get("generated_at"),
            "tv_picks_n": n_picks,
            "strategies_n": blob.get("strategies_n"),
            "rows_n": len(rows),
            "errors_n": len(errs),
            "errors_head": errs[:15],
        },
    }
    body = json.dumps(envelope, ensure_ascii=False)

    try:
        import redis  # noqa: WPS433
    except ImportError:
        print("redis not installed; printed envelope only", file=sys.stderr)
        print(body[:2000])
        return 0

    try:
        r = redis.Redis(host="localhost", port=6379, decode_responses=True)
        r.ping()
    except Exception as exc:
        print("Redis unavailable (%s); printed envelope only" % exc, file=sys.stderr)
        print(body[:2000])
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
