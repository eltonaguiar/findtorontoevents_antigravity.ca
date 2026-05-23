# Audit Gap Analysis: findtorontoevents.ca/audit & /audit/hyrotrader

**Analyst:** Quantitative Audit Agent  
**Date:** 2026-05-04  
**Scope:** Live audit dashboard vs. documented requirements (repo + blueprint)  
**Pages Audited:** `https://findtorontoevents.ca/audit/` and `https://findtorontoevents.ca/audit/hyrotrader/`  

---

## Executive Summary

Cross-referencing the live v99.0 Unified Audit Dashboard and HyroTrader tracker against repo documentation reveals **15+ material gaps**, including **critical data integrity inconsistencies** where the same asset class shows contradictory metrics between the headline summary card and the detailed breakdown section. The most severe gaps are:

1. **FOREX headline PF 0.27 vs. breakdown PF 1.41** — a 5.2x discrepancy in the same page  
2. **EQUITY headline "T2 candidate" vs. deep-analysis blacklist** — contradicts the 2026-04-06 report that called EQUITY "toxic"  
3. **HyroTrader `trading_days_logged = 0`** — manual journal entry never updated since Apr 8  
4. **Risk-adjusted metrics (Phase 4) still entirely missing** — deferred since v3 proposal (2026-04-20)  
5. **Stale / truncated HyroTrader JSON feeds** — quan bridge stale since Apr 18, truncated to 1 symbol  

---

## Structured Gap Analysis Table

### Gaps 1–5: Critical Data Integrity / Inconsistency

| # | Requirement | Asset Class | Current Status | Gap Description | Priority | Suggested Fix | Evidence |
|---|-------------|-------------|----------------|-------------------|----------|---------------|----------|
| 1 | **Headline and breakdown metrics must agree** for every asset class | FOREX | **Broken** | Summary card claims **PF 0.27, WR 46.4%, n=1169**; asset-class breakdown shows **PF 1.41, WR 21.4%, n=913 closed + 6 active**. A 5.2× PF discrepancy and 25pp WR discrepancy on the same page undermines all credibility. | **P0 Critical** | Reconcile data sources. The summary card uses `asset_class_health` in `dashboard_data.json` (post-resolver-v2, generated 2026-05-03). The breakdown uses live pick aggregation. One of these pipelines is wrong — likely the resolver-v2 filter is over-suppressing losses or double-counting flat trades. Run a reconciliation query joining both sources and publish the diff. | Live /audit/ page: summary card vs. 💱 Forex breakdown section |
| 2 | **Asset-class health must reflect ground-truth closed-pick performance** | EQUITY | **Broken** | Summary card: **PF 1.41, WR 52.7%, n=421** calling it "T2 candidate. Scale." Deep analysis report (2026-04-06, 1,986 trades) found **EQUITY -2.28% avg, 20.0% WR, PF 0.26** and recommended **"Blacklist EQUITY — reduce to <5% allocation or disable entirely"**. The deep analysis is older but the live dashboard shows no evidence the equity engine was fixed. Either the deep analysis is stale (in which case document the fix) or the live headline is misleading. | **P0 Critical** | Publish a dated bridge study showing why EQUITY went from PF 0.26 (deep analysis, n=20) to PF 1.41 (live, n=421). If the improvement is real, link the study on the dashboard. If not, downgrade the headline. | `ASSET_CLASS_DEEP_ANALYSIS_REPORT.md` §7 P0 #3; live /audit/ headline |
| 3 | **Per-asset-class walk-forward (OOS) data must cover all asset classes** | BOND | **Missing** | Walk-forward table shows **COMMODITY, CRYPTO, EQUITY, ETF, FOREX** but **BOND is absent** despite having a headline card. The update note says "updated 2026-05-04" but only 5 classes appear. | **P1 High** | Add BOND to `walk_forward_by_class()` output. BOND has n=18 closed trades; if the walk-forward requires minimum folds, state the threshold explicitly and show "insufficient data" rather than omitting the row. | Live /audit/ walk-forward table |
| 4 | **Walk-forward Sharpe values must be actionable** | CRYPTO, COMMODITY, FOREX | **Broken** | OOS Sharpe values are **deeply negative** for 3 of 5 classes: COMMODITY -2.412, CRYPTO -0.143, FOREX -1.406. Only EQUITY (+3.527) and ETF (+6.368) are positive. Negative Sharpe means the OOS strategy loses money on a risk-adjusted basis. The dashboard displays these without any alarm state (only color coding: red < 0). No remediation action is linked. | **P1 High** | For any asset class with OOS Sharpe < 0, auto-populate a "Halt new entries" recommendation in the summary card. The dashboard currently shows these red Sharpe values passively; they should trigger the same alert severity as the 7d WR dropouts. | Live /audit/ walk-forward table |
| 5 | **Score 60–79 inversion must be recalibrated** | CRYPTO (scoring system) | **Broken** | Deep analysis report (2026-04-06) identified **Score 60–79 bucket shows NEGATIVE returns (-0.11%) with 39.8% WR** — higher score = worse performance. This affects 191 trades (9.8% of volume). No evidence of recalibration in any update doc. | **P1 High** | Implement direction multiplier per the deep analysis recommendation: apply +20% to SHORT scores, -20% to LONG scores. Republish the score distribution after recalibration and verify the 60–79 bucket lifts above the 40–59 bucket. | `ASSET_CLASS_DEEP_ANALYSIS_REPORT.md` §4 Flaw #1, §7 P1 #4 |

