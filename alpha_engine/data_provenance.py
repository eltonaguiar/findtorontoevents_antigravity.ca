"""Provenance stamps for universe artifacts (P0.9, 2026-11-20).

A yfinance-derived universe is today's survivors, so any backtest over it is
flattered by construction. Callers stamp the artifact instead of pretending the
bias is absent; consumers (reports, dashboards, promotion gates) can then refuse
to promote a survivorship-flattered result.
"""

from __future__ import annotations

# Sources whose membership is fixed as of the observation date.
SURVIVORSHIP_FREE_SOURCES = frozenset({
    "sec_edgar", "cftc", "alfred", "fred", "crsp", "compustat_pit",
})


def stamp_provenance(artifact: dict, source: str, universe_as_of: str | None = None) -> dict:
    """Return ``artifact`` with provenance fields added (never mutates)."""
    src = str(source or "").strip().lower()
    out = dict(artifact)
    out["provenance_source"] = src
    out["universe_as_of"] = universe_as_of
    out["survivorship_flattered"] = src not in SURVIVORSHIP_FREE_SOURCES
    return out


def is_flattered(artifact: dict) -> bool:
    """Missing or null provenance counts as flattered -- unknown is not clean."""
    value = artifact.get("survivorship_flattered", True)
    return True if value is None else bool(value)
