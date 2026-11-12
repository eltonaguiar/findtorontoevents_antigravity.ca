#!/usr/bin/env python3
"""Discover free models from gateway catalogs and merge them into a LiteLLM config.

Why this exists
---------------
The static `litellm_config.yaml` hardcodes model IDs. When an upstream retires or
renames a model the proxy keeps routing to it and every request 410s/404s (e.g.
`nvidia_nim/meta/llama-3.1-8b-instruct` was retired 2026-08-26). Gateway
catalogs, by contrast, are always current — so we re-read them on every proxy
start instead of trusting a frozen list.

Providers
---------
  kilo      https://ai-gateway.kilo.ai/api/v1/models   — NO AUTH REQUIRED.
            (anonymous: ~200 req/hour per IP; with KILOCODE_API_KEY: higher)
  opencode  https://opencode.ai/zen/v1/models          — needs OPENCODE_API_KEY.
            Free-tier models are 403 when called outside the app, and an expired
            key reports api_key_expired; both cases are skipped, never fatal.

Output
------
A merged copy of the base config with extra `model_list` entries appended to
dedicated groups (`ULTRA_FREE_KILO`, `ULTRA_FREE_OPENCODE`) which are then
registered as fallbacks of the strict-free cloud groups.

Usage
-----
  python3 tools/litellm_dynamic_models.py --base litellm_config.yaml \
          --out /tmp/litellm_config.dynamic.yaml
  python3 tools/litellm_dynamic_models.py --dry-run     # print what it found

Exit codes
----------
  0  at least one provider contributed models; merged config written
  1  nothing discovered (caller should keep using the static config)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import requests
except Exception:  # pragma: no cover
    print("[dynamic-models] requests not available", file=sys.stderr)
    raise SystemExit(1)

try:
    import yaml
except Exception:  # pragma: no cover
    print("[dynamic-models] PyYAML not available", file=sys.stderr)
    raise SystemExit(1)

KILO_BASE = "https://ai-gateway.kilo.ai/api/v1"
OPENCODE_BASES = ("https://opencode.ai/zen/v1", "https://opencode.ai/inference/openai/v1")

# Groups that should be able to fall back onto freshly discovered free models.
FALLBACK_TARGETS = ("ULTRA_FREE_CLOUD", "ULTRA_FREE_CLOUD_FAST")

DEFAULT_OUT_TOKENS = 8192
HTTP_TIMEOUT = 20

# Cloudflare-fronted gateways answer the default `python-requests` agent with a
# bare 403/1010. Send a browser-shaped UA or healthy providers look dead.
USER_AGENT = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36")


def _log(msg: str) -> None:
    print(f"[dynamic-models] {msg}", file=sys.stderr)


def _pricing_is_free(entry: dict[str, Any]) -> bool:
    """A model is free only if the catalog says every price component is exactly 0.

    NEGATIVE prices must be rejected. OpenRouter encodes "price varies / this is
    a router, bill the underlying model" as `-1`:

        openrouter/auto     pricing {prompt: "-1", completion: "-1"}
        nvidia/switchyard   pricing {prompt: "-1", completion: "-1"}

    Testing `float(raw) > 0` therefore classified every router as FREE, which
    would route traffic to PAID models and spend real credit. Only an exact zero
    is free.
    """
    pricing = entry.get("pricing") or {}
    if not isinstance(pricing, dict):
        return False
    for key in ("prompt", "completion"):
        raw = pricing.get(key)
        if raw in (None, ""):
            continue
        try:
            if float(raw) != 0.0:
                return False
        except (TypeError, ValueError):
            return False
    return True


def _extract_ids(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        for key in ("data", "models", "results"):
            if isinstance(payload.get(key), list):
                return [x for x in payload[key] if isinstance(x, dict)]
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    return []


@dataclass(frozen=True)
class ProviderSpec:
    """One OpenAI-compatible gateway we can discover free models from."""

    name: str
    base: str
    key_env: str | None      # None => anonymous works
    group: str               # LiteLLM model_name to write the entries under
    rpm_env: str
    needs_key: bool
    probe_candidates: int = 2
    # Drop free models smaller than this. A 64k-context model is free but is not
    # useful as a general fallback for this proxy's workloads.
    min_context: int = 0
    # Native LiteLLM providers (openrouter, groq, ...) must be addressed as
    # `openrouter/<id>` with NO api_base. Gateways get `openai/<id>` + api_base.
    litellm_provider: str | None = None
    # Reject models whose output is not text (OpenRouter's zero-priced
    # google/lyria-* entries are MUSIC models — free, but not chat).
    require_text_output: bool = False
    # simple-shuffle weight when the rpm env var is unset.
    rpm_default: int = 3


PROVIDERS: dict[str, ProviderSpec] = {
    "kilo": ProviderSpec("kilo", KILO_BASE, "KILOCODE_API_KEY", "ULTRA_FREE_KILO", "KILO_RPM",
                         needs_key=False),
    "opencode": ProviderSpec("opencode", OPENCODE_BASES[0], "OPENCODE_API_KEY", "ULTRA_FREE_OPENCODE",
                             "OPENCODE_RPM", needs_key=True),
    # OpenRouter is unusual: /models needs no auth, free models are identified by
    # zero pricing (not only the `:free` suffix), and it is a NATIVE litellm
    # provider. Free quota is 50/day without credit but 1000/day once any credit
    # is purchased — verify with GET /api/v1/key (`free_model_daily_requests`).
    # Keep rpm low: the cap is shared by every free model on the account.
    "openrouter": ProviderSpec("openrouter", "https://openrouter.ai/api/v1",
                               "OPENROUTER_API_KEY", "ULTRA_FREE_OPENROUTER",
                               "OPENROUTER_FREE_RPM", needs_key=False,
                               min_context=100_000, litellm_provider="openrouter",
                               require_text_output=True, rpm_default=2),
}


def _auth_headers(spec: ProviderSpec) -> tuple[dict[str, str], str | None]:
    key = os.environ.get(spec.key_env) if spec.key_env else None
    h = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if key:
        h["Authorization"] = f"Bearer {key}"
    return h, key


def _is_free_id(mid: str) -> bool:
    m = mid.lower()
    return ":free" in m or m.endswith("/free") or m.endswith("-free") or m.startswith("free")


def _entry_context(entry: dict[str, Any]) -> int:
    top = entry.get("top_provider") or {}
    try:
        return int(entry.get("context_length") or top.get("context_length") or 0)
    except (TypeError, ValueError):
        return 0


def _is_chat(entry: dict[str, Any]) -> bool:
    """False for zero-priced NON-chat models.

    OpenRouter exposes zero-priced music models such as
    `google/lyria-3-pro-preview` with `output_modalities: ["text", "audio"]`.
    Accepting anything that merely CONTAINS "text" lets them through, so every
    output modality must be text.
    """
    arch = entry.get("architecture") or {}
    outs = arch.get("output_modalities")
    if not outs:
        return True  # field absent => don't second-guess the catalog
    return all(str(o).lower() == "text" for o in outs)


def _accept(spec: ProviderSpec, entry: dict[str, Any]) -> bool:
    """Is this catalog row a FREE, usable chat model for this provider?"""
    mid = str(entry["id"])
    if spec.require_text_output and not _is_chat(entry):
        return False
    # OpenRouter marks freeness by pricing, and not every free row carries `:free`.
    if spec.name == "openrouter":
        return _pricing_is_free(entry)
    return _is_free_id(mid) and _pricing_is_free(entry)


def _list_models(spec: ProviderSpec) -> list[dict[str, Any]]:
    headers, _ = _auth_headers(spec)
    try:
        r = requests.get(f"{spec.base}/models", headers=headers, timeout=HTTP_TIMEOUT)
    except Exception as exc:
        _log(f"{spec.name}: list failed ({str(exc)[:70]})")
        return []
    if r.status_code != 200:
        try:
            detail = str(r.json().get("error") or "")[:90]
        except Exception:
            detail = r.text[:90]
        _log(f"{spec.name}: list HTTP {r.status_code} {detail}")
        return []
    return _extract_ids(r.json())


def _judge_completion(r, model_id: str) -> tuple[bool, str, bool]:
    """Return (ok, detail, retry_bigger).

    Three distinct 200-shaped outcomes must NOT be conflated:
      * non-JSON body            -> a retirement/placeholder page (GitHub Models
                                     answered `text/plain "OK"` for months). Dead.
      * empty content, finish=length -> a REASONING model that spent the whole
                                     budget thinking (Together's Ternary-Bonsai
                                     needs ~415 tokens before emitting text).
                                     Not dead — retry with a bigger budget.
      * empty content, finish=stop   -> genuinely empty. Reject.
    """
    ctype = (r.headers.get("content-type") or "").lower()
    if "json" not in ctype:
        return False, f"non-JSON body ({ctype or 'no content-type'}): {r.text[:60]!r}", False
    try:
        d = r.json()
    except Exception:
        return False, f"unparseable JSON: {r.text[:60]!r}", False
    ch = (d.get("choices") or [{}])[0]
    msg = ch.get("message") or {}
    content = (msg.get("content") or "").strip()
    reasoning = (msg.get("reasoning_content") or msg.get("reasoning") or "")
    finish = ch.get("finish_reason")
    if content:
        return True, f"content={content[:30]!r}", False
    if finish == "length":
        return False, "empty content, finish=length (reasoning model — budget too small)", True
    if reasoning:
        return True, "reasoning-only response (finish=stop)", False
    return False, f"empty content, finish={finish}", False


def _probe_generation(spec: ProviderSpec, model_id: str) -> tuple[bool, str]:
    """One cheap completion — proof that the model actually serves inference.

    A 200 from /models does NOT mean inference works. Three distinct traps this
    catches:
      * OpenCode lists ~11 `*-free` models, then 429 FreeUsageLimitError for any
        external client (free tier is gated to the official app).
      * A gateway can list a model that is retired upstream (NVIDIA returned
        HTTP 410 Gone for months for `meta/llama-3.1-8b-instruct`).
      * An account can be alive but unfunded (402 / NOT_ENOUGH_BALANCE).
    """
    headers, key = _auth_headers(spec)
    headers["Content-Type"] = "application/json"
    last = ""
    # Two attempts: reasoning models emit nothing until they finish thinking, so
    # a small budget yields an empty-but-HTTP-200 response that must NOT be read
    # as success (or as death).
    for max_tokens in (64, 800):
        try:
            r = requests.post(
                f"{spec.base}/chat/completions",
                json={"model": model_id,
                      "messages": [{"role": "user", "content": "Reply with the word BANANA."}],
                      "max_tokens": max_tokens},
                headers=headers,
                timeout=120,
            )
        except Exception as exc:
            return False, f"probe error: {str(exc)[:60]}"
        if r.status_code != 200:
            return False, f"HTTP {r.status_code} {r.text[:110].replace(chr(10), ' ')}"
        ok, detail, retry_bigger = _judge_completion(r, model_id)
        if ok:
            return True, detail
        last = detail
        if not retry_bigger:
            return False, detail
    return False, last


def discover(spec: ProviderSpec, probe: bool = True) -> tuple[list[dict[str, Any]], str]:
    """List -> keep free -> PROVE inference. Returns (free_models, status)."""
    _, key = _auth_headers(spec)
    if spec.needs_key and not key:
        _log(f"{spec.name}: no {spec.key_env} set — skipped")
        return [], "no key"

    entries = _list_models(spec)
    free = [e for e in entries if e.get("id") and _accept(spec, e)]
    _log(f"{spec.name}: {len(entries)} listed, {len(free)} free")
    if not free:
        return [], "no free models"
    if spec.min_context:
        keep = [e for e in free if _entry_context(e) >= spec.min_context]
        if len(keep) != len(free):
            _log(f"{spec.name}: dropped {len(free) - len(keep)} below "
                 f"{spec.min_context} ctx")
        free = keep
        if not free:
            return [], f"no free models >= {spec.min_context} ctx"
    if not probe:
        return free, "unprobed"

    # Try more than one candidate: the first may be cold-starting or briefly
    # rate-limited while another free model on the same gateway serves fine.
    for cand in free[: max(1, spec.probe_candidates)]:
        ok, detail = _probe_generation(spec, str(cand["id"]))
        if ok:
            _log(f"{spec.name}: generation verified via {cand['id']} ({len(free)} enrolled)")
            return free, "verified"
        _log(f"{spec.name}: probe {cand['id']} failed ({detail})")
    _log(f"{spec.name}: no free model could generate — provider skipped")
    return [], "probe failed"


def _entry(model_name: str, real_id: str, api_base: str, key_env: str, rpm: int,
           ctx: int | None, out_tokens: int | None, supports_tools: bool,
           litellm_provider: str | None = None) -> dict[str, Any]:
    if litellm_provider:
        model_ref = f"{litellm_provider}/{real_id}"
    elif api_base:
        model_ref = f"openai/{real_id}"
    else:
        model_ref = real_id
    params: dict[str, Any] = {
        "model": model_ref,
        "api_key": f"os.environ/{key_env}",
        # simple-shuffle is WEIGHTED BY rpm — an entry with no rpm is effectively
        # never picked, so this field is mandatory for these to appear in rotation.
        "rpm": rpm,
    }
    if api_base:
        params["api_base"] = api_base
    # Context is annotated ONLY when a catalog actually stated it.
    #
    # This used to be `"max_input_tokens": ctx or 128000`, which wrote a
    # fabricated 128,000 for every model whose catalog row carried no
    # `context_length`. A fabricated floor is worse than a missing one: it is
    # indistinguishable from a measured value, so clients size prompts against
    # it and the failure lands upstream as a 400 (or truncates silently)
    # instead of being visible here. Omitting the key leaves LiteLLM to resolve
    # the window from its own provider map, and leaves a genuinely unknown model
    # reported as `null` rather than confidently wrong.
    info: dict[str, Any] = {}
    if ctx:
        info["max_input_tokens"] = int(ctx)
    info["max_output_tokens"] = out_tokens or DEFAULT_OUT_TOKENS
    info["supports_function_calling"] = bool(supports_tools)
    return {"model_name": model_name, "litellm_params": params, "model_info": info}


def build_entries(spec: ProviderSpec, entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rpm = int(os.environ.get(spec.rpm_env, str(spec.rpm_default)))
    out = []
    for e in entries:
        mid = str(e["id"])
        top = e.get("top_provider") or {}
        ctx = e.get("context_length") or top.get("context_length")
        max_out = e.get("max_completion_tokens") or top.get("max_completion_tokens")
        params_supported = e.get("supported_parameters") or []
        supports_tools = any(str(p).lower() in ("tools", "tool_choice", "function_calling")
                             for p in params_supported)
        env = spec.key_env or ""
        out.append(_entry(spec.group, mid, spec.base, env, rpm, ctx, max_out, supports_tools,
                          litellm_provider=spec.litellm_provider))
    return out


def merge(base_path: Path, kilo_entries: list[dict[str, Any]], oc_entries: list[dict[str, Any]],
          gemini_entries: list[dict[str, Any]] | None = None,
          pin_entries: list[dict[str, Any]] | None = None,
          openrouter_entries: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    cfg = yaml.safe_load(base_path.read_text(encoding="utf-8")) or {}
    cfg.setdefault("model_list", [])

    # Every dynamic entry names its own group, so derive the group list from the
    # entries instead of hardcoding it here. A hardcoded list silently omits a
    # newly added provider from the fallback graph — the group then exists but is
    # never reachable, which looks identical to "discovery found nothing".
    dynamic = (list(kilo_entries or []) + list(oc_entries or [])
               + list(gemini_entries or []) + list(openrouter_entries or []))
    added: list[str] = []
    for entry in dynamic:
        group = entry.get("model_name")
        if group and group not in added:
            added.append(group)
    if dynamic:
        cfg["model_list"].extend(dynamic)

    # Pins are standalone aliases — deliberately NOT added to the fallback graph,
    # because a pin exists precisely so it does not silently become another model.
    if pin_entries:
        cfg["model_list"].extend(pin_entries)

    if added:
        fb = cfg.setdefault("router_settings", {}).setdefault("fallbacks", [])
        for target in FALLBACK_TARGETS:
            for item in fb:
                if isinstance(item, dict) and target in item:
                    current = item[target] or []
                    for group in added:
                        if group not in current:
                            current.append(group)
                    item[target] = current

    _normalize_shuffle_metrics(cfg)
    return cfg


def _normalize_shuffle_metrics(cfg: dict[str, Any]) -> int:
    """Make every deployment in a group carry the SAME shuffling metric.

    LiteLLM's `simple_shuffle` inspects only `healthy_deployments[0]` to decide
    which metric to use, then scores everyone else with `.get(metric, 0)`:

        weight = healthy_deployments[0]["litellm_params"].get(weight_by, None)
        weights = [m["litellm_params"].get(weight_by, 0) for m in healthy_deployments]

    So if the FIRST deployment declares `rpm`, every sibling that declares only
    `weight` — or nothing at all — scores 0 and is **never selected**. That was
    observed live: 38 of 45 routes in BAD_LEGACY_MIXED_F_MODE unpickable, 4 of 13
    in ULTRA_HYBRID_MODEL_LARGE. Which metric "wins" also depends on list order,
    so the same config can behave differently after a reorder.

    Fix: normalise per group, not globally. Pick the metric the group's first
    deployment uses (falling back to whichever metric any member uses), then give
    every member that same metric — carrying each member's own value where it has
    one, so intentional weighting survives.

    Also normalizes the legacy Kilo host onto the one this project probes.
    """
    default_rpm = int(os.environ.get("LITELLM_DEFAULT_RPM", "5"))
    default_weight = 1

    groups: dict[str, list[dict[str, Any]]] = {}
    for dep in cfg.get("model_list", []):
        if isinstance(dep, dict):
            groups.setdefault(str(dep.get("model_name") or "?"), []).append(dep)

    changed = 0
    for deps in groups.values():
        params_list = [d.setdefault("litellm_params", {}) for d in deps]
        first = params_list[0]
        if "weight" in first:
            metric = "weight"
        elif "rpm" in first:
            metric = "rpm"
        elif any("weight" in p for p in params_list):
            metric = "weight"
        else:
            metric = "rpm"

        fallback = default_weight if metric == "weight" else default_rpm
        for params in params_list:
            if metric not in params:
                other = "rpm" if metric == "weight" else "weight"
                params[metric] = params.get(other, fallback)
                changed += 1
            base = params.get("api_base")
            if isinstance(base, str) and base.startswith("https://api.kilo.ai/api/gateway/v1"):
                params["api_base"] = KILO_BASE

    if changed:
        _log(f"shuffle-metric: aligned {changed} deployment(s) onto their group's metric")
    return changed


# ---------------------------------------------------------------------------
# Last-good cache
#
# The most dangerous failure mode for a dynamically generated config is a
# *silent* one: a provider's catalog endpoint hiccups, discovery returns zero
# models, and the group quietly disappears — turning a degraded provider into a
# dead one. Keep the last successful list per source and reuse it when a refresh
# comes back empty. Entries contain only `os.environ/<NAME>` references, never
# key material, so the cache file holds no secrets.
# ---------------------------------------------------------------------------
CACHE_PATH = Path(os.environ.get("LITELLM_DYNAMIC_CACHE", "/tmp/litellm_dynamic_cache.json"))


def _cache_load() -> dict[str, Any]:
    try:
        return json.loads(CACHE_PATH.read_text())
    except Exception:
        return {}


def _cache_save(source: str, entries: list[dict[str, Any]]) -> None:
    if not entries:
        return
    state = _cache_load()
    state[source] = {
        "saved_utc": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc).isoformat(timespec="seconds"),
        "entries": entries,
    }
    try:
        CACHE_PATH.write_text(json.dumps(state, indent=2))
    except Exception:
        pass


def _cache_get(source: str) -> list[dict[str, Any]]:
    entry = _cache_load().get(source) or {}
    rows = entry.get("entries") or []
    return rows if isinstance(rows, list) else []


def with_cache(source: str, produced: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Successful refresh replaces the cache; an empty one falls back to it."""
    if produced:
        _cache_save(source, produced)
        return produced
    cached = _cache_get(source)
    if cached:
        _log(f"{source}: refresh returned nothing — reusing {len(cached)} cached deployment(s)")
        return cached
    _log(f"{source}: refresh returned nothing and no cache exists — source skipped")
    return []


