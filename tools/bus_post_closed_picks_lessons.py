#!/usr/bin/env python3
"""Publish closed picks lessons to alpha_engine_bus."""

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
        "bus_topic": "closed_picks_lessons_scoring_tweaks",
        "from": "kilo-closed-picks-analysis",
        "ts": ts,
        "summary": "CLOSED_PICKS_LESSONS.md — 3223 closed picks analyzed with academic research validation. KEY FINDINGS: (1) TUESDAY is best entry day: 50.6% WR +0.427% avg (vs Wed worst 24.5% WR). Confirmed by Caporale & Plastun 2019 crypto day-of-week research. (2) R:R 2.0 (system default) has WORST performance: 28.3% WR. HIGH confidence + LOW R:R (1.0) = 81.2% WR. (3) Asia/Pre-Asia sessions best (35-36% WR), London worst (23.8% WR, 54.7% SL rate). (4) ML models work on FET/RENDER/BNB (75-84% WR) but fail on BTC/SOL/TRX. (5) 11-20 bar holds = +1.124% avg (best), 50+ bars = -0.876% (worst). (6) Inverting low-confidence losers would recover +138% PnL. 7 scoring tweaks proposed. Academic validation: Kumari et al 2025 confirms weekend momentum effect in crypto. Published to CLOSED_PICKS_LESSONS.md.",
        "doc_path_repo_relative": "CLOSED_PICKS_LESSONS.md",
        "academic_sources": [
            "Kumari, Wasan & Chhimwal (2025) - Weekend Effect in Crypto Momentum - ACR Journal",
            "Caporale & Plastun (2019) - Day of Week Effect in Crypto - Finance Research Letters",
            "Baur et al (2019) - Bitcoin time-of-day effects - Finance Research Letters",
        ],
        "7_scoring_tweaks": [
            "R:R rework: tight 1.0 for high-conf (81.2% WR), wide 3.0 for rest",
            "Tuesday boost +1.30x / Wednesday penalty 0.70x",
            "ML symbol whitelist: FET/RENDER/BNB/DOGE only",
            "Session filter: avoid London 08-13 UTC, prefer Asia 00-08 UTC",
            "Hold window cap at 20 bars (never 50+)",
            "Inverse signal for confidence <0.5 + ml_composite <0.3",
            "Double concentration risk penalty",
        ],
        "action_required": "Review CLOSED_PICKS_LESSONS.md. Tweak 1 (R:R rework) and Tweak 3 (ML whitelist) are lowest effort with highest expected impact.",
    }
    body = json.dumps(envelope, separators=(",", ":"))
    _, code = run_redis_cmd(["PUBLISH", "alpha_engine_bus", body])
    short = f"closed_picks_lessons | Tue 50.6%WR | R:R 1.0 = 81.2%WR | 7 tweaks | {ts}"
    run_redis_cmd(["LPUSH", "bus:broadcast:log", short])
    run_redis_cmd(["LTRIM", "bus:broadcast:log", "0", "99"])
    print("[OK]" if code == 0 else "[WARN]", short)
    return 0 if code == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
