#!/usr/bin/env python3
"""
EAGLE enhancement suite — one CLI for monitor + variants + mutation scan.

Synthesizes recommendations from EAGLE*.MD* (2026-05-19 → 2026-06-02):
  - quant_monitor (concentration / resolver / freeze)
  - strategy_variants registry
  - mutation_framework on dashboard closed picks
  - optional strategy_admit for a sleeve

Usage:
  python3 tools/run_eagle_suite.py
  python3 tools/run_eagle_suite.py --admit etf_dual_momentum --asset-class ETF
  python3 tools/run_eagle_suite.py --write reports/eagle_suite_latest.json
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_monitor() -> dict:
    from verified_strategies.quant_monitor import run_full_monitor

    r = run_full_monitor()
    return {
        "freeze_promotions": r.freeze_promotions,
        "alerts": r.alerts,
        "source_hhi": r.concentration.source_hhi,
        "expired_positive_rate": r.resolver.expired_positive_rate,
        "class_health": {
            ac: {"pf": h.pf, "wr": h.wr, "n": h.n, "status": h.status}
            for ac, h in r.class_health.items()
        },
    }


def run_variants() -> dict:
    from verified_strategies.strategy_variants import EAGLE_STRATEGY_VARIANTS, list_variants

    return {
        "count": len(list_variants()),
        "sleeves": {
            k: {
                "asset_class": v.asset_class,
                "param_grid": v.param_grid,
                "notes": v.notes,
                "eagle_source": v.eagle_source,
            }
            for k, v in EAGLE_STRATEGY_VARIANTS.items()
        },
    }


def run_mutation_scan() -> dict:
    from verified_strategies.mutation_framework import run_full_mutation_scan
    from verified_strategies.quant_monitor import load_dashboard

    data = load_dashboard()
    closed = data.get("picks", {}).get("recent_closed", [])
    by_strategy: dict = defaultdict(list)
    for p in closed:
        key = p.get("source_system") or p.get("strategy") or "unknown"
        by_strategy[key].append(p)

    results = run_full_mutation_scan(dict(by_strategy), min_n=15, max_pf=1.0)
    top = [
        {
            "strategy": r.strategy_name,
            "axis": r.axis.value,
            "verdict": r.verdict,
            "original_pf": round(r.original_pf, 3),
            "mutated_pf": round(r.mutated_pf, 3),
            "improvement": round(r.improvement, 3),
        }
        for r in results[:15]
    ]
    adopt = [t for t in top if t["verdict"] == "ADOPT"]
    return {"scanned_strategies": len(by_strategy), "top_results": top, "adopt_count": len(adopt)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="EAGLE enhancement suite")
    ap.add_argument("--admit", help="Run strategy_admit for sleeve name")
    ap.add_argument("--asset-class", default="ETF")
    ap.add_argument("--write", help="Write combined JSON report path")
    args = ap.parse_args(argv)

    payload = {
        "schema": "eagle_suite/v1",
        "generated_at": _now(),
        "monitor": run_monitor(),
        "strategy_variants": run_variants(),
        "mutation_scan": run_mutation_scan(),
    }

    if args.admit:
        from tools.strategy_admit import admit

        payload["admit"] = admit(args.admit, args.asset_class)

    text = json.dumps(payload, indent=2)
    print(text)

    if args.write:
        out = Path(args.write)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text + "\n", encoding="utf-8")
        print(f"Wrote {out}", file=sys.stderr)

    return 1 if payload["monitor"].get("freeze_promotions") else 0


if __name__ == "__main__":
    raise SystemExit(main())
