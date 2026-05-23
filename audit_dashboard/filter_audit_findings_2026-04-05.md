# Audit Dashboard Filter & Quality Gate Audit Findings
**Date:** 2026-04-05  
**Status:** Investigation Complete - Recommendations Pending

---

## Executive Summary

The audit reveals several potential issues with the filtering logic between "Active Picks" (quality-gated view) and "Show All Picks" (full candidate pool). The 66-70% removal rate at the backend gate level warrants review.

---

## 1. Quality Gates Breakdown

### Current Data (dashboard_data.json)
| Metric | Value |
|--------|-------|
| Total active before gates | 162 |
| Active after gates | 54 |
| Filtered out | 108 (66.7%) |

### Quality Stats
- `conflict_minority_dropped`: 3
- `degradation_severe_strategies`: 3 (penalty -30 each)
- `degradation_high_strategies`: 2 (penalty -20 each)
- `degradation_lifting_strategies`: 33

### Display Tiers (Score-Based)
- ELITE: 0, PREMIUM: 0, STANDARD: 19, WATCH: 32

---

## 2. Trust Tier Filtering Analysis

### Distribution in active_raw (162 picks)
- WATCH: 138 (85.2%)
- RELIABLE: 13 (8.0%)
- PROVEN: 5 (3.1%)
- UNTRUSTED: 6 (3.7%)

### Distribution in active (54 picks)
- WATCH: 42 (77.8%)
- RELIABLE: 7 (13.0%)
- PROVEN: 2 (3.7%)
- UNTRUSTED: 0 (0%)

### Key Finding: DEVELOPING Tier Missing
- Data contains RELIABLE, but HF Book filter checks for PROVEN + DEVELOPING
- Frontend `getTrustTier()` dynamically recomputes tier from live system data
- **Potential Issue:** Mismatch between static data field and dynamic filtering

---

## 3. Forward Degradation Analysis

### Aggregate Performance
- Trades: 3,604
- Source WR: 39.7% -> Realized WR: 43.3%
- Delta: +3.6pp (IMPROVEMENT, not degradation!)
- **Status: OK**

### Worst 5 Strategies
| Strategy | Source WR | Realized WR | Delta | Severity | Penalty |
|----------|-----------|-------------|-------|----------|---------|
| ema_stack_momentum | 66.7% | 25.0% | -41.7pp | SEVERE | -30 |
| unknown | 71.7% | 42.4% | -29.3pp | SEVERE | -30 |
| crypto_drawdown_convexity_recovery_v1 | 45.2% | 22.2% | -23.0pp | SEVERE | -30 |
| MomentumEMA | 45.5% | 28.6% | -16.9pp | HIGH | -20 |
| extreme_fear | 43.2% | 27.3% | -15.9pp | HIGH | -20 |

### Verified Alpha
- Active picks: 35
- Audited WR: 53.5% -> Realized WR: 44.0%
- Gap: -9.5pp

---

## 4. Conflict & Duplicate Analysis

### Quality Stats Conflicts
- `conflict_minority_dropped`: 3
- `conflict_symbol_count`: 6
- `conflict_active_pick_count`: 17
- `duplicate_symbol_groups`: 10
- `duplicate_symbol_picks`: 22
- `duplicate_symbol_direction_groups`: 8
- `duplicate_symbol_direction_picks`: 16

### Active Picks Reality (51 picks)
- **Duplicate Symbols:**
  - ETHUSDT: 7 times
  - BTCUSDT: 5 times
  - SOLUSDT, BNBUSDT, XRPUSDT, ADAUSDT: multiple

- **Direction Conflicts (LONG + SHORT):**
  - BNBUSDT, BTCUSDT, SUIUSDT, ADAUSDT, DOGEUSDT, ETHUSDT
  - Total: 6 symbols with bidirectional conflicts

---

## 5. Systems Completely Filtered Out

8 source systems were completely removed by quality gates:
- crypto_ml_edge
- kimi_riseoftheclaw
- signal_validation
- goldmine_unified
- goldmine_stocks
- prediction_market_consensus
- smart_money
- non_crypto_consensus

---

## 6. Issues Identified

### Issue 1: High Gate Removal Rate (66.7%)
**Description:** 108 out of 162 picks filtered out by backend quality gates  
**Concern:** May be overly aggressive - potentially filtering valid picks  
**Recommendation:** Review quality gate thresholds for appropriateness

### Issue 2: Trust Tier Mapping Mismatch
**Description:** Data has RELIABLE, but HF Book filter checks PROVEN + DEVELOPING  
**Impact:** Dynamic tier computation may produce different results than expected  
**Recommendation:** Verify that RELIABLE is properly mapped to DEVELOPING tier

### Issue 3: Bidirectional Conflicts
**Description:** 6 symbols have both LONG and SHORT positions simultaneously  
**Question:** Should these be auto-resolved (keep only one direction per symbol)?  
**Recommendation:** Decide on conflict resolution policy

### Issue 4: Unknown Strategy with Severe Degradation
**Description:** "unknown" strategy in forward_degradation has 33 trades, -29.3pp degradation  
**Finding:** Not found in current active picks - may be from historical data  
**Recommendation:** Investigate source of "unknown" strategy labels

### Issue 5: Verified Alpha Gap
**Description:** 9.5pp gap between audited WR (53.5%) and realized WR (44.0%)  
**Concern:** Realized performance significantly underperforms audited  
**Recommendation:** Review verified alpha criteria

---

## 7. Show All Picks Functionality

### Verified Working:
- Trust tier filter bypassed (shows PROVEN + DEVELOPING + WATCH + etc.)
- Blocked systems filter bypassed
- Stale picks filter bypassed
- rapid_fire score filter bypassed

### Always Applied (Sanity Check):
- Entry price filter (entry > 0 && entry <= 1,000,000)

### Issues Fixed Previously:
- renderPicks() now checks _showAllPicks and uses active_raw when enabled
- Quality gate filters wrapped in "if (!_showAll)" conditions

### Pending Sync (index.html to template.html):
- Line 3566: renderSummary trust filter
- Line 3594: renderSummary smartRows trust filter  
- Line 9087: export handler trust filter

---

## 8. Recommended Actions

1. **Review 66.7% gate removal rate** - Determine if this is intentional or too aggressive
2. **Resolve bidirectional conflicts** - Decide whether to keep both directions or auto-resolve
3. **Fix index.html sync** - Apply the 3 remaining _showAllPicks fixes to match template.html
4. **Investigate "unknown" strategy** - Find source and fix labeling
5. **Verify trust tier mapping** - Ensure RELIABLE properly maps to DEVELOPING in HF Book view

---

## 9. Data Sources Analyzed

- `audit_dashboard/data/dashboard_data.json`
- `audit_dashboard/index.html` (frontend filtering logic)
- `audit_dashboard/template.html` (source of truth)

---

*Generated by automated audit analysis*