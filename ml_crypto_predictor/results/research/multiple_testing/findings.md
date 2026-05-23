# multiple_testing_researcher — BH-FDR over source-systems

_Generated: 2026-05-02T04:02:15.958373+00:00_

**Question:** mt_001 — How many sources survive 5%-FDR?

**Result:** 1/6 survive.

| Source | n | PF | Mean PnL | p | BH 5% |
|---|---|---|---|---|---|
| multi_asset_cot | 41 | 8.029 | +0.0353% | 0.0000 | **OK** |
| cta_replicator | 83 | 0.813 | -0.0003% | 0.7117 | FAIL |
| multi_asset_copytrader | 412 | 0.787 | -0.0015% | 0.9420 | FAIL |
| unknown | 782 | 0.643 | -0.0198% | 0.9973 | FAIL |
| rapid_fire | 207 | 0.158 | -0.2209% | 1.0000 | FAIL |
| quan_engine | 5896 | 0.411 | -0.1689% | 1.0000 | FAIL |

**Wire-up:** add `requires_bh_fdr_clearance` flag to `alpha_engine/anti_overfit_validator.py` consuming `statistical_rigor.benjamini_hochberg`.

