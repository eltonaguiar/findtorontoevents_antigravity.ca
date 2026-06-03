#!/usr/bin/env python3
"""Provenance + signal_ts backfill PROPOSER (report-only).

Swarm-converged next step (2026-06-02): the FDR/Bonferroni gate, the
single-source gate and the tournament-vs-production drift detector all operate
on the closed-picks ledger — but `signal_ts` is absent under that key and ~11%
of rows lack `source_system`, so those gates run on un-auditable data and the
208-trade tournament sample is not yet statistically valid.

This tool RECONSTRUCTS the two fields from sibling columns that ARE populated
(timestamps live under entry_date/entry_time/timestamp/created_at; provenance
under source_system/original_source/_source_file) and writes a SHADOW-AUDIT
report of proposed backfills + coverage stats.

HARD RULE: report-only. It never mutates the live ledger or DB. The proposals
go to a separate shadow JSON for a human-approved apply step later.
"""
from __future__ import annotations

import argparse
import json
from typing import Any, Dict, List, Optional

# Ordered fallback chains — first populated wins.
SIGNAL_TS_KEYS = ["signal_ts", "signal_time", "entry_ts", "entry_time",
                  "entry_date", "timestamp", "created_at", "_replay_bar_date"]
SOURCE_KEYS = ["source_system", "source", "original_source",
               "source_integration", "_source_file"]


def _first_populated(row: Dict[str, Any], keys: List[str]) -> Optional[Any]:
    for k in keys:
        v = row.get(k)
        if v not in (None, "", [], {}):
            return v
    return None


def propose_signal_ts(row: Dict[str, Any]) -> Optional[Any]:
    """Reconstruct a signal timestamp from the first populated time-ish field."""
    return _first_populated(row, SIGNAL_TS_KEYS)


def propose_source(row: Dict[str, Any]) -> Optional[str]:
    """Reconstruct provenance; last resort infers from the strategy name."""
    src = _first_populated(row, SOURCE_KEYS)
    if src:
        return str(src)
    strat = row.get("strategy")
    if strat:
        # infer a coarse source from the strategy slug prefix
        return f"inferred:{str(strat).split('_')[0]}"
    return None


def backfill_report(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Read-only coverage report + per-row proposals. Never mutates rows."""
    ts_present = ts_recovered = ts_unrepairable = 0
    src_present = src_recovered = src_inferred = src_unrepairable = 0
    proposals: List[Dict[str, Any]] = []

    for i, row in enumerate(rows):
        has_ts = row.get("signal_ts") not in (None, "")
        ts_val = propose_signal_ts(row)
        if has_ts:
            ts_present += 1
        elif ts_val is not None:
            ts_recovered += 1
        else:
            ts_unrepairable += 1

        has_src = row.get("source_system") not in (None, "")
        src_val = propose_source(row)
        if has_src:
            src_present += 1
        elif src_val is None:
            src_unrepairable += 1
        elif str(src_val).startswith("inferred:"):
            src_inferred += 1
        else:
            src_recovered += 1

        if (not has_ts and ts_val is not None) or (not has_src and src_val is not None):
            proposals.append({"index": i,
                              "symbol": row.get("symbol"),
                              "strategy": row.get("strategy"),
                              "proposed_signal_ts": None if has_ts else ts_val,
                              "proposed_source": None if has_src else src_val})

    n = len(rows)

    def pct(x):
        return round(100 * x / n, 1) if n else 0.0

    return {
        "n_total": n,
        "signal_ts": {"present": ts_present, "recoverable": ts_recovered,
                      "unrepairable": ts_unrepairable,
                      "coverage_after_backfill_pct": pct(ts_present + ts_recovered)},
        "source": {"present": src_present, "recoverable": src_recovered,
                   "inferred": src_inferred, "unrepairable": src_unrepairable,
                   "coverage_after_backfill_pct": pct(src_present + src_recovered + src_inferred)},
        "n_proposals": len(proposals),
        "proposals_sample": proposals[:25],
        "_mutated_ledger": False,
    }


def _cli():
    ap = argparse.ArgumentParser(description="Provenance/signal_ts backfill proposer (report-only).")
    ap.add_argument("ledger_json", help="picks JSON (list) — read only")
    ap.add_argument("--asset-class", default=None)
    ap.add_argument("--out", default=None, help="write full proposals JSON here (shadow audit)")
    args = ap.parse_args()
    data = json.load(open(args.ledger_json, encoding="utf-8"))
    rows = data if isinstance(data, list) else data.get("picks", data.get("rows", []))
    if args.asset_class:
        ac = args.asset_class.upper()
        rows = [r for r in rows if str(r.get("asset_class", "")).upper() == ac]
    report = backfill_report(rows)
    if args.out:
        # shadow-audit artifact ONLY — never the live ledger path
        full = dict(report)
        full["all_proposals"] = [
            {"index": i, "symbol": r.get("symbol"), "strategy": r.get("strategy"),
             "proposed_signal_ts": (None if r.get("signal_ts") not in (None, "")
                                    else propose_signal_ts(r)),
             "proposed_source": (None if r.get("source_system") not in (None, "")
                                 else propose_source(r))}
            for i, r in enumerate(rows)
        ]
        json.dump(full, open(args.out, "w", encoding="utf-8"), indent=2, default=str)
    summary = {k: v for k, v in report.items() if k != "proposals_sample"}
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":  # pragma: no cover
    _cli()
