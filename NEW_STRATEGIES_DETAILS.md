# Detailed Strategy Implementations

## 1. Options Volatility Strategies (`alpha_engine/options_volatility_strategies.py`)
- Implements a simple high‑IV straddle sell when IV > 80%.
- Uses `context['iv_surface']` and `context['spot_price']`.
- Returns a signal dict with `symbol`, `direction`, `entry`, `tp`, `sl`, `size`, `reason`.

## 2. DeFi Yield‑Farming & Staking (`alpha_engine/defi_yield_farming.py`)
- Reads `context['defi_pools']` containing `apy`, `price`, `momentum`.
- Filters pools with `apy > 15%` and `momentum > 0.5%`.
- Generates long signals with 10% TP and 5% SL.

## 3. Cross‑Chain DEX Arbitrage (`alpha_engine/cross_chain_dex_arbitrage.py`)
- Expects `context['dex_prices']` mapping symbols to per‑DEX prices.
- Finds max‑min spread > 1% and creates a short‑straddle‑style signal.

## 4. NFT Momentum (`alpha_engine/nft_momentum.py`)
- Uses `context['nft_data']` with `floor`, `volume`, `momentum`.
- Emits long signals when momentum > 1% and volume > 1000.

## 5. News Sentiment (`alpha_engine/news_sentiment_strategies.py`)
- Consumes `context['sentiment_scores']` (positive = bullish, negative = bearish).
- Generates long/short signals with 5% TP/SL.

## 6. Reinforcement‑Learning Adaptive Trader
- **Production Scanner** (`rl_agent/production_scanner.py`)
  - Loads a PPO model (`rl_agent/model/ppo_latest.pt`).
  - Builds an observation from `spot_price`, `volume`, `momentum`.
  - Calls `agent.act(obs)` and translates actions into standard signal dicts.
- **Baby Wrapper** (`baby_strategies/rl_adaptive_strategy.py`)
  - Instantiates `RLProductionScanner` and forwards `generate_signals()`.

## 7. Risk‑Parity Portfolio Optimizer (`crypto_portfolio_optimizer/optimizer.py`)
- Simple inverse‑volatility weighting.
- `compute_weights()` returns a `{symbol: weight}` dict.

## Integration
- All new classes follow the platform’s `generate_signals()` API and can be imported by the main scanners (`alpha_engine/scanner.py`, `coinglass_strategies/scanner.py`).
- Add the new class names to `alpha_engine/__init__.py` if they need to be part of the `ALL_STRATEGIES` list.

## Documentation Links
- Architecture overview: [`NEW_STRATEGIES_ARCHITECTURE.md`](NEW_STRATEGIES_ARCHITECTURE.md:1)
- Summary of changes: [`chatwithit.md`](chatwithit.md:1)
