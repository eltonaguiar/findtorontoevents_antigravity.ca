# Strategy Gap Analysis: Kimi Research vs Our Systems
## Generated 2026-03-15

Cross-referencing 8 strategies from Kimi's `advanced_strategies.md` and the `executive_summary.md` against our existing codebase (Alpha Engine, KIMI ROTC, ML Battleground, Genome, etc.).

---

## Strategies We HAVE (Match the Research)

### 1. Funding Rate Arbitrage
- **Research:** Strategy 3 -- 85% WR, Sharpe 2.1, 15-25% annual
- **Our implementation:**
  - `alpha_engine/onchain_strategies.py` -- `funding_rate_arbitrage` (long spot + short perps, 19-115% annual documented)
  - `alpha_engine/crypto_strategies.py` -- `funding_rate_carry`
  - `alpha_engine/cerebrus_strategies.py` -- funding rate variant
- **Status:** FULLY COVERED. We have multiple implementations including the carry trade variant.

### 2. Mean Reversion with Bollinger Bands
- **Research:** Strategy 4 -- 64% WR, Sharpe 1.9, BB + RSI oversold/overbought
- **Our implementation:**
  - `alpha_engine/statistical_strategies.py` -- Bollinger squeeze / mean reversion
  - `alpha_engine/batch2_strategies.py` -- mean reversion variant
  - `alpha_engine/survivor_strategies.py` -- mean reversion survivor
  - `KIMI_RISEOFTHECLAW/proven_mean_reversion.py` -- dedicated module
  - `KIMI_RISEOFTHECLAW/alpha_research_engine.py` -- mean reversion component
- **Status:** FULLY COVERED with multiple approaches.

### 3. Multi-Timeframe Trend Following
- **Research:** Strategy 6 -- 58% WR, Sharpe 1.35, weekly/daily/4H/1H EMA alignment
- **Our implementation:**
  - `alpha_engine/crypto_strategies.py` -- `multi_timeframe_ema_stack` (EMA 9/21/50/200 aligned, 65-72% WR)
  - `ml_battleground/system_a_filter/strategies.py` -- multi-timeframe variant
  - `multi_asset/scanner.py` -- MTF trend component
