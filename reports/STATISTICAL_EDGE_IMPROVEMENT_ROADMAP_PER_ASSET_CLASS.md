# Statistical Edge Improvement Roadmap — Per Asset Class

**Generated:** 2026-05-15  
**Status:** Ready for implementation prioritization  

---

## Executive Summary

Based on analysis of daily ideas, performance data, and plan reviews, the following roadmap identifies the highest-impact changes to improve statistical edge per asset class. Priority is ranked by **impact × verifiability × actionability**.

---

## Current State Snapshot

| Class | n | WR % | PF | Status |
|-------|---|------|-----|--------|
| **COMMODITY** | 422 | 67.5 | **3.89** | T1 candidate — driven by CT=F single-symbol concentration |
| **EQUITY** | 447 | 53.2 | 1.55 | **T2 confirmed** — widest for expansion |
| **ETF** | 107 | 56.1 | 1.34 | BORDERLINE — WR passes, PF slightly below |
| **CRYPTO** | 7935 | 46.5 | 1.36 | MASKED — top systems elite, class dragged by high-volume losers |
| **FOREX** | 1355 | 46.1 | 0.29 | **STRESSED** — catastrophic PF, needs complete rehab |
| **BOND** | 11 | 54.5 | 0.66 | TOO THIN — needs ramp first |

---

## Tier 1: Immediate Priority (Implement Within 48h)

### Edge #1 — BTC UTC-Hour Death-Zone Filter
**Impact:** 15% WR lift for CRYPTO class  
**Effort:** S (1 hour)  
**Status:** Ready with proven data

- **Problem:** 08-09 UTC = death zone (WR ~30%), 22 UTC = 61.2% WR (n>1000)
- **Solution:** 
  ```python
  # alpha_engine/score_booster.py or smart_picks_engine
  hour = pick.created_at.hour
  if pick.asset_class == "CRYPTO" and hour in (8, 9):
      return SKIP  # death zone
  ```
- **Action:** Add `CRYPTO_HOUR_FILTER=1` env flag, A/B test

### Edge #2 — DB Freshness Guardian Workflow
**Impact:** Prevents silent stalls across all asset classes  
**Effort:** S-M (3-4 hours)  
**Status:** Design ready

- **Problem:** Tables can stop updating without detection
- **Solution:** `.github/workflows/db-freshness-guardian.yml` + `tools/db_freshness_check.py`
- **Action:** Create workflow with per-table thresholds

### Edge #3 — Replace Confidence with Trust Score in HC Gate
**Impact:** Removes anti-edge signal for ETF/CRYPTO  
**Effort:** S (1 hour)  
**Status:** Verified anti-edge

- **Problem:** Confidence inverts on ETF/CRYPTO (ρ = NEGATIVE)
- **Solution:** `HIGH_CONVICTION` button uses `trust_score >= 0.6` instead of `confidence >= 0.85`
- **Action:** `audit_dashboard/template.html` patch

### Edge #4 — FOREX Hard-Disable Until Carry-Factor Ships
**Impact:** Stop bleeding capital immediately  
**Effort:** S (1 hour)  
**Status:** Empirical necessity

- **Problem:** PF 0.29 / -1026% PnL / n=1355 = no working strategies
- **Solution:** `FOREX_HARD_DISABLE=1` env-gate in `alpha_engine/config.py`
- **Action:** Default ON until carry-factor verified

---

## Tier 2: Verification & Foundation (1-2 weeks)

### Edge #5 — multi_asset_cot DB Verification
**Impact:** Validates/disproves entire COMMODITY edge thesis  
**Effort:** S (5 min dispatch + 5 min inspection)  
**Status:** Blockers identified

- **Problem:** PF 21.33 / WR 88.2% / n=144 is implausibly high
- **Solution:** `gh workflow run ab_analysis.yml` → inspect `system_pf_verification.json`
- **Action:** Dispatch workflow, block sizing until MATCH verdict

### Edge #6 — Friction-Adjusted DSR Gate
**Impact:** Institutional-grade viability gate  
**Effort:** S (pending cron)  
**Status:** Tool shipped

