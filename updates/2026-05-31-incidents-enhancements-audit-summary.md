# Incidents & Enhancements Audit Summary — 2026-05-31

**Status:** Database audit complete. 49 incidents + 75 enhancements extracted from MySQL. Ready for PR mapping and implementation.

---

## Executive Summary

The incidents/enhancements dashboard (`https://findtorontoevents.ca/audit/incidents.html`) is backed by 18 MySQL tables (9 INCIDENT_* + 9 ENHANCEMENT_* for asset classes: OVERALL, STOCKS, ETFS, CRYPTO, FOREX, COMMODITIES, BONDS, FUTURES, PENNY).

**Current State:**
- **49 incidents** across all classes (26 OVERALL, 4 STOCKS, 1 ETFS, 4 CRYPTO, 4 FOREX, 4 COMMODITIES, 2 BONDS, 2 FUTURES, 2 PENNY)
- **75 enhancements** across all classes (52 OVERALL, 3 STOCKS, 3 ETFS, 3 CRYPTO, 2 FOREX, 3 COMMODITIES, 6 BONDS, 2 FUTURES, 1 PENNY)
- **1 RESOLVED incident** (false alarm: forward_validator frozen 270h → actually misread of bt_backtest_trades row count)
- **25 OPEN incidents** (highest priority)
- **19 TRIAGED incidents** (medium priority)
- **3 IN_PROGRESS incidents** (actively being worked)

---

## Database Schema

### INCIDENT_* Tables (9 total)
**Columns:** incident_id, asset_class, source_ref, title, description, severity (P0/P1/P2/P3/INFO), status (OPEN/TRIAGED/IN_PROGRESS/RESOLVED/WONTFIX/DUPLICATE), affected_component, reported_by, assigned_to, recommended_fix, target_release, evidence (JSON), resolution_notes, duplicate_of, created_at, date_est, time_est, updated_at, resolved_at, link_md_path, link_url, link_github_ref

### ENHANCEMENT_* Tables (9 total)
**Columns:** enhancement_id, asset_class, source_ref, title, description, category (SCORING/GATE/DATA_FEED/UI/METHODOLOGY/PERSONA/OTHER), expected_impact (HIGH/MEDIUM/LOW/UNKNOWN), effort (S/M/L/XL), status (BACKLOG/VALIDATED/ACCEPTED/IMPLEMENTED/REJECTED/SUPERSEDED), proposed_by, related_persona_id, proposed_features (JSON), success_metric, target_release, review_notes, implementation_pr, created_at, updated_at, implemented_at, link_md_path, link_url, link_github_ref, enhancement_plan

---

## Critical P0 Incidents (Highest Priority)

### 1. **trust_score NULL on 99.99% of closed picks** (OVERALL)
- **Severity:** P0 | **Status:** OPEN
- **Component:** trading_picks.trust_score / audit_dashboard/hc_filter.js
- **Issue:** 38,884 of 38,889 closed picks have NULL trust_score. HC overlay requires trust_score>=4 (CRYPTO) / >=5 (EQUITY). Stats unreproducible.
- **Fix:** Backfill trust_score from strategy registry OR move HC gate to elite_score / derived TRUST tier
- **Effort:** M | **Impact:** HIGH
- **Files:** `audit_dashboard/hc_filter.js`, `tools/dashboard_hc_rules.py`, `alpha_engine/strategy_registry.py`

### 2. **5 FOREX rows have pnl_pct < -100%** (OVERALL)
- **Severity:** P0 | **Status:** OPEN
- **Component:** trading_picks.pnl_pct (FOREX category)
- **Issue:** Unit-clamp bug missed 5 rows (one at -106,700%). Distorts FOREX avg to -8%.
- **Fix:** `UPDATE trading_picks SET pnl_pct = -100 WHERE pnl_pct < -100 AND category='FOREX'`
- **Effort:** S | **Impact:** HIGH
- **Files:** `alpha_engine/score_booster.py`, `tools/audit_pick_funnel/render_incidents_page.py`

### 3. **signal_outcomes table 82 days stale** (OVERALL)
- **Severity:** P0 | **Status:** OPEN
- **Component:** at_signal_outcomes / outcome resolver pipeline
- **Issue:** Last resolved 2026-03-04. Outcome resolver pipeline appears dead. All forward-WR claims unverifiable.
- **Fix:** Investigate why resolver stopped writing. Possibly tied to broken cron, env-var rotation, or schema drift.
- **Effort:** L | **Impact:** HIGH
- **Files:** `.github/workflows/outcome-resolver.yml`, `alpha_engine/forward_validator.py`, `tools/audit_pick_funnel/render_incidents_page.py`

### 4. **COT paper pilot over-emission** (OVERALL)
- **Severity:** P0 | **Status:** OPEN
- **Component:** cot_paper_pilot.py / cot_positioning strategy
- **Issue:** Counts same weekly CFTC release as ~100 separate trades. Inflates n from ~5 to 101. DSR=1.0/WR=86.5% overstated.
- **Fix:** Deduplicate by CFTC release week. Recompute DSR + WR + PF on deduped n.
- **Effort:** M | **Impact:** HIGH
- **Files:** `alpha_engine/cot_paper_pilot.py`, `alpha_engine/cot_positioning.py`

