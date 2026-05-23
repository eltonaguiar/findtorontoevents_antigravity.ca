"""Namespaced state helper for circuit-breaker-style JSON state files.

Prevents the stale-state leak documented in memory
``feedback_circuit_breaker_stale_state_leak`` (2026-04-27 incident:
``circuit_breaker_state.json`` leaked ``max_picks=0`` for ~115h on
``alpha_engine_fast``). Each namespace carries a write timestamp and a
TTL; expired namespaces are ignored on read instead of contributing
sticky min/max values.

Schema::

    {
      "schema_version": "v1",
      "namespaces": {
        "<key>": {
          "data": { ... arbitrary ... },
          "written_at": "<UTC ISO>",
          "ttl_seconds": 3600
        }
      }
    }

Read path returns ``None`` when a namespace is missing or its
``written_at`` + ``ttl_seconds`` is in the past. Callers MUST treat
``None`` as "no usable state" — never fall back to a min(0, ...) /
max(0, ...) pattern, that is precisely the bug this prevents.

Intentionally sidecar (no production caller in this commit).

Wiring Plan (per CLAUDE.md Wire-Up Rule):
    Target caller: ``alpha_engine/drift_circuit_breaker.py`` (mimo PR,
    not yet merged).  Expected PR/date: after #961 + #942 land, in a
    subsequent split PR; this module ships ahead so the namespace
    contract is reviewable independently of the drift breaker logic.
    Until that PR opens, this module is exercised only by
    ``tests/test_breaker_namespaces.py``.

NFA. Read-only by default. The write helper is opt-in and never auto-
loaded.
"""
from __future__ import annotations
import json
import os
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "v1"
DEFAULT_TTL_SECONDS = 3600

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_STATE_PATH = REPO_ROOT / "alpha_engine" / "data" / "breaker_namespaced_state.json"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_ts(ts: str) -> datetime | None:
    if not ts:
        return None
    try:
        # Tolerate both "Z" suffix and explicit offset
        if ts.endswith("Z"):
            ts = ts[:-1] + "+00:00"
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


def _load_raw(path: Path) -> dict:
    if not path.exists():
        return {"schema_version": SCHEMA_VERSION, "namespaces": {}}
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"schema_version": SCHEMA_VERSION, "namespaces": {}}
    if not isinstance(d, dict) or "namespaces" not in d:
        return {"schema_version": SCHEMA_VERSION, "namespaces": {}}
    return d


def _is_expired(entry: dict, now: datetime) -> bool:
    ts = _parse_ts(entry.get("written_at", ""))
    if ts is None:
        return True
    ttl = entry.get("ttl_seconds")
    if not isinstance(ttl, (int, float)) or ttl <= 0:
        ttl = DEFAULT_TTL_SECONDS
    return now > ts + timedelta(seconds=ttl)


def read_namespace(name: str, path: Path | None = None,
                   now: datetime | None = None) -> dict | None:
    """Return ``data`` payload for namespace, or ``None`` if missing/expired.

    Never returns partial / stale data. Callers must defensive-default
    on ``None``, NOT fall through to a sticky min/max merge.
    """
    p = path or DEFAULT_STATE_PATH
    raw = _load_raw(p)
    entry = (raw.get("namespaces") or {}).get(name)
    if not isinstance(entry, dict):
        return None
    if _is_expired(entry, now or _now()):
        return None
    data = entry.get("data")
    if not isinstance(data, dict):
        return None
    return data


def write_namespace(name: str, data: dict, ttl_seconds: int = DEFAULT_TTL_SECONDS,
                    path: Path | None = None,
                    now: datetime | None = None) -> Path:
    """Write ``data`` under ``name`` with ``ttl_seconds``.

    Atomic: write-then-rename. Does NOT touch other namespaces.
    """
    if not isinstance(data, dict):
        raise TypeError("data must be dict")
    if not isinstance(ttl_seconds, int) or ttl_seconds <= 0:
        raise ValueError("ttl_seconds must be positive int")
    p = path or DEFAULT_STATE_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    raw = _load_raw(p)
    raw.setdefault("schema_version", SCHEMA_VERSION)
    namespaces = raw.setdefault("namespaces", {})
    namespaces[name] = {
        "data": data,
        "written_at": (now or _now()).isoformat(),
        "ttl_seconds": ttl_seconds,
    }
    # Atomic write
    fd, tmp = tempfile.mkstemp(prefix=p.name + ".", dir=str(p.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(raw, f, indent=2)
        os.replace(tmp, p)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    return p


def list_namespaces(path: Path | None = None,
                    now: datetime | None = None) -> dict[str, str]:
    """Returns ``{name: status}`` where status is 'fresh' or 'expired'."""
    p = path or DEFAULT_STATE_PATH
    raw = _load_raw(p)
    cur = now or _now()
    out: dict[str, str] = {}
    for name, entry in (raw.get("namespaces") or {}).items():
        if not isinstance(entry, dict):
            continue
        out[name] = "expired" if _is_expired(entry, cur) else "fresh"
    return out


def purge_expired(path: Path | None = None,
                  now: datetime | None = None) -> int:
    """Delete expired namespaces from the state file. Returns count removed.

    Safe to call periodically (e.g. once per dashboard refresh).
    """
    p = path or DEFAULT_STATE_PATH
    if not p.exists():
        return 0
    raw = _load_raw(p)
    cur = now or _now()
    ns = raw.get("namespaces") or {}
    keep = {k: v for k, v in ns.items() if isinstance(v, dict) and not _is_expired(v, cur)}
    removed = len(ns) - len(keep)
    if removed > 0:
        raw["namespaces"] = keep
        fd, tmp = tempfile.mkstemp(prefix=p.name + ".", dir=str(p.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(raw, f, indent=2)
            os.replace(tmp, p)
        except Exception:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise
    return removed
