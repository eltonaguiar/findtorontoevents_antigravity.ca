# /money-maker-readyv2 PENNY — Plan (2026-05-31, 06:30Z)

## Scope
Per-class action plan for PENNY (categories: `penny`, `pennystock`) on findtorontoevents.ca/audit.

## Methodology
1. Pull `ejaguiar1_stocks.trading_picks WHERE category IN ('penny','pennystock')` — class aggregates, per-strategy aggregates, 14d / 48h recency, 30d/90d emission cadence, NULL pnl, exit_reason distribution.
2. Cross-reference vs `audit_dashboard/data/pf_registry.json :: by_asset_class_policy_clean_net` — confirm whether PENNY is even tracked as its own class (it is NOT — gets folded into EQUITY).
3. Trace gate path: `production_scanner.py` Gate 0 (`_BLOCKED_CATEGORY_STRATEGIES`), category normalization (line 2611), penny-specific emitters (`skyrocket_detector`, `penny_stock_strategy_harness`, `institutional_picks_engine`).
4. Cross-reference Phase-3 MC watchlist (PR #179) — PENNY has no MC candidate at all (no strategy with n≥30 in this class).
5. Identify resolver-bug exposure (Phase 4 finding: writes past-TP without intrabar verification) — note 0/8 PENNY rows have `tp_fill_method` populated, all closes were SL/TIME/PURGE/STATUS_STANDARDIZED, so Phase-4 TP-fabrication is NOT the dominant problem here.

## Output
- `reports/peer_claude-phase10b-money-maker-penny_plan_2026-05-31.md` (this file)
- `reports/peer_claude-phase10b-money-maker-penny_result_2026-05-31.md` (verdict + ranked actions)
- Server-side docs PR if scope is docs-only.
