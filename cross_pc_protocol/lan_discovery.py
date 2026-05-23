"""LAN discovery via UDP broadcast for peer discovery."""
from __future__ import annotations

import json
import socket
import threading
import time
from typing import Dict, List

DISCOVERY_MAGIC = "cross-pc-discovery-v1"


class LanDiscovery:
    def __init__(
        self,
        peer_id: str,
        gateway_port: int,
        discovery_port: int = 47655,
        broadcast_ip: str = "255.255.255.255",
        interval_sec: int = 3,
        ttl_sec: int = 15,
    ) -> None:
        self.peer_id = peer_id
        self.gateway_port = gateway_port
        self.discovery_port = discovery_port
        self.broadcast_ip = broadcast_ip
        self.interval_sec = interval_sec
        self.ttl_sec = ttl_sec

        self._stop = threading.Event()
        self._announce_thread: threading.Thread | None = None
        self._listen_thread: threading.Thread | None = None
        self._peers: Dict[str, Dict[str, object]] = {}
        self._lock = threading.Lock()

    def start(self) -> None:
        if self._announce_thread and self._announce_thread.is_alive():
            return
        self._stop.clear()
        self._announce_thread = threading.Thread(target=self._announce_loop, daemon=True)
        self._listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._announce_thread.start()
        self._listen_thread.start()

    def stop(self) -> None:
        self._stop.set()

    def peers(self) -> List[Dict[str, object]]:
        now = time.time()
        with self._lock:
            stale = [
                peer_id
                for peer_id, entry in self._peers.items()
                if now - float(entry.get("last_seen_epoch", 0)) > self.ttl_sec
            ]
            for peer_id in stale:
                self._peers.pop(peer_id, None)
            return list(self._peers.values())

    def _announce_loop(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        while not self._stop.is_set():
            packet = {
                "magic": DISCOVERY_MAGIC,
                "peer_id": self.peer_id,
                "gateway_port": self.gateway_port,
                "ts_epoch": time.time(),
            }
            raw = json.dumps(packet, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
            try:
                sock.sendto(raw, (self.broadcast_ip, self.discovery_port))
            except OSError:
                pass
            self._stop.wait(self.interval_sec)

    def _listen_loop(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("0.0.0.0", self.discovery_port))
        sock.settimeout(1.0)
        while not self._stop.is_set():
            try:
                raw, addr = sock.recvfrom(8192)
            except socket.timeout:
                continue
            except OSError:
                break
            try:
                packet = json.loads(raw.decode("utf-8", errors="replace"))
            except json.JSONDecodeError:
                continue
            if packet.get("magic") != DISCOVERY_MAGIC:
                continue
            peer_id = str(packet.get("peer_id") or "").strip()
            if not peer_id or peer_id == self.peer_id:
                continue
            with self._lock:
                self._peers[peer_id] = {
                    "peer_id": peer_id,
                    "ip": addr[0],
                    "gateway_port": int(packet.get("gateway_port", 0) or 0),
                    "last_seen_epoch": time.time(),
                }
