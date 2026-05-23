from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


_DATA_DIR = Path(__file__).resolve().parent / "data"
_INSTITUTIONAL_KILL_LIST = Path(__file__).resolve().parent / "strategy_kill_list.json"
_PRIMARY_WHITELIST = _DATA_DIR / "core_whitelist.json"
_FALLBACK_WHITELIST = Path(__file__).resolve().parent.parent / "trading" / "data" / "core_whitelist.json"
_WHITELIST_GROUPS = ("protected_strategies", "core_strategies", "incubator_strategies")


def bare_strategy_name(name: str | None) -> str:
    if not isinstance(name, str):
        return ""
    lowered = name.strip().lower()
    if "::" in lowered:
        return lowered.split("::", 1)[1]
    return lowered


@lru_cache(maxsize=8)
def load_kill_list(path_hint: str | None = None) -> set[str]:
    """Load institutional and community kill lists.
    
    Checks institutional_kill_list.json first for hard suppressions,
    then pulls from core_whitelist.json for historical context.
    """
    kill_entries: set[str] = set()

    # 1. Load institutional hard kills (April 2026 Audit)
    if _INSTITUTIONAL_KILL_LIST.exists():
        try:
            with open(_INSTITUTIONAL_KILL_LIST, "r", encoding="utf-8") as f:
                hard_kills = json.load(f)
                # Sync with institutional_kills or auto_kill_strategies key
                for key in ("institutional_kills", "auto_kill_strategies"):
                    for entry in hard_kills.get(key, []):
                        if isinstance(entry, str) and entry.strip():
                            kill_entries.add(entry.strip().lower())
        except Exception:
            pass

    # 2. Existing whitelist-based kills (manual/historical)
    candidate_paths: list[Path] = []
    if path_hint:
        candidate_paths.append(Path(path_hint))
    candidate_paths.extend([_PRIMARY_WHITELIST, _FALLBACK_WHITELIST])

    seen: set[Path] = set()
    for wl_path in candidate_paths:
        if wl_path in seen:
            continue
        seen.add(wl_path)
        try:
            with open(wl_path, "r", encoding="utf-8") as f:
                whitelist = json.load(f)
        except Exception:
            continue

        protected: set[str] = set()
        for group in _WHITELIST_GROUPS:
            protected.update(
                bare_strategy_name(item)
                for item in whitelist.get(group, [])
                if isinstance(item, str) and item.strip()
            )

        # 2. Existing whitelist-based kills (manual/historical)
        # Note: Do NOT reset kill_entries here!
        for raw in whitelist.get("kill_list", []):
            if not isinstance(raw, str):
                continue
            full = raw.strip().lower()
            if not full:
                continue
            if bare_strategy_name(full) in protected:
                continue
            kill_entries.add(full)

        return kill_entries

    return set()


def suppression_keys_from_row(row: dict[str, Any] | None) -> set[str]:
    if not isinstance(row, dict):
        return set()

    strategy = (
        row.get("strategy")
        or row.get("strategy_name")
        or row.get("algorithm")
        or ""
    )
    bare = bare_strategy_name(strategy)
    if not bare:
        return set()

    keys = {bare}
    for key in ("source_system", "source", "system", "source_subsystem"):
        raw_source = row.get(key)
        if isinstance(raw_source, str) and raw_source.strip():
            keys.add(f"{raw_source.strip().lower()}::{bare}")
    return keys


def is_strategy_killed(
    strategy: str | None,
    kill_list: set[str],
    *,
    source_system: str | None = None,
    source_subsystem: str | None = None,
) -> bool:
    bare = bare_strategy_name(strategy)
    if not bare or not kill_list:
        return False

    keys = {bare}
    for raw_source in (source_system, source_subsystem):
        if isinstance(raw_source, str) and raw_source.strip():
            keys.add(f"{raw_source.strip().lower()}::{bare}")
    return any(key in kill_list for key in keys)


def is_row_killed(row: dict[str, Any] | None, kill_list: set[str]) -> bool:
    if not kill_list:
        return False
    return any(key in kill_list for key in suppression_keys_from_row(row))
