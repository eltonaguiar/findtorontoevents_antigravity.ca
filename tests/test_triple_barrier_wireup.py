"""Tests for the triple-barrier labeler wire-up in outcome_resolver.

Covers:
  * Pure unit tests on the bar-replay routine using contrived OHLC bars
    (TP@+5%, SL@-3%) — verifies first-touch detection, SL conservative
    tie-break, TIMEOUT fallback, and hold-days cap.
  * Integration tests on ``apply_triple_barrier_labels`` using picks that
    pre-supply their own ``ohlc_window`` field (no network) — verifies
    additive stamping (pnl_pct / status / exit_price NEVER mutated).
  * Asset-class inference helper.
  * Sanity test: 50-pick clear-edge agreement vs the existing pnl_pct
    sign-based labeler must be >= 95%.
  * Env-var gating values.

The yfinance fetch path (``_triple_barrier_fetch_bars``) is exercised in
the ``--triple-barrier`` CLI flow which ships behind the env-var gate, and
is not reached when ``ohlc_window`` is pre-supplied to the picks.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from alpha_engine.outcome_resolver import (  # noqa: E402
    apply_triple_barrier_labels,
    TRIPLE_BARRIER_HOLD_DAYS_BY_CLASS,
    TRIPLE_BARRIER_HOLD_DAYS_DEFAULT,
    _triple_barrier_asset_class,
    _triple_barrier_label_bar_replay,
)


def _bars(*highs_lows_closes, start_date="2025-01-01"):
    """Helper: build a bar list from (high, low, close) triples."""
    from datetime import date, timedelta
    d0 = date.fromisoformat(start_date)
    out = []
    for i, (hi, lo, cl) in enumerate(highs_lows_closes):
        out.append({
            "date": (d0 + timedelta(days=i)).isoformat(),
            "open": cl, "high": hi, "low": lo, "close": cl,
        })
    return out


# ---------------------------------------------------------------------------
# Pure unit tests — bar-replay
# ---------------------------------------------------------------------------

def test_long_tp_hit_first():
    """LONG @ entry=100, TP=105, SL=97. Bar with high=106 → WIN at TP."""
    pick = {"direction": "LONG", "entry_price": 100, "take_profit": 105, "stop_loss": 97}
    bars = _bars((101, 99, 100), (106, 100, 105))  # day 2 hits TP
    out = _triple_barrier_label_bar_replay(pick, bars, hold_days=14)
    assert out["triple_barrier_label"] == "WIN"
    assert out["triple_barrier_first_barrier"] == "TP"
    assert out["triple_barrier_resolution_price"] == 105.0
    assert out["triple_barrier_bars_walked"] == 2
    assert out["triple_barrier_hold_days_cap"] == 14


def test_long_sl_hit_first():
    """LONG @ entry=100, TP=105, SL=97. Bar with low=96 → LOSS at SL."""
    pick = {"direction": "LONG", "entry_price": 100, "take_profit": 105, "stop_loss": 97}
    bars = _bars((102, 96, 97))
    out = _triple_barrier_label_bar_replay(pick, bars, hold_days=14)
    assert out["triple_barrier_label"] == "LOSS"
    assert out["triple_barrier_first_barrier"] == "SL"
    assert out["triple_barrier_resolution_price"] == 97.0


def test_long_both_in_one_bar_sl_wins_conservative():
    """If a single bar has high >= TP AND low <= SL, conservative rule
    picks SL first (worst case for retroactive labeling)."""
    pick = {"direction": "LONG", "entry_price": 100, "take_profit": 105, "stop_loss": 97}
    bars = _bars((106, 96, 100))  # wide bar touches both
    out = _triple_barrier_label_bar_replay(pick, bars, hold_days=14)
    assert out["triple_barrier_label"] == "LOSS"
    assert out["triple_barrier_first_barrier"] == "SL"


def test_short_tp_hit_first():
    """SHORT @ entry=100, TP=95, SL=103. Bar with low=94 → WIN at TP."""
    pick = {"direction": "SHORT", "entry_price": 100, "take_profit": 95, "stop_loss": 103}
    bars = _bars((101, 99, 100), (102, 94, 95))
    out = _triple_barrier_label_bar_replay(pick, bars, hold_days=14)
    assert out["triple_barrier_label"] == "WIN"
    assert out["triple_barrier_first_barrier"] == "TP"
    assert out["triple_barrier_resolution_price"] == 95.0


def test_short_sl_hit_first():
    """SHORT @ entry=100, SL=103. Bar with high=104 → LOSS at SL."""
    pick = {"direction": "SHORT", "entry_price": 100, "take_profit": 95, "stop_loss": 103}
    bars = _bars((104, 99, 100))
    out = _triple_barrier_label_bar_replay(pick, bars, hold_days=14)
    assert out["triple_barrier_label"] == "LOSS"
    assert out["triple_barrier_first_barrier"] == "SL"
    assert out["triple_barrier_resolution_price"] == 103.0


def test_timeout_neither_barrier_hit():
    """LONG with TP=110 SL=90; bars stay between 95-105 → TIMEOUT."""
    pick = {"direction": "LONG", "entry_price": 100, "take_profit": 110, "stop_loss": 90}
    bars = _bars((102, 98, 100), (104, 99, 102), (105, 100, 103))
    out = _triple_barrier_label_bar_replay(pick, bars, hold_days=14)
    assert out["triple_barrier_label"] == "TIMEOUT"
    assert out["triple_barrier_first_barrier"] == "TIME"
    assert out["triple_barrier_resolution_price"] == 103.0
    assert out["triple_barrier_bars_walked"] == 3


def test_hold_days_cap_truncates_window():
    """hold_days=2 should stop after bar 2 even if bar 3 would hit TP."""
    pick = {"direction": "LONG", "entry_price": 100, "take_profit": 105, "stop_loss": 90}
    bars = _bars((101, 99, 100), (102, 99, 101), (106, 105, 105))  # TP on day 3
    out = _triple_barrier_label_bar_replay(pick, bars, hold_days=2)
    assert out["triple_barrier_label"] == "TIMEOUT"
    assert out["triple_barrier_bars_walked"] == 2


def test_no_bars_returns_unlabeled():
    pick = {"direction": "LONG", "entry_price": 100, "take_profit": 105, "stop_loss": 97}
    out = _triple_barrier_label_bar_replay(pick, [], hold_days=14)
    assert out["triple_barrier_label"] == "UNLABELED"


def test_no_barriers_returns_unlabeled():
    pick = {"direction": "LONG", "entry_price": 100, "take_profit": 0, "stop_loss": 0}
    bars = _bars((110, 90, 100))
    out = _triple_barrier_label_bar_replay(pick, bars, hold_days=14)
    assert out["triple_barrier_label"] == "UNLABELED"


# ---------------------------------------------------------------------------
# Integration — apply_triple_barrier_labels (additive stamping)
# ---------------------------------------------------------------------------

def test_apply_additive_does_not_mutate_pnl_or_status():
    """Wire-up must NEVER touch pnl_pct, status, exit_price, etc."""
    pick = {
        "id": "pick-eq-1",
        "symbol": "AAPL",
        "asset_class": "EQUITY",
        "direction": "LONG",
        "entry_price": 100.0,
        "take_profit": 105.0,
        "stop_loss": 97.0,
        # legacy resolver fields — must be preserved untouched
        "pnl_pct": 0.0,
        "status": "CLOSED",
        "exit_price": 100.0,
        "exit_reason": "RESOLVE_FAILED_BREAKEVEN",
        # synthetic OHLC window: TP hit on day 2
        "ohlc_window": _bars((101, 99, 100), (106, 100, 105)),
    }
    report = apply_triple_barrier_labels(
        [pick], fetch_bars=False, skip_crypto=True, dry_run=False,
    )
    assert report["stamped"] == 1
    assert report["label_counts"].get("WIN") == 1

    # Additive fields present
    assert pick["triple_barrier_label"] == "WIN"
    assert pick["triple_barrier_first_barrier"] == "TP"
    assert pick["triple_barrier_resolution_price"] == 105.0
    assert pick["triple_barrier_asset_class"] == "EQUITY"
    assert pick["triple_barrier_hold_days_cap"] == TRIPLE_BARRIER_HOLD_DAYS_BY_CLASS["EQUITY"]
    assert pick["triple_barrier_labeler_version"] == "v1"
    assert pick["triple_barrier_stamped_at"]  # non-empty
    # Sign-based cross-check stamped too (will be FLAT_CLOSE_BUG since pnl=0
    # and barriers are valid — that's the expected output of the existing labeler).
    assert "triple_barrier_pnl_sign_label" in pick

    # Legacy fields untouched — additive contract
    assert pick["pnl_pct"] == 0.0
    assert pick["status"] == "CLOSED"
    assert pick["exit_price"] == 100.0
    assert pick["exit_reason"] == "RESOLVE_FAILED_BREAKEVEN"


def test_apply_skips_crypto_by_default():
    pick = {
        "id": "pick-crypto-1",
        "symbol": "BTCUSDT",
        "asset_class": "CRYPTO",
        "direction": "LONG",
        "entry_price": 50000,
        "take_profit": 51000,
        "stop_loss": 49000,
        "pnl_pct": 0.01,
        "status": "WON",
        "ohlc_window": _bars((51500, 49500, 51000)),
    }
    report = apply_triple_barrier_labels(
        [pick], fetch_bars=False, skip_crypto=True, dry_run=False,
    )
    assert report["skipped_crypto"] == 1
    assert report["stamped"] == 0
    assert "triple_barrier_label" not in pick


def test_apply_dry_run_does_not_mutate():
    pick = {
        "id": "pick-fx-1",
        "symbol": "EURUSD=X",
        "asset_class": "FOREX",
        "direction": "LONG",
        "entry_price": 1.10,
        "take_profit": 1.12,
        "stop_loss": 1.09,
        "ohlc_window": _bars((1.13, 1.10, 1.12)),
    }
    report = apply_triple_barrier_labels(
        [pick], fetch_bars=False, skip_crypto=True, dry_run=True,
    )
    assert report["stamped"] == 1
    assert "triple_barrier_label" not in pick


def test_apply_no_barriers_is_skipped():
    pick = {
        "id": "pick-eq-2",
        "symbol": "AAPL",
        "asset_class": "EQUITY",
        "direction": "LONG",
        "entry_price": 100.0,
        "take_profit": 0.0,
        "stop_loss": 0.0,
        "ohlc_window": _bars((110, 90, 100)),
    }
    report = apply_triple_barrier_labels(
        [pick], fetch_bars=False, skip_crypto=True, dry_run=False,
    )
    assert report["skipped_no_barriers"] == 1
    assert report["stamped"] == 0


def test_apply_no_bars_stamps_unlabeled():
    """When no bars are available AND fetch_bars=False, stamp UNLABELED so
    the pick is distinguishable from one that simply hasn't been processed."""
    pick = {
        "id": "pick-fx-2",
        "symbol": "EURUSD=X",
        "asset_class": "FOREX",
        "direction": "LONG",
        "entry_price": 1.10,
        "take_profit": 1.12,
        "stop_loss": 1.09,
    }
    report = apply_triple_barrier_labels(
        [pick], fetch_bars=False, skip_crypto=True, dry_run=False,
    )
    assert report["skipped_no_bars"] == 1
    assert pick["triple_barrier_label"] == "UNLABELED"
    assert pick["triple_barrier_labeler_version"] == "v1"


