"""Tests for the forward-ledger ingestion adapter. No DB: pure functions + tmp files."""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alpha_engine import forward_observations as FO
from alpha_engine import forward_observations_ingest as ING

NOW = datetime(2026, 11, 19, 12, 0, tzinfo=timezone.utc)
H = 3600_000


def _cohort(**over):
    row = {
        "id": 1, "symbol": "BTCUSDT", "direction": "LONG", "asset_class": "CRYPTO",
        "entry_price": 100.0, "exit_price": 101.0, "intrabar_pnl_pct": 1.0,
        "intrabar_status": "TP_HIT", "opened_at": datetime(2026, 11, 1, 14, 0),
        "intrabar_resolved_at": datetime(2026, 11, 1, 18, 0),
        "strategy": "ensemble", "source_system": "alpha_engine",
    }
    row.update(over)
    return row


def _feats(**over):
    f = {"F1": "x", "F2": "y", "F3": "50-70", "F4": "z", "F5": "US", "dow": 0}
    f.update(over)
    return f


def _bars(n=6, start=100.0, end=105.0):
    """Hourly bars covering the row's window."""
    return [(i * H + int(datetime(2026, 11, 1, 14, 0, tzinfo=timezone.utc).timestamp() * 1000),
             start + (end - start) * i / max(1, n - 1)) for i in range(n)]


# ─────────────────────────────────────────────────────────── row construction ──
def test_admissible_row_satisfies_the_contract():
    row, reason = ING.row_from_cohort(_cohort(), _feats(), _bars(), "H-119", now=NOW)
    assert reason is None
    assert FO.validate(row, {"H-119"}) == []
    # net return = gross - 16bp RT, and it reproduces the canonical outcome
    assert FO.net_returns([row])[0] * 100 == pytest.approx(1.0 - 0.16, abs=1e-9)


def test_short_rows_are_signed_correctly():
    row, _ = ING.row_from_cohort(
        _cohort(direction="SHORT", entry_price=100.0, exit_price=99.0,
                intrabar_pnl_pct=1.0), _feats(), _bars(), "H-119", now=NOW)
    assert row["side"] == "SHORT"
    assert FO.net_returns([row])[0] * 100 == pytest.approx(1.0 - 0.16, abs=1e-9)


def test_id_is_deterministic_so_reruns_are_idempotent():
    a, _ = ING.row_from_cohort(_cohort(), _feats(), _bars(), "H-119", now=NOW)
    b, _ = ING.row_from_cohort(_cohort(), _feats(), _bars(), "H-119", now=NOW)
    assert a["id"] == b["id"]
    other, _ = ING.row_from_cohort(
        _cohort(opened_at=datetime(2026, 11, 2, 14, 0)), _feats(), _bars(),
        "H-119", now=NOW)
    assert other["id"] != a["id"]


# ────────────────────────────────────────────────────────────── integrity gate ──
def test_exit_price_is_reconciled_to_the_resolved_return():
    # entry/exit imply +1% but the resolver says +40%. ~58% of honest rows look like
    # this, so the outcome wins and the disagreement is preserved for audit.
    row, reason = ING.row_from_cohort(
        _cohort(intrabar_pnl_pct=40.0), _feats(), _bars(), "H-119", now=NOW)
    assert reason is None
    assert row["exit_px"] == pytest.approx(140.0)
    assert FO.net_returns([row])[0] * 100 == pytest.approx(40.0 - 0.16, abs=1e-9)
    assert row["resolver_exit_px"] == 101.0
    assert row["gross_mismatch_pp"] == pytest.approx(39.0)   # labelled, not hidden


def test_missing_price_is_rejected():
    row, reason = ING.row_from_cohort(
        _cohort(entry_price=None), _feats(), _bars(), "H-119", now=NOW)
    assert row is None
    assert reason == "missing_price_or_outcome"


def test_a_missing_resolver_exit_still_yields_a_row_with_a_null_audit_field():
    row, reason = ING.row_from_cohort(
        _cohort(exit_price=None), _feats(), _bars(), "H-119", now=NOW)
    assert reason is None
    assert row["resolver_exit_px"] is None and row["gross_mismatch_pp"] is None


