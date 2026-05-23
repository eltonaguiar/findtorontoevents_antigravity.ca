# CRITICAL BLOCKER: Placeholder Stats in HC Gate-Passing Picks

**Date:** 2026-04-22
**Blocker ID:** #2 - Placeholder Stats vs Realized Edge
**Severity:** CRITICAL - Trading Halt Recommended
**Analyst:** Claude Code (Ollama/kimi-k2.5-cloud)

---

## Executive Summary

**Finding:** All 50 crypto picks passing the HIGHFWWRABV55_SCOREABOVE50_V4 gate are `clone_hl_copy_*` rows exhibiting a suspicious **identical-triple pattern** where `score == n ≈ fwd_wr` across unrelated symbols. This is statistically impossible for real computed metrics.

**Conclusion:** These are **placeholder stats, not realized edge**. Trading on these picks would be trading on fabricated data.

---

## Evidence Summary

### 1. The Identical-Triple Pattern

| Source Pattern | Score | n | fwd_wr | Symbols |
|----------------|-------|---|--------|---------|
| `clone_hl_copy_PensionFund_24M` + `clone_hl_copy_lb_None` | 100 | 100 | 100.0% | BTC, BNB, AVAX, LINK, NEAR, SUI, RENDER, HYPE, ONDO |
| `clone_hl_copy_whale_433roi` | 85 | 85 | 85.7% | Multiple |
| `clone_hl_copy_lb_None` (shorts) | 80 | 80 | 80.0% | BTC, ETH, ADA, XRP, SOL, DOGE, AVAX, LINK… |

**Red Flag:** Score, sample count (n), and forward win rate are nearly identical across **unrelated symbols** with different volatilities and market structures. This is not a computed statistic—it's a placeholder pattern.

### 2. Missing Trust Indicators

Every row exhibits:
- `trust_tier=""` (empty string)
- `trust_score=null`

Per `feedback_clone_hl_placeholder_stats.md` (added 2026-04-22): *"50/50 rows passing HIGHFWWRABV55_SCOREABOVE50 gate were clone_hl_copy_* with identical-triple stats… Treat as placeholder, not realized edge; quarantine before any HC-label account trade."*

### 3. Historical Corroboration

| Source | Finding |
|--------|---------|
| `updates/2026-04-17-edge-deepscan-5-filter-catalog.md:179-196` | Flagged HIGHFWWRABV55_SCOREABOVE50_V3 — 8/8 red picks, historical edge collapsed to n=1 |
| `edge_report.md` | Only **1/31 active picks** (3.2%) pass the real HC gate, not 50 |
| System-wide performance | WR 31.1%, PF 0.72 on 3,500 trades — contradicts 80-100% WR claims |

### 4. Memory-Document Cross-References

| Memory Document | Relevant Finding |
|-----------------|------------------|
| `feedback_confidence_is_not_edge.md` | *"Never conflate self-reported confidence/R:R math with realized profitability"* |
| `feedback_long_source_bias.md` | *"7 sources are 99-100% LONG-only; reject their LONGs on red BTC 4h"* — clone_hl_copy sources fit this pattern |
| `feedback_gate_at_execution_not_generation.md` | Filter-named accounts bypass gate at pick-generation; must re-run at execution |
| `feedback_clone_hl_placeholder_stats.md` | Explicitly flags this exact pattern as placeholder stats |

---

## Gate Analysis Results

Applied full HC gate (`scoreCompoundFloor:50` + `forwardWRMinPct:55`) to `alpha_engine/data/active_picks.json` (126 rows):

| Asset Class | n | Longs | Shorts | Median Score | Naive Gate Pass |
|-------------|---|-------|--------|--------------|-----------------|
| **CRYPTO** | 75 | 53 | 21 | 71.0 | **50** |
| FOREX | 24 | 9 | 15 | 52.0 | 0 |
| EQUITY | 12 | 12 | 0 | 52.0 | 0 |
| COMMODITY | 9 | 5 | 4 | 51.0 | 0 |
| STOCKS | 3 | 3 | 0 | 56.0 | 0 |
| FUTURES | 3 | 3 | 0 | 56.0 | 0 |

**Critical Observation:** All 50 passing picks are CRYPTO from `clone_hl_copy_*` sources. Zero picks from legitimate quantitative sources (luxalgo, dna_winner, etc.) pass the gate.

---

## Options Analysis

