# PEER_REVIEW R2 — Index (2026-11-14)

Round-2 peer review: reviews of the peers' master-plan / proposed-fixes / cross-ref work that appeared after the first review round.

## Folder structure

```
PEER_REVIEW_R2/
  00_INDEX.md
  overall/
    PEER_REVIEW_R2_OVERALL.md        <- consolidated consensus + master-plan adjustments
    PEER_REVIEW_V4.md                <- finpredict-v4 archive
    PEER_REVIEW_V1_MASTERPLAN.md     <- finpredict v1 master-plan input set
    PEER_REVIEW_V2.md                <- finpredict-v2 (reconciliation backbone)
    PEER_REVIEW_ML_AUDIT.md          <- ML-audit childlike-airport proposed fixes
    PEER_REVIEW_SCRATCH.md           <- scratch-hippodraco quick-wins
    PEER_REVIEW_SEER.md              <- hilarious-seer quick-wins
```

## Summary

- **All 6 peers agree** on the core problems (frozen 0% PnL, zombies, survivorship, multiple-testing, 0/9 money-ready, backtest↔forward disconnect).
- **Highest-value first fixes** (multi-peer): PnL-unit contract; NULL-tombstone zombie drain.
- **Backbone:** adopt v2 (reconciliation). **Checklist:** scratch QW-ALL-1..9. **Merge after fixes:** v1 master-plan. **Red-line:** ML-audit destructive SQL + mutual-fund stub scanner.
- **Keep the rigor gate:** no "solid" claim until the horizon harness passes.
