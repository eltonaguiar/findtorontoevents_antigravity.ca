"""
Call-count-based provider blacklist for the local LiteLLM proxy.

Problem this solves
-------------------
LiteLLM's built-in cooldown is TIME-based (`allowed_fails` + `cooldown_time: 65`
in litellm_config.yaml). A provider that is genuinely down (dead key, exhausted
quota, upstream outage) therefore gets retried again ~65 s later, on every
subsequent request, forever. With `routing_strategy: simple-shuffle` the router
keeps re-picking the dead provider, so a noticeable fraction of user requests
fail even though healthy providers are available.

This callback adds a CALL-COUNT-based blacklist: when a deployment fails in a
way that means "this provider is unhealthy", it is removed from the healthy
candidate pool for the next N client API calls (default 30). It only returns to
rotation after those calls have been consumed -- or immediately if the proxy is
restarted with an emptied state file.

How it works (all hooks verified against litellm 1.86.0)
-------------------------------------------------------
1. `async_pre_call_hook`  -> advances a global call counter (once per client
   request). Returns None so LiteLLM leaves request `data` completely untouched.
2. **Two** Router methods are patched at class level, because LiteLLM uses
   different ones on different paths:
   - `Router.async_get_healthy_deployments` -> the PRIMARY routing path
     (`async_get_available_deployment`). Patching only the underscore variant
     is NOT enough: it is never consulted for the first pick.
   - `Router._async_get_healthy_deployments` -> the retry / fallback and
     scheduler paths.
   Both drop blacklisted deployments from the candidate pool *before* the
   routing strategy picks one, composing cleanly with LiteLLM's own cooldown.
   The patch is installed lazily (at import and retried on the first request)
   because the proxy's config loader may import this module while `litellm` is
   still partially initialised, when `litellm.Router` does not exist yet.
3. `async_log_failure_event` -> classifies the upstream error (reusing
   `tools.litellm_smart_cooldown._classify`) and blacklists the deployment only
   for provider-unhealthy categories. Request-specific faults (400s, context
   window, content policy) are deliberately NOT blacklisted.

Safety properties
-----------------
- FAIL-OPEN: if filtering would empty the candidate pool, the unfiltered pool is
  returned. The blacklist can never make a request fail that would otherwise
  have had a candidate.
- FAIL-SAFE EXPIRY: the call counter advances for any call type that isn't a
  known non-LLM endpoint, so a blacklist entry always expires.
- NEVER RAISES: every hook swallows its own exceptions. A bug here degrades to
  "no blacklist", never to "proxy broken".

State file: /tmp/litellm_blacklist_state.json  (override: LITELLM_BLACKLIST_STATE)

CLI
---
  python3 tools/litellm_call_blacklist.py status    # who is blacklisted, for how many more calls
  python3 tools/litellm_call_blacklist.py clear     # un-blacklist everyone
  python3 tools/litellm_call_blacklist.py selftest  # offline logic test (no proxy needed)
  python3 tools/litellm_call_blacklist.py patchtest # Router-hook regression test (no proxy needed)
  python3 tools/litellm_call_blacklist.py stress --calls 40 --down 40   # live acceptance test

Env knobs
---------
  LITELLM_BLACKLIST_ENABLE=0        disable entirely
  LITELLM_BLACKLIST_CALLS=30        blacklist window, in client API calls
  LITELLM_BLACKLIST_STATE=<path>    state file location
"""
from __future__ import annotations

import fcntl
import json
import os
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# Importable without litellm so the CLI/selftest can run under system python.
try:  # pragma: no cover - depends on environment
    from litellm.integrations.custom_logger import CustomLogger  # type: ignore
except Exception:  # pragma: no cover
    class CustomLogger:  # type: ignore
        """Fallback shim so this module imports for CLI use without litellm."""


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except Exception:
        return default


STATE_PATH = Path(os.environ.get("LITELLM_BLACKLIST_STATE", "/tmp/litellm_blacklist_state.json"))
BLACKLIST_CALLS = _env_int("LITELLM_BLACKLIST_CALLS", 30)
ENABLED = os.environ.get("LITELLM_BLACKLIST_ENABLE", "1").lower() not in ("0", "false", "no", "off")

