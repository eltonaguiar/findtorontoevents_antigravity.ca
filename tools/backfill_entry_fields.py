"""Derive entry fields for already-closed picks (2026-11-20).

New picks are stamped at creation by the dashboard ingest. Historical rows are
not rewritten in place (the payload is generated) -- this writes a joinable
sidecar: pick id -> derived entry_time/entry_price and the source field, so
regime and hedge analysis can cover rows that were emitted before the contract.

Usage: python3 tools/backfill_entry_fields.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from alpha_engine.pick_contract import (  # noqa: E402
    derive_entry_price, derive_entry_time, coverage,
)

PICKS = REPO_ROOT / "audit_dashboard" / "data" / "dashboard_data.json"
OUT = REPO_ROOT / "audit_dashboard" / "data" / "entry_fields_backfill.json"


def main() -> None:
    rows = json.loads(PICKS.read_text())["picks"]["recent_closed"]
    before = coverage(rows)
    derived = {}
    sources: dict[str, int] = {}
    for r in rows:
        pid = r.get("id") or ""
        ts, ts_src = derive_entry_time(r)
        px, px_src = derive_entry_price(r)
        if ts or px:
            derived[pid] = {"entry_time": ts, "entry_price": px,
                            "entry_time_source": ts_src, "entry_price_source": px_src}
            if ts_src:
                sources[ts_src] = sources.get(ts_src, 0) + 1
    after_rows = [
        {**r, "entry_time": derived.get(r.get("id"), {}).get("entry_time"),
         "entry_price": derived.get(r.get("id"), {}).get("entry_price")}
        for r in rows
    ]
    after = coverage(after_rows)
    payload = {
        "generated_from": str(PICKS.name),
        "n_rows": len(rows),
        "coverage_before": before,
        "coverage_after": after,
        "derived_by_source": dict(sorted(sources.items(), key=lambda kv: -kv[1])),
        "entry_fields": derived,
    }
    OUT.write_text(json.dumps(payload, indent=1))
    print("  before:", before)
    print("  after :", after)
    print("  derived from:", payload["derived_by_source"])
    print(f"  written -> {OUT.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
