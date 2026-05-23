# Enhanced DNA Engine v2.0 - Complete Guide

## Overview

The Enhanced DNA Engine expands the gene pool from ~10 basic parameters to **50+ data points** across 9 categories. This enables discovery of more sophisticated, multi-factor trading strategies.

## Gene Categories

### 1. Technical Genes (14 genes)
Traditional TA indicators with expanded parameter ranges.

| Gene | Options | Description |
|------|---------|-------------|
| `timeframe` | 1m to 1w | Candle timeframe |
| `ema_fast` | 5-50 | Fast EMA period |
| `ema_slow` | 20-200 | Slow EMA period |
| `rsi_period` | 7, 14, 21 | RSI lookback |
| `rsi_overbought` | 65-85 | RSI sell threshold |
| `rsi_oversold` | 15-35 | RSI buy threshold |
| `macd_fast/slow/signal` | Various | MACD parameters |
| `bb_period/std` | Various | Bollinger Bands |
| `atr_period` | 7-28 | ATR lookback |
| `volume_ma_period` | 10-100 | Volume smoothing |
| `adx_period/threshold` | Various | Trend strength |

### 2. On-Chain Genes (10 genes)
Blockchain metrics for crypto-specific alpha.

| Gene | Options | Description |
|------|---------|-------------|
| `exchange_flow_threshold` | ±500 to ±100 BTC | Exchange in/out flows |
| `whale_movement_min` | 100-5000 BTC | Whale wallet threshold |
| `nupl_threshold` | -0.5 to 0.75 | Net Unrealized Profit/Loss |
| `sopr_threshold` | 0.95-1.05 | Spent Output Profit Ratio |
| `active_addresses_change` | ±20% | Network growth |
| `miner_position_index` | -1 to 1 | Miner selling pressure |
| `long_term_holder_threshold` | 50-80% | HODLer concentration |
| `exchange_reserve_threshold` | ±10% | Exchange supply change |
| `cohort_age_threshold` | 30-365 days | Holder age bands |
| `realized_price_deviation` | ±30% | MVRV proxy |

### 3. Sentiment Genes (9 genes)
Crowd psychology and social metrics.

| Gene | Options | Description |
|------|---------|-------------|
| `fear_greed_threshold` | 10-90 | Crypto Fear & Greed Index |
| `social_volume_change` | ±50% | Social media mentions |
| `twitter_sentiment_min` | -0.8 to 0.8 | Twitter mood |
| `reddit_sentiment_min` | -0.8 to 0.8 | Reddit mood |
| `google_trends_change` | ±30% | Search interest |
| `news_sentiment_min` | -0.9 to 0.9 | News sentiment |
| `crowd_fear_threshold` | 20-80 | Extreme fear detection |
| `smart_money_confidence` | 0.3-0.9 | Smart money proxy |
| `contrarian_threshold` | 0.1-0.4 | Crowd consensus % |

### 4. Derivatives Genes (9 genes)
Futures market dynamics.

| Gene | Options | Description |
|------|---------|-------------|
| `funding_rate_threshold` | ±0.01 | Perp funding cost |
| `open_interest_change` | ±30% | OI momentum |
| `liquidation_threshold` | $100K-$5M | Liquidation volume |
| `premium_index_threshold` | ±0.5% | Perp premium |
| `predicted_funding_threshold` | ±0.02 | Expected funding |
| `perp_spot_basis_threshold` | ±1% | Cash-and-carry |
| `options_iv_change` | ±30% | Options volatility |
| `skew_threshold` | ±20 | Put/call skew |
| `term_structure_slope` | ±0.5 | Futures curve |

### 5. Microstructure Genes (9 genes)
Order book and flow analysis.

| Gene | Options | Description |
|------|---------|-------------|
| `orderbook_imbalance_threshold` | ±0.8 | Bid/ask imbalance |
| `bid_ask_spread_max` | 0.01-0.5% | Spread filter |
| `trade_flow_imbalance` | ±0.7 | Buy/sell pressure |
| `large_order_threshold` | $10K-$500K | Whale order size |
| `iceberg_detection_sensitivity` | 0.1-0.9 | Hidden order detection |
| `tick_poison_ratio` | 0.1-0.5 | Toxic flow ratio |
| `vpoc_threshold` | 0.1-0.3 | Volume point of control |
| `delta_threshold` | ±1M | Cumulative delta |
| `cvd_slope_threshold` | ±1000 | CVD momentum |

### 6. Cross-Asset Genes (10 genes)
Macro and intermarket relationships.