# Only these failure categories mean "the provider itself is unhealthy".
# `bad_request` / `other` are request-specific and must NOT blacklist a provider.
BLACKLIST_CATEGORIES = {
    "daily_quota_cf",
    "monthly_quota_hf",
    "dead_key",
    "rate_limit",
    "server_error",
    "quota",
}

# Endpoints that are not LLM calls -> don't advance the blacklist clock.
_NON_LLM_CALL_TYPES = {
    "models", "health", "health_readiness", "health_liveliness",
    "get_models", "list_models", "model_info", "model_group_info",
}

_lock = threading.RLock()

# Diagnostics: LITELLM_BLACKLIST_DEBUG=1 makes the router patch record every
# routing decision into the state file. Used to prove the patch is on the hot
# path. Off by default (it adds one file write per routing call).
DEBUG = os.environ.get("LITELLM_BLACKLIST_DEBUG", "0").lower() in ("1", "true", "yes", "on")

# Router-patch bookkeeping, surfaced by `python3 tools/litellm_call_blacklist.py status`.
_PATCH: Dict[str, Any] = {"installed": False, "attempts": 0, "classes": [], "last_error": None}


class _FileLock:
    """Cross-process exclusive lock so the read-modify-write of the state file
    (done by both the proxy and this CLI) cannot lose the other's updates."""

    def __init__(self, path: Any) -> None:
        self._path = Path(str(path) + ".lock")
        self._fh = None

    def __enter__(self):
        try:
            self._fh = open(self._path, "a+")
            fcntl.flock(self._fh, fcntl.LOCK_EX)
        except Exception:
            self._fh = None
        return self

    def __exit__(self, *exc):
        if self._fh is not None:
            try:
                fcntl.flock(self._fh, fcntl.LOCK_UN)
                self._fh.close()
            except Exception:
                pass
        return False


def _save_debug(st: Dict[str, Any], healthy: List[Dict], kept: List[Dict], all_deps: List[Dict],
                hook: str = "?", model: Any = None) -> None:
    try:
        dbg = st.setdefault("debug", {}).setdefault(hook, {})
        dbg["model"] = str(model)
        dbg["patched_calls"] = int(dbg.get("patched_calls", 0)) + 1
        dbg["last_healthy"] = len(healthy)
        dbg["last_kept"] = len(kept)
        dbg["last_filtered_out"] = len(healthy) - len(kept)
        dbg["blacklisted_keys"] = len(st.get("entries") or {})
        dbg["sample_deployment_ids"] = [str((d.get("model_info") or {}).get("id"))[:16] for d in all_deps[:3]]
        dbg["kept_ids"] = [str((d.get("model_info") or {}).get("id"))[:16] for d in kept[:3]]
        # Full internal id set — lets an operator diff it against /v1/model/info.
        dbg["all_deployment_ids"] = [str((d.get("model_info") or {}).get("id")) for d in all_deps if isinstance(d, dict)]
        # What the filter itself saw (diagnoses key/expiry mismatches).
        ent = st.get("entries") or {}
        dbg["seq_at_filter"] = int(st.get("call_seq", 0))
        dbg["n_entries_seen"] = len(ent)
        dbg["sample_entry_keys"] = list(ent)[:2]
        dbg["sample_until_seq"] = [ent[k].get("until_seq") for k in list(ent)[:2]]
        dbg["sample_computed_keys"] = [
            _keys_for_deployment(d)[0] for d in all_deps[:2] if isinstance(d, dict)
        ]
        _save(st)
    except Exception:
        pass


def _note_fail_open(st: Dict[str, Any], healthy: List[Dict], hook: str, model: Any) -> None:
    """Record that the blacklist was overridden because parking would have
    emptied the candidate pool. Fail-open is deliberate (a request must still
    be attempted), but it must be OBSERVABLE: it means every healthy candidate
    for this group is parked, so a parked provider may get traffic again."""
    try:
        fo = st.setdefault("fail_open", {"count": 0})
        fo["count"] = int(fo.get("count", 0)) + 1
        fo["last_model"] = str(model)
        fo["last_hook"] = hook
        fo["last_healthy"] = len(healthy)
        fo["last_ts"] = _now()
        _save(st)
        print(f"[call_blacklist] FAIL-OPEN: every candidate for '{model}' is parked "
              f"({len(healthy)} deployments) - routing to them anyway", file=sys.stderr, flush=True)
    except Exception:
        pass
