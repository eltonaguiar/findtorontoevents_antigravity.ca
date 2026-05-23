# multi_asset_copytrader FOREX Investigation — 2026-05-17

**Protocol:** `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` + `docs/MUTATION_THREE_AXIS_PROTOCOL.md`  
**Action:** Direction block LONG only (SHORT shows edge, kept)  
**Ticket:** M-063 (MASTER_ACTION_PLAN_2026-05-15.md §23.2)

## Aggregate Performance (FOREX only)

| Metric | Value |
|---|---|
| Total FOREX picks | 696 |
| WR | 16.5% |
| PF | 0.229 |
| Total PnL | −2.27% |

This is catastrophically below charter T3 floor (PF>1.0).

## Axis 1 — Direction Autopsy

| Direction | n | WR | PF | Verdict |
|---|---|---|---|---|
| LONG | 603 | 10.9% | 0.140 | **BLOCK** |
| SHORT | 93 | 52.7% | 1.351 | Watch (sub-T2 PF but positive edge) |

LONG drives 87% of volume and is the overwhelmingly dominant drag. SHORT shows real edge —
block LONG only, keep SHORT.

## Axis 2 — Symbol Autopsy (LONG picks, worst to best)

| Symbol | n | WR | PF | Note |
|---|---|---|---|---|
| EURJPY=X | 154 | 1.9% | 0.025 | JPY cross — worst by volume |
| USDJPY=X | 133 | 3.0% | 0.036 | JPY cross |
| GBPJPY=X | 87 | 10.3% | 0.163 | JPY cross |
| AUDJPY=X | 84 | 3.6% | 0.054 | JPY cross |
| NZDUSD=X | 59 | 15.3% | 0.288 | Non-JPY — moderate, still sub-floor |
| EURGBP=X | 48 | 70.8% | 3.437 | Non-JPY — **T1 edge** |
| CADJPY=X | 41 | 9.8% | 0.125 | JPY cross |
| USDCAD=X | 31 | 35.5% | 0.744 | Non-JPY — marginal |
| GBPUSD=X | 30 | 66.7% | 2.449 | Non-JPY — **T1 edge** |
| AUDUSD=X | 20 | 50.0% | 1.600 | Non-JPY — T2 |

**Root cause:** JPY-cross LONG exposure is the kill mechanism. EURJPY+USDJPY+GBPJPY+AUDJPY+CADJPY
account for ~499 of 603 LONG picks with WR of 1.9–10.3%. The JPY crosses behave differently
from non-JPY pairs — likely a trending momentum strategy being applied to a mean-reverting regime.

## Axis 3 — Confidence Bucket

Not computed separately — all picks use the `multi_asset_copytrader` source_system and confidence
values span 0.55–0.80 per status field. No useful confidence bucket signal beyond the direction split.

## Mutation Decision

**Per MUTATION_THREE_AXIS_PROTOCOL.md Step 5 (winning subset):**
- JPY crosses LONG: 499 picks, WR < 10% — no subset rescues this
- Non-JPY LONG: ~104 picks, WR ≈ 35–40% — marginal; do not unlock until n≥100 and PF≥1.5

**Action taken:**
- `BLOCKED_DIRECTION_TRIPLES`: added `("FOREX", "multi_asset_copytrader", "LONG")`
- SHORT kept unblocked — WR=52.7%/PF=1.351, needs 30+ more days to confirm T2 floor

## Short Direction — Monitoring Plan

SHORT n=93, WR=52.7%, PF=1.351 is below the T2 PF=1.5 charter floor but is positive edge.  
Re-evaluate at n=150 (expected ~2026-06-16) or if PF drops below 1.0.

## Related Actions

- M-062: COT publication-time gate (cot_positioning look-ahead fix) — NOT addressed in this PR
- cta_cross_asset_tsmom FOREX LONG already blocked 2026-05-16 (PR #687)
- FOREX LONG direction blocks: ig_contrarian_sentiment, myfxbook_retail_contrarian, fx_smart_carry_trade_momentum also blocked

## Commit

Direction block committed to `audit_trail/quality_gates.py`. Syntax validated (py_compile OK).  
Tests: 463 passed, 6 skipped.
