# Penalty Calibration Audit — 2026-04-15

## Executive Summary

Comprehensive analysis of 3,500 closed picks from `dashboard_data.json` revealed the scoring/penalty system was **blocking profitable strategies** and **over-stacking trust penalties**. Four targeted fixes were applied to `audit_trail/quality_gates.py`.

---

## Problem Statement

| Metric | Finding |
|--------|---------|
| Gating rejection rate | 67% (211 active_raw → 69 pass gates → 142 blocked) |
| Score 30-39 bucket | **52.7% WR, +215.2% cumPnL** — best bucket, but filtered out by min score 50 |
| Score 40-49 bucket | 42.4% WR, -81.3% cumPnL — **worse** than Score 30-39 |
| Score 50-59 bucket | 42.9% WR, -36.6% cumPnL — still **underperforms** Score 30-39 |
| Low Score + High PnL anomalies | **331 picks** blocked with positive PnL |
| High Score + Negative PnL | **45 picks** passed gates but lost money |

**Key insight:** The score-to-PnL relationship is **non-monotonic** — the scoring system penalizes components that don't correlate with profitability, creating a "dead zone" at scores 40-55.

---

## Changes Made (all in `audit_trail/quality_gates.py`)

### 1. Forward-Validated Strategy Bypass (Smart Gate)

**Location:** `passes_smart_gate()` — score threshold section

**What:** If a strategy has strong forward-test evidence (≥20 trades & ≥50% WR, or ≥10 trades & ≥55% WR), it can bypass the per-asset-class min score gate.

**Why:** Strategies like `luxalgo_confluence` (64.4% WR, 90 trades, +120.8% cumPnL) scored only ~37.8 avg because they get 0 ML score, 0 source bonus, and 0 confluence points — none of which relate to their actual edge. The forward WR is the direct measure of profitability.

**Affected strategies (previously blocked, now can pass):**
| Strategy | Trades | WR | CumPnL | Avg Score |
|----------|--------|----|--------|-----------|
| luxalgo_confluence | 90 | 64.4% | +120.8% | 37.8 |
| strong consensus | 103 | 56.3% | +61.5% | 33.4 |
| Bollinger MR | 80 | 53.8% | +59.7% | 31.0 |
| forex_rsi2_mean_reversion | 394 | 50.5% | +34.5% | 21.0 |
| stocks_rsi2_pullback | 10 | 90.0% | +12.9% | 23.0 |
| donchian-stock-breakout | 5 | 80.0% | +33.3% | 18.0 |

### 2. Goldmine Crypto Asset-Class Block

**Location:** `BLOCKED_ASSET_STRATEGY_PAIRS`

**What:** Added `(CRYPTO, goldmine_1x_consensus)`, `(CRYPTO, goldmine_2x_consensus)`, `(CRYPTO, goldmine_3x_consensus)` to the blocked pairs list.

**Why:** These strategies have 18-19% WR on crypto with -29% to -87% cumPnL but were scoring ~49 (just under the gate threshold), occasionally leaking through. They were previously un-killed because their EQUITY application works — this block is crypto-specific, preserving equity picks.

### 3. Strategy & Source Scoring Bonuses

**Location:** `_STRATEGY_SCORES` and `_SOURCE_SYSTEM_SCORES`

**What added:**

| Dict | Entry | Bonus | Rationale |
|------|-------|-------|-----------|
| `_SOURCE_SYSTEM_SCORES` | `luxalgo_filters` | +10 | Powers luxalgo_confluence (64.4% WR, 90 trades) |
| `_STRATEGY_SCORES` | `luxalgo_confluence` | +15 | 64.4% WR, +120.8% cumPnL, was getting 0 strategy pts |
| `_STRATEGY_SCORES` | `strong consensus` | +10 | 56.3% WR, +61.5% cumPnL |
| `_STRATEGY_SCORES` | `bollinger mr` | +10 | 53.8% WR, +59.7% cumPnL |
| `_STRATEGY_SCORES` | `stocks_rsi2_pullback` | +8 | 90.0% WR on 10 trades |
| `_STRATEGY_SCORES` | `donchian-stock-breakout` | +8 | 80.0% WR on 5 trades |
| `_STRATEGY_SCORES` | `macd_rsi_confluence` | +6 | 58.3% WR on 12 trades |

**Note:** `luxalgo_confluence` also has a LONG direction penalty of -10 (35% WR on LONGs) — the edge is on SHORTs. Net effect: SHORT picks get +15, LONG picks get +5. This is correct per the data.

### 4. Trust Penalty Stack Reduction

**Location:** `_apply_score_penalties()` — trust scoring section

**What:** Reduced `trust_low(N)` penalty from **-15 → -10**.

**Why:** Low-trust picks were getting triple-stacked penalties:
- `trust_LOW` (trust label): -10
- `trust_low(N)` (trust score ≤3): -15 → now **-10**
- `long_low_trust_combo`: -10

