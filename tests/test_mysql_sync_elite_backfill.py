"""
Regression test for the elite_score backfill added to
alpha_engine/mysql_trading_sync.py::sync 2026-05-09.

Reference: reports/portfolio_lessons_2026-05-08.md — 92% of crypto picks
(3,128 of 3,394 in 14d) had elite_score=NULL because polymarket-derived
sources bypass elite_scorer in their own pipelines. Backfill at sync time
ensures every pick reaching trading_picks gets scored.
"""
from __future__ import annotations

import importlib

import pytest


@pytest.fixture
def polymarket_picks():
    """A spread of unscored picks from the 4 sources flagged in lessons doc."""
    return [
        {
            "id": "pm_whale_test",
            "symbol": "ENAUSDT", "direction": "LONG", "category": "crypto",
            "entry_price": 0.125, "take_profit": 0.130, "stop_loss": 0.120,
            "confidence": 0.62,
            "source_system": "polymarket_whale_tracker",
            "strategy": "pm_whale_test_strat",
            "created_at": "2026-05-09",
        },
        {
            "id": "pm_momentum_test",
            "symbol": "JUPUSDT", "direction": "LONG", "category": "crypto",
            "entry_price": 0.225, "take_profit": 0.240, "stop_loss": 0.215,
            "confidence": 0.58,
            "source_system": "polymarket_momentum",
            "strategy": "pm_momentum_test_strat",
            "created_at": "2026-05-09",
        },
        {
            "id": "pma_test",
            "symbol": "RENDERUSDT", "direction": "LONG", "category": "crypto",
            "entry_price": 2.0, "take_profit": 2.10, "stop_loss": 1.95,
            "confidence": 0.65,
            "source_system": "prediction_market_agents",
            "strategy": "pma_test_strat",
            "created_at": "2026-05-09",
        },
        {
            "id": "ct_pm_test",
            "symbol": "ADAUSDT", "direction": "LONG", "category": "crypto",
            "entry_price": 0.27, "take_profit": 0.28, "stop_loss": 0.265,
            "confidence": 0.60,
            "source_system": "copy_trader_polymarket",
            "strategy": "ct_pm_test_strat",
            "created_at": "2026-05-09",
        },
    ]


def test_enrich_picks_assigns_elite_score(polymarket_picks):
    from alpha_engine.elite_scorer import enrich_picks_with_elite_score
    res = enrich_picks_with_elite_score(polymarket_picks)
    for p in res:
        assert p.get("elite_score") is not None, f"{p['id']} unscored"
        assert isinstance(p["elite_score"], (int, float))
        assert 0 <= p["elite_score"] <= 200  # ml_composite scale up to ~183
        assert p.get("elite_grade") in ("S", "A", "B", "C", "D", "F")


def test_enrich_idempotent_on_already_scored(polymarket_picks):
    """Running enrichment twice doesn't re-randomize scores."""
    from alpha_engine.elite_scorer import enrich_picks_with_elite_score
    enrich_picks_with_elite_score(polymarket_picks)
    first = [p["elite_score"] for p in polymarket_picks]
    enrich_picks_with_elite_score(polymarket_picks)
    second = [p["elite_score"] for p in polymarket_picks]
    assert first == second, "elite_score not deterministic across runs"


def test_short_dominant_engine_pick_also_scored():
    """short_dominant_engine generated 485 picks in 14d, all unscored.
    Backfill should assign them too."""
    from alpha_engine.elite_scorer import enrich_picks_with_elite_score
    picks = [{
        "id": "sde_test",
        "symbol": "TONUSDT", "direction": "SHORT", "category": "crypto",
        "entry_price": 2.50, "take_profit": 2.40, "stop_loss": 2.55,
        "confidence": 0.55,
        "source_system": "short_dominant_engine",
        "strategy": "short_dominant_engine",
        "created_at": "2026-05-09",
    }]
    res = enrich_picks_with_elite_score(picks)
    assert res[0].get("elite_score") is not None


def test_picks_missing_tp_sl_get_defaults(polymarket_picks):
    """Picks with no TP/SL should still get scored after default-fill."""
    from alpha_engine.elite_scorer import enrich_picks_with_elite_score
    bare_pick = {
        "id": "bare_test",
        "symbol": "INJUSDT", "direction": "LONG", "category": "crypto",
        "entry_price": 4.0,
        "confidence": 0.65,
        "source_system": "polymarket_whale_tracker",
        "strategy": "bare_test",
        "created_at": "2026-05-09",
    }
    res = enrich_picks_with_elite_score([bare_pick])
    assert res[0].get("elite_score") is not None
    assert res[0].get("take_profit") is not None  # default applied
    assert res[0].get("stop_loss") is not None
    assert res[0].get("_tp_default") is True
    assert res[0].get("_sl_default") is True


def test_sync_module_imports_elite_scorer_path():
    """Smoke: mysql_trading_sync.sync() can resolve the elite_scorer import."""
    sync_mod = importlib.import_module("alpha_engine.mysql_trading_sync")
    assert hasattr(sync_mod, "sync")
    # Confirm import path is reachable from this module's context.
    from alpha_engine.elite_scorer import enrich_picks_with_elite_score
    assert callable(enrich_picks_with_elite_score)
