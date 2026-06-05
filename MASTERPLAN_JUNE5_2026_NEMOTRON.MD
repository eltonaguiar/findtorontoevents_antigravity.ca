# MASTERPLAN_JUNE5_2026_NEMOTRON.MD
## FindTorontoEvents.ai - Multi-AI Prediction System Improvement Plan
**Date:** June 5, 2026  
**Model:** nemotron-3-super-120b-a12b:free (via OpenRouter)  
**Goal:** Achieve "real-money" worthy picks by resolving data integrity issues, diversifying AI engines, and improving strategy robustness.

---

## 1. Executive Summary

The system currently relies on a single AI engine (claude-opus-4-7) for pick generation, resulting in suboptimal performance across asset classes. While the medium-horizon strategy shows promise (rank_score 40.35, WR 35%), most asset classes and horizons remain in the "building" phase due to insufficient sample sizes (n < 20). Critical issues include:

1. **Data Integrity Problems**: Resolver failures and unadjusted stock/split data causing skewed outcomes
2. **Engine Monoculture**: Only one AI engine contributing to the leaderboard
3. **Strategy Limitations**: Over-reliance on trend-following without sufficient alpha generation
4. **Insufficient Sample Sizes**: Most asset class/horizon combinations lack the n≥20 threshold for ranked status

This plan addresses these issues through immediate data fixes, engine diversification, strategy refinement, and enhanced monitoring.

---

## 2. Current State Analysis

### 2.1 AI Leaderboard Status (as of 2026-06-05)
- **Total Engines**: 1 (claude-opus-4-7)
- **Total Picks**: 38 (29 resolved)
- **Best Performing Horizon**: Medium (n=20, WR=35%, PF=1.36, rank_score=40.35)
- **Best Performing Asset Class**: Equity (n=6, WR=50%, PF=2.97, rank_score=58.38) *but building due to n<20*
- **Best Performing Horizon/Asset Combo**: Long horizon (n=5, WR=80%, PF=6.81) *but building*

### 2.2 Data Infrastructure
- **Databases**: 
  - ejaguiar1_stocks (live picks & resolver outputs)
  - ejaguiar1_backtests (backtest data)
  - ejaguiar1_backups (archive)
  - 8 additional specialized databases (deals, events, etc.)
- **Credential Management**: Centralized via `tools/db_env.py` with canonical source `DB_PASSWORDS_JSON`
- **Database Tools**: 
  - `tools/db_freshness_check.py` (monitors staleness)
  - `tools/cross_db_consistency.py` (validates strategy key alignment)
  - `tools/db_backup.py` (archives pre-mutation state)

### 2.3 Strategy Components
- **Core Scanner**: `alpha_engine/scanner.py` and `production_scanner.py`
- **Strategy Engine**: `alpha_engine/antigravity_strategies.py`
- **Scoring**: `alpha_engine/score_booster.py`, `hyrotrader_enhanced_scoring.py`
- **Validation**: `alpha_engine/forward_validator.py`, `walkforward_validator.py`
- **MA Trend Strategies**: Separate tracking system with 6-year backtests

---

## 3. Data Integrity Plan

### 3.1 Immediate Fixes (Week 1)
- **Resolver Audit**: 
  - Run `tools/resolve_all_picks.py` (if exists) or equivalent to verify resolver outputs
  - Check for unresolved picks in `ejaguiar1_stocks.trading_picks` where `resolved=0` and age > 48h
- **Stock Split Adjustment**:
  - Implement split/dividend adjustment pipeline using `alpha_engine/price_validator.py`
  - Validate against `tools/split_adjustment_verifier.py` (create if missing)
- **Data Freshness Enforcement**:
  - Lower `DB_FRESHNESS_THRESHOLD_RED` from 6h to 2h for live picks
  - Add alerting when resolver lag > 2h (vs current 4h)

### 3.2 Systemic Improvements (Weeks 2-4)
- **Database Schema Validation**:
  - Monthly run of `tools/check_table_schema.py` against all databases
  - Automated migration test suite for schema changes
