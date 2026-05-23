"""Tests for cftc_cot_commercial_signal retirement (Finding #4 of 48h code review).

Verifies the strategy is blocked by strategy_blocklist after being added to
_RETIRED_STRATEGIES on 2026-05-02. Empirical evidence documented in:
  - PR #542: 27/27 closed rows on COMMODITY_BLACKLIST symbols
  - updates/2026-05-02-48h-code-review.md Finding #4
"""

import pytest
from alpha_engine.strategy_blocklist import (
    is_blocked_pick,
    is_blocked_strategy,
    block_reason,
)


def test_cftc_cot_commercial_signal_is_retired():
    """Strategy must be blocked at the name level."""
    assert is_blocked_strategy("cftc_cot_commercial_signal") is True


def test_cftc_cot_block_reason_is_retired():
    """Reason must be 'retired' (not 'paper-only')."""
    assert block_reason("cftc_cot_commercial_signal") == "retired"


def test_cftc_cot_pick_is_blocked():
    """A pick dict with this strategy must be blocked."""
    pick = {
        "strategy": "cftc_cot_commercial_signal",
        "source_system": "multi_asset",
        "symbol": "CT=F",
        "asset_class": "COMMODITY",
    }
    assert is_blocked_pick(pick) is True


def test_cftc_cot_pick_with_different_source_still_blocked():
    """Retirement is strategy-level, not composite — any source blocked."""
    pick = {
        "strategy": "cftc_cot_commercial_signal",
        "source_system": "alpha_engine",
        "symbol": "CL=F",
    }
    assert is_blocked_pick(pick) is True
