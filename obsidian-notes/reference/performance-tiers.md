---
tags: [reference]
created: 2026-06-06
---

# Performance Tiers

Source: `reports/hedge_fund_performance_review_*.md`

| Tier | Label | PF | WR | MDD |
|------|-------|----|----|-----|
| T1 | Renaissance | >2.0 | >55% | <10% |
| T2 | Hedge Fund | >1.5 | >50% | <20% |
| T3 | Retail-grade | >1.2 | >45% | <35% |
| Fail | | <1.2 | — | — |

## Rules

- **T2 minimum** to size up any class
- **T1** is the long-run target
- Never promote to T2 without n≥100 clean (post-noise-filter) trades
- Always verify 14d/48h panels before acting on historical numbers
- Concentration gate must be enforced before DSR/SPA (open P0 since 2026-05-17)

## Current Status (2026-06-06)

| Class | PF | WR | n | Tier |
|-------|----|----|---|------|
| CRYPTO | 1.14 | 43% | 728 | sub-T2 |
| EQUITY | 0.90 | 33% | 33 | FAIL |
| COMMODITY | 0.31 | 11% | 28 | FAIL |
| ETF | 11.99 | 50% | 2 | INSUFF-N |
| FOREX | 0.55 | 40% | 53 | FAIL |
| BOND | 0 | 0% | 8 | INSUFF-N |

> mega_mutation (CRYPTO sub-strategy) is the **only confirmed T1** (PF 2.86, n=204).
