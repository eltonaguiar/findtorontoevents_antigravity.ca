# Manual PR Triage — Goal-1 Lens — 2026-05-03

**Author:** Claude Code (Opus 4.7 1M, manual triage subagent)
**Method:** Read-only review of `gh pr view` + `gh pr diff` + selected `Read` of cited files. NO swarm dispatch (broken; see `swarm_runs/PR_REVIEW_ABORTED.md`).
**Source-of-truth baseline:** `audit_dashboard/data/dashboard_data.json::performance.asset_class_health`
**Cross-references:**
- `reports/HEDGE_FUND_PR_MERGE_AUDIT_2026_05_03.md` (peer Claude, ~6h ago)
- `swarm_runs/CONSENSUS_v2.md` (5-engine asset-class consensus)
- `swarm_runs/DISAGREEMENT_RESOLUTION.md` (final ETF/BOND/FOREX verdicts)

---

## Goal-1 baseline (from dashboard_data.json — fresh read 2026-05-03)

| Class | Status | n | WR % | PF | Total PnL % | Tier? |
|---|---|---:|---:|---:|---:|---|
| EQUITY | stable | 420 | 52.9 | 1.41 | +269.08 | T2-candidate (PF<1.5) |
| CRYPTO | watch | 8100 | 44.5 | 1.24 | +2060.97 | sub-T2 (drag) |
| **FOREX** | **stressed** | **1169** | **46.4** | **0.27** | **−986.30** | **sub-floor (P0 emergency)** |
| COMMODITY | stable | 750 | 46.9 | **1.78** | +167.19 | meets T2 PF |
| ETF | stable | 87 | 55.2 | 1.24 | +23.55 | borderline (n→100) |
| BOND | thin_sample | 18 | 55.6 | 1.72 | +3.41 | passive-only |
| FUTURES | insufficient | 2 | 100 | n/a | 0 | n/a |
| UNKNOWN | insufficient | 5 | 60 | 4.59 | +0.18 | reclassify |

**Where lift is most needed:** FOREX is the only sub-floor class (PF 0.27 over 1169 trades — not noise). CRYPTO is the largest-n drag at PF 1.24 due to internal drag strategies (per `project_strategy_state_2026_05_03.md`: alpha_engine_fast PF 0.62 + kimi_signal_tracking PF 0.26). EQUITY is the closest to T2 promotion. ETF needs only 13 more clean closes to clear n>=100 floor for promotion. Any PR that doesn't move FOREX or CRYPTO drag-strategy quality, or sharpen EQUITY/ETF gates, is goal-1-secondary.

---

## Per-PR Reviews

### PR #724 — investigation(forex+crypto): deep-dives + FOREX rescue plan + 5 new strategies

- **Author:** eltonaguiar | **Base:** main | **Head:** investigation/forex-crypto-deep-dives-2026-05-03
- **Mergeable:** CONFLICTING | **CI:** scan SUCCESS (only conflict-marker check)
- **Affected files:** `FOREX_COMMODITIES_BONDS.MD` (+651), `reports/FOREX_RESCUE_CONSOLIDATED_2026_05_03.md` (+142), `reports/deep_dive_CRYPTO_quan_unknown_drag_2026_05_03.md` (+167), `reports/deep_dive_FOREX_2026_05_03.md` (+158), `reports/forex_corrupt_filter_analysis_2026_05_03.md` (+105), `reports/forex_new_strategies_2026_05_03.md` (+167)
- **What this actually does:** Six new markdown investigation/rescue documents — zero code changes. Deep-dives FOREX (sub-floor PF 0.27) and CRYPTO drag, names the JPY corruption-filter at `audit_trail/dashboard_generator.py:4163-4240` as the highest-leverage FOREX repair lever, and proposes 5 candidate strategies + rescue plan.
- **Goal-1 alignment:** **HIGH** — directly targets the only sub-floor class (FOREX) per CLAUDE.md "deep-dive" mandate. PR body itself flags 2 fabricated claims caught by adversarial review and points readers to the *consolidated* doc as authoritative.
- **Asset class affected:** FOREX (primary), CRYPTO (secondary), META (docs)
- **Risk register:**
  - VERIFIED: JPY filter at `audit_trail/dashboard_generator.py:4163-4240` matches the diff's claim — `_PNL_PCT_CORRUPT_DIVERGENCE = 10.0` at line 4169 and JPY-aware override `_PNL_PCT_CORRUPT_DIVERGENCE_JPY = 50.0` at line 4178 (already added in a prior PR; the relax flag `PNL_PCT_CORRUPT_DIVERGENCE_JPY_RELAX` exists at line 4270). The 10×→50× narrative in the rescue doc is partially shipped already; PR body should note this.
  - PR body openly admits 2 fabricated claims in `reports/deep_dive_FOREX_2026_05_03.md` (the original CRYPTO "quan_engine 18% / unknown 7%" claim was REFUTED in the same PR — quan_engine is 3.4% / PF 0.30, unknown 0%). This contradicts CLAUDE.md MAJOR GOALS § ranking.
  - Wire-Up Rule: doc-only PR, no rule violation, but 5 proposed strategies need follow-up code PRs with caller wiring.
  - CONFLICTING merge state — needs rebase.
