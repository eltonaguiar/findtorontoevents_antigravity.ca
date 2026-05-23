#!/usr/bin/env python3
"""Publish asset class deep dive to alpha_engine_bus."""

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
        "bus_topic": "asset_class_deep_dive_scoring_flaws",
        "from": "kilo-asset-class-analysis",
        "ts": ts,
        "summary": "ASSET_CLASS_DEEP_DIVE.md — 3223 closed picks analyzed by mode/asset. KEY FINDINGS: (1) SWING mode is the ONLY profitable mode: 38.5% WR +0.874% avg +68.18% total. SCALP mode (81.5% of trades) loses at 27.5% WR. (2) TAOUSDT in SWING: +90.91% PnL. Same symbol in SCALP: -48.53%. Mode assignment is the difference. (3) MATICUSDT: 553 trades 0% WR -83% PnL — should have been auto-killed. (4) Confidence 0.6-0.7 (58% of trades) has 23.3% WR — anti-predictive band. (5) SHORT 47.7% WR vs LONG 29.5% — only 5.5% of trades are SHORT. (6) Tuesday entries: 47.3% WR in SCALP. Wednesday: 20.3% WR. (7) R:R 2.0 default: 28.3% WR. R:R 1.0: 44.3% WR. 10 concrete fixes proposed. See ASSET_CLASS_DEEP_DIVE.md.",
        "doc_path_repo_relative": "ASSET_CLASS_DEEP_DIVE.md",
        "top_5_fixes": [
            "Kill MATICUSDT (0% WR, 553 trades, -83% PnL)",
            "Auto-kill symbols at 50+ trades with <15% WR",
            "Boost SWING mode to 15-20% of picks (+0.874% avg)",
            "Penalize confidence 0.6-0.7 band (0.85x multiplier)",
            "Block weekend SCALP entries (25-27% WR)",
        ],
        "action_required": "Review ASSET_CLASS_DEEP_DIVE.md. Fix 1 (kill MATIC) is TRIVIAL. Fix 3 (boost SWING) is highest expected impact.",
    }
    body = json.dumps(envelope, separators=(",", ":"))
    _, code = run_redis_cmd(["PUBLISH", "alpha_engine_bus", body])
    short = f"asset_class_deep_dive | SWING +68% vs SCALP -426% | MATIC 0% WR 553 trades | {ts}"
    run_redis_cmd(["LPUSH", "bus:broadcast:log", short])
    run_redis_cmd(["LTRIM", "bus:broadcast:log", "0", "99"])
    print("[OK]" if code == 0 else "[WARN]", short)
    return 0 if code == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