| Gene | Options | Description |
|------|---------|-------------|
| `btc_dominance_threshold` | 40-70% | BTC market share |
| `altcoin_season_index` | 20-100 | Alt strength |
| `eth_btc_ratio_threshold` | 0.03-0.08 | ETH/BTC valuation |
| `total_market_cap_change` | ±20% | Total crypto cap |
| `defi_tvl_change` | ±15% | DeFi growth |
| `stablecoin_inflow_threshold` | $10M-$500M | New money entering |
| `m2_correlation` | ±0.5 | Money supply correlation |
| `dxy_correlation` | ±0.8 | Dollar correlation |
| `spx_correlation` | ±0.5 | Stocks correlation |
| `gold_correlation` | ±0.3 | Gold correlation |

### 7. Temporal Genes (8 genes)
Time-based patterns.

| Gene | Options | Description |
|------|---------|-------------|
| `entry_hour_min/max` | 0-23 | Time window |
| `day_of_week_filter` | Mon-Sun/Weekday/etc | Day filter |
| `funding_time_offset` | -4 to +4h | Funding timing |
| `weekend_trading` | True/False | Weekend positions |
| `monthly_pattern` | Beginning/Middle/End | Month effects |
| `quarterly_rebalance` | True/False | Rebalance timing |
| `session_overlap_only` | NY/London/Asia | Best session |
| `halving_phase` | Pre/Post/etc | Cycle timing |

### 8. Risk Management Genes (10 genes)
Position sizing and risk controls.

| Gene | Options | Description |
|------|---------|-------------|
| `position_size` | 1-30% | Risk per trade |
| `max_positions` | 1-15 | Portfolio limit |
| `daily_loss_limit` | 1-10% | Circuit breaker |
| `kelly_fraction` | 0.1-1.0 | Kelly criterion % |
| `volatility_target` | 5-50% | Vol targeting |
| `correlation_limit` | 0.3-0.9 | Max correlation |
| `concentration_limit` | 0.1-0.5 | Max single position |
| `drawdown_circuit_breaker` | 5-30% | DD halt level |
| `trailing_stop_activation` | 0.5-3.0R | TS trigger |
| `breakeven_trigger` | 0.5-2.0R | BE trigger |

### 9. Fundamental Genes (6 genes)
Network and protocol metrics.

| Gene | Options | Description |
|------|---------|-------------|
| `valuation_metric` | NVT/MVRV/etc | Valuation model |
| `network_growth_threshold` | ±20% | Adoption rate |
| `developer_activity_min` | ±50% | GitHub activity |
| `protocol_revenue_change` | ±30% | Fee generation |
| `token_unlock_impact` | Ignore/Avoid/etc | Unlock filter |
| `governance_event_filter` | Pre/Post/etc | Vote timing |

## New Capabilities

### 1. Reverse Engineering
```python
python genome/reverse_engineer_today.py --analyze
```
Analyzes today's price action to find:
- What patterns would have won
- Optimal entry/exit timing
- Symbol-specific vs universal patterns

### 2. Universal Pattern Discovery
```python
python genome/universal_strategy_finder.py --run
```
Finds strategies that work across ALL symbols:
- Tests 20+ crypto pairs simultaneously
- Scores based on consistency
- Eliminates symbol-specific overfitting

### 3. Massive Evolution
```python
python genome/run_all_dna_variations.py
```
Runs full pipeline:
- Population: 1000-2000 strategies
- Generations: 50-200
- Gene combinations: 50+ data points
- Selection: Universal + reverse-engineered patterns

## Usage Examples

### Quick Analysis
```bash
python genome/run_all_dna_variations.py --quick
```
Fast mode with smaller population.

### Live Signals
```bash
python genome/universal_strategy_finder.py --live
```
Generate signals from best patterns.

### Discord Integration
```bash
python genome/discord_dna_enhanced.py --send
```
Send enhanced signals to Discord.

## Output Files

| File | Description |
|------|-------------|
| `genome/results/dna_master_output.json` | Aggregated results |
| `genome/results/reverse_engineered_today.json` | Today's patterns |
| `genome/results/universal_patterns.json` | Multi-symbol patterns |
| `genome/results/enhanced_evolution_v2.json` | Evolved strategies |
| `genome/results/live_signals_universal.json` | Live signals |

## Key Innovations

1. **50+ Gene Pool**: 5x increase in parameter space
2. **9 Categories**: Covers all aspects of market analysis
3. **Universal Patterns**: Works on any symbol, not just specific coins
4. **Reverse Engineering**: Learns from what would have worked
5. **Multi-Factor**: Combines on-chain + sentiment + technicals

## Performance Expectations

| Metric | Traditional DNA | Enhanced DNA |
|--------|-----------------|--------------|
| Gene Count | ~10 | 50+ |
| Symbol Coverage | 1-3 pairs | 20+ pairs |
| Win Rate (backtest) | 60-70% | 65-75% |
| Universal Score | N/A | 0.5-0.8 |
| Robustness | Low | High |

## Next Steps

1. Run `run_all_dna_variations.py` to generate patterns
2. Review results in `dna_master_output.json`
3. Deploy top patterns to paper trading
4. Monitor forward performance
5. Iterate on winning gene combinations
