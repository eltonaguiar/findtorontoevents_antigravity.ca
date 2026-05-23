#!/usr/bin/env python3
"""Freebuff-compatible adapter for cross-PC protocol."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from cross_pc_protocol.client import ProtocolClient


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


def _build_payload(args: argparse.Namespace) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "command": args.command,
        "workspace": args.workspace or os.getcwd(),
        "meta": {
            "engine": "freebuff",
            "priority": args.priority,
        },
    }
    if args.extra_json:
        payload["extra"] = json.loads(args.extra_json)
    return payload


async def _run(args: argparse.Namespace) -> int:
    client = ProtocolClient(
        peer_id=args.peer_id,
        ws_url=args.ws_url,
        http_base=args.http_base,
    )
    await client.connect_ws(capabilities=["freebuff", "worker", "cli-adapter"])

    if args.mode == "dispatch":
        payload = _build_payload(args)
        result = await client.send(
            topic="worker.dispatch",
            payload=payload,
            to=args.to,
            require_ack=args.require_ack,
        )
        print(json.dumps(result, indent=2))
    elif args.mode == "heartbeat":
        payload = {"capabilities": ["freebuff", "worker"], "status": args.status}
        result = await client.send(
            topic="heartbeat",
            payload=payload,
            to=args.to,
            require_ack=False,
        )
        print(json.dumps(result, indent=2))
    else:
        # Poll self inbox + all inbox (broadcasts go to peer "all")
        results = []
        acks_sent = []
        peers_to_poll = [args.peer_id]
        if args.poll_peer and args.poll_peer != args.peer_id:
            peers_to_poll.append(args.poll_peer)
        for peer in peers_to_poll:
            r = client.poll(peer_id=peer, limit=args.limit)
            if peer != args.peer_id:
                r["peer_id"] = peer  # annotate which inbox
            results.append(r)
            # Auto-ACK any messages that require acknowledgment
            for msg in r.get("messages", []):
                if msg.get("require_ack"):
                    msg_id = msg.get("message_id", "")
                    if msg_id:
                        try:
                            ack_result = client.ack(msg_id)
                            acks_sent.append({"message_id": msg_id, "ack": ack_result})
                        except Exception as exc:
                            acks_sent.append({"message_id": msg_id, "error": str(exc)})
        output = {"ok": True, "polls": results}
        if acks_sent:
            output["acks_sent"] = acks_sent
        if len(results) == 1:
            print(json.dumps(output, indent=2))
        else:
            print(json.dumps(output, indent=2))

    await client.close_ws()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Freebuff protocol adapter")
    parser.add_argument("--peer-id", required=True)
    parser.add_argument("--ws-url", default=_GATEWAY_WS)
    parser.add_argument("--http-base", default=_GATEWAY_HTTP)
    sub = parser.add_subparsers(dest="mode", required=True)

    dispatch_p = sub.add_parser("dispatch")
    dispatch_p.add_argument("--command", required=True)
    dispatch_p.add_argument("--to", default="")
    dispatch_p.add_argument("--workspace", default="")
    dispatch_p.add_argument("--priority", default="normal")
    dispatch_p.add_argument("--extra-json", default="")
    dispatch_p.add_argument("--require-ack", action="store_true")

    heartbeat_p = sub.add_parser("heartbeat")
    heartbeat_p.add_argument("--status", default="ready")
    heartbeat_p.add_argument("--to", default="")

    poll_p = sub.add_parser("poll")
    poll_p.add_argument("--limit", type=int, default=20)
    poll_p.add_argument("--poll-peer", default="", help="Also poll a specific peer's inbox (e.g. 'all' for broadcasts) alongside own inbox")

    args = parser.parse_args()
    try:
        return asyncio.run(_run(args))
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON argument: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
