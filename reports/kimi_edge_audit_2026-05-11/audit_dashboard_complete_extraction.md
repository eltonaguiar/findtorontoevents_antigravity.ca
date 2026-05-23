# Unified Audit Dashboard - Complete Performance Data Extraction
## Source: https://findtorontoevents.ca/audit
### Extraction Date: 2026-05-11
### Dashboard Version: v99.0

---

## 1. EXECUTIVE SUMMARY

The Antigravity Unified Audit Dashboard is a comprehensive financial prediction system tracking **130+ systems** generating picks across **7 asset classes** (Crypto, Equity, Forex, Commodity, ETF, Bond, Futures). The dashboard displays real-time performance metrics, walk-forward validation results, tier-2 proven strategies, and extensive alerting for degraded systems.

**Key Headline Metrics:**
- **Total Closed Picks**: 3,386 (filtered) / 29,258 (raw) / 9,627 (resolved)
- **Active Picks**: 50-61 (varies by quality gates)
- **Systems**: 13 active proven, 130+ total
- **Overall Win Rate**: 34.8-40.0%
- **Total PnL**: +949.43% (capped) / +986.01% (latest)
- **Profit Factor**: 1.49-1.51
- **Expectancy**: +0.28-0.29%

---

## 2. DB HEALTH METRICS

| Metric | Value | Status |
|--------|-------|--------|
| PnL Integrity (sampled) | 42.0% | RED (58,000/100,000 mismatch >1pp) |
| Ghost Rows (constant pnl_pct) | 655,000 | RED (18 cohorts, n>1000) |
| Forward Validator Freshness | 840h | RED (last WON/LOST: 2026-04-02) |
| Phantom EXPIRED rows | 100.0% | RED (1 class, worst-case) |
| Raw-Pick Outcome Coverage | 0.09% | RED (121/136,374 resolved) |
| WON-vs-PnL contradiction | YES | RED (avg pnl per status — writer bug) |

**Action Required**: Red-tier metrics detected. See `reports/db_evidence_graded_final_2026-05-08.md` for remediation.

---

## 3. ASSET CLASS HEALTH (Headline - Full History)

| Asset Class | Profit Factor | Win Rate | n (trades) | Tier Status | Notes |
|-------------|--------------|----------|------------|-------------|-------|
| **COMMODITY** | **2.08** | 48.7% | 816 | T2 PF confirmed | Post-resolver-v2, 7d clean. Lift WR to 50%+ for full T2. |
| **BOND** | **1.72** | **55.6%** | 18 | Meets T2 thresholds | n<100 charter floor |
| **EQUITY** | **1.42** | **52.8%** | 428 | T2 candidate | Scale candidate |
| **ETF** | 1.20 | **53.4%** | 88 | Borderline T3 | n→100 needed |
| **CRYPTO** | 1.26 | 44.8% | 8,162 | Sub-T2 | quan_engine base (PF 0.66, 21% vol) not yet blocked |
| **FOREX** | **0.28** | 45.6% | 1,249 | Sub-floor (genuine) | Confirmed NOT resolver noise. Mutation protocol required. |

### Recent vs Headline Divergence (60-90d window)

| Asset Class | Headline PF | Recent PF | Headline n | Recent n |
|-------------|-------------|-----------|------------|----------|
| CRYPTO | 1.25 | 0.89 | 8,067 | 1,650 |
| COMMODITY | 1.78 | 1.09 | - | - |

---

## 4. TIER DEFINITIONS

| Tier | Profit Factor | Win Rate | Max Drawdown | Description |
|------|--------------|----------|--------------|-------------|
| T1 (Renaissance) | >2.0 | >55% | <10% | Highest grade |
| T2 (Institutional) | >1.5 | >50% | <20% | Institutional grade |
| T3 (Retail-OK) | >1.2 | >48% | <30% | Acceptable for retail |

---

## 5. WALK-FORWARD OUT-OF-SAMPLE METRICS