### Gaps 6–10: Risk-Adjusted Metrics & Charter Compliance

| # | Requirement | Asset Class | Current Status | Gap Description | Priority | Suggested Fix | Evidence |
|---|-------------|-------------|----------------|-------------------|----------|---------------|----------|
| 6 | **Phase 4 risk-adjusted metrics pipeline must ship before any headline banner** | All | **Missing** | `REMAINING_ENHANCEMENT_PROPOSALS_V3_2026_04_20.md` §Phase 4 gates any future banner on: (1) Sharpe, (2) Max DD, (3) Net-of-cost PF, (4) Expectancy in R, (5) Regime decomposition 3×3 grid, (6) 95% CI on PF via block-bootstrap. Live dashboard still says: *"Risk-adjusted metrics (Sharpe, max DD, net-of-cost PF, regime decomposition) pending — no headline point-estimate claims until they land."* | **P1 High** | Schedule Phase 4. Effort estimate: 3–5 days. The v3 doc explicitly says "Only once all six are computed and freshened weekly should a headline number appear on /audit." Until then, the current headline numbers violate the project's own governance. | `REMAINING_ENHANCEMENT_PROPOSALS_V3_2026_04_20.md` §Phase 4; live /audit/ disclaimer |
| 7 | **Tier-2 proven strategies must meet CHARTER §2 n≥100 floor** | CRYPTO | **Partial** | `TIER-2 PROVEN` section shows 4 strategies. Only **signal_validation** (n=184) clears the 100-pick floor. **mega_mutation** (n=79), **rl_agent** (n=5), and **claude_gainer** (n=32) are all below floor. The dashboard correctly flags these as "THIN" and "Building" but still labels the section "TIER-2 PROVEN" — a contradiction. | **P1 High** | Either (a) rename section to "TIER-2 CANDIDATES" while n<100, or (b) suppress strategies below floor from the tier badge display until they graduate. Do not use the word "PROVEN" for n=5. | `PERFORMANCE_CHARTER.md` §2; live /audit/ TIER-2 PROVEN section |
| 8 | **Trust scores must not be inverted** | All | **Broken** | Deep analysis found **"Trust scores are INVERTED — low trust picks outperform high trust by 0.24%"**. High trust (7–10) avg +0.45%; Low trust (0–5) avg +0.69%. No update doc mentions a fix. | **P2 Medium** | Investigate whether the trust-weighting formula over-penalizes new sandbox systems that actually perform well. Publish a trust-score calibration study with before/after inversion metrics. | `ASSET_CLASS_DEEP_ANALYSIS_REPORT.md` §5, §7 P1 #5 |
| 9 | **MFE/MAE schema must be populated for survivable-DD analysis** | All | **Missing** | v3 Phase 6 requires `max_favorable_excursion_pct` and `max_adverse_excursion_pct` on closed rows. Without MFE/MAE, the dashboard cannot answer "survivable DD?" for position sizing. Schema exists in blueprint but no evidence of upstream writer plumbing. | **P2 Medium** | Add MFE/MAE fields to `_CLOSED_PICK_KEEP_FIELDS`. Update TP/SL resolution writers to populate them. Effort: 2–3 days. Defer if no position-sizing recommendations are imminent. | `REMAINING_ENHANCEMENT_PROPOSALS_V3_2026_04_20.md` §Phase 6 |
| 10 | **Regime decomposition grid must be visible** | All | **Missing** | Phase 4 requirement: "3×3 grid (F&G bucket × BTC-trend regime). Flag any cell with n<10." No grid exists on the live page. Without it, users cannot tell if a headline PF was earned in one favorable regime or is robust across regimes. | **P2 Medium** | Add a collapsible "Regime Decomposition" panel to /audit/. Compute the 3×3 grid weekly and flag cells with n<10 in grey. This gates headline claims per the project's own rules. | `REMAINING_ENHANCEMENT_PROPOSALS_V3_2026_04_20.md` §Phase 4 |