### 5. **ML calibration system-wide inverted** (OVERALL)
- **Severity:** P0 | **Status:** TRIAGED
- **Component:** smart_picks_engine.py / score derivation
- **Issue:** Confidence is anti-predictive: conf>=0.9 → WR 14.4%, conf 0.5-0.6 → WR 60.3%. Top-of-funnel ranker structurally flipped.
- **Fix:** Invert confidence contribution for crypto (or use trust_score as primary signal). Validate across other classes.
- **Effort:** M | **Impact:** HIGH
- **Files:** `alpha_engine/smart_picks_engine.py`, `alpha_engine/score_booster.py`

### 6. **PnL integrity mismatch on 38.97% of sampled closed picks** (OVERALL)
- **Severity:** P0 | **Status:** OPEN
- **Component:** trading_picks.pnl_pct integrity
- **Issue:** 10,501 / 26,945 sampled rows have >1% pnl discrepancy between stored pnl_pct and recomputed (entry/exit/direction). All cohort WR/PF stats suspect.
- **Fix:** Re-resolve historical closed picks via re_resolve_historical_v2.py. Quantify per-strategy drift and re-publish asset_class_health.
- **Effort:** L | **Impact:** HIGH
- **Files:** `alpha_engine/forward_validator.py`, `tools/audit_pick_funnel/render_incidents_page.py`

### 7. **WON status rows show avg pnl_pct = -41.1%** (OVERALL)
- **Severity:** P0 | **Status:** OPEN
- **Component:** trading_picks.status='WON' rows
- **Issue:** 2,531 rows tagged status='WON' have avg_pnl=-41.13%, 9 with negative pnl. Every claim using status='WON' as win flag is corrupted.
- **Fix:** Re-label legacy 'WON' rows by recomputing from pnl_pct sign + exit_reason. WON→TP_HIT where pnl>0, WON→LOST where pnl<=0. Add CHECK constraint.
- **Effort:** M | **Impact:** HIGH
- **Files:** `alpha_engine/forward_validator.py`, `tools/audit_pick_funnel/render_incidents_page.py`

### 8. **56,559 ghost rows in trading_picks** (OVERALL)
- **Severity:** P0 | **Status:** OPEN
- **Component:** trading_picks ghost-row write path
- **Issue:** 12 cohorts with thousands of identical (asset_class, strategy, symbol, direction, pnl_pct) rows. Top: CRYPTO/quan_engine/MATICUSDT/LONG/pnl=-15.0 with n=20,474 from 1 distinct entry. Dragging quan_engine_scalp to PF 0.42 / WR 37%.
- **Fix:** DEDUP via (asset_class, strategy, symbol, direction, pnl_pct, created_at) where distinct_entries=1 and n>50. Investigate quan_engine + meta_strategy writers.
- **Effort:** L | **Impact:** HIGH
- **Files:** `alpha_engine/quan_engine_scalp.py`, `alpha_engine/meta_strategy.py`, `tools/audit_pick_funnel/render_incidents_page.py`

### 9. **sync_active_mysql_picks_to_json upstream writer missing** (OVERALL)
- **Severity:** P0 | **Status:** OPEN
- **Component:** alpha_engine/active_picks_sync.py (proposed) + forward_validator.validate_picks()
- **Issue:** Missing upstream writer that should read ACTIVE at_raw_picks, detect TP/SL/time-exit per asset class, and feed new entries into closed_picks.json. signal_outcomes has 0.09% coverage of raw picks.
- **Fix:** New module alpha_engine/active_picks_sync.py invoked inline from forward_validator. Reuses existing failover price fetchers. Estimate 2-3h with tests.
- **Effort:** L | **Impact:** HIGH
- **Files:** `alpha_engine/forward_validator.py`, `alpha_engine/active_picks_sync.py` (new)

### 10. **Cherry-picked SUPREME EDGE stats surfaced without caveat** (OVERALL)
- **Severity:** P0 | **Status:** OPEN
- **Component:** audit_dashboard/template.html SUPREME EDGE block
- **Issue:** Numbers come from cell-by-cell search across (confidence × R:R × strategy family) buckets. Not actionable forward signals but presented as if they were.
- **Fix:** Add 'post-hoc segment search — not an actionable forward signal; for narrative only' caveat to every cell from top_edges_per_class.json. Pin actual forward-test WR/PF alongside.
- **Effort:** S | **Impact:** HIGH
- **Files:** `audit_dashboard/template.html`, `audit_dashboard/blueprint_generator.py`

### 11. **smart_picks_engine weights confidence-derived elite/quality at 35%** (OVERALL)
- **Severity:** P0 | **Status:** OPEN
- **Component:** alpha_engine/smart_picks_engine.py
- **Issue:** Ranker formula bakes inverted signal into headline score with largest weight. Downstream of calibration bug but separate fix.
- **Fix:** Either (a) invert confidence contribution for crypto in _single_signal_score, or (b) replace confidence with trust_score as primary signal. Quantify lift via paired-bootstrap.
- **Effort:** M | **Impact:** HIGH
- **Files:** `alpha_engine/smart_picks_engine.py`, `alpha_engine/score_booster.py`

