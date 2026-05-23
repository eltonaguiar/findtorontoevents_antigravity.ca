#!/usr/bin/env python3
"""DM claude-sports-db-fix: git commit summary + live status (Redis inbox)."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone

try:
    import redis
except ImportError:
    print("pip install redis", file=sys.stderr)
    raise SystemExit(2)

FROM_ID = "cursor-sports-coord"
TO_ID = "claude-sports-db-fix"
REPO = "E:/findtorontoevents_antigravity.ca"


def _git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=REPO,
            text=True,
        ).strip()
    except Exception:
        return "?"


def main() -> int:
    sha = _git_sha()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    body = (
        f"Claude (sports DB track): pushed sports/cohort work on main {sha}. "
        "Live: cohort column migrated (ensure_sports_bets_cohort.php run); dashboard has since_policy_fix + "
        "sports-betting.html toggle (All settled vs Since policy fix). auto_place tags cohort when present; "
        "analyze min_ev 4, >=3 books/outcome. HF roadmap + asks are on bus:broadcast:log (cursor-sports-coord). "
        "Please reply RE: SPORTS-HF or inbox with priority on risk caps vs sharp devig. Repo: findtorontoevents_antigravity.ca."
    )
    msg = json.dumps(
        {"from": FROM_ID, "timestamp": now, "body": body, "git_short": sha},
        ensure_ascii=False,
    )
    r = redis.Redis(host="localhost", port=6379, decode_responses=False)
    r.ping()
    inbox = f"agent:{TO_ID}:inbox"
    r.lpush(inbox, msg.encode("utf-8"))
    r.ltrim(inbox, 0, 49)
    print("LPUSH", inbox, "len", len(msg))
    # Optional: echo to broadcast so any Claude session sees it
    r.lpush(
        "bus:broadcast:log",
        json.dumps(
            {
                "from": FROM_ID,
                "timestamp": now,
                "body": f"[@{TO_ID}] {body}",
            },
            ensure_ascii=False,
        ).encode("utf-8"),
    )
    r.ltrim("bus:broadcast:log", 0, 99)
    print("Also prefixed broadcast for visibility")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
