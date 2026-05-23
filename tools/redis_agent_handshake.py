"""Redis agent bus: set status, list peers, drain inbox, show broadcasts, post online ping."""
import json
import sys
from datetime import datetime, timezone

import redis

AID = "cursor-audit-quant"


def main() -> int:
    r = redis.Redis(host="localhost", port=6379, decode_responses=True)
    r.ping()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    r.hset(
        f"agent:{AID}:status",
        mapping={
            "summary": (
                "Audit dashboard quant: NC server/UI bucket parity, drill-down PnL "
                "alignment, Playwright DASHBOARD_DATA audit, market spot-checks, VA "
                "traceability; PEER_WORK_AUDIT_DASHBOARD_QUANT.md"
            ),
            "cwd": "E:/findtorontoevents_antigravity.ca",
            "last_seen": now,
            "tool": "cursor",
        },
    )
    r.expire(f"agent:{AID}:status", 3600)

    keys = sorted(r.keys("agent:*:status"))
    print("=== PEERS (agent:*:status) ===")
    for k in keys:
        print(k, json.dumps(r.hgetall(k), indent=2))

    inbox_key = f"agent:{AID}:inbox"
    inbox = r.lrange(inbox_key, 0, -1)
    print("\n=== INBOX (read + clear) ===")
    for m in inbox:
        print(m)
    r.ltrim(inbox_key, 1, 0)

    print("\n=== bus:broadcast:log [0..9] ===")
    for m in r.lrange("bus:broadcast:log", 0, 9):
        print(m)

    msg = json.dumps(
        {
            "from": AID,
            "timestamp": now,
            "body": (
                "Online — audit/quant workstream; will use SET lock:file:<path> before "
                "editing dashboard_generator.py / audit_dashboard/template.html; "
                "detail in PEER_WORK_AUDIT_DASHBOARD_QUANT.md"
            ),
        }
    )
    r.lpush("bus:broadcast:log", msg)
    r.ltrim("bus:broadcast:log", 0, 99)
    print("\n=== Posted broadcast; latest ===")
    print(r.lrange("bus:broadcast:log", 0, 0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
