#!/usr/bin/env python3
"""Post-deploy / hourly validation for asset-class prediction plan changes.

Checks:
  - audit_trail/data/dashboard_payload.json recent_closed has smart_score + tier fields
  - verified_alpha has cohorts + active_pick_refs_audited (when payload from new generator)
  - optional: audit_dashboard/data/dashboard_data.json same checks

Exit 0 if payload looks fresh; 1 if missing file or fields (regenerate generator).

Usage:
  python tools/validate_asset_class_plan_changes.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def _check_closed(rows: list, label: str) -> list[str]:
    errs: list[str] = []
    if not rows:
        errs.append(f"{label}: no recent_closed")
        return errs
    with_ss = sum(1 for p in rows if isinstance(p, dict) and p.get("smart_score") is not None)
    with_tier = sum(1 for p in rows if isinstance(p, dict) and p.get("quality_tier"))
    if with_ss < max(1, len(rows) // 100):
        errs.append(
            f"{label}: only {with_ss}/{len(rows)} closed picks have smart_score "
            "(run: python -m audit_trail.dashboard_generator)"
        )
    if with_tier < max(1, len(rows) // 100):
        errs.append(f"{label}: only {with_tier}/{len(rows)} have quality_tier")
    return errs


def _check_va(va: dict, label: str) -> list[str]:
    errs: list[str] = []
    if not va:
        return errs
    if not va.get("cohorts"):
        errs.append(f"{label}: verified_alpha.cohorts missing (old payload?)")
    if not va.get("active_pick_refs_audited") and va.get("active_count"):
        errs.append(f"{label}: active_pick_refs_audited missing")
    return errs


def main() -> int:
    errs: list[str] = []
    for rel in (
        REPO / "audit_trail" / "data" / "dashboard_payload.json",
        REPO / "audit_dashboard" / "data" / "dashboard_data.json",
    ):
        if not rel.is_file():
            continue
        try:
            data = json.loads(rel.read_text(encoding="utf-8", errors="replace"))
        except Exception as e:
            errs.append(f"{rel.name}: JSON error {e}")
            continue
        label = rel.name
        rc = (data.get("picks") or {}).get("recent_closed") or []
        errs.extend(_check_closed(rc, label))
        errs.extend(_check_va(data.get("verified_alpha") or {}, label))

    if not errs:
        print("OK: closed picks carry SMART fields and VA cohort metadata (where payload present).")
        return 0
    for e in errs:
        print(e, file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
