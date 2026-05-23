# Crypto Signals Framework — Audit Action Items
## Cross-referenced against our system (March 15, 2026)

**Our System:** Battleground 62.7% WR | Alpha Engine 100+ strategies | KIMI 81 algos | Cross-aggregation consensus | Timeframe classifier | ML ranker (33 features) | Regime router | Confluence engine | Portfolio risk manager | Position sizer

---

## Full Framework Review

### Part 1: Industry Benchmarks (Sections 1.1-1.3)
- **Finding:** Top providers hit 70-92% WR; industry avg 73.8%. Our battleground is 62.7%.
- **Finding:** Win rate alone is meaningless — expectancy (WR x AvgWin - LR x AvgLoss) matters more.
- **Finding:** Ensemble ML methods (61-68% accuracy, 1.6 Sharpe) outperform single models.
- **Status:** We track WR and Sharpe per strategy. Expectancy is computed in some modules but NOT surfaced as a primary KPI on dashboards. Ensemble approach is partially done via cross-aggregation consensus.

### Part 2: High-Performance Strategies (Sections 2.1-2.4)
- **Finding:** ICT (liquidity zones, order blocks, FVGs, breaker structures) = 65-75% WR.
- **Status:** We have `break_of_structure` (ICT BOS/CHOCH, 55-65% WR) and `swing_failure_pattern` in Alpha Engine. Missing: Fair Value Gaps, order block detection, breaker structures, liquidity pool targeting.
- **Finding:** Multi-timeframe confluence (Monthly->Weekly->Daily->4H->1H->15m) with 3+ alignment = highest probability.
- **Status:** We have `multi_timeframe_ema_stack` and `timeframe_classifier` in cross-aggregation. Partial coverage — we classify timeframes but don't require cross-timeframe alignment before signal publication.
- **Finding:** Ensemble ML model with weighted inputs: Technical 30%, On-Chain 25%, Sentiment 20%, Market Structure 15%, Macro 10%.
- **Status:** Our ML ranker has 33 features but the weighting is learned from data, not structured into these buckets. On-chain and sentiment features exist but aren't weighted at this ratio.

### Part 3: Risk Management (Sections 3.1-3.4)
- **Finding:** Volatility-adjusted position sizing (BTC 1.0x, ETH 1.2x, Alts 2.0x, Low-cap 3.0x).
- **Status:** `position_sizer.py` does regime-based sizing. `shared/portfolio_risk_manager.py` has asset-class awareness. Volatility multipliers per-asset are partially implemented.
- **Finding:** ATR-based trailing stops outperform fixed % stops.
- **Status:** ATR stops exist in `scanner.py`, `onchain_strategies.py`, and several strategy files. Trailing stops are in `exit_manager.py`. NOT universally applied — many strategies still use fixed % stops.
- **Finding:** Portfolio risk limits: single trade 1-2%, single asset 10%, sector 20%, correlated 15%, total open risk 5-10%, max drawdown 20%.
- **Status:** `portfolio_risk_manager.py` enforces concentration limits and drawdown guards. Correlation-based exposure limits are NOT explicitly implemented.

### Part 4: On-Chain Analytics (Sections 4.1-4.3)
- **Finding:** NUPL, MVRV Z-Score, Exchange Flows, SOPR, LTH Supply, Pi Cycle Top.
- **Status:** `onchain_strategies.py` has: MVRV proxy, hash ribbon, NVT, SOPR proxy, stablecoin supply ratio, fear/greed, on-chain composite score. Missing: NUPL (direct), Pi Cycle Top indicator, LTH Supply tracking, ETF flow tracking.
- **Finding:** Combining on-chain with technical (6-point checklist) for high-conviction entries.
- **Status:** `confluence_engine.py` does combine on-chain + technical signals. The specific 6-point checklist format is not codified but the concept is implemented.

### Part 5: Sentiment Analysis (Sections 5.1-5.3)
- **Finding:** Multi-source sentiment: Twitter/X 25%, Reddit 20%, Telegram 15%, News 20%, F&G 15%, Google Trends 5%.
- **Status:** We have `lunarcrush_signal.py`, `binance_sentiment.py`, `cryptopanic_feargreed.py`, `google_trends_signal.py`, `news_sentiment_strategies.py`. Coverage is good. Missing: Reddit-specific scraping, Telegram-specific sentiment, weighted composite sentiment score.
- **Finding:** Sentiment + Price Divergence as a signal (bullish div = price lower lows, sentiment higher lows).
- **Status:** NOT implemented. We track sentiment and price independently but don't compute divergences between them.

