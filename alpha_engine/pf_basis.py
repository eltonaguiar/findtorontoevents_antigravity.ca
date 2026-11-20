"""One canonical way to print a profit factor, with its denominator attached.

Why this module exists (2026-11-20): the repo published CRYPTO at PF 1.31, 0.83
and 0.26 in three places, and every one of those numbers was arithmetically
correct -- they differ only in which picks were counted and whether cost was
charged. A PF without its ``n`` and its cost treatment is not a measurement, it
is a rumour, and readers had no way to tell the three apart.

Rule: a class/system PF is quoted as ``PF <value> (n=<count>[, net <bp>bp])``.

Usage::

    from alpha_engine.pf_basis import format_pf, pf_record

    label = format_pf(0.8339, 6874, cost_bps=9.85)   # 'PF 0.83 (n=6,874, net 9.9bp)'
    payload.update(pf_record(0.8339, 6874, cost_bps=9.85))
"""
from __future__ import annotations

import math
from typing import Any


def _fmt_value(value: Any) -> str:
    if value is None:
        return "n/a"
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "n/a"
    if math.isnan(v):
        return "n/a"
    if math.isinf(v):
        return "inf" if v > 0 else "-inf"
    return f"{v:.2f}"


def format_pf(
    value: Any,
    n: Any = None,
    cost_bps: Any = None,
    basis: str | None = None,
) -> str:
    """``'PF 0.83 (n=6,874, net 9.9bp)'`` -- value, denominator, cost treatment.

    ``cost_bps`` wins over ``basis`` when both are given: a number for the cost
    charged is strictly more informative than the word "gross"/"net".
    """
    parts: list[str] = []
    if n is not None:
        try:
            parts.append(f"n={int(n):,}")
        except (TypeError, ValueError):
            parts.append(f"n={n}")
    if cost_bps is not None:
        try:
            c = float(cost_bps)
            parts.append("net 0.0bp" if c == 0 else f"net {c:.1f}bp")
        except (TypeError, ValueError):
            parts.append("net ?bp")
    elif basis:
        parts.append(str(basis))
    inner = ", ".join(parts)
    head = f"PF {_fmt_value(value)}"
    return f"{head} ({inner})" if inner else head


def pf_record(
    value: Any,
    n: Any = None,
    cost_bps: Any = None,
    basis: str | None = None,
    population: str | None = None,
) -> dict:
    """Structured companion to :func:`format_pf` for JSON payloads.

    Emitted next to the raw PF so a consumer can never hold the ratio without
    the denominator: ``pf_label`` is the human string, ``pf_n`` the count,
    ``pf_cost_bps`` the cost charged per pick (``None`` when not measured --
    never 0.0 as a stand-in), ``pf_basis`` the word otherwise, and
    ``pf_population`` a name for the cohort.
    """
    out: dict = {
        "pf_label": format_pf(value, n, cost_bps, basis),
        "pf_n": None,
        "pf_cost_bps": None,
        "pf_basis": "net" if cost_bps is not None else (basis or None),
        "pf_population": population,
    }
    if n is not None:
        try:
            out["pf_n"] = int(n)
        except (TypeError, ValueError):
            out["pf_n"] = None
    if cost_bps is not None:
        try:
            out["pf_cost_bps"] = round(float(cost_bps), 4)
        except (TypeError, ValueError):
            out["pf_cost_bps"] = None
    return out
