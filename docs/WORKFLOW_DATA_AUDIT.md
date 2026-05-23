# Comprehensive Workflow & Data Output Audit
**Generated: 2026-03-25**

---

## Executive Summary

- **Total workflow files:** 240+ in `.github/workflows/`
- **Total data directories:** 43 across the repo
- **Dashboard sources wired:** 115 systems in `audit_trail/dashboard_generator.py` (JSON_PICK_SOURCES)
- **Dashboard payload:** 115 systems, 379 active picks, 14,016 closed picks
- **MySQL tables (ejaguiar1_stocks):** 6 tables (at_audit_events, at_discord_notifications, at_discord_gate_log, at_filter_log, at_local_picks, at_signal_outcomes, strategy_registry)
- **Isolated high-value signals found:** YES — see Section 5

---

## Section 1: All Workflow Categories & Data Outputs

### 1A. Core Pick Scanners (Generate Active Picks)

| Workflow | System | Output Path | Schedule | Asset Class | Feeds Dashboard? |
|---|---|---|---|---|---|
| `alpha-engine-live.yml` | alpha_engine | `alpha_engine/data/active_picks.json` | Every 45 min | Multi (crypto, forex, equity) | YES |
| `alpha-engine-fast.yml` | alpha_engine_fast | `alpha_engine/data/active_picks_fast.json` | Every 30 min | Crypto | YES |
| `alpha-gainer-capture.yml` | gainer_capture | `alpha_engine/data/gainer_capture_picks.json` | Every 30 min | Crypto | YES (via alpha_engine merge) |
| `alpha-quant-stack.yml` | quant_stack | `alpha_engine/data/active_picks.json` (merged) | Every 30 min | Crypto | YES |
| `alpha-trend-catcher.yml` | trend_catcher | `alpha_engine/data/active_picks.json` (merged) | Every 4h | Crypto | YES |
| `kimi-feb172026-live.yml` | kimi_riseoftheclaw | `KIMI_RISEOFTHECLAW/data/active_picks.json` | Every 15 min | Crypto | YES |
| `now-scanner.yml` | rapid_fire | `rapid_fire_data/active_picks.json` | Frequent | Crypto | YES |
| `mercury2-scan.yml` | mercury2 | `mercury2/data/active_picks.json` | Per schedule | Crypto | YES |
| `crypto-ml-edge.yml` | crypto_ml_edge | `crypto_ml_edge/data/active_picks.json` | Every 30 min | Crypto | YES |
| `claude-gainer-ml-live.yml` | claude_gainer | `claude_gainer_ml/tracker/claude_live_picks.json` | Every 30 min | Crypto | YES |
| `claude-gainer-short-term.yml` | claude_gainer_st | `claude_gainer_ml/tracker/short_term_active.json` | Every 30 min | Crypto | YES |
| `quan-engine-live.yml` | quan_engine | `quan_engine/data/active_signals.json` | Per schedule | Crypto | YES |
| `copy-trader-intelligence.yml` | copy_trader_intel | `copy_trader_intel/data/active_picks.json` | Every 15 min | Crypto | YES |
| `multi-asset-scanner.yml` | multi_asset | `multi_asset/data/active_picks.json` | Per schedule | Multi (forex, equity, crypto) | YES |
| `proven-strategies-scanner.yml` | proven_strategies | `proven_strategies/data/proven_strategy_picks.json` | Per schedule | Crypto | YES |
| `signal-engine.yml` | crypto_signal_engine | `crypto_signal_engine/data/active_picks.json` | Per schedule | Crypto | YES |
| `coinglass-scanner.yml` | coinglass | `coinglass_strategies/data/active_picks.json` | Hourly | Crypto | YES |
| `smart-money-tracker.yml` | smart_money | `smart_money/data/active_picks.json` | Per schedule | Equity | YES |
| `breakout-arena.yml` | breakout_a/b/c | `breakout_arena/*/data/active_picks.json` | Hourly | Crypto | YES |
| `regime-terminal.yml` | regime_terminal | `regime_terminal/data/active_signals.json` | Per schedule | Crypto | YES (informational) |
| `asterdex-paper-trading.yml` | asterdex_paper | `trading/data/dashboard_data.json` | Hourly | Crypto | YES |
| `ml-battleground-a.yml` through `f.yml` | ml_bg_system_a-f | `ml_battleground/system_*/data/active_picks.json` | Per schedule | Crypto | YES |
| `ml-battleground-ensemble.yml` | ml_bg_ensemble | `ml_battleground/ensemble_data/active_picks.json` | Per schedule | Crypto | YES |
| `antigravity-claudeopus.yml` | (various) | Merges into alpha_engine | Hourly | Crypto | YES (indirect) |
| `meta-strategy.yml` | meta_strategy | `meta_strategy/data/active_picks.json` | Per schedule | Multi | YES |
| `rl-agent-ppo.yml` | rl_agent | `rl_agent/data/active_picks.json` | Per schedule | Crypto | YES |