**Before:** Total stack = **-35** (kills any pick starting under score ~85)  
**After:** Total stack = **-30** (still meaningful, 5pts less devastating)

This penalty combination was the #1 reason picks were being gated out (90× trust_LOW, 71× trust_low, 66× long_low_trust_combo in the active_raw pool).

---

## Projected Benefits

### Quantified Impact (from threshold backtesting on 3,500 closed picks)

| Metric | Before | After (projected) |
|--------|--------|-------------------|
| Smart Picks passing gate | 69 of 211 (33%) | ~85-100 of 211 (40-47%) |
| Blocked winners recovered | 0 | ~15-25 picks with WR>50% |
| Goldmine crypto drain stopped | -87% to -29% cumPnL leak | Blocked at source |
| luxalgo_confluence score | ~37.8 avg → blocked | ~62.8 avg → passes gate |
| Trust penalty max stack | -35 | -30 |

### Expected PnL Impact

From the score-bucket backtesting:
- **Score ≥35 threshold** (what forward bypass effectively creates): cumPnL +289.5%, PF 1.44 — vs Score ≥50 current: +183.7%, PF 1.63
- Net: **+105.8% additional cumPnL** captured with slightly lower PF (still well above 1.0)
- The PF reduction is acceptable because the 30-39 score bucket (52.7% WR) has **better WR than the 40-55 range** that currently passes

### Risk Mitigation

- Forward bypass requires **hard evidence** (≥20 trades at ≥50% WR or ≥10 at ≥55%) — can't game it
- Goldmine block is crypto-only — equity application preserved
- Trust penalty still strong (-30 max stack) — just not absurdly punishing
- All other Smart Gate checks still apply (mode, health, RR, direction conflict, tech alignment, etc.)

---

## Where to See the Impact

### findtorontoevents.ca/audit

| Section | What changes | Related strategies/systems |
|---------|-------------|--------------------------|
| **Smart Picks tab** | More picks qualify; previously blocked ~15-25 winners will now appear | `luxalgo_confluence`, `strong consensus`, `Bollinger MR`, `forex_rsi2_mean_reversion`, `stocks_rsi2_pullback` |
| **Active Picks tab** | Goldmine crypto picks get -20 `blocked_strategy` penalty | `goldmine_1x_consensus`, `goldmine_2x_consensus`, `goldmine_3x_consensus` (CRYPTO only) |
| **Tier breakdown** | S-Tier (51.5% WR) should improve as forward-validated strategies join Smart Picks | All strategies with ≥50% forward WR and ≥20 trades |
| **Score distribution** | Scores shift up +6 to +25 for affected strategies (source + strategy bonuses) | `luxalgo_confluence` (+25 total), `strong consensus` (+10), `Bollinger MR` (+10) |
| **Penalty breakdown** | `trust_low(N):-15` entries change to `trust_low(N):-10` | All picks with trust_score 1-3 |
| **Gated-out picks** | Fewer picks show "score below threshold" as rejection reason | Forward-validated strategies with 10+ trades and WR ≥55% |

### Source Systems Affected

| Source | Strategy | Impact |
|--------|----------|--------|
| `luxalgo_filters` | `luxalgo_confluence` | New +10 source bonus + +15 strategy bonus = +25 score lift |
| `stocks_competition` | `Bollinger MR` | +10 strategy bonus (source already has +15) |
| `alpha_engine` | `strong consensus` | +10 strategy bonus |
| `goldmine_stocks` | `goldmine_*_consensus` (CRYPTO) | Blocked via BLOCKED_ASSET_STRATEGY_PAIRS |
| All low-trust sources | Any trust_score 1-3 | -5 pts less penalty (from -15 to -10) |

### Dashboard Metrics to Monitor Post-Deploy

1. **Smart Picks count** — should increase from ~69 to ~85-100
2. **Smart Picks WR%** — should stay ≥50% (forward-validated bypass ensures only proven strategies enter)
3. **S-Tier cumPnL** — should improve as we stop blocking the 52.7% WR score-bucket
4. **Goldmine crypto picks** — should no longer appear in Smart Picks
5. **Trust penalty histogram** — peak moves from -35 to -30

---

## Files Modified

- `audit_trail/quality_gates.py` — all 4 changes

## Not Changed (Considered but deferred)

| Considered | Rationale for deferral |
|-----------|----------------------|
| Lower `SMART_PICKS_MIN_SCORE` from 50 to 35 | Forward bypass achieves same effect without lowering the general floor. Risk: lets in untested strategies. |
| Lower `SMART_PICKS_MIN_SCORE_EQUITY` from 50 to 25 | Equity score distribution is anti-predictive at 35-49. Needs deeper investigation into *why* that range performs poorly before lowering. |
| Kill `goldmine_*_consensus` globally | Equity application is producing +2-4% winners. Crypto-only block is the right scalpel. |
| Add more `_VIABLE_STRATEGIES_FORWARD` entries | The forward bypass mechanism achieves this dynamically — strategies with forward data don't need manual catalog entries. |