- **Verdict:** **MERGE-AS-DOCS** (after rebase) — the consolidated rescue doc is the highest-value goal-1 artifact in the open backlog. Bad parts of `deep_dive_FOREX_2026_05_03.md` are explicitly superseded; merging documents the audit trail. Code follow-ups (5 strategies + JPY-relax flag default-on test) ship in separate PRs.
- **Recommendation:** Rebase + merge as docs. Update CLAUDE.md MAJOR GOALS § FOREX line to cite `reports/FOREX_RESCUE_CONSOLIDATED_2026_05_03.md` as the canonical FOREX recovery doc.

---

### PR #723 — feat(B18): shadow-mode auto-promotion for zero-closed-history strategies

- **Author:** eltonaguiar | **Base:** main | **Head:** feat/b18-shadow-promote-v2-2026-05-03
- **Mergeable:** CONFLICTING | **CI:** no checks reported
- **Affected files:** `audit_trail/dashboard_generator.py` (+83), `audit_trail/quality_gates.py` (+36), `tests/test_shadow_promotion.py` (+137), `tools/dashboard_hc_rules.py` (+3), `reports/REMAINING_ACTION_ITEMS_2026_04_30.md`, two B18 feedback reports, one updates doc
- **What this actually does:** Adds a default-OFF (env flag `SHADOW_MODE_AUTO_PROMOTE_ENABLED=1`) shadow-promotion gate that lets zero-closed-history strategies with ≥10 raw active emits accumulate 1 pick/cycle on /audit (capped at 5 system-wide, excluded from HC). Wired in `dashboard_generator.py` post-`final_active_picks`.
- **Goal-1 alignment:** **MED** — doesn't directly improve any sub-T2 class, but breaks the chicken-and-egg trap that prevents new candidate strategies from ever accumulating closed-pick history (which is goal-1 infrastructure for *future* promotions, including the 5 new FOREX strategies in #724).
- **Asset class affected:** META (system-wide, all classes)
- **Risk register:**
  - Wire-Up Rule: SATISFIED. `should_shadow_promote()` is called from `dashboard_generator.py::generate()` (production pick-gen path) at the post-`final_active_picks` block, with default-OFF env flag (correct opt-in pattern).
  - Mutation-safety: diff uses `{**rp, "shadow_mode": True}` copy pattern (not in-place) — addresses the self-review's surfaced contradiction `B18-claude-sonnet-self-review-2026-05-03.md` §B item 1.
  - Test coverage: 13 new tests in `tests/test_shadow_promotion.py` (PR body says all pass) — independent verification not run here, but file count and shape look right.
  - `passes_active_gate` early-return in `quality_gates.py:3919-3924` allows shadow picks through gate; the env-flag-guarded check is correct so default-OFF is preserved.
  - CONFLICTING — needs rebase.
- **Verdict:** **MERGE** (after rebase) — clean opt-in sidecar with proper wiring, tests, and feedback loop.
- **Recommendation:** Rebase, run pytest locally if CI is silent, merge.

---

### PR #676 — data(events): quality follow-up — remove duplicates + SVG placeholders

- **Author:** eltonaguiar | **Base:** main | **Head:** data/events-quality-2026-05-02
- **Mergeable:** CONFLICTING | **CI:** no checks reported
- **Affected files:** `EVENT_DATA_QUALITY_REPORT.md` (+8/-26), `events.json` (-69), `next/events.json` (+76/-145)
- **What this actually does:** Removes 2 duplicate events (Summerlicious, Nuit Blanche) from `events.json` (-69 lines) and rewrites 75 SVG placeholder image fields in `next/events.json` to `placehold.co` URLs. Goal-3 (events listing).
- **Goal-1 alignment:** **NONE** — this is a goal-3 (events listing) data-cleanup PR. Diff confirms changes are limited to events JSON + report.
- **Asset class affected:** N/A (events feature)
- **Risk register:**
  - Diff scope verified: only events.json/next/events.json/report — no goal-1 surface touched.
  - Per CLAUDE.md "Critical File Rules": editing JSON data files is fine; the React build only reads `next/events.json`. The Toronto-events index.html mega-menu is not modified.
  - 75 SVG → placehold.co is a network dependency (placehold.co outage = broken images). Acceptable cleanup tradeoff vs. inline SVG bloat.
  - CONFLICTING — needs rebase.
- **Verdict:** **MERGE** (after rebase) — small, safe, goal-3 hygiene.
- **Recommendation:** Rebase, merge — does not affect goal-1.

---

### PR #661 — Infrastructure v2.0 — Track Calculator, PSR/DSR Validation, Decay Tracker

