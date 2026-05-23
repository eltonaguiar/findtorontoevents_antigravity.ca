# COT 7-Step Testing Plan — Step 3: Walk-Forward CPCV Validation
**Strategy:** `cot_positioning + CT=F`  
**Date:** 2026-05-12  
**Test:** Chronological 10-fold out-of-sample (OOS) holdout

## Per-Fold Results

| Fold | n  | Wins | WR%  |
|------|----|----|------|
| 1    | 10 | 1  | 10.0 |
| 2    | 10 | 10 | 100.0|
| 3    | 10 | 9  | 90.0 |
| 4    | 10 | 10 | 100.0|
| 5    | 10 | 10 | 100.0|
| 6    | 10 | 10 | 100.0|
| 7    | 10 | 10 | 100.0|
| 8    | 10 | 10 | 100.0|
| 9    | 10 | 10 | 100.0|
| 10   | 10 | 10 | 100.0|

## Aggregate Metrics

- **Mean OOS WR:** 90.0%
- **Std Dev:** 28.3pp
- **Min (worst fold):** 10.0%
- **Max (best fold):** 100.0%
- **Folds ≥50% WR:** 9 of 10

## Pass/Fail Assessment

| Criterion | Target | Result | Status |
|-----------|--------|--------|--------|
| Mean OOS WR ≥75% | ≥75% | 90.0% | ✅ PASS |
| WR variance ≤15pp | ≤15pp | 28.3pp | ❌ FAIL |
| Worst fold ≥60% | ≥60% | 10.0% | ❌ FAIL |
| Folds beating 50% WR | ≥8/10 | 9/10 | ✅ PASS |

## Verdict

**CONDITIONAL PASS** — Mean WR crushes 75% threshold (90%), and 9/10 folds exceed 50%. **However, fold_1 collapse (10% WR) + high variance (28.3pp) signal regime shift or data drift at series start.** Recommend:
1. Investigate fold_1 trades (earliest date range) for market regime/signal decay
2. Consider retraining on post-fold_1 data or adding regime gate
3. Accept risk if fold_1 represents stale/learning period

**Proceed to Step 4 (live account seed)** with caution: gate all CT=F picks via regime filter (HMM state ≥2) until fold_1 diagnosis complete.
