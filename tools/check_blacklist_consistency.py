"""
Ops smoke tool — verify `kimi_signal_tracking` exec-gate enforcement.

Companion to `tests/test_blacklist_exec_gate_enforcement.py` (PR-B).
Runnable on demand from repo root:

    python tools/check_blacklist_consistency.py

Exits 0 if all consistency checks pass, non-zero if any layer has drifted.
Read-only — no writes, no network.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from alpha_engine.config import BLACKLISTED_STRATEGIES  # noqa: E402
from audit_trail.quality_gates import BLOCKED_SOURCE_SYSTEMS  # noqa: E402

TARGET = "kimi_signal_tracking"
ACTIVE_PICKS_PATH = REPO_ROOT / "alpha_engine" / "data" / "active_picks.json"


def _load_active_rows():
    if not ACTIVE_PICKS_PATH.exists():
        return None
    with ACTIVE_PICKS_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        return data.get("picks") or data.get("active") or []
    return data


def main() -> int:
    failures: list[str] = []

    intake_ok = TARGET in BLACKLISTED_STRATEGIES
    if not intake_ok:
        failures.append(f"INTAKE: {TARGET!r} missing from alpha_engine.config.BLACKLISTED_STRATEGIES")

    exec_ok = TARGET in BLOCKED_SOURCE_SYSTEMS
    if not exec_ok:
        failures.append(
            f"EXEC:   {TARGET!r} missing from audit_trail.quality_gates.BLOCKED_SOURCE_SYSTEMS"
        )

    rows = _load_active_rows()
    if rows is None:
        active_leaks = -1
        active_total = -1
        failures.append(f"DATA:   {ACTIVE_PICKS_PATH} not present")
    else:
        active_total = len(rows)
        active_leaks = sum(
            1
            for r in rows
            if str(r.get("source_system", "") or "").lower().strip() == TARGET
        )
        if active_leaks:
            failures.append(
                f"LEAK:   {active_leaks} {TARGET!r} rows in {ACTIVE_PICKS_PATH.name} "
                "(exec-gate bypass)"
            )

    status = "OK" if not failures else "FAIL"
    print(
        f"[blacklist-consistency] target={TARGET} intake={intake_ok} "
        f"exec={exec_ok} active_total={active_total} leaks={active_leaks} status={status}"
    )
    for line in failures:
        print(f"  - {line}")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
