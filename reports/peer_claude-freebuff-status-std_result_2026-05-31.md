# Status Standardization Result — trading_picks legacy → canonical

**Date:** 2026-05-31
**Task:** Standardize 185 legacy statuses (WON / CLOSED_SL / CLOSED_TP / FLAT)
**DB:** `ejaguiar1_stocks.trading_picks`
**Outcome:** **ABORTED — no UPDATE issued**
**Return code:** `ABORTED:WON_exit_reason_ambiguous_185_rows_NEEDS_USER`

## Why ABORTED

The disambiguation rules in the task spec require an exit_reason that
explicitly says `TP_HIT`, `TIME_EXIT`, or `EXPIRED` to safely map a WON row.
All 185 WON rows carry one of two reasons, **neither of which matches**:

| exit_reason                       | count | matches a rule? |
|-----------------------------------|-------|-----------------|
| `RECONCILED_POSITIVE_PNL`         | 162   | no              |
| `PRICE_RESOLVED [RECO [FIX] (RE`  | 23    | no (also truncated/corrupted) |

Per the spec: *"If exit_reason is NULL/empty: skip the row (don't guess) —
drop into 'needs operator review' list."* Strict reading → skip all 185.

Supplementary evidence (TP-fill check) confirms guessing would be unsafe:
only 38/185 rows show `exit_price >= take_profit`; the other 147 closed
positive but **below** TP, which is consistent with TIME_EXIT@positive-PnL
rather than TP_HIT.

## Pre-counts (LIVE)

```
WON: 185 | CLOSED_SL: 0 | CLOSED_TP: 0 | FLAT: 0 | TOTAL: 185
```

## Post-counts (UNCHANGED — no mutation)

```sql
SELECT status, COUNT(*) FROM trading_picks
WHERE status IN ('WON','CLOSED_SL','CLOSED_TP','FLAT')
GROUP BY status;
-- WON: 185 | CLOSED_SL: 0 | CLOSED_TP: 0 | FLAT: 0
```

## Mutations applied

| rule                            | rows updated |
|---------------------------------|--------------|
| CLOSED_SL → SL_HIT              | 0            |
| CLOSED_TP → TP_HIT              | 0            |
| FLAT → TIME_EXIT (FLAT_AT_EXIT) | 0            |
| WON → TP_HIT (by exit_reason)   | 0            |
| WON → TIME_EXIT (by exit_reason)| 0            |
| WON → SKIP (NEEDS_USER)         | 185          |
| **TOTAL UPDATEs**               | **0**        |

Safety cap (≤250) not engaged.

## Backup

185 rows snapshotted before any decision:

- DB: `ejaguiar1_backups.trading_picks_pre_status_std_20260531` (verified 185 rows)
- JSON: `reports/trading_picks_pre_status_std_20260531.json`

## Sample of 5 rows flagged for operator review

| id | symbol | direction | exit_reason | pnl_pct | exit_price | take_profit | exit_price≥TP? |
|---|---|---|---|---|---|---|---|
| `::ATOM-USD::2026-05-27`  | ATOM-USD  | LONG  | RECONCILED_POSITIVE_PNL | 3.9480 | 2.23800056 | 2.23912012 | NO (TIME_EXIT?) |
| `::INJ-USD::2026-05-29`   | INJ-USD   | LONG  | RECONCILED_POSITIVE_PNL | 3.9480 | 6.28885420 | 6.29200020 | NO (TIME_EXIT?) |
| `::NEAR-USD::2026-05-27`  | NEAR-USD  | LONG  | RECONCILED_POSITIVE_PNL | 3.9480 | 2.55816024 | 2.55943996 | NO (TIME_EXIT?) |
| `::RNDR-USD::2026-05-27`  | RNDR-USD  | LONG  | RECONCILED_POSITIVE_PNL | 4.0000 | 2.31399990 | 2.31399990 | **YES** (TP_HIT) |
| `06cffd73-42cd-4a5b-8b15-6658f9a6c6e8` | SPY | LONG | RECONCILED_POSITIVE_PNL | 1.2438 | 750.46997070 | 756.07500000 | NO (TIME_EXIT?) |

Every sample is sub-TP except RNDR-USD, which lands exactly at the TP price —
a strong but not definitive TP_HIT signal.

## Recommended next step (NEEDS_USER)

Pick one of:

1. **Side-aware comparator pre-count.** Build pre-counts under the rule
   `LONG: exit_price>=take_profit → TP_HIT, else TIME_EXIT` and the mirror
   for SHORT, then re-evaluate.
2. **Re-run the resolver.** Re-execute `alpha_engine/outcome_resolver.py` over
   these 185 picks (v2.1 post-bug-bundle) and let it emit canonical statuses
   + clean exit_reasons. This also clears the truncated
   `PRICE_RESOLVED [RECO [FIX] (RE` artifact.

Either way, restore source-of-truth from `ejaguiar1_backups.trading_picks_pre_status_std_20260531`
if anything goes wrong.

## Related

- freebuff DB health audit (post PR #193 / 44 pnl_status_mismatch fixed)
- `reports/peer_claude-freebuff-status-std_plan_2026-05-31.md`
- Out-of-scope but observed: `LOST` is also non-canonical in `trading_picks.status`
  and not in the freebuff "185" cohort. Worth a separate follow-up audit.
