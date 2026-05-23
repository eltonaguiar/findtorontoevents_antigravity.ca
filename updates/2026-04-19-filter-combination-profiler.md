# Filter Combination Profiler Report
## Date: 2026-04-19
## Dataset: alpha_engine/data/closed_picks.json (4,503 records)

---

## Executive Summary

This report profiles the empirical performance of specific score/filter combinations using the full historical closed-picks dataset. **Critical data limitations were discovered** that prevent several requested combinations from being tested:

- **`elite_score` max = 63.0** in closed picks (not 100). Any filter requiring `elite_score > 70/80/90` returns **n = 0**.
- **`ml_composite_score` max = 63.0** (same scale as elite_score).
- **`forward_wr` only overlaps with score fields on 11 records**, making combined forward-track + score filters nearly impossible to evaluate.
- **Crypto picks (467 records) lack grade fields** — 462 of 467 have `None` for `elite_grade` and `method_a_grade`.
- **`confluence_score` is always exactly 1.0** for the 466 records that have it (never >= 2).
- **`confidence` max = 0.88**, so `confidence > 0.80` is at the extreme edge of the distribution.

These limitations are documented in the "Untestable Claims" section at the end of this report.

---

## Results Table

| # | Filter Combination | Proxy / Filter Used | n | Win Rate | Profit Factor | Avg PnL/Trade | Total PnL |
|---|-------------------|---------------------|---|----------|---------------|---------------|-----------|
| 1 | track > 70% + score > 80 | Proxied as: forward_wr > 0.70 AND elite_score > 80 | 0 | — | — | — | — |
| 2 | track > 70% + score > 90 | Proxied as: forward_wr > 0.70 AND elite_score > 90 | 0 | — | — | — | — |
| 3a | AGV > 80 + score = 100 + trust > 7 (closest proxy) | Proxied as: elite_score > 80 (AGV, score=100, and trust fields all unavailable) | 0 | — | — | — | — |
| 3b | Near-perfect score proxy | Proxied as: elite_score >= 95 | 0 | — | — | — | — |
| 4a | smart picks + score > 100 (elite_score proxy) | Proxied as: elite_score > 80 (no smart_score in closed data) | 0 | — | — | — | — |
| 4b | smart picks + score > 100 (ml_composite proxy) | Proxied as: ml_composite_score > 80 (no smart_score in closed data) | 0 | — | — | — | — |
| 5a | crypto high-grade (elite_grade) | Proxied as: category == 'crypto' AND elite_grade IN ('A','S','A+','S+') | 0 | — | — | — | — |
| 5b | crypto high-grade (method_a_grade) | Proxied as: category == 'crypto' AND method_a_grade IN ('A','B') | 0 | — | — | — | — |
| 6 | High confidence + high score | Proxied as: confidence > 0.80 AND elite_score > 70 | 0 | — | — | — | — |
| 7 | High confluence | Filter: confluence_score >= 2 | 0 | — | — | — | — |
| 8 | Low R:R + high confidence | Filter: risk_reward < 1.5 AND confidence > 0.75 | 48 | 68.8% | 4.96 | 0.04% | 1.97% |
| 9 | High R:R + high confidence | Filter: risk_reward >= 2.0 AND confidence > 0.75 | 36 | 55.6% | 0.66 | -0.07% | -2.38% |
| Ref A | confluence_score >= 1 (reference baseline) | All records with any confluence_score value | 466 | 54.3% | 0.50 | -0.03% | -13.70% |
| Ref B | All closed picks (universal baseline) | Full dataset of 4,503 closed picks | 4,503 | 31.5% | 0.40 | -0.15% | -666.59% |

---

## Key Findings

### Testable Combinations That Produced Results

**8. Low R:R + high confidence** (`risk_reward < 1.5 AND confidence > 0.75`)
- **n = 48**, Win Rate = **68.8%**, Profit Factor = **4.96**
- This is the only combination that shows strong positive edge in closed data.
- Avg PnL per trade is modest (+0.04%) but consistent, suggesting a high-probability, low-edge profile.

