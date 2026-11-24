"""One definition of "this closed row counts toward performance".

Why this file exists
--------------------
Two components decided the same question differently:

  * ``alpha_engine/audit3_tribunal.py`` (``load_rows``) — a 3-value status
    deny-list (``OPEN``, ``PENDING``, ``""``) that never reads ``exit_reason``.
  * ``alpha_engine/resolved_closed_view.py`` — a 5-value status deny-list
    *plus* an ``exit_reason`` deny-list plus a ``STALE*`` prefix rule.

Measured on live data they disagreed on ~4.9k rows (4,868 with
``exit_reason IS NULL``, 100 with a ``STALE*`` prefix). The disagreement was
dormant only because the live ledger happened to run in ``mode: canonical``
with the sidecar present — the ``payload_slice`` fallback applied the weaker
filter. The status halves agreed on zero rows: that half is vacuous today and
these tests do not invent a difference that does not exist.

The fix is one predicate, ``is_performance_scored_row(row)``, in
``resolved_closed_view.py``, encoding the CANONICAL semantics (the stricter,
already-published definition), called by both consumers.

The tests below are written so that the drift test fails on a real assertion
— not on an ImportError — before the predicate exists: it compares the two
*existing* code paths (``load_rows`` vs ``default_exclusion_reason``), and the
predicate-existence tests fail with ``assert pred is not None``.
"""
from __future__ import annotations

import json

import pytest

from alpha_engine import resolved_closed_view as rcv
from alpha_engine.audit3_tribunal import load_rows


def _row(row_id: str, status: str, exit_reason, pnl: float = 1.0,
         closed_at: str | None = "2026-11-01T00:00:00Z", **extra) -> dict:
    row = {
        "id": row_id,
        "symbol": "BTCUSDT",
        "direction": "LONG",
        "strategy": "fixture_strategy",
        "entry_price": 100.0,
        "status": status,
        "exit_reason": exit_reason,
        "pnl_pct": pnl,
        "asset_class": "CRYPTO",
    }
    if closed_at is not None:
        row["closed_at"] = closed_at
    row.update(extra)
    return row


#: Rows where the two filters DISAGREE today, plus controls where they agree.
#: Every disagreeing row has a non-zero pnl and a plausible status, so the only
#: thing separating it from a scored row is the exit/status clause under test.
FIXTURE: list[dict] = [
    # control: a real closed trade — both keep it.
    _row("r_normal", "TP_HIT", "TAKE_PROFIT", pnl=3.0),
    # exit_reason NULL, non-zero pnl, no close marker, non-terminal status:
    # tribunal keeps, canonical drops. This is the measured live shape — a
    # null exit is only acceptable when something else proves the row closed.
    _row("r_null_exit", "TIME_EXIT", None, pnl=-1.5, closed_at=None),
    # exit_reason NULL but terminally resolved with a close marker: canonical
    # KEEPS it (the status is evidence of closure), so the tribunal must too.
    _row("r_null_exit_terminal", "WON", None, pnl=2.2),
    # STALE* prefix: tribunal keeps, canonical drops.
    _row("r_stale_exit", "TIME_EXIT", "STALE_OPEN_BACKFILL", pnl=0.4),
    # status the old tribunal deny-list admits but canonical drops.
    _row("r_cancelled_status", "CANCELLED", "STOP_LOSS", pnl=-2.0),
    # exit_reason in the canonical deny-list: tribunal keeps, canonical drops.
    _row("r_manual_exit", "TIME_EXIT", "MANUAL", pnl=1.1),
    # control: unresolved — both drop it.
    _row("r_open", "OPEN", "", pnl=0.0),
]

#: Ids the canonical semantics keep. The tribunal must keep exactly these.
EXPECTED_KEPT = ["r_normal", "r_null_exit_terminal"]


