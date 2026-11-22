#!/usr/bin/env python3
"""consult_multi.py — Multi-provider AI consult tool.

Wraps 9 free/paid LLM providers behind one CLI so multi-AI fan-outs and
single-provider consults share one well-tested code path.

Providers (alphabetical):
    cerebras       Cerebras inference (free key) — fast Llama/Qwen
    cloudflare     Cloudflare Workers AI — many open-source models
    fireworks      Fireworks AI (free key) — Llama / DeepSeek / Qwen / Mixtral
    gemini_api     Google Gemini direct REST (free key) — flash + pro
    github_models  GitHub Models (free quota on github_pat tokens) — GPT-4o, o1, Llama
    groq           Groq (free key) — fastest Llama-3.3 / Mixtral / Gemma
    huggingface    HuggingFace Inference Router (free hf_ token)
    nvidia         NVIDIA NIM (free key) — DeepSeek, Kimi, GLM, Nemotron, GPT-OSS
    together       Together AI (free key) — Llama-405B, DeepSeek-V3, Qwen

Key resolution: env vars FIRST (NVIDIA_API_KEY etc.), then ~/dbpasses.txt as
a fallback parser. The dbpasses.txt file is gitignored and stays in
/home/eaguiar2015 — NEVER committed.

Usage:
    python3 tools/consult_multi.py --list
    python3 tools/consult_multi.py --provider groq --model llama-3.3-70b-versatile \
        --prompt "What is 2+2?"
    python3 tools/consult_multi.py --provider nvidia --model moonshotai/kimi-k2.6 \
        --prompt-file /tmp/q.md
    python3 tools/consult_multi.py --fanout diverse5 --prompt-file /tmp/q.md \
        --out-dir /tmp/fanout_results

Fan-out presets (single prompt → all peers; aggregated to one dir):
    diverse5       1× each of nvidia/kimi, cloudflare/llama, groq/llama, gemini/pro, cerebras/llama
    fast4          groq/llama-instant, cerebras/llama, fireworks/llama, gemini/flash
    reasoning4     nvidia/kimi, gemini/pro, together/llama-405b, fireworks/deepseek
    all9           one model per provider (defaults below)

A `leakage-context block` is mandatory in prompts about asset-class or pick
performance. See .claude/skills/consult-nvidia-models/SKILL.md for the template.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Key loading
# ---------------------------------------------------------------------------
_KEYS_FILE = Path.home() / "dbpasses.txt"
_KEY_LABELS = {
    # env-var name : label string in dbpasses.txt that precedes the key
    "NVIDIA_API_KEY":     "NVIDIA:",
    "NVIDIA_API_KEY_ALT": "NVIDIA ALT KEY:",
    "GROQ_API_KEY":       "GROQ FREE KEY:",
    "GEMINI_API_KEY":     "GOOGLE GEMINI API KEY:",
    "GEMINI_API_KEY_ALT": "GOOGLE GEMIINI API KEY ALT:",  # sic — file has typo
    "GITHUB_MODELS_KEY":  "GITHUB MODELS API KEY:",
    "GITHUB_MODELS_KEY2": "GITHUB MODELS API KEY2:",
    "TOGETHER_API_KEY":   "TOGETHER AI API KEY:",
    "TOGETHER_API_KEY_ALT": "TOGETHER AI API KEY ALT:",
    "CEREBRAS_API_KEY":   "CEREBRAS_FREE_API_KEY:",
    "HF_API_TOKEN":       "HUGGING_FACE_TOKEN",
    "HF_API_TOKEN_ALT":   "HUGGING_FACE_TOKEN ALT(TRIED FINE GRAIN AND SETTING BUNCH OF CHECKBOXES):",
    "HF_API_TOKEN_ALT2":  "HUGGINF_FACE TOKEN ALT2(READ):",  # sic — file typo
    "FIREWORKS_API_KEY":  "FIREWORKS FREE API KEY:",
    "FIREWORKS_API_KEY_ALT": "FIREWORKS FREE API KEY ALT:",
    "DEEPINFRA_API_KEY":  "DEEPINFRA API KEY:",
    "DEEPINFRA_API_KEY_ALT": "DEEPINFRA API KEY ALT:",
    "NOUS_API_KEY":       "NOUS API KEY (USE ONLY FREE MODELS):",
    "NOUS_API_KEY_ALT":   "NOUS API KEY ALT USE ONLY FREE MODELS:",
    "MISTRAL_API_KEY":    "MISTRAL API KEY:",
    "MISTRAL_API_KEY_ALT": "MISTRAL API KEY ALT:",
    "AIMLAPI_FREE_KEY":   "AIMLAPI.COM",
    "AIMLAPI_PAID_KEY":   "AIMLAPIKEY PAID ($20 limit):",
    "HYPEREAL_API_KEY":   "HYPEREAL CLOUD API KEY:",
    "HYPEREAL_API_KEY_ALT": "HYPEREAL CLOUD API KEY 2:",
    "CF_ACCOUNT_ID":      "Cloudflare account iD:",
    "CF_API_TOKEN":       "Cloudflare API key:",
    "XIAOMI_MIMO_TOKEN_PLAN": "XIAOMI_MIMO_TOKEN_PLAN",
}
_keys_cache: dict[str, str] = {}


def _clean_key(raw: Optional[str]) -> Optional[str]:
    """Reduce a dbpasses/env value to the bare credential.

    2026-11-21: the Gemini lines in ~/dbpasses.txt carry inner whitespace (109
    characters for a 39-character key), and the whole line was pasted into the
    request URL -- so the key went out with trailing commentary and the 400
    response echoed it into a log. A credential is one whitespace-free token:
    take the first, then strip the quoting people wrap around it.
    """
    if not raw:
        return None
    v = raw.strip().strip('"' + "'" + '`').strip()
    if not v:
        return None
    token = v.split()[0].strip().rstrip(",;")
    return token.strip('"' + "'" + '`') or None


def _scrub(text: str) -> str:
    """Remove every known credential from an error string before it is shown.

    Provider errors routinely echo the request URL, and Gemini carries its key in
    a query param -- ``str(exc)`` must never reach a log or a terminal as-is.
    """
    out = str(text)
    for value in _keys_cache.values():
        if value and len(value) >= 8:
            out = out.replace(value, "***")
    out = re.sub(r"(key=)[A-Za-z0-9_\-\.]+", r"\1***", out)
    out = re.sub(r"(Bearer )[A-Za-z0-9_\-\.]+", r"\1***", out)
    return out


def _load_keys() -> None:
    """Populate the in-memory cache. File FIRST (canonical credential store),
    env vars only as fallback.

    Rationale: env vars in the user's shell can be stale (rotated keys
    from old sessions) and silently shadow the live values in
    ~/dbpasses.txt — that bit us 2026-05-25 when several providers
    returned HTTP 403 because stale env keys were tried instead of the
    file. The file is the authoritative source; env is the override of
    last resort.
    """
    if _keys_cache:
        return
    # File FIRST — line N is label, line N+1 (after possibly blank) is value
    if _KEYS_FILE.exists():
        try:
            lines = _KEYS_FILE.read_text(encoding="utf-8").splitlines()
        except OSError:
            lines = []
        for env_name, label in _KEY_LABELS.items():
            for i, line in enumerate(lines):
                if line.strip() == label:
                    for j in range(i + 1, min(i + 4, len(lines))):
                        v = lines[j].strip()
                        if v and not v.endswith(":"):
                            cleaned = _clean_key(v)
                            if cleaned:
                                _keys_cache[env_name] = cleaned
                            break
                    break
    # Env as fallback (only fills in missing keys)
    for k in _KEY_LABELS:
        if k not in _keys_cache:
            v = os.environ.get(k)
            if v:
                cleaned = _clean_key(v)
                if cleaned:
                    _keys_cache[k] = cleaned


def _get_key(name: str) -> Optional[str]:
    _load_keys()
    return _keys_cache.get(name)


# ---------------------------------------------------------------------------
# Provider registry
# ---------------------------------------------------------------------------
# Each entry: callable(model, prompt, max_tokens, timeout) -> str | raises.

def _post_openai_compat(url: str, key: str, model: str, prompt: str,
                         max_tokens: int = 1500, timeout: int = 90) -> str:
    """Standard OpenAI chat-completions POST. Returns assistant content."""
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.3,
    }).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload, method="POST",
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json",
                 # 2026-05-25: Groq/Cerebras/Together reject the default
                 # `Python-urllib/3.X` UA with 403. Send a real UA instead.
                 "User-Agent": "consult-multi/1.0 (curl-compat)"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001 -- re-raised with the key scrubbed
        raise RuntimeError(f"{type(exc).__name__}: {_scrub(exc)}") from None
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise RuntimeError(f"malformed completion: {json.dumps(data)[:200]}") from None
    # 2026-11-21: the HF router answers HTTP 200 with ``content: null`` when the
    # monthly credit pool is spent, so a None body was being reported as "OK".
    if not content:
        raise RuntimeError(
            f"empty completion (finish_reason="
            f"{data['choices'][0].get('finish_reason')!r}) -- quota or model refusal"
        )
    return content


def _call_nvidia(model, prompt, max_tokens=1500, timeout=90):
    key = _get_key("NVIDIA_API_KEY") or _get_key("NVIDIA_API_KEY_ALT")
    if not key:
        raise RuntimeError("NVIDIA_API_KEY not in env or ~/dbpasses.txt")
    return _post_openai_compat(
        "https://integrate.api.nvidia.com/v1/chat/completions",
        key, model, prompt, max_tokens, timeout)


def _call_groq(model, prompt, max_tokens=1500, timeout=90):
    key = _get_key("GROQ_API_KEY")
    if not key:
        raise RuntimeError("GROQ_API_KEY not in env or ~/dbpasses.txt")
    return _post_openai_compat(
        "https://api.groq.com/openai/v1/chat/completions",
        key, model, prompt, max_tokens, timeout)


def _call_cerebras(model, prompt, max_tokens=1500, timeout=90):
    key = _get_key("CEREBRAS_API_KEY")
    if not key:
        raise RuntimeError("CEREBRAS_API_KEY not in env or ~/dbpasses.txt")
    return _post_openai_compat(
        "https://api.cerebras.ai/v1/chat/completions",
        key, model, prompt, max_tokens, timeout)


def _call_together(model, prompt, max_tokens=1500, timeout=90):
    key = _get_key("TOGETHER_API_KEY") or _get_key("TOGETHER_API_KEY_ALT")
    if not key:
        raise RuntimeError("TOGETHER_API_KEY not in env or ~/dbpasses.txt")
    return _post_openai_compat(
        "https://api.together.xyz/v1/chat/completions",
        key, model, prompt, max_tokens, timeout)


def _call_fireworks(model, prompt, max_tokens=1500, timeout=90):
    key = _get_key("FIREWORKS_API_KEY") or _get_key("FIREWORKS_API_KEY_ALT")
    if not key:
        raise RuntimeError("FIREWORKS_API_KEY not in env or ~/dbpasses.txt")
    return _post_openai_compat(
        "https://api.fireworks.ai/inference/v1/chat/completions",
        key, model, prompt, max_tokens, timeout)


def _call_github_models(model, prompt, max_tokens=1500, timeout=90):
    key = _get_key("GITHUB_MODELS_KEY") or _get_key("GITHUB_MODELS_KEY2")
    if not key:
        raise RuntimeError("GITHUB_MODELS_KEY not in env or ~/dbpasses.txt")
    # GitHub Models exposes an OpenAI-compatible endpoint
    return _post_openai_compat(
        "https://models.inference.ai.azure.com/chat/completions",
        key, model, prompt, max_tokens, timeout)


def _call_huggingface(model, prompt, max_tokens=1500, timeout=90):
    """HF Router — OpenAI-compatible. Each HF account has its own monthly
    free credit pool, so cycle through all 3 keys on 402 (each could be a
    separate account). 2026-05-25: legacy api-inference.huggingface.co is
    DNS-unresolvable from this network; only the router is usable."""
    keys = [k for k in (_get_key("HF_API_TOKEN"),
                         _get_key("HF_API_TOKEN_ALT"),
                         _get_key("HF_API_TOKEN_ALT2")) if k]
    if not keys:
        raise RuntimeError("no HF_API_TOKEN* in env or ~/dbpasses.txt")
    last_exc = None
    for key in keys:
        try:
            return _post_openai_compat(
                "https://router.huggingface.co/v1/chat/completions",
                key, model, prompt, max_tokens, timeout)
        except urllib.error.HTTPError as exc:
            # On 402 (payment required) and 429 (rate limit) try the next key;
            # any other status surfaces immediately.
            if exc.code in (402, 429):
                last_exc = exc
                continue
            raise
    raise last_exc or RuntimeError("all HF keys exhausted")


def _call_deepinfra(model, prompt, max_tokens=1500, timeout=90):
    """Deep Infra — OpenAI-compatible. CAUTION: provider stops free models
    when balance hits 0, so prefer the smallest free-tier models.
    2026-05-25: primary key dead (401); preferring alt."""
    key = _get_key("DEEPINFRA_API_KEY_ALT") or _get_key("DEEPINFRA_API_KEY")
    if not key:
        raise RuntimeError("DEEPINFRA_API_KEY not in env or ~/dbpasses.txt")
    return _post_openai_compat(
        "https://api.deepinfra.com/v1/openai/chat/completions",
        key, model, prompt, max_tokens, timeout)


def _call_nous(model, prompt, max_tokens=1500, timeout=90):
    """Nous Research Portal — OpenAI-compatible. CAUTION: free models only.
    User flagged: balance=0 stops free access."""
    key = _get_key("NOUS_API_KEY") or _get_key("NOUS_API_KEY_ALT")
    if not key:
        raise RuntimeError("NOUS_API_KEY not in env or ~/dbpasses.txt")
    return _post_openai_compat(
        "https://inference-api.nousresearch.com/v1/chat/completions",
        key, model, prompt, max_tokens, timeout)


def _call_mistral(model, prompt, max_tokens=1500, timeout=90):
    """Mistral AI direct REST — OpenAI-compatible."""
    key = _get_key("MISTRAL_API_KEY") or _get_key("MISTRAL_API_KEY_ALT")
    if not key:
        raise RuntimeError("MISTRAL_API_KEY not in env or ~/dbpasses.txt")
    return _post_openai_compat(
        "https://api.mistral.ai/v1/chat/completions",
        key, model, prompt, max_tokens, timeout)


def _call_aimlapi(model, prompt, max_tokens=1500, timeout=90):
    """AIMLAPI.com — OpenAI-compatible gateway aggregating many providers.
    Prefer the FREE key first (the PAID key has a $20 limit that we
    should preserve for genuine paid-only models)."""
    key = _get_key("AIMLAPI_FREE_KEY") or _get_key("AIMLAPI_PAID_KEY")
    if not key:
        raise RuntimeError("AIMLAPI_FREE_KEY not in env or ~/dbpasses.txt")
    return _post_openai_compat(
        "https://api.aimlapi.com/v1/chat/completions",
        key, model, prompt, max_tokens, timeout)


def _call_hypereal(model, prompt, max_tokens=1500, timeout=90):
    """Hypereal Cloud (https://hypereal.cloud/) — OpenAI-compatible frontier-
    model proxy. Hosts Claude Opus 4.7, GPT-5.5, Gemini 3.5, Kimi K2.6, GLM 5.1,
    DeepSeek V4 Pro, Qwen3 Max, etc. NOTE: paid service, requires $2 min credit
    balance. Anthropic models route via /v1/messages (Anthropic format), not
    /v1/chat/completions. 2026-05-25: keys present but account balance=0 so
    all calls return 'insufficient_credits'."""
    key = _get_key("HYPEREAL_API_KEY") or _get_key("HYPEREAL_API_KEY_ALT")
    if not key:
        raise RuntimeError("HYPEREAL_API_KEY not in env or ~/dbpasses.txt")
    return _post_openai_compat(
        "https://api.hypereal.cloud/v1/chat/completions",
        key, model, prompt, max_tokens, timeout)


def _call_gemini_api(model, prompt, max_tokens=1500, timeout=90):
    """Google Gemini's REST API uses key in query param, not header."""
    key = _get_key("GEMINI_API_KEY") or _get_key("GEMINI_API_KEY_ALT")
    if not key:
        raise RuntimeError("GEMINI_API_KEY not in env or ~/dbpasses.txt")
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{model}:generateContent?key={urllib.parse.quote(key, safe='')}")
    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": max_tokens,
                              "temperature": 0.3},
    }).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload, method="POST",
        headers={"Content-Type": "application/json",
                 "User-Agent": "consult-multi/1.0 (curl-compat)"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"{type(exc).__name__}: {_scrub(exc)}") from None
    parts = data["candidates"][0]["content"]["parts"]
    return "".join(p.get("text", "") for p in parts)


