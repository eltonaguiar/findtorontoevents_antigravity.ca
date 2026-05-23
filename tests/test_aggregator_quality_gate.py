import sys
from unittest.mock import MagicMock

# Stub incubator.testing to avoid pandas dependency
sys.modules.setdefault("incubator", MagicMock())
sys.modules.setdefault("incubator.testing", MagicMock())

from cross_aggregation.aggregator import passes_quality_gate

def test_demoted_strategy_filtered():
    """Strategies with COLLECTING status should be filtered from consensus."""
    result = passes_quality_gate("test_strat", forward_trades=3, forward_win_rate=0, forward_sharpe=0)
    assert result is False

def test_proven_strategy_passes():
    """PROVEN strategies should pass the quality gate."""
    result = passes_quality_gate("test_strat", forward_trades=30, forward_win_rate=62, forward_sharpe=1.5)
    assert result is True

def test_testing_strategy_passes():
    """TESTING status (minimum threshold) should pass."""
    result = passes_quality_gate("test_strat", forward_trades=15, forward_win_rate=52, forward_sharpe=0.6, forward_max_dd=-15, forward_pnl=5.0)
    assert result is True
