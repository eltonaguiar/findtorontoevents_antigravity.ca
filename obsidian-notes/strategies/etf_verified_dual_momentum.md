---
tags: [strategy, asset-class/ETF]
created: 2026-06-06
status: paper-pilot
tier: lab-T2
---

# etf_verified_dual_momentum

## Stats

| Metric | Value | Source |
|--------|-------|--------|
| PF | 1.60 | lab backtest |
| WR | 50% | |
| n (closed, lab) | small | |
| Tier | lab-T2 (INSUFF-N live) | |

## Paper Pilot

- **Started:** 2026-06-02
- **Cron:** daily 06:15Z
- **Walk-forward:** PASS
- **Sidecar flags:** all OFF
- **PRs:** #434 + #414

## Admissibility Checklist

- [x] Walk-forward PASS
- [x] Daily cron wired
- [ ] n≥150 (OOS_READY threshold)
- [ ] Maintain PF≥1.3

## Related

- [[asset-classes/ETF]]
- [[sessions/2026-06-02-etf-pilot-day1]]
- [[reference/performance-tiers]]
