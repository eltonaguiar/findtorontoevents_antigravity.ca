#!/usr/bin/env python3
"""Run standalone LAN discovery announcer/listener."""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from cross_pc_protocol.lan_discovery import LanDiscovery


def main() -> int:
    parser = argparse.ArgumentParser(description="Cross-PC LAN discovery utility")
    parser.add_argument("--peer-id", required=True, help="Local peer id")
    parser.add_argument("--gateway-port", type=int, default=8787)
    parser.add_argument("--discovery-port", type=int, default=47655)
    parser.add_argument("--interval-sec", type=int, default=3)
    args = parser.parse_args()

    service = LanDiscovery(
        peer_id=args.peer_id,
        gateway_port=args.gateway_port,
        discovery_port=args.discovery_port,
        interval_sec=args.interval_sec,
    )
    service.start()
    print("LAN discovery started. Press Ctrl+C to stop.")
    try:
        while True:
            peers = service.peers()
            print(json.dumps({"peer_id": args.peer_id, "peers": peers}, indent=2))
            time.sleep(max(args.interval_sec, 1))
    except KeyboardInterrupt:
        service.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
