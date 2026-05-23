# GitHub Actions — Workflow Inventory

_Last updated 2026-05-15_

All **315** workflows under `.github/workflows/`. For each: triggers, cron schedules, jobs, the script files it runs, and JSON artifacts it reads/writes. Regenerate with `tools/_gen_gh_actions_doc.py`.

## Index

- [`2hour_challenge.yml`](#2hour_challengeyml) — 2hour-challenge · workflow_dispatch:
- [`_dynamic-runner-template.yml`](#_dynamic-runner-templateyml) — Dynamic Runner Template · workflow_call:
- [`ab_analysis.yml`](#ab_analysisyml) — A/B Analysis + Zero-PnL Audit · schedule:
- [`actions-failure-guardian.yml`](#actions-failure-guardianyml) — actions-failure-guardian · workflow_dispatch:
- [`adaptive-trust-tuner.yml`](#adaptive-trust-tuneryml) — ALPHA ENGINE - Adaptive Trust Tuner · schedule:
- [`algorithm-competition-refresh.yml`](#algorithm-competition-refreshyml) — Algorithm Competition Refresh · schedule:
- [`alpha-engine-bond.yml`](#alpha-engine-bondyml) — ALPHA ENGINE - Bond Emitter · schedule:
- [`alpha-engine-daily-picks.yml`](#alpha-engine-daily-picksyml) — Alpha Engine  Daily Picks · schedule:
- [`alpha-engine-etf.yml`](#alpha-engine-etfyml) — ALPHA ENGINE - ETF Emitter · schedule:
- [`alpha-engine-fast.yml`](#alpha-engine-fastyml) — ALPHA ENGINE FAST Tighter TP/SL, Shorter Holds · schedule:
- [`alpha-engine-live.yml`](#alpha-engine-liveyml) — ALPHA ENGINE - Live Autonomous Scanner · schedule:
- [`alpha-gainer-capture.yml`](#alpha-gainer-captureyml) — ALPHA ENGINE Gainer Capture (15min) · schedule:
- [`alpha-quant-stack.yml`](#alpha-quant-stackyml) — ALPHA ENGINE - Quant Stack (KAMA + ATR + Regime) · schedule:
- [`alpha-trend-catcher.yml`](#alpha-trend-catcheryml) — ALPHA ENGINE - Trend Catcher (4H Adaptive) · schedule:
- [`alpha-verify-predictions.yml`](#alpha-verify-predictionsyml) — ALPHA  Verify Predictions · schedule:
- [`alpha-weekly-validation.yml`](#alpha-weekly-validationyml) — Alpha Engine - Weekly Validation Suite · schedule:
- [`analyst-tracker.yml`](#analyst-trackeryml) — Analyst Tracker  Top 20 Crypto Analysts · schedule:
- [`antigravity-claudeopus.yml`](#antigravity-claudeopusyml) — ANTIGRAVITY-CLAUDEOPUS  Live Picks & Discord · schedule:
- [`asset-class-freshness-watchdog.yml`](#asset-class-freshness-watchdogyml) — Asset Class Freshness Watchdog · schedule:
- [`asterdex-paper-trader.yml`](#asterdex-paper-traderyml) — AsterDEX Paper Trader (DISABLED) · workflow_dispatch
- [`asterdex-paper-trading.yml`](#asterdex-paper-tradingyml) — AsterDEX Paper Trading · schedule:
- [`audit-dashboard.yml`](#audit-dashboardyml) — Unified Audit Dashboard · —
- [`audit-drift-telemetry.yml`](#audit-drift-telemetryyml) — Audit Drift Telemetry · push:
- [`audit-impact-tracker.yml`](#audit-impact-trackeryml) — Audit Impact Tracker · schedule:
- [`auto-retire-daily.yml`](#auto-retire-dailyyml) — Auto-Retire — Daily Bleeder Check · schedule:
- [`automated-reporting.yml`](#automated-reportingyml) — Automated Reporting · schedule:
- [`autonomous_trading.yml`](#autonomous_tradingyml) — Autonomous Trading Bot - Runs Automatically Every 4 Hours · schedule,push,workflow_dispatch
- [`baby-strat-forward-paper.yml`](#baby-strat-forward-paperyml) — Baby Strat Real Forward Monitor · push:
- [`backfill-features.yml`](#backfill-featuresyml) — Backfill OHLCV Features · schedule:
- [`backfill.yml`](#backfillyml) — Backfill Missing Audit Trail Sources · schedule:
- [`backtest-and-deploy.yml`](#backtest-and-deployyml) — Run Backtests & Deploy Dashboards · schedule:
- [`battle_test.yml`](#battle_testyml) — Real-Time Battle Test - Eliminate Losers, Optimize Winners · schedule,push,workflow_dispatch
- [`battleground-mass-backtest-part2.yml`](#battleground-mass-backtest-part2yml) — Battleground Mass Backtest (Part 2 - Babies) · workflow_dispatch:
- [`battleground-mass-backtest.yml`](#battleground-mass-backtestyml) — Battleground Mass Backtest · workflow_dispatch:
- [`benchmark-comparison.yml`](#benchmark-comparisonyml) — Benchmark Comparison  Daily · schedule:
- [`blacklist-reconciler.yml`](#blacklist-reconcileryml) — Blacklist Reconciler (cross-check vs live systems) · schedule:
- [`bond-agent.yml`](#bond-agentyml) — Bond Agent · schedule:
- [`breakout-arena.yml`](#breakout-arenayml) — Breakout Arena  3 Approaches · schedule:
- [`buy-now-analysis.yml`](#buy-now-analysisyml) — Buy Now Analysis & Tracking · schedule:
- [`check-streamer-status.yml`](#check-streamer-statusyml) — Check Streamer Live Status · schedule:
- [`ci-tests.yml`](#ci-testsyml) — CI Tests · —
- [`claude-gainer-ml-live.yml`](#claude-gainer-ml-liveyml) — Claude Gainer ML  Live Scanner · schedule:
- [`claude-gainer-short-term.yml`](#claude-gainer-short-termyml) — Claude Gainer Short-Term Predictor · schedule:
- [`claude-gainer-tracker.yml`](#claude-gainer-trackeryml) — Claude Code Gainer ML Tracker · schedule:
- [`claudes-test-portfolios.yml`](#claudes-test-portfoliosyml) — Claude's Test - Portfolio Manager · schedule:
- [`clear-channel-command.yml`](#clear-channel-commandyml) — Clear Channel Command · workflow_dispatch:
- [`closed-picks-command.yml`](#closed-picks-commandyml) — Closed Picks Command · workflow_dispatch:
- [`coinglass-scanner.yml`](#coinglass-scanneryml) — Coinglass DNA Scanner · schedule:
- [`commodities-agent.yml`](#commodities-agentyml) — Commodities Agent · schedule:
- [`conflict-marker-check.yml`](#conflict-marker-checkyml) — Conflict Marker Check · —
- [`consensus-outcome-tracker.yml`](#consensus-outcome-trackeryml) — Consensus Outcome Tracker · schedule:
- [`contested-pick-checker.yml`](#contested-pick-checkeryml) — Contested Pick Checker (Claude vs Antigravity) · schedule:
- [`continuous-improvement-monitor.yml`](#continuous-improvement-monitoryml) — Continuous Improvement Monitor · schedule:
- [`conviction-picks.yml`](#conviction-picksyml) — Conviction Picks Ultra-Selective Discord Alert · workflow_dispatch:
- [`copy-trader-forward-test.yml`](#copy-trader-forward-testyml) — Copy Trader Forward Test · schedule:
- [`copy-trader-intelligence.yml`](#copy-trader-intelligenceyml) — Copy Trader Intelligence  Scrape + Analyze + Track · schedule:
- [`copytrader-tracker.yml`](#copytrader-trackeryml) — Copy Trader Portfolio Tracker · schedule:
- [`correlation-monitor.yml`](#correlation-monitoryml) — Cross-Asset Correlation Monitor · schedule:
- [`cross-aggregator.yml`](#cross-aggregatoryml) — Cross-System Signal Aggregator · schedule:
- [`crypto-ml-edge.yml`](#crypto-ml-edgeyml) — Crypto ML Edge GSD Scanner · schedule:
- [`crypto-ml-tracker.yml`](#crypto-ml-trackeryml) — Crypto Gainer ML Live Tracker · schedule:
- [`crypto-smart-picks.yml`](#crypto-smart-picksyml) — CRYPTO SMART PICKS - Portfolio A/B/C/D Scanner · schedule:
- [`crypto-test-portfolios.yml`](#crypto-test-portfoliosyml) — Crypto Test Portfolios · schedule:
- [`crypto-winner-scan.yml`](#crypto-winner-scanyml) — Crypto Winner Scanner  Auto Scan · schedule:
- [`daily-feed-summary.yml`](#daily-feed-summaryyml) — Daily Feed Summary · schedule:
- [`daily-miracle-scan.yml`](#daily-miracle-scanyml) — Daily Miracle DayTrades Scan · schedule:
- [`daily-mutualfund-refresh.yml`](#daily-mutualfund-refreshyml) — Daily Mutual Fund Refresh (DISABLED) · workflow_dispatch
- [`daily-picks-snapshot.yml`](#daily-picks-snapshotyml) — Daily Picks Snapshot  Crypto, Forex & Stocks · schedule:
- [`daily-price-refresh.yml`](#daily-price-refreshyml) — Daily Price Refresh · schedule:
- [`daily-stock-refresh.yml`](#daily-stock-refreshyml) — Daily Stock Data Refresh · schedule:
- [`daily_runs.yml`](#daily_runsyml) — Daily Runs · schedule:
- [`darwin-evolution.yml`](#darwin-evolutionyml) — DARWIN ENGINE - DNA Evolution Pipeline · schedule:
- [`dashboard-pick-trader.yml`](#dashboard-pick-traderyml) — Dashboard Pick Trader · schedule:
- [`data-pipeline-test.yml`](#data-pipeline-testyml) — Data Pipeline Reliability Test · schedule:
- [`db-backup-email.yml`](#db-backup-emailyml) — FINDTORONTOEVENTS.CA Database Backups · schedule:
- [`db-sync-bidirectional.yml`](#db-sync-bidirectionalyml) — DB Sync: Bi-directional User Data · schedule:
- [`db-sync-to-mirror.yml`](#db-sync-to-mirroryml) — DB Sync: findtorontoevents.ca  torontoevent.net · schedule:
- [`deals-refresh.yml`](#deals-refreshyml) — Deals & Freebies  Verify & Refresh · schedule:
- [`decile-separation-test.yml`](#decile-separation-testyml) — Decile Separation Test · schedule:
- [`deploy-alpha-dashboard.yml`](#deploy-alpha-dashboardyml) — Deploy Alpha Engine Dashboard · push:
- [`deploy-battleground-ftp.yml`](#deploy-battleground-ftpyml) — Deploy Battleground to FTP · push:
- [`deploy-competition-to-site.yml`](#deploy-competition-to-siteyml) — Deploy Competition to Live Site · push:
- [`deploy-fc-api-env-godaddy.yml`](#deploy-fc-api-env-godaddyyml) — Deploy fc/api/.env to GoDaddy (torontoevent.net) · workflow_dispatch:
- [`deploy-fc-api-hotfix.yml`](#deploy-fc-api-hotfixyml) — Deploy FC API Hotfix (3 domains) · workflow_dispatch:
- [`deploy-fc-frontend.yml`](#deploy-fc-frontendyml) — Deploy FavCreators Frontend (/fc/) · push:
- [`deploy-findcryptopairs-ftp.yml`](#deploy-findcryptopairs-ftpyml) — Deploy FindCryptoPairs to FTP · push:
- [`deploy-friendtracker.yml`](#deploy-friendtrackeryml) — Deploy FriendTracker · push:
- [`deploy-fte-events-json.yml`](#deploy-fte-events-jsonyml) — Deploy findtorontoevents.ca next/events.json · workflow_dispatch:
- [`deploy-fte-index.yml`](#deploy-fte-indexyml) — Deploy findtorontoevents.ca core site · workflow_dispatch:
- [`deploy-movieshows-all.yml`](#deploy-movieshows-allyml) — Deploy MOVIESHOWS2 + MOVIESHOWS3 (All 3 Domains) · workflow_dispatch:
- [`deploy-movieshows3-hotfix.yml`](#deploy-movieshows3-hotfixyml) — Deploy MOVIESHOWS3 Hotfix · workflow_dispatch:
- [`deploy-pages.yml`](#deploy-pagesyml) — Deploy to GitHub Pages (DISABLED) · workflow_dispatch:
- [`deploy-riseoftheclaw.yml`](#deploy-riseoftheclawyml) — Deploy Rise of the Claw Dashboard · schedule,workflow_dispatch
- [`deploy-vetted-picks.yml`](#deploy-vetted-picksyml) — Deploy Vetted Master-Picks · workflow_dispatch:
- [`deploy_bundle.yml`](#deploy_bundleyml) — Deploy Strategy Bundle · workflow_dispatch:
- [`discord-bot.yml`](#discord-botyml) — Discord Bot  Persistent · workflow_dispatch:
- [`discord-heartbeat.yml`](#discord-heartbeatyml) — Discord Channel Heartbeat · schedule:
- [`discord-status.yml`](#discord-statusyml) — Discord ML Status Report · schedule:
- [`discord_status.yml`](#discord_statusyml) — ANTIGRAVITY ML  Hourly Discord Status + Picks · schedule:
- [`dna-mutation-cycle.yml`](#dna-mutation-cycleyml) — DNA Mutation Cycle · schedule:
- [`dna_strategy_pipeline.yml`](#dna_strategy_pipelineyml) — DNA Strategy Pipeline · push:
- [`dynamic-alpha-engine.yml`](#dynamic-alpha-engineyml) — ALPHA ENGINE - Dynamic Runner (Cloud or Local) · schedule:
- [`dynamic-universe.yml`](#dynamic-universeyml) — Dynamic Universe Scanner · schedule:
- [`edge-decay-check.yml`](#edge-decay-checkyml) — Edge decay monitor · —
- [`ema-retracement-scan.yml`](#ema-retracement-scanyml) — EMA Retracement Mean Reversion Scanner · schedule:
- [`enhanced-ml-crypto.yml`](#enhanced-ml-cryptoyml) — Enhanced ML Crypto Train & Predict · schedule,workflow_dispatch
- [`equities-agent.yml`](#equities-agentyml) — Equities & Stocks Agent · schedule:
- [`etf-agent.yml`](#etf-agentyml) — ETF Agent · schedule:
- [`etf-bond-scanner.yml`](#etf-bond-scanneryml) — ETF & Bond Scanner · schedule:
- [`fast-stocks-competition.yml`](#fast-stocks-competitionyml) — Fast Stocks Competition  High Frequency Scanner · workflow_dispatch
- [`fast-variants-master.yml`](#fast-variants-masteryml) — Fast Trading Variants  Master Scheduler · schedule:
- [`fc-crypto-pro.yml`](#fc-crypto-proyml) — FC-CRYPTO PRO Top Actionable Picks · workflow_dispatch:
- [`feature-stability-check.yml`](#feature-stability-checkyml) — Feature Stability Check (Weekly) · schedule:
- [`feed-health.yml`](#feed-healthyml) — Feed Health Check · schedule:
- [`fetch-movies-v3.yml`](#fetch-movies-v3yml) — Deploy & Refresh MOVIESHOWS3 · schedule:
- [`fetch-movies.yml`](#fetch-moviesyml) — Fetch New Movies & TV Shows · schedule:
- [`fix-battleground.yml`](#fix-battlegroundyml) — Fix Battleground Deployment · workflow_dispatch:
- [`fix-ghost-cards.yml`](#fix-ghost-cardsyml) — Fix Ghost Cards & Thumbnails  All Sites · workflow_dispatch:
- [`forex-agent.yml`](#forex-agentyml) — Forex Agent · schedule:
- [`forex-smart-picks.yml`](#forex-smart-picksyml) — Forex Smart Picks Scanner · schedule:
- [`forward-signal-scanner.yml`](#forward-signal-scanneryml) — Forward Signal Scanner · schedule:
- [`forward-test-daily.yml`](#forward-test-dailyyml) — Forward Test Daily · schedule:
- [`forward-test-new-strategies.yml`](#forward-test-new-strategiesyml) — Forward-Test New Strategies Tracker · schedule:
- [`forward-tracking-v2.yml`](#forward-tracking-v2yml) — Forward Trade Tracking v2 · schedule:
- [`forward_test.yml`](#forward_testyml) — Forward Test - Strategy Validation · schedule:
- [`futures-agent.yml`](#futures-agentyml) — Futures Agent · schedule:
- [`gainer-predictor.yml`](#gainer-predictoryml) — Gainer Predictor Scanner · schedule:
- [`genome-daily-pipeline.yml`](#genome-daily-pipelineyml) — DNA Genome Daily Pipeline · push:
- [`genome-evolution.yml`](#genome-evolutionyml) — Strategy Genome Evolution · schedule:
- [`gha-stale-workflows-audit.yml`](#gha-stale-workflows-audityml) — GHA stale workflows audit · schedule:
- [`goldmine-tracker.yml`](#goldmine-trackeryml) — Goldmine Tracker - Archive & Maintain · schedule:
- [`growth-stock-screener-daily.yml`](#growth-stock-screener-dailyyml) — Growth Stock Screener Daily · —
- [`gsd-edge-test-discord.yml`](#gsd-edge-test-discordyml) — GSD Edge Engine - Test Discord Notification · workflow_dispatch:
- [`hc-parity.yml`](#hc-parityyml) — HC Evaluator Parity Test · schedule:
- [`hierarchical-bayes.yml`](#hierarchical-bayesyml) — Hierarchical Bayesian Edge Update · schedule:
- [`hindsight-learner.yml`](#hindsight-learneryml) — Hindsight Learner  Hourly Winner Analysis · schedule:
- [`hoffman-tracker.yml`](#hoffman-trackeryml) — Hoffman IRB Strategy Tracker · schedule:
- [`hourly-master-picks.yml`](#hourly-master-picksyml) — Hourly Master Picks to Discord · schedule:
- [`hub-sync.yml`](#hub-syncyml) — Hub Data Sync · schedule:
- [`hyro-bridge-regen.yml`](#hyro-bridge-regenyml) — Hyro Quan Bridge Regen · —
- [`hyro-daily.yml`](#hyro-dailyyml) — Hyro daily (filter + backtest) · —
- [`incubator-pipeline.yml`](#incubator-pipelineyml) — Incubator Pipeline  Strategy Graduation · schedule:
- [`incubator-strategies.yml`](#incubator-strategiesyml) — ALPHA ENGINE - Incubator Strategies · schedule:
- [`index-creator-content.yml`](#index-creator-contentyml) — Index All Creator Content · schedule:
- [`kimi-feb172026-live.yml`](#kimi-feb172026-liveyml) — KIMI_FEB172026 - Live Trading System · schedule,workflow_dispatch
- [`kimi-fetch-movies.yml`](#kimi-fetch-moviesyml) — Kimi Fetch Movies/TV · workflow_dispatch:
- [`kimi-goldmine-collector.yml`](#kimi-goldmine-collectoryml) — KIMI Goldmine Data Collection · schedule:
- [`live-monitor-refresh.yml`](#live-monitor-refreshyml) — Live Trading Monitor  Auto Refresh · schedule:
- [`live-position-monitor.yml`](#live-position-monitoryml) — BTCC Live Position Monitor (REAL MONEY) · workflow_dispatch
- [`live_spike_trading.yml`](#live_spike_tradingyml) — LIVE SPIKE TRADING - Autonomous Crypto Monitor · schedule:
- [`live_tracker.yml`](#live_trackeryml) — Live Picks Tracker · workflow_dispatch:
- [`live_trading.yml`](#live_tradingyml) — Live Trading Bot · schedule:
- [`live_trading_canada.yml`](#live_trading_canadayml) — Live Trading Bot - Canada Edition · schedule:
- [`live_trading_canada_free.yml`](#live_trading_canada_freeyml) — Live Trading Bot - Canada Edition (FREE Data) · schedule:
- [`low-score-tracker.yml`](#low-score-trackeryml) — Low-Score Winner Tracker · schedule:
- [`luxalgo-signals.yml`](#luxalgo-signalsyml) — LuxAlgo Signal Generator · schedule:
- [`market_beating.yml`](#market_beatingyml) — Market Beating System - Crypto & Forex Priority · schedule,push,workflow_dispatch
- [`master-automation-scheduler.yml`](#master-automation-scheduleryml) — Master Automation Scheduler · schedule:
- [`master-picks-health.yml`](#master-picks-healthyml) — Master-Picks Health Score · schedule:
- [`mega-mutation-tracker.yml`](#mega-mutation-trackeryml) — Mega Mutation Live Tracker · schedule:
- [`meme-scanner-fixed.yml`](#meme-scanner-fixedyml) — Meme Coin Scanner  Fixed with Monitoring · workflow_dispatch
- [`meme-scanner-v2.yml`](#meme-scanner-v2yml) — Meme Coin Scanner v2  Fixed & Monitored · schedule:
- [`meme-scanner.yml`](#meme-scanneryml) — Meme Coin Scanner Auto Scan & Resolve · schedule:
- [`mercury2-fast-scan.yml`](#mercury2-fast-scanyml) — Mercury2 Fast  High Frequency Crypto Scanner · workflow_dispatch
- [`mercury2-retrain.yml`](#mercury2-retrainyml) — Mercury 2  Weekly Retrain · schedule:
- [`mercury2-scan.yml`](#mercury2-scanyml) — Mercury 2  Signal Scanner · schedule,workflow_dispatch
- [`meta-strategy.yml`](#meta-strategyyml) — Meta-Strategy Permutation Engine · schedule:
- [`mirror-site.yml`](#mirror-siteyml) — Mirror: findtorontoevents.ca  torontoevent.net · schedule:
- [`missed-opportunity-scan.yml`](#missed-opportunity-scanyml) — Missed Opportunity Analyzer Hourly Self-Improvement · schedule:
- [`ml-battleground-a.yml`](#ml-battleground-ayml) — Superpowers - System A (The Filter) · workflow_dispatch
- [`ml-battleground-abc-pilots.yml`](#ml-battleground-abc-pilotsyml) — Superpowers  ABC Forward Test + ML Pilots · workflow_dispatch
- [`ml-battleground-b.yml`](#ml-battleground-byml) — Superpowers - System B (The Regime) · workflow_dispatch
- [`ml-battleground-bootstrap.yml`](#ml-battleground-bootstrapyml) — SUPERPOWERS - Bootstrap All 3 ML Systems · workflow_dispatch:
- [`ml-battleground-c.yml`](#ml-battleground-cyml) — Superpowers - System C (The Neural Net) · workflow_dispatch
- [`ml-battleground-d.yml`](#ml-battleground-dyml) — ML Battleground System D (The Carry Trade) · workflow_dispatch
- [`ml-battleground-e.yml`](#ml-battleground-eyml) — ML Battleground System E (The Momentum) · workflow_dispatch
- [`ml-battleground-ensemble.yml`](#ml-battleground-ensembleyml) — ML Battleground Ensemble · workflow_dispatch
- [`ml-battleground-f.yml`](#ml-battleground-fyml) — ML Battleground System F (Claws of Doom) · schedule,workflow_dispatch
- [`ml-battleground-monitor.yml`](#ml-battleground-monitoryml) — ML Battleground Pick Monitor · workflow_dispatch
- [`ml-battleground-retrain.yml`](#ml-battleground-retrainyml) — ML Battleground Daily Retrain · schedule:
- [`ml-battleground-test-discord.yml`](#ml-battleground-test-discordyml) — SUPERPOWERS - Test Discord Notifications · workflow_dispatch:
- [`ml-discord-status.yml`](#ml-discord-statusyml) — ML Crypto  Discord Hourly Status · schedule:
- [`ml-feedback-loop.yml`](#ml-feedback-loopyml) — ML Feedback Loop · schedule:
- [`ml-feedback-retrain.yml`](#ml-feedback-retrainyml) — ML Feedback Retrain  Learn from Closed Trades · schedule:
- [`ml-forward-test.yml`](#ml-forward-testyml) — ML Forward Test 1745 Models · schedule:
- [`ml-gatekeeper-ab-bootstrap.yml`](#ml-gatekeeper-ab-bootstrapyml) — ML Gatekeeper A/B Bootstrap · workflow_dispatch:
- [`ml-gatekeeper-train-ab.yml`](#ml-gatekeeper-train-abyml) — ML Gatekeeper Train A/B (Phase D) · workflow_dispatch:
- [`ml-health-monitor.yml`](#ml-health-monitoryml) — ML System Health Monitor · schedule:
- [`ml-model-autotraining.yml`](#ml-model-autotrainingyml) — ML Model Auto-Training · schedule:
- [`ml-monthly-retrain.yml`](#ml-monthly-retrainyml) — ML Monthly Full Retrain · schedule:
- [`ml-staleness-watchdog.yml`](#ml-staleness-watchdogyml) — ML Model Staleness Watchdog · schedule:
- [`ml-strategy-reviver.yml`](#ml-strategy-reviveryml) — ML Strategy Reviver Bridge & Standalone · schedule:
- [`ml_hourly_picks.yml`](#ml_hourly_picksyml) — ML Picks  Hourly Discord Alert · schedule:
- [`momentum-catcher.yml`](#momentum-catcheryml) — MOMENTUM CATCHER - Real-time Pump Detector · schedule:
- [`momentum-scanner.yml`](#momentum-scanneryml) — MOMENTUM SCALP SCANNER - Dynamic Universe Expansion · schedule:
- [`momentum-tracker.yml`](#momentum-trackeryml) — MOMENTUM TRACKER - Real-Time Gainer Scanner · schedule:
- [`monthly-tournament.yml`](#monthly-tournamentyml) — Monthly DNA Tournament · schedule:
- [`multi-asset-scanner.yml`](#multi-asset-scanneryml) — Multi-Asset Copytrader Scanner v2  Forex/Futures/Stocks/Commodities · schedule:
- [`mutation-analysis-report.yml`](#mutation-analysis-reportyml) — Mutation analysis report · —
- [`mutation-lab.yml`](#mutation-labyml) — Mutation Lab  Strategy Evolution Pipeline · schedule:
- [`mutation-lifecycle-runner.yml`](#mutation-lifecycle-runneryml) — Mutation Lifecycle Runner · schedule:
- [`mysql-trading-sync.yml`](#mysql-trading-syncyml) — MySQL Trading Picks Sync · schedule:
- [`news-video-healthcheck.yml`](#news-video-healthcheckyml) — \U0001F4FA News Video Health Check · schedule:
- [`non-crypto-ab-test.yml`](#non-crypto-ab-testyml) — Non-Crypto A/B Portfolio Tracker · schedule:
- [`now-scanner.yml`](#now-scanneryml) — Rapid Fire - NOW Scanner · schedule:
- [`obi-snapshot.yml`](#obi-snapshotyml) — OBI Hourly Snapshot · schedule:
- [`opposite-day.yml`](#opposite-dayyml) — Opposite Day Paper-Trade [DISABLED] · workflow_dispatch:
- [`optimize-score-thresholds.yml`](#optimize-score-thresholdsyml) — Optimize Score Thresholds · schedule:
- [`outcome-resolver.yml`](#outcome-resolveryml) — Outcome Resolver  Validate Unresolved Picks · schedule:
- [`overnight-mutations.yml`](#overnight-mutationsyml) — Overnight Mutations · workflow_dispatch:
- [`paper-trading.yml`](#paper-tradingyml) — Paper Trading Portfolio · workflow_dispatch
- [`parquet-ingest.yml`](#parquet-ingestyml) — Parquet Data Ingestion · schedule:
- [`penny-skyrocket-runner.yml`](#penny-skyrocket-runneryml) — Penny Skyrocket Detector · schedule:
- [`penny-stock-picks.yml`](#penny-stock-picksyml) — Penny Stock Daily Picks · schedule:
- [`pick-monitor-30min.yml`](#pick-monitor-30minyml) — Pick Monitor & Price Validator (30min) · schedule:
- [`picks_dispatch.yml`](#picks_dispatchyml) — Crypto Picks Dispatch · schedule:
- [`pine-generator.yml`](#pine-generatoryml) — Pine Script Generator · workflow_run:
- [`polymarket-signals.yml`](#polymarket-signalsyml) — Polymarket Prediction Market Signals (Multi-Asset) · schedule:
- [`portfolio-trackers.yml`](#portfolio-trackersyml) — Portfolio Trackers (Real Money + Theory) · schedule:
- [`pre-spike-scan.yml`](#pre-spike-scanyml) — Pre-Spike Early Warning · schedule:
- [`prediction-market-agents.yml`](#prediction-market-agentsyml) — Prediction Market Agents · schedule:
- [`prediction-quality-tracker.yml`](#prediction-quality-trackeryml) — Prediction Quality Tracker · schedule:
- [`proven-strategies-scanner.yml`](#proven-strategies-scanneryml) — Proven Strategies Scanner · schedule:
- [`prune-strategy-performance.yml`](#prune-strategy-performanceyml) — Prune strategy_performance.json (30d) · schedule:
- [`quan-engine-live.yml`](#quan-engine-liveyml) — QUAN ENGINE - Live Autonomous Scanner · schedule:
- [`quant-auditor-deep-nightly.yml`](#quant-auditor-deep-nightlyyml) — Quant Auditor (deep nightly) · —
- [`quant-auditor-fast-pr.yml`](#quant-auditor-fast-pryml) — Quant Auditor (fast PR check) · —
- [`quantum_fusion.yml`](#quantum_fusionyml) — QuantumFusion Crypto Engine · schedule:
- [`quick-guess-ml.yml`](#quick-guess-mlyml) — Quick Guess ML Agent · schedule:
- [`rapid-validation-CLAUDECODE_Feb152026.yml`](#rapid-validation-claudecode_feb152026yml) — Rapid Validation Engine · schedule:
- [`real_2hour_challenge.yml`](#real_2hour_challengeyml) — REAL 2-HOUR CHALLENGE - Live Market Data · workflow_dispatch
- [`recommended-portfolio.yml`](#recommended-portfolioyml) — Recommended Portfolio Generator · schedule:
- [`refresh-creator-updates.yml`](#refresh-creator-updatesyml) — Refresh Creator Updates · schedule:
- [`refresh-stocks-portfolio.yml`](#refresh-stocks-portfolioyml) — Refresh All Portfolio Data · schedule:
- [`refresh-top-movies.yml`](#refresh-top-moviesyml) — Refresh Top Movies Data · schedule:
- [`regime-detector.yml`](#regime-detectoryml) — Daily Regime Detection + Position Sizing · schedule:
- [`regime-terminal.yml`](#regime-terminalyml) — Regime Terminal  HMM Live Scanner · schedule:
- [`research-orchestrator.yml`](#research-orchestratoryml) — Research Orchestrator (weekly) · —
- [`riseoftheclaw-weekly-backtest.yml`](#riseoftheclaw-weekly-backtestyml) — [RiseOfTheClaw] Weekly Backtest + Elimination · schedule:
- [`rl-agent-ppo.yml`](#rl-agent-ppoyml) — RL Agent (PPO) Train & Predict · workflow_dispatch:
- [`scrape-events.yml`](#scrape-eventsyml) — Scrape events · workflow_dispatch:
- [`sec-edgar-fetch.yml`](#sec-edgar-fetchyml) — SEC EDGAR  Insider Trades & 13F Holdings · schedule:
- [`self_optimizing_trading.yml`](#self_optimizing_tradingyml) — Self-Optimizing Trading Bot - Auto-Validates & Tweaks · schedule,push,workflow_dispatch
- [`send-accountability-reminders.yml`](#send-accountability-remindersyml) — Send Accountability Reminders · schedule:
- [`send-event-notifications.yml`](#send-event-notificationsyml) — Send Event Notifications (DISABLED) · workflow_dispatch
- [`send-goal-followups.yml`](#send-goal-followupsyml) — Send Morning Goal Follow-Ups · schedule:
- [`sidecar-status-update.yml`](#sidecar-status-updateyml) — Sidecar Status Markdown Update · schedule:
- [`signal-engine.yml`](#signal-engineyml) — Crypto Signal Engine · schedule:
- [`signal-integrator.yml`](#signal-integratoryml) — Signal Integrator - Isolated Source Aggregator · schedule:
- [`signal-quality-monitor.yml`](#signal-quality-monitoryml) — Signal Quality Monitor · schedule:
- [`signal-recorder.yml`](#signal-recorderyml) — Signal Recorder · schedule:
- [`signal_tracking.yml`](#signal_trackingyml) — Signal Tracking & Validation - Beat the Market · schedule,push,workflow_dispatch
- [`skyrocket-detector.yml`](#skyrocket-detectoryml) — Skyrocket Detector  Live Scanner · schedule:
- [`smart-money-tracker.yml`](#smart-money-trackeryml) — \U0001F9E0 Smart Money Intelligence · schedule:
- [`smart-picks-tracker.yml`](#smart-picks-trackeryml) — Smart Picks Tracker · schedule:
- [`social-prediction-tracker.yml`](#social-prediction-trackeryml) — Social Media Prediction Tracker · schedule:
- [`social_investigation.yml`](#social_investigationyml) — Social Media Algo Trader Investigation · schedule,workflow_dispatch
- [`specialized-scanners.yml`](#specialized-scannersyml) — Specialized Scanners - Rocket, Short Engine, TSMOM · schedule:
- [`spike-scanner.yml`](#spike-scanneryml) — Spike Scanner · schedule:
- [`sports-betting-refresh.yml`](#sports-betting-refreshyml) — Sports Betting  Odds Refresh & Auto-Settle · schedule:
- [`sports-data-snapshots.yml`](#sports-data-snapshotsyml) — Sports data snapshots · schedule:
- [`sports-forensics-weekly.yml`](#sports-forensics-weeklyyml) — Sports Forensics Weekly · schedule:
- [`sports-prediction-market-sync.yml`](#sports-prediction-market-syncyml) — Sports Prediction Market Sync · schedule:
- [`sports-smoke-and-e2e.yml`](#sports-smoke-and-e2eyml) — Sports endpoint smoke + Playwright · pull_request:
- [`statistical_validation.yml`](#statistical_validationyml) — Statistical Rigor Validation - Thousands of Signals · schedule,workflow_dispatch
- [`stocks-daily-stocksunify.yml`](#stocks-daily-stocksunifyyml) — STOCKSUNIFY Daily Stock Picks · schedule:
- [`stocks-daily.yml`](#stocks-dailyyml) — Daily Stock Picks Generator (STOCKSUNIFY) · schedule:
- [`stocksunify2-pull.yml`](#stocksunify2-pullyml) — STOCKSUNIFY2 daily-stocks pull · schedule:
- [`strategy-forward-tester.yml`](#strategy-forward-testeryml) — Strategy Forward Tester · schedule:
- [`strategy-health-monitor.yml`](#strategy-health-monitoryml) — Strategy Health Monitor · schedule:
- [`strategy-health-report.yml`](#strategy-health-reportyml) — Strategy Health Report · schedule:
- [`strategy-performance-no-regression.yml`](#strategy-performance-no-regressionyml) — strategy_performance.json no-regression guard · pull_request:
- [`sustained-gainer-scan.yml`](#sustained-gainer-scanyml) — Sustained Gainer Confluence Scanner · schedule:
- [`swarm-janitor.yml`](#swarm-janitoryml) — swarm-janitor · schedule:
- [`swarm-pick-review.yml`](#swarm-pick-reviewyml) — Swarm Pick Review (resolve + weekly + patterns) · schedule:
- [`swarm-sync-v2.yml`](#swarm-sync-v2yml) — Swarm State Sync · schedule:
- [`swing_screener_daily.yml`](#swing_screener_dailyyml) — UEPS Swing Screener Daily · —
- [`system-health-check.yml`](#system-health-checkyml) — System Health Check · schedule:
- [`taste-profile-scan.yml`](#taste-profile-scanyml) — Taste Profile Scanner · workflow_dispatch:
- [`test-fast.yml`](#test-fastyml) — Test Fast Variants · workflow_dispatch:
- [`test-portfolios.yml`](#test-portfoliosyml) — Test Portfolios  Hourly Strategy Validation · schedule:
- [`top-gainers-scan.yml`](#top-gainers-scanyml) — Top Gainers Spike Scanner · schedule:
- [`torontoevent-algorithm-refresh.yml`](#torontoevent-algorithm-refreshyml) — [torontoevent.net] Algorithm Competition Refresh · schedule:
- [`torontoevent-backtest-and-deploy-ROOCODE.yml`](#torontoevent-backtest-and-deploy-roocodeyml) — [torontoevent.net] Run Backtests & Deploy Dashboards (ROOCODE) · schedule:
- [`torontoevent-backtest-and-deploy.yml`](#torontoevent-backtest-and-deployyml) — [torontoevent.net] Run Backtests & Deploy Dashboards · schedule:
- [`torontoevent-deploy-competition.yml`](#torontoevent-deploy-competitionyml) — [torontoevent.net] Deploy Competition to Live Site · push:
- [`torontoevent-deploy-live-monitor.yml`](#torontoevent-deploy-live-monitoryml) — [torontoevent.net] Deploy Live Monitor APIs · push:
- [`torontoevent-deploy-riseoftheclaw.yml`](#torontoevent-deploy-riseoftheclawyml) — [torontoevent.net] Deploy Rise of the Claw · schedule:
- [`torontoevent-forward-test.yml`](#torontoevent-forward-testyml) — [torontoevent.net] Forward Test Daily · schedule:
- [`torontoevent-goldmine-tracker.yml`](#torontoevent-goldmine-trackeryml) — [torontoevent.net] Goldmine Tracker - Archive & Maintain · schedule:
- [`torontoevent-rapid-validation.yml`](#torontoevent-rapid-validationyml) — [torontoevent.net] Rapid Validation Engine · schedule:
- [`torontoevent-spike-scanner.yml`](#torontoevent-spike-scanneryml) — [torontoevent.net] Spike Scanner · schedule:
- [`track-quick-picks.yml`](#track-quick-picksyml) — Track Quick Pick Portfolios · schedule:
- [`traditional-test-portfolios.yml`](#traditional-test-portfoliosyml) — Traditional Test Portfolios (5-8) · schedule:
- [`train_crypto_models.yml`](#train_crypto_modelsyml) — Train Crypto ML Models · schedule:
- [`tv-paper-tpsl-watchdog.yml`](#tv-paper-tpsl-watchdogyml) — TV Paper TP/SL Watchdog · schedule:
- [`tv-strategy-scanner.yml`](#tv-strategy-scanneryml) — TradingView Strategy Scanner · schedule:
- [`ueps-pick-runner.yml`](#ueps-pick-runneryml) — UEPS Pick Runner · —
- [`ueps_smoke_tests.yml`](#ueps_smoke_testsyml) — UEPS Smoke Tests · —
- [`universe-expander.yml`](#universe-expanderyml) — ALPHA ENGINE - Universe Expander · schedule:
- [`update-creator-news.yml`](#update-creator-newsyml) — Update Creator News · schedule:
- [`validate-hf-asset-class.yml`](#validate-hf-asset-classyml) — Validate HF by asset class · —
- [`value_resolver_quarterly.yml`](#value_resolver_quarterlyyml) — UEPS Value Resolver Quarterly · —
- [`value_screener_weekly.yml`](#value_screener_weeklyyml) — UEPS Value Screener Weekly · —
- [`volatile-alt-scanner.yml`](#volatile-alt-scanneryml) — VOLATILE ALT SCANNER Hyperliquid High-Vol Alts · schedule:
- [`walk-forward-backtest.yml`](#walk-forward-backtestyml) — Walk-Forward Backtest (Weekly) · schedule:
- [`walkforward-gate.yml`](#walkforward-gateyml) — walkforward-gate · pull_request:
- [`weekly-stock-simulation.yml`](#weekly-stock-simulationyml) — Weekly Exhaustive Stock Simulation · schedule:
- [`weekly-strategy-scorecard.yml`](#weekly-strategy-scorecardyml) — Weekly Strategy Scorecard · schedule:
- [`weekly_score_quartile_spread.yml`](#weekly_score_quartile_spreadyml) — Weekly score quartile spread · —
- [`what-worked-insights.yml`](#what-worked-insightsyml) — What Worked Active Picks Insights · schedule:
- [`winner-pattern-scanner.yml`](#winner-pattern-scanneryml) — Winner Pattern Precursor Scanner · schedule:
- [`worldclass-intelligence.yml`](#worldclass-intelligenceyml) — World-Class Intelligence  Daily Pipeline · schedule:
- [`worldclass-pipeline.yml`](#worldclass-pipelineyml) — World-Class Algorithm Pipeline · schedule:
- [`wsl-runner-manager.yml`](#wsl-runner-manageryml) — WSL Runner Manager · workflow_dispatch:

## Workflows

### `2hour_challenge.yml`

- **Name:** 2hour-challenge
- **Triggers:** workflow_dispatch:
- **Cron:** `0 12 * * 1-5`
- **Jobs:** `execute-challenge`
- **Scripts:** `.github/scripts/safe_push.sh`, `audit_trail/data/2hour_challenge_results.js`, `real_2hour_challenge.py`
- **JSON I/O:** `audit_trail/data/2hour_challenge_results.json`

### `_dynamic-runner-template.yml`

- **Name:** Dynamic Runner Template
- **Triggers:** workflow_call:
- **Jobs:** `dynamic-job`

### `ab_analysis.yml`

- **Name:** A/B Analysis + Zero-PnL Audit
- **Triggers:** schedule:
- **Cron:** `30 5 * * *`
- **Jobs:** `ab-analysis`
- **Scripts:** `audit_dashboard/data/commodity_carry_momo.js`, `audit_dashboard/data/correlation_regime.js`, `audit_dashboard/data/cot_cl.js`, `audit_dashboard/data/cot_ct.js`, `audit_dashboard/data/cot_gc.js`, `audit_dashboard/data/cot_hg.js`, `audit_dashboard/data/cot_ng.js`, `audit_dashboard/data/cot_pa.js`, `audit_dashboard/data/cot_pl.js`, `audit_dashboard/data/cot_si.js`, `audit_dashboard/data/cot_step7_friction_adjusted_mc.js`, `audit_dashboard/data/cot_zc.js`, `audit_dashboard/data/cot_zs.js`, `audit_dashboard/data/cot_zw.js`, `audit_dashboard/data/system_pf_verification.js`, `audit_trail/data/zero_pnl_report.js`, `audit_trail/zero_pnl_detector.py`, `ml_gatekeeper/ab_analysis.py`, `ml_gatekeeper/data/ab_rollback_state.js`, `ml_gatekeeper/data/ab_summary.js`, `tools/correlation_regime_sidecar.py`, `tools/cot_fetcher_socrata.py`, `tools/cot_step7_friction_adjusted_mc.py`, `tools/verify_system_pf.py`
- **JSON I/O:** `audit_dashboard/data/commodity_carry_momo.json`, `audit_dashboard/data/correlation_regime.json`, `audit_dashboard/data/cot_cl.json`, `audit_dashboard/data/cot_ct.json`, `audit_dashboard/data/cot_gc.json`, `audit_dashboard/data/cot_hg.json`, `audit_dashboard/data/cot_ng.json`, `audit_dashboard/data/cot_pa.json`, `audit_dashboard/data/cot_pl.json`, `audit_dashboard/data/cot_si.json`, `audit_dashboard/data/cot_step7_friction_adjusted_mc.json`, `audit_dashboard/data/cot_zc.json`, `audit_dashboard/data/cot_zs.json`, `audit_dashboard/data/cot_zw.json`, `audit_dashboard/data/system_pf_verification.json`, `audit_trail/data/zero_pnl_report.json`, `closed_picks.json`, `ml_gatekeeper/data/ab_rollback_state.json`, `ml_gatekeeper/data/ab_summary.json`

### `actions-failure-guardian.yml`

- **Name:** actions-failure-guardian
- **Triggers:** workflow_dispatch:
- **Cron:** `*/30 * * * *`
- **Jobs:** `monitor-and-retry`
- **Scripts:** `reports/actions_failure_guardian.js`, `scripts/actions_failure_guardian.py`
- **JSON I/O:** `reports/actions_failure_guardian.json`

### `adaptive-trust-tuner.yml`

- **Name:** ALPHA ENGINE - Adaptive Trust Tuner
- **Triggers:** schedule:
- **Cron:** `15 0,12 * * *`
- **Jobs:** `trust-tuner`
- **Scripts:** `.github/scripts/safe_push.sh`, `alpha_engine/adaptive_trust_tuner.py`, `alpha_engine/data/trust_adjustments.js`
- **JSON I/O:** `alpha_engine/data/trust_adjustments.json`

### `algorithm-competition-refresh.yml`

- **Name:** Algorithm Competition Refresh
- **Triggers:** schedule:
- **Cron:** `0 10 * * 0`
- **Jobs:** `refresh-competition`
- **Scripts:** `.github/scripts/safe_push.sh`, `STOCKS/competition/competition-crypto.js`, `STOCKS/competition/competition-forex.js`, `STOCKS/competition/competition-meme_coins.js`, `STOCKS/competition/competition-penny_stocks.js`, `STOCKS/competition/competition-results.js`, `STOCKS/competition/competition-slim.js`, `STOCKS/competition/competition-stocks.js`, `STOCKS/competition/forward_picks.js`, `STOCKS/competition/run_competition.py`
- **JSON I/O:** `STOCKS/competition/competition-crypto.json`, `STOCKS/competition/competition-forex.json`, `STOCKS/competition/competition-meme_coins.json`, `STOCKS/competition/competition-penny_stocks.json`, `STOCKS/competition/competition-results.json`, `STOCKS/competition/competition-slim.json`, `STOCKS/competition/competition-stocks.json`, `STOCKS/competition/forward_picks.json`

### `alpha-engine-bond.yml`

- **Name:** ALPHA ENGINE - Bond Emitter
- **Triggers:** schedule:
- **Cron:** `10 6 * * *`
- **Jobs:** `emit-bond-picks`
- **Scripts:** `alpha_engine/data/active_picks_bond.js`, `alpha_engine/data/active_picks_bond_draft.js`, `tools/bond_emitter_spike.py`
- **JSON I/O:** `alpha_engine/data/active_picks_bond.json`, `alpha_engine/data/active_picks_bond_draft.json`

### `alpha-engine-daily-picks.yml`

- **Name:** Alpha Engine  Daily Picks
- **Triggers:** schedule:
- **Cron:** `0 22 * * 1-5`, `0 5 * * 0`
- **Jobs:** `generate-picks`
- **Scripts:** `//findtorontoevents.ca/findstocks/alpha/latest_picks.js`, `alpha_engine/output/latest_picks.js`
- **JSON I/O:** `//findtorontoevents.ca/findstocks/alpha/latest_picks.json`, `alpha_engine/output/latest_picks.json`

### `alpha-engine-etf.yml`

- **Name:** ALPHA ENGINE - ETF Emitter
- **Triggers:** schedule:
- **Cron:** `5 */6 * * *`
- **Jobs:** `emit-etf-picks`
- **Scripts:** `alpha_engine/data/active_picks_etf.js`, `alpha_engine/data/active_picks_etf_draft.js`, `alpha_engine/data/etf_decay_picks.js`, `alpha_engine/data/etf_sector_picks.js`, `alpha_engine/strategies/etf_decay_shorts.py`, `tools/etf_emitter_spike.py`, `tools/etf_sector_emitter.py`
- **JSON I/O:** `alpha_engine/data/active_picks_etf.json`, `alpha_engine/data/active_picks_etf_draft.json`, `alpha_engine/data/etf_decay_picks.json`, `alpha_engine/data/etf_sector_picks.json`, `etf_decay_picks.json`, `etf_sector_picks.json`

### `alpha-engine-fast.yml`

- **Name:** ALPHA ENGINE FAST Tighter TP/SL, Shorter Holds
- **Triggers:** schedule:
- **Cron:** `2,32 * * * *`
- **Jobs:** `alpha-fast`
- **Scripts:** `.github/scripts/safe_push.sh`, `alpha_engine/data/active_picks_fast.js`, `alpha_engine/data/closed_picks_fast.js`, `alpha_engine/production_scanner.py`
- **JSON I/O:** `alpha_engine/data/active_picks_fast.json`, `alpha_engine/data/closed_picks_fast.json`

### `alpha-engine-live.yml`

- **Name:** ALPHA ENGINE - Live Autonomous Scanner
- **Triggers:** schedule:
- **Cron:** `3 */2 * * *`
- **Jobs:** `alpha-engine`
- **Scripts:** `.github/notify-failure.sh`, `.github/scripts/safe_push.sh`, `/latest.js`, `alpha_engine/audit_push.py`, `alpha_engine/audit_verify.py`, `alpha_engine/auto_dna_mutator.py`, `alpha_engine/auto_tuner.py`, `alpha_engine/cryptopanic_feargreed.py`, `alpha_engine/data/active_picks.js`, `alpha_engine/data/closed_picks.js`, `alpha_engine/data/freshpicks_sent.js`, `alpha_engine/data/strategy_tweaks.js`, `alpha_engine/data/tradingagents_watchlist.js`, `alpha_engine/filter_danger_analyzer.py`, `alpha_engine/forward_validator.py`, `alpha_engine/isolated_signal_integrator.py`, `alpha_engine/kalshi_signals.py`, `alpha_engine/lunarcrush_signal.py`, `alpha_engine/mc_quality_purge.py`, `alpha_engine/ml_predictor_merger.py`, `alpha_engine/ml_strategy_reviver.py`, `alpha_engine/pipeline_health_monitor.py`, `alpha_engine/polymarket_merger.py`, `alpha_engine/polymarket_signals.py`, `alpha_engine/portfolio_monitor.py` … (+28)
- **JSON I/O:** `/latest.json`, `active_picks.json`, `alpha_engine/data/active_picks.json`, `alpha_engine/data/closed_picks.json`, `alpha_engine/data/freshpicks_sent.json`, `alpha_engine/data/strategy_tweaks.json`, `alpha_engine/data/tradingagents_watchlist.json`, `copy_trader_intel/data/polymarket_picks.json`, `copy_trader_intel/data/polymarket_trader_profiles.json`, `data/active_picks.json`, `data/closed_picks.json`, `data/freshpicks_gate_state.json`, `data/hmm_regime.json`, `data/strategy_performance.json`, `data/strategy_tweaks.json`, `latest.json`, `ml_crypto_predictor/enhanced_models/live_picks/all_picks_log.json`

### `alpha-gainer-capture.yml`

- **Name:** ALPHA ENGINE Gainer Capture (15min)
- **Triggers:** schedule:
- **Cron:** `10,40 * * * *`
- **Jobs:** `gainer-capture`
- **Scripts:** `.github/scripts/safe_push.sh`, `alpha_engine/data/gainer_capture_picks.js`, `alpha_engine/data/gainer_portfolio_state.js`, `alpha_engine/gainer_capture_strategy.py`
- **JSON I/O:** `alpha_engine/data/gainer_capture_picks.json`, `alpha_engine/data/gainer_portfolio_state.json`

### `alpha-quant-stack.yml`

- **Name:** ALPHA ENGINE - Quant Stack (KAMA + ATR + Regime)
- **Triggers:** schedule:
- **Cron:** `5,35 * * * *`
- **Jobs:** `quant-stack`
- **Scripts:** `alpha_engine/quant_stack_strategy.py`, `scanner.py`

### `alpha-trend-catcher.yml`

- **Name:** ALPHA ENGINE - Trend Catcher (4H Adaptive)
- **Triggers:** schedule:
- **Cron:** `5 0,4,8,12,16,20 * * *`
- **Jobs:** `trend-catcher`
- **Scripts:** `.github/scripts/safe_push.sh`, `alpha_engine/data/trend_catcher_backtest.js`, `alpha_engine/trend_catcher.py`
- **JSON I/O:** `alpha_engine/data/trend_catcher_backtest.json`

### `alpha-verify-predictions.yml`

- **Name:** ALPHA  Verify Predictions
- **Triggers:** schedule:
- **Cron:** `26 */2 * * *`
- **Jobs:** `verify`
- **Scripts:** `.github/scripts/safe_push.sh`, `alpha_engine/data/prediction_verification_log.js`, `alpha_engine/verify_predictions.py`
- **JSON I/O:** `alpha_engine/data/prediction_verification_log.json`

### `alpha-weekly-validation.yml`

- **Name:** Alpha Engine - Weekly Validation Suite
- **Triggers:** schedule:
- **Cron:** `0 6 * * 1`
- **Jobs:** `weekly-validation`
- **Scripts:** `.github/scripts/safe_push.sh`, `alpha_engine/data/precision_recall_report.js`, `alpha_engine/data/risk_metrics.js`, `alpha_engine/data/walk_forward_rolling_report.js`
- **JSON I/O:** `alpha_engine/data/precision_recall_report.json`, `alpha_engine/data/risk_metrics.json`, `alpha_engine/data/walk_forward_rolling_report.json`

### `analyst-tracker.yml`

- **Name:** Analyst Tracker  Top 20 Crypto Analysts
- **Triggers:** schedule:
- **Cron:** `15 */4 * * *`, `0 * * * *`
- **Jobs:** `scrape-analysts`, `validate-prices`
- **Scripts:** `.github/scripts/safe_push.sh`, `data/analyst_active_calls.js`, `data/analyst_leaderboard.js`, `data/leaderboard.js`, `run_analyst_scraper.py`, `validation/price_validator.py`
- **JSON I/O:** `data/analyst_active_calls.json`, `data/analyst_leaderboard.json`, `data/leaderboard.json`

### `antigravity-claudeopus.yml`

- **Name:** ANTIGRAVITY-CLAUDEOPUS  Live Picks & Discord
- **Triggers:** schedule:
- **Cron:** `0 * * * *`
- **Jobs:** `live-picks`
- **Scripts:** `.github/scripts/safe_push.sh`

### `asset-class-freshness-watchdog.yml`

- **Name:** Asset Class Freshness Watchdog
- **Triggers:** schedule:
- **Cron:** `30 13 * * *`
- **Jobs:** `freshness`
- **Scripts:** `/tmp/asset_class_freshness.js`, `audit_dashboard/data/dashboard_data.js`, `tools/generate_asset_class_freshness_report.py`
- **JSON I/O:** `/tmp/asset_class_freshness.json`, `audit_dashboard/data/dashboard_data.json`

### `asterdex-paper-trader.yml`

- **Name:** AsterDEX Paper Trader (DISABLED)
- **Triggers:** workflow_dispatch
- **Cron:** `*/30 * * * *`
- **Jobs:** `paper-trade`
- **Scripts:** `.github/scripts/safe_push.sh`, `asterdex_paper/data/dashboard.js`, `asterdex_paper/data/portfolio_state.js`, `asterdex_paper/paper_trader.py`
- **JSON I/O:** `asterdex_paper/data/dashboard.json`, `asterdex_paper/data/portfolio_state.json`

### `asterdex-paper-trading.yml`

- **Name:** AsterDEX Paper Trading
- **Triggers:** schedule:
- **Cron:** `5 * * * *`
- **Jobs:** `trade`, `daily-summary`
- **Scripts:** `.github/scripts/safe_push.sh`, `trading/data/dashboard_data.js`, `trading/data/signals_log.js`
- **JSON I/O:** `trading/data/dashboard_data.json`, `trading/data/signals_log.json`

### `audit-dashboard.yml`

- **Name:** Unified Audit Dashboard
- **Triggers:** —
- **Cron:** `10 * * * *`
- **Jobs:** `generate-and-deploy`
- **Scripts:** `.github/scripts/assert_no_conflict_markers.sh`, `.github/scripts/safe_push.sh`, `.github/scripts/verify_dashboard_publish_consistency.py`, `alpha_engine/active_picks_sync.py`, `alpha_engine/antigravity_strategies.py`, `alpha_engine/audit_sync.py`, `alpha_engine/btc_breakout_strategy.py`, `alpha_engine/combined_confidence_strategy.py`, `alpha_engine/config.py`, `alpha_engine/contrarian_consensus.py`, `alpha_engine/data/active_picks.js`, `alpha_engine/data/btc_breakout_picks.js`, `alpha_engine/data/contrarian_picks.js`, `alpha_engine/data/cot_emitted_releases.js`, `alpha_engine/data/funding_rate_picks.js`, `alpha_engine/data/kalshi_signals.js`, `alpha_engine/data/polymarket_signals.js`, `alpha_engine/data/prediction_market_picks.js`, `alpha_engine/data/regime_flip_alert.js`, `alpha_engine/data/regime_report.js`, `alpha_engine/data/strategy_performance.js`, `alpha_engine/data/system_trends.js`, `alpha_engine/forward_validator.py`, `alpha_engine/funding_rate_arb.py`, `alpha_engine/growth_stock_screener.py` … (+80)
- **JSON I/O:** `alpha_engine/data/active_picks.json`, `alpha_engine/data/btc_breakout_picks.json`, `alpha_engine/data/contrarian_picks.json`, `alpha_engine/data/cot_emitted_releases.json`, `alpha_engine/data/funding_rate_picks.json`, `alpha_engine/data/kalshi_signals.json`, `alpha_engine/data/polymarket_signals.json`, `alpha_engine/data/prediction_market_picks.json`, `alpha_engine/data/regime_flip_alert.json`, `alpha_engine/data/regime_report.json`, `alpha_engine/data/strategy_performance.json`, `alpha_engine/data/system_trends.json`, `audit_dashboard/data/cot_paper_pilot_status.json`, `audit_dashboard/data/cot_step7_ror_mc.json`, `audit_dashboard/data/dashboard_data.json`, `audit_dashboard/data/db_health.json`, `audit_dashboard/data/effective_n_report.json`, `audit_dashboard/data/hyro_backtest_results.json`, `audit_dashboard/data/hyro_live_strategies.json`, `audit_dashboard/data/hyro_ml_pick_rankings.json` … (+29)

### `audit-drift-telemetry.yml`

- **Name:** Audit Drift Telemetry
- **Triggers:** push:
- **Cron:** `10 * * * *`
- **Jobs:** `drift`
- **Scripts:** `./tools/drift/export_drift_metrics.ps1`, `./tools/drift/trigger_probation_actions.ps1`, `./tools/drift/validate_backtest_integrity.ps1`, `audit_dashboard/data/dashboard_data.js`, `audit_dashboard/data/drift_scores_latest.js`, `audit_dashboard/data/hourly_asset_class_24h_report.js`, `config/asset_class_map.js`, `config/drift_params.js`, `tmp/backtest_forward_drift_analysis.js`, `tmp/backtest_forward_drift_analysis.validated.js`, `tmp/strategy_probation_state.js`, `tools/drift/build_backtest_forward_drift.py`, `tools/drift/compute_dynamic_drift_score.js`
- **JSON I/O:** `audit_dashboard/data/dashboard_data.json`, `audit_dashboard/data/drift_scores_latest.json`, `audit_dashboard/data/hourly_asset_class_24h_report.json`, `config/asset_class_map.json`, `config/drift_params.json`, `tmp/backtest_forward_drift_analysis.json`, `tmp/backtest_forward_drift_analysis.validated.json`, `tmp/strategy_probation_state.json`

### `audit-impact-tracker.yml`

- **Name:** Audit Impact Tracker
- **Triggers:** schedule:
- **Cron:** `0 */6 * * *`
- **Jobs:** `audit-impact`
- **Scripts:** `.github/scripts/safe_push.sh`, `battleground/alpha_vs_beta_benchmark.py`, `battleground/audit_impact_tracker.py`, `battleground/data/alpha_benchmark_report.js`, `battleground/data/audit_baseline_20260313.js`, `battleground/data/audit_impact_results.js`
- **JSON I/O:** `battleground/data/alpha_benchmark_report.json`, `battleground/data/audit_baseline_20260313.json`, `battleground/data/audit_impact_results.json`

### `auto-retire-daily.yml`

- **Name:** Auto-Retire — Daily Bleeder Check
- **Triggers:** schedule:
- **Cron:** `30 9 * * *`
- **Jobs:** `retire-check`
- **Scripts:** `alpha_engine/auto_retire.py`, `alpha_engine/quarantine_manifest.js`
- **JSON I/O:** `alpha_engine/quarantine_manifest.json`, `quarantine_manifest.json`

### `automated-reporting.yml`

- **Name:** Automated Reporting
- **Triggers:** schedule:
- **Cron:** `0 8 * * *`, `0 9 * * 1`
- **Jobs:** `generate-report`
- **Scripts:** `.github/scripts/safe_push.sh`, `/latest.js`, `forward_testing/models/training_report.js`, `reports/health/latest.js`, `risk_management/models/risk_model_metadata.js`, `signal_aggregator/models/training_report.js`
- **JSON I/O:** `/latest.json`, `forward_testing/models/training_report.json`, `reports/health/latest.json`, `risk_management/models/risk_model_metadata.json`, `signal_aggregator/models/training_report.json`

### `autonomous_trading.yml`

- **Name:** Autonomous Trading Bot - Runs Automatically Every 4 Hours
- **Triggers:** schedule, push, workflow_dispatch
- **Cron:** `0 */4 * * *`
- **Jobs:** `trade`
- **Scripts:** `.github/scripts/safe_push.sh`, `live_trading_bot_canada.py`
- **JSON I/O:** `trading_results.json`

### `baby-strat-forward-paper.yml`

- **Name:** Baby Strat Real Forward Monitor
- **Triggers:** push:
- **Cron:** `15 * * * *`
- **Jobs:** `forward-monitor`
- **Scripts:** `.github/notify-failure.sh`, `.github/scripts/assert_no_conflict_markers.sh`, `.github/scripts/safe_push.sh`, `//download.py`, `battleground/data/active_picks.js`, `battleground/data/baby_strats_dashboard.js`, `battleground/data/closed_picks.js`, `battleground/data/incubator_ledger.js`, `battleground/data/incubator_signals.js`, `battleground/export_top_picks.py`, `battleground/incubator/run_incubator_strategies.py`, `battleground/rebuild_bundles.py`, `incubator/backtest_team/generate_baby_strats_dashboard.py`, `incubator/config/baby_strats_dashboard.js`, `incubator/validation/backfill_paper_window.py`, `incubator/validation/seed_paper_fasttrack.py`, `incubator/validation/update_forward_matches.py`, `ml_crypto_predictor/fetch_and_populate_db.py`, `paper_trading/strategies/championship_strategies_pt.py`, `paper_trading/strategies/hoffman_winning_strategies.py`
- **JSON I/O:** `.py.meta.json`, `battleground/data/active_picks.json`, `battleground/data/baby_strats_dashboard.json`, `battleground/data/closed_picks.json`, `battleground/data/incubator_ledger.json`, `battleground/data/incubator_signals.json`, `incubator/config/baby_strats_dashboard.json`

### `backfill-features.yml`

- **Name:** Backfill OHLCV Features
- **Triggers:** schedule:
- **Cron:** `0 4 * * *`
- **Jobs:** `backfill`
- **Scripts:** `.github/scripts/safe_push.sh`, `alpha_engine/data/closed_picks.js`
- **JSON I/O:** `alpha_engine/data/closed_picks.json`

### `backfill.yml`

- **Name:** Backfill Missing Audit Trail Sources
- **Triggers:** schedule:
- **Cron:** `0 */2 * * *`
- **Jobs:** `backfill`
- **Scripts:** `.github/scripts/safe_push.sh`

### `backtest-and-deploy.yml`

- **Name:** Run Backtests & Deploy Dashboards
- **Triggers:** schedule:
- **Cron:** `0 6 * * *`, `0 14,16,18,20 * * 1-5`, `0 */4 * * 0,6`
- **Jobs:** `backtest`
- **Scripts:** `.github/scripts/assert_no_conflict_markers.sh`, `.github/scripts/safe_push.sh`, `//torontoevent.net/riseoftheclaw/data/active_picks.js`, `//torontoevent.net/riseoftheclaw/data/live_competition.js`, `KIMI_CLAW_RESEARCH_FEB162026/backtest_framework.py`, `KIMI_CLAW_RESEARCH_FEB162026/generate_dashboard_data.py`, `KIMI_CLAW_RESEARCH_FEB162026/run_tier1_backtest.py`, `KIMI_CLAW_RESEARCH_FEB162026/strategies_tier1.py`, `KIMI_RISEOFTHECLAW/live_scanner.py`, `deploy_riseoftheclaw.py`, `generate_dashboard_data.py`, `live_scanner.py`, `tools/deploy_riseoftheclaw.py`
- **JSON I/O:** `//torontoevent.net/riseoftheclaw/data/active_picks.json`, `//torontoevent.net/riseoftheclaw/data/live_competition.json`

### `battle_test.yml`

- **Name:** Real-Time Battle Test - Eliminate Losers, Optimize Winners
- **Triggers:** schedule, push, workflow_dispatch
- **Cron:** `0 * * * *`
- **Jobs:** `battle-test`
- **Scripts:** `.github/scripts/safe_push.sh`, `battle_test_real_time.py`
- **JSON I/O:** `battle_test_results.json`

### `battleground-mass-backtest-part2.yml`

- **Name:** Battleground Mass Backtest (Part 2 - Babies)
- **Triggers:** workflow_dispatch:
- **Jobs:** `mass-backtest-babies`
- **Scripts:** `.github/scripts/safe_push.sh`, `incubator/backtest_team/batch_backtest_all.py`
- **JSON I/O:** `.meta.json`

### `battleground-mass-backtest.yml`

- **Name:** Battleground Mass Backtest
- **Triggers:** workflow_dispatch:
- **Jobs:** `mass-backtest`
- **Scripts:** `.github/scripts/assert_no_conflict_markers.sh`, `.github/scripts/safe_push.sh`, `incubator/backtest_team/batch_backtest_all.py`

### `benchmark-comparison.yml`

- **Name:** Benchmark Comparison  Daily
- **Triggers:** schedule:
- **Cron:** `0 7 * * *`
- **Jobs:** `benchmark`
- **Scripts:** `.github/scripts/safe_push.sh`, `alpha_engine/data/benchmark_comparison.js`
- **JSON I/O:** `alpha_engine/data/benchmark_comparison.json`

### `blacklist-reconciler.yml`

- **Name:** Blacklist Reconciler (cross-check vs live systems)
- **Triggers:** schedule:
- **Cron:** `0 4 * * *`
- **Jobs:** `reconcile`
- **Scripts:** `audit_dashboard/data/blacklist_reconciliation.js`, `tools/blacklist_reconciler.py`
- **JSON I/O:** `audit_dashboard/data/blacklist_reconciliation.json`

### `bond-agent.yml`

- **Name:** Bond Agent
- **Triggers:** schedule:
- **Cron:** `32 14 * * 1-5`
- **Jobs:** `bond-scan`
- **Scripts:** `.github/scripts/safe_push.sh`, `alpha_engine/bond_strategies.py`, `alpha_engine/data/active_picks.js`, `bond_strategies.py`, `non_crypto_agent/data/bond_picks.js`
- **JSON I/O:** `active_picks.json`, `alpha_engine/data/active_picks.json`, `bond_picks.json`, `non_crypto_agent/data/bond_picks.json`

### `breakout-arena.yml`

- **Name:** Breakout Arena  3 Approaches
- **Triggers:** schedule:
- **Cron:** `10 * * * *`
- **Jobs:** `scan-all`
- **Scripts:** `.github/scripts/safe_push.sh`

### `buy-now-analysis.yml`

- **Name:** Buy Now Analysis & Tracking
- **Triggers:** schedule:
- **Cron:** `0 */6 * * *`
- **Jobs:** `analyze-and-track`
- **Scripts:** `.github/scripts/safe_push.sh`, `signal_aggregator/buy_now_analysis.py`, `signal_aggregator/data/pick_tracking.js`
- **JSON I/O:** `signal_aggregator/data/pick_tracking.json`

### `check-streamer-status.yml`

- **Name:** Check Streamer Live Status
- **Triggers:** schedule:
- **Cron:** `0 */2 * * *`
- **Jobs:** `check-streamers`
- **Scripts:** `.github/scripts/check_streamer_status.py`
- **JSON I/O:** `streamer_check_results.json`

### `ci-tests.yml`

- **Name:** CI Tests
- **Triggers:** —
- **Jobs:** `test`
- **Scripts:** `matrix.py`

### `claude-gainer-ml-live.yml`

- **Name:** Claude Gainer ML  Live Scanner
- **Triggers:** schedule:
- **Cron:** `15,45 * * * *`
- **Jobs:** `scan`
- **Scripts:** `.github/notify-failure.sh`, `.github/scripts/safe_push.sh`, `claude_gainer_ml/tracker/claude_live_picks.js`, `claude_gainer_ml/tracker/claude_performance.js`, `live_scanner.py`, `updates/data/antigravity_ml_performance.js`, `updates/data/antigravity_ml_pick_history.js`
- **JSON I/O:** `claude_gainer_ml/tracker/claude_live_picks.json`, `claude_gainer_ml/tracker/claude_performance.json`, `claude_performance.json`, `updates/data/antigravity_ml_performance.json`, `updates/data/antigravity_ml_pick_history.json`

### `claude-gainer-short-term.yml`

- **Name:** Claude Gainer Short-Term Predictor
- **Triggers:** schedule:
- **Cron:** `7,37 * * * *`
- **Jobs:** `scan`
- **Scripts:** `.github/scripts/safe_push.sh`, `claude_gainer_ml.sh`, `data/freshpicks_gate_state.js`
- **JSON I/O:** `data/freshpicks_gate_state.json`, `short_term_closed.json`

### `claude-gainer-tracker.yml`

- **Name:** Claude Code Gainer ML Tracker
- **Triggers:** schedule:
- **Cron:** `15 */4 * * *`, `15 13 * * *`, `0 6 * * 0`
- **Jobs:** `predict-and-track`, `weekly-retrain`
- **Scripts:** `.github/scripts/safe_push.sh`, `claude_gainer_ml/data/gainer_predictions.js`, `claude_gainer_ml/models/improvement_log.js`, `claude_gainer_ml/models/training_meta.js`, `claude_gainer_ml/tracker/claude_live_picks.js`, `claude_gainer_ml/tracker/claude_performance.js`, `claude_gainer_ml/tracker/claude_pick_history.js`, `claude_gainer_ml/tracker/claude_scan_log.js`, `claude_gainer_ml/tracker/freshpicks_sent.js`, `data/freshpicks_gate_state.js`, `live_scanner.py`, `self_improver.py`, `tp_sl_tracker.py`, `trigger_retraining.py`, `updates/data/antigravity_ml_performance.js`, `updates/data/claude_ml_history.js`, `updates/data/claude_ml_performance.js`, `updates/data/claude_ml_picks.js`, `updates/data/claude_ml_scan_log.js`, `updates/data/dashboard_status.js`
- **JSON I/O:** `claude_gainer_ml/data/gainer_predictions.json`, `claude_gainer_ml/models/improvement_log.json`, `claude_gainer_ml/models/training_meta.json`, `claude_gainer_ml/tracker/claude_live_picks.json`, `claude_gainer_ml/tracker/claude_performance.json`, `claude_gainer_ml/tracker/claude_pick_history.json`, `claude_gainer_ml/tracker/claude_scan_log.json`, `claude_gainer_ml/tracker/freshpicks_sent.json`, `data/freshpicks_gate_state.json`, `updates/data/antigravity_ml_performance.json`, `updates/data/claude_ml_history.json`, `updates/data/claude_ml_performance.json`, `updates/data/claude_ml_picks.json`, `updates/data/claude_ml_scan_log.json`, `updates/data/dashboard_status.json`

### `claudes-test-portfolios.yml`

- **Name:** Claude's Test - Portfolio Manager
- **Triggers:** schedule:
- **Cron:** `*/30 * * * *`
- **Jobs:** `manage-portfolios`
- **Scripts:** `.github/scripts/assert_no_conflict_markers.sh`, `.github/scripts/safe_push.sh`, `audit_dashboard/data/claudes_test_dashboard.js`, `audit_dashboard/data/claudes_test_state.js`, `audit_dashboard/portfolio_manager.py`
- **JSON I/O:** `audit_dashboard/data/claudes_test_dashboard.json`, `audit_dashboard/data/claudes_test_state.json`

### `clear-channel-command.yml`

- **Name:** Clear Channel Command
- **Triggers:** workflow_dispatch:
- **Jobs:** `clear-channel`
- **Scripts:** `signal_aggregator/clear_channel_command.py`

### `closed-picks-command.yml`

- **Name:** Closed Picks Command
- **Triggers:** workflow_dispatch:
- **Jobs:** `send-closed-picks`
- **Scripts:** `signal_aggregator/closed_picks_command.py`

### `coinglass-scanner.yml`

- **Name:** Coinglass DNA Scanner
- **Triggers:** schedule:
- **Cron:** `3 * * * *`
- **Jobs:** `scan`
- **Scripts:** `.github/scripts/safe_push.sh`, `coinglass_strategies/data/active_picks.js`, `coinglass_strategies/data/reconciled_ids.js`, `safe_push.sh`
- **JSON I/O:** `coinglass_strategies/data/active_picks.json`, `coinglass_strategies/data/reconciled_ids.json`

### `commodities-agent.yml`

- **Name:** Commodities Agent
- **Triggers:** schedule:
- **Cron:** `0 10 * * 1-5`, `0 20 * * 1-5`
- **Jobs:** `commodities-scan`
- **Scripts:** `.github/scripts/safe_push.sh`, `non_crypto_agent/data/commodities_picks.js`
- **JSON I/O:** `non_crypto_agent/data/commodities_picks.json`

### `conflict-marker-check.yml`

- **Name:** Conflict Marker Check
- **Triggers:** —
- **Jobs:** `scan`

### `consensus-outcome-tracker.yml`

- **Name:** Consensus Outcome Tracker
- **Triggers:** schedule:
- **Cron:** `*/30 * * * *`
- **Jobs:** `track-outcomes`
- **Scripts:** `.github/scripts/safe_push.sh`, `cross_aggregation/data/consensus_outcomes.js`, `safe_push.sh`
- **JSON I/O:** `cross_aggregation/data/consensus_outcomes.json`

### `contested-pick-checker.yml`

- **Name:** Contested Pick Checker (Claude vs Antigravity)
- **Triggers:** schedule:
- **Cron:** `0 * * * *`
- **Jobs:** `check-contested`
- **Scripts:** `.github/scripts/safe_push.sh`, `cross_aggregation/contested_pick_checker.py`, `cross_aggregation/data/contested_picks_tracker.js`
- **JSON I/O:** `cross_aggregation/data/contested_picks_tracker.json`

### `continuous-improvement-monitor.yml`

- **Name:** Continuous Improvement Monitor
- **Triggers:** schedule:
- **Cron:** `36 */2 * * *`
- **Jobs:** `monitor`
- **Scripts:** `.github/scripts/safe_commit_push.sh`, `alpha_engine/__init__.py`, `alpha_engine/data/continuous_improvement_history.js`, `alpha_engine/data/continuous_improvement_report.js`
- **JSON I/O:** `alpha_engine/data/continuous_improvement_history.json`, `alpha_engine/data/continuous_improvement_report.json`

### `conviction-picks.yml`

- **Name:** Conviction Picks Ultra-Selective Discord Alert
- **Triggers:** workflow_dispatch:
- **Cron:** `56 * * * *`
- **Jobs:** `conviction-picks`
- **Scripts:** `.github/scripts/safe_push.sh`, `cross_aggregation/data/conviction_picks.js`, `cross_aggregation/data/conviction_sent.js`
- **JSON I/O:** `cross_aggregation/data/conviction_picks.json`, `cross_aggregation/data/conviction_sent.json`

### `copy-trader-forward-test.yml`

- **Name:** Copy Trader Forward Test
- **Triggers:** schedule:
- **Cron:** `17 * * * *`
- **Jobs:** `forward-test`
- **Scripts:** `.github/scripts/safe_push.sh`, `alpha_engine/data/portfolio_copytrader.js`, `alpha_engine/data/portfolio_copytrader_raw.js`, `alpha_engine/portfolio_tracker_copytrader.py`, `alpha_engine/portfolio_tracker_copytrader_raw.py`, `copy_trader_intel/outcome_resolver.py`, `safe_push.sh`
- **JSON I/O:** `alpha_engine/data/portfolio_copytrader.json`, `alpha_engine/data/portfolio_copytrader_raw.json`

### `copy-trader-intelligence.yml`

- **Name:** Copy Trader Intelligence  Scrape + Analyze + Track
- **Triggers:** schedule:
- **Cron:** `7,52 * * * *`
- **Jobs:** `copy-trader-scan`
- **Scripts:** `.github/scripts/safe_commit_push.sh`, `alpha_engine/data/active_picks.js`, `alpha_engine/data/copy_trader_patterns.js`, `alpha_engine/data/portfolio_1x.js`, `alpha_engine/data/portfolio_20x.js`, `alpha_engine/data/portfolio_copytrader.js`, `alpha_engine/data/portfolio_copytrader_dashboard.js`, `alpha_engine/portfolio_tracker_1x.py`, `alpha_engine/portfolio_tracker_20x.py`, `alpha_engine/portfolio_tracker_copytrader.py`, `copy_trader_intel/data/active_picks.js`, `copy_trader_intel/data/bingx_picks.js`, `copy_trader_intel/data/bingx_trader_profiles.js`, `copy_trader_intel/data/bitget_picks.js`, `copy_trader_intel/data/bitget_trader_profiles.js`, `copy_trader_intel/data/bybit_picks.js`, `copy_trader_intel/data/bybit_trader_profiles.js`, `copy_trader_intel/data/closed_trades.js`, `copy_trader_intel/data/copin_picks.js`, `copy_trader_intel/data/copin_trader_profiles.js`, `copy_trader_intel/data/dex_picks.js`, `copy_trader_intel/data/dex_trader_profiles.js`, `copy_trader_intel/data/dex_whale_picks.js`, `copy_trader_intel/data/dydx_picks.js`, `copy_trader_intel/data/dydx_trader_profiles.js` … (+26)
- **JSON I/O:** `alpha_engine/data/active_picks.json`, `alpha_engine/data/copy_trader_patterns.json`, `alpha_engine/data/portfolio_1x.json`, `alpha_engine/data/portfolio_20x.json`, `alpha_engine/data/portfolio_copytrader.json`, `alpha_engine/data/portfolio_copytrader_dashboard.json`, `copy_trader_intel/data/active_picks.json`, `copy_trader_intel/data/bingx_picks.json`, `copy_trader_intel/data/bingx_trader_profiles.json`, `copy_trader_intel/data/bitget_picks.json`, `copy_trader_intel/data/bitget_trader_profiles.json`, `copy_trader_intel/data/bybit_picks.json`, `copy_trader_intel/data/bybit_trader_profiles.json`, `copy_trader_intel/data/closed_trades.json`, `copy_trader_intel/data/copin_picks.json`, `copy_trader_intel/data/copin_trader_profiles.json`, `copy_trader_intel/data/dex_picks.json`, `copy_trader_intel/data/dex_trader_profiles.json`, `copy_trader_intel/data/dex_whale_picks.json`, `copy_trader_intel/data/dydx_picks.json` … (+22)

### `copytrader-tracker.yml`

- **Name:** Copy Trader Portfolio Tracker
- **Triggers:** schedule:
- **Cron:** `42 */2 * * *`
- **Jobs:** `track-copytrader`
- **Scripts:** `.github/scripts/safe_push.sh`, `alpha_engine/data/portfolio_copytrader.js`, `alpha_engine/portfolio_tracker_copytrader.py`
- **JSON I/O:** `alpha_engine/data/portfolio_copytrader.json`

### `correlation-monitor.yml`

- **Name:** Cross-Asset Correlation Monitor
- **Triggers:** schedule:
- **Cron:** `15 0,6,12,18 * * *`
- **Jobs:** `correlation-monitor`
- **Scripts:** `.github/scripts/safe_push.sh`, `alpha_engine/correlation_monitor.py`, `alpha_engine/data/correlation_report.js`
- **JSON I/O:** `alpha_engine/data/correlation_report.json`

### `cross-aggregator.yml`

- **Name:** Cross-System Signal Aggregator
- **Triggers:** schedule:
- **Cron:** `8,38 * * * *`
- **Jobs:** `aggregate`
- **Scripts:** `.github/scripts/safe_push.sh`, `alpha_engine/data/closed_picks.js`, `cross_aggregation/aggregator.py`, `cross_aggregation/data/beta_score_tracker.js`, `cross_aggregation/data/consensus_outcomes.js`, `cross_aggregation/data/forward_test_results.js`, `cross_aggregation/data/super_signals.js`, `data/aggregated_picks.js`, `data/elite_picks.js`, `data/experimental_picks.js`, `data/freshpicks_consensus_sent.js`, `data/freshpicks_gate_state.js`, `mercury2/data/closed_picks.js`, `ml_battleground/system_f_clawsofdoom/data/closed_picks.js`, `signal_aggregator/audit_push.py`, `smart_money/data/active_picks.js`, `smart_money/scanner.py`
- **JSON I/O:** `aggregated_picks.json`, `alpha_engine/data/closed_picks.json`, `cross_aggregation/data/beta_score_tracker.json`, `cross_aggregation/data/consensus_outcomes.json`, `cross_aggregation/data/forward_test_results.json`, `cross_aggregation/data/super_signals.json`, `data/aggregated_picks.json`, `data/elite_picks.json`, `data/experimental_picks.json`, `data/freshpicks_consensus_sent.json`, `data/freshpicks_gate_state.json`, `mercury2/data/closed_picks.json`, `ml_battleground/system_f_clawsofdoom/data/closed_picks.json`, `smart_money/data/active_picks.json`

### `crypto-ml-edge.yml`

- **Name:** Crypto ML Edge GSD Scanner
- **Triggers:** schedule:
- **Cron:** `*/30 * * * *`
- **Jobs:** `scan`
- **Scripts:** `.github/scripts/safe_push.sh`, `crypto_ml_edge/audit_push.py`, `crypto_ml_edge/data/active_picks.js`
- **JSON I/O:** `crypto_ml_edge/data/active_picks.json`

### `crypto-ml-tracker.yml`

- **Name:** Crypto Gainer ML Live Tracker
- **Triggers:** schedule:
- **Cron:** `0 * * * *`
- **Jobs:** `predict-and-track`
- **Scripts:** `.github/scripts/safe_push.sh`, `crypto_gainer_ml/tracker/live_picks.js`, `crypto_gainer_ml/tracker/performance_summary.js`, `crypto_gainer_ml/tracker/pick_history.js`, `crypto_gainer_ml/tracker/scorecard.js`, `live_predictor.py`, `updates/data/cursor_ml_history.js`, `updates/data/cursor_ml_performance.js`, `updates/data/cursor_ml_picks.js`, `updates/data/cursor_ml_scorecard.js`
- **JSON I/O:** `crypto_gainer_ml/tracker/live_picks.json`, `crypto_gainer_ml/tracker/performance_summary.json`, `crypto_gainer_ml/tracker/pick_history.json`, `crypto_gainer_ml/tracker/scorecard.json`, `updates/data/cursor_ml_history.json`, `updates/data/cursor_ml_performance.json`, `updates/data/cursor_ml_picks.json`, `updates/data/cursor_ml_scorecard.json`

### `crypto-smart-picks.yml`

- **Name:** CRYPTO SMART PICKS - Portfolio A/B/C/D Scanner
- **Triggers:** schedule:
- **Cron:** `47 */2 * * *`
- **Jobs:** `crypto-smart-picks`
- **Scripts:** `.github/scripts/safe_push.sh`, `alpha_engine/data/crypto_portfolio_backtest.js`, `alpha_engine/data/crypto_smart_picks.js`, `crypto_portfolio_backtest.py`, `crypto_smart_picks.py`
- **JSON I/O:** `alpha_engine/data/crypto_portfolio_backtest.json`, `alpha_engine/data/crypto_smart_picks.json`

### `crypto-test-portfolios.yml`

- **Name:** Crypto Test Portfolios
- **Triggers:** schedule:
- **Cron:** `15 */4 * * *`
- **Jobs:** `portfolio-tracker`
- **Scripts:** `.github/scripts/safe_push.sh`, `alpha_engine/crypto_test_portfolios.py`, `alpha_engine/data/crypto_portfolio_results.js`, `alpha_engine/data/crypto_portfolio_state.js`
- **JSON I/O:** `alpha_engine/data/crypto_portfolio_results.json`, `alpha_engine/data/crypto_portfolio_state.json`

### `crypto-winner-scan.yml`

- **Name:** Crypto Winner Scanner  Auto Scan
- **Triggers:** schedule:
- **Cron:** `*/15 * * * *`, `0 */6 * * *`, `0 3 * * 0`
- **Jobs:** `scan-and-track`

### `daily-feed-summary.yml`

- **Name:** Daily Feed Summary
- **Triggers:** schedule:
- **Cron:** `0 */2 * * *`
- **Jobs:** `generate-summary`
- **Scripts:** `.github/notify-failure.sh`, `.github/scripts/safe_push.sh`, `/findtorontoevents.ca/daily-feed/data/summary.js`, `daily-feed/data/summary.js`, `scripts/daily_feed_summary.py`
- **JSON I/O:** `/findtorontoevents.ca/daily-feed/data/summary.json`, `daily-feed/data/summary.json`

### `daily-miracle-scan.yml`

- **Name:** Daily Miracle DayTrades Scan
- **Triggers:** schedule:
- **Cron:** `0 23 * * 1-5`
- **Jobs:** `miracle-scan`

### `daily-mutualfund-refresh.yml`

- **Name:** Daily Mutual Fund Refresh (DISABLED)
- **Triggers:** workflow_dispatch
- **Jobs:** `refresh`

### `daily-picks-snapshot.yml`

- **Name:** Daily Picks Snapshot  Crypto, Forex & Stocks
- **Triggers:** schedule:
- **Cron:** `0 22 * * 1-5`, `0 5 * * 1`
- **Jobs:** `daily-snapshot`

### `daily-price-refresh.yml`

- **Name:** Daily Price Refresh
- **Triggers:** schedule:
- **Cron:** `0 22 * * 1-5`, `0 2 * * 2-6`
- **Jobs:** `refresh-prices`

### `daily-stock-refresh.yml`

- **Name:** Daily Stock Data Refresh
- **Triggers:** schedule:
- **Cron:** `30 22 * * 1-5`, `0 14 * * 1-5`
- **Jobs:** `refresh-stock-data`

### `daily_runs.yml`

- **Name:** Daily Runs
- **Triggers:** schedule:
- **Cron:** `0 0 * * *`
- **Jobs:** `run-daily`
- **Scripts:** `corr_pruner.py`, `garch_vol.py`, `hmm_regime.py`, `kelly_sizer.py`, `meta_label.py`

### `darwin-evolution.yml`

- **Name:** DARWIN ENGINE - DNA Evolution Pipeline
- **Triggers:** schedule:
- **Cron:** `0 * * * *`
- **Jobs:** `evolve`
- **Scripts:** `.github/scripts/assert_no_conflict_markers.sh`, `.github/scripts/safe_push.sh`, `genome/audit_ensemble_evolver.py`, `genome/darwin_portfolio_tracker.py`, `genome/ensemble_evolver.py`, `genome/failure_evolver.py`, `genome/genetic_programmer.py`, `genome/mape_evolver.py`, `genome/revive_stale_systems.py`

### `dashboard-pick-trader.yml`

- **Name:** Dashboard Pick Trader
- **Triggers:** schedule:
- **Cron:** `43 * * * *`
- **Jobs:** `trade-dashboard-picks`
- **Scripts:** `.github/scripts/safe_push.sh`, `alpha_engine/dashboard_pick_trader.py`, `alpha_engine/data/dashboard_trader_log.js`, `alpha_engine/data/portfolio_1x.js`, `alpha_engine/data/portfolio_20x.js`
- **JSON I/O:** `alpha_engine/data/dashboard_trader_log.json`, `alpha_engine/data/portfolio_1x.json`, `alpha_engine/data/portfolio_20x.json`

### `data-pipeline-test.yml`

- **Name:** Data Pipeline Reliability Test
- **Triggers:** schedule:
- **Cron:** `0 */6 * * *`
- **Jobs:** `test-data-sources`
- **Scripts:** `.github/scripts/safe_push.sh`, `tools/data_pipeline_healthcheck.py`
- **JSON I/O:** `data_source_health.json`

### `db-backup-email.yml`

- **Name:** FINDTORONTOEVENTS.CA Database Backups
- **Triggers:** schedule:
- **Cron:** `0 4 * * *`
- **Jobs:** `backup-source-site`

### `db-sync-bidirectional.yml`

- **Name:** DB Sync: Bi-directional User Data
- **Triggers:** schedule:
- **Cron:** `0 8 * * *`
- **Jobs:** `bidirectional-sync`

### `db-sync-to-mirror.yml`

- **Name:** DB Sync: findtorontoevents.ca  torontoevent.net
- **Triggers:** schedule:
- **Cron:** `0 6 * * *`
- **Jobs:** `sync-databases`

### `deals-refresh.yml`

- **Name:** Deals & Freebies  Verify & Refresh
- **Triggers:** schedule:
- **Cron:** `0 14 * * 1`, `0 14 1 * *`
- **Jobs:** `verify-deals`

### `decile-separation-test.yml`

- **Name:** Decile Separation Test
- **Triggers:** schedule:
- **Cron:** `0 6 * * *`
- **Jobs:** `decile-test`
- **Scripts:** `.github/scripts/safe_push.sh`, `alpha_engine/data/closed_picks.js`, `alpha_engine/decile_separation_test.py`, `data/decile_test.js`
- **JSON I/O:** `alpha_engine/data/closed_picks.json`, `data/decile_test.json`

### `deploy-alpha-dashboard.yml`

- **Name:** Deploy Alpha Engine Dashboard
- **Triggers:** push:
- **Jobs:** `deploy`

### `deploy-battleground-ftp.yml`

- **Name:** Deploy Battleground to FTP
- **Triggers:** push:
- **Jobs:** `deploy`
- **Scripts:** `.github/notify-failure.sh`, `battleground/app.js`

### `deploy-competition-to-site.yml`

- **Name:** Deploy Competition to Live Site
- **Triggers:** push:
- **Jobs:** `deploy`
- **Scripts:** `STOCKS/competition/competition-crypto.js`, `STOCKS/competition/competition-forex.js`, `STOCKS/competition/competition-meme_coins.js`, `STOCKS/competition/competition-penny_stocks.js`, `STOCKS/competition/competition-slim.js`, `STOCKS/competition/competition-stocks.js`, `STOCKS/competition/forward_picks.js`, `audit_dashboard/data/claudes_test_dashboard.js`, `audit_dashboard/data/claudes_test_state.js`, `backtest_cursor.py`, `cross_aggregation/data/conflict_lessons_learned.js`, `cross_aggregation/data/consensus_outcomes.js`, `cross_aggregation/data/contested_picks_tracker.js`, `cross_aggregation/data/super_signals.js`, `simpleton_backtest.py`, `simpleton_backtester.py`
- **JSON I/O:** `STOCKS/competition/competition-crypto.json`, `STOCKS/competition/competition-forex.json`, `STOCKS/competition/competition-meme_coins.json`, `STOCKS/competition/competition-penny_stocks.json`, `STOCKS/competition/competition-slim.json`, `STOCKS/competition/competition-stocks.json`, `STOCKS/competition/forward_picks.json`, `audit_dashboard/data/claudes_test_dashboard.json`, `audit_dashboard/data/claudes_test_state.json`, `cross_aggregation/data/conflict_lessons_learned.json`, `cross_aggregation/data/consensus_outcomes.json`, `cross_aggregation/data/contested_picks_tracker.json`, `cross_aggregation/data/super_signals.json`

### `deploy-fc-api-env-godaddy.yml`

- **Name:** Deploy fc/api/.env to GoDaddy (torontoevent.net)
- **Triggers:** workflow_dispatch:
- **Jobs:** `deploy-env`

### `deploy-fc-api-hotfix.yml`

- **Name:** Deploy FC API Hotfix (3 domains)
- **Triggers:** workflow_dispatch:
- **Jobs:** `deploy`

### `deploy-fc-frontend.yml`

- **Name:** Deploy FavCreators Frontend (/fc/)
- **Triggers:** push:
- **Jobs:** `deploy`

### `deploy-findcryptopairs-ftp.yml`

- **Name:** Deploy FindCryptoPairs to FTP
- **Triggers:** push:
- **Cron:** `15 */6 * * *`
- **Jobs:** `deploy`

### `deploy-friendtracker.yml`

- **Name:** Deploy FriendTracker
- **Triggers:** push:
- **Jobs:** `deploy`
- **Scripts:** `//findtorontoevents.ca/friendtracker/script.js`

### `deploy-fte-events-json.yml`

- **Name:** Deploy findtorontoevents.ca next/events.json
- **Triggers:** workflow_dispatch:
- **Jobs:** `deploy`
- **Scripts:** `//findtorontoevents.ca/next/events.js`, `/next/events.js`, `/tmp/events_bak.js`, `next/events.js`
- **JSON I/O:** `//findtorontoevents.ca/next/events.json`, `/next/events.json`, `/tmp/events_bak.json`, `events.json`, `last_update.json`, `next/events.json`

### `deploy-fte-index.yml`

- **Name:** Deploy findtorontoevents.ca core site
- **Triggers:** workflow_dispatch:
- **Jobs:** `deploy`
- **Scripts:** `//findtorontoevents.ca/next/events.js`, `/next/events.js`, `findtorontoevents.ca/events.js`, `findtorontoevents.ca/last_update.js`, `findtorontoevents.ca/next/events.js`, `hashlib.sh`, `next/events.js`
- **JSON I/O:** `//findtorontoevents.ca/next/events.json`, `/next/events.json`, `events.json`, `findtorontoevents.ca/events.json`, `findtorontoevents.ca/last_update.json`, `findtorontoevents.ca/next/events.json`, `last_update.json`, `next/events.json`

### `deploy-movieshows-all.yml`

- **Name:** Deploy MOVIESHOWS2 + MOVIESHOWS3 (All 3 Domains)
- **Triggers:** workflow_dispatch:
- **Jobs:** `deploy`
- **Scripts:** `TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS/ms1-upgrade-toast.js`, `TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS2/categories.js`, `TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS2/db-connector.js`, `TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS2/features.js`, `TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS2/freestyle.js`, `TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS2/motivation.js`, `TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS2/ms2-enhancer.js`, `TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS2/script.js`, `TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS2/scroll-fix.js`, `TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS2/ui-cleanup.js`, `TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS2/ui-minimal.js`

### `deploy-movieshows3-hotfix.yml`

- **Name:** Deploy MOVIESHOWS3 Hotfix
- **Triggers:** workflow_dispatch:
- **Jobs:** `deploy`

### `deploy-pages.yml`

- **Name:** Deploy to GitHub Pages (DISABLED)
- **Triggers:** workflow_dispatch:
- **Jobs:** `build`, `deploy`
- **Scripts:** `STOCKS/competition/competition-slim.js`, `battleground/app.js`, `crypto_ml_edge/data/active_picks.js`, `incubator/config/baby_strats_dashboard.js`
- **JSON I/O:** `STOCKS/competition/competition-slim.json`, `crypto_ml_edge/data/active_picks.json`, `events.json`, `incubator/config/baby_strats_dashboard.json`, `last_update.json`

### `deploy-riseoftheclaw.yml`

- **Name:** Deploy Rise of the Claw Dashboard
- **Triggers:** schedule, workflow_dispatch
- **Cron:** `0,30 * * * *`
- **Jobs:** `deploy`
- **Scripts:** `.github/scripts/safe_push.sh`, `KIMI_RISEOFTHECLAW/audit_push.py`, `KIMI_RISEOFTHECLAW/data/active_picks.js`, `KIMI_RISEOFTHECLAW/data/algorithms.js`, `KIMI_RISEOFTHECLAW/data/freshpicks_sent.js`, `KIMI_RISEOFTHECLAW/data/live_competition.js`, `KIMI_RISEOFTHECLAW/data/live_signals_now.js`, `KIMI_RISEOFTHECLAW/data/paper_portfolio.js`, `KIMI_RISEOFTHECLAW/data/signal_tracking.js`, `KIMI_RISEOFTHECLAW/live_scanner.py`, `KIMI_RISEOFTHECLAW/signal_tracker.py`, `STOCKS/competition/competition-slim.js`, `_site/asterdex/data/dashboard.js`, `_site/audit/antigravity_picks_data.js`, `_site/audit/data/dashboard_data.js`, `_site/audit/data/dashboard_payload.js`, `_site/audit/data/grok_top_picks.js`, `_site/audit/data/kimi_best_3_current.js`, `_site/audit/data/kimi_top_3_live_picks.js`, `_site/audit/data/mercury_top_picks.js`, `_site/audit/data/stock_prices.js`, `_site/audit/data/universal_resolved_picks.js`, `_site/audit/symbol_predictability.js`, `_site/audit/tournament_results.js`, `_site/battleground/app.js` … (+58)
- **JSON I/O:** `KIMI_RISEOFTHECLAW/data/active_picks.json`, `KIMI_RISEOFTHECLAW/data/algorithms.json`, `KIMI_RISEOFTHECLAW/data/freshpicks_sent.json`, `KIMI_RISEOFTHECLAW/data/live_competition.json`, `KIMI_RISEOFTHECLAW/data/live_signals_now.json`, `KIMI_RISEOFTHECLAW/data/paper_portfolio.json`, `KIMI_RISEOFTHECLAW/data/signal_tracking.json`, `STOCKS/competition/competition-slim.json`, `_site/asterdex/data/dashboard.json`, `_site/audit/antigravity_picks_data.json`, `_site/audit/data/dashboard_data.json`, `_site/audit/data/dashboard_payload.json`, `_site/audit/data/grok_top_picks.json`, `_site/audit/data/kimi_best_3_current.json`, `_site/audit/data/kimi_top_3_live_picks.json`, `_site/audit/data/mercury_top_picks.json`, `_site/audit/data/stock_prices.json`, `_site/audit/data/universal_resolved_picks.json`, `_site/audit/symbol_predictability.json`, `_site/audit/tournament_results.json` … (+61)

### `deploy-vetted-picks.yml`

- **Name:** Deploy Vetted Master-Picks
- **Triggers:** workflow_dispatch:
- **Cron:** `15 */4 * * *`
- **Jobs:** `deploy-vetted-picks`
- **Scripts:** `.github/scripts/safe_push.sh`, `signal_aggregator/data/master_picks_history.js`, `signal_aggregator/data/master_picks_tracker.js`, `signal_aggregator/deploy_vetted_picks.py`
- **JSON I/O:** `signal_aggregator/data/master_picks_history.json`, `signal_aggregator/data/master_picks_tracker.json`

### `deploy_bundle.yml`

- **Name:** Deploy Strategy Bundle
- **Triggers:** workflow_dispatch:
- **Jobs:** `validate`, `deploy`
- **Scripts:** `deploy_prod_bundle.py`
- **JSON I/O:** `validation_results.json`

### `discord-bot.yml`

- **Name:** Discord Bot  Persistent
- **Triggers:** workflow_dispatch:
- **Cron:** `5 */6 * * *`
- **Jobs:** `run-bot`
- **Scripts:** `discord.py`, `discord_bot.py`

### `discord-heartbeat.yml`

- **Name:** Discord Channel Heartbeat
- **Triggers:** schedule:
- **Cron:** `0 */4 * * *`
- **Jobs:** `heartbeat`
- **Scripts:** `scripts/discord_heartbeat.py`

### `discord-status.yml`

- **Name:** Discord ML Status Report
- **Triggers:** schedule:
- **Cron:** `0 * * * *`
- **Jobs:** `send-status`

### `discord_status.yml`

- **Name:** ANTIGRAVITY ML  Hourly Discord Status + Picks
- **Triggers:** schedule:
- **Cron:** `0 * * * *`
- **Jobs:** `post-status`
- **Scripts:** `ml_crypto_predictor/enhanced_models/discord_status.py`

### `dna-mutation-cycle.yml`

- **Name:** DNA Mutation Cycle
- **Triggers:** schedule:
- **Cron:** `0 5 * * *`
- **Jobs:** `mutation-cycle`
- **Scripts:** `.github/scripts/safe_push.sh`, `alpha_engine/data/dna_mutations.js`, `alpha_engine/dna_mutation_engine.py`, `data/closed_picks.js`
- **JSON I/O:** `alpha_engine/data/dna_mutations.json`, `data/closed_picks.json`

### `dna_strategy_pipeline.yml`

- **Name:** DNA Strategy Pipeline
- **Triggers:** push:
- **Cron:** `11 */4 * * *`
- **Jobs:** `evolve-strategies`, `generate-picks`, `phoenix-revival`, `notify`, `factory-register`, `check-promotions`, `evaluate-promotions`
- **Scripts:** `.github/scripts/safe_push.sh`, `battleground/data/dna_factory_registry.js`, `genome/active_picks.js`, `genome/dna_strategy_factory.py`, `genome/evolve_strategies.py`, `genome/generate_picks.py`, `genome/progressive_promotion.py`
- **JSON I/O:** `battleground/data/dna_factory_registry.json`, `genome/active_picks.json`

### `dynamic-alpha-engine.yml`

- **Name:** ALPHA ENGINE - Dynamic Runner (Cloud or Local)
- **Triggers:** schedule:
- **Cron:** `18,48 * * * *`
- **Jobs:** `wsl-direct`, `alpha-engine`
- **Scripts:** `alpha_engine/production_scanner.py`, `production_scanner.py`, `safe_push.sh`

### `dynamic-universe.yml`

- **Name:** Dynamic Universe Scanner
- **Triggers:** schedule:
- **Cron:** `37 */2 * * *`
- **Jobs:** `update-universe`
- **Scripts:** `.github/scripts/safe_push.sh`, `alpha_engine/data/dynamic_universe.js`, `alpha_engine/dynamic_universe.py`
- **JSON I/O:** `alpha_engine/data/dynamic_universe.json`

### `edge-decay-check.yml`

- **Name:** Edge decay monitor
- **Triggers:** —
- **Cron:** `20 7 * * 1-5`
- **Jobs:** `monitor`
- **Scripts:** `audit_trail/data/edge_decay_report.js`, `tools/edge_decay_monitor.py`
- **JSON I/O:** `audit_trail/data/edge_decay_report.json`

### `ema-retracement-scan.yml`

- **Name:** EMA Retracement Mean Reversion Scanner
- **Triggers:** schedule:
- **Cron:** `15 * * * *`
- **Jobs:** `ema-retracement`
- **Scripts:** `.github/scripts/safe_push.sh`, `alpha_engine/data/ema_retracement_backtest.js`, `alpha_engine/ema_retracement_strategy.py`
- **JSON I/O:** `alpha_engine/data/ema_retracement_backtest.json`

### `enhanced-ml-crypto.yml`

- **Name:** Enhanced ML Crypto Train & Predict
- **Triggers:** schedule, workflow_dispatch
- **Cron:** `0 2 * * *`, `19 */2 * * *`
- **Jobs:** `enhanced-ml`
- **Scripts:** `.github/scripts/safe_push.sh`, `alpha_engine/data/active_picks.js`, `alpha_engine/data/ml_reviver_picks.js`, `crypto_gainer_ml/tracker/enhanced_ml_picks.js`, `feature_engine.py`, `ml_crypto_predictor/enhanced_models/ab_tests/ab_test_report.js`, `ml_crypto_predictor/enhanced_models/export_picks.py`, `ml_crypto_predictor/enhanced_models/results/current_regime.js`, `ml_crypto_predictor/enhanced_models/results/training_summary.js`, `ml_reviver_merger.py`, `ml_strategy_reviver.py`, `updates/data/enhanced_ml_ab_test.js`, `updates/data/enhanced_ml_predictions.js`, `updates/data/enhanced_ml_regime.js`, `updates/data/enhanced_ml_training.js`
- **JSON I/O:** `active_picks.json`, `alpha_engine/data/active_picks.json`, `alpha_engine/data/ml_reviver_picks.json`, `crypto_gainer_ml/tracker/enhanced_ml_picks.json`, `ml_crypto_predictor/enhanced_models/ab_tests/ab_test_report.json`, `ml_crypto_predictor/enhanced_models/results/current_regime.json`, `ml_crypto_predictor/enhanced_models/results/training_summary.json`, `updates/data/enhanced_ml_ab_test.json`, `updates/data/enhanced_ml_predictions.json`, `updates/data/enhanced_ml_regime.json`, `updates/data/enhanced_ml_training.json`

### `equities-agent.yml`

- **Name:** Equities & Stocks Agent
- **Triggers:** schedule:
- **Cron:** `0 13 * * 1-5`, `0 21 * * 1-5`
- **Jobs:** `equities-scan`
- **Scripts:** `.github/scripts/safe_push.sh`, `non_crypto_agent/data/equities_picks.js`
- **JSON I/O:** `non_crypto_agent/data/equities_picks.json`

### `etf-agent.yml`

- **Name:** ETF Agent
- **Triggers:** schedule:
- **Cron:** `30 14 * * 1-5`
- **Jobs:** `etf-scan`
- **Scripts:** `.github/scripts/safe_push.sh`, `non_crypto_agent/data/etf_picks.js`
- **JSON I/O:** `non_crypto_agent/data/etf_picks.json`

### `etf-bond-scanner.yml`

- **Name:** ETF & Bond Scanner
- **Triggers:** schedule:
- **Cron:** `35 13 * * 1-5`, `0 14 * * 1-5`
- **Jobs:** `etf-scan`, `bond-scan`
- **Scripts:** `alpha_engine/data/scanner_output/active_picks_bond.js`, `alpha_engine/data/scanner_output/active_picks_etf.js`
- **JSON I/O:** `active_picks.json`, `alpha_engine/data/scanner_output/active_picks_bond.json`, `alpha_engine/data/scanner_output/active_picks_etf.json`

### `fast-stocks-competition.yml`

- **Name:** Fast Stocks Competition  High Frequency Scanner
- **Triggers:** workflow_dispatch
- **Cron:** `0 14,18 * * 1-5`
- **Jobs:** `scan`
- **Scripts:** `.github/scripts/safe_push.sh`, `STOCKS/competition/fast_forward_picks.js`, `run_fast_competition.py`
- **JSON I/O:** `STOCKS/competition/fast_forward_picks.json`, `dashboard_payload.json`

### `fast-variants-master.yml`

- **Name:** Fast Trading Variants  Master Scheduler
- **Triggers:** schedule:
- **Cron:** `0 */4 * * *`
- **Jobs:** `fast-stocks`, `mercury2-fast`, `commit-results`
- **Scripts:** `.github/scripts/safe_push.sh`, `STOCKS/competition/fast_forward_picks.js`, `mercury2/mercury2_fast_picks.js`, `mercury2_fast.py`, `run_fast_competition.py`
- **JSON I/O:** `STOCKS/competition/fast_forward_picks.json`, `dashboard_payload.json`, `mercury2/mercury2_fast_picks.json`

### `fc-crypto-pro.yml`

- **Name:** FC-CRYPTO PRO Top Actionable Picks
- **Triggers:** workflow_dispatch:
- **Cron:** `0 */2 * * *`
- **Jobs:** `fc-crypto-pro`
- **Scripts:** `.github/scripts/safe_push.sh`, `battleground/data/active_picks.js`, `battleground/data/closed_picks.js`, `battleground/export_top_picks.py`, `data/fc_crypto_pro_picks.js`, `fc_crypto_pro.py`
- **JSON I/O:** `battleground/data/active_picks.json`, `battleground/data/closed_picks.json`, `data/fc_crypto_pro_picks.json`

### `feature-stability-check.yml`

- **Name:** Feature Stability Check (Weekly)
- **Triggers:** schedule:
- **Cron:** `0 6 * * 1`
- **Jobs:** `feature-stability`
- **Scripts:** `.github/scripts/safe_push.sh`, `alpha_engine/data/feature_correlation.js`, `alpha_engine/data/feature_dead_cleanup.js`, `alpha_engine/data/feature_dead_history.js`, `alpha_engine/data/feature_discovery.js`, `alpha_engine/data/feature_importance_history.js`, `alpha_engine/data/feature_stability_report.js`, `alpha_engine/feature_stability_monitor.py`
- **JSON I/O:** `alpha_engine/data/feature_correlation.json`, `alpha_engine/data/feature_dead_cleanup.json`, `alpha_engine/data/feature_dead_history.json`, `alpha_engine/data/feature_discovery.json`, `alpha_engine/data/feature_importance_history.json`, `alpha_engine/data/feature_stability_report.json`

### `feed-health.yml`

- **Name:** Feed Health Check
- **Triggers:** schedule:
- **Cron:** `25 */1 * * *`
- **Jobs:** `health`
- **Scripts:** `audit_trail/data/dashboard_payload.js`, `audit_trail/feed_health_check.py`
- **JSON I/O:** `audit_trail/data/dashboard_payload.json`

### `fetch-movies-v3.yml`

- **Name:** Deploy & Refresh MOVIESHOWS3
- **Triggers:** schedule:
- **Cron:** `0 7 * * *`
- **Jobs:** `deploy-and-fetch`
- **Scripts:** `tools/deploy_movieshows3.py`

### `fetch-movies.yml`

- **Name:** Fetch New Movies & TV Shows
- **Triggers:** schedule:
- **Cron:** `0 6 * * *`
- **Jobs:** `deploy-and-fetch`
- **Scripts:** `tools/deploy_movieshows2.py`

### `fix-battleground.yml`

- **Name:** Fix Battleground Deployment
- **Triggers:** workflow_dispatch:
- **Jobs:** `deploy-battleground`

### `fix-ghost-cards.yml`

- **Name:** Fix Ghost Cards & Thumbnails  All Sites
- **Triggers:** workflow_dispatch:
- **Jobs:** `patch`
- **Scripts:** `tools/patch_thumbnails.py`

### `forex-agent.yml`

- **Name:** Forex Agent
- **Triggers:** schedule:
- **Cron:** `0 0,8,13,17 * * 1-5`
- **Jobs:** `forex-scan`
- **Scripts:** `.github/scripts/safe_push.sh`, `non_crypto_agent/data/forex_picks.js`, `non_crypto_quality_gate.py`
- **JSON I/O:** `non_crypto_agent/data/forex_picks.json`

### `forex-smart-picks.yml`

- **Name:** Forex Smart Picks Scanner
- **Triggers:** schedule:
- **Cron:** `0 2,6,10,14,18,22 * * 1-5`
- **Jobs:** `forex-smart-picks`
- **Scripts:** `.github/scripts/safe_push.sh`, `alpha_engine/data/active_picks.js`, `alpha_engine/forex_smart_picks.py`
- **JSON I/O:** `alpha_engine/data/active_picks.json`

### `forward-signal-scanner.yml`

- **Name:** Forward Signal Scanner
- **Triggers:** schedule:
- **Cron:** `0 */2 * * *`
- **Jobs:** `scan`
- **Scripts:** `.github/scripts/safe_push.sh`, `discord_freshpicks_baby.py`, `incubator/backtest_results/forward_signals.js`, `incubator/backtest_team/forward_signal_scanner.py`
- **JSON I/O:** `incubator/backtest_results/forward_signals.json`

### `forward-test-daily.yml`

- **Name:** Forward Test Daily
- **Triggers:** schedule:
- **Cron:** `30 14 * * 1-5`, `0 16,20,0,4 * * *`
- **Jobs:** `forward-test`
- **Scripts:** `.github/notify-failure.sh`, `.github/scripts/safe_push.sh`, `STOCKS/competition/forward_picks.js`, `STOCKS/competition/forward_test.py`
- **JSON I/O:** `STOCKS/competition/forward_picks.json`, `forward_picks.json`

### `forward-test-new-strategies.yml`

- **Name:** Forward-Test New Strategies Tracker
- **Triggers:** schedule:
- **Cron:** `0 */6 * * *`
- **Jobs:** `forward-test`
- **Scripts:** `.github/scripts/safe_push.sh`, `alpha_engine/data/new_strategy_forward_results.js`, `alpha_engine/forward_test_new_strategies.py`
- **JSON I/O:** `alpha_engine/data/new_strategy_forward_results.json`

### `forward-tracking-v2.yml`

- **Name:** Forward Trade Tracking v2
- **Triggers:** schedule:
- **Cron:** `0 * * * *`
- **Jobs:** `track-signals`
- **Scripts:** `.github/scripts/safe_push.sh`, `KIMI_RISEOFTHECLAW/data/active_picks.js`, `alpha_engine/data/active_picks.js`, `forward_trade_executor_v2.py`, `genome/active_picks.js`, `genome/data/battleground_mutation_picks.js`, `genome/data/confluence_mutation_picks.js`, `genome/data/dna_winner_picks.js`, `genome/data/macd_mutation_picks.js`, `genome/data/momentum_scalp_picks.js`, `genome/data/mutation_lab_picks.js`, `genome/data/pumpwatch_mutation_picks.js`, `genome/data/pumpwatch_v2_picks.js`, `genome/data/rapid_fire_mutation_picks.js`, `genome/data/signal_engine_mutation_picks.js`, `predictions/data/active_predictions.js`
- **JSON I/O:** `KIMI_RISEOFTHECLAW/data/active_picks.json`, `alpha_engine/data/active_picks.json`, `forward_stats.json`, `genome/active_picks.json`, `genome/data/battleground_mutation_picks.json`, `genome/data/confluence_mutation_picks.json`, `genome/data/dna_winner_picks.json`, `genome/data/macd_mutation_picks.json`, `genome/data/momentum_scalp_picks.json`, `genome/data/mutation_lab_picks.json`, `genome/data/pumpwatch_mutation_picks.json`, `genome/data/pumpwatch_v2_picks.json`, `genome/data/rapid_fire_mutation_picks.json`, `genome/data/signal_engine_mutation_picks.json`, `predictions/data/active_predictions.json`

### `forward_test.yml`

- **Name:** Forward Test - Strategy Validation
- **Triggers:** schedule:
- **Cron:** `0 0,4,8,12,16,20 * * *`
- **Jobs:** `forward-test`
- **Scripts:** `.github/scripts/safe_push.sh`, `alpha_engine/data/survivor_backtest_results.js`, `results/forward_test_latest.js`
- **JSON I/O:** `alpha_engine/data/survivor_backtest_results.json`, `results/forward_test_latest.json`

### `futures-agent.yml`

- **Name:** Futures Agent
- **Triggers:** schedule:
- **Cron:** `0 14 * * 1-5`, `0 22 * * 1-5`, `0 22 * * 0`
- **Jobs:** `futures-scan`
- **Scripts:** `.github/scripts/safe_push.sh`, `non_crypto_agent/data/futures_picks.js`
- **JSON I/O:** `non_crypto_agent/data/futures_picks.json`

### `gainer-predictor.yml`

- **Name:** Gainer Predictor Scanner
- **Triggers:** schedule:
- **Cron:** `*/30 * * * *`
- **Jobs:** `scan`
- **Scripts:** `.github/scripts/safe_push.sh`, `incubator/agents/claude_code_01/gainer_data_pipeline.py`, `incubator/agents/claude_code_01/gainer_scoring_service.py`

### `genome-daily-pipeline.yml`

- **Name:** DNA Genome Daily Pipeline
- **Triggers:** push:
- **Cron:** `0 */3 * * *`
- **Jobs:** `data-collection`, `strategy-permutation`, `quality-scoring`, `deploy-to-ftp`
- **Scripts:** `.github/scripts/assert_no_conflict_markers.sh`, `.github/scripts/safe_push.sh`, `dna_backtester.py`, `dna_engine.py`, `genome/active_picks.js`, `genome/data/battleground_mutation_picks.js`, `genome/data/confluence_mutation_picks.js`, `genome/data/dna_winner_picks.js`, `genome/data/macd_mutation_picks.js`, `genome/data/pumpwatch_mutation_picks.js`, `genome/data/pumpwatch_v2_picks.js`, `genome/data/rapid_fire_mutation_picks.js`, `genome/data/signal_engine_mutation_picks.js`, `genome/dna_confluence_mutations.py`, `genome/dna_macd_mutations.py`, `genome/dna_pumpwatch_mutations.py`, `genome/dna_pumpwatch_v2_mutations.py`, `genome/dna_rapid_fire_mutations.py`, `genome/dna_signal_engine_mutations.py`, `genome/dna_winner_mutations.py`, `ml_battleground/battleground_mutations.py`, `picks_generator.py`, `quality_engine.py`, `strategy_registry.py`
- **JSON I/O:** `active_picks.json`, `genome/active_picks.json`, `genome/data/battleground_mutation_picks.json`, `genome/data/confluence_mutation_picks.json`, `genome/data/dna_winner_picks.json`, `genome/data/macd_mutation_picks.json`, `genome/data/pumpwatch_mutation_picks.json`, `genome/data/pumpwatch_v2_picks.json`, `genome/data/rapid_fire_mutation_picks.json`, `genome/data/signal_engine_mutation_picks.json`

### `genome-evolution.yml`

- **Name:** Strategy Genome Evolution
- **Triggers:** schedule:
- **Cron:** `0 6 * * 0`
- **Jobs:** `evolve`
- **Scripts:** `.github/notify-failure.sh`, `.github/scripts/safe_push.sh`, `quant_lab/strategy_genome.py`

### `gha-stale-workflows-audit.yml`

- **Name:** GHA stale workflows audit
- **Triggers:** schedule:
- **Cron:** `30 5 * * *`
- **Jobs:** `scan`
- **Scripts:** `tools/check_workflow_sparse_safe_push.py`, `tools/find_stale_github_workflows.py`

### `goldmine-tracker.yml`

- **Name:** Goldmine Tracker - Archive & Maintain
- **Triggers:** schedule:
- **Cron:** `0 7 * * *`, `0 18 * * *`, `0 0 * * *`
- **Jobs:** `track-and-maintain`

### `growth-stock-screener-daily.yml`

- **Name:** Growth Stock Screener Daily
- **Triggers:** —
- **Cron:** `0 14 * * 1-5`
- **Jobs:** `run-growth-screener`
- **Scripts:** `alpha_engine/growth_stock_screener.py`, `audit_dashboard/data/growth_stock_picks.js`
- **JSON I/O:** `audit_dashboard/data/growth_stock_picks.json`

### `gsd-edge-test-discord.yml`

- **Name:** GSD Edge Engine - Test Discord Notification
- **Triggers:** workflow_dispatch:
- **Jobs:** `test-notification`

### `hc-parity.yml`

- **Name:** HC Evaluator Parity Test
- **Triggers:** schedule:
- **Cron:** `0 15 * * 1`
- **Jobs:** `hc-parity`
- **Scripts:** `audit_dashboard/hc_filter.js`, `audit_trail/feed_membership.py`, `hc_gates_python.py`, `tools/data/hc_parity_baseline.js`, `tools/hc_gates_python.py`, `tools/hc_parity_test.js`, `tools/hc_parity_test.py`
- **JSON I/O:** `tools/data/hc_parity_baseline.json`

### `hierarchical-bayes.yml`

- **Name:** Hierarchical Bayesian Edge Update
- **Triggers:** schedule:
- **Cron:** `30 2 * * *`
- **Jobs:** `run-bayes`

### `hindsight-learner.yml`

- **Name:** Hindsight Learner  Hourly Winner Analysis
- **Triggers:** schedule:
- **Cron:** `7 * * * *`
- **Jobs:** `analyze`
- **Scripts:** `.github/scripts/safe_push.sh`, `alpha_engine/data/hindsight_log.js`, `alpha_engine/data/winner_analysis.js`, `alpha_engine/data/winner_history.js`, `alpha_engine/data/winner_patterns.js`
- **JSON I/O:** `alpha_engine/data/hindsight_log.json`, `alpha_engine/data/winner_analysis.json`, `alpha_engine/data/winner_history.json`, `alpha_engine/data/winner_patterns.json`

### `hoffman-tracker.yml`

- **Name:** Hoffman IRB Strategy Tracker
- **Triggers:** schedule:
- **Cron:** `0 */6 * * *`
- **Jobs:** `track`

### `hourly-master-picks.yml`

- **Name:** Hourly Master Picks to Discord
- **Triggers:** schedule:
- **Cron:** `5 * * * *`
- **Jobs:** `send-master-picks`
- **Scripts:** `.github/scripts/safe_push.sh`, `scripts/send_top_picks_now.py`, `signal_aggregator/data/consensus_output.js`, `signal_aggregator/data/last_sent_cache.js`, `signal_aggregator/data/master_picks_history.js`, `signal_aggregator/data/master_picks_tracker.js`
- **JSON I/O:** `signal_aggregator/data/consensus_output.json`, `signal_aggregator/data/last_sent_cache.json`, `signal_aggregator/data/master_picks_history.json`, `signal_aggregator/data/master_picks_tracker.json`

### `hub-sync.yml`

- **Name:** Hub Data Sync
- **Triggers:** schedule:
- **Cron:** `22 * * * *`
- **Jobs:** `sync`
- **Scripts:** `.github/scripts/safe_push.sh`, `hub/js/consensus_engine.js`, `hub/js/quality_scorer.js`, `signal_recorder/export_hub_combos.py`

### `hyro-bridge-regen.yml`

- **Name:** Hyro Quan Bridge Regen
- **Triggers:** —
- **Cron:** `40 5 * * *`
- **Jobs:** `regen`
- **Scripts:** `audit_dashboard/data/hyro_live_strategies.js`, `audit_dashboard/data/hyro_quan_bridge.js`, `tools/hyro_quan_bridge.py`
- **JSON I/O:** `audit_dashboard/data/hyro_live_strategies.json`, `audit_dashboard/data/hyro_quan_bridge.json`, `hyro_live_strategies.json`, `hyro_quan_bridge.json`

### `hyro-daily.yml`

- **Name:** Hyro daily (filter + backtest)
- **Triggers:** —
- **Cron:** `35 13 * * *`
- **Jobs:** `hyro`
- **Scripts:** `audit_dashboard/data/hyro_backtest_results.js`, `audit_dashboard/data/hyrotrader_picks.js`, `tools/hyro_backtest.py`, `tools/hyro_filter_from_dashboard.py`
- **JSON I/O:** `audit_dashboard/data/hyro_backtest_results.json`, `audit_dashboard/data/hyrotrader_picks.json`, `hyrotrader_picks.json`

### `incubator-pipeline.yml`

- **Name:** Incubator Pipeline  Strategy Graduation
- **Triggers:** schedule:
- **Cron:** `0 6 * * *`
- **Jobs:** `incubator`
- **Scripts:** `.github/scripts/safe_push.sh`, `alpha_engine/data/incubator_paper_ready.js`, `alpha_engine/data/incubator_report.js`
- **JSON I/O:** `alpha_engine/data/incubator_paper_ready.json`, `alpha_engine/data/incubator_report.json`, `incubator_paper_ready.json`, `incubator_report.json`

### `incubator-strategies.yml`

- **Name:** ALPHA ENGINE - Incubator Strategies
- **Triggers:** schedule:
- **Cron:** `15 */2 * * *`
- **Jobs:** `incubator-scan`
- **Scripts:** `.github/scripts/safe_push.sh`, `alpha_engine/data/incubator_picks.js`, `alpha_engine/incubator_strategies.py`
- **JSON I/O:** `alpha_engine/data/incubator_picks.json`

### `index-creator-content.yml`

- **Name:** Index All Creator Content
- **Triggers:** schedule:
- **Cron:** `0 3 * * *`
- **Jobs:** `index-content`
- **Scripts:** `/tmp/index_result_1.js`, `/tmp/index_result_2.js`, `/tmp/index_result_3.js`, `/tmp/index_result_4.js`
- **JSON I/O:** `/tmp/index_result_1.json`, `/tmp/index_result_2.json`, `/tmp/index_result_3.json`, `/tmp/index_result_4.json`

### `kimi-feb172026-live.yml`

- **Name:** KIMI_FEB172026 - Live Trading System
- **Triggers:** schedule, workflow_dispatch
- **Cron:** `0 */2 * * *`, `0 */4 * * *`, `0 0 * * *`
- **Jobs:** `kimi-trading`
- **Scripts:** `.github/scripts/safe_push.sh`, `KIMI_FEB172026/data/active_picks.js`, `KIMI_FEB172026/data/forward_test_status.js`, `KIMI_FEB172026/data/freshpicks_sent.js`, `KIMI_FEB172026/data/signal_tracking.js`, `check_unified_status.py`, `data/freshpicks_gate_state.js`, `data/latest_signals.js`, `data/signal_tracking.js`, `data/system_status.js`, `data/unified_status.js`, `data/validation_results.js`, `deploy_underdog_strategies.py`, `unified_forward_test.py`
- **JSON I/O:** `KIMI_FEB172026/data/active_picks.json`, `KIMI_FEB172026/data/forward_test_status.json`, `KIMI_FEB172026/data/freshpicks_sent.json`, `KIMI_FEB172026/data/signal_tracking.json`, `active_picks.json`, `data/freshpicks_gate_state.json`, `data/latest_signals.json`, `data/signal_tracking.json`, `data/system_status.json`, `data/unified_status.json`, `data/validation_results.json`

### `kimi-fetch-movies.yml`

- **Name:** Kimi Fetch Movies/TV
- **Triggers:** workflow_dispatch:
- **Cron:** `0 6 * * *`
- **Jobs:** `kimi_fetch_movies`
- **Scripts:** `.github/scripts/safe_push.sh`, `github.sh`, `movieshows2/log/pull_log.js`
- **JSON I/O:** `movieshows2/log/pull_log.json`

### `kimi-goldmine-collector.yml`

- **Name:** KIMI Goldmine Data Collection
- **Triggers:** schedule:
- **Cron:** `0 13,15,17,19 * * 1-5`, `0 */2 * * *`
- **Jobs:** `collect-and-update`
- **Scripts:** `.github/scripts/safe_push.sh`, `data/goldmine/meme_winners.js`, `data/goldmine/sports_picks.js`, `data/goldmine/stats.js`, `data/goldmine/stock_picks.js`, `data/goldmine/track_closed_trades.py`, `data/goldmine/unified_picks.js`
- **JSON I/O:** `data/goldmine/meme_winners.json`, `data/goldmine/sports_picks.json`, `data/goldmine/stats.json`, `data/goldmine/stock_picks.json`, `data/goldmine/unified_picks.json`

### `live-monitor-refresh.yml`

- **Name:** Live Trading Monitor  Auto Refresh
- **Triggers:** schedule:
- **Cron:** `42 * * * *`, `0 2 * * 0`
- **Jobs:** `live-refresh`, `hour-learning`

### `live-position-monitor.yml`

- **Name:** BTCC Live Position Monitor (REAL MONEY)
- **Triggers:** workflow_dispatch
- **Cron:** `0,30 * * * *`
- **Jobs:** `monitor`
- **Scripts:** `.github/scripts/safe_push.sh`, `live_monitor/data/position_state.js`, `live_monitor/position_monitor.py`
- **JSON I/O:** `live_monitor/data/position_state.json`

### `live_spike_trading.yml`

- **Name:** LIVE SPIKE TRADING - Autonomous Crypto Monitor
- **Triggers:** schedule:
- **Cron:** `29 */2 * * *`
- **Jobs:** `spike-trading`
- **Scripts:** `.github/scripts/safe_push.sh`, `data/spike_trader_active.js`, `live_spike_trader.py`
- **JSON I/O:** `data/spike_trader_active.json`, `spike_trading_results.json`

### `live_tracker.yml`

- **Name:** Live Picks Tracker
- **Triggers:** workflow_dispatch:
- **Cron:** `25 * * * *`
- **Jobs:** `update-dashboard`
- **Scripts:** `.github/scripts/safe_push.sh`, `dashboard/generate_dashboard.py`, `live_picks_tracker.py`

### `live_trading.yml`

- **Name:** Live Trading Bot
- **Triggers:** schedule:
- **Cron:** `0 */4 * * *`
- **Jobs:** `trade`
- **Scripts:** `.github/scripts/safe_push.sh`, `live_trading_bot.py`
- **JSON I/O:** `trading_results.json`

### `live_trading_canada.yml`

- **Name:** Live Trading Bot - Canada Edition
- **Triggers:** schedule:
- **Cron:** `0 */4 * * *`
- **Jobs:** `trade`
- **Scripts:** `.github/scripts/safe_push.sh`, `live_trading_bot_canada.py`
- **JSON I/O:** `performance_history.json`, `trading_results.json`

### `live_trading_canada_free.yml`

- **Name:** Live Trading Bot - Canada Edition (FREE Data)
- **Triggers:** schedule:
- **Cron:** `0 */4 * * *`
- **Jobs:** `trade`
- **Scripts:** `.github/scripts/safe_push.sh`, `live_trading_bot_canada.py`
- **JSON I/O:** `performance_history.json`, `trading_results.json`

### `low-score-tracker.yml`

- **Name:** Low-Score Winner Tracker
- **Triggers:** schedule:
- **Cron:** `5 * * * *`
- **Jobs:** `track`
- **Scripts:** `.github/scripts/safe_commit_push.sh`, `alpha_engine/data/low_score_tracking.js`
- **JSON I/O:** `alpha_engine/data/low_score_tracking.json`

### `luxalgo-signals.yml`

- **Name:** LuxAlgo Signal Generator
- **Triggers:** schedule:
- **Cron:** `25 * * * *`
- **Jobs:** `generate-signals`
- **Scripts:** `.github/scripts/assert_no_conflict_markers.sh`, `.github/scripts/safe_push.sh`, `battleground/data/luxalgo_active_picks.js`, `battleground/data/luxalgo_closed_picks.js`, `luxalgo_signal_generator.py`
- **JSON I/O:** `battleground/data/luxalgo_active_picks.json`, `battleground/data/luxalgo_closed_picks.json`

### `market_beating.yml`

- **Name:** Market Beating System - Crypto & Forex Priority
- **Triggers:** schedule, push, workflow_dispatch
- **Cron:** `0 */2 * * *`
- **Jobs:** `market-beating`
- **Scripts:** `.github/scripts/safe_push.sh`, `market_beating_bot.py`, `signal_tracker.py`
- **JSON I/O:** `signals_database.json`, `tweak_history.json`, `validation_results.json`

### `master-automation-scheduler.yml`

- **Name:** Master Automation Scheduler
- **Triggers:** schedule:
- **Cron:** `0 * * * *`, `0 */4 * * *`, `0 3 * * *`, `0 0 * * 0`
- **Jobs:** `hourly-tasks`, `four-hourly-tasks`, `daily-tasks`, `weekly-tasks`
- **Scripts:** `.github/scripts/safe_push.sh`, `dna_engine_enhanced.py`, `forward_testing/models/training_report.js`, `reports/ml/metrics.js`, `signal_aggregator/consensus_filtered.js`, `signal_aggregator/consensus_output.js`, `signal_aggregator/data/master_picks_history.js`, `signal_aggregator/data/master_picks_tracker.js`, `signal_aggregator/models/training_report.js`
- **JSON I/O:** `consensus_output.json`, `forward_testing/models/training_report.json`, `reports/ml/metrics.json`, `signal_aggregator/consensus_filtered.json`, `signal_aggregator/consensus_output.json`, `signal_aggregator/data/master_picks_history.json`, `signal_aggregator/data/master_picks_tracker.json`, `signal_aggregator/models/training_report.json`

### `master-picks-health.yml`

- **Name:** Master-Picks Health Score
- **Triggers:** schedule:
- **Cron:** `30 */4 * * *`
- **Jobs:** `send-health-score`
- **Scripts:** `signal_aggregator/send_health_score.py`

### `mega-mutation-tracker.yml`

- **Name:** Mega Mutation Live Tracker
- **Triggers:** schedule:
- **Cron:** `45 * * * *`
- **Jobs:** `track`
- **Scripts:** `.github/scripts/assert_no_conflict_markers.sh`, `.github/scripts/safe_push.sh`, `audit_trail/data/dashboard_payload.js`, `battleground/data/incubator_ledger.js`, `genome/data/active_picks.js`, `genome/data/closed_picks.js`, `genome/data/mega_mutation_picks.js`, `genome/mega_mutation_live_tracker.py`
- **JSON I/O:** `audit_trail/data/dashboard_payload.json`, `battleground/data/incubator_ledger.json`, `dashboard_payload.json`, `genome/data/active_picks.json`, `genome/data/closed_picks.json`, `genome/data/mega_mutation_picks.json`

### `meme-scanner-fixed.yml`

- **Name:** Meme Coin Scanner  Fixed with Monitoring
- **Triggers:** workflow_dispatch
- **Jobs:** `meme-scan`
- **Scripts:** `scripts/meme_sentiment_scraper_v2.py`

### `meme-scanner-v2.yml`

- **Name:** Meme Coin Scanner v2  Fixed & Monitored
- **Triggers:** schedule:
- **Cron:** `*/10 * * * *`, `0 */3 * * *`, `0 * * * *`
- **Jobs:** `meme-scan`
- **Scripts:** `scripts/meme_scanner_monitor.py`

### `meme-scanner.yml`

- **Name:** Meme Coin Scanner Auto Scan & Resolve
- **Triggers:** schedule:
- **Cron:** `0 */2 * * *`, `0 */3 * * *`
- **Jobs:** `meme-scan`
- **Scripts:** `.github/scripts/safe_push.sh`, `data/meme_scanner_active.js`
- **JSON I/O:** `data/meme_scanner_active.json`

### `mercury2-fast-scan.yml`

- **Name:** Mercury2 Fast  High Frequency Crypto Scanner
- **Triggers:** workflow_dispatch
- **Cron:** `0 */4 * * *`
- **Jobs:** `scan`
- **Scripts:** `.github/scripts/safe_push.sh`, `audit_trail/data/dashboard_payload.js`, `mercury2/data/closed_picks.js`, `mercury2/mercury2_fast_picks.js`, `mercury2_fast.py`, `ml_battleground/baseline_metrics.js`, `ml_battleground/retrain_trigger.js`
- **JSON I/O:** `audit_trail/data/dashboard_payload.json`, `dashboard_payload.json`, `mercury2/data/closed_picks.json`, `mercury2/mercury2_fast_picks.json`, `ml_battleground/baseline_metrics.json`, `ml_battleground/retrain_trigger.json`

### `mercury2-retrain.yml`

- **Name:** Mercury 2  Weekly Retrain
- **Triggers:** schedule:
- **Cron:** `0 2 * * 0`
- **Jobs:** `retrain`
- **Scripts:** `.github/scripts/safe_push.sh`, `mercury2/data/training_summary.js`, `ml_battleground/baseline_metrics.js`, `ml_battleground/retrain_trigger.js`
- **JSON I/O:** `mercury2/data/training_summary.json`, `ml_battleground/baseline_metrics.json`, `ml_battleground/retrain_trigger.json`

### `mercury2-scan.yml`

- **Name:** Mercury 2  Signal Scanner
- **Triggers:** schedule, workflow_dispatch
- **Cron:** `35 * * * *`
- **Jobs:** `scan`
- **Scripts:** `.github/notify-failure.sh`, `.github/scripts/safe_push.sh`, `mercury2/audit_push.py`, `ml_battleground/baseline_metrics.js`, `ml_battleground/retrain_trigger.js`
- **JSON I/O:** `ml_battleground/baseline_metrics.json`, `ml_battleground/retrain_trigger.json`

### `meta-strategy.yml`

- **Name:** Meta-Strategy Permutation Engine
- **Triggers:** schedule:
- **Cron:** `20 * * * *`, `0 5,11,17,23 * * *`
- **Jobs:** `meta-strategy`
- **Scripts:** `.github/scripts/assert_no_conflict_markers.sh`, `.github/scripts/safe_push.sh`, `alpha_engine/data/strategy_performance.js`, `battleground/data/combo_metrics.js`, `genome/data/unified_strategy_catalog.js`, `meta_strategy/data/unified_strategy_catalog.js`, `safe_push.sh`
- **JSON I/O:** `alpha_engine/data/strategy_performance.json`, `battleground/data/combo_metrics.json`, `combo_metrics.json`, `genome/data/unified_strategy_catalog.json`, `meta_strategy/data/unified_strategy_catalog.json`, `swarm_weights.json`

### `mirror-site.yml`

- **Name:** Mirror: findtorontoevents.ca  torontoevent.net
- **Triggers:** schedule:
- **Cron:** `0 */6 * * *`
- **Jobs:** `mirror`
- **Scripts:** `.github/scripts/assert_ftp_host.sh`

### `missed-opportunity-scan.yml`

- **Name:** Missed Opportunity Analyzer Hourly Self-Improvement
- **Triggers:** schedule:
- **Cron:** `19 * * * *`
- **Jobs:** `missed-opportunity-scan`
- **Scripts:** `.github/scripts/safe_push.sh`, `alpha_engine/data/hourly_improvement_report.js`, `alpha_engine/data/missed_gainers_log.js`, `alpha_engine/data/wrong_guesses_log.js`, `alpha_engine/missed_opportunity_analyzer.py`
- **JSON I/O:** `alpha_engine/data/hourly_improvement_report.json`, `alpha_engine/data/missed_gainers_log.json`, `alpha_engine/data/wrong_guesses_log.json`

### `ml-battleground-a.yml`

- **Name:** Superpowers - System A (The Filter)
- **Triggers:** workflow_dispatch
- **Cron:** `2 */2 * * *`
- **Jobs:** `scan`
- **Scripts:** `.github/notify-failure.sh`, `.github/scripts/safe_push.sh`, `//download.py`, `ml_battleground/audit_push.py`

### `ml-battleground-abc-pilots.yml`

- **Name:** Superpowers  ABC Forward Test + ML Pilots
- **Triggers:** workflow_dispatch
- **Cron:** `22,52 * * * *`
- **Jobs:** `scan`
- **Scripts:** `.github/scripts/safe_push.sh`

### `ml-battleground-b.yml`

- **Name:** Superpowers - System B (The Regime)
- **Triggers:** workflow_dispatch
- **Cron:** `7,37 * * * *`
- **Jobs:** `scan`
- **Scripts:** `.github/notify-failure.sh`, `.github/scripts/safe_push.sh`, `//download.py`, `ml_battleground/audit_push.py`

### `ml-battleground-bootstrap.yml`

- **Name:** SUPERPOWERS - Bootstrap All 3 ML Systems
- **Triggers:** workflow_dispatch:
- **Jobs:** `bootstrap`, `scan-a`, `scan-b`, `scan-c`
- **Scripts:** `.github/scripts/safe_push.sh`, `//download.py`, `ml_battleground.sh`, `ml_battleground/bootstrap/bootstrap_summary.js`, `safe_push.sh`
- **JSON I/O:** `ml_battleground/bootstrap/bootstrap_summary.json`

### `ml-battleground-c.yml`

- **Name:** Superpowers - System C (The Neural Net)
- **Triggers:** workflow_dispatch
- **Cron:** `12,27,42,57 * * * *`
- **Jobs:** `scan`
- **Scripts:** `.github/notify-failure.sh`, `.github/scripts/safe_push.sh`, `//download.py`, `ml_battleground/audit_push.py`

### `ml-battleground-d.yml`

- **Name:** ML Battleground System D (The Carry Trade)
- **Triggers:** workflow_dispatch
- **Cron:** `40 * * * *`
- **Jobs:** `scan`
- **Scripts:** `.github/notify-failure.sh`, `.github/scripts/safe_push.sh`, `//download.py`, `ml_battleground/audit_push.py`

### `ml-battleground-e.yml`

- **Name:** ML Battleground System E (The Momentum)
- **Triggers:** workflow_dispatch
- **Cron:** `45 * * * *`
- **Jobs:** `scan`
- **Scripts:** `.github/notify-failure.sh`, `.github/scripts/safe_push.sh`, `//download.py`, `ml_battleground/audit_push.py`

### `ml-battleground-ensemble.yml`

- **Name:** ML Battleground Ensemble
- **Triggers:** workflow_dispatch
- **Cron:** `0,30 * * * *`
- **Jobs:** `scan`
- **Scripts:** `.github/notify-failure.sh`, `.github/scripts/safe_push.sh`, `//download.py`, `ml_battleground/audit_push.py`

### `ml-battleground-f.yml`

- **Name:** ML Battleground System F (Claws of Doom)
- **Triggers:** schedule, workflow_dispatch
- **Cron:** `47 * * * *`
- **Jobs:** `sync`
- **Scripts:** `.github/notify-failure.sh`, `.github/scripts/safe_push.sh`, `//raw.githubusercontent.com/eltonaguiar/CLAWSOFDOOM/main/docs/active_picks.js`, `//raw.githubusercontent.com/eltonaguiar/CLAWSOFDOOM/main/docs/closed_picks.js`, `//raw.githubusercontent.com/eltonaguiar/CLAWSOFDOOM/main/docs/picks.js`, `//raw.githubusercontent.com/eltonaguiar/CLAWSOFDOOM/main/docs/picks_history.js`, `audit_push.py`, `ml_battleground/audit_push.py`, `ml_battleground/system_f_clawsofdoom/data/active_picks.js`, `ml_battleground/system_f_clawsofdoom/data/closed_picks.js`, `ml_battleground/system_f_clawsofdoom/data/picks.js`, `ml_battleground/system_f_clawsofdoom/data/picks_history.js`, `ml_battleground/system_f_clawsofdoom/data/scan_summary.js`
- **JSON I/O:** `//raw.githubusercontent.com/eltonaguiar/CLAWSOFDOOM/main/docs/active_picks.json`, `//raw.githubusercontent.com/eltonaguiar/CLAWSOFDOOM/main/docs/closed_picks.json`, `//raw.githubusercontent.com/eltonaguiar/CLAWSOFDOOM/main/docs/picks.json`, `//raw.githubusercontent.com/eltonaguiar/CLAWSOFDOOM/main/docs/picks_history.json`, `active_picks.json`, `closed_picks.json`, `ml_battleground/system_f_clawsofdoom/data/active_picks.json`, `ml_battleground/system_f_clawsofdoom/data/closed_picks.json`, `ml_battleground/system_f_clawsofdoom/data/picks.json`, `ml_battleground/system_f_clawsofdoom/data/picks_history.json`, `ml_battleground/system_f_clawsofdoom/data/scan_summary.json`, `picks.json`, `scan_summary.json`

### `ml-battleground-monitor.yml`

- **Name:** ML Battleground Pick Monitor
- **Triggers:** workflow_dispatch
- **Cron:** `20 * * * *`
- **Jobs:** `monitor`
- **Scripts:** `.github/scripts/safe_push.sh`, `//download.py`

### `ml-battleground-retrain.yml`

- **Name:** ML Battleground Daily Retrain
- **Triggers:** schedule:
- **Cron:** `0 4 * * *`
- **Jobs:** `retrain`
- **Scripts:** `.github/notify-failure.sh`, `.github/scripts/safe_push.sh`, `//download.py`, `ml_battleground/retrain_summary.js`
- **JSON I/O:** `ml_battleground/retrain_summary.json`

### `ml-battleground-test-discord.yml`

- **Name:** SUPERPOWERS - Test Discord Notifications
- **Triggers:** workflow_dispatch:
- **Jobs:** `test`

### `ml-discord-status.yml`

- **Name:** ML Crypto  Discord Hourly Status
- **Triggers:** schedule:
- **Cron:** `0 * * * *`
- **Jobs:** `send-status`

### `ml-feedback-loop.yml`

- **Name:** ML Feedback Loop
- **Triggers:** schedule:
- **Cron:** `0 */6 * * *`
- **Jobs:** `feedback-check`
- **Scripts:** `.github/scripts/safe_push.sh`, `ml_battleground.sh`, `ml_battleground/baseline_metrics.js`, `ml_battleground/retrain_trigger.js`
- **JSON I/O:** `ml_battleground/baseline_metrics.json`, `ml_battleground/retrain_trigger.json`

### `ml-feedback-retrain.yml`

- **Name:** ML Feedback Retrain  Learn from Closed Trades
- **Triggers:** schedule:
- **Cron:** `23 */12 * * *`
- **Jobs:** `feedback-retrain`
- **Scripts:** `.github/scripts/safe_push.sh`, `/closed_picks.js`, `ml_crypto_predictor/enhanced_models/feedback_data/feedback_training_report.js`
- **JSON I/O:** `/closed_picks.json`, `ml_crypto_predictor/enhanced_models/feedback_data/feedback_training_report.json`

### `ml-forward-test.yml`

- **Name:** ML Forward Test 1745 Models
- **Triggers:** schedule:
- **Cron:** `30 */4 * * *`
- **Jobs:** `forward-test`
- **Scripts:** `.github/scripts/safe_push.sh`, `ml_crypto_predictor/enhanced_models/live_picks/active_picks.js`, `ml_crypto_predictor/enhanced_models/live_picks/closed_picks.js`
- **JSON I/O:** `closed_picks.json`, `ml_crypto_predictor/enhanced_models/live_picks/active_picks.json`, `ml_crypto_predictor/enhanced_models/live_picks/closed_picks.json`

### `ml-gatekeeper-ab-bootstrap.yml`

- **Name:** ML Gatekeeper A/B Bootstrap
- **Triggers:** workflow_dispatch:
- **Jobs:** `bootstrap`
- **Scripts:** `ab_analysis.py`, `ml_gatekeeper/gatekeeper.py`

### `ml-gatekeeper-train-ab.yml`

- **Name:** ML Gatekeeper Train A/B (Phase D)
- **Triggers:** workflow_dispatch:
- **Jobs:** `train`

### `ml-health-monitor.yml`

- **Name:** ML System Health Monitor
- **Triggers:** schedule:
- **Cron:** `0 */6 * * *`
- **Jobs:** `health-check`
- **Scripts:** `scripts/ml_system_health.py`

### `ml-model-autotraining.yml`

- **Name:** ML Model Auto-Training
- **Triggers:** schedule:
- **Cron:** `0 */6 * * *`
- **Jobs:** `check-and-train`
- **Scripts:** `.github/scripts/safe_push.sh`, `forward_testing/models/training_report.js`, `reports/ml_training_report.js`, `signal_aggregator/models/training_report.js`
- **JSON I/O:** `forward_testing/models/training_report.json`, `reports/ml_training_report.json`, `signal_aggregator/models/training_report.json`

### `ml-monthly-retrain.yml`

- **Name:** ML Monthly Full Retrain
- **Triggers:** schedule:
- **Cron:** `0 4 1 * *`
- **Jobs:** `full-retrain`
- **Scripts:** `.github/scripts/safe_push.sh`, `//download.py`, `ml_battleground.sh`

### `ml-staleness-watchdog.yml`

- **Name:** ML Model Staleness Watchdog
- **Triggers:** schedule:
- **Cron:** `0 13 * * *`
- **Jobs:** `check-freshness`
- **Scripts:** `/tmp/freshness.js`, `alpha_engine/auto_tuner.py`, `alpha_engine/crypto_ml_tuner.py`, `alpha_engine/ml_ranker.py`, `claude_gainer_ml/trigger_retraining.py`, `mercury2/trainer.py`, `ml_battleground/retrain_on_live.py`, `ml_crypto_predictor/enhanced_models/feedback_trainer.py`, `ml_gatekeeper/gatekeeper.py`, `tools/assert_model_freshness.py`
- **JSON I/O:** `/tmp/freshness.json`

### `ml-strategy-reviver.yml`

- **Name:** ML Strategy Reviver Bridge & Standalone
- **Triggers:** schedule:
- **Cron:** `23 */2 * * *`
- **Jobs:** `revive`
- **Scripts:** `.github/scripts/safe_push.sh`, `alpha_engine/data/active_picks.js`, `alpha_engine/data/ml_reviver_picks.js`, `alpha_engine/ml_strategy_reviver.py`
- **JSON I/O:** `active_picks.json`, `alpha_engine/data/active_picks.json`, `alpha_engine/data/ml_reviver_picks.json`, `ml_reviver_picks.json`

### `ml_hourly_picks.yml`

- **Name:** ML Picks  Hourly Discord Alert
- **Triggers:** schedule:
- **Cron:** `10 */4 * * *`
- **Jobs:** `send-picks`
- **Scripts:** `backtest_results/walk_forward_results.js`, `updates/data/antigravity_ml_live_picks.js`
- **JSON I/O:** `backtest_results/walk_forward_results.json`, `updates/data/antigravity_ml_live_picks.json`

### `momentum-catcher.yml`

- **Name:** MOMENTUM CATCHER - Real-time Pump Detector
- **Triggers:** schedule:
- **Cron:** `*/30 * * * *`
- **Jobs:** `momentum-scan`
- **Scripts:** `.github/notify-failure.sh`, `.github/scripts/safe_push.sh`, `alpha_engine/data/active_picks.js`, `alpha_engine/data/momentum_picks.js`, `data/active_picks.js`, `data/momentum_picks.js`
- **JSON I/O:** `active_picks.json`, `alpha_engine/data/active_picks.json`, `alpha_engine/data/momentum_picks.json`, `data/active_picks.json`, `data/momentum_picks.json`

### `momentum-scanner.yml`

- **Name:** MOMENTUM SCALP SCANNER - Dynamic Universe Expansion
- **Triggers:** schedule:
- **Cron:** `0 */4 * * *`
- **Jobs:** `momentum-scan`
- **Scripts:** `.github/scripts/safe_push.sh`, `audit_dashboard/check_top_picks_outcome.py`, `audit_dashboard/data/claude_top_picks.js`, `genome/data/momentum_scalp_picks.js`, `genome/data/top_gainers_scan.js`, `genome/data/tracked_live_picks.js`, `genome/mutation_lab/generate_tracked_picks.py`, `genome/mutation_lab/momentum_scalp_scanner.py`
- **JSON I/O:** `audit_dashboard/data/claude_top_picks.json`, `genome/data/momentum_scalp_picks.json`, `genome/data/top_gainers_scan.json`, `genome/data/tracked_live_picks.json`

### `momentum-tracker.yml`

- **Name:** MOMENTUM TRACKER - Real-Time Gainer Scanner
- **Triggers:** schedule:
- **Cron:** `37 * * * *`
- **Jobs:** `momentum-scan`
- **Scripts:** `.github/notify-failure.sh`, `.github/scripts/safe_push.sh`, `alpha_engine/data/momentum_tracker_picks.js`, `alpha_engine/data/momentum_tracker_state.js`, `alpha_engine/momentum_tracker.py`
- **JSON I/O:** `alpha_engine/data/momentum_tracker_picks.json`, `alpha_engine/data/momentum_tracker_state.json`

### `monthly-tournament.yml`

- **Name:** Monthly DNA Tournament
- **Triggers:** schedule:
- **Cron:** `0 6 1 * *`
- **Jobs:** `tournament`
- **Scripts:** `.github/scripts/assert_no_conflict_markers.sh`, `.github/scripts/safe_push.sh`, `genome/data/symbol_predictability.js`, `genome/data/tournament_results.js`, `genome/mega_mutation_tournament.py`
- **JSON I/O:** `genome/data/symbol_predictability.json`, `genome/data/tournament_results.json`

### `multi-asset-scanner.yml`

- **Name:** Multi-Asset Copytrader Scanner v2  Forex/Futures/Stocks/Commodities
- **Triggers:** schedule:
- **Cron:** `*/30 * * * *`
- **Jobs:** `multi-asset-scan`
- **Scripts:** `.github/scripts/safe_push.sh`, `copy_trader_intel/cta_strategy_replicator.py`, `copy_trader_intel/multi_asset_bridge.py`, `copy_trader_intel/multi_asset_copytrader_scraper.py`, `copy_trader_intel/multi_asset_scorer.py`, `copy_trader_intel/pick_quality_monitor.py`, `copy_trader_intel/variation_portfolio_builder.py`

### `mutation-analysis-report.yml`

- **Name:** Mutation analysis report
- **Triggers:** —
- **Cron:** `25 6 * * 1`
- **Jobs:** `report`
- **Scripts:** `alpha_engine/data/closed_picks.js`, `github.sh`, `tools/matrix_diff.py`, `tools/mutation_analysis.py`
- **JSON I/O:** `alpha_engine/data/closed_picks.json`

### `mutation-lab.yml`

- **Name:** Mutation Lab  Strategy Evolution Pipeline
- **Triggers:** schedule:
- **Cron:** `0 */3 * * *`
- **Jobs:** `scout`, `mutate-amplify`, `mutate-invert`, `mutate-hybrid`, `promote`
- **Scripts:** `.github/scripts/safe_commit_push.sh`, `genome/data/mutation_lab_picks.js`, `genome/data/mutation_lab_summary.js`
- **JSON I/O:** `genome/data/mutation_lab_picks.json`, `genome/data/mutation_lab_summary.json`, `mutation_targets.json`

### `mutation-lifecycle-runner.yml`

- **Name:** Mutation Lifecycle Runner
- **Triggers:** schedule:
- **Cron:** `30 5 * * *`
- **Jobs:** `lifecycle`
- **Scripts:** `.github/scripts/safe_push.sh`, `alpha_engine/data/dna_mutations.js`, `tools/mutation_lifecycle_runner.py`
- **JSON I/O:** `alpha_engine/data/dna_mutations.json`

### `mysql-trading-sync.yml`

- **Name:** MySQL Trading Picks Sync
- **Triggers:** schedule:
- **Cron:** `30 * * * *`
- **Jobs:** `sync`
- **Scripts:** `alpha_engine/mysql_trading_sync.py`

### `news-video-healthcheck.yml`

- **Name:** \U0001F4FA News Video Health Check
- **Triggers:** schedule:
- **Cron:** `0 15 * * 1,4`
- **Jobs:** `check-streams`
- **Scripts:** `scripts/validate_news_videos.py`

### `non-crypto-ab-test.yml`

- **Name:** Non-Crypto A/B Portfolio Tracker
- **Triggers:** schedule:
- **Cron:** `30 13 * * 1-5`, `30 19 * * 1-5`, `30 1 * * 1-5`, `30 7 * * 1-5`
- **Jobs:** `ab-test`
- **Scripts:** `.github/scripts/safe_push.sh`, `alpha_engine/data/non_crypto_ab_history.js`, `alpha_engine/data/non_crypto_ab_report.js`
- **JSON I/O:** `alpha_engine/data/non_crypto_ab_history.json`, `alpha_engine/data/non_crypto_ab_report.json`

### `now-scanner.yml`

- **Name:** Rapid Fire - NOW Scanner
- **Triggers:** schedule:
- **Cron:** `14,44 * * * *`
- **Jobs:** `scan`
- **Scripts:** `.github/scripts/assert_no_conflict_markers.sh`, `.github/scripts/safe_push.sh`, `NOW.py`, `rapid_fire_data/active_picks.js`, `rapid_fire_data/pick_tracker.py`
- **JSON I/O:** `rapid_fire_data/active_picks.json`

### `obi-snapshot.yml`

- **Name:** OBI Hourly Snapshot
- **Triggers:** schedule:
- **Cron:** `30 * * * *`
- **Jobs:** `snapshot`
- **Scripts:** `.github/scripts/safe_commit_push.sh`

### `opposite-day.yml`

- **Name:** Opposite Day Paper-Trade [DISABLED]
- **Triggers:** workflow_dispatch:
- **Jobs:** `opposite-day`
- **Scripts:** `.github/scripts/safe_push.sh`

### `optimize-score-thresholds.yml`

- **Name:** Optimize Score Thresholds
- **Triggers:** schedule:
- **Cron:** `30 3 * * *`
- **Jobs:** `optimize`
- **Scripts:** `.github/scripts/safe_push.sh`, `analysis/score_calibration.py`, `analysis/walkforward_optimizer.py`, `audit_dashboard/data/dashboard_data.js`, `data/context_rankings.js`, `data/score_thresholds.js`, `data/walkforward_results.js`, `engine/context_ranking.py`, `engine/dynamic_threshold.py`
- **JSON I/O:** `audit_dashboard/data/dashboard_data.json`, `data/context_rankings.json`, `data/score_thresholds.json`, `data/walkforward_results.json`

### `outcome-resolver.yml`

- **Name:** Outcome Resolver  Validate Unresolved Picks
- **Triggers:** schedule:
- **Cron:** `15 */1 * * *`
- **Jobs:** `resolve-outcomes`
- **Scripts:** `.github/scripts/safe_push.sh`, `alpha_engine/data/closed_picks.js`, `alpha_engine/data/outcome_resolver_log.js`, `alpha_engine/outcome_resolver.py`, `claude_gainer_ml/tracker/claude_live_picks.js`, `quan_engine/data/active_signals.js`, `rapid_fire_data/closed_picks.js`, `rapid_fire_data/now_picks.js`
- **JSON I/O:** `alpha_engine/data/closed_picks.json`, `alpha_engine/data/outcome_resolver_log.json`, `claude_gainer_ml/tracker/claude_live_picks.json`, `quan_engine/data/active_signals.json`, `rapid_fire_data/closed_picks.json`, `rapid_fire_data/now_picks.json`

### `overnight-mutations.yml`

- **Name:** Overnight Mutations
- **Triggers:** workflow_dispatch:
- **Cron:** `0 2 * * 6`
- **Jobs:** `mutate`
- **Scripts:** `.github/scripts/safe_push.sh`, `alpha_engine/data/massive_mutation_results.js`, `alpha_engine/run_massive_mutations.py`
- **JSON I/O:** `alpha_engine/data/massive_mutation_results.json`

### `paper-trading.yml`

- **Name:** Paper Trading Portfolio
- **Triggers:** workflow_dispatch
- **Cron:** `0 * * * *`
- **Jobs:** `run-scanner`
- **Scripts:** `.github/scripts/safe_push.sh`, `paper_trading/data/active_picks.js`, `paper_trading/sandbox_reporter.py`, `paper_trading/send_hourly_top_picks.py`, `paper_trading/store_backtest_to_mysql.py`
- **JSON I/O:** `paper_trading/data/active_picks.json`

### `parquet-ingest.yml`

- **Name:** Parquet Data Ingestion
- **Triggers:** schedule:
- **Cron:** `0 */4 * * *`
- **Jobs:** `ingest`
- **Scripts:** `.github/scripts/safe_push.sh`

### `penny-skyrocket-runner.yml`

- **Name:** Penny Skyrocket Detector
- **Triggers:** schedule:
- **Cron:** `48 14 * * 1-5`
- **Jobs:** `scan`
- **Scripts:** `.github/scripts/safe_push.sh`, `alpha_engine/data/skyrocket_picks.js`, `alpha_engine/strategies/skyrocket_detector.py`, `skyrocket_detector/detector.py`
- **JSON I/O:** `alpha_engine/data/skyrocket_picks.json`

### `penny-stock-picks.yml`

- **Name:** Penny Stock Daily Picks
- **Triggers:** schedule:
- **Cron:** `0 12 * * 1-5`
- **Jobs:** `penny-picks`, `track-picks`
- **Scripts:** `.github/scripts/safe_push.sh`, `findstocks/portfolio2/data/penny_picks_latest.js`, `penny_stock_picks.py`
- **JSON I/O:** `findstocks/portfolio2/data/penny_picks_latest.json`, `r.json`

### `pick-monitor-30min.yml`

- **Name:** Pick Monitor & Price Validator (30min)
- **Triggers:** schedule:
- **Cron:** `0 */2 * * *`
- **Jobs:** `monitor-and-validate`
- **Scripts:** `.github/scripts/safe_push.sh`, `alpha_engine/data/active_picks.js`, `alpha_engine/data/pick_monitor_report.js`, `alpha_engine/data/price_validation_log.js`, `alpha_engine/pick_monitor.py`, `alpha_engine/price_validator.py`
- **JSON I/O:** `alpha_engine/data/active_picks.json`, `alpha_engine/data/pick_monitor_report.json`, `alpha_engine/data/price_validation_log.json`

### `picks_dispatch.yml`

- **Name:** Crypto Picks Dispatch
- **Triggers:** schedule:
- **Cron:** `0 */4 * * *`
- **Jobs:** `dispatch`
- **Scripts:** `scripts/send_top_picks_now.py`

### `pine-generator.yml`

- **Name:** Pine Script Generator
- **Triggers:** workflow_run:
- **Jobs:** `generate-pine`
- **Scripts:** `.github/scripts/safe_push.sh`, `pine_generator/generate_pine.py`, `pine_generator/output/version.js`
- **JSON I/O:** `pine_generator/output/version.json`

### `polymarket-signals.yml`

- **Name:** Polymarket Prediction Market Signals (Multi-Asset)
- **Triggers:** schedule:
- **Cron:** `13,43 * * * *`
- **Jobs:** `polymarket-scan`
- **Scripts:** `.github/scripts/safe_push.sh`, `alpha_engine/data/kalshi_signals.js`, `alpha_engine/data/polymarket_signals.js`, `alpha_engine/data/prediction_market_picks.js`, `alpha_engine/data/prediction_market_whales.js`, `alpha_engine/kalshi_signals.py`, `alpha_engine/polymarket_signals.py`, `alpha_engine/prediction_market_consensus.py`, `alpha_engine/prediction_market_whales.py`, `copy_trader_intel/data/polymarket_picks.js`, `copy_trader_intel/data/polymarket_trader_profiles.js`, `copy_trader_intel/polymarket_scraper.py`
- **JSON I/O:** `alpha_engine/data/kalshi_signals.json`, `alpha_engine/data/polymarket_signals.json`, `alpha_engine/data/prediction_market_picks.json`, `alpha_engine/data/prediction_market_whales.json`, `copy_trader_intel/data/polymarket_picks.json`, `copy_trader_intel/data/polymarket_trader_profiles.json`

### `portfolio-trackers.yml`

- **Name:** Portfolio Trackers (Real Money + Theory)
- **Triggers:** schedule:
- **Cron:** `15 * * * *`
- **Jobs:** `track`
- **Scripts:** `.github/scripts/safe_commit_push.sh`, `alpha_engine/data/real_money_history.js`, `alpha_engine/data/real_money_portfolio.js`, `alpha_engine/data/theory_portfolios.js`, `alpha_engine/data/theory_portfolios_history.js`
- **JSON I/O:** `alpha_engine/data/real_money_history.json`, `alpha_engine/data/real_money_portfolio.json`, `alpha_engine/data/theory_portfolios.json`, `alpha_engine/data/theory_portfolios_history.json`

### `pre-spike-scan.yml`

- **Name:** Pre-Spike Early Warning
- **Triggers:** schedule:
- **Cron:** `0 12,13,14 * * 1-5`
- **Jobs:** `scan`
- **Scripts:** `.github/scripts/safe_push.sh`, `STOCKS/competition/forward_picks.js`, `STOCKS/scanners/data/pre_spike_picks.js`, `pre_spike_detector.py`
- **JSON I/O:** `STOCKS/competition/forward_picks.json`, `STOCKS/scanners/data/pre_spike_picks.json`

### `prediction-market-agents.yml`

- **Name:** Prediction Market Agents
- **Triggers:** schedule:
- **Cron:** `15 */2 * * *`
- **Jobs:** `prediction-market-scan`
- **Scripts:** `.github/scripts/safe_push.sh`, `alpha_engine/data/active_picks.js`, `copy_trader_intel/data/polymarket_picks.js`, `copy_trader_intel/data/polymarket_trader_profiles.js`
- **JSON I/O:** `alpha_engine/data/active_picks.json`, `copy_trader_intel/data/polymarket_picks.json`, `copy_trader_intel/data/polymarket_trader_profiles.json`

### `prediction-quality-tracker.yml`

- **Name:** Prediction Quality Tracker
- **Triggers:** schedule:
- **Cron:** `47 * * * *`
- **Jobs:** `track-quality`
- **Scripts:** `.github/scripts/safe_push.sh`, `alpha_engine/data/prediction_quality_history.js`, `alpha_engine/prediction_quality_tracker.py`, `prediction_quality_tracker.py`
- **JSON I/O:** `alpha_engine/data/prediction_quality_history.json`

### `proven-strategies-scanner.yml`

- **Name:** Proven Strategies Scanner
- **Triggers:** schedule:
- **Cron:** `0 */2 * * *`
- **Jobs:** `scan`
- **Scripts:** `../alpha_engine/data/active_picks.js`, `.github/scripts/safe_push.sh`, `alpha_engine/data/active_picks.js`, `alpha_engine/data/beaten_majors_picks.js`, `alpha_engine/data/rel_strength_picks.js`, `alpha_engine/data/rsi_cap_picks.js`, `data/active_picks.js`, `data/proven_strategy_picks.js`, `proven_strategies.py`, `proven_strategies/data/proven_strategy_picks.js`
- **JSON I/O:** `../alpha_engine/data/active_picks.json`, `active_picks.json`, `alpha_engine/data/active_picks.json`, `alpha_engine/data/beaten_majors_picks.json`, `alpha_engine/data/rel_strength_picks.json`, `alpha_engine/data/rsi_cap_picks.json`, `data/active_picks.json`, `data/proven_strategy_picks.json`, `proven_strategies/data/proven_strategy_picks.json`, `proven_strategy_picks.json`

### `prune-strategy-performance.yml`

- **Name:** Prune strategy_performance.json (30d)
- **Triggers:** schedule:
- **Cron:** `0 3 * * *`
- **Jobs:** `prune`
- **Scripts:** `.github/scripts/safe_push.sh`, `alpha_engine/data/strategy_performance.js`, `tools/prune_strategy_performance.py`
- **JSON I/O:** `alpha_engine/data/strategy_performance.json`, `strategy_performance.json`

### `quan-engine-live.yml`

- **Name:** QUAN ENGINE - Live Autonomous Scanner
- **Triggers:** schedule:
- **Cron:** `*/30 * * * *`
- **Jobs:** `quan-engine`
- **Scripts:** `.github/notify-failure.sh`, `.github/scripts/assert_no_conflict_markers.sh`, `.github/scripts/safe_push.sh`, `alpha_engine/outcome_resolver.py`, `quan_engine/audit_push.py`, `quan_engine/data/active_signals.js`, `quan_engine/data/market_analysis.js`, `safe_push.sh`
- **JSON I/O:** `quan_engine/data/active_signals.json`, `quan_engine/data/market_analysis.json`

### `quant-auditor-deep-nightly.yml`

- **Name:** Quant Auditor (deep nightly)
- **Triggers:** —
- **Cron:** `15 6 * * *`
- **Jobs:** `audit`
- **Scripts:** `audit_dashboard/data/dashboard_data.js`, `tmp/audit/result.js`, `tools/audit/schema_review_v1_2.js`
- **JSON I/O:** `audit_dashboard/data/dashboard_data.json`, `tmp/audit/result.json`, `tools/audit/schema_review_v1_2.json`

### `quant-auditor-fast-pr.yml`

- **Name:** Quant Auditor (fast PR check)
- **Triggers:** —
- **Jobs:** `audit`
- **Scripts:** `alpha_engine/config.py`, `alpha_engine/forward_validator.py`, `alpha_engine/outcome_resolver.py`, `alpha_engine/regime_position_sizer.py`, `alpha_engine/score_booster.py`, `alpha_engine/smart_picks_engine.py`, `alpha_engine/walkforward_validator.py`, `audit_dashboard/data/dashboard_data.js`, `audit_trail/check_asset_quality_gate.py`, `audit_trail/dashboard_generator.py`, `audit_trail/quality_gates.py`, `audit_trail/quality_monitor.py`, `audit_trail/transaction_cost_model.py`, `audit_trail/universal_pick_resolver.py`, `tmp/audit/result.js`, `tools/audit/schema_review_v1_2.js`
- **JSON I/O:** `audit_dashboard/data/dashboard_data.json`, `tmp/audit/result.json`, `tools/audit/schema_review_v1_2.json`

### `quantum_fusion.yml`

- **Name:** QuantumFusion Crypto Engine
- **Triggers:** schedule:
- **Cron:** `0 * * * *`
- **Jobs:** `quantum-fusion`
- **Scripts:** `.github/scripts/safe_push.sh`, `discord_ml_status.py`, `quantum_fusion_crypto_engine.py`
- **JSON I/O:** `quantum_fusion_report.json`

### `quick-guess-ml.yml`

- **Name:** Quick Guess ML Agent
- **Triggers:** schedule:
- **Cron:** `9 * * * *`
- **Jobs:** `quick-guess`
- **Scripts:** `.github/scripts/safe_push.sh`, `safe_push.sh`

### `rapid-validation-CLAUDECODE_Feb152026.yml`

- **Name:** Rapid Validation Engine
- **Triggers:** schedule:
- **Cron:** `15 */4 * * *`
- **Jobs:** `rapid-validation`

### `real_2hour_challenge.yml`

- **Name:** REAL 2-HOUR CHALLENGE - Live Market Data
- **Triggers:** workflow_dispatch
- **Jobs:** `real-challenge`
- **Scripts:** `.github/scripts/safe_push.sh`, `real_2hour_challenge.py`
- **JSON I/O:** `REAL_CHALLENGE_RESULTS.json`

### `recommended-portfolio.yml`

- **Name:** Recommended Portfolio Generator
- **Triggers:** schedule:
- **Cron:** `28 * * * *`
- **Jobs:** `generate-portfolio`
- **Scripts:** `.github/scripts/safe_push.sh`, `alpha_engine/data/recommended_portfolio.js`, `alpha_engine/generate_recommended_portfolio.py`
- **JSON I/O:** `alpha_engine/data/recommended_portfolio.json`

### `refresh-creator-updates.yml`

- **Name:** Refresh Creator Updates
- **Triggers:** schedule:
- **Cron:** `0 2 * * *`
- **Jobs:** `refresh-updates`
- **Scripts:** `/tmp/refresh_result.js`, `/tmp/refresh_result_meta.js`
- **JSON I/O:** `/tmp/refresh_result.json`, `/tmp/refresh_result_meta.json`

### `refresh-stocks-portfolio.yml`

- **Name:** Refresh All Portfolio Data
- **Triggers:** schedule:
- **Cron:** `30 23 * * 1-5`, `0 0 * * 0`
- **Jobs:** `refresh-stocks`

### `refresh-top-movies.yml`

- **Name:** Refresh Top Movies Data
- **Triggers:** schedule:
- **Cron:** `0 */6 * * *`
- **Jobs:** `refresh`
- **Scripts:** `.github/scripts/safe_push.sh`, `TORONTOEVENTS_ANTIGRAVITY/shared/top-movies.js`, `tools/scrapers/top_movies_scraper.py`
- **JSON I/O:** `TORONTOEVENTS_ANTIGRAVITY/shared/top-movies.json`

### `regime-detector.yml`

- **Name:** Daily Regime Detection + Position Sizing
- **Triggers:** schedule:
- **Cron:** `30 20 * * 1-5`, `0 14 * * 0`
- **Jobs:** `regime-detection`, `meta-labeler-training`
- **Scripts:** `meta_labeler.py`, `position_sizer.py`, `regime_detector.py`

### `regime-terminal.yml`

- **Name:** Regime Terminal  HMM Live Scanner
- **Triggers:** schedule:
- **Cron:** `*/30 * * * *`
- **Jobs:** `regime-scan`
- **Scripts:** `.github/scripts/safe_push.sh`, `STOCKS/competition/.regime_cache.js`, `alpha_engine/data/hmm_regime.js`, `regime_terminal/data/active_signals.js`, `regime_terminal/data/regime_state.js`
- **JSON I/O:** `STOCKS/competition/.regime_cache.json`, `active_signals.json`, `alpha_engine/data/hmm_regime.json`, `hmm_regime.json`, `regime_cache.json`, `regime_state.json`, `regime_terminal/data/active_signals.json`, `regime_terminal/data/regime_state.json`

### `research-orchestrator.yml`

- **Name:** Research Orchestrator (weekly)
- **Triggers:** —
- **Cron:** `0 6 * * 6`
- **Jobs:** `research`
- **Scripts:** `tools/swarm/swarm_run.py`

### `riseoftheclaw-weekly-backtest.yml`

- **Name:** [RiseOfTheClaw] Weekly Backtest + Elimination
- **Triggers:** schedule:
- **Cron:** `0 3 * * 0`
- **Jobs:** `backtest`
- **Scripts:** `KIMI_RISEOFTHECLAW/backtest_engine.py`, `KIMI_RISEOFTHECLAW/data/backtest_detail.js`, `KIMI_RISEOFTHECLAW/data/backtest_rankings.js`, `data/backtest_rankings.js`
- **JSON I/O:** `KIMI_RISEOFTHECLAW/data/backtest_detail.json`, `KIMI_RISEOFTHECLAW/data/backtest_rankings.json`, `backtest_rankings.json`, `data/backtest_rankings.json`

### `rl-agent-ppo.yml`

- **Name:** RL Agent (PPO) Train & Predict
- **Triggers:** workflow_dispatch:
- **Jobs:** `rl-agent`
- **Scripts:** `.github/scripts/safe_push.sh`

### `scrape-events.yml`

- **Name:** Scrape events
- **Triggers:** workflow_dispatch:
- **Cron:** `0 12 * * *`
- **Jobs:** `scrape`
- **Scripts:** `.github/scripts/assert_no_conflict_markers.sh`, `.github/scripts/safe_push.sh`, `add_missing_events.py`, `github.sh`, `next/events.js`, `tools/scrape_and_sync_events.py`
- **JSON I/O:** `events.json`, `last_update.json`, `next/events.json`

### `sec-edgar-fetch.yml`

- **Name:** SEC EDGAR  Insider Trades & 13F Holdings
- **Triggers:** schedule:
- **Cron:** `0 13 * * 1-5`, `0 6 * * 0`
- **Jobs:** `sec-fetch`

### `self_optimizing_trading.yml`

- **Name:** Self-Optimizing Trading Bot - Auto-Validates & Tweaks
- **Triggers:** schedule, push, workflow_dispatch
- **Cron:** `0 */4 * * *`
- **Jobs:** `trade`
- **Scripts:** `.github/scripts/safe_push.sh`, `self_optimizing_bot.py`
- **JSON I/O:** `performance_history.json`, `trading_results.json`

### `send-accountability-reminders.yml`

- **Name:** Send Accountability Reminders
- **Triggers:** schedule:
- **Cron:** `0 * * * *`
- **Jobs:** `send-reminders`
- **Scripts:** `/tmp/reminder_response.js`
- **JSON I/O:** `/tmp/reminder_response.json`

### `send-event-notifications.yml`

- **Name:** Send Event Notifications (DISABLED)
- **Triggers:** workflow_dispatch
- **Cron:** `0 13 * * *`, `0 13 * * 1`
- **Jobs:** `send-daily`, `send-weekly`

### `send-goal-followups.yml`

- **Name:** Send Morning Goal Follow-Ups
- **Triggers:** schedule:
- **Cron:** `0 14 * * *`
- **Jobs:** `send-followups`

### `sidecar-status-update.yml`

- **Name:** Sidecar Status Markdown Update
- **Triggers:** schedule:
- **Cron:** `7 */4 * * *`
- **Jobs:** `render`
- **Scripts:** `.github/scripts/safe_commit_push.sh`, `audit_dashboard/data/dashboard_data.js`, `tools/render_sidecar_status_md.py`
- **JSON I/O:** `audit_dashboard/data/dashboard_data.json`

### `signal-engine.yml`

- **Name:** Crypto Signal Engine
- **Triggers:** schedule:
- **Cron:** `*/30 * * * *`, `0 2 * * *`
- **Jobs:** `signal-engine`
- **Scripts:** `.github/notify-failure.sh`, `.github/scripts/safe_push.sh`, `crypto_signal_engine/audit_push.py`, `crypto_signal_engine/data/active_picks.js`
- **JSON I/O:** `crypto_signal_engine/data/active_picks.json`

### `signal-integrator.yml`

- **Name:** Signal Integrator - Isolated Source Aggregator
- **Triggers:** schedule:
- **Cron:** `15 * * * *`
- **Jobs:** `integrate`
- **Scripts:** `.github/scripts/safe_push.sh`, `alpha_engine/data/integration_report.js`, `alpha_engine/isolated_signal_integrator.py`
- **JSON I/O:** `alpha_engine/data/integration_report.json`

### `signal-quality-monitor.yml`

- **Name:** Signal Quality Monitor
- **Triggers:** schedule:
- **Cron:** `15 * * * *`
- **Jobs:** `monitor-quality`
- **Scripts:** `.github/scripts/safe_push.sh`, `reports/quality/latest.js`
- **JSON I/O:** `reports/quality/latest.json`

### `signal-recorder.yml`

- **Name:** Signal Recorder
- **Triggers:** schedule:
- **Cron:** `48 * * * *`
- **Jobs:** `record-signals`
- **Scripts:** `.github/scripts/safe_push.sh`, `signal_recorder/combo_engine.py`, `signal_recorder/export_hub_combos.py`, `signal_recorder/forward_test_picks.py`, `signal_recorder/outcome_tracker.py`, `signal_recorder/system_scanner.py`, `signal_recorder/tv_technicals.py`

### `signal_tracking.yml`

- **Name:** Signal Tracking & Validation - Beat the Market
- **Triggers:** schedule, push, workflow_dispatch
- **Cron:** `0 */2 * * *`
- **Jobs:** `track-and-validate`
- **Scripts:** `.github/scripts/safe_push.sh`, `self_optimizing_bot.py`, `signal_tracker.py`
- **JSON I/O:** `signals_database.json`, `tweak_history.json`, `validation_results.json`

### `skyrocket-detector.yml`

- **Name:** Skyrocket Detector  Live Scanner
- **Triggers:** schedule:
- **Cron:** `33 * * * *`
- **Jobs:** `scan`
- **Scripts:** `.github/scripts/assert_no_conflict_markers.sh`, `.github/scripts/safe_push.sh`

### `smart-money-tracker.yml`

- **Name:** \U0001F9E0 Smart Money Intelligence
- **Triggers:** schedule:
- **Cron:** `0 11 * * 1-5`, `0 14 * * 0`
- **Jobs:** `finnhub-data`, `sec-13f`, `social-sentiment`, `consensus`
- **Scripts:** `insider_tracker.py`, `sec_13f_tracker.py`, `wsb_sentiment.py`

### `smart-picks-tracker.yml`

- **Name:** Smart Picks Tracker
- **Triggers:** schedule:
- **Cron:** `54 * * * *`
- **Jobs:** `track`
- **Scripts:** `.github/scripts/safe_commit_push.sh`, `alpha_engine/data/smart_picks.js`, `alpha_engine/data/smart_picks_history.js`, `smart_picks_engine.py`, `smart_picks_tracker.py`
- **JSON I/O:** `alpha_engine/data/smart_picks.json`, `alpha_engine/data/smart_picks_history.json`

### `social-prediction-tracker.yml`

- **Name:** Social Media Prediction Tracker
- **Triggers:** schedule:
- **Cron:** `30 */2 * * *`
- **Jobs:** `track-predictions`
- **Scripts:** `.github/scripts/safe_commit_push.sh`, `data/leaderboard.js`, `predictions/audit_push.py`, `scrapers/coincodex_scraper.py`, `scrapers/coinmarketcap_scraper.py`, `scrapers/crypto_community_scraper.py`, `scrapers/currents_kol_scraper.py`, `scrapers/eventregistry_kol_scraper.py`, `scrapers/fourchan_scraper.py`, `scrapers/gnews_kol_scraper.py`, `scrapers/kalshi_scraper.py`, `scrapers/limitless_scraper.py`, `scrapers/mediastack_kol_scraper.py`, `scrapers/messari_kol_scraper.py`, `scrapers/newsapi_kol_scraper.py`, `scrapers/polymarket_scraper.py`, `scrapers/reddit_scraper.py`, `scrapers/stocktwits_scraper.py`, `scrapers/substack_kol_scraper.py`, `scrapers/telegram_kol_scraper.py`, `scrapers/thenewsapi_kol_scraper.py`, `scrapers/tradingview_scraper.py`, `scrapers/twitter_scraper.py`, `scrapers/web_kol_scraper.py`, `scrapers/youtube_kol_scraper.py` … (+3)
- **JSON I/O:** `data/leaderboard.json`

### `social_investigation.yml`

- **Name:** Social Media Algo Trader Investigation
- **Triggers:** schedule, workflow_dispatch
- **Cron:** `0 12 * * *`
- **Jobs:** `investigate-traders`
- **Scripts:** `.github/scripts/safe_push.sh`, `social_trader_database.py`
- **JSON I/O:** `social_traders.json`

### `specialized-scanners.yml`

- **Name:** Specialized Scanners - Rocket, Short Engine, TSMOM
- **Triggers:** schedule:
- **Cron:** `0 1,5,9,13,17,21 * * *`
- **Jobs:** `run-scanners`
- **Scripts:** `.github/scripts/safe_push.sh`, `alpha_engine/data/rocket_picks.js`, `alpha_engine/data/short_dominant_picks.js`, `alpha_engine/data/tsmom_picks.js`, `alpha_engine/rocket_scanner.py`, `alpha_engine/short_dominant_engine.py`, `alpha_engine/tsmom_strategy.py`
- **JSON I/O:** `alpha_engine/data/rocket_picks.json`, `alpha_engine/data/short_dominant_picks.json`, `alpha_engine/data/tsmom_picks.json`

### `spike-scanner.yml`

- **Name:** Spike Scanner
- **Triggers:** schedule:
- **Cron:** `0 */2 * * *`
- **Jobs:** `scan`

### `sports-betting-refresh.yml`

- **Name:** Sports Betting  Odds Refresh & Auto-Settle
- **Triggers:** schedule:
- **Cron:** `0 15,18,21,0,3 * * *`
- **Jobs:** `odds-refresh`, `custom-sports-update`
- **Scripts:** `.sql/.sh`, `/tmp/odds_probe.js`, `/tmp/today.js`, `alpha_engine/data/sports_prediction_market_signals.js`, `backfill/sports_custom_picks.js`, `live-monitor/backfill/sports_prediction_market_signals.js`, `live-monitor/balldontlie_odds_fallback.py`, `live-monitor/betway_ca_scraper.py`, `live-monitor/cfl_odds_scraper.py`, `live-monitor/highlightly_odds_fallback.py`, `live-monitor/multi_source_odds_fallback.py`, `live-monitor/nfl_odds_scraper.py`, `live-monitor/nhl_nba_odds_fallback.py`, `live-monitor/nhl_odds_scraper.py`, `live-monitor/oddsharvester_clv_backfill.py`, `live-monitor/olg_line_checker.py`, `live-monitor/olg_prolineplus_scraper.py`, `live-monitor/sportsbetting_lib/backtest_runner.py`, `live-monitor/sportsdataverse_backfill.py`, `live-monitor/thesportsdb_schedule_gate.py`, `prediction_market_agents/sports_prediction_market_bridge.py`, `tools/update_custom_sports_picks.py`
- **JSON I/O:** `/tmp/odds_probe.json`, `/tmp/today.json`, `alpha_engine/data/sports_prediction_market_signals.json`, `backfill/sports_custom_picks.json`, `live-monitor/backfill/sports_prediction_market_signals.json`

### `sports-data-snapshots.yml`

- **Name:** Sports data snapshots
- **Triggers:** schedule:
- **Cron:** `*/15 * * * *`
- **Jobs:** `snapshot`
- **Scripts:** `live-monitor/data/nhl_goalies_today.js`, `live-monitor/data/tennis_elo_ratings.js`, `live-monitor/tennis_elo_engine.py`, `tools/pinnacle_anchor_scrape.py`, `tools/scrapers/nhl_goalie_scraper.py`
- **JSON I/O:** `live-monitor/data/nhl_goalies_today.json`, `live-monitor/data/tennis_elo_ratings.json`, `nhl_goalies_today.json`, `tennis_elo_ratings.json`

### `sports-forensics-weekly.yml`

- **Name:** Sports Forensics Weekly
- **Triggers:** schedule:
- **Cron:** `30 6 * * 1`
- **Jobs:** `forensics`
- **Scripts:** `tools/validate_sports_api_schema.py`

### `sports-prediction-market-sync.yml`

- **Name:** Sports Prediction Market Sync
- **Triggers:** schedule:
- **Cron:** `0 14,20 * * *`
- **Jobs:** `sync`
- **Scripts:** `alpha_engine/data/sports_prediction_market_signals.js`, `alpha_engine/sports_prediction_market_sync.py`, `backfill/sports_prediction_market_signals.js`
- **JSON I/O:** `alpha_engine/data/sports_prediction_market_signals.json`, `backfill/sports_prediction_market_signals.json`

### `sports-smoke-and-e2e.yml`

- **Name:** Sports endpoint smoke + Playwright
- **Triggers:** pull_request:
- **Cron:** `17 * * * *`
- **Jobs:** `smoke`, `deploy-guard`
- **Scripts:** `config/auto_place_policy.js`, `live-monitor/sports-betting.js`, `tests/sports_betting_js_errors.spec.js`, `tests/test_sports_endpoints_smoke.py`, `tools/deploy_sports_files.sh`
- **JSON I/O:** `config/auto_place_policy.json`

### `statistical_validation.yml`

- **Name:** Statistical Rigor Validation - Thousands of Signals
- **Triggers:** schedule, workflow_dispatch
- **Cron:** `0 0 * * *`
- **Jobs:** `statistical-validation`
- **Scripts:** `.github/scripts/safe_push.sh`, `statistical_validator.py`

### `stocks-daily-stocksunify.yml`

- **Name:** STOCKSUNIFY Daily Stock Picks
- **Triggers:** schedule:
- **Cron:** `40 21 * * 1-5`
- **Jobs:** `generate`
- **Scripts:** `.github/scripts/safe_push.sh`, `STOCKSUNIFY/data/daily-stocks.js`, `STOCKSUNIFY/package-lock.js`
- **JSON I/O:** `STOCKSUNIFY/data/daily-stocks.json`, `STOCKSUNIFY/package-lock.json`, `daily-stocks.json`

### `stocks-daily.yml`

- **Name:** Daily Stock Picks Generator (STOCKSUNIFY)
- **Triggers:** schedule:
- **Cron:** `35 21 * * 1-5`
- **Jobs:** `generate`
- **Scripts:** `.github/scripts/safe_push.sh`, `STOCKSUNIFY/data/daily-stocks.js`
- **JSON I/O:** `STOCKSUNIFY/data/daily-stocks.json`, `daily-stocks.json`

### `stocksunify2-pull.yml`

- **Name:** STOCKSUNIFY2 daily-stocks pull
- **Triggers:** schedule:
- **Cron:** `5 13 * * *`
- **Jobs:** `pull`
- **Scripts:** `audit_dashboard/data/stocksunify2_active_picks.js`, `tools/safe_commit_push.sh`, `tools/sync_stocksunify2.py`
- **JSON I/O:** `audit_dashboard/data/stocksunify2_active_picks.json`

### `strategy-forward-tester.yml`

- **Name:** Strategy Forward Tester
- **Triggers:** schedule:
- **Cron:** `15 */2 * * *`
- **Jobs:** `forward-test`
- **Scripts:** `.github/scripts/safe_push.sh`, `alpha_engine/strategies/connors_rsi2.py`, `alpha_engine/strategies/new_strategies/forex_carry.py`, `alpha_engine/strategies/new_strategies/tsmom.py`, `tools/data/strategy_prover_results.js`, `tools/strategy_prover/strategy_prover.py`
- **JSON I/O:** `tools/data/strategy_prover_results.json`

### `strategy-health-monitor.yml`

- **Name:** Strategy Health Monitor
- **Triggers:** schedule:
- **Cron:** `0 */4 * * *`
- **Jobs:** `refresh`
- **Scripts:** `.github/scripts/safe_push.sh`, `strategy_health/data/banned_strategies.js`
- **JSON I/O:** `banned_strategies.json`, `strategy_health/data/banned_strategies.json`

### `strategy-health-report.yml`

- **Name:** Strategy Health Report
- **Triggers:** schedule:
- **Cron:** `0 8 * * *`
- **Jobs:** `report`

### `strategy-performance-no-regression.yml`

- **Name:** strategy_performance.json no-regression guard
- **Triggers:** pull_request:
- **Jobs:** `check`
- **Scripts:** `alpha_engine/data/strategy_performance.js`, `alpha_engine/forward_validator.py`, `github.event.pull_request.base.sh`, `github.event.pull_request.head.sh`, `tools/prune_strategy_performance.py`
- **JSON I/O:** `alpha_engine/data/strategy_performance.json`, `strategy_performance.json`

### `sustained-gainer-scan.yml`

- **Name:** Sustained Gainer Confluence Scanner
- **Triggers:** schedule:
- **Cron:** `16,46 * * * *`
- **Jobs:** `sustained-gainer`
- **Scripts:** `.github/scripts/safe_push.sh`, `alpha_engine/data/sustained_gainer_state.js`, `alpha_engine/sustained_gainer_algorithm.py`
- **JSON I/O:** `alpha_engine/data/sustained_gainer_state.json`

### `swarm-janitor.yml`

- **Name:** swarm-janitor
- **Triggers:** schedule:
- **Cron:** `0 4 * * *`
- **Jobs:** `janitor`
- **Scripts:** `tools/swarm/swarm_janitor.py`

### `swarm-pick-review.yml`

- **Name:** Swarm Pick Review (resolve + weekly + patterns)
- **Triggers:** schedule:
- **Cron:** `0 3 * * *`
- **Jobs:** `refresh`
- **Scripts:** `audit_dashboard/data/swarm_leaderboard.js`, `audit_dashboard/data/swarm_pattern_tags.js`, `audit_dashboard/data/swarm_picks.js`, `tools/swarm/outcome_resolver_swarm.py`, `tools/swarm/pattern_miner.py`, `tools/swarm/swarm_pick_schema.py`, `tools/swarm/weekly_review.py`
- **JSON I/O:** `audit_dashboard/data/swarm_leaderboard.json`, `audit_dashboard/data/swarm_pattern_tags.json`, `audit_dashboard/data/swarm_picks.json`

### `swarm-sync-v2.yml`

- **Name:** Swarm State Sync
- **Triggers:** schedule:
- **Cron:** `*/30 * * * *`
- **Jobs:** `sync`
- **Scripts:** `tools/swarm_sync.py`
- **JSON I/O:** `agent_shared_memory.json`, `agent_swarm_state.json`

### `swing_screener_daily.yml`

- **Name:** UEPS Swing Screener Daily
- **Triggers:** —
- **Cron:** `0 14 * * 1-5`
- **Jobs:** `run-swing-screener`
- **Scripts:** `alpha_engine/data/swing_picks.js`, `alpha_engine/data/swing_screener_picks.js`, `alpha_engine/equity_price_failover.py`, `alpha_engine/swing_screener_runner.py`, `audit_dashboard/data/swing_screener_picks.js`
- **JSON I/O:** `alpha_engine/data/swing_picks.json`, `alpha_engine/data/swing_screener_picks.json`, `audit_dashboard/data/swing_screener_picks.json`

### `system-health-check.yml`

- **Name:** System Health Check
- **Triggers:** schedule:
- **Cron:** `0 */2 * * *`
- **Jobs:** `health-check`
- **Scripts:** `.github/scripts/safe_push.sh`, `circuit_breaker_system.py`, `data_fetcher_enhanced.py`, `forward_testing/signal_quality_ml.py`, `forward_trade_executor_v2.py`, `reports/health/latest.js`, `risk_management/position_sizer.py`, `signal_aggregator/integrations.py`, `signal_aggregator/ml_consensus.py`
- **JSON I/O:** `reports/health/latest.json`

### `taste-profile-scan.yml`

- **Name:** Taste Profile Scanner
- **Triggers:** workflow_dispatch:
- **Cron:** `0 3 * * 0`
- **Jobs:** `scan`
- **Scripts:** `favcreators/public/taste-profile/taste_profile.js`, `tools/deploy_to_ftp.py`, `tools/taste_profile_scanner.py`
- **JSON I/O:** `favcreators/public/taste-profile/taste_profile.json`, `taste_profile.json`

### `test-fast.yml`

- **Name:** Test Fast Variants
- **Triggers:** workflow_dispatch:
- **Jobs:** `test`

### `test-portfolios.yml`

- **Name:** Test Portfolios  Hourly Strategy Validation
- **Triggers:** schedule:
- **Cron:** `22 * * * *`
- **Jobs:** `run`
- **Scripts:** `.github/scripts/safe_commit_push.sh`, `battleground/data/test_portfolios.js`, `battleground/test_portfolios.py`
- **JSON I/O:** `battleground/data/test_portfolios.json`

### `top-gainers-scan.yml`

- **Name:** Top Gainers Spike Scanner
- **Triggers:** schedule:
- **Cron:** `*/30 13-19 * * 1-5`
- **Jobs:** `scan`
- **Scripts:** `.github/scripts/safe_push.sh`, `STOCKS/competition/forward_picks.js`, `STOCKS/scanners/data/top_gainers_picks.js`, `STOCKS/scanners/top_gainers_scanner.py`
- **JSON I/O:** `STOCKS/competition/forward_picks.json`, `STOCKS/scanners/data/top_gainers_picks.json`

### `torontoevent-algorithm-refresh.yml`

- **Name:** [torontoevent.net] Algorithm Competition Refresh
- **Triggers:** schedule:
- **Cron:** `0 10 * * 0`
- **Jobs:** `refresh-competition`
- **Scripts:** `.github/scripts/assert_ftp_host.sh`, `.github/scripts/safe_push.sh`, `STOCKS/competition/competition-crypto.js`, `STOCKS/competition/competition-forex.js`, `STOCKS/competition/competition-meme_coins.js`, `STOCKS/competition/competition-penny_stocks.js`, `STOCKS/competition/competition-results.js`, `STOCKS/competition/competition-slim.js`, `STOCKS/competition/competition-stocks.js`, `STOCKS/competition/forward_picks.js`, `STOCKS/competition/run_competition.py`
- **JSON I/O:** `STOCKS/competition/competition-crypto.json`, `STOCKS/competition/competition-forex.json`, `STOCKS/competition/competition-meme_coins.json`, `STOCKS/competition/competition-penny_stocks.json`, `STOCKS/competition/competition-results.json`, `STOCKS/competition/competition-slim.json`, `STOCKS/competition/competition-stocks.json`, `STOCKS/competition/forward_picks.json`

### `torontoevent-backtest-and-deploy-ROOCODE.yml`

- **Name:** [torontoevent.net] Run Backtests & Deploy Dashboards (ROOCODE)
- **Triggers:** schedule:
- **Cron:** `0 6 * * *`, `*/15 14-21 * * 1-5`, `0 */4 * * 0,6`
- **Jobs:** `backtest-ROOCODE`
- **Scripts:** `.github/scripts/safe_push.sh`, `//torontoevent.net/kimi-claw-ROOCODE/data/dashboard_data.js`, `//torontoevent.net/kimi-claw-ROOCODE/data/tier1_summary.js`, `KIMI_CLAW_RESEARCH_FEB162026/backtest_framework.py`, `KIMI_CLAW_RESEARCH_FEB162026/generate_dashboard_data.py`, `KIMI_CLAW_RESEARCH_FEB162026/run_tier1_backtest.py`, `KIMI_CLAW_RESEARCH_FEB162026/strategies_tier1.py`, `KIMI_RISEOFTHECLAW/live_scanner.py`, `generate_dashboard_data.py`, `live_scanner.py`
- **JSON I/O:** `//torontoevent.net/kimi-claw-ROOCODE/data/dashboard_data.json`, `//torontoevent.net/kimi-claw-ROOCODE/data/tier1_summary.json`

### `torontoevent-backtest-and-deploy.yml`

- **Name:** [torontoevent.net] Run Backtests & Deploy Dashboards
- **Triggers:** schedule:
- **Cron:** `0 6 * * *`, `*/15 14-21 * * 1-5`, `0 */4 * * 0,6`
- **Jobs:** `backtest`
- **Scripts:** `.github/scripts/safe_push.sh`, `//torontoevent.net/kimi-claw/data/dashboard_data.js`, `//torontoevent.net/kimi-claw/data/tier1_summary.js`, `KIMI_CLAW_RESEARCH_FEB162026/backtest_framework.py`, `KIMI_CLAW_RESEARCH_FEB162026/generate_dashboard_data.py`, `KIMI_CLAW_RESEARCH_FEB162026/run_tier1_backtest.py`, `KIMI_CLAW_RESEARCH_FEB162026/strategies_tier1.py`, `KIMI_RISEOFTHECLAW/live_scanner.py`, `generate_dashboard_data.py`, `live_scanner.py`
- **JSON I/O:** `//torontoevent.net/kimi-claw/data/dashboard_data.json`, `//torontoevent.net/kimi-claw/data/tier1_summary.json`

### `torontoevent-deploy-competition.yml`

- **Name:** [torontoevent.net] Deploy Competition to Live Site
- **Triggers:** push:
- **Jobs:** `deploy`
- **Scripts:** `.github/scripts/assert_ftp_host.sh`, `STOCKS/competition/competition-crypto.js`, `STOCKS/competition/competition-forex.js`, `STOCKS/competition/competition-meme_coins.js`, `STOCKS/competition/competition-penny_stocks.js`, `STOCKS/competition/competition-slim.js`, `STOCKS/competition/competition-stocks.js`, `STOCKS/competition/forward_picks.js`, `backtest_cursor.py`, `cross_aggregation/data/consensus_outcomes.js`, `cross_aggregation/data/super_signals.js`, `simpleton_backtest.py`, `simpleton_backtester.py`
- **JSON I/O:** `STOCKS/competition/competition-crypto.json`, `STOCKS/competition/competition-forex.json`, `STOCKS/competition/competition-meme_coins.json`, `STOCKS/competition/competition-penny_stocks.json`, `STOCKS/competition/competition-slim.json`, `STOCKS/competition/competition-stocks.json`, `STOCKS/competition/forward_picks.json`, `cross_aggregation/data/consensus_outcomes.json`, `cross_aggregation/data/super_signals.json`

### `torontoevent-deploy-live-monitor.yml`

- **Name:** [torontoevent.net] Deploy Live Monitor APIs
- **Triggers:** push:
- **Jobs:** `deploy`
- **Scripts:** `.github/scripts/assert_ftp_host.sh`

### `torontoevent-deploy-riseoftheclaw.yml`

- **Name:** [torontoevent.net] Deploy Rise of the Claw
- **Triggers:** schedule:
- **Cron:** `*/30 * * * *`
- **Jobs:** `deploy`
- **Scripts:** `KIMI_RISEOFTHECLAW/live_scanner.py`, `KIMI_RISEOFTHECLAW/signal_tracker.py`, `data/live_competition.js`, `data/scan_runs.js`
- **JSON I/O:** `data/live_competition.json`, `data/scan_runs.json`

### `torontoevent-forward-test.yml`

- **Name:** [torontoevent.net] Forward Test Daily
- **Triggers:** schedule:
- **Cron:** `30 14 * * 1-5`, `0 16,20,0,4 * * *`
- **Jobs:** `forward-test`
- **Scripts:** `.github/scripts/assert_ftp_host.sh`, `.github/scripts/safe_push.sh`, `STOCKS/competition/forward_picks.js`, `STOCKS/competition/forward_test.py`
- **JSON I/O:** `STOCKS/competition/forward_picks.json`, `forward_picks.json`

### `torontoevent-goldmine-tracker.yml`

- **Name:** [torontoevent.net] Goldmine Tracker - Archive & Maintain
- **Triggers:** schedule:
- **Cron:** `0 7 * * *`, `0 18 * * *`, `0 0 * * *`
- **Jobs:** `track-and-maintain`

### `torontoevent-rapid-validation.yml`

- **Name:** [torontoevent.net] Rapid Validation Engine
- **Triggers:** schedule:
- **Cron:** `18 * * * *`
- **Jobs:** `rapid-validation`

### `torontoevent-spike-scanner.yml`

- **Name:** [torontoevent.net] Spike Scanner
- **Triggers:** schedule:
- **Cron:** `*/30 * * * *`
- **Jobs:** `scan`

### `track-quick-picks.yml`

- **Name:** Track Quick Pick Portfolios
- **Triggers:** schedule:
- **Cron:** `0 23 * * 1-5`, `0 12 * * 0`
- **Jobs:** `track-portfolios`

### `traditional-test-portfolios.yml`

- **Name:** Traditional Test Portfolios (5-8)
- **Triggers:** schedule:
- **Cron:** `30 13 * * 1-5`, `30 19 * * 1-5`, `30 1 * * 1-5`, `30 7 * * 1-5`
- **Jobs:** `run-portfolios`
- **Scripts:** `.github/scripts/safe_push.sh`, `alpha_engine/data/traditional_portfolio_results.js`, `alpha_engine/data/traditional_portfolio_state.js`
- **JSON I/O:** `alpha_engine/data/traditional_portfolio_results.json`, `alpha_engine/data/traditional_portfolio_state.json`

### `train_crypto_models.yml`

- **Name:** Train Crypto ML Models
- **Triggers:** schedule:
- **Cron:** `0 0 * * *`
- **Jobs:** `train`
- **Scripts:** `.github/scripts/assert_no_conflict_markers.sh`, `.github/scripts/safe_push.sh`, `backtest_results/walk_forward_results.js`, `ml_crypto_predictor/fetch_and_populate_db.py`, `ml_crypto_predictor/production_engine.py`, `updates/data/antigravity_ml_live_picks.js`, `updates/data/antigravity_ml_performance.js`, `updates/data/antigravity_ml_scorecard.js`
- **JSON I/O:** `backtest_results/walk_forward_results.json`, `updates/data/antigravity_ml_live_picks.json`, `updates/data/antigravity_ml_performance.json`, `updates/data/antigravity_ml_scorecard.json`

### `tv-paper-tpsl-watchdog.yml`

- **Name:** TV Paper TP/SL Watchdog
- **Triggers:** schedule:
- **Cron:** `*/15 * * * *`
- **Jobs:** `audit`
- **Scripts:** `alpha_engine/data/tv_paper_positions_snapshot.js`, `tools/tv_paper_tpsl_audit.py`
- **JSON I/O:** `alpha_engine/data/tv_paper_positions_snapshot.json`

### `tv-strategy-scanner.yml`

- **Name:** TradingView Strategy Scanner
- **Triggers:** schedule:
- **Cron:** `0 */4 * * *`
- **Jobs:** `scan`
- **Scripts:** `.github/scripts/safe_push.sh`, `tv_strategy_scanner.py`

### `ueps-pick-runner.yml`

- **Name:** UEPS Pick Runner
- **Triggers:** —
- **Cron:** `15 */4 * * *`
- **Jobs:** `run-ueps-pickers`
- **Scripts:** `.github/scripts/safe_push.sh`, `alpha_engine/data/active_picks.js`, `alpha_engine/equity_price_failover.py`, `audit_dashboard/data/ueps_picks.js`, `dashboard_generator.py`, `safe_push.sh`, `tools/run_ueps_pickers.py`
- **JSON I/O:** `active_picks.json`, `alpha_engine/data/active_picks.json`, `audit_dashboard/data/ueps_picks.json`, `ueps_picks.json`

### `ueps_smoke_tests.yml`

- **Name:** UEPS Smoke Tests
- **Triggers:** —
- **Jobs:** `ueps-pytest`
- **Scripts:** `_resolver.py`, `alpha_engine/dividend_history_fetcher.py`, `alpha_engine/earnings_calendar_fetcher.py`, `alpha_engine/fundamentals_fetcher.py`, `alpha_engine/long_term_pick_contract.py`, `alpha_engine/swing_resolver.py`, `alpha_engine/swing_screener.py`, `alpha_engine/thesis_resolver.py`, `alpha_engine/value_screener.py`, `screener.py`, `steps.py`, `tests/test_dividend_history_fetcher.py`, `tests/test_earnings_calendar_fetcher.py`, `tests/test_fundamentals_fetcher.py`, `tests/test_long_term_pick_contract.py`, `tests/test_swing_resolver.py`, `tests/test_swing_screener.py`, `tests/test_thesis_resolver.py`, `tests/test_value_backtest.py`, `tests/test_value_screener.py`

### `universe-expander.yml`

- **Name:** ALPHA ENGINE - Universe Expander
- **Triggers:** schedule:
- **Cron:** `52 */4 * * *`
- **Jobs:** `expand-universe`
- **Scripts:** `.github/scripts/safe_push.sh`, `alpha_engine/data/universe_expansion.js`, `alpha_engine/gainer_universe_expander.py`
- **JSON I/O:** `alpha_engine/data/universe_expansion.json`

### `update-creator-news.yml`

- **Name:** Update Creator News
- **Triggers:** schedule:
- **Cron:** `0 */2 * * *`
- **Jobs:** `update-news`
- **Scripts:** `/tmp/result.js`
- **JSON I/O:** `/tmp/result.json`

### `validate-hf-asset-class.yml`

- **Name:** Validate HF by asset class
- **Triggers:** —
- **Cron:** `35 6 * * *`
- **Jobs:** `validate`
- **Scripts:** `alpha_engine/conviction_stack.py`, `audit_trail/data/dashboard_hc_parity.js`, `audit_trail/data/hf_asset_class_report.js`, `audit_trail/data/tier_significance.js`, `config/hf_conviction_tiers.js`, `tests/test_dashboard_hc_rules.py`, `tests/test_hf_pick_contracts.py`, `tests/test_hf_validation_stats.py`, `tools/dashboard_hc_rules.py`, `tools/hf_pick_contracts.py`, `tools/hf_validation_stats.py`, `tools/tier_significance.py`, `tools/validate_dashboard_parity.py`, `tools/validate_hf_by_asset_class.py`
- **JSON I/O:** `audit_trail/data/dashboard_hc_parity.json`, `audit_trail/data/hf_asset_class_report.json`, `audit_trail/data/tier_significance.json`, `config/hf_conviction_tiers.json`

### `value_resolver_quarterly.yml`

- **Name:** UEPS Value Resolver Quarterly
- **Triggers:** —
- **Cron:** `0 7 1 */3 *`
- **Jobs:** `run-value-resolver`
- **Scripts:** `alpha_engine/data/long_term_value_closures.js`, `alpha_engine/data/value_resolver_closures.js`, `alpha_engine/equity_price_failover.py`, `alpha_engine/value_resolver_runner.py`, `audit_dashboard/data/value_resolver_closures.js`
- **JSON I/O:** `alpha_engine/data/long_term_value_closures.json`, `alpha_engine/data/value_resolver_closures.json`, `audit_dashboard/data/value_resolver_closures.json`

### `value_screener_weekly.yml`

- **Name:** UEPS Value Screener Weekly
- **Triggers:** —
- **Cron:** `0 6 * * 1`
- **Jobs:** `run-value-screener`
- **Scripts:** `alpha_engine/data/long_term_value_picks.js`, `alpha_engine/data/value_screener_picks.js`, `alpha_engine/equity_price_failover.py`, `alpha_engine/value_screener_runner.py`, `audit_dashboard/data/value_screener_picks.js`
- **JSON I/O:** `alpha_engine/data/long_term_value_picks.json`, `alpha_engine/data/value_screener_picks.json`, `audit_dashboard/data/value_screener_picks.json`

### `volatile-alt-scanner.yml`

- **Name:** VOLATILE ALT SCANNER Hyperliquid High-Vol Alts
- **Triggers:** schedule:
- **Cron:** `3 * * * *`
- **Jobs:** `volatile-alt-scan`
- **Scripts:** `.github/scripts/safe_push.sh`, `alpha_engine/data/active_picks.js`, `alpha_engine/data/volatile_alt_picks.js`, `alpha_engine/volatile_alt_scanner.py`
- **JSON I/O:** `alpha_engine/data/active_picks.json`, `alpha_engine/data/volatile_alt_picks.json`

### `walk-forward-backtest.yml`

- **Name:** Walk-Forward Backtest (Weekly)
- **Triggers:** schedule:
- **Cron:** `0 8 * * 0`
- **Jobs:** `walk-forward`
- **Scripts:** `.github/scripts/safe_push.sh`, `alpha_engine/data/forex_walk_forward_results.js`, `alpha_engine/data/institutional_backtest_report.js`, `alpha_engine/data/walk_forward_results.js`, `alpha_engine/data/wf_audit_picks.js`, `alpha_engine/forex_walk_forward_builtins.py`, `alpha_engine/generate_wf_audit_picks.py`, `alpha_engine/walk_forward_backtester.py`, `backtest_results/walk_forward_results.js`
- **JSON I/O:** `alpha_engine/data/forex_walk_forward_results.json`, `alpha_engine/data/institutional_backtest_report.json`, `alpha_engine/data/walk_forward_results.json`, `alpha_engine/data/wf_audit_picks.json`, `backtest_results/walk_forward_results.json`

### `walkforward-gate.yml`

- **Name:** walkforward-gate
- **Triggers:** pull_request:
- **Jobs:** `gate`
- **Scripts:** `alpha_engine/data/backtest_forward_correlation.js`, `alpha_engine/data/walkforward_results.js`, `tests/test_walkforward_gate.py`, `tools/check_walkforward_gate.py`
- **JSON I/O:** `alpha_engine/data/backtest_forward_correlation.json`, `alpha_engine/data/walkforward_results.json`

### `weekly-stock-simulation.yml`

- **Name:** Weekly Exhaustive Stock Simulation
- **Triggers:** schedule:
- **Cron:** `0 6 * * 0`
- **Jobs:** `run-exhaustive-simulation`

### `weekly-strategy-scorecard.yml`

- **Name:** Weekly Strategy Scorecard
- **Triggers:** schedule:
- **Cron:** `0 0 * * 0`
- **Jobs:** `scorecard`
- **Scripts:** `.github/scripts/safe_push.sh`, `tools/data/strategy_prover_results.js`, `tools/strategy_prover/drift_monitor.py`, `tools/strategy_prover/strategy_prover.py`
- **JSON I/O:** `tools/data/strategy_prover_results.json`

### `weekly_score_quartile_spread.yml`

- **Name:** Weekly score quartile spread
- **Triggers:** —
- **Cron:** `15 14 * * 1`
- **Jobs:** `quartile-spread`
- **Scripts:** `analyze_audit_scores_vs_pnl.py`, `tools/data/score_pnl_analysis.js`, `tools/weekly_score_quartile_regression.py`
- **JSON I/O:** `tools/data/score_pnl_analysis.json`

### `what-worked-insights.yml`

- **Name:** What Worked Active Picks Insights
- **Triggers:** schedule:
- **Cron:** `0 */4 * * *`
- **Jobs:** `what-worked`
- **Scripts:** `.github/scripts/safe_push.sh`, `alpha_engine/data/what_worked.js`, `alpha_engine/what_worked.py`
- **JSON I/O:** `alpha_engine/data/what_worked.json`

### `winner-pattern-scanner.yml`

- **Name:** Winner Pattern Precursor Scanner
- **Triggers:** schedule:
- **Cron:** `18,48 * * * *`
- **Jobs:** `winner-pattern-scan`
- **Scripts:** `.github/scripts/safe_push.sh`, `alpha_engine/data/active_picks.js`, `alpha_engine/data/precursor_history.js`, `alpha_engine/data/precursor_picks.js`, `alpha_engine/winner_pattern_strategy.py`
- **JSON I/O:** `active_picks.json`, `alpha_engine/data/active_picks.json`, `alpha_engine/data/precursor_history.json`, `alpha_engine/data/precursor_picks.json`, `precursor_history.json`, `precursor_picks.json`

### `worldclass-intelligence.yml`

- **Name:** World-Class Intelligence  Daily Pipeline
- **Triggers:** schedule:
- **Cron:** `30 11 * * 1-5`, `0 14 * * 0`
- **Jobs:** `worldclass-intelligence`
- **Scripts:** `congress_tracker.py`, `cusum_detector.py`, `finbert_sentiment.py`, `hmm_regime.py`, `hyperparam_optimizer.py`, `macro_intelligence.py`, `meta_labeling.py`, `onchain_analytics.py`, `options_flow.py`, `portfolio_optimizer.py`, `signal_bundles.py`, `transfer_entropy_analyzer.py`, `walk_forward_validator.py`, `worldquant_alphas.py`

### `worldclass-pipeline.yml`

- **Name:** World-Class Algorithm Pipeline
- **Triggers:** schedule:
- **Cron:** `45 20 * * 1-5`, `0 15 * * 0`
- **Jobs:** `regime`, `alphas`, `bundles`, `intelligence`, `validate`, `summary`
- **Scripts:** `congress_tracker.py`, `cusum_detector.py`, `finbert_sentiment.py`, `fred_macro.py`, `meta_labeler.py`, `onchain_analytics.py`, `options_flow.py`, `portfolio_optimizer.py`, `position_sizer.py`, `regime_detector.py`, `signal_bundles.py`, `transfer_entropy_analyzer.py`, `walk_forward_validator.py`, `worldquant_alphas.py`

### `wsl-runner-manager.yml`

- **Name:** WSL Runner Manager
- **Triggers:** workflow_dispatch:
- **Jobs:** `manage-runner`, `check-status`
- **Scripts:** `run.sh`