- **Problem:** DSR < 0.85 = NOT LIVE_ELIGIBLE regardless of paper-pilot
- **Solution:** `tools/cot_step7_friction_adjusted_mc.py` output validation
- **Action:** Monitor next cron, quarantine if < 0.85

### Edge #7 — Strategy-Level CRYPTO Drag Autopsy
**Impact:** 0.5+ PF lift by quarantining losers  
**Effort:** S (2 hours)  
**Status:** Data structure exists

- **Problem:** `kimi_signal_tracking` (-930%), `alpha_engine_fast` (PF 0.62), `crypto_winners` (PF 0.39)
- **Solution:** Auto-quarantine strategies with >40% volume and PF < 1.0
- **Action:** Add routine to `quality_gates.py` probation system

---

## Tier 3: Class-Specific Expansion (2-4 weeks)

### Edge #8 — PEAD Strategy on EQUITY Top-100
**Impact:** Tier-2 class expansion with documented anomaly  
**Effort:** M (1 day)  
**Status:** Partial infrastructure exists

- **Problem:** Only confirmed Tier-2 class needs more strategies
- **Solution:** `alpha_engine/strategies/pead_equity.py` with 2-day post-earnings window
- **Action:** Backtest against n=447 EQUITY cohort

### Edge #9 — DBMF/KMLM Commodity-Momentum Replication
**Impact:** Institutional-grade CTA strategy with public data  
**Effort:** M (3-5 days)  
**Status:** Industry documented

- **Problem:** Need diversified COMMODITY edge beyond CT=F single-symbol
- **Solution:** `tools/research/dbmf_replication.py` as backtest target
- **Action:** Scaffold, backtest, tier-classify

### Edge #10 — Hyperliquid HLP Carry Replication
**Impact:** Proven Sharpe 2.5-3.5 on $1.5B AUM strategy  
**Effort:** M (3-4 days)  
**Status:** Data key required

- **Problem:** Missing `CFTC_API_KEY` blocks implementation
- **Solution:** `tools/research/hyperliquid_carry.py` backtest
- **Action:** Procure `CFTC_API_KEY` via `gh secret set CFTC_API_KEY`

---

## Tier 4: Multi-Class Infrastructure

### Edge #11 — Exec-Time PCG-5 Portfolio Gate Stack
**Impact:** Systematic edge degradation prevention  
**Effort:** M (8h shadow + 4h enforce)  
**Status:** Novel spec available

- **Problem:** Existing gates are disclosure-only, not enforcement
- **Solution:** 5-gate enforcement: regime-directional, cross-account-net, concentration-reject, profit-lock, correlation-demote
- **Action:** Ship `audit_trail/portfolio_gates.py` in shadow mode

### Edge #12 — Cross-DB Strategy Key Consistency Audit
**Impact:** Data integrity across all classes  
**Effort:** M (1 day)  
**Status:** Design ready

- **Problem:** Strategies can exist in backtests but never emit live
- **Solution:** `tools/cross_db_consistency.py` + nightly workflow
- **Action:** Identify orphaned strategies, mismatched labels

---

## Tier 5: Rehab & Ramp (Pending Foundation)

### Edge #13 — FOREX Carry-Factor Activation
**Impact:** 30-year Sharpe 0.7-0.9 documented alpha  
**Effort:** M (3-4 days)  
**Status:** Blocked until HARD_DISABLE lifted

- **Problem:** MomentumEMA failing, carry is the documented solution
- **Solution:** Long high-yielder, short low-yielder; monthly rebalance
- **Action:** Scaffold `tools/research/forex_carry.py` after clearance

### Edge #14 — BOND Class Ramp
**Impact:** Enable scoring once n≥100 threshold met  
**Effort:** S-M (ongoing)  
**Status:** BOND scanner shipped

- **Problem:** n=11 / charter floor 100 — need months of accumulation
- **Solution:** TLT/IEF momentum, credit spreads, curve steepener
- **Action:** Monitor `dashboard_data.json::performance.asset_class_health`