### Part 6: Signal Generation (Sections 6.1-6.3)
- **Finding:** Signal Quality Scorecard (0-100): Technical 25%, On-Chain 20%, Sentiment 15%, RRR 20%, Market Structure 15%. Only publish >= 70.
- **Status:** ML ranker produces a score (0-1) and confluence engine adds multipliers. We do NOT have a structured 100-point scorecard with explicit category weights. The gating threshold concept exists (signals below ML threshold are suppressed).
- **Finding:** Signal format with multiple TPs (TP1, TP2, TP3 runner), position sizing, hold time.
- **Status:** Signals have entry/TP/SL. Multiple TP levels are not standard across all systems. Hold time is tracked by signal_tracker but not always published with the signal.
- **Finding:** Pre-publication verification checklist (10 items including backtest, RRR, macro check).
- **Status:** We have `strategy_guard.py` and `genome_validate.py` for validation. Not all 10 checklist items are enforced.

### Part 7: Performance Tracking (Sections 7.1-7.3)
- **Finding:** Track: WR, Avg Win, Profit Factor, Sharpe, Max Drawdown, Expectancy, Signal Frequency, Retention.
- **Status:** `signal_tracker.py` tracks WR, win/loss by asset class. `auto_tuner.py` and `forward_validator.py` track Sharpe. Profit factor and expectancy are computed in backtest modules but NOT in the live tracking dashboard.
- **Finding:** Weekly/Monthly/Quarterly review cadence with optimization.
- **Status:** We have continuous automation (every 15-30 min scans) but no structured periodic review process with parameter adjustment. `auto_tuner.py` exists but is not on a scheduled cadence.

### Part 8: Technology Stack (Sections 8.1-8.2)
- **Finding:** Recommended: Binance API, CoinGecko Pro, Glassnode, CryptoQuant, LunarCrush, Santiment, TradingView, XGBoost, Telegram/Discord bots.
- **Status:** We use Binance, CoinGecko, CryptoQuant, LunarCrush, TradingView (Pine scripts), XGBoost (ML ranker), Discord (cross-aggregation notifier). Missing: Glassnode, Santiment, Telegram bot distribution.
- **Finding:** WebSocket real-time price feeds.
- **Status:** We use REST API polling (every 15-30 min). No WebSocket implementation for real-time streaming.

### Part 9: Competitive Differentiation (Sections 9.1-9.2)
- **Finding:** Regime-adaptive signals that adjust strategy parameters per market condition.
- **Status:** `regime_router.py` classifies regimes and filters strategies. `regime_detector.py` detects trending/ranging/volatile/crisis. This is IMPLEMENTED and is a differentiator.
- **Finding:** Verified public track record with third-party audit.
- **Status:** We have `audit_dashboard/`, `audit_trail/`, and live dashboards at GitHub Pages. Partial — it's public but not third-party audited.
- **Finding:** Kelly Criterion for optimal position sizing.
- **Status:** `kelly_position_sizing.py` exists in Kimi_Agent prompting guide. Not integrated into the live production pipeline.

---

## Top 10 Most Impactful Action Items

### 1. Unified Signal Quality Scorecard (0-100)
- **WHAT:** Implement a structured 100-point scoring system: Technical Confluence (25pts), On-Chain Support (20pts), Sentiment Alignment (15pts), Risk-Reward Ratio (20pts), Market Structure (15pts). Only publish signals scoring >= 70. Show breakdown on dashboard.
- **WHY:** Framework shows this is what separates top providers from average. Currently our ML score is opaque — a transparent scorecard builds trust, improves signal quality, and provides clear gating. Expected: +5-8% WR improvement by filtering low-quality signals.
- **EFFORT:** Medium (refactor confluence_engine.py to output structured 0-100 scores instead of multipliers)
- **PRIORITY:** 1
- **STATUS:** Partially done — confluence_engine.py exists but outputs multipliers, not structured categorical scores.