- **Data Quality Gates**:
  - Implement pre-ingest validation for all data sources (prices, fundamentals, alternative data)
  - Create `alpha_engine/data_ingest_validator.py` with:
    - Price anomaly detection (>50% moves without volume)
    - Split/dividend flag verification
    - Cross-exchange price consistency checks
- **Backup Verification**:
  - Weekly test restore from `ejaguiar1_backups` to staging environment
  - Verify pick resolver can replay historical data correctly

### 3.3 Monitoring & Alerting
- **Dashboard Enhancements**:
  - Add data health tab to audit dashboard showing:
    - Resolver lag histogram
    - Split adjustment success rate
    - Database connection error rates
  - Create `tools/data_health_monitor.py` exporting Prometheus metrics
- **Automated Regression Testing**:
  - Weekly script comparing current resolver output against known-good snapshots
  - Fail CI if resolver accuracy drops >5% month-over-month

---

## 4. Model and Engine Diversification Plan

### 4.1 Immediate Engine Expansion (Week 1)
- **Activate Configured Models**:
  - Check `config.yaml` for enabled LLM providers (currently showing: free-mode, free-mode-fast via VLLM)
  - Run `python tools/ai_attribution/build_ai_leaderboard.py --force-refresh` to attribute existing picks to all consulted models
  - Expected outcome: Multiple engines appear in leaderboard (currently only seeing claude-opus-4-7 due to attribution logic)
- **Add New Engines**:
  - Configure additional API keys from dbpasses.txt:
    - Groq (gsk_UW...PMlj) for fast inference
    - Together AI (tgp_v1_vVslDuq1GClrP_JIGKpin40TPTsJwcvYAZ9oyGtQEVg)
    - Fireworks (fw_2pDVjP9s61eoArpMF6eCd)
    - Gemini (AIzaSy...gmdY)
  - Update `config.yaml` to enable these as separate engines in the swarm

### 4.2 Engine Specialization (Weeks 2-3)
- **Asset-Class Specific Models**:
  - Assign Groq/Llama3 for high-frequency crypto signals (low latency critical)
  - Assign Gemini 1.5 Pro for macro-driven equity/ETF analysis (long context)
  - Assign Claude 3 Opus for complex derivatives/futures reasoning
- **Prompt Engineering per Engine**:
  - Create `prompts/` directory with asset-class/hourizon optimized prompts
  - Implement dynamic prompt selection in `alpha_engine/prompt_router.py`
- **Ensemble Voting Improvements**:
  - Weight votes by historical performance per asset class
  - Add confidence calibration using Platt scaling on historical outcomes

### 4.3 Performance Attribution
- **Enhanced Leaderboard**:
  - Modify `tools/ai_attribution/build_ai_leaderboard.py` to show:
    - Per-engine calibration metrics (Brier score, reliability diagrams)
    - Engine correlation matrix to avoid redundant picks
    - Kelly criterion optimal allocation weights
- **Live Engine Rotation**:
  - Implement weekly engine performance review
  - Automatically reduce weight of engines with 3-week rolling Sharpe < 0.5

---

## 5. Strategy Improvement Plan

### 5.1 Immediate Fixes (Week 1)
- **MA Strategy Honesty**:
  - Address the Monte-Carlo warning: MA trends are defensive overlays, not alpha sources
  - Remove MA strategies from primary alpha generation; use only for regime filtering
  - Update `alpha_engine/regime_filter.py` to use MA as regime indicator only
- **Parameter Sweep Validation**:
  - Re-run `alpha_engine/scanner.py` with walk-forward validation to prevent overfitting
  - Discard strategies with IS/OOS PF ratio > 2.0 (indicating overfit)

### 5.2 New Strategy Development (Weeks 2-6)
- **Mean Reversion Revival**:
  - Focus on EQUITY and ETF mean reversion (currently showing best PF in equity: 2.97)
  - Develop pair trading strategies for sector ETFs (XLE/XOP, IBB/XBI)
  - Implement cointegration-based crypto pairs (ETH/BTC, SOL/BTC)
