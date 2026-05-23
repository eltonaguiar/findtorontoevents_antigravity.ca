"""Post-wave-2 wire verification script.

Run after the hourly dashboard regen at :10 past the hour to confirm
that PRs #977, #981, #984 have actually taken effect on /audit data.

Usage: python tools/verify_wave2_wires.py

Exits 0 if all wires verified, non-zero with details otherwise.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DASHBOARD = REPO / "audit_dashboard" / "data" / "dashboard_data.json"
ACTIVE_PICKS = REPO / "alpha_engine" / "data" / "active_picks.json"

# PR merge timestamps (UTC) — anything generated after these timestamps
# should reflect the corresponding wire.
PR_977_MERGED = datetime(2026, 5, 13, 23, 27, tzinfo=timezone.utc)   # drift breaker dashboard wire
PR_981_MERGED = datetime(2026, 5, 13, 23, 32, tzinfo=timezone.utc)   # bond merge step
PR_984_MERGED = datetime(2026, 5, 13, 23, 52, tzinfo=timezone.utc)   # ETF floor + 60d enrich


def _parse_ts(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def check_dashboard() -> tuple[bool, list[str]]:
    notes: list[str] = []
    if not DASHBOARD.exists():
        return False, [f"dashboard_data.json missing at {DASHBOARD}"]
    data = json.loads(DASHBOARD.read_text(encoding="utf-8"))
    gen_ts = _parse_ts(data.get("generated_at"))
    if gen_ts is None:
        return False, ["dashboard generated_at unparseable"]
    notes.append(f"dashboard generated_at: {gen_ts.isoformat()}")

    ach = data.get("performance", {}).get("asset_class_health", {}) or {}
    if not ach:
        return False, notes + ["asset_class_health empty"]

    classes = list(ach.keys())
    notes.append(f"asset_class_health classes: {classes}")

    ok = True
    if gen_ts >= PR_977_MERGED:
        any_cb = any(v.get("circuit_breaker") for v in ach.values() if isinstance(v, dict))
        if not any_cb:
            notes.append("FAIL: PR #977 wire — no class has circuit_breaker stamp")
            ok = False
        else:
            notes.append("OK: PR #977 wire — circuit_breaker stamped on at least one class")
    else:
        notes.append(f"SKIP: dashboard older than PR #977 merge time")

    if gen_ts >= PR_984_MERGED:
        any_60d = any("pf_60d" in v for v in ach.values() if isinstance(v, dict))
        any_n_alias = any("n" in v for v in ach.values() if isinstance(v, dict))
        if not any_n_alias:
            notes.append("FAIL: PR #984 — no class has canonical 'n' alias")
            ok = False
        else:
            notes.append("OK: PR #984 — 'n' alias present on at least one class")
        if not any_60d:
            notes.append("FAIL: PR #984 — no class has 60d-window fields (pf_60d)")
            ok = False
        else:
            notes.append("OK: PR #984 — 60d-window fields present on at least one class")
    else:
        notes.append("SKIP: dashboard older than PR #984 merge time")

    return ok, notes


def check_active_picks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    if not ACTIVE_PICKS.exists():
        return False, [f"active_picks.json missing at {ACTIVE_PICKS}"]
    data = json.loads(ACTIVE_PICKS.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        return False, [f"active_picks.json is not a list ({type(data).__name__})"]

    bond_picks = [p for p in data
                  if isinstance(p, dict)
                  and str(p.get("asset_class", "")).lower() in ("bond", "bonds")]
    notes.append(f"active_picks.json: total={len(data)} bond_n={len(bond_picks)}")
    if bond_picks:
        notes.append("OK: PR #981 wire — BOND picks present in active_picks.json")
        notes.append(f"  examples: " + ", ".join(
            f"{p.get('symbol')}/{p.get('strategy')}" for p in bond_picks[:3]
        ))
        return True, notes
    notes.append("PENDING: PR #981 wire — no BOND picks yet (bond-agent runs hourly; "
                 "first cron must complete + emit qualified picks first)")
    return True, notes  # PENDING is informational, not a failure


def main() -> int:
    print("=== Wave-2 wire verification ===")
    dash_ok, dash_notes = check_dashboard()
    for n in dash_notes:
        print(f"  [DASH] {n}")
    picks_ok, picks_notes = check_active_picks()
    for n in picks_notes:
        print(f"  [PICKS] {n}")
    return 0 if (dash_ok and picks_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