### 12. **Profitable-but-filtered picks not surfaced anywhere** (OVERALL)
- **Severity:** P0 | **Status:** OPEN
- **Component:** audit_trail/quality_gates.py + dashboard_generator.py audit surfaces
- **Issue:** Current audit pipeline shows rejects in aggregate but provides no durable lane for picks that failed gates and later would have won materially.
- **Fix:** Add profitable-but-filtered / profitable-but-quarantined audit lane with per-pick first-failed gate, later outcome, and asset-class rollups. Keep observational first.
- **Effort:** L | **Impact:** HIGH
- **Files:** `audit_trail/quality_gates.py`, `audit_trail/dashboard_generator.py`, `audit_dashboard/template.html`

### 13. **HC JS/Python parity drift can change eligibility by surface** (OVERALL)
- **Severity:** P0 | **Status:** OPEN
- **Component:** audit_dashboard/hc_filter.js / tools/dashboard_hc_rules.py
- **Issue:** High Conviction decision path split across JS and Python. Likely drift around confidence handling and small-sample relaxations.
- **Fix:** Create one canonical HC parameter contract and parity test corpus. Until parity proven, treat HC disagreements as first-class incident.
- **Effort:** M | **Impact:** HIGH
- **Files:** `audit_dashboard/hc_filter.js`, `tools/dashboard_hc_rules.py`

### 14. **Antigravity_bond: 0% WR on n=9 — kill emission** (BONDS)
- **Severity:** P0 | **Status:** OPEN
- **Component:** alpha_engine antigravity_bond
- **Issue:** BOND class is 0% WR / PF 0.00 / Sharpe -2.465. Only strategy is antigravity_bond with 1 historical pick.
- **Fix:** Kill BOND emission entirely. Re-enable only after viable yield-curve or duration strategy is built.
- **Effort:** S | **Impact:** HIGH
- **Files:** `alpha_engine/antigravity_bond.py`, `alpha_engine/config.py`

### 15. **Class-level COMMODITY 11.9% WR / PF 0.29 / Sharpe -0.534** (COMMODITIES)
- **Severity:** P0 | **Status:** OPEN
- **Component:** alpha_engine commodity strategies (post cot_positioning block)
- **Issue:** cot_positioning at STRATEGY level is strong (DSR=1.0 per Ring) but at CLASS level catastrophic because cot_positioning is BLOCKED and remaining strategies are losers.
- **Fix:** Retire all remaining COMMODITY strategies. Rebuild from non-COT signals (term structure, EIA inventory, weather overlay). Reconcile Ring 'DSR=1.0' vs audit 'BLOCKED' claim.
- **Effort:** L | **Impact:** HIGH
- **Files:** `alpha_engine/cta_cross_asset_tsmom.py`, `alpha_engine/cta_commodity_momentum_term.py`

### 16. **Reconcile: cot_positioning DSR=1.0 (Ring) vs BLOCKED (audit benchmark)** (COMMODITIES)
- **Severity:** P0 | **Status:** OPEN
- **Component:** cot_positioning evaluation (pipeline vs paper-pilot vs class aggregate)
- **Issue:** Ring's 2026-05-25 audit says cot_positioning is SUPREME EDGE (DSR=1.0, WR=86.5%, n=104). audit_benchmark says BLOCKED and downgraded to WR 5% / PF 0.12 on n=20 post-dedup.
- **Fix:** Run COT-dedup audit live, compute n + WR + PF under (a) raw, (b) deduped-by-release-week, (c) cot_paper_pilot-only sleeve. Publish truth-table.
- **Effort:** M | **Impact:** HIGH
- **Files:** `alpha_engine/cot_positioning.py`, `alpha_engine/cot_paper_pilot.py`

### 17. **COMMODITY headline PF/WR contaminated by pre-clean COT aggregation** (COMMODITIES)
- **Severity:** P0 | **Status:** OPEN
- **Component:** COMMODITY class-health aggregation / COT-derived history
- **Issue:** Class story remains unsafe while pre-clean or over-emitted COT history can still dominate class-level PF/WR claims.
- **Fix:** Recompute class health from deduped independent COT cycles only, then re-derive honest class verdict. Block promotional Tier claims until cleaned aggregation is live source of truth.
- **Effort:** M | **Impact:** HIGH
- **Files:** `audit_trail/dashboard_generator.py`, `alpha_engine/cot_positioning.py`

### 18. **All FOREX strategies losers except cta_cross_asset_tsmom SHORT** (FOREX)
- **Severity:** P0 | **Status:** OPEN
- **Component:** alpha_engine FOREX strategies (concentration risk)
- **Issue:** forex_carry_momentum, forex_rsi2_mean_reversion, myfxbook_retail_contrarian all losing. Only cta_cross_asset_tsmom SHORT has WR 57.6% but is 93% concentrated in USDJPY.
- **Fix:** Block all FOREX strategies except cta_cross_asset_tsmom SHORT. Force symbol diversification on that one (cap USDJPY at <50%). Add forex_carry as second leg.
- **Effort:** M | **Impact:** HIGH
- **Files:** `alpha_engine/config.py`, `alpha_engine/non_crypto_policy.py`