| Class | Folds | OOS WR | OOS Sharpe | Decay | Consistency | Worst-fold WR |
|-------|-------|--------|------------|-------|-------------|---------------|
| **CRYPTO** | 25 | 46.1-46.5% | **1.833-1.936** | -0.4 | 68.0% | 27.0% |
| **EQUITY** | 8 | **64.1%** | **6.555** | +3.9 | 87.5% | 40.0% |
| **ETF** | 4 | **76.2%** | **11.372-11.414** | +28.8 | **100.0%** | 70.0% |
| **FOREX** | 52 | 40.4-40.5% | **-3.504 to -3.518** | -1.9 to -2.0 | 46.2-48.1% | **2.0%** |

*Sharpe color coding: green > 0.5, yellow 0-0.5, red < 0*

---

## 6. TIER-2 PROVEN STRATEGIES

### 6a. signal_validation (TIER 2)

| Metric | Value |
|--------|-------|
| Win Rate | 52.8% |
| Profit Factor | 2.09 |
| Max Drawdown | 18.9% |
| Total Trades (n) | 248 |
| 90d Cumulative | +177.7% |
| Asset Classes | CRYPTO, FOREX |

**Recent 3 Picks:**
| Symbol | Direction | PnL |
|--------|-----------|-----|
| AUD-USD | SHORT | +0.00% |
| DOT-USD | SHORT | +3.00% |
| AUD-USD | SHORT | +0.00% |

### 6b. mega_mutation (BELOW TIER 3)

| Metric | Value |
|--------|-------|
| Win Rate | 57.9% |
| Profit Factor | 2.41 |
| Max Drawdown | **36.0%** (exceeds T2 limit) |
| Total Trades (n) | 145 (THIN) |
| 90d Cumulative | +230.8% |
| Asset Class | CRYPTO |

**Recent 3 Picks:**
| Symbol | Direction | PnL |
|--------|-----------|-----|
| STXUSDT | SHORT | -2.11% |
| STXUSDT | SHORT | -2.11% |
| STXUSDT | SHORT | -2.11% |

### 6c. rl_agent (BUILDING)

| Metric | Value |
|--------|-------|
| Win Rate | 60.0% |
| Profit Factor | 2.54 |
| Max Drawdown | 2.1% |
| Total Trades (n) | **5** (THIN - below 100-pick floor) |
| 90d Cumulative | +6.4% |
| Asset Class | CRYPTO |

### 6d. claude_gainer (BUILDING)

| Metric | Value |
|--------|-------|
| Win Rate | 56.2% |
| Profit Factor | 2.23 |
| Max Drawdown | 33.5% |
| Total Trades (n) | **32** (THIN - below 100-pick floor) |
| 90d Cumulative | +80.2% |
| Asset Class | CRYPTO |

---

## 7. FLAGGED DEGRADED SYSTEMS (HIGH ALERTS - 11 systems)

| System | Rolling 7d WR | Baseline WR | Drop | Action |
|--------|--------------|-------------|------|--------|
| cta_cross_asset_tsmom | 29% | 45% | >20% | REDUCE |
| myfxbook_retail_contrarian | 14-17% | 46% | >20% | REDUCE |
| ig_contrarian_sentiment | 19-20% | 45% | >20% | REDUCE |
| forex_rsi2_mean_reversion | 9-10% | 44% | >20% | REDUCE |
| futures_momentum | 4% | 42% | >20% | REDUCE |
| st_multi_day_momentum | 47% | 68% | >20% | REDUCE |
| macd_rsi_m048 | 53% | 73% | >20% | REDUCE |
| ema_momentum_m006 | 36% | 56% | >20% | REDUCE |
| luxalgo_confluence | 34% | 45% | >20% | REDUCE |
| hs_lb_None | 0% | 34% | >20% | REDUCE |
| crypto_vwap_volprofile_reversion_v1 | 0% | 32% | >20% | REDUCE |

### MEDIUM ALERTS (4 inactive systems)

| System | Issue |
|--------|-------|
| copy_trader_clones | No pick in 91h |
| stocksunify2 | No pick in 94h |
| kimi_riseoftheclaw | No pick in 72h |
| kimi_live_signals | No pick in 96h |

---

## 8. ACTIVE PICKS SUMMARY

