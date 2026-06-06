"""Regression: tournament horizon labels must map to swarm_pick_schema timeframes."""
from tools.swarm.promote_tournament_picks import normalize_timeframe


def test_normalize_tournament_horizons():
    assert normalize_timeframe("14d") == "1M"
    assert normalize_timeframe("7d") == "1W"
    assert normalize_timeframe("30d") == "1M"
    assert normalize_timeframe("60d") == "3M"
    assert normalize_timeframe("equity_default") == "1D"
    assert normalize_timeframe("4H") == "4H"
    assert normalize_timeframe("") == "4H"