---
tags: [asset-class, CRYPTO]
created: 2026-06-06
status: sub-T2
---

# CRYPTO

## Current Status (2026-06-06)

| Metric | Value |
|--------|-------|
| PF (class-level) | 1.14 |
| WR | 43% |
| n (closed) | 728 |
| Tier | sub-T2 |

> Class-level numbers are lagging. Only `mega_mutation` sub-strategy is T1.

## Confirmed Strategies

- [[strategies/mega_mutation]] — T1 (PF 2.86 / WR 63.9% / n=204, **sole confirmed T1**)

## Candidates

- RENDER_ensemble — T2 shape (n=30, needs n→100)

## Known Issues

- 90d raw DB: 39% WR / PF 0.37 — 4 leakage signals (1864 duplicate signal-ts groups, EXPIRED→WON mislabels, 91.7% concentration in `claude_gainer_st`)
- `claude_gainer_st` has only 3 closed rows in raw DB — flagged on live page since commit `c1b977997`
- last10_WR on mega_mutation dropped to 20% — monitor recency panel
- 0 closed in 48h window (322 still active as of 2026-06-05)

## Banned Sources

See [[reference/banned-sources]] — several CRYPTO sources banned after PF<1 verified.

## Blocker

[[incidents/resolver-intrabar-blocker]] — 4 sleeves (JUP/ENA/ADA/DYDX) blocked at Stage 0.
