#!/usr/bin/env python3
"""Stop-fill model — tell a resting stop from a late polled exit.

Why this exists (2026-11-14 audit, final_v2/quant-audit-2026-11-14):

  Of 1,468 SL_HIT rows in the live dashboard payload, 1,360 exited at a price
  that is NOT the declared stop. Mean planned risk was 1.919% of entry; mean
  realized loss was 2.990% — a 1.56x overshoot. For CRYPTO alone the overshoot
  totaled +828.0pp against a class total of -837.8pp, i.e. 98.8% of the class
  loss came from where the stop *filled*, not from which trades were chosen.

  Those rows carry resolver_version=None: they were written by self-tracked
  system writers that close at whatever price the poller last saw, then label
  the row SL_HIT. That conflates two different events:

    - the stop was touched and we exited there (a planned loss = -1R), and
    - the stop was touched but we exited later, at market (a larger loss).

  Every risk metric downstream — R-multiples, breakeven win rate, required
  R:R, per-strategy edge — was computed as if these were the same thing.

What this module does NOT do:

  It never rewrites ``pnl_pct``. The realized exit is a fact. Inventing a
  better fill would be the mirror of the bug we are fixing. Instead each row
  gets ``pnl_pct_at_stop`` (the counterfactual) alongside the realized number,
  so the difference is explicit and auditable.

Fill model (see ``find_stop_fill``):

  Resting stop → fill at the stop price when the bar's range spans it, at the
  bar's OPEN when price gapped through it. Gap-through fills are worse than the
  stop by construction; that is the honest direction of error.

Usage:
    python -m audit_trail.stop_fill --payload /tmp/peercheck/dashboard_payload.json
    python -m audit_trail.stop_fill --payload X.json --json out.json
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Optional, Sequence

# Fill provenance labels written onto annotations.
BASIS_STOP = "stop"            # exited at the declared stop price
BASIS_GAP = "gap_through"      # bar opened beyond the stop — filled at the open
BASIS_LATE = "late_polled"     # exited somewhere other than the stop (the defect)
BASIS_UNMEASURED = "unmeasured"  # missing/zero fields — no basis to judge

_STOP_REASONS = {"SL_HIT", "STOP_LOSS", "SL", "LOST"}

# Two prices count as "the same" when they differ by less than this fraction of
# entry. Float noise on a 8-decimal price is far below 1e-6 of entry.
_EQUAL_TOL = 1e-6


def _f(v: Any) -> Optional[float]:
    """Coerce to float, returning None for missing/garbage (never 0.0)."""
    if v is None or v == "":
        return None
    try:
        out = float(v)
    except (TypeError, ValueError):
        return None
    return out if out == out else None  # drop NaN


def _is_long(direction: Any) -> bool:
    d = str(direction or "LONG").upper()
    return d not in ("SHORT", "SELL")


def _is_stop_row(row: Dict[str, Any]) -> bool:
    return str(row.get("exit_reason") or row.get("status") or "").upper() in _STOP_REASONS


def planned_risk_pct(row: Dict[str, Any]) -> Optional[float]:
    """Distance from entry to the declared stop, as a % of entry (always +).

    This is the risk the strategy *intended* to take.
    """
    entry = _f(row.get("entry_price"))
    sl = _f(row.get("stop_loss"))
    if not entry or entry <= 0 or not sl or sl <= 0:
        return None
    return abs(entry - sl) / entry * 100.0


def realized_risk_pct(row: Dict[str, Any]) -> Optional[float]:
    """Direction-aware adverse excursion from entry to the realized exit, % of entry.

    Positive means the trade moved against us by that much. A stopped trade that
    fills exactly at the stop returns ~planned_risk_pct.
    """
    entry = _f(row.get("entry_price"))
    xp = _f(row.get("exit_price"))
    if not entry or entry <= 0 or xp is None or xp <= 0:
        return None
    if _is_long(row.get("direction")):
        return (entry - xp) / entry * 100.0
    return (xp - entry) / entry * 100.0


def stop_slippage_pct(row: Dict[str, Any]) -> Optional[float]:
    """Realized risk minus planned risk, in percentage points.

    Positive = we lost more than the plan (late fill). Zero = filled at stop.
    Negative is possible only when the exit beat the stop, which for a genuine
    stop hit means the data disagrees with the label.
    """
    planned = planned_risk_pct(row)
    realized = realized_risk_pct(row)
    if planned is None or realized is None:
        return None
    return realized - planned


def pnl_at_stop(row: Dict[str, Any]) -> Optional[float]:
    """The PnL% this trade would have booked had the stop filled at the stop."""
    entry = _f(row.get("entry_price"))
    sl = _f(row.get("stop_loss"))
    if not entry or entry <= 0 or not sl or sl <= 0:
        return None
    # For LONG the stop sits below entry so (sl-entry) is negative already;
    # for SHORT the adverse move is upward, so flip the sign.
    mult = 1.0 if _is_long(row.get("direction")) else -1.0
    return (sl - entry) / entry * 100.0 * mult


def classify_row(row: Dict[str, Any]) -> str:
    """Return the fill basis for a closed row (BASIS_* constant)."""
    if not _is_stop_row(row):
        return BASIS_UNMEASURED
    entry = _f(row.get("entry_price"))
    sl = _f(row.get("stop_loss"))
    xp = _f(row.get("exit_price"))
    if not entry or entry <= 0 or not sl or sl <= 0 or xp is None or xp <= 0:
        return BASIS_UNMEASURED
    if abs(xp - sl) <= entry * _EQUAL_TOL:
        return BASIS_STOP
    return BASIS_LATE


def annotate_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of ``row`` with stop-fill provenance fields added.

    ``pnl_pct`` is preserved untouched. Added keys:
      stop_fill_basis        stop | gap_through | late_polled | unmeasured
      planned_risk_pct       intended risk, % of entry
      realized_risk_pct      adverse move actually taken, % of entry
      stop_slippage_pct      realized - planned (pp); >0 = lost more than planned
      pnl_pct_at_stop        counterfactual PnL had the stop filled at the stop
      stop_fill_cost_pp      pnl_pct_at_stop - pnl_pct (negative = late fill hurt)
    """
    out = dict(row)
    basis = classify_row(row)
    planned = planned_risk_pct(row)
    realized = realized_risk_pct(row)
    at_stop = pnl_at_stop(row)
    pnl = _f(row.get("pnl_pct"))

    out["stop_fill_basis"] = basis
    out["planned_risk_pct"] = None if planned is None else round(planned, 4)
    out["realized_risk_pct"] = None if realized is None else round(realized, 4)
    slip = stop_slippage_pct(row)
    out["stop_slippage_pct"] = None if slip is None else round(slip, 4)
    out["pnl_pct_at_stop"] = None if at_stop is None else round(at_stop, 4)
    if at_stop is not None and pnl is not None:
        out["stop_fill_cost_pp"] = round(at_stop - pnl, 4)
    else:
        out["stop_fill_cost_pp"] = None
    return out


