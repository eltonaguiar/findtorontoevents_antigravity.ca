# CT=F (Cotton) Symbol Rehabilitation — PROBATION (2026-05-16)

**Symbol:** CT=F
**Asset Class:** COMMODITY
**Block Reason:** COT over-emission (multiple picks per CFTC release cycle)
**Root Cause Fix:** PR-#994 COT dedup (`COT_DEDUP_GATE` with 72h window)

---

## Promotion Criteria Met

| Metric | Value | PROBATION Threshold | Met |
|--------|-------|---------------------|-----|
| n (post-block) | 43 | ≥ 20 | ✓ |
| Win Rate | 81.4% | ≥ 52% | ✓ |
| Profit Factor | 6.33 | ≥ 1.3 | ✓ |
| Wilson 95% LB WR | 70.0% | — | ✓ |

---

## PROBATION Window

**2026-05-16 → 2026-05-30**

During PROBATION, CT=F is eligible for reduced-size live picks (50% sizing).
The `COT_DEDUP_GATE` (72h) remains active to prevent re-emission artifacts.

---

## Reblock Triggers

- WR < 50% on n ≥ 20 during PROBATION
- Trailing 7d PF < 0.8
- Trailing 7d WR < 40% (on n ≥ 5)
- Single-week drawdown > 25%

---

## Full Unblock Criteria

- n ≥ 30 post-PROBATION clean deduped trades (already met)
- max_strat_share ≤ 40% (currently 56% — blocking item)
- Trailing 7d WR ≥ 45%, PF ≥ 1.3 (monitor weekly)
- No single-week drawdown > 25%
- Wilson 95% LB ≥ 45%

---

## Files Changed

- `audit_trail/quality_gates.py`: Added `PROBATION_STATUS`, removed CT=F from `PENDING_UNBLOCK_REVIEW`, added `_is_probation_symbol()` helper.
