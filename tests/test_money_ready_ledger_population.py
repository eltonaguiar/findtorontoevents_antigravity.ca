"""Invariant tests for the /audit money_ready_verdict ledger populations.

These target three defects that were LIVE on 2026-11-20 and that a reader could
have caught from the shipped JSON alone — no statistics required.

Why these test the GENERATOR and not the shipped JSON
-----------------------------------------------------
`audit_dashboard/data/money_ready_verdict.json` is a build artifact regenerated
by the hourly publisher. Asserting directly on it means the suite goes red for an
hour after this fix merges, purely because CI has not re-published yet — which
trains everyone to ignore red. So we assert on the code that produces the
artifact. When the publisher runs, the artifact necessarily inherits the fix.

Background
----------
1. TWO POPULATIONS, ONE TABLE.
   `n`          -> the class's own picks from the JSON source
                   (closed_picks / dashboard_fallback)
   `n_resolved` -> the SIZING cohort, i.e. `at_signal_outcomes` intrabar rows
   Different populations, so `n_resolved > n` is arithmetically impossible and
   is a hard tell that the two numbers describe different row sets. The shipped
   file violated it on 5 of 11 classes:
       EQUITY 257>213, FOREX 634>458, ETF 53>29, COMMODITY 234>27, FUTURES 62>17

2. SURVIVORSHIP IN THE INTRABAR LEDGER.
   `_intrabar_truth_map()` selected only TP_HIT/SL_HIT, dropping every
   TIME_EXIT: 1695 of 6928 genuinely-resolved trades (24.6%). Trades that hit
   neither target nor stop are exactly the ones that decide whether a
   "2:1 reward:risk" book actually pays.

3. TIME_EXIT ON STILL-OPEN ROWS.
   ~40k rows carry intrabar_status='TIME_EXIT' with closed_at IS NULL and
   intrabar_pnl_pct=0.0000. TIME_EXIT asserts "closed at the horizon", which
   cannot be true for an open row. Those phantom 0.0% break-evens leak into the
   ledger.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
MIN_N_CLASS = 100


# --------------------------------------------------------------------------
# 1. The population invariant (pure function — always runs)
# --------------------------------------------------------------------------
def test_population_invariant_flags_subset_larger_than_parent():
    """`n_resolved > n` is impossible for one cohort, so it must be flagged."""
    from alpha_engine.money_ready_verdict import _population_invariant

    flagged = _population_invariant(213, 257, "dashboard_fallback", "intrabar_truth")
    assert flagged["population_mismatch"] is True
    assert "257" in flagged["population_note"]
    assert "213" in flagged["population_note"]
    assert "DIFFERENT COHORTS" in flagged["population_note"]


def test_population_invariant_is_quiet_when_cohorts_are_consistent():
    """No false positive when n_resolved genuinely is a subset of n."""
    from alpha_engine.money_ready_verdict import _population_invariant

    clean = _population_invariant(3726, 3726, "closed_picks", "intrabar_truth")
    assert clean["population_mismatch"] is False
    assert clean["population_note"] is None


def test_population_invariant_never_raises_on_zero_n():
    """Degenerate MUTUAL_FUND-style rows (n=0) must not blow up the generator."""
    from alpha_engine.money_ready_verdict import _population_invariant

    zero = _population_invariant(0, 0, "backfill_no_data", "intrabar_truth")
    assert zero["population_mismatch"] is False


def test_all_five_measured_violations_are_detected():
    """Regression pin: the exact 2026-11-20 violations must all be caught."""
    from alpha_engine.money_ready_verdict import _population_invariant

    measured = {
        "EQUITY": (213, 257), "FOREX": (458, 634), "ETF": (29, 53),
        "COMMODITY": (27, 234), "FUTURES": (17, 62),
    }
    missed = [
        ac for ac, (n, nr) in measured.items()
        if not _population_invariant(
            n, nr, "dashboard_fallback", "intrabar_truth")["population_mismatch"]
    ]
    assert not missed, f"undetected cohort mismatches: {missed}"


# --------------------------------------------------------------------------
# 2. The survivorship invariant (DB read-only; skips cleanly if unreachable)
# --------------------------------------------------------------------------
@pytest.fixture(scope="module")
def intrabar_truth():
    """Call the real generator once per module. Skips if DB unreachable."""
    try:
        from alpha_engine import money_ready_verdict as m
    except Exception as exc:  # pragma: no cover - env dependent
        pytest.skip(f"cannot import generator: {exc}")
    m._INTRABAR_TRUTH_ENABLED = True
    try:
        data = m._intrabar_truth_map()
    except Exception as exc:  # pragma: no cover - env dependent
        pytest.skip(f"intrabar ledger unreachable: {exc}")
    if not data:
        pytest.skip("intrabar ledger returned no rows")
    return data


def test_intrabar_truth_exposes_both_decided_and_all_status_cohorts(intrabar_truth):
    """`wr` alone is decided-only; `wr_all` must sit beside it."""
    for ac, row in intrabar_truth.items():
        if not row.get("n"):
            continue
        assert "wr_all" in row, (
            f"{ac}: publishes decided-only 'wr' with no 'wr_all' — TIME_EXIT rows "
            "are being dropped (survivorship bias)"
        )
        assert row.get("n_all", 0) >= row.get("n", 0), (
            f"{ac}: n_all={row.get('n_all')} < n={row.get('n')}; the all-status "
            "cohort must be a superset of the decided cohort"
        )
        assert "survivorship_gap_pp" in row, (
            f"{ac}: survivorship_gap_pp missing — readers cannot tell how much "
            "the decided-only cohort distorts the book"
        )


def test_survivorship_gap_matches_the_two_win_rates(intrabar_truth):
    """`survivorship_gap_pp` must be exactly (wr - wr_all) in percentage points."""
    checked = 0
    for ac, row in intrabar_truth.items():
        gap, wr, wr_all = row.get("survivorship_gap_pp"), row.get("wr"), row.get("wr_all")
        if gap is None or wr is None or wr_all is None:
            continue
        checked += 1
        assert abs(gap - round((wr - wr_all) * 100, 2)) < 0.02, (
            f"{ac}: survivorship_gap_pp={gap} but (wr-wr_all)*100="
            f"{round((wr - wr_all) * 100, 2)}"
        )
    assert checked, "no comparable survivorship gaps found"


def test_time_exit_share_is_reported_and_bounded(intrabar_truth):
    """time_exit_share must be a real fraction, never a phantom artefact."""
    for ac, row in intrabar_truth.items():
        if not row.get("n_all"):
            continue
        share = row.get("time_exit_share")
        assert share is not None, f"{ac}: time_exit_share missing"
        assert 0.0 <= share <= 1.0, f"{ac}: time_exit_share={share} out of range"
        assert row.get("n_time_exit", 0) <= row["n_all"], (
            f"{ac}: n_time_exit={row.get('n_time_exit')} exceeds n_all={row['n_all']}"
        )


# --------------------------------------------------------------------------
# 3. The TIME_EXIT mislabelling (xfail until the backfill runs)
# --------------------------------------------------------------------------
@pytest.mark.xfail(
    reason="40,228 still-OPEN rows are mislabelled intrabar_status='TIME_EXIT' "
           "with closed_at NULL. Fix = UPDATE ... SET intrabar_status='OPEN' "
           "WHERE intrabar_status='TIME_EXIT' AND closed_at IS NULL. Held back "
           "from this PR because it mutates production; remove this marker "
           "once the backfill has run.",
    strict=False,
)
def test_no_time_exit_with_null_closed_at():
    """TIME_EXIT asserts 'closed at the horizon' — impossible for an open row."""
    try:
        import pymysql
        from tools.db_env import get_stocks_creds
    except Exception as exc:  # pragma: no cover - env dependent
        pytest.skip(f"DB tooling unavailable: {exc}")

    try:
        creds = {k: v for k, v in get_stocks_creds().items()
                 if k in ("host", "user", "password", "database", "port",
                          "connect_timeout")}
        conn = pymysql.connect(**creds)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM at_signal_outcomes "
                "WHERE intrabar_status='TIME_EXIT' AND closed_at IS NULL"
            )
            bad = int(cur.fetchone()[0] or 0)
        conn.close()
    except Exception as exc:  # pragma: no cover - env dependent
        pytest.skip(f"could not query at_signal_outcomes: {exc}")

    assert bad == 0, (
        f"{bad} rows labelled intrabar_status='TIME_EXIT' with closed_at NULL — "
        "those are still-OPEN positions, not time exits"
    )


# --------------------------------------------------------------------------
# 4. The sample floor (a real invariant, just not the bug it was assumed to be)
# --------------------------------------------------------------------------
def test_thin_classes_are_never_marked_money_ready():
    """A class with < MIN_N_CLASS resolved trades must not be MONEY_READY."""
    from alpha_engine.money_ready_verdict import _verdict

    # pf 5.0 / wr 90% on 99 trades is the most flattering thing you can hand the
    # gate. It must still refuse, on sample size alone.
    verdict = _verdict(MIN_N_CLASS - 1, 0.90, 5.0, None, None, None,
                       asset_class="CRYPTO")
    assert verdict == "INSUFFICIENT_DATA", (
        f"n={MIN_N_CLASS - 1} with a perfect-looking PF was graded {verdict!r}"
    )


def test_floor_admits_a_qualified_sample():
    """Sanity: the floor must not be so strict that nothing can ever pass it."""
    from alpha_engine.money_ready_verdict import _verdict

    verdict = _verdict(MIN_N_CLASS, 0.55, 1.8, {}, {}, {},
                       asset_class="CRYPTO")
    assert verdict != "INSUFFICIENT_DATA", (
        "a class at exactly the sample floor is being refused for insufficient "
        "data — the floor is off by one"
    )