### Gaps 11–15: HyroTracker Specific

| # | Requirement | Asset Class | Current Status | Gap Description | Priority | Suggested Fix | Evidence |
|---|-------------|-------------|----------------|-------------------|----------|---------------|----------|
| 11 | **Trading days logged must reflect actual trading activity** | HyroTrader | **Broken** | `trading_days_logged: 0` in `hyrotrader_picks.json` despite account snapshot showing `cumulative_pnl_usdt: -70.66` and `last_session_date: 2026-04-08`. The note says *"increment trading_days_logged when Hyro counts a day"* but no one has updated it. The dashboard displays "0" without any warning that manual entry is required. | **P0 Critical** | Add a red banner when `trading_days_logged == 0` but `cumulative_pnl_usdt != 0`, stating: "Manual data entry required — update `trading_days_logged` in `hyrotrader_picks.json`." Or better: infer trading days from `hyrotrader_journal.json` trade timestamps. | Live /audit/hyrotrader/; `audit_dashboard/data/hyrotrader_picks.json` `account_snapshot` |
| 12 | **`hyrotrader_journal.json` must be written and linked** | HyroTrader | **Missing** | Strategy doc mandates: *"Log all trades in hyrotrader_journal.json"*. The playbook JSON says the same. No `hyrotrader_journal.json` is referenced in the dashboard data sources list. Trading days = 0 implies the journal either does not exist or is empty. | **P1 High** | Create `audit_dashboard/data/hyrotrader_journal.json` with schema: `[{date, symbol, direction, entry, stop, target, exit, r_multiple, daily_cum}]`. Populate from the trade log template in `HYROTRADER_CHALLENGE_STRATEGY.md`. Update the dashboard to read from this file for trading-days computation. | `docs/HYROTRADER_CHALLENGE_STRATEGY.md` §Trade log template; live page |
| 13 | **Consistency bar requires `largest_single_day_profit_usdt`** | HyroTrader | **Broken** | `largest_single_day_profit_usdt: null` in `account_snapshot`. The consistency rule says *"No day > 40% of eval profit"* (~$200 P1 / ~$100 P2). Without the largest-day value, the dashboard cannot compute whether the trader is compliant. The page shows: *"Consistency: set largest_single_day_profit_usdt in account_snapshot when you know your best eval day"* — a passive prompt instead of a data field. | **P1 High** | Populate `largest_single_day_profit_usdt` from `hyrotrader_journal.json` max daily PnL. If null, show a yellow "Incomplete data" warning on the consistency bar instead of the current silent null. | `audit_dashboard/data/hyrotrader_picks.json`; live /audit/hyrotrader/ |
| 14 | **Entry prices, stop loss, and take profit must be populated** | HyroTrader | **Broken** | All 6+ picks in `hyrotrader_picks.json` have `entry_price`, `stop_loss`, `take_profit` all `null`. The 2026-04-19 dashboard fix said to run `python tools/hyro_filter_from_dashboard.py --save` to populate from audit, but no evidence this was run. The live page still shows empty price fields for all picks. | **P1 High** | Run the validator with closed-picks enrichment as documented: `python tools/hyro_pick_performance_validator.py --save --lookback-days 30`. Then backfill `entry_price`, `stop_loss`, `take_profit` from the pre-validated signal data. If prices remain null after enrichment, show a "Price data unavailable — run validator" banner. | `updates/2026-04-19-hyrotrader-audit-dashboard-fixes.md`; live /audit/hyrotrader/ |
| 15 | **HyroTrader quan bridge must serve all 15 symbols** | HyroTrader | **Broken** | `hyro_quan_bridge.json` is **truncated** — only `BTCUSDT` present; the `_repair_note` says *"ETH+13 symbols dropped. Next GHA run will regenerate with atomic write."* The freshness test (`hyrotrader_live_freshness.spec.ts`) requires all 15 symbols. The `generated_at` is 2026-04-18, which is >48h stale. | **P0 Critical** | Fix the atomic-write logic in `tools/hyro_quan_bridge.py` so truncation never reaches production. Add a post-write validation step that asserts `len(symbols) == 15` before git-commit. Run the workflow immediately to regenerate the full bridge. | `audit_dashboard/data/hyro_quan_bridge.json`; `tests/hyrotrader_live_freshness.spec.ts` |