| Metric | Value |
|--------|-------|
| Active Picks (of total) | 50-61 of 188-200 |
| Proven | 6 |
| Sandbox | 44-54 |
| Gated Out | 128-150 |

---

## 9. CLOSED PICKS PERFORMANCE

### 9a. Headline Metrics

| Metric | Value |
|--------|-------|
| Total Closed Picks | 3,382-3,386 |
| Win Rate | 34.8-35.0% |
| Total PnL | +949.43% to +986.01% |
| Excl. Outliers (+/-10% cap) | +773.66% to +810.25% (27 capped) |
| EW Compound (+/-500 cap, chrono) | +360,456% to +516,065% |
| Rolling 100 | +107.58% to +217.79% |
| Annualized Geomean | +9999.00% |
| Median Trade | -0.00% |
| Profit Factor | 1.49-1.51 |
| Expectancy | +0.28% to +0.29% |
| Avg Win / Avg Loss | +2.46-2.48% / -1.35% |
| W / L / F | 1178-1183 / 1440-1448 / 759-760 |
| Systems | 12-13 |

### 9b. Smart Snapshot

| Metric | Value |
|--------|-------|
| Smart Snapshot WR | 48.9% |
| Swing Picks | 49% (135) |
| Verified Alpha | 16-17 (27-34% of active) |
| Audited Source WR | 64.2-66.1% (13-15 covered) |
| Verified Realized WR | 33.8-34.2% (2520-2731 trades) |

---

## 10. MERCURY VALIDATION METRICS

| Metric | Value |
|--------|-------|
| Daily Volatility | 2.91% |
| Net Sharpe | 0.0894 (1.42 annualized) |
| Rolling 30d Max DD | N/A (filtered) |
| Signal-to-Trade | -- |
| Sortino | 0.1397 (2.22 annualized) |
| Calmar | N/A (filtered) |
| Sharpe (per-trade) | 0.1034 |
| Sharpe (per-trade, filtered) | 0.0268 |
| Sharpe (per-trade, annualized) | 4.58 |

---

## 11. ACTIVE PnL BY ASSET CLASS (LIVE)

| Asset Class | Active Picks | Smart Picks | Avg Score | FWR |
|-------------|-------------|-------------|-----------|-----|
| CRYPTO | 33 | 0 | 46.9 | 0.38 |
| EQUITY | 23 | 0 | 19.4 | 0.13 |
| FOREX | 2 | 0 | 32.5 | 0.55 |
| COMMODITY | 0 | 0 | 0.0 | 0.00 |
| FUTURES | 0 | 0 | 0.0 | 0.00 |
| BOND | 0 | 0 | 0.0 | 0.00 |
| ETF | 3 | 1 | 28.0 | 0.55 |

**Live Position Summary:**
- Active PnL (Live): -3.05% (61 picks with live prices)
- Active W/L (Live): 29W / 32L (48% currently green)

---

## 12. CRYPTO PERFORMANCE BY TIER

### All Tiers Combined
| Metric | Value |
|--------|-------|
| Win Rate | 46.5-46.6% |
| Total PnL | +506.23% |
| Active | 32 |
| Closed | 1450-1451 |
| W/L/F | 675/775/1 |
| Profit Factor | 1.39 |
| Avg PnL/trade | 0.35% |

### S-Tier (Elite)
| Metric | Value |
|--------|-------|
| Win Rate | **75.0%** |
| Active | 4 |
| Closed | 12 |
| W/L/F | 9/3/0 |
| Profit Factor | **7.22** |
| Realized PnL | +25.21% |
| Avg PnL/trade | **2.10%** |

### A-Tier
| Metric | Value |
|--------|-------|
| Win Rate | 45.5% |
| Active | 7 |
| Closed | 367 |
| W/L/F | 167/200/0 |
| Profit Factor | 1.39 |
| Realized PnL | +142.34% |
| Avg PnL/trade | 0.39% |

### B-Tier
| Metric | Value |
|--------|-------|
| Win Rate | 52.2% |
| Active | 9 |
| Closed | 592 |
| W/L/F | 309/282/1 |
| Profit Factor | **1.65** |
| Realized PnL | +289.69% |
| Avg PnL/trade | 0.49% |

