# Cross-PC Protocol Runbook

This runbook covers startup, health verification, debugging, and failure drills for the debug-first cross-PC protocol.

## Components

- Gateway: `tools/protocol_gateway.py`
- LAN discovery utility: `tools/lan_discovery.py`
- Inspector: `tools/protocol_inspect.py`
- Cursor/Claude adapter: `tools/adapters/cursor_claude_adapter.py`
- Freebuff adapter: `tools/adapters/freebuff_adapter.py`
- Spec: `docs/cross_pc_protocol_v1.md`

## Supported operator environments

- Claude/Cursor on Windows PowerShell
- Claude/Cursor on cmd.exe
- Hermes/Claude in WSL bash
- Freebuff-style CLI workers

All environments use the same gateway and envelope. Only shell quoting differs.

## Startup

1. Start the gateway on PC A:

```bash
python tools/protocol_gateway.py --host 0.0.0.0 --ws-port 8787 --http-port 8788 --peer-id pc-a-gateway
```

2. On any peer PC, point adapters to PC A:

```bash
python tools/adapters/cursor_claude_adapter.py --peer-id cursor-pc-b --ws-url ws://PC_A_IP:8787 --http-base http://PC_A_IP:8788 poll --limit 5
```

3. Optional local discovery monitor:

```bash
python tools/lan_discovery.py --peer-id monitor-a --gateway-port 8787
```

## Shell-safe command examples

- PowerShell:
```powershell
python tools/adapters/cursor_claude_adapter.py --peer-id claude-win send --topic task.request --payload '{"summary":"hello"}' --to freebuff-b --require-ack
```

- cmd.exe:
```cmd
python tools/adapters/cursor_claude_adapter.py --peer-id claude-cmd send --topic task.request --payload "{\"summary\":\"hello\"}" --to freebuff-b --require-ack
```

- WSL/bash (Hermes or Claude):
```bash
python3 tools/adapters/cursor_claude_adapter.py --peer-id hermes-wsl send --topic task.request --payload '{"summary":"hello"}' --to freebuff-b --require-ack
```

## Health Checks

- Gateway health:

```bash
python tools/protocol_inspect.py --http-base http://127.0.0.1:8788 health
```

- Tail recent events:

```bash
python tools/protocol_inspect.py tail --limit 20
```

- Replay a trace:

```bash
python tools/protocol_inspect.py trace --trace-id <trace_id>
```

## Multi-network topologies

### 1) Same LAN

- Gateway host: bind `0.0.0.0`
- Peers: connect to `ws://<LAN_IP>:8787` and `http://<LAN_IP>:8788`
- Discovery: UDP LAN discovery usually works

### 2) Different networks (internet/VPN)

- Preferred: private overlay network (Tailscale/ZeroTier)
- Alternative: SSH tunnel
  - From peer machine:
```bash
ssh -N -L 8787:localhost:8787 -L 8788:localhost:8788 user@gateway-host
```
  - Then peer uses localhost endpoints.
- If using direct port-forwarding, allow inbound firewall rules and TLS/proxy as needed.

### 3) Discovery unavailable

- If UDP broadcast is blocked, configure peer endpoints explicitly.
- Protocol remains functional without discovery.

## Failure Drills

1. **WS outage simulation**  
   Stop WS clients, then send using adapters. Confirm HTTP fallback still publishes.

2. **Offline peer queueing**  
   Send to a peer ID with no active WS session. Verify queue growth in `/health` and drain via `poll`.

3. **ACK timeout/retry**  
   Send message with `--require-ack` but do not ACK. Verify retried events appear in event log.

4. **Duplicate suppression**  
   Re-submit the same `message_id` payload and confirm status `duplicate`.

5. **Redis bridge degraded mode**  
   Stop local Redis and verify gateway still accepts, queues, and logs messages while `redis_bridge_available=false`.

## Troubleshooting

- If a peer appears in LAN discovery but receives no messages:
  - Verify gateway `/health` includes peer in `connected_peers`.
  - Check if messages are in `offline_queues` for that peer.
  - Use `trace` to confirm envelope `to` and `topic`.

- If messages are dropped:
  - Ensure envelope validates against `cross-pc/v1`.
  - Check event log status `rejected` and note field for validation error.

- If retries never stop:
  - Ensure receiver sends `ack` topic or calls `/ack`.
  - Confirm `payload.message_id` references the original message.
- If LAN works but remote peer does not:
  - Verify remote URL reachability (`curl <http_base>/health`).
  - Verify NAT/firewall and port-forwarding.
  - Prefer VPN overlay endpoints for stable routing.

## Compatibility Matrix

| Client type | WS | HTTP fallback | ACK | Poll queue | Notes |
|---|---|---|---|---|---|
| Cursor adapter | Yes | Yes | Yes | Yes | `tools/adapters/cursor_claude_adapter.py` |
| Claude peer adapter | Yes | Yes | Yes | Yes | same adapter, different `peer_id` |
| Freebuff adapter | Yes | Yes | Yes | Yes | `tools/adapters/freebuff_adapter.py` |
| Legacy Redis consumers | Bridge only | N/A | N/A | N/A | receives mirrored envelopes on `alpha_engine_bus` |