### 1B. DNA/Genome Evolution Systems

| Workflow | System | Output Path | Feeds Dashboard? |
|---|---|---|---|
| `genome-daily-pipeline.yml` | genome/dna_* | `genome/data/*.json` (12+ pick files) | YES (all wired) |
| `genome-evolution.yml` | genome | `quant_lab/genome_results/` | NO (research only) |
| `dna-mutation-cycle.yml` | macd_dna_mutations, etc. | `genome/data/*_mutation_picks.json` | YES |
| `overnight-mutations.yml` | overnight_mutations | `alpha_engine/data/massive_mutation_results.json` | YES |
| `mega-mutation-tracker.yml` | mega_mutation | `genome/data/mega_mutation_picks.json` | YES |
| `darwin-evolution.yml` | darwin | `genome/data/darwin_portfolios.json` | Partial |
| `mutation-lab.yml` | mutation_lab | `genome/data/mutation_lab_picks.json` | YES |
| `dna_strategy_pipeline.yml` | (various) | Multiple genome data files | YES (mostly) |

### 1C. Aggregation & Consensus Systems

| Workflow | System | Output Path | Feeds Dashboard? |
|---|---|---|---|
| `cross-aggregator.yml` | super_signals | `cross_aggregation/data/super_signals.json` | YES |
| `consensus-outcome-tracker.yml` | aggregated_picks | `cross_aggregation/data/consensus_outcomes.json` | YES |
| `conviction-picks.yml` | conviction_picks | `cross_aggregation/data/conviction_picks.json` | YES |
| `contested-pick-checker.yml` | contested_picks | `cross_aggregation/data/contested_picks_tracker.json` | YES |
| `hourly-master-picks.yml` | (hub) | `hub/data/` | Partial |
| `signal-recorder.yml` | signal_recorder | `signal_recorder/data/winning_combos.json` | NO (analytics only) |

### 1D. Validation, Tracking & Analytics (No Pick Generation)

| Workflow | Purpose | Output | Feeds Dashboard? |
|---|---|---|---|
| `alpha-verify-predictions.yml` | Verify prediction outcomes | `alpha_engine/data/prediction_verification_log.json` | NO (validation) |
| `alpha-weekly-validation.yml` | Weekly stats | Reports | NO |
| `audit-dashboard.yml` | Generate dashboard payload | `audit_trail/data/dashboard_payload.json` | IS the dashboard |
| `audit-impact-tracker.yml` | Track audit improvements | `battleground/data/audit_impact_results.json` | NO (analytics) |
| `continuous-improvement-monitor.yml` | Monitor improvements | `alpha_engine/data/continuous_improvement_report.json` | NO |
| `benchmark-comparison.yml` | BTC/ETH benchmark | Reports | NO |
| `signal-quality-monitor.yml` | Signal quality tracking | Analytics | NO |
| `strategy-health-monitor.yml` | Strategy health | `strategy_health/data/banned_strategies.json` | YES (bans) |
| `strategy-health-report.yml` | Health reports | Reports | NO |
| `prediction-quality-tracker.yml` | Track prediction quality | Analytics | NO |
| `pick-monitor-30min.yml` | Monitor active picks | Analytics | NO |
| `what-worked-insights.yml` | Post-hoc analysis | `alpha_engine/data/what_worked.json` | NO (research) |
| `winner-pattern-scanner.yml` | Winner pattern mining | `alpha_engine/data/winner_pattern_analysis.json` | NO (research) |

