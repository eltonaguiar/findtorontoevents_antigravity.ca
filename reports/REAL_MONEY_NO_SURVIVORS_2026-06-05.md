# Real-Money Picks Investigation — 2026-06-05 (No Survivors)

**Date:** 2026-06-05
**Author:** claude-sonnet-4.6
**Status:** **NO surviving real-money candidates in current dataset**

---

## 0. Headline

After 3 separate filtration attempts on the live DB:
1. CRYPTO: 4 candidate sleeves — **all REFUTED at resolver gate** (see PAPER_PILOT_RESOLVER_FAIL_2026-06-05.md)
2. Non-CRYPTO (forex/stocks/etf/commodity/bond): **0 candidates pass batch-artifact filter**

**There are no actionable real-money picks in the current `ejaguiar1_stocks.trading_picks` table.**

---

## 1. The Batch-Artifact Problem (Recap)

The 2026-06-04 backfill contaminated the entire dataset. Examples from live DB:

| Strategy | Category | Total n | 2026-06-04 n | % on 1 day |
|---|---|---|---|---|
| futures_bb_mean_reversion | commodity | 255 | **250** | 98.0% |
| non_crypto_consensus (commodity) | commodity | 738 | **724** | 98.1% |
| cta_commodity_momentum_term | commodity | 2034 | ~1900 | ~93% |
| forex_carry_momentum | forex | 707 | ~600 | ~85% |
| ig_contrarian_sentiment | forex | 3308 | ~2800 | ~85% |
| myfxbook_retail_contrarian | forex | 2481 | ~2400 | ~97% |
| regime_mild_bear | None | 26 | 21 | 80.8% |

When `max_day_count / n > 0.50` (i.e., a single date has more than half the trades), the strategy is a **batch artifact, not an edge**.

**Filter applied:** `max_day_count < 50% * n` (relaxed from the strict 35% in v2 spec)
**Result: 0 survivors from 11 candidates with n>=20 closed before 2026-06-04.**

---

## 2. What This Means for Real-Money Deployment

**All real-money deployment is BLOCKED** at this point. The infrastructure for generating paper-pilot candidates is producing fiction:

1. **CRYPTO** is blocked at the resolver gate (NOMINAL_TP_LEGACY = fiction)
2. **Non-CRYPTO** is blocked at the batch-artifact gate (closed_at backfill = fiction)
3. **All asset classes** need data quality fixes BEFORE any new paper-pilot cohort can be designed

---

## 3. Root Cause Analysis

### 3a. Why CRYPTO resolver is fiction
- `tp_fill_method = NOMINAL_TP_LEGACY` means the resolver assumes clean TP fills
- In reality, intrabar price action hits SL first in 28-100% of "TP_HIT" picks
- This is the **exact same pattern** the swarm reviewers warned about
- Fix: rewrite `alpha_engine/outcome_resolver.py` to do true intrabar OHLCV replay (P0)

### 3b. Why non-CRYPTO is fiction
- The 2026-06-04 closed_at backfill populated `closed_at` for ~35,000 picks
- All backfill was done in a single day with the same scoring/resolver pipeline
- This is a **single-snapshot resolver artifact** at the dataset level
- The picks look "real" but are all computed at the same wall-clock time
- Fix: identify the actual signal source dates (not closed_at) and use those for trade-time validation

---

## 4. Path Forward

### 4a. Data Quality (P0)
- **Identify signal source dates** for all picks (not closed_at)
- **Re-score picks using true intrabar OHLCV** (existing `TP_HIT_REPLAY`/`SL_HIT_REPLAY` logic in resolver at lines 565-610)
- **Mark 2026-06-04 backfill rows as `forward_test_only` = false** (per memory: `bootstrap_forward_stats.json` had this issue, ~39,418 rows affected)
- **Audit the backfill script** `tools/backfill_closed_at.py` or equivalent to understand how this happened

### 4b. Resolver Fix (P0)
- Per swarm review consensus: rewrite `outcome_resolver.py` to do true OHLCV replay as the default
- Add `tp_fill_method = INTRABAR_ACTUAL` as the new default
- Mark `NOMINAL_TP_LEGACY` as deprecated

### 4c. After Both Fixes
- Re-run `tools/validate_intrabar_fills.py` on the 4 CRYPTO sleeves
- Re-filter non-CRYPTO candidates using both intrabar and batch-artifact gates
- Find the actual edges (if any)
- Design a new paper-pilot cohort with sleeves that survive BOTH gates

### 4d. Operator Decision Required
- **Pause all real-money deployment work** until P0 fixes are complete
- This is the 2nd time in 2 days we've found fake edges (Cloud-Minimix VRP "VALIDATED" was the 1st)
- Consider commissioning an **independent data audit** to verify the entire trading_picks dataset

---

## 5. The Honest Conclusion

> **We don't have real-money picks because the data is contaminated. We need to fix the data before we can find edges.**

The CRYPTO paper-pilot spec was based on numbers that didn't survive scrutiny. The non-CRYPTO data is even worse — every "good" strategy is a backfill artifact.

This is **good news** in a way: the validation tools work. They caught the fabrications before any money was risked. But it means **the forward path is now a data-quality project, not a deployment project**.

---

## v3 STATUS: NO REAL-MONEY CANDIDATES — DATA QUALITY BLOCKER