def test_uncompassable_direction_is_rejected():
    row, reason = ING.row_from_cohort(
        _cohort(direction="FLAT"), _feats(), _bars(), "H-119", now=NOW)
    assert row is None
    assert reason == "uncompassable_direction"


# ────────────────────────────────────────────────────────────── attribution ──
def test_only_the_registered_condition_gets_rows():
    assert ING.classify(_feats(), "CRYPTO") == "H-119"
    assert ING.classify(_feats(F3="70-90"), "CRYPTO") is None       # wrong RSI band
    assert ING.classify(_feats(F5="ASIA"), "CRYPTO") is None        # wrong session
    assert ING.classify(_feats(), "EQUITY") is None                 # wrong class
    assert ING.classify(None, "CRYPTO") is None                     # unstamped


def test_equity_breakout_pod_is_classified_by_strategy_and_direction():
    # POD-EQUITY-BREAKOUT (pre-registered) is strategy-keyed, not feature-keyed:
    # its `requires` is empty and it must match on emitter strategy + LONG direction
    # so forward rows accrue to H-BABY-EQUITY-VT-PATTERN-SWEEP-001.
    feats = _feats()
    hid = "H-BABY-EQUITY-VT-PATTERN-SWEEP-001"
    assert ING.classify(feats, "EQUITY", strategy="rs-breakout-scout", direction="LONG") == hid
    assert ING.classify(feats, "ETF", strategy="donchian-stock-breakout", direction="LONG") == hid
    assert ING.classify(feats, "EQUITY", strategy="rs-breakout-scout", direction="SHORT") is None
    assert ING.classify(feats, "EQUITY", strategy="unrelated-momentum", direction="LONG") is None
    assert ING.classify(feats, "CRYPTO", strategy="rs-breakout-scout", direction="LONG") == "H-119"


def test_rows_outside_every_condition_are_skipped_not_rejected():
    rows, rejects, counts = ING.build_rows(
        [(_cohort(), _feats(F5="ASIA"), _bars())], now=NOW)
    assert rows == []
    assert rejects == []
    assert counts["not_in_any_condition"] == 1


def test_rejection_counts_are_reported_per_reason():
    rows, rejects, counts = ING.build_rows(
        [(_cohort(entry_price=None), _feats(), _bars())], now=NOW)
    assert rows == []
    assert counts["rejected_missing_price_or_outcome"] == 1
    assert rejects[0]["reason"] == "missing_price_or_outcome"


# ──────────────────────────────────────────────────────────────── benchmark ──
def test_benchmark_leg_is_direction_adjusted():
    bars = _bars(start=100.0, end=95.0)
    t0, t1 = bars[0][0], bars[3][0]          # real bar timestamps, not bar indices
    long_leg = ING.benchmark_leg(bars, t0, t1, "LONG")
    short_leg = ING.benchmark_leg(bars, t0, t1, "SHORT")
    assert long_leg is not None and long_leg < 0
    assert short_leg is not None and short_leg > 0
    assert short_leg == pytest.approx(-long_leg, abs=1e-12)


def test_missing_bars_leave_the_benchmark_null_rather_than_zero():
    bars = _bars()
    t0, t1 = bars[0][0], bars[3][0]
    assert ING.benchmark_leg([], t0, t1, "LONG") is None
    assert ING.benchmark_leg(bars, None, t1, "LONG") is None
    assert ING.benchmark_leg(bars, t0, t1 + 30 * 86400_000, "LONG") is None  # stale end


def test_close_at_takes_the_bar_at_or_after_the_timestamp():
    bars = [(0, 10.0), (H, 11.0), (2 * H, 12.0)]
    assert ING.close_at(bars, 0) == 10.0
    assert ING.close_at(bars, H + 1) == 12.0
    assert ING.close_at(bars, 2 * H + 1) is None


# ─────────────────────────────────────────────────────────────────── append ──
def test_rerun_appends_nothing_new(tmp_path):
    ledge = tmp_path / "ledger.jsonl"
    row, _ = ING.row_from_cohort(_cohort(), _feats(), _bars(), "H-119", now=NOW)
    first = FO.append([row], ledge)
    second = FO.append([row], ledge)
    assert first["added"] == 1
    assert second["added"] == 0 and second["duplicates"] == 1
    assert FO.verify(ledge)["n_rows"] == 1


