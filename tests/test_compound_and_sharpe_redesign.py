"""Tests for T1.4 / loop2 #6 metric redesign.

Covers the new compound functions and per-trade Sharpe in
``audit_trail.dashboard_generator``:

  - ``_compound_rolling_window``           (last-N geometric compound)
  - ``_compound_per_day_geomean_annualized`` (daily geomean × 252)
  - ``_per_trade_sharpe``                  (mean/std per-trade Sharpe)

Plus a schema check that the summary block keys list expected to be emitted
includes all 4 compound + 4 sharpe keys (introspection, no end-to-end run).
"""

from __future__ import annotations

import math
from typing import Any

import pytest

from audit_trail import dashboard_generator as dg


# ─── helpers ────────────────────────────────────────────────────────────────

def _mk_pick(pnl: float, day: str = "2026-05-01", sym: str = "BTCUSDT") -> dict:
    """Minimal resolved-pick shape for the metric functions."""
    return {
        "pnl_pct": pnl,
        "timestamp": f"{day}T00:00:00Z",
        "symbol": sym,
    }


def _mk_n_picks(n: int, pnl: float = 0.5, base_day: str = "2026-05-01") -> list[dict]:
    """N picks all on ``base_day`` with the same pnl. Fast for sequence tests."""
    return [_mk_pick(pnl, day=base_day, sym=f"S{i:04d}") for i in range(n)]


# ─── _compound_rolling_window ───────────────────────────────────────────────

def test_rolling_window_uses_all_when_n_below_window() -> None:
    picks = _mk_n_picks(50, pnl=1.0)
    result = dg._compound_rolling_window(picks, window=100)
    expected = ((1.01) ** 50 - 1.0) * 100.0
    assert result == pytest.approx(expected, abs=0.01)


def test_rolling_window_uses_last_window_when_n_exceeds() -> None:
    """200 picks: first 100 are -5%, last 100 are +1%. Window=100 → only +1% trades."""
    picks: list[dict] = []
    for i in range(100):
        picks.append({"pnl_pct": -5.0, "timestamp": f"2026-05-01T{i:02d}:00:00Z",
                      "symbol": f"L{i:04d}"})
    for i in range(100):
        picks.append({"pnl_pct": 1.0, "timestamp": f"2026-05-02T{i:02d}:00:00Z",
                      "symbol": f"W{i:04d}"})

    result = dg._compound_rolling_window(picks, window=100)
    expected = ((1.01) ** 100 - 1.0) * 100.0
    assert result == pytest.approx(expected, abs=0.05)


def test_rolling_window_empty_returns_zero() -> None:
    assert dg._compound_rolling_window([], window=100) == 0.0


def test_rolling_window_caps_per_trade_pnl() -> None:
    """A single +500% trade must be capped at the default 10% ceiling."""
    picks = [_mk_pick(500.0)]
    result = dg._compound_rolling_window(picks, window=100, max_pnl_pct=10.0)
    assert result == pytest.approx(10.0, abs=0.01)


# ─── _compound_per_day_geomean_annualized ──────────────────────────────────

def test_geomean_annualized_constant_daily_return() -> None:
    """+0.1% per day over sufficient span (>=30d) yields positive annualized CAGR (calendar)."""
    picks: list[dict] = []
    for d in range(40):
        day = f"2026-05-{d+1:02d}" if d < 31 else f"2026-06-{d-30:02d}"
        picks.append(_mk_pick(0.1, day=day, sym=f"S{d}"))
    result = dg._compound_per_day_geomean_annualized(picks)
    # 40 daily +0.1% over ~39d span → positive CAGR after annualization; not None
    assert result is not None
    assert result > 10.0  # conservative; actual ~ (1.001**40)**(365.25/39) annualized


def test_geomean_annualized_alternating_returns_near_zero() -> None:
    """Alternating +1%/-1% per day over >=30d span → CAGR near 0%."""
    picks: list[dict] = []
    for d in range(31):
        day = f"2026-05-{d+1:02d}"
        pnl = 1.0 if d % 2 == 0 else -1.0
        picks.append(_mk_pick(pnl, day=day, sym=f"S{d}"))
    result = dg._compound_per_day_geomean_annualized(picks)
    # Pairwise (1.01*0.99)=0.9999 → slight decay but near-zero annualized over 30d
    assert result is not None
    assert abs(result) < 15.0  # slight geo decay from 0.9999/pair annualizes to ~10% neg over short obs


