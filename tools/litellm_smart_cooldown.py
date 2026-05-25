"""
LiteLLM smart-cooldown custom logger.

Classifies per-deployment failures into a category and computes a meaningful
unban time, instead of the static `cooldown_time: 300` seconds in the router.

Categories
----------
  daily_quota   (CF, some HF) → cool until next UTC midnight
  monthly_quota (HF account-pool 402) → cool until UTC midnight on 1st of next month
  dead_key      (401 with "invalid"/"out of funds") → cool 24h (operator action needed)
  rate_limit    (transient 429 without quota markers) → cool 300s
  server_error  (5xx) → cool 60s

Writes a state file at /tmp/litellm_cooldown_state.json so the human
operator can see WHY a provider is parked (which the LiteLLM internal
state alone never tells you).

How LiteLLM picks this up
-------------------------
litellm_settings:
  callbacks: tools.litellm_smart_cooldown.smart_cooldown

Register the *instance* (smart_cooldown) — LiteLLM treats it as a
CustomLogger and calls async_log_failure_event() on every upstream failure.

Reading the state file:
  jq . /tmp/litellm_cooldown_state.json
"""
from __future__ import annotations

import datetime as _dt
import json
import os
from pathlib import Path
from typing import Any

from litellm.integrations.custom_logger import CustomLogger  # type: ignore

_STATE_PATH = Path(os.environ.get("LITELLM_COOLDOWN_STATE", "/tmp/litellm_cooldown_state.json"))


def _now_utc() -> _dt.datetime:
    return _dt.datetime.now(_dt.timezone.utc)


def _seconds_until_next_utc_midnight() -> int:
    now = _now_utc()
    tomorrow = (now + _dt.timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return max(60, int((tomorrow - now).total_seconds()))


def _seconds_until_next_month_start() -> int:
    now = _now_utc()
    if now.month == 12:
        nxt = now.replace(year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        nxt = now.replace(month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
    return max(3600, int((nxt - now).total_seconds()))


def _classify(exc: BaseException | None, api_base: str | None) -> tuple[str, int]:
    """Return (category, cooldown_seconds)."""
    msg = (str(exc) if exc else "").lower()
    base = (api_base or "").lower()

    # Cloudflare daily neuron quota
    if "cloudflare.com" in base and ("429" in msg or "rate" in msg or "quota" in msg or "neuron" in msg):
        return "daily_quota_cf", _seconds_until_next_utc_midnight()

    # HuggingFace monthly account-pool 402
    if "huggingface" in base or "hf.co" in base:
        if "402" in msg or "payment required" in msg or "monthly" in msg or "credit" in msg:
            return "monthly_quota_hf", _seconds_until_next_month_start()
        if "429" in msg:
            return "rate_limit", 300

    # Dead-key / insufficient-funds signals (Nous balance=0, OFOX invalid key,
    # Hypereal "Insufficient credits", DeepInfra primary 401, etc.)
    if (
        "401" in msg
        or "unauthorized" in msg
        or "invalid api key" in msg
        or "invalid or expired api key" in msg
        or "out of funds" in msg
        or "insufficient credits" in msg
        or "insufficient balance" in msg
        or "balance" in msg
        or "top up" in msg
    ):
        return "dead_key", 24 * 3600

    # Generic rate limit
    if "429" in msg or "rate limit" in msg or "too many requests" in msg:
        return "rate_limit", 300

    # 5xx
    if "500" in msg or "502" in msg or "503" in msg or "504" in msg or "internal server" in msg:
        return "server_error", 60

    # Context-window / bad-request → don't cool, return 0 (let router handle context fallback)
    if "400" in msg or "context" in msg or "max_tokens" in msg or "input validation" in msg:
        return "bad_request", 0

    return "other", 120


def _load_state() -> dict[str, Any]:
    if not _STATE_PATH.exists():
        return {"version": 1, "cooled": {}}
    try:
        return json.loads(_STATE_PATH.read_text())
    except Exception:
        return {"version": 1, "cooled": {}}


def _save_state(state: dict[str, Any]) -> None:
    try:
        _STATE_PATH.write_text(json.dumps(state, indent=2, default=str))
    except Exception:
        pass


def _record(api_base: str | None, model: str | None, category: str, cooldown_s: int, exc: str) -> None:
    state = _load_state()
    cooled: dict[str, Any] = state.setdefault("cooled", {})
    key = f"{model or '?'} @ {api_base or '?'}"
    until = _now_utc() + _dt.timedelta(seconds=cooldown_s)
    entry = cooled.get(key, {"hits": 0})
    entry.update({
        "category": category,
        "cooldown_seconds": cooldown_s,
        "cool_until_utc": until.isoformat(),
        "last_error": exc[:300],
        "last_seen_utc": _now_utc().isoformat(),
        "hits": int(entry.get("hits", 0)) + 1,
    })
    cooled[key] = entry
    _save_state(state)


class _SmartCooldown(CustomLogger):
    """LiteLLM custom logger — observes upstream failures and tags them.

    NOTE: this records the *recommended* cooldown to the state file for the
    operator. LiteLLM's router still owns the live cooldown via cooldown_time.
    To enforce the dynamic value, set litellm_settings.cooldown_time to the
    longest of the categories (24h) and rely on `_record` for visibility.
    A full enforcement variant would require monkey-patching router internals
    which is brittle across LiteLLM versions.
    """

    async def async_log_failure_event(self, kwargs, response_obj, start_time, end_time):  # noqa: D401
        try:
            litellm_params = kwargs.get("litellm_params") or {}
            api_base = litellm_params.get("api_base") or kwargs.get("api_base")
            model = kwargs.get("model")
            exc = kwargs.get("exception")
            category, cooldown_s = _classify(exc, api_base)
            _record(api_base, model, category, cooldown_s, str(exc) if exc else "")
        except Exception:
            pass

    def log_failure_event(self, kwargs, response_obj, start_time, end_time):  # sync variant
        try:
            litellm_params = kwargs.get("litellm_params") or {}
            api_base = litellm_params.get("api_base") or kwargs.get("api_base")
            model = kwargs.get("model")
            exc = kwargs.get("exception")
            category, cooldown_s = _classify(exc, api_base)
            _record(api_base, model, category, cooldown_s, str(exc) if exc else "")
        except Exception:
            pass


smart_cooldown = _SmartCooldown()
