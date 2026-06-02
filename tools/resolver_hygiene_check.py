#!/usr/bin/env python3
"""Resolver-hygiene checker (INCIDENT_CRYPTO #8) — REPORT-ONLY.

CRYPTO money_ready shows MDD=1.0 / CVaR95 -85% (money_ready_verdict 2026-06-02):
the fingerprint of never-closed / mislabeled tails inflating the loss tail. This
scans a picks ledger (a list of row dicts, e.g. closed_picks.json) and flags four
classes of suspect rows so a human can decide remediation:

  1. never_closed   — terminal/EXPIRED status but carries a non-zero outcome/pnl,
                      OR closed without a close timestamp.
  2. duplicates     — repeated (symbol, signal_ts, strategy) groups (flicker dupes).
  3. mislabels      — EXPIRED status tagged WON, or pnl sign disagreeing with outcome.
  4. missing_prov   — no source_system / source_id (provenance gap).

HARD RULE: this NEVER mutates the ledger or the DB. It returns a report dict and,
via the CLI, reads a JSON path read-only and prints counts + a sample of suspects.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from typing import Any, Dict, List

_TERMINAL_NONWIN = {"EXPIRED", "CANCELLED", "CANCELED", "OPEN", "ACTIVE", "PENDING"}


def _f(row: Dict[str, Any], *keys, default=None):
    for k in keys:
        if k in row and row[k] is not None:
            return row[k]
    return default


def _pnl(row: Dict[str, Any]) -> float:
    try:
        return float(_f(row, "pnl_pct", "pnl", default=0) or 0)
    except (TypeError, ValueError):
        return 0.0


def scan_ledger(picks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Pure, read-only scan. Returns a report dict (never mutates `picks`)."""
    never_closed, mislabels, missing_prov = [], [], []
    dup_groups: Dict[tuple, int] = defaultdict(int)

    for i, row in enumerate(picks):
        status = str(_f(row, "status", "state", default="")).upper()
        outcome = str(_f(row, "outcome", "result", default="")).upper()
        pnl = _pnl(row)
        close_ts = _f(row, "close_ts", "closed_at", "exit_ts")

        # 1. never_closed: terminal-nonwin status yet has realized outcome/pnl,
        #    or marked closed/WON/LOST without a close timestamp.
        if status in _TERMINAL_NONWIN and (pnl != 0 or outcome in {"WON", "LOST"}):
            never_closed.append(i)
        elif outcome in {"WON", "LOST"} and not close_ts:
            never_closed.append(i)

        # 3. mislabels: EXPIRED/terminal-nonwin tagged WON, or pnl sign vs outcome.
        if status in _TERMINAL_NONWIN and outcome == "WON":
            mislabels.append(i)
        elif outcome == "WON" and pnl < 0:
            mislabels.append(i)
        elif outcome == "LOST" and pnl > 0:
            mislabels.append(i)

        # 4. provenance gap
        if not _f(row, "source_system", "source_id", "source"):
            missing_prov.append(i)

        # 2. duplicate key
        key = (_f(row, "symbol", "ticker", default=""),
               _f(row, "signal_ts", "signal_time", "ts", default=""),
               _f(row, "strategy", "source_system", default=""))
        if key != ("", "", ""):
            dup_groups[key] += 1

    dup_keys = {k: c for k, c in dup_groups.items() if c > 1}
    n_dup_rows = sum(c for c in dup_keys.values())

    n = len(picks)
    return {
        "n_total": n,
        "never_closed": len(never_closed),
        "duplicate_groups": len(dup_keys),
        "duplicate_rows": n_dup_rows,
        "mislabels": len(mislabels),
        "missing_provenance": len(missing_prov),
        "suspect_pct": round(
            100 * len(set(never_closed + mislabels)) / n, 2) if n else 0.0,
        "sample_suspect_indices": sorted(set(never_closed + mislabels))[:20],
        "top_duplicate_keys": [
            {"key": list(k), "count": c}
            for k, c in Counter(dup_keys).most_common(10)
        ],
        "_mutated_ledger": False,   # invariant: this tool never writes
    }


def _cli():
    ap = argparse.ArgumentParser(description="Resolver-hygiene checker (report-only).")
    ap.add_argument("ledger_json", help="path to a picks JSON (list of rows) — read only")
    ap.add_argument("--asset-class", default=None, help="filter to one asset_class")
    args = ap.parse_args()
    with open(args.ledger_json, encoding="utf-8") as fh:
        data = json.load(fh)
    rows = data if isinstance(data, list) else data.get("picks", data.get("rows", []))
    if args.asset_class:
        ac = args.asset_class.upper()
        rows = [r for r in rows if str(r.get("asset_class", "")).upper() == ac]
    print(json.dumps(scan_ledger(rows), indent=2, default=str))


if __name__ == "__main__":  # pragma: no cover
    _cli()