- **Alternative Data Integration**:
  - Integrate Google Trends, Twitter sentiment, and on-chain metrics
  - Create `alpha_engine/alternative_data_harvester.py` for:
    - LunarCrush social metrics for crypto
    - AAII investor sentiment for equities
    - COT reports for commodities/futures
- **Regime-Adaptive Position Sizing**:
  - Implement volatility targeting (target 15% annualized volatility)
  - Adjust position sizing based on VIX, BVOL, CVOL, and asset-specific volatility

### 5.3 Strategy Lifecycle Management
- **Promotion/Demotion Criteria**:
  - Promote to "live trading" after: 
    - 30+ trades, PF > 1.4, Sharpe > 0.8, max drawdown < 20%
  - Demote to "research" if:
    - Rolling 20-trade PF < 1.1 or max drawdown > 35%
- **Weekly Strategy Review**:
  - Every Friday: run `tools/strategy_performance_review.py`
  - Archive underperforming strategies to `strategies/archive/`
  - Promote promising research strategies to active pool

---

## 6. Risk Management and Position Sizing

### 6.1 Position Sizing Framework
- **Kelly Criterion with Safety**:
  - Use fractional Kelly (f = 0.5) to reduce volatility
  - Cap max position size at 2% of portfolio per pick
  - Adjust for correlation: reduce size if picking >2 highly correlated assets
- **Volatility Targeting**:
  - Target 12% portfolio volatility (adjustable based on regime)
  - Use ATR(20) for position sizing in commodities/crypto
  - Use implied volatility rank for options/volatility products

### 6.2 Portfolio Construction Rules
- **Diversification Limits**:
  - Max 20% portfolio in any single asset class
  - Max 15% in any single sector (for equity/ETF)
  - Max 10% in any single pick (individual position)
- **Risk Budgeting**:
  - Allocate risk (not capital) across strategies:
    - 40% to mean reversion
    - 30% to trend following (regime filtered)
    - 20% to breakout/momentum
    - 10% to alternative data/special situations
- **Stop Loss Protocols**:
  - Hard stop: 2x ATR(14) or 8% (whichever tighter)
  - Time stop: Exit if no movement after 3x expected hold time
  - Trailing stop: Activate after 1.5x risk profit achieved

### 6.3 Real-Time Risk Monitoring
- **Live Risk Dashboard**:
  - Add to audit dashboard: current portfolio VaR, correlation matrix, leverage
  - Create `tools/live_risk_monitor.py` calculating:
    - Portfolio beta to BTC/SPY
    - Concentration metrics (Herfindahl-Hirschman index)
    - Stress test results (2008, 2020, 2022 scenarios)
- **Circuit Breakers**:
  - Pause new picks if daily loss > 3% of portfolio
  - Pause if portfolio volatility > 2x target for 2 consecutive days
  - Require manual override to resume after circuit breaker trigger

---

## 7. Automation and Monitoring

### 7.1 Enhanced Cron Jobs
- **Data Pipeline**:
  - 00:05 UTC: Price data ingestion (crypto, equity, forex, futures)
  - 00:20 UTC: Fundamental data update (earnings, dividends, splits)
  - 00:35 UTC: Alternative data ingestion (social, on-chain, macro)
  - 01:00 UTC: Resolver run (all pending picks)
  - 02:00 UTC: Strategy signal generation
  - 03:00 UTC: Pick validation and archival
  - 04:00 UTC: Leaderboard and dashboard refresh
  - 05:00 UTC: Risk metrics calculation
  - 06:00 UTC: Database consistency and freshness checks
- **Notification System**:
  - Slack/email alerts for:
    - New pick generation (with confidence score)
    - Resolver failures (>5 consecutive failures)
    - Strategy performance degradation
    - Data pipeline failures

