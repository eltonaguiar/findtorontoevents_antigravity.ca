"""One population artifact, so every rate names the rows it is computed over.

2026-11-21 collective review: "closed picks" was quoted as 4,618, 1,927, 8,769,
16,372 and 7,942 across /audit, /audit2 and /audit3, and the audit3 ledger's own
``scored_share_of_valid_pct_status`` was ``not_comparable`` because scored rows
(8,769) exceeded ``valid_closed_picks`` (7,942) -- 110.41%. Every win rate, PF and
kill rate divided by a different population and no reader could tell which.

This module builds the single sidecar (``audit_dashboard/data/denominator.json``)
that states each population once:

    canonical_sha256    hash of the canonical resolved rows (pins the book)
    n_canonical         rows in that view -- what audit3 actually scores
    n_total_closed      every closed pick the publisher knows about
    exclusion_reasons   [{reason, n}] why total - canonical is not scored

A missing input is reported as ``null`` plus a note. It is never coerced to 0 or
to 1: "population unknown" must read differently from "no rows".
"""
from __future__ import annotations

from typing import Any

SCHEMA = "audit.denominator.v1"


def _int(value: Any) -> int | None:
    """Non-negative int, else None. Booleans are not counts."""
    if isinstance(value, bool):
        return None
    try:
        n = int(value)
    except (TypeError, ValueError):
        return None
    return n if n >= 0 else None


def _merge_reasons(*blocks: Any) -> list[dict]:
    """Merge {reason: n} maps from several pipelines into one ranked list."""
    merged: dict[str, int] = {}
    for block in blocks:
        if not isinstance(block, dict):
            continue
        for key, value in block.items():
            n = _int(value)
            if not n:
                continue
            merged[str(key)] = merged.get(str(key), 0) + n
    return [{"reason": k, "n": v}
            for k, v in sorted(merged.items(), key=lambda kv: (-kv[1], kv[0]))]


def format_label(denominator: dict) -> str:
    """Render the population as the one sentence every page can print."""
    n = _int(denominator.get("n_canonical"))
    total = _int(denominator.get("n_total_closed"))
    if n is None:
        return "population unknown (no canonical row count)"
    if not total:
        return f"{n:,} canonical rows (book size unknown)"
    share = 100.0 * n / total
    sha = denominator.get("canonical_sha256")
    tail = f" · sha {str(sha)[:12]}" if sha else ""
    return f"{n:,} of {total:,} closed picks scored ({share:.1f}%){tail}"


def build(dashboard: dict | None = None,
          ledger: dict | None = None,
          *, generated_at: str | None = None) -> dict:
    """Build the denominator sidecar from the two canonical inputs.

    Precedence: the publisher's own canonical view
    (``dashboard_data.resolved_closed_picks_net``) wins; the audit3 ledger's
    ``coverage.denominator`` is the fallback and is named in ``canonical_source``
    so a reader can tell which pipeline produced the number.
    """
    dash = dashboard if isinstance(dashboard, dict) else {}
    canon = dash.get("resolved_closed_picks_net")
    canon = canon if isinstance(canon, dict) else {}
    counts = canon.get("counts") if isinstance(canon.get("counts"), dict) else {}

    cov = (ledger or {}).get("coverage") if isinstance(ledger, dict) else {}
    cov = cov if isinstance(cov, dict) else {}
    den = cov.get("denominator") if isinstance(cov.get("denominator"), dict) else {}

    n_canonical = _int(counts.get("kept_rows"))
    sha = canon.get("rows_sha256") or den.get("canonical_rows_sha256")
    canonical_source = "dashboard_data.resolved_closed_picks_net"
    if n_canonical is None:
        # Fall back to whichever pipeline did record a canonical count.
        n_canonical = _int(den.get("canonical_kept_rows"))
        if n_canonical is None:
            n_canonical = _int(cov.get("scored_rows"))
        if n_canonical is not None:
            canonical_source = "audit3_ledger.coverage"

    n_total = _int(cov.get("total_closed_picks"))
    n_valid = _int(cov.get("valid_closed_picks"))
    # The two inputs are written by different jobs and can be hours apart. If the
    # ledger's canonical count disagrees with the publisher's, the "share of the
    # closed book" below mixes snapshots -- say so instead of publishing a ratio
    # of two different books.
    ledger_canonical = _int(den.get("canonical_kept_rows"))
    reasons = _merge_reasons(counts.get("excluded_by_reason"),
                             den.get("canonical_excluded_by_reason"))
    n_unscored = (n_total - n_canonical
                  if n_total is not None and n_canonical is not None else None)

    notes: list[str] = []
    if n_canonical is None:
        notes.append("no canonical row count in either input -- population unknown, not zero")
    if sha is None:
        notes.append("no canonical rows hash -- the population cannot be pinned to a book")
    if n_total is None:
        notes.append("no total_closed_picks -- the share of the closed book is unknown")
    if (ledger_canonical is not None and n_canonical is not None
            and ledger_canonical != n_canonical):
        notes.append(
            f"input snapshots differ: canonical view {n_canonical:,} rows vs "
            f"ledger canonical {ledger_canonical:,} -- the share below mixes two "
            "runs, so compare surfaces by hash, not by percentage")
    if n_unscored is not None and reasons:
        explained = sum(r["n"] for r in reasons)
        if explained != n_unscored:
            notes.append(
                f"exclusion reasons total {explained:,} but total - canonical = "
                f"{n_unscored:,}: the publisher and the tribunal exclude different "
                "cohorts, so these are separate pipelines, not one subtraction")

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at": generated_at,
        "canonical_source": canonical_source,
        "canonical_schema": canon.get("schema") or den.get("canonical_schema"),
        "canonical_sha256": sha,
        "n_canonical": n_canonical,
        "n_total_closed": n_total,
        "n_valid_closed": n_valid,
        "n_unscored": n_unscored,
        "exclusion_reasons": reasons,
        "sources": {
            "dashboard": "audit_dashboard/data/dashboard_data.json",
            "ledger": "audit_dashboard/data/audit3_ledger.json",
            "dashboard_generated_at": dash.get("generated_at"),
            "ledger_generated_at": (ledger or {}).get("generated_at")
            if isinstance(ledger, dict) else None,
        },
        "notes": notes,
    }
    payload["complete"] = bool(n_canonical is not None and sha and n_total is not None)
    payload["population_label"] = format_label(payload)
    return payload