### 1E. Backtesting & Forward Testing

| Workflow | Purpose | Output | Feeds Dashboard? |
|---|---|---|---|
| `backtest-and-deploy.yml` | KIMI backtest + deploy | `KIMI_CLAW_RESEARCH_FEB162026/data/` | YES (paper_only) |
| `battleground-mass-backtest.yml` | Mass backtest strategies | `battleground/data/` | NO (backtest) |
| `walk-forward-backtest.yml` | Walk-forward validation | `alpha_engine/data/walk_forward_results.json` | NO |
| `forward-test-daily.yml` | Daily forward test | Various | Partial |
| `baby-strat-forward-paper.yml` | Baby strategy testing | `baby_strategies/data/` | YES (via special handler) |
| `copy-trader-forward-test.yml` | CT forward test | `alpha_engine/data/portfolio_copytrader.json` | YES (portfolio) |
| `forward-tracking-v2.yml` | Forward tracking | Various | Partial |

### 1F. Stock & Non-Crypto Systems

| Workflow | System | Output | Asset Class | Feeds Dashboard? |
|---|---|---|---|---|
| `fast-stocks-competition.yml` | fast_stocks_competition | `STOCKS/competition/fast_forward_picks.json` | Equity | YES |
| `algorithm-competition-refresh.yml` | stocks_competition | `STOCKS/competition/forward_picks.json` | Multi | YES |
| `daily-stock-refresh.yml` | (support) | Stock price data | Equity | NO (data) |
| `weekly-stock-simulation.yml` | (simulation) | Simulation results | Equity | NO |
| `analyst-tracker.yml` | predictions | `predictions/data/*.json` | Crypto | YES |
| `forex-smart-picks.yml` | (forex) | Merged into multi_asset | Forex | YES (indirect) |

### 1G. Deployment & Infrastructure (No Signal Data)

| Workflow | Purpose |
|---|---|
| `deploy-pages.yml` | Deploy GitHub Pages |
| `deploy-riseoftheclaw.yml` | Deploy KIMI dashboard to 50webs/GoDaddy |
| `deploy-alpha-dashboard.yml` | Deploy alpha dashboard |
| `deploy-battleground-ftp.yml` | Deploy battleground to FTP |
| `deploy-competition-to-site.yml` | Deploy competition page |
| `mirror-site.yml` | Mirror site to alternate domain |
| `discord-bot.yml` / `discord-heartbeat.yml` / `discord-status.yml` | Discord integration |
| `actions-failure-guardian.yml` | Monitor failed actions |
| `system-health-check.yml` | System health monitoring |
| Various `deploy-*` and `torontoevent-*` workflows | FTP deployment |

### 1H. Non-Trading Workflows

| Workflow | Purpose |
|---|---|
| `scrape-events.yml` | Toronto events scraping |
| `fetch-movies.yml` / `fetch-movies-v3.yml` | Movie data |
| `sports-betting-refresh.yml` | Sports data |
| `send-event-notifications.yml` | Event notifications |
| `refresh-creator-updates.yml` | Creator content |
| `taste-profile-scan.yml` | Entertainment preferences |

---

## Section 2: Data Directory Inventory

### Active Picks by Source (Current State)

