# Ownership: Qwen Pending Work — 2026-05-31

**Operator directive (2026-05-31 evening):** claude takes ownership of qwen's
remaining audit/Mercury2 work. This file is the inventory.

## Source material

- `/.qwen/worktrees/audit-pick-funnel-analysis-2026-05-31/updates/2026-05-31-audit-quick-summary.md`
- `/.qwen/worktrees/audit-pick-funnel-analysis-2026-05-31/updates/2026-05-31-db-crosscheck-pick-funnel-audit.md`
- `/.qwen/worktrees/audit-pick-funnel-analysis-2026-05-31/audit_dashboard/data/db_crosscheck_report.json`
- `/.qwen/worktrees/audit-pick-funnel-analysis-2026-05-31/backfill/db_crosscheck_light.py`
- Mercury2 plan (10-section roadmap) + 8-step quick-start checklist

## Cross-reference vs what claude shipped today (2026-05-31)

- PR #316 — master harness (cursor framework = qwen's recommended stat gates)
- PR #329 — verified qwen PF reversal claims (FOREX DOESNT_REPRODUCE; EQUITY magnitudes fabricated)
- PR #285 — edge-stability daily cron
- PR #324 — clear updates entry (operator-readable)
- PR #326 — copytrader status by class
- PR #327 — baby + alpha-engine status by class
- PR #330 — ML-DYDX degradation flag
- wave wkyapjb3g (in flight) — 4 verifiers on qwen claims + Mercury2 gap synth

## Ownership inventory

| Qwen open item | Status | Owner | Next action |
|---|---|---|---|
| Hardcoded DB creds → GitHub Secrets (5 scripts) | DEFERRED (deepseek P1, scoped) | claude (next session) | scope + migration plan + grep targets |
| Audit page timestamps (data-as-of badges) | PARTIAL (kilo `dashboard_freshness.js` PR #319 docs-only) | claude (next session) | cherry-pick decision: wire vs close |
| Filter-click logger → `filter_stats` table | NOT_STARTED | claude (low priority) | scope when paper-pilot has n>=100 |
| Backtest engine refresh (`bt_backtest_trades` 25d stale) | NOT_STARTED | claude (next session) | restart sync pipeline + diagnose stall |
| 3.7M row gap on `bt_backtest_trades` | wkyapjb3g verifying | claude | await verdict from in-flight wave |
| Mercury2 statistical gates (DSR/SPA/PBO/walk-forward) | ALREADY_SHIPPED via PR #316 | claude | monitor harness, no new code |
| Walk-forward per asset class (PR #654 placeholder) | NOT_STARTED | claude (next session) | wire `walkforward_validator.py` |
| Position sizing (Kelly / vol-parity) | NOT_STARTED | claude (gate later) | wait until paper-pilot graduates first class to T2 |
| Grafana monitoring | NOT_NEEDED (we use `audit_dashboard`) | n/a | n/a |
| 9,657 ghost OPEN picks | NOT_STARTED | claude (next session) | resolver fix — replay intrabar OHLC |
| Non-canonical statuses (closed/WIN/EXPIRED→WON) | NOT_STARTED | claude (next session) | normalize via `at_signal_outcomes_slhit_positive_pre_fix` pattern |
| Pick funnel button-stats automation | NOT_STARTED | claude (low priority) | scope after paper-pilot |
| CRYPTO Smart Picks 46-pt WR gap (78.9% vs 39.4%) | KNOWN/DISPUTED (banner live since `c1b977997`) | claude | leave disputed banner; treat as PR #316 harness verdict input |
| FOREX wiring-mix bug (good strats starved) | KNOWN | claude (next session) | revisit after #316 harness re-ranks FOREX strategies |
| Confidence inversion (HIGH-conf underperforms) | REFUTED 2026-05-31 (live audit) | n/a | see `project-confidence-trust-edges-2026-05-31.md` |
| SL too tight (78.9% SL-hit) | REFUTED 2026-05-31 price-path replay | n/a | see commit `34ec109ec` — tightening SL collapsed PF (whipsaw) |
| COMMODITY 0% WR / regime collapse | KNOWN | claude (next session) | already FAIL+INSUFF-N; further mutation gated on `MUTATION_THREE_AXIS_PROTOCOL.md` |

## Summary counts

- Qwen open items inventoried: **17**
- Already shipped by claude today: **3** (Mercury2 stat gates, edge-stability cron, verification of PF reversal claims)
- Refuted / not-needed: **3** (confidence inversion, SL-too-tight, Grafana)
- In flight (wkyapjb3g): **1** (3.7M row gap)
- Claude open for next session: **6**
  1. DB creds → GitHub Secrets
  2. Audit page timestamp cherry-pick (PR #319 decision)
  3. Backtest engine sync restart (25d stale)
  4. Walk-forward per asset class (#654 placeholder)
  5. Ghost OPEN picks resolver fix (n=9,657)
  6. Non-canonical status normalization

## Tonight policy

**NO new code changes.** Paper-pilot harness runs 13:30 UTC tomorrow. Action
items wait until then.

## Resume next session

Read this file + `project-qwen-ownership-2026-05-31.md` (memory index).
Start with the 6 open items above, in priority order (DB creds first — security).
