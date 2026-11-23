# Incubator output defects (alpha_engine/data/incubator_paper_ready.json)

**Date:** 2026-11-23T04:15Z · **Author:** Kilo · Paper only. **Not patched in production — reported with the exact fix.**

## Defects (measured by `tools/validate_incubator.py` → `reports/incubator_validated.json`)
From 4,987 permutations / 24,935 backtests → 20 "paper-ready":
1. **No `n` on any row** → DSR is undefined; a "paper-ready" strategy cannot be admitted to audit3 without a sample size.
2. **16 duplicate rows** (e.g. three identical `cross_sectional_momentum` at Sharpe 4.08 / PF 2.056) → dedup missing.
3. **`best_sharpe: 9248.977`** in the summary → a computation bug (near-zero variance), so the Sharpe column is untrustworthy.

**Validator verdict: 0/20 admissible as-is.**

## Where it is generated
`alpha_engine/incubator/run_incubator.py` → `db.get_paper_ready()` (`alpha_engine/incubator/incubator_db.py`);
metrics `combined_sharpe`, `combined_pf`, `composite_score` come from the DB. The `n`/`n_trades` field is never written.

## Required fix (for the owner — not applied here to avoid a blind production change)
1. Persist `n_trades` (and `n_backtests` for that permutation) on every paper-ready row.
2. Dedup on `(archetype, rounded(combined_sharpe,2), rounded(combined_pf,2))` before export.
3. Guard the Sharpe: reject `abs(sharpe) > 10` as a variance bug (fix the denominator), never export it.
4. Gate promotion: only export paper-ready if `n_trades >= 30` AND DSR at the honest permutation count (N=4,987)
   is `>= 0.95`. At N=4,987 the bar is high by construction — which is the point.
5. Call `tools/validate_incubator.py` (or its logic) as the last step; refuse to write the file if 0 pass.

Until then, no incubator row should enter audit3 as a pod.

*Paper only. Not investment advice.*