# ---------------------------------------------------------------------------
# Google Gemini — one deployment per (model x key)
#
# Free-tier Google quotas are enforced PER MODEL PER DAY (and per model per
# minute), not per account. A static fallback *chain* is therefore the wrong
# shape: it burns model #1's daily allowance, fails, then moves on, and only
# reacts after the quota is already spent.
#
# Registering each (model x key) pair as its own deployment inside ONE group
# lets simple-shuffle spread load across every quota bucket simultaneously.
# When one model caps out, the smart-cooldown parks only that one deployment
# while its siblings keep serving.
# ---------------------------------------------------------------------------
GEMINI_API = "https://generativelanguage.googleapis.com/v1beta"
GEMINI_KEY_ENVS = ("GEMINI_API_KEY", "GEMINI_API_KEY_ALT", "GEMINI_API_KEY_ALT2", "GEMINI_NOV112026")
GEMINI_MAX_MODELS_PER_KEY = 12          # keeps the group readable and startup fast
_GEMINI_NON_CHAT = re.compile(r"(embedding|aqa|imagen|veo|tts|native-audio|-image)", re.I)


def _gemini_rank(model_id: str) -> tuple[int, int, str]:
    """Prefer flash-lite (highest free quota), then flash; avoid heavy `pro`."""
    low = model_id.lower()
    if "flash-lite" in low:
        return (0, 0, low)
    if "flash" in low:
        return (1, 0, low)
    if "pro" in low:
        return (3, 0, low)
    return (2, 0, low)


