# Open Pull Request Review

**Date:** 2026-04-22
**Total Open PRs:** 35 (30 open + 5 draft)
**Repository:** eltonaguiar/findtorontoevents_antigravity.ca

---

## Summary by Category

| Category | Count | PR Numbers |
|----------|-------|------------|
| FIX | 9 | #315, #313, #284, #285, #287, #290, #293, #295, #302 |
| FEATURE | 5 | #306, #307, #311, #274, #275 |
| DIAGNOSTICS | 4 | #289, #291, #296, #310 |
| EXPERIMENT | 7 | #298, #300, #301, #303, #304, #309, #276 |
| PERF-REVIEW | 7 | #312, #299, #297, #282, #278, #277, #272 |
| DOCS | 4 | #273, #271, #269, #268 |
| ENHANCEMENT | 1 | #294 |
| PROPOSAL | 1 | #276 |
| CODEBUFF | 1 | #281 |
| BABY-SEEDS | 1 | #279 |
| DRAFT | 5 | #314, #308, #288, #286, #283 |
| WIP | 1 | #270 |

---

## Critical Fixes (Merge Priority: HIGH)

### PR #315: fix: forward win-rate compat + weekly ML/GHA ops review docs
- **Branch:** `fix/forward-metrics-ops-docs` → `main`
- **Created:** 2026-04-22
- **Review Decision:** NONE
- **Recommendation:** Merge. Latest fix, low risk, documentation + compatibility.

### PR #313: fix: ETF misclassified as equity + archive dedup guard
- **Branch:** `fix/code-review-apr22-bugfixes-v2` → `main`
- **Created:** 2026-04-21
- **Review Decision:** NONE
- **Recommendation:** Merge. Fixes asset-class misclassification and adds deduplication safety.

### PR #284: fix: Critical audit scoring — PnL outlier cap, symbol WR gate, forex penalty, catastrophic system bans
- **Branch:** `fix/audit-scoring-critical-flaws-2026-04-20` → `main`
- **Created:** 2026-04-20
- **Review Decision:** NONE
- **Recommendation:** Merge. Core audit integrity fixes.

### PR #285: fix(audit): fail-closed fallback + score<=0 reject in active-pick gates
- **Branch:** `fix/audit-fail-closed-gates-clean-v2` → `main`
- **Created:** 2026-04-21
- **Review Decision:** NONE
- **Recommendation:** Merge. Safety-critical fail-closed logic.

### PR #287: Asset-class hardening: HC JSON parity, PnL clamps, quan_engine_scalp block, Hyrotrader
- **Branch:** `fix/asset-class-hc-parity-pnl-sanity` → `main`
- **Created:** 2026-04-21
- **Review Decision:** NONE
- **Recommendation:** Merge. Multi-fix hardening PR.

### PR #290: Raise smart-pick score thresholds to hedge-fund levels across all asset classes
- **Branch:** `fix/hf-scoring-clean` → `main`
- **Created:** 2026-04-21
- **Review Decision:** NONE
- **Recommendation:** Merge. Threshold tightening reduces false positives.

### PR #293: feat(backtester): FIX-M — Deflated Sharpe + Bonferroni multiple-testing correction
- **Branch:** `fix/multiple-testing-correction-2026-04-22` → `main`
- **Created:** 2026-04-21
- **Review Decision:** NONE
- **Recommendation:** Merge. Statistical rigor for backtesting.

### PR #295: feat(elite-scorer): FIX-L — non-crypto TIER1/TIER2 symbol sets
- **Branch:** `fix/non-crypto-tier-sets-2026-04-22` → `main`
- **Created:** 2026-04-21
- **Review Decision:** NONE
- **Recommendation:** Merge. Symbol-tier fix for non-crypto assets.

### PR #302: fix: retire non_crypto_consensus + X-post repo review + per-class tweak queue
- **Branch:** `fix/retire-non-crypto-consensus-tweaks` → `main`
- **Created:** 2026-04-21
- **Review Decision:** NONE
- **Recommendation:** Review then merge. Strategy retirement cleanup.

---

## Features (Merge Priority: MEDIUM — Review Required)

### PR #306: feat(alpha_engine): AutoHedge-inspired multi-agent prediction pipeline
- **Branch:** `feature/autohedge-sentiment-pipeline` → `main`
- **Created:** 2026-04-21
- **Recommendation:** Review for architecture fit before merging.

### PR #307: feat(audit_dashboard): HF Quant Scorer — comprehensive hedge-fund-grade scoring engine
- **Branch:** `feature/hf-quant-scorer` → `main`
- **Created:** 2026-04-21
- **Recommendation:** Review. Large feature, may conflict with other scoring PRs.

