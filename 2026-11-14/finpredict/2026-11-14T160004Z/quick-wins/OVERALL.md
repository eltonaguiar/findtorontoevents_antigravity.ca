# OVERALL — cross-cutting quick wins

## QW-1 — Surface honesty metrics (excluded counts + n + binomial CI) next to WR
- **Problem:** Headline WR is computed on `valid_closed_picks` = 7,914/16,126 (49%); `integrity_excluded 7,567` + `auto_expired_excluded 8,888` are emitted but never displayed, so WR looks unbiased.
- **Fix:** Add `win_rate_ci_low/high` + `excluded_pct` to `payload["summary"]` (Wilson helper already exists at `dashboard_generator.py:7673/:7769`). Render `n / excluded / CI` beside WR in the UI.
- **Targets:** `audit_trail/dashboard_generator.py` `generate()` summary block (lines ~16861–16939); `audit_dashboard/dashboard_enhancements.js`.
- **Effort S · Impact H.** Verify: summary gains CI + excluded_pct; WR card shows `n=…, excluded=…, CI=…`.

## QW-2 — Add `edge_ratio` back (or remove the orphaned reader)
- **Problem:** `edge_ratio` absent from main `summary` (only the hyrotrader panel reads it). Corrected: main dashboard reads `data.edge_surfaces.verified_lab` (present); `edge_ratio` is hyrotrader-only.
- **Fix:** Re-emit `edge_ratio` into `summary` (value already computed in `tools/hyro_pick_performance_validator.py:549`), or delete the hyrotrader column if stale.
- **Targets:** `dashboard_generator.py` summary block; `audit_dashboard/hyrotrader/index.html:1730`.
- **Effort S · Impact M.**

## QW-3 — Emit `INSUFFICIENT` when `forward_trades == 0`
- **Problem:** `forward_wr`/`fwd_trades` are 88–97% empty; UI shows blank/misleading 0% instead of "insufficient".
- **Fix:** Set `forward_wr = None` (or `INSUFFICIENT` sentinel) when `fwd_trades == 0`; render a label in the UI.
- **Targets:** `dashboard_generator.py` forward-stat assembly (lines ~6565–6568, 6600–6605, 6661, 7256–7279, 11107–11470); `dashboard_enhancements.js`.
- **Effort S · Impact M.**

## QW-4 — Refresh-or-remove dead sections/sidecars
- **Problem:** In-payload stale: `walkforward` (2026-04-15), `ml_health` (2026-05-25), `analyst_active_calls`/`predictions_leaderboard` (2026-03-26). Sidecars stale: `regime_report.json`, `strategy_ic_analysis.json`; `strong_signals.json` / `stock_forex_prices.json` have **no producer** (orphan deploy refs); 5 "AI battle" top-pick files frozen 2026-03-14.
- **Fix:** Add generated-at staleness guard in `dashboard_freshness.js` (framework already at :345–510) to hide/relabel old sections; remove orphan deploy entries from `tools/deploy_audit_files.py:38/:59`.
- **Targets:** `dashboard_generator.py` (payload keys ~16998/16730/17010), `dashboard_freshness.js:95–160 & 345–510`, `tools/deploy_audit_files.py`.
- **Effort M · Impact M.**

## QW-5 — Cap/flag outlier PnL (surface existing flags)
- **Problem:** ±500% / −99% artifacts. Clamp+flag machinery already exists (`audit_trail/pnl_ingest_sanity.py`, `universal_pick_resolver.py:1470`, `dashboard_generator.py:1792`) but is invisible.
- **Fix:** Add `outlier_clamped_count` to `summary` + flagged-rows list in UI (no new logic).
- **Targets:** `dashboard_generator.py` summary block; `dashboard_enhancements.js`.
- **Effort S · Impact M.**

## QW-6 — Fix recurring Actions `Install dependencies` / `Install Playwright` failures
- **Problem:** 28 workflows failing last run; many at `Install dependencies`; Sports smoke at `Install Playwright`; CI Tests on 3.11+3.12; Unified Audit Dashboard cancel-cascade (0-job runs).
- **Fix:** Pin `actions/setup-python` + `python-version`; replace `pip install -r requirements.txt` with the real dependency path (user-site `~/.local`); add `playwright install --with-deps chromium` behind a flag; retire `.retired`/`.disabled` workflows. No single `requirements.txt` confirmed — fix is per-file.
- **Targets:** `.github/workflows/autonomous_trading.yml:48–51`, `sports-smoke-and-e2e.yml:83–86`, `ci-tests.yml`, `live_trading*.yml`, `self_optimizing_trading.yml`, `forward_test.yml`, `robust-edge-miner.yml`.
- **Effort M · Impact M.**

## QW-7 — Hide gated/placeholder rows from the active list
- **Problem:** `_apply_per_class_visibility_floor()` surfaces `_gate_passed=False`/`_below_gate` rows into `picks.active`, so FUTURES shows "3 OPEN, 0 closed ever" as if real.
- **Fix:** Exclude `_below_gate` rows from published `picks.active` for zero-closed-history classes (or tag `placeholder=True` and collapse in UI). Stopgap: env `PER_CLASS_ACTIVE_FLOOR=0`.
- **Targets:** `dashboard_generator.py` `_apply_per_class_visibility_floor()` (:14311), `_apply_shadow_promotion()` (:14386), active-pool assembly (~:17468).
- **Effort S · Impact M–H.**

## QW-8 — Remove the "mutual funds" claim or build the page
- **Problem:** `alpha_engine/mutual_fund_ranker.py` and `/audit/mutual-funds.html` do **not exist**; only `multi_asset/portfolio_defs.py` defines the class, and `_NON_CRYPTO_ASSET_CLASSES` already excludes it.
- **Fix:** Relabel the `/audit/mutual-funds.html` reference as "planned/not built" (or delete it).
- **Targets:** `audit_dashboard/institutional_readiness_plan.html:190`; reference `multi_asset/portfolio_defs.py:382/677/773`.
- **Effort S · Impact L.**