### 19. **Multi-AI panel reached wrong COMMODITY consensus on ungrounded prompt** (OVERALL)
- **Severity:** P1 | **Status:** OPEN
- **Component:** tools/swarm/api_consult.py + consult-nvidia-models / consult-cloudflare-models skills
- **Issue:** 5-engine NVIDIA NIM panel unanimously declared COMMODITY #1 alpha. 3-engine codex/grok/gemini panel (shown same numbers PLUS leakage signals) classified as DATA_QUALITY_LEAKAGE. In-house verification confirmed leakage panel.
- **Fix:** Mandate inclusion of reports/hypothesis_registry.json rejected-hypothesis entries. Update consult-nvidia-models/SKILL.md + consult-cloudflare-models/SKILL.md to require leakage-context block in every prompt template.
- **Effort:** S | **Impact:** HIGH
- **Files:** `tools/swarm/api_consult.py`, `skills/consult-nvidia-models/SKILL.md`, `skills/consult-cloudflare-models/SKILL.md`

---

## High-Priority P1 Incidents (Medium Priority)

### 20. **ML 'edges' with PF 99-1094 are likely look-ahead leakage** (CRYPTO)
- **Severity:** P1 | **Status:** TRIAGED
- **Component:** alpha_engine ml_enhanced_* family / copy_trader_intel feature pipeline
- **Issue:** Cells like 'copy_trader_intel & LONG' (n=21, PF 1094) and 'conf=0.80-0.85 & ml' (n=42, PF 674) indicate look-ahead bias, not real edge.
- **Fix:** Audit feature pipeline for look-ahead bias. Add walk-forward gate before any ML strategy claims edge. Mark current 'DSR=0.9995' claims as 'small-sample, awaiting n>=100 confirmation'.
- **Effort:** L | **Impact:** HIGH
- **Files:** `alpha_engine/ml_enhanced_*.py`, `alpha_engine/copy_trader_intel.py`

### 21. **quan_engine_scalp degraded to PF 0.42 / WR 37%** (CRYPTO)
- **Severity:** P1 | **Status:** OPEN
- **Component:** alpha_engine quan_engine_scalp emitter
- **Issue:** n=4236, WR 37.4%, PF 0.42 — verdict 'dead'. Yet substantial share of open CRYPTO volume.
- **Fix:** Per mutation-three-axis protocol: cut volume share, mutate, or kill. Required to lift CRYPTO class PF above T2 threshold.
- **Effort:** M | **Impact:** HIGH
- **Files:** `alpha_engine/quan_engine_scalp.py`, `alpha_engine/config.py`

### 22. **meta_strategy template explosion — 1.6M template rows** (CRYPTO)
- **Severity:** P1 | **Status:** TRIAGED
- **Component:** meta_strategy emitter / bt_backtest_trades writer
- **Issue:** 1.6M template rows from meta_strategy across MEMECOIN/CRYPTO symbol+direction pairs. Same root cause as ghost-rows finding.
- **Fix:** Wait 1-2 cron cycles for db_health refresh post-commit d317560ac9c. Then decide: blanket-block meta_strategy on CRYPTO/MEMECOIN OR symbol-triple enumeration.
- **Effort:** M | **Impact:** HIGH
- **Files:** `alpha_engine/meta_strategy.py`, `alpha_engine/config.py`

### 23. **CRYPTO ML strategies DSR>=0.9995 on n=25-34 without 'insufficient n' badge** (CRYPTO)
- **Severity:** P1 | **Status:** OPEN
- **Component:** audit_dashboard/anti_overfit.html / DSR sidecar rendering
- **Issue:** ml_enhanced_INJUSDT_1d_B_lightgbm (n=25 WR 100%), ml_enhanced_DYDXUSDT_15m_D (n=31 WR 96.8%), etc. show DSR>=0.9995 as publishable confidence but n too small.
- **Fix:** Add 'insufficient n — awaiting n>=100' badge to any row with n<100. Reorder so n>=100 rows come first.
- **Effort:** S | **Impact:** MEDIUM
- **Files:** `audit_dashboard/anti_overfit.html`, `audit_dashboard/blueprint_generator.py`

### 24. **Smart Picks 'Signal Time' is dashboard-file age, not pick age** (OVERALL)
- **Severity:** P1 | **Status:** OPEN
- **Component:** audit_trail/dashboard_generator.py (smart_picks_feed builder)
- **Issue:** smart_picks_feed pick objects lack signal_time field. Template logic falls back to age_hours computed at dashboard JSON build time.
- **Fix:** Populate signal_time = trading_picks.created_at on every entry in smart_picks_feed payload. One-line addition.
- **Effort:** S | **Impact:** MEDIUM
- **Files:** `audit_trail/dashboard_generator.py`

