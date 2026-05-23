"""HF conviction tiers S/A/B (dashboard extreme-conviction rules)."""

from alpha_engine.conviction_stack import (
    attach_hf_conviction_tiers_to_picks,
    classify_hf_conviction_tier,
    clear_conviction_tiers_cache_for_tests,
)


def _s_pick():
    return {
        "asset_class": "CRYPTO",
        "symbol": "DOTUSDT",
        "strategy": "st_fear_greed_contrarian",
        "direction": "LONG",
        "trust_tier": "PROVEN",
        "strat_fwd_wr": 60,
        "strat_fwd_trades": 40,
        "elite_score": 55,
        "btc_regime": "bull",
        "forward_wr": 0.60,
        "forward_trades": 40,
    }


def test_tier_s_core():
    tier, rs = classify_hf_conviction_tier(_s_pick())
    assert tier == "S"
    assert "tier_s" in rs[0]


def test_tier_s_fails_missing_regime():
    p = _s_pick()
    del p["btc_regime"]
    tier, _ = classify_hf_conviction_tier(p)
    assert tier is None


def test_tier_a_expanded_symbol_watch():
    p = {
        "asset_class": "CRYPTO",
        "symbol": "LINKUSDT",
        "strategy": "st_fear_greed_contrarian",
        "direction": "LONG",
        "trust_tier": "WATCH",
        "strat_fwd_wr": 58,
        "strat_fwd_trades": 12,
        "elite_score": 50,
        "regime_at_entry": "neutral",
    }
    tier, rs = classify_hf_conviction_tier(p)
    assert tier == "A"
    assert "watch" in rs[0]


def test_tier_b_major():
    p = {
        "asset_class": "CRYPTO",
        "symbol": "BTCUSDT",
        "strategy": "quan_engine_scalp",
        "direction": "LONG",
        "trust_tier": "PROVEN",
    }
    tier, rs = classify_hf_conviction_tier(p)
    assert tier == "B"
    assert "major" in rs[0]


def test_tier_a_alt_short_bear():
    p = {
        "asset_class": "CRYPTO",
        "symbol": "DOGEUSDT",
        "strategy": "short_only",
        "direction": "SHORT",
        "trust_tier": "PROVEN",
        "btc_regime": "bear",
        "strat_fwd_wr": 60,
        "strat_fwd_trades": 20,
        "forward_wr": 0.60,
        "forward_trades": 20,
    }
    tier, rs = classify_hf_conviction_tier(p)
    assert tier == "A"
    assert "short" in rs[0].lower() or "bear" in rs[0]


def test_attach_counts():
    clear_conviction_tiers_cache_for_tests()
    picks = [_s_pick(), {
        "symbol": "BTCUSDT", "asset_class": "CRYPTO", "direction": "LONG",
        "trust_tier": "PROVEN", "strat_fwd_wr": 60, "strat_fwd_trades": 20,
        "forward_wr": 0.60, "forward_trades": 20,
    }]
    c = attach_hf_conviction_tiers_to_picks(picks)
    assert c["S"] == 1
    assert c["B"] == 1


def test_non_crypto_tier_b_pead():
    clear_conviction_tiers_cache_for_tests()
    p = {
        "asset_class": "EQUITY",
        "symbol": "AAPL",
        "strategy": "pead_earnings_drift",
        "direction": "LONG",
        "confidence": 0.76,
        "strat_fwd_wr": 60,
        "strat_fwd_trades": 20,
        "forward_wr": 0.60,
        "forward_trades": 20,
    }
    tier, rs = classify_hf_conviction_tier(p)
    assert tier == "B"
    assert "non_crypto" in rs[0]


def test_non_crypto_tier_a_pead_regime():
    clear_conviction_tiers_cache_for_tests()
    p = {
        "asset_class": "EQUITY",
        "symbol": "MSFT",
        "strategy": "quality_value",
        "direction": "LONG",
        "confidence": 0.85,
        "regime_at_entry": "bull",
        "strat_fwd_wr": 60,
        "strat_fwd_trades": 20,
        "forward_wr": 0.60,
        "forward_trades": 20,
    }
    tier, rs = classify_hf_conviction_tier(p)
    assert tier == "A"
    assert "non_crypto" in rs[0]
