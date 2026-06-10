#!/usr/bin/env python3
"""Build chatLanguageModels.json from ~/dbpasses.txt — all BYOK providers, real keys."""
from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path

HOME = Path.home()
DBPASSES = HOME / "dbpasses.txt"
REPO = Path(__file__).resolve().parents[1]
FIX_OUT = REPO / "tools" / "FIX_NOW_chatLanguageModels.json"
REMOTE_USER_SETTINGS = HOME / ".vscode-server" / "data" / "User" / "settings.json"
REMOTE_MACHINE_SETTINGS = HOME / ".vscode-server" / "data" / "Machine" / "settings.json"
REMOTE_USER_LM = HOME / ".vscode-server" / "data" / "User" / "chatLanguageModels.json"
REMOTE_MACHINE_LM = HOME / ".vscode-server" / "data" / "Machine" / "chatLanguageModels.json"
LOCAL_CODE_LM = HOME / ".config" / "Code" / "User" / "chatLanguageModels.json"

# label in dbpasses.txt -> next-line key pattern
KEY_SPECS: list[tuple[str, re.Pattern[str]]] = [
    ("DEEPSEEK_API", re.compile(r"^sk-")),
    ("OPEN ROUTER API KEY", re.compile(r"^sk-or-")),
    ("ANTR_MAY2026", re.compile(r"^sk-ant-")),
    ("ANTR", re.compile(r"^sk-ant-")),
    ("GROK NEW2", re.compile(r"^xai-")),
    ("GROK NEW", re.compile(r"^xai-")),
    ("OPENAI_KEY", re.compile(r"^sk-")),
]


def read_dbpasses_keys() -> dict[str, str]:
    if not DBPASSES.exists():
        raise SystemExit(f"Missing {DBPASSES}")
    lines = [ln.rstrip("\r") for ln in DBPASSES.read_text(encoding="utf-8", errors="replace").splitlines()]
    found: dict[str, str] = {}
    for label, pattern in KEY_SPECS:
        if label in found:
            continue
        norm_label = label.rstrip(":").strip()
        for i, line in enumerate(lines):
            if line.strip().rstrip(":").strip() != norm_label:
                continue
            for j in range(i + 1, min(i + 4, len(lines))):
                candidate = lines[j].strip()
                if candidate and pattern.match(candidate):
                    found[label] = candidate
                    break
            break
    if "DEEPSEEK_API" not in found:
        raise SystemExit("DEEPSEEK_API missing in dbpasses.txt")
    return found


def deepseek_block(api_key: str) -> dict:
    return {
        "name": "DeepSeek",
        "vendor": "customendpoint",
        "apiKey": api_key,
        "apiType": "chat-completions",
        "models": [
            {
                "id": "deepseek-v4-pro",
                "name": "DeepSeek V4 Pro",
                "url": "https://api.deepseek.com/chat/completions",
                "toolCalling": True,
                "vision": False,
                "thinking": True,
                "maxInputTokens": 128000,
                "maxOutputTokens": 8192,
                "supportsReasoningEffort": ["low", "medium", "high"],
            },
            {
                "id": "deepseek-v4-flash",
                "name": "DeepSeek V4 Flash",
                "url": "https://api.deepseek.com/chat/completions",
                "toolCalling": True,
                "vision": False,
                "thinking": True,
                "maxInputTokens": 128000,
                "maxOutputTokens": 8192,
                "supportsReasoningEffort": ["low", "medium", "high"],
            },
        ],
    }


def build_config(keys: dict[str, str]) -> list[dict]:
    cfg: list[dict] = []

    openrouter = keys.get("OPEN ROUTER API KEY")
    if openrouter:
        cfg.append({"name": "OpenRouter", "vendor": "openrouter", "apiKey": openrouter})

    xai = keys.get("GROK NEW2") or keys.get("GROK NEW")
    if xai:
        cfg.append({"name": "xAI", "vendor": "xai", "apiKey": xai})

    anthropic = keys.get("ANTR_MAY2026") or keys.get("ANTR")
    if anthropic:
        cfg.append({"name": "Anthropic", "vendor": "anthropic", "apiKey": anthropic})

    cfg.append(deepseek_block(keys["DEEPSEEK_API"]))
    return cfg


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent="\t") + "\n", encoding="utf-8")
    print(f"wrote {path}")


def merge_settings_file(path: Path, api_key: str) -> None:
    data: dict = {}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {}
    data["deepseek-copilot.apiKey"] = api_key
    write_json(path, data)


def verify_deepseek(api_key: str) -> None:
    req = urllib.request.Request(
        "https://api.deepseek.com/chat/completions",
        data=json.dumps(
            {
                "model": "deepseek-v4-flash",
                "messages": [{"role": "user", "content": "ping"}],
                "max_tokens": 4,
                "stream": False,
            }
        ).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        if resp.status != 200:
            raise SystemExit(f"DeepSeek API verify failed: HTTP {resp.status}")
    print("DeepSeek API key from dbpasses.txt: OK")


def main() -> int:
    keys = read_dbpasses_keys()
    cfg = build_config(keys)
    write_json(LOCAL_CODE_LM, cfg)
    write_json(REMOTE_USER_LM, cfg)
    write_json(REMOTE_MACHINE_LM, cfg)
    write_json(FIX_OUT, cfg)
    merge_settings_file(REMOTE_USER_SETTINGS, keys["DEEPSEEK_API"])
    merge_settings_file(REMOTE_MACHINE_SETTINGS, keys["DEEPSEEK_API"])
    verify_deepseek(keys["DEEPSEEK_API"])

    present = []
    if keys.get("OPEN ROUTER API KEY"):
        present.append("OpenRouter")
    if keys.get("GROK NEW2") or keys.get("GROK NEW"):
        present.append("xAI")
    if keys.get("ANTR_MAY2026") or keys.get("ANTR"):
        present.append("Anthropic")
    present.append("DeepSeek")
    print(f"Providers with keys: {', '.join(present)}")
    print("Run: python3 tools/set_deepseek_copilot_key.py  (Vizards SecretStorage + Machine settings)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())