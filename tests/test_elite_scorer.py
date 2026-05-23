from alpha_engine.elite_scorer import compute_elite_score


def test_compute_elite_score_handles_multi_asset_copy_pick_without_name_error() -> None:
    pick = {
        "id": "multi_asset_futures_momentum::SI=F::2026-04-08_2321",
        "strategy": "futures_momentum",
        "symbol": "SI=F",
        "category": "commodity",
        "direction": "SHORT",
        "entry_price": 73.754997,
        "take_profit": 70.067247,
        "stop_loss": 75.967647,
        "confidence": 0.75,
        "ml_score": 0.75,
        "risk_reward": 1.67,
        "status": "OPEN",
        "source_system": "multi_asset_copytrader",
        "forward_test_only": True,
        "asset_class": "FUTURES",
        "forward_trades": 0,
        "forward_wr": 0.0,
    }

    result = compute_elite_score(pick, monte_carlo_results={}, strategy_perf={}, copy_trader_scorebook={})

    assert "elite_score" in result
    assert isinstance(result["elite_breakdown"], dict)


def test_compute_elite_score_applies_non_crypto_boost_for_forex():
    """CLAUDE_DEBUGGING_GUIDE.MD Part 6: non_crypto_boosters must be wired into elite scoring."""
    from alpha_engine.elite_scorer import compute_elite_score

    forex_pick = {
        "symbol": "EURUSD=X",
        "direction": "LONG",
        "asset_class": "FOREX",
        "strategy": "forex_session_momentum",
        "confidence": 0.65,
        "entry_price": 1.0850,
        "take_profit": 1.0920,
        "stop_loss": 1.0815,
    }
    result = compute_elite_score(forex_pick)
    breakdown = result["elite_breakdown"]
    # Booster registers the key whenever the pick reaches a non-crypto branch,
    # even if the resulting boost is 0 (e.g. exotic session); the wire-up
    # contract is "key is recorded for non-crypto picks".
    assert "non_crypto_boost" in breakdown, "non_crypto_boost must be recorded for FOREX picks"
    assert breakdown["non_crypto_boost"] >= 0


def test_compute_elite_score_no_boost_for_crypto():
    """Crypto picks must not receive the non-crypto boost (no behavior change)."""
    from alpha_engine.elite_scorer import compute_elite_score

    crypto_pick = {
        "symbol": "BTCUSDT",
        "direction": "LONG",
        "asset_class": "CRYPTO",
        "strategy": "fear_greed_contrarian",
        "confidence": 0.65,
        "entry_price": 84000,
        "take_profit": 88000,
        "stop_loss": 82000,
    }
    result = compute_elite_score(crypto_pick)
    breakdown = result["elite_breakdown"]
    # compute_non_crypto_boost returns (0, {"_non_crypto_boost": "skipped_crypto"})
    # for CRYPTO. The wire only adds the "non_crypto_boost" key when the boost
    # is truthy, so the key must be absent for crypto.
    assert "non_crypto_boost" not in breakdown, (
        "CRYPTO must not get a non_crypto_boost (it already has MTF + ensemble boosters)"
    )
