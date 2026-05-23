"""Regression test for BLACKLISTED_STRATEGIES enforcement.

Locks in PR #740 (commit 73d49c3fd78) which closed the blacklist bypass
that admitted 3,517 quan_engine_scalp picks (sum PnL -600.3% / 32.7% WR)
between 2026-04-03 and 2026-04-25 because the blacklist was only enforced
in copy_trader_bridge.py:192 and not at the main pick-intake gate
(smart_picks_engine.score_pick) or resolution layer
(outcome_resolver.resolve_single_pick).

See reports/HEDGE_FUND_PR_MERGE_AUDIT_2026_05_03.md section 5.
"""
from __future__ import annotations

import pytest

from alpha_engine.config import BLACKLISTED_STRATEGIES
from alpha_engine.outcome_resolver import resolve_single_pick
from alpha_engine.smart_picks_engine import score_pick


def _blacklisted_pick(strategy: str = "quan_engine_scalp") -> dict:
    return {
        "id": "test-blacklist-1",
        "symbol": "BTCUSDT",
        "direction": "LONG",
        "strategy": strategy,
        "source": strategy,
        "entry_price": 100.0,
        "take_profit": 105.0,
        "stop_loss": 98.0,
        "score": 80,
        "elite_score": 80,
        "confidence": 0.9,
        "asset_class": "CRYPTO",
    }


def test_blacklist_constant_contains_quan_engine_scalp():
    assert "quan_engine_scalp" in BLACKLISTED_STRATEGIES, (
        "quan_engine_scalp must remain blacklisted (0% WR / -794% PnL zombie). "
        "Removing this entry requires a new investigation per "
        "docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md."
    )


@pytest.mark.parametrize("strat", list(BLACKLISTED_STRATEGIES))
def test_score_pick_rejects_blacklisted_strategies(strat):
    """smart_picks_engine.score_pick must filter blacklisted strategies BEFORE
    scoring. Returns a dict whose `_filter` key marks the rejection reason.
    """
    pick = _blacklisted_pick(strategy=strat)
    result = score_pick(
        pick,
        live_price=100.0,
        regime_data={},
        now=None,
        fear_greed=50,
    )
    assert isinstance(result, dict), f"score_pick should return dict, got {type(result)}"
    assert result.get("_filter") == "blacklisted_strategy", (
        f"Pick with strategy={strat!r} must be rejected with "
        f"_filter=blacklisted_strategy, got {result.get('_filter')!r}"
    )


@pytest.mark.parametrize("strat", list(BLACKLISTED_STRATEGIES))
def test_resolve_single_pick_neutralizes_blacklisted_strategies(strat):
    """outcome_resolver.resolve_single_pick must short-circuit before
    PF/WR-impacting resolution and tag exit_reason=BLACKLISTED + pnl_pct=0.0
    so the pick is forensic-visible but does not contaminate aggregates.
    """
    pick = _blacklisted_pick(strategy=strat)
    out = resolve_single_pick(pick, live_price=110.0)
    assert out["status"] == "CLOSED"
    assert out["exit_reason"] == "BLACKLISTED"
    assert out["pnl_pct"] == 0.0
    assert "_blacklist_reason" in out
    assert strat.lower() in out["_blacklist_reason"].lower()


def test_score_pick_allows_non_blacklisted_strategy():
    """Negative control — a non-blacklisted strategy must NOT trip the
    blacklist filter (it may be filtered by other gates, but not this one).
    """
    pick = _blacklisted_pick(strategy="dna_winner")
    result = score_pick(
        pick,
        live_price=100.0,
        regime_data={},
        now=None,
        fear_greed=50,
    )
    # If filtered, must be for some OTHER reason than blacklist
    if isinstance(result, dict) and "_filter" in result:
        assert result["_filter"] != "blacklisted_strategy"


def test_resolve_single_pick_allows_non_blacklisted_strategy():
    """Negative control — non-blacklisted picks fall through to normal
    resolution (we don't assert their exit_reason since that depends on
    price walk; we only assert the BLACKLISTED tag is absent).
    """
    pick = _blacklisted_pick(strategy="dna_winner")
    out = resolve_single_pick(pick, live_price=110.0)
    assert out.get("exit_reason") != "BLACKLISTED"
    assert "_blacklist_reason" not in out
