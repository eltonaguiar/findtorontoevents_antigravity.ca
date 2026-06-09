---
tags: [strategy, asset-class/CRYPTO]
created: 2026-06-06
status: refuted
tier: REFUTED
---

# mega_mutation

> [!danger] T1 claim REFUTED on clean data (2026-06-09)
> The "PF 2.86 / WR 63.9% / n=204" figure is the RAW `trading_picks` cohort (source_system='mega_mutation', 296 rows, **100% NULL created_at**). On the canonical `at_pick_outcomes` clean cohort it is **n=13, 30.8% WR, PF 0.57** — and the only month resolved by the honest v2.2_sync resolver (June) is **4/9 LOST**. The naive-fill subset (65% WR) over-reports vs the intrabar-OBSERVED subset (60.3%), decaying Apr 69%→May 63%→Jun 31%. The per-symbol "ready" picks (NEARUSDT 90.9%, INJUSDT 90.5%, ATOMUSDT 75.8%) are **NOT in the mega_mutation cohort at all** (its symbols are JUP/WIF/AVAX/DOT/RENDER/STX/ENA/ADA) — fabricated/mis-attributed. **Do NOT size real money.** Source: workflow w7x37pkzk, `reports/OBS_FINDING_JUNE8.MD`.

## Stats (2026-06-05, post-dedup)

| Metric | Value | Source |
|--------|-------|--------|
| PF | 2.86 | pf_registry policy-clean |
| WR | 63.9% | live DB verified |
| Sharpe | 8.6 | |
| n (closed) | 204 (deduped from 296 raw) | |
| MDD | TBD | |

## OOS / Walk-Forward

- [x] Walk-forward PASS
- [x] 14d panel checked
- [ ] Intrabar fill validated (blocked — resolver not shipped)
- [x] Verified by 3 independent reviewers (Cursor + 2 subagents)

## Key Events

- **2026-06-05:** 296 raw → 204 dedup (31% dup); `created_at=NULL` was root cause of duplicates
- **2026-06-05:** AVAXUSDT killed (surgical removal by Cursor)
- **Alert:** last10_WR dropped to 20% — monitor recency
- **2026-06-05:** Bootstrap contamination found (`closed_at=NULL` ~95% in forward_stats); mega_mutation is sole confirmed T1

## Blockers

- Intrabar OHLC resolver needed before sizing up → `tools/validate_intrabar_fills.py`
- 4 CRYPTO sleeves (JUP/ENA/ADA + DYDX) blocked at Stage 0

## Related

- [[sessions/2026-06-05-session4-deliverables]]
- [[incidents/resolver-intrabar-blocker]]
- [[asset-classes/CRYPTO]]
