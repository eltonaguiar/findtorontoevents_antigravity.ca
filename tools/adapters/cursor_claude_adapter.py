#!/usr/bin/env python3
"""Cursor/Claude adapter for cross-PC protocol."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import socket
import sys
from pathlib import Path
from typing import Any, Dict

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from cross_pc_protocol.client import ProtocolClient
from cross_pc_protocol.inbox_drain import startup_inbox_check


def _discover_gateway() -> tuple[str, str]:
    """Return (http_base, ws_url) by checking env → GATEWAY_ADDRESS.json → localhost fallback."""
    env_http = os.environ.get("CHATBIBLE_GATEWAY_HTTP", "").strip()
    env_ws = os.environ.get("CHATBIBLE_GATEWAY_WS", "").strip()
    if env_http:
        ws = env_ws or env_http.replace("http://", "ws://").replace(":8788", ":8787")
        return env_http, ws
    addr_file = REPO_ROOT / "GATEWAY_ADDRESS.json"
    if addr_file.exists():
        try:
            data = json.loads(addr_file.read_text(encoding="utf-8"))
            http = data.get("http_base", "")
            ws = data.get("ws_url", "")
            if http:
                return http, ws or http.replace("http://", "ws://").replace(":8788", ":8787")
        except Exception:
            pass
    return "http://127.0.0.1:8788", "ws://127.0.0.1:8787"


_GATEWAY_HTTP, _GATEWAY_WS = _discover_gateway()


def _runtime_default() -> str:
    return str(os.environ.get("CROSS_PC_RUNTIME", "cursor")).strip().lower() or "cursor"


def _resolve_peer_id(args: argparse.Namespace) -> str:
    if args.peer_id:
        return args.peer_id.strip()
    env_peer = str(os.environ.get("CROSS_PC_PEER_ID", "")).strip()
    if env_peer:
        return env_peer
    runtime = args.runtime
    host = socket.gethostname().lower().replace(" ", "-")
    return f"{runtime}-{host}"


async def _run(args: argparse.Namespace) -> int:
    peer_id = _resolve_peer_id(args)
    client = ProtocolClient(
        peer_id=peer_id,
        ws_url=args.ws_url,
        http_base=args.http_base,
    )
    await client.connect_ws(capabilities=["cursor", "claude", "mcp-adapter"])

    if args.mode == "send":
        payload: Dict[str, Any] = json.loads(args.payload)
        result = await client.send(
            topic=args.topic,
            payload=payload,
            to=args.to,
            require_ack=args.require_ack,
        )
        print(json.dumps(result, indent=2))
        # Auto-drain the inbox on every send. Prevents the "send-only agent"
        # bug (2026-05-15): an agent broadcasts requests but never polls its
        # own DM/broadcast queue, so replies sit unread. Coupling drain to
        # send makes that failure structurally impossible. Fail-soft.
        try:
            from cross_pc_protocol.inbox_drain import startup_inbox_check
            pending = startup_inbox_check(peer_id, http_base=args.http_base)
            if pending:
                print(json.dumps(
                    {"inbox_drained": len(pending), "messages": pending},
                    indent=2))
        except Exception as _drain_err:  # noqa: BLE001
            print(f"[inbox] drain skipped: {_drain_err}", file=sys.stderr)
        await client.close_ws()
        return 0

    if args.mode == "poll":
        result = client.poll(limit=args.limit)
        print(json.dumps(result, indent=2))
        await client.close_ws()
        return 0

    if args.mode == "listen":
        print("Listening for one message...")
        message = await client.listen_once()
        if not message:
            print("No WS message received.")
            await client.close_ws()
            return 1
        print(json.dumps(message, indent=2))
        payload = message.get("payload", {})
        source_message_id = payload.get("message_id")
        if args.auto_ack and source_message_id:
            ack = client.ack(str(source_message_id))
            print(json.dumps({"ack": ack}, indent=2))
        await client.close_ws()
        return 0

    await client.close_ws()
    return 0


def main() -> int:
    # Auto-drain inbox on every adapter invocation (startup + every send/heartbeat).
    # This makes send-only agents impossible and fixes the multi-hour coordination loops.
    # Fail-soft: never let inbox drain break the adapter.
    try:
        peer = os.environ.get("CROSS_PC_PEER_ID") or ""
        if peer:
            startup_inbox_check(peer)
    except Exception:
        pass  # fail soft

    parser = argparse.ArgumentParser(description="Cursor/Claude protocol adapter")
    parser.add_argument(
        "--peer-id",
        default="",
        help="Explicit sender identity. If omitted, uses CROSS_PC_PEER_ID or inferred runtime-host id.",
    )
    parser.add_argument(
        "--runtime",
        default=_runtime_default(),
        choices=["cursor", "claude", "hermes", "freebuff", "agent"],
        help="Runtime identity namespace used when --peer-id is omitted.",
    )
    parser.add_argument("--ws-url", default=_GATEWAY_WS)
    parser.add_argument("--http-base", default=_GATEWAY_HTTP)
    sub = parser.add_subparsers(dest="mode", required=True)

    send_p = sub.add_parser("send")
    send_p.add_argument("--topic", required=True)
    send_p.add_argument("--payload", required=True, help="JSON object string")
    send_p.add_argument("--to", default="")
    send_p.add_argument("--require-ack", action="store_true")

    poll_p = sub.add_parser("poll")
    poll_p.add_argument("--limit", type=int, default=20)

    listen_p = sub.add_parser("listen")
    listen_p.add_argument("--auto-ack", action="store_true")

    args = parser.parse_args()
    try:
        return asyncio.run(_run(args))
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON payload: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
