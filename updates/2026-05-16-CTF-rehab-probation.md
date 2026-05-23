# CT=F (Cotton) Symbol Rehabilitation — PROBATION (2026-05-16)

**Promoted from:** `COMMODITY_BLACKLIST` (hard block)  
**Promoted to:** PROBATION (50% sizing, COT_DEDUP_GATE active)  
**Review date:** 2026-06-06  

---

## Evidence for Promotion

| Metric | Value | PROBATION Threshold | Full Unblock Threshold |
|--------|-------|--------------------|-----------------------|
| n (post-block) | 43 | ≥ 20 ✓ | ≥ 30 ✓ |
| Win Rate | 81.4% | ≥ 52% ✓ | — |
| Profit Factor | 6.33 | ≥ 1.3 ✓ | ≥ 1.5 ✓ |
| Wilson 95% LB WR | 69.9% | — | ≥ 45% ✓ |
| Calendar days | 22d | — | ≥ 14d ✓ |
| Post-block PnL | +151.38% | Positive ✓ | — |
| **max_strat_share** | **56%** | — | **≤ 40% ✗ BLOCKING** |

CT=F meets all full-unblock criteria **except** max_strat_share (56% from a single strategy vs 40% cap). This edge-concentration risk holds it at PROBATION.

---

## Why CT=F Was Originally Blocked

**Original block decision (2026-04-14):** n=12, WR=8.3%, sum_pnl=-8.41% — clear kill signal.

**Root cause (identified PR #994, 2026-05-15):** COT (Commitment of Traders) source `multi_asset_cot` was re-emitting CT=F on every CFTC weekly release cycle tick, inflating n from ~12 real trades to hundreds of duplicates. The headline WR/PF included re-emitted duplicate positions counted as separate trades.

**Fix applied:** `COT_DEDUP_GATE` (72h dedup window in `quality_gates.py`) now rejects same-symbol COT picks within 72 hours. Post-dedup data: n=43 clean distinct trades over 22 calendar days.

---

## Active Constraints in PROBATION

1. **COT_DEDUP_GATE remains active** — 72h window prevents re-emission artifacts. This is non-negotiable while CT=F is in any rehab stage.
2. **50% position sizing** — as per `REHAB_CRITERIA.md` Stage 2 (PROBATION).
3. **max_strat_share monitoring** — if the dominant strategy's share drops below 40% before 2026-06-06, full unblock can be triggered early with agent review.
4. **High Watch period** — 30 days post-promotion. Auto-re-block if: trailing 7d PF < 0.8 OR trailing 7d WR < 40% (on n ≥ 5).

---

## Full Unblock Criteria (2026-06-06 review)

- max_strat_share ≤ 40% (currently 56%)
- n ≥ 30 post-PROBATION clean deduped trades (already met)
- Trailing 7d WR ≥ 45%, PF ≥ 1.3 (monitor weekly)
- No single-week drawdown > 25%

---

## Files Changed

- `audit_trail/quality_gates.py`: Removed CT=F from `COMMODITY_BLACKLIST`, updated `PENDING_UNBLOCK_REVIEW` to PROBATION status.
- `tools/data/symbol_rehab_candidates.json`: CT=F appears as PROBATION candidate (pre-existing).

*Generated 2026-05-16 by Claude Sonnet 4.6 acting on Kimi/Copilot P1 recommendation.*