### Gaps 16–18: Pipeline / Workflow / Data Freshness

| # | Requirement | Asset Class | Current Status | Gap Description | Priority | Suggested Fix | Evidence |
|---|-------------|-------------|----------------|-------------------|----------|---------------|----------|
| 16 | **Stale-data quality gate must block commits, not just warn** | HyroTrader | **Partial** | The 2026-04-14 stale-data fix added a quality gate: *"Blocks commit if ≥2 key files are stale"*. However, the 2026-04-21 edge-failures report still found `hyro_quan_bridge.json` (3 days stale) and `hyro_pick_performance.json` (2 days stale) in production. The gate may not be running, or the threshold is too permissive. | **P1 High** | Lower the stale threshold from "≥2 files" to "≥1 file" for the quan bridge (most critical). Add a dashboard banner when any Hyro JSON is >24h old. The gate should fail the GHA job (red X) so stale data never deploys. | `updates/2026-04-14-hyrotrader-stale-data-fix.md`; `updates/2026-04-21-hyrotrader-edge-failures-fixes.md` |
| 17 | **FOREX must have a documented remediation plan or be killed** | FOREX | **Missing** | Summary card says *"Sub-floor; investigate-before-kill"* but no remediation plan is linked. The blueprint does not list any FOREX-specific strategy fixes. `ASSET_CLASS_EDGE_ANALYSIS.json` shows only 7 FOREX trades (n=7, WR 28.6%, avg -0.42%). The deep analysis says FOREX had 0% WR on 5 trades. There is no path from PF 0.27 to T3 floor (PF>1.2). | **P1 High** | Publish a dated FOREX remediation plan with 3 options: (a) disable all FOREX emitters and reallocate to CRYPTO/EQUITY, (b) apply the deep-analysis SHORT bias (+25% position size) to FOREX if direction data exists, or (c) set a kill date (e.g., 2026-05-15) if no improvement. Do not leave "investigate-before-kill" as a permanent state. | Live /audit/ FOREX card; `ASSET_CLASS_EDGE_ANALYSIS.json`; `ASSET_CLASS_DEEP_ANALYSIS_REPORT.md` §7 P0 #3 |
| 18 | **`ASSET_CLASS_EDGE_ANALYSIS.json` must stay in sync with live data** | All | **Broken** | The JSON shows CRYPTO n=2670, FOREX n=7, NON-CRYPTO n=488. Live dashboard shows CRYPTO n=8067, FOREX n=1169, EQUITY n=421, etc. The JSON is stale by a factor of ~3× for CRYPTO and ~167× for FOREX. Any downstream consumers of this file (e.g., scoring weights, position sizing) are using obsolete sample sizes. | **P2 Medium** | Regenerate `ASSET_CLASS_EDGE_ANALYSIS.json` from the latest closed-picks database (`ejaguiar1_stocks` or `data/audit_trail.db`) on every daily run. Add a CI check that fails if the JSON is >7 days older than the newest closed pick. | `ASSET_CLASS_EDGE_ANALYSIS.json`; live /audit/ summary cards |

---

## Top 10 Gaps Prioritized (Summary)

| Rank | Gap | Asset / Scope | Priority | Business Impact |
|------|-----|---------------|----------|-----------------|
| 1 | **FOREX headline vs. breakdown PF discrepancy** (5.2×) | FOREX | **P0** | Destroys credibility; users cannot trust any metric if the same page contradicts itself |
| 2 | **EQUITY headline "T2 candidate" vs. deep-analysis blacklist** | EQUITY | **P0** | Risk of scaling capital into a class previously flagged as "toxic" with no published bridge study |
| 3 | **HyroTrader `trading_days_logged = 0`** | HyroTrader | **P0** | Challenge compliance cannot be verified; min 10 trading days rule is invisible |
| 4 | **HyroTrader quan bridge truncated to 1 symbol** | HyroTrader | **P0** | 14 of 15 symbols missing; consensus engine, risk gate, and live scanner all broken |
| 5 | **Phase 4 risk-adjusted metrics entirely missing** | All | **P1** | Headline numbers violate project's own governance; no Sharpe, DD, net-of-cost PF, regime decomp |
| 6 | **Tier-2 "PROVEN" badge applied to n=5 strategies** | CRYPTO | **P1** | CHARTER §2 requires n≥100; mislabeling unproven strategies as proven is a compliance violation |
| 7 | **Score 60–79 inversion never recalibrated** | CRYPTO | **P1** | 9.8% of volume receives inverted signals; users sizing on mid-tier scores are systematically misled |
| 8 | **FOREX has no kill/remediation plan** | FOREX | **P1** | PF 0.27 is irrecoverably below T3 floor; "investigate-before-kill" is an indefinite holding pattern |
| 9 | **HyroTrader journal missing / empty** | HyroTrader | **P1** | No trade log means no reproducibility, no consistency check, no trading-days inference |
| 10 | **OOS Sharpe negative for 3/5 classes with no action** | CRYPTO, COMMODITY, FOREX | **P1** | Negative Sharpe = risk-adjusted losses; dashboard displays these passively instead of halting entries |

