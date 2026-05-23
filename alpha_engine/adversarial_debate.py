"""Adversarial bull/bear debate sidecar for UEPS-style picks.

Inspired by tauricresearch/tradingagents (Apache-2.0): two opposing LLMs
produce independent theses for each pick, then a deterministic synthesizer
emits an adversarial score = bull_conf - bear_conf clamped to [-1, +1].

This module is wired to `tools/run_ueps_pickers.run_screeners` (B9, 2026-05-04)
as a 14-day shadow run. Default-off via env flag `UEPS_ADVERSARIAL_ENABLED=1`.
Stamps `adversarial_score` / `adversarial_keep` on long picks — never filters,
only annotates. Flip default-on after 30-close shadow validates Sharpe improvement
on Wilson-95% lower bound.

Provider-agnostic: every supported provider exposes an OpenAI-compatible
`/chat/completions` endpoint, so we use stdlib urllib + JSON, no SDK deps.

Standard env-var names (lifted from tauricresearch/tradingagents README):
    ANTHROPIC_API_KEY, OPENAI_API_KEY, GOOGLE_API_KEY, XAI_API_KEY,
    DEEPSEEK_API_KEY, DASHSCOPE_API_KEY, ZHIPU_API_KEY, OPENROUTER_API_KEY

Legacy fallbacks (this repo's earlier env names) are honored if the
standard name is absent: CEREBRAS_API, X_AI_KEY, DEEPSEEK_API,
KIMI_API_KEY, GROK_SUPER, OLLAMA_CLOUD_KEY.
"""
from __future__ import annotations

import json
import logging
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

ENV_FLAG = "UEPS_ADVERSARIAL_ENABLED"
DEFAULT_BULL_PROVIDER = os.environ.get("UEPS_ADVERSARIAL_BULL_PROVIDER", "deepseek").lower()
DEFAULT_BEAR_PROVIDER = os.environ.get("UEPS_ADVERSARIAL_BEAR_PROVIDER", "xai").lower()
HTTP_TIMEOUT_SEC = float(os.environ.get("UEPS_ADVERSARIAL_TIMEOUT", "20"))

# Decision threshold: keep pick if bull - bear margin exceeds this. Operator
# overridable via env; documented in the wiring-plan PR body.
KEEP_MARGIN = float(os.environ.get("UEPS_ADVERSARIAL_KEEP_MARGIN", "0.15"))


# ────────────────────────────────────────────────────────────────────────
# Provider registry
# ────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Provider:
    name: str
    base_url: str
    default_model: str
    standard_env: str
    legacy_envs: tuple[str, ...] = ()


_PROVIDERS: dict[str, Provider] = {
    "deepseek": Provider(
        name="deepseek",
        base_url="https://api.deepseek.com/v1/chat/completions",
        default_model="deepseek-chat",
        standard_env="DEEPSEEK_API_KEY",
        legacy_envs=("DEEPSEEK_API",),
    ),
    "xai": Provider(
        name="xai",
        base_url="https://api.x.ai/v1/chat/completions",
        default_model="grok-2-latest",
        standard_env="XAI_API_KEY",
        legacy_envs=("X_AI_KEY", "GROK_SUPER", "X_AI_SECONDOP"),
    ),
    "anthropic": Provider(
        name="anthropic",
        # Anthropic uses /v1/messages not /v1/chat/completions; we route
        # through OpenRouter by default for OpenAI-compat. Direct anthropic
        # path requires a different request shape — left out of v1.
        base_url="https://openrouter.ai/api/v1/chat/completions",
        default_model="anthropic/claude-sonnet-4.5",
        standard_env="OPENROUTER_API_KEY",
        legacy_envs=("ANTHROPIC_API_KEY",),
    ),
    "openai": Provider(
        name="openai",
        base_url="https://api.openai.com/v1/chat/completions",
        default_model="gpt-4o-mini",
        standard_env="OPENAI_API_KEY",
    ),
    "openrouter": Provider(
        name="openrouter",
        base_url="https://openrouter.ai/api/v1/chat/completions",
        default_model="anthropic/claude-sonnet-4.5",
        standard_env="OPENROUTER_API_KEY",
    ),
    "kimi": Provider(
        name="kimi",
        base_url="https://api.moonshot.ai/v1/chat/completions",
        default_model="moonshot-v1-8k",
        standard_env="MOONSHOT_API_KEY",
        legacy_envs=("KIMI_API_KEY",),
    ),
    "cerebras": Provider(
        name="cerebras",
        base_url="https://api.cerebras.ai/v1/chat/completions",
        default_model="qwen-3-235b-a22b-instruct-2507",
        standard_env="CEREBRAS_API_KEY",
        legacy_envs=("CEREBRAS_API",),
    ),
    "ollama_cloud": Provider(
        name="ollama_cloud",
        base_url="https://ollama.com/api/chat",
        default_model="qwen3-coder:480b",
        standard_env="OLLAMA_CLOUD_KEY",
    ),
}