try:
    from tools.litellm_smart_cooldown import _classify as _classify  # type: ignore
except Exception:  # pragma: no cover - path fallback
    try:
        from litellm_smart_cooldown import _classify as _classify  # type: ignore
    except Exception:
        def _classify(exc: Optional[BaseException], api_base: Optional[str]) -> tuple:
            msg = (str(exc) if exc else "").lower()
            if "429" in msg or "rate limit" in msg or "quota" in msg:
                return "rate_limit", 300
            if any(c in msg for c in ("500", "502", "503", "504", "internal server")):
                return "server_error", 60
            if "401" in msg or "invalid api key" in msg or "out of funds" in msg or "balance" in msg:
                return "dead_key", 86400
            return "other", 0


# ---------------------------------------------------------------------------
# state
# ---------------------------------------------------------------------------
def _now() -> float:
    return time.time()


def _blank_state() -> Dict[str, Any]:
    return {"version": 1, "call_seq": 0, "entries": {}, "router_patched": False}


def _load() -> Dict[str, Any]:
    try:
        st = json.loads(STATE_PATH.read_text())
        if isinstance(st, dict) and "entries" in st:
            st.setdefault("call_seq", 0)
            return st
    except Exception:
        pass
    return _blank_state()


def _save(st: Dict[str, Any]) -> None:
    try:
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp = STATE_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(st, indent=2, default=str))
        tmp.replace(STATE_PATH)
    except Exception:
        pass


def _prune(st: Dict[str, Any]) -> Dict[str, Any]:
    seq = int(st.get("call_seq", 0))
    st["entries"] = {
        k: v for k, v in (st.get("entries") or {}).items()
        if seq < int(v.get("until_seq", 0))
    }
    return st


# ---------------------------------------------------------------------------
# deployment keys
# ---------------------------------------------------------------------------
def _composite(group: Any, model: Any, api_base: Any) -> str:
    return f"{group or '?'}|{model or '?'}|{api_base or ''}"


def _keys_for_deployment(d: Dict[str, Any]) -> List[str]:
    keys: List[str] = []
    mid = (d.get("model_info") or {}).get("id")
    if mid:
        keys.append(f"id:{mid}")
    lp = d.get("litellm_params") or {}
    keys.append(_composite(d.get("model_name"), lp.get("model"), lp.get("api_base")))
    return keys


def _keys_for_failure(kwargs: Dict[str, Any]) -> List[str]:
    keys: List[str] = []
    lp = kwargs.get("litellm_params") or {}
    mid = kwargs.get("model_id") or (lp.get("model_info") or {}).get("id")
    if mid:
        keys.append(f"id:{mid}")
    keys.append(_composite(
        kwargs.get("model") or lp.get("model_name"),
        lp.get("model"),
        lp.get("api_base") or kwargs.get("api_base"),
    ))
    return keys


# ---------------------------------------------------------------------------
# counter + blacklist ops
# ---------------------------------------------------------------------------
def advance_call_counter(n: int = 1) -> int:
    if not ENABLED:
        return 0
    with _lock, _FileLock(STATE_PATH):
        st = _prune(_load())
        st["call_seq"] = int(st.get("call_seq", 0)) + n
        _save(st)
        return int(st["call_seq"])


def should_count_call(call_type: Any) -> bool:
    ct = (call_type or "").lower()
    if not ct:
        return True  # unknown -> count, so entries always expire
    return ct not in _NON_LLM_CALL_TYPES


