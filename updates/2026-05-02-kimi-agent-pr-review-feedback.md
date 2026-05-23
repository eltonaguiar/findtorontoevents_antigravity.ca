# Kimi Agent Asset Performance PR Review — Feedback & Analysis
**Date:** 2026-05-02  
**Reviewer:** opencode (based on Kimi Agent attachment files)  
**Scope:** 15 open PRs + Hedge Fund Audit Report + Integration Plan

---

## Executive Summary

The Kimi Agent produced a thorough hedge-fund-grade audit with high-quality analysis. The core findings are **validated**:

| Asset | 7d PF | 7d WR | Tier Status | Gap to Tier-2 |
|-------|--------|--------|-------------|--------------|
| CRYPTO | 1.33 | 44.5% | 🟡 Approaching | PF +0.17, WR +5.5% |
| EQUITY | 1.07 | 48.5% | 🟡 Approaching | PF +0.43, WR +1.5% |
| FOREX | 0.43 | 16.7% | 🔴 Far Below | PF +1.07, WR +33.3% |
| COMMODITY | 1.18 | 20.0% | 🔴 Below | PF +0.32, WR +30% |
| ETF | 1.57 | 63% | ✅ Above T2 | — |

**Verdict:** ~40% achieved toward "phenomenal performance across ALL asset classes" goal.

---

## PR-by-PR Recommendations

### ✅ MERGE Queue (after rebase)

| PR | Verdict | Action |
|----|---------|--------|
| **#676** | ✅ MERGE | Clean data-quality PR. Remove duplicates + SVG placeholders. No code changes. |
| **#669** | ✅ MERGE | B2 coverage lane grid. 12 tests, additive, backward-compatible. Rebase first. |
| **#655** | ✅ MERGE | Docs-only PR roadmap. No production risk. |
| **#625** | ✅ MERGE | Docs PR for peer agent triage state. |

### 🛑 REQUEST_CHANGES (must fix before merge)

| PR | Blocker | Required Action |
|----|---------|-----------------|
| **#615** | `__builtins__.print` regression (8 test failures), circuit breaker reset with -25,465% DD | Fix `import builtins; builtins.print = print`. Revert `circuit_breaker.json`. Split resolver v2.1 to PR #610. |
| **#597** | Missing staleness filter from `main`, 7 failing tests | Rebase onto `origin/main`. Split 4 workstreams into separate PRs. |
| **#644** | Scope dishonesty (claims 1 file, delivers 9), zero tests for new CI gates, thresholds from n=3 samples | Add `tests/test_quality_monitor.py`. Fix scope claim. Justify n=3 thresholds. |
| **#665** | Undocumented walkforward payload removal breaks frontend | Restore `walkforward` block OR document removal + update frontend. Rebase. |
| **#703** | Overstates impact ("closes Goal-#1" but MDD gap is 55%) | Add unit tests for kelly clamp. Document vol-target calc. |
| **#699** | No volume cap enforcement, no tests for config loading | Add enforcement in `quality_gates.py` OR document as Phase 2. Add `tests/test_unified_gates.py`. Rebase. |
| **#681** | "11 failing strategies" lacks evidence table | Add strategy evidence table with PF/WR. Add unit tests. Coordinate with #699. |

### ⚠️ HOLD / DO-NOT-MERGE

| PR | Reason |
|----|--------|
| **#660** | Sweeping gate changes ("replace elite_score", "abolish WINNER_FILTER") without documented replacements or tests. |
| **#658** | "Comprehensive" scope likely duplicates #699. Needs scope clarification. |
| **#661** | 3 major features bundled (Track Calculator, PSR/DSR, Decay Tracker). Split needed. Overlaps #699/#681. |
| **#608** | Branch behind `main`, CI failing. Code is safe but needs rebase. |

### 📊 HOLD (branch hygiene)

| PR | Reason |
|----|--------|
| **#668** | `REQUEST_CHANGES` per attachment. `ml_gatekeeper` config in #699 depends on this. |

---

## Key Findings from Audit Reports

### 1. CRYPTO — Approaching Tier-2 (closest)
- **24h/72h:** Tier-1 quality (PF 3.10, WR 60.6%)
- **7d/30d drag:** `quan_engine` (18% volume, PF 0.70) + `unknown` (6.8%, PF 0.35)
- **Action:** Cap `quan_engine` volume at 15% or raise quality floor

