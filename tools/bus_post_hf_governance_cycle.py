#!/usr/bin/env python3
"""Publish hedge-fund governance cycle payload to Redis bus."""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REDIS_CLI = "C:/Users/zerou/redis-bus/redis-cli.exe"
PORT = 6379
TOPIC = "HF_GOVERNANCE_CYCLE"
DEFAULT_REVIEW = Path(__file__).resolve().parents[1] / "audit_trail" / "data" / "hf_enhancement_review.json"


def run_redis_cmd(args: list[str]) -> tuple[str, int]:
    cmd = [REDIS_CLI, "-p", str(PORT)] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout.strip(), result.returncode


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--review-json", type=Path, default=DEFAULT_REVIEW)
    ap.add_argument("--from-id", default="cursor-hf-governance")
    ap.add_argument("--inbox-peers", default="cursor-hc-filter,cursor-hc-filter-v3")
    args = ap.parse_args()

    if not args.review_json.is_file():
        print("Missing review JSON:", args.review_json)
        return 1

    review = json.loads(args.review_json.read_text(encoding="utf-8"))
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    summary = {
        "counts": review.get("counts", {}),
        "closed_by_asset_class": review.get("closed_by_asset_class", {}),
        "closed_by_trust_tier": review.get("closed_by_trust_tier", {}),
        "active_concentration": review.get("active_concentration", {}),
        "active_pass_watchlist": review.get("active_pass_watchlist", {}),
        "score_tier_validation": review.get("score_tier_validation", {}),
        "strategy_diagnostics": review.get("strategy_diagnostics", {}),
        "manager_actions": review.get("manager_actions", {}),
    }

    envelope = {
        "bus_topic": TOPIC,
        "topic": TOPIC,
        "schema_version": 1,
        "from": args.from_id,
        "ts": ts,
        "timestamp_utc": ts,
        "summary": (
            "HF governance cycle: asset-class PnL review, trust-tier separation, "
            "active concentration, and sleeve actions. See review JSON for full matrix."
        ),
        "review_snapshot": summary,
        "doc_path_repo_relative": "audit_trail/data/hf_enhancement_review.json",
        "related_artifacts": [
            "tools/hf_enhancement_review.py",
            "tools/run_hf_weekly_verify.py",
            "config/risk_policy.json",
            "alpha_engine/smart_picks_engine.py",
        ],
        "coordination": {
            "peer_append_topic": "HF_MERGED_PLAN_PEER_APPEND",
            "required_fields": [
                "asset_class_perf",
                "trust_tier_perf",
                "system_x_asset_class_top_bottom",
                "active_pass_concentration",
                "actions_taken",
            ],
            "peer_validation_requests": [
                "confirm tierSABypassIndependentConsensus is not bypassing blacklist gates",
                "identify stale docs with obsolete DO_NOT_MERGE language",
                "review equity/forex sleeve cap enforcement and bypass paths",
            ],
        },
    }
    body = json.dumps(envelope, separators=(",", ":"))
    _, code_pub = run_redis_cmd(["PUBLISH", "alpha_engine_bus", body])
    short = f"{TOPIC} | {ts} | review={args.review_json.name}"
    _, code_push = run_redis_cmd(["LPUSH", "bus:broadcast:log", short])
    run_redis_cmd(["LTRIM", "bus:broadcast:log", "0", "99"])

    for peer in [p.strip() for p in args.inbox_peers.split(",") if p.strip()]:
        peer_msg = json.dumps(
            {
                "from": args.from_id,
                "to": peer,
                "timestamp": ts,
                "topic": TOPIC,
                "body": envelope["summary"],
            },
            separators=(",", ":"),
        )
        run_redis_cmd(["LPUSH", f"agent:{peer}:inbox", peer_msg])
        run_redis_cmd(["LTRIM", f"agent:{peer}:inbox", "0", "49"])

    ok = code_pub == 0 and code_push == 0
    print("[OK]" if ok else "[WARN]", short)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

