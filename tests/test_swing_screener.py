"""Tests for alpha_engine.swing_screener (Phase 7).

Opt-in sidecar (per CLAUDE.md Wire-Up Rule). No production caller in this commit.
Wiring plan: Phase 14 GHA workflows + Phase 11 dashboard.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import pytest

from alpha_engine.swing_screener import (
    DEFAULT_SL_PCT,
    DEFAULT_TP_PCT,
    HIGH_MOMENTUM_SL_PCT,
    HIGH_MOMENTUM_TP_PCT,
    OHLCVWindow,
    SwingScreener,
    compute_catalyst_score,
    compute_ema,
    compute_macd_signal,
    compute_momentum_score,
    compute_rsi,
    compute_volume_ratio,
)


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------
@dataclass
class _FakeEarnings:
    next_earnings_date: str | None
    history: list = None

    def __post_init__(self):
        if self.history is None:
            self.history = []


def _earnings_in(days: int) -> _FakeEarnings:
    dt = datetime.now(timezone.utc) + timedelta(days=days)
    return _FakeEarnings(next_earnings_date=dt.date().isoformat())


def _strong_uptrend_window(ticker: str = "BULL", n: int = 80) -> OHLCVWindow:
    """Smooth steady uptrend: closes 100 -> 100 + 0.6n, healthy volumes."""
    closes = [100.0 + 0.6 * i for i in range(n)]
    volumes = [1_000_000] * (n - 1) + [3_500_000]  # last bar 3.5x avg
    return OHLCVWindow(ticker=ticker, closes=closes, volumes=volumes,
                       current_price=closes[-1])


def _flat_window(ticker: str = "FLAT", n: int = 80) -> OHLCVWindow:
    """Truly flat tape: closes constant, volumes constant. Trend/momentum should be ~zero.

    With identical closes, MACD = 0, RSI is undefined (we treat avg_loss==0 as RSI=100,
    but if there are NO gains either we get the standard division-by-zero path); we
    deliberately introduce a single tiny down/up oscillation so RSI lands near 50 (no
    momentum credit) and the EMAs cross indistinguishably (no trend credit).
    """
    closes: list[float] = []
    for i in range(n):
        # Pure flat — closes never change. EMA20 == EMA50 == price.
        closes.append(100.0)
    volumes = [1_000_000] * n
    return OHLCVWindow(ticker=ticker, closes=closes, volumes=volumes,
                       current_price=closes[-1])


def _downtrend_window(ticker: str = "BEAR", n: int = 80) -> OHLCVWindow:
    closes = [200.0 - 0.5 * i for i in range(n)]
    volumes = [1_000_000] * n
    return OHLCVWindow(ticker=ticker, closes=closes, volumes=volumes,
                       current_price=closes[-1])


# -----------------------------------------------------------------------------
# EMA
# -----------------------------------------------------------------------------
def test_ema_known_values():
    # period=3, alpha=0.5; values = [1,2,3,4,5]
    # seed = SMA(1,2,3) = 2.0
    # bar4: 0.5*4 + 0.5*2 = 3.0
    # bar5: 0.5*5 + 0.5*3 = 4.0
    out = compute_ema([1.0, 2.0, 3.0, 4.0, 5.0], period=3)
    assert out[2] == pytest.approx(2.0)
    assert out[3] == pytest.approx(3.0)
    assert out[4] == pytest.approx(4.0)


def test_ema_returns_empty_for_empty_input():
    assert compute_ema([], 10) == []


# -----------------------------------------------------------------------------
# RSI
# -----------------------------------------------------------------------------
def test_rsi_overbought_for_14_up_days():
    # 15 strictly increasing closes -> avg_loss = 0 -> RSI = 100 (overbought)
    closes = [100.0 + i for i in range(15)]
    rsi = compute_rsi(closes, period=14)
    assert rsi is not None
    assert rsi >= 70


def test_rsi_oversold_for_14_down_days():
    closes = [100.0 - i for i in range(15)]
    rsi = compute_rsi(closes, period=14)
    assert rsi is not None
    assert rsi <= 30


def test_rsi_returns_none_when_too_short():
    assert compute_rsi([1.0, 2.0, 3.0], period=14) is None


# -----------------------------------------------------------------------------
# MACD
# -----------------------------------------------------------------------------
def test_macd_returns_floats_for_35_bar_window():
    closes = [100.0 + i * 0.5 for i in range(35)]
    macd, signal = compute_macd_signal(closes)
    assert macd is not None
    assert signal is not None
    # Uptrend -> MACD line should be >= signal line
    assert macd >= signal


def test_macd_returns_none_for_short_window():
    macd, signal = compute_macd_signal([1.0] * 10)
    assert macd is None and signal is None


# -----------------------------------------------------------------------------
# Volume ratio
# -----------------------------------------------------------------------------
def test_volume_ratio_detects_3x_spike():
    volumes = [1_000_000] * 20 + [3_000_000]
    r = compute_volume_ratio(volumes, lookback=20)
    assert r is not None
    assert r == pytest.approx(3.0, abs=1e-6)


def test_volume_ratio_none_when_too_short():
    assert compute_volume_ratio([100, 200, 300], lookback=20) is None


# -----------------------------------------------------------------------------
# Catalyst
# -----------------------------------------------------------------------------
def test_catalyst_score_zero_with_no_earnings():
    assert compute_catalyst_score(None) == 0.0


def test_catalyst_score_high_within_5_days():
    s = compute_catalyst_score(_earnings_in(3))
    assert s == 1.0


def test_catalyst_score_medium_within_14_days():
    s = compute_catalyst_score(_earnings_in(10))
    assert s == 0.7


def test_catalyst_score_low_within_30_days():
    s = compute_catalyst_score(_earnings_in(25))
    assert s == 0.4


def test_catalyst_score_zero_far_future():
    s = compute_catalyst_score(_earnings_in(90))
    assert s == 0.0


def test_catalyst_score_zero_when_date_in_past():
    assert compute_catalyst_score(_earnings_in(-5)) == 0.0


def test_catalyst_score_zero_with_invalid_date():
    bad = _FakeEarnings(next_earnings_date="not-a-date")
    assert compute_catalyst_score(bad) == 0.0


# -----------------------------------------------------------------------------
# SwingScreener integration
# -----------------------------------------------------------------------------
def test_strong_setup_yields_quality_strong_or_moderate():
    """A real uptrend + volume spike + near earnings should grade strong/moderate."""
    screener = SwingScreener()
    window = _strong_uptrend_window()
    earnings = _earnings_in(3)
    score = screener.score_one(window, earnings=earnings)
    # The composite must comfortably clear the moderate threshold
    assert score.signal_quality in ("strong", "moderate")
    assert score.total_score >= 0.55


def test_weak_flat_setup_rejects():
    screener = SwingScreener()
    window = _flat_window()
    score = screener.score_one(window, earnings=None)
    # Flat tape should not exceed the moderate bar
    assert score.signal_quality in ("weak", "reject")


def test_screen_universe_filters_by_min_quality():
    screener = SwingScreener()
    windows = [_strong_uptrend_window("AAA"), _flat_window("BBB"),
               _downtrend_window("CCC")]
    earnings_map = {"AAA": _earnings_in(3)}
    picks = screener.screen_universe(windows, earnings_map=earnings_map,
                                     top_n=10, min_quality="moderate")
    tickers = {p["symbol"] for p in picks}
    # Strong uptrend should be there; flat / downtrend should be filtered
    assert "AAA" in tickers
    assert "BBB" not in tickers
    assert "CCC" not in tickers


def test_emitted_picks_have_swing_contract_fields():
    screener = SwingScreener()
    window = _strong_uptrend_window()
    picks = screener.screen_universe([window], earnings_map={window.ticker: _earnings_in(3)},
                                     top_n=5, min_quality="moderate")
    assert len(picks) == 1
    pick = picks[0]
    assert pick["pick_type"] == "swing"
    assert pick["exit_mode"] == "tp_sl"
    assert pick["take_profit"] > pick["entry_price"]
    assert pick["stop_loss"] < pick["entry_price"]
    assert pick["stop_loss"] > 0


def test_tp_widens_for_high_momentum():
    """Verify the TP/SL helper widens TP and tightens SL above the momentum bar."""
    from alpha_engine.swing_screener import _compute_tp_sl
    price = 100.0
    tp_low, sl_low = _compute_tp_sl(price, momentum=0.5)
    tp_hi, sl_hi = _compute_tp_sl(price, momentum=0.95)
    assert tp_low == pytest.approx(price * (1 + DEFAULT_TP_PCT))
    assert sl_low == pytest.approx(price * (1 - DEFAULT_SL_PCT))
    assert tp_hi == pytest.approx(price * (1 + HIGH_MOMENTUM_TP_PCT))
    assert sl_hi == pytest.approx(price * (1 - HIGH_MOMENTUM_SL_PCT))
    assert tp_hi > tp_low
    assert sl_hi > sl_low  # tighter (closer to price) for high momentum


def test_works_without_earnings_fetcher_or_earnings():
    """No earnings_fetcher passed and no earnings_map should still emit/score."""
    screener = SwingScreener()
    window = _strong_uptrend_window()
    score = screener.score_one(window, earnings=None)
    assert score.catalyst_score == 0.0
    # screen_universe with no earnings_map at all
    picks = screener.screen_universe([window], earnings_map=None,
                                     top_n=5, min_quality="weak")
    # The strong uptrend should still be eligible at min_quality=weak
    assert any(p["symbol"] == window.ticker for p in picks)


def test_score_one_extra_dict_carries_indicator_values():
    screener = SwingScreener()
    window = _strong_uptrend_window()
    score = screener.score_one(window)
    assert "rsi" in score.extra
    assert "volume_ratio" in score.extra
    assert score.extra["rsi"] is not None


def test_momentum_score_low_for_oversold_no_macd_pos():
    """Down-trend produces oversold RSI + bearish MACD -> low momentum."""
    closes = [200.0 - 0.5 * i for i in range(60)]
    window = OHLCVWindow(ticker="BEAR", closes=closes,
                         volumes=[1_000_000] * 60, current_price=closes[-1])
    m = compute_momentum_score(window)
    assert m <= 0.2