### C-Tier
| Metric | Value |
|--------|-------|
| Win Rate | 39.6% |
| Active | 12 |
| Closed | 480 |
| W/L/F | 190/290/0 |
| Profit Factor | 1.10 |
| Realized PnL | +48.99% |
| Avg PnL/trade | 0.10% |

---

## 13. NON-CRYPTO PERFORMANCE

### Aggregate: 26.0% WR | +443.20% PnL | 28 active, 1935 closed

### Equities & Stocks
| Metric | Value |
|--------|-------|
| Win Rate | **54.4%** |
| Active | 23 |
| Closed | 272 |
| W/L/F | 148/109/15 |
| Profit Factor | **2.08** |
| Realized PnL | **+360.39%** |
| Avg PnL/trade | **1.32%** |
| Top Strategy | markov_zone_transition |

### Forex
| Metric | Value |
|--------|-------|
| Win Rate | 15.8% |
| Active | 2 |
| Closed | 1388 |
| W/L/F | 219/484/685 |
| Profit Factor | 0.52 |
| Realized PnL | **-91.58%** |
| Avg PnL/trade | -0.07% |
| Top Strategy | fx_smart_forex_rsi2_me... |

### Commodities
| Metric | Value |
|--------|-------|
| Win Rate | **43.7%** |
| Active | 0 |
| Closed | 167 |
| W/L/F | 73/40/54 |
| Profit Factor | **3.61** |
| Realized PnL | **+123.21%** |
| Avg PnL/trade | 0.74% |
| Top Strategy | cftc_cot_commercial_si... |

### ETFs
| Metric | Value |
|--------|-------|
| Win Rate | **58.2%** |
| Active | 3 |
| Closed | 98 |
| W/L/F | 57/38/3 |
| Profit Factor | 1.58 |
| Realized PnL | +52.62% |
| Avg PnL/trade | 0.54% |
| Top Strategy | rs-breakout-scout |

### Bonds
| Metric | Value |
|--------|-------|
| Win Rate | **50.0%** |
| Active | 0 |
| Closed | 12 |
| W/L/F | 6/5/1 |
| Profit Factor | 0.66 |
| Realized PnL | -1.53% |
| Avg PnL/trade | -0.13% |
| Top Strategy | betting-against-beta |

---

## 14. TIMEFRAME PERFORMANCE (Institutional-Grade Capped Stats)

| Period | Trades | Raw PnL | Capped PnL | Median | Avg Trade | PF | Sharpe | Outliers |
|--------|--------|---------|------------|--------|-----------|-----|--------|----------|
| Last 24h | 227 | +174.24% | +50.77% | -0.54% | +0.77% | **1.78** | 0.0759 | 8 |
| Last 7d | 1482 | +434.18% | +285.27% | -0.50% | +0.29% | 1.31 | 0.0729 | 15 |
| Last 30d | 5033 | +1247.30% | +1044.67% | +0.00% | +0.25% | 1.33 | 0.0882 | 33 |
| All Time | 9575 | +1119.34% | +1205.58% | -0.01% | +0.12% | 1.11 | 0.0424 | 189 |

---

## 15. PERFORMANCE BY SYSTEM CATEGORY

| Category | Systems | Active | Closed | Wins | Losses | Win Rate | Total PnL | PF |
|----------|---------|--------|--------|------|--------|----------|-----------|-----|
| Proven Systems | 4 | 4 | 4,699 | 152 | 136 | **52.8%** | +127.45% | **1.68** |
| Sandbox (Unproven) | 46 | 102 | 8,522 | 1,381 | 1,567 | 46.8% | +2170.57% | **2.18** |
| Probation | 16 | 27 | 46,275 | 2,694 | 2,893 | 48.2% | +1937.52% | 1.26 |
| **WR >= 50% (min 5)** | **16** | **37** | **8,087** | **1,161** | **731** | **61.4%** | **+2601.83%** | **2.45** |
| WR < 50% (min 5) | 43 | 96 | 51,392 | 3,065 | 3,862 | 44.2% | +1636.68% | 1.19 |

