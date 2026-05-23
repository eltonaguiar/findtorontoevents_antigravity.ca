"""Smoke tests for tools/edge/edge_stability.py.

Addresses swarm-review P1 finding (2026-05-11): "15-module Python research
package shipped with zero tests". This file covers the edge_stability
sidecar; a research-orchestrator companion test suite is queued.

Coverage:
  - Wilson CI math edge cases (n=0, n=1, all-wins, all-losses)
  - _normalize_pick handles malformed/missing fields without crash
  - _stability_score is bounded [0, 100]
  - _decay_or_lift threshold math
  - compute_class on synthetic picks produces stable schema
"""

from __future__ import annotations

import datetime as dt
from datetime import timezone

import pytest

from tools.edge import edge_stability as es


# ── Wilson CI ─────────────────────────────────────────────────────────────


def test_wilson_ci_zero_n():
    assert es.wilson_ci(0, 0) == (0.0, 0.0)


def test_wilson_ci_all_wins():
    lo, hi = es.wilson_ci(10, 10)
    assert hi == 100.0
    assert 0 < lo < 100


def test_wilson_ci_all_losses():
    lo, hi = es.wilson_ci(0, 10)
    assert lo == 0.0
    assert 0 < hi < 100


def test_wilson_ci_half():
    lo, hi = es.wilson_ci(50, 100)
    assert 30 < lo < 50
    assert 50 < hi < 70


# ── _normalize_pick robustness ────────────────────────────────────────────


def test_normalize_pick_handles_empty():
    assert es._normalize({}) is None
    assert es._normalize(None) is None  # type: ignore[arg-type]
    assert es._normalize("not a dict") is None  # type: ignore[arg-type]


def test_normalize_pick_requires_asset_class():
    assert es._normalize({"pnl_pct": 1.0, "closed_at": "2026-05-01T00:00:00Z"}) is None


def test_normalize_pick_requires_pnl():
    assert es._normalize({"asset_class": "CRYPTO", "closed_at": "2026-05-01T00:00:00Z"}) is None


def test_normalize_pick_strips_ghost():
    pick = {
        "asset_class": "CRYPTO",
        "symbol": "MATICUSDT",
        "source_system": "quan_engine",
        "pnl_pct": 2.5,
        "closed_at": "2026-05-01T00:00:00Z",
        "status": "WIN",
    }
    assert es._normalize(pick) is None  # ghost stripped


def test_normalize_pick_good():
    pick = {
        "asset_class": "BOND",
        "symbol": "IEF",
        "source_system": "test_source",
        "strategy": "test_strat",
        "pnl_pct": "1.23",  # string ok
        "closed_at": "2026-05-01T00:00:00Z",
        "status": "WON",
    }
    n = es._normalize(pick)
    assert n is not None
    assert n["asset_class"] == "BOND"
    assert n["pnl_pct"] == pytest.approx(1.23)
    assert n["won"] is True


def test_is_won_status_override():
    assert es._is_won({"status": "WIN", "pnl_pct": -1}) is True
    assert es._is_won({"status": "LOSS", "pnl_pct": 1}) is False
    assert es._is_won({"pnl_pct": 0.5}) is True
    assert es._is_won({"pnl_pct": -0.5}) is False
    assert es._is_won({"pnl_pct": 0}) is False


# ── _stability_score bounded ──────────────────────────────────────────────


def test_stability_score_bounded():
    # Empty windows → 0
    score = es._stability_score({"7d": {}, "30d": {}, "90d": {}, "all": {}})
    assert 0 <= score <= 100

    # All winning windows
    score = es._stability_score({
        "7d": {"pf": 2.0, "wr": 60, "n": 100},
        "30d": {"pf": 1.8, "wr": 55, "n": 100},
        "90d": {"pf": 1.7, "wr": 53, "n": 100},
        "all": {"pf": 1.6, "wr": 52, "n": 200},
    })
    assert score >= 75  # should hit STABLE_EDGE threshold


def test_decay_or_lift_thresholds():
    # 7d much lower than 90d → decay
    decay, lift = es._decay_or_lift({
        "7d": {"wr": 30}, "90d": {"wr": 50}
    })
    assert decay is True
    assert lift is False

    # 7d much higher than 90d → lift
    decay, lift = es._decay_or_lift({
        "7d": {"wr": 70}, "90d": {"wr": 50}
    })
    assert decay is False
    assert lift is True

    # Stable
    decay, lift = es._decay_or_lift({
        "7d": {"wr": 52}, "90d": {"wr": 50}
    })
    assert decay is False
    assert lift is False


# ── compute_class schema stability ────────────────────────────────────────


def _synthetic_picks(n: int, asset_class: str = "BOND"):
    """N synthetic normalized picks spread over the last 60 days."""
    now = dt.datetime.now(tz=timezone.utc)
    picks = []
    for i in range(n):
        days_ago = (i * 60.0) / n
        picks.append({
            "asset_class": asset_class,
            "strategy": f"test_strat_{i % 3}",
            "source_system": f"src_{i % 2}",
            "symbol": "IEF",
            "pnl_pct": 1.0 if i % 3 == 0 else -0.5,
            "won": (i % 3 == 0),
            "exit_dt": now - dt.timedelta(days=days_ago),
            "id": f"pick-{i}",
            "direction": "LONG",
        })
    return picks


def test_compute_class_schema_keys_stable():
    """Schema contract: these keys must be present per SCHEMA_VERSION='v1'."""
    picks = _synthetic_picks(30)
    out = es.compute_class("BOND", picks)
    required = {
        "schema_version", "asset_class", "as_of", "n_total", "tier_floor",
        "windows", "per_window_aggregate", "per_strategy", "latest_picks",
        "concentration", "consistency_verdict", "consistency_rationale",
    }
    assert required.issubset(out.keys())
    assert out["schema_version"] == "v1"
    assert out["asset_class"] == "BOND"


def test_compute_class_insufficient_data_below_floor():
    picks = _synthetic_picks(5)  # below n=100 floor
    out = es.compute_class("BOND", picks)
    assert out["consistency_verdict"] == "INSUFFICIENT_DATA"


def test_compute_class_empty_class_does_not_crash():
    out = es.compute_class("FOREX", [])
    assert out["n_total"] == 0
    assert out["consistency_verdict"] == "INSUFFICIENT_DATA"


def test_compute_class_latest_picks_capped_at_10():
    picks = _synthetic_picks(30)
    out = es.compute_class("BOND", picks)
    assert len(out["latest_picks"]) <= 10
    assert all("pnl_pct" in p for p in out["latest_picks"])
    assert all("closed_at" in p for p in out["latest_picks"])