- **Status:** FULLY COVERED. Our EMA stack is actually more granular (4 EMAs vs research's 2).

### 4. Whale Tracking / Accumulation
- **Research:** Strategy 8 -- 62% WR, exchange flow + large TX monitoring
- **Our implementation:**
  - `alpha_engine/crypto_strategies.py` -- `whale_accumulation_detector` (5x vol + bullish in downtrend, 58-65% WR)
  - `alpha_engine/exchange_flow_strategies.py` -- dedicated exchange flow module
  - `alpha_engine/onchain_strategies.py` -- `exchange_netflow` / `stablecoin_buying_power`
  - `KIMI_RISEOFTHECLAW/crypto_acceleration_engine.py` -- whale signal injection (`__order_book__`)
- **Status:** FULLY COVERED. We track both on-chain flows and volume-based whale detection.

### 5. On-Chain Analytics (MVRV, NUPL, SOPR, Exchange Flows)
- **Research:** Executive summary Section 4 -- MVRV Z-Score, NUPL, SOPR, exchange flows
- **Our implementation:**
  - `alpha_engine/onchain_strategies.py` -- `mvrv_sma_proxy`, `sopr_dip_buy_proxy`, `nvt_overvaluation`, `onchain_composite_score`
  - `onchain_metrics_agent.py` -- dedicated on-chain metrics
  - `cross_aggregation/enhanced_data_feeds.py` -- NUPL/MVRV/SOPR feeds
  - `genome/onchain_data.py` -- on-chain data for genome system
- **Status:** FULLY COVERED. We have 10+ on-chain strategies across multiple systems.

### 6. Sentiment / Fear & Greed Contrarian
- **Research:** Executive summary Section 6 -- F&G extremes as contrarian signals
- **Our implementation:**
  - `alpha_engine/onchain_strategies.py` -- `fear_greed_extreme_dca` (F&G <= 10 multi-day DCA, 14.6% annual)
  - `alpha_engine/crypto_strategies.py` -- fear/greed component
  - `baby_strategies/contrarian_fg_tiered.py` -- tiered contrarian F&G
  - `incubator/agents/web_ai/fear_greed_reversion.py` -- F&G reversion agent
- **Status:** FULLY COVERED with multiple approaches including tiered DCA.

### 7. ML Signal Filtering
- **Research:** Executive summary Section 3 -- XGBoost ensemble, 67% accuracy, filter low-quality trades
- **Our implementation:**
  - `KIMI_RISEOFTHECLAW/ml_signal_ranker.py` -- heuristic mode, RF auto-trains at >= 50 closed picks
  - `ml_battleground/` -- entire system dedicated to ML model competition
  - `ml_crypto_predictor/` -- production ML predictor
  - `ml_ranker_fixed.py` -- ML ranking
- **Status:** FULLY COVERED. We actually go beyond the research with a multi-system ML battleground.

### 8. News/Event-Based Trading
- **Research:** Strategy 7 -- 55% WR, Sharpe 1.8, CPI/Fed/ETF event trading
- **Our implementation:**
  - `alpha_engine/event_strategies.py` -- 8 event-driven strategies
  - `alpha_engine/news_sentiment_strategies.py` -- news sentiment module
  - `alpha_engine/opposite_day_strategies.py` -- news-based contrarian
  - `coinglass_strategies/strategies/news_sentiment.py` -- news sentiment
- **Status:** FULLY COVERED.

---

## Strategies We're MISSING (Worth Adding)

### 1. ICT Market Structure + Order Block + Fair Value Gap ("Golden Confluence")
- **Research:** Strategy 1 -- 72.3% WR, Sharpe 1.62, Profit Factor 2.8
- **Gap:** We have `break_of_structure` (ICT BOS/CHOCH) and `swing_failure_pattern` in Alpha Engine, but we do NOT have:
  - **Order block detection** (institutional supply/demand zones from 4H/Daily)
  - **Fair value gap (FVG) identification** (3-candle imbalance zones)
  - **Liquidity sweep detection** (stop hunts above/below swing points)
  - The full confluence system combining ICT structure + on-chain + sentiment
- **Priority: HIGH.** The 72.3% WR and 2.8 profit factor are the best in the research doc. We already have the on-chain and sentiment pieces -- we just need the ICT entry framework.
- **Adaptable code:** The research has a backtesting framework (`ConfluenceStrategy` class) that could be adapted. The ICT components need custom implementation for order block and FVG detection from OHLCV data.
- **Suggested file:** `alpha_engine/ict_confluence_strategy.py`

### 2. Grid Trading Bot
- **Research:** Strategy 5 -- 60-70% WR per level, 3-8% monthly in ranging markets
- **Gap:** We have NO grid trading implementation anywhere in the codebase.
- **Priority: MEDIUM.** Grid trading is profitable in sideways markets, which complements our trend-following and breakout strategies. However, it requires:
  - Active order management (place/cancel limit orders)
  - Exchange API integration for order execution
  - Real-time price monitoring
  - This is more of an execution strategy than a signal strategy
- **Adaptable code:** The research provides a clean config-based implementation. Would need ccxt integration.
- **Suggested file:** `alpha_engine/grid_trading_strategy.py`

### 3. Regime Detection / Adaptive Strategy Selection
- **Research:** Executive summary Section 8 -- "No regime detection" listed as a gap in existing providers
- **Gap:** We have regime detectors scattered across the codebase (`risk_management/regime_detector.py`, `ml_battleground/system_b_regime/regime_classifier.py`, `regime_terminal/hierarchical_regime.py`, `alpha_engine/regime_detector.py`) but they are NOT integrated into a unified strategy selector that automatically picks the best strategy for current market conditions.
- **Priority: HIGH.** The research's Strategy Selection Matrix (trending -> trend following, sideways -> grid/mean reversion, volatile -> breakout, low vol -> arb) is exactly the kind of adaptive routing we need.
- **What to build:** A meta-strategy that classifies the current regime and routes signals to the appropriate strategy set. We have all the pieces; they just need to be wired together.
- **Suggested file:** `alpha_engine/regime_adaptive_router.py`

---

## Strategies to SKIP (Not Worth Adding)

### 1. ML-Enhanced Breakout Detection (Strategy 2)
- **Research:** 67.2% accuracy, Sharpe 1.45
- **Skip because:** We already have `ml_battleground/` with multiple ML systems (System A filter, System B regime, System C deep learning) that surpass this basic XGBoost approach. Our ML signal ranker in KIMI already does confidence-based filtering. The research's approach is essentially a simpler version of what we already run.

### 2. Generic Bollinger Band Mean Reversion (Strategy 4 as-is)
- **Research:** 64% WR, BB + RSI
- **Skip because:** We already have this exact strategy plus more sophisticated variants (Bollinger squeeze with Keltner compression, statistical mean reversion with z-scores). The research version is a textbook implementation with no edge over what we have.

### 3. Basic Whale Alert Monitoring (Strategy 8 as-is)
- **Research:** 62% WR, monitoring $10M+ transactions
- **Skip because:** Our whale accumulation detector uses volume-based detection (5x average volume) which is more responsive than waiting for Whale Alert notifications. We also have exchange flow strategies that track the same underlying signal (exchange inflows/outflows) with more granularity.

### 4. Generic Position Sizing Formula
- **Research:** Risk-based position sizing (Section 5 of exec summary)
- **Skip because:** This is standard Kelly/risk-based sizing. Our `risk_management/` directory and individual scanner modules already implement position sizing. Nothing novel here.

---

## Summary Scorecard

| Research Strategy | WR | Sharpe | Status | Action |
|---|---|---|---|---|
| Golden Confluence (ICT+OnChain+Sentiment) | 72.3% | 1.62 | MISSING (partial) | **BUILD** -- add ICT order block/FVG/liquidity sweep |
| ML-Enhanced Breakout | 67.2% | 1.45 | HAVE (better) | Skip |
| Funding Rate Arbitrage | 85% | 2.1 | HAVE | Skip |
| Mean Reversion BB | 64% | 1.9 | HAVE (better) | Skip |
| Grid Trading | 65% | 1.5 | MISSING | **BUILD** -- complements sideways regime |
| Multi-Timeframe Trend | 58% | 1.35 | HAVE (better) | Skip |
| News Volatility | 55% | 1.8 | HAVE | Skip |
| Whale Tracking | 62% | 2.0 | HAVE | Skip |
| Regime-Adaptive Routing | N/A | N/A | PARTIAL | **WIRE UP** -- connect existing detectors |

## Recommended Priority

1. **ICT Confluence Strategy** -- Highest WR in the research (72.3%), we have all supporting pieces (on-chain, sentiment), just need the ICT entry framework (order blocks, FVGs, liquidity sweeps)
2. **Regime-Adaptive Router** -- We have 4+ regime detectors already built but siloed. Connecting them to auto-select strategies per market condition could improve overall system performance significantly
3. **Grid Trading** -- Lower priority since it requires exchange execution integration, but fills a genuine gap in sideways market strategies

---

*Source documents: `docs/kimi_audit/advanced_strategies.md`, `docs/kimi_audit/executive_summary.md`*
