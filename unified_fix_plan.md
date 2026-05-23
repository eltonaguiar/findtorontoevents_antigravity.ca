# Unified Remediation Plan for Algorithmic Trading System

## Overview
This plan unifies findings from `audit_report.md` (initial high-level audit) and `AUDIT_REPORT_2026-02-18.md` (detailed follow-up). Key issues include: 0 forward-test trades, poor win rates (0-44%), data staleness (daily forex data for intraday signals), API instability (yfinance failures), inadequate TP/SL calibration, noisy ML features, and lack of statistical certainty scoring. The system lags Renaissance Technologies-level performance (Sharpe >3, WR ~52-55% with microsecond latency) due to no real-time data, unvalidated strategies, and static risk params.

Focus: High-certainty crypto/forex predictions (24/7 for crypto) with entry, TP/SL, mimicking premium Discord services (real-time alerts, multi-indicator confluence, on-chain insights). All fixes use free/low-cost resources to maintain $0 API spend where possible.

Plan structured by priority, with owners, effort, and impact. Total timeline: 1-3 months. Goal: Achieve 55-65% WR, Sharpe >1.0, >70% signal certainty.

## Key Issues Summary (Unified from Both Reports)
- **Data Quality:** Stale timestamps, missing values (NaNs), duplicates, fake simulated prices in production.
- **ML Performance:** Insufficient training data, noisy features, no held-out sets, wrong metrics (accuracy vs. ROC-AUC), 0 forward-test validation.
- **API/Pipeline:** yfinance instability (15-20% failures), daily-only forex data, no retries, hardcoded secrets.
- **Signal Quality:** 0-44% WR, 94% expiration rate, static TP/SL mismatched to volatility, no statistical confidence (e.g., std dev-based probability).
- **Benchmarking Gap:** Vs. Renaissance (microsecond latency, 100+ data feeds) and premium services (75-95% WR, real-time alerts) – our batch CI delays signals by 15-30min.

## Unified Remediation Roadmap

### Priority 1 (Critical – Fix in 1-2 Weeks)
These address immediate failures (0 wins, fake data, security) to enable basic functionality.

- **Action 1.1: Remove simulated prices and fix data sources.**
  - Details: Replace `mt_rand()` in `live.php` with real APIs (yfinance for stocks, Binance WS for crypto). Integrate OANDA/Twelve Data for intraday forex.
  - Owner: Data Pipeline Agent.
  - Effort: Low.
  - Impact: Eliminates fake data; enables accurate crypto/forex predictions.

- **Action 1.2: Rotate exposed secrets.**
  - Details: Move API keys/DB passwords to env vars; rotate compromised ones.
  - Owner: DevOps Agent.
  - Effort: Low.
  - Impact: Security fix; prevents breaches.

- **Action 1.3: Implement forward-test gate.**
  - Details: Require ≥30 forward-test trades per strategy with WR >50%, Sharpe >1.0 before deployment. Update `prove_winners.py` and `signal_tracker.py`.
  - Owner: ML Performance Agent.
  - Effort: Medium.
  - Impact: No more unvalidated strategies; directly fixes 0 forward trades.

- **Action 1.4: Add yfinance retries and monitoring.**
  - Details: Exponential backoff (3 tries); log failures to `scan_errors.json`.
  - Owner: API Audit Agent.
  - Effort: Low.
  - Impact: Reduces pipeline failures by 50-70%.

### Priority 2 (High – Complete in 2-4 Weeks)
Focus on crypto/forex enhancements for high-certainty signals.

- **Action 2.1: Real-time crypto pipeline (24/7).**
  - Details: Use Binance WebSocket for continuous price feeds; generate/check signals every 10-60 seconds. Prioritize majors (BTC, ETH) and memes (DOGE, PEPE).
  - Owner: Signal Quality Agent.
  - Effort: Medium.
  - Impact: Enables "quick trades" with <1s latency; mimics premium real-time alerts.

- **Action 2.2: Dynamic TP/SL with std dev certainty.**
  - Details: Set TP/SL as multiples of rolling std dev (e.g., TP = entry + 2*std_dev, SL = entry -1*std_dev). Compute P(TP before SL) using normal approximation; filter signals <70% certainty.
  - Owner: Signal Quality Agent.
  - Effort: Medium.
  - Impact: Improves resolution rate to >50%; provides "high certainty" metric like premium services.

- **Action 2.3: Confluence filtering with on-chain data.**
  - Details: Require 2+ indicator agreement (RSI, MACD, etc.) + on-chain check (e.g., high liquidations from CoinGlass free API signal squeezes).
  - Owner: Strategy Enhancement Agent.
  - Effort: Medium.
  - Impact: Boosts WR by 10-15%; adds "skyrocketing find" detection for crypto.

- **Action 2.4: Fix ML ranker.**
  - Details: Remove noisy features; switch to ROC-AUC; add train/test split and regime-conditional training.
  - Owner: ML Performance Agent.
  - Effort: Medium.
  - Impact: Lifts model accuracy to 60-65%; better ranks high-certainty picks.

### Priority 3 (Medium – Complete in 1-3 Months)
Longer-term enhancements for Renaissance-level edge.

- **Action 3.1: Regime-conditional strategies.**
  - Details: Route signals based on market regime (ADX for trend, VIX for vol); compute regime-specific WR/CI.
  - Owner: Signal Quality Agent.
  - Effort: High.
  - Impact: Further WR lift (5-10%); avoids mismatched trades.

- **Action 3.2: Real-time notifications.**
  - Details: Build Telegram/Discord bot for push alerts on high-certainty signals (entry, TP/SL, certainty %).
  - Owner: DevOps Agent.
  - Effort: Medium.
  - Impact: Matches premium services' delivery; enables user monetization.

- **Action 3.3: On-chain/meme sentiment integration.**
  - Details: Add CoinGlass for liquidations/OI; Reddit API for meme buzz. Trigger signals on whale activity or social spikes.
  - Owner: Data Quality Agent.
  - Effort: Medium.
  - Impact: Unique edge for crypto "skyrocketing finds" without extra cost.

- **Action 3.4: Walk-forward optimization loop.**
  - Details: Auto-retrain monthly with fresh data; demote decaying strategies.
  - Owner: ML Performance Agent.
  - Effort: High.
  - Impact: Sustains performance over time, approaching quant firm standards.

## Resource Requirements
- **APIs:** Binance WS, OANDA/Twelve Data, CoinGlass, Reddit (all free tiers).
- **Tools:** NumPy/SciPy for stats; WebSockets for real-time.
- **Cost:** $0 (potential $5-10/mo for VPS if needed for 24/7 WS listener).
- **Testing:** 1-week forward-test on testnet; monitor WR, Sharpe, certainty.

This plan will elevate the system to compete with top firms: real-time, statistically robust crypto/forex picks with >70% certainty, targeting 60%+ WR and Sharpe >1. If implemented, re-audit in 3 months.

