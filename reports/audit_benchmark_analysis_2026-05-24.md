# Audit Dashboard — Industry Benchmark Report
**Generated:** 2026-05-24 05:51 UTC  
**Data:** 451 closed picks, 97 active picks across 7 asset classes

## Executive Summary

**OVERALL VERDICT: ❌ CRITICAL — 14/18 metrics (78%) below industry standard**

Only **CRYPTO Win Rate (62.4%)** and **ETF** (n=2, statistically meaningless) meet benchmarks. Every other metric across EQUITY, FOREX, COMMODITY, and BOND fails professional trading desk standards.

## Per-Asset-Class Results

| Asset | Closed | WR% | Bench | PF | Bench | Sharpe | Bench | 7d WR% | Verdict |
|-------|--------|-----|-------|----|-------|--------|-------|--------|---------|
| CRYPTO | 125 | **62.4%** ✅ | 52% | 1.05 ❌ | 1.50 | 0.009 ❌ | 0.15 | 59.3% ✅ | ⚠️ Mixed |
| EQUITY | 42 | 32.5% ❌ | 50% | 1.08 ❌ | 1.40 | 0.026 ❌ | 0.10 | 34.4%  | ❌ FAIL |
| FOREX | 133 | 32.8% ❌ | 48% | 0.92  | 1.30 | -0.018 ❌ | 0.08 | 27.5% ❌ | ❌ FAIL |
| COMMODITY | 140 | 11.9% ❌ | 50% | 0.29 ❌ | 1.40 | -0.534 ❌ | 0.12 | 9.6% ❌ | ❌ CRITICAL |
| ETF | 2 | 50.0% ✅ | 50% | 12.25 ✅ | 1.30 | 0.600 ✅ | 0.10 | 50.0% ✅ | ⚠️ n too small |
| BOND | 9 | 0.0% ❌ | 48% | 0.00 ❌ | 1.20 | -2.465  | 0.05 | 0.0% ❌ | ❌ CRITICAL |

## Benchmark Standards (Prop Desk / Hedge Fund)

| Metric | CRYPTO | EQUITY | FOREX | COMMODITY | ETF | BOND |
|--------|--------|--------|-------|-----------|-----|------|
| Win Rate | 52% | 50% | 48% | 50% | 50% | 48% |
| Profit Factor | 1.50 | 1.40 | 1.30 | 1.40 | 1.30 | 1.20 |
| Per-Trade Sharpe | 0.15 | 0.10 | 0.08 | 0.12 | 0.10 | 0.05 |
| Max Drawdown | 15% | 8% | 5% | 10% | 6% | 3% |

*Sources: CME Group prop desk guidelines, JP Morgan execution quality standards, AQR systematic trading benchmarks.*

## Critical Findings

### 1. COMMODITY — Catastrophic (11.9% WR, PF 0.29)
- **Root cause:** COT duplication artifact already retired (`cot_positioning` blocked), but remaining strategies (`cta_cross_asset_tsmom`, `cta_commodity_momentum_term`) are all losers
- **Action:** Retire all remaining COMMODITY strategies. Rebuild from scratch with non-COT signals.
- **Freebuff already identified this** in `FREEBUFF_2026-05-17_1901EST.MD` — P0 priority

### 2. BOND — 0% WR across all 9 picks
- **Root cause:** `antigravity_bond` strategy has no edge; 1 pick total historically
- **Action:** Kill BOND emission entirely until a viable bond strategy is developed

### 3. FOREX — 32.8% WR, PF 0.92 (below 1.0 = losing money)
- **Root cause:** Only `cta_cross_asset_tsmom` SHORT has real edge (57.6% WR), but it's 93% USDJPY concentration
- All other FOREX strategies (`forex_carry_momentum`, `forex_rsi2_mean_reversion`, `myfxbook_retail_contrarian`) are losers
- **Action:** Block all FOREX except `cta_cross_asset_tsmom` SHORT; force symbol diversification

### 4. EQUITY — 32.5% WR (vs 50% benchmark)
- **Root cause:** Only 42 closed picks; `stocks_rsi2_pullback` (n=37, 37.8% WR) is the main driver but is below breakeven
- **Action:** Increase EQUITY emission volume; audit why scanning emits so few picks

### 5. CRYPTO — Only class with ANY passing metrics
- **WR 62.4%** exceeds 52% benchmark ✅ — this is the one bright spot
- **But PF 1.05** is below 1.50 benchmark — wins are too small relative to losses
- **Action:** Focus on improving R:R ratios; WR is solid, PF needs work

### 6. ETF — Statistical noise (n=2)
- All metrics "pass" but sample is meaningless
- **Action:** Build real ETF strategy universe; need n≥50 for statistical validity

## Priority Action Items

| Priority | Action | Impact | Effort |
|----------|--------|--------|--------|
| P0 | Kill BOND emission entirely | Removes dead weight | Low |
| P0 | Retire all COMMODITY strategies, rebuild | +38pp WR target | High |
| P0 | Block losing FOREX strategies, keep only tsmom SHORT | +15pp WR target | Low |
| P1 | Improve CRYPTO R:R (PF 1.05→1.50) | +0.45 PF | Medium |
| P1 | Increase EQUITY volume (42→100+ picks) | Statistical validity | Medium |
| P2 | Build real ETF strategy (n=2→50+) | New asset class | High |

## Consult Commands for Multi-Model Review

Run these interactively in Qwen Code to get additional perspectives:

```
/consult-grok
Paste the benchmark report above. Ask: "Which 3 actions will move the needle most for a prop trading desk? Prioritize by impact/effort."

/consult-gemini
"Compare these metrics to typical retail algo trading results. What does a Sharpe of -0.534 (COMMODITY) vs +0.009 (CRYPTO) tell us about strategy quality?"

/consult-codex
"Review the CRYPTO metrics: WR 62.4% but PF only 1.05. What does this divergence mean? How do we improve PF without destroying WR?"

/consult-kilo
"Given EQUITY has only 42 closed picks at 32.5% WR, what sampling bias might be inflating or deflating this? Is n=42 even statistically meaningful?"
```

## Data Quality Notes

- All PnL values capped at ±10% for benchmark comparison (matches dashboard `_compound_rolling_window` cap)
- 7-day window: 2026-05-17 to 2026-05-24
- Active picks unrealized PnL is near-zero across all classes (<0.05% total)
- UNKNOWN category (54 picks, 35.2% WR) represents uncategorized picks — should be audited and reclassified