def discover_gemini(probe: bool = True) -> list[dict[str, Any]]:
    """Return LiteLLM deployments for every (model x key) pair we can reach."""
    key_envs = [e for e in GEMINI_KEY_ENVS if os.environ.get(e)]
    if not key_envs:
        _log("gemini: no GEMINI_* env vars set — skipped")
        return []

    entries: list[dict[str, Any]] = []
    for env_name in key_envs:
        key = os.environ[env_name]
        try:
            r = requests.get(f"{GEMINI_API}/models", params={"key": key},
                             headers={"User-Agent": USER_AGENT}, timeout=HTTP_TIMEOUT)
        except Exception as exc:
            _log(f"gemini[{env_name}]: list failed ({str(exc)[:60]})")
            continue
        if r.status_code != 200:
            _log(f"gemini[{env_name}]: HTTP {r.status_code} — key skipped")
            continue

        rows = (r.json() or {}).get("models") or []
        usable = []
        for row in rows:
            mid = str(row.get("name") or "").split("/")[-1]
            if not mid or _GEMINI_NON_CHAT.search(mid):
                continue
            methods = row.get("supportedGenerationMethods") or []
            if "generateContent" not in methods:
                continue
            usable.append(row)
        usable.sort(key=lambda x: _gemini_rank(str(x.get("name") or "")))
        usable = usable[:GEMINI_MAX_MODELS_PER_KEY]
        _log(f"gemini[{env_name}]: {len(rows)} listed, {len(usable)} generateContent models")

        if probe and usable:
            # Quotas are per MODEL per day, so one exhausted model says nothing
            # about its siblings. Try up to 3 candidates before condemning a key.
            # Only a key-wide auth failure (401/403) short-circuits.
            passed = False
            last = ""
            for row in usable[:3]:
                cand = str(row.get("name") or "").split("/")[-1]
                ok, detail = _gemini_probe(key, cand)
                if ok:
                    _log(f"gemini[{env_name}]: smoke call OK via {cand}")
                    passed = True
                    break
                last = f"{cand}: {detail}"
                if detail.startswith("HTTP 401") or detail.startswith("HTTP 403"):
                    break
            if not passed:
                _log(f"gemini[{env_name}]: no model could generate ({last}) — key skipped")
                continue

        for row in usable:
            mid = str(row.get("name") or "").split("/")[-1]
            ctx = row.get("inputTokenLimit")
            out_tok = row.get("outputTokenLimit")
            entries.append(_entry("ULTRA_FREE_GEMINI", f"gemini/{mid}", None,
                                  env_name, int(os.environ.get("GEMINI_RPM", "5")),
                                  ctx, out_tok, "tools" in " ".join(
                                      str(x) for x in (row.get("supportedGenerationMethods") or []))))
    return entries


