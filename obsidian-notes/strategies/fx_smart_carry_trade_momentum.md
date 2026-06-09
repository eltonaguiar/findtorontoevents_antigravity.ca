---
tags: [strategy, asset-class/FOREX]
created: 2026-06-06
status: candidate
tier: T2-candidate
---

# fx_smart_carry_trade_momentum

## Stats (2026-06-05, OOS-robust)

| Metric | Value | Source |
|--------|-------|--------|
| PF | 1.85 | pf_registry OOS |
| WR | TBD | |
| n (closed) | 25 | live DB |
| Tier | T2-candidate | |
| n→100 ETA | ~5-6 weeks | |

## OOS / Walk-Forward

- [x] OOS-robust confirmed
- [ ] Walk-forward formal PASS
- [ ] n≥100 (ETA 5-6 weeks)
- [ ] Intrabar fill validated

## Notes

Lead T2 candidate for FOREX. Current n=25 is below the 100-trade admissibility floor, but OOS metrics are clean.

## Related

- [[asset-classes/FOREX]]
- [[reference/performance-tiers]]
