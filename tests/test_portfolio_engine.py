"""Unit tests for the Phase 2 portfolio engine (pure functions).

Covers sizing clamps, trend filter, TP/SL sign correctness, risk-cap breaches,
drawdown breaker, exit conditions, and full evaluate_entry happy/reject paths.
Uses the REAL risk profiles via load_profiles() so the design constants in
config/portfolio_risk_profiles.json are pinned.
"""
import math

import pytest

from tools.portfolios.profiles import load_profiles
from tools.portfolios import sizing, risk, engine

PROFILES = load_profiles()
CONS = PROFILES["conservative"]
BAL = PROFILES["balanced"]
AGG = PROFILES["aggressive"]


# --------------------------------------------------------------------------- #
# sizing.realized_vol
# --------------------------------------------------------------------------- #
def test_realized_vol_insufficient_data_returns_none():
    assert sizing.realized_vol([100.0, 101.0], window=20) is None
    assert sizing.realized_vol([], window=5) is None


def test_realized_vol_flat_series_is_zero():
    prices = [100.0] * 25
    vol = sizing.realized_vol(prices, window=20)
    assert vol == 0.0


def test_realized_vol_positive_for_moving_series():
    prices = [100.0 * (1.01 ** i) if i % 2 == 0 else 100.0 * (1.01 ** i) * 0.99
              for i in range(30)]
    vol = sizing.realized_vol(prices, window=20)
    assert vol is not None and vol > 0


def test_realized_vol_nonpositive_price_returns_none():
    prices = [100.0] * 19 + [0.0, 101.0]
    assert sizing.realized_vol(prices, window=20) is None


# --------------------------------------------------------------------------- #
# sizing.vol_scalar
# --------------------------------------------------------------------------- #
def test_vol_scalar_none_or_zero_returns_neutral():
    assert sizing.vol_scalar(0.15, None) == 1.0
    assert sizing.vol_scalar(0.15, 0) == 1.0


def test_vol_scalar_clamped_high():
    # tiny realized vol -> huge ratio -> clamp to 3.0
    assert sizing.vol_scalar(0.28, 0.001) == 3.0


def test_vol_scalar_clamped_low():
    # huge realized vol -> tiny ratio -> clamp to 0.1
    assert sizing.vol_scalar(0.08, 100.0) == 0.1


def test_vol_scalar_midrange():
    s = sizing.vol_scalar(0.15, 0.30)  # 0.5
    assert math.isclose(s, 0.5)


# --------------------------------------------------------------------------- #
# sizing.target_weight
# --------------------------------------------------------------------------- #
def test_target_weight_clamped_to_max_position():
    # kelly 1.0 * edge 1.0 * vol_scalar 3.0 = 3.0 -> clamp to 15% = 0.15
    w = sizing.target_weight(edge_signal=1.0, kelly_fraction=1.0, vol_scalar=3.0,
                             max_single_position_pct=AGG["max_single_position_pct"])
    assert math.isclose(w, 0.15)


def test_target_weight_edge_clamped_to_unit():
    w = sizing.target_weight(edge_signal=5.0, kelly_fraction=0.25, vol_scalar=1.0,
                             max_single_position_pct=4.0)
    # edge clamps to 1.0 -> 0.25 -> but max 0.04 -> 0.04
    assert math.isclose(w, 0.04)


def test_target_weight_proportional_below_cap():
    # 0.5*0.1*1.0 = 0.05, below the 0.08 cap -> proportional, not clamped.
    w = sizing.target_weight(edge_signal=0.1, kelly_fraction=0.5, vol_scalar=1.0,
                             max_single_position_pct=8.0)
    assert math.isclose(w, 0.05)


def test_target_weight_exact_value():
    w = sizing.target_weight(edge_signal=0.1, kelly_fraction=0.5, vol_scalar=1.0,
                             max_single_position_pct=8.0)
    assert math.isclose(w, 0.05)  # 0.5*0.1*1.0 = 0.05, below 0.08 cap


def test_target_weight_never_negative():
    w = sizing.target_weight(edge_signal=-1.0, kelly_fraction=0.5, vol_scalar=1.0,
                             max_single_position_pct=8.0)
    assert w == 0.0


# --------------------------------------------------------------------------- #
# sizing.position_qty
# --------------------------------------------------------------------------- #
def test_position_qty_basic():
    qty = sizing.position_qty(0.04, 100000.0, 50.0)
    assert math.isclose(qty, 80.0)  # 4000 / 50