def _gemini_probe(key: str, model_id: str) -> tuple[bool, str]:
    try:
        r = requests.post(
            f"{GEMINI_API}/models/{model_id}:generateContent",
            params={"key": key},
            json={"contents": [{"parts": [{"text": "1+1?"}]}],
                  "generationConfig": {"maxOutputTokens": 5}},
            headers={"User-Agent": USER_AGENT, "Content-Type": "application/json"},
            timeout=45,
        )
    except Exception as exc:
        return False, f"error {str(exc)[:50]}"
    if r.status_code == 200:
        return True, "ok"
    return False, f"HTTP {r.status_code} {r.text[:90].replace(chr(10), ' ')}"


# ---------------------------------------------------------------------------
# PINNED single-model aliases
#
# Pools are great for throughput but bad for consistency: shuffle means a
# different model answers each time, so behaviour drifts mid-conversation.
# A pin is the opposite trade — ONE deployment per alias, so you always talk to
# the same model, but WHICH model is re-resolved from the live catalog on every
# start (IDs rot; the pin does not).
#
#   ULTRA_ALL_DAY_LONG_<FAMILY>_N   one large-context free model each, N=1..3
#   PAID-DEEPSEEK-PRO / -FLASH      paid, latest matching id, no ULTRA prefix
#   MERCURY                         RETIRED 2026-12-28 (Inception API sunset)
#
# Every pin is probe-verified individually before it is emitted — the entire
# point of a pin is reliability, so an unverified pin is worse than no pin.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class PinSpec:
    prefix: str
    provider: str
    count: int = 1
    min_context: int = 0
    match: str = ""          # substring required in the model id, lowercased


