from audit_trail.empirical_bayes_scorer import EmpiricalBayesScorer
from audit_trail.forward_test_gates import GateFilter
from audit_trail.non_crypto_smart_score import calculate_non_crypto_smart_score as ncss


def test_empirical_bayes_matches_algorithm_field():
    """Forward-test rows use `algorithm`; scorer must bucket like `strategy`."""
    trades = [{"algorithm": "Classic Momentum", "symbol": "AAPL", "direction": "LONG", "pnl_pct": 2.0}] * 8
    trades += [{"algorithm": "Classic Momentum", "symbol": "AAPL", "direction": "LONG", "pnl_pct": -1.0}] * 2
    eb = EmpiricalBayesScorer(trades)
    r = eb.win_prob("AAPL", "Classic Momentum", "LONG", "CRYPTO")
    assert r["win_prob"] > 0.5


def test_empirical_bayes_hierarchy():
    trades = []
    for _ in range(12):
        trades.append(
            {
                "strategy": "s1",
                "symbol": "AAA",
                "direction": "LONG",
                "asset_class": "CRYPTO",
                "pnl_pct": 1.0,
            }
        )
    trades.append(
        {"strategy": "s1", "symbol": "AAA", "direction": "LONG", "asset_class": "CRYPTO", "pnl_pct": -1.0}
    )
    eb = EmpiricalBayesScorer(trades)
    r = eb.win_prob("AAA", "s1", "LONG", "CRYPTO")
    assert r["win_prob"] > 0.5
    assert r["tier"] in ("SYMBOL_STRATEGY_DIRECTION", "SYMBOL_STRATEGY", "STRATEGY")


def test_empirical_bayes_caps_net_loser_enhanced_score():
    trades = [{"strategy": "loser", "symbol": "BTCUSDT", "direction": "LONG", "asset_class": "CRYPTO", "pnl_pct": 1.0}] * 6
    trades += [{"strategy": "loser", "symbol": "BTCUSDT", "direction": "LONG", "asset_class": "CRYPTO", "pnl_pct": -3.0}] * 6
    eb = EmpiricalBayesScorer(trades)
    scored = eb.score_pick({"strategy": "loser", "symbol": "BTCUSDT", "direction": "LONG", "asset_class": "CRYPTO", "score": 94})
    assert scored["eb_net_loser_cap_applied"] is True
    assert scored["enhanced_score"] <= 59.9


def test_gate_filter_blocks_ml():
    closed = [{"strategy": "x", "symbol": "BTCUSDT", "pnl_pct": 1.0}] * 10
    g = GateFilter(closed, [])
    ok, reason = g.should_take_trade(
        {
            "strategy": "x",
            "symbol": "ETHUSDT",
            "direction": "LONG",
            "entry": 3000,
            "tp": 3300,
            "sl": 2900,
            "ml_score": 0.2,
            "asset_class": "CRYPTO",
        }
    )
    assert not ok and "kill_zone" in reason


def test_non_crypto_smart_score_shape():
    r = ncss(
        {"symbol": "AAPL", "direction": "LONG", "elite_score": 60, "age_hours": 2, "entry": 100, "tp": 110},
        vix_regime="PARTLY_CLOUDY",
        days_to_earnings=20,
        sector_momentum_20d=2.0,
        daily_aligned=True,
        weekly_aligned=True,
    )
    assert 0 <= r["smart_score"] <= 100