def _resolve_api_key(provider: Provider) -> str | None:
    val = os.environ.get(provider.standard_env)
    if val:
        return val.strip() or None
    for legacy in provider.legacy_envs:
        val = os.environ.get(legacy)
        if val:
            return val.strip() or None
    return None


# ────────────────────────────────────────────────────────────────────────
# Prompt templates (kept short to keep token cost bounded)
# ────────────────────────────────────────────────────────────────────────

BULL_SYSTEM = (
    "You are a long-only equity analyst arguing the BULL case for a single "
    "stock pick. Be specific, cite catalysts, and assign a confidence in "
    "[0.0, 1.0]. Reply ONLY in JSON: "
    '{"thesis": "<<= 2 sentences", "confidence": <float>}'
)

BEAR_SYSTEM = (
    "You are a short-biased equity analyst arguing the BEAR case for a single "
    "stock pick. Be specific, cite risks, and assign a confidence in "
    "[0.0, 1.0]. Reply ONLY in JSON: "
    '{"thesis": "<<= 2 sentences", "confidence": <float>}'
)


def _user_prompt(pick: dict) -> str:
    fields = (
        "symbol", "asset_class", "direction", "entry_price",
        "take_profit", "stop_loss", "score", "confidence",
        "trust_score", "catalyst", "thesis", "strategy",
    )
    payload = {k: pick.get(k) for k in fields if pick.get(k) is not None}
    return f"Pick under review:\n{json.dumps(payload, separators=(',', ':'))}"


# ────────────────────────────────────────────────────────────────────────
# HTTP transport
# ────────────────────────────────────────────────────────────────────────

class DebateError(RuntimeError):
    """Raised when a debate call fails after retries — caller decides fallback."""


def _post_chat(provider_name: str, system: str, user: str, *, model: str | None = None,
               max_tokens: int = 250, http_post=None) -> dict:
    """Call an OpenAI-compatible /chat/completions endpoint.

    `http_post` is injectable so tests can stub the network without monkeypatching urllib.
    """
    provider = _PROVIDERS.get(provider_name)
    if provider is None:
        raise DebateError(f"unknown provider {provider_name!r}")
    api_key = _resolve_api_key(provider)
    if not api_key:
        raise DebateError(
            f"no API key for provider {provider_name!r}; "
            f"set {provider.standard_env} (or one of {provider.legacy_envs})"
        )
    body = {
        "model": model or provider.default_model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.2,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    raw = json.dumps(body).encode("utf-8")
    poster = http_post or _stdlib_post
    return poster(provider.base_url, headers, raw)


def _stdlib_post(url: str, headers: dict, body: bytes) -> dict:
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_SEC) as resp:
            text = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        raise DebateError(f"http {e.code} from {url}: {e.read()[:200]!r}") from e
    except urllib.error.URLError as e:
        raise DebateError(f"network error to {url}: {e.reason!r}") from e
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise DebateError(f"non-JSON response from {url}: {text[:200]!r}") from e


def _extract_content(api_response: dict) -> str:
    """Pull the assistant text out of an OpenAI-compatible response."""
    try:
        choices = api_response.get("choices") or []
        if not choices:
            raise DebateError(f"no choices in response: {api_response!r}")
        msg = choices[0].get("message") or {}
        content = msg.get("content") or ""
        if not content:
            raise DebateError(f"empty content in response: {api_response!r}")
        return content
    except (AttributeError, IndexError, TypeError) as e:
        raise DebateError(f"malformed response: {api_response!r}") from e


_JSON_BLOB_RE = re.compile(r"\{[^{}]*\}", re.DOTALL)


