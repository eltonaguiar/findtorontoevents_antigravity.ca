# `confidence` Feature — Sliced Diagnosis

**Hypothesis:** the -0.087 global correlation between `confidence` and WIN is not a
code bug (no `confidence = 1 - X` patterns exist in `alpha_engine/`). It's structural.
Question: does the sign FLIP in specific slices (source_system, asset_class, direction)?


## Global correlation (baseline)

r(confidence, win) = **-0.0866** across 5,135 closed picks.

## By source_system (n >= 80)

| source_system   |    n |     wr |      pf |   r(conf,win) |   r(conf,pnl) |   mean_conf |
|:----------------|-----:|-------:|--------:|--------------:|--------------:|------------:|
| quan_engine     | 4998 | 0.2975 | 0.39224 |       -0.0866 |        0.0542 |      0.6322 |

## By asset_class (n >= 80)

| asset_class   | n   | wr   | pf   | r(conf,win)   | r(conf,pnl)   | mean_conf   |
|---------------|-----|------|------|---------------|---------------|-------------|

## By signal_type direction (n >= 80)

| signal_type   |    n |     wr |       pf |   r(conf,win) |   r(conf,pnl) |   mean_conf |
|:--------------|-----:|-------:|---------:|--------------:|--------------:|------------:|
| LONG          | 4568 | 0.2824 | 0.378414 |       -0.0674 |        0.0795 |      0.6348 |
| SHORT         |  403 | 0.4541 | 0.455453 |       -0.0345 |       -0.0243 |      0.6062 |

## By strategy (top 12 by n, min_n=40)

| strategy          |    n |     wr |       pf |   r(conf,win) |   r(conf,pnl) |   mean_conf |
|:------------------|-----:|-------:|---------:|--------------:|--------------:|------------:|
| quan_engine_scalp | 4836 | 0.2984 | 0.385114 |       -0.0822 |        0.0687 |      0.6326 |
| quan_engine_swing |  109 | 0.2752 | 0.994682 |        0.1075 |        0.0944 |      0.6253 |

## Confidence bucket vs outcome

| bucket    |    n |       wr |         pf |   mean_pnl_pct |
|:----------|-----:|---------:|-----------:|---------------:|
| <0.50     |   15 |   0.0667 |   0.417913 |        -0.0794 |
| 0.50-0.60 | 1422 |   0.3636 |   0.421857 |        -0.1899 |
| 0.60-0.70 | 3212 |   0.2559 |   0.352575 |        -0.1629 |
| 0.70-0.80 |  348 |   0.4195 |   0.571177 |        -0.1251 |
| 0.80-0.90 |    1 | nan      | nan        |       nan      |