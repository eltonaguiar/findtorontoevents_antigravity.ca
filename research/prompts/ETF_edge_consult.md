# ETF edge consult

## Mechanism under test
ETF creation/redemption flow. When shares outstanding jump, authorized
participants are creating units to meet demand. The hypothesis is that
creation-flow z-score (30-day rolling, strictly past observations) predicts
forward ETF returns cross-sectionally. Implementation exists as ET-1 in
`tools/et1_etf_creation_redemption_research.py`.

## Measured evidence so far (trading_picks, 2026-11-22)
- n = 79 closed rows, gross PF 1.5737, net PF 1.4974 at class cost 0.05 pct
- 2x-cost net PF 1.4256  <-- the only class in the whole 12-class sweep above 1 at double cost
- bootstrap CI lower bound on net mean: -0.2660  (so the mean is NOT distinguishable from zero)
- split halves: +0.9892 / -0.0885  (second half negative)
- top symbol QQQ with 14 rows; 6+ different source systems; 27 rows have NULL created_at
- walk-forward: 0 folds (n too small for a purged split)

## Specific question
1. Is ETF creation/redemption flow a documented, non-arbitraged predictor of
   ETF returns, or is it mostly mechanical (index rebalancing, in-kind
   conversions) and therefore not an edge?
2. What is the minimum number of independent ETF observations before a
   cross-sectional flow signal is credible? Justify a number.
3. The second half is negative while the first half is strongly positive. What
   are the most likely explanations, and what single test separates them?
4. At 5bp cost the gross edge nearly survives; name the extra real-world costs
   (borrow, spread, market impact for the ETF itself) that the 5bp misses.

## Constraint
Every answer must name a falsifiable test. Do not assert an edge exists.
