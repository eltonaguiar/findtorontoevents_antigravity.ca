#!/usr/bin/env python3
"""swarm_models.py — canonical free-model registry for the consult swarm.

One place that lists every free LLM endpoint the swarm can fan out to, the
env var holding its key, its OpenAI-compatible base URL, and a default model.
Consult scripts import `available_endpoints()` instead of hardcoding their own
ENDPOINTS list, so adding a provider is a one-line change here.

Key resolution (Windows-aware): a key is looked up in the process environment
first; if absent, the Windows User and Machine registry scopes are read
directly. This matters because a key set with `setx` after a shell started is
NOT in that shell's process env — but every consult script still finds it.

Zero pip deps. Pure stdlib.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class Endpoint:
    label: str
    env_vars: tuple[str, ...]   # first one that resolves wins
    base_url: str               # OpenAI-compatible; /chat/completions appended
    model: str
    notes: str = ""
    enabled: bool = True        # False = registered but not callable (no key path)
    extra_headers: tuple[tuple[str, str], ...] = ()  # provider-specific headers
    tier: str = "smart"         # "smart" = reasoning-grade (verdict consults);
    #                             "fast"  = quick/cheap (breadth, not verdicts)


# ---------------------------------------------------------------------------
# The roster. OpenAI-compatible /chat/completions endpoints only.
# Existing 6 (deepseek/groq/cerebras/xai/openrouter/kimi) + new free providers.
# ---------------------------------------------------------------------------
ENDPOINTS: list[Endpoint] = [
    Endpoint("deepseek", ("DEEPSEEK_API_KEY", "DEEPSEEK_API"),
             "https://api.deepseek.com/v1", "deepseek-reasoner",
             "DeepSeek reasoner — strongest cross-vendor second opinion."),
    Endpoint("groq", ("GROQ_API_KEY",),
             "https://api.groq.com/openai/v1", "llama-3.3-70b-versatile",
             "Groq — fast; also serves Kimi K2 / gpt-oss-120b.", tier="fast"),
    Endpoint("cerebras", ("CEREBRAS_API", "CEREBRAS_API_KEY"),
             "https://api.cerebras.ai/v1", "llama-3.3-70b",
             "Cerebras — 30 RPM / 14.4k RPD free; gpt-oss-120b available.",
             tier="fast"),
    Endpoint("xai-grok", ("XAI_API_KEY",),
             "https://api.x.ai/v1", "grok-3", "xAI Grok."),
    Endpoint("openrouter", ("OPENROUTER", "OPENROUTER_API_KEY"),
             "https://openrouter.ai/api/v1", "deepseek/deepseek-chat",
             "OpenRouter — gateway; many :free models incl. gpt-oss-120b, "
             "Qwen3-Coder-480B, inclusionai/ling-2.6-1t."),
    Endpoint("kimi", ("KIMI_API_KEY", "KIMI_MOONSHOT_APIKEY"),
             "https://api.moonshot.ai/v1", "moonshot-v1-32k", "Moonshot Kimi."),
    # ---- new free providers (2026-05-18) ----
    Endpoint("mistral", ("MISTRA_API_KEY_FREE", "MISTRAL_API_KEY"),
             "https://api.mistral.ai/v1", "mistral-large-latest",
             "Mistral AI free tier. Note env var spelling MISTRA_API_KEY_FREE. "
             "Use codestral-latest for code-heavy tasks."),
    Endpoint("mistral-codestral", ("MISTRA_API_KEY_FREE", "MISTRAL_API_KEY"),
             "https://api.mistral.ai/v1", "codestral-latest",
             "Mistral Codestral — 256K ctx, code-specialised, ~1 RPS/500K TPM.",
             tier="fast"),
    Endpoint("llm7", ("LLM7_API_KEY_FREE", "LLM7_API_KEY"),
             "https://api.llm7.io/v1", "qwen2.5-coder-32b",
             "LLM7.io free — qwen2.5-coder-32b, 131K ctx, 120 RPM with token. "
             "REQUIRES a browser User-Agent header (bot-protection 403 without).",
             extra_headers=(("User-Agent", "Mozilla/5.0"),), tier="fast"),
    # ---- registered, not yet callable ----
    Endpoint("chutes", ("CHUTES_API_KEY_FREE", "CHUTES_API_KEY"),
             "https://llm.chutes.ai/v1", "zai-org/GLM-5-TEE",
             "Chutes.ai — key is valid (/models lists ~14: GLM-5, "
             "DeepSeek-V3.2, Qwen3.5-397B, Kimi-K2.6, Qwen2.5-Coder-32B) but "
             "inference returns 402 Payment Required on every model — the "
             "free key has no inference quota. Add Chutes credits to enable; "
             "flip enabled=True once /chat/completions stops 402-ing.",
             enabled=False, extra_headers=(("User-Agent", "Mozilla/5.0"),)),
    Endpoint("ovh-qwen3-coder", ("OVH_AI_ENDPOINTS_KEY",),
             "https://oai.endpoints.kepler.ai.cloud.ovh.net/v1",
             "Qwen3-Coder-30B-A3B-Instruct",
             "OVHcloud AI Endpoints — Qwen3-Coder-30B, 262K ctx, 2 RPM anon. "
             "GET KEY: OVHcloud manager -> Public Cloud -> AI Endpoints -> "
             "API keys; store as OVH_AI_ENDPOINTS_KEY. Disabled until then.",
             enabled=False, tier="fast"),
]


def _windows_scoped_env(name: str) -> str:
    """Read a Windows User- or Machine-scope env var via the registry.
    Returns '' if not found or not on Windows. Handles keys set with `setx`
    after the current process started."""
    if sys.platform != "win32":
        return ""
    try:
        import winreg
    except ImportError:
        return ""
    for root, sub in (
        (winreg.HKEY_CURRENT_USER, "Environment"),
        (winreg.HKEY_LOCAL_MACHINE,
         r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"),
    ):
        try:
            with winreg.OpenKey(root, sub) as k:
                val, _ = winreg.QueryValueEx(k, name)
                if val:
                    return str(val).strip()
        except OSError:
            continue
    return ""


def resolve_key(env_vars: tuple[str, ...]) -> str:
    """First resolvable key across the given env-var names. Process env first,
    then Windows User/Machine registry scopes."""
    for name in env_vars:
        v = os.environ.get(name, "").strip()
        if v:
            return v
    for name in env_vars:
        v = _windows_scoped_env(name)
        if v:
            return v
    return ""


def available_endpoints() -> list[Endpoint]:
    """Endpoints that are enabled AND have a resolvable API key right now."""
    return [e for e in ENDPOINTS
            if e.enabled and resolve_key(e.env_vars)]


def smart_endpoints() -> list[Endpoint]:
    """Callable reasoning-grade endpoints — for verdict-grade consults."""
    return [e for e in available_endpoints() if e.tier == "smart"]


def build_headers(endpoint: Endpoint, key: str) -> dict[str, str]:
    """Full request header dict for an endpoint — auth + JSON + any
    provider-specific headers (e.g. LLM7's required User-Agent)."""
    h = {"Authorization": "Bearer " + key, "Content-Type": "application/json"}
    h.update(dict(endpoint.extra_headers))
    return h


def main() -> int:
    """CLI: print roster status — which providers are callable."""
    print("Swarm model roster (%d registered):" % len(ENDPOINTS))
    for e in ENDPOINTS:
        key = resolve_key(e.env_vars)
        if not e.enabled:
            state = ("DISABLED (key present, see notes)" if key
                     else "DISABLED (no key)")
        elif key:
            state = "READY (key len%d)" % len(key)
        else:
            state = "NO KEY — set one of: %s" % ", ".join(e.env_vars)
        print("  %-18s %-34s %s" % (e.label, e.model, state))
    ready = available_endpoints()
    print("\n%d/%d endpoints callable right now." % (len(ready), len(ENDPOINTS)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
