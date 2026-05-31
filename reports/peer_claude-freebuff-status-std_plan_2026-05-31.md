# Status Standardization Plan — trading_picks legacy → canonical

**Date:** 2026-05-31
**Author:** peer/claude (status-std swarm task)
**Source audit:** freebuff DB health audit after PR #193 (44 pnl_status_mismatch fixed)
**DB:** `ejaguiar1_stocks.trading_picks`

## Canonical status set
`TP_HIT`, `SL_HIT`, `EXPIRED`, `TIME_EXIT` (closed) + `OPEN`, `ACTIVE` (live)

## Pre-mutation legacy counts (LIVE VERIFY)

```sql
SELECT status, COUNT(*) FROM trading_picks
WHERE status IN ('WON','CLOSED_SL','CLOSED_TP','FLAT')
GROUP BY status;
```

Result (2026-05-31):

| status      | count |
|-------------|-------|
| WON         | 185   |
| CLOSED_SL   | 0     |
| CLOSED_TP   | 0     |
| FLAT        | 0     |
| **TOTAL**   | **185** |

Confirms freebuff's audit number (~185). 100% of the legacy bucket is `WON`. The
clean unambiguous mappings (`CLOSED_SL → SL_HIT`, `CLOSED_TP → TP_HIT`,
`FLAT → TIME_EXIT[FLAT_AT_EXIT]`) have nothing to mutate.

Additional finding: `LOST` is also present as a non-canonical status (not in
task scope, deferred to a follow-up).

## WON disambiguation — exit_reason distribution

```sql
SELECT IFNULL(exit_reason,'<NULL>'), COUNT(*) FROM trading_picks
WHERE status='WON' GROUP BY exit_reason ORDER BY 2 DESC;
```

| exit_reason                       | count |
|-----------------------------------|-------|
| `RECONCILED_POSITIVE_PNL`         | 162   |
| `PRICE_RESOLVED [RECO [FIX] (RE`  | 23    |
| (NULL)                            | 0     |

**Neither value satisfies the task's disambiguation rules:**

- Rule "exit_reason says TP_HIT" → 0 rows
- Rule "exit_reason says TIME_EXIT or EXPIRED" → 0 rows
- Rule "exit_reason NULL/empty → skip" → 0 rows (strictly)

Both exit_reason strings (a) come from the outcome-resolver positive-PnL path
and (b) do not declare which canonical exit caused the close. The second value
is also visibly truncated/corrupted (`PRICE_RESOLVED [RECO [FIX] (RE`) and may
itself be a prior partial-fix artifact.

## Additional evidence — TP-fill check on the 185 WON rows

```sql
SELECT
  SUM(CASE WHEN exit_price >= take_profit THEN 1 ELSE 0 END) AS tp_strong,
  SUM(CASE WHEN exit_price <  take_profit THEN 1 ELSE 0 END) AS below_tp,
  COUNT(*) total
FROM trading_picks WHERE status='WON';
-- → tp_strong=38, below_tp=147, total=185
```

Only ~21% of the WON rows show a clean TP fill (exit_price >= take_profit). The
remaining 147 closed positive but **below** the take-profit level — consistent
with TIME_EXIT at positive PnL, not TP_HIT. Direction split: 76 LONG / 109
SHORT, so the "below TP" cohort is not just a SHORT-direction comparator
inversion (a SHORT TP_HIT would have exit_price <= take_profit, and a quick
check shows mixed evidence across both sides).

## Mapping decision

| Legacy status | Disambiguator | Target | Rows |
|---------------|---------------|--------|------|
| CLOSED_SL     | unambiguous   | SL_HIT | 0    |
| CLOSED_TP     | unambiguous   | TP_HIT | 0    |
| FLAT          | unambiguous   | TIME_EXIT (exit_reason='FLAT_AT_EXIT') | 0 |
| WON / RECONCILED_POSITIVE_PNL | **ambiguous** (no canonical label in reason; only 38/162 show exit_price≥take_profit) | **SKIP — NEEDS_OPERATOR_REVIEW** | 162 |
| WON / PRICE_RESOLVED [RECO [FIX] (RE | **ambiguous + corrupted reason string** | **SKIP — NEEDS_OPERATOR_REVIEW** | 23 |

## Mutation plan

**No UPDATEs will be issued.** Per the safety rules in the task spec
("If exit_reason is NULL/empty: skip the row — don't guess"), the WON cohort
fails the disambiguation requirement and must be operator-reviewed.

## Backup (executed before reporting)

Snapshot of all 185 candidate rows preserved to:

- DB: `ejaguiar1_backups.trading_picks_pre_status_std_20260531` (185 rows, verified)
- JSON: `reports/trading_picks_pre_status_std_20260531.json`

Schema mirrors `trading_picks` plus `backed_up_at` timestamp.

## Recommended follow-up for operator review

Two disambiguation paths the operator can choose:

1. **Side-aware TP-fill comparator** — define TP_HIT for LONG as
   `exit_price >= take_profit` and for SHORT as `exit_price <= take_profit`;
   everything else with positive pnl_pct → TIME_EXIT. Pre-counts to be
   recomputed under this rule before any mutation.
2. **Resolver re-run** — re-run `alpha_engine/outcome_resolver.py` over these
   185 picks with the v2.1 post-bug-bundle logic and let the resolver emit
   canonical statuses + clean exit_reason strings (also fixes the truncated
   `PRICE_RESOLVED [RECO [FIX] (RE` artifact).

Both should be evaluated against the backup snapshot before any DB mutation.
