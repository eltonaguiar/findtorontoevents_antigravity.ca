#!/usr/bin/env python3
"""Publish the audit high-certainty rollout summary to alpha_engine_bus."""

import json
import subprocess
from datetime import datetime, timezone

REDIS_CLI = "C:/Users/zerou/redis-bus/redis-cli.exe"
PORT = 6379


def run_redis_cmd(args):
    cmd = [REDIS_CLI, "-p", str(PORT)] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout.strip(), result.returncode


def main() -> int:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    envelope = {
        "bus_topic": "AUDIT_HIGH_CERTAINTY_ROLLOUT",
        "from": "cursor-composer",
        "ts": ts,
        "summary": (
            "Rolled out stricter crypto Smart Pick tradability gates on /audit: "
            "SANDBOX crypto blocked from Smart, trust>=5 required unless PROVEN, "
            "0.90+ confidence trapped unless proven/high-sample edge, and consensus "
            "bonus reduced for low-trust or correlated-looking rows. "
            "Also fixed smart_picks_count to use the final gated active pool."
        ),
        "doc_path_repo_relative": "docs/AUDIT_HIGH_CERTAINTY_ROLLOUT_2026-04-06.md",
        "related_artifacts": [
            "audit_trail/quality_gates.py",
            "audit_trail/dashboard_generator.py",
            "docs/AUDIT_HIGH_CERTAINTY_ROLLOUT_2026-04-06.md",
        ],
        "key_findings": {
            "crypto_min_trust_score": 5,
            "crypto_overconfidence_trap": 0.90,
            "crypto_sandbox_smart_pick_policy": "blocked",
            "smart_summary_source": "final_active_picks",
        },
        "action_required": (
            "Re-check the Smart Picks surface and downstream routing. "
            "If quality improves, replay this gate on closed picks and promote it from containment to baseline policy."
        ),
    }
    body = json.dumps(envelope, separators=(",", ":"))
    _, code = run_redis_cmd(["PUBLISH", "alpha_engine_bus", body])
    short = "AUDIT_HIGH_CERTAINTY_ROLLOUT | %s" % ts
    run_redis_cmd(["LPUSH", "bus:broadcast:log", short])
    run_redis_cmd(["LTRIM", "bus:broadcast:log", "0", "99"])
    print("[OK]" if code == 0 else "[WARN]", short)
    return 0 if code == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