### Option (a): Place the Single Real HC-Gate Pass
**Approach:** Use the 1 pick from `edge_report.md` that legitimately passes.

**Pros:** Only trade verified real edge.
**Cons:** Single pick = no diversification; may not fill.
**Requirements:** Need pick ID from `hc_filter.js` run against `dashboard_data.json`.

### Option (b): Drop fwd_wr≥55 Requirement, Route Non-Clone Sources
**Approach:** Trade luxalgo/dna_winner SHORTs (per LONG-bias memo) on this account.

**Pros:** Avoids placeholder stats; trades proven strategies.
**Cons:** Account label "HIGHFWWRABV55_SCOREABOVE50" no longer matches traded picks; audit trail confusion.
**Risk:** Label mismatch could violate compliance/logging requirements.

### Option (c): Accept Clone_hl_copy Picks (Explicit Override)
**Approach:** Trade the 50 placeholder-stat picks with documented override.

**Pros:** Immediate action; high pick count.
**Cons:** **Trading on fabricated data**; likely significant losses.
**Verdict:** ❌ **UNACCEPTABLE** - Violates "Confidence ≠ Edge" principle.

### Option (d): Fix Placeholder-Stat Pipeline First
**Approach:** Debug why `clone_hl_copy_*` rows have `score==n≈fwd_wr`; fix data pipeline.

**Pros:** Addresses root cause; enables legitimate trading.
**Cons:** Delay; requires engineering resources.
**Timeline:** Likely 24-48 hours for fix + validation.

---

## Recommendation

**Primary Recommendation: Option (d) + Short-Term Option (a)**

1. **Immediate (Today):** Halt trading on HIGHFWWRABV55_SCOREABOVE50_V4 account.
2. **Identify the 1 real pick** from `edge_report.md` and place it manually if desired.
3. **Root Cause Fix (24-48h):** Debug `alpha_engine/data/active_picks.json` generation pipeline.
   - Why do `clone_hl_copy_*` rows have identical-triple stats?
   - Why is `trust_tier` empty?
   - Why is `trust_score` null?
4. **Validation:** Re-run HC gate after fix; verify legitimate picks pass.
5. **Resume Trading:** Only after confirmed real edge exists.

---

## Required Actions

### Engineering Tasks
- [ ] Locate and examine `alpha_engine/data/active_picks.json` generation code
- [ ] Identify where `clone_hl_copy_*` placeholder stats originate
- [ ] Add data validation: `score == n` should trigger warning/exception
- [ ] Fix trust scoring pipeline for copy-trader sources
- [ ] Re-run HC gate after fix and verify

### Trading Desk Tasks
- [ ] ❌ **HALT** all trading on HIGHFWWRABV55_SCOREABOVE50_V4 account
- [ ] Retrieve candidate list from `/tmp/hf55_s50_candidates.json` for analysis
- [ ] Identify the 1 real pick from `edge_report.md` (if manual trading desired)
- [ ] Document placeholder-stat incident for post-mortem

### Documentation Tasks
- [ ] Update `feedback_clone_hl_placeholder_stats.md` with this incident
- [ ] Add data validation to HC gate to detect score==n patterns
- [ ] Create runbook for future placeholder-stat detection

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Trading on fabricated data | Certain (if not halted) | **Severe** (financial loss) | **HALT trading immediately** |
| Delayed strategy deployment | High | Medium | Fix pipeline in 24-48h |
| Compliance issues from label mismatch | Medium (Option b) | Medium | Avoid Option b; use d then a |
| Recurrence of placeholder stats | Medium | High | Add validation gates |

---

## Supporting Artifacts

- Candidate list: `/tmp/hf55_s50_candidates.json` (50 rows)
- Gate definition: `audit_dashboard/hc_filter.js:23-50`
- Source data: `alpha_engine/data/active_picks.json` (126 rows)
- Historical flag: `updates/2026-04-17-edge-deepscan-5-filter-catalog.md:179-196`
- Edge report: `edge_report.md`

---

## References

- `feedback_confidence_is_not_edge.md` - Core principle
- `feedback_long_source_bias.md` - Clone source bias documented
- `feedback_gate_at_execution_not_generation.md` - Execution gate requirement
- `feedback_clone_hl_placeholder_stats.md` - Specific placeholder pattern flag
- Memory: System-wide WR 31.1% / PF 0.72 reality check

---

**Status:** ⛔ **TRADING HALT RECOMMENDED**

**Next Review:** After pipeline fix + validation (target: 2026-04-24)