### 2. Sentiment-Price Divergence Detection
- **WHAT:** Build a module that computes divergences between sentiment trend and price trend. Bullish divergence = price making lower lows while sentiment makes higher lows. Bearish = opposite.
- **WHY:** This is an entirely unimplemented signal type in our system. Academic research shows sentiment divergence precedes 60-70% of major reversals. Adds a unique edge no single strategy currently captures.
- **EFFORT:** Medium (new module, requires correlating existing sentiment feeds with price data)
- **PRIORITY:** 2
- **STATUS:** Not started — we have both sentiment and price data but never compare their trends.

### 3. ATR-Based Trailing Stops as Default
- **WHAT:** Replace fixed-% stop losses with ATR-based trailing stops across all strategies that currently use fixed stops. Use 2.5x ATR for entry stop, trail at 2x ATR from highest price.
- **WHY:** Framework and academic data show ATR trailing stops capture 15-30% more profit in trending markets while maintaining same protection. Many of our strategies still use fixed 2-5% stops.
- **EFFORT:** Medium (audit all strategies, update stop logic in scanner.py and strategy files)
- **PRIORITY:** 3
- **STATUS:** Partially done — some strategies use ATR stops, but it's not the default. exit_manager.py has trailing logic.

### 4. Correlation-Based Exposure Limits
- **WHAT:** Add real-time correlation checks to portfolio_risk_manager.py. Before opening a new position, compute rolling 30d correlation with all open positions. Reject if correlated exposure > 15% of portfolio.
- **WHY:** Framework specifies correlated positions max 15%. We currently check concentration by symbol and sector but NOT by correlation. In crypto, BTC/ETH/SOL often move together — we could have 5 "different" positions that are effectively one bet.
- **EFFORT:** Low-Medium (extend existing portfolio_risk_manager.py with numpy correlation matrix)
- **PRIORITY:** 4
- **STATUS:** Not started — portfolio_risk_manager.py has concentration limits but no correlation check.

### 5. Expectancy & Profit Factor as Primary Dashboard KPIs
- **WHAT:** Surface expectancy ((WR x AvgWin) - (LR x AvgLoss)) and profit factor (GrossWin / GrossLoss) on all dashboards alongside WR. Make expectancy the primary sort metric instead of WR alone.
- **WHY:** Framework's key insight: "Win rate alone is meaningless." A 55% WR strategy with 3:1 RRR beats 80% WR with 1:5 RRR. We currently over-index on WR in strategy selection and dashboard display.
- **EFFORT:** Low (data already exists in signal_tracker.py and backtest modules — just needs surfacing)
- **PRIORITY:** 5
- **STATUS:** Partially done — computed in backtests but not surfaced as primary KPI on live dashboards.

### 6. Multi-Timeframe Alignment Gate
- **WHAT:** Before publishing any signal, require confirmation across at least 2 higher timeframes. E.g., a 4H buy signal must have daily and weekly trend alignment. Reject signals where higher timeframes contradict.
- **WHY:** Framework calls this "highest probability setup." Our timeframe_classifier classifies signals but doesn't enforce cross-timeframe alignment. Expected: +3-5% WR by filtering counter-trend signals.
- **EFFORT:** Medium (extend timeframe_classifier.py to fetch and check higher TF data before signal approval)
- **PRIORITY:** 6
- **STATUS:** Partially done — timeframe_classifier exists, multi_timeframe_ema_stack strategy exists, but no mandatory gate.

### 7. ICT Fair Value Gap + Liquidity Pool Detection
- **WHAT:** Add Fair Value Gap (FVG) detection and liquidity pool mapping to complement existing BOS/CHOCH signals. FVGs are 3-candle patterns where middle candle gaps create unfilled zones.
- **WHY:** ICT methodology is 65-75% WR per framework. We have BOS/SFP but missing the other core ICT components (FVGs, order blocks, breaker structures). These are high-alpha institutional signals.
- **EFFORT:** Medium-High (new strategy module with specific candle pattern detection)
- **PRIORITY:** 7
- **STATUS:** Not started — only have break_of_structure and swing_failure_pattern from ICT toolkit.

