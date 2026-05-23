#!/usr/bin/env python3
"""Validate local audit payload: age, JSON_PICK_SOURCES coverage, numeric fields.

Run from repo root:
  python tools/audit_payload_health.py

Shared logic: audit_trail/dashboard_payload_health.py
"""
from __future__ import annotations

import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
PAYLOAD_PATH = REPO / "audit_trail" / "data" / "dashboard_payload.json"
MAX_AGE_SECONDS = 4 * 3600


def main() -> int:
    sys.path.insert(0, str(REPO))
    from audit_trail.collect_sources import get_registered_pick_source_names
    from audit_trail.dashboard_payload_health import check_dashboard_payload

    if not PAYLOAD_PATH.is_file():
        print(f"Missing {PAYLOAD_PATH}", file=sys.stderr)
        return 2

    health = check_dashboard_payload(REPO, PAYLOAD_PATH, max_age_seconds=MAX_AGE_SECONDS)
    if not health.ok:
        for line in health.summary_lines():
            print(line, file=sys.stderr)
        return 1

    print(
        f"OK payload age_s={health.age_seconds} "
        f"registered_sources={len(get_registered_pick_source_names())}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
