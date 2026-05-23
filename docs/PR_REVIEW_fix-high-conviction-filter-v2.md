# PR Review: fix/high-conviction-filter-v2

**Branch:** `fix/high-conviction-filter-v2`  
**Base:** `main`  
**Commits:** 12  
**Date:** 2026-04-09

---

## Executive Summary

**Recommendation: DO NOT MERGE** until the "zero HC picks" regression is fixed.

While the code changes improve data extraction and add proper validation gates, they have inadvertently blocked all picks from reaching HC tier. The branch needs additional work before merging.

---

## Changes Summary

### Core Logic Fixes (4 commits)

| Commit | Change |
|--------|--------|
| `95ba34d293` | CSV export: extract forward_wr/forward_trades from extra_json |
| `1e17cd6392` | HC filter fallback to strategy_performance.json for forward_wr |
| `1f4fb5d98b` | Add forward_trades validation gate (min_n >= 5) |
| `f42f013239` | Frontend/backend alignment, PROBATION blacklist, HF tier support |

### Infrastructure (3 commits)

| Commit | Change |
|--------|--------|
| `1bca0c52b9` | Redis bus HC fleet coordination |
| `91ae7758b1` | HEARTBEAT.md monitoring setup |
| `9ed5a0a26b` | HC stamped-tier dashboard path alignment |

### Documentation (3 commits)

| Commit | Change |
|--------|--------|
| `a6996cbbd3` | HC_FILTER_FEEDBACK_2026-04-09.md |
| `db4112fef3` | CODEBUFF_HC_FILTER_ROOT_CAUSE_ANALYSIS.md |
| `ca5f74c4ad` | HC filter v3 Gate 9 correlation + ordered filter |

---

## Code Quality Assessment

### Strengths
1. **Proper JSON parsing** - Extra_json extraction now handles nested paths
2. **Strategy performance fallback** - HC filter can read from closed picks data
3. **Validation gates** - Overconfidence and insufficient trades now blocked
4. **Python syntax** - All key files compile without errors

### Issues Found

#### 1. CRITICAL: Zero HC Picks Regression
- **Before:** HC filter returned coin-toss quality picks (27-52% WR)
- **After:** HC filter returns **0 picks** (100% rejection rate)
- **Root cause:** Validation gate `min_n=5` blocks all active picks
- **Impact:** No conviction picks displayed on audit dashboard

#### 2. Active Picks Data Gap
- Active picks lack `trust_tier` field - cannot filter by PROVEN/SANDBOX
- Most active picks are copy traders with positive WR but < 5 trades
- ML-enhanced strategies with 80%+ WR not being classified properly

#### 3. Fallback Logic Issue
- `_forward_wr_pct` fallback to `strategy_performance.json` may not be triggered
- Need verification that cache is being populated correctly

---

## Files Modified

```
alpha_engine/conviction_stack.py    # Core HC filter logic
audit_dashboard/index.html          # CSV export functions
docs/HC_FILTER_FEEDBACK_*.md        # Feedback documents
HEARTBEAT.md                        # Monitoring setup
tools/dashboard_hc_rules.py         # New HC testing tools
tests/test_hc_filter.js             # New HC tests
```

---

## Testing Status

| Test | Status |
|------|--------|
| Python syntax | PASS |
| Import validation | PASS |
| HC filter logic | FAIL (0 picks) |
| CSV export | Not verified |

---

## Required Fixes Before Merge

1. **Fix min_n threshold** - Lower to 3 for proven strategies (WR > 60%)
2. **Add copy trader bypass** - Allow positive forward_wr without 5 trade minimum
3. **Verify strategy_performance fallback** - Add logging to confirm it's working
4. **Add trust_tier to active picks** - Enable PROVEN/SANDBOX filtering

---

## Risk Assessment

| Risk | Severity | Notes |
|------|----------|-------|
| Zero HC picks | CRITICAL | Dashboard shows no conviction picks |
| Over-strict validation | HIGH | Rejects strategies with proven edge |
| Data flow gaps | MEDIUM | trust_tier missing in active_picks.json |

---

## Conclusion

The branch addresses real issues (data extraction, validation gates) but introduces a critical regression. The HC filter must be able to identify and display high-conviction picks - currently it displays none.

**Action Required:** Fix the validation gate logic to allow proven strategies through while maintaining quality standards. Re-test before merge.

---

*Reviewer: Claude (Codebuff)*  
*Date: 2026-04-09*