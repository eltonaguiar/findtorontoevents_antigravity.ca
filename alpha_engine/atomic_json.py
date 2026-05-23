"""Atomic JSON read/write helpers — cross-platform, stdlib-only.

Solves three production hazards observed across this codebase:

1. **Partial-read race:** worker A is writing strategy_performance.json (multi-MB
   file) while worker B reads it -> B sees malformed JSON -> JSONDecodeError
   propagates up the scan pipeline. `atomic_write_json` uses temp file + `os.replace`
   so readers always see EITHER the old file OR the new file, never a mix.

2. **Overwrite-loses-history:** elite_scorer.rebuild_strategy_performance() rebuilds
   the file from currently-scanned strategies, dropping 111 of 161 historical entries
   per cycle (354k-line git churn, see updates/2026-04-17-alpha-engine-data-loss-bug.md).
   `merge_write_json` reads existing -> merges new on top -> writes atomic. Caller can
   opt in to merge semantics without changing default rebuild behavior.

3. **Stale entries forever:** without pruning, merged files grow unbounded. `prune_stale`
   drops entries with last-seen timestamps older than N days.

Cross-platform: relies on `os.replace()` which is POSIX-atomic on Linux and atomic
on Windows since Python 3.3. No pip dependencies.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import tempfile
from pathlib import Path
from typing import Any


def read_json(path: str | Path, default: Any = None) -> Any:
    """Read JSON; return `default` (or {} if not provided) on missing/corrupt file."""
    p = Path(path)
    fallback = {} if default is None else default
    if not p.exists():
        return fallback
    try:
        text = p.read_text(encoding="utf-8")
        if not text.strip():
            return fallback
        return json.loads(text)
    except (json.JSONDecodeError, OSError):
        return fallback


def atomic_write_json(path: str | Path, data: Any, indent: int = 2) -> None:
    """Atomically write JSON via temp-file + os.replace.

    Guarantees no concurrent reader sees a partially-written file.
    Temp file lives in the same directory as the target so the rename is on
    the same filesystem (cross-device renames are NOT atomic).
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = tempfile.NamedTemporaryFile(
        mode="w",
        dir=str(p.parent),
        prefix=p.name + ".",
        suffix=".tmp",
        delete=False,
        encoding="utf-8",
    )
    try:
        json.dump(data, tmp, indent=indent, default=str)
        tmp.flush()
        try:
            os.fsync(tmp.fileno())
        except OSError:
            pass  # not fatal; some filesystems (e.g. some Windows network mounts) reject fsync
        tmp.close()
        os.replace(tmp.name, p)
    except Exception:
        # Clean up temp file on any failure
        try:
            tmp.close()
        except Exception:
            pass
        try:
            os.unlink(tmp.name)
        except OSError:
            pass
        raise


def merge_write_json(
    path: str | Path,
    new_data: dict,
    *,
    indent: int = 2,
    stamp_field: str | None = "last_seen",
) -> dict:
    """Read-modify-write: merge `new_data` into existing JSON dict. New keys win.

    If `stamp_field` is not None, every key in new_data gets its dict value's
    `stamp_field` set to ISO-UTC-now. This enables `prune_stale` later.

    Returns the merged dict (also written to disk).
    """
    if not isinstance(new_data, dict):
        raise TypeError(f"new_data must be dict, got {type(new_data).__name__}")
    existing = read_json(path, default={})
    if not isinstance(existing, dict):
        existing = {}
    if stamp_field is not None:
        now_iso = _dt.datetime.now(_dt.timezone.utc).isoformat()
        for k, v in new_data.items():
            if isinstance(v, dict):
                v.setdefault(stamp_field, now_iso)
                v[stamp_field] = now_iso  # always update on merge
    merged = {**existing, **new_data}
    atomic_write_json(path, merged, indent=indent)
    return merged


def prune_stale(
    data: dict,
    *,
    max_age_days: int,
    ts_field: str = "last_seen",
    now: _dt.datetime | None = None,
) -> dict:
    """Drop entries where data[k][ts_field] is older than max_age_days.

    Entries without a timestamp, with an unparseable timestamp, or where the
    value isn't a dict are KEPT (defensive — pruning should never silently
    delete data we don't understand).
    """
    if now is None:
        now = _dt.datetime.now(_dt.timezone.utc)
    cutoff = now - _dt.timedelta(days=max_age_days)
    pruned: dict = {}
    for k, v in data.items():
        if not isinstance(v, dict):
            pruned[k] = v
            continue
        ts = v.get(ts_field)
        if not isinstance(ts, str):
            pruned[k] = v
            continue
        try:
            # Accept both 'Z' suffix and '+00:00' style
            normalized = ts.replace("Z", "+00:00") if ts.endswith("Z") else ts
            ts_dt = _dt.datetime.fromisoformat(normalized)
            if ts_dt.tzinfo is None:
                ts_dt = ts_dt.replace(tzinfo=_dt.timezone.utc)
            if ts_dt >= cutoff:
                pruned[k] = v
            # else: drop (older than cutoff)
        except (ValueError, TypeError):
            pruned[k] = v  # unparseable -> keep
    return pruned