def test_geomean_annualized_insufficient_days_returns_none() -> None:
    picks = [_mk_pick(1.0, day="2026-05-01")]
    assert dg._compound_per_day_geomean_annualized(picks) is None


def test_geomean_annualized_clamped_at_sanity_cap() -> None:
    """Huge positive daily returns over sufficient span → clamped at 999.9 (new cap)."""
    picks: list[dict] = []
    for d in range(40):
        day = f"2026-05-{d+1:02d}" if d < 31 else f"2026-06-{d-30:02d}"
        # 9.5% daily (capped at 10% in func) over 39d → explosive CAGR → clamp 999.9
        picks.append(_mk_pick(9.5, day=day, sym=f"S{d}"))
    result = dg._compound_per_day_geomean_annualized(picks)
    assert result == 999.9


# ─── _per_trade_sharpe ─────────────────────────────────────────────────────

def test_per_trade_sharpe_zero_variance_returns_zero() -> None:
    picks = [_mk_pick(1.0) for _ in range(20)]
    sharpe, annual = dg._per_trade_sharpe(picks, days_span=10)
    assert sharpe == 0.0
    assert annual == 0.0


def test_per_trade_sharpe_known_mean_std() -> None:
    """Hand-computed: pnls = [1, -1, 2, -2, 3, -3] → mean=0, std=2.366 → sharpe=0."""
    pnls = [1.0, -1.0, 2.0, -2.0, 3.0, -3.0]
    picks = [_mk_pick(p, sym=f"S{i}") for i, p in enumerate(pnls)]
    sharpe, _ = dg._per_trade_sharpe(picks, days_span=6)
    assert sharpe == pytest.approx(0.0, abs=1e-6)


def test_per_trade_sharpe_positive_mean_yields_positive_sharpe() -> None:
    pnls = [2.0, 1.0, 3.0, 1.5, 2.5, 2.0]  # mean=2.0, std~0.71
    picks = [_mk_pick(p, sym=f"S{i}") for i, p in enumerate(pnls)]
    sharpe, annual = dg._per_trade_sharpe(picks, days_span=6)
    n = len(pnls)
    mean = sum(pnls) / n
    var = sum((x - mean) ** 2 for x in pnls) / (n - 1)
    expected = mean / math.sqrt(var)
    assert sharpe == pytest.approx(expected, abs=1e-3)
    # Annualized factor: trades_per_year = (6/6)*252 = 252 → annual = sharpe*sqrt(252)
    assert annual == pytest.approx(expected * math.sqrt(252), abs=1e-2)


def test_per_trade_sharpe_too_few_picks_returns_zero() -> None:
    sharpe, annual = dg._per_trade_sharpe([_mk_pick(1.0)], days_span=1)
    assert sharpe == 0.0
    assert annual == 0.0


# ─── back-compat: deprecated function still exists & works ──────────────────

def test_legacy_compound_equal_weight_still_callable() -> None:
    picks = _mk_n_picks(10, pnl=1.0)
    result = dg._compound_equal_weight_capped_sequence(picks)
    expected = ((1.01) ** 10 - 1.0) * 100.0
    assert result == pytest.approx(expected, abs=0.01)


# ─── schema: new summary keys are referenced in source ──────────────────────

def test_summary_block_emits_all_compound_and_sharpe_keys() -> None:
    """Static check: source contains all 4 compound + 4 sharpe summary keys."""
    src = dg.__file__
    with open(src, "r", encoding="utf-8") as f:
        text = f.read()

    compound_keys = [
        '"total_pnl_pct"',
        '"total_pnl_pct_sum_raw"',
        '"total_pnl_pct_compounded_ew"',
        '"total_pnl_pct_compounded_rolling_100"',
        '"total_pnl_pct_geomean_annualized"',
    ]
    sharpe_keys = [
        '"net_sharpe"',
        '"net_sharpe_annual"',
        '"net_sharpe_daily"',
        '"net_sharpe_daily_annual"',
        '"net_sharpe_per_trade"',
        '"net_sharpe_per_trade_annual"',
    ]
    for k in compound_keys + sharpe_keys:
        assert k in text, f"missing summary key: {k}"
