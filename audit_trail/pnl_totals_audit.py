"""Reconcile the dashboard's P&L headlines and flag resolver anomalies.

2026-11-16 audit findings this module addresses
------------------------------------------------
* The payload exposed four incompatible totals with no basis labels:
  ``total_pnl_pct`` (-77.67), ``total_pnl_pct_sum_raw`` (-1356.44),
  ``total_pnl_pct_compounded_ew`` (-99.0, silently floored) and
  ``total_pnl_pct_geomean_annualized`` (-99.9).
* ``total_pnl_pct_compounded_ew`` was clamped to -99 without recording the
  pre-clamp value, so a -1356% compounded figure looked like a -99% loss.
* ``zero_pnl_count`` reported 132 while 3,868 rows carried ``pnl_pct: 0.0``
  (2,938 of them EXPIRED crypto rows) — unresolved rows wearing a zero.
* ``NEARUSDT`` SHORT printed ``pnl_pct: -99.0`` (``pre_clamp -135.472``)
  after its stop never fired: entry 1.356, SL 1.37973, exit 3.193, EXPIRED
  as "STALE >5809h". A failed stop was recorded as a normal -99% loss.

``build_pnl_headline`` labels every total by basis; ``compute_resolver_anomalies``
counts the rows whose recorded outcome cannot come from the published geometry.
Both are pure functions so they can be unit-tested without the 25 MB payload.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable

_MIN_ABS_PNL = 0.01
_STOP_BREACH_TOLERANCE = 1.25  # 25% beyond the planned stop distance


def _float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def build_pnl_headline(
    *,
    headline: Any,
    rolling_100: Any,
    sum_raw: Any,
    compounded_ew: Any,
    compounded_ew_pre_floor: Any = None,
    geomean_annualized: Any = None,
) -> Dict[str, Any]:
    """Return a single labelled view of every P&L total the payload exposes."""
    floored = (
        compounded_ew_pre_floor is not None
        and compounded_ew is not None
        and abs(_float(compounded_ew) - _float(compounded_ew_pre_floor)) > 1e-9
    )
    return {
        "primary_metric": "total_pnl_pct",
        "primary_basis": "rolling-100 compounded equal-weight (bounded)",
        "values": {
            "rolling_100_compounded_ew": rolling_100,
            "raw_additive_sum": sum_raw,
            "full_ledger_compounded_ew": compounded_ew,
            "full_ledger_compounded_ew_pre_floor": compounded_ew_pre_floor,
            "annualized_geomean": geomean_annualized,
            "legacy_headline": headline,
        },
        "basis_notes": {
            "rolling_100_compounded_ew": "last 100 resolved trades, 10% per-trade cap; the headline",
            "raw_additive_sum": "sum of capped per-trade % — NOT a portfolio return",
            "full_ledger_compounded_ew": "fictitious 100% reinvestment on every trade; floored at -99",
            "annualized_geomean": "daily-mean geomean x 252; scale-sensitive, not comparable to the others",
        },
        "compounded_ew_floored": floored,
        "compounded_ew_pre_floor": compounded_ew_pre_floor
        if floored
        else compounded_ew,
        "reconciled": True,
    }


def compute_resolver_anomalies(rows: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """Count resolved rows whose outcome cannot follow from their own geometry."""
    stale_beyond_stop = 0
    clamped_losses = 0
    zero_pnl_unresolved = 0
    closed_missing_closed_at = 0
    total = 0
    for row in rows:
        if not isinstance(row, dict):
            continue
        total += 1
        status = str(row.get("status", "")).upper()
        exit_reason = str(row.get("exit_reason", "") or "").upper()
        pnl = _float(row.get("pnl_pct"), default=0.0)

        if status == "EXPIRED" and exit_reason.startswith("STALE"):
            entry = _float(row.get("entry_price"))
            stop = _float(row.get("stop_loss") or row.get("sl_price"))
            if entry > 0 and stop > 0:
                stop_pct = abs(entry - stop) / entry * 100.0
                if pnl < 0 and abs(pnl) > stop_pct * _STOP_BREACH_TOLERANCE:
                    stale_beyond_stop += 1

        pre_clamp = row.get("pnl_pct_pre_clamp")
        if pre_clamp is not None and pnl <= -99.0 and _float(pre_clamp) < -99.0:
            clamped_losses += 1

        if status == "EXPIRED" and abs(pnl) <= _MIN_ABS_PNL:
            zero_pnl_unresolved += 1

        if status in ("WON", "LOST", "CLOSED", "TP_HIT", "SL_HIT") and not row.get(
            "closed_at"
        ):
            closed_missing_closed_at += 1

    return {
        "rows_scanned": total,
        "stale_exit_beyond_planned_stop": stale_beyond_stop,
        "clamped_loss_rows": clamped_losses,
        "expired_zero_pnl_rows": zero_pnl_unresolved,
        "closed_rows_missing_closed_at": closed_missing_closed_at,
    }