### 2. EQUITY — Monotonic degradation 30d→7d
- **30d:** Tier-1 (PF 3.21, WR 61.3%)
- **7d drag:** `stocks_rsi2_pullback` (42% volume, PF 0.89, WR 35.7%)
- **Action:** `goldmine_6x_consensus` kill (#692) should help. Monitor `stocks_rsi2_pullback`

### 3. FOREX — Structurally broken
- **Best window:** 24h n=7 (PF 1.61) — statistically meaningless
- **7d:** PF 0.43, WR 16.7%, MDD 20%
- **Drags:** `forex_rsi2_mean_reversion` (JPY pre-#687 picks aging out), `non_crypto_consensus` (0% WR, n=18)
- **Action:** Re-audit in 72h after JPY picks age out. Investigate `non_crypto_consensus`

### 4. COMMODITY — Thin + weak
- **7d:** PF 1.18, WR 20%, n=60
- **Challenge:** 69% of 30d picks are "flat" (near-zero PnL)
- **Action:** Higher admission thresholds until more signal history

### 5. ETF — Best performing class
- **7d:** PF 1.57, WR 63% (Tier-2)
- **30d:** PF 4.06, WR 78% (Tier-1)
- **Action:** Use as model for other asset classes

---

## Integration & Testing Plan (14-Day Timeline)

### Phase 0 (Days 0-2): Foundation
- [ ] Merge #669 (B2 grid), #676 (data quality), #655, #625
- [ ] Rebase #699, add config loader tests
- [ ] CI integration: `python tools/run_audit.py --output audit.json`

### Phase 1 (Days 3-7): Monitoring
- [ ] Re-audit FOREX after JPY pre-#687 picks age out
- [ ] Investigate `non_crypto_consensus` FORCE_CLOSED pattern
- [ ] EQUITY 7d should improve after `goldmine_6x` ages out

### Phase 2 (Days 8-14): Enforcement
- [ ] Cap `quan_engine` volume at 15% in CRYPTO
- [ ] Mutation review for `stocks_rsi2_pullback` (halve notional)
- [ ] Penny stock / meme coin framework (if data sources ready)

### Phase 3 (Days 15-30): Optimization
- [ ] All asset classes at Tier-2 minimum
- [ ] At least one class at Tier-1
- [ ] Fine-tune per-asset thresholds based on enforcement data

---

## Critical Issues Blocking Goal Achievement

| Issue | Priority | Status |
|-------|----------|--------|
| #686 FOREX quality regression | P0 | Being addressed by #687+#692 |
| #690 `ml_enhanced_*` -2.00% pattern | P2 | Open — needs investigation |
| #693 EQUITY 7d degradation | P1 | Monitoring after #692 |
| #696 Walkforward payload removed by #665 | P1 | Needs frontend fix |
| `quan_engine` volume drag | P1 | Cap at 15% (Phase 2) |
| `non_crypto_consensus` 0% WR | P1 | Investigate FORCE_CLOSED pattern |

---

## Config Recommendations (`config_revised.yaml`)

The proposed `config_revised.yaml` is well-structured. Key recommendations:

1. **Add explicit enforcement:** Config defines `max_strategy_volume_pct: 15` but no code enforces it
2. **Lower FOREX thresholds:** `min_pf_for_admission: 1.0`, `min_wr_for_admission: 40` — appropriate given structural difficulty
3. **ETF higher bar:** `min_pf_for_admission: 1.5` — correct given strong performance
4. **BOND activation:** Keep `active: false` until n≥50 historical picks
5. **ml_gatekeeper:** Keep `enabled: false` until PR #668 merges and is validated

---

## Fabrication Risk Assessment

Per the attachment files:
- ✅ `HEDGE_FUND_AUDIT_REPORT_2026_05_02.md`: No fabricated stats (uses live `dashboard_data.json` n=3500)
- ✅ `EVIDENCE_REPORT_2026_05_02.md`: All claims backed by concrete pick walkthroughs
- ✅ `GOAL_ASSESSMENT_2026_05_02.md`: Honest "40% achieved" verdict
- ⚠️ PR #615: `circuit_breaker.json` -25,465.5% DD flagged as "physically impossible"
- ⚠️ PR #644: Thresholds from n=3 samples flagged as "statistically insignificant"

---

## Cross-AI Consensus

| Source | Assessment |
|--------|-----------|
| **Kimi K2** | 6 merged PRs significant progress. FOREX/COMMODITY still far below goal. |
| **Claude Opus 4.7** | EQUITY divergence flagged independently. `stocks_rsi2_pullback` needs monitoring. |
| **GitHub Copilot** | Flagged EQUITY divergence. Cross-validated methodology. |
| **Grok-4** | Confirmed JPY-cross refutation and live-data methodology. |

---

## Next Steps

1. **Author:** Address `REQUEST_CHANGES` blockers on #615, #597, #644, #665, #703, #699, #681
2. **Author:** Split bundled PRs (#597, #660, #658, #661) into focused workstreams
3. **Reviewer:** Rebase #608, #668 onto `origin/main`
4. **CI:** Configure status checks (many PRs show "0 statuses" — no CI running)
5. **Audit:** Re-run `run_audit.py` after 72h to measure JPY-aging effect on FOREX

---

*This feedback is based on attachment files from `C:\Users\zerou\Downloads\Kimi_Agent_Asset Performance PR Review (2)\` including config, evidence reports, goal assessment, audit report, integration plan, PR action plan, and individual PR reviews.*
