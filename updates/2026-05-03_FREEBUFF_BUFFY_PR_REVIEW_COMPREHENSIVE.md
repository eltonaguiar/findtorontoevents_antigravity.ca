# Buffy PR Review: 14 Open PRs + Audit Evidence Analysis

**Date:** 2026-05-03
**Reviewer:** Buffy (Claude, DeepSeek-v4-Pro)
**Attachments Reviewed:** `config_revised.yaml`, `EVIDENCE_REPORT_2026_05_02.md`, `GOAL_ASSESSMENT_2026_05_02.md`, `HEDGE_FUND_AUDIT_REPORT_2026_05_02.md`, `INTEGRATION_TESTING_PLAN.md`, `plan.md`, all individual PR review JSONs and commentary

---

## Executive Summary

15 open PRs reviewed at session start (#704–#597). #703 was already merged. #704 merged during this session.

| Verdict | Count | PRs |
|---------|-------|-----|
| MERGE | 8 | #704, #700, #699, #676, #669, #668, #655, #625 |
| HOLD | 4 | #661, #660, #658, #608 |
| REQUEST CHANGES | 5 | #681, #665, #644, #615, #597 |

**Note:** #608 is HOLD (rebase needed) but code quality is high enough to MERGE after rebase. #681 is REQUEST CHANGES but has one extractable component (the `wf_audit_signals` starvation alarm) worth a separate fast-track PR.

---

## Asset Performance Context (from Audit Attachments)

Before reviewing individual PRs, the following performance picture from the May 2-3, 2026 audit cycle informs all gate and strategy PRs:

| Asset Class | 24h | 7d | 30d | Verdict |
|-------------|-----|----|-----|---------|
| **ETF** | T1 | T1 | T1 | Best performer |
| **CRYPTO** | T1 | Below T2 | Below T2 | Diluted by `quan_engine` volume |
| **EQUITY** | T2 | Below T2 | T1 | 7d weakness from `stocks_rsi2_pullback` |
| **FOREX** | Below T2 | Below T2 | Below T2 | Structural — `non_crypto_consensus` at 0% WR |
| **COMMODITY** | Below T2 | Below T2 | Below T2 | Needs investigation |

**Confirmed Fixes (already in main):**
- JPY-cross BUY rule bug (PR #687) — all synonymous directions now blocked
- Toxic strategy removals (PR #692) — `forex_carry_momentum` and `goldmine_6x_consensus` eliminated
- Kelly vol-target clamp (PR #703) — crypto MDD targeting 9-25% vs prior 40-60%

**Critical Outstanding Issues:**
- `quan_engine` exceeds 15% volume concentration in CRYPTO while failing performance standards
- FOREX `non_crypto_consensus` has 0% win rate — structural, not a gate issue
- `forex_rsi2_mean_reversion` identified as a 7d drag on FOREX
- `stocks_rsi2_pullback` identified as a 7d drag on EQUITY

---

## Detailed PR Reviews

### MERGE Queue (7 PRs — Ready Now)

#### PR #704 — `fix(dashboard): restore walkforward payload accidentally removed by PR #665` ✅
**Verdict: MERGE.** Closes confirmed breaking regression #696.

Restores `_wf_by_class`, `_wf_results_generated_at`, and `walkforward` fields consumed by `battleground/app.js:2555`. The root cause (how #665's payload removal slipped through the review checklist) should be logged as a process improvement item.

---

#### PR #700 — `docs(plan): PR action plan + 14-day integration & testing timeline` ✅
**Verdict: MERGE.**

Delivers two well-structured operational documents: a PR action plan with clear merge sequencing (14 open + 5 new PRs), and a 4-phase 30-day integration plan with concrete 14-day Tier-2 targets per asset class.

**Suggestions (non-blocking):**
- Consider linking each 14-day target metric to `tools/run_audit.py` output path for independent reviewer validation
- The rollback plan section could mention `KELLY_VOL_MIN_SCALE` env var as a quick-rollback pattern already in main

---

#### PR #699 — `feat(gates+audit): Unified gate framework + reproducible audit script + full report` ✅
**Verdict: MERGE.** High-impact, evidence-backed deliverable from the May 2, 2026 cross-AI audit.

Three pillars are self-contained and CI-ready:
- **Unified Gate Framework** (`config/unified_gates.yaml`): PF/WR/MDD tier targets, 15% volume caps, auto-disable rules (PF<0.8 or WR<35% over 7 days → halve notional; PF<0.5 → zero). `meme_coin` and `penny_stock` sandbox configs with tighter controls are prudent.
- **Reproducible Audit Script** (`tools/run_audit.py`): CLI-driven, dependency-free, CI-integratable. Active-pick exclusion checks are exactly what the audit-dashboard workflow needs.
- **Audit Report** confirms all four underperforming asset classes. ETF is T2 ✅. ETF is the best performer.

**Post-merge watch items:**
- Monitor `quan_engine` volume concentration in CRYPTO — primary 7d/30d performance diluter. PR #703 (KELLY_VOL_MIN_SCALE) should help but watch for persistence.
- `config_revised.yaml` (from Kimi's attachments) and `config/unified_gates.yaml` may have overlapping scopes — verify after merge that both load and the more restrictive thresholds win.
- FOREX PF gap (~0.43 vs T2 target ~0.8) needs investigation beyond the gate framework — `non_crypto_consensus` 0% WR is structural.

---

#### PR #676 — `data(events): quality follow-up — remove duplicates + SVG placeholders` ✅
**Verdict: MERGE.** Textbook data-quality PR.

- Removed only verified duplicate event IDs (Summerlicious 2026, Nuit Blanche Toronto 2026)
- Maintained symmetry between `events.json` and `next/events.json` — prevents drift
- Replaced 75+ inline SVG Data URIs with `placehold.co` URLs — significant file size reduction
- Reduced HIGH-priority issues from 2 to 0
- Correctly skipped medium-severity work — this restraint signals mature engineering judgment

**Pre-merge:** Confirm the retained Summerlicious 2026 record has `end_date` and `is_multi_day=true` from the removed duplicate (EVIDENCE_REPORT confirms, but a quick JSON check is cheap insurance).

---

#### PR #668 — `feat(config): enable ml_gatekeeper, what_if_analysis, smart_picks_explainability flags` ✅
**Verdict: MERGE.** Minimal, safe, flag-only configuration change.

Enables three dormant but previously wired feature flags. `policy_version` bumped to `v4-2026-05-02` — proper versioning hygiene.

**Post-merge:** Ensure follow-up PRs that wire actual callers reference `v4-2026-05-02` as the minimum policy version dependency. Consider adding `feature_flags.json` to the push-trigger paths in `audit-dashboard.yml`.

---

#### PR #655 — `docs: persist Cloud Agent's follow-up PR roadmap (post-PR-#654 wire-up plan)` ✅
**Verdict: MERGE.** Documentation-only PR that correctly captures the follow-up roadmap.

4-phase roadmap sequence with agent prompts, dependency graph, and accurate cross-references to upstream PRs.

**Post-merge:** PR #2 (`outcome_resolver` noise filter) should explicitly reference the `outcome_resolver.py` v2.1 work blocked in PR #615 — the two threads need to converge. Apply `[skip ci]` to the commit.

---

#### PR #625 — `docs(broadcast): 2026-05-02 PR triage state — for peer agents` ✅
**Verdict: MERGE.** Clean information-only broadcast.

No production code, zero regression risk. Apply `[skip ci]` to commit message.

---

### HOLD Queue (4 PRs — Needs Work Before Merge)

#### PR #661 — `Infrastructure v2.0 — Track Calculator, PSR/DSR Validation, Decay Tracker` 🟡
**Verdict: HOLD — Architecture Review Needed.**

Four new modules address real infrastructure gaps, but 626 additions with no production wiring means this is currently a **library**, not a feature.

**Required before merge:**
1. **Wire-Up Compliance:** Add explicit TODO/plan in PR body for wiring each module into production callers. Per CLAUDE.md conventions, new modules must integrate into production paths.
2. **Environment-Based Default-OFF Gate:** No `*_ENABLED=0` env flag for any of the 4 new modules — violates project standard.
3. **Walk-Forward Validation:** New metrics (PSR, DSR, Sharpe-based decay tiers) must be validated in a 14-day shadow-production run before going live.

**Strengths:** Bailey & Lopez de Prado methodology is sound. 4-tier kill-switch (GREEN/YELLOW/RED/BLACK) is the right abstraction. Track Calculator correctly addresses strategy-level win-rate masking bug. `INFRASTRUCTURE_README.md` with deployment guidance is good practice.

---

#### PR #660 — `P0 Emergency Gate Fixes — Replace elite_score, Abolish WINNER_FILTER, Suspend C-Tier` 🟡
**Verdict: HOLD — Cross-Validation Needed.**

Projected impact (+$1,901 monthly revenue, +35% P&L) is significant. However, multiple PRs now touch overlapping configuration space.

**Required before merge:**
1. **Resolve overlapping gate configs:** `config/hf_quality_gates.json` (this PR) and `config/unified_gates.yaml` (PR #699) may have conflicting tier thresholds. `config/per_asset_thresholds.json` overlaps with `config/unified_gates.yaml` targets. Resolve which is canonical.
2. **ML Score Threshold Alignment:** Ensure `ml_score >= 0.82` aligns with `ml_gatekeeper` scoring bands in `feature_flags.json` (PR #668).
3. **R:R Floor Risk:** Confirm 0.8 → 1.25 tightening does not starve smart picks. Current `forward_validated` wiring rejects all smart picks — a higher R:R floor compounds this.

**Strengths:** `ml_score >= 0.82` replacement is meaningful. Soft Gate Sizing (position modulation by ml_score bands) is a strong enhancement. `WINNER_FILTER` abolition is supported by audit evidence. C-Tier suspension correctly scoped to CRYPTO. Deployment and rollback plan is excellent.

---

#### PR #658 — `Hedge Fund Quality Enhancement PR — Comprehensive Audit & Evidence-Backed Enhancements` 🟡
**Verdict: HOLD — Segmentation Required.**

36,404-word master document, 9 deep-analysis reports, 18 visualizations, 5 CSVs — comprehensive and evidence-backed. But a 20,227-line single PR cannot be reviewed effectively.

**Required before merge:**
1. **Segment into 5 focused PRs** (see below)
2. **Verify P&L projections:** +35% to +60% are forward-looking counterfactuals — label as estimated with confidence intervals, not guaranteed

**Suggested segmentation:**

| New PR | Scope | Rationale |
|--------|-------|-----------|
| PR-A | Emergency Triage (C-Tier suspension, WINNER_FILTER abolition, elite_score replacement) | Already largely covered by #660 — consolidate here |
| PR-B | Crypto Enhancements (Perp Funding Arb, ML scaling) | Crypto-specific |
| PR-C | Equity Enhancements (CEF NAV Discount, L100 scaling) | Equity-specific |
| PR-D | Forex Sleeve (Forex Carry Sleeve implementation) | Forex-specific |
| PR-E | Audit Infrastructure (visualizations, CSV data, reference docs) | Documentation |

**Strengths:** Bailey & Lopez de Prado statistical rigor properly applied. Sharpe ratio target of 4.20 is clear and measurable. audit-enhancement directory structure is organized and reusable.

---

#### PR #608 — `test(tradingagents): B26 — live smoke test gated on TRADINGAGENTS_LIVE_SMOKE=1` 🟡
**Verdict: HOLD → MERGE after rebase.**

Code quality and safety design are solid. Double-gating (env var + API key check) is correct. Bounded live call volume is responsible.

**Current blocker:** Branch predates PR #617 — CI failures on unrelated tests block merge. Rebase required.

**Recommended improvements (non-blocking):**
1. Replace `os.environ` mutation with `monkeypatch` or `unittest.mock.patch.dict('os.environ', ...)` for cleaner test teardown
2. Import existing `_is_placeholder()` from the emitter module instead of hardcoding `_PLACEHOLDER_STRINGS`
3. Address fixture fragility: the module-scoped `smoke_picks` fixture means a single LLM failure cascades — consider function-scoped or yield+teardown pattern

---

### REQUEST CHANGES (5 PRs — Author Work Required)

#### PR #681 — `feat(strategy-decay): emergency diagnostic + auto-reduce guard for 11 failing strategies` 🛑
**Verdict: REQUEST CHANGES. DO NOT MERGE.** Confirmed by two independent AI reviewers (Claude Opus + DeepSeek-Reasoner).

**Critical issues:**
1. **Data path error:** Queries `closed_picks.json` instead of `dashboard_data.json` — strategies fall back to static `EMERGENCY_OVERRIDES` map without proper runtime data. Most dangerous bug: profitable strategies get shut down.
2. **Profitable strategies incorrectly flagged:** Four strategies were flagged for reduction/removal despite being profitable.
3. **No environment-based default-OFF gate:** No `STRATEGY_DECAY_GUARD_ENABLED=0` flag — violates project convention.
4. **No walk-forward validation:** 14-day shadow-production period mentioned in plan but not implemented.
5. **Code bugs:** Silent JSON error swallows, zero-value return bug potential, docstring inaccuracies.

**Extractable component:** The `wf_audit_signals` starvation alarm logic is sound and could be a small, standalone PR worth fast-tracking.

**Recommended path:** Extract starvation alarm → separate small PR. Rewrite remaining logic using `dashboard_data.json`, implement live decay detection, add `STRATEGY_DECAY_GUARD_ENABLED` env flag, add 14-day shadow period.

---

#### PR #665 — `feat(gates): shadow HC after-cost gate + field-stamp on active picks` 🛑
**Verdict: REQUEST CHANGES.**

Shadow gate design and field-stamping mechanism are well-thought-out. However:
1. **Breaking change — walkforward payload removal:** `_wf_by_class`, `_wf_results_generated_at`, `walkforward` removed without documentation. Consumed by `battleground/app.js:2555`. PR #704 was already filed to fix this regression. Must restore or coordinate with simultaneous frontend update.
2. **Merge conflict:** Must rebase.
3. **Dead code:** `passes_hc_after_cost()` has no production callers. Add TODO comment or wire it in.
4. **Test hygiene:** `_AC_STRATEGY_INDEX_CACHE` mutated globally without teardown — add fixture-based reset.
5. **Dependency risk:** Potential conflict with PR #683 re: `cftc_cot_commercial_signal`.

**Strengths:** Shadow gate is correctly default-OFF. 19-test suite is excellent. Defensive field stamping with staleness guards. Thorough PR body.

---

#### PR #644 — `docs(audit): add evidence-backed per-asset-class quality gate plan` 🛑
**Verdict: REQUEST CHANGES.**

Direction is correct. `warn`-mode rollout posture is prudent. However:
1. **Scope dishonesty:** PR claims single-file change but diff shows 9 production files. Correct the PR body.
2. **Zero automated tests:** `quality_monitor.py` and `check_asset_quality_gate.py` have no pytest tests. Add unit tests.
3. **Statistically insignificant thresholds:** FOREX n=3, EQUITY n=5, CRYPTO n=10 — sample sizes too small. Lower all classes to `warn` mode until volume thresholds are met, document as temporary.
4. **Smart pick starvation risk:** `passes_smart_gate()` hard-rejects picks where `forward_validated` is falsy. Current snapshot would reject ALL smart picks — clarify upstream wiring immediately.
5. **FOREX forward WR gap:** Diverges 5.5x from live realized data — document this unreliability and handle gracefully.

---

#### PR #615 — `fix: resolve 5 scanner blockers (circuit breaker, stdout crashes, earnings dict bug)` 🛑
**Verdict: REQUEST CHANGES. DO NOT MERGE.** Explicitly flagged DO-NOT-MERGE in existing Kimi review.

**Critical issues:**
1. **Circuit breaker safety risk:** Attempting to reset `circuit_breaker.json` from EMERGENCY to NORMAL while showing -25,465.5% drawdown (physically impossible) is a dangerous safety bypass. Drop this change entirely — handle as operator runbook action only after Issue #623 audit is complete.
2. **Regression:** `__builtins__.print` patch breaks in CPython test context (8 failures) because `__builtins__` is a dict, not a module.
3. **Unreachable code:** tee-to-log branch in `production_scanner.py` is unreachable.
4. **yfinance timeout doesn't bound runtime:** `ThreadPoolExecutor.shutdown()` blocks until hung thread finishes.
5. **Scope creep:** `outcome_resolver.py` v2.1 changes fall outside the stated 5-scanner-blockers scope.

**Recommended path:** Surgical PR for scanner fixes only (stdout wraps, `__builtins__` fix, log reachability). Separate PR for resolver v2.1 (wire into PR #610). Drop circuit_breaker.json reset. Rebase on main.

---

#### PR #597 — `P0 fixes + USDCHF investigation: rapid_fire pair-block, pick revalidator, USDCHF FALSIFIED` 🛑
**Verdict: REQUEST CHANGES. Split required.**

This PR bundles four distinct workstreams with different risk profiles. **The trading system fixes are ready; the frontend changes are blocked.**

**Ready to merge (extract to own PRs):**
- **Pair-Blocklist Fix:** `is_blocked_pick()` integration into signal pipeline is a high-quality P0 fix.
- **pick_revalidator Sidecar:** `alpha_engine/pick_revalidator.py` with 14 tests is well-designed. Three status checks (`PLAYED_OUT_TP`, `PLAYED_OUT_SL`, `R_R_DEGRADED`) are clean.
- **USDCHF Investigation:** Legitimate read-only analysis. Worth preserving in an `investigations/` folder.

**Must extract and fix separately:**
- **Frontend regression:** `TORONTOEVENTS_ANTIGRAVITY/index.html` has confirmed staleness-filter regression causing `test_events_staleness_filter.py` to fail. Fix first.

**Additional blocker:** Branch stale relative to main — `test_quan_engine_concurrency_cap.py` failing.

---

## Cross-PR Coordination Recommendations

Based on the audit evidence and overlapping PR scopes, the following coordination actions are recommended:

### 1. Configuration File Canonicalization
Before merging #660, #699, and #644, determine which config file is canonical for:
- Asset class tier thresholds (PF/WR/MDD targets)
- Quality gate enforcement levels
- Auto-disable rules and volume caps

**Recommendation:** Make `config/unified_gates.yaml` (PR #699) the canonical source. Have #660 and #644 reference it rather than duplicating thresholds.

### 2. Smart Pick Wiring Convergence
Multiple PRs (#660, #644, #699) touch smart pick quality gates. The current `forward_validated` wiring (which would reject ALL smart picks) is a critical gap that must be resolved before any of these PRs merge.

**Recommendation:** Open a dedicated issue for `forward_validated` wiring and gate it as a prerequisite for the smart pick PRs.

### 3. FOREX Structural Investigation
FOREX performance (PF ~0.43, WR 17%) is structural, not addressable by gate changes. The `non_crypto_consensus` 0% win rate and `forex_rsi2_mean_reversion` drag require investigation beyond PR scope.

**Recommendation:** Assign a dedicated investigation PR for FOREX root cause analysis before the 14-day Tier-2 deadline.

### 4. Volume Concentration Enforcement
`quan_engine` exceeds 15% concentration threshold in CRYPTO. PR #703 (Kelly clamp) should help but does not directly cap volume. The unified gate framework (PR #699) has volume caps but they are not yet enforced.

**Recommendation:** Priority sequence: merge #699 first (establishes caps), then enforce `quan_engine` volume cap in a follow-up PR.

---

## Kimi Audit Evidence: Key Findings to Track

From the attached evidence reports:

1. **JPY-cross bug fixed (PR #687):** All synonymous long directions now blocked. Legacy picks aging out over ~5 days.

2. **Toxic strategies removed (PR #692):** `forex_carry_momentum` and `goldmine_6x_consensus` confirmed absent from active picks. Active gate health: all 37 current picks pass all gates.

3. **FOREX structural gap:** `non_crypto_consensus` at 0% WR in FOREX — gate framework alone cannot fix this. Investigation needed.

4. **CRYPTO dilution:** `quan_engine` is the primary 7d/30d performance diluter in CRYPTO despite strong 24h/72h windows.

5. **No look-ahead bias detected:** All features computed at pick emission time confirmed. Minor `yfinance` timeout issues addressed.

6. **Project ~40% toward goal:** Tier-2 must be reached simultaneously across all four underperforming asset classes to satisfy the goal.

---

## Audit Script Integration Notes

The `tools/run_audit.py` script (delivered in PR #699) should be:
1. Added to the `audit-dashboard.yml` push-trigger paths if not already present
2. Integrated as a nightly CI check against `dashboard_data.json`
3. Extended to flag `quan_engine` volume concentration as a standard alert

---

*Review by Buffy (Claude, DeepSeek-v4-Pro) — 2026-05-03*
*Comments posted on all 15 open PRs: #704, #700, #699, #681, #676, #669, #668, #661, #660, #658, #655, #644, #625, #615, #608, #597*
*PR #709: docs/freebuff-buffy-pr-review-20260503 → main*