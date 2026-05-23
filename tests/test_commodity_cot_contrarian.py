"""Tests for alpha_engine.commodity_cot_contrarian (freebuff B4).

Pins:
  • extreme-long  → SHORT  (fade crowded speculator longs)
  • extreme-short → LONG   (fade crowded speculator shorts)
  • mid-percentile → no signal
  • stale (>14d)  → empty list
  • rollback env  → empty list
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from alpha_engine import commodity_cot_contrarian as ccc


# ──────────────────────────────────────────────────────────────────────────────
# Mock CFTC report builders
# ──────────────────────────────────────────────────────────────────────────────
def _report(date_str: str, nc_long: int, nc_short: int) -> dict:
    return {
        "report_date_as_yyyy_mm_dd": date_str,
        "noncomm_positions_long_all": str(nc_long),
        "noncomm_positions_short_all": str(nc_short),
    }


def _build_reports(latest_net: int, baseline_net: int = 0,
                   weeks: int = 52, latest_date: str | None = None) -> list[dict]:
    """Newest first. Latest week = latest_net, prior 51 weeks = baseline_net."""
    end = datetime.strptime(latest_date or "2026-05-05", "%Y-%m-%d")
    rows: list[dict] = []
    for i in range(weeks):
        d = (end - timedelta(weeks=i)).strftime("%Y-%m-%d")
        if i == 0:
            net = latest_net
        else:
            net = baseline_net + (i * 100)  # tiny variation so distribution isn't degenerate
        if net >= 0:
            rows.append(_report(d, nc_long=net + 100_000, nc_short=100_000))
        else:
            rows.append(_report(d, nc_long=100_000, nc_short=100_000 - net))
    return rows


_FRESH_NOW = datetime(2026, 5, 8, 12, 0, tzinfo=timezone.utc)


# ──────────────────────────────────────────────────────────────────────────────
# Signal computation (unit, no network)
# ──────────────────────────────────────────────────────────────────────────────
def test_extreme_long_emits_short() -> None:
    reports = _build_reports(latest_net=10_000_000, baseline_net=0)
    out = ccc.compute_noncomm_signal(reports, now=_FRESH_NOW)
    assert out["signal"] == "SELL"
    assert out["direction"] == "SHORT"
    assert out["percentile_rank"] >= ccc.EXTREME_LONG_PERCENTILE
    assert out["confidence"] >= 50
    assert "fade" in out["reason"].lower()


def test_extreme_short_emits_long() -> None:
    reports = _build_reports(latest_net=-10_000_000, baseline_net=0)
    out = ccc.compute_noncomm_signal(reports, now=_FRESH_NOW)
    assert out["signal"] == "BUY"
    assert out["direction"] == "LONG"
    assert out["percentile_rank"] <= ccc.EXTREME_SHORT_PERCENTILE
    assert out["confidence"] >= 50
    assert "fade" in out["reason"].lower()


def test_mid_percentile_no_signal() -> None:
    # Latest sits in the middle of the 52w distribution
    rng_nets = [i * 1_000 for i in range(52)]
    median_net = rng_nets[26]
    reports: list[dict] = []
    end = datetime(2026, 5, 5)
    for i, net in enumerate(reversed(rng_nets)):  # newest first
        if i == 0:
            net = median_net
        d = (end - timedelta(weeks=i)).strftime("%Y-%m-%d")
        reports.append(_report(d, nc_long=net + 100_000, nc_short=100_000))
    out = ccc.compute_noncomm_signal(reports, now=_FRESH_NOW)
    assert out["signal"] == "NEUTRAL"
    assert out["direction"] == "NEUTRAL"
    assert out["confidence"] == 0


def test_stale_reports_neutral() -> None:
    # Latest report is 30d old → must be flagged stale, no signal
    stale_date = "2026-04-01"
    reports = _build_reports(latest_net=10_000_000, baseline_net=0,
                              latest_date=stale_date)
    out = ccc.compute_noncomm_signal(reports, now=_FRESH_NOW)
    assert out["signal"] == "NEUTRAL"
    assert out["stale"] is True


def test_insufficient_data_neutral() -> None:
    out = ccc.compute_noncomm_signal([], now=_FRESH_NOW)
    assert out["signal"] == "NEUTRAL"


# ──────────────────────────────────────────────────────────────────────────────
# Public picks() — fetch is mocked
# ──────────────────────────────────────────────────────────────────────────────
@pytest.mark.skip(reason="commodity_cot_contrarian module gated 2026-05-14 (look-ahead bias from CFTC publication lag). Re-enable when M-008/M-021 lag-corrected pipeline lands.")
def test_picks_emits_short_on_extreme_long(monkeypatch: pytest.MonkeyPatch) -> None:
    fresh_date = _FRESH_NOW.strftime("%Y-%m-%d")
    fake = _build_reports(latest_net=10_000_000, baseline_net=0,
                           latest_date=fresh_date)

    def fake_fetch(_code: str):
        return fake

    monkeypatch.setattr(ccc, "_fetch_cftc_reports", fake_fetch)
    # Pin "now" so the freshness gate sees recent reports
    real_dt = ccc.datetime
    class _DT(real_dt):
        @classmethod
        def now(cls, tz=None):
            return _FRESH_NOW
    monkeypatch.setattr(ccc, "datetime", _DT)
    monkeypatch.delenv("COMMODITY_COT_CONTRARIAN_DISABLED", raising=False)

    picks = ccc.commodity_cot_contrarian_picks()
    assert len(picks) == len(ccc.COMMODITY_CONTRACTS)
    for p in picks:
        assert p["direction"] == "SHORT"
        assert p["strategy"] == "commodity_cot_contrarian"
        assert p["asset_class"] == "COMMODITY"
        assert p["timeframe"] == "1w"
        assert p["confidence"] > 0
        # Schema parity with cftc_cot_commercial_signal output
        for key in ("symbol", "direction", "strategy", "asset_class",
                    "timeframe", "confidence", "generated_at",
                    "percentile", "current_net", "latest_cot_date"):
            assert key in p, f"missing schema key: {key}"


@pytest.mark.skip(reason="commodity_cot_contrarian module gated 2026-05-14 (look-ahead bias from CFTC publication lag). Re-enable when M-008/M-021 lag-corrected pipeline lands.")
def test_picks_emits_long_on_extreme_short(monkeypatch: pytest.MonkeyPatch) -> None:
    fresh_date = _FRESH_NOW.strftime("%Y-%m-%d")
    fake = _build_reports(latest_net=-10_000_000, baseline_net=0,
                           latest_date=fresh_date)
    monkeypatch.setattr(ccc, "_fetch_cftc_reports", lambda _c: fake)
    real_dt = ccc.datetime
    class _DT(real_dt):
        @classmethod
        def now(cls, tz=None):
            return _FRESH_NOW
    monkeypatch.setattr(ccc, "datetime", _DT)
    monkeypatch.delenv("COMMODITY_COT_CONTRARIAN_DISABLED", raising=False)

    picks = ccc.commodity_cot_contrarian_picks()
    assert len(picks) > 0
    assert all(p["direction"] == "LONG" for p in picks)


def test_picks_empty_on_stale(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _build_reports(latest_net=10_000_000, baseline_net=0,
                           latest_date="2026-04-01")  # 37d before _FRESH_NOW
    monkeypatch.setattr(ccc, "_fetch_cftc_reports", lambda _c: fake)
    real_dt = ccc.datetime
    class _DT(real_dt):
        @classmethod
        def now(cls, tz=None):
            return _FRESH_NOW
    monkeypatch.setattr(ccc, "datetime", _DT)
    monkeypatch.delenv("COMMODITY_COT_CONTRARIAN_DISABLED", raising=False)

    picks = ccc.commodity_cot_contrarian_picks()
    assert picks == []


def test_picks_empty_on_fetch_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ccc, "_fetch_cftc_reports", lambda _c: None)
    monkeypatch.delenv("COMMODITY_COT_CONTRARIAN_DISABLED", raising=False)
    assert ccc.commodity_cot_contrarian_picks() == []


def test_rollback_env_returns_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    # Even with rich data, rollback must short-circuit immediately.
    fake = _build_reports(latest_net=10_000_000, baseline_net=0)

    def boom(_code: str):
        raise AssertionError("fetch should not be called when rollback is set")

    monkeypatch.setattr(ccc, "_fetch_cftc_reports", boom)
    monkeypatch.setenv("COMMODITY_COT_CONTRARIAN_DISABLED", "1")
    assert ccc.commodity_cot_contrarian_picks() == []


# ──────────────────────────────────────────────────────────────────────────────
# Backtest sanity
# ──────────────────────────────────────────────────────────────────────────────
def test_synthetic_backtest_runs() -> None:
    bt = ccc._synthetic_backtest(seed=7)
    assert bt["weeks_simulated"] == 104
    assert bt["n_signals"] >= 0
    assert 0.0 <= bt["win_rate_pct"] <= 100.0
    assert bt["wins"] + bt["losses"] == bt["n_signals"]