PIN_SPECS: tuple[PinSpec, ...] = (
    # Free "all day long" large-context models. Kilo is the only gateway that
    # actually serves these to external clients, so it holds the working pins.
    PinSpec("ULTRA_ALL_DAY_LONG_KILO", "kilo", count=3, min_context=500_000),
    # Kept as a real spec rather than a comment: if OpenCode ever lifts its
    # free-tier gating these groups appear automatically on the next start.
    PinSpec("ULTRA_ALL_DAY_LONG_OPENCODE", "opencode", count=3, min_context=500_000),
    # Paid pins: no ULTRA prefix by request — these are known-cost aliases.
    PinSpec("PAID-DEEPSEEK-PRO", "deepseek", count=1, match="pro"),
    PinSpec("PAID-DEEPSEEK-FLASH", "deepseek", count=1, match="flash"),
    PinSpec("PAID-KIMI", "moonshot", count=1),
    PinSpec("PAID-GROK", "xai", count=1),
    # Cerebras: after their 2026 platform migration the free credit key works again
    # and it is the fastest inference we have by a wide margin (measured 616 tok/s
    # on gpt-oss-120b, 498 on qwen-3.8-27b). Draws on the account's credit, so it is
    # NOT placed in any strict-free group or fallback graph.
    PinSpec("ULTRA_FAST_CEREBRAS", "cerebras", count=2),
    # Together's free lane. Prism-ML/Ternary-Bonsai-27B is a REASONING model:
    # it emits nothing until ~415 tokens of thinking are done, so it must be
    # probed with a large budget and called with max_tokens >= 512 or callers
    # will see empty strings and mistake them for failures.
    PinSpec("ULTRA_FREE_TOGETHER_BONSAI", "together", count=1, match="ternary-bonsai"),
)

