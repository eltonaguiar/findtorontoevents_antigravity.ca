"""Reliability primitives: idempotency, retries, and offline queues."""
from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any, Deque, Dict, List


class IdempotencyCache:
    def __init__(self, ttl_sec: int = 3600) -> None:
        self.ttl_sec = ttl_sec
        self._seen: Dict[str, float] = {}

    def add(self, message_id: str) -> None:
        self._seen[message_id] = time.time()
        self._evict()

    def has(self, message_id: str) -> bool:
        self._evict()
        return message_id in self._seen

    def _evict(self) -> None:
        cutoff = time.time() - self.ttl_sec
        stale = [k for k, ts in self._seen.items() if ts < cutoff]
        for key in stale:
            self._seen.pop(key, None)


class OfflineQueue:
    def __init__(self, max_per_peer: int = 500) -> None:
        self.max_per_peer = max_per_peer
        self._queues: Dict[str, Deque[Dict[str, Any]]] = defaultdict(
            lambda: deque(maxlen=self.max_per_peer)
        )

    def push(self, peer_id: str, envelope: Dict[str, Any]) -> int:
        msg_id = envelope.get("message_id")
        queue = self._queues[peer_id]
        # Skip if already queued — prevents duplicate copies on retry loop re-routes
        if msg_id and any(r.get("message_id") == msg_id for r in queue):
            return len(queue)
        queue.append(envelope)
        return len(queue)

    def pop_many(self, peer_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        queue = self._queues[peer_id]
        messages: List[Dict[str, Any]] = []
        while queue and len(messages) < limit:
            messages.append(queue.popleft())
        return messages

    def size(self, peer_id: str) -> int:
        return len(self._queues[peer_id])

    def sizes(self) -> Dict[str, int]:
        return {peer_id: len(queue) for peer_id, queue in self._queues.items() if queue}


@dataclass
class PendingAck:
    envelope: Dict[str, Any]
    attempts: int
    max_attempts: int
    next_retry_epoch: float


class RetryTracker:
    def __init__(self, retry_interval_sec: int = 10, max_attempts: int = 3) -> None:
        self.retry_interval_sec = retry_interval_sec
        self.max_attempts = max_attempts
        self._pending: Dict[str, PendingAck] = {}

    def track(self, envelope: Dict[str, Any]) -> None:
        message_id = envelope["message_id"]
        self._pending[message_id] = PendingAck(
            envelope=envelope,
            attempts=1,
            max_attempts=self.max_attempts,
            next_retry_epoch=time.time() + self.retry_interval_sec,
        )

    def ack(self, message_id: str) -> bool:
        return self._pending.pop(message_id, None) is not None

    def due_retries(self) -> List[Dict[str, Any]]:
        now = time.time()
        due: List[Dict[str, Any]] = []
        for message_id, record in list(self._pending.items()):
            if record.next_retry_epoch > now:
                continue
            if record.attempts >= record.max_attempts:
                self._pending.pop(message_id, None)
                continue
            record.attempts += 1
            record.next_retry_epoch = now + self.retry_interval_sec
            envelope = dict(record.envelope)
            envelope["debug"] = dict(envelope.get("debug", {}))
            envelope["debug"]["attempt"] = record.attempts
            due.append(envelope)
        return due

    def pending_count(self) -> int:
        return len(self._pending)
