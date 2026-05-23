# New Strategy Architecture

This document outlines the newly‑added strategy modules and their integration points within the existing codebase.

## Modules Added
| Module | Location | Purpose |
|--------|----------|---------|
| **Options Volatility Strategies** | `alpha_engine/options_volatility_strategies.py` | Implements straddles, strangles, delta‑neutral spreads, and volatility‑decay harvesting using IV surfaces and options chain data. |
| **DeFi Yield‑Farming & Staking** | `alpha_engine/defi_yield_farming.py` | Systematic allocation to liquidity‑mining pools, staking rewards, and protocol‑specific yield optimization. |
| **Cross‑Chain DEX Arbitrage** | `alpha_engine/cross_chain_dex_arbitrage.py` | Arbitrage across multiple DEXs (Uniswap, SushiSwap, PancakeSwap) and blockchains, leveraging price differences. |
| **NFT Momentum** | `alpha_engine/nft_momentum.py` | Momentum / mean‑reversion models for high‑value NFT collections and metaverse tokens. |
| **News‑Sentiment Strategies** | `alpha_engine/news_sentiment_strategies.py` | Real‑time parsing of crypto‑related news, regulatory announcements, and social‑media sentiment to generate signals. |
| **RL Adaptive Trader – Production Scanner** | `rl_agent/production_scanner.py` | Thin wrapper that runs the trained PPO agent and outputs signals via the standard `generate_signals()` interface. |
| **RL Adaptive Trader – Baby Wrapper** | `baby_strategies/rl_adaptive_strategy.py` | Exposes the RL agent as a baby strategy with `generate_signals()` for the bundle system. |
| **Crypto Risk‑Parity Optimizer** | `crypto_portfolio_optimizer/optimizer.py` | Portfolio‑level risk‑parity allocation across crypto assets, used by bundle‑optimized portfolios. |
| **Futures Calendar‑Spread** | `coinglass_strategies/strategies/calendar_spread.py` | Generates calendar‑spread signals using Binance futures 15‑min data (near‑month vs far‑month). |
| **Roll‑Yield Strategy** | `coinglass_strategies/strategies/roll_yield.py` | Captures roll‑yield opportunities from term‑structure differences in futures contracts. |

## Integration Points
- All **alpha_engine** modules are automatically imported by `alpha_engine/scanner.py` which builds the `ALL_STRATEGIES` list. Add the new class names to `alpha_engine/__init__.py` if needed.
- The **RL** scanner (`rl_agent/production_scanner.py`) is referenced by `baby_strategies/rl_adaptive_strategy.py` and then appears in the baby‑strategy inventory.
- **Coinglass** strategies are loaded by `coinglass_strategies/scanner.py`; the new `calendar_spread.py` and `roll_yield.py` follow the same pattern as existing strategies.
- The **risk‑parity optimizer** can be called from `baby_strategies/bundle_optimized/` to rebalance bundles before execution.

## Usage Example
```python
from alpha_engine.options_volatility_strategies import OptionsVolatilityStrategy
from alpha_engine.defi_yield_farming import DeFiYieldFarmingStrategy

# In the main scanner loop
signals = []
signals += OptionsVolatilityStrategy().generate_signals()
signals += DeFiYieldFarmingStrategy().generate_signals()
```

Each module implements a class with a `generate_signals()` method that returns a list of dictionaries matching the platform’s signal schema.
