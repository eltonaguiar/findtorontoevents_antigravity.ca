#!/usr/bin/env python3
"""Compare picks.active vs picks.active_raw for non-crypto asset buckets.

Reads audit_trail/data/dashboard_payload.json (repo copy). Use to see whether
zeros on the audit Non-Crypto cards are empty pipeline vs gate-filtered.

Run from repo root:
  python tools/audit_nc_active_investigation.py
  python tools/audit_nc_active_investigation.py path/to/dashboard_payload.json
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_payload(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8", errors="replace"))


def main() -> int:
    default = ROOT / "audit_trail" / "data" / "dashboard_payload.json"
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else default
    try:
        data = _load_payload(path)
    except FileNotFoundError as e:
        print(f"Missing payload: {e}", file=sys.stderr)
        return 1

    try:
        from audit_trail.dashboard_generator import nc_asset_category_for_pick
    except ImportError:
        sys.path.insert(0, str(ROOT))
        from audit_trail.dashboard_generator import nc_asset_category_for_pick

    picks = data.get("picks") or {}
    active = picks.get("active") or []
    raw = picks.get("active_raw") or active

    def bucket_rows(rows: list) -> Counter:
        c: Counter = Counter()
        for p in rows:
            if not isinstance(p, dict):
                continue
            cat = nc_asset_category_for_pick(p)
            if cat:
                c[cat] += 1
        return c

    c_active = bucket_rows(active)
    c_raw = bucket_rows(raw)

    nc_keys = ("FOREX", "EQUITY", "STOCK", "COMMODITY", "FUTURES", "BOND", "ETF")
    print(f"Payload: {path}")
    print(f"picks.active: {len(active)}  picks.active_raw: {len(raw)}")
    print()
    print(f"{'Category':<12} {'active':>8} {'active_raw':>12} {'raw-only':>10}")
    print("-" * 44)
    for k in nc_keys:
        a, r = c_active.get(k, 0), c_raw.get(k, 0)
        print(f"{k:<12} {a:>8} {r:>12} {r - a:>10}")

    print()
    for k in ("COMMODITY", "FUTURES", "BOND"):
        a, r = c_active.get(k, 0), c_raw.get(k, 0)
        if a == 0 and r == 0:
            print(f"Note: {k} has 0 rows in both pools -> no open picks in sources for this payload (not gate-skew).")
        elif r > a:
            print(f"Note: {k} has {r - a} raw-only row(s) -> gate or dedup removed some opens.")

    # Futures: sample gate-failed rows from raw pool
    raw_futures = [
        p
        for p in raw
        if isinstance(p, dict) and nc_asset_category_for_pick(p) == "FUTURES"
    ]
    in_active_syms = {
        (p.get("symbol"), p.get("strategy"), p.get("source_system"))
        for p in active
        if isinstance(p, dict) and nc_asset_category_for_pick(p) == "FUTURES"
    }
    leaked = [
        p
        for p in raw_futures
        if (p.get("symbol"), p.get("strategy"), p.get("source_system")) not in in_active_syms
    ]
    print()
    print("FUTURES diagnostics (up to 8 rows in active_raw but not in active):")
    if not leaked:
        print("  (none - same futures in both pools, or no futures in active_raw)")
    for p in leaked[:8]:
        pens = p.get("_penalties") or []
        pen_str = "; ".join(str(x) for x in pens[:6]) if pens else "(no _penalties)"
        if len(pens) > 6:
            pen_str += "..."
        print(
            f"  sym={p.get('symbol')} strat={p.get('strategy')} "
            f"score={p.get('score')} trust={p.get('trust_score')} "
            f"_gate_passed={p.get('_gate_passed')!r}"
        )
        print(f"    penalties: {pen_str}")

    if leaked:
        try:
            from audit_trail.quality_gates import passes_active_gate
        except ImportError:
            sys.path.insert(0, str(ROOT))
            from audit_trail.quality_gates import passes_active_gate
        print()
        print("  passes_active_gate recheck (deepcopy; -60 blocked_asset_class etc. applied):")
        for p in leaked[:5]:
            pc = deepcopy(p)
            pre = pc.get("score")
            ok = passes_active_gate(pc)
            pens = pc.get("_penalties") or []
            print(
                f"    {p.get('symbol')}: pass={ok} score {pre} -> {pc.get('score')} "
                f"penalties={pens[:5]}"
            )

    # ETF: expect all raw ETF excluded from active
    etf_raw = [
        p for p in raw if isinstance(p, dict) and nc_asset_category_for_pick(p) == "ETF"
    ]
    etf_active = [
        p for p in active if isinstance(p, dict) and nc_asset_category_for_pick(p) == "ETF"
    ]
    print()
    print(
        f"ETF: active={len(etf_active)} active_raw={len(etf_raw)} "
        f"(narrow gate in passes_active_gate; expect raw>=active)"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
