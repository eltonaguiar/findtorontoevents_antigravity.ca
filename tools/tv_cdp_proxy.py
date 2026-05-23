"""Userland TCP forwarder for the TradingView Desktop CDP port.

The `tradingview-desktop` MCP hard-codes the CDP port to 9222. TradingView is
often launched on 9223 to avoid collisions with other Chromium tools. This
script bridges 9222 -> 9223 (or any forward port) without requiring admin
(unlike `netsh interface portproxy`).

Usage:
    python tools/tv_cdp_proxy.py [listen=9222] [forward=9223]

Referenced from .claude/skills/tv-cdp-launch/SKILL.md (Step 4b).
"""

from __future__ import annotations

import socket
import sys
import threading


def pipe(a: socket.socket, b: socket.socket) -> None:
    try:
        while True:
            data = a.recv(65536)
            if not data:
                break
            b.sendall(data)
    except OSError:
        pass
    finally:
        for s in (a, b):
            try:
                s.close()
            except OSError:
                pass


def handle(client: socket.socket, forward_port: int) -> None:
    upstream = socket.socket()
    upstream.connect(("127.0.0.1", forward_port))
    threading.Thread(target=pipe, args=(client, upstream), daemon=True).start()
    pipe(upstream, client)


def main(listen: int = 9222, forward: int = 9223) -> None:
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("127.0.0.1", listen))
    s.listen(50)
    print(f"LISTEN {listen} -> {forward}", flush=True)
    while True:
        client, _ = s.accept()
        threading.Thread(target=handle, args=(client, forward), daemon=True).start()


if __name__ == "__main__":
    listen_port = int(sys.argv[1]) if len(sys.argv) > 1 else 9222
    forward_port = int(sys.argv[2]) if len(sys.argv) > 2 else 9223
    main(listen_port, forward_port)