def blacklist_keys(keys: List[str], category: str, error: str, calls: Optional[int] = None) -> int:
    """Blacklist `keys` for the next `calls` client requests. Returns until_seq."""
    if not ENABLED or not keys:
        return 0
    n = BLACKLIST_CALLS if calls is None else calls
    with _lock, _FileLock(STATE_PATH):
        st = _prune(_load())
        seq = int(st.get("call_seq", 0))
        until = seq + n
        for k in keys:
            e = st["entries"].get(k) or {}
            e.update({
                "until_seq": until,
                "remaining_calls": n,
                "category": category,
                "last_error": (error or "")[:300],
                "blacklisted_at": _now(),
                "hits": int(e.get("hits", 0)) + 1,
            })
            st["entries"][k] = e
        _save(st)
        return until


def _is_blacklisted_with(st: Dict[str, Any], keys: List[str]) -> bool:
    seq = int(st.get("call_seq", 0))
    entries = st.get("entries") or {}
    for k in keys:
        e = entries.get(k)
        if e and seq < int(e.get("until_seq", 0)):
            return True
    return False


def is_blacklisted_deployment(d: Dict[str, Any], st: Optional[Dict[str, Any]] = None) -> bool:
    if not ENABLED:
        return False
    return _is_blacklisted_with(st if st is not None else _load(), _keys_for_deployment(d))


def record_failure(kwargs: Dict[str, Any]) -> Optional[str]:
    """Blacklist the failing deployment if its error category means 'provider down'."""
    if not ENABLED:
        return None
    try:
        lp = kwargs.get("litellm_params") or {}
        api_base = lp.get("api_base") or kwargs.get("api_base")
        exc = kwargs.get("exception")
        category, _cooldown_s = _classify(exc, api_base)
        if category not in BLACKLIST_CATEGORIES:
            return None
        blacklist_keys(_keys_for_failure(kwargs), category, str(exc) if exc else "")
        return category
    except Exception:
        return None


def clear_all() -> int:
    with _lock, _FileLock(STATE_PATH):
        st = _load()
        n = len(st.get("entries") or {})
        st["entries"] = {}
        st.pop("fail_open", None)
        _save(st)
        return n


# ---------------------------------------------------------------------------
# Router patch — filter blacklisted deployments out of the candidate pool
# ---------------------------------------------------------------------------
def _resolve_router_classes() -> List[type]:
    """Best-effort resolution of the Router class(es) actually in use.

    The proxy may import this module while `litellm` is still partially
    initialised (so `litellm.Router` does not exist yet), therefore we try
    several sources and retry lazily on the first request.
    """
    found: List[type] = []

    def _add(obj: Any) -> None:
        try:
            if obj is not None and hasattr(obj, "_async_get_healthy_deployments") and obj not in found:
                found.append(obj)
        except Exception:
            pass

    # 1. the live proxy router instance — most reliable once serving
    try:
        from litellm.proxy.proxy_server import llm_router  # type: ignore
        if llm_router is not None:
            _add(type(llm_router))
    except Exception as exc:
        _PATCH["last_error"] = f"proxy_server: {exc}"

    # 2/3. the class itself via both common import paths
    try:
        import litellm  # type: ignore
        _add(getattr(litellm, "Router", None))
    except Exception as exc:
        _PATCH["last_error"] = f"import litellm: {exc}"
    try:
        from litellm.router import Router as _Router  # type: ignore
        _add(_Router)
    except Exception as exc:
        _PATCH["last_error"] = f"litellm.router: {exc}"

    return found


def _make_list_filter(original):
    """Wrapper for `async_get_healthy_deployments` (returns a LIST — this is the
    method the PRIMARY routing path uses)."""

    async def _patched(self, *args, _orig=original, **kwargs):  # type: ignore[no-untyped-def]
        healthy = await _orig(self, *args, **kwargs)
        model_name = kwargs.get("model") or (args[0] if args else None)
        try:
            if ENABLED and isinstance(healthy, list) and healthy:
                st = _load()
                kept = [d for d in healthy if not is_blacklisted_deployment(d, st)]
                # FAIL-OPEN: never let the blacklist empty the pool.
                if kept and len(kept) < len(healthy):
                    if DEBUG:
                        _save_debug(st, healthy, kept, healthy, "list", model_name)
                    return kept
                if not kept:
                    _note_fail_open(st, healthy, "list", model_name)
                if DEBUG:
                    _save_debug(st, healthy, kept or healthy, healthy, "list", model_name)
        except Exception:
            pass
        return healthy

    return _patched


