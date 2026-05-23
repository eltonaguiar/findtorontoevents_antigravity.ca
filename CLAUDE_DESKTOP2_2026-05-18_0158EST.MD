# CLAUDE DESKTOP 2 — Session Drop · 2026-05-18 01:58 EST

Instance: Claude Opus 4.7 (1M ctx) · Branch worked: `feat/fork2-new-signals` → committing to `main`.

## What I accomplished

### 1. New skill — `audit-pick-flow`
`.claude/skills/audit-pick-flow/` — traces any `/audit` pick from source emitter →
gates → active/closed. Files: `SKILL.md`, `references/pipeline-map.md` (every gate +
file:line + env kill-switch), `references/db-tables.md`, `scripts/trace_pick.py`
(single-pick flow), `scripts/pick_flow_funnel.py` (per-class funnel). Both scripts
py_compile-clean and verified against live MySQL.

### 2. DB audit-trail acceleration layer — APPLIED LIVE to `ejaguiar1_stocks`
`audit_integration/05_pick_audit_trail_schema.sql`. Three new InnoDB tables:
- `at_pick_flow_daily` — per-day per-class funnel rollup; nightly MySQL event
  `ev_pick_flow_daily_rollup` + proc `sp_rebuild_pick_flow_daily`. Backfilled 15 days.
- `at_pick_audit_trail` — full per-gate PASS/REJECT trace; opt-in writer pending.
- `at_job_log` — scheduled-event run log.
Event scheduler verified firing (2-min one-shot probe logged + auto-dropped).
Grok-flagged bug fixed: reject-reason now MODAL not alphabetical.

### 3. Reports
- `reports/audit_pick_flow_case_study_2026_05_18.md` — past-week funnel per asset class.
- `reports/roadmap_no_edge_to_money_ready_2026_05_18.md` — 6-phase measurement-first plan.
- `reports/kilo_fork2_vetting_2026_05_18.md` — 6-agent vetting of OPENROUTER/kilo Fork-2.

### 4. Vetting verdict on OPENROUTER (kilo) Fork-2 work
`options_flow.py` + `onchain_crypto.py`: **DO NOT MERGE** — gamma math bug, dead skew
function, never call the harness, banned signal rebuild, zero tests, TX-volume proxy
relabeled as on-chain. The kilo *research conclusion* (8 harness kills, no edge) is
honest and verified on disk — trust it.

## Key findings (per asset class)

| Class | State |
|-------|-------|
| CRYPTO | only class with real sample — sub-floor, WR ~33%, PF 0.17-0.41 |
| EQUITY/FOREX/FUTURES/ETF/BOND | unresolved — closed at `pnl_pct=0.0` placeholder (resolver bug) |
| COMMODITY | headline inflated by killed COT strategies — artifact |

No asset class is money-ready. 5 of 6 classes are statistically invisible until the
non-crypto resolver is fixed.

## What's remaining (→ profitability per asset class)

Profitability is gated behind **measurement**, not more signal hunting:
1. **Phase 0 (BLOCKER)** — fix non-crypto resolver, populate `closed_at`, normalize
   `status` enum, wire the `at_pick_audit_trail` writer. Until this lands, WR/PF for
   5 classes are fiction.
2. **Phase 1** — fix plumbing: most picks die to staleness/no_consensus, not quality.
3. **Phase 2** — per-class triage (CRYPTO cut volume; others gather n≥100 clean).
4. **Phase 3** — genuine new-input edge hunt, harness-gated (`is_admissible()` only).
5. **Phase 4** — money-ready promotion gate per class (Tier-2 charter thresholds).
6. **Phase 5** — fix the orphaned `/audit` "Money Ready" button; surface the funnel.

Honest expectation (Grok-confirmed): after 8 harness kills, there may be **no edge in
the current generator family**. The roadmap therefore optimizes for a *truthful*
dashboard first; a proven edge per class is Phase 3-4, not guaranteed.

## Handoff asks
- OPENROUTER/kilo: see `reports/kilo_fork2_vetting_2026_05_18.md` — fix or drop the two modules.
- Anyone on Phase 0: the resolver fix is the highest-leverage task in the repo right now.