**Key Insight**: Trading only systems with WR >= 50% yields **61.4% WR** and **+2601.83% total PnL** vs +1636.68% for WR < 50% systems.

---

## 16. 2-HOUR TIMEFRAME STATS (Last 24h)

| Window (EST) | Opened | By Asset | Closed | By Asset | Avg PnL | WR |
|-------------|--------|----------|--------|----------|---------|-----|
| 05-11 14:25-16:25 | 9 | C:6,E:2,F:1 | 4 | C:3,E:1 | **+2.30%** | 50% |
| 05-11 12:25-14:25 | 37 | C:16,E:18,ET:2,F:1 | 17 | C:12,ET:2,F:3 | +1.64% | **88%** |
| 05-11 10:25-12:25 | 4 | C:4 | 21 | CM:1,C:16,F:4 | +1.88% | 52% |
| 05-11 08:25-10:25 | 3 | C:1,E:1,ET:1 | 11 | C:9,E:1,ET:1 | -0.59% | 27% |
| 05-11 06:25-08:25 | 0 | -- | 8 | C:7,F:1 | **+3.30%** | 63% |
| 05-11 04:25-06:25 | 0 | -- | 3 | CM:1,C:2 | **+3.99%** | **100%** |
| 05-11 02:25-04:25 | 0 | -- | 8 | C:7,F:1 | +1.05% | 38% |
| 05-11 00:25-02:25 | 0 | -- | 9 | C:8,F:1 | **+7.08%** | **78%** |
| 05-10 22:25-00:25 | 0 | -- | 45 | C:43,F:2 | -0.37% | 27% |
| 05-10 20:25-22:25 | 0 | -- | 15 | C:13,F:2 | +0.52% | 47% |
| 05-10 18:25-20:25 | 1 | C:1 | 15 | C:15 | +0.94% | 40% |
| 05-10 16:25-18:25 | 2 | C:2 | 74 | C:73,F:1 | -1.25% | 19% |

**24h Summary**: 56 opened | 230 closed | WR: 38.3% | Avg PnL: +0.41%

### 24h Asset Summary
| Asset | Opened | Closed | Total |
|-------|--------|--------|-------|
| COMMODITY | 0 | 2 | 2 |
| CRYPTO | 30 | 208 | **238** |
| EQUITY | 21 | 2 | 23 |
| ETF | 3 | 3 | 6 |
| FOREX | 2 | 15 | 17 |

---

## 17. CROSS-SYSTEM AGREEMENT MATRIX (4 Proven Systems)

Data: 19 raw signals -> 10 unique (deduped)

| System | BTC | ETH | SOL | XRP | BNB |
|--------|-----|-----|-----|-----|-----|
| super signals (143t, 51.1% WR) | -- | -- | -- | -- | -- |
| battleground (146t, 47.3% WR) | -- | -- | -- | LONG | -- |
| signal_validation (523t, 52.8% WR) | -- | LONG | -- | -- | -- |
| regime_terminal (71t, 36.2% WR) | -- | -- | LONG | -- | -- |
| **Agree (deduped)** | **2 LONG** | **2 LONG** | **2 LONG** | **2 LONG** | **2 LONG** |

---

## 18. QUALITY GATES & FILTERS

| Metric | Value |
|--------|-------|
| Total Active Before Gates | 242 |
| Active After Gates | 61 |
| Smart Picks Count | 2-3 |
| Smart Picks % | 3.3-28.3% |
| Filtered Out | 181 |
| Score Safety Net Applied | 6 |
| Score Safety Net Rejected | 1 |
| Duplicate Symbols Removed | 31 |
| Degradation - Severe | 9 strategies |
| Degradation - High | 3 strategies |
| Degradation - Lifting | 31 strategies |
| Strong Active Count | 21 |

### Display Tier Counts
| Tier | Count |
|------|-------|
| ELITE | 0 |
| PREMIUM | 0 |
| STANDARD | 32 |
| WATCH | 29 |

### HF Conviction Tiers
| Tier | Count |
|------|-------|
| S | 0 |
| A | 1 |
| B | 13 |

---

## 19. SYSTEM LIST (100+ Systems Identified)