# Each entry may list several key env names: providers issue multiple keys and
# only some stay valid. The first one whose catalog answers wins.
_PIN_SOURCES: dict[str, tuple[str, tuple[str, ...]]] = {
    "kilo": (KILO_BASE, ("KILOCODE_API_KEY",)),
    "opencode": (OPENCODE_BASES[0], ("OPENCODE_API_KEY", "OPENCODE_API_KEY_ALT")),
    "deepseek": ("https://api.deepseek.com", ("DEEPSEEK_API_KEY",)),
    "moonshot": ("https://api.moonshot.ai/v1", ("MOONSHOT_API_KEY", "MOONSHOT_API_KEY_ALT")),
    "xai": ("https://api.x.ai/v1", ("XAI_API_KEY", "XAI_API_KEY_ALT")),
    "cerebras": ("https://api.cerebras.ai/v1", ("CEREBRAS_API_KEY", "CEREBRAS_API_KEY_ALT")),
    "together": ("https://api.together.xyz/v1", ("TOGETHER_API_KEY", "TOGETHER_API_KEY_ALT")),
}

# Preference order for the free large-context pins. Named first because these
# are the ones measured fast + reliable through Kilo; anything else falls back
# to plain context-length ordering.
_PIN_PREFERENCE = (
    "nemotron-3.5-super-vl",
    "nemotron-3.5-lightning",
    "inkling-2-small",
    "ernie-5.5-flash",
    "nemotron-3-ultra",
)


def _version_key(model_id: str) -> tuple:
    """Sort 'kimi-k2.6' > 'kimi-k2' numerically."""
    nums = re.findall(r"\d+(?:\.\d+)?", model_id)
    return tuple(float(n) for n in nums) if nums else (0.0,)


