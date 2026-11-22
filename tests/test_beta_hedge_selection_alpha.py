"""Deterministic tests for tools/beta_hedge_selection_alpha.py (no DB)."""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.beta_hedge_selection_alpha import (  # noqa: E402
    MIN_BETA_BARS,
    beta,
    bootstrap_ci,
    hedged_alpha,
    returns,
    window_return,
)

DATES = [f"2026-01-{d:02d}" for d in range(1, 29)]
# Entry must leave >= MIN_BETA_BARS returns of pre-entry history behind it,
# otherwise every pick is (correctly) skipped for "no_beta".
ENTRY = DATES[20]
EXIT = DATES[26]


def _market(beta_scaled: bool = False) -> list[tuple[str, float]]:
    """Alternating up/down market so beta is well-defined and non-zero."""
    px, out = 100.0, []
    for i, d in enumerate(DATES):
        px *= 1.01 if i % 2 == 0 else 0.995
        out.append((d, px))
    return out


def _symbol(mult: float, bars=None) -> list[tuple[str, float]]:
    """A symbol whose returns are `mult` times the market's."""
    base = bars or _market()
    px, out = 100.0, [base[0]]
    for i in range(1, len(base)):
        m = base[i][1] / base[i - 1][1] - 1.0
        px *= 1.0 + mult * m
        out.append((base[i][0], px))
    return out


def test_returns_are_relative_and_skip_zero_base():
    got = returns([100.0, 110.0, 99.0])
    assert len(got) == 2
    assert abs(got[0] - 0.1) < 1e-12 and abs(got[1] + 0.1) < 1e-12
    assert returns([0.0, 10.0]) == []


def test_beta_recovers_the_true_multiplier():
    mkt = returns([c for _, c in _market()])
    for mult in (0.5, 1.0, 2.0):
        sym = returns([c for _, c in _symbol(mult)])
        b = beta(sym, mkt)
        assert b is not None
        assert abs(b - mult) < 0.05, (mult, b)


def test_beta_is_none_below_the_minimum_sample():
    mkt = returns([c for _, c in _market()])
    short = mkt[: MIN_BETA_BARS - 1]
    assert beta(short, mkt[: len(short)]) is None


def test_beta_is_none_when_market_has_no_variance():
    flat = [0.0] * 30
    sym = [0.01] * 30
    assert beta(sym, flat) is None


def test_window_return_uses_bars_at_or_before_each_end():
    bars = [("2026-01-01", 100.0), ("2026-01-05", 110.0), ("2026-01-09", 121.0)]
    r = window_return(bars, "2026-01-05", "2026-01-09")
    assert abs(r - 0.1) < 1e-9
    # an end date with no exact bar falls back to the last bar before it
    assert abs(window_return(bars, "2026-01-01", "2026-01-07") - 0.1) < 1e-9


def test_window_return_is_none_when_window_is_outside_the_data():
    bars = [("2026-01-01", 100.0)]
    assert window_return(bars, "2025-12-01", "2025-12-15") is None


def test_pure_beta_pick_is_hedged_to_about_zero():
    """A pick that is exactly the market move must not look like alpha."""
    mkt = _market()
    picks = [{
        "asset_class": "EQUITY", "symbol": "AAA", "direction": "LONG",
        "entry_time": ENTRY, "closed_at": EXIT, "pnl_pct": 0.0,
    }]
    # pnl is 0 but the symbol moved with the market: hedging should subtract it
    res = hedged_alpha(picks, lambda s: _symbol(1.0), mkt)
    assert res["available"] is True
    eq = res["classes"]["EQUITY"]
    mret = window_return(mkt, ENTRY, EXIT)
    assert abs(eq["hedged_alpha_pct"] - (-1.0 * mret * 100.0)) < 0.5
    assert abs(eq["mean_beta"] - 1.0) < 0.1


def test_short_direction_hedges_with_the_opposite_sign():
    mkt = _market()
    mk = lambda d: [{  # noqa: E731
        "asset_class": "EQUITY", "symbol": "AAA", "direction": d,
        "entry_time": ENTRY, "closed_at": EXIT, "pnl_pct": 0.0}]
    long_r = hedged_alpha(mk("LONG"), lambda s: _symbol(1.0), mkt)["classes"]["EQUITY"]
    short_r = hedged_alpha(mk("SHORT"), lambda s: _symbol(1.0), mkt)["classes"]["EQUITY"]
    assert abs(long_r["hedged_alpha_pct"] + short_r["hedged_alpha_pct"]) < 1e-6


def test_beta_is_point_in_time_not_full_sample():
    """Beta must come from pre-entry bars: post-entry data cannot change it."""
    mkt = _market()
    early = ENTRY
    # append a violent post-entry swing to the symbol only
    sym = _symbol(1.0)
    noisy = sym + [("2026-02-01", sym[-1][1] * 5)]
    picks = lambda: [{  # noqa: E731
        "asset_class": "EQUITY", "symbol": "AAA", "direction": "LONG",
        "entry_time": early, "closed_at": EXIT, "pnl_pct": 1.0}]
    a = hedged_alpha(picks(), lambda s: sym, mkt)["classes"]["EQUITY"]
    b = hedged_alpha(picks(), lambda s: noisy, mkt)["classes"]["EQUITY"]
    assert abs(a["mean_beta"] - b["mean_beta"]) < 1e-9


def test_rows_without_bars_are_skipped_and_counted():
    mkt = _market()
    picks = [{"asset_class": "EQUITY", "symbol": "MISSING", "direction": "LONG",
              "entry_time": DATES[5], "closed_at": DATES[9], "pnl_pct": 1.0}]
    res = hedged_alpha(picks, lambda s: [], mkt)
    assert res["available"] is False
    assert res["skipped"]["no_bars"] == 1
    assert "reason" in res


def test_thin_class_is_inconclusive_not_a_verdict():
    mkt = _market()
    picks = [{"asset_class": "BOND", "symbol": "AAA", "direction": "LONG",
              "entry_time": ENTRY, "closed_at": EXIT, "pnl_pct": 0.5}]
    rec = hedged_alpha(picks, lambda s: _symbol(1.0), mkt)["classes"]["BOND"]
    assert rec["verdict"].startswith("inconclusive")
    assert "need" in rec["verdict"]


def test_factor_default_is_used_when_symbol_bars_are_absent():
    mkt = _market()
    picks = [{"asset_class": "ETF", "symbol": "XYZ", "sector": "XLK",
              "direction": "LONG", "entry_time": ENTRY,
              "closed_at": EXIT, "pnl_pct": 0.0}]
    res = hedged_alpha(picks, lambda s: _symbol(1.0) if s == "XLK" else [],
                       mkt, factor_default=lambda p: p["sector"])
    assert res["available"] is True
    assert res["classes"]["ETF"]["n"] == 1


def test_bootstrap_ci_is_seeded_and_deterministic():
    vals = [0.1, -0.2, 0.3, 0.05, -0.1, 0.2, 0.0, 0.15]
    assert bootstrap_ci(vals) == bootstrap_ci(vals)
    lo, hi = bootstrap_ci(vals)
    assert lo <= sum(vals) / len(vals) <= hi


def test_bootstrap_ci_is_none_for_tiny_samples():
    assert bootstrap_ci([1.0, 2.0]) is None
