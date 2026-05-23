"""Client library with WebSocket primary and HTTP fallback transport."""
from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, Optional  # noqa: F401 — used in type hints

import requests

from .schema import new_envelope

try:
    import websockets
except Exception:  # pragma: no cover
    websockets = None


class ProtocolClient:
    def __init__(
        self,
        peer_id: str,
        ws_url: str = "ws://127.0.0.1:8787",
        http_base: str = "http://127.0.0.1:8788",
        timeout_sec: int = 10,
    ) -> None:
        self.peer_id = peer_id
        self.ws_url = ws_url
        self.http_base = http_base.rstrip("/")
        self.timeout_sec = timeout_sec
        self._ws = None

    async def connect_ws(self, capabilities: Optional[list[str]] = None) -> bool:
        if websockets is None:
            return False
        try:
            self._ws = await websockets.connect(self.ws_url)
            register_env = new_envelope(
                sender=self.peer_id,
                topic="peer.register",
                payload={"capabilities": capabilities or []},
            )
            await self._ws.send(json.dumps(register_env))
            await self._ws.recv()
            return True
        except Exception:
            self._ws = None
            return False

    async def close_ws(self) -> None:
        if self._ws is not None:
            await self._ws.close()
            self._ws = None

    async def send(
        self,
        topic: str,
        payload: Dict[str, Any],
        to: str = "",
        trace_id: str = "",
        require_ack: bool = False,
        debug: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        envelope = new_envelope(
            sender=self.peer_id,
            topic=topic,
            payload=payload,
            target=to,
            trace_id=trace_id,
            require_ack=require_ack,
            debug=debug or {},
        )
        return await self.send_envelope(envelope)

    async def send_envelope(self, envelope: Dict[str, Any]) -> Dict[str, Any]:
        if self._ws is not None:
            try:
                await self._ws.send(json.dumps(envelope))
                return {"ok": True, "transport": "ws", "message_id": envelope["message_id"]}
            except Exception:
                self._ws = None
        return self.publish_http(envelope)

    def publish_http(self, envelope: Dict[str, Any]) -> Dict[str, Any]:
        response = requests.post(
            f"{self.http_base}/publish",
            json=envelope,
            timeout=self.timeout_sec,
        )
        response.raise_for_status()
        data = response.json()
        data["transport"] = "http"
        return data

    def poll(self, peer_id: Optional[str] = None, limit: int = 50) -> Dict[str, Any]:
        effective_peer = peer_id if peer_id is not None else self.peer_id
        response = requests.get(
            f"{self.http_base}/poll",
            params={"peer_id": effective_peer, "limit": limit},
            timeout=self.timeout_sec,
        )
        response.raise_for_status()
        return response.json()

    async def listen_once(self) -> Optional[Dict[str, Any]]:
        if self._ws is None:
            return None
        raw = await self._ws.recv()
        return json.loads(raw)

    def ack(self, message_id: str) -> Dict[str, Any]:
        response = requests.post(
            f"{self.http_base}/ack",
            json={"message_id": message_id, "from": self.peer_id},
            timeout=self.timeout_sec,
        )
        response.raise_for_status()
        return response.json()