### 7.2 Self-Improvement Loops
- **Weekly Retraining**:
  - Sundays: Retrain ML models (if any) on latest data
  - Mondays: Validate against walk-forward window
  - Tuesdays: Update strategy weights based on performance
- **Monthly Deep Dive**:
  - First weekend: Full system audit
  - Review: data quality, strategy performance, engine calibration
  - Archive: monthly performance report to `reports/monthly/`

### 7.3 Chaos Engineering
- **Monthly GameDays**:
  - Simulate: database failure, API key expiration, data feed corruption
  - Measure: time to detection and recovery
  - Update: runbooks based on findings
- **Fault Injection**:
  - Randomly delay resolver by 10-30min to test buffering
  - Corrupt 1% of price data to test outlier detection

---

## 8. Backtesting and Validation Enhancements

### 8.1 Backtesting Framework Upgrades
- **Transaction Cost Modeling**:
  - Implement dynamic slippage model: 
    - Base: 5bps + 0.1% * (volatility/avg_volatility)
    - Crypto: add 0.05% * (trade size / avg_daily_volume)
    - Equity: use hourly VWAP participation model
  - Include: commissions, fees, exchange fees, funding rates
- **Look-Ahead Bias Prevention**:
  - Enforce: all fundamental data lagged by 1 day (earnings, dividends)
  - Ensure: split/dividend data only available after ex-date
  - Validate: no future data in feature calculation using `alpha_engine/feature_leakage_detector.py`
- **Out-of-Sample Testing**:
  - Require: 3-year walk-forward with annual retraining
  - Report: IS/OOS performance decay metrics
  - Reject: strategies with OOS PF < 0.8 * IS PF

### 8.2 Validation Toolkit
- **Performance Attribution**:
  - Create `tools/performance_attribution.py` breaking down returns by:
    - Asset class, horizon, strategy type, signal source
    - Timing vs selection contribution
- **Robustness Testing**:
  - Monte Carlo permutation testing (1000 iterations)
  - Bootstrap confidence intervals on Sharpe, PF, max drawdown
  - Sensitivity analysis: vary parameters ±20%
- **Regime Testing**:
  - Test performance in: bull, bear, sideways, high volatility, low liquidity regimes
  - Require: strategy profitable in ≥3 of 4 regimes

### 8.3 Production Validation
- **Paper Trading Requirements**:
  - Minimum 30 days paper trading before live deployment
  - Must achieve: PF > 1.3, max daily loss < 1.5% of portfolio
  - Weekly review: compare paper trading signals to actual signals
- **Shadow Trading**:
  - Run parallel to live: same signals, no execution
  - Track: slippage, fill rates, market impact
  - Alert: if live slippage > 2x paper trading slippage for 3 consecutive days

---

## 9. Implementation Roadmap

### Phase 1: Stabilization (Weeks 1-2)
- [ ] Fix resolver and data integrity issues
- [ ] Activate all configured AI engines in attribution system
- [ ] Implement enhanced data validation pipeline
- [ ] Lower data freshness thresholds to 2h/4h
- [ ] Add data health monitoring to audit dashboard
- [ ] Expected outcome: Multiple engines visible on leaderboard, data freshness GREEN

### Phase 2: Diversification (Weeks 3-4)
- [ ] Deploy 3+ new AI engines (Groq, Together, Fireworks, Gemini)
- [ ] Implement asset-class specific prompt routing
- [ ] Begin mean reversion strategy development
- [ ] Remove MA trend strategies from alpha generation (use for regime only)
- [ ] Expected outcome: Leaderboard shows 4+ engines, mean reversion strategies in research

### Phase 3: Optimization (Weeks 5-6)
- [ ] Implement Kelly fractional position sizing with volatility targeting
- [ ] Deploy alternative data integrations (social, on-chain, macro)
- [ ] Activate weekly strategy review and promotion/demotion system
- [ ] Expected outcome: Leaderboard shows ranked cells in ≥3 asset classes, portfolio volatility on target

