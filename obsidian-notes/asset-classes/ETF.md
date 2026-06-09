---
tags: [asset-class, ETF]
created: 2026-06-06
status: paper-pilot
---

# ETF

## Current Status (2026-06-06)

| Metric | Value |
|--------|-------|
| PF | 11.99 |
| WR | 50% |
| n (closed) | 2 |
| Tier | INSUFF-N (lab T2 shape) |

> n=2 is not statistically meaningful — PF 11.99 is an artifact of small sample.

## Paper Pilot Active

- [[strategies/etf_verified_dual_momentum]] wired for forward n
- Daily cron: 06:15Z
- Walk-forward: PASS
- Sidecar flags: all OFF

## PRs

- PR #434 + #414 reviewed and merged

## Next

- Reach n≥150 for OOS_READY designation
- Maintain PF≥1.3 as pilot runs
