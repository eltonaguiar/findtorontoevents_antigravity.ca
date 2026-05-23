#!/usr/bin/env python3
"""
Write GATEWAY_ADDRESS.json at repo root with this machine's current LAN IP.

Run this ONCE after starting the gateway on the desktop. The committed file
lets any agent on any machine do `git pull` to discover the gateway address
without hardcoding IPs or relying on UDP auto-discovery.

Usage:
    python tools/write_gateway_address.py [--http-port 8788] [--ws-port 8787] [--commit]

The --commit flag does: git add GATEWAY_ADDRESS.json && git commit && git push
so the address is immediately available to all peers via git pull.
"""
from __future__ import annotations

import argparse
import json
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT = REPO_ROOT / "GATEWAY_ADDRESS.json"


def _lan_ip() -> str:
    """Return this machine's LAN IP by routing toward 8.8.8.8."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return "127.0.0.1"


def main() -> int:
    parser = argparse.ArgumentParser(description="Write GATEWAY_ADDRESS.json")
    parser.add_argument("--http-port", type=int, default=8788)
    parser.add_argument("--ws-port", type=int, default=8787)
    parser.add_argument("--peer-id", default="")
    parser.add_argument("--commit", action="store_true",
                        help="git add + commit + push so all peers get it immediately")
    args = parser.parse_args()

    ip = _lan_ip()
    hostname = socket.gethostname()
    peer_id = args.peer_id or f"gateway-{hostname.lower()}"
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    record = {
        "gateway_host": ip,
        "http_port": args.http_port,
        "ws_port": args.ws_port,
        "http_base": f"http://{ip}:{args.http_port}",
        "ws_url": f"ws://{ip}:{args.ws_port}",
        "gateway_peer_id": peer_id,
        "hostname": hostname,
        "updated_utc": now,
        "_note": (
            "Auto-written by tools/write_gateway_address.py on gateway start. "
            "Do `git pull` then read this file to find the gateway. "
            "Agents: use http_base value directly — no hardcoded IPs needed."
        ),
    }

    OUTPUT.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(f"[write_gateway_address] Wrote {OUTPUT}")
    print(f"  gateway_host : {ip}")
    print(f"  http_base    : http://{ip}:{args.http_port}")
    print(f"  ws_url       : ws://{ip}:{args.ws_port}")
    print(f"  updated_utc  : {now}")

    if args.commit:
        cmds = [
            ["git", "add", "GATEWAY_ADDRESS.json"],
            ["git", "commit", "-m",
             f"chore: update GATEWAY_ADDRESS.json — gateway at {ip}:{args.http_port} [{now}] [skip ci]"],
            ["git", "push", "origin", "HEAD:main"],
        ]
        for cmd in cmds:
            r = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
            if r.returncode != 0:
                print(f"[write_gateway_address] WARNING: {' '.join(cmd)} failed:\n{r.stderr}")
            else:
                print(f"[write_gateway_address] {' '.join(cmd[:3])} OK")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
