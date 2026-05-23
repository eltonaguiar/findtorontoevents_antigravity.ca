#!/usr/bin/env python3
"""Ask Claude to place paper picks on TradingView only (Redis inbox + broadcast)."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import redis
except ImportError:
    print("pip install redis", file=sys.stderr)
    raise SystemExit(2)

FROM_ID = "cursor-sports-coord"
# Primary inbox; broadcast reaches any Claude session tailing log
TO_IDS = (
    "claude-sports-db-fix",
    "claude-paper-tv",
    "claude-dash-fix",
)

BODY = """TV-PAPER-PICKS (user scope: TradingView paper portfolios ONLY — not repo SQLite/JSON unless mirroring for audit).

Please add/size trades on TradingView paper accounts (e.g. SCALPER, TESTER, TRUSTOURSCORE, BROKIE, zerounderscore — see docs/PORTFOLIO_DECISIONS_20260404.md for sizing norms).

Context:
- Coordination levels: alpha_engine/data/joint_paper_portfolio_picks_2026-04-04.json + docs/JOINT_ASSET_CLASS_PAPER_COORDINATION_2026-04-04.md
- Copytrader: prefer multi_asset_copytrader / non-crypto edge narrative; treat copy_trader_intel headline PnL as suspect until phantom entry/exit rows are scrubbed (dashboard excludes >100x entry/exit in metrics)
- Use limit/stop where session closed; crypto perps can use limit at referenced entry

Reply RE: TV-PAPER or confirm fills on bus. Cursor is not placing TV orders."""


def main() -> int:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    root = Path(__file__).resolve().parents[1]
    msg = json.dumps(
        {"from": FROM_ID, "timestamp": now, "body": BODY.strip(), "execution_venue": "tradingview_paper"},
        ensure_ascii=False,
    )
    b = msg.encode("utf-8")
    r = redis.Redis(host="localhost", port=6379, decode_responses=False)
    r.ping()
    for to_id in TO_IDS:
        key = f"agent:{to_id}:inbox"
        r.lpush(key, b)
        r.ltrim(key, 0, 49)
        print("LPUSH", key)
    broad = json.dumps(
        {"from": FROM_ID, "timestamp": now, "body": "[TV-PAPER] " + BODY.strip()},
        ensure_ascii=False,
    ).encode("utf-8")
    r.lpush("bus:broadcast:log", broad)
    r.ltrim("bus:broadcast:log", 0, 99)
    print("bus:broadcast:log [TV-PAPER]")
    r.hset(
        f"agent:{FROM_ID}:status",
        mapping={
            "summary": "Delegated paper picks to Claude — TradingView only",
            "cwd": str(root).replace("\\", "/"),
            "last_seen": now,
            "tool": "cursor",
        },
    )
    r.expire(f"agent:{FROM_ID}:status", 3600)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
