"""audit3_denylist.py — make the kill tribunal an emission gate, not a web page.

The tribunal's own review said it best: "a tribunal that reports kills while the
emitter never reads it is theatre." This module is the read path. It loads
`audit_dashboard/data/audit3_ledger.json` and answers one question about a
candidate pick — is this cell, symbol or class a proven-harm cohort?

Scope rules, all deliberate:

* **Direction-aware.** audit3 kills cells, not brands. On the 2026-11-19 ledger
  `luxalgo_confluence` is KILL LONG and CANDIDATE SHORT; blocking the name would
  discard the side that survived.
* **Class kills are a stronger bar, not a blanket ban** (decided 2026-11-19).
  A KILL class means the aggregate is negative after costs — CRYPTO n=1851 at
  −0.51%/trade, COMMODITY n=55 at −3.17%. Blanket-blocking the class would also
  discard cells that separately cleared a positive gate, and would permanently
  lock out any new hypothesis in that class. Default mode `positive_cells`
  therefore admits only cells whose own verdict is CANDIDATE or PROVEN_T2, and
  always admits paper picks so measurement continues. Modes:
  `AUDIT3_DENYLIST_CLASS_GATE=positive_cells` (default) | `all` | `off`.
* **Fail-open.** A missing, stale (`AUDIT3_DENYLIST_MAX_AGE_DAYS`, default 14) or
  malformed ledger denies nothing and reports why. An audit artifact must never
  be able to silently halt every emitter — but "silent" is the problem, so
  `tools/audit3_denylist_health.py` fails CI loudly when that happens.
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
POSITIVE_VERDICTS = ("CANDIDATE", "PROVEN_T2")
_CLASS_GATE_MODES = {"positive_cells", "all", "off"}
_CACHE: dict[str, Any] = {"key": None, "index": None, "note": ""}


def _flag(name: str, default: str = "") -> str:
    return (os.environ.get(name) or default).strip().lower()


def _disabled() -> bool:
    return _flag("AUDIT3_DENYLIST_DISABLED") in ("1", "true", "yes", "on")


def class_gate_mode() -> str:
    mode = _flag("AUDIT3_DENYLIST_CLASS_GATE", "positive_cells") or "positive_cells"
    return mode if mode in _CLASS_GATE_MODES else "positive_cells"


def _allow_paper_in_killed_class() -> bool:
    return _flag("AUDIT3_CLASS_GATE_ALLOW_PAPER", "1") not in ("0", "false", "no", "off")


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


def _dir(value: Any) -> str:
    key = direction_key(value)
    # A class aggregate carries no direction ("-"), so it binds either side.
    return "UNKNOWN" if key in ("", "-") else key


def _reason_for_cell(cell: dict[str, Any]) -> str:
    return (f"audit3 KILL: {cell.get('asset_class')} {cell.get('strategy')} "
            f"{cell.get('direction')} n={cell.get('n')} "
            f"net={cell.get('net_expectancy_pct')}%/trade "
            f"(harm q={cell.get('harm_q')})")


def _build_index(ledger: dict[str, Any]) -> dict[str, Any]:
    strategies: dict[tuple[str, str], str] = {}
    symbols: dict[tuple[str, str], str] = {}
    classes: dict[str, str] = {}
    positive_strategies: set[tuple[str, str]] = set()
    positive_symbols: set[tuple[str, str]] = set()

    for cell in ledger.get("cells") or []:
        if not isinstance(cell, dict):
            continue
        name = str(cell.get("strategy") or "").strip().casefold()
        direction = _dir(cell.get("direction"))
        if not name:
            continue
        if cell.get("verdict") == "KILL":
            strategies[(name, direction)] = _reason_for_cell(cell)
        elif cell.get("verdict") in POSITIVE_VERDICTS:
            positive_strategies.add((name, direction))

    for cell in ledger.get("symbols") or []:
        if not isinstance(cell, dict):
            continue
        symbol = canonical_symbol(cell.get("symbol"), cell.get("asset_class"))
        direction = _dir(cell.get("direction"))
        if not symbol:
            continue
        if cell.get("verdict") == "KILL":
            symbols[(symbol, direction)] = _reason_for_cell(cell)
        elif cell.get("verdict") in POSITIVE_VERDICTS:
            positive_symbols.add((symbol, direction))

    for kill in (ledger.get("kill_tribunal") or {}).get("kills") or []:
        if not isinstance(kill, dict) or kill.get("verdict", "KILL") != "KILL":
            continue
        scope = str(kill.get("scope") or "").lower()
        ac = str(kill.get("asset_class") or "").upper()
        if scope == "class" and ac:
            classes[ac] = _reason_for_cell(kill)
        elif scope == "symbol":
            key = canonical_symbol(kill.get("strategy"), ac)
            if key:
                symbols[(key, _dir(kill.get("direction")))] = _reason_for_cell(kill)

    return {"strategies": strategies, "symbols": symbols, "classes": classes,
            "positive_strategies": positive_strategies,
            "positive_symbols": positive_symbols}


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
            f"{len(index['symbols'])} KILL symbol cells, "
            f"{len(index['classes'])} KILL classes, {age_days:.1f}d old")
    _CACHE.update({"key": key, "index": index, "note": note})
    return index, note


def _lookup(table: dict, keys, positive: set) -> tuple[str, bool]:
    """Return (denial reason, separately-cleared)."""
    for key in keys:
        hit = table.get(key)
        if hit:
            return hit, key in positive
    return "", any(k in positive for k in keys)


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
        direction = _dir(pick.get("direction") or pick.get("signal"))
        name = str(pick.get("strategy") or "").strip().casefold()
        symbol = canonical_symbol(pick.get("symbol"), ac)

        # 1. Direct cell/symbol kills bind regardless of paper status: this is
        # proven harm, and a paper pick from a killed cell is not a measurement.
        for key in ((name, direction), (name, "UNKNOWN"), (name, "-")):
            hit = index["strategies"].get(key)
            if hit:
                return hit
        for key in ((symbol, direction), (symbol, "UNKNOWN"), (symbol, "-")):
            hit = index["symbols"].get(key)
            if hit:
                return hit

        # 2. Class gate.
        mode = class_gate_mode()
        if mode == "off" or ac not in index["classes"]:
            return ""

        reason = index["classes"][ac]
        if _allow_paper_in_killed_class() and (pick.get("paper_only") or pick.get("paper_trade")):
            return ""
        if mode == "all":
            return reason

        # mode == "positive_cells": only a cell that separately cleared a positive
        # gate may emit inside a class the aggregate proved harmful.
        _, strat_ok = _lookup(index["strategies"], ((name, direction), (name, "UNKNOWN")),
                              index["positive_strategies"])
        _, sym_ok = _lookup(index["symbols"], ((symbol, direction), (symbol, "UNKNOWN")),
                            index["positive_symbols"])
        if strat_ok or sym_ok:
            return ""
        return (f"{reason} — class gate: this cell is not CANDIDATE/PROVEN_T2, "
                f"so it may not emit inside a killed class (paper picks are exempt)")
    except Exception:  # pragma: no cover - defensive: never block emission
        return ""


def summary(ledger_path: str | None = None) -> dict[str, Any]:
    """Diagnostics for CI / the dashboard: is the denylist actually armed?"""
    index, note = load(ledger_path)
    return {
        "armed": bool(index),
        "note": note,
        "generated_at": (index or {}).get("generated_at"),
        "age_days": (index or {}).get("age_days"),
        "n_strategy_kills": len((index or {}).get("strategies") or {}),
        "n_symbol_kills": len((index or {}).get("symbols") or {}),
        "n_class_kills": len((index or {}).get("classes") or {}),
        "class_gate": class_gate_mode(),
        "class_gate_paper_exempt": _allow_paper_in_killed_class(),
        "max_age_days": _max_age_days(),
    }
