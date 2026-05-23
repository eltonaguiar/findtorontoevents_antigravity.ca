# Review Findings: Recently Added MD Files and Merged PRs

**Date:** 2026-04-22
**Scope:** Recently added/modified markdown files and merged PRs (last 48h)

---

## Recently Added / Modified Markdown Files

| File | Type | Status | Key Content |
|------|------|--------|-------------|
| `docs/OPEN_PR_REVIEW_2026_04_22.md` | Review | Committed | 35 open PRs categorized with merge recommendations |
| `docs/LIBRARY_INTEGRATION_CANDIDATES_2026_04_22.md` | Research | Untracked | 10 open-source quant libraries ranked for integration |
| `docs/AUDIT_PERFORMANCE_DEEP_ANALYSIS_2026_04_22.md` | Analysis | Committed | Deep asset class performance investigation |
| `updates/2026-04-22-24-hour-review.md` | Review | Committed | 24h change summary with key findings |
| `docs/REHAB_AND_MUTATION_AUDIT_2026_04_22.md` | Audit | Untracked | Strategy rehabilitation and mutation audit |
| `docs/WEEKLY_REVIEW_ACTIONABLE_2026_04_22.md` | Review | Untracked | Weekly actionable review |
| `updates/2026-04-22-deep-strategy-investigation-implementation.md` | Update | Untracked | Deep strategy investigation implementation notes |
| `updates/2026-04-22-quant-libraries-integration.md` | Update | Untracked | Quant libraries integration details |

---

## Merged PRs (Last 48 Hours)

| PR | Title | Impact | Notes |
|----|-------|--------|-------|
| #313 | fix: ETF misclassified as equity + archive dedup guard | HIGH | 38,399 duplicate entries purged (87.2% reduction). Fixed asset classification bug. |
| #311 | feat(picks): kill quan_engine_scalp, throttle ml_crypto_predictor, elite_score >= 70 gate | HIGH | Removed confirmed bleeder. Throttled noisy predictor. Raised quality bar. |
| #310 | diag: 48h performance investigation + Ollama fact-check + 3-agent reconciliation | MEDIUM | Investigation data archived. Findings should feed into strategy rehab. |
| #295 | feat(elite-scorer): non-crypto TIER1/TIER2 symbol sets | MEDIUM | Expands coverage to equities, forex, commodities. Critical for diversification. |
| #294 | enh: extend Phase-1 TOD block (16-21 UTC) + conf dead-zone gate | HIGH | 50pp time-of-day edge now exploited. Reduces exposure during poor windows. |
| #293 | feat(backtester): Deflated Sharpe + Bonferroni multiple-testing correction | HIGH | Statistical rigor for backtests. Will filter false strategies. |
| #291 | diag: deep strategy investigation by asset class (n=3500) | HIGH | Found 50pp TOD edge. Found zombie strategies. Informs PR #294 and #309. |
| #285 | fix(audit): fail-closed fallback + score <= 0 reject in active-pick gates | HIGH | Safety-critical. Prevents negative-score picks from reaching active book. |

### PRs Still Open (as of 2026-04-22)

| PR | Title | Priority | Recommendation |
|----|-------|----------|------------------|
| #315 | fix: forward win-rate compat + weekly ML/GHA ops review docs | HIGH | Merge -- latest fix, low risk |
| #314 | Phase 4 M1: unified feed risk-metrics pipeline (DRAFT) | MEDIUM | Needs reviewer sign-off |
| #307 | feat(audit_dashboard): HF Quant Scorer | MEDIUM | Large feature, review for conflicts |
| #306 | feat(alpha_engine): AutoHedge-inspired multi-agent prediction pipeline | MEDIUM | Architecture review needed |
| #304 | exp: persona-critic committee (Buffett/Munger/Druckenmiller/Taleb/Burry) | LOW | Hold -- novel but unproven |
| #303 | exp: 5 advanced HF tools -- Hurst, CUSUM, Vol-sizer, HRP, MTF ensemble | LOW | Consider splitting into smaller PRs |
| #302 | fix: retire non_crypto_consensus + X-post repo review + per-class tweak queue | HIGH | Merge -- cleanup PR |
| #301 | exp: hedge-fund gap-fillers -- 684 FLAT_CLOSE_BUG picks found | LOW | Bug findings should become fix PRs |
| #300 | exp: skill-vs-luck filter -- ZERO verified across 174 strategies | LOW | Close if result is final |
| #298 | exp: AutoHedge-style committee scorer -- +1.30 PF lift on equity, mixed elsewhere | LOW | Hold -- mixed results |

---

## Key Findings from Reviews

### 1. Archive Deduplication Success

PR #313 successfully purged **38,399 duplicate entries** (87.2% reduction) from `closed_picks.archive.jsonl` without data loss. This is a significant data integrity win.

**Risk:** The dedup guard must remain active. Without it, duplicates will re-accumulate rapidly given the 120-system fleet.

### 2. Strategy Bleeders Eliminated

PR #311 killed `quan_engine_scalp` and throttled `ml_crypto_predictor`. This aligns with the deep audit findings that identified these as consistent losers.