| Source | Active Picks | Closed Picks | Win Rate | Avg PnL | In Dashboard? |
|---|---|---|---|---|---|
| **ml_crypto_predictor** | 3 | 985 | **57.4%** | +5.18% | YES |
| **battleground** | 3 | 100 | **59.0%** | +0.31% | YES |
| **ml_bg_system_f** | 0 | 98 | **50.5%** | +0.54% | YES |
| **mercury2** | 0 | 71 | **49.3%** | +0.78% | YES |
| **claude_gainer_st** | 2 | 2,000 | 44.6% | +0.14% | YES |
| **alpha_engine_fast** | 0 | 313 | 44.4% | -0.34% | YES |
| **baby_strats_forward** | 0 | 5,755 | 43.3% | +0.01% | YES |
| **alpha_engine** | 1 | 504 | 42.3% | +2.16% | YES |
| **claude_gainer** | 6 | 188 | 42.3% | +0.20% | YES |
| **kimi_riseoftheclaw** | 22 | 427 | 37.4% | -0.78% | YES |
| **luxalgo_filters** | 3 | 312 | 35.4% | -0.09% | YES |
| **super_signals** | 21 | 80 | 32.1% | +0.33% | YES |
| **multi_asset** | 72 | 105 | 24.1% | -0.57% | YES |
| **quan_engine** | 5 | 47 | 0.0%* | +0.00%* | YES (no PnL tracking) |
| **copy_trader_intel** | 10 | 49 | 0.0%* | +0.00%* | YES (no PnL tracking) |
| **rapid_fire** | 79 | 334 | 0.0%* | +0.00%* | YES (no PnL tracking) |
| **predictions** | 0 | 324 | 0.0%* | +0.00%* | YES (no PnL tracking) |
| **goldmine_stocks** | 37 | 14 | 0.0%* | +0.00%* | YES (no PnL tracking) |

*Systems marked 0.0% WR with +0.00% avg_pnl have no price validation running -- picks are wired but outcomes are not resolved.*

### Consensus Outcomes Tracker (cross_aggregation/data/consensus_outcomes.json)

| Agreement Level | Win Rate | Sample Size | Avg PnL |
|---|---|---|---|
| 2 sources agree | 45% | 94 | +2.17% |
| 3 sources agree | 69% | 13 | +1.80% |
| 4 sources agree | 55% | 11 | +1.26% |
| 5 sources agree | **82%** | 11 | +1.94% |
| 6 sources agree | **86%** | 7 | -0.03% |
| 7 sources agree | **100%** | 4 | +1.14% |
| 8 sources agree | **100%** | 3 | +1.57% |

**Key finding:** 5+ source agreement has 82-100% WR on 25 closed picks.

### Consensus Outcomes by Source System (Best Performers)

| System | Consensus WR | Picks | Avg PnL |
|---|---|---|---|
| genome | **100%** | 28 | +1.74% |
| incubator_fwd | **100%** | 23 | +1.62% |
| ml_crypto_pred | **100%** | 20 | +4.08% |
| coinglass_strategies | **100%** | 15 | +1.40% |
| claude_gainer_st | **97%** | 30 | +1.67% |
| mercury2 | **89%** | 9 | +4.54% |
| luxalgo_filters | **88%** | 16 | +1.87% |
| battleground | **87%** | 15 | +1.56% |
| quan_engine | **81%** | 27 | +2.38% |
| crypto_ml_edge | **70%** | 33 | +1.15% |
| kimi | **66%** | 41 | +1.35% |

---

## Section 3: MySQL Database (ejaguiar1_stocks @ mysql.50webs.com)

### Tables Found in Code

| Table | Written By | Purpose |
|---|---|---|
| `at_discord_notifications` | `audit_trail/mysql_client.py` | Every Discord send (picks, TP/SL hits) |
| `at_discord_gate_log` | `audit_trail/mysql_client.py` | Gate decisions (pass/reject with reason) |
| `at_local_picks` | `audit_trail/backfill_local_sources.py` | Backfill from local SQLite/JSON |
| `at_audit_events` | `audit_trail/backfill_local_sources.py` | Audit event log |
| `at_signal_outcomes` | `audit_trail/backfill_local_sources.py` | Signal outcome tracking |
| `at_filter_log` | `audit_trail/backfill_local_sources.py` | Pick filter decisions |
| `strategy_registry` | `audit_trail/build_strategy_registry.py` | Strategy metadata catalog |

