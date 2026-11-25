# PBO block-length sensitivity and White's Reality Check — 2026-11-22

Matrix: **39 cells x 5157 union rows**, common window **1478 days** (2021-01-04 → 2026-11-20).

## Item 26 — is PBO = 0.345 an artefact of s = 16?

| s_blocks | block length (days) | PBO, harness convention (NaN=0) | PBO, common window |
|---|---|---|---|
| 8 | 644.6 | 0.35 | 0.57 |
| 16 | 322.3 | 0.345 | 0.535 |
| 24 | 214.9 | 0.315 | 0.505 |

Reproduction of the frozen scalar: **0.345** → **0.345** (|diff| 0.0) — reproduced.

## Item 27 — does the best cell survive a family-wide search?

| test | statistic | best cell | observed | p | uncorrected p |
|---|---|---|---|---|---|
| Reality Check (raw) | 0.0394 | H-200:NVDA | 10.258 bp/day | 0.4794 | 0.052921 |
| Reality Check (studentised) | 1.803 | H-201 | 5.471 bp/day | 0.5322 | 0.035693 |
| Hansen SPA | 1.803 | H-201 | 5.471 bp/day | 0.5018 | 0.035693 |
| RC, spread-zero diagnostic | 0.0536 | H-200:NVDA | 7.462 bp/day | 0.2232 | 0.001669 |

### Full-history family (34 cells present from 2012-01-03, 3735 days)

The all-cells common window above starts in 2021 only because a few cells start late; this is the same test on the cells that exist for the whole sample.

| test | best cell | observed | p | uncorrected p |
|---|---|---|---|---|
| Reality Check (raw) | H-200:NVDA | 9.444 bp/day | 0.1436 | 0.002846 |
| Reality Check (studentised) | H-201 | 5.512 bp/day | 0.0156 | 0.000777 |
| Hansen SPA | H-201 | 5.512 bp/day | 0.0152 | 0.000777 |

A cell is only evidence of an edge when CI-LB > 0, CI-LB@2x > 0, both halves > 0, DSR >= 0.95, excess-vs-bench > 0, **and** the family-wide p-value clears its threshold. Nothing else counts.