---

## Implementation Sequence

### Sprint 1 (Mon-Wed)
1. BTC UTC-hour filter (#1)
2. HIGH_CONVICTION trust_score swap (#3)
3. FOREX_HARD_DISABLE (#4)
4. `multi_asset_cot` verification dispatch (#5)
5. CRYPTO drag autopsy (#7)

### Sprint 2 (Thu-Sun)
6. DB Freshness Guardian (#2)
7. Cross-DB consistency audit (#12)
8. PCG-5 shadow mode (#11)

### Sprint 3+ (Next)
9. PEAD EQUITY strategy (#8)
10. Single-persona swarm backfill (#10)

---

## Go/No-Go Decision Gates (Adopted from PLAN_COMPARISON_RESPONSE.md)

| Gate | Checkpoint | Decision |
|------|------------|----------|
| Month 1 | 50+ trades per class, WR > 48% | Continue or extend |
| Month 3 | 500+ trades, Sharpe > 1.0 | Begin 10% live |
| Month 6 | 1000+ trades, consistent PF | Scale to 25% |
| Month 9 | 6mo live profit, WR > 55% | Scale to 50% |

---

## Red Flag Circuit Breakers

```python
RED_FLAGS = {
    "3_consecutive_losing_weeks": True,
    "max_drawdown_exceeds_20%": True,
    "win_rate_below_45%_over_50_trades": True,
    "single_strategy_loses_30%_allocated": True,
    "placeholder_stats_detected": True,  # From PLAN_BLOCKER2 analysis
}
```

---

## Gate Enforcement Protocol

Per `feedback_gate_at_execution_not_generation.md`:

1. **Generation-time gates** - Initial filtering
2. **Execution-time gates** - Final validation with real data
3. **Placeholder stats rejection** - Assert `score != n` or `abs(n - fwd_wr) >= 1` across symbols

---

## Client Communication Standards (MUST INCLUDE)

**NEVER claim:**
- Guaranteed returns
- Specific percentages without 2+ years data
- Sharpe ratios > 3 without 2+ years data
- "Risk-free" anything

**ALWAYS disclose:**
- Algorithmic trading risks
- Past performance ≠ future results
- 15-30% backtest decay typical
- 20-30% drawdowns possible
- 6+ months required to prove edge

---

## Merged Plan Structure (Strategic + Implementation)

### Strategic Layer (Phases)
1. **Phase 1: Triage** (Week 1) — Disable losing strategies, focus on proven ones
2. **Phase 2: Data Accumulation** (Months 1-3) — 30-50 trades/month, 500+ total
3. **Phase 3: Validation** (Months 3-6) — Statistical validation, regime testing
4. **Phase 4: Limited Deploy** (Months 6-12) — Graduated capital (10% → 100%)

### Implementation Layer
- `tools/db_freshness_check.py` — DB health monitoring
- `tools/cross_db_consistency.py` — Strategy key integrity
- `audit_trail/portfolio_gates.py` — Exec-time PCG-5 enforcement
- `alpha_engine/strategies/pead_equity.py` — PEAD backtester

---

## Sizing Gate Requirements

**NO REAL-MONEY SIZING until all conditions met:**

1. `multi_asset_cot` DB-verify returns `MATCH`
2. Friction-adjusted DSR ≥ 0.85
3. 30-day rolling clean performance
4. `docs/MUTATION_THREE_AXIS_PROTOCOL.md` applied to any TP/SL changes
5. Confidence → trust_score swap deployed (anti-edge removed)

---

## Anti-Edge Findings (Must NOT Implement)

| Anti-Pattern | Evidence | Action |
|--------------|----------|--------|
| **Confidence-based HC gate** | ρ = NEGATIVE for ETF/CRYPTO | Removed, use trust_score |
| **claude_gainer_st** | PF 6.80 → blacklisted (real WR 26.5%) | Example: high WR ≠ live edge |
| **Opus-4.7 only consensus** | 9/10 personas backed by same model | Use `--preset non-opus-4` for diversity |
| **Large PR merges** | PR #1017-1020 rejected for Wire-Up violation | Enforce PR size limits |

---

## Success Metrics

| Metric | Current | Target | Timeline |
|--------|---------|--------|----------|
| COMMODITY PF | 3.89 | ≥4.50 | After verification |
| EQUITY PF | 1.55 | ≥2.00 | After PEAD deployment |
| CRYPTO PF | 1.36 | ≥1.80 | After drag removal |
| FOREX PF | 0.29 | ≥1.20 | After carry-factor |
| BOND n | 11 | ≥100 | 2-3 months accumulation |

---

## Wire-Up Rule Compliance

All new modules MUST declare a production caller:
- `calculate_smart_score`
- `passes_active_gate`
- `passes_smart_gate`
- `score_pick`
- `production_scanner`

No orphan modules permitted per `HEDGE_LIBS_LEVERAGE_AUDIT_2026_04_22.md`.

---

## Placeholder Stats Detection (Critical from PLAN_BLOCKER2)

**The "100/100/100" + "85/85/85.7" + "80/80/80" pattern is mathematically impossible** across unrelated symbols. Three fixed triples across a dozen symbols means the pipeline is writing fixed seed values, not computed statistics.

### Detection Assertion
```python
# Reject batch if score == n and abs(n - fwd_wr) < 1 across >=3 unrelated symbols
# This catches clone_hl_copy-* and similar placeholder patterns
if score == n and abs(n - fwd_wr) < 1:
    raise PlaceholderStatsError(f"Impossible stats: score={score}, n={n}, fwd_wr={fwd_wr}")
```

### Required Actions
1. Trace where `clone_hl_copy-*` rows get their fields populated
2. Add assertion at ingestion in `dashboard_generator.py`
3. Re-apply same check at execution time per `feedback_gate_at_execution_not_generation.md`
4. Require `trust_tier != ""` and `trust_score is not null` for HC-gated execution

---

## Related Documentation

- `reports/daily_ideas_edge_per_class_20260513T010800Z.md` — Source edge hypotheses
- `reports/daily_ideas_synthesis_2026-05-15.md` — Prioritized action list
- `docs/PERFORMANCE_CHARTER.md` — Tier definitions
- `docs/MUTATION_THREE_AXIS_PROTOCOL.md` — Strategy changes protocol
- `CLAUDE.md` — Strategy investigation before kill rules

---

## Data Sources Reviewed

| File | Contribution |
|------|--------------|
| `reports/daily_ideas_edge_per_class_20260513T010800Z.md` | 16 edge hypotheses ranked by leverage |
| `reports/daily_ideas_synthesis_2026-05-15.md` | Top 10 prioritized actions |
| `DAILY_IDEAS.MD` | Alt-data ideas, hedge-fund rescue brief |
| `docs/PLAN_REVIEW_STRUGGLING_ASSET_CLASSES_2026-04-14.md` | Reviewer feedback on infrastructure fixes |
| `PLAN_FIX_LOWPICKSCOUNT.MD` | 6-phase triage and recovery plan |
| `PLAN_COMPARISON_RESPONSE.md` | Go/No-Go gates and client standards |
| `reports/PLAN_BLOCKER2_PLUS_BENCHMARK_2026_04_22.md` | Placeholder stats detection, benchmark findings |
| `reports/daily_ideas_raw_sources_review_2026-05-15.md` | Cross-file convergence analysis |

---

## Quick Start Checklist

- [ ] Dispatch `ab_analysis.yml` for `multi_asset_cot` verification
- [ ] Procure `CFTC_API_KEY` for Hyperliquid carry backtest
- [ ] Procure `GLASSNODE_API_KEY` for on-chain signal validation
- [ ] Add `CRYPTO_HOUR_FILTER=1` environment flag
- [ ] Patch `HIGH_CONVICTION` gate to use `trust_score`
- [ ] Enable `FOREX_HARD_DISABLE` by default