def _parse_thesis_json(text: str) -> tuple[str, float]:
    """Tolerant JSON parser: models often wrap JSON in markdown fences or prose."""
    candidates: list[str] = []
    # Prefer anything inside the outermost {...} braces in case of fences.
    matches = _JSON_BLOB_RE.findall(text)
    candidates.extend(matches)
    candidates.append(text.strip().strip("`"))
    for cand in candidates:
        try:
            obj = json.loads(cand)
            thesis = str(obj.get("thesis", "")).strip()
            conf_raw = obj.get("confidence", 0.0)
            try:
                conf = float(conf_raw)
            except (TypeError, ValueError):
                conf = 0.0
            conf = max(0.0, min(1.0, conf))
            if thesis:
                return thesis, conf
        except json.JSONDecodeError:
            continue
    return text.strip()[:280], 0.0


# ────────────────────────────────────────────────────────────────────────
# Public API
# ────────────────────────────────────────────────────────────────────────

def is_enabled() -> bool:
    return os.environ.get(ENV_FLAG, "0").strip().lower() in ("1", "true", "yes", "on")


def bull_thesis(pick: dict, *, provider: str | None = None, http_post=None) -> tuple[str, float]:
    resp = _post_chat(
        provider or DEFAULT_BULL_PROVIDER,
        BULL_SYSTEM,
        _user_prompt(pick),
        http_post=http_post,
    )
    return _parse_thesis_json(_extract_content(resp))


def bear_thesis(pick: dict, *, provider: str | None = None, http_post=None) -> tuple[str, float]:
    resp = _post_chat(
        provider or DEFAULT_BEAR_PROVIDER,
        BEAR_SYSTEM,
        _user_prompt(pick),
        http_post=http_post,
    )
    return _parse_thesis_json(_extract_content(resp))


def score_pick(pick: dict, *, http_post=None) -> dict[str, Any]:
    """Run the bull/bear pair on a single pick and return the score block.

    Always returns a dict (never raises into the caller). On provider failure
    the failed side gets confidence 0.0 with the error text in `_error_*`.
    """
    out: dict[str, Any] = {
        "bull_thesis": "",
        "bull_confidence": 0.0,
        "bear_thesis": "",
        "bear_confidence": 0.0,
        "adversarial_score": 0.0,
        "adversarial_keep": False,
    }
    try:
        b_text, b_conf = bull_thesis(pick, http_post=http_post)
        out["bull_thesis"] = b_text
        out["bull_confidence"] = b_conf
    except DebateError as e:
        out["_error_bull"] = str(e)
        logger.warning("[adversarial] bull failed for %s: %s", pick.get("symbol"), e)

    try:
        s_text, s_conf = bear_thesis(pick, http_post=http_post)
        out["bear_thesis"] = s_text
        out["bear_confidence"] = s_conf
    except DebateError as e:
        out["_error_bear"] = str(e)
        logger.warning("[adversarial] bear failed for %s: %s", pick.get("symbol"), e)

    margin = out["bull_confidence"] - out["bear_confidence"]
    # Clamp to [-1, 1] for downstream sort ergonomics.
    out["adversarial_score"] = max(-1.0, min(1.0, margin))
    both_answered = "_error_bull" not in out and "_error_bear" not in out
    out["adversarial_keep"] = bool(both_answered and margin >= KEEP_MARGIN)
    return out


def apply_to_picks(picks, *, http_post=None):
    """Mutate-in-place + return: stamp adversarial fields on every pick.

    Hard no-op when the env flag is OFF — picks are returned unchanged so this
    is safe to drop into a hot path before flipping default-on. If `picks` is
    already a list, the same reference is returned (mutation in-place).
    """
    picks_list = picks if isinstance(picks, list) else list(picks)
    if not is_enabled():
        return picks_list
    for pick in picks_list:
        try:
            score_block = score_pick(pick, http_post=http_post)
            pick.update(score_block)
        except Exception:  # noqa: BLE001 — sidecar must never break the host
            logger.exception("[adversarial] unexpected failure on pick %s", pick.get("symbol"))
    return picks_list


__all__ = [
    "ENV_FLAG",
    "KEEP_MARGIN",
    "DebateError",
    "is_enabled",
    "bull_thesis",
    "bear_thesis",
    "score_pick",
    "apply_to_picks",
]
