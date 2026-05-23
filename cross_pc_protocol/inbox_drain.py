"""Cross-PC inbox auto-drain — fixes the send-only agent bug.

Grok/Hermes agent instances were observed to be *send-only*: they publish
envelopes to the gateway but never poll their own DM queue or the broadcast
queue, so they never receive replies. On 2026-05-15 this caused a multi-hour
coordination failure (an agent re-asked the same question for hours while 9
answers sat unread in its queue).

Every agent must drain its inbox on startup and on each heartbeat. Call
``startup_inbox_check(peer_id)`` once at adapter startup, and ``drain_inbox``
on the heartbeat tick.

Fail-soft by design: a down gateway returns ``[]``, never raises — checking
your inbox must not be able to crash an agent.

## Broadcast drain log

Broadcast queues are destructive — the first peer that polls ``peer_id=all``
consumes the messages. To prevent other peers from silently missing broadcasts,
``drain_inbox`` appends every drained broadcast to a local JSONL file:

    logs/cross_pc_protocol/broadcast_drain.jsonl

Each line records: drainer peer_id, drain timestamp, message_id, from, topic,
payload. Any peer can tail this file to see broadcasts they missed. The file
is append-only and never truncated — it is the shared "what got drained and by
whom" audit trail. Commit + push it to git after long sessions so laptop peers
can sync via ``git pull``.
"""
from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from pathlib import Path

log = logging.getLogger("cross_pc.inbox_drain")

DEFAULT_HTTP_BASE = "http://127.0.0.1:8788"
BROADCAST_DRAIN_LOG = Path("logs/cross_pc_protocol/broadcast_drain.jsonl")


def _poll_queue(peer_id: str, http_base: str, limit: int) -> list[dict]:
    """GET {http_base}/poll?peer_id=<peer_id>&limit=<limit>. Fail-soft -> []."""
    url = f"{http_base.rstrip('/')}/poll?peer_id={peer_id}&limit={int(limit)}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "inbox-drain"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
    except (urllib.error.URLError, OSError, ValueError, TimeoutError) as e:
        log.warning("[inbox] gateway unreachable polling %s: %s", peer_id, e)
        return []
    msgs = data.get("messages") or data.get("envelopes") or []
    return msgs if isinstance(msgs, list) else []


def _log_drained_broadcasts(peer_id: str, broadcasts: list[dict]) -> None:
    """Append drained broadcasts to the shared drain log (fail-soft)."""
    if not broadcasts:
        return
    try:
        BROADCAST_DRAIN_LOG.parent.mkdir(parents=True, exist_ok=True)
        drained_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with BROADCAST_DRAIN_LOG.open("a", encoding="utf-8") as fh:
            for m in broadcasts:
                record = {
                    "drained_by": peer_id,
                    "drained_at": drained_at,
                    "message_id": m.get("message_id"),
                    "from": m.get("from"),
                    "to": m.get("to") or "*",
                    "topic": m.get("topic"),
                    "ts_utc": m.get("ts_utc"),
                    "payload": m.get("payload"),
                }
                fh.write(json.dumps(record, ensure_ascii=True) + "\n")
        log.debug("[inbox] logged %d drained broadcast(s) to %s", len(broadcasts), BROADCAST_DRAIN_LOG)
    except Exception as exc:  # noqa: BLE001 — fail-soft, never crash the agent
        log.warning("[inbox] could not write drain log: %s", exc)


def drain_inbox(
    peer_id: str,
    http_base: str = DEFAULT_HTTP_BASE,
    limit: int = 50,
) -> list[dict]:
    """Drain this peer's DM queue AND the broadcast queue.

    Returns the combined message list — DM messages first, then broadcasts —
    de-duplicated by ``message_id``. Polling is destructive (messages pop off
    the gateway queue); the durable event log keeps a copy.

    Drained broadcasts are also appended to
    ``logs/cross_pc_protocol/broadcast_drain.jsonl`` so other peers that
    missed the broadcast can read what was consumed and by whom.

    Fail-soft: a down/unreachable gateway yields ``[]``, never raises.
    """
    if not peer_id:
        log.warning("[inbox] drain_inbox called with empty peer_id")
        return []
    dms = _poll_queue(peer_id, http_base, limit)
    broadcasts = _poll_queue("all", http_base, limit)

    _log_drained_broadcasts(peer_id, broadcasts)

    out: list[dict] = []
    seen: set = set()
    for m in list(dms) + list(broadcasts):
        if not isinstance(m, dict):
            continue
        mid = m.get("message_id")
        if mid is not None:
            if mid in seen:
                continue
            seen.add(mid)
        out.append(m)
    return out


def startup_inbox_check(
    peer_id: str,
    http_base: str = DEFAULT_HTTP_BASE,
) -> list[dict]:
    """Drain the inbox once at adapter startup; log a one-line summary.

    Returns the drained messages so the caller can act on them. Intended to be
    called exactly once when an agent/adapter session begins — the cure for
    the send-only bug.
    """
    msgs = drain_inbox(peer_id, http_base=http_base)
    log.info("[inbox] %d message(s) for %s on startup", len(msgs), peer_id)
    return msgs