def _pin_rank(spec: PinSpec, model_id: str, ctx: int) -> tuple:
    low = model_id.lower()
    for idx, token in enumerate(_PIN_PREFERENCE):
        if token in low:
            return (0, idx, -ctx, low)
    if spec.provider in ("deepseek", "moonshot", "xai"):
        v = _version_key(low)
        return (0, 0, tuple(-x for x in v), low) if v else (1, 0, -ctx, low)
    return (1, 0, -ctx, low)


def _pin_probe(base: str, key_env: str, model_id: str) -> tuple[bool, str]:
    key = os.environ.get(key_env)
    headers = {"User-Agent": USER_AGENT, "Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    last = ""
    # Two attempts: the second with a budget large enough for a reasoning model
    # to finish thinking and actually emit text.
    for max_tokens in (64, 800):
        try:
            r = requests.post(f"{base}/chat/completions",
                              json={"model": model_id,
                                    "messages": [{"role": "user", "content": "Reply with the word BANANA."}],
                                    "max_tokens": max_tokens},
                              headers=headers, timeout=120)
        except Exception as exc:
            return False, f"error {str(exc)[:50]}"
        if r.status_code != 200:
            return False, f"HTTP {r.status_code} {r.text[:90].replace(chr(10), ' ')}"
        ok, detail, retry_bigger = _judge_completion(r, model_id)
        if ok:
            return True, detail
        last = detail
        if not retry_bigger:
            return False, detail
    return False, last


def build_pins(probe: bool = True) -> list[dict[str, Any]]:
    """Resolve every PinSpec against the live catalog; emit 1 deployment per alias."""
    out: list[dict[str, Any]] = []
    for spec in PIN_SPECS:
        base, key_envs = _PIN_SOURCES[spec.provider]
        present = [e for e in key_envs if os.environ.get(e)]
        if not present and spec.provider != "kilo":     # Kilo answers anonymously
            _log(f"pin {spec.prefix}: none of {key_envs} set — skipped")
            continue

        # Try each credential until a catalog answers; a dead key must not
        # masquerade as "provider has no models".
        rows: list[dict[str, Any]] = []
        key_env = present[0] if present else key_envs[0]
        for cand_env in (present or [key_envs[0]]):
            rows = _list_models(ProviderSpec(spec.provider, base, cand_env, spec.prefix,
                                             "PIN_RPM", needs_key=False))
            if rows:
                key_env = cand_env
                break
            _log(f"pin {spec.prefix}: catalog empty for {cand_env}")
        if not rows:
            _log(f"pin {spec.prefix}: no catalog — skipped")
            continue

        cands: list[tuple[str, int]] = []
        for row in rows:
            mid = str(row.get("id") or "")
            if not mid:
                continue
            ctx = int(row.get("context_length") or
                      (row.get("top_provider") or {}).get("context_length") or 0)
            if spec.provider in ("kilo", "opencode"):
                if not _is_free_id(mid) or not _pricing_is_free(row):
                    continue
                if ctx and ctx < spec.min_context:
                    continue
            if spec.match and spec.match not in mid.lower():
                continue
            cands.append((mid, ctx))
        cands.sort(key=lambda c: _pin_rank(spec, c[0], c[1]))

        accepted: list[tuple[str, int]] = []
        for mid, ctx in cands:
            if probe:
                ok, detail = _pin_probe(base, key_env, mid)
                if not ok:
                    _log(f"pin {spec.prefix}: {mid} failed probe ({detail})")
                    continue
            accepted.append((mid, ctx))
            if len(accepted) >= spec.count:
                break

        if not accepted:
            _log(f"pin {spec.prefix}: nothing verified — skipped")
            continue

        for i, (mid, ctx) in enumerate(accepted, 1):
            group = spec.prefix if spec.count == 1 else f"{spec.prefix}_{i}"
            out.append(_entry(group, mid, base, key_env, int(os.environ.get("PIN_RPM", "4")),
                              ctx or None, None, False))
        _log(f"pin {spec.prefix}: " + ", ".join(m for m, _ in accepted))
    return out


def verify_static(base_path: Path, workers: int = 8, timeout: int = 30,
                  only: str | None = None) -> int:
    """Probe every deployment in a static LiteLLM config and report dead ones.

    This is the same "does it actually generate?" gate as `discover()`, applied
    to the hand-written entries. It catches the failure mode that motivated this
    tool: `nvidia_nim/meta/llama-3.1-8b-instruct` sat in the config returning
    HTTP 410 Gone long after NVIDIA retired it on 2026-08-26.

    Uses litellm.completion directly so provider→base-URL mapping matches exactly
    what the proxy does at runtime.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    import litellm

    cfg = yaml.safe_load(base_path.read_text(encoding="utf-8")) or {}
    deployments = [
        m for m in cfg.get("model_list", [])
        if isinstance(m, dict) and m.get("litellm_params", {}).get("model")
    ]
    if only:
        deployments = [d for d in deployments if only in str(d["litellm_params"]["model"])]
    if not deployments:
        _log("verify-static: no deployments matched")
        return 1

    def check(dep: dict[str, Any]) -> tuple[str, str, str]:
        p = dict(dep["litellm_params"])
        group = dep.get("model_name", "?")
        real = p.pop("model")
        key = p.get("api_key")
        if isinstance(key, str) and key.startswith("os.environ/"):
            p["api_key"] = os.environ.get(key.split("/", 1)[1], "")
        p.setdefault("timeout", timeout)
        try:
            litellm.completion(
                model=real,
                messages=[{"role": "user", "content": "ok"}],
                max_tokens=8,
                **{k: v for k, v in p.items() if k != "rpm"},
            )
            return group, real, "OK"
        except Exception as exc:
            msg = str(exc).replace("\n", " ")
            return group, real, msg[:150]

    dead, alive = [], 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(check, d) for d in deployments]
        for fut in as_completed(futures):
            group, real, status = fut.result()
            if status == "OK":
                alive += 1
            else:
                dead.append((group, real, status))

    print(f"\nverified {len(deployments)} deployments: {alive} OK, {len(dead)} DEAD\n")
    for group, real, status in sorted(dead):
        print(f"  DEAD  {group:28} {real:52} {status}")
    if dead:
        print("\nSuggested action: comment out the DEAD entries in the config, or move "
              "the provider behind a live gateway so discovery can replace it.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Merge live gateway free models into a LiteLLM config")
    ap.add_argument("--base", default="litellm_config.yaml")
    ap.add_argument("--out", default="/tmp/litellm_config.dynamic.yaml")
    ap.add_argument("--providers", default="kilo,opencode,gemini,pins,openrouter")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-probe", action="store_true",
                    help="skip the OpenCode generation probe (may enrol non-working free models)")
    ap.add_argument("--summary", default="/tmp/litellm_dynamic_models.json")
    ap.add_argument("--verify-static", action="store_true",
                    help="probe every deployment in --base and report dead ones instead of merging")
    ap.add_argument("--only", default=None, help="with --verify-static: substring filter on model id")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--timeout", type=int, default=30)
    args = ap.parse_args()

    if args.verify_static:
        return verify_static(Path(args.base), workers=args.workers,
                             timeout=args.timeout, only=args.only)

    providers = [p.strip() for p in args.providers.split(",") if p.strip()]
    kilo_entries: list[dict[str, Any]] = []
    oc_entries: list[dict[str, Any]] = []
    gemini_entries: list[dict[str, Any]] = []
    pin_entries: list[dict[str, Any]] = []
    openrouter_entries: list[dict[str, Any]] = []

    for pname in providers:
        if pname == "gemini":
            gemini_entries = with_cache("gemini", discover_gemini(probe=not args.no_probe))
            if not gemini_entries:
                _log("gemini: nothing enrolled")
            continue
        if pname == "pins":
            pin_entries = with_cache("pins", build_pins(probe=not args.no_probe))
            if not pin_entries:
                _log("pins: nothing resolved")
            continue
        spec = PROVIDERS.get(pname)
        if spec is None:
            _log(f"unknown provider '{pname}' — known: {', '.join(PROVIDERS)}, gemini")
            continue
        models, status = discover(spec, probe=not args.no_probe)
        if not models:
            _log(f"{pname}: nothing discovered ({status}) — checking last-good cache")
        built = build_entries(spec, models) if models else []
        built = with_cache(pname, built)
        if not built:
            _log(f"{pname}: nothing enrolled")
            continue
        if pname == "kilo":
            kilo_entries = built
        elif pname == "opencode":
            oc_entries = built
        elif pname == "openrouter":
            openrouter_entries = built
        else:
            kilo_entries = kilo_entries + built

    total = (len(kilo_entries) + len(oc_entries) + len(gemini_entries)
             + len(pin_entries) + len(openrouter_entries))
    if total == 0:
        _log("no free models discovered — leaving config untouched")
        return 1

    summary = [e["litellm_params"]["model"].replace("openai/", "")
               for e in (kilo_entries + oc_entries + gemini_entries + pin_entries
                         + openrouter_entries)]
    if args.dry_run:
        print(json.dumps(summary, indent=2))
        return 0

    base = Path(args.base)
    if not base.exists():
        _log(f"base config not found: {base}")
        return 1

    cfg = merge(base, kilo_entries, oc_entries, gemini_entries, pin_entries, openrouter_entries)
    out = Path(args.out)
    out.write_text(
        "# AUTO-GENERATED by tools/litellm_dynamic_models.py — do not edit.\n"
        f"# base: {base}   free models: {total}\n"
        + yaml.safe_dump(cfg, sort_keys=False, default_flow_style=False),
        encoding="utf-8",
    )

    try:
        Path(args.summary).write_text(json.dumps({
            "generated_utc": __import__("datetime").datetime.now(
                __import__("datetime").timezone.utc).isoformat(),
            "count": total,
            "groups": {
                "ULTRA_FREE_KILO": len(kilo_entries),
                "ULTRA_FREE_OPENCODE": len(oc_entries),
                "ULTRA_FREE_GEMINI": len(gemini_entries),
            },
            "models": summary,
        }, indent=2), encoding="utf-8")
    except Exception:
        pass

    _log(f"wrote {out} (+{total} free models)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