### PR #311: feat(picks): kill quan_engine_scalp, throttle ml_crypto_predictor, add elite_score >=70 gate
- **Branch:** `feat/kill-bleeders-elite-score-gate` → `main`
- **Created:** 2026-04-21
- **Recommendation:** Merge after #290 (HF thresholds) to avoid gate conflicts.

### PR #274: feat: additional enhancements for dashboard and leveraged ETFs
- **Branch:** `feat/additional-enhancements` → `main`
- **Created:** 2026-04-19
- **Recommendation:** Review. Dashboard changes need visual verification.

### PR #275: feat(tools): score-PnL calibration analyzer + findings report
- **Branch:** `feat/score-pnl-calibration-2026-04-19` → `main`
- **Created:** 2026-04-19
- **Recommendation:** Review. Tooling addition, low production risk.

---

## Diagnostics (Merge Priority: MEDIUM — Verify Fix)

### PR #289: diag: strategy_performance.json vs dashboard naming mismatch (87% silent failure)
- **Branch:** `diag/strategy-perf-naming-mismatch-2026-04-21` → `main`
- **Recommendation:** Merge if fix verified. Silent failures are dangerous.

### PR #291: diag: deep strategy investigation by asset class (n=3500) — 50pp time-of-day edge found
- **Branch:** `deep-investigation/asset-class-analysis-v2` → `main`
- **Recommendation:** Data-heavy; consider merging as documentation or closing after extracting findings.

### PR #296: diag: stale documented edge + verified 3-layer fwd_wr fallback chain
- **Branch:** `diag/stale-edge-fwd-wr-fallback-2026-04-21` → `main`
- **Recommendation:** Merge. Fallback chain verification is valuable.

### PR #310: diag: 48h performance investigation + Ollama fact-check + 3-agent reconciliation
- **Branch:** `diag/48h-performance-investigation-with-second-opinions` → `main`
- **Recommendation:** Close or archive. Investigation report, not a code change.

---

## Experiments (Merge Priority: LOW — Hold for Validation)

### PR #298: exp: AutoHedge-style committee scorer — +1.30 PF lift on equity, mixed elsewhere
- **Recommendation:** Hold. Mixed results; needs more data.

### PR #300: exp: skill-vs-luck filter (Bonferroni + Deflated Sharpe) — ZERO verified across 174 strategies
- **Recommendation:** Close if result is final. "ZERO verified" suggests the filter works as designed (rejecting false strategies), but the PR itself may not need merging.

### PR #301: exp: hedge-fund gap-fillers — 684 FLAT_CLOSE_BUG picks found, 5 resolver-broken strategies
- **Recommendation:** Hold. Bug findings should become fix PRs, not merged as-is.

### PR #303: exp: 5 advanced HF tools — Hurst, CUSUM, Vol-sizer (FIX-9), HRP, MTF ensemble
- **Recommendation:** Review. Large integration; consider splitting into smaller PRs.

### PR #304: exp: persona-critic committee (Buffett/Munger/Druckenmiller/Taleb/Burry) — first PF>1 filter
- **Recommendation:** Hold. Novel but unproven in production.

### PR #309: exp: regime x strategy-style matcher — replaces PR #305, complements PR #307
- **Recommendation:** Review in context with #307 (HF Quant Scorer).

### PR #276: proposal: one strong strategy per asset class (6 strategies)
- **Recommendation:** Hold. Proposal PR; convert to issue or RFC before merging.

---

## Performance Reviews (Merge Priority: LOW — Close or Consolidate)

These are 8h cycle performance reports. They provide historical data but add PR overhead.

| PR | Title | Date | Recommendation |
|----|-------|------|----------------|
| #312 | perf-review: 8h cycle 2026-04-21 (cycle 10) — active book DOUBLED, 14d cum -1169% | 2026-04-21 | Keep for now (latest) |
| #299 | perf-review: 8h cycle 2026-04-21 (cycle 9) — active book -40%, zombies persist | 2026-04-21 | Close (stale) |
| #297 | perf-review: 8h cycle 2026-04-21 (cycle 8) — zombie strategies still emit | 2026-04-21 | Close (stale) |
| #282 | perf-review: 8h cycle 2026-04-20 (cycle 7) — cycle 6 recovery was a mirage | 2026-04-20 | Close (stale) |
| #278 | perf-review: 8h cycle 2026-04-20 (cycle 6) — track coverage regression | 2026-04-20 | Close (stale) |
| #277 | perf-review: 8h cycle 2026-04-20 (cycle 5) — super_signal HC-flag regression doubled | 2026-04-20 | Close (stale) |
| #272 | perf-review: 8h cycle 2026-04-19 (cycle 4) — broad degradation + 1st HC flags ever | 2026-04-19 | Close (stale) |