### Workflows Writing to MySQL

- `alpha-engine-live.yml` (via audit_sync)
- `audit-dashboard.yml` (mysql_sync_permutations)
- `claude-gainer-short-term.yml` (backfill)
- `consensus-outcome-tracker.yml` (outcome tracking)
- `db-backup-email.yml` (backup)
- `db-sync-to-mirror.yml` (mirror sync)
- `dna_strategy_pipeline.yml` (strategy registry)
- `hoffman-tracker.yml` (backfill)
- `incubator-pipeline.yml` (backfill)
- `mega-mutation-tracker.yml` (backfill)
- `now-scanner.yml` (backfill)
- `strategy-health-monitor.yml` (bans)
- `strategy-health-report.yml` (reports)

### What's NOT Being Written to MySQL

The MySQL database receives **Discord events and pick gate decisions** but does NOT receive:
1. Full pick lifecycle (open → price update → close) for most systems
2. Win/loss outcomes from the dashboard_payload
3. Strategy performance metrics
4. Consensus agreement data
5. Portfolio P&L tracking

The local SQLite (`data/audit_trail.db`) is the primary audit store. MySQL is secondary (Discord audit + backfill).

---

## Section 4: Systems with 0% WR / No PnL Tracking (Dashboard-Wired but Broken)

These systems ARE wired into the dashboard but show 0% WR because their picks never get price-validated:

| System | Active | Closed | Issue |
|---|---|---|---|
| `quan_engine` | 5 | 47 | No TP/SL price validation |
| `copy_trader_intel` | 10 | 49 | No outcome resolution |
| `copy_trader_highscore` | 0 | 19 | No outcome resolution |
| `copy_trader_clones` | 0 | 40 | No outcome resolution |
| `copy_trader_consensus` | 4 | 13 | No outcome resolution |
| `rapid_fire` | 79 | 334 | No outcome resolution |
| `predictions` | 0 | 324 | No outcome resolution |
| `goldmine_stocks` | 37 | 14 | No outcome resolution |
| `kimi_signal_tracking` | 11 | 169 | No PnL calculation |
| `revival_*` (7 systems) | 0 | 284 total | No outcome resolution |
| `genetic_programmer` | 0 | 50 | No outcome resolution |
| `ensemble_evolver` | 0 | 25 | No outcome resolution |
| `mape_evolver` | 0 | 27 | No outcome resolution |

**Total: ~1,400+ closed picks with NO win/loss tracking.**

---

## Section 5: TOP 5 Isolated / Under-Utilized Signal Sources to Integrate

### 1. Consensus Outcomes with 5+ Agreement (HIGHEST PRIORITY)
- **Location:** `cross_aggregation/data/consensus_outcomes.json`
- **Current state:** 113 active, 143 closed, overall 55.2% WR
- **Key finding:** When 5+ sources agree: **82-100% WR** on 25 picks with +1.57% avg PnL
- **Issue:** This data IS tracked but the high-agreement signals are NOT surfaced as a separate "conviction" tier in the dashboard. The consensus WR by agreement level is buried.
- **Action:** Create a `consensus_5plus` virtual system that only surfaces picks with 5+ source agreement. These are the highest-conviction signals in the entire platform.

### 2. Copy Trader Intelligence — No Price Validation (49 closed, 0% tracked WR)
- **Location:** `copy_trader_intel/data/active_picks.json` (39 picks)
- **Sub-systems:** highscore (19), clones (40), consensus (17), variations (0)
- **Current state:** 10 active + 49 closed = fully wired, but ALL show 0% WR because no price validation runs
- **Issue:** These are real Hyperliquid/Binance/BingX trader positions (on-chain verified). They have entry_price, take_profit, stop_loss fields but no outcome resolver.
- **Action:** Wire `copy_trader_intel` closed picks into the price validation pipeline (similar to how `claude_gainer_st` resolves TP_HIT/SL_HIT). The `copy-trader-forward-test.yml` workflow exists but only tracks portfolio PnL, not individual pick outcomes.

