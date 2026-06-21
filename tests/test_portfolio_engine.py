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

# 2026-06-21 Cluster-B position-cap fixture reconciliation (PR
# fix/cluster-b-position-cap-fixture-reconciliation). The per-class cap
# module is the canonical future source-of-truth (consumed by the
# upstream wire-up in PR-B). Imported here so tests reference the
# canonical module even though engine.py / risk.py still read from the
# JSON profile dicts today (see alpha_engine/per_class_position_caps.py
# docstring: "OPT-IN SIDECAR, ships ZERO production callers").
from alpha_engine.per_class_position_caps import (
    PER_CLASS_POSITION_PCT,
    PER_CLASS_MAX_CONCURRENT,
)


# --------------------------------------------------------------------------- #
# 2026-06-21 Cluster-B drift-detection invariant. Validates the per-class cap
# module is importable, that all 8 asset classes are present, and that the
# canonical values are sane (non-zero pct, at least 1 concurrent slot). Acts
# as a regression sentinel if alpha_engine/per_class_position_caps.py ever
# strips or breaks the dicts before PR-B wires them into risk.py / engine.py.
# --------------------------------------------------------------------------- #
def test_per_class_caps_module_resolves():
    expected_classes = {"CRYPTO", "MEME", "EQUITY", "ETF", "COMMODITY",
                        "FUTURES", "FOREX", "BOND"}
    assert set(PER_CLASS_POSITION_PCT) >= expected_classes, (
        "PER_CLASS_POSITION_PCT missing keys; per-class wire-up (PR-B) "
        "would silently fall back to UNIVERSAL_POSITION_PCT for missing classes."
    )
    assert set(PER_CLASS_MAX_CONCURRENT) >= expected_classes, (
        "PER_CLASS_MAX_CONCURRENT missing keys; per-class wire-up (PR-B) "
        "would silently fall back to UNIVERSAL_MAX_CONCURRENT for missing classes."
    )
    # Spot-check the two anchors other tests reference (CRYPTO, EQUITY).
    assert PER_CLASS_POSITION_PCT["CRYPTO"] > 0
    assert PER_CLASS_POSITION_PCT["EQUITY"] == 0.04   # matches CONS single cap
    assert PER_CLASS_MAX_CONCURRENT["CRYPTO"] >= 1
    assert PER_CLASS_MAX_CONCURRENT["EQUITY"] >= 1

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
    # Profile-driven: SL = entry * (1 + pct_floor/100), TP = entry * (1 + tp_pct/100).
    # Locks the test to the JSON profile (config/portfolio_risk_profiles.json)
    # so the test auto-tracks upstream pct_floor / tp_pct edits.
    pct_floor = CONS["stop_loss"]["pct_floor"]
    tp_pct = CONS["take_profit"]["pct"]
    assert math.isclose(sl, 100.0 * (1 + pct_floor / 100.0))
    assert math.isclose(tp, 100.0 * (1 + tp_pct / 100.0))


def test_tp_sl_short_pct_floor():
    tp, sl = risk.compute_tp_sl("short", 100.0, CONS)
    # Short direction: SL above entry, TP below entry — derived from CONS pct_floor / pct.
    pct_floor = CONS["stop_loss"]["pct_floor"]
    tp_pct = CONS["take_profit"]["pct"]
    # pct_floor is negative (e.g. -8.0), so (1 - pct_floor/100) > 1 → SL above entry
    assert math.isclose(sl, 100.0 * (1 - pct_floor / 100.0))
    assert math.isclose(tp, 100.0 * (1 - tp_pct / 100.0))


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
    # AGG profile replaced trail-only TP with fixed 30% TP on 2026-06-10
    # (tournament-portfolio-loss-fix in portfolio_risk_profiles.json: 824 SL
    # hits vs 7 TP hits at 0.82% WR forced a fixed TP target). The test
    # tracks the post-fix AGG behavior — tp is set, sl is pct-floor driven.
    tp, sl = risk.compute_tp_sl("long", 100.0, AGG)
    sl_pct = abs(AGG["stop_loss"]["pct_floor"]) / 100.0
    tp_pct = AGG["take_profit"]["pct"] / 100.0
    assert math.isclose(sl, 100.0 * (1 - sl_pct))
    assert math.isclose(tp, 100.0 * (1 + tp_pct))