### 25. **smart_picks.json file 25 days stale** (OVERALL)
- **Severity:** P0 | **Status:** OPEN
- **Component:** data/smart_picks.json / smart_picks_engine.py
- **Issue:** Last regenerated 2026-04-30T02:56. Dashboard reads smart_picks_feed (more recent ~1.5h) but underlying picks may be cycled with stale entry prices.
- **Fix:** Re-run smart_picks_engine.py and wire to daily cron. Confirm whether dashboard actually reads this file or builds own feed from trading_picks.
- **Effort:** M | **Impact:** HIGH
- **Files:** `alpha_engine/smart_picks_engine.py`, `.github/workflows/smart-picks-nightly.yml`

### 26. **Swarm Picks tab effectively abandoned** (OVERALL)
- **Severity:** P1 | **Status:** OPEN
- **Component:** audit/ Swarm Picks tab / .github/workflows/swarm-pick-review.yml
- **Issue:** data/swarm_picks.json has 38 picks; newest is 2026-05-12 (13 days old). Workflow runs daily but no longer adds picks.
- **Fix:** Either revive multi_model_pick_gen.py so fresh consensus picks flow in, OR deprecate Swarm Picks tab and redirect to /audit/ai-tournament.html.
- **Effort:** M | **Impact:** MEDIUM
- **Files:** `alpha_engine/multi_model_pick_gen.py`, `.github/workflows/swarm-pick-review.yml`

### 27. **forex_carry.py exists in repo but is NOT in allowlist** (FOREX)
- **Severity:** P1 | **Status:** OPEN
- **Component:** alpha_engine/non_crypto_policy.py allowlist
- **Issue:** alpha_engine/new_strategies/forex_carry.py implements G10 interest-rate differential carry with claimed 55-60% WR / PF 1.2-1.5 but not registered in NON_CRYPTO_STRATEGY_POLICY.
- **Fix:** Add forex_carry to NON_CRYPTO_STRATEGY_POLICY with probation thresholds. Document wire-up in updates/.
- **Effort:** S | **Impact:** MEDIUM
- **Files:** `alpha_engine/non_crypto_policy.py`, `alpha_engine/new_strategies/forex_carry.py`

### 28. **FOREX SL at 0.5% sits at median daily FX ATR** (FOREX)
- **Severity:** P1 | **Status:** TRIAGED
- **Component:** alpha_engine FOREX TP/SL config
- **Issue:** Causes 44% SL hit rate vs 12% TP hit (3.7x more stops than targets). After April 2026 widening situation improved but still asymmetric.
- **Fix:** Widen FOREX SL to >=1.0% (or use 1.5x daily ATR). Backtest before deploying.
- **Effort:** M | **Impact:** MEDIUM
- **Files:** `alpha_engine/config.py`, `alpha_engine/forex_*.py`

### 29. **FOREX class still aggregates losers around small winner subset** (FOREX)
- **Severity:** P1 | **Status:** OPEN
- **Component:** FOREX class aggregation / per-sleeve visibility
- **Issue:** EAGLE review found class story dominated by few stronger sleeves while aggregate dragged down by broad losers. Dashboard doesn't expose isolate-the-winner vs kill-the-drag distinction cleanly.
- **Fix:** Add per-sleeve isolation reporting and treat FOREX as basket of sleeves, not monolith. Promote only proven sleeve(s) in audit visibility.
- **Effort:** M | **Impact:** MEDIUM
- **Files:** `audit_trail/dashboard_generator.py`, `audit_dashboard/template.html`

### 30. **summary_picks.json shows identical last_pick_at across all asset classes** (OVERALL)
- **Severity:** P1 | **Status:** OPEN
- **Component:** audit_dashboard/data/summary_picks.json + its writer
- **Issue:** All asset classes report same last-pick timestamp to the second. Statistically implausible — suggests auto-generated/simulated rather than computed from real picks.
- **Fix:** Identify writer of summary_picks.json. If fixture, replace with real query that pulls MAX(created_at) per category. If real query that's bugged, fix GROUP BY.
- **Effort:** S | **Impact:** MEDIUM
- **Files:** `audit_trail/dashboard_generator.py`, `audit_dashboard/blueprint_generator.py`

### 31. **job-health.md self-commit loop spams main** (OVERALL)
- **Severity:** P1 | **Status:** IN_PROGRESS
- **Component:** .github/workflows/branch-large-file-dup-guard.yml
- **Issue:** Prepends timestamped alert + commits updates/job-health.md on every run whenever cross-branch dup blobs exist (always), polluting main history.
- **Fix:** Content-idempotent commit: signature=sorted(blob:branch_count); skip when unchanged.
- **Effort:** S | **Impact:** MEDIUM
- **Files:** `.github/workflows/branch-large-file-dup-guard.yml`

---

## Medium-Priority P2 Incidents (Lower Priority)

### 32. **All 5 ETF strategies on probation with ZERO verified forward trades** (ETFS)
- **Severity:** P2 | **Status:** OPEN
- **Component:** alpha_engine ETF strategies / config
- **Issue:** etf_dual_momentum, etf_sector_momentum, etf_risk_parity_rotation, etf_faber_tactical, etf_trend_following all allow_without_forward=True. No track record.
- **Fix:** Pick one (etf_faber_tactical has strongest academic backing per Ring) and graduate to probation with real forward floor. Document promotion path.
- **Effort:** M | **Impact:** MEDIUM
- **Files:** `alpha_engine/etf_*.py`, `alpha_engine/config.py`

