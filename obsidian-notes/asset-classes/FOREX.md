---
tags: [asset-class, FOREX]
created: 2026-06-06
status: fail
---

# FOREX

## Current Status (2026-06-06)

| Metric | Value |
|--------|-------|
| PF | 0.55 |
| WR | 40% |
| n (closed) | 53 |
| Tier | FAIL |
| Concentration | USDJPY 55% |

## T2 Candidate

- [[strategies/fx_smart_carry_trade_momentum]] — PF 1.85 / n=25 OOS-robust; n→100 ~5-6 weeks

## Known Issues

- USDJPY 55% concentration → failing concentration gate
- Post-resolver-fix data is trustworthy (v2 + v2.1 bug bundle 2026-05-02)
- Pre-fix data in `by_asset_class` (raw); use `asset_class_health` for verdict-grade numbers
- INCIDENT_FOREX#7 open

## References

- `reports/action_B_resolver_2026_04_27.md`
- `feedback_noncrypto_resolver_live_close_bug.md`