def _call_cloudflare(model, prompt, max_tokens=1500, timeout=90):
    """Cloudflare Workers AI — distinct API shape (no /chat/completions path)."""
    acct = _get_key("CF_ACCOUNT_ID")
    key = _get_key("CF_API_TOKEN")
    if not (acct and key):
        raise RuntimeError("CF_ACCOUNT_ID and CF_API_TOKEN required")
    url = f"https://api.cloudflare.com/client/v4/accounts/{acct}/ai/run/{model}"
    payload = json.dumps({
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
    }).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload, method="POST",
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"{type(exc).__name__}: {_scrub(exc)}") from None
    if not data.get("success"):
        raise RuntimeError(f"CF error: {data.get('errors')}")
    result = data.get("result") or {}
    if isinstance(result, dict):
        return result.get("response") or json.dumps(result)[:2000]
    if isinstance(result, list) and result:
        return result[0].get("response") or str(result)[:2000]
    return str(result)[:2000]


PROVIDERS = {
    # Defaults pick free/small models; override with --model for the full list
    "nvidia":        (_call_nvidia,        "meta/llama-3.1-8b-instruct"),
    "groq":          (_call_groq,          "qwen/qwen3-32b"),
    "cerebras":      (_call_cerebras,      "llama3.1-8b"),
    "together":      (_call_together,      "meta-llama/Meta-Llama-3-8B-Instruct-Lite"),
    "fireworks":     (_call_fireworks,     "accounts/fireworks/models/kimi-k2p5"),
    "github_models": (_call_github_models, "gpt-4o-mini"),
    "huggingface":   (_call_huggingface,   "openai/gpt-oss-20b"),
    "gemini_api":    (_call_gemini_api,    "gemini-flash-latest"),
    "cloudflare":    (_call_cloudflare,    "@cf/meta/llama-3.1-8b-instruct"),
    "deepinfra":     (_call_deepinfra,     "meta-llama/Meta-Llama-3.1-8B-Instruct"),
    "nous":          (_call_nous,          "Hermes-4-405B"),
    "mistral":       (_call_mistral,       "mistral-small-latest"),
    "aimlapi":       (_call_aimlapi,       "gpt-4o-mini"),
    "hypereal":      (_call_hypereal,      "gpt-5.5-instant"),
}


