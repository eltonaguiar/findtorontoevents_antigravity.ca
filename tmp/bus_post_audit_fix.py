#!/usr/bin/env python3
"""Post to Redis bus: audit dashboard active picks fixed."""

import json, redis, sys

msg = {
    "from": "cursor-audit-quant",
    "timestamp": "2026-04-05T13:35:00Z",
    "body": "AUDIT FIX: Active picks now showing 35 (was 26). Root cause: index.html had _showAllPicks=false while template.html had _showAllPicks=true. Commit 9c585580cb synced them. Live site /audit/ verified fixed.",
}

r = redis.Redis(host="localhost", port=6379, decode_responses=False)
r.publish("alpha_engine_bus", json.dumps(msg))
print("Broadcast: AUDIT FIX - active picks restored to 35")