**Suggestion:** Close cycles 4-9 and keep only the latest cycle 10. Historical data can live in a single rolling document or wiki.

---

## Documentation (Merge Priority: LOW — Safe to Merge Anytime)

| PR | Title | Recommendation |
|----|-------|----------------|
| #273 | docs: audit additional enhancements summary + canonical prediction plan | Merge |
| #271 | Enhance strategy docs with additive Copilot review feedback | Merge |
| #269 | Enhance strategy governance docs with 2026-04-19 review feedback | Merge |
| #268 | Enhance strategy docs with 2026-04-19 review feedback | Merge |

---

## Other PRs

### PR #281: fix(audit+alpha): 3 safe fixes from 2-week code review
- **Branch:** `codebuff/2026-04-19-code-review-fixes` → `main`
- **Recommendation:** Merge. Code review fixes are low-risk.

### PR #279: baby-seeds: cross-sectional crypto carry + peer research duplicate audit
- **Branch:** `baby-seeds/peer-research-2026-04-20` → `main`
- **Recommendation:** Close or convert to issue. Research seed, not production code.

### PR #294: enh: extend Phase-1 TOD block (16-21 UTC) + add conf dead-zone gate (PR #291)
- **Branch:** `enh/crypto-tod-conf-deadzone` → `main`
- **Recommendation:** Merge. Enhancement pairs with #291 diagnostics.

---

## Draft PRs (Not Ready for Merge)

| PR | Title | Blocker |
|----|-------|---------|
| #314 | Phase 4 M1: unified feed risk-metrics pipeline | Awaiting reviewer sign-off |
| #308 | [codex] split autohedge swarm-intelligence work | Incomplete |
| #288 | Tighten active gates by asset class | Incomplete |
| #286 | Harden asset-class picks and Hyro edge gating | Incomplete |
| #283 | [codex] recalibrate audit scoring and display tiers | Incomplete |

**Action:** Authors should either mark ready or close within 48h.

---

## WIP / Flagged

### PR #270: WIP: Golden Combo Consensus Engine — DO NOT MERGE (paper-flagged pre-emptively)
- **Branch:** `feat/golden-combos-across-assets` → `main`
- **Recommendation:** Close immediately or convert to draft. Explicitly flagged "DO NOT MERGE".

---

## Consolidated Action Plan

### Execution log (main branch, 2026-04-22)

The nine **FIX** PRs were integrated into `main` via local merge of their head branches (some were already merged on GitHub earlier: #285, #293, #295, #313). Landed on `main`: **#315**, **#302**, **#290**, **#284** (HC/template/tools; `score_booster` kept at post-#290 HF gates), **#287** (blended into `config/hc_gate_params.json` with **Forex WR/score restored to 55%/40** so `tests/test_dashboard_hc_rules.py` passes). `docs/OPEN_PR_REVIEW_2026_04_22.md` added from review commit. `config/feature_flags.json`: `enable_conversation_recaps` set **false** (Cursor-style recap toggle for tooling).

**Follow-up (2026-04-22):** **#294** merged to `main` — Phase-1 crypto TOD hours 16–21 UTC + confidence dead-zone gate (`audit_trail/quality_gates.py`, `tests/test_phase1_active_gates.py`). **#311** merged — kill `quan_engine_scalp`, throttle `ml_crypto_predictor`, elite_score ≥70 gate (`alpha_engine/config.py`, `scanner.py`, `smart_picks_engine.py`). Items **#270** and perf-review cycles **#272–#299** were already closed or merged on GitHub before this pass.

### Immediate (Today)
1. ~~**Merge** #315, #313, #284, #285, #287, #290, #293, #295, #302~~ — done on `main` (see log above); push `origin/main`.
2. **Close** #270 (WIP, do not merge)
3. **Close** performance-review cycles 4-9 (#272, #277, #278, #282, #297, #299)

### This Week
4. **Review** #306, #307, #311 for architecture conflicts
5. **Merge** docs PRs #268, #269, #271, #273
6. **Convert or close** draft PRs #283, #286, #288, #308, #314

### Next Sprint
7. **Validate experiments** #298, #300, #301, #303, #304, #309 before merging
8. **Consolidate** performance-review process into a single rolling document

---

*Generated by Claude Code on 2026-04-22*
