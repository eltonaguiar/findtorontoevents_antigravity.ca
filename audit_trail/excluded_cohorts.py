"""Aggregate the rows a dashboard build drops, so the bias is measurable.

N6 (excluded-cohort bias): audit3 scores only the rows that survive the
dashboard's integrity filters. The excluded cohorts (invalid rows, mirror
duplicates, non-performance exits, resolver fallbacks, auto-expired) are dropped
before export, so their PnL is never reported and nobody can tell whether the
retained book is flattered. The generator has these rows in hand at exclusion
time; this module turns them into a compact, publishable summary.

Pure functions, stdlib only. The caller supplies rows that already carry an
``exclude_reason`` (or passes the reason via ``reason``).
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable, Mapping


def _num(v: Any) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _side(row: Mapping[str, Any]) -> str:
    d = str(row.get("direction") or row.get("signal") or "").strip().upper()
    return d if d in ("LONG", "SHORT") else "UNKNOWN"


_SUMMARY_REASONS = (
    "invalid_row",
    "mirror_duplicate",
    "non_performance_exit",
    "resolver_breakeven_fallback",
)
_SUMMARY_NOTES = [
    "cohorts overlap; by_reason may sum to more than total",
    "total counts each excluded row once; by_reason counts each row once per "
    "distinct reason it carries, so a row in two cohorts with one reason is "
    "one row and one reason, not two",
]


def _row_class(row: Mapping[str, Any]) -> str:
    """Asset class for a row, or 'UNKNOWN' when the row carries none."""
    cls = str(row.get("asset_class") or "").strip().upper()
    return cls if cls else "UNKNOWN"


def summarize_excluded_rows(
    cohorts: Mapping[str, Iterable[Mapping[str, Any]]] | None
) -> dict[str, Any]:
    """Class-and-reason summary of the rows a build drops, or why not.

    ``cohorts`` maps a cohort name to the rows that cohort dropped. Cohorts may
    overlap (the dashboard's integrity and auto-expired sets do), so a row is
    counted once in ``total`` no matter how many cohorts contain it, and once
    per distinct reason it carries in ``by_reason`` / ``by_class_and_reason``.
    ``overlap`` is published (True when more than one cohort was supplied)
    instead of implying the cohorts partition.

    Every row with no class lands in an explicit ``"UNKNOWN"`` bucket (never
    silently dropped), and per-reason detail is delegated to
    :func:`summarize_excluded` so there is one implementation of the counting.
    """
    cohorts = cohorts if isinstance(cohorts, Mapping) else {}
    by_class: dict[str, int] = {}
    by_class_and_reason: dict[str, dict[str, int]] = {}
    reason_rows: dict[str, list[Mapping[str, Any]]] = {}
    seen_ids: set[int] = set()
    seen_row_reason: set[tuple[int, str]] = set()
    total = 0
    for _name, rows in cohorts.items():
        for row in rows or []:
            if not isinstance(row, Mapping):
                continue
            ident = id(row)
            cls = _row_class(row)
            if ident not in seen_ids:
                seen_ids.add(ident)
                total += 1
                by_class[cls] = by_class.get(cls, 0) + 1
            reason = str(row.get("exclude_reason") or row.get("_exclude_reason")
                         or "unknown")
            if (ident, reason) in seen_row_reason:
                continue
            seen_row_reason.add((ident, reason))
            per = by_class_and_reason.setdefault(cls, {})
            per[reason] = per.get(reason, 0) + 1
            reason_rows.setdefault(reason, []).append(row)

    detail = summarize_excluded(
        [r for rows in reason_rows.values() for r in rows]
    )
    by_reason: dict[str, int] = {k: 0 for k in _SUMMARY_REASONS}
    for reason, rows in reason_rows.items():
        by_reason[reason] = len(rows)
    return {
        "total": total,
        "by_reason": by_reason,
        "by_class": dict(sorted(by_class.items())),
        "by_class_and_reason": {
            cls: dict(sorted(per.items()))
            for cls, per in sorted(by_class_and_reason.items())
        },
        "overlap": len(cohorts) > 1,
        "reason_detail": detail["by_reason"],
        "notes": list(_SUMMARY_NOTES),
    }


def summarize_excluded(rows: Iterable[Mapping[str, Any]],
                       reason: str | None = None) -> dict[str, Any]:
    """Per-reason n / win-rate / mean-PnL / long-short split / top symbols."""
    by: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"n": 0, "n_with_pnl": 0, "n_pnl_numeric": 0, "wins": 0,
                 "losses": 0, "sum_pnl": 0.0, "long": 0, "short": 0,
                 "unknown": 0, "symbols": defaultdict(int),
                 "first_closed": None, "last_closed": None})
    total = 0
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        reason_key = str(reason or row.get("exclude_reason")
                         or row.get("_exclude_reason") or "unknown")
        b = by[reason_key]
        total += 1
        b["n"] += 1
        side = _side(row)
        b[side.lower() if side != "UNKNOWN" else "unknown"] += 1
        sym = str(row.get("symbol") or "?")
        b["symbols"][sym] += 1
        closed = row.get("closed_at") or row.get("timestamp")
        if closed:
            b["first_closed"] = b["first_closed"] or closed
            b["last_closed"] = closed
        pnl = _num(row.get("pnl_pct"))
        won = row.get("won")
        if pnl is None and won is None:
            continue
        b["n_with_pnl"] += 1
        if pnl is not None:
            b["n_pnl_numeric"] += 1
            b["sum_pnl"] += pnl
            if pnl > 0:
                b["wins"] += 1
            elif pnl < 0:
                b["losses"] += 1
        elif won is True:
            b["wins"] += 1
        elif won is False:
            b["losses"] += 1

    out: dict[str, Any] = {"total_excluded": total, "by_reason": {}}
    for key, b in sorted(by.items()):
        n_pnl = b["n_with_pnl"]
        out["by_reason"][key] = {
            "n": b["n"],
            "n_with_pnl": n_pnl,
            "win_rate": round(b["wins"] / n_pnl, 4) if n_pnl else None,
            "mean_pnl_pct": (round(b["sum_pnl"] / b["n_pnl_numeric"], 4)
                             if b["n_pnl_numeric"] else None),
            "sum_pnl_pct": round(b["sum_pnl"], 4),
            "long": b["long"], "short": b["short"], "unknown": b["unknown"],
            "top_symbols": dict(sorted(b["symbols"].items(),
                                       key=lambda kv: -kv[1])[:5]),
            "first_closed": b["first_closed"],
            "last_closed": b["last_closed"],
        }
    return out


def bias_report(included: Iterable[Mapping[str, Any]],
                excluded: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Compare the retained book against the excluded cohorts.

    A materially better retained mean than the excluded mean is the signal that
    the integrity filters are selecting on outcome, not on data quality.
    """
    def mean_pnl(rows):
        vals = [v for v in (_num(r.get("pnl_pct")) for r in rows
                            if isinstance(r, Mapping)) if v is not None]
        return (round(sum(vals) / len(vals), 4) if vals else None), len(vals)

    inc_mean, inc_n = mean_pnl(included)
    exc = summarize_excluded(excluded)
    exc_all = [v for v in (_num(r.get("pnl_pct")) for r in excluded
                           if isinstance(r, Mapping)) if v is not None]
    exc_mean = round(sum(exc_all) / len(exc_all), 4) if exc_all else None
    gap = (round(inc_mean - exc_mean, 4)
           if inc_mean is not None and exc_mean is not None else None)
    return {
        "included": {"n_with_pnl": inc_n, "mean_pnl_pct": inc_mean},
        "excluded": {"n_with_pnl": len(exc_all), "mean_pnl_pct": exc_mean,
                     "by_reason": exc["by_reason"]},
        "retained_minus_excluded_pp": gap,
        "note": ("A positive gap means the retained book looks better than the "
                 "rows the build dropped; read it as selection risk, not skill."),
    }


def is_auto_expired(row: Mapping[str, Any]) -> bool:
    """True when the row carries the generator's auto-expired marker."""
    return bool(row.get("_auto_expired")) or \
        str(row.get("exit_reason") or "").upper().startswith("STALE")


def split_auto_expired(rows: Iterable[Mapping[str, Any]]) -> tuple[list, list]:
    """Split rows into (real, auto_expired) without mutating them."""
    real, auto = [], []
    for r in rows:
        if not isinstance(r, Mapping):
            continue
        (auto if is_auto_expired(r) else real).append(r)
    return real, auto