**Remaining Bleeders (from deep analysis):**
- `kimi_signal_tracking`: -1,001% PnL (worst system globally)
- `copy_trader_intel`: -753% PnL
- `claude_gainer_st`: -159% on 1,274 trades
- `mercury2_fast`: PF 0.07
- `cta_replicator`: 8.3% WR
- `goldmine_stocks`: 0% WR

**Action:** These must be killed or rehabilitated immediately. PR #311 set the precedent.

### 3. Time-of-Day Edge Now Exploited

PR #294 implemented the TOD block (16-21 UTC) + confidence dead-zone gate based on PR #291's findings of a **50pp time-of-day edge**.

**Impact:** This should improve CRYPTO win rates from the current 41.8%. Monitor 8h cycle reviews for evidence.

### 4. Statistical Rigor Improving

PR #293 added Deflated Sharpe + Bonferroni correction. PR #295 added non-crypto TIER1/TIER2 symbol sets. Together these raise the bar for strategy validation.

**Impact:** Going forward, fewer false strategies should reach production. However, this does NOT retroactively fix existing bleeders.

### 5. Fail-Closed Safety Critical

PR #285 added fail-closed fallback and score <= 0 rejection. Combined with PR #311's elite_score >= 70 gate, the active-pick pipeline is now much safer.

**Impact:** Should reduce the "zombie strategies" problem identified in perf-review cycles 8-10.

### 6. Library Integration Candidates Doc

`docs/LIBRARY_INTEGRATION_CANDIDATES_2026_04_22.md` proposes 10 open-source quant libraries. Top candidates:
1. **mlfinlab** -- triple-barrier labeling, purged CV, PBO
2. **vectorbt** -- GPU-speed parameter sweeps
3. **Riskfolio-Lib** -- HRP, CVaR portfolio optimization
4. **skfolio** -- sklearn-native portfolio optimization
5. **QuantStats** -- comprehensive reporting

**Recommendation:** Prioritize mlfinlab + vectorbt. These directly attack the backtest-forward gap identified in the deep audit (78 strategies with >10pp degradation).

### 7. Performance Still Catastrophic

Despite all the fixes merged in the last 48h, the **live dashboard shows:**
- Overall PnL: -1,031.68% raw
- Overall PF: 0.91
- CRYPTO: PF 0.99 (breakeven on 22,128 trades)
- FOREX: PF 0.27 (catastrophic on 1,413 trades)
- Only EQUITY is healthy (PF 1.39, +217%)

**Conclusion:** The merged fixes are structural improvements but will take time to show in live metrics. The existing bleeders must be purged faster.

### 8. High-Conviction Pick Desert

The 24-hour review notes that only **2 out of 67 active picks (3%)** passed the HC gate -- both CRYPTO grade-b. Five of six asset classes have ZERO HC picks.

**Root Cause:** Score compression and trust-tier promotion bottlenecks.

**Action:** The fail-closed gate (PR #285) and elite_score >= 70 (PR #311) may make this worse before it gets better. Monitor HC pick count daily.

---

## Recommendations

### Immediate (Today)
1. **Merge #315** -- forward win-rate compat + ops docs
2. **Merge #302** -- retire non_crypto_consensus cleanup
3. **Kill `kimi_signal_tracking`** -- -1,001% PnL, no justification for keeping it alive
4. **Kill `copy_trader_intel`** -- -753% PnL
5. **Monitor dashboard** for TOD gate impact (PR #294)

### Short-Term (This Week)
6. **Merge #307 (HF Quant Scorer)** if no conflicts -- will improve scoring granularity
7. **Merge #306 (AutoHedge pipeline)** after architecture review
8. **Start mlfinlab integration** -- highest impact library per candidate doc
9. **Close or convert remaining perf-review PRs** -- data is now stale
10. **Address HC pick desert** -- investigate why non-crypto asset classes have zero HC signals

### Medium-Term (Next 2 Weeks)
11. **Integrate vectorbt** for walk-forward validation
12. **Re-evaluate all strategies** with Deflated Sharpe (PR #293)
13. **Implement portfolio-level drawdown circuit breaker** at 20%
14. **Cap symbol concentration** -- no single symbol > 5% of book
15. **Add short-biased strategies** for downtrending markets (currently 6.2% WR)

---

## Files Requiring Follow-Up

| File | Issue | Action |
|------|-------|--------|
| `docs/LIBRARY_INTEGRATION_CANDIDATES_2026_04_22.md` | Untracked | Stage and commit, or add to .gitignore |
| `docs/REHAB_AND_MUTATION_AUDIT_2026_04_22.md` | Untracked | Stage and commit |
| `docs/WEEKLY_REVIEW_ACTIONABLE_2026_04_22.md` | Untracked | Stage and commit |
| `updates/2026-04-22-deep-strategy-investigation-implementation.md` | Untracked | Stage and commit |
| `updates/2026-04-22-quant-libraries-integration.md` | Untracked | Stage and commit |

---

*Generated by Claude Code on 2026-04-22*