### 8. Structured Monthly Performance Reports
- **WHAT:** Auto-generate monthly performance reports (following framework's template) with: total signals, WR, avg win/loss, profit factor, Sharpe, max drawdown, strategy breakdown, asset breakdown, market conditions, lessons learned.
- **WHY:** Framework emphasizes continuous improvement cycle. We have all the raw data but no automated reporting. This enables systematic optimization and builds credible track record for audit.
- **EFFORT:** Low (signal_tracker.py has all data — just needs a report generator script + scheduled action)
- **PRIORITY:** 8
- **STATUS:** Not started — data exists, report generation does not.

### 9. Kelly Criterion Integration for Production Position Sizing
- **WHAT:** Integrate Kelly Criterion (f* = (bp - q) / b where b=win/loss ratio, p=win probability, q=loss probability) into position_sizer.py. Use half-Kelly for safety. Override current regime-only sizing with Kelly-informed sizing.
- **WHY:** Framework recommends Kelly as advanced position sizing. kelly_position_sizing.py already exists but isn't plugged into production. Kelly optimizes growth rate while limiting ruin probability.
- **EFFORT:** Low (code exists in Kimi_Agent guide — needs integration into position_sizer.py)
- **PRIORITY:** 9
- **STATUS:** Partially done — kelly_position_sizing.py exists but is not in the production pipeline.

### 10. Multiple Take-Profit Levels (TP1/TP2/TP3 Runner)
- **WHAT:** Standardize all signal outputs to include 3 TP levels: TP1 at 1.5:1 RRR (take 50%), TP2 at 3:1 RRR (take 30%), TP3 as runner (trail remaining 20%). Move stop to breakeven at TP1.
- **WHY:** Framework's signal format includes this. Most of our strategies output a single TP. Multi-TP approach locks in profits early while maintaining upside. Reduces avg loss by moving stop to breakeven after TP1.
- **EFFORT:** Medium (modify signal output format across all strategy modules + update signal_tracker.py to track partial exits)
- **PRIORITY:** 10
- **STATUS:** Not started — most strategies output single entry/TP/SL. No partial exit tracking.

---

## Implementation Priority Matrix

| Priority | Action Item | Effort | Expected WR Impact | Expected P&L Impact |
|----------|-------------|--------|-------------------|---------------------|
| 1 | Unified Scorecard (0-100) | Medium | +5-8% | High (quality gate) |
| 2 | Sentiment-Price Divergence | Medium | +2-3% new alpha | Medium-High |
| 3 | ATR Trailing Stops Default | Medium | +0% WR, +15-30% avg win | High (P&L) |
| 4 | Correlation Exposure Limits | Low-Med | Risk reduction | High (drawdown) |
| 5 | Expectancy as Primary KPI | Low | Indirect (better decisions) | Medium |
| 6 | Multi-TF Alignment Gate | Medium | +3-5% | Medium-High |
| 7 | ICT FVG + Liquidity Pools | Med-High | +5-10% on ICT signals | Medium |
| 8 | Monthly Performance Reports | Low | Indirect (optimization) | Medium |
| 9 | Kelly Criterion Sizing | Low | +10-20% growth rate | Medium-High |
| 10 | Multi-TP (TP1/TP2/TP3) | Medium | +15-30% avg win | High (P&L) |

---

## Items Already Well-Implemented (No Action Needed)

- **Regime Detection:** `regime_detector.py` + `regime_router.py` = fully operational, classifies trending/ranging/volatile/crisis and routes strategies accordingly.
- **ML Signal Ranking:** `ml_signal_ranker.py` with 33 features, auto-trains at 50+ closed picks.
- **Cross-System Consensus:** `cross_aggregation/aggregator.py` combines KIMI + Alpha + Battleground picks.
- **Discord Notifications:** `cross_aggregation/discord_notify.py` sends consensus picks.
- **Elimination Engine:** `elimination_engine.py` with probation/elimination/challenger system.
- **On-Chain Strategies:** 10+ on-chain strategies including MVRV, hash ribbon, NVT, SOPR, fear/greed.
- **Sentiment Data Sources:** LunarCrush, Binance sentiment, CryptoPanic, Google Trends all integrated.
- **Public Performance Dashboard:** GitHub Pages dashboards for Alpha Engine and monitor.
- **Portfolio Risk Manager:** Drawdown guards, concentration limits, leverage checks.
- **Position Sizing:** Regime-aware position sizing with confidence factors.

---

*Generated: March 15, 2026 | Source: crypto_signals_framework.md (Kimi Agent Research)*
