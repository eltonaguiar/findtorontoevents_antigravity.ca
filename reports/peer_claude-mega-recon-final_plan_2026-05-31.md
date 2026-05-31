# Mega Recon — Final DB Drift Cleanup (PLAN)

Date: 2026-05-31
Author: peer_claude (Opus 4.7)
Scope: walk every `vw_all_incidents` row with status IN ('OPEN','TRIAGED','IN_PROGRESS'), reconcile against today's merged-PR ledger, flip the drifted ones.

## Snapshot (pre-mutation)

Pulled 13 actionable rows across `INCIDENT_BONDS/COMMODITIES/CRYPTO/FUTURES/STOCKS/OVERALL`.

## Verified merged PRs (origin/main, 2026-05-31)

#136, #142, #147, #148, #149, #150, #153, #154, #155, #156, #157, #158, #159, #160, #161, #163, #164, #165, #166, #167, #168, #169, #170, #182, #190, #192, #193, #194, #197-205 — all confirmed merged via `gh pr list --search "merged:>=2026-05-30"`.

## Per-row disposition

| Tbl | id | sev | cur_status | title (truncated) | Decision | PR ref |
|---|---|---|---|---|---|---|
| BONDS | 1 | P3 | OPEN | bond_connors_rsi2 new, probation | **FLIP -> RESOLVED** | #148 (disabled alpha-engine-bond.yml; emits via etf-bond-scanner.yml) |
| COMMODITIES | 1 | P2 | OPEN | cftc_cot_commercial_signal BLOCKED 19% WR n=16 | **FLIP -> RESOLVED** | #167 (mutation analysis + disposition) |
| COMMODITIES | 2 | P0 | OPEN | Class-level COMMODITY 11.9% WR | **KEEP OPEN** — resolution_notes already says OPERATOR-PENDING (rebuild path selection) | — |
| COMMODITIES | 7 | P1 | TRIAGED | cot_positioning DSR 1.0 falsified 7.33x over-emission | **FLIP -> RESOLVED** | #149 (per-release dedup) + #157 (reconciliation truth-table) |
| CRYPTO | 1 | P1 | TRIAGED | ML 'edges' PF 99-1094 look-ahead leakage | **KEEP TRIAGED** — ledger explicitly says TRIAGED-doc; walk-forward gate code is operator-pending | #170 (linked) |
| CRYPTO | 2 | P1 | OPEN | quan_engine_scalp PF 0.42 / WR 37% | **FLIP -> RESOLVED** | #182 (RETIRE suspect strategies) |
| CRYPTO | 3 | P1 | TRIAGED | meta_strategy template explosion 1.6M rows | **KEEP TRIAGED** — no PR mapping; bt_backtest_trades cleanup is operator | — |
| CRYPTO | 6 | P1 | OPEN | CRYPTO 48h closures at 0 — resolver DESC fix landed | **FLIP -> RESOLVED** | #142 (TIME_EXIT pnl_pct preservation) + #119 (DESC ORDER BY) |
| FUTURES | 3 | P1 | TRIAGED | FUTURES zombie tile | **FLIP -> RESOLVED** | #153 (FUTURES research-only policy formalized) |
| STOCKS | 6 | P0 | OPEN | EQUITY emission unlocked but all PROBATION-tier | **KEEP OPEN** — resolution_notes says OPERATOR-PENDING Path A/B/C selection | — |
| OVERALL | 24 | P0 | OPEN | Profitable-but-filtered picks not surfaced | **FLIP -> RESOLVED** | #136 (observability lane shipped) |
| OVERALL | 34 | P1 | OPEN | 17 pytest failures on main | **KEEP OPEN** — instruction says docs-only; real fix needs operator | #169 triage docs (link only) |
| OVERALL | 41 | P3 | TRIAGED | SL_HIT positive-pnl 24% labeling | **KEEP TRIAGED** — ledger says TRIAGED-DOC; historical repair deferred | #164 (already linked) |

## Tally

- **FLIP -> RESOLVED: 7** (BONDS#1, COMMODITIES#1, COMMODITIES#7, CRYPTO#2, CRYPTO#6, FUTURES#3, OVERALL#24)
- **KEEP OPEN — operator-pending: 3** (COMMODITIES#2, STOCKS#6, OVERALL#34)
- **KEEP TRIAGED — already documented, follow-up deferred: 3** (CRYPTO#1, CRYPTO#3, OVERALL#41)
- **Remaining actionable after recon: 6**

## Backup strategy

Create `ejaguiar1_backups.incident_db_mega_recon_pre_20260531` with the row snapshot of all 7 rows about to mutate. Schema mirrors `vw_all_incidents`. INSERT-then-UPDATE pattern, autocommit OFF, single transaction.

## Mutation SQL (parameterized; per-table UPDATE because no central table)

For each FLIP row:
- `UPDATE INCIDENT_<tbl> SET status='RESOLVED', resolved_at=NOW(), updated_at=NOW(), resolution_notes=CONCAT(COALESCE(resolution_notes,''),'\n\n[MEGA_RECON 2026-05-31] Resolved via merged PR(s) ...'), link_github_ref='PR#<n>' WHERE incident_id=<id>`

## Safety

- Only touches 7 rows on per-class tables (no cross-shard fanout).
- Skips all 4 explicitly-named exclusion patterns from the instructions.
- Does not touch `id`, `created_at`, `evidence`, `title`, `description`.
- Backup committed before any UPDATE.