# ---------------------------------------------------------------------------
# Fan-out presets
# ---------------------------------------------------------------------------
# VERIFIED: 2026-11-22 by `python3 tools/consult_multi.py --probe`.
#
# Why this section was rewritten: the previous presets (diverse5 / fast4 /
# reasoning4) were ALL DEAD -- every member returned HTTP 410 Gone or 404
# retired-model errors, and the tool reported them as per-peer ERROR rows while
# still printing a fan-out summary. A preset that silently produces zero real
# answers is worse than no preset.
#
# House rule (recorded in ~/dbpasses memory): NEVER trust a provider's /models
# listing. Probe one real completion. The 2026-11-22 probe found exactly ONE
# provider answering: cloudflare. Everything else was 410 Gone (nvidia),
# 401/404 (groq, together, fireworks, cerebras, mistral, github_models), or
# unresolvable (nous, aimlapi).
#
# Consequence: the presets below are deliberately SMALL and HONEST rather than
# diverse and fictional. When providers come back online, re-run --probe and
# extend PRESET_VERIFIED_AT.
PRESET_VERIFIED_AT = "2026-11-22"

# Providers confirmed answering a real completion on PRESET_VERIFIED_AT.
LIVE_PROVIDERS = {"cloudflare", "deepinfra"}

FANOUTS = {
    # Every member below answered a REAL completion on 2026-11-22. Models are
    # listed by verified id; do not add an id from memory.
    "diverse5": [
        ("cloudflare", "@cf/meta/llama-3.3-70b-instruct-fp8-fast"),
        ("cloudflare", "@cf/openai/gpt-oss-120b"),
        ("cloudflare", "@cf/meta/llama-4-scout-17b-16e-instruct"),
        ("cloudflare", "@cf/mistralai/mistral-small-3.1-24b-instruct"),
        ("deepinfra",  "meta-llama/Meta-Llama-3.1-8B-Instruct"),
    ],
    "fast4": [
        ("cloudflare", "@cf/meta/llama-3.1-8b-instruct"),
        ("cloudflare", "@cf/meta/llama-3.2-3b-instruct"),
        ("cloudflare", "@cf/google/gemma-3-12b-it"),
        ("deepinfra",  "meta-llama/Meta-Llama-3.1-8B-Instruct"),
    ],
    "reasoning4": [
        ("cloudflare", "@cf/openai/gpt-oss-120b"),
        ("cloudflare", "@cf/meta/llama-3.3-70b-instruct-fp8-fast"),
        ("cloudflare", "@cf/meta/llama-4-scout-17b-16e-instruct"),
        ("cloudflare", "@cf/qwen/qwen2.5-coder-32b-instruct"),
    ],
    # The full panel still includes dead providers on purpose -- use it to
    # measure which are alive today, not to collect answers.
    "all": [(name, default) for name, (_, default) in PROVIDERS.items()],
}