def _make_tuple_filter(original):
    """Wrapper for `_async_get_healthy_deployments` (returns a (healthy, all) TUPLE
    — used by the retry / fallback and scheduler paths)."""

    async def _patched(self, *args, _orig=original, **kwargs):  # type: ignore[no-untyped-def]
        healthy, all_deployments = await _orig(self, *args, **kwargs)
        model_name = kwargs.get("model") or (args[0] if args else None)
        try:
            if ENABLED and healthy:
                st = _load()
                kept = [d for d in healthy if not is_blacklisted_deployment(d, st)]
                # FAIL-OPEN: never let the blacklist empty the pool.
                if kept and len(kept) < len(healthy):
                    if DEBUG:
                        _save_debug(st, healthy, kept, all_deployments, "tuple", model_name)
                    return kept, all_deployments
                if not kept:
                    _note_fail_open(st, healthy, "tuple", model_name)
                if DEBUG:
                    _save_debug(st, healthy, kept or healthy, all_deployments, "tuple", model_name)
        except Exception:
            pass
        return healthy, all_deployments

    return _patched


# Both must be patched: `async_get_healthy_deployments` drives the primary
# selection, `_async_get_healthy_deployments` drives retries/fallbacks.
_PATCH_TARGETS = (
    ("async_get_healthy_deployments", _make_list_filter),
    ("_async_get_healthy_deployments", _make_tuple_filter),
)


def install_router_patch() -> bool:
    """Patch Router so blacklisted deployments never reach the routing strategy.

    Idempotent, never raises, and safe to call repeatedly — it is also retried
    lazily on the first request in case the import-time attempt ran before
    `litellm.Router` existed.
    """
    if _PATCH["installed"]:
        return True
    _PATCH["attempts"] = int(_PATCH["attempts"]) + 1

    classes = _resolve_router_classes()
    if not classes:
        return False

    patched: List[str] = []
    for cls in classes:
        if getattr(cls, "_call_blacklist_patched", False):
            patched.append(f"{cls.__module__}.{cls.__name__}")
            continue
        done: List[str] = []
        for attr, maker in _PATCH_TARGETS:
            original = getattr(cls, attr, None)
            if original is None:
                continue
            try:
                setattr(cls, attr, maker(original))
                done.append(attr)
            except Exception as exc:
                _PATCH["last_error"] = f"patch {cls.__name__}.{attr}: {exc}"
        if done:
            cls._call_blacklist_patched = True  # type: ignore[attr-defined]
            patched.append(f"{cls.__module__}.{cls.__name__}[{', '.join(done)}]")

    if patched:
        _PATCH["installed"] = True
        _PATCH["classes"] = patched
        try:
            print(f"[call_blacklist] router patch installed on {patched}", file=sys.stderr, flush=True)
        except Exception:
            pass
        try:
            st = _load()
            st["router_patched"] = True
            st["blacklist_calls"] = BLACKLIST_CALLS
            _save(st)
        except Exception:
            pass
    return bool(patched)


# ---------------------------------------------------------------------------
# LiteLLM CustomLogger
# ---------------------------------------------------------------------------
class _CallBlacklist(CustomLogger):
    async def async_pre_call_hook(self, user_api_key_dict, cache, data, call_type):  # noqa: ANN001
        # Count one client API call. Return None => LiteLLM leaves `data` untouched.
        try:
            # Retry the patch here: the config loader may have imported this
            # module before `litellm.Router` existed.
            if not _PATCH["installed"]:
                install_router_patch()
            if should_count_call(call_type):
                advance_call_counter(1)
        except Exception:
            pass
        return None

    async def async_log_failure_event(self, kwargs, response_obj, start_time, end_time):  # noqa: ANN001
        try:
            record_failure(kwargs)
        except Exception:
            pass

    def log_failure_event(self, kwargs, response_obj, start_time, end_time):  # noqa: ANN001
        try:
            record_failure(kwargs)
        except Exception:
            pass