### 33. **cftc_cot_commercial_signal BLOCKED (19% WR on n=16)** (COMMODITIES)
- **Severity:** P2 | **Status:** OPEN
- **Component:** alpha_engine cftc_cot_commercial_signal
- **Issue:** Strategy in code but blocked from production. Either rehab via mutation protocol or formally retire.
- **Fix:** Run mutation analysis (docs/MUTATION_THREE_AXIS_PROTOCOL.md). If no axis recovers, formally retire and remove from allowlist.
- **Effort:** M | **Impact:** MEDIUM
- **Files:** `alpha_engine/cftc_cot_commercial_signal.py`, `alpha_engine/config.py`

### 34. **UNKNOWN asset_class on 951 active + 54 closed picks** (OVERALL)
- **Severity:** P2 | **Status:** OPEN
- **Component:** trading_picks.category writer / classifier
- **Issue:** Category is NULL/UNKNOWN for 951 active picks (~10% of active set) and 54 closed (35.2% WR). UI can't apply per-class gates.
- **Fix:** Backfill UNKNOWN rows using symbol pattern matching (USDT/BTC suffix → CRYPTO; =X suffix → FOREX; etc.). Add classifier guard at write time.
- **Effort:** S | **Impact:** MEDIUM
- **Files:** `alpha_engine/score_booster.py`, `tools/audit_pick_funnel/render_incidents_page.py`

### 35. **IPO asset class advertised as 'tracked' but has zero coverage** (OVERALL)
- **Severity:** P2 | **Status:** OPEN
- **Component:** audit_dashboard tab listing / IPO scanner (missing)
- **Issue:** /audit lists IPO as tracked asset class but codebase has zero IPO-specific strategy or pick writer.
- **Fix:** Either (a) remove IPO claim from UI until writer exists, or (b) build minimal IPO scanner using PEAD framework adapted for lockup expiry + insider selling + revenue trajectory.
- **Effort:** L | **Impact:** LOW
- **Files:** `audit_dashboard/template.html`, `alpha_engine/ipo_scanner.py` (new)

---

## Low-Priority P3 Incidents (Lowest Priority)

### 36. **bond_connors_rsi2 new, probation, no forward trades** (BONDS)
- **Severity:** P3 | **Status:** OPEN
- **Component:** alpha_engine/new_strategies/bond_connors_rsi2.py
- **Issue:** Claims 73% WR but is brand new — needs forward-test data before promotion.
- **Fix:** Run for 60 days in shadow; gate to probation when n>=20 with WR>=55%.
- **Effort:** S | **Impact:** LOW
- **Files:** `alpha_engine/new_strategies/bond_connors_rsi2.py`, `alpha_engine/config.py`

### 37. **futures_mean_reversion and ema_stack_momentum BANNED at 0% WR** (FUTURES)
- **Severity:** P3 | **Status:** OPEN
- **Component:** alpha_engine futures_mean_reversion / ema_stack_momentum
- **Issue:** Both strategies sit in code with BANNED status. Remove from registry to declutter.
- **Fix:** Formal retirement entry. Move source files to deprecated/ subfolder.
- **Effort:** S | **Impact:** LOW
- **Files:** `alpha_engine/futures_mean_reversion.py`, `alpha_engine/ema_stack_momentum.py`

---

## Enhancement Priorities (75 Total)

### HIGH-IMPACT ENHANCEMENTS (Expected Impact: HIGH)

**OVERALL (52 total):**
1. **Update 'forward validator frozen 270h' incident title/description** — Fix misattribution (outcome resolver git add pathspec, not forward_validator)
2. **Fix outcome-resolver.yml git add step** — Pathspec closed_picks.json error blocking signal_outcomes
3. **MySQL sync workflow silent-fail removal** — Remove || echo non-fatal swallow in mysql-trading-sync.yml
4. **Schema drift watchdog nightly workflow** — information_schema snapshot + automated diff vs version-controlled baseline
5. **Fix duplicate leaderboard entries** — source="" inflation + reconcile alpha_engine aggregate loss vs sub-strat buried winners
6. **Fix incidents.html EST timestamps + add enhancement_plan + target_date columns** — Add schema columns + population + generator fixes
7. **triage_dashboard_P0_regression_diff_and_escalation** — Add post-render job showing P0 counts, age>7d escalation, OPEN→RESOLVED→OPEN regressions
8. **append_only_incidents_seed_with_finding_key** — Nightly seed re-inserts destroy triage state; add deterministic finding_key + INSERT ... ON DUPLICATE KEY
9. **Verify the 648-for-0 un-gated-picks claim** — Verify n / WR per quality_tier bucket from raw DB
10. **Runtime _assert_no_lookahead leakage guard in walk-forward harness** — Check columns NaN pre-cutoff AND populated post-cutoff
11. **WON-vs-PnL backfill SQL** — Re-label legacy contradicted rows
12. **Add VIX/realised-vol regime tag at pick submission** — Addresses 7 personas / ~470 picks; ~30% of picks fire in wrong regime
13. **Single-persona swarm-pick backfill + tier-gate** — Backfill 60d for tier=single; promote only if PF>=1.30 & WR>=50% at n>=100
14. **Verify 648-for-0 un-gated-picks claim (DeepSeek session)** — Roo's NIM panel session reports 0-for-648 over 6-day window destroying -825% PnL
15. **Backfill trust_score from strategy registry** — Enable HC overlay to work on 99.99% of closed picks
16. **Add signal_time to smart_picks_feed** — One-line addition to populate signal_time = trading_picks.created_at
17. **Implement research_basis flag** — Add to every pick; gate high-conviction on research_basis=TRUE
18. **Cross-model consensus tier-rating** — Implement 3-tier (CONSENSUS, SPLIT, OUTLIER) based on multi-AI agreement
19. **Pick-funnel rejection visibility** — Add observational lane for profitable-but-filtered picks
20. **Hot-streak exemption** — Implement probation-to-live fast-track for strategies with 20+ consecutive wins
21. **HC JS/Python parity audit** — Create canonical HC parameter contract and parity test corpus

