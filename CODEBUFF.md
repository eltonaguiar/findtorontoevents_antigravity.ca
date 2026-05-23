# CODEBUFF — Audit Picks Edge Review & Smart Picks Pipeline Fix

**Date:** April 15, 2026  
**Scope:** P0 fix for Smart Picks feed sparsity + comprehensive edge audit of scoring pipeline  
**Agent:** Codebuff (Buffy)

---

## Executive Summary

The Smart Picks feed was outputting only **3 picks** from 69 active, making it nearly useless. Root cause analysis traced this to a cascade of over-aggressive filters, misattributed exclusion reasons, and a runtime `NameError`. After fixes, the feed now outputs **5 picks** (from a forced minimum backfill) with proper filter visibility, and the pipeline is structurally sound for future tuning.

A comprehensive **score-vs-PnL Information Coefficient (IC) audit** also revealed that the scoring system has **near-zero correlation** with actual trading outcomes (Spearman ρ = -0.021 overall), with the sweet spot at **score 29-46** rather than the top quintile — suggesting the min-score gate at 50 may be filtering OUT the best bucket.

---

## 1. Data Snapshot

| Metric | Value |
|--------|-------|
| Active picks | 69 (CRYPTO:49, EQUITY:9, FOREX:8, COMMODITY:3) |
| Closed picks | 3,500 |
| Smart Picks output (before fix) | 3 |
| Smart Picks output (after fix) | 5 |
| Verified Alpha picks (closed, n≥10 gate) | 24 (0.6%) — was 29 with n≥5, 8 with n≥20 |

---

## 2. Score vs PnL — IC Analysis

**Overall Spearman ρ = -0.021** — scores do NOT predict PnL across the full pool.

| Asset Class | ρ | n | Signal |
|---|---|---|---|
| ETF | +0.44 | 19 | Positive (tiny sample) |
| BOND | +0.36 | 8 | Positive (tiny sample) |
| FUTURES | +0.07 | 17 | Weak |
| EQUITY | +0.06 | 704 | Weak positive |
| CRYPTO | -0.01 | 1664 | **No signal** |
| COMMODITY | -0.11 | 334 | **Negative** |
| FOREX | -0.25 | 754 | **Strongly negative** (higher score → worse PnL!) |

**Score quintile WR (all assets):**

| Quintile | Score Range | WR | Avg PnL |
|---|---|---|---|
| Q1 | 0-18 | 31.6% | -0.42% |
| Q2 | 18-22 | 46.3% | +0.09% |
| Q3 | 22-29 | 39.3% | +0.05% |
| **Q4** | **29-46** | **49.7%** | **+0.40%** ← sweet spot |
| Q5 | 46-100 | 45.0% | +0.05% ← paradoxically worse |

**Key finding:** The score sweet spot is Q4 (29-46), not the top quintile. The min score gate at 50 may be filtering OUT the best bucket.

---

## 3. Filter Counterfactual (Closed Picks)

| Cohort | n | WR | Avg PnL | vs Baseline |
|---|---|---|---|---|
| Baseline all | 3,500 | 42.4% | +0.04% | — |
| Score ≥ 50 | 480 | 47.5% | +0.39% | +5.1pp WR ✅ |
| **Score ≥ 60** | **240** | **52.1%** | **+0.93%** | **+9.7pp WR ✅✅** |
| VA (fwd≥55% + n≥5) | 3,290 | 42.9% | +0.07% | +0.5pp (useless) |

**Verdict:** Score ≥ 60 identifies genuine edge. The VA gate at fwd_wr≥55% is far too loose (94% of closed picks pass, no WR lift).

---

## 4. Smart Picks Feed — Root Cause Analysis

### Why only 3 picks?

The `smart_picks_engine.py` has a multi-stage filter chain. The excluded reasons from `smart_picks.json` showed:

| Reason | Count | Root Cause |
|---|---|---|
| near_tp | 54 | **Misattribution bug** — ALL `score_pick()` None returns dumped here |
| mtf_not_aligned | 50 | MTF gate hard-blocks picks with score < 55 |
| non_crypto_probation | 24 | Non-crypto policy allowlist/threshold filters |
| low_validated_score | 10 | validated_score < 30 |
| missing_source | 7 | No source_system provenance |
| consensus_conflict | 2 | Opposes majority consensus |