call_blacklist = _CallBlacklist()

# Install at import time: LiteLLM imports this module while loading the config,
# which happens before the proxy starts serving.
ROUTER_PATCHED = install_router_patch()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _status() -> None:
    st = _load()
    seq = int(st.get("call_seq", 0))
    entries = _prune(st).get("entries") or {}
    print(f"blacklist enabled : {ENABLED}")
    print(f"window            : {BLACKLIST_CALLS} calls")
    print(f"call_seq          : {seq}")
    print(f"state file        : {STATE_PATH}")
    print(f"router patch      : installed={_PATCH['installed']} attempts={_PATCH['attempts']} "
          f"classes={_PATCH['classes']}")
    if _PATCH.get("last_error"):
        print(f"  last patch error: {_PATCH['last_error']}")
    dbg = st.get("debug")
    if dbg:
        print(f"debug             : patched_calls={dbg.get('patched_calls')} "
              f"last_healthy={dbg.get('last_healthy')} last_kept={dbg.get('last_kept')} "
              f"last_filtered_out={dbg.get('last_filtered_out')}")
        print(f"  sample ids      : {dbg.get('sample_deployment_ids')}")
        print(f"  kept ids        : {dbg.get('kept_ids')}")
    fo = st.get("fail_open")
    if fo:
        print(f"fail_open         : count={fo.get('count')} last_model={fo.get('last_model')} "
              f"last_hook={fo.get('last_hook')} last_healthy={fo.get('last_healthy')}")
    if not entries:
        print("blacklisted       : (none)")
        return
    print(f"blacklisted       : {len(entries)}")
    for k, v in sorted(entries.items(), key=lambda kv: kv[1].get("until_seq", 0), reverse=True):
        remaining = max(0, int(v.get("until_seq", 0)) - seq)
        print(f"  - {k}\n      category={v.get('category')} remaining_calls={remaining} "
              f"hits={v.get('hits')} err={(v.get('last_error') or '')[:90]}")


def _selftest() -> int:
    import tempfile
    global STATE_PATH, ENABLED, BLACKLIST_CALLS
    failures = []

    tmp = Path(tempfile.mkdtemp()) / "bl.json"
    orig = (STATE_PATH, ENABLED, BLACKLIST_CALLS)
    STATE_PATH, ENABLED, BLACKLIST_CALLS = tmp, True, 30
    try:
        dep = {
            "model_name": "free-mode",
            "litellm_params": {"model": "groq/llama-3.1-8b-instant", "api_base": None},
            "model_info": {"id": "dep-abc123"},
        }
        other = {
            "model_name": "free-mode",
            "litellm_params": {"model": "gemini/gemini-2.5-flash", "api_base": None},
            "model_info": {"id": "dep-xyz789"},
        }

        # 1. not blacklisted initially
        if is_blacklisted_deployment(dep):
            failures.append("fresh deployment should not be blacklisted")

        # 2. a provider-down failure blacklists it (id key path)
        record_failure({
            "model": "free-mode",
            "model_id": "dep-abc123",
            "litellm_params": {"model": "groq/llama-3.1-8b-instant", "api_base": None},
            "exception": Exception("Error code: 429 - rate limit exceeded"),
        })
        if not is_blacklisted_deployment(dep):
            failures.append("deployment should be blacklisted after 429")

        # 3. sibling deployment unaffected
        if is_blacklisted_deployment(other):
            failures.append("unrelated deployment must not be blacklisted")

        # 4. request-specific errors must NOT blacklist
        record_failure({
            "model": "free-mode", "model_id": "dep-xyz789",
            "litellm_params": {"model": "gemini/gemini-2.5-flash"},
            "exception": Exception("Error code: 400 - invalid request, context window exceeded"),
        })
        if is_blacklisted_deployment(other):
            failures.append("400/context-window must not blacklist a provider")

        # 5. expires after exactly 30 counted calls
        for _ in range(29):
            advance_call_counter(1)
        if not is_blacklisted_deployment(dep):
            failures.append("should still be blacklisted after 29 calls")
        advance_call_counter(1)
        if is_blacklisted_deployment(dep):
            failures.append("should expire after 30 calls")

        # 6. composite-key path (no model_id in failure kwargs)
        dep2 = {
            "model_name": "paid-mode",
            "litellm_params": {"model": "openai/mimo-v2.5-pro", "api_base": "https://x/v1"},
            "model_info": {"id": "dep-composite"},
        }
        record_failure({
            "model": "paid-mode",
            "litellm_params": {"model": "openai/mimo-v2.5-pro", "api_base": "https://x/v1"},
            "exception": Exception("Error code: 401 - invalid api key"),
        })
        if not is_blacklisted_deployment(dep2):
            failures.append("composite-key blacklist path failed")
    finally:
        STATE_PATH, ENABLED, BLACKLIST_CALLS = orig

    if failures:
        print("SELFTEST FAILED:")
        for f in failures:
            print("  x", f)
        return 1
    print("SELFTEST PASSED (6/6 checks)")
    return 0