---

## Cross-Reference Matrix: Doc → Implementation

| Document | Key Requirement | Implementation Status | Gap # |
|----------|---------------|----------------------|-------|
| `AUDIT_BLUEPRINT.md` | SQLite + MySQL dual schema, filter funnel, dedup | **Implemented** | — |
| `REMAINING_ENHANCEMENT_PROPOSALS_V3_2026_04_20.md` | Phase 0 descriptive legend (no PF banner) | **Implemented** | — |
| `REMAINING_ENHANCEMENT_PROPOSALS_V3_2026_04_20.md` | Phase 1 at-issue stamping | **Unknown** — no evidence visible | 6 (indirect) |
| `REMAINING_ENHANCEMENT_PROPOSALS_V3_2026_04_20.md` | Phase 4 risk-adjusted metrics (gates banners) | **Missing** | 6 |
| `REMAINING_ENHANCEMENT_PROPOSALS_V3_2026_04_20.md` | Phase 5 Wilson LB ≥ 0.52, n ≥ 50, hysteresis | **Unknown** — no evidence visible | — |
| `REMAINING_ENHANCEMENT_PROPOSALS_V3_2026_04_20.md` | Phase 6 MFE/MAE schema | **Missing** | 9 |
| `ASSET_CLASS_DEEP_ANALYSIS_REPORT.md` | Disable ml_crypto_predictor, apply SHORT bias, blacklist EQUITY, recalibrate 60–79 | **Partial** — ml_crypto_predictor still appears in systems list; SHORT bias & recalibration not visible | 2, 5, 7 |
| `HYROTRADER_CHALLENGE_STRATEGY.md` | 0.75% risk/trade, 5-day minimum, log all trades, SL before entry | **Partial** — risk reduced to 0.50% (justified by DD), but **journal missing** | 11, 12, 13 |
| `HYROTRADER_PIPELINE_FIXES.md` | Pipeline fixes (not fully fetched, but updates/ cover fixes) | **Partial** — stale data fix deployed Apr 14, but edge failures persist Apr 21 | 15, 16 |
| `updates/2026-04-14-hyrotrader-stale-data-fix.md` | Auto-commit, quality gate, 3 missing scripts added to GHA | **Deployed** | — |
| `updates/2026-04-19-hyrotrader-audit-dashboard-fixes.md` | Closed-picks source for validator, NO_DATA dimming, ML sparse notice | **Deployed** | — |
| `updates/2026-04-21-hyrotrader-edge-failures-fixes.md` | Hourly refresh, consensus threshold 0.45→0.35, strength filter | **Not deployed** — quan bridge still stale, threshold still 0.45 | 15, 16 |
| `tests/hyrotrader_live_freshness.spec.ts` | <48h data, 15 symbols, 12 strategies, no JS errors | **Failing** — quan bridge >48h stale, truncated to 1 symbol | 15 |
| `tests/hyrotrader_tracker.spec.ts` | Tracker tests (not fully fetched) | **Unknown** | — |

---

## Recommended Immediate Actions (Next 48 Hours)

1. **Reconcile FOREX metrics** — run a single SQL query comparing `asset_class_health` (dashboard_data.json source) vs. live pick aggregation. Publish the diff publicly.
2. **Regenerate `hyro_quan_bridge.json`** — fix atomic-write truncation, validate 15 symbols before deploy.
3. **Update `hyrotrader_picks.json`** — set `trading_days_logged` to the actual Hyro T-days count; populate `largest_single_day_profit_usdt` from journal or manual input.
4. **Publish EQUITY bridge study** — if EQUITY truly improved from PF 0.26 to 1.41, show the before/after trade list and the fix applied.
5. **Add dashboard alarm for negative OOS Sharpe** — treat COMMODITY (-2.412), CRYPTO (-0.143), FOREX (-1.406) the same as 7d WR dropouts: red banner, "Halt new entries."

---

*End of Audit Gap Analysis*