- **Author:** eltonaguiar | **Base:** main | **Head:** infrastructure-modules-2026-05-02
- **Mergeable:** MERGEABLE | **CI:** **test (3.11) FAILURE**, test (3.12) CANCELLED, scan SUCCESS
- **Affected files:** `alpha_engine/INFRASTRUCTURE_README.md` (+79), `alpha_engine/__init__.py` (+24/-1), `alpha_engine/decay_tracker.py` (+279/-158 — full rewrite of existing file), `alpha_engine/track_calculator.py` (+244 — NEW)
- **What this actually does:** Adds `track_calculator.py` (per-(strategy,symbol,direction) WR), rewrites `decay_tracker.py` (state-persisted GREEN/YELLOW/RED/BLACK ladder), and adds package-level `__init__.py` re-exports. PR description claims a 3rd file `alpha_engine/statistical_rigor.py` but **this file is NOT in the diff** — it already shipped in PR #626 (commit `80b7ac53466`) per `git log`.
- **Goal-1 alignment:** **MED** (would-be HIGH if wired) — institutional-grade validation infrastructure (PSR/DSR/decay) is the right kind of goal-1 lift, but as shipped today, none of the new modules has any production caller.
- **Asset class affected:** META
- **Risk register:**
  - **CI FAILURE on test (3.11)** — peer Claude's audit at `reports/HEDGE_FUND_PR_MERGE_AUDIT_2026_05_03.md:59-60` cites the root cause: `alpha_engine/__init__.py` (this PR's diff line 14-21) re-exports `StrategyValidator`, `batch_validate`, `ValidationResult` from `statistical_rigor.py`. **VERIFIED via Grep on main:** `Grep StrategyValidator|batch_validate|ValidationResult` against `alpha_engine/statistical_rigor.py` returned NO matches. The export is fabricated; any `import alpha_engine` crashes.
  - **decay_tracker rewrite breaks production caller:** old stateless `compute_decay_blocks(...)` API is gone; `tools/run_strategy_research.py:36,183` calls the old API per peer audit. Not verified by me in this pass; but consistent with the +279/-158 rewrite signature.
  - **statistical_rigor.py is in PR description but not in diff** — `gh pr diff 661` confirms (3 files only). Misleading PR body.
  - **Wire-Up Rule violation:** Zero production callers for `TrackCalculator`, `get_track_wr`, `DecayTracker`. PR body has no `## Wiring Plan` section.
  - **PR not rebased:** silently deletes PR #659 (per-asset walk-forward card merged 2026-05-02 07:36Z, ~8 min before this PR opened) per peer audit.
- **Verdict:** **REQUEST_CHANGES** — CI is hard-broken via fabricated `__init__.py` exports. Do not merge.
- **Recommendation:** Close + replace with 3 surgical PRs per peer audit §2 PR #661 plan: PR-A track_calculator + 1 caller; PR-B decay_tracker preserving old `compute_decay_blocks` wrapper + updating `tools/run_strategy_research.py`; PR-C `__init__.py` cleanup.

---

### PR #660 — P0 Emergency Gate Fixes — Replace elite_score, Abolish WINNER_FILTER, Suspend C-Tier

