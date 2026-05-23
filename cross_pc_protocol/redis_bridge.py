"""Redis compatibility bridge for legacy channels and logs."""
from __future__ import annotations

import json
from typing import Any, Dict

try:
    import redis
except Exception:  # pragma: no cover - optional at runtime
    redis = None


class RedisBridge:
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        channel: str = "alpha_engine_bus",
        list_key: str = "bus:alpha_engine_bus:log",
        broadcast_key: str = "bus:broadcast:log",
        max_log_entries: int = 200,
    ) -> None:
        self.channel = channel
        self.list_key = list_key
        self.broadcast_key = broadcast_key
        self.max_log_entries = max_log_entries
        self.client = None

        if redis is not None:
            try:
                self.client = redis.Redis(host=host, port=port, decode_responses=True)
                self.client.ping()
            except Exception:
                self.client = None

    def is_available(self) -> bool:
        return self.client is not None

    def publish(self, envelope: Dict[str, Any]) -> None:
        if not self.client:
            return
        payload = json.dumps(envelope, separators=(",", ":"), ensure_ascii=True)
        self.client.publish(self.channel, payload)
        self.client.lpush(self.list_key, payload)
        self.client.ltrim(self.list_key, 0, self.max_log_entries - 1)

        target = str(envelope.get("to") or "").strip()
        if target:
            self.client.lpush(f"agent:{target}:inbox", payload)

        body = str((envelope.get("payload") or {}).get("summary") or envelope.get("topic"))
        broadcast_item = {
            "from": envelope.get("from"),
            "timestamp": envelope.get("ts_utc"),
            "body": body,
        }
        self.client.lpush(self.broadcast_key, json.dumps(broadcast_item))
        self.client.ltrim(self.broadcast_key, 0, 99)
