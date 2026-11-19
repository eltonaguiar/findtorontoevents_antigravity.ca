"""audit3_denylist.py — make the kill tribunal an emission gate, not a web page.

The tribunal's own review said it best: "a tribunal that reports kills while the
emitter never reads it is theatre." This module is the read path. It loads
`audit_dashboard/data/audit3_ledger.json` and answers one question about a
candidate pick — is this cell a proven-harm cell?

Scope rules, all deliberate:

* **Direction-aware.** audit3 kills cells, not brands. On the 2026-11-19 ledger
  `luxalgo_confluence` is KILL LONG and PROVEN SHORT; blocking the name would
  discard the side that survived.
* **Strategy and symbol scope only.** Class-scope KILLs (CRYPTO, COMMODITY) are
  real findings, but suspending a whole asset class is a policy decision. Opt in
  with `AUDIT3_DENYLIST_INCLUDE_CLASS=1`.
* **Fail-open.** A missing, stale (`AUDIT3_DENYLIST_MAX_AGE_DAYS`, default 14) or
  malformed ledger denies nothing and reports why. An audit artifact must never
  be able to silently halt every emitter.
* **Kill switch.** `AUDIT3_DENYLIST_DISABLED=1` bypasses everything.

Usage from the emission path::

    if denied_reason(pick):
        return False
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from alpha_engine.symbol_identity import canonical_symbol, direction_key

DEFAULT_LEDGER = "audit_dashboard/data/audit3_ledger.json"
MAX_AGE_DAYS = 14
_CACHE: dict[str, Any] = {"key": None, "index": None, "note": ""}


def _disabled() -> bool:
    return (os.environ.get("AUDIT3_DENYLIST_DISABLED") or "").strip().lower() in (
        "1", "true", "yes", "on")


def _include_class() -> bool:
    return (os.environ.get("AUDIT3_DENYLIST_INCLUDE_CLASS") or "").strip().lower() in (
        "1", "true", "yes", "on")


def _max_age_days() -> float:
    try:
        return float(os.environ.get("AUDIT3_DENYLIST_MAX_AGE_DAYS") or MAX_AGE_DAYS)
    except (TypeError, ValueError):
        return MAX_AGE_DAYS


def _parse(ts: Any) -> datetime | None:
    if not isinstance(ts, str) or not ts:
        return None
    v = ts[:-1] + "+00:00" if ts.endswith("Z") else ts
    try:
        dt = datetime.fromisoformat(v)
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _reason_for_cell(cell: dict[str, Any]) -> str:
    return (f"audit3 KILL: {cell.get('asset_class')} {cell.get('strategy')} "
            f"{cell.get('direction')} n={cell.get('n')} "
            f"net={cell.get('net_expectancy_pct')}%/trade "
            f"(harm q={cell.get('harm_q')})")


def _build_index(ledger: dict[str, Any]) -> dict[str, Any]:
    strategies: dict[tuple[str, str], str] = {}
    symbols: dict[tuple[str, str], str] = {}
    classes: dict[tuple[str, str], str] = {}

    for cell in ledger.get("cells") or []:
        if not isinstance(cell, dict) or cell.get("verdict") != "KILL":
            continue
        name = str(cell.get("strategy") or "").strip().casefold()
        if name:
            strategies[(name, direction_key(cell.get("direction")))] = _reason_for_cell(cell)

    for kill in (ledger.get("kill_tribunal") or {}).get("kills") or []:
        if not isinstance(kill, dict) or kill.get("verdict", "KILL") != "KILL":
            continue
        scope = str(kill.get("scope") or "").lower()
        direction = direction_key(kill.get("direction"))
        ac = str(kill.get("asset_class") or "").upper()
        if scope == "symbol":
            key = canonical_symbol(kill.get("strategy"), ac)
            if key:
                symbols[(key, direction)] = _reason_for_cell(kill)
        elif scope == "class":
            classes[(ac, direction)] = _reason_for_cell(kill)

    return {"strategies": strategies, "symbols": symbols, "classes": classes}


def load(ledger_path: str | None = None,
         now: datetime | None = None) -> tuple[dict[str, Any] | None, str]:
    """Return (index, note). ``index`` is None when the denylist must not fire."""
    if _disabled():
        return None, "disabled by AUDIT3_DENYLIST_DISABLED"

    path = Path(ledger_path or os.environ.get("AUDIT3_DENYLIST_LEDGER") or DEFAULT_LEDGER)
    try:
        st = path.stat()
    except OSError:
        return None, f"ledger not found at {path} — denying nothing (fail-open)"
    key = f"{path}:{st.st_mtime_ns}:{st.st_size}"
    if _CACHE.get("key") == key:
        return _CACHE["index"], _CACHE["note"]

    try:
        ledger = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        note = f"ledger unreadable ({exc}) — denying nothing (fail-open)"
        _CACHE.update({"key": key, "index": None, "note": note})
        return None, note

    if not isinstance(ledger, dict) or not str(ledger.get("schema", "")).startswith("audit3."):
        note = "ledger schema is not audit3.* — denying nothing"
        _CACHE.update({"key": key, "index": None, "note": note})
        return None, note

    generated = _parse(ledger.get("generated_at"))
    if generated is None:
        note = "ledger has no generated_at — denying nothing"
        _CACHE.update({"key": key, "index": None, "note": note})
        return None, note
    age_days = ((now or datetime.now(timezone.utc)) - generated).total_seconds() / 86400.0
    if age_days > _max_age_days():
        note = (f"ledger is {age_days:.1f} days old (> {_max_age_days():.0f}d) — "
                "denying nothing (fail-open)")
        _CACHE.update({"key": key, "index": None, "note": note})
        return None, note

    index = _build_index(ledger)
    index["generated_at"] = ledger.get("generated_at")
    index["age_days"] = round(age_days, 3)
    note = (f"loaded {path.name}: {len(index['strategies'])} KILL strategy cells, "
            f"{len(index['symbols'])} KILL symbol cells, {age_days:.1f}d old")
    _CACHE.update({"key": key, "index": index, "note": note})
    return index, note


def denied_reason(pick: dict[str, Any], ledger_path: str | None = None,
                  now: datetime | None = None) -> str:
    """Return why a pick is denied, or "" when it may emit.

    Never raises: an audit artifact must not be able to break the scanner.
    """
    if not isinstance(pick, dict):
        return ""
    try:
        index, _note = load(ledger_path, now=now)
        if not index:
            return ""
        ac = str(pick.get("asset_class") or "").upper()
        direction = direction_key(pick.get("direction") or pick.get("signal"))

        # Exact direction first, then a direction-blind cell (rare, e.g. a
        # strategy with unknown side) so an ambiguous kill still binds.
        name = str(pick.get("strategy") or "").strip().casefold()
        for key in ((name, direction), (name, "UNKNOWN")):
            hit = index["strategies"].get(key)
            if hit:
                return hit

        symbol = canonical_symbol(pick.get("symbol"), ac)
        for key in ((symbol, direction), (symbol, "UNKNOWN")):
            hit = index["symbols"].get(key)
            if hit:
                return hit

        if _include_class():
            for key in ((ac, direction), (ac, "UNKNOWN")):
                hit = index["classes"].get(key)
                if hit:
                    return hit
        return ""
    except Exception as exc:  # pragma: no cover - defensive: never block emission
        return "" if not exc else ""


def summary(ledger_path: str | None = None) -> dict[str, Any]:
    """Diagnostics for the dashboard / CI: is the denylist actually armed?"""
    index, note = load(ledger_path)
    return {
        "armed": bool(index),
        "note": note,
        "generated_at": (index or {}).get("generated_at"),
        "age_days": (index or {}).get("age_days"),
        "n_strategy_kills": len((index or {}).get("strategies") or {}),
        "n_symbol_kills": len((index or {}).get("symbols") or {}),
        "n_class_kills": len((index or {}).get("classes") or {}),
        "include_class": _include_class(),
    }
