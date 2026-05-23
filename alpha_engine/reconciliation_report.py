"""
Reconciliation Report — Settlement-Integrity SLA for the Audit Page
=====================================================================

Implements Theme B's last bullet: a daily reconciliation report that
shows visitors of ``findtorontoevents.ca/audit`` what every prop shop
already shows internally — *was every closed pick actually settled
against an exchange tape, on schedule?*

Output shape (one row per asset class plus a portfolio total):

    {
      "as_of": "2026-05-02T03:30:00Z",
      "by_class": {
        "EQUITY": {
          "n_total": 381,
          "n_resolved": 379,
          "n_unresolved": 2,
          "pct_resolved": 99.48,
          "median_latency_seconds": 86400,
          "p95_latency_seconds": 172800,
          "n_v2": 379,
          "n_v1_legacy": 0,
          "needs_attention": false
        },
        ...
      },
      "portfolio": { ...same keys, aggregated... }
    }

Wiring plan
-----------
Opt-in sidecar today. Target production caller is
``audit_trail/dashboard_generator.py`` (Week 2 of the plan): the
generator will call :func:`build_reconciliation_report` and surface
the per-class block in a "Reconciliation" row at the top of the audit
page. ``needs_attention=True`` should flip a red dot in the UI.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Iterable, Sequence

from .decay_tracker import _parse_ts


def _percentile(values: Sequence[float], q: float) -> float:
    """Pure-Python percentile (q in [0, 1]). Returns NaN on empty input."""
    if not values:
        return float("nan")
    s = sorted(values)
    if len(s) == 1:
        return s[0]
    pos = q * (len(s) - 1)
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    frac = pos - lo
    return s[lo] + (s[hi] - s[lo]) * frac


def _row(
    picks: Sequence[dict],
    *,
    pct_attention_threshold: float = 95.0,
    p95_attention_seconds: float = 7 * 86400,
) -> dict:
    n_total = len(picks)
    if n_total == 0:
        return {
            "n_total": 0,
            "n_resolved": 0,
            "n_unresolved": 0,
            "pct_resolved": 0.0,
            "median_latency_seconds": None,
            "p95_latency_seconds": None,
            "n_v2": 0,
            "n_v1_legacy": 0,
            "needs_attention": False,
        }

    latencies: list[float] = []
    n_resolved = 0
    n_v2 = 0
    n_v1 = 0
    for p in picks:
        status = str(p.get("status") or p.get("outcome") or "").upper()
        # A pick is "resolved" if it has a non-PENDING outcome and a finite pnl
        pnl = p.get("pnl_pct")
        try:
            pnl_f = float(pnl) if pnl is not None else None
        except (TypeError, ValueError):
            pnl_f = None
        is_resolved = (
            status in {"WON", "WIN", "LOST", "LOSS", "FLAT", "CLOSED"}
            and pnl_f is not None
            and math.isfinite(pnl_f)
        )
        if is_resolved:
            n_resolved += 1
            opened = _parse_ts(p.get("emitted_at") or p.get("opened_at") or p.get("timestamp"))
            closed = _parse_ts(p.get("resolved_at") or p.get("closed_at"))
            if opened and closed and closed >= opened:
                latencies.append((closed - opened).total_seconds())
        v = p.get("resolver_version")
        if v == "v2":
            n_v2 += 1
        elif v in (None, "v1", ""):
            n_v1 += 1

    pct_resolved = (n_resolved / n_total) * 100.0 if n_total else 0.0
    median_lat = _percentile(latencies, 0.5) if latencies else None
    p95_lat = _percentile(latencies, 0.95) if latencies else None

    needs_attention = (
        pct_resolved < pct_attention_threshold
        or (p95_lat is not None and p95_lat > p95_attention_seconds)
    )
    return {
        "n_total": n_total,
        "n_resolved": n_resolved,
        "n_unresolved": n_total - n_resolved,
        "pct_resolved": round(pct_resolved, 2),
        "median_latency_seconds": median_lat,
        "p95_latency_seconds": p95_lat,
        "n_v2": n_v2,
        "n_v1_legacy": n_v1,
        "needs_attention": needs_attention,
    }


def build_reconciliation_report(
    closed_picks: Iterable[dict],
    *,
    now: datetime | None = None,
    asset_class_field: str = "asset_class",
    pct_attention_threshold: float = 95.0,
    p95_attention_seconds: float = 7 * 86400,
) -> dict:
    """Build the per-class + portfolio reconciliation block.

    Args:
        closed_picks: iterable of closed-pick dicts (the
            ``closed_picks`` array from ``dashboard_payload.json``
            works directly).
        now: reference time (defaults to UTC now); injectable for tests.
        asset_class_field: schema override for the asset-class column.
        pct_attention_threshold: below this resolved-share %, the row
            flips to ``needs_attention=True``. Default 95%.
        p95_attention_seconds: above this p95 settlement latency, the
            row flips to ``needs_attention=True``. Default 7 days.

    Returns:
        Dict shaped for direct injection into ``dashboard_payload.json``.
    """
    ref = now or datetime.now(timezone.utc)
    by_class: dict[str, list[dict]] = {}
    all_picks: list[dict] = []
    for p in closed_picks:
        ac = str(p.get(asset_class_field) or p.get("category") or "UNKNOWN").upper()
        by_class.setdefault(ac, []).append(p)
        all_picks.append(p)

    return {
        "as_of": ref.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "by_class": {
            ac: _row(
                rows,
                pct_attention_threshold=pct_attention_threshold,
                p95_attention_seconds=p95_attention_seconds,
            )
            for ac, rows in sorted(by_class.items())
        },
        "portfolio": _row(
            all_picks,
            pct_attention_threshold=pct_attention_threshold,
            p95_attention_seconds=p95_attention_seconds,
        ),
    }


__all__ = ["build_reconciliation_report"]
