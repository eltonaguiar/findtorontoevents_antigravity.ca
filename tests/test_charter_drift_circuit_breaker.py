"""Tests for Charter §7 drift circuit-breaker."""
from datetime import datetime, timedelta, timezone

import pytest

from alpha_engine.charter_drift_circuit_breaker import (
    DEFAULT_MIN_REALIZED_N,
    compute_realized_wr_30d,
    evaluate_all_classes,
    is_sizing_breached,
)


NOW = datetime(2026, 5, 13, 12, 0, tzinfo=timezone.utc)


def _pick(asset_class, outcome, days_ago, *, field="_outcome"):
    ts = (NOW - timedelta(days=days_ago)).isoformat()
    p = {"asset_class": asset_class, "timestamp": ts}
    p[field] = outcome
    return p


def test_realized_wr_empty():
    wr, n = compute_realized_wr_30d([], "CRYPTO", now=NOW)
    assert wr is None
    assert n == 0


def test_realized_wr_basic_60pct():
    picks = (
        [_pick("CRYPTO", "WIN", 5) for _ in range(6)]
        + [_pick("CRYPTO", "LOSS", 5) for _ in range(4)]
    )
    wr, n = compute_realized_wr_30d(picks, "CRYPTO", now=NOW)
    assert wr == pytest.approx(60.0)
    assert n == 10


def test_realized_wr_falls_back_to_status_field():
    # Pre-resolver-gap-fix: only `status` is set, not `_outcome`.
    picks = (
        [_pick("EQUITY", "WIN", 3, field="status") for _ in range(7)]
        + [_pick("EQUITY", "LOSS", 3, field="status") for _ in range(3)]
    )
    wr, n = compute_realized_wr_30d(picks, "EQUITY", now=NOW)
    assert wr == pytest.approx(70.0)
    assert n == 10


def test_realized_wr_excludes_old_picks():
    # 45 days ago > 30-day lookback
    picks = [_pick("CRYPTO", "WIN", 45) for _ in range(10)]
    wr, n = compute_realized_wr_30d(picks, "CRYPTO", now=NOW)
    assert wr is None
    assert n == 0


def test_realized_wr_filters_by_asset_class():
    picks = (
        [_pick("CRYPTO", "WIN", 5) for _ in range(10)]
        + [_pick("FOREX", "LOSS", 5) for _ in range(10)]
    )
    wr_crypto, n_crypto = compute_realized_wr_30d(picks, "CRYPTO", now=NOW)
    wr_forex, n_forex = compute_realized_wr_30d(picks, "FOREX", now=NOW)
    assert wr_crypto == 100.0 and n_crypto == 10
    assert wr_forex == 0.0 and n_forex == 10


def test_realized_wr_ignores_flat():
    picks = (
        [_pick("CRYPTO", "WIN", 5) for _ in range(5)]
        + [_pick("CRYPTO", "FLAT", 5) for _ in range(10)]
    )
    wr, n = compute_realized_wr_30d(picks, "CRYPTO", now=NOW)
    assert wr == 100.0
    assert n == 5  # FLATs excluded


def test_sizing_breached_no_backtest():
    breached, reason = is_sizing_breached([], {}, "CRYPTO", now=NOW)
    assert not breached
    assert "no_backtest" in reason


def test_sizing_breached_no_baseline():
    wf = {"CRYPTO": {"oos_wr": None, "oos_wr_std": None}}
    breached, reason = is_sizing_breached([], wf, "CRYPTO", now=NOW)
    assert not breached
    assert "no_baseline" in reason


def test_sizing_breached_cold_start_when_n_below_min():
    wf = {"CRYPTO": {"oos_wr": 50.0, "oos_wr_std": 5.0}}
    picks = [_pick("CRYPTO", "LOSS", 5) for _ in range(5)]
    breached, reason = is_sizing_breached(picks, wf, "CRYPTO", now=NOW)
    assert not breached
    assert "cold_start" in reason


def test_sizing_breached_trip_on_deep_drift():
    # Backtest: 50% +/- 5%. Lower bound at 2-sigma = 40%.
    # Realized: 20% with n=40.
    wf = {"CRYPTO": {"oos_wr": 50.0, "oos_wr_std": 5.0}}
    picks = (
        [_pick("CRYPTO", "WIN", 5) for _ in range(8)]
        + [_pick("CRYPTO", "LOSS", 5) for _ in range(32)]
    )
    breached, reason = is_sizing_breached(picks, wf, "CRYPTO", now=NOW)
    assert breached
    assert "drift_breach" in reason
    assert "20.0%" in reason


def test_sizing_not_breached_when_within_band():
    wf = {"CRYPTO": {"oos_wr": 50.0, "oos_wr_std": 5.0}}
    # 45% realized — inside the 2-sigma band [40%, 60%]
    picks = (
        [_pick("CRYPTO", "WIN", 5) for _ in range(18)]
        + [_pick("CRYPTO", "LOSS", 5) for _ in range(22)]
    )
    breached, reason = is_sizing_breached(picks, wf, "CRYPTO", now=NOW)
    assert not breached
    assert "ok:" in reason


def test_evaluate_all_classes_emits_verdict_per_class():
    wf = {
        "CRYPTO": {"oos_wr": 50.0, "oos_wr_std": 5.0},
        "EQUITY": {"oos_wr": 60.0, "oos_wr_std": 8.0},
    }
    picks = []  # all classes will be cold_start
    out = evaluate_all_classes(picks, wf, now=NOW)
    assert "CRYPTO" in out
    assert "EQUITY" in out
    assert "FOREX" in out  # default classes list includes FOREX
    assert out["CRYPTO"]["breached"] is False
    assert out["CRYPTO"]["realized_n_30d"] == 0


def test_default_min_realized_n_is_20():
    # Lowered 30→20 (2026-05-17) so ETF (~25 resolved/30d) gets circuit-breaker
    # coverage. 2σ trip still requires WR<28% at n=20 — false-positive guard holds.
    assert DEFAULT_MIN_REALIZED_N == 20