**Proven/Named Systems**: aggregated_picks, alpha_engine, alpha_engine_fast, asterdex_paper, audit_ensemble, auto_dna_mutation, baby_strats_forward, battleground, battleground_mutations, breakout_a_sr, breakout_b_ml, breakout_c_spike, chatgpt_combined, claude_gainer, claude_gainer_ml_perf, claude_gainer_st, coinglass, combined_confidence_strategy, contested_picks, contrarian_consensus, contrarian_evolver, conviction_picks, copy_trader_clones, copy_trader_consensus, copy_trader_highscore, copy_trader_intel, copy_trader_variations, cot_positioning, crypto_gainer_ml, crypto_ml_edge, crypto_signal_engine, crypto_winners, cta_replicator, dna_confluence_mutations, dna_rapid_fire_mutations, dna_winner_picks, ensemble_evolver, etf_sector_rotation, failure_evolver, fast_stocks_competition, fc_crypto_pro, forex_copy_trader, forward_signals, genetic_programmer, genome, goldmine_meme, goldmine_stocks, goldmine_unified, hyperparam_dna, incubator_battleground, incubator_forward, incubator_gainer, incubator_pipeline, institutional_picks_engine, inverse_mutations, kimi_claw_research, kimi_live_signals, kimi_riseoftheclaw, kimi_signal_tracking, leveraged_etf_decay, live_position_monitor, luxalgo_filters, macd_dna_mutations, mape_evolver, maplestax_cbc, mega_mutation, mega_strategies, meme_scanner, mercury2, mercury2_fast, ml_bg_ensemble, ml_bg_system_a-f, ml_consensus, ml_crypto_pred, ml_crypto_pred_v12, ml_crypto_predictor, ml_gatekeeper, momentum_evolver, multi_asset, multi_asset_copytrader, multi_asset_cot, multi_asset_institutional, multi_asset_scanner, multitf_evolver, mutation_lab, neat_neural, non_crypto_consensus, non_crypto_enhanced, orphan_emitter_*, overnight_mutations, paper_trading, penny_screener, pm_kalshi_signals, pm_whale_signals, polymarket_signals, prediction_market_consensus, predictions, prop_firm_strategies, proven_strategies, quan_engine, rapid_fire, regime_terminal, riseoftheclaw, rl_agent, rocket_scanner, short_engine, signal_aggregator, signal_engine_mutations, signal_validation, skyrocket_detector, smart_money, stocks_competition, stocksunify2, super_signals, top_gainer_predictor, tradingagents, trusted_genome, tsmom_strategy, ueps, wf_audit_signals

---

## 20. CONCENTRATION RISK WARNINGS

### Overall Concentration
| Warning | Detail |
|---------|--------|
| **CRITICAL** | 215.4% of total PnL comes from USDCHF=X trades |
| Without USDCHF=X | Overall PnL drops from +202.8% to +639.7% |
| Top Symbol | USDCHF=X (-436.88% PnL) |

### Top 5 Symbols by PnL Impact (All Time)
| Symbol | PnL | % of Total |
|--------|-----|------------|
| USDCHF=X | -436.88% | 215.4% |
| INJUSDT | +311.42% | 153.5% |
| FETUSDT | +231.56% | 114.2% |
| AUDJPY=X | -205.87% | 101.5% |
| NZDJPY=X | -203.68% | 100.4% |

### Top 5 PnL Sources (Capped)
| Source System | Share % | PnL Capped Sum |
|--------------|---------|----------------|
| alpha_engine | 18.8% | 1,914.2 |
| kimi_riseoftheclaw | 13.5% | 1,370.77 |
| luxalgo_filters | 13.3% | 1,348.2 |
| baby_strats_forward | 8.6% | 876.99 |
| ml_bg_system_f | 5.0% | 507.95 |

---

## 21. BTC SCALPING STRATEGY REPLICATION (Research Dossier)

| Metric | Claimed | Actual |
|--------|---------|--------|
| Win Rate | 91.67% | NOT REPLICABLE |
| Reported Trades | 12 | - |
| Real Match | - | 2/12 trades matched real BTC data |
| Best Backtest | - | 40.00% (strongest observed rerun) |
| Practical WR | - | 60-75% (replacement strategy target) |
| Automation Confidence | - | 95% |
| Conflicts | - | 3 (intermediate files contradict final report) |