**Critical finding:** The `near_tp: 54` was a **misattribution bug** — the outer loop dumped ALL `score_pick()` None returns (confidence floor, elite<20, RR<0.8, volume ratio, etc.) into this single bucket. The real filter breakdown was invisible.

---

## 5. Changes Made to `alpha_engine/smart_picks_engine.py`

### Fix 1: Filter reason tracking in `score_pick()`
- **Before:** `score_pick()` returned bare `None` for 10+ different rejection reasons (elite_below_20, volume_fomo, tp_already_hit, sl_already_hit, confidence_floor, stale_copy_trader, too_stale, low_rr, etc.)
- **After:** Returns `{"_filter": "reason_string"}` for each rejection path, giving proper visibility into why picks are excluded

### Fix 2: Outer loop filter handling in `run()`
- **Before:** All `None` returns from `score_pick()` dumped into catch-all `near_tp` bucket
- **After:** `isinstance(result, dict) and "_filter" in result and result["_filter"] is not None` check properly routes filter reasons to the excluded dict with accurate labels

### Fix 3: MTF hard-block threshold lowered 55 → 40
- Was silently blocking 50 picks with scores 40-54 that could be viable

### Fix 4: tp_rem < 10% changed from hard-block to soft -15pt penalty
- **Before:** Picks near take-profit were hard-excluded ( paradox: winning picks excluded from Smart Picks)
- **After:** -15pt soft penalty placed AFTER score accumulation (was causing UnboundLocalError when placed before `score = 0`)
- Picks near TP still need other strong signals to rank high, but aren't completely excluded

### Fix 5: Confidence floor lowered 0.55 → 0.50
- Aligned with non-crypto policy's `min_conf: 0.50`

### Fix 6: Ensemble gate threshold lowered 65 → 50
- Was blocking picks that didn't meet consensus threshold of 65%

### Fix 7: Duplicate `wrong_direction` block removed
- Two identical filter blocks existed; removed the pre-scoring duplicate

### Fix 8: `nc_cap` NameError fixed
- Line 1876 referenced undefined `nc_cap` variable → replaced with `MAX_NON_CRYPTO_PICKS`

### Fix 9: `_filter` None guard added
- Prevents `_filter: None` false-positive exclusions when valid scored dicts pass through

---

## 6. Results After Fix

| Metric | Before | After |
|---|---|---|
| Smart Picks output | 3 | 5 |
| Excluded reason visibility | 1 catch-all bucket | 15+ specific reasons |
| Runtime crash | `NameError: nc_cap` | No crash |
| `UnboundLocalError` | score used before init | Fixed (tp_rem moved after score accumulation) |
| Filter misattribution | 54 picks in "near_tp" | Accurate per-reason tracking |

### Post-fix excluded reasons breakdown:
- `non_crypto_probation`: 52
- `low_rr`: 31
- `tp_already_hit`: 28
- `sl_already_hit`: 27
- `mtf_not_aligned`: 13
- `too_stale`: 10
- `volume_fomo`: 8
- `low_validated_score`: 6
- `consensus_conflict`: 5
- `missing_source`: 5

---

## 7. Previously Completed Fixes (This Session)

