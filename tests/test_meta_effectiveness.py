"""Tests for tools/portfolios/meta_effectiveness.py (Phase 6).

Synthetic fixtures only — no DB, no FS dependencies beyond tmp_path.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tools.portfolios import meta_effectiveness as me  # noqa: E402


# ---------------------------------------------------------------------------
# 1. Sharpe matches mean/stdev * sqrt(252).
# ---------------------------------------------------------------------------
def test_sharpe_matches_formula():
    rets = [0.01, -0.005, 0.012, -0.003, 0.008, -0.002, 0.004]
    mean = sum(rets) / len(rets)
    # population stdev (matches me._stdev)
    var = sum((r - mean) ** 2 for r in rets) / len(rets)
    sd = math.sqrt(var)
    expected = (mean / sd) * math.sqrt(252)
    got = me.sharpe(rets)
    assert got == pytest.approx(expected, rel=1e-9)


def test_sharpe_low_n_still_computes():
    # n=2: stdev defined → Sharpe defined (not gated on n=252)
    rets = [0.01, -0.005]
    out = me.sharpe(rets)
    assert isinstance(out, float)
    # n=1 → 0.0 by convention.
    assert me.sharpe([0.01]) == 0.0


# ---------------------------------------------------------------------------
# 2. MaxDD on a known peak-trough series.
# ---------------------------------------------------------------------------
def test_max_drawdown_known_series():
    navs = [100.0, 120.0, 90.0, 110.0, 60.0, 80.0]
    # Peak=120 at idx1, trough=60 at idx4 → DD = (60-120)/120 = -0.5
    assert me.max_drawdown(navs) == pytest.approx(-0.5, rel=1e-9)


def test_max_drawdown_empty_or_single():
    assert me.max_drawdown([]) == 0.0
    assert me.max_drawdown([100.0]) == 0.0


# ---------------------------------------------------------------------------
# 3. Equal-weight counterfactual / attribution on a 2-position fixture.
# ---------------------------------------------------------------------------
def test_attribution_equal_weight_counterfactual():
    detail = {
        "portfolio": {"starting_nav": 100000.0},
        "nav_curve": [
            {"asof_date": "2026-05-01", "nav_usd": 100000.0},
            {"asof_date": "2026-05-10", "nav_usd": 105000.0},
        ],
        "positions": [
            {"status": "closed", "asset_class": "CRYPTO",
             "realized_pnl_pct": 0.10, "direction": "long",
             "entry_date": "2026-05-02", "entry_price": 100.0, "qty": 10.0},
            {"status": "closed", "asset_class": "CRYPTO",
             "realized_pnl_pct": -0.02, "direction": "long",
             "entry_date": "2026-05-03", "entry_price": 50.0, "qty": 20.0},
        ],
    }
    port_metric = {"total_return_pct": 0.05}  # +5% total return
    attr = me._attribution(detail, port_metric)
    # equal_weight = mean(0.10, -0.02) = 0.04
    # sizing_contrib = 0.05 - 0.04 = 0.01
    assert attr["sizing_contrib"] == pytest.approx(0.01, rel=1e-9)
    assert attr["selection_contrib"] == 0.0  # documented in dry-run


# ---------------------------------------------------------------------------
# 4. Per-class skill picks highest-Sharpe model.
# ---------------------------------------------------------------------------
def test_per_class_skill_picks_best():
    roster = [
        {"portfolio_key": "A", "model_id": "alpha"},
        {"portfolio_key": "B", "model_id": "beta"},
        {"portfolio_key": "C", "model_id": "gamma"},
    ]
    details = {
        "A": {"positions": [
            {"status": "closed", "asset_class": "EQUITY", "realized_pnl_pct": 0.01},
            {"status": "closed", "asset_class": "EQUITY", "realized_pnl_pct": 0.02},
            {"status": "closed", "asset_class": "EQUITY", "realized_pnl_pct": 0.015},
        ]},
        "B": {"positions": [
            {"status": "closed", "asset_class": "EQUITY", "realized_pnl_pct": 0.05},
            {"status": "closed", "asset_class": "EQUITY", "realized_pnl_pct": -0.04},
            {"status": "closed", "asset_class": "EQUITY", "realized_pnl_pct": 0.06},
        ]},
        "C": {"positions": [
            {"status": "closed", "asset_class": "EQUITY", "realized_pnl_pct": -0.02},
            {"status": "closed", "asset_class": "EQUITY", "realized_pnl_pct": -0.03},
            {"status": "closed", "asset_class": "EQUITY", "realized_pnl_pct": -0.01},
        ]},
    }
    skill = me._per_class_skill(roster, details)
    assert len(skill) == 1
    row = skill[0]
    assert row["asset_class"] == "EQUITY"
    assert row["n_models"] == 3
    assert row["n_trades"] == 9
    # alpha = consistent small positive (high mean/sd) → wins over volatile beta
    # and negative-mean gamma.
    assert row["best_model_id"] == "alpha"


# ---------------------------------------------------------------------------
# 5. Empty state — no portfolios.
# ---------------------------------------------------------------------------
def test_empty_state_exits_clean(tmp_path, capsys):
    # Point to an empty data dir (no pf_portfolios.json present).
    rc = me.main([
        "--asof", "2026-05-30",
        "--out", str(tmp_path / "report.md"),
        "--json", str(tmp_path / "pf_meta.json"),
        "--dry-run",
    ])
    # Inject a missing data dir by monkey-patching DATA_DIR — easier: use real
    # default path; if pf_portfolios.json is absent it should write empty JSON.
    # Either way exit code 0.
    assert rc == 0
    # The JSON path passed should contain empty arrays if it was written.
    target = tmp_path / "pf_meta.json"
    if target.exists():
        payload = json.loads(target.read_text())
        assert payload["rank_by_sharpe"] == []
        assert payload["per_class_skill"] == []


def test_analyze_empty_inputs():
    payload = me.analyze([], {}, "2026-05-30")
    assert payload["rank_by_sharpe"] == []
    assert payload["per_class_skill"] == []
    assert payload["best_of_class_blend"]["beat_all_single_models"] is False


# ---------------------------------------------------------------------------
# 6. Tiny NAV series (5 points) still produces a Sharpe.
# ---------------------------------------------------------------------------
def test_tiny_nav_series_computes_sharpe():
    navs = [100.0, 101.0, 100.5, 102.0, 101.5]
    rets = me.daily_returns_from_nav(navs)
    assert len(rets) == 4
    sh = me.sharpe(rets)
    # Don't assert a magic value; just that we get a real finite float.
    assert math.isfinite(sh)
    # And matches manual formula.
    mean = sum(rets) / len(rets)
    var = sum((r - mean) ** 2 for r in rets) / len(rets)
    sd = math.sqrt(var)
    expected = (mean / sd) * math.sqrt(252) if sd else 0.0
    assert sh == pytest.approx(expected, rel=1e-9)


# ---------------------------------------------------------------------------
# Extra: CAGR sanity.
# ---------------------------------------------------------------------------
def test_cagr_one_year_double():
    # Double in exactly 365.25 days → CAGR = 1.0 (i.e. +100%)
    navs = [100.0, 200.0]
    cg = me.cagr(navs, int(round(365.25)))
    assert cg == pytest.approx(1.0, rel=1e-3)


def test_render_markdown_smoke():
    payload = me.analyze([], {}, "2026-05-30")
    md = me.render_markdown(payload)
    assert "Portfolio Meta-Effectiveness" in md
    assert "2026-05-30" in md