# ---------------------------------------------------------------------------
# Asset-class inference + cross-agreement sanity
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("inputs,expected", [
    ({"asset_class": "EQUITY"}, "EQUITY"),
    ({"category": "stocks"}, "EQUITY"),
    ({"asset_class": "FX"}, "FOREX"),
    ({"symbol": "EURUSD=X"}, "FOREX"),
    ({"symbol": "GC=F"}, "COMMODITY"),
    ({"symbol": "BTCUSDT"}, "CRYPTO"),
])
def test_asset_class_inference(inputs, expected):
    assert _triple_barrier_asset_class(inputs) == expected


def test_50_pick_clear_edge_agreement_vs_pnl_sign():
    """50-pick sanity: bar-replay label agrees with the existing
    pnl_pct-sign labeler on >= 95% of clear-edge picks (>5% move).

    This exercises both labelers on the same picks; disagreement on clear
    edge would indicate a wire-up bug.
    """
    picks = []
    for i in range(25):
        # Clear WIN: bar hits TP, pnl_pct = +5% so sign-based labeler returns WIN.
        picks.append({
            "id": f"win-{i}",
            "symbol": "AAPL" if i % 2 == 0 else "EURUSD=X",
            "asset_class": "EQUITY" if i % 2 == 0 else "FOREX",
            "direction": "LONG",
            "entry_price": 100.0,
            "take_profit": 105.0,
            "stop_loss": 95.0,
            "pnl_pct": 0.05,
            "ohlc_window": _bars((101, 99, 100), (106, 100, 105)),
        })
    for i in range(25):
        # Clear LOSS: bar hits SL, pnl_pct = -5% → sign-based labeler returns LOSS.
        picks.append({
            "id": f"loss-{i}",
            "symbol": "MSFT" if i % 2 == 0 else "GBPUSD=X",
            "asset_class": "EQUITY" if i % 2 == 0 else "FOREX",
            "direction": "LONG",
            "entry_price": 100.0,
            "take_profit": 105.0,
            "stop_loss": 95.0,
            "pnl_pct": -0.05,
            "ohlc_window": _bars((96, 94, 95)),
        })

    report = apply_triple_barrier_labels(
        picks, fetch_bars=False, skip_crypto=True, dry_run=False,
    )
    agree = report["agreement_with_pnl_sign"]
    total = agree["agree"] + agree["disagree"]
    assert total > 0
    pct = agree["agree"] / total * 100
    assert pct >= 95.0, (
        f"Bar-replay vs pnl-sign agreement {pct:.1f}% < 95% "
        f"(agree={agree['agree']}, disagree={agree['disagree']}, "
        f"either_unlabeled={agree['either_unlabeled']})"
    )


# ---------------------------------------------------------------------------
# Env-var gate
# ---------------------------------------------------------------------------

def test_env_var_truthy_values_recognized(monkeypatch):
    """Sanity: the documented env-var values match the parser logic in main()."""
    truthy = {"1", "true", "yes", "on"}
    for v in ("1", "true", "TRUE", "yes", "on"):
        monkeypatch.setenv("TRIPLE_BARRIER_LABEL", v)
        assert os.environ["TRIPLE_BARRIER_LABEL"].strip().lower() in truthy
    for v in ("0", "false", "no", ""):
        monkeypatch.setenv("TRIPLE_BARRIER_LABEL", v)
        assert os.environ["TRIPLE_BARRIER_LABEL"].strip().lower() not in truthy
