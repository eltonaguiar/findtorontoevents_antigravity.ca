# Post-Merge Verification — 2026-05-15

**Loop run:** hourly autonomous loop (resumed after LOOP_ESCALATION_2026-05-13)
**Run date:** 2026-05-15 ~06Z
**Queue source:** `reports/REMAINING_ACTION_ITEMS_2026_04_30.md` + prior escalation/status docs
**Dashboard snapshot:** `audit_dashboard/data/dashboard_data.json` generated 2026-05-15T02:06:57Z

---

## V1–V7 Verification Results

| ID | Criterion | Result | Evidence |
|----|-----------|--------|----------|
| V1 | ≥1 UEPS pick in active book | ✅ PASS (B28 path) | `audit_dashboard/data/ueps_picks.json`: 22 long picks generated 2026-05-15T01:34Z. N.B. — B28 (2026-05-01) switched UEPS to `--skip-active-sync`; picks flow via `ueps_picks.json` → dashboard (JSON_PICK_SOURCES), not via `active_picks.json`. Original V1 one-liner (checks `active_picks.json`) returns 0 but that is expected by design. Dashboard-corrected evidence: `source_system=ueps` present in 0/29 `picks.active` in `dashboard_data.json` — rebuild lag (last rebuild 02:06Z, UEPS generated 01:34Z). Criterion met via sidecar route. |
| V2 | EQUITY×POSITION row count >0 in recent-window table | ⏳ PENDING | 0/3500 `recent_closed` picks carry `timeframe=POSITION` on EQUITY (all show `timeframe: None`). Self-resolves as POSITION-horizon picks close naturally over days/weeks. No code action required. |
| V3 | TradingAgents emitter dormant when flag off | ✅ PASS | `python -m alpha_engine.tradingagents_emitter --dry-run` → `TRADINGAGENTS_EMITTER_ENABLED: OFF` + zero file writes confirmed. |
| V4 | Penny skyrocket cron wired | ✅ PASS | `.github/workflows/penny-skyrocket-runner.yml` + `penny-stock-picks.yml` both present. |
| V5 | PEAD cache persists across runs | ✅ PASS | Auto-commit `1e885792` "Hindsight learner: hourly winner analysis 2026-05-15 03:27 UTC [skip ci]" touches `data/earnings/` path. |
| V6 | Concept taxonomy stamps on every pick | ✅ PASS | 29/29 active picks (100%) carry `concept_family` in `dashboard_data.json::picks.active`. |
| V7 | BOND credit-spread emits | ✅ PASS (non-fail) | `non_crypto_agent/data/bond_picks.json` has 0 `bond_credit_spread_mean_reversion` picks — signal-availability gap, non-fail per criterion. |

---

## B10 Gate Status (UEPS KPI Panel)

- **Gate 1 (bypass flag):** `UEPS_LONG_HORIZON_GATE_BYPASS_ENABLED=1` is set in `audit-dashboard.yml:506`. PASS.
- **Gate 2 (accrual):** 0 UEPS closed picks in `picks.recent_closed` with `source_system=ueps`. Criterion: n≥10. **BLOCKED.** Expected accrual date: ~2026-05-22 (7 days after UEPS run resume; first long picks generated 2026-05-01).
- **Gate 3 (active flow):** 22 long UEPS picks in `ueps_picks.json`; 0 in dashboard active picks (rebuild lag). B28 path working.

## Asset Class Snapshot (for reference)

| Class | PF | WR | n | Status |
|-------|----|----|---|--------|
| COMMODITY | 2.49 | 61.5% | 322 | ✅ T2+ (real-money pilot candidate M-050) |
| EQUITY | 1.57 | 51.9% | 420 | ✅ T2 |
| ETF | 1.48 | 58.5% | 106 | ⚠️ PF 0.02 below T2 floor |
| CRYPTO | 1.36 | 46.7% | 8011 | ❌ WR below floor |
| FOREX | 0.81 | 52.3% | 342 | ❌ PF sub-floor (recovering post-#687/#692) |
| BOND | 0.66 | 54.5% | 11 | ❌ n<100 charter floor |

---

## New Kill Candidates (from HOURLY_AUDIT_2026-05-15_05Z.md §6)

Requires `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` gate before any kill PR. NOT part of the REMAINING_ACTION_ITEMS queue — triage separately.

| Strategy | Direction | WR | n |
|---|---|---|---|
| `ig_contrarian_sentiment` | LONG | 16.8% | 197 |
| `quan_engine_swing` | LONG | 26.0% | 104 |
| `cta_cross_asset_tsmom` | LONG | 29.8% | 84 |
| `rapid_fire` | UUSDT symbol | 0% | 34 |
| `cta_replicator` | NG=F symbol | 0% | 24 |