**9. High R:R + high confidence** (`risk_reward >= 2.0 AND confidence > 0.75`)
- **n = 36**, Win Rate = **55.6%**, Profit Factor = **0.66**
- Underperforms relative to the low R:R cohort, with negative average and total PnL.

**Reference A. confluence_score >= 1**
- **n = 466**, Win Rate = **54.3%**, Profit Factor = **0.50**
- Despite a >50% win rate, the Profit Factor is poor (0.50) because losses are larger than wins on average.

**Reference B. All closed picks**
- **n = 4,503**, Win Rate = **31.5%**, Profit Factor = **0.40**, Avg PnL = **−0.15%**, Total PnL = **−666.6%**
- The overall dataset is slightly loss-making, which makes the low-R:R high-confidence filter (Test 8) stand out as a genuine positive outlier.

---

## Untestable Claims

The following combinations **cannot be verified** on the historical closed-picks dataset due to missing or capped fields:

| Claim | Why It's Untestable | What Was Tested Instead |
|-------|---------------------|-------------------------|
| **3. "AGV > 80 + score = 100 + trust > 7"** | Fields `agv_score`, `score = 100`, and `trust_score` do not exist in closed picks. | `elite_score > 80` and `elite_score >= 95` — both returned **n = 0** because `elite_score` max = 63.0. |
| **4. "smart picks + score > 100"** | `smart_score` is absent from closed picks. `score > 100` exceeds the max of both `elite_score` (63) and `ml_composite_score` (63). | `elite_score > 80` and `ml_composite_score > 80` — both returned **n = 0**. |
| **5. "crypto high-grade"** | 462 of 467 crypto records have `None` for `elite_grade` and `method_a_grade`. Only 5 crypto records have any score at all. | Tests on the tiny non-null subset returned **n = 0** because available grades were F/D/C. |
| **1 & 2. "track > 70% + score > 80/90"** | While `forward_wr` exists, it overlaps with `elite_score` on only **11 records** worldwide, and none have `elite_score > 80`. | Exact proxy filters returned **n = 0**. |
| **6. "confidence > 0.80 AND elite_score > 70"** | `elite_score` never exceeds 63, so the intersection is empty. | Exact proxy returned **n = 0**. |
| **7. "confluence_score >= 2"** | `confluence_score` is always exactly 1.0 for the 466 records that carry the field. | `confluence_score >= 1` was tested as a baseline instead. |

---

## Data Limitations Summary

| Field | Availability / Range | Impact |
|-------|----------------------|--------|
| `elite_score` | 3,942 records, range 0–63 | Cannot test any threshold > 63. |
| `ml_composite_score` | 3,942 records, range 0–63 | Same scale limitation as elite_score. |
| `method_a_score` | 3,942 records, range 4–100 | **Usable** for high-score filters (> 80 works). |
| `forward_wr` | 473 records | Very sparse; cross-filtered combinations usually fail. |
| `confidence` | 4,404 records, range 0.40–0.88 | > 0.80 is at the extreme tail. |
| `confluence_score` | 466 records, all = 1.0 | Cannot test >= 2. |
| `elite_grade` (crypto) | 5 of 467 records | Effectively missing for crypto. |
| `method_a_grade` (crypto) | 5 of 467 records | Effectively missing for crypto. |

---

## Bottom Line

Out of the nine requested filter combinations, **only three (Tests 7, 8, and 9) were mechanically testable** on the closed historical dataset, and only **Tests 8 and 9 returned non-zero sample sizes**. 

The standout empirical result is:
> **Low R:R + high confidence** (`risk_reward < 1.5` + `confidence > 0.75`) — 48 trades, 68.8% win rate, 4.96 profit factor.

All score-based filters relying on `elite_score > 80/90/100` are **not reproducible** on closed picks because the `elite_score` distribution tops out at 63. If these filters are meant to represent real operational logic, the scoring system used in production today differs materially from the scale captured in historical closed data.

*Report generated from alpha_engine/data/closed_picks.json (n = 4,503).*
