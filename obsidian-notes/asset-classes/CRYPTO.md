---
tags: [asset-class, CRYPTO]
created: 2026-06-06
status: fail-unverified
---

# CRYPTO

## Current Status (2026-06-09 — clean cohort + intrabar replay)

| Layer | n | WR | PF | Notes |
|-------|---|-----|-----|-------|
| **Clean cohort** (artifact filters) | 1773 | 46.6% | 1.25 | `reports/OBS_FINDING_JUNE8.MD` |
| **Intrabar replay** (15,021 picks) | — | 39.7% true WR | — | orig 47.1% → 21.9% TP→SL reclass; `reresolve_intrabar_latest.json` |
| **money_ready Tier-2** | — | — | — | **0/9 pass** (2026-06-08 verdict) |

> **No confirmed money-ready edge.** Prior T1 claim for `mega_mutation` is **disputed** until intrabar + clean cohort both pass n≥100 at Tier-2.

## Prior Status (2026-06-06 — superseded)

| Metric | Value |
|--------|-------|
| PF (class-level) | 1.14 |
| WR | 43% |
| n (closed) | 728 |
| Tier | sub-T2 |

> Class-level numbers are lagging. ~~Only `mega_mutation` sub-strategy is T1.~~ **Retracted 2026-06-09.**

## Confirmed Strategies

- ~~[[strategies/mega_mutation]] — T1 (PF 2.86 / WR 63.9% / n=204)~~ → **UNCONFIRMED** pending intrabar apply + forward pilot

## Candidates (intrabar screen — sanity PF≤10, n≥30)

- `cg_whale_divergence` — n=215, true WR 69.8%, PF 3.8 (verify feed bugs / concentration)
- `copy_pm_justdance` — n=485, true WR 54%, PF 1.88
- `pm_whale_0xa2f1fe` — n=275, true WR 54.2%, PF 1.97

**None promoted to money-ready without 4-week forward pilot.**

## Legacy Candidates (pre-intrabar)

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
