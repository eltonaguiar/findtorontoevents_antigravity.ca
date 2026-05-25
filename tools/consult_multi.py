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
import subprocess
import sys
import time
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
}
_keys_cache: dict[str, str] = {}


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
                            _keys_cache[env_name] = v
                            break
                    break
    # Env as fallback (only fills in missing keys)
    for k in _KEY_LABELS:
        if k not in _keys_cache:
            v = os.environ.get(k)
            if v:
                _keys_cache[k] = v.strip()


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
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]


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
           f"{model}:generateContent?key={key}")
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
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
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
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
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
    "hypereal":      (_call_hypereal,      "kimi-k2.6"),
}


# ---------------------------------------------------------------------------
# Fan-out presets
# ---------------------------------------------------------------------------
FANOUTS = {
    # All defaults verified 2026-05-25 with a '1+1?' ping — only known-working
    # free-tier models on accounts that aren't rate-limited.
    "diverse5": [
        ("nvidia",     "moonshotai/kimi-k2.6"),
        ("groq",       "qwen/qwen3-32b"),
        ("cerebras",   "llama3.1-8b"),
        ("together",   "meta-llama/Meta-Llama-3-8B-Instruct-Lite"),
        ("fireworks",  "accounts/fireworks/models/kimi-k2p5"),
    ],
    "fast4": [
        ("groq",       "qwen/qwen3-32b"),
        ("cerebras",   "llama3.1-8b"),
        ("mistral",    "mistral-small-latest"),
        ("github_models", "gpt-4o-mini"),
    ],
    "reasoning4": [
        ("nvidia",     "moonshotai/kimi-k2.6"),
        ("nous",       "Hermes-4-405B"),
        ("fireworks",  "accounts/fireworks/models/kimi-k2p5"),
        ("aimlapi",    "gpt-4o-mini"),
    ],
    # The full panel includes quota-blocked providers — they'll record ERROR
    # entries but the run continues. Use this when you want maximum diversity
    # and don't mind partial misses.
    "all": [(name, default) for name, (_, default) in PROVIDERS.items()],
}


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
    ap.add_argument("--out-dir", default="/tmp/consult_multi",
                     help="Where fan-out writes per-peer responses (default /tmp/consult_multi)")
    ap.add_argument("--max-tokens", type=int, default=1500)
    ap.add_argument("--timeout", type=int, default=90)
    args = ap.parse_args()

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

    if args.fanout:
        if args.fanout not in FANOUTS:
            ap.error(f"unknown fanout preset {args.fanout!r}")
        out = Path(args.out_dir); out.mkdir(parents=True, exist_ok=True)
        print(f"# fan-out {args.fanout} → {out}")
        for provider, model in FANOUTS[args.fanout]:
            fn, _ = PROVIDERS[provider]
            slug = f"{provider}__{model.replace('/', '_').replace('@', '')}"[:90]
            path = out / f"{slug}.md"
            print(f"\n=== {provider} · {model} ===")
            try:
                text = fn(model, prompt, args.max_tokens, args.timeout)
                path.write_text(text, encoding="utf-8")
                print(f"  -> {path} ({len(text)} chars)")
            except Exception as exc:
                err = f"ERROR: {type(exc).__name__}: {exc}"
                path.write_text(err, encoding="utf-8")
                print(f"  -> {path} ({err[:200]})")
            time.sleep(0.5)
        return 0

    ap.error("provide --list, --provider, or --fanout")
    return 2


if __name__ == "__main__":
    sys.exit(main())