**CRYPTO (3 total):**
1. **Add on-chain + funding-rate feed** — Glassnode + Coinglass integration for BTC/ETH
2. **Funding-Oscillation Pairs MR for BTC-ETH** — Extend pairs_arb with funding divergence + chop/EMA-osc regime filter
3. **High-ADV Chop-Adaptive MR Overlay** — Regime-gated short-term fades on liquid core only

**COMMODITIES (3 total):**
1. **Wire CFTC COT feed** — Execute COT 7-step testing plan
2. **Recompute class health from deduped cycles** — Rebuild from non-COT signals (term structure, EIA inventory, weather overlay)
3. **Reconcile COT DSR=1.0 vs BLOCKED claim** — Run live COT-dedup audit

**BONDS (6 total):**
1. **Wire bond_scanner.py** — Implement yield-curve-momentum strategy
2. **Add yield-curve-momentum** — New strategy for BONDS class
3. **Implement duration strategy** — Re-enable BOND emission after viable strategy built
4. **Backtest bond_connors_rsi2** — 60-day forward test before promotion
5. **Implement bond_carry strategy** — Interest-rate differential carry for bonds
6. **Add credit-spread signal** — High-yield spread momentum for BONDS

**STOCKS (3 total):**
1. **Promote pead_equity from shadow to probation** — Upgrade PEAD equity strategy
2. **Add earnings-surprise signal** — Integrate earnings-beat/miss signals
3. **Implement sector-rotation overlay** — VIX-gated sector rotation for STOCKS

**FOREX (2 total):**
1. **Add forex_carry to allowlist** — Wire up forex_carry.py with probation thresholds
2. **Widen FOREX SL to >=1.0%** — Reduce SL hit rate asymmetry

**FUTURES (2 total):**
1. **Add commodity term-structure roll-yield** — New strategy for FUTURES class
2. **Implement financial-futures scanner** — Unified futures taxonomy

**ETFS (3 total):**
1. **Add real GEX + 0DTE flow data** — Glassnode + Coinglass integration
2. **Make VIX-gated sector rotation primary sleeve** — Upgrade ETF sector rotation
3. **Implement etf_faber_tactical forward test** — Graduate to probation with real forward floor

**PENNY (1 total):**
1. **Implement float-squeeze detector** — Detect low-float high-volume setups

---

## Recommended PR Structure

### PR #1: Critical Data Integrity Fixes (P0 Quick Wins)
**Files:** `alpha_engine/forward_validator.py`, `tools/audit_pick_funnel/render_incidents_page.py`
**Changes:**
- Fix 5 FOREX pnl_pct < -100% rows (unit clamp)
- Re-label 2,531 WON status rows with negative pnl
- Add CHECK constraint on pnl_pct sign coherence
**Effort:** S | **Impact:** HIGH | **Tests:** Existing audit tests

### PR #2: ML Calibration Inversion Fix
**Files:** `alpha_engine/smart_picks_engine.py`, `alpha_engine/score_booster.py`
**Changes:**
- Invert confidence contribution for CRYPTO (or use trust_score as primary)
- Validate across other classes
- Quantify lift via paired-bootstrap on closed picks
**Effort:** M | **Impact:** HIGH | **Tests:** New backtest validation

### PR #3: Ghost Rows Deduplication
**Files:** `alpha_engine/quan_engine_scalp.py`, `alpha_engine/meta_strategy.py`
**Changes:**
- DEDUP 56,559 ghost rows via (asset_class, strategy, symbol, direction, pnl_pct, created_at)
- Investigate quan_engine + meta_strategy writers
- Re-publish asset_class_health post-dedup
**Effort:** L | **Impact:** HIGH | **Tests:** Existing audit tests

### PR #4: Signal Outcomes Pipeline Restoration
**Files:** `.github/workflows/outcome-resolver.yml`, `alpha_engine/forward_validator.py`, `alpha_engine/active_picks_sync.py` (new)
**Changes:**
- Investigate outcome resolver pipeline (82 days stale)
- Implement alpha_engine/active_picks_sync.py upstream writer
- Wire to forward_validator inline
**Effort:** L | **Impact:** HIGH | **Tests:** New integration tests

