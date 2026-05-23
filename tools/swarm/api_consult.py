#!/usr/bin/env python3
"""Direct-API consultant for the swarm. Bypasses tools/consult_*.py
(those are widely used by other peer agents and have been reverted by
linters in the past — keep them stable; this module owns the swarm path).

Supports: deepseek, cerebras, xai, inception, ollama_cloud, ollama_local, openrouter, nous.

Usage:
    python tools/swarm/api_consult.py --provider deepseek --prompt-file p.md
    cat p.md | python tools/swarm/api_consult.py --provider xai -

Reads prompt from positional arg (path or `-` for stdin) or via
--prompt-file. Writes response text to stdout (utf-8) and exits 0.
Errors go to stderr; exit non-zero.

Env keys:
    DEEPSEEK_API / DEEPSEEK_API_KEY
    CEREBRAS_API / CEREBRAS_API_KEY
    X_AI_KEY / XAI_API_KEY / X_AI / GROK_SUPER
    INCEPTION_AI_KEY / INCEPTION_API_KEY
    OLLAMA_CLOUD_KEY (informational only — local `ollama` CLI does the call)
    OLLAMA_LOCAL_MODEL / OLLAMA_MODEL (optional; keyless local ollama)
    OPENROUTER (OpenAI-compat gateway, 200+ models from many vendors)

Model overrides: DEEPSEEK_MODEL, CEREBRAS_MODEL, XAI_MODEL, INCEPTION_MODEL,
                 OLLAMA_CLOUD_MODEL, OLLAMA_LOCAL_MODEL, OPENROUTER_MODEL.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

# NOTE: Do NOT import from _config_shared.py here — it has the wrong pollinations
# URL (/openai instead of /v1/chat/completions) and missing model_param.
# This module owns its own PROVIDERS dict with the correct config.

PROVIDERS: dict[str, dict] = {
    "deepseek": {
        "url": "https://api.deepseek.com/chat/completions",
        "model": "deepseek-chat",
        "key_envs": ("DEEPSEEK_API", "DEEPSEEK_API_KEY"),
        "max_tokens_field": "max_tokens",
        "max_tokens": 4000,
    },
    "xai": {
        "url": "https://api.x.ai/v1/chat/completions",
        "model": "grok-3-latest",
        "key_envs": ("X_AI_KEY", "XAI_API_KEY", "X_AI", "GROK_SUPER", "GROK_API_KEY", "GROK_API_KEY_PAID"),
        "max_tokens_field": "max_tokens",
        "max_tokens": 4000,
    },
    "inception": {
        "url": "https://api.inceptionlabs.ai/v1/chat/completions",
        "model": "mercury-2",
        "key_envs": ("INCEPTION_AI_KEY", "INCEPTION_API_KEY"),
        "max_tokens_field": "max_tokens",
        "max_tokens": 4000,
    },
    "openrouter": {
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "model": "openai/gpt-4o-mini",
        "key_envs": ("OPENROUTER_API_KEY", "OPENROUTER", "OPENROUTER_API_KEY_PAID", "OPENROUTER_API_KEY_ALT"),
        "max_tokens_field": "max_tokens",
        "max_tokens": 4000,
    },
    "groq": {
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "model": "llama-3.3-70b-versatile",
        "key_envs": ("GROQ_KEY", "GROQ_API_KEY", "GROQ_API_KEY_PAID"),
        "max_tokens_field": "max_tokens",
        "max_tokens": 4000,
    },
    "huggingface": {
        "url": "https://router.huggingface.co/v1/chat/completions",
        "model": "meta-llama/Llama-3.3-70B-Instruct",
        "key_envs": ("HUGGINGFACE_API", "HF_TOKEN", "HUGGINGFACE_API_KEY", "HUGGINGFACE_API_KEY_PAID", "HUGGING_FACE_TOKEN"),
        "max_tokens_field": "max_tokens",
        "max_tokens": 4000,
    },
    "gemini": {
        "url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        "model": "gemini-2.5-flash-preview-05-20",
        "key_envs": ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GEMINI_API_KEY_PAID"),
        "max_tokens_field": "max_tokens",
        "max_tokens": 4000,
    },
    "github_models": {
        "url": "https://models.inference.ai.azure.com/chat/completions",
        "model": "gpt-4o-mini",
        "key_envs": ("GITHUB_TOKEN", "GH_TOKEN", "GITHUB_TOKEN_PAID"),
        "max_tokens_field": "max_tokens",
        "max_tokens": 4000,
    },
    # Pollinations AI — genuinely zero-key OpenAI-compatible endpoint.
    # Routes to available open-source models without any authentication.
    # Useful as a true last-resort fallback when all keys are exhausted.
    # Model is passed as query param ?model=<name> (e.g. ?model=nvidia/nemotron-3-nano).
    # The request body uses "model": "openai" (pollinations' internal routing token).
    "pollinations": {
        "url": "https://text.pollinations.ai/v1/chat/completions",
        "model": "openai",
        "key_envs": (),  # no key required
        "max_tokens_field": "max_tokens",
        "max_tokens": 4000,
        "model_param": "model",   # query param name for model override
    },
    "cerebras": {
        "url": "https://api.cerebras.ai/v1/chat/completions",
        "model": "gpt-oss-120b",
        "key_envs": ("CEREBRAS_API_KEY", "CEREBRAS_API", "CEREBRAS_API_KEY_PAID",
                     "CEREBRAS_API_KEY_FREE", "CERBRAS_FREE_ITHINK"),
        "max_tokens_field": "max_completion_tokens",
        "max_tokens": 4000,
    },
    "nous": {
        "url": "https://inference-api.nousresearch.com/v1/chat/completions",
        "model": "Hermes-4-70B",
        "key_envs": ("NOUS_API_KEY", "NOUS_PORTAL_KEY", "NOUS_API_KEY_PAID"),
        "max_tokens_field": "max_tokens",
        "max_tokens": 4000,
    },
    # OFOX AI — OpenAI-compatible gateway; free model: z-ai/glm-4.7-flash:free
    # Key env: OFOX_AI_KEY (set via: setx OFOX_AI_KEY "..." in admin CMD)
    # Model override: OFOX_MODEL env var
    "ofox": {
        "url": "https://api.ofox.ai/v1/chat/completions",
        "model": "z-ai/glm-4.7-flash:free",
        "key_envs": ("OFOX_AI_KEY", "OFOX_API_KEY"),
        "max_tokens_field": "max_tokens",
        "max_tokens": 4000,
    },
}

# Per-provider sampling defaults. Each call_* function accepts an optional
# `sampling: dict | None` kwarg that merges over these defaults (caller
# values win on key collision). Provider-specific quirks:
#   - cerebras   : uses `max_completion_tokens`, NOT `max_tokens`.
#   - ollama_cloud / ollama_local: pass `num_predict` via OLLAMA_NUM_PREDICT;
#                   `max_tokens` is also accepted as an alias and converted.
# Env-level overrides (read at call time, lowest precedence):
#   <ENGINE>_TEMPERATURE / <ENGINE>_MAX_TOKENS / <ENGINE>_TOP_P
SAMPLING_DEFAULTS: dict[str, dict] = {
    "deepseek":     {"temperature": 0.2, "max_tokens": 4000, "top_p": 1.0},
    "xai":          {"temperature": 0.2, "max_tokens": 4000, "top_p": 1.0},
    "inception":    {"temperature": 0.2, "max_tokens": 4000, "top_p": 1.0},
    "cerebras":     {"temperature": 0.2, "max_completion_tokens": 4000, "top_p": 1.0},
    "ollama_cloud": {"temperature": 0.2, "num_predict": 4000, "top_p": 1.0},
    "ollama_local": {"temperature": 0.2, "num_predict": 2500, "top_p": 1.0},
    "openrouter":   {"temperature": 0.2, "max_tokens": 4000, "top_p": 1.0},
    "groq":         {"temperature": 0.2, "max_tokens": 4000, "top_p": 1.0},
    "huggingface":  {"temperature": 0.2, "max_tokens": 4000, "top_p": 1.0},
    "gemini":       {"temperature": 0.2, "max_tokens": 4000, "top_p": 1.0},
    "github_models":{"temperature": 0.2, "max_tokens": 4000, "top_p": 1.0},
    "pollinations": {"temperature": 0.2, "max_tokens": 4000, "top_p": 1.0},
    "nous":         {"temperature": 0.2, "max_tokens": 4000, "top_p": 1.0},
    "ofox":         {"temperature": 0.2, "max_tokens": 4000, "top_p": 1.0},
}


def _resolve_sampling(provider: str, override: dict | None) -> dict:
    """Merge defaults <- env <- explicit override into a single sampling dict.

    Env keys read: <PROVIDER>_TEMPERATURE, <PROVIDER>_MAX_TOKENS, <PROVIDER>_TOP_P.
    `max_tokens` from env / override is auto-mapped to the provider-correct
    field name (cerebras: max_completion_tokens; ollama_cloud: num_predict).
    """
    base = dict(SAMPLING_DEFAULTS.get(provider, {}))
    # Env overrides.
    env_prefix = provider.upper()
    env_temp = os.environ.get(f"{env_prefix}_TEMPERATURE")
    env_max = os.environ.get(f"{env_prefix}_MAX_TOKENS")
    env_top_p = os.environ.get(f"{env_prefix}_TOP_P")
    if env_temp:
        try:
            base["temperature"] = float(env_temp)
        except ValueError:
            pass
    if env_max:
        try:
            mt = int(env_max)
            if provider == "cerebras":
                base["max_completion_tokens"] = mt
            elif provider in ("ollama_cloud", "ollama_local"):
                base["num_predict"] = mt
            else:
                base["max_tokens"] = mt
        except ValueError:
            pass
    if env_top_p:
        try:
            base["top_p"] = float(env_top_p)
        except ValueError:
            pass
    # Explicit override wins.
    if override:
        for k, v in override.items():
            if v is None:
                continue
            # Map common alias to provider-correct name.
            if k == "max_tokens" and provider == "cerebras":
                base["max_completion_tokens"] = v
            elif k == "max_tokens" and provider in ("ollama_cloud", "ollama_local"):
                base["num_predict"] = v
            else:
                base[k] = v
    return base


def _sanitize_for_log(text: str) -> str:
    """Strip API keys, tokens, and other secrets before logging.

    2026-05-05 fix: prevents API keys from leaking to stderr / logs.
    """
    import re
    patterns = [
        r'sk-[a-zA-Z0-9]{32,96}',
        r'csk-[a-zA-Z0-9]{40,60}',
        r'xai-[a-zA-Z0-9]{50,70}',
        r'ghp_[a-zA-Z0-9]{36,}',
        r'gho_[a-zA-Z0-9]{36,}',
        r'ghu_[a-zA-Z0-9]{36,}',
        r'ghs_[a-zA-Z0-9]{36,}',
        r'ghr_[a-zA-Z0-9]{36,}',
        r'Bearer\s+[a-zA-Z0-9\-_]{20,}',
        r'key["\s:=]+[a-zA-Z0-9\-_]{32,}',
        r'"api_key"\s*:\s*"[^"]{20,}"',
    ]
    for p in patterns:
        text = re.sub(p, '[REDACTED]', text, flags=re.IGNORECASE)
    return text


def _read_prompt(path: str | None) -> str:
    if not path or path == "-":
        return sys.stdin.read()
    return Path(path).read_text(encoding="utf-8")


def _resolve_key(envs: tuple[str, ...]) -> str | None:
    for n in envs:
        v = os.environ.get(n)
        if v:
            return v
    return None


# HTTP safety defaults (2026-05-05 fix per swarm review).
# Per-request timeout prevents individual HTTP calls from hanging indefinitely.
# Deadline enforcement ensures retries don't exceed an overall budget.
DEFAULT_HTTP_TIMEOUT = 60      # seconds per individual request attempt
DEFAULT_MAX_TOTAL_DURATION = 180  # seconds total across all retry attempts


def _post(url: str, body: dict, key: str | None = None, timeout: int = 180,
          extra_headers: dict | None = None,
          *, _deadline: float | None = None) -> tuple[dict, int]:
    """POST a JSON body with exponential-backoff retry on 429 / 5xx.

    FIX 2026-05-05: added `_deadline` parameter for overall call-budget
    enforcement. If the cumulative retry time would exceed the deadline,
    remaining attempts are skipped to prevent runaway total duration.
    Previous code only enforced per-request timeout (300s subprocess),
    not overall HTTP call budget — multiple retries could exceed intended
    time limits. See DEFAULT_MAX_TOTAL_DURATION.

    Returns (parsed-response, http-status).
    Raises urllib.error.HTTPError on non-retryable errors (4xx except 429);
    caller can read e.code for status.

    `extra_headers` lets a provider attach non-auth headers (e.g. OpenRouter's
    HTTP-Referer + X-Title etiquette headers used for rate-limit attribution
    and leaderboard credit). Authorization + Content-Type always win on
    collision. If `key` is None, no Authorization header is sent (for
    genuinely keyless providers like Pollinations).

    Retry policy (2026-05-05 fix per Kimi's swarm review):
      - 429 / 500 / 502 / 503 / 504: retry up to 3 times with exponential backoff
        (base=1.5s, ±20% jitter) starting at 1s, max 30s between attempts.
      - Other 4xx: fail immediately (client error, no point retrying).
      - timeout / network errors: retry once immediately.
    """
    data = json.dumps(body).encode("utf-8")
    headers: dict[str, str] = {
        "Content-Type": "application/json",
        # Default User-Agent to avoid Cloudflare WAF block (error 1010).
        # The default Python-urllib/3.x UA is rejected by Cloudflare-protected
        # APIs like Groq, causing HTTP 403 with all requests.
        "User-Agent": "Mozilla/5.0 (compatible; findtorontoevents-swarm/1.0)",
        "Accept": "application/json",
    }
    if key:
        headers["Authorization"] = f"Bearer {key}"
    if extra_headers:
        for hk, hv in extra_headers.items():
            # Don't let extras clobber auth/content-type.
            if hk.lower() in ("authorization", "content-type"):
                continue
            headers[hk] = hv
    req = urllib.request.Request(url, data=data, headers=headers)

    RETRYABLE = {429, 500, 502, 503, 504}
    max_attempts = 3
    base_delay = 1.0  # seconds
    max_delay = 30.0  # seconds

    # FIX 2026-05-05: enforce overall deadline to prevent runaway total duration.
    # _deadline is set by the caller; default is DEFAULT_MAX_TOTAL_DURATION from
    # when the first attempt starts. If cumulative retry time would exceed the
    # deadline, we skip remaining attempts to stay within budget.
    deadline = _deadline if _deadline else (time.time() + DEFAULT_MAX_TOTAL_DURATION)

    for attempt in range(max_attempts):
        # Check if we still have time before attempting.
        remaining = deadline - time.time()
        if remaining <= 0:
            raise TimeoutError(
                f"_post to {url} exceeded overall deadline "
                f"({DEFAULT_MAX_TOTAL_DURATION}s across all attempts)"
            )
        # Clamp per-request timeout to not exceed remaining budget (keep 5s buffer).
        per_request_timeout = min(timeout, max(5, int(remaining * 0.8)))
        try:
            with urllib.request.urlopen(req, timeout=per_request_timeout) as r:
                status = r.getcode() or 200
                # 2026-05-05 fix: wrap json.loads in try/except to catch
                # malformed JSON (truncated, garbage, streaming partial).
                # On decode error, log a sanitized preview and raise a
                # structured RuntimeError so callers can distinguish it from
                # HTTP-level errors.
                raw = r.read()
                try:
                    return json.loads(raw), status
                except json.JSONDecodeError as e:
                    preview = raw.decode("utf-8", errors="replace")[:200].replace("\n", " ")
                    raise RuntimeError(
                        f"non-JSON response from {url} (status={status}): "
                        f"line {e.lineno} col {e.colno} — preview: {preview!r}"
                    ) from e
        except urllib.error.HTTPError as e:
            if e.code not in RETRYABLE or attempt == max_attempts - 1:
                raise
            delay = min(base_delay * (1.5 ** attempt) * random.uniform(0.8, 1.2),
                        max_delay)
            # 2026-05-05 fix: sanitize error body before logging.
            # Never log raw response bodies — they may contain API keys,
            # tokens, or PII. Log only: status code, attempt count, delay.
            err_body = e.read().decode("utf-8", errors="replace")[:100]
            err_body_sanitized = _sanitize_for_log(err_body)
            sys.stderr.write(
                f"[_post retry] {url} → {e.code}, "
                f"attempt {attempt + 1}/{max_attempts}, "
                f"waiting {delay:.1f}s, body={err_body_sanitized!r}\n"
            )
            time.sleep(delay)
        except (urllib.error.URLError, TimeoutError) as e:
            # Network / timeout errors: retry once immediately without backoff
            if attempt == max_attempts - 1:
                raise
            sys.stderr.write(
                f"[_post retry] {url} → {type(e).__name__}, "
                f"attempt {attempt + 1}/{max_attempts}, retry immediately\n"
            )
            time.sleep(0.5)


def _empty_meta() -> dict:
    """Fresh meta dict — keys are the imp-B audit fields. Callers populate."""
    return {
        "model_fingerprint": "",
        "tokens_in": 0,
        "tokens_out": 0,
        "transport_status": "ok",
    }


def call_openai_compat(provider: str, prompt: str, model_override: str | None,
                       sampling: dict | None = None) -> tuple[str, dict]:
    """Returns (content, meta). Meta carries imp-B audit fields:
    model_fingerprint (data.model echoed by API), tokens_in / tokens_out
    (from data.usage), transport_status (HTTP code as string)."""
    cfg = PROVIDERS[provider]
    key = _resolve_key(cfg["key_envs"])
    if not key and cfg["key_envs"]:
        raise RuntimeError(f"{provider}: no key in env (checked {cfg['key_envs']})")
    model = model_override or os.environ.get(f"{provider.upper()}_MODEL", cfg["model"])
    # Pollinations: model goes as a query param, not in the body.
    # Its body uses "model": "openai" (internal routing token).
    model_qp_name = cfg.get("model_param")  # e.g. "model" for pollinations
    s = _resolve_sampling(provider, sampling)
    # Build request body. Pollinations uses cfg["model"] ("openai" routing token)
    # in the body; all other providers use the actual model name.
    body_model = cfg["model"] if model_qp_name else model
    body = {
        "model": body_model,
        "messages": [{"role": "user", "content": prompt}],
    }
    # Build URL: append ?model=<name> for providers that use query-param routing.
    base_url = cfg["url"]
    if model_qp_name:
        # URL-encode the model name to handle any special characters safely.
        encoded_model = urllib.parse.quote(model, safe="")
        base_url = f"{base_url}?{model_qp_name}={encoded_model}"
    # Pass through known sampling keys; OpenAI-compat ignores unknowns silently.
    for k in ("temperature", "top_p", "max_tokens", "max_completion_tokens",
              "presence_penalty", "frequency_penalty"):
        if k in s:
            body[k] = s[k]
    # 2026-05-13: reasoning-effort support. Opt-in via env or sampling override.
    # Whitelist engines known to honor the OpenAI-compat `reasoning_effort` field:
    #   xai          (Grok-4 supports low|medium|high; Grok-3 ignores silently)
    #   openrouter   (forwards to upstream — works for o1 / claude-3.7-sonnet routing)
    #   opencode     (Grok-4.x backend per self-id)
    # For other engines we DON'T inject — silent-ignore is fine but cleaner to skip.
    _REASONING_SUPPORTED = {"xai", "openrouter", "opencode"}
    _reasoning = s.get("reasoning_effort") or os.environ.get(
        f"{provider.upper()}_REASONING_EFFORT"
    ) or os.environ.get("SWARM_REASONING_EFFORT")
    if _reasoning and provider in _REASONING_SUPPORTED:
        _val = str(_reasoning).strip().lower()
        if _val in ("low", "medium", "high", "minimal", "max"):
            # Normalize alias: 'max' -> 'high' (xai's API tops at 'high')
            body["reasoning_effort"] = "high" if _val == "max" else _val
    meta = _empty_meta()
    # Provider-specific extra headers. OpenRouter requires (well, strongly
    # encourages) HTTP-Referer + X-Title — used for per-app rate-limit
    # attribution and the public leaderboard. They're harmless on other
    # OpenAI-compat providers but we only send them for openrouter to avoid
    # signaling a foreign origin to deepseek/xai/inception.
    extra_headers: dict | None = None
    if provider == "openrouter":
        extra_headers = {
            "HTTP-Referer": "https://github.com/eltonaguiar/findtorontoevents_antigravity.ca",
            "X-Title": "findtorontoevents-swarm",
        }
    try:
        data, status = _post(base_url, body, key, extra_headers=extra_headers)
    except urllib.error.HTTPError as e:
        meta["transport_status"] = str(e.code)
        raise
    meta["transport_status"] = str(status)
    # `data.model` is the actual model id the provider used (catches self-spoof,
    # e.g., a router silently routing to a smaller model than requested).
    fp = data.get("model") or ""
    if fp:
        meta["model_fingerprint"] = str(fp)
    usage = data.get("usage") or {}
    # Standard OpenAI-compat keys; deepseek/xai/inception all comply.
    meta["tokens_in"] = int(usage.get("prompt_tokens") or 0)
    meta["tokens_out"] = int(usage.get("completion_tokens") or 0)
    choices = data.get("choices") or [{}]
    content = choices[0].get("message", {}).get("content", "") or ""
    return content, meta


def _call_cerebras_via_http(prompt: str, model_override: str | None,
                             sampling: dict | None, key: str) -> tuple[str, dict]:
    """OpenAI-compat HTTP fallback for cerebras when the SDK isn't installed.

    Reuses the same _post() helper used by openai_compat providers. Cerebras'
    /v1/chat/completions endpoint accepts the OpenAI request shape, just with
    `max_completion_tokens` instead of `max_tokens`.
    """
    model = model_override or os.environ.get("CEREBRAS_MODEL", "gpt-oss-120b")
    s = _resolve_sampling("cerebras", sampling)
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
    }
    for k in ("temperature", "top_p", "max_completion_tokens"):
        if k in s:
            body[k] = s[k]
    meta = _empty_meta()
    data, status = _post(
        "https://api.cerebras.ai/v1/chat/completions",
        body, key,
    )
    meta["transport_status"] = str(status)
    fp = data.get("model") or ""
    if fp:
        meta["model_fingerprint"] = str(fp)
    usage = data.get("usage") or {}
    meta["tokens_in"] = int(usage.get("prompt_tokens", 0) or 0)
    meta["tokens_out"] = int(usage.get("completion_tokens", 0) or 0)
    choices = data.get("choices") or [{}]
    content = (choices[0].get("message", {}).get("content") or "")
    return content, meta


def call_cerebras(prompt: str, model_override: str | None,
                  sampling: dict | None = None) -> tuple[str, dict]:
    """Cerebras has its own SDK and accepts max_completion_tokens.
    Returns (content, meta) — meta.model_fingerprint catches the case where
    cerebras silently routes to a different model id than requested."""
    key = _resolve_key(PROVIDERS["cerebras"]["key_envs"])
    if not key:
        raise RuntimeError("cerebras: no key in env")
    try:
        from cerebras.cloud.sdk import Cerebras
    except ImportError:
        # 2026-05-05 fix: fall back to OpenAI-compat HTTP when SDK missing.
        # Cerebras /v1/chat/completions is OpenAI-compatible; the SDK is a
        # convenience wrapper, not a hard requirement. Without this fallback,
        # every cerebras call fails with "pip install cerebras-cloud-sdk"
        # even though the underlying API would work via plain HTTP.
        # Evidence: swarm_runs/run_pr_swarm_compare/ +
        # swarm_runs/run_actions_swarm_compare/ both show stderr_tail with the
        # SDK-missing error, while deepseek (HTTP path) succeeded same run.
        return _call_cerebras_via_http(prompt, model_override, sampling, key)
    model = model_override or os.environ.get("CEREBRAS_MODEL", "gpt-oss-120b")
    client = Cerebras(api_key=key)
    s = _resolve_sampling("cerebras", sampling)
    kwargs = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
    }
    for k in ("temperature", "top_p", "max_completion_tokens"):
        if k in s:
            kwargs[k] = s[k]
    meta = _empty_meta()
    resp = client.chat.completions.create(**kwargs)
    # SDK exposes `model` and `usage` on the response object.
    fp = getattr(resp, "model", "") or ""
    if fp:
        meta["model_fingerprint"] = str(fp)
    usage = getattr(resp, "usage", None)
    if usage is not None:
        # cerebras sdk may expose attributes or .model_dump(); try both.
        pt = getattr(usage, "prompt_tokens", None)
        ct = getattr(usage, "completion_tokens", None)
        if pt is None or ct is None:
            try:
                ud = usage.model_dump() if hasattr(usage, "model_dump") else dict(usage)
                pt = pt if pt is not None else ud.get("prompt_tokens")
                ct = ct if ct is not None else ud.get("completion_tokens")
            except Exception:
                pass
        meta["tokens_in"] = int(pt or 0)
        meta["tokens_out"] = int(ct or 0)
    meta["transport_status"] = "ok"
    content = resp.choices[0].message.content or ""
    return content, meta


# Smart punctuation -> ASCII. Local `ollama` CLI line-wraps + cloud models
# emit U+2018/2019/201C/201D/2011 etc. that break json.loads downstream.
_OLLAMA_SMART_PUNCT = {
    "‘": "'", "’": "'", "‚": "'", "‛": "'",
    "“": '"', "”": '"', "„": '"', "‟": '"',
    "′": "'", "″": '"',
    "‑": "-", "–": "-", "—": "-",
    "…": "...",
}


def _ollama_normalize_smart_punct(s: str) -> str:
    if not s:
        return s
    for src, dst in _OLLAMA_SMART_PUNCT.items():
        if src in s:
            s = s.replace(src, dst)
    return s


def _ollama_repair_wrap_dup(s: str) -> str:
    """The local `ollama` CLI on Windows soft-wraps output at terminal
    width even when piped, AND replays the wrapped suffix at the start of
    the next line. Two flavors observed:

      A) Wrap mid-string, continuation:
           "...long-short tilt (value, momentum, quality) \\ncalibrated on MSCI..."
         (literal LF inside JSON string — invalid.)

      B) Wrap mid-token, replay duplicate:
           "...fallback chain"\\nchain",
           "...multi-pro\\nmulti-provider sanity checks"
           "...risk model\\nmodel",
         (the suffix from the truncated line gets re-emitted on next line.)

    Repair strategy (line-based, run BEFORE structural JSON parsing):
      1. Split on '\\n'. For each adjacent pair (prev, cur):
         - If cur starts with a token T and prev ends with that same T
           (with optional trailing punctuation like ',' or '"' or ' ' on prev),
           treat as wrap-dup: drop the duplicate prefix from cur.
         - Specifically: find the longest k>=2 such that the last k chars
           of prev's trailing word equal the first k chars of cur's leading
           word; if found, strip those k chars from the head of cur.
      2. Then handle flavor (A): inside any remaining JSON string literal,
         replace bare LF with space.
    """
    if not s:
        return s
    import re as _re
    lines = s.split("\n")
    if len(lines) < 2:
        return s
    repaired: list[str] = [lines[0]]
    for cur in lines[1:]:
        prev = repaired[-1]
        # Extract trailing word of prev (alnum + apostrophe + hyphen).
        m_prev = _re.search(r"([A-Za-z0-9'\-]+)([\"',\s]*)$", prev)
        m_cur = _re.match(r"^([A-Za-z0-9'\-]+)", cur)
        new_cur = cur
        if m_prev and m_cur:
            prev_word = m_prev.group(1)
            cur_word = m_cur.group(1)
            # Check prefix-overlap: is cur_word a prefix-replay that finishes prev_word?
            # Pattern (B1): prev_word == cur_word -> drop cur_word.
            # Pattern (B2): cur_word startswith prev_word -> cur is the completed token.
            #               Replace prev_word in prev with cur_word, drop cur_word from cur.
            # Pattern (B3): prev_word endswith some prefix of cur_word -> overlap.
            if prev_word == cur_word:
                # Exact replay: drop the duplicate token at start of cur.
                new_cur = cur[len(cur_word):]
                # If prev already ends with the structural punct that cur
                # tried to re-emit (e.g. prev=`...chain"`, cur=`chain",` ->
                # new_cur=`",`), drop those redundant chars from cur.
                prev_tail = m_prev.group(2)  # punct after prev_word in prev
                # Strip from new_cur any leading chars that are already in prev_tail.
                k = 0
                while k < len(new_cur) and k < len(prev_tail) and new_cur[k] == prev_tail[k]:
                    k += 1
                # Also: a common pattern is prev ends `chain"` and cur is `chain",` ->
                # after dropping `chain`, new_cur=`",`. The `"` is redundant
                # (prev already closed the string). Drop matching close-quote.
                if k == 0 and new_cur.startswith('"') and prev_tail.endswith('"'):
                    new_cur = new_cur[1:]
                else:
                    new_cur = new_cur[k:]
            elif cur_word.startswith(prev_word) and len(cur_word) > len(prev_word):
                # cur has the FULL token; prev was truncated. Replace in prev.
                # Only safe if prev_word appears at end of prev's content
                # (allowing punct tail like `"`).
                prev_tail = m_prev.group(2)
                idx = prev.rfind(prev_word + prev_tail)
                if idx >= 0 and idx + len(prev_word) + len(prev_tail) == len(prev):
                    repaired[-1] = prev[:idx] + cur_word + prev_tail
                    new_cur = cur[len(cur_word):]
        repaired.append(new_cur)
    joined = "\n".join(repaired)

    # Now flavor (A): replace bare LF inside JSON string literals with space.
    out: list[str] = []
    in_str = False
    escape = False
    for ch in joined:
        if escape:
            out.append(ch)
            escape = False
            continue
        if ch == "\\" and in_str:
            out.append(ch)
            escape = True
            continue
        if ch == '"':
            in_str = not in_str
            out.append(ch)
            continue
        if in_str and ch in ("\n", "\r"):
            out.append(" ")
            continue
        out.append(ch)
    return "".join(out)


def call_ollama_cloud(prompt: str, model_override: str | None,
                      sampling: dict | None = None) -> tuple[str, dict]:
    """Use local `ollama` CLI (it's signed-in for cloud-tagged models).
    OLLAMA_CLOUD_KEY env is an SSH push-key, NOT a chat token; do not use it for HTTP.

    Sampling is applied via the `ollama run --format` is not used; instead we
    embed the sampling parameters into the prompt as Modelfile-style PARAMETER
    pre-amble lines that ollama runners accept via stdin. The local CLI does
    not have first-class flags for temperature/top_p/num_predict on `run`
    in older versions, so we use the `set parameter` mechanism via stdin
    injection. If the user supplied no sampling override and env is unset,
    the prompt is left untouched (back-compat).
    """
    if shutil.which("ollama") is None:
        raise RuntimeError("ollama_cloud: `ollama` CLI not on PATH")
    model = model_override or os.environ.get("OLLAMA_CLOUD_MODEL", "gpt-oss:120b-cloud")
    s = _resolve_sampling("ollama_cloud", sampling)
    # Build an args list. Ollama's `run` does not accept temperature flags
    # directly, but it honours OLLAMA_* env vars or in-prompt /set parameter
    # directives. Easiest portable path: prepend a small directive block to
    # the prompt (newline-delimited). Ollama treats /set lines emitted on
    # stdin as parameter sets prior to the actual user turn — but only in
    # interactive mode. For non-interactive `run <model> <prompt>`, the
    # only reliable surface is the OLLAMA_* env. We set them on the child
    # process below (does NOT pollute parent env).
    child_env = os.environ.copy()
    if "temperature" in s:
        child_env["OLLAMA_TEMPERATURE"] = str(s["temperature"])
    if "top_p" in s:
        child_env["OLLAMA_TOP_P"] = str(s["top_p"])
    if "num_predict" in s:
        child_env["OLLAMA_NUM_PREDICT"] = str(s["num_predict"])
    meta = _empty_meta()
    # ollama_cloud doesn't expose API model id reliably; record the requested
    # name so reviewers can at least see which model was asked for.
    meta["model_fingerprint"] = str(model)
    proc = subprocess.run(
        ["ollama", "run", model, prompt],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=400, shell=False, env=child_env,
    )
    if proc.returncode != 0:
        meta["transport_status"] = f"rc={proc.returncode}"
        raise RuntimeError(f"ollama_cloud rc={proc.returncode}: {proc.stderr[-300:]}")
    meta["transport_status"] = "ok"
    out = proc.stdout
    # Strip terminal escapes the CLI emits even when piped.
    import re
    out = re.sub(r"\x1b\[[0-9?;]*[a-zA-Z]", "", out)
    out = re.sub(r"Thinking\.\.\..*?\.\.\.done thinking\.\s*", "", out, flags=re.DOTALL)
    out = _ollama_normalize_smart_punct(out)
    out = _ollama_repair_wrap_dup(out)
    # Sanity: try parsing as JSON; if it fails, log first/last 200 chars to
    # stderr so downstream debug has signal. Don't raise — caller's
    # _extract_json_object has its own repair path.
    candidate = out.strip()
    if candidate.startswith("{") and candidate.endswith("}"):
        try:
            json.loads(candidate)
        except json.JSONDecodeError as e:
            sys.stderr.write(
                f"[ollama_cloud parse-warn] {type(e).__name__}: {e.msg} "
                f"@ line {getattr(e, 'lineno', '?')} col {getattr(e, 'colno', '?')}\n"
                f"  head: {candidate[:200]!r}\n"
                f"  tail: {candidate[-200:]!r}\n"
            )
    return candidate, meta


def call_ollama_local(prompt: str, model_override: str | None,
                      sampling: dict | None = None) -> tuple[str, dict]:
    """Use local `ollama` daemon only (no API key required).

    Defaults to small local models so the swarm can run keyless on developer
    machines. Model resolution order:
      1) --model
      2) OLLAMA_LOCAL_MODEL
      3) OLLAMA_MODEL
      4) llama3.2:3b
    """
    if shutil.which("ollama") is None:
        raise RuntimeError("ollama_local: `ollama` CLI not on PATH")
    model = (
        model_override
        or os.environ.get("OLLAMA_LOCAL_MODEL")
        or os.environ.get("OLLAMA_MODEL")
        or "llama3.2:3b"
    )
    s = _resolve_sampling("ollama_local", sampling)
    child_env = os.environ.copy()
    if "temperature" in s:
        child_env["OLLAMA_TEMPERATURE"] = str(s["temperature"])
    if "top_p" in s:
        child_env["OLLAMA_TOP_P"] = str(s["top_p"])
    if "num_predict" in s:
        child_env["OLLAMA_NUM_PREDICT"] = str(s["num_predict"])

    meta = _empty_meta()
    meta["model_fingerprint"] = str(model)
    proc = subprocess.run(
        ["ollama", "run", model, prompt],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=400, shell=False, env=child_env,
    )
    if proc.returncode != 0:
        meta["transport_status"] = f"rc={proc.returncode}"
        raise RuntimeError(f"ollama_local rc={proc.returncode}: {proc.stderr[-300:]}")
    meta["transport_status"] = "ok"

    import re
    out = re.sub(r"\x1b\[[0-9?;]*[a-zA-Z]", "", proc.stdout)
    out = re.sub(r"Thinking\.\.\..*?\.\.\.done thinking\.\s*", "", out, flags=re.DOTALL)
    out = _ollama_normalize_smart_punct(out)
    out = _ollama_repair_wrap_dup(out)
    candidate = out.strip()
    return candidate, meta


PROVIDER_ALIASES = {
    "gemini_api": "gemini",
}

SUPPORTED_PROVIDERS = sorted(set(PROVIDERS.keys()) | set(PROVIDER_ALIASES.keys()) | {"cerebras", "ollama_cloud", "ollama_local", "gemini", "github_models", "pollinations"})


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", required=True, choices=SUPPORTED_PROVIDERS)
    ap.add_argument("--prompt-file")
    ap.add_argument("--model")
    ap.add_argument("--temperature", type=float, default=None,
                    help="Override sampling temperature (default per-provider in SAMPLING_DEFAULTS).")
    ap.add_argument("--max-tokens", type=int, default=None,
                    help="Override max tokens (auto-mapped to max_completion_tokens for cerebras / num_predict for ollama providers).")
    ap.add_argument("--top-p", type=float, default=None,
                    help="Override top_p (default 1.0 per-provider).")
    ap.add_argument("--meta-file", default=None,
                    help="If set, write the imp-B audit-meta JSON "
                         "(model_fingerprint, tokens_in, tokens_out, "
                         "transport_status) to this path. Used by "
                         "worker_runner.call_api_consultant to pipe meta "
                         "into CallTimer alongside the textual response.")
    ap.add_argument("prompt_path", nargs="?")
    args = ap.parse_args()

    src = args.prompt_file or args.prompt_path or "-"
    prompt = _read_prompt(src)
    if not prompt.strip():
        print("empty prompt", file=sys.stderr)
        return 1

    provider = PROVIDER_ALIASES.get(args.provider, args.provider)

    sampling: dict = {}
    if args.temperature is not None:
        sampling["temperature"] = args.temperature
    if args.max_tokens is not None:
        sampling["max_tokens"] = args.max_tokens
    if args.top_p is not None:
        sampling["top_p"] = args.top_p
    sampling_arg = sampling or None

    meta = _empty_meta()
    try:
        if provider == "cerebras":
            content, meta = call_cerebras(prompt, args.model, sampling_arg)
        elif provider == "ollama_cloud":
            content, meta = call_ollama_cloud(prompt, args.model, sampling_arg)
        elif provider == "ollama_local":
            content, meta = call_ollama_local(prompt, args.model, sampling_arg)
        else:
            content, meta = call_openai_compat(provider, prompt, args.model, sampling_arg)
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")[:500]
        except Exception:
            pass
        # 2026-05-05 fix: sanitize body before logging to prevent key leaks.
        body_sanitized = _sanitize_for_log(body)
        print(f"{provider} HTTP {e.code}: {body_sanitized}", file=sys.stderr)
        meta["transport_status"] = str(e.code)
        if args.meta_file:
            try:
                Path(args.meta_file).write_text(json.dumps(meta), encoding="utf-8")
            except Exception:
                pass
        return 2
    except subprocess.TimeoutExpired:
        print(f"{provider} timeout", file=sys.stderr)
        meta["transport_status"] = "timeout"
        if args.meta_file:
            try:
                Path(args.meta_file).write_text(json.dumps(meta), encoding="utf-8")
            except Exception:
                pass
        return 4
    except Exception as e:
        print(f"{provider} error: {e}", file=sys.stderr)
        meta["transport_status"] = meta.get("transport_status") or "error"
        if args.meta_file:
            try:
                Path(args.meta_file).write_text(json.dumps(meta), encoding="utf-8")
            except Exception:
                pass
        return 3

    if args.meta_file:
        try:
            Path(args.meta_file).write_text(json.dumps(meta), encoding="utf-8")
        except Exception as e:
            sys.stderr.write(f"[meta-file write] {type(e).__name__}: {e}\n")

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    sys.stdout.write(content)
    return 0


if __name__ == "__main__":
    sys.exit(main())