---

## 22. OPEN FORWARD TRADES BY SYSTEM (LIVE P/L)

| System | Open | Winners | Losers | Avg P/L | Total P/L | W/L | Best Pick | Worst Pick | Last Pick |
|--------|------|---------|--------|---------|-----------|-----|-----------|------------|-----------|
| riseoftheclaw | 5 | 3 | 2 | +0.85% | +4.2% | 1.5 | DOGE-USD +3.74% | ADA-USD -0.28% | BTC-USD -0.01% |
| dna winner picks | 1 | 1 | 0 | +0.59% | +0.6% | inf | JUPUSDT +0.59% | - | JUPUSDT +0.59% |
| non crypto consensus | 1 | 1 | 0 | +0.26% | +0.3% | inf | EURGBP=X +0.26% | - | EURGBP=X +0.26% |
| ml gatekeeper | 8 | 5 | 3 | +0.12% | +1.0% | 1.7 | SOXX +3.42% | UBER -3.06% | GBPUSD=X +0.36% |
| polymarket signals | 1 | 1 | 0 | +0.02% | +0.0% | inf | BTCUSDT +0.02% | - | BTCUSDT +0.02% |
| pm kalshi signals | 3 | 1 | 2 | +0.01% | +0.0% | 0.5 | BNBUSDT +0.16% | ETHUSDT -0.09% | ETHUSDT -0.09% |
| battleground | 1 | 0 | 1 | -0.36% | -0.4% | 0.0 | - | XRPUSDT -0.36% | XRPUSDT -0.36% |
| smart money | 2 | 0 | 2 | -0.40% | -0.8% | 0.0 | - | AMZN -0.51% | AMZN -0.51% |
| regime terminal | 4 | 1 | 3 | -0.42% | -1.7% | 0.3 | SOL-USD +1.67% | GOOGL -2.46% | GOOGL -2.46% |
| tsmom strategy | 3 | 1 | 2 | -1.21% | -3.6% | 0.5 | ONDOUSDT +2.33% | OSMOUSDT -4.92% | ONDOUSDT +2.33% |
| ueps | 16 | 6 | 10 | -12.47% | -199.5% | 0.6 | TXN +1.20% | MDT -99.99% | TXN +1.20% |

---

## 23. ISSUES & ERRORS OBSERVED

### Critical Database Issues
1. **PnL Integrity**: Only 42.0% integrity (58,000/100,000 mismatches >1pp)
2. **Ghost Rows**: 655,000 rows with constant pnl_pct (18 cohorts)
3. **Forward Validator**: 840h stale (last WON/LOST: April 2)
4. **Phantom EXPIRED**: 100% in 1 class (worst-case)
5. **Outcome Coverage**: Only 0.09% resolved (121/136,374)
6. **WON-vs-PnL Contradiction**: YES - writer bug detected

### System Degradation
- 11 HIGH-priority alerts for systems with >20% WR drop
- 4 MEDIUM-priority alerts for inactive systems (>72h no picks)
- 9 severe degradation strategies
- 3 high degradation strategies

### Data Quality
- 27 outlier trades capped at +/-10%
- 7 toxic/broken outliers purged (TRX, KATUSDT, Mercury2)
- High concentration risk: USDCHF=X accounts for 215.4% of total PnL

### Known Bugs
- Resolver v2 shipped 2026-04-28; v2.1 bug bundle 2026-05-02
- Historical re-resolve pending for pre-fix labels
- Two PF/WR figures may appear per class (headline vs recent panel)

---

## 24. SCREENSHOT FILE PATHS

| File | Path |
|------|------|
| Full Page Screenshot | `/mnt/agents/output/audit_dashboard_full.png` |

---

*Report compiled from live dashboard extraction and dashboard_data.json analysis.*
*All data current as of 2026-05-11, ~3:40-4:35 PM EST.*
*Disclaimer: This is NOT financial advice. All data is for educational and research purposes only.*
