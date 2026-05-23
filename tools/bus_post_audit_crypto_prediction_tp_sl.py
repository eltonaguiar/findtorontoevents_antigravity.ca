#!/usr/bin/env python3
"""Publish AUDIT_CRYPTO_PREDICTION_TP_SL_QUALITY to alpha_engine_bus."""

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REDIS_CLI = "C:/Users/zerou/redis-bus/redis-cli.exe"
PORT = 6379
REPO = Path(__file__).resolve().parent.parent
DOC = "docs/AUDIT_CRYPTO_PREDICTION_TP_SL_QUALITY_2026-04-02.md"


def run_redis_cmd(args):
    cmd = [REDIS_CLI, "-p", str(PORT)] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout.strip(), result.returncode


def main() -> int:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    envelope = {
        "bus_topic": "AUDIT_CRYPTO_PREDICTION_TP_SL_QUALITY",
        "from": "cursor-composer",
        "ts": ts,
        "summary": (
            "Codebase review: /audit crypto pick quality + TP/SL. P0 unify _vol_aware_tp_sl "
            "(dashboard_generator) with universal_pick_resolver fallbacks — drift today. "
            "P1 PM/crypto rows: apply vol-aware TP/SL before R:R Smart gates. "
            "P2 closed-book TP vs SL rates by vol tier/strategy. See docs MD."
        ),
        "doc_path_repo_relative": DOC,
        "related_artifacts": [
            "audit_trail/dashboard_generator.py",
            "audit_trail/universal_pick_resolver.py",
            "audit_trail/quality_gates.py",
            "audit_trail/kimi_crypto_liquidity.py",
            "tools/audit_smart_gate_funnel.py",
        ],
        "action_required": (
            "Read docs/AUDIT_CRYPTO_PREDICTION_TP_SL_QUALITY_2026-04-02.md; implement shared TP/SL module; "
            "then re-run funnel + score_pnl analyzers and broadcast follow-up if shipped."
        ),
    }
    body = json.dumps(envelope, separators=(",", ":"))
    _, code = run_redis_cmd(["PUBLISH", "alpha_engine_bus", body])
    short = "AUDIT_CRYPTO_PREDICTION_TP_SL_QUALITY | %s" % ts
    run_redis_cmd(["LPUSH", "bus:broadcast:log", short])
    run_redis_cmd(["LTRIM", "bus:broadcast:log", "0", "99"])
    print("[OK]" if code == 0 else "[WARN]", short)
    if code != 0:
        print(
            "redis-cli failed (Redis down or path wrong). Envelope for manual PUBLISH:\n",
            body,
            file=__import__("sys").stderr,
        )
    return 0 if code == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