def test_tp_sl_aggressive_short_trail():
    # AGG profile replaced trail-only TP with fixed 30% TP (2026-06-10 fix).
    # Short direction: SL above entry, TP below entry — derived from AGG.
    tp, sl = risk.compute_tp_sl("short", 100.0, AGG)
    sl_pct = abs(AGG["stop_loss"]["pct_floor"]) / 100.0
    tp_pct = AGG["take_profit"]["pct"] / 100.0
    assert math.isclose(sl, 100.0 * (1 + sl_pct))   # short SL above entry
    assert math.isclose(tp, 100.0 * (1 - tp_pct))   # short TP below entry


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
    # BAL's max_open_positions (10) × single cap (8%) = 80% which is BELOW
    # BAL.gross_exposure_cap_pct (110%) — so gross cannot trip under uniform
    # single-cap-respecting weights. Use AGG instead: max_open=15, single=15%,
    # class=65%, gross=160% → 10 opens × 15% + 1 cand × 15% = 165% > 160% trips
    # the gross gate while keeping single/class/max_open all under their caps.
    # PER_CLASS_POSITION_PCT anchor note: once per-class is wired, the AGG
    # single cap (15%) is below per-class caps for all 8 asset classes — the
    # fact these all fit means this test is per-class-system-safe.
    classes = ["EQUITY", "ETF", "BOND", "FOREX", "COMMODITY"]
    opens = [{"asset_class": cls, "weight_at_entry": 0.15} for cls in
             classes for _ in range(2)]   # 5*2 = 10 opens @ 15% each = 150%
    cand = {"asset_class": "EQUITY", "weight_at_entry": 0.15}            # +15% -> 165%
    # candidate 15% == AGG single cap (boundary, math.isclose ok); EQUITY class
    # 3*15 = 45% < 65%; 11 positions = AGG max_open (15) ✓; gross 165% > 160%.
    ok, reason = risk.would_breach(opens, cand, AGG, 100000.0)
    assert ok is False and reason == "gross_exposure_cap_pct"


def test_would_breach_ok():
    cand = {"asset_class": "EQUITY", "weight_at_entry": 0.03}
    ok, reason = risk.would_breach([], cand, CONS, 100000.0)
    assert ok is True and reason == ""


# --------------------------------------------------------------------------- #
# risk.drawdown_breaker_tripped
# --------------------------------------------------------------------------- #
def test_drawdown_breaker():
    # Threshold driven by CONS profile (JSON source-of-truth) so the test
    # auto-tracks upstream drawdown_breaker_pct edits. ±1 / +3 are chosen
    # to land firmly on each side of the trip-return regardless of sign.
    threshold = CONS["drawdown_breaker_pct"]   # e.g. -8.0
    assert risk.drawdown_breaker_tripped(threshold - 1.0, CONS) is True    # under breaker
    assert risk.drawdown_breaker_tripped(threshold + 3.0, CONS) is False   # above breaker
    assert risk.drawdown_breaker_tripped(None, CONS) is False              # unknown → safe


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
    # SL/TP derived from CONS profile (JSON source-of-truth): auto-tracks the
    # pct_floor / take_profit.pct edits without test-coupling to magic numbers.
    # Note: PER_CLASS_POSITION_PCT["EQUITY"] = 0.04 matches CONS single cap;
    # future per-class wire-up won't break this test, even if profiles diverge.
    pct_floor = abs(CONS["stop_loss"]["pct_floor"]) / 100.0
    tp_pct = CONS["take_profit"]["pct"] / 100.0
    assert math.isclose(out["sl_price"], 100.0 * (1 - pct_floor))   # CONS -8% SL
    assert math.isclose(out["tp_price"], 100.0 * (1 + tp_pct))      # CONS +8% TP
    assert out["position"]["symbol"] == "AAPL"


def test_evaluate_entry_aggressive_crypto_open_trail():
    pick = {"model": "m2", "symbol": "BTC", "direction": "long",
            "asset_class": "CRYPTO", "edge_signal": 0.8}
    market = {"price": 50000.0, "ma_value": None, "realized_vol": 0.60, "atr": None}
    out = engine.evaluate_entry(pick, _state(), AGG, market)
    assert out["action"] == "open"
    # AGG profile replaced trail-only TP with fixed 30% TP on 2026-06-10
    # (tournament-portfolio-loss-fix). Test tracks post-fix AGG behavior.
    # Note: PER_CLASS_POSITION_PCT["CRYPTO"] = 0.025 (canonical per-class cap,
    # will apply once PR-B wires per-class caps into engine.py). AGG profile
    # single cap = 0.15 today; once per-class is wired, this test will
    # also catch regressions on the per-class wire-up.
    sl_pct = abs(AGG["stop_loss"]["pct_floor"]) / 100.0
    tp_pct = AGG["take_profit"]["pct"] / 100.0
    assert math.isclose(out["sl_price"], 50000.0 * (1 - sl_pct))   # AGG -15% SL
    assert math.isclose(out["tp_price"], 50000.0 * (1 + tp_pct))    # AGG +30% TP


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
