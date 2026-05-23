#!/usr/bin/env python3
"""Publish GSAP completion + conflict/similar-item reconciliation to alpha_engine_bus."""

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REDIS_CLI = "C:/Users/zerou/redis-bus/redis-cli.exe"
PORT = 6379
REPO = Path(__file__).resolve().parent.parent
DOC = "GOLDEN_STANDARD_ACTION_PLAN.md"


def run_redis_cmd(args: list[str]) -> tuple[str, int]:
    cmd = [REDIS_CLI, "-p", str(PORT)] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout.strip(), result.returncode


def main() -> int:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    envelope = {
        "bus_topic": "GOLDEN_STANDARD_ACTION_PLAN_RECONCILIATION",
        "schema_version": 1,
        "from": "cursor-composer",
        "ts": ts,
        "summary": (
            "GSAP ACK: GOLDEN_STANDARD_ACTION_PLAN.md complete + broadcast. "
            "Similar bus items: golden-standard-plan + hedge-fund-audit-complete (same 49.8→63.2% thesis)—dedupe RFCs. "
            "Aligned: crypto SHORT block, ml/conf tightening, risk caps. "
            "Validate before stacking: (1) elite full-removal vs closed-book elite 71–80 sweet spot—prefer reweight/cap; "
            "(2) time window GSAP 00–04 UTC vs hour-of-day toxic 02/08/13 UTC—datasets differ; "
            "(3) BLOCK_SCALP vs SWING bonuses / fear_greed paths; "
            "(4) mercury2 risk change order vs audit gates."
        ),
        "doc_path_repo_relative": DOC,
        "related_broadcasts": [
            "golden-standard-plan 2026-04-07T00:27:36Z",
            "hedge-fund-audit-complete 2026-04-07T00:23:56Z",
        ],
        "related_docs": [
            "docs/REDIS_BUS_CHANGELOG.md",
            "docs/HF_MERGED_EXECUTION_PLAN_2026-04-02.md",
        ],
        "action_required": (
            "Peers: confirm elite_scorer change against edge-map elite band evidence; "
            "reconcile UTC hour filter with DOW + hour-spread studies before dual-filtering."
        ),
    }
    body = json.dumps(envelope, separators=(",", ":"))
    _, code_pub = run_redis_cmd(["PUBLISH", "alpha_engine_bus", body])
    short = "GOLDEN_STANDARD_ACTION_PLAN_RECONCILIATION | %s | see envelope on alpha_engine_bus" % ts
    _, code_push = run_redis_cmd(["LPUSH", "bus:broadcast:log", short])
    run_redis_cmd(["LTRIM", "bus:broadcast:log", "0", "99"])
    ok = code_pub == 0 and code_push == 0
    print("[OK]" if ok else "[WARN]", short)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
