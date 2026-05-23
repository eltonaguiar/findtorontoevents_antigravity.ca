#!/usr/bin/env python3
"""
Registered pick pipeline names from JSON_PICK_SOURCES.

Uses a runtime import of audit_trail.dashboard_generator (not regex parsing) so the
health check never drifts from the true ingest list. Entries in _HIDDEN_SYSTEMS are
excluded — they are intentionally absent from payload.systems[].
"""

from __future__ import annotations

import sys
from pathlib import Path


def repo_root() -> Path:
    """Repository root (parent of audit_trail/)."""
    return Path(__file__).resolve().parents[1]


def get_registered_pick_source_names() -> list[str]:
    """Sorted unique system names from JSON_PICK_SOURCES, excluding _HIDDEN_SYSTEMS."""
    root = repo_root()
    root_s = str(root)
    if root_s not in sys.path:
        sys.path.insert(0, root_s)

    from audit_trail.dashboard_generator import JSON_PICK_SOURCES, _HIDDEN_SYSTEMS

    names: list[str] = []
    for row in JSON_PICK_SOURCES:
        if isinstance(row, (list, tuple)) and row and isinstance(row[0], str):
            n = row[0]
            if n not in _HIDDEN_SYSTEMS:
                names.append(n)
    return sorted(set(names))


if __name__ == "__main__":
    for name in get_registered_pick_source_names():
        print(name)