- **Author:** eltonaguiar | **Base:** main | **Head:** emergency-gate-fixes-2026-05-02
- **Mergeable:** CONFLICTING | **CI:** scan SUCCESS only
- **Affected files:** `config/EMERGENCY_GATE_FIXES.md` (+123 NEW), `config/hf_quality_gates.json` (+66/-22 v1→v2), `config/per_asset_thresholds.json` (+117 NEW)
- **What this actually does:** Edits two config JSONs to (a) remove `min_elite_score`, (b) add `min_ml_score: 0.82` (then v2.1 raised to 0.90 in `per_asset_thresholds.json`), (c) lower min R:R floor 0.8→1.25 in `hf_quality_gates.json` BUT v2.1 simultaneously says floor must be 1.50 in `per_asset_thresholds.json`. (d) Removes WINNER_FILTER. (e) Sets `enabled: true`.
- **Goal-1 alignment:** **HIGH (intent) / LOW (delivered)** — the *intent* is goal-1 critical (ml_score > elite_score is a real finding per `project_performance_reality.md`). Delivery is broken: internal config contradiction + 100% no-op gate + zero wiring.
- **Asset class affected:** META (intended to affect ALL via gate logic)
- **Risk register:**
  - **Internal config contradiction (BLOCKER):** `config/hf_quality_gates.json` (this PR diff) sets `min_risk_reward: 1.25`. Same PR's `config/per_asset_thresholds.json` v2.1 _changelog explicitly says: "R:R floor corrected from 1.25 BACK to 1.50 — 1.25-1.5 band PF 1.01, Kelly -1.6% UNPROFITABLE." Two files in same PR disagree; runtime can't pick.
  - **`min_ml_score: 0.82` (in `hf_quality_gates.json`) → 0.90 (in `per_asset_thresholds.json`):** per peer audit §2 the live `dashboard_data.json` shows max observed `ml_score = 0.865`, so a 0.90 gate blocks 100% of picks. (Not re-verified by me in this pass — peer's claim. Severity = blocker if true.)
  - **Zero wiring (BLOCKER):** Both JSON files are read by `alpha_engine/hf_quality_gate.py` (per Grep at lines 18, 46), but `hf_quality_gate.py::hf_smart_pick_post_score_reason` has zero production callers. The LIVE gate is `alpha_engine/hedge_fund_quality_gate.py::passes_hedge_fund_gate` (wired at `audit_trail/quality_gates.py:5128, 5142`) — and that file uses HARDCODED Python constants, not these JSONs. Net production effect of merging this PR: **zero**.
  - **Existing R:R floor 1.5 already in production:** `audit_trail/quality_gates.py:565 SMART_PICKS_MIN_RR = 1.5`, used at line 4981. The PR's "lower R:R 0.8→1.25" claim ignores that the active gate already enforces 1.5.
  - **WINNER_FILTER status disputed:** PR claims it's a 0%-accuracy filter; peer audit says WINNER_FILTER is live with STATS tracking at `alpha_engine/forward_validator.py:399-569`. Headline numbers (R:R 1.5-2.0 PF 5.81) contradicted by live ledger (PF 1.211 per peer audit).
  - **Cited evidence files don't exist:** `reports/near_miss_analysis_2026_05_02.md`, `reports/gate_optimization_2026_05_02.md`, `reports/crypto_analysis_2026_05_02.md` — all referenced in `_evidence` strings; per peer audit none exist on main.
  - **CONFLICTING + silently reverts PR #659 walk-forward card** per peer audit.
- **Verdict:** **CLOSE** — replace with single-purpose PR per peer audit §2 plan: rebase on main + R:R ceiling 3.5→2.0 only + wire into `passes_hedge_fund_gate()` directly + cite live `dashboard_data.json` reproducer.
- **Recommendation:** Close with comment pointing to peer audit §2 #660 replacement plan.

---

### PR #644 — docs(audit): add evidence-backed per-asset-class quality gate plan

- **Author:** eltonaguiar | **Base:** main | **Head:** docs/per-asset-quality-plan
- **Mergeable:** CONFLICTING | **CI:** drift SUCCESS, scan SUCCESS
- **Affected files (top 5):** `audit_trail/quality_gates.py` (+91/-51), `audit_trail/quality_monitor.py` (+212 NEW), `audit_trail/dashboard_generator.py` (+99/-1), `audit_dashboard/template.html` (+53), `audit_trail/check_asset_quality_gate.py` (+54 NEW), `.github/workflows/audit-dashboard.yml` (+10), 3 docs
- **What this actually does:** **NOT a docs-only PR** despite the title — adds runtime per-asset quality monitoring (`quality_monitor.py`, `check_asset_quality_gate.py`), an asset-class-quality strip on the audit dashboard (`template.html`), wiring into `dashboard_generator.py` (per-asset summary builder), and modifies penalty math in `quality_gates.py` (toxic_combo:-25→-10, direction_conflict:-12→-8, sunday_penalty:-12→-3, long_overconf:-25→-15) plus introduces `ASSET_CLASS_SMART_THRESHOLDS` dict. Adds a CI gate via `QUALITY_GATE_MODE` (warn/hard).
- **Goal-1 alignment:** **HIGH** — directly addresses CLAUDE.md MAJOR GOALS § "find edge across ALL asset classes, but prioritize where the edge is best worth the risk" by surfacing per-class health on /audit + adding a CI gate.
- **Asset class affected:** META (affects ALL via quality_gates.py penalty deltas + per-asset thresholds)
- **Risk register:**
  - **PR title/body misrepresent scope.** Title says "docs"; diff includes 4 Python files + 1 HTML + 1 workflow. Reviewer expecting docs would miss the penalty-coefficient changes. Treat as feature PR.
  - **Penalty deltas not justified by linked evidence.** Diff at `audit_trail/quality_gates.py:2253` shows `toxic_combo: score -= 10` (was -25), `direction_conflict: score -= 8` (was -12), `long_overconf_combo: score -= 15` (was -25), `sunday_penalty: score -= 3` (was -12, comment still says "-6"). These are score-curve relaxations across all classes; **the linked plan doc `updates/2026-05-02-per-asset-quality-gate-implementation-plan.md` is in the diff but the rationale for the specific multipliers is not visible** in the diff snippets I read. Could be a value-destroying loosening if the curves were calibrated to current class metrics. Severity: needs evidence cite or reverification before merging.
  - **Wire-Up Rule:** SATISFIED. New `quality_monitor.py` + `check_asset_quality_gate.py` wired into `audit-dashboard.yml` workflow at lines 359-362; `_build_per_asset_quality_summary` wired into `dashboard_generator.py` payload at the smart-picks block.
  - **CI gate `QUALITY_GATE_MODE` is `warn` by default** (`vars.QUALITY_GATE_MODE || 'warn'`), so no immediate hard block — safe rollout pattern.
  - **CONFLICTING** — needs rebase against current main.
- **Verdict:** **HOLD / REQUEST_CHANGES** — gating infra + dashboard tile are good, but the score-penalty coefficient changes need their own evidence cite in the PR body before merge. Penalty deltas reduce penalties (i.e., let through more picks); on a system already running PF 0.27 FOREX this is the wrong direction without evidence.
- **Recommendation:** Request changes: (a) split penalty-coefficient changes into a separate PR with `dashboard_data.json` evidence, (b) keep the per-asset summary + dashboard strip + CI gate in this PR, (c) rename PR title to drop "docs(audit)" since 75% of the diff is code.

---

### PR #615 — fix: resolve 5 scanner blockers (circuit breaker, stdout crashes, earnings dict bug)

- **Author:** eltonaguiar | **Base:** main | **Head:** scanner-fixes-2026-05-01
- **Mergeable:** CONFLICTING | **CI:** test (3.11) CANCELLED, test (3.12) FAILURE, scan SUCCESS
- **Affected files:** `alpha_engine/data/circuit_breaker.json` (EMERGENCY→NORMAL, -25465.5% drawdown reset), `alpha_engine/inverse_edge_system.py` (+5/-2), `alpha_engine/outcome_resolver.py` (+119/-19 — v2.1 retry-cap + yfinance timeout), `alpha_engine/production_scanner.py` (+14/-10 print() guard), `copy_trader_intel/cta_strategy_replicator.py` (+5/-2), `tests/test_outcome_resolver_v21_bugfixes.py` (+227 NEW), 1 docs file
- **What this actually does:** Resets the circuit breaker that's been stuck since 2026-04-23, adds Windows-safe yfinance timeout (`concurrent.futures` instead of `signal.alarm`), adds `MAX_RESOLVE_RETRIES=3` cap to `outcome_resolver.py` so picks that can't be resolved get force-closed at entry with `exit_reason=RESOLVE_FAILED_MAX_RETRIES` (status=FLAT), wraps Windows stdout redirects in try/except. Bumps `RESOLVER_VERSION` to "v2.1".
- **Goal-1 alignment:** **HIGH** — the resolver retry-loop bug + circuit-breaker stuck state directly affect goal-1 metrics. Per CLAUDE.md MAJOR GOALS § "Resolver fix (DONE 2026-04-28, v2 + v2.1 bug bundle 2026-05-02)" — this IS the v2.1 bundle the goals doc refers to.
- **Asset class affected:** META (resolver) + indirectly EQUITY/FOREX/COMMODITY (yfinance-resolved classes)
- **Risk register:**
  - **CI FAILURE on test (3.12)** — needs investigation; could be the v2.1 test file itself (`tests/test_outcome_resolver_v21_bugfixes.py:227 lines`) or a regression in v2 tests. Per diff, `tests/test_outcome_resolver_v2.py` was edited to relax `assertEqual(resolver_version, "v2")` to `startswith("v2")` — looks safe.
  - **Circuit-breaker reset is a config-data commit.** `alpha_engine/data/circuit_breaker.json:status` flipped EMERGENCY→NORMAL with prior `total_drawdown_pct: -25465.5`. Per `feedback_circuit_breaker_stale_state_leak.md` (2026-04-27), state files have leaked stale `max_picks=0`. Need to verify the rest of the JSON (drawdown fields) doesn't carry rotted state that leaks back via `min()` aggregation.
  - **PR body says "Pre-existing unrelated changes (copy source quality thresholds) were intentionally excluded"** — not seeing those in the diff, so claim is consistent.
  - Wire-Up: outcome_resolver is called from production paths; `RESOLVER_VERSION` bump is observable in dashboard payload.
  - CONFLICTING — needs rebase.
- **Verdict:** **REQUEST_CHANGES** — fix the test (3.12) failure first, but otherwise this is HIGH-priority goal-1.
- **Recommendation:** Rebase, debug test (3.12) failure (likely a flaky import or stdlib API change), confirm circuit-breaker JSON has clean drawdown fields after the EMERGENCY→NORMAL flip. Then merge as P0.

---

### PR #608 — test(tradingagents): B26 — live smoke test gated on TRADINGAGENTS_LIVE_SMOKE=1

- **Author:** eltonaguiar | **Base:** main | **Head:** feat/b26-tradingagents-smoke-2026-05-02
- **Mergeable:** CONFLICTING | **CI:** test (3.11) FAILURE, test (3.12) CANCELLED
- **Affected files:** `tests/test_tradingagents_smoke.py` (+202 NEW), `reports/REMAINING_ACTION_ITEMS_2026_04_30.md` (+5/-5 row update), `updates/2026-05-02-b26-tradingagents-smoke.md` (+55)
- **What this actually does:** Adds a single live smoke test that, when run with `TRADINGAGENTS_LIVE_SMOKE=1` + a real LLM API key, exercises the B24+B25 placeholder/dedup guards on real LLM output for AAPL/MSFT/GOOGL (or NVDA/SOFI/AMD per diff text). Skipped unconditionally in CI.
- **Goal-1 alignment:** **LOW** — TradingAgents emitter is currently OFF (`TRADINGAGENTS_EMITTER_ENABLED: OFF` per `reports/REMAINING_ACTION_ITEMS_2026_04_30.md` V3 row); test guards future activation but doesn't lift any current class metric.
- **Asset class affected:** META (test infra, EQUITY-future)
- **Risk register:**
  - **CI FAILURE on test (3.11):** PR body says smoke test is `skipif TRADINGAGENTS_LIVE_SMOKE != 1` — so CI failure is unlikely to be from this file itself. Likely a pre-existing test failure on main; worth diffing against current main test output.
  - Test correctly gated via `pytest.mark.skipif` (verified in diff at lines 27-29).
  - Wire-Up: test file only, no production caller required.
  - CONFLICTING — needs rebase.
- **Verdict:** **HOLD** — clean test addition but CI is red; do not merge into a state where CI is flaky.
- **Recommendation:** Rebase + verify CI failure on test (3.11) is pre-existing (not caused by this PR), then merge if green.

---

### PR #597 — P0 fixes + USDCHF investigation: rapid_fire pair-block, pick revalidator, USDCHF FALSIFIED

- **Author:** eltonaguiar | **Base:** main | **Head:** investigate/usdchf-concentration-2026-05-01
- **Mergeable:** MERGEABLE | **CI:** test (3.11) FAILURE×2, test (3.12) FAILURE/CANCELLED, scan SUCCESS
- **Affected files (top 5):** `tests/events_month_filters.spec.ts` (+580 NEW Playwright), `TORONTOEVENTS_ANTIGRAVITY/index.html` (+69/-24), `updates/2026-05-01-this-month-next-month-filter-fix.md` (+216), `alpha_engine/pick_revalidator.py` (+175 NEW), `tests/test_pick_revalidator.py` (+137 NEW)
- **What this actually does:** Three independent things bundled by branch-flip cron: (1) **USDCHF investigation: hypothesis FALSIFIED** — read-only doc; (2) **rapid_fire pair-blocklist fix** in `alpha_engine/isolated_signal_integrator.py` (+19) — adds `is_blocked_pick()` call to catch `_RETIRED_SYSTEM_STRATEGY_PAIRS` like `(rapid_fire, macd_rsi_confluence)` that bare-name match missed; (3) **`alpha_engine/pick_revalidator.py`** (NEW, sidecar) — pure-function gate that re-anchors R:R to live price, returns `OK/PLAYED_OUT_TP/PLAYED_OUT_SL/R_R_DEGRADED`. Plus an unrelated multi-day events filter fix (`TORONTOEVENTS_ANTIGRAVITY/index.html` +69 lines for "this month"/"next month" overlap logic) and a Samsung S25 Ultra Playwright profile.
- **Goal-1 alignment:** **HIGH** for the rapid_fire fix + revalidator (both directly affect pick quality on a class that's currently stressed); **NONE** for the events month-filter fix (goal-3) and **NONE** for the FALSIFIED-investigation doc (informational).
- **Asset class affected:** META (rapid_fire pair-block applies to all classes; revalidator pure function); separately, EVENTS feature
- **Risk register:**
  - **Mixed-scope PR** — bundles goal-1 (rapid_fire, revalidator), goal-3 (events filter), and pure-investigation. PR description openly acknowledges "Multi-purpose PR landed on this branch". Hard to roll back if any one piece breaks.
  - **CI FAILURE on test (3.11) and (3.12)** — could be the new Playwright test file `tests/events_month_filters.spec.ts` (+580 lines) or unrelated. Worth checking against main.
  - **Revalidator is a sidecar with no caller wired** — PR body explicitly says "Wire-up of `pick_revalidator` into `smart_picks_engine.py` — separate PR per CLAUDE.md Wire-Up Rule." Acceptable (opt-in sidecar with explicit wiring plan), but reviewer should confirm a wiring PR is queued.
  - **rapid_fire fix is correctly wired:** diff shows `is_blocked_pick({"strategy": strategy, "source_system": source_name})` call inserted at `alpha_engine/isolated_signal_integrator.py:670` inside the per-pick gate chain. Verified import block at lines 28-34 falls back gracefully. **VERIFIED present in current main:** `Grep BLACKLISTED_STRATEGIES` shows `alpha_engine/smart_picks_engine.py:755-761` already enforces the blocklist as of 2026-05-03 — so the toxic-strategy bug from peer audit §5 is at least partially fixed.
- **Verdict:** **REQUEST_CHANGES** — split into 3 PRs (P0 rapid_fire + revalidator; events month-filter; USDCHF doc), each with clean CI.
- **Recommendation:** Ask author to split. If splitting is too costly, prioritize merging just the rapid_fire pair-block fix as a P0 cherry-pick (the only piece that directly improves goal-1 production picks today). The revalidator + investigation can ship later.

---

## Top 3 priority-merges (with goal-1 evidence)

1. **PR #724** — `reports/FOREX_RESCUE_CONSOLIDATED_2026_05_03.md` is the canonical FOREX recovery roadmap targeting the only sub-floor class (PF 0.27, n=1169). Docs-only, low merge risk, high goal-1 informational value. **Rebase first.**
2. **PR #615** — v2.1 outcome_resolver bug-fix bundle (retry cap + yfinance timeout + circuit-breaker reset). Per CLAUDE.md MAJOR GOALS § Resolver fix line, this IS the v2.1 bundle the project's authoritative doc points to. **Fix CI, then merge.**
3. **PR #723 (B18)** — clean opt-in shadow-promotion gate; satisfies Wire-Up Rule, default-OFF, 13 tests. Doesn't lift current class metrics but unblocks promotion paths for new candidate strategies (e.g., the 5 in #724). **Rebase + merge.**

## Top 3 close/replace candidates (with reason)

1. **PR #660** — internal config contradiction (R:R 1.25 vs 1.50), zero wiring (target file `hf_quality_gate.py` has no production callers; live gate is `passes_hedge_fund_gate` which uses Python constants), cited evidence files don't exist on main. Replace per peer audit §2.
2. **PR #661** — fabricated `__init__.py` exports break CI hard (`alpha_engine/statistical_rigor.py` does not export `StrategyValidator`/`batch_validate`/`ValidationResult` — verified via Grep). Wire-Up Rule violation (zero callers for new modules). PR body claims a 3rd file that's already on main from PR #626. Decompose per peer audit §2 into 3 surgical PRs.
3. **PR #644** (HOLD/split, not pure close) — title misrepresents scope (claims docs, actually 4 Python files); penalty-coefficient relaxations need their own evidence cite. Split off the per-asset-summary + dashboard tile + CI gate (those parts are good) and request changes on the penalty deltas.

## Open questions for operator

1. **Toxic-strategy enforcement bug status:** Peer audit §5 says `BLACKLISTED_STRATEGIES` was unwired in `alpha_engine/smart_picks_engine.py`. **My re-grep at 2026-05-03 shows lines 755-761 DO now enforce the blocklist** — was this fixed between 6h ago and now (potentially in a [skip ci] commit)? If so, the 5,293 quan_engine_scalp closed picks are still in the ledger and may still be poisoning aggregate metrics until they age out. Confirm with `git log --since="6 hours" -- alpha_engine/smart_picks_engine.py`.
2. **#660 R:R floor:** the PR ships R:R 1.25 in one file and R:R 1.50 in another. Which is intended for production?
3. **#615 circuit-breaker reset:** flipping EMERGENCY→NORMAL with `-25465.5%` lingering in the JSON — is the rest of the state (max_picks, etc.) clean per `feedback_circuit_breaker_stale_state_leak.md`?
4. **#724 follow-up code PRs:** are the 5 new FOREX strategies queued as separate code PRs, and is one-of-them the JPY-corruption-filter relax flag default-on test?
5. **#644 penalty deltas:** is there a missing evidence file justifying toxic_combo:-25→-10 / long_overconf:-25→-15 / sunday_penalty:-12→-3? These are loosenings on a system with PF 0.27 FOREX.

## Action items

- [ACTION] Rebase PR #724 against main and merge as docs-PR. Cmd: `gh pr merge 724 --squash --delete-branch`
- [ACTION] Rebase PR #723 (B18 shadow-promote), confirm pytest passes locally, merge. Cmd: `gh pr merge 723 --squash --delete-branch`
- [ACTION] Close PR #660 with comment pointing to peer-audit replacement plan. Cmd: `gh pr close 660 --comment "Closing per swarm_runs/PR_TRIAGE_2026_05_03_MANUAL.md and reports/HEDGE_FUND_PR_MERGE_AUDIT_2026_05_03.md §2 — internal config contradiction, zero wiring (live gate is passes_hedge_fund_gate, not hf_smart_pick_post_score_reason), cited evidence files don't exist on main. Replacement PR: rebase + R:R ceiling 3.5→2.0 only + wire into passes_hedge_fund_gate() with dashboard_data.json reproducer."`
- [ACTION] Close PR #661 with replacement plan. Cmd: `gh pr close 661 --comment "Closing — CI hard-broken via fabricated __init__.py exports (StrategyValidator/batch_validate/ValidationResult not in alpha_engine/statistical_rigor.py — verified via grep). Decompose into 3 surgical PRs per reports/HEDGE_FUND_PR_MERGE_AUDIT_2026_05_03.md §2."`
- [ACTION] Request changes on PR #644: split penalty deltas into separate PR. Cmd: `gh pr review 644 --request-changes --body "Title says docs(audit) but diff includes 4 Python files + 1 HTML + 1 workflow. Penalty coefficient changes (toxic_combo:-25→-10, direction_conflict:-12→-8, long_overconf:-25→-15, sunday_penalty:-12→-3) need their own dashboard_data.json evidence cite. Please split into: (1) per-asset summary + dashboard tile + warn-mode CI gate (this PR's good parts), (2) score-penalty deltas with evidence."`
- [ACTION] Rebase PR #615, debug test (3.12) failure, verify circuit_breaker.json clean. Cmd: `gh pr comment 615 --body "Rebase + investigate test (3.12) failure (RED on CI). Confirm alpha_engine/data/circuit_breaker.json is clean of stale state per feedback_circuit_breaker_stale_state_leak.md before merge — flipping EMERGENCY→NORMAL with -25465% drawdown lingering looks like the same pattern."`
- [ACTION] Rebase PR #676 and merge (events-data only, goal-3). Cmd: `gh pr merge 676 --squash --delete-branch`
- [ACTION] Hold PR #608 until CI green on rebase. Cmd: `gh pr comment 608 --body "Holding pending CI investigation: test (3.11) FAILURE — likely pre-existing main breakage but please rebase and re-check before merge."`
- [ACTION] Request split on PR #597 (or cherry-pick rapid_fire piece). Cmd: `gh pr review 597 --request-changes --body "Multi-purpose PR — please split into (1) rapid_fire pair-block fix (P0 goal-1, ready to ship), (2) pick_revalidator sidecar with explicit wiring plan, (3) events month-filter goal-3 fix, (4) USDCHF FALSIFIED doc. Currently CI is RED on test (3.11)+(3.12) and unclear which piece broke it."`
- [ACTION] Verify peer audit §5 toxic-strategy bug is now fixed. Cmd: `git log --since="2026-05-03 00:00" -- alpha_engine/smart_picks_engine.py alpha_engine/outcome_resolver.py | head -30` — and re-check `alpha_engine/data/closed_picks.json` for new quan_engine_scalp picks since the fix.

---

## Self-check (per quality gate)

Random concern selected: **PR #661 — `__init__.py` re-exports `StrategyValidator`/`batch_validate`/`ValidationResult` that don't exist in `statistical_rigor.py`.**

Re-verification: `Grep "StrategyValidator|batch_validate|ValidationResult"` in `e:\findtorontoevents_antigravity.ca\alpha_engine\statistical_rigor.py` returned **No matches found**. The `__init__.py` diff at lines 11-13 imports these symbols, and `git log --oneline -5 -- alpha_engine/statistical_rigor.py` shows the file shipped 2026-04-30 in PR #626 (`80b7ac53466`). The file does not export the symbols PR #661's `__init__.py` claims. **Concern stands. CI failure is real.**

(no [CHECK FAIL])

---

## Contradictions found vs `reports/HEDGE_FUND_PR_MERGE_AUDIT_2026_05_03.md` (peer Claude, 6h ago)

1. **Peer audit §5 (BLACKLISTED_STRATEGIES enforcement bug):** Peer says `alpha_engine/smart_picks_engine.py` has "no blacklist check" and that this is "CONFIRMED AND SEVERE." **My Grep at 2026-05-03 finds `BLACKLISTED_STRATEGIES` enforcement at `alpha_engine/smart_picks_engine.py:755-761` (commented "2026-05-03: Enforce BLACKLISTED_STRATEGIES from alpha_engine.config").** Either the bug was fixed in the last 6 hours via a [skip ci] commit, or peer's grep was against a stale tree. The 5,293 historical quan_engine_scalp picks in `closed_picks.json` are still ledger-poison until aged out, so peer's downstream-impact concern remains valid even if the wiring is now in place.
2. **Peer audit §1 PR #668 (Cloud Agent feature flags):** peer says merged 2026-05-03 04:34Z. I did not need to triage this — already merged.
3. **PR #660 R:R floor 0.8→1.25:** peer cites the same internal contradiction I see (`hf_quality_gates.json:1.25` vs `per_asset_thresholds.json:1.50`). Concur.
4. **PR #661 statistical_rigor.py duplication:** peer says the file already shipped in PR #626. **Confirmed via `git log` — first commit `80b7ac53466` (PR #626), second `8eaaa41e09c` (PR #633 cherry-pick of deflated_sharpe_ratio).** PR #661 takes credit for code already on main.

No contradictions between this triage and peer audit on the listed PRs other than the BLACKLISTED_STRATEGIES wiring point above.

---

*End of manual triage. Operator decides — no PRs were merged, closed, or commented by this subagent.*