### 3. Quan Engine — 107 Active Signals, 0% Tracked WR
- **Location:** `quan_engine/data/active_signals.json` (107 picks, 47 closed)
- **Schedule:** Runs via `quan-engine-live.yml`
- **Current state:** Has `audit_push.py` that writes to audit trail, but closed picks show 0% WR
- **Issue:** The audit push may be writing picks but not resolving outcomes. With 107 active signals this is the highest active-pick count outside multi_asset and rapid_fire.
- **Action:** Verify `quan_engine/audit_push.py` includes outcome resolution. If not, add TP/SL price checking.

### 4. Rapid Fire (NOW.py) — 500 Picks in now_picks.json, No Outcome Resolution
- **Location:** `rapid_fire_data/now_picks.json` (500 picks), `rapid_fire_data/active_picks.json` (1 pick)
- **Schedule:** `now-scanner.yml` runs frequently
- **Current state:** 79 active + 334 closed in dashboard, ALL 0% WR
- **Issue:** NOW.py generates high-frequency 1h crypto picks but none get price-validated. The 500 picks in now_picks.json are treated as the "closed" path but have no outcome field.
- **Action:** Add price validation to the NOW scanner workflow. With 500+ picks, even a modest WR improvement would be statistically significant and could identify time-of-day or volatility patterns.

### 5. Predictions/Analyst Tracker — 324 Closed, 0% Tracked WR
- **Location:** `predictions/data/active_predictions.json` (324 picks)
- **Schedule:** `analyst-tracker.yml` runs every 4h
- **Current state:** Analyst leaderboard exists (`predictions/data/analyst_leaderboard.json`) but currently has 0 analysts, 0 active calls
- **Issue:** The scraper may be failing or the analyst sources dried up. 324 "closed" predictions have no outcome tracking.
- **Action:** Check if `analyst-tracker.yml` is successfully scraping. Fix the pipeline so analyst calls get price-validated. If analysts are producing real signals, this is a completely untapped alpha source.

---

## Section 6: Additional Findings

### Workflow Count by Category
- **Pick scanners:** ~35 workflows generating trading signals
- **DNA/Genome evolution:** ~10 workflows mutating/evolving strategies
- **Aggregation/consensus:** ~5 workflows combining signals
- **Validation/tracking:** ~15 workflows verifying outcomes
- **Backtesting:** ~10 workflows running backtests
- **Deployment:** ~25 workflows deploying to FTP/Pages
- **Discord:** ~8 workflows sending notifications
- **Non-trading:** ~10 workflows (events, movies, etc.)
- **Other (monitoring, health, etc.):** ~120+ workflows

### Data Volume
- `alpha_engine/data/`: **284 JSON files** (largest data directory)
- `battleground/data/`: ~30 JSON files
- `genome/data/`: ~30 JSON files
- `copy_trader_intel/data/`: ~15 JSON files
- `cross_aggregation/data/`: ~10 JSON files

### Key Insight: The Dashboard IS Comprehensive
The `audit_trail/dashboard_generator.py` `JSON_PICK_SOURCES` list contains **114 source tuples** covering virtually every pick-generating system. The issue is NOT that signals are isolated from the dashboard -- it's that **many wired systems have no outcome resolution**, so they show 0% WR despite having real picks.

### The Real Problem: Price Validation Gap
Of 115 dashboard systems:
- **26 systems** have real WR tracking (non-zero outcomes)
- **~50 systems** have closed picks but 0% WR (no price validation)
- **~39 systems** have 0 active + 0 closed picks (dormant/empty)

**Fix priority:** Adding price validation to the top 5 systems above would add ~2,000+ resolved picks to the dashboard, dramatically increasing statistical significance and potentially revealing hidden edge.