def _patchtest() -> int:
    """Deterministic regression test for the Router patch (no proxy needed).

    Covers the exact bug that cost hours: the PRIMARY routing path calls
    `async_get_healthy_deployments` (returns a LIST), while retries and the
    scheduler call `_async_get_healthy_deployments` (returns a TUPLE).
    Patching only the underscore variant filters nothing for normal traffic.
    """
    import asyncio
    import tempfile

    global STATE_PATH, ENABLED
    orig = (STATE_PATH, ENABLED)
    STATE_PATH, ENABLED = Path(tempfile.mkdtemp()) / "patchtest.json", True
    failures: List[str] = []
    try:
        try:
            import litellm  # type: ignore
        except Exception as exc:
            print(f"PATCHTEST SKIPPED: litellm not importable ({exc})")
            return 0
        if not install_router_patch():
            print("PATCHTEST FAILED: install_router_patch() returned False")
            return 1

        router = litellm.Router(model_list=[
            {"model_name": "grp", "litellm_params": {"model": "openai/m-a", "api_key": "sk-x", "api_base": "https://a.example/v1"}},
            {"model_name": "grp", "litellm_params": {"model": "openai/m-b", "api_key": "sk-x", "api_base": "https://b.example/v1"}},
            {"model_name": "grp", "litellm_params": {"model": "openai/m-c", "api_key": "sk-x", "api_base": "https://c.example/v1"}},
        ])

        def _ids(deployments: List[Dict[str, Any]]) -> List[str]:
            return sorted(d["model_info"]["id"] for d in deployments)

        async def _run() -> None:
            # --- primary path: LIST method (the one that was originally missed) ---
            pool = await router.async_get_healthy_deployments("grp", {})
            if not isinstance(pool, list) or len(pool) != 3:
                failures.append(f"primary(list): expected pool of 3, got {len(pool) if isinstance(pool, list) else type(pool).__name__}")
                return
            victim = pool[0]
            blacklist_keys(_keys_for_deployment(victim), "dead_key", "patchtest")

            pool2 = await router.async_get_healthy_deployments("grp", {})
            if victim["model_info"]["id"] in _ids(pool2):
                failures.append("primary(list): blacklisted deployment STILL routed (two-method bug)")
            if len(pool2) != 2:
                failures.append(f"primary(list): expected pool of 2, got {len(pool2)}")

            # --- retry / scheduler path: TUPLE method ---
            healthy, all_deps = await router._async_get_healthy_deployments("grp", None)
            if victim["model_info"]["id"] in _ids(healthy):
                failures.append("retry(tuple): blacklisted deployment STILL routed")
            if len(all_deps) != 3:
                failures.append(f"retry(tuple): expected 3 total deployments, got {len(all_deps)}")

            # --- FAIL-OPEN: park everything, the pool must not be emptied ---
            for d in all_deps:
                blacklist_keys(_keys_for_deployment(d), "dead_key", "patchtest-all")
            if not await router.async_get_healthy_deployments("grp", {}):
                failures.append("fail-open: list pool was emptied by the blacklist")
            h2, _ = await router._async_get_healthy_deployments("grp", None)
            if not h2:
                failures.append("fail-open: tuple pool was emptied by the blacklist")

        try:
            asyncio.run(_run())
        except Exception as exc:
            failures.append(f"exception: {type(exc).__name__}: {exc}")
    finally:
        STATE_PATH, ENABLED = orig

    if failures:
        print("PATCHTEST FAILED:")
        for f in failures:
            print("  x", f)
        return 1
    print("PATCHTEST PASSED (primary list hook + retry tuple hook + fail-open)")
    return 0


