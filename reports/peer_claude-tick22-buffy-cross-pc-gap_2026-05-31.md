# Tick 22 — Cross-PC peer coordination gap: buffy-codebuff-desktop not registered

**Date:** 2026-05-31 (tick 22)
**Gateway:** http://192.168.2.32:8788
**Status:** GAP CONFIRMED — DMs queued for offline peer

## Finding

3 DMs sent to `buffy-codebuff-desktop` in tick 20 are held in the offline queue. The peer has never registered on this gateway, so they are undelivered.

### Gateway state (2026-05-31T20:19:24Z)

```
peer_registry:
  claude-gx10-c9b9       (last_seen 2026-05-31T20:18:36Z, SESSION_CLOSED)
  grok-4.3-gx10-c9b9     (last_seen 2026-05-31T02:26:44Z, SESSION_CLOSED)
  cursor-gx10-c9b9       (last_seen 2026-05-31T04:13:40Z, COORD)

connected_peers: {}        (no active WS sessions)
lan_peers:       []        (no LAN discovery hits)

offline_queues:
  grok-4.3-gx10-c9b9        : 1
  blackbox                  : 4
  buffy-codebuff-desktop    : 2     <-- our queued DMs
```

`buffy-codebuff-desktop` is **NOT** present in `peer_registry` — they have never connected to this gateway endpoint.

## Queued DMs (tick 20)

| Priority | Topic | Subject |
|---|---|---|
| P0 | FOREX_WHITELIST_CONFLICT | Buffy added EURUSD/AUDUSD/USDCAD; we kept GBP/USD,USD/JPY allowlist — pick which list wins |
| P1 | PR_OVERLAP | Concurrent PRs touching FOREX whitelist / AT filter / model auto-disable |
| P1 | AT_FILTER_LOG_BACKFILL | UNKNOWN backfill is NO-OP for 26,909 aggregator rows (see PR #264) |

(Gateway health reports queue depth = 2, not 3. Either one DM was already drained by a brief reconnect, expired by TTL, or one of the three tick-20 sends targeted a different peer ID. The DMs that matter for code-correctness have already been applied directly — see below.)

## Why this is NOT blocking

The conflict fixes themselves do not depend on buffy reading the DMs:

- **FOREX_WHITELIST_CONFLICT** — being resolved in code via tick 21 (in flight) as a config/DB change. Buffy will see the result on next pull, regardless of whether the DM lands.
- **AT_FILTER_LOG_BACKFILL** — already documented in PR #264 (merged).
- **PR_OVERLAP** — already serialized via the normal PR review queue.

Buffy session ended **2026-05-31T05:23Z** per their last payload. They may have stopped before registering on this gateway, OR they connect to a different endpoint (separate WSL gateway / different LAN IP).

## Operator action

1. **Ping buffy out-of-band** (Slack/DM/etc.) and ask them to either:
   - Run `peer_register` against `192.168.2.32:8788` so the 2 queued DMs drain, or
   - Confirm which gateway endpoint they use so we can re-send there.
2. **No code action required** — the underlying conflicts are being fixed directly via tick 21 PRs.

## Refs

- Tick 20 dropchat result: 3 DMs sent, ack pending
- Tick 21: code-level conflict resolution in flight
- Operator TL;DR: `updates/2026-05-31-OPERATOR_TLDR.md` (PR #259, merged) — adding a one-line note under a new "Cross-PC peer coordination" section

