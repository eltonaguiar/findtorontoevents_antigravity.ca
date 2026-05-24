#!/usr/bin/env python3
"""Cross-PC protocol heartbeat client.

Connects to the canonical gateway (default http://192.168.2.32:8788) and
publishes a `peer.heartbeat` envelope every --interval seconds so the gateway's
`peer_registry` always reflects who is actually online.

Key behaviors:

- Retries with capped exponential backoff on connection-refused / timeout.
  Does NOT spin up a competing local gateway — there is exactly ONE canonical
  gateway per fleet and starting a second one fragments the bus (see
  CHATBIBLE_FAILURE.MD 2026-05-22T13:28Z correction).
- After --fail-threshold consecutive failures, appends a structured entry to
  CHATBIBLE_FAILURE.MD so the operator sees the gap without having to
  manually check /health.
- Logs every state transition (connected -> down, down -> connected) to
  stdout so it works cleanly under nssm/systemd journal capture.

Usage:
    python3 tools/register_peer.py \\
        --peer-id claude-opus-4-7-linux-wsl \\
        --http-base http://192.168.2.32:8788 \\
        --interval 60

Run as a service (Linux):
    add to systemd as a User service, ExecStart=python3 tools/register_peer.py ...

Run as a service (Windows):
    same nssm install pattern as the gateway itself.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import platform
import socket
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from cross_pc_protocol.client import ProtocolClient  # noqa: E402
from cross_pc_protocol.schema import new_envelope  # noqa: E402

DEFAULT_HTTP = "http://192.168.2.32:8788"
DEFAULT_INTERVAL = 60
DEFAULT_FAIL_THRESHOLD = 5  # ~5 missed heartbeats before logging to CHATBIBLE
MIN_BACKOFF = 5
MAX_BACKOFF = 300
FAILURE_LOG = REPO_ROOT / "CHATBIBLE_FAILURE.MD"


def _utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _log(msg: str) -> None:
    print(f"[{_utc_now()}] register_peer: {msg}", flush=True)


def _append_failure_entry(peer_id: str, http_base: str, error: str, consecutive: int) -> None:
    """Append a CHATBIBLE_FAILURE.MD entry. Best-effort — never raises."""
    try:
        entry = f"""
---
- **timestamp_utc:** {_utc_now()}
- **agent_runtime:** register_peer.py (heartbeat daemon)
- **provider/model:** n/a
- **ide / surface:** {platform.platform()}
- **host:** {socket.gethostname()}
- **stage_that_failed:** heartbeat
- **error_observed:** `{error}` (consecutive_failures={consecutive})
- **gateway_endpoint_tried:** `{http_base}`
- **peer_id_used:** {peer_id}
- **what_i_was_trying_to_send:** peer.heartbeat keepalive
- **fallback_used:** none — heartbeat daemon retries with exponential backoff and does NOT self-host a competing gateway
- **next_action:** restart canonical gateway on the Windows desktop service (nssm restart cross-pc-gateway) or investigate network reachability to {http_base}
"""
        with FAILURE_LOG.open("a", encoding="utf-8") as fh:
            fh.write(entry)
        _log(f"appended failure entry to {FAILURE_LOG.name}")
    except Exception as exc:
        _log(f"could not append to failure log: {exc}")


def _send_heartbeat(client: ProtocolClient, capabilities: list[str]) -> dict:
    payload = {
        "capabilities": capabilities,
        "host": socket.gethostname(),
        "platform": platform.platform(),
        "pid": os.getpid(),
        "ts_utc": _utc_now(),
    }
    envelope = new_envelope(
        sender=client.peer_id,
        topic="peer.heartbeat",
        payload=payload,
    )
    return client.publish_http(envelope)


def run_loop(args: argparse.Namespace) -> int:
    client = ProtocolClient(peer_id=args.peer_id, http_base=args.http_base)
    capabilities = [c.strip() for c in (args.capabilities or "").split(",") if c.strip()]

    _log(f"starting heartbeat: peer_id={args.peer_id} -> {args.http_base} every {args.interval}s")

    consecutive_failures = 0
    backoff = MIN_BACKOFF
    last_state = "init"  # "up" | "down" | "init"
    failure_entry_logged = False

    while True:
        try:
            # Manually built envelope via publish_http so we don't need .send()'s
            # message_id minting — the gateway re-stamps anyway. Catch network
            # errors only; let unexpected exceptions crash so a service manager
            # restarts us.
            resp = _send_heartbeat(client, capabilities)
            ok = bool(resp.get("ok") or resp.get("status") in ("accepted", "ok"))
            if not ok:
                raise RuntimeError(f"gateway rejected heartbeat: {resp}")

            if last_state != "up":
                _log(f"connected (transport={resp.get('transport', 'http')}) — was {last_state}")
                last_state = "up"
            consecutive_failures = 0
            backoff = MIN_BACKOFF
            failure_entry_logged = False
            time.sleep(args.interval)

        except KeyboardInterrupt:
            _log("interrupted, exiting cleanly")
            return 0

        except Exception as exc:
            consecutive_failures += 1
            err = f"{type(exc).__name__}: {exc}"
            if last_state != "down":
                _log(f"DOWN — {err} (will retry with backoff)")
                last_state = "down"
            else:
                _log(f"still down ({consecutive_failures}x) — {err}")

            if (
                consecutive_failures == args.fail_threshold
                and not failure_entry_logged
            ):
                _append_failure_entry(args.peer_id, args.http_base, err, consecutive_failures)
                failure_entry_logged = True

            time.sleep(backoff)
            backoff = min(backoff * 2, MAX_BACKOFF)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else "")
    parser.add_argument("--peer-id", required=True, help="unique peer identifier")
    parser.add_argument("--http-base", default=DEFAULT_HTTP)
    parser.add_argument("--interval", type=int, default=DEFAULT_INTERVAL,
                        help="seconds between heartbeats (default 60)")
    parser.add_argument("--fail-threshold", type=int, default=DEFAULT_FAIL_THRESHOLD,
                        help="consecutive failures before appending to CHATBIBLE_FAILURE.MD")
    parser.add_argument("--capabilities", default="",
                        help="comma-separated capability tags advertised in peer_registry")
    parser.add_argument("--once", action="store_true",
                        help="send one heartbeat and exit (for smoke testing)")
    args = parser.parse_args()

    if args.once:
        client = ProtocolClient(peer_id=args.peer_id, http_base=args.http_base)
        caps = [c.strip() for c in (args.capabilities or "").split(",") if c.strip()]
        try:
            resp = _send_heartbeat(client, caps)
            print(json.dumps(resp, indent=2))
            return 0 if resp.get("ok") else 1
        except Exception as exc:
            print(json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}"}, indent=2))
            return 1

    return run_loop(args)


if __name__ == "__main__":
    raise SystemExit(main())
