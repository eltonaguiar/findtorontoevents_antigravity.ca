# Phase 10b Readiness Check — Plan (BEFORE)

**Author:** Claude Opus 4.7 (sub-agent)
**Date:** 2026-05-31
**Purpose:** Final tally + GO/HOLD decision on launching per-class `/money-maker-readyv2` plans (Phase 10b).

## Context

User criterion: move to `/money-maker-readyv2` once incidents are *fairly addressed*. This report verifies three preconditions before Phase 10b launches.

## Three Questions

### Q1 — Incidents page "fairly addressed"?

- **Query:** `SELECT status, COUNT(*) FROM vw_all_incidents GROUP BY status`
- **PASS criteria:** `actionable_surface_now < 12` **OR** `(actionable_now / total) < 25%`
- **"Actionable" defined as:** status in {OPEN, IN_PROGRESS, PENDING, NEW, ACTIVE, REOPENED, TRIAGED-but-not-resolved} — i.e. not in {RESOLVED, WONTFIX, DUPLICATE, CLOSED}.

### Q2 — Published JSONs reflect today's RETIRE PR #182?

PR #182 merged at **2026-05-31T05:47:35Z** — retires `cta_golden_cross_200` and `prediction_market_consensus` (Phase-4 resolver artifacts).

- **Q2a:** `pf_registry.json` `.generated_utc` > 05:47Z **AND** neither retired strategy present in any `by_asset_class_*` list.
- **Q2b:** `money_ready_verdict.json` `.generated_at` > 05:47Z **AND** neither retired strategy present in classes/top-edges.

**Nuance:** if `.generated_utc` < 05:47Z but the retired strategies are already absent, that's still effectively PASS (the JSON predates the PR but reflects the desired post-retirement state). Flag for operator to refresh, but do not HOLD.

### Q3 — Watchlist candidates still valid?

For each Phase-3 MC top candidate, re-run live stats and confirm n hasn't dropped to insignificance and PF hasn't moved off the T2-watchlist boundary.

- **EQUITY `stocks_rsi2_pullback`:**
  `SELECT COUNT(*) n, AVG(pnl_pct), SUM(pnl_pct>0)/COUNT(*) wr FROM trading_picks WHERE strategy LIKE '%stocks_rsi2_pullback%' AND category='equity' AND closed_at IS NOT NULL`
- **FOREX `fx_smart_carry_trade_momentum`:**
  same query for `category='forex'`.

**PASS criteria per candidate:** n >= 20 (still meaningful), avg_pnl_pct > 0, WR >= 50%.

## Decision Matrix

| Q1 | Q2 | Q3 (both candidates) | Verdict |
|----|----|----------------------|---------|
| PASS | PASS | PASS | **GO_PHASE10B** |
| PASS | FAIL | PASS | HOLD — refresh JSONs |
| FAIL | * | * | HOLD — finish incident triage |
| * | * | partial FAIL | GO with reduced candidate set (drop failed candidate) |

## Deliverables

1. `reports/peer_claude-phase10b-readiness_plan_2026-05-31.md` (this file)
2. `reports/peer_claude-phase10b-readiness_result_2026-05-31.md` (after queries run)
3. Server-side docs PR via `gh api`; admin-merge if 1-2 files.

## Reference Anchors

- PR #182 (RETIRE): https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/pull/182 (merged 05:47:35Z)
- `audit_dashboard/data/pf_registry.json` (canonical pre-publish)
- `audit_dashboard/data/money_ready_verdict.json` (canonical pre-publish)
- Live published copies under `https://findtorontoevents.ca/audit/data/`