### PR #5: COT Deduplication & Reconciliation
**Files:** `alpha_engine/cot_positioning.py`, `alpha_engine/cot_paper_pilot.py`
**Changes:**
- Deduplicate by CFTC release week
- Recompute DSR + WR + PF on deduped n
- Reconcile Ring DSR=1.0 vs audit BLOCKED claim
**Effort:** M | **Impact:** HIGH | **Tests:** New COT audit tests

### PR #6: FOREX Strategy Consolidation
**Files:** `alpha_engine/config.py`, `alpha_engine/non_crypto_policy.py`
**Changes:**
- Block all FOREX strategies except cta_cross_asset_tsmom SHORT
- Add forex_carry to allowlist with probation thresholds
- Force symbol diversification (cap USDJPY at <50%)
**Effort:** M | **Impact:** HIGH | **Tests:** Existing config tests

### PR #7: BOND & COMMODITY Class Cleanup
**Files:** `alpha_engine/antigravity_bond.py`, `alpha_engine/config.py`
**Changes:**
- Kill BOND emission (0% WR / PF 0.00)
- Retire COMMODITY strategies (11.9% WR / PF 0.29)
- Document re-enable path for future strategies
**Effort:** S | **Impact:** HIGH | **Tests:** Existing config tests

### PR #8: Dashboard UI & Data Integrity
**Files:** `audit_dashboard/template.html`, `audit_dashboard/blueprint_generator.py`, `audit_trail/dashboard_generator.py`
**Changes:**
- Add 'post-hoc segment search' caveat to SUPREME EDGE block
- Fix summary_picks.json identical last_pick_at bug
- Add 'insufficient n' badge to anti_overfit.html rows with n<100
- Fix smart_picks_feed signal_time (one-line addition)
**Effort:** S | **Impact:** MEDIUM | **Tests:** Existing dashboard tests

### PR #9: Trust Score Backfill & HC Parity
**Files:** `audit_dashboard/hc_filter.js`, `tools/dashboard_hc_rules.py`, `alpha_engine/strategy_registry.py`
**Changes:**
- Backfill trust_score from strategy registry (or move HC gate to elite_score)
- Create canonical HC parameter contract
- Implement parity test corpus
**Effort:** M | **Impact:** HIGH | **Tests:** New HC parity tests

### PR #10: Workflow & Automation Fixes
**Files:** `.github/workflows/outcome-resolver.yml`, `.github/workflows/mysql-trading-sync.yml`, `.github/workflows/branch-large-file-dup-guard.yml`
**Changes:**
- Remove || echo non-fatal swallow in mysql-trading-sync.yml
- Fix outcome-resolver.yml git add pathspec
- Implement content-idempotent commit in branch-large-file-dup-guard.yml
- Add schema drift watchdog nightly workflow
**Effort:** M | **Impact:** HIGH | **Tests:** Existing workflow tests

---

## Next Steps

1. **Create clean branches** for each PR (one per branch)
2. **Implement fixes** in priority order (P0 first, then P1, then P2/P3)
3. **Add update documentation** for each fix in `updates/` directory
4. **Run targeted tests** (existing audit tests + new validation tests)
5. **Submit PRs** with clear commit messages and evidence links
6. **Track resolution** in MySQL incident/enhancement tables

---

## Database Queries for Verification

### Count incidents by severity/status:
```sql
SELECT asset_class, severity, status, COUNT(*) as count
FROM (
  SELECT * FROM INCIDENT_OVERALL UNION ALL
  SELECT * FROM INCIDENT_STOCKS UNION ALL
  SELECT * FROM INCIDENT_ETFS UNION ALL
  SELECT * FROM INCIDENT_CRYPTO UNION ALL
  SELECT * FROM INCIDENT_FOREX UNION ALL
  SELECT * FROM INCIDENT_COMMODITIES UNION ALL
  SELECT * FROM INCIDENT_BONDS UNION ALL
  SELECT * FROM INCIDENT_FUTURES UNION ALL
  SELECT * FROM INCIDENT_PENNY
) vw_all_incidents
GROUP BY asset_class, severity, status
ORDER BY asset_class, severity;
```

### Count enhancements by category/status:
```sql
SELECT asset_class, category, status, COUNT(*) as count
FROM (
  SELECT * FROM ENHANCEMENT_OVERALL UNION ALL
  SELECT * FROM ENHANCEMENT_STOCKS UNION ALL
  SELECT * FROM ENHANCEMENT_ETFS UNION ALL
  SELECT * FROM ENHANCEMENT_CRYPTO UNION ALL
  SELECT * FROM ENHANCEMENT_FOREX UNION ALL
  SELECT * FROM ENHANCEMENT_COMMODITIES UNION ALL
  SELECT * FROM ENHANCEMENT_BONDS UNION ALL
  SELECT * FROM ENHANCEMENT_FUTURES UNION ALL
  SELECT * FROM ENHANCEMENT_PENNY
) vw_all_enhancements
GROUP BY asset_class, category, status
ORDER BY asset_class, category;
```

---

**Document Generated:** 2026-05-31T00:46:00Z
**Audit Inventory:** 49 incidents + 75 enhancements extracted from MySQL
**Status:** Ready for PR implementation
