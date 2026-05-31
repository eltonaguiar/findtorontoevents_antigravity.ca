# WON-185 Forensics — Result (AFTER) — OPERATOR DECISION NEEDED

Date: 2026-05-31
Author: Claude Opus 4.7 (peer subagent)
Plan: `reports/peer_claude-won185-forensics_plan_2026-05-31.md`

## Action taken

**No DB mutation.** Per the decision tree in the task, the 185-row population is **MIXED** (two semantically different sub-populations), so a blanket relabel would invent information. The status='WON' is non-canonical but **semantically valid** (positive PnL, exit recorded) — preserving it with the existing exit_reason is the conservative correct call for 162 of 185.

The 23 truncated-label rows are a candidate for a separate re-resolve PR, but they need operator confirmation of the source-of-truth resolver path (live vs legacy) before mutation.

## Distribution matrix

| # | sub-population | n | share | character | recommended action |
|---|---|---|---|---|---|
| A | `exit_reason='RECONCILED_POSITIVE_PNL'` | 162 | 87.6% | spread across 13 source_systems × 7 categories; pnl 0.13%→30%+; explicit "exit mechanism indeterminate" backfill label | **PRESERVE** as status='WON' with current exit_reason. Optionally add a `_RECONCILED` suffix convention to the canonical status dictionary so dashboards can group WON+TP_HIT+RECONCILED_POSITIVE properly. |
| B | `exit_reason='PRICE_RESOLVED [RECO [FIX] (RE'` (truncated VARCHAR(30)) | 23 | 12.4% | 20 forex + 3 commodity, all 100% with `|pnl_pct|<5bp` (sub-threshold per `PNL_WIN_THRESHOLD_BY_CLASS`) | **RE-RESOLVE → status='TIME_EXIT', exit_reason='FLAT_SUBTHRESHOLD_FOREX_FIX'**. These are mislabeled wins from a pre-v2 resolver path. Mutation set ≤23 (well under 200 cap). |

## Operator decision menu

### Option 1 (LOW RISK — recommended) — preserve all 185 as-is, document the convention

- Add `WON` to the recognized-but-non-canonical status list in `docs/STATUS_TAXONOMY.md` (create if missing).
- Update dashboard generator to treat `WON` as equivalent to `TP_HIT|TIME_EXIT_PROFITABLE` for tier-table aggregation (it already shows up as a positive-PnL closed pick, but the label is invisible in some legacy joins).
- Schedule a Phase-11 backfill pass that re-runs `outcome_resolver.py` against the 162 RECONCILED rows so each gets a definitive TP_HIT vs TIME_EXIT classification via intrabar OHLC replay (per `feedback-sl-optimization-needs-pricepath` memory).
- **Cost:** 0 DB mutations now, 162 mutations in Phase-11 after intrabar replay infra is in place.

### Option 2 (MEDIUM RISK) — relabel only Group B (23 rows)

- Backup `trading_picks` → `ejaguiar1_backups.trading_picks_pre_won185_forensics_20260531`.
- `UPDATE trading_picks SET status='TIME_EXIT', exit_reason='FLAT_SUBTHRESHOLD_FOREX_FIX' WHERE status='WON' AND exit_reason LIKE 'PRICE_RESOLVED%' AND ABS(pnl_pct)<0.05` (expected: 23 rows).
- Preserves 162 RECONCILED rows untouched.
- **Cost:** 23 row mutations, deflates forex WR by 23 spurious "wins" (matches `feedback_noncrypto_resolver_live_close_bug.md` direction).

### Option 3 (HIGH RISK — NOT recommended) — coerce all 185 to a single canonical label

- Would force-map 162 reconciled rows to either TP_HIT or TIME_EXIT despite the pnl-bucket spread (0.13%–30%+) being incompatible with a single exit mechanism.
- Invents information. Rejected by decision tree.

## Recommended action for operator

**Approve Option 2 in a follow-up PR**, gated on operator confirmation that:
1. The pre-v2 forex resolver path is no longer writing new sub-threshold wins (verify last `closed_at` for Group B is before the resolver v2 deploy date — last row is **2026-04-23 19:37**, resolver v2 + v2.1 bug bundle landed **2026-05-02**, so YES — Group B is pre-v2 legacy and re-resolving is safe).
2. The `FLAT_SUBTHRESHOLD_FOREX_FIX` reason string is acceptable in the canonical taxonomy.

Adopt Option 1 for the 162 reconciled rows (documentation + Phase-11 intrabar re-resolve).

## Before/after counts

This forensics PR makes **no DB changes**. Counts unchanged:

```
trading_picks WHERE status='WON': 185 (162 RECONCILED_POSITIVE_PNL + 23 PRICE_RESOLVED [RECO truncated)
```

## Backup status

**Not created.** No mutation performed. If operator approves Option 2, the follow-up PR will create `ejaguiar1_backups.trading_picks_pre_won185_forensics_20260531` first.

## Return code

`DOCS_PR:#<N>:operator_decision_needed` — see PR created in same commit.