def _tribunal_kept_ids(rows: list[dict], tmp_path) -> list[str]:
    """Admission as the tribunal actually decides it — by running ``load_rows``.

    Deliberately not a reimplementation of the filter: a copy in the test would
    drift from the real one and the drift test would prove nothing.
    """
    payload = tmp_path / "picks.json"
    payload.write_text(json.dumps({"generated_at": "2026-11-20T00:00:00Z",
                                   "picks": rows}), encoding="utf-8")
    kept, _ = load_rows(str(payload))
    return sorted(r["id"] for r in kept)


def _canonical_kept_ids(rows: list[dict]) -> list[str]:
    """Admission as the canonical view attributes it: kept == no exclusion reason."""
    return sorted(r["id"] for r in rows if rcv.default_exclusion_reason(r) is None)


def _predicate():
    """The shared predicate, or None before it exists (a clean assertion, not an error)."""
    return getattr(rcv, "is_performance_scored_row", None)


# ── The drift test ────────────────────────────────────────────────────────────
def test_tribunal_and_canonical_agree_row_by_row(tmp_path):
    """DRIFT TEST — the one that fails if the two implementations ever diverge again.

    Intent: for EVERY row in the fixture, whatever the tribunal uses to admit
    rows and whatever the canonical view uses must produce the SAME boolean.
    Two filters answering one question is the bug; this asserts there is one
    answer. It fails today because the tribunal never reads ``exit_reason``.
    """
    tribunal = set(_tribunal_kept_ids(FIXTURE, tmp_path))
    canonical = set(_canonical_kept_ids(FIXTURE))
    per_row = {
        r["id"]: (r["id"] in tribunal) == (r["id"] in canonical) for r in FIXTURE
    }
    assert all(per_row.values()), (
        f"filters disagree on {sorted(k for k, ok in per_row.items() if not ok)}: "
        f"tribunal={sorted(tribunal)} canonical={sorted(canonical)}"
    )


def test_kept_ids_equal_canonical(tmp_path):
    """The tribunal keeps exactly the canonical rows — the exit condition of Phase A."""
    assert _tribunal_kept_ids(FIXTURE, tmp_path) == EXPECTED_KEPT


# ── The predicate itself ─────────────────────────────────────────────────────
def test_predicate_exists():
    assert _predicate() is not None, (
        "resolved_closed_view.is_performance_scored_row is missing — the two "
        "consumers have no single definition to share"
    )


def test_predicate_excludes_null_exit_reason():
    """exit_reason NULL, no close marker, non-terminal status → not scored."""
    pred = _predicate()
    assert pred is not None
    row = _row("x", "TIME_EXIT", None, pnl=-1.5, closed_at=None)
    assert pred(row) is False


def test_predicate_keeps_null_exit_when_terminal():
    """A terminal status is itself evidence of closure — canonical keeps it."""
    pred = _predicate()
    assert pred is not None
    assert pred(_row("x", "WON", None, pnl=2.2)) is True
    assert pred(_row("x", "TIME_EXIT", None, pnl=2.2)) is True  # close marker


def test_predicate_excludes_stale_prefix():
    """A STALE* exit is a stale/backfill row, never a realised outcome."""
    pred = _predicate()
    assert pred is not None
    row = _row("x", "TIME_EXIT", "STALE_OPEN_BACKFILL", pnl=0.4)
    assert pred(row) is False


def test_predicate_excludes_cancelled_status():
    """CANCELLED is a non-resolution even when the exit reason looks normal."""
    pred = _predicate()
    assert pred is not None
    row = _row("x", "CANCELLED", "STOP_LOSS", pnl=-2.0)
    assert pred(row) is False


def test_predicate_includes_real_exit():
    """A real exit reason with a resolved status is a scored row."""
    pred = _predicate()
    assert pred is not None
    row = _row("x", "TP_HIT", "TAKE_PROFIT", pnl=3.0)
    assert pred(row) is True


@pytest.mark.parametrize("row", FIXTURE, ids=[r["id"] for r in FIXTURE])
def test_predicate_matches_canonical_exclusion(row):
    """The predicate and the canonical exclusion reason are one decision, not two."""
    pred = _predicate()
    assert pred is not None
    assert pred(row) == (rcv.default_exclusion_reason(row) is None)
