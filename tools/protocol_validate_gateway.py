#!/usr/bin/env python3
"""Validate which cross-PC gateway address the local agent should use.

Run this BEFORE any cross-PC broadcast. It auto-detects the local machine's
IP, decides whether to use `127.0.0.1:8788` (desktop, talking to its own
gateway) or `192.168.2.32:8788` (any other PC on the LAN, talking to the
desktop's gateway), probes /health, and prints a canonical config block
the adapter scripts can source.

Stops agents (and humans) from posting to the wrong endpoint and then
"confirming success" by polling that same wrong endpoint — see
CHATBIBLE.MD §0b ("the local confirmation trap").

Exit codes:
  0 — gateway reachable + agent's own peer-id, host, and chosen endpoint
      printed as JSON to stdout
  1 — gateway unreachable on the chosen endpoint
  2 — agent appears to BE the gateway host (desktop) and 192.168.2.32 was
      forced via --force-lan, which would route through its own NIC and
      produce a misleading "success" — refused

Usage:

  python tools/protocol_validate_gateway.py
  python tools/protocol_validate_gateway.py --runtime hermes
  python tools/protocol_validate_gateway.py --json | tee /tmp/gateway_config.json
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import sys
from typing import Any, Dict, Tuple

try:
    import urllib.request as urlreq
except ImportError:
    urlreq = None  # type: ignore

DESKTOP_LAN_IP = "192.168.2.32"
GATEWAY_HTTP_PORT = 8788
GATEWAY_WS_PORT = 8787
DESKTOP_HOSTNAME_HINTS = ("desktop-081g9oh", "081g9oh")


def detect_local_ipv4_addrs() -> list[str]:
    """Best-effort enumeration of this host's non-loopback IPv4 addresses."""
    addrs: set[str] = set()
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            ip = info[4][0]
            if ip and not ip.startswith("127."):
                addrs.add(ip)
    except OSError:
        pass
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0)
        s.connect(("8.8.8.8", 80))
        addrs.add(s.getsockname()[0])
        s.close()
    except OSError:
        pass
    return sorted(addrs)


def probe_health(http_base: str, timeout: float = 3.0) -> Tuple[bool, dict[str, Any]]:
    if urlreq is None:
        return False, {"error": "urllib not available"}
    try:
        with urlreq.urlopen(f"{http_base}/health", timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
            return bool(data.get("ok")), data
    except Exception as exc:
        return False, {"error": f"{type(exc).__name__}: {exc}"}


def is_desktop_host(hostname: str, local_ips: list[str]) -> bool:
    name_lower = hostname.lower()
    if any(hint in name_lower for hint in DESKTOP_HOSTNAME_HINTS):
        return True
    return DESKTOP_LAN_IP in local_ips


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--runtime", default=None,
                    help="If set, suggested --peer-id is <runtime>-<hostname>")
    ap.add_argument("--force-lan", action="store_true",
                    help="Force LAN endpoint even on the desktop. Refused: misleads")
    ap.add_argument("--json", action="store_true",
                    help="Output JSON only (no human-readable summary)")
    args = ap.parse_args()

    hostname = socket.gethostname()
    local_ips = detect_local_ipv4_addrs()
    desktop = is_desktop_host(hostname, local_ips)

    if desktop and args.force_lan:
        print(
            "REFUSED: --force-lan requested but this host (%s, ips=%s) appears to BE the desktop. "
            "Hitting 192.168.2.32 from here returns this same gateway via the local NIC, "
            "which fakes a success. Use the default (no --force-lan) on the desktop."
            % (hostname, local_ips),
            file=sys.stderr,
        )
        return 2

    if desktop:
        http_base = f"http://127.0.0.1:{GATEWAY_HTTP_PORT}"
        ws_url = f"ws://127.0.0.1:{GATEWAY_WS_PORT}"
        role = "desktop"
    else:
        http_base = f"http://{DESKTOP_LAN_IP}:{GATEWAY_HTTP_PORT}"
        ws_url = f"ws://{DESKTOP_LAN_IP}:{GATEWAY_WS_PORT}"
        role = "lan-peer"

    ok, health = probe_health(http_base)

    suggested_peer_id = None
    if args.runtime:
        # Hostname slug: strip domain, lowercase, remove non-alphanum
        slug = "".join(c if c.isalnum() else "-" for c in hostname.lower()).strip("-")
        suggested_peer_id = f"{args.runtime}-{slug}"

    n_peers = len(health.get("peer_registry") or {}) if ok else 0
    config: Dict[str, Any] = {
        "ok": ok,
        "role": role,
        "hostname": hostname,
        "local_ips": local_ips,
        "http_base": http_base,
        "ws_url": ws_url,
        "n_peers": n_peers,
        "peer_registry_sample": list((health.get("peer_registry") or {}).keys())[:5],
        "lan_peers": health.get("lan_peers", []) if ok else [],
        "suggested_peer_id": suggested_peer_id,
    }

    if not ok:
        config["health_error"] = health.get("error") or health.get("note") or "unknown"

    if args.json:
        print(json.dumps(config, indent=2))
        return 0 if ok else 1

    # Human-readable summary
    print("=" * 60)
    print("cross-PC gateway validation")
    print("=" * 60)
    print(f"hostname      : {hostname}")
    print(f"local IPs     : {', '.join(local_ips) or '(none detected)'}")
    print(f"role detected : {role}")
    print(f"endpoint      : {http_base}  (ws={ws_url})")
    if suggested_peer_id:
        print(f"suggested --peer-id: {suggested_peer_id}")
    print("-" * 60)
    if ok:
        print(f"health ok     : YES  ({n_peers} peers in registry)")
        sample = config["peer_registry_sample"]
        print(f"peers (sample): {', '.join(sample) if sample else '(empty — post-restart first-arrival OK)'}")
        if n_peers == 1 and sample and suggested_peer_id and sample[0].startswith(args.runtime or ""):
            print()
            print("NOTE: n_peers == 1 and it looks like that peer is YOU.")
            print("Per CHATBIBLE §0c rule-of-thumb table: this is either post-restart")
            print("first-arrival (wait + others reconnect) OR the localhost trap.")
            print("Verify by sending a probe broadcast + asking desktop operator to tail.")
        return 0
    else:
        print(f"health ok     : NO   ({config['health_error']})")
        print()
        if role == "lan-peer":
            print("Troubleshooting (per CHATBIBLE §0c):")
            print(f"  1. ping {DESKTOP_LAN_IP}                       — basic LAN reachability")
            print(f"  2. curl -s http://{DESKTOP_LAN_IP}:{GATEWAY_HTTP_PORT}/health  — manual repro")
            print(f"  3. Ask desktop operator if the gateway is running")
            print(f"  4. If on a different subnet: VPN / SSH tunnel (CHATBIBLE §8)")
        else:
            print("Gateway on this desktop is down. Start it:")
            print("  python tools/protocol_gateway.py --host 0.0.0.0 \\")
            print("    --ws-port 8787 --http-port 8788 --peer-id gateway-a")
        return 1


if __name__ == "__main__":
    sys.exit(main())
