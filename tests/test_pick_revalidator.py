"""Tests for alpha_engine/pick_revalidator.py.

Each test corresponds to a real pattern observed during 2026-04-30 / 2026-05-01
trading sessions where the gate would have prevented a futile trade attempt.
"""
import pytest
from alpha_engine.pick_revalidator import (
    revalidate_pick,
    filter_picks_by_live_quote,
    DEFAULT_RR_ANTIPRED_CUTOFF,
)


def test_long_signal_actionable_passes():
    """LTC LONG @ 55.20 with TP 58.14 / SL 53.94 — actionable, R:R from live ~2.3."""
    pick = {"direction": "LONG", "entry_price": 55.23, "take_profit": 58.14, "stop_loss": 53.94}
    r = revalidate_pick(pick, live_price=55.20)
    assert r["verdict"] == "OK"
    assert r["ok"] is True
    assert 1.5 < r["rr_live"] < 3.0


def test_short_signal_already_played_out_tp(caplog):
    """USDJPY SHORT @ 157.29 / TP 156.81 — but live 156.78 has already broken TP."""
    pick = {"direction": "SHORT", "entry_price": 157.29, "take_profit": 156.81, "stop_loss": 157.60}
    r = revalidate_pick(pick, live_price=156.78)
    assert r["verdict"] == "PLAYED_OUT_TP"
    assert r["ok"] is False


def test_short_signal_already_stopped_out():
    """CT=F SHORT @ 79.86 / SL 82.45 — but live 84.26 has already breached SL."""
    pick = {"direction": "SHORT", "entry_price": 79.86, "take_profit": 76.40, "stop_loss": 82.45}
    r = revalidate_pick(pick, live_price=84.26)
    assert r["verdict"] == "PLAYED_OUT_SL"
    assert r["ok"] is False


def test_long_signal_stopped_out():
    """APT LONG entered yesterday @ 0.972 / SL 0.952 — live 0.94 has stopped it."""
    pick = {"direction": "LONG", "entry_price": 0.972, "take_profit": 1.066, "stop_loss": 0.952}
    r = revalidate_pick(pick, live_price=0.94)
    assert r["verdict"] == "PLAYED_OUT_SL"
    assert r["ok"] is False


def test_rr_degraded_above_3_blocks():
    """SUI LONG @ 0.9235 / TP 0.9697 / SL 0.8912 — but live moved to 0.9068
    pushes R:R from live to ~4.0, above the IC anti-predictive cutoff."""
    pick = {"direction": "LONG", "entry_price": 0.9235, "take_profit": 0.9697, "stop_loss": 0.8912}
    r = revalidate_pick(pick, live_price=0.9068)
    assert r["verdict"] == "R_R_DEGRADED"
    assert r["ok"] is False
    assert r["rr_live"] >= DEFAULT_RR_ANTIPRED_CUTOFF


def test_buy_alias_treated_as_long():
    """`direction='BUY'` is treated as LONG (per active_picks.json convention)."""
    pick = {"direction": "BUY", "entry_price": 100.0, "take_profit": 105.0, "stop_loss": 98.0}
    r = revalidate_pick(pick, live_price=100.5)
    assert r["verdict"] == "OK"
    assert r["ok"] is True


def test_sell_alias_treated_as_short():
    pick = {"direction": "SELL", "entry_price": 100.0, "take_profit": 95.0, "stop_loss": 102.0}
    r = revalidate_pick(pick, live_price=99.5)
    assert r["verdict"] == "OK"
    assert r["ok"] is True


def test_missing_fields_returns_missing_verdict():
    pick = {"direction": "LONG", "entry_price": 0, "take_profit": 0, "stop_loss": 0}
    r = revalidate_pick(pick, live_price=100)
    assert r["verdict"] == "MISSING_FIELDS"
    assert r["ok"] is False


def test_bad_direction_returns_bad_direction():
    pick = {"direction": "XYZ", "entry_price": 100, "take_profit": 105, "stop_loss": 98}
    r = revalidate_pick(pick, live_price=100)
    assert r["verdict"] == "BAD_DIRECTION"
    assert r["ok"] is False


def test_filter_picks_by_live_quote_segregates_correctly():
    """Mirror the 2026-05-01 pattern: 4 candidates, only LTC OK."""
    picks_with_quotes = [
        # USDJPY SHORT — played out at TP
        ({"direction": "SHORT", "entry_price": 157.29, "take_profit": 156.81, "stop_loss": 157.60}, 156.78),
        # CT=F SHORT — stopped out
        ({"direction": "SHORT", "entry_price": 79.86, "take_profit": 76.40, "stop_loss": 82.45}, 84.26),
        # SUI LONG — R:R degraded
        ({"direction": "LONG", "entry_price": 0.9235, "take_profit": 0.9697, "stop_loss": 0.8912}, 0.9068),
        # LTC LONG — actionable
        ({"direction": "LONG", "entry_price": 55.23, "take_profit": 58.14, "stop_loss": 53.94}, 55.20),
    ]
    kept, dropped = filter_picks_by_live_quote(picks_with_quotes)
    assert len(kept) == 1
    assert len(dropped) == 3
    # All kept picks have ok=True via _revalidation; all dropped have ok=False
    assert kept[0]["_revalidation"]["ok"] is True
    assert all(p["_revalidation"]["ok"] is False for p in dropped)
    # Verdict shapes
    drop_verdicts = sorted(p["_revalidation"]["verdict"] for p in dropped)
    assert drop_verdicts == ["PLAYED_OUT_SL", "PLAYED_OUT_TP", "R_R_DEGRADED"]


def test_rr_signal_computed_correctly_for_long():
    """rr_signal should equal (tp-entry)/(entry-sl) for LONG."""
    pick = {"direction": "LONG", "entry_price": 100, "take_profit": 110, "stop_loss": 95}
    r = revalidate_pick(pick, live_price=100)
    # rr_signal = 10 / 5 = 2.0
    assert abs(r["rr_signal"] - 2.0) < 1e-6


def test_rr_signal_computed_correctly_for_short():
    """rr_signal should equal (entry-tp)/(sl-entry) for SHORT."""
    pick = {"direction": "SHORT", "entry_price": 100, "take_profit": 90, "stop_loss": 105}
    r = revalidate_pick(pick, live_price=100)
    # rr_signal = 10 / 5 = 2.0
    assert abs(r["rr_signal"] - 2.0) < 1e-6


def test_custom_rr_cutoff_is_respected():
    """Lowering the cutoff should drop more picks."""
    pick = {"direction": "LONG", "entry_price": 100, "take_profit": 105, "stop_loss": 99}
    # Live at 99.5 → tp_distance=5.5, sl_distance=0.5, rr_live=11
    r_default = revalidate_pick(pick, live_price=99.5)
    assert r_default["verdict"] == "R_R_DEGRADED"
    # With cutoff 100.0, the same pick passes
    r_relaxed = revalidate_pick(pick, live_price=99.5, rr_antipred_cutoff=100.0)
    assert r_relaxed["verdict"] == "OK"


def test_default_cutoff_value():
    assert DEFAULT_RR_ANTIPRED_CUTOFF == 3.0
