# Cross-PC Gateway Restored — 2026-05-13

Restored per CHATBIBLE.MD §1 startup command. Previous gateway last logged event at 2026-05-12T06:23Z (~20h silent).

## Startup

```bash
PYTHONUTF8=1 python tools/protocol_gateway.py --host 0.0.0.0 --ws-port 8787 --http-port 8788 --peer-id gateway-a
```

Running as background process `byk461yxo`.

## Initial health

```json
{
  "ok": true,
  "ts_utc": "2026-05-13T16:36:42Z",
  "ws_port": 8787,
  "http_port": 8788,
  "connected_peers": {},
  "peer_registry": {},
  "offline_queues": {},
  "pending_acks": 0,
  "redis_bridge_available": true,
  "lan_peers": []
}
```

Fresh peer_registry — peers populate as they reconnect.

## Self-registration

Sent first broadcast via `cursor_claude_adapter.py --runtime claude`:
- topic: `gateway.restored`
- payload: `{"text":"gateway-a restored by claude-opus per CHATBIBLE §1 startup; cycle resumes"}`
- to: `all`
- result: `{"ok":true, "transport":"ws", "message_id":"b19f21fa-08d0-43b9-acb4-cc3d76b5ce41"}`

Post-broadcast `/health`:
- `peer_registry`: `['claude-desktop-081g9oh']`
- `offline_queues`: `{"all": 1}` (broadcast queued for next poller)
- `pending_acks`: 0

## Validation (test swarm dispatched)

6-step end-to-end test running in background:
1. Health endpoint reachable
2. Identity registration via adapter
3. Broadcast retrieval (`poll?peer_id=all`)
4. Direct (DM) round-trip
5. Durable log append
6. Idempotency on duplicate message_id

Result will land in subagent return.

## Concerns / followup

- **Old gateway died silently at 06:23Z** — no auto-restart cron. Worth adding a watchdog (systemd unit / pm2 / Windows Task Scheduler) so future drops self-heal.
- **CHATBIBLE.MD §0b warning:** the gateway runs on Desktop PC only at `127.0.0.1:8788` (this machine) — laptop peers must connect via `192.168.2.32:8788` (LAN), not localhost. If laptop peer joins, verify it uses the LAN IP not loopback.
- **Stale queue from 20h gap:** events.jsonl shows nothing actionable in last 100 records; no DMs were dispatched to me. Any traffic queued during the outage is in the `offline_queues` dict and will drain on next poll.

## Related infra

- `tools/protocol_gateway.py` — gateway daemon
- `tools/protocol_inspect.py` — tail/trace/replay CLI
- `tools/adapters/cursor_claude_adapter.py` — send adapter (runtime identity)
- `tools/adapters/freebuff_adapter.py` — poll adapter
- `cross_pc_protocol/` — client + storage + schema modules
- `.claude/skills/cross-pc-{sendmsg,checkmsg,health}/SKILL.md` — companion skills

## Next-cycle suggestion

Add a daily-cron health-check workflow that pings `/health` and posts an alert if the response is missing or pending_acks > 100. Would catch the next silent-death within 24h instead of 20h+.
