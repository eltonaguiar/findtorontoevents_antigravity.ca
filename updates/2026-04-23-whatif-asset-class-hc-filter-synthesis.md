# What-If / Asset Class / HC Filter Synthesis — 2026-04-23

> **⚠️ Data-source correction (added 2026-04-23 by synthesis PR #364):**
> Non-crypto findings in this doc were derived from `alpha_engine/data/closed_picks.json`,
> which contains 6,031 rows of which **5,285 have NULL `asset_class`** and only
> 4 COMMODITY / 2 FOREX / 1 EQUITY are tagged. That file is effectively crypto-only.
>
> The **correct** source for per-AC analysis is `audit_dashboard/data/dashboard_data.json.picks.recent_closed`
> (3,500 rows, full AC tags: 1,648 CRYPTO / 790 FOREX / 607 COMMODITY / 357 EQUITY / 78 ETF / 17 BOND).
>
> Therefore the following claims here are **NOT reliable**:
> - "Bonds: 0 closed picks — NO DATA" (correct count: 17)
> - "ETF: 16.7% WR on 12 picks" (correct sample: 78)
> - "Non-crypto supply-chain failure" framing
>
> Generalizable findings that survive the source error (confidence ≥ 0.90 sweet spot,
> SHORT bias on crypto, TOD windows, regime blocklist) remain useful — see
> `reports/SYNTHESIS_6_ANALYSES_AUDIT_WHATIF_2026_04_23.md` §3a for the audit trail.

## Executive Summary

This report answers four questions:
1. **What if we traded on today's picks vs yesterday's picks?** — Which portfolios/asset classes win?
2. **Which asset class has the real edge?** — Verified per-class performance
3. **How should we ideally filter picks by edge per asset class?** — The ideal methodology
4. **Why do bonds/ETFs lack validated filters?** — Root causes and gap analysis

**Central finding: The HC filter works in theory (65.3% WR counterfactual on n=75) but over-filters in practice (only 1/31 active picks pass). Confidence is anti-predictive on crypto. The real edge axis is `strat_fwd_wr >= 70` + direction bias toward SHORT + per-asset-class TP/SL calibration.**

---

## 1. What-If Analysis: Today vs Yesterday Picks

### Source: [`audit_dashboard/data/whatif_analysis.json`](audit_dashboard/data/whatif_analysis.json)

The what-if analysis covers **26 portfolios, 33 positions** with scenario comparisons.

#### By-Confidence Bucket

| Confidence Range | n | WR | PnL/10K |
|-----------------|---|-----|---------|
| 0.90+ | 9 | **88.9%** | **+$99.94** |
| 0.85–0.90 | 33 | 48.5% | -$1.04 |
| 0.80–0.85 | 500 | 21.2% | -$14.49 |
| 0.70–0.80 | 22 | **0.0%** | **-$34.54** |
| 0.60–0.70 | 11 | 18.2% | -$12.44 |

**→ The ONLY profitable confidence tier is 0.90+.** Below that, all tiers lose money. The UI's emphasis on confidence as a quality signal is actively misleading — confidence below 0.90 is either non-predictive or anti-predictive.

#### By-Strategy (Top & Bottom)

| Strategy | n | WR | PnL/10K |
|----------|---|-----|---------|
| incubator_gainer_composite | 21 | **71.4%** | **+$104.28** |
| cmf_cross | 2 | 100% | +$14.60 |
| ema_aggressive_prop | 5 | 80.0% | +$5.17 |
| ... | | | |
| enhanced_ml_A_xgboost | 6 | 16.7% | -$55.36 |
| **Breakout Momentum** | **4** | **0.0%** | **-$84.76** |

**Optimal combo:** `incubator_gainer_composite` @ confidence 0.90+ = **100% WR, +$149.77/10K** (n=4)

#### Which Asset Class Would Have Won?

The what-if data doesn't break by asset class directly, but the strategy-level data maps:
- **CRYPTO SHORT via incubator_gainer_composite**: 71.4% WR, best performer
- **Stocks/EQUITY via claude_gainer_st and copy_trader_intel**: 0-16.7% WR, worst performers
- **Forex via non_crypto_consensus**: small sample, mixed results

**Verdict: Crypto SHORT picks with high score (≥70) or incubator_gainer_composite would have won. Non-crypto picks would have lost or been untradable due to sample size.**

---

## 2. Asset Class Performance Breakdown

### Verified Win Rates (from [`updates/2026-04-22-deep-asset-class-edge-analysis.md`](updates/2026-04-22-deep-asset-class-edge-analysis.md))

| Asset Class | Closed Picks | Verified WR | Claimed WR | Mismatch? |
|-------------|-------------|-------------|------------|-----------|
| CRYPTO (ALL) | 9,124 | 34.4% | — | — |
| CRYPTO (SHORT) | 4,533 | **38.7%** | — | — |
| CRYPTO (BUY) | 4,591 | **28.7%** | — | — |
| FOREX | 34 | 23.5% | 5% | YES — actual much higher than claimed |
| EQUITY | 14 | 35.7% | 65% | YES — actual far lower |
| ETF | 12 | 16.7% | 85% | YES — actual far lower |
| FUTURES | 19 | N/A (no PnL tracked) | — | YES |
| COMMODITY | 0 | N/A | 15% | **NO DATA** |
| BOND | 0 | N/A | 47.1% | **NO DATA** |

### Critical Gap: 96% of Closed Picks Are Crypto

```
CRYPTO:    9,124 picks (95.9%)
MEME:       306 picks (3.2%)
FOREX:       34 picks (0.4%)
FUTURES:     19 picks (0.2%)
EQUITY:      14 picks (0.1%)
ETF:         12 picks (0.1%)
COMMODITY:    0 picks (0%)
BOND:         0 picks (0%)
```

**Non-crypto claims cannot be verified.** Samples of 0-34 picks are too small for any statistical significance. The multi_asset system generates picks but:
- They rarely close with tracked PnL
- The outcome resolver doesn't close non-crypto picks properly
- Filename typos in [`non_crypto_consensus.py`](copy_trader_intel/non_crypto_consensus.py) starve commodity/equity supply

### Direction Edge (CRYPTO — 9,124 picks)

| Direction | n | WR | Avg PnL | PF |
|-----------|---|-----|---------|-----|
| **SHORT** | 4,533 | **38.7%** | +0.0642% | 0.80 |
| BUY | 4,591 | **28.7%** | -0.1595% | 0.52 |

**→ SHORT outperforms BUY by 10 percentage points across 9,000+ picks.** This is the single strongest directional signal in the system.

### Time-of-Day Edge (CRYPTO)

From [`updates/2026-04-21-deep-strategy-investigation-by-asset-class.md`](updates/2026-04-21-deep-strategy-investigation-by-asset-class.md):

| Hour (UTC) | n | WR | Mean PnL |
|------------|---|-----|----------|
| 22:00 | 39 | **71.8%** | +1.08% |
| 21:00 | 56 | 47.7% | -0.45% |
| 23:00 | 73 | 45.2% | -0.29% |
| 00:00 | 65 | 43.0% | +0.61% |
| ... | | | |
| 20:00 | 41 | **17.1%** | -1.03% |
| 08:00 | 62 | 19.4% | -0.28% |

**→ A 50+ point WR swing between best and worst hours.** Time-of-day is a massively underutilized filter.

---

## 3. High-Conviction Filter: Current State

### HC Filter Architecture ([`audit_dashboard/hc_filter.js`](audit_dashboard/hc_filter.js))

The HC filter uses 9 sequential gates:
1. **Score floor** (per-asset-class)
2. **Forward WR minimum** (per-asset-class)
3. **Trust tier** (blacklist: SANDBOX, UNPROVEN, PROBATION, DEMOTED)
4. **Regime direction** (block BEAR→BUY, BULL→SHORT)
5. **Confidence gate** (≥0.80)
6. **Confidence dead-zone** (0.65-0.75 → reject)
7. **Walk-forward rejection** (fwd_trades < 2)
8. **Independent consensus** (≥3 groups)
9. **Correlation pair registry** (max 1 correlated symbol)

Plus stamped HF tier contract and supplemental path.

### HC Config ([`config/hc_gate_params.json`](config/hc_gate_params.json))

Per-asset-class floors (v4.2):
- CRYPTO: WR 40%, score 45
- EQUITY: WR 50%, score 45
- FOREX: WR 55%, score 40
- COMMODITY/FUTURES/BOND/ETF: WR 40%, score 35

**Conflict:** Embedded defaults in hc_filter.js (lines 337-359) vs end-of-file overrides. BOND/ETF/COMMODITY score floor is 40 in embedded defaults but overridden to 35 at end of file.

### HC Counterfactual Performance (from [`audit_dashboard/data/edge_report.md`](audit_dashboard/data/edge_report.md))

| Cohort | n | WR | Mean PnL% | PF |
|--------|---|-----|-----------|-----|
| Baseline (all closed) | 3,500 | 39.3% | -0.29% | 0.76 |
| **HC counterfactual** | **75** | **65.3%** | **+0.76%** | **3.44** |
| PROVEN only | 793 | 26.7% | -0.44% | 0.54 |
| PROVEN + conf 0.8-0.9 | 0 | — | — | — |

**→ HC counterfactual shows 65.3% WR, 3.44 PF — a massive improvement over baseline.** But only 75 out of 3,500 picks pass (2.1% pass rate).

### The Over-Filtering Problem

Currently only **1/31 active picks (3.2%)** pass HC gates. Three problematic gates (from [`updates/2026-04-22-active-picks-gate-overfiltering.md`](updates/2026-04-22-active-picks-gate-overfiltering.md)):

1. **Confidence gate (<0.80)** — Confidence is anti-predictive on crypto; using ≥0.80 rejects valid SHORT picks
2. **Confidence dead-zone (0.65-0.75)** — Intended to catch a bad band but the data doesn't support it being meaningfully worse than other bands
3. **Time-of-day gate (8-11 UTC, 16-21 UTC)** — Blocks hours that include valid trading windows

### The Confidence Anti-Prediction (CRYPTO)

| Confidence | n | WR | Avg PnL | PF |
|-----------|---|-----|---------|-----|
| 0.00-0.55 | 862 | **35.7%** | -0.0900% | 0.64 |
| 0.55-0.65 | 2,092 | 34.2% | -0.0886% | 0.64 |
| 0.65-0.75 | 2,830 | 33.7% | -0.0898% | 0.63 |
| 0.75-0.85 | 1,286 | 35.4% | -0.0708% | 0.69 |
| **0.85+** | **40** | **45.0%** | **+0.0661%** | **1.42** |

**→ Confidence is flat/non-predictive from 0.00 through 0.85.** The lowest confidence band (0.00-0.55) actually has HIGHER WR than most middle bands. Only the 0.85+ tier shows edge.

**Implication:** Using confidence as a primary filter gate is counterproductive. It should be demoted to a secondary/tipping indicator.

---

## 4. Bonds/ETFs: Why No Validated Filters?

### Root Cause Tree

```
BONDS/ETFs lack validated filters
├── No closed picks with PnL (0 BOND, 12 ETF)
├── Supply pipeline issues
│   ├── Filename typos in non_crypto_consensus.py
│   │   └── Starves commodity/equity supply
│   └── Multi_asset system generates picks but rarely closes them
├── PnL tracking gaps
│   ├── 105 picks in multi_asset_closed.json
│   ├── Only 51 have pnl_pct
│   └── Outcome resolver doesn't close non-crypto picks properly
├── Strategy mismatch
│   ├── Crypto strategies applied to non-crypto assets
│   ├── TP/SL not calibrated per class
│   │   └── AssetConfig has correct defaults but strategies ignore them
│   └── ETF daily moves (0.5-2%) vs crypto TP (2-10%)
└── Sample size crisis
    ├── 34 FOREX picks (borderline)
    ├── 14 EQUITY picks (too small)
    ├── 12 ETF picks (too small)
    ├── 19 FUTURES picks (mostly no PnL)
    ├── 0 COMMODITY picks (no data)
    └── 0 BOND picks (no data)
```

### Config Exists But Never Activates

[`config/hc_gate_params.json`](config/hc_gate_params.json) defines per-asset floors for BOND/ETF/COMMODITY:
- forwardWRMinPct: 40
- scoreFloor: 35 (or 40, depending on which section of config you read)
- fwdMinTrades: 2 (relaxed from 5 for small-sample classes)

**But these floors can never be validated** because no BOND/COMMODITY picks and almost no ETF picks have closed with tracked PnL. The HC filter's forward WR floor (gate 2) requires `strat_fwd_wr >= forwardWRMinPct`, but if a class has 0-12 closed picks, the forward WR is either undefined or statistically meaningless.

### Summary Table

| Class | Config Exists? | Closed Picks | Can Filter Validate? | Root Issue |
|-------|---------------|-------------|---------------------|------------|
| BOND | Yes (WR≥40%, score≥35) | 0 | **No** | No picks generated or tracked |
| COMMODITY | Yes (WR≥40%, score≥35) | 0 | **No** | Filename typos starve supply |
| ETF | Yes (WR≥40%, score≥35) | 12 | **No** | Strategy mismatch + no PnL |
| FUTURES | Yes (WR≥40%, score≥35) | 19 | **No** | PnL not tracked |
| FOREX | Yes (WR≥55%, score≥40) | 34 | **Borderline** | Small sample, pip-vs-percent corruption |
| EQUITY | Yes (WR≥50%, score≥45) | 14 | **No** | Too few samples |

---

## 5. Ideal Filtering Methodology

### The Dominant Axis: `strat_fwd_wr >= 70`

From [`updates/2026-04-17-edge-deepscan-2-filter-combos.md`](updates/2026-04-17-edge-deepscan-2-filter-combos.md):

**Every winning filter combo contains `strat_fwd_wr`.**

| Combo | n | WR | Note |
|-------|---|-----|------|
| fwd_wr≥70 + PROVEN/RELIABLE + no_conflict | 22 | **95.5%** | Super-golden |
| fwd_wr≥70 alone | ~50 | **~75%** | Single most predictive axis |
| fwd_wr≥65 | ~220 | ~61% | Threshold cliff |
| fwd_wr≥55 + score≥50 (current live) | ~400 | 61% | Current filter, below cliff |

**The threshold cliff at fwd_wr≥70 is undeniable.** Going from ≥65 to ≥70 reduces cohort by 4.4× but adds 13pp WR.

### Proposed Filter Stack (Priority Order)

```
1. ASSET_CLASS_PRESENCE
   → Reject picks in classes with <30 closed PnL samples
   → Audit: FOREX(34) = borderline pass; EQUITY(14), ETF(12), FUTURES(19), COMMODITY(0), BOND(0) = fail
   
2. strat_fwd_wr >= 70
   → Single dominant axis, validated across 3,500 closed picks
   → Overrides per-class WR floor when sample is small
   
3. DIRECTION_BIAS
   → CRYPTO: SHORT preferred (38.7% WR vs 28.7% BUY)
   → Non-crypto: direction analysis deferred until sample >30
   
4. SCORE_TIER
   → Score ≥70: strongly predictive (70% WR, PF 2.54) but rare (n=10)
   → Score ≥55: moderate filter (33.4% WR — still below baseline)
   → Score <55: reject (28-34% WR range)
   
5. CONFIDENCE (demoted to tiebreaker)
   → conf ≥0.85: positive edge (45% WR, PF 1.42) — small sample
   → conf <0.85: non-predictive — do NOT use as rejection gate
   → Remove confidence dead-zone gate entirely
   → Remove confidence minimum gate entirely
   
6. TRUST_TIER
   → Blacklist: SANDBOX, UNPROVEN, PROBATION, DEMOTED
   → PROVEN/RELIABLE: boosts WR when combined with fwd_wr≥70
   
7. REGIME_ALIGNMENT
   → RANGING regime: 0% WR (n=9) — block all picks
   → TRENDING_DOWN: 6.2% WR (n=16) — block all picks
   → Other regimes: use per-class direction rules
   
8. TIME_OF_DAY (CRYPTO ONLY)
   → Best hours: 21:00-23:59 UTC (45-72% WR)
   → Worst hours: 08:00-09:00, 20:00 UTC (17-19% WR — block)
   → Can add 5-10pp WR with no sample loss cost
   
9. INDEPENDENT_CONSENSUS
   → Require ≥3 independent signal groups
   → Current implementation correct, keep as-is
   
10. CORRELATION_REGISTRY
    → Max 1 per correlated pair
    → Current implementation correct, keep as-is
```

### Per-Asset-Class Floor Table (Revised)

| Class | Min Closed Samples | strat_fwd_wr Floor | Score Floor | Direction Preference |
|-------|-------------------|-------------------|------------|---------------------|
| CRYPTO | N/A (9,124) | 70 | 55 | SHORT >> BUY |
| FOREX | 30 (currently 34) | 70 (not 55) | 45 | TBD |
| EQUITY | 30 (currently 14) | 70 (not 50) | 45 | TBD |
| ETF | 30 (currently 12) | 70 (not 40) | 40 | TBD |
| FUTURES | 30 (currently 19) | 70 (not 40) | 40 | TBD |
| COMMODITY | 30 (currently 0) | 70 (not 40) | 40 | TBD |
| BOND | 30 (currently 0) | 70 (not 40) | 40 | TBD |

**Key change:** Non-crypto classes should use the general `strat_fwd_wr≥70` floor rather than per-class lowered floors (40-55%). The per-class floors were set low to avoid over-filtering, but low-floor picks lose money. Better to under-generate non-crypto picks with high WR than over-generate with guaranteed losses.

### Action Items

#### P0 — Fix Data Integrity (affects all analysis)
1. **Backfill asset_class** on ~5,863 untagged historical picks using [`audit_trail/asset_classification.py`](audit_trail/asset_classification.py)
2. **Fix PnL tracking** for non-crypto picks — outcome resolver must handle `realized_pnl_pct` for forex/stocks/ETF
3. **Fix non_crypto_consensus.py filename typos** to unblock commodity/equity supply (from [`updates/2026-04-18-non-crypto-synthesis-and-action-plan.md`](updates/2026-04-18-non-crypto-synthesis-and-action-plan.md))

#### P1 — Fix HC Filter Gates
4. **Remove confidence minimum gate** (≥0.80) — it's anti-predictive on crypto
5. **Remove confidence dead-zone gate** (0.65-0.75) — not empirically justified
6. **Remove time-of-day gate** from HC filter (or move to shadow/logging-only mode)
7. **Raise strat_fwd_wr floor to 70** for all asset classes (was 40-55 per class)
8. **Add SHORT bias** to crypto scoring — weight SHORT signals higher than BUY

#### P2 — Add Missing Filters
9. **Add time-of-day filter** as a standalone (not HC) module for crypto: block 08:00-09:00 UTC and 20:00 UTC
10. **Add regime-based blocking** for RANGING and TRENDING_DOWN regimes
11. **Add minimum closed-sample check** per asset class before applying forward-WR floors

#### P3 — Supply Pipeline
12. **Fix multi_asset closing pipeline** — ensure non-crypto picks close with PnL
13. **Increase non-crypto pick generation** by fixing the supply chain issues
14. **Add asset-class-specific strategy development** (stop applying crypto strategies to bonds)

### Verification Plan

After applying the proposed filter stack, verify:

1. **HC counterfactual re-run**: The new gates should maintain ≥65% WR while expanding the pass rate from 2.1% to ~5-8%
2. **Active pick pass rate**: Should increase from 1/31 (3.2%) to ~3-5/31 (10-16%)
3. **Non-crypto sample accumulation**: Track weekly whether EQUITY/FOREX/ETF closed-pick counts are growing
4. **Confidence gate removal impact**: Verify the 0.80-0.90 confidence band doesn't dump bad picks post-removal

---

## Appendix: Key Data Caveats

1. **All non-crypto WRs are based on <35 closed picks** — not statistically significant
2. **Date range is 2 months** (2026-02-22 to 2026-04-22) — too short for regime analysis
3. **Closed-pick PnL excludes fees/slippage** — real returns are worse
4. **The what-if analysis covers 33 positions** — much smaller than the 3,500-pick closed book
5. **5,863 untagged picks** may change asset class distributions if backfilled
6. **SHORT vs BUY edge (10pp)** is the strongest verified signal, but SHORT has different risk characteristics (funding rates, exchange limits)

---

*Report generated 2026-04-23 from synthesis of: dashboard_data.json, whatif_analysis.json, hc_filter.js, hc_gate_params.json, edge_report.md, hourly_asset_class_24h_report.json, consolidated_portfolios.json, and 5+ prior analysis documents.*