# ---------------------------------------------------------------------------
# Intrabar fill model — used by the resolver, not by annotation
# ---------------------------------------------------------------------------
def _bar_fields(bar: Dict[str, Any]):
    return (_f(bar.get("open")), _f(bar.get("high")), _f(bar.get("low")))


def find_stop_fill(
    direction: Any,
    stop: Optional[float],
    bars: Sequence[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """First bar that breaches ``stop``, with the price a resting stop would fill at.

    Returns ``{"price", "basis", "bar_index"}`` or None when never breached.

    Rules (per bar, chronological):
      LONG  breached when low <= stop.
            - bar.open <= stop  → gapped through: fill at bar.open (worse)
            - else              → fill at stop
      SHORT breached when high >= stop.
            - bar.open >= stop  → gapped through: fill at bar.open (worse)
            - else              → fill at stop

    A bar with no usable open falls back to the stop price — the range proves
    the level was crossed, and assuming no gap is the pre-existing behaviour.
    """
    st = _f(stop)
    if not st or st <= 0:
        return None
    long_side = _is_long(direction)

    for idx, bar in enumerate(bars or []):
        op, hi, lo = _bar_fields(bar)
        if hi is None or lo is None:
            continue
        if long_side:
            if lo > st:
                continue
            if op is not None and 0 < op < st:
                return {"price": op, "basis": BASIS_GAP, "bar_index": idx}
            return {"price": st, "basis": BASIS_STOP, "bar_index": idx}
        if hi < st:
            continue
        if op is not None and op > st:
            return {"price": op, "basis": BASIS_GAP, "bar_index": idx}
        return {"price": st, "basis": BASIS_STOP, "bar_index": idx}
    return None


# ---------------------------------------------------------------------------
# Aggregate reporting
# ---------------------------------------------------------------------------
def summarize(rows: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """Per-asset-class stop-fill summary over closed rows.

    Reports the overshoot the late fills represent, and the PnL counterfactual
    had every stop filled at its stop. Both totals are reported so the reader
    can see the size of the fix without mistaking it for a profit claim.

    PnL totals are restricted to STOPPED rows: a take-profit or time exit is a
    different exit mechanism and averaging the two would hide the fill effect.
    """
    by_class: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {
            "n_closed": 0, "n_sl": 0, "n_stop": 0, "n_late": 0, "n_unmeasured": 0,
            "planned_risk_sum": 0.0, "realized_risk_sum": 0.0,
            "slippage_sum_pp": 0.0, "pnl_sum": 0.0, "pnl_at_stop_sum": 0.0,
            "pnl_matched_sum": 0.0,
            "n_planned": 0, "n_realized": 0, "n_counterfactual": 0,
        }
    )
    for row in rows:
        if not isinstance(row, dict):
            continue
        ac = str(row.get("asset_class") or "UNKNOWN").upper()
        acc = by_class[ac]
        acc["n_closed"] += 1
        ann = annotate_row(row)
        basis = ann["stop_fill_basis"]
        if basis == BASIS_UNMEASURED:
            if _is_stop_row(row):
                acc["n_unmeasured"] += 1
            continue
        acc["n_sl"] += 1
        if basis == BASIS_STOP:
            acc["n_stop"] += 1
        else:
            acc["n_late"] += 1
        if ann["planned_risk_pct"] is not None:
            acc["planned_risk_sum"] += ann["planned_risk_pct"]
            acc["n_planned"] += 1
        if ann["realized_risk_pct"] is not None:
            acc["realized_risk_sum"] += ann["realized_risk_pct"]
            acc["n_realized"] += 1
        if ann["stop_slippage_pct"] is not None:
            acc["slippage_sum_pp"] += ann["stop_slippage_pct"]
        pnl = _f(row.get("pnl_pct"))
        if pnl is not None:
            acc["pnl_sum"] += pnl
        if ann["pnl_pct_at_stop"] is not None:
            acc["pnl_at_stop_sum"] += ann["pnl_pct_at_stop"]
            acc["n_counterfactual"] += 1
            # Realized PnL restricted to the SAME rows the counterfactual covers,
            # so the delta is a like-for-like comparison and not SL-vs-everything.
            if pnl is not None:
                acc["pnl_matched_sum"] += pnl

    out: Dict[str, Any] = {}
    for ac, acc in sorted(by_class.items()):
        n_pl, n_rl = acc["n_planned"], acc["n_realized"]
        out[ac] = {
            "n_closed": acc["n_closed"],
            "n_sl": acc["n_sl"],
            "n_filled_at_stop": acc["n_stop"],
            "n_late_fill": acc["n_late"],
            "n_unmeasured": acc["n_unmeasured"],
            "mean_planned_risk_pct": round(acc["planned_risk_sum"] / n_pl, 4) if n_pl else None,
            "mean_realized_risk_pct": round(acc["realized_risk_sum"] / n_rl, 4) if n_rl else None,
            "overshoot_ratio": (
                round((acc["realized_risk_sum"] / n_rl) / (acc["planned_risk_sum"] / n_pl), 4)
                if n_pl and n_rl and acc["planned_risk_sum"] else None
            ),
            "slippage_pp_total": round(acc["slippage_sum_pp"], 2),
            "pnl_pp_total": round(acc["pnl_sum"], 2),
            "pnl_pp_total_stop_matched": round(acc["pnl_matched_sum"], 2),
            "pnl_at_stop_pp_total": round(acc["pnl_at_stop_sum"], 2),
            "delta_if_filled_at_stop_pp": round(
                acc["pnl_at_stop_sum"] - acc["pnl_matched_sum"], 2
            ),
        }
    return out


def load_closed_rows(path: str) -> List[Dict[str, Any]]:
    """Load closed rows from a dashboard payload or dashboard_data.json."""
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if isinstance(data, dict):
        picks = data.get("picks")
        if isinstance(picks, dict) and isinstance(picks.get("recent_closed"), list):
            return [r for r in picks["recent_closed"] if isinstance(r, dict)]
        if isinstance(data.get("recent_closed"), list):
            return [r for r in data["recent_closed"] if isinstance(r, dict)]
        if isinstance(data.get("closed_picks"), list):
            return [r for r in data["closed_picks"] if isinstance(r, dict)]
    if isinstance(data, list):
        return [r for r in data if isinstance(r, dict)]
    return []


def _print_report(summary: Dict[str, Any]) -> None:
    hdr = (
        f"{'class':<11}{'n_cl':>6}{'n_sl':>6}{'at_stop':>8}{'late':>6}"
        f"{'plan%':>8}{'real%':>8}{'x':>7}{'slip_pp':>10}{'pnl_pp':>10}{'at_stop':>10}"
    )
    print(hdr)
    print("-" * len(hdr))
    for ac, s in summary.items():
        print(
            f"{ac:<11}{s['n_closed']:>6}{s['n_sl']:>6}{s['n_filled_at_stop']:>8}"
            f"{s['n_late_fill']:>6}"
            f"{(s['mean_planned_risk_pct'] if s['mean_planned_risk_pct'] is not None else 0):>8.3f}"
            f"{(s['mean_realized_risk_pct'] if s['mean_realized_risk_pct'] is not None else 0):>8.3f}"
            f"{(s['overshoot_ratio'] if s['overshoot_ratio'] is not None else 0):>7.2f}"
            f"{s['slippage_pp_total']:>10.1f}{s['pnl_pp_total']:>10.1f}"
            f"{s['pnl_at_stop_pp_total']:>10.1f}"
        )


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--payload", required=True, help="dashboard payload JSON or dashboard_data.json")
    ap.add_argument("--json", help="write the per-class summary here")
    args = ap.parse_args(argv)

    rows = load_closed_rows(args.payload)
    if not rows:
        print(f"No closed rows found in {args.payload}")
        return 2
    summary = summarize(rows)
    _print_report(summary)
    total_pnl = sum(s["pnl_pp_total_stop_matched"] for s in summary.values())
    total_at_stop = sum(s["pnl_at_stop_pp_total"] for s in summary.values())
    print(f"\nstopped-trade realized pnl (matched) = {total_pnl:.1f}pp")
    print(f"same trades filled at the stop       = {total_at_stop:.1f}pp")
    print(f"delta (pp)        = {total_at_stop - total_pnl:+.1f}")
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump({"summary": summary, "rows": len(rows)}, fh, indent=2, sort_keys=True)
        print(f"wrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