def test_position_qty_nonpositive_price_zero():
    assert sizing.position_qty(0.04, 100000.0, 0.0) == 0.0
    assert sizing.position_qty(0.04, 100000.0, -5.0) == 0.0


# --------------------------------------------------------------------------- #
# risk.passes_trend_filter
# --------------------------------------------------------------------------- #
def test_trend_filter_no_filter_when_ma_days_none():
    assert risk.passes_trend_filter("long", 10.0, None, None) is True


def test_trend_filter_missing_ma_value_rejects():
    assert risk.passes_trend_filter("long", 10.0, None, 200) is False


def test_trend_filter_long():
    assert risk.passes_trend_filter("long", 105.0, 100.0, 200) is True
    assert risk.passes_trend_filter("long", 95.0, 100.0, 200) is False


def test_trend_filter_short():
    assert risk.passes_trend_filter("short", 95.0, 100.0, 50) is True
    assert risk.passes_trend_filter("short", 105.0, 100.0, 50) is False


# --------------------------------------------------------------------------- #
# risk.compute_tp_sl
# --------------------------------------------------------------------------- #
def test_tp_sl_long_pct_floor():
    tp, sl = risk.compute_tp_sl("long", 100.0, CONS)
    # SL pct_floor -6.5% -> 93.5 ; TP pct +8% -> 108
    assert math.isclose(sl, 93.5)
    assert math.isclose(tp, 108.0)


def test_tp_sl_short_pct_floor():
    tp, sl = risk.compute_tp_sl("short", 100.0, CONS)
    # short SL above entry; TP below entry
    assert math.isclose(sl, 106.5)
    assert math.isclose(tp, 92.0)


def test_tp_sl_atr_based_sl_and_pct_tp():
    # BAL: atr_mult 2.0 * 4 = 8 distance -> SL 92. TP pct (15%) -> 115.
    tp, sl = risk.compute_tp_sl("long", 100.0, BAL, atr=4.0)
    assert math.isclose(sl, 92.0)
    assert math.isclose(tp, 115.0)


def test_tp_sl_r_multiple_when_no_pct():
    # Synthetic appetite with no pct -> TP from r_multiple * SL distance.
    appetite = {"stop_loss": {"atr_mult": 2.0, "pct_floor": -10.0},
                "take_profit": {"pct": None, "r_multiple": 3.0}}
    tp, sl = risk.compute_tp_sl("long", 100.0, appetite, atr=4.0)
    assert math.isclose(sl, 92.0)   # 2.0*4 = 8 -> 92
    assert math.isclose(tp, 124.0)  # 3 * 8 = 24 -> 124


def test_tp_sl_aggressive_trail_no_tp():
    tp, sl = risk.compute_tp_sl("long", 100.0, AGG)
    # take_profit pct null, r_multiple "trail" -> tp None ; SL pct_floor -15%
    assert tp is None
    assert math.isclose(sl, 85.0)


def test_tp_sl_aggressive_short_trail():
    tp, sl = risk.compute_tp_sl("short", 100.0, AGG)
    assert tp is None
    assert math.isclose(sl, 115.0)


# --------------------------------------------------------------------------- #
# risk.would_breach
# --------------------------------------------------------------------------- #
def test_would_breach_max_open_positions():
    opens = [{"asset_class": "EQUITY", "weight_at_entry": 0.01}
             for _ in range(CONS["max_open_positions"])]
    cand = {"asset_class": "EQUITY", "weight_at_entry": 0.01}
    ok, reason = risk.would_breach(opens, cand, CONS, 100000.0)
    assert ok is False and reason == "max_open_positions"


def test_would_breach_single_position():
    cand = {"asset_class": "EQUITY", "weight_at_entry": 0.05}  # 5% > 4%
    ok, reason = risk.would_breach([], cand, CONS, 100000.0)
    assert ok is False and reason == "max_single_position_pct"


def test_would_breach_class_exposure():
    # BAL: single cap 8%, class cap 40%. Build EQUITY exposure to 36%, then a
    # 6% candidate (under single cap) pushes class to 42% > 40%.
    opens = [{"asset_class": "EQUITY", "weight_at_entry": 0.06} for _ in range(6)]  # 36%
    cand = {"asset_class": "EQUITY", "weight_at_entry": 0.06}  # +6% -> 42% > 40%
    ok, reason = risk.would_breach(opens, cand, BAL, 100000.0)
    assert ok is False and reason == "max_class_exposure_pct"


