"""Protocol gateway with WebSocket primary transport and HTTP fallback."""
from __future__ import annotations

import argparse
import asyncio
import json
import threading
import urllib.parse
from dataclasses import dataclass
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional

from .lan_discovery import LanDiscovery
from .redis_bridge import RedisBridge
from .reliability import IdempotencyCache, OfflineQueue, RetryTracker
from .schema import ProtocolValidationError, normalize_envelope
from .storage import EventStore

try:
    import websockets
except Exception:  # pragma: no cover
    websockets = None


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class PeerSession:
    peer_id: str
    ws: Any
    connected_ts_utc: str
    last_seen_ts_utc: str


class ProtocolGateway:
    def __init__(
        self,
        host: str = "0.0.0.0",
        ws_port: int = 8787,
        http_port: int = 8788,
        event_log_path: str = "logs/cross_pc_protocol/events.jsonl",
        peer_id: str = "gateway",
        discovery_port: int = 47655,
    ) -> None:
        self.host = host
        self.ws_port = ws_port
        self.http_port = http_port
        self.peer_id = peer_id

        self.event_store = EventStore(Path(event_log_path))
        self.idempotency = IdempotencyCache(ttl_sec=3600)
        self.offline_queue = OfflineQueue(max_per_peer=500)
        self.retry_tracker = RetryTracker(retry_interval_sec=10, max_attempts=3)
        self.redis_bridge = RedisBridge()
        self.discovery = LanDiscovery(
            peer_id=f"{self.peer_id}-{self.ws_port}",
            gateway_port=self.ws_port,
            discovery_port=discovery_port,
        )

        self._sessions: Dict[str, PeerSession] = {}
        self._sessions_lock = threading.Lock()
        self._peer_registry: Dict[str, Dict[str, Any]] = {}
        self._peer_registry_lock = threading.Lock()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._stop = asyncio.Event()
        self._http_server: Optional[ThreadingHTTPServer] = None
        self._ws_server = None

    async def run(self) -> None:
        if websockets is None:
            raise RuntimeError("websockets package is required for ProtocolGateway.")
        self.discovery.start()
        self._loop = asyncio.get_running_loop()
        self._http_server = self._start_http_server()
        self._ws_server = await websockets.serve(self._ws_handler, self.host, self.ws_port)
        retry_task = asyncio.create_task(self._retry_loop())
        try:
            await self._stop.wait()
        finally:
            retry_task.cancel()
            self.discovery.stop()
            if self._http_server is not None:
                self._http_server.shutdown()
                self._http_server.server_close()
            self._ws_server.close()
            await self._ws_server.wait_closed()

    async def stop(self) -> None:
        self._stop.set()

    async def process_inbound(
        self, raw_envelope: Dict[str, Any], transport: str = "unknown"
    ) -> Dict[str, Any]:
        try:
            envelope = normalize_envelope(raw_envelope)
        except ProtocolValidationError as exc:
            self._log_event(raw_envelope, transport, status="rejected", note=str(exc))
            return {"ok": False, "status": "rejected", "error": str(exc)}

        message_id = envelope["message_id"]
        if self.idempotency.has(message_id):
            self._log_event(envelope, transport, status="duplicate", note="idempotent drop")
            return {"ok": True, "status": "duplicate", "message_id": message_id}

        self.idempotency.add(message_id)
        self._update_peer_registry(envelope, transport=transport)
        self._log_event(envelope, transport, status="accepted")
        if envelope.get("topic") == "ack":
            ack_target = str((envelope.get("payload") or {}).get("message_id") or "").strip()
            if ack_target:
                ack_result = await self.register_ack(ack_target, from_peer=envelope.get("from", ""))
                return {"ok": True, "status": "ack_processed", "message_id": ack_target, "ack": ack_result}
        await self._route_envelope(envelope, transport=transport)
        if envelope.get("require_ack"):
            self.retry_tracker.track(envelope)
        return {"ok": True, "status": "accepted", "message_id": message_id}

    async def register_ack(self, message_id: str, from_peer: str = "") -> Dict[str, Any]:
        ok = self.retry_tracker.ack(message_id)
        ack_envelope = {
            "schema_version": "cross-pc/v1",
            "message_id": f"ack-{message_id}",
            "trace_id": message_id,
            "causation_id": message_id,
            "from": from_peer or "unknown",
            "to": "",
            "topic": "ack",
            "ts_utc": _utc_now_iso(),
            "require_ack": False,
            "ttl_sec": 60,
            "payload": {"message_id": message_id, "accepted": ok},
            "debug": {"transport": "ack"},
        }
        self._log_event(ack_envelope, "http", status="acked" if ok else "ack_miss")
        return {"ok": ok, "message_id": message_id}

    def poll(self, peer_id: str, limit: int = 50) -> Dict[str, Any]:
        messages = self.offline_queue.pop_many(peer_id, limit=limit)
        for message in messages:
            self._log_event(message, "poll", status="dequeued")
        return {"ok": True, "peer_id": peer_id, "messages": messages}

    def replay_trace(self, trace_id: str, limit: int = 500) -> Dict[str, Any]:
        return {"ok": True, "trace_id": trace_id, "events": self.event_store.by_trace_id(trace_id, limit)}

    def health(self) -> Dict[str, Any]:
        with self._sessions_lock:
            peers = {
                peer_id: {
                    "connected_ts_utc": sess.connected_ts_utc,
                    "last_seen_ts_utc": sess.last_seen_ts_utc,
                }
                for peer_id, sess in self._sessions.items()
            }
        return {
            "ok": True,
            "ts_utc": _utc_now_iso(),
            "ws_port": self.ws_port,
            "http_port": self.http_port,
            "connected_peers": peers,
            "peer_registry": self._peer_registry_snapshot(),
            "offline_queues": self.offline_queue.sizes(),
            "pending_acks": self.retry_tracker.pending_count(),
            "redis_bridge_available": self.redis_bridge.is_available(),
            "lan_peers": self.discovery.peers(),
        }

    def _peer_registry_snapshot(self) -> Dict[str, Dict[str, Any]]:
        with self._peer_registry_lock:
            return dict(self._peer_registry)

    def _update_peer_registry(self, envelope: Dict[str, Any], transport: str) -> None:
        sender = str(envelope.get("from") or "").strip()
        if not sender:
            return
        payload = envelope.get("payload", {})
        capabilities = []
        if isinstance(payload, dict):
            caps = payload.get("capabilities")
            if isinstance(caps, list):
                capabilities = [str(item) for item in caps]
        with self._peer_registry_lock:
            is_new_peer = sender not in self._peer_registry
            existing = dict(self._peer_registry.get(sender, {}))
            existing.update(
                {
                    "peer_id": sender,
                    "last_seen_ts_utc": _utc_now_iso(),
                    "last_transport": transport,
                    "last_topic": envelope.get("topic"),
                }
            )
            if capabilities:
                existing["capabilities"] = capabilities
            self._peer_registry[sender] = existing

        # Backfill: new peer joining after a broadcast was already sent.
        # Replay recent broadcasts from the event log into their individual queue
        # so they don't miss messages just because they registered late.
        if is_new_peer:
            try:
                missed = self.event_store.recent_broadcasts(since_sec=3600, limit=100)
                backfilled = 0
                for bc_env in missed:
                    bc_sender = str(bc_env.get("from") or "").strip()
                    if bc_sender == sender:
                        continue  # don't backfill their own messages
                    bc_mid = bc_env.get("message_id")
                    if bc_mid:
                        self.offline_queue.push(sender, bc_env)
                        backfilled += 1
                if backfilled:
                    self._log_event(
                        {"from": "gateway", "to": sender, "topic": "backfill",
                         "payload": {"count": backfilled}, "message_id": f"backfill-{sender}",
                         "trace_id": "", "causation_id": "", "ts_utc": _utc_now_iso(),
                         "require_ack": False, "ttl_sec": 0},
                        "internal",
                        status="backfilled",
                        note=f"replayed {backfilled} broadcasts to new peer {sender}",
                    )
            except Exception as exc:  # noqa: BLE001 — never crash registration
                import logging
                logging.getLogger(__name__).warning("backfill failed for %s: %s", sender, exc)

    async def _retry_loop(self) -> None:
        while not self._stop.is_set():
            due = self.retry_tracker.due_retries()
            for envelope in due:
                await self._route_envelope(envelope, transport="retry")
                self._log_event(envelope, "retry", status="retried")
            await asyncio.sleep(1)

    async def _route_envelope(self, envelope: Dict[str, Any], transport: str) -> None:
        target = envelope.get("to", "").strip()
        sender = str(envelope.get("from") or "").strip()
        routed = False
        if target:
            session = self._get_session(target)
            if session:
                await session.ws.send(json.dumps(envelope))
                routed = True
                with self._sessions_lock:
                    if target in self._sessions:
                        self._sessions[target].last_seen_ts_utc = _utc_now_iso()
                self._log_event(envelope, transport, status="routed")
            else:
                size = self.offline_queue.push(target, envelope)
                self._log_event(envelope, transport, status="queued", note=f"queue_size={size}")
        else:
            # Broadcast: push to live WS sessions AND fan-out to each registered
            # peer's individual offline queue so HTTP/polling peers each get their
            # own copy. First-poller-wins race is eliminated — draining your own
            # queue never consumes the copy in another peer's queue.
            # Also push to the legacy "all" queue for backwards compat.
            live_peers: set[str] = set()
            ws_peers = self._all_sessions()
            for peer_id, session in ws_peers.items():
                if peer_id == sender:
                    continue
                await session.ws.send(json.dumps(envelope))
                routed = True
                live_peers.add(peer_id)

            # Fan-out to offline queues for all registered peers (HTTP pollers)
            with self._peer_registry_lock:
                registered_peers = list(self._peer_registry.keys())
            for peer_id in registered_peers:
                if peer_id == sender or peer_id in live_peers:
                    continue  # skip sender and peers already reached via WS
                self.offline_queue.push(peer_id, envelope)
                routed = True

            # Legacy "all" queue — kept so old poll?peer_id=all clients still work
            self.offline_queue.push("all", envelope)
            self._log_event(envelope, transport, status="broadcasted" if routed else "accepted")

        self.redis_bridge.publish(envelope)

    async def _ws_handler(self, websocket: Any) -> None:
        peer_id = ""
        try:
            try:
                async for raw in websocket:
                    try:
                        payload = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    if payload.get("topic") == "peer.register":
                        peer_id = str(payload.get("from") or "").strip()
                        if not peer_id:
                            continue
                        with self._sessions_lock:
                            self._sessions[peer_id] = PeerSession(
                                peer_id=peer_id,
                                ws=websocket,
                                connected_ts_utc=_utc_now_iso(),
                                last_seen_ts_utc=_utc_now_iso(),
                            )
                        await websocket.send(
                            json.dumps(
                                {
                                    "ok": True,
                                    "status": "registered",
                                    "peer_id": peer_id,
                                    "ts_utc": _utc_now_iso(),
                                }
                            )
                        )
                        continue
                    await self.process_inbound(payload, transport="ws")
            except Exception:
                # Client sockets can disappear mid-frame; treat disconnects as non-fatal.
                pass
        finally:
            if peer_id:
                with self._sessions_lock:
                    self._sessions.pop(peer_id, None)

    def _log_event(
        self,
        envelope: Dict[str, Any],
        transport: str,
        status: str,
        note: str = "",
    ) -> None:
        event = {
            "gateway_ts_utc": _utc_now_iso(),
            "direction": "inbound" if status in {"accepted", "duplicate", "rejected"} else "internal",
            "transport": transport,
            "status": status,
            "note": note,
            "envelope": envelope,
        }
        self.event_store.append(event)

    def _get_session(self, peer_id: str) -> Optional[PeerSession]:
        with self._sessions_lock:
            return self._sessions.get(peer_id)

    def _all_sessions(self) -> Dict[str, PeerSession]:
        with self._sessions_lock:
            return dict(self._sessions)

    def _start_http_server(self) -> ThreadingHTTPServer:
        gateway = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                parsed = urllib.parse.urlparse(self.path)
                query = urllib.parse.parse_qs(parsed.query)
                if parsed.path == "/health":
                    self._json(HTTPStatus.OK, gateway.health())
                    return
                if parsed.path == "/poll":
                    peer_id = (query.get("peer_id", [""])[0] or "").strip()
                    limit = int((query.get("limit", ["50"])[0] or "50"))
                    if not peer_id:
                        self._json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "peer_id is required"})
                        return
                    self._json(HTTPStatus.OK, gateway.poll(peer_id, limit=limit))
                    return
                if parsed.path == "/replay":
                    trace_id = (query.get("trace_id", [""])[0] or "").strip()
                    limit = int((query.get("limit", ["500"])[0] or "500"))
                    if not trace_id:
                        self._json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "trace_id is required"})
                        return
                    self._json(HTTPStatus.OK, gateway.replay_trace(trace_id, limit=limit))
                    return
                if parsed.path == "/replay_message":
                    message_id = (query.get("message_id", [""])[0] or "").strip()
                    if not message_id:
                        self._json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "message_id is required"})
                        return
                    self._json(
                        HTTPStatus.OK,
                        {"ok": True, "message_id": message_id, "events": gateway.event_store.by_message_id(message_id)},
                    )
                    return
                self._json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not_found"})

            def do_POST(self) -> None:  # noqa: N802
                parsed = urllib.parse.urlparse(self.path)
                payload = self._read_json()
                if payload is None:
                    self._json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "invalid_json"})
                    return
                if parsed.path == "/publish":
                    fut = asyncio.run_coroutine_threadsafe(
                        gateway.process_inbound(payload, transport="http"), gateway._loop
                    )
                    self._json(HTTPStatus.OK, fut.result(timeout=30))
                    return
                if parsed.path == "/ack":
                    message_id = str(payload.get("message_id") or "").strip()
                    from_peer = str(payload.get("from") or "").strip()
                    if not message_id:
                        self._json(
                            HTTPStatus.BAD_REQUEST,
                            {"ok": False, "error": "message_id is required"},
                        )
                        return
                    fut = asyncio.run_coroutine_threadsafe(
                        gateway.register_ack(message_id, from_peer=from_peer), gateway._loop
                    )
                    self._json(HTTPStatus.OK, fut.result(timeout=30))
                    return
                self._json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not_found"})

            def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
                return

            def _read_json(self) -> Optional[Dict[str, Any]]:
                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length) if length > 0 else b"{}"
                try:
                    data = json.loads(raw.decode("utf-8", errors="replace"))
                except json.JSONDecodeError:
                    return None
                if not isinstance(data, dict):
                    return None
                return data

            def _json(self, status: HTTPStatus, payload: Dict[str, Any]) -> None:
                body = json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
                self.send_response(int(status))
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        server = ThreadingHTTPServer((self.host, self.http_port), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        return server


def main() -> int:
    parser = argparse.ArgumentParser(description="Run cross-PC protocol gateway")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--ws-port", type=int, default=8787)
    parser.add_argument("--http-port", type=int, default=8788)
    parser.add_argument("--peer-id", default="gateway")
    parser.add_argument("--event-log", default="logs/cross_pc_protocol/events.jsonl")
    parser.add_argument("--discovery-port", type=int, default=47655)
    args = parser.parse_args()

    gateway = ProtocolGateway(
        host=args.host,
        ws_port=args.ws_port,
        http_port=args.http_port,
        peer_id=args.peer_id,
        event_log_path=args.event_log,
        discovery_port=args.discovery_port,
    )
    try:
        asyncio.run(gateway.run())
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