def test_cohort_datetime_fields_are_converted_not_stringified_into_nothing():
    # Regression: str(datetime) is parseable, but treating the object as a string in
    # _ms() collapsed every bar window to the epoch and produced 0 stamped rows.
    ms = ING._ms(datetime(2026, 11, 1, 14, 0))
    assert ms == int(datetime(2026, 11, 1, 14, 0, tzinfo=timezone.utc).timestamp() * 1000)
    assert ING._ms(datetime(2026, 11, 1, 14, 0, tzinfo=timezone.utc)) == ms
    row, reason = ING.row_from_cohort(_cohort(), _feats(), _bars(), "H-119", now=NOW)
    assert reason is None
    assert row["opened_at"].startswith("2026-11-01T14:00")   # ISO, not "2026-11-01 14:00:00"
    assert FO.validate(row, {"H-119"}) == []


def test_position_pod_is_classified_by_timeframe():
    # H-144 is the CRYPTO POSITION-horizon pod; it has no entry-condition stamp.
    assert ING.classify(None, "CRYPTO", timeframe="POSITION") == "H-144"
    # precedence: a POSITION row that also carries H-119's RSI/session stamp stays
    # with H-119, so this pod cannot rewrite an existing attribution
    assert ING.classify(_feats(), "CRYPTO", timeframe="POSITION") == "H-119"
    # other horizons and other classes must not be captured
    assert ING.classify(None, "CRYPTO", timeframe="INTRADAY") is None
    assert ING.classify(None, "ETF", timeframe="POSITION") is None


def test_feature_keyed_pod_still_needs_its_stamp():
    # The guard change must not let a feature-keyed pod match unstamped rows.
    assert ING.classify(None, "CRYPTO") is None
    assert ING.classify(_feats(), "CRYPTO") == "H-119"
    # ...and a strategy-keyed pod no longer needs features to classify.
    assert ING.classify(None, "EQUITY", strategy="rs-breakout-scout",
                        direction="LONG") == "H-BABY-EQUITY-VT-PATTERN-SWEEP-001"


def test_unmatched_strategies_are_reported_not_hidden():
    """3,334 cohort rows vanish into one opaque skip; the report must name them."""
    from collections import Counter
    unmatched = Counter()
    entries = [({"asset_class": "EQUITY", "strategy": "mystery_strategy",
                 "direction": "LONG"}, None, [])]
    rows, rejects, counts = ING.build_rows(entries, unmatched_out=unmatched)
    assert rows == [] and counts["not_in_any_condition"] == 1
    assert unmatched[("EQUITY", "mystery_strategy")] == 1


def test_registered_breakout_pod_claims_its_strategies():
    """POD-EQUITY-BREAKOUT must keep matching its four registered strategies."""
    for strat in ("donchian-stock-breakout", "rs-breakout-scout",
                  "vol-contraction-scout", "adx-trend-scout"):
        assert (ING.classify(None, "EQUITY", strategy=strat, direction="LONG")
                == "H-BABY-EQUITY-VT-PATTERN-SWEEP-001")
        assert (ING.classify(None, "ETF", strategy=strat, direction="LONG")
                == "H-BABY-EQUITY-VT-PATTERN-SWEEP-001")

def test_registered_emitting_pods_are_wired_to_their_hypotheses():
    """Pods whose strategies emit but had no condition never accrued forward rows."""
    assert ING.classify(None, "ETF", strategy="etf_faber_tactical",
                        direction="LONG") == "H-2026-11-19-03"
    assert ING.classify(None, "EQUITY", strategy="faber_taa",
                        direction="LONG") == "H-2026-11-19-03"
    assert ING.classify(None, "ETF", strategy="etf_dual_momentum",
                        direction="LONG") == "H-2026-11-19-06"
    assert ING.classify(None, "COMMODITY", strategy="contango_roll_yield",
                        direction="SHORT") == "H-2026-11-19-05"
    assert ING.classify(None, "COMMODITY", strategy="contango_roll_yield",
                        direction="LONG") == "H-2026-11-19-05"
    # Direction still gates: the Faber sleeve is long-only.
    assert ING.classify(None, "ETF", strategy="etf_faber_tactical",
                        direction="SHORT") is None
