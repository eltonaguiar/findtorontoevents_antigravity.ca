"""Tests for audit_trail.stop_fill — resting-stop vs late-polled fills."""
import pytest

from audit_trail import stop_fill as sf


def _row(**kw):
    base = {
        "symbol": "BTCUSDT",
        "direction": "LONG",
        "entry_price": 100.0,
        "stop_loss": 98.0,
        "take_profit": 104.0,
        "exit_price": 98.0,
        "exit_reason": "SL_HIT",
        "pnl_pct": -2.0,
        "asset_class": "CRYPTO",
    }
    base.update(kw)
    return base


# --- risk measures ---------------------------------------------------------
def test_planned_risk_long_and_short():
    assert sf.planned_risk_pct(_row()) == pytest.approx(2.0)
    assert sf.planned_risk_pct(
        {"direction": "SHORT", "entry_price": 100.0, "stop_loss": 102.0}
    ) == pytest.approx(2.0)


def test_planned_risk_missing_fields_is_none():
    assert sf.planned_risk_pct({"entry_price": 100.0}) is None
    assert sf.planned_risk_pct({"entry_price": 100.0, "stop_loss": 0}) is None


def test_realized_risk_is_direction_aware():
    # LONG: exit below entry is an adverse move
    assert sf.realized_risk_pct(_row(exit_price=97.0)) == pytest.approx(3.0)
    # SHORT: exit above entry is the adverse move
    short = _row(direction="SHORT", entry_price=100.0, stop_loss=102.0, exit_price=103.0)
    assert sf.realized_risk_pct(short) == pytest.approx(3.0)


def test_slippage_is_realized_minus_planned():
    assert sf.stop_slippage_pct(_row(exit_price=98.0)) == pytest.approx(0.0)
    assert sf.stop_slippage_pct(_row(exit_price=97.0)) == pytest.approx(1.0)


# --- counterfactual --------------------------------------------------------
def test_pnl_at_stop_long_is_negative_planned_risk():
    assert sf.pnl_at_stop(_row()) == pytest.approx(-2.0)


def test_pnl_at_stop_short_is_negative_planned_risk():
    short = _row(direction="SHORT", entry_price=100.0, stop_loss=102.0, exit_price=102.0, pnl_pct=-2.0)
    assert sf.pnl_at_stop(short) == pytest.approx(-2.0)


# --- classification --------------------------------------------------------
def test_classify_exact_fill_uses_relative_tolerance():
    assert sf.classify_row(_row()) == sf.BASIS_STOP
    # a 1-cent miss on a 100 entry is a real different fill, not float noise
    assert sf.classify_row(_row(exit_price=98.01)) == sf.BASIS_LATE


def test_classify_late_fill():
    assert sf.classify_row(_row(exit_price=96.7)) == sf.BASIS_LATE


def test_classify_non_stop_reason_is_unmeasured():
    assert sf.classify_row(_row(exit_reason="TP_HIT")) == sf.BASIS_UNMEASURED


def test_classify_missing_exit_is_unmeasured():
    assert sf.classify_row(_row(exit_price=None)) == sf.BASIS_UNMEASURED
    assert sf.classify_row(_row(stop_loss=0)) == sf.BASIS_UNMEASURED


# --- annotation must not rewrite the realized result ------------------------
def test_annotate_preserves_pnl_and_adds_fields():
    row = _row(exit_price=96.7, pnl_pct=-3.3)
    ann = sf.annotate_row(row)
    assert ann["pnl_pct"] == -3.3, "annotation must never rewrite the realized PnL"
    assert row.get("stop_fill_basis") is None, "originals stay untouched"
    assert ann["stop_fill_basis"] == sf.BASIS_LATE
    assert ann["planned_risk_pct"] == pytest.approx(2.0)
    assert ann["realized_risk_pct"] == pytest.approx(3.3)
    assert ann["stop_slippage_pct"] == pytest.approx(1.3)
    assert ann["pnl_pct_at_stop"] == pytest.approx(-2.0)
    # filling at the stop would have cost 1.3pp less
    assert ann["stop_fill_cost_pp"] == pytest.approx(1.3)


# --- intrabar fill model ---------------------------------------------------
BARS = [
    {"open": 100.0, "high": 101.0, "low": 99.5},
    {"open": 99.4, "high": 99.6, "low": 97.5},   # spans the stop
    {"open": 97.4, "high": 97.8, "low": 96.0},
]


def test_find_stop_fill_returns_stop_when_bar_spans_it():
    fill = sf.find_stop_fill("LONG", 98.0, BARS)
    assert fill["price"] == pytest.approx(98.0)
    assert fill["basis"] == sf.BASIS_STOP
    assert fill["bar_index"] == 1


def test_find_stop_fill_uses_open_on_gap_through():
    bars = [
        {"open": 100.0, "high": 101.0, "low": 99.5},
        {"open": 96.0, "high": 96.5, "low": 95.0},  # gaps straight past 98
    ]
    fill = sf.find_stop_fill("LONG", 98.0, bars)
    assert fill["price"] == pytest.approx(96.0)
    assert fill["basis"] == sf.BASIS_GAP


def test_find_stop_fill_short_side():
    bars = [{"open": 100.0, "high": 100.5, "low": 99.0},
            {"open": 101.0, "high": 102.5, "low": 100.8}]
    fill = sf.find_stop_fill("SHORT", 102.0, bars)
    assert fill["price"] == pytest.approx(102.0)
    assert fill["basis"] == sf.BASIS_STOP


def test_find_stop_fill_short_gap_through_uses_open():
    bars = [{"open": 103.0, "high": 104.0, "low": 102.5}]
    fill = sf.find_stop_fill("SHORT", 102.0, bars)
    assert fill["price"] == pytest.approx(103.0)
    assert fill["basis"] == sf.BASIS_GAP


def test_find_stop_fill_never_breached_is_none():
    assert sf.find_stop_fill("LONG", 90.0, BARS) is None
    assert sf.find_stop_fill("LONG", None, BARS) is None
    assert sf.find_stop_fill("LONG", 98.0, []) is None


def test_find_stop_fill_skips_bars_without_range():
    bars = [{"open": 99.0}, {"open": 99.4, "high": 99.6, "low": 97.5}]
    fill = sf.find_stop_fill("LONG", 98.0, bars)
    assert fill["bar_index"] == 1


# --- summary ---------------------------------------------------------------
def test_summarize_counts_and_totals():
    rows = [
        _row(exit_price=98.0, pnl_pct=-2.0),      # exact
        _row(exit_price=96.7, pnl_pct=-3.3),      # late
        _row(exit_reason="TP_HIT", exit_price=104.0, pnl_pct=4.0),
    ]
    s = sf.summarize(rows)["CRYPTO"]
    assert s["n_closed"] == 3
    assert s["n_sl"] == 2
    assert s["n_filled_at_stop"] == 1
    assert s["n_late_fill"] == 1
    assert s["mean_planned_risk_pct"] == pytest.approx(2.0)
    assert s["mean_realized_risk_pct"] == pytest.approx(2.65)
    assert s["overshoot_ratio"] == pytest.approx(1.325)
    # pnl totals are restricted to stopped rows by construction (non-stopped rows
    # have a different exit mechanism and are not part of this comparison)
    assert s["pnl_pp_total"] == pytest.approx(-5.3)
    assert s["pnl_pp_total_stop_matched"] == pytest.approx(-5.3)
    assert s["pnl_at_stop_pp_total"] == pytest.approx(-4.0)
    # filling both stops at the stop would have cost 1.3pp less on those rows
    assert s["delta_if_filled_at_stop_pp"] == pytest.approx(1.3)
