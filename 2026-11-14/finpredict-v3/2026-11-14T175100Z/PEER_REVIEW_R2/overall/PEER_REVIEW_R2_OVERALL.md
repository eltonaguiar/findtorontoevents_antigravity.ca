# PEER REVIEW R2 — Consolidated Overall (2026-11-14, ~17:51Z)

This round reviews the peers' **master-plan / proposed-fixes / cross-ref** work that appeared after my first review. It is a REVIEW (attributing every claim to its peer), not a new audit.

## Peers reviewed (subagents)

| Peer area | Review file | Verdict on their work |
|---|---|---|
| `finpredict-v4` (audits/…) | `PEER_REVIEW_V4.md` | strong verification; some stale re-used evidence + conflicts |
| `finpredict` v1 master-plan | `PEER_REVIEW_V1_MASTERPLAN.md` | strong planning foundation — merge, with fixes |
| `finpredict-v2` | `PEER_REVIEW_V2.md` | strongest for cross-peer reconciliation — backbone |
| ML-audit childlike-airport | `PEER_REVIEW_ML_AUDIT.md` | sound diagnosis, NOT implementation-ready (SQL no-op risk, destructive actions) |
| scratch-hippodraco quick-wins | `PEER_REVIEW_SCRATCH.md` | most implementation-ready (verified file:line targets) |
| hilarious-seer | `PEER_REVIEW_SEER.md` | corroboration only (stubs, no evidence) |

## Cross-peer consensus (now 6 peers)

All agree: frozen-price false-0% PnL, zombie/garbage rows, unresolved/expiry survivorship, multiple-testing inflation, 0/9 money-ready, and the backtest↔forward disconnect. The two highest-value first changes cited by multiple peers: (a) **PnL-unit contract** and (b) **NULL-tombstone zombie drain**.

## Key deltas to merge (from this round)

1. **v2 is the reconciliation backbone**: fleet policy-clean n=22,941, WR 42.21%, PF 0.2657, z=−23.60; 0/9 money-ready; 365 workflows/24 fail/24h; 20 curated vs 4,148 raw; crypto 86.7% EXPIRED zombies; N=658 multiple-testing (≈32.9 false positives); PBO invalid T=20, Reality Check didn't run; `summary_picks` WR>100% bug; 5 conflicting "active" counts.
2. **scratch is most implementation-ready**: QW-ALL-1..9 with verified file:line targets, effort, verify steps. (Proposals only — uncommitted.)
3. **v1 master-plan is strong but needs**: one canonical fix registry (IDs duplicated across class docs); close 4 open decision conflicts (quote enum, dedup key, FUTURES/COMMODITY end-state, FOREX hard-disable default) before P1; fold in v2 GA1–GA4 deep-dive; surface v1's unique evidence (127-pick batch, flat-3% cohort, EQUITY n=8 rewrite).
4. **ML-audit is NOT implementation-ready**: per-class SQL targets a top-level `asset_class` column that `etfs`/`overall` say doesn't exist → would no-op; destructive blanket UPDATE / row-move / `INSERT OR REPLACE`; **mutual-fund stub scanner must be vetoed** (adopt classification-only). futures/commodity have no ML fix folder.
5. **v4**: evidence `pick_summary_stats.json` is 173d stale (re-used); conflicting FOREX PF figures (2.02/0.108/0.66); June-vs-live mixing; ML-confidence inversion contradicts peer's own "ML code sound".
6. **seer**: 3 stub files only; per-class claims unverifiable; use as corroboration only.

## Recommended master-plan adjustments (my discretion)

- **Adopt v2 as the reconciliation backbone** (it's the most complete cross-peer map).
- **Adopt scratch QW-ALL-1..9** as the implementation checklist (verify + commit it first).
- **Merge v1 master-plan** after fixing the registry-ID duplication and closing the 4 conflicts.
- **Reject/red-line** the ML-audit destructive SQL and the mutual-fund stub-scanner (classify only).
- **Update v4's stale evidence** (pick_summary_stats) and resolve its FOREX PF conflict.
- **Keep the prohibition**: no placeholder/emitted "solid" claims until the horizon harness (n≥60/≥30, CI excludes 50%, PF>1.05, win-majority ≥66% of windows) passes.
