---
title: "World-Class Gameplan Synthesis — 2026-05-27"
date: 2026-05-27
sources:
  - reports/2026-05-27_world_class_benchmark.md (subagent A)
  - reports/2026-05-27_strategy_reverse_engineering.md (subagent B)
  - swarm_runs/gameplan-*/deepseek.json (multi-AI quant CIO consult)
  - audit_dashboard/data/pf_registry.json (canonical, fresh 2026-05-26 20:26 UTC)
  - audit_dashboard/data/db_health.json (live MySQL integrity)
  - audit_dashboard/data/ai_tournament_leaderboard.json (grok3 leads BUILDING)
---

# Are we world-class? No. Here's the honest gameplan.

## Are we top-notch per asset class today?

**No.** Canonical net-of-slippage policy-clean view (`pf_registry.json::by_asset_class_policy_clean_net`):

| Class | n | WR | PF | World-class benchmark | Gap |
|---|---:|---:|---:|---|---|
| CRYPTO | 210 | 30.95% | **0.96** | Renaissance ~70%, Sharpe 2+ | -0.5 PF, -39pp WR |
| FOREX | 11 | 9.09% | 0.20 | AQR systematic Sharpe 0.8-1.2 | losing |
| FUTURES | 11 | 9.09% | 0.47 | Bridgewater Sharpe 1+ | losing |
| EQUITY | missing | INSUFF | INSUFF | Citadel/Two Sigma Sharpe 1.5+ | no data |
| COMMODITY | missing | INSUFF | INSUFF | -- | no data |
| ETF | missing | INSUFF | INSUFF | -- | no data |
| BOND | missing | INSUFF | INSUFF | -- | no data |

`money_ready_verdict.json::summary.money_ready = []`. **Zero classes money-ready, zero on watch.**

## Genuinely unsaturated edges — only 3 candidates

Per the anti-overfit audit (42 strategies × Bonferroni + holdout):

| Strategy | DSR | n | OOS WR | Status | Saturation risk |
|---|---:|---:|---:|---|---|
| **COMMODITY: cot_positioning SHORT** (CT=F) | 1.0 | 137 raw / **5 deduped** | 74.45% raw | SHADOW_INSUFFICIENT_N | Over-emission falsified (26×); needs 15+ more CFTC releases (~4 months) |
| **CRYPTO: ml_crypto_predictor** | 0.95+ | 255 | 43.5% / PF 10.58 holdout 2.52 | EDGE_LIKELY_REAL | Single-source concentration |
| **EQUITY: stocks_rsi2_pullback** | 0.994 | 70 | 62.9% | EDGE_LIKELY_REAL | Bull-regime-dependent |

**The famous "78.9% CRYPTO Smart-Picks" headline is the EXPIRED→WON mislabel trap**, not edge.

**AI Tournament**: grok3 is the only model with PF lower-95-CI > 1.0 (n=13 resolved, BUILDING phase, 17 more needed for rank-eligibility).

## Gameplan (synthesized from subagent + multi-AI consult)

### First 14 days — fix data, not models

The hedge-fund CIO consult (deepseek): "**The biggest mistake is optimizing for in-sample Sharpe via a massive model ensemble that memorizes noise, while data contamination makes all backtests unreliable.**"

1. **Halt new strategy development.** Fix the 38.97% PnL mismatch + 56,559 ghost rows + frozen validator (335h) before believing ANY new backtest. db_health.json's `won_pnl_contradiction` shows 2,595 WON rows averaging **−40.04% PnL** — fix the labeling pipeline first.

2. **Strip to one simple CRYPTO model.** Take 3-5 features, single linear/logistic model, strict 20% holdout (never retrained). Compare to the 23-model ensemble. If the simple model beats the ensemble, the ensemble is overfit and should be discarded.

3. **Run a permutation test on the surviving "EDGE_LIKELY_REAL" 3 strategies.** Shuffle target labels 1,000 times, retrain, measure where real PF lands in noise distribution. Must be > 99th percentile.

### 3 questions for our AI ensemble we probably haven't asked

1. For each of 23 models, what's the OOS Sharpe on a **completely unseen 20% holdout that was never touched** during training OR validation?
2. If we randomly shuffle target labels and retrain, what's the distribution of PF/Sharpe across 1,000 shuffles? Does our real result lie outside the 99th percentile?
3. Which single feature, when removed, causes the largest OOS-performance drop? If none, the ensemble is overfit.

