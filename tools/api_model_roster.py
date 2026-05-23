#!/usr/bin/env python3
"""Probe API keys, refresh model lists, ping-test chat — one provider at a time.

Writes: config/api_model_roster.json (machine) + optional markdown append.

Usage:
  python tools/api_model_roster.py --probe all
  python tools/api_model_roster.py --probe openrouter --ping-model inclusionai/ring-2.5
  python tools/api_model_roster.py --list-ring
  python tools/api_model_roster.py --status
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT_JSON = REPO / "config" / "api_model_roster.json"
PING_PROMPT = "Reply with exactly: PONG plus one repo path you would wire first (e.g. ml_consensus/consensus.py)."


@dataclass
class ProviderSpec:
    slug: str
    key_envs: tuple[str, ...]
    models_url: str | None = None
    chat_url: str | None = None
    default_model: str = ""
    extra_headers: dict[str, str] = field(default_factory=dict)
    notes: str = ""


def _winreg_key(name: str) -> str:
    if sys.platform != "win32":
        return ""
    try:
        import winreg
        for root, sub in (
            (winreg.HKEY_CURRENT_USER, "Environment"),
            (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"),
        ):
            try:
                with winreg.OpenKey(root, sub) as k:
                    val, _ = winreg.QueryValueEx(k, name)
                    if val:
                        return str(val).strip()
            except OSError:
                continue
    except ImportError:
        pass
    return ""


def resolve_key(envs: tuple[str, ...]) -> str:
    for n in envs:
        v = os.environ.get(n, "").strip()
        if v:
            return v
    for n in envs:
        v = _winreg_key(n)
        if v:
            return v
    return ""


PROVIDERS: list[ProviderSpec] = [
    ProviderSpec("cerebras_free", ("CEREBRAS_FREE_API_KEY", "CEREBRAS_API_KEY_FREE"),
                 "https://api.cerebras.ai/v1/models", "https://api.cerebras.ai/v1/chat/completions", "llama-3.3-70b"),
    ProviderSpec("cerebras_paid", ("CEREBRAS_PAID_API_KEY", "CEREBRAS_API_KEY"),
                 "https://api.cerebras.ai/v1/models", "https://api.cerebras.ai/v1/chat/completions", "gpt-oss-120b"),
    ProviderSpec("groq", ("GROQ_API_KEY", "GROQ_KEY"),
                 "https://api.groq.com/openai/v1/models", "https://api.groq.com/openai/v1/chat/completions",
                 "llama-3.3-70b-versatile"),
    ProviderSpec("openrouter", ("OPENROUTER", "OPENROUTER_API_KEY", "OPENROUTER_API_KEY_PAID"),
                 "https://openrouter.ai/api/v1/models", "https://openrouter.ai/api/v1/chat/completions",
                 "openrouter/free"),
    ProviderSpec("deepseek", ("DEEPSEEK_API_KEY", "DEEPSEEK_API"),
                 None, "https://api.deepseek.com/chat/completions", "deepseek-chat"),
    ProviderSpec("inception", ("INCEPTION_AI_KEY", "INCEPTION_API_KEY"),
                 None, "https://api.inceptionlabs.ai/v1/chat/completions", "mercury-2"),
    ProviderSpec("xai", ("XAI_API_KEY", "X_AI_KEY", "GROK_API_KEY"),
                 None, "https://api.x.ai/v1/chat/completions", "grok-3-latest"),
    ProviderSpec("kimi", ("KIMI_API_KEY", "KIMI_MOONSHOT_APIKEY"),
                 None, "https://api.moonshot.ai/v1/chat/completions", "moonshot-v1-32k"),
    ProviderSpec("huggingface", ("HUGGING_FACE_TOKEN", "HF_TOKEN", "HUGGINGFACE_API_KEY"),
                 None, "https://router.huggingface.co/v1/chat/completions",
                 "meta-llama/Llama-3.3-70B-Instruct"),
    ProviderSpec("chutes", ("CHUTES_API_KEY_FREE", "CHUTES_API_KEY"),
                 "https://llm.chutes.ai/v1/models", "https://llm.chutes.ai/v1/chat/completions",
                 "zai-org/GLM-5-TEE", extra_headers={"User-Agent": "Mozilla/5.0"}),
    ProviderSpec("ofox", ("OFOX_API_KEY", "OFOX_AI_KEY"),
                 None, "https://api.ofox.ai/v1/chat/completions", "z-ai/glm-4.7-flash:free"),
    ProviderSpec("llm7", ("LLM7_API_KEY_FREE", "LLM7_API_KEY"),
                 "https://api.llm7.io/v1/models", "https://api.llm7.io/v1/chat/completions",
                 "qwen2.5-coder-32b", extra_headers={"User-Agent": "Mozilla/5.0"}),
    ProviderSpec("mistral", ("MISTRA_API_KEY_FREE", "MISTRAL_API_KEY"),
                 "https://api.mistral.ai/v1/models", "https://api.mistral.ai/v1/chat/completions",
                 "mistral-small-latest"),
    ProviderSpec("ollama_cloud", ("OLLAMA_CLOUD_KEY",),
                 None, "https://ollama.com/v1/chat/completions", "gpt-oss:120b"),
    ProviderSpec("opencode", ("OPENCODE_API_KEY",), notes="CLI-only — not HTTP pinged here"),
    ProviderSpec("kilocode", ("KILOCODE_API_KEY", "KILO_API_KEY"), notes="CLI gateway — not HTTP pinged here"),
]


def http_get(url: str, key: str, headers: dict | None = None, timeout: int = 60) -> tuple[int, str]:
    req = urllib.request.Request(url, method="GET")
    if key:
        req.add_header("Authorization", "Bearer " + key)
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")[:2000]
    except Exception as e:
        return 0, str(e)[:500]


def http_chat(url: str, key: str, model: str, headers: dict | None = None,
              timeout: int = 90, max_tokens: int = 80) -> tuple[bool, float, str, str]:
    body = {
        "model": model,
        "messages": [{"role": "user", "content": PING_PROMPT}],
        "max_tokens": max_tokens,
        "temperature": 0.1,
    }
    if "cerebras" in url:
        body = {
            "model": model,
            "messages": body["messages"],
            "max_completion_tokens": max_tokens,
            "temperature": 0.1,
        }
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    if key:
        req.add_header("Authorization", "Bearer " + key)
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
        elapsed = round(time.time() - t0, 2)
        text = raw.get("choices", [{}])[0].get("message", {}).get("content", "") or ""
        return True, elapsed, text[:500], ""
    except urllib.error.HTTPError as e:
        elapsed = round(time.time() - t0, 2)
        err = e.read().decode("utf-8", errors="replace")[:400]
        return False, elapsed, "", f"HTTP {e.code}: {err}"
    except Exception as e:
        return False, round(time.time() - t0, 2), "", str(e)[:400]


def parse_models_json(text: str) -> list[str]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    ids: list[str] = []
    if isinstance(data, dict) and "data" in data:
        for item in data["data"]:
            mid = item.get("id") or item.get("name")
            if mid:
                ids.append(str(mid))
    return ids[:500]


def find_ring_models(models: list[str]) -> list[str]:
    return sorted([m for m in models if "ring" in m.lower() or "inclusionai" in m.lower()])


def probe_provider(spec: ProviderSpec, ping_model: str | None = None) -> dict:
    key = resolve_key(spec.key_envs)
    result: dict = {
        "slug": spec.slug,
        "key_present": bool(key),
        "key_env_hit": next((e for e in spec.key_envs if resolve_key((e,))), ""),
        "notes": spec.notes,
        "models": [],
        "ring_models": [],
        "ping": None,
    }
    if not key and spec.slug not in ("opencode", "kilocode"):
        result["error"] = "no_key"
        return result
    if spec.slug in ("opencode", "kilocode"):
        result["cli_only"] = True
        return result

    if spec.models_url:
        code, text = http_get(spec.models_url, key, spec.extra_headers)
        result["models_http"] = code
        if code == 200:
            result["models"] = parse_models_json(text)
            result["ring_models"] = find_ring_models(result["models"])

    model = ping_model or spec.default_model
    if spec.chat_url and model:
        ok, elapsed, text, err = http_chat(spec.chat_url, key, model, spec.extra_headers)
        result["ping"] = {
            "model": model,
            "ok": ok,
            "elapsed_s": elapsed,
            "chars": len(text),
            "preview": text[:200],
            "error": err,
        }
    return result


def load_roster() -> dict:
    if OUT_JSON.is_file():
        return json.loads(OUT_JSON.read_text(encoding="utf-8"))
    return {"version": 1, "providers": {}, "history": []}


def save_roster(data: dict) -> None:
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    data["updated_utc"] = datetime.now(timezone.utc).isoformat()
    OUT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--probe", metavar="SLUG", help="provider slug or 'all'")
    ap.add_argument("--ping-model", help="override model for ping test")
    ap.add_argument("--list-ring", action="store_true", help="print Ring models from last openrouter probe")
    ap.add_argument("--status", action="store_true", help="print key status only")
    args = ap.parse_args()

    if args.status:
        for spec in PROVIDERS:
            k = resolve_key(spec.key_envs)
            print(f"  {spec.slug:16} {'READY' if k else 'NO KEY':8}  {spec.key_envs[0]}")
        return 0

    roster = load_roster()
    if "providers" not in roster:
        roster["providers"] = {}

    if args.list_ring:
        or_data = roster.get("providers", {}).get("openrouter", {})
        for m in or_data.get("ring_models", []):
            print(m)
        return 0

    if not args.probe:
        ap.print_help()
        return 1

    targets = PROVIDERS if args.probe == "all" else [p for p in PROVIDERS if p.slug == args.probe]
    if not targets:
        print(f"Unknown provider: {args.probe}", file=sys.stderr)
        return 1

    for spec in targets:
        print(f"Probing {spec.slug}...", flush=True)
        r = probe_provider(spec, args.ping_model if args.probe != "all" else None)
        roster["providers"][spec.slug] = r
        roster["history"].append({"ts": datetime.now(timezone.utc).isoformat(), "slug": spec.slug,
                                  "ping_ok": (r.get("ping") or {}).get("ok")})
        save_roster(roster)
        ping = r.get("ping") or {}
        print(f"  key={'Y' if r.get('key_present') else 'N'} models={len(r.get('models', []))} "
              f"ping={'OK' if ping.get('ok') else 'FAIL'} {ping.get('elapsed_s', '-')}s")
        if r.get("ring_models"):
            print(f"  ring: {', '.join(r['ring_models'][:8])}")
        if ping.get("error"):
            err = ping["error"][:120].encode("ascii", errors="replace").decode("ascii")
            print(f"  err: {err}")
        time.sleep(1)

    print(f"\nWrote {OUT_JSON}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
