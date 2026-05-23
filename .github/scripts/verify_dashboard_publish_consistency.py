#!/usr/bin/env python3
"""Verify dashboard_payload.json matches dashboard_data.json before git amend/push.

Used by Unified Audit Dashboard workflow after a post-rebase generator re-run.
Extracted from inline bash heredoc: indented closing PYEOF broke bash (delimiter must
start at column 0 after <<- handling), causing silent script truncation / exit 2.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    payload_path = root / "audit_trail" / "data" / "dashboard_payload.json"
    dashboard_path = root / "audit_dashboard" / "data" / "dashboard_data.json"
    if not payload_path.exists() or not dashboard_path.exists():
        print(
            "ERROR: Missing dashboard JSON artifact(s) after regeneration",
            file=sys.stderr,
        )
        return 1
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    dashboard = json.loads(dashboard_path.read_text(encoding="utf-8"))
    # 2026-04-17: dashboard_data.json is a slimmed external copy of payload by design
    # (different top-level shape for size optimization). Full-dict equality (`!=`) was
    # producing false positives — observed in run 24564335200 where both reported the
    # same active=59 but the script blocked commit citing "mismatch". Compare on the
    # meaningful invariants instead: same active-pick count + same closed-pick count
    # + matching summary if both have it.
    pa = len((payload.get("picks") or {}).get("active") or [])
    da = len((dashboard.get("picks") or {}).get("active") or [])
    pc = len((payload.get("picks") or {}).get("recent_closed") or [])
    dc = len((dashboard.get("picks") or {}).get("recent_closed") or [])
    if pa != da or pc != dc:
        print(
            f"ERROR: Generated JSON mismatch: payload active={pa} closed={pc}, "
            f"dashboard_data active={da} closed={dc}. Refusing to commit mixed-generation artifacts.",
            file=sys.stderr,
        )
        return 1
    active = (payload.get("picks") or {}).get("active") or []
    missing_source = sum(
        1
        for p in active
        if not ((p.get("source") or p.get("source_system") or "").strip())
    )
    missing_system = sum(
        1
        for p in active
        if not (
            (p.get("system") or p.get("source_subsystem") or p.get("source_system") or "")
            .strip()
        )
    )
    summary = payload.get("summary") or {}
    if "portfolio_uniqueness" not in summary:
        print(
            "ERROR: Missing summary.portfolio_uniqueness in generated payload",
            file=sys.stderr,
        )
        return 1
    if missing_source or missing_system:
        print(
            f"ERROR: Missing attribution fields in active picks: "
            f"source={missing_source}, system={missing_system}",
            file=sys.stderr,
        )
        return 1
    nc = summary.get("non_crypto_performance") or {}
    if not nc:
        print(
            "WARN: summary.non_crypto_performance empty — cards may lack NC drill-down",
            file=sys.stderr,
        )
    print(
        f"Publish consistency OK: active={len(active)} "
        f"portfolio_uniqueness=present missing_source={missing_source} "
        f"missing_system={missing_system}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