### Phase 4: Validation (Weeks 7-8)
- [ ] Complete backtesting framework upgrades with realistic transaction costs
- [ ] Implement paper trading requirement for all new strategies
- [ ] Launch monthly deep dive and chaos engineering program
- [ ] Expected outcome: Verified PF > 1.4 across strategies, <10% performance decay IS/OOS

### Phase 5: Live Deployment (Week 9+)
- [ ] Begin live trading with 20% allocation (80% paper trading/shadow)
- [ ] Scale to 50% allocation after 2-week live track record
- [ ] Full deployment after 1-month live validation
- [ ] Expected outcome: Live PF > 1.3, max drawdown < 15%, Sharpe > 0.7

---

## 10. Success Metrics

### 10.1 Primary Goals (90-day target)
- **AI Leaderboard**: 
  - ≥4 engines with classified status (n≥20) in at least 1 asset class
  - Best engine PF > 1.5, Sharpe > 0.8
- **Data Integrity**:
  - Resolver lag < 2h 95% of time
  - Zero unadjusted stock splits in live data
- **Strategy Performance**:
  - Portfolio PF > 1.4 (live or paper trading)
  - Max drawdown < 20%
  - Win rate > 40% with profit factor > win rate/loss rate

### 10.2 Monitoring Targets
- **System Health**:
  - Data pipeline uptime > 99%
  - False alert rate < 5% (data quality alerts)
  - Mean time to detection (MTTD) < 15min for data issues
- **Trading Efficiency**:
  - Average slippage < 15bps for liquid assets (BTC, ETH, SPY)
  - Fill rate > 95% for limit orders placed within 1% of midprice
  - Portfolio turnover < 200% annually (avoid excessive churn)

### 10.3 Risk Compliance
- **VaR Limits**:
  - 95% 1-day VaR < 3% of portfolio
  - 99% 1-day VaR < 5% of portfolio
- **Liquidity Risk**:
  - Max position size < 10% of average daily volume for liquid assets
  - No single position > 20% of portfolio liquidation daily volume
- **Model Risk**:
  - No strategy weight > 30% of active allocation
  - Engine correlation < 0.7 between top 3 weighted engines

---

## Appendices

### Appendix A: Key Files and Scripts
- **Data Integrity**: 
  - `tools/db_env.py`, `tools/db_freshness_check.py`, `tools/cross_db_consistency.py`
  - `alpha_engine/price_validator.py`, `tools/split_adjustment_verifier.py` (to create)
- **Engine Management**:
  - `tools/ai_attribution/build_ai_leaderboard.py`, `config.yaml`
  - `alpha_engine/prompt_router.py` (to create), `prompts/` directory (to create)
- **Strategy Engine**:
  - `alpha_engine/scanner.py`, `alpha_engine/antigravity_strategies.py`
  - `alpha_engine/score_booster.py`, `alpha_engine/regime_filter.py`
- **Risk Management**:
  - `tools/live_risk_monitor.py` (to create), `tools/performance_attribution.py` (to create)
- **Monitoring**:
  - `tools/data_health_monitor.py` (to create), audit dashboard enhancements

### Appendix B: Database Credentials Reference
From `dbpasses.txt` and `.env.dbpw`:
- **Host**: mysql.50webs.com
- **Stocks DB**: ejaguiar1_stocks / password: stocks1234560
- **Backtests DB**: ejaguiar1_backtests / password: backtests1234560
- **Backups DB**: ejaguiar1_backups / password: backups1234560
- **Canonical Source**: `DB_PASSWORDS_JSON` or `.env.dbpw`

### Appendix C: Current Leaderboard Interpretation
- **Classification Threshold**: n ≥ 20 (MIN_N_RANKED)
- **Rank Score Formula**: Shrinkage-weighted win rate toward asset-class prior
- **Wilson CI**: 95% confidence interval on win rate
- **Profit Factor (PF)**: Gross profit / gross loss
- **Expectancy**: Average profit per trade (in R-multiples)

---
**Next Step**: Execute Phase 1 immediate actions starting with data integrity fixes and engine attribution verification.