# FINAL V2 REPORT — Profitability Research & Strategy Synthesis

**Date:** 2026-11-14 | **Worktree:** flaxen-hair | **Repo:** findtorontoevents_antigravity.ca

This folder contains the second-stage review: per-asset-class profitability ideas, peer work synthesis, root repo profitability research review, risk management, execution plan, and final recommendations.

## Folder Structure

| Folder | Contents |
|--------|----------|
| `01_asset_class_profitability_ideas/` | Per-asset-class profitability ideas ranked by probability of success |
| `02_peer_work_review/` | All peer agent work: finpredict-v4, hilarious-seer, scratch-hippodraco |
| `03_root_repo_review/` | Root repo profitability research (23 hypotheses, v1-v4 verdicts) |
| `04_profitability_strategies/` | Actionable profitability strategies per asset class |
| `05_risk_management/` | Risk management framework (position sizing, drawdown controls, statistical gates) |
| `06_execution_plan/` | 4-phase execution plan with go/no-go criteria |
| `07_summary_recommendations/` | Final summary and prioritized recommendations |

## Executive Summary

### The Search is Exhausted — No Approach is PROVED

The profitability research program tested **23 hypotheses across 4 protocol versions**. **NONE are PROVED** (SCORECARD.md: "Actual profitability proof: 0/10"). The keyless data hypothesis space is exhausted.

### Only ONE Approach Shows Forward Edge: mega_mutation_macd_rsi on CRYPTO

| Metric | Backtest | Forward (live since Jun 6, 2026) |
|--------|----------|----------------------------------|
| Profit Factor | 3.12–5.816 | **8.32** |
| Win Rate | 64–76% | **84%** |
| Trades | 100–593 | **50** |
| Statistical validation | — | Paired bootstrap pass_95=True (m048/m084), MC pct=0.949 |

**Production status:** `production_enable = true`, `promotion_ready = true`

### All Other Asset Classes Show Negative Edge

After PnL normalization and rigorous testing, every other asset class (equity, ETFs, bonds, mutual funds, forex, commodities/futures) shows negative or no edge. Bonds, mutual funds, forex, and commodities have **zero coverage** — no hypotheses tested, no algorithms, no data sources.

### What Was Falsified

- **Peer VWAP claim:** FALSIFIED (annualization error, PBO not PBO, DSR not DSR, intrabar stops PF 0.81)
- **TradingView contest winners:** Survivorship bias, not proof of repeatable method
- **H10 RSI(2):** NOT_PROVED (contaminated OOS, effective N≈38, execution fragility)

## Top 3 Recommendations

### P0 — Do This Week
1. Paper trade mega_mutation via gated scanner daily (`daily_forward_tracker.py --once`)
2. Monitor forward performance toward n=100 target (currently n=50)
3. Apply finpredict-v4 6-gate scoring to all strategies

### P1 — Do This Sprint
4. Clean forward OOS test of H10 RSI(2) on SPY/QQQ (frozen parameters)
5. Develop new hypotheses for untested asset classes (bonds, mutual funds, forex, commodities)
6. Investigate ENA funding-rate collinearity risk

### P2 — Do in 1-3 Months
7. Promote to live capital only if go/no-go criteria met (n≥100, WR≥55%, PF≥1.5, all gates passing)
8. Acquire new data sources (intraday, options, venue-level capital)
9. Implement heterogeneous stacking and prediction tail clipping

## Peer Agents Reviewed

| Peer | Contribution |
|------|-------------|
| finpredict-v4 | 6-gate statistical scoring framework + TradingView contest winner research |
| hilarious-seer | Per-asset-class quick-win synthesis + live PnL refresh |
| scratch-hippodraco | Per-asset-class quick-wins bundle + peer review + ML validation |
| childlike-airport | Stale data + accuracy audit across asset classes |