def test_would_breach_gross_cap_explicit():
    # BAL: single 8%, class 40%, gross 110%, max_open 20.
    # Build 14 positions at 8% across 4 classes -> 112%? keep each class <=40%.
    # Use 5 classes x ~3 positions to stay under class cap, gross ~104%.
    classes = ["EQUITY", "ETF", "BOND", "FOREX", "COMMODITY"]
    opens = []
    for cls in classes:
        for _ in range(3):  # 3 * 8% = 24% per class (< 40 cap)
            opens.append({"asset_class": cls, "weight_at_entry": 0.07})  # 15*7% = 105%
    cand = {"asset_class": "EQUITY", "weight_at_entry": 0.07}  # +7% -> 112% > 110%
    # candidate 7% < 8% single cap; EQUITY class becomes 28% < 40%; 16 positions < 20.
    ok, reason = risk.would_breach(opens, cand, BAL, 100000.0)
    assert ok is False and reason == "gross_exposure_cap_pct"


def test_would_breach_ok():
    cand = {"asset_class": "EQUITY", "weight_at_entry": 0.03}
    ok, reason = risk.would_breach([], cand, CONS, 100000.0)
    assert ok is True and reason == ""


# --------------------------------------------------------------------------- #
# risk.drawdown_breaker_tripped
# --------------------------------------------------------------------------- #
def test_drawdown_breaker():
    assert risk.drawdown_breaker_tripped(-9.0, CONS) is True   # -9 <= -8
    assert risk.drawdown_breaker_tripped(-5.0, CONS) is False
    assert risk.drawdown_breaker_tripped(None, CONS) is False


# --------------------------------------------------------------------------- #
# risk.check_exit
# --------------------------------------------------------------------------- #
def test_check_exit_tp_long():
    pos = {"direction": "long", "entry_price": 100.0, "tp_price": 108.0, "sl_price": 95.0}
    assert risk.check_exit(pos, 109.0) == (True, "tp")


def test_check_exit_sl_long():
    pos = {"direction": "long", "entry_price": 100.0, "tp_price": 108.0, "sl_price": 95.0}
    assert risk.check_exit(pos, 94.0) == (True, "sl")


def test_check_exit_sl_short():
    pos = {"direction": "short", "entry_price": 100.0, "tp_price": 92.0, "sl_price": 105.0}
    assert risk.check_exit(pos, 106.0) == (True, "sl")


def test_check_exit_trend_flip_long():
    pos = {"direction": "long", "entry_price": 100.0, "tp_price": 200.0, "sl_price": 50.0}
    assert risk.check_exit(pos, 99.0, ma_value=100.0) == (True, "trend_flip")


def test_check_exit_time_stop():
    pos = {"direction": "long", "entry_price": 100.0, "tp_price": 200.0,
           "sl_price": 50.0, "entry_date": "2026-05-01", "max_hold_days": 10}
    assert risk.check_exit(pos, 101.0, asof_date="2026-05-15") == (True, "time_stop")


def test_check_exit_hold():
    pos = {"direction": "long", "entry_price": 100.0, "tp_price": 108.0, "sl_price": 95.0}
    assert risk.check_exit(pos, 101.0) == (False, "")


# --------------------------------------------------------------------------- #
# engine.mark_position
# --------------------------------------------------------------------------- #
def test_mark_position_long():
    pos = {"direction": "long", "entry_price": 100.0, "qty": 10.0}
    m = engine.mark_position(pos, 110.0)
    assert math.isclose(m["unrealized_pnl_pct"], 10.0)
    assert math.isclose(m["unrealized_pnl_usd"], 100.0)


def test_mark_position_short_profit_on_drop():
    pos = {"direction": "short", "entry_price": 100.0, "qty": 10.0}
    m = engine.mark_position(pos, 90.0)
    assert math.isclose(m["unrealized_pnl_pct"], 10.0)
    assert math.isclose(m["unrealized_pnl_usd"], 100.0)


# --------------------------------------------------------------------------- #
# engine.evaluate_entry — happy path + rejects
# --------------------------------------------------------------------------- #
def _state(open_positions=None, nav=100000.0, mtd=0.0):
    return {"nav_usd": nav, "cash_usd": nav, "mtd_return_pct": mtd,
            "open_positions": open_positions or []}


def test_evaluate_entry_happy_path_open():
    pick = {"model": "m1", "symbol": "AAPL", "direction": "long",
            "asset_class": "EQUITY", "edge_signal": 0.5, "thesis": "uptrend"}
    market = {"price": 100.0, "ma_value": 90.0, "realized_vol": 0.30, "atr": None}
    out = engine.evaluate_entry(pick, _state(), CONS, market)
    assert out["action"] == "open"
    assert out["weight"] > 0 and out["qty"] > 0
    assert math.isclose(out["sl_price"], 93.5)   # -6.5%
    assert math.isclose(out["tp_price"], 108.0)  # +8%
    assert out["position"]["symbol"] == "AAPL"