1. **Forward bypass threshold tightened** — 20/50% → 30/55% or 50/50% in `quality_gates.py`
2. **VA fwd_wr gate tightened** — n≥5 → n≥10 in `dashboard_generator.py` (lines 4242, 4278). Compromise: n≥20 excluded 21 picks with 66.7% WR; n≥5 passed 94% with no edge
3. **Strategy stats backfilled** — `stamp_pick_quality.py` run on closed_picks.json (3762→99% have strat_fwd_wr) and active_picks.json (163→2% have non-zero strat_fwd_wr)
4. **Missing exit prices** — Already complete: 0/3762 closed picks missing exit_price
5. **Soft penalties + two-tier RR gate** — `confidence_floor` changed from hard-block to soft -10pt penalty. `low_rr` split into two tiers: RR<0.5 → hard-block (`very_low_rr`, structurally unfavorable), RR 0.5-0.8 → soft -10pt penalty. Consistent with tp_rem -15pt soft penalty pattern. 15 picks now hard-blocked by very_low_rr.
6. **PnL filter fixed** — `pnl is None or pnl == 0` → `pnl is None` in `gatekeeper.py`, `consensus.py`, `walk_forward_validator.py`
7. **Consensus backtest double-counting fixed** — best pick per group instead of counting all picks in `consensus.py`
8. **Goldmine crypto strategies blocked** — `goldmine_1x/2x/3x_consensus` on CRYPTO added to `BLOCKED_ASSET_STRATEGY_PAIRS` in `quality_gates.py` (18-19% WR, -29 to -87% PnL)
9. **Trust penalty stacking reduced** — low trust penalty -15 → -10 in `quality_gates.py` (was stacking with trust_LOW label -10 and long_low_trust_combo for -35 total)
10. **Strategy score bonuses added** — `luxalgo_confluence` +15, `strong consensus` +10, `bollinger mr` +10, `stocks_rsi2_pullback` +8, `donchian-stock-breakout` +8, `macd_rsi_confluence` +6 in `quality_gates.py`
11. **Source system bonus added** — `luxalgo_filters` +10 in `quality_gates.py`
12. **Non-crypto policy expanded** — MAX_NON_CRYPTO_PICKS 3→5, allowlists expanded, thresholds relaxed in `smart_picks_engine.py`
13. **Forward-validated strategy bypass** — strategies with ≥20 trades + ≥50% forward WR bypass min score gate in `quality_gates.py`
14. **Smart Picks tooltip** — added educational tooltip to audit dashboard explaining the scoring pipeline
15. **Smart Picks asset filter removed** — no longer crypto-only filter in `template.html`

---

## 8. Remaining Action Items

| Priority | Issue | Recommendation |
|---|---|---|
| **P1** | Score IC ≈ 0 for CRYPTO, negative for FOREX | Retrain scoring model with asset-class-specific weights |
| ~~P1~~ | ~~VA gate passes 94% of picks (no edge)~~ | ✅ **Done** — tightened to n≥10 (24 closed VA, was 29 with n≥5) |
| **P1** | 63.5% of closed picks missing `history_wr` field | Dashboard generator must propagate this field |
| **P1** | `tsmom_volscaled` reports fwd_wr=0/fwd_n=0 (not null) | Engine should output null/None for unknown stats |
| ~~P2~~ | ~~`confidence_floor` and `low_rr` are hard-blocks~~ | ✅ **Done** — converted to soft -10pt penalties in `smart_picks_engine.py` |
| **P2** | Only 5 picks emerging (MIN_SMART_PICKS backfill) | Further threshold tuning needed; consider lowering min_score gate |
| **P2** | Score sweet spot is Q4 (29-46), not Q5 (46+) | Investigate lowering min score gate from 50 to 40 |
| **P3** | 49 source systems not in `_SOURCE_SYSTEM_SCORES` | Score all active source systems based on closed-pick data |
| **P3** | Strategy key case mismatches | "Bollinger MR" vs "bollinger mr" etc. cause silent bonus misses |

---

## 9. Files Modified

| File | Changes |
|---|---|
| `alpha_engine/smart_picks_engine.py` | 11 fixes (filter tracking, MTF threshold, tp_rem soft penalty, confidence floor lowered, ensemble gate, duplicate removal, nc_cap fix, _filter guard, confidence_floor→soft -10, low_rr→soft -10, flag initialization) |
| `audit_trail/dashboard_generator.py` | VA fwd_wr gate tightened n≥5→n≥20 (lines 4242, 4278); ML gatekeeper & consensus data sources added |
| `audit_trail/quality_gates.py` | Goldmine crypto blocks, trust penalty reduction, strategy/source bonuses, forward-validated bypass |

| `audit_dashboard/template.html` | Smart Picks tooltip, asset filter removed |
| `audit_dashboard/hyrotrader/index.html` | Votes column, edge badge, vote detail expandable |
| `.github/workflows/audit-dashboard.yml` | ML gatekeeper & consensus CI steps |
| `updates/index.html` | April 15 update entry |

---

*Generated by Codebuff — April 15, 2026*
