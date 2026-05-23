# Swarm Task: Critique + Extend Kimi 2026-05-18 Action Plan

**Task ID:** kimi-plan-critique-20260518  
**Priority:** P0  
**Agents:** 3  
**Mode:** research + critique (no code changes, read-only)

---

## Context

Kimi (a cloud AI agent) generated 4 files on 2026-05-18 for the findtorontoevents_antigravity.ca trading system.
The files have been committed to `reports/`. Key correction already applied: Kimi claimed CRYPTO=MONEY_READY
but our peer cross-validation proved CRYPTO=NOT_READY (ml_enhanced sprawl, 97.7% of filter set, family PF=0.64).

## Files to Critique

1. `reports/MASTER_ACTION_PLAN_kimi_2026-05-18.md` — per-class gameplan (CRYPTO verdict corrected)
2. `reports/audit_infrastructure_technical_brief_kimi_2026-05-18.md` — technical brief on pick lifecycle
3. `reports/PICK_TRACEABILITY_SPEC_kimi_2026-05-18.md` — spec for pick traceability system
4. `reports/PR_PLAN_kimi_2026-05-18.md` — 37 PRs across 8 workstreams

## Research Questions (Parallel)

### Agent 1 — Verdict Validation
For each asset class verdict in Kimi's MASTER_ACTION_PLAN, validate against current codebase state:
- Check `audit_dashboard/data/pf_registry.json::by_asset_class_policy_clean_net` for canonical PF/WR/n
- Check `alpha_engine/data/closed_picks.json` for local n counts
- Check `audit_dashboard/data/dashboard_data.json::performance.asset_class_health` for dashboard values
- Flag any verdict (WR, PF, n, sized/Kelly%) that doesn't match the pf_registry canonical values
- Confirm CRYPTO NOT_READY is correctly understood (don't revert to MONEY_READY)
- Output: verdict_validation_report.md

### Agent 2 — Pick Traceability Gap Analysis
Read `reports/audit_infrastructure_technical_brief_kimi_2026-05-18.md` and `audit_trail/quality_gates.py`:
- Verify Kimi's claim that filter_log has no pick_id correlation (check actual filter_log write sites)
- Verify the 4 gap claims: no pre-assignment pick IDs, no per-gate attribution, no score trace, no what-if replay
- Check if `pick_gate_decisions` table already exists in `audit_trail/pick_feature_store.py` or `audit_trail.db`
- Check if any `pick_lifecycle_events` table already exists
- Check `passes_active_gate()` and `passes_smart_gate()` for any existing structured logging
- Check `audit_trail/data/audit_trail.db` schema (if accessible via py_compile-safe inspection)
- Validate Kimi's SQL schemas (pick_gate_decisions, pick_lifecycle_events, gate_impact_attribution) against existing schema
- Output: traceability_gap_validation.md

### Agent 3 — PR Plan Feasibility Check
Read `reports/PR_PLAN_kimi_2026-05-18.md`:
- For each of the 5 PRs in Section 9 of MASTER_ACTION_PLAN, check if the target files already exist:
  - `core/pick_lifecycle_logger.py` — does it exist? If not, what's the closest existing file?
  - `filters/cot_staleness.py` — does it exist? cot_positioning logic is where?
  - `filters/concentration_cap.py` — does concentration logic already exist in quality_gates.py?
  - `gates/vix_gate.py` — does `audit_trail/vix_regime_gate.py` already cover this?
  - `config/equity_universe.csv` — does any equity universe CSV exist? (alpha_engine/config.py has symbols)
- Check if `db/migrations/` directory exists (Kimi assumes MySQL migration files)
- For the VIX gate (E-005): check current wiring status in `alpha_engine/etf_scanner.py` and `audit_trail/quality_gates.py`
- For COT lag (M-001): check `tools/cot_positioning.py` or equivalent for the 3-day lag issue
- For COMMODITY concentration cap (M-002): check if `system_concentration.json` + existing logic covers CT=F capping
- Output: pr_feasibility_report.md with verdict: FEASIBLE/NEEDS_REMAP/DUPLICATE for each PR

## Output Format

Each agent writes a compact report (max 200 lines each) to stdout. Swarm aggregates into one JSON:
```json
{
  "verdict_validation": { ... },
  "traceability_gaps": { ... },
  "pr_feasibility": { ... },
  "consensus_recommendations": [ ... ],
  "highest_impact_next_action": "..."
}
```

## Constraints

- NEVER run dashboard_generator.py — py_compile only
- NEVER invent numbers — all figures must come from actual files
- NEVER commit code — research only
- If a claim in Kimi's files cannot be verified from codebase, mark it UNVERIFIED (not assume true)
