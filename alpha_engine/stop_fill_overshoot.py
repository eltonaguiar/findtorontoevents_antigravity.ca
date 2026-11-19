"""stop_fill_overshoot.py — how far stopped exits land from their stop.

Purpose
-------
A stop promises a bounded loss: |entry - stop| / entry. The 2026-11-14 peer
audit (quant-audit-2026-11-14) found crypto stopped trades realizing a mean
loss of 2.990% against a mean planned risk of 1.919% (+1.071pp overshoot,
98.8% of the crypto class loss). This module makes that measurement
reproducible over any closed-pick ledger.

Definitions
-----------
planned_risk_pct  = |entry_price - stop_loss| / entry_price * 100
realized_loss_pct = -pnl_pct
overshoot         = realized_loss_pct - planned_risk_pct

A positive overshoot means the fill was worse than the stop promised. Rows
with missing/non-numeric fields, entry <= 0, or a non-positive planned risk
are skipped, and the skip count is reported so a silent denominator change is
visible. The absolute value keeps the measure direction-agnostic (a short's
stop sits above the entry), so only a zero or invalid risk is ever skipped.

By default only stopped trades are counted (see ``_is_stopped``); pass
``stopped_only=False`` to include every row. ``status``/``exit_reason`` are
carried on the row and used for that filter.

Pure stdlib: no network, no DB.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from typing import Any, Iterable

#: Relative tolerance for "the exit filled exactly at the stop".
EXIT_EQ_REL_TOL = 1e-9


def _num(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


#: Statuses / exit reasons that identify a stopped trade. A winner is not a
#: stopped trade, and counting it (realized "loss" = -pnl) would pollute the
#: overshoot mean — which is exactly the mistake this filter prevents.
_STOPPED_STATUS = {"LOST", "LOSS", "SL_HIT", "STOPPED", "STOPPED_OUT", "STOPPED_OUT_PARTIAL"}
_STOPPED_REASONS = {"STOP", "STOP_LOSS", "STOPLOSS", "SL", "SL_HIT", "STOPPED"}


def _is_stopped(r: dict) -> bool:
    st = str(r.get("status") or "").strip().upper()
    if st in _STOPPED_STATUS:
        return True
    er = str(r.get("exit_reason") or "").strip().upper().replace("-", "_")
    if er in _STOPPED_REASONS:
        return True
    return "STOP_LOSS" in er or er.startswith("STOP")


def _summarize(rows: Iterable[dict], stopped_only: bool = True) -> dict[str, Any]:
    planned: list[float] = []
    realized: list[float] = []
    overshoot: list[float] = []
    at_stop = 0
    skipped = 0
    for r in rows:
        if not isinstance(r, dict):
            skipped += 1
            continue
        if stopped_only and not _is_stopped(r):
            skipped += 1
            continue
        entry = _num(r.get("entry_price"))
        stop = _num(r.get("stop_loss"))
        exit_price = _num(r.get("exit_price"))
        pnl = _num(r.get("pnl_pct"))
        if entry is None or stop is None or exit_price is None or pnl is None:
            skipped += 1
            continue
        if entry <= 0:
            skipped += 1
            continue
        risk = abs(entry - stop) / entry * 100.0
        if risk <= 0:
            skipped += 1
            continue
        planned.append(risk)
        realized.append(-pnl)
        overshoot.append(-pnl - risk)
        if abs(exit_price - stop) <= EXIT_EQ_REL_TOL * max(1.0, abs(stop)):
            at_stop += 1
    n = len(planned)
    out: dict[str, Any] = {
        "n_stopped": n,
        "n_skipped": skipped,
        "n_exit_at_stop": at_stop,
        "n_exit_off_stop": n - at_stop,
        "mean_planned_risk_pct": None,
        "mean_realized_loss_pct": None,
        "mean_overshoot_pp": None,
        "median_planned_risk_pct": None,
        "median_realized_loss_pct": None,
        "median_overshoot_pp": None,
    }
    if n:
        out["mean_planned_risk_pct"] = round(sum(planned) / n, 4)
        out["mean_realized_loss_pct"] = round(sum(realized) / n, 4)
        out["mean_overshoot_pp"] = round(sum(overshoot) / n, 4)
        out["median_planned_risk_pct"] = round(statistics.median(planned), 4)
        out["median_realized_loss_pct"] = round(statistics.median(realized), 4)
        out["median_overshoot_pp"] = round(statistics.median(overshoot), 4)
    return out


def overshoot_stats(rows: Iterable[dict], stopped_only: bool = True) -> dict[str, Any]:
    """Per-asset-class and overall stop-fill overshoot for a stopped cohort.

    rows: closed pick dicts carrying entry_price, stop_loss, exit_price,
    pnl_pct, status and asset_class. Returns ``{"overall": {...},
    "by_asset_class": {...}}`` where each bucket reports n_stopped, n_skipped,
    n_exit_at_stop, n_exit_off_stop, mean/median planned risk, mean/median
    realized loss, mean overshoot in pp and median overshoot in pct. A bucket
    with no usable rows reports its counts and None for every statistic.
    """
    materialized = list(rows or [])
    by_class: dict[str, list[dict]] = {}
    for r in materialized:
        if isinstance(r, dict):
            key = str(r.get("asset_class") or "UNKNOWN").upper()
            by_class.setdefault(key, []).append(r)
    return {
        "overall": _summarize(materialized, stopped_only=stopped_only),
        "by_asset_class": {k: _summarize(v, stopped_only=stopped_only)
                           for k, v in sorted(by_class.items())},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Measure stop-fill overshoot from a closed-pick JSON ledger.")
    parser.add_argument(
        "path", nargs="?", default="audit_dashboard/data/dashboard_data.json",
        help="JSON list of picks, or a dashboard_data.json payload")
    args = parser.parse_args(argv)
    with open(args.path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        picks = data.get("picks")
        rows = picks.get("recent_closed") if isinstance(picks, dict) else picks
    else:
        rows = data
    if not isinstance(rows, list):
        print(f"{args.path}: no closed-pick list found", file=sys.stderr)
        return 2
    print(json.dumps(overshoot_stats(rows), indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
