# Phase-0 Resolver — Reconciled Canonical Plan — 2026-05-18

Two Phase-0 resolver plans landed on `main` the same day:
- `reports/phase0_resolver_fix_plan_2026_05_18.md` (Claude-desktop agent) — focused
  on `outcome_resolver.py` never writing `closed_at` + yfinance symbol-suffix gap.
- `reports/RESOLUTION_PIPELINE_FIX_PLAN_2026-05-18.md` (3-agent swarm + 3-engine
  swarm-plan) — live-DB-grounded; found 3 defects in the `active_picks_sync` /
  `universal_pick_resolver` / symbol-write path.

## Reconciliation verdict

**`RESOLUTION_PIPELINE_FIX_PLAN_2026-05-18.md` is canonical.** Reasons:
1. It is grounded in live-DB resolution-rate queries (CRYPTO 65% / EQUITY 45% /
   FOREX 22% / FUTURES 8.7% / ETF 33%) — it explicitly disproves the "non-crypto
   0% resolution" briefing as a stale Hermes artifact (per the Multi-AI
   Convergence Trap rule + `project_hermes_phantom_work` memory: verify inputs).
2. It identifies the dominant defect (symbol-format chaos) with row counts and
   a swarm-vetted staged, no-straight-to-prod order.

**The two plans converge** on the real root cause: symbol-format inconsistency
(`=X`/`=F` suffix handling). The `closed_at` finding from the desktop plan is a
candidate sub-item — verify it against the canonical plan's live numbers before
acting (if EQUITY resolves at 45%, `closed_at` is being written somewhere).

## Execution order (from the canonical plan)

1. **Stage A — safe, now:** workflow dry-run-all-classes edit + the 2
   `active_picks_sync.py` code-bug fixes (Bug 1 WHERE-clause mismatch, Bug 2
   fail-loud on 0 prices). No production writes. ← executed this session.
2. Symbol-format write-time fix: shared `canonicalize_symbol()` +
   `build_pf_registry._norm()` suffix fix. Code-only.
3. DB symbol normalization (~2,086-row UPDATE) — **operator confirmation +
   backup table required.** Not autonomous.
4. Stage B — `active_picks_sync` `--apply` flip after 3-5 clean Stage-A cycles.
5. FUTURES orphan-source backlog sweep once the writer is live.

Steps 3-5 are gated on operator sign-off / live cycles. Steps 1-2 are autonomous.