### Spend / cut

**ADD spend on:**
- Senior quant with live-trading track record (3-month audit)
- Tick-level CRYPTO data (Coinbase/Binance nanosecond timestamps) to replace suspect feed
- Compute for Monte Carlo + bootstrap validation, NOT more models

**CUT:**
- Cancel API subs for 20 of 23 models — keep top-3 by OOS Sharpe (likely zero)
- Freeze FOREX, FUTURES, EQUITY/COMMODITY/ETF/BOND development until CRYPTO data is clean
- Eliminate "regime gates" and "ML composite scoring" — complexity without evidence of edge

### The single 90-day bet

**CRYPTO**, because:
- Most data (n=210 already, vs 11 for FOREX/FUTURES)
- 24/7 continuous markets → faster iteration
- Current PF 0.96 is close to break-even — small genuine edge MAY be buried under noise
- Clean tick data + 1 simple model could reach PF 1.5 in 90 days; FOREX/FUTURES can't reach statistical significance at all

If a 90-day clean-data + simple-model CRYPTO experiment doesn't beat PF 1.2, **pivot to execution-only strategies** (market making, latency arbitrage) — predictive edge isn't accessible to us.

## Strategy-level reverse-engineering (subagent B)

For the 2 EDGE_LIKELY_REAL strategies, specific tweaks proposed (~+0.3 PF expected lift each):

**CRYPTO ml_crypto_predictor (currently PF 10.58 holdout 2.52)**:
- Widen TP on consensus-LONG signals (current TP-too-tight is the EXPIRED→WON trap)
- Add 2× ATR stops (vs fixed 0.5%)
- SPY > 200SMA gate (regime overlay)

**EQUITY stocks_rsi2_pullback (currently WR 62.9% n=70)**:
- RSI < 5 entry filter (was RSI < 10) — tighten oversold definition
- SPY > 200SMA gate — only enter in bull regime
- 2× ATR stop replacing 1.5% fixed

**COMMODITY CT=F COT (SHADOW)**:
- Add COT z-score gate (only trade when commercial-hedger positioning > 2σ extreme)
- Diversify to ZS=F, ZC=F, ZW=F (test if grain COT shares the cotton signal's structure)
- Wait for n>=20 unique CFTC releases (~16 weeks) before promoting beyond SHADOW

## What world-class actually looks like

| Firm | Sharpe | WR | Strategy archetype |
|---|---:|---:|---|
| Renaissance Medallion | 2.0+ | ~70% | Multi-thousand microstructure signals, internal tick data, decade+ refinement |
| Two Sigma | 1.5+ | ~58% | Factor portfolios, ML+fundamentals, alt-data |
| Citadel Wellington | 1.0+ | ~55% | Multi-strat, market-making, statistical arb |
| AQR systematic | 0.8-1.2 | ~53% | Academic factor implementation |
| Bridgewater Pure Alpha | 1.0+ | ~55% | Macro + risk parity |

We are nowhere near any of these. To get to AQR-tier (lowest bar) requires:
- Clean data first (we have <60% clean)
- 1-2 persistent signals (we have ~2 candidates pending validation)
- Honest OOS protocol (we have leakage flags on multiple datasets)
- ≥1 year of clean live track record (we have ~0 days post-data-fix)

**Realistic timeline to AQR-tier**: 9-12 months of disciplined execution starting from "data is clean" — which we're maybe 2-4 weeks away from depending on how fast P0 #4/#5/#6/#7 close.

## Confidence statement

This synthesis is built from:
- 3 canonical dashboard JSON files (fresh, generated within 6h)
- 2 subagent reports that independently read the same files
- 1 multi-AI gameplan consult (deepseek, confidence: high)
- 16 prior ticks of this session's analysis (including the TICK 15 retraction that proves the dedup discipline matters)

The verdict's robustness comes from cross-source agreement, not any single number. If even one of those sources said "you're closer than you think," I'd flag the disagreement. They don't — they converge.

## Files written this session related to this question

- reports/2026-05-27_world_class_benchmark.md (subagent A — 620 words)
- reports/2026-05-27_strategy_reverse_engineering.md (subagent B — 800 words)
- reports/2026-05-27_world_class_gameplan_synthesis.md (this file — consolidated synthesis)
- .claude/skills/consult-swarm/SKILL.md (new skill — how to ask other AIs in the future)