---

## Section 7: Quick Reference — All Data Directories

| Directory | Files | Purpose | Dashboard Wired? |
|---|---|---|---|
| `alpha_engine/data/` | 284 | Core engine picks + analytics | YES |
| `audit_trail/data/` | DB + payload | Dashboard payload, SQLite | IS the dashboard |
| `audit_dashboard/data/` | AI challenge picks | AI challenge curators | YES |
| `battleground/data/` | ~30 | Battleground picks + backtests | YES |
| `genome/data/` | ~30 | DNA evolution picks | YES |
| `copy_trader_intel/data/` | ~15 | Copy trader picks | YES (no PnL) |
| `cross_aggregation/data/` | ~10 | Consensus/conviction signals | YES |
| `mercury2/data/` | ~8 | Mercury2 scanner | YES |
| `crypto_signal_engine/data/` | ~6 | Signal engine | YES |
| `crypto_ml_edge/data/` | ~2 | ML Edge scanner | YES |
| `claude_gainer_ml/data/` | ~3 | Gainer ML predictions | YES (tracker/) |
| `quan_engine/data/` | ~2 | Quant engine | YES (no PnL) |
| `regime_terminal/data/` | ~2 | Regime classifier | YES (informational) |
| `rapid_fire_data/` | ~3 | NOW.py rapid picks | YES (no PnL) |
| `signal_recorder/data/` | ~1 | Winning combos | NO (analytics) |
| `proven_strategies/data/` | ~1 | Research-backed picks | YES |
| `multi_asset/data/` | ~10 | Forex + equity + crypto | YES |
| `predictions/data/` | ~4 | Analyst predictions | YES (no PnL) |
| `signal_aggregator/data/` | ~7 | Signal aggregation hub | YES |
| `smart_money/data/` | ~1 | Equity analyst ratings | YES |
| `coinglass_strategies/data/` | ~2 | Coinglass liquidation data | YES |
| `meta_strategy/data/` | ~7 | Meta-strategy combos | YES |
| `ml_crypto_predictor/data/` | ~1 | ML predictor cache | YES |
| `baby_strategies/data/` | ~1 | Baby strategy backtests | YES (via handler) |
| `asterdex_paper/data/` | ~2 | Paper trading | YES |
| `skyrocket_detector/data/` | ~2 | Skyrocket alerts | NO |
| `KIMI_RISEOFTHECLAW/data/` | ~20 | KIMI scanner | YES |
| `riseoftheclaw/data/` | ~10 | Legacy KIMI | YES |
| `STOCKS/competition/` | ~8 | Stock competition | YES |
| `live_monitor/data/` | ~2 | Position monitoring | YES |
| `paper_trading/data/` | varies | Paper trading | YES |
| `ml_battleground/` (6 subdirs) | varies | ML battleground A-F | YES |
| `breakout_arena/` (3 subdirs) | varies | Breakout approaches | YES |
| `hub/data/` | ~1 | Hub state | Partial |
| `trading/data/` | ~3 | AsterDEX paper trading | YES |
| `portfolio_tracker/data/` | ~1 | Portfolio metrics | YES (portfolio) |
| `rl_agent/data/` | varies | RL agent picks | YES |
| `incubator/` | varies | Strategy incubation | YES (forward_signals) |
| `KIMI_FEB172026/data/` | ~1 | Legacy KIMI Feb 2026 | YES |
| `KIMI_CLAW_RESEARCH_FEB162026/data/` | ~5 | Research portfolio | YES (paper_only) |
| `STOCKSUNIFY/data/` | ~1 | Stock unification | NO |
| `sandbox/data/` | varies | Sandbox testing | NO |
| `tournament_agents/data/` | varies | Tournament agents | NO |
| `parallel_agent/data/` | varies | Parallel agent | NO |
| `pine_generator/data/` | varies | Pine script data | NO |
| `daily-feed/data/` | varies | Daily feed | NO |
| `updates/data/` | varies | Updates page data | NO |