def test_evaluate_entry_aggressive_crypto_open_trail():
    pick = {"model": "m2", "symbol": "BTC", "direction": "long",
            "asset_class": "CRYPTO", "edge_signal": 0.8}
    market = {"price": 50000.0, "ma_value": None, "realized_vol": 0.60, "atr": None}
    out = engine.evaluate_entry(pick, _state(), AGG, market)
    assert out["action"] == "open"
    assert out["tp_price"] is None  # trail-only
    assert math.isclose(out["sl_price"], 50000.0 * 0.85)


def test_evaluate_entry_reject_class_not_allowed():
    pick = {"model": "m1", "symbol": "BTC", "direction": "long",
            "asset_class": "CRYPTO", "edge_signal": 0.5}
    market = {"price": 100.0, "ma_value": 90.0, "realized_vol": 0.3}
    out = engine.evaluate_entry(pick, _state(), CONS, market)
    assert out["action"] == "reject" and out["reason"] == "class_not_allowed"


def test_evaluate_entry_reject_already_held():
    held = [{"symbol": "AAPL", "asset_class": "EQUITY", "weight_at_entry": 0.02}]
    pick = {"model": "m1", "symbol": "AAPL", "direction": "long",
            "asset_class": "EQUITY", "edge_signal": 0.5}
    market = {"price": 100.0, "ma_value": 90.0, "realized_vol": 0.3}
    out = engine.evaluate_entry(pick, _state(held), CONS, market)
    assert out["action"] == "reject" and out["reason"] == "already_held"


def test_evaluate_entry_reject_no_edge():
    pick = {"model": "m1", "symbol": "AAPL", "direction": "long",
            "asset_class": "EQUITY", "edge_signal": 0.0}
    market = {"price": 100.0, "ma_value": 90.0, "realized_vol": 0.3}
    out = engine.evaluate_entry(pick, _state(), CONS, market)
    assert out["action"] == "reject" and out["reason"] == "no_edge"


def test_evaluate_entry_reject_trend_filter():
    pick = {"model": "m1", "symbol": "AAPL", "direction": "long",
            "asset_class": "EQUITY", "edge_signal": 0.5}
    market = {"price": 80.0, "ma_value": 100.0, "realized_vol": 0.3}  # below MA
    out = engine.evaluate_entry(pick, _state(), CONS, market)
    assert out["action"] == "reject" and out["reason"] == "trend_filter"


def test_evaluate_entry_reject_drawdown_breaker():
    pick = {"model": "m1", "symbol": "AAPL", "direction": "long",
            "asset_class": "EQUITY", "edge_signal": 0.5}
    market = {"price": 100.0, "ma_value": 90.0, "realized_vol": 0.3}
    out = engine.evaluate_entry(pick, _state(mtd=-10.0), CONS, market)
    assert out["action"] == "reject" and out["reason"] == "drawdown_breaker"


def test_evaluate_entry_reject_breach_max_open():
    opens = [{"symbol": f"S{i}", "asset_class": "EQUITY", "weight_at_entry": 0.01}
             for i in range(CONS["max_open_positions"])]
    pick = {"model": "m1", "symbol": "NEW", "direction": "long",
            "asset_class": "EQUITY", "edge_signal": 0.5}
    market = {"price": 100.0, "ma_value": 90.0, "realized_vol": 0.3}
    out = engine.evaluate_entry(pick, _state(opens), CONS, market)
    assert out["action"] == "reject" and out["reason"] == "max_open_positions"


# --------------------------------------------------------------------------- #
# engine.evaluate_exit
# --------------------------------------------------------------------------- #
def test_evaluate_exit_tp_realizes_pnl():
    pos = {"direction": "long", "entry_price": 100.0, "qty": 10.0,
           "tp_price": 108.0, "sl_price": 95.0}
    out = engine.evaluate_exit(pos, {"price": 109.0})
    assert out["action"] == "exit" and out["reason"] == "tp"
    assert math.isclose(out["exit_price"], 109.0)
    assert math.isclose(out["realized_pnl_pct"], 9.0)
    assert math.isclose(out["realized_pnl_usd"], 90.0)


def test_evaluate_exit_hold():
    pos = {"direction": "long", "entry_price": 100.0, "qty": 10.0,
           "tp_price": 108.0, "sl_price": 95.0}
    out = engine.evaluate_exit(pos, {"price": 101.0})
    assert out["action"] == "hold"
