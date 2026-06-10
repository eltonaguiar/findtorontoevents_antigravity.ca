#!/usr/bin/env python3
"""Apply Copilot BYOK on gx10 + push to Windows gateway host (no manual steps)."""
from __future__ import annotations

import asyncio
import json
import socket
import sys
import uuid
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from cross_pc_protocol.client import ProtocolClient  # noqa: E402
from cross_pc_protocol.schema import new_envelope  # noqa: E402
from tools.write_copilot_lm_config import (  # noqa: E402
    FIX_OUT,
    LOCAL_CODE_LM,
    build_config,
    merge_remote_settings,
    read_dbpasses_keys,
    verify_deepseek,
    write_json,
)

VSCODE_SERVER_USER = Path.home() / ".vscode-server/data/User/chatLanguageModels.json"

GATEWAY_HTTP = "http://192.168.2.32:8788"
GATEWAY_WS = "ws://192.168.2.32:8787"
VSCODE_SERVER_MACHINE = Path.home() / ".vscode-server/data/Machine/chatLanguageModels.json"


def write_all_local(cfg: list) -> None:
    write_json(LOCAL_CODE_LM, cfg)
    write_json(VSCODE_SERVER_USER, cfg)
    write_json(VSCODE_SERVER_MACHINE, cfg)
    write_json(FIX_OUT, cfg)


async def push_to_windows_gateway(cfg: list) -> dict:
    host = socket.gethostname().lower().replace(" ", "-")
    peer = f"cursor-{host}"
    client = ProtocolClient(peer_id=peer, ws_url=GATEWAY_WS, http_base=GATEWAY_HTTP)
    envelope = new_envelope(
        sender=peer,
        target="gateway",
        topic="copilot.apply_lm",
        payload={"config": cfg},
    )
    return client.publish_http(envelope)


def main() -> int:
    keys = read_dbpasses_keys()
    cfg = build_config(keys)
    write_all_local(cfg)
    merge_remote_settings(keys["DEEPSEEK_API"])
    verify_deepseek(keys["DEEPSEEK_API"])

    try:
        result = asyncio.run(push_to_windows_gateway(cfg))
        print("gateway:", json.dumps(result))
        if result.get("status") == "copilot_lm_applied" and result.get("ok"):
            print("Windows chatLanguageModels.json written via gateway.")
            return 0
    except Exception as exc:
        print(f"gateway push failed: {exc}")

    print("gx10 configs written (OpenRouter, xAI, Anthropic, DeepSeek).")
    print("Reload VS Code window to pick up remote BYOK.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())