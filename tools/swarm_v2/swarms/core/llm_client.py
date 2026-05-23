"""Real LLM client for swarm workers.

Self-contained, OpenAI-compatible multi-provider client. Auto-detects an
available provider from environment-variable API keys. Falls back to the
keyless Pollinations endpoint, and finally to ``None`` (callers then use
their deterministic template fallback).

Usage
-----
    client = LLMClient()              # auto-detect best provider
    if client.available:
        text = client.complete("Write a haiku", system="You are terse.")

CLI
---
    python -m swarms.core.llm_client --validate   # probe every key
"""

from __future__ import annotations

import json
import logging
import os
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) swarm-v2/2.0"

# ── Provider registry ───────────────────────────────────────────────
# All endpoints are OpenAI chat-completions compatible. ``token_param``
# distinguishes Cerebras (max_completion_tokens) from the rest.


@dataclass(frozen=True)
class Provider:
    name: str
    url: str
    model: str
    key_envs: tuple[str, ...]
    token_param: str = "max_tokens"
    keyless: bool = False  # True = no API key required (e.g. LLM7.io)


# Order = auto-detection preference. Providers verified working against
# this environment (2026-05-15) are listed first; xai/inception are kept
# for forward-compat but their keys currently fail (invalid key / 403).
PROVIDERS: tuple[Provider, ...] = (
    Provider(
        "deepseek",
        "https://api.deepseek.com/chat/completions",
        "deepseek-chat",
        ("DEEPSEEK_API", "DEEPSEEK_API_KEY"),
    ),
    Provider(
        "groq",
        "https://api.groq.com/openai/v1/chat/completions",
        "llama-3.3-70b-versatile",
        ("GROQ_KEY", "GROQ_API_KEY"),
    ),
    Provider(
        "gemini",
        "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        "gemini-2.5-flash",
        ("GEMINI_FREE_KEY", "GEMINI_API_KEY"),
    ),
    Provider(
        "cerebras",
        "https://api.cerebras.ai/v1/chat/completions",
        "llama3.1-8b",
        ("CEREBRAS_API", "CEREBRAS_API_KEY", "CEREBRAS_API_KEY_PAID", "CEREBRAS_API_KEY_FREE"),
        token_param="max_completion_tokens",
    ),
    Provider(
        "openrouter",
        "https://openrouter.ai/api/v1/chat/completions",
        "openai/gpt-4o-mini",
        ("OPENROUTER_API_KEY", "OPENROUTER"),
    ),
    Provider(
        "openrouter-free",
        "https://openrouter.ai/api/v1/chat/completions",
        "meta-llama/llama-3.3-70b-instruct:free",
        ("OPENROUTER_FREE_KEY",),
    ),
    Provider(
        "together",
        "https://api.together.xyz/v1/chat/completions",
        "meta-llama/Llama-3.3-70B-Instruct-Turbo",
        ("TOGETHER_API_KEY", "TOGETHER_API"),
    ),
    Provider(
        "kilo",
        "https://api.kilo.ai/api/gateway/chat/completions",
        "kilo-auto/free",
        ("KILO_API", "KILO_API_KEY"),
    ),
    Provider(
        "ollama",
        "https://ollama.com/v1/chat/completions",
        "kimi-k2.6",
        ("OLLAMA_CLOUD_KEY", "OLLAMA_API_KEY"),
    ),
    Provider(
        "xai",
        "https://api.x.ai/v1/chat/completions",
        "grok-3-latest",
        ("X_AI_KEY", "XAI_API_KEY", "X_AI", "GROK_SUPER", "GROK_API_KEY"),
    ),
    Provider(
        "inception",
        "https://api.inceptionlabs.ai/v1/chat/completions",
        "mercury-2",
        ("INCEPTION_AI_KEY", "INCEPTION_API_KEY"),
    ),
    Provider(
        "nous",
        "https://inference-gateway.nousresearch.com/v1/chat/completions",
        "hermes-3-llama-3.1-70b",
        ("NOUS_API_KEY", "NOUS_API"),
    ),
    # Keyless fallback — listed last so any keyed provider wins auto-detection.
    # LLM7.io is OpenAI-compatible and needs no API key (anonymous tier:
    # ~8000-char input cap). Used only when no keyed provider is configured.
    Provider(
        "llm7",
        "https://api.llm7.io/v1/chat/completions",
        "gpt-oss-20b",
        (),
        keyless=True,
    ),
)

# Provider order = preference order for auto-detection.
_PROVIDER_BY_NAME = {p.name: p for p in PROVIDERS}


def _resolve_key(provider: Provider) -> Optional[str]:
    """Return the first non-empty env value among *provider.key_envs*."""
    for env in provider.key_envs:
        val = os.environ.get(env)
        if val:
            return val
    return None


def detect_providers() -> list[str]:
    """Return names of usable providers: those with an API key, plus any
    keyless provider (which is always usable)."""
    return [p.name for p in PROVIDERS if p.keyless or _resolve_key(p)]


class LLMClient:
    """OpenAI-compatible chat client with automatic provider selection.

    Parameters
    ----------
    provider :
        Explicit provider name. When ``None`` the first provider with a
        configured key (in :data:`PROVIDERS` order) is used.
    model :
        Optional model override for the selected provider.
    timeout :
        Per-request timeout in seconds.
    """

    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 60.0,
    ) -> None:
        self.timeout = timeout
        self._provider: Optional[Provider] = None
        self._key: Optional[str] = None
        self._model: Optional[str] = model

        if provider is not None:
            p = _PROVIDER_BY_NAME.get(provider)
            if p is None:
                raise ValueError(f"Unknown provider '{provider}'")
            self._provider = p
            self._key = _resolve_key(p)
        else:
            # Prefer a keyed provider; fall back to the first keyless one.
            keyless_fallback: Optional[Provider] = None
            for p in PROVIDERS:
                if p.keyless and keyless_fallback is None:
                    keyless_fallback = p
                    continue
                key = _resolve_key(p)
                if key:
                    self._provider = p
                    self._key = key
                    break
            if self._provider is None and keyless_fallback is not None:
                self._provider = keyless_fallback
                self._key = None

        if self._provider is not None:
            logger.info(
                "LLMClient: using provider '%s' (model %s)",
                self._provider.name,
                self._model or self._provider.model,
            )
        else:
            logger.warning(
                "LLMClient: no API key found — client unavailable, "
                "workers will use deterministic template fallback."
            )

    # -- properties ------------------------------------------------------

    @property
    def available(self) -> bool:
        """True when a usable provider is configured — a keyed provider with
        its key, or a keyless provider (no key needed)."""
        if self._provider is None:
            return False
        return self._provider.keyless or bool(self._key)

    @property
    def provider_name(self) -> Optional[str]:
        return self._provider.name if self._provider else None

    @property
    def model(self) -> Optional[str]:
        if self._provider is None:
            return None
        return self._model or self._provider.model

    # -- completion ------------------------------------------------------

    def complete(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 4000,
        temperature: float = 0.2,
    ) -> Optional[str]:
        """Run a chat completion. Returns text, or ``None`` on any failure.

        Returning ``None`` rather than raising lets callers fall back to a
        deterministic path without special-casing network errors.
        """
        if not self.available:
            return None

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        body = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            self._provider.token_param: max_tokens,
        }
        data = json.dumps(body).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            # Some providers (Cerebras, Groq, LLM7) sit behind Cloudflare and
            # reject the default urllib User-Agent with HTTP 403/1010.
            "User-Agent": _USER_AGENT,
        }
        # Keyless providers (LLM7.io) must NOT send an Authorization header —
        # a "Bearer None" string would be rejected.
        if self._key:
            headers["Authorization"] = f"Bearer {self._key}"
        req = urllib.request.Request(
            self._provider.url,
            data=data,
            method="POST",
            headers=headers,
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            message = payload["choices"][0]["message"]
            # Reasoning models (e.g. Cerebras gpt-oss) may return the answer
            # under reasoning_content with an empty/absent content field.
            content = message.get("content") or message.get("reasoning_content")
            if not content:
                raise KeyError("content")
            return content
        except (urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
            logger.warning(
                "LLMClient[%s]: request failed: %s", self.provider_name, exc
            )
            return None
        except (KeyError, IndexError, ValueError, json.JSONDecodeError) as exc:
            logger.warning(
                "LLMClient[%s]: malformed response: %s", self.provider_name, exc
            )
            return None


# ── Key validation CLI ──────────────────────────────────────────────


def validate_all() -> dict[str, str]:
    """Probe every provider with a configured key. Returns name -> status."""
    results: dict[str, str] = {}
    for name in detect_providers():
        client = LLMClient(provider=name)
        reply = client.complete("Reply with the single word: OK", max_tokens=8)
        if reply is None:
            results[name] = "FAIL (no response / network error)"
        elif "OK" in reply.upper():
            results[name] = "VALID"
        else:
            results[name] = f"RESPONDED ('{reply.strip()[:40]}')"
    return results


def _main(argv: list[str]) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    if "--validate" in argv:
        detected = detect_providers()
        if not detected:
            print("No provider API keys found in environment.")
            return 1
        print(f"Detected keyed providers: {', '.join(detected)}\n")
        for name, status in validate_all().items():
            print(f"  {name:12s} {status}")
        return 0
    print(__doc__)
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
