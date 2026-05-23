import pytest
from alpha_engine.options_volatility_strategies import OptionsVolatilityStrategy
from alpha_engine.defi_yield_farming import DeFiYieldFarmingStrategy
from alpha_engine.nft_momentum import NFTMomentumStrategy
from alpha_engine.news_sentiment_strategies import NewsSentimentStrategy
from alpha_engine.cross_chain_dex_arbitrage import CrossChainDEXArbitrageStrategy
from baby_strategies.rl_adaptive_strategy import RLAdaptiveStrategy
from crypto_portfolio_optimizer.optimizer import RiskParityOptimizer


def test_options_volatility():
    strat = OptionsVolatilityStrategy()
    signals = strat.generate_signals()
    assert len(signals) > 0, "Options strategy should generate signals with mock data"
    for sig in signals:
        assert sig["direction"] in ("LONG", "SHORT")
        assert sig["entry"] > 0
        assert "reason" in sig


def test_defi_yield_farming():
    strat = DeFiYieldFarmingStrategy()
    signals = strat.generate_signals()
    assert len(signals) > 0, "DeFi strategy should generate signals with mock data"
    for sig in signals:
        assert sig["direction"] == "LONG"  # yield farming is always long
        assert sig["tp"] > sig["entry"]


def test_nft_momentum():
    strat = NFTMomentumStrategy()
    signals = strat.generate_signals()
    assert len(signals) > 0, "NFT strategy should generate signals with mock data"
    for sig in signals:
        assert sig["direction"] == "LONG"
        assert "momentum" in sig["reason"].lower() or "breakout" in sig["reason"].lower()


def test_news_sentiment():
    strat = NewsSentimentStrategy()
    signals = strat.generate_signals()
    assert len(signals) > 0, "News sentiment should generate signals with mock data"
    for sig in signals:
        assert sig["direction"] in ("LONG", "SHORT")


def test_cross_chain_dex_arbitrage():
    # Override mock data with wider spreads to trigger signals
    wider_spreads = {
        "BTC": {"uniswap": 30000.0, "sushiswap": 29600.0, "pancake": 30200.0},
        "ETH": {"uniswap": 2000.0, "sushiswap": 1970.0, "pancake": 2050.0},
    }
    strat = CrossChainDEXArbitrageStrategy(context={"dex_prices": wider_spreads})
    signals = strat.generate_signals()
    assert len(signals) > 0, "Cross-chain arb should generate signals with wide spreads"
    for sig in signals:
        assert sig["direction"] == "LONG"
        assert "arb" in sig["reason"].lower() or "spread" in sig["reason"].lower()


def test_cross_chain_dex_arbitrage_no_spread():
    # Default mock data has <1% spreads — should generate no signals
    strat = CrossChainDEXArbitrageStrategy()
    signals = strat.generate_signals()
    assert len(signals) == 0, "No arb signals expected when spread < 1%"


def test_rl_adaptive():
    # RL requires model — returns 0 signals without model, which is correct
    strat = RLAdaptiveStrategy()
    signals = strat.generate_signals()
    assert signals is not None, "RL strategy should return a list (even if empty)"
    assert isinstance(signals, list)


def test_risk_parity_optimizer():
    from data_providers.crypto_data import get_vol_series
    optimizer = RiskParityOptimizer(vol_series=get_vol_series())
    weights = optimizer.compute_weights()
    assert len(weights) > 0
    total_weight = sum(weights.values())
    assert 0.95 < total_weight < 1.05, f"Weights should sum to ~1.0, got {total_weight}"
    # Verify inverse-vol property: lower vol = higher weight
    assert weights["BTC"] > weights["DOGE"], "BTC (lower vol) should have higher weight than DOGE"


if __name__ == "__main__":
    pytest.main(["-v", __file__])