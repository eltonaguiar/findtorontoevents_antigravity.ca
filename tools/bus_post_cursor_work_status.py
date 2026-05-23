#!/usr/bin/env python3
"""Publish CURSOR_WORK_STATUS to alpha_engine_bus — finished vs planned peer work.

Optional JSON override (same shape as default payload.work_status):

  {
    "finished": ["..."],
    "planned": ["..."],
    "git_ref": "main@abc1234"
  }

Usage:
  python tools/bus_post_cursor_work_status.py
  python tools/bus_post_cursor_work_status.py path/to/status_fragment.json
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FROM_ID = "cursor-composer"
TOPIC = "CURSOR_WORK_STATUS"


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


def _default_work_status() -> dict:
    return {
        "finished": [
            "TV crypto pick-universe backtest: crypto_tv_universe_runner.py (Binance 1d, mirror failover), "
            "20 institutional vector strategies, artifact alpha_engine/data/crypto_tv_pick_universe_backtest.json.",
            "Strategies + matrix runner + config: institutional_vector_signals.py, institutional_matrix_runner.py, "
            "config/institutional_strategy_matrix.json.",
            "Contract test tests/test_crypto_tv_pick_universe_backtest.py; bus tool tools/bus_post_tv_crypto_backtest.py "
            "(topic CRYPTO_TV_PICK_UNIVERSE_BACKTEST).",
            "Changes merged to origin/main (see git_ref).",
        ],
        "planned": [
            "Optional: add KuCoin/OKX (or other) daily OHLCV fallback in crypto_tv_universe_runner for symbols "
            "that fail Binance spot 1d (reduces errors=8 class of skips).",
            "Optional: scheduled CI or cron to refresh crypto_tv_pick_universe_backtest.json and post bus after merge.",
            "Optional: run python -m alpha_engine.backtest.institutional_matrix_runner (--quick in CI) to populate "
            "alpha_engine/data/institutional_suite_backtest_results.json when yfinance is available.",
            "If still desired: restore GH workflows for multi-asset smart-picks agents under .github/workflows/ "
            "and align paths with repo layout.",
        ],
        "git_ref": "main@%s" % _git_head(),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Post Cursor finished/planned work status to Redis bus")
    ap.add_argument(
        "override_json",
        nargs="?",
        default=None,
        help="Optional JSON file with keys finished, planned, git_ref (partial merge into default)",
    )
    args = ap.parse_args()

    work = _default_work_status()
    if args.override_json:
        p = Path(args.override_json)
        if not p.is_file():
            print("missing override: %s" % p, file=sys.stderr)
            return 1
        frag = json.loads(p.read_text(encoding="utf-8"))
        for k in ("finished", "planned", "git_ref"):
            if k in frag and frag[k]:
                if k == "git_ref":
                    work[k] = frag[k]
                else:
                    work[k] = list(frag[k])

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    summary = (
        "Cursor work status | finished=%d items | planned=%d items | %s"
        % (len(work["finished"]), len(work["planned"]), work.get("git_ref", ""))
    )

    envelope = {
        "schema_version": 1,
        "from": FROM_ID,
        "topic": TOPIC,
        "timestamp_utc": ts,
        "summary": summary[:1200],
        "doc_path_repo_relative": "tools/bus_post_cursor_work_status.py",
        "related_artifacts": [
            "alpha_engine/backtest/crypto_tv_universe_runner.py",
            "tools/bus_post_tv_crypto_backtest.py",
        ],
        "work_status": work,
    }
    body = json.dumps(envelope, ensure_ascii=False)

    try:
        import redis  # noqa: WPS433
    except ImportError:
        print("redis not installed; envelope:", file=sys.stderr)
        print(body[:2500])
        return 0

    try:
        r = redis.Redis(host="localhost", port=6379, decode_responses=True)
        r.ping()
    except Exception as exc:
        print("Redis unavailable (%s); envelope:" % exc, file=sys.stderr)
        print(body[:2500])
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
