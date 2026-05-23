from empirical_bayes_scorer import EmpiricalBayesScorer


def test_score_pick_caps_net_loser_strategy():
    closed = []
    for _ in range(8):
        closed.append({"strategy": "loser", "symbol": "BTCUSDT", "direction": "LONG", "pnl_pct": -2.0})
    for _ in range(2):
        closed.append({"strategy": "loser", "symbol": "BTCUSDT", "direction": "LONG", "pnl_pct": 1.0})

    scorer = EmpiricalBayesScorer(closed)
    pick = {"strategy": "loser", "symbol": "BTCUSDT", "direction": "LONG", "asset_class": "CRYPTO", "score": 94}

    result = scorer.score_pick(pick)

    assert result["eb_net_loser_cap_applied"] is True
    assert result["enhanced_score"] == scorer.NET_LOSER_SCORE_CAP


def test_score_pick_does_not_cap_profitable_strategy():
    closed = []
    for _ in range(8):
        closed.append({"strategy": "winner", "symbol": "BTCUSDT", "direction": "LONG", "pnl_pct": 2.0})
    for _ in range(2):
        closed.append({"strategy": "winner", "symbol": "BTCUSDT", "direction": "LONG", "pnl_pct": -1.0})

    scorer = EmpiricalBayesScorer(closed)
    pick = {"strategy": "winner", "symbol": "BTCUSDT", "direction": "LONG", "asset_class": "CRYPTO", "score": 94}

    result = scorer.score_pick(pick)

    assert result["eb_net_loser_cap_applied"] is False
    assert result["enhanced_score"] > scorer.NET_LOSER_SCORE_CAP
