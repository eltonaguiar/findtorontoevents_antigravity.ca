# Final 6 Operator-Pending Items — Post Mega-Recon

Date: 2026-05-31
Source: `vw_all_incidents` (live ejaguiar1_stocks) after mega-recon flip pass (w9gciwk0g)
Author: peer_claude

## Live counts

OPEN: 2 · TRIAGED: 3 · IN_PROGRESS: 1 · TOTAL: 6

(Previously OPEN: 3 — incident #2 flipped to IN_PROGRESS this run, see "Still-drifted flips" below.)

## Items

| # | severity | class | title | category | operator action |
|---|---|---|---|---|---|
| 2 | P0 | COMMODITIES | Class-level COMMODITY 11.9% WR / PF 0.29 / Sharpe -0.534 (post-COT-dedup PF 0.13, n=52) | OPERATOR-DECISION-REQUIRED | Pick rebuild direction: (a) retire COMMODITY entirely; (b) rebuild from non-COT signals (term-structure, EIA inventory, weather); (c) external-replication via DBMF/KMLM. Then expand `BLOCKED_STRATEGIES` under MUTATION_THREE_AXIS_PROTOCOL. |
| 6 | P0 | Stocks (EQUITY) | EQUITY emission unlocked (1,424 outcomes) but all strategies PROBATION-tier (trust=3) | OPERATOR-DECISION-REQUIRED | Pick Path A (tune existing 4 strategies via mutation), Path B (import proven edge: QMOM / Faber TAA), or Path C (shadow + scale once WR>=50/PF>=1.5 @ n>=100). |
| 1 | P1 | CRYPTO | ML "edges" with PF 99-1094 are likely look-ahead leakage | OPEN-CODE-CHANGE-NEEDED-OPERATOR-REVIEW | Approve walk-forward gate code (PR #170 linked for audit + small-sample badge; gate code itself still operator-pending). |
| 3 | P1 | CRYPTO | meta_strategy template explosion — 1.6M template rows across ~140 symbol/dir pairs | TIMING-BLOCKED | Wait 1-2 cron cycles for db_health refresh post-commit d317560ac9c, then operator picks blanket-block on CRYPTO/MEMECOIN vs symbol-triple enumeration. |
| 34 | P1 | OVERALL | CI Tests: 17 pytest failures on main (m096/m098/quality_gates/pr10_ab/outcome_resolver) | OPEN-CODE-CHANGE-NEEDED-OPERATOR-REVIEW | Approve production-logic changes: (1) AB_ENABLED default flip after 24h soak; (2) CRYPTO quality gate `crypto_not_liquid_core` scoring review; (3) FOREX `outcome_resolver_noncrypto` test data update. |
| 41 | P3 | OVERALL | at_signal_outcomes SL_HIT rows have 24% with positive pnl_pct (labeling inconsistency) | OPEN-CODE-CHANGE-NEEDED-OPERATOR-REVIEW | Approve deferred fixes: exit_price band-check in outcome_resolver.py; audit SHORT pnl branch; investigate smart_money_accumulation SL geometry; historical row repair. |

## Still-drifted flips (this run)

- **#2 COMMODITY P0**: resolution_notes said "Marked IN_PROGRESS until operator approves the kill list" but DB status was still OPEN. Flipped OPEN → IN_PROGRESS. Pre-flip row backed up to `ejaguiar1_backups.incident_final_6_pre_20260531`.

## Category tally

- OPERATOR-DECISION-REQUIRED: 2 (#2, #6)
- OPEN-CODE-CHANGE-NEEDED-OPERATOR-REVIEW: 3 (#1, #34, #41)
- TIMING-BLOCKED: 1 (#3)
- STILL-DRIFTED: 0 remaining (1 flipped)

## Recommended trigger order

If operator wants to advance, work top-down by leverage-per-decision:

1. **#6 EQUITY rebuild scope (P0)** → Operator picks Path A/B/C. Single sentence unblocks the highest-volume class (1,424 outcomes already flowing; just needs trust-tier upgrade or proven external edge). Highest leverage because emission is already wired — only strategy selection is missing.
2. **#2 COMMODITY rebuild direction (P0)** → Operator picks (a)/(b)/(c). Until picked, no agent can touch COMMODITY without violating the kill rule. Picking (a) is the lowest-effort honest move (PF 0.13 is irrecoverable on current signals).
3. **#34 CI test triage (P1)** → Operator approves each of the 3 production-logic changes individually (AB_ENABLED soak, CRYPTO gate scoring, FOREX resolver test data). Unblocks main-branch test green.
4. **#1 ML walk-forward gate (P1)** → Operator approves the gate code change. Removes the last false-edge risk on CRYPTO ML strategies.
5. **#41 SL_HIT labeling fixes (P3)** → Operator approves the 3-part fix (band-check + SHORT branch + smart_money_accumulation). Low urgency (P3, 7 truly contradictory rows after the NULL-pnl population was isolated).
6. **#3 meta_strategy explosion (P1)** → Wait for cron refresh, then operator picks blanket-block vs enumeration. Timing-blocked, not decision-blocked yet.

## Acceptance

- `SELECT COUNT(*) FROM vw_all_incidents WHERE status IN ('OPEN','TRIAGED','IN_PROGRESS')` = 6.
- Backup row count `ejaguiar1_backups.incident_final_6_pre_20260531` = 1 (incident #2 pre-flip).
- No agent should pick up any of the 6 above without explicit operator direction on the listed action.