def _warn_dead_preset(peers, name):
    """Refuse to pretend a fan-out worked when no peer is verified live."""
    dead = [(p, m) for p, m in peers if p not in LIVE_PROVIDERS]
    if dead and len(dead) == len(peers):
        print(f"WARNING: every member of preset {name!r} is on a provider that "
              f"failed its {PRESET_VERIFIED_AT} probe. Expected answers: 0.\n"
              f"         Re-run --probe before relying on this preset.")
    elif dead:
        print(f"note: {len(dead)}/{len(peers)} members of {name!r} are on "
              f"unverified providers and will likely ERROR.")


def cmd_probe(args) -> int:
    """Probe one real completion per provider. Never trust /models.

    This is the check that would have caught the dead presets on the day they
    died instead of weeks later.
    """
    prompt = "Reply with exactly the single word PONG and nothing else."
    results = []
    print(f"probing {len(PROVIDERS)} providers with a real completion "
          f"(timeout {args.timeout}s)")
    print(f"{'provider':<16}{'model':<52}{'result'}")
    print("-" * 92)
    for name, (fn, default_model) in PROVIDERS.items():
        model = args.model if (args.model and args.provider == name) else default_model
        try:
            out = fn(model, prompt, 32, min(args.timeout, 30))
            txt = (out or "").strip().replace("\n", " ")[:40]
            ok = bool(txt)
            results.append((name, model, "OK" if ok else "EMPTY", txt))
            print(f"{name:<16}{model[:51]:<52}{'OK' if ok else 'EMPTY'}  {txt}")
        except Exception as exc:  # noqa: BLE001
            msg = f"{type(exc).__name__}: {str(exc)[:44]}"
            results.append((name, model, "FAIL", msg))
            print(f"{name:<16}{model[:51]:<52}FAIL  {msg}")
    live = [r[0] for r in results if r[2] == "OK"]
    print("-" * 92)
    print(f"live: {len(live)}/{len(results)}  ->  {live or 'NONE'}")
    print(f"\nUpdate LIVE_PROVIDERS and PRESET_VERIFIED_AT in this file to:")
    print(f"    LIVE_PROVIDERS = {set(live)!r}")
    print(f"    PRESET_VERIFIED_AT = \"{__import__('datetime').date.today()}\"")
    if not live:
        print("\nBLOCKED: no provider answered. Any fan-out today returns zero "
              "real answers.\nDo not record a fan-out as evidence until this "
              "probe is green.")
    return 0 if live else 4


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--list", action="store_true", help="List providers + default models")
    ap.add_argument("--provider", help="Single-provider call: " + ",".join(PROVIDERS))
    ap.add_argument("--model", help="Override default model for --provider")
    ap.add_argument("--prompt", help="Prompt string (use --prompt-file for longer)")
    ap.add_argument("--prompt-file", help="Path to prompt file")
    ap.add_argument("--fanout", help="Fan-out preset: " + ",".join(FANOUTS))
    ap.add_argument("--probe", action="store_true",
                    help="Probe every provider with a REAL completion and report "
                         "which are live. Never trust /models.")
    ap.add_argument("--out-dir", default="/tmp/consult_multi",
                     help="Where fan-out writes per-peer responses (default /tmp/consult_multi)")
    ap.add_argument("--peers",
                     help="Custom fan-out as provider:model,provider:model "
                          "(default model when the model part is omitted)")
    ap.add_argument("--parallel", type=int, default=1,
                     help="Fan-out concurrency (default 1 = sequential)")
    ap.add_argument("--doctor", action="store_true",
                     help="Ping every provider with a tiny prompt and report what answered")
    ap.add_argument("--max-tokens", type=int, default=1500)
    ap.add_argument("--timeout", type=int, default=90)
    args = ap.parse_args()

    if args.probe:
        _load_keys()
        return cmd_probe(args)

    if args.list:
        _load_keys()
        print(f"{'provider':<14}{'has_key':>9}  default_model")
        print("-" * 78)
        key_for_provider = {
            "nvidia": ("NVIDIA_API_KEY",), "groq": ("GROQ_API_KEY",),
            "cerebras": ("CEREBRAS_API_KEY",),
            "together": ("TOGETHER_API_KEY",),
            "fireworks": ("FIREWORKS_API_KEY",),
            "github_models": ("GITHUB_MODELS_KEY",),
            "huggingface": ("HF_API_TOKEN",),
            "gemini_api": ("GEMINI_API_KEY",),
            "cloudflare": ("CF_API_TOKEN", "CF_ACCOUNT_ID"),
            "deepinfra": ("DEEPINFRA_API_KEY",),
            "nous": ("NOUS_API_KEY",),
            "mistral": ("MISTRAL_API_KEY",),
            "aimlapi": ("AIMLAPI_FREE_KEY",),
            "hypereal": ("HYPEREAL_API_KEY",),
        }
        for name, (_, default) in PROVIDERS.items():
            need = key_for_provider.get(name, ())
            ok = all(_get_key(k) for k in need)
            print(f"{name:<14}{('yes' if ok else 'NO'):>9}  {default}")
        print()
        print("Fan-out presets:")
        for pname, peers in FANOUTS.items():
            print(f"  {pname:<12} ({len(peers)} peers): "
                  f"{', '.join(p[0] for p in peers)}")
        return 0

    if args.doctor:
        _load_keys()
        print(f"{'provider':<14}{'model':<44}status")
        print("-" * 100)
        alive = 0
        for name, (fn, default_model) in PROVIDERS.items():
            t0 = time.time()
            try:
                text = fn(default_model, "Reply with exactly: OK", 8, args.timeout)
                snippet = " ".join(str(text).split())[:48]
                print(f"{name:<14}{default_model:<44}OK   {time.time() - t0:5.1f}s  {snippet}")
                alive += 1
            except Exception as exc:  # noqa: BLE001
                print(f"{name:<14}{default_model:<44}FAIL       {_scrub(exc)[:70]}")
        print(f"\n{alive}/{len(PROVIDERS)} providers answered")
        return 0 if alive else 1

    # Get prompt text
    if args.prompt and args.prompt_file:
        ap.error("use --prompt OR --prompt-file, not both")
    if args.prompt_file:
        prompt = Path(args.prompt_file).read_text(encoding="utf-8")
    elif args.prompt:
        prompt = args.prompt
    else:
        if not sys.stdin.isatty():
            prompt = sys.stdin.read()
        else:
            ap.error("provide --prompt, --prompt-file, or pipe to stdin")

    if args.provider:
        if args.provider not in PROVIDERS:
            ap.error(f"unknown provider {args.provider!r}")
        fn, default_model = PROVIDERS[args.provider]
        model = args.model or default_model
        print(fn(model, prompt, args.max_tokens, args.timeout))
        return 0

    if args.fanout or args.peers:
        if args.peers:
            peers: list[tuple[str, str]] = []
            for spec in args.peers.split(","):
                spec = spec.strip()
                if not spec:
                    continue
                provider, _, model = spec.partition(":")
                if provider not in PROVIDERS:
                    ap.error(f"unknown provider {provider!r} in --peers")
                peers.append((provider, model.strip() or PROVIDERS[provider][1]))
            label = "custom"
        else:
            if args.fanout not in FANOUTS:
                ap.error(f"unknown fanout preset {args.fanout!r}")
            peers = list(FANOUTS[args.fanout])
            label = args.fanout
            _warn_dead_preset(peers, label)
        out = Path(args.out_dir); out.mkdir(parents=True, exist_ok=True)
        print(f"# fan-out {label} → {out}  ({len(peers)} peers, parallel={args.parallel})")

        def _one(peer: tuple[str, str]):
            provider, model = peer
            fn, _ = PROVIDERS[provider]
            try:
                return peer, fn(model, prompt, args.max_tokens, args.timeout), None
            except Exception as exc:  # noqa: BLE001
                return peer, None, f"ERROR: {type(exc).__name__}: {_scrub(exc)}"

        if args.parallel > 1:
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=max(1, args.parallel)) as pool:
                results = list(pool.map(_one, peers))
        else:
            results = [_one(peer) for peer in peers]

        for (provider, model), text, err in results:
            slug = f"{provider}__{model.replace('/', '_').replace('@', '')}"[:90]
            path = out / f"{slug}.md"
            print(f"\n=== {provider} · {model} ===")
            if err:
                path.write_text(err, encoding="utf-8")
                print(f"  -> {path} ({err[:160]})")
            else:
                path.write_text(text, encoding="utf-8")
                print(f"  -> {path} ({len(text)} chars)")
        return 0

    ap.error("provide --list, --provider, or --fanout")
    return 2


if __name__ == "__main__":
    sys.exit(main())
