---
tags: [asset-class, FOREX]
created: 2026-06-06
status: fail
---

# FOREX

## Current Status (2026-06-09 — clean cohort)

| Metric | Value |
|--------|-------|
| PF (clean) | 0.63 |
| WR (clean) | 8.5% |
| n (clean closed) | 117 |
| 14d clean WR | **5.0%** |
| Tier | **FAIL** |

> **Refuted:** Copilot/session claim of FOREX 14d 64.2% WR / PF 2.43 and GBPUSD n=114 WR 58.8%. See `reports/OBS_FINDING_JUNE8.MD`.

## Prior Status (2026-06-06 — superseded)

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