def _stress(calls: int, model: str, max_consec_fail: int, down: int) -> int:
    """Acceptance test: `calls` consecutive calls must all succeed and never
    produce a run of `max_consec_fail` consecutive failures.

    `--down K` first blacklists K deployments of `model`, simulating providers
    being down, so the run proves the blacklist keeps users working.
    """
    import urllib.request

    base = os.environ.get("LITELLM_STRESS_URL", "http://localhost:4000")

    def _get_json(url: str, data: Any = None, timeout: int = 150):
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode() if data is not None else None,
            headers={"Content-Type": "application/json", "Authorization": "Bearer anything"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode()), dict(r.headers)

    injected: List[str] = []
    try:
        # Start from a clean slate so the reported fail-open count is per-run.
        clear_all()
        if down > 0:
            info, _ = _get_json(base + "/v1/model/info")
            ids = [d["model_info"]["id"] for d in info["data"] if d.get("model_name") == model]
            injected = ids[:down]
            for did in injected:
                blacklist_keys([f"id:{did}"], "stress_test", "simulated down")
            print(f"simulated {len(injected)}/{len(ids)} '{model}' deployments as down")

        ok_count = 0
        consec = 0
        max_consec = 0
        for i in range(calls):
            ok = False
            exc_txt = ""
            try:
                _get_json(base + "/v1/chat/completions",
                          {"model": model, "messages": [{"role": "user", "content": "say ok"}],
                           "max_tokens": 8})
                ok = True
            except Exception as exc:
                exc_txt = f"{type(exc).__name__}: {str(exc)[:70]}"
            if ok:
                ok_count += 1
                consec = 0
            else:
                consec += 1
                max_consec = max(max_consec, consec)
            print(f"  call {i+1:>3}/{calls}: {'OK  ' if ok else 'FAIL'} "
                  f"(ok={ok_count} consec_fail={consec}){('  ' + exc_txt) if exc_txt else ''}")
            if consec >= max_consec_fail:
                print(f"ABORT: {consec} consecutive failures (limit {max_consec_fail})")
                break

        passed = (ok_count == calls) and (max_consec < max_consec_fail)
        fo = (_load().get("fail_open") or {}).get("count", 0)
        print(f"\nRESULT: successes={ok_count}/{calls} "
              f"max_consecutive_failures={max_consec} (limit {max_consec_fail}) "
              f"fail_open_overrides={fo} "
              f"-> {'PASS' if passed else 'FAIL'}")
        return 0 if passed else 1
    finally:
        n = clear_all()
        print(f"cleanup: cleared {n} blacklist entr(ies)")


def main(argv: List[str]) -> int:
    args = argv[1:]
    cmd = args[0] if args else "status"
    opts: Dict[str, str] = {}
    i = 1
    while i < len(args):
        if args[i].startswith("--") and i + 1 < len(args):
            opts[args[i][2:]] = args[i + 1]
            i += 2
        else:
            i += 1

    if cmd == "status":
        _status()
        return 0
    if cmd == "clear":
        print(f"cleared {clear_all()} blacklist entr(ies)")
        return 0
    if cmd == "selftest":
        return _selftest()
    if cmd == "patchtest":
        return _patchtest()
    if cmd == "stress":
        return _stress(
            calls=int(opts.get("calls", 40)),
            model=opts.get("model", "free-mode"),
            max_consec_fail=int(opts.get("max-consec-fail", 3)),
            down=int(opts.get("down", 0)),
        )
    if cmd == "patch":
        ok = install_router_patch()
        print("router patch installed:", ok, _PATCH)
        return 0 if ok else 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
