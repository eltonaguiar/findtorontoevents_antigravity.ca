# GitHub Actions Failure Analysis

**Generated:** 2026-05-14 00:36 UTC
**Analysis Period:** Last 100 runs
**Token Source:** GIT_PAT_CLASSIC (authenticated as eltonaguiar)

---

## Critical Findings

### CI Tests: 100% Failure Rate (9/9 in sample)

**Most Recent Failed Test:**
- Run ID: 25841562730
- Branch: main
- Python: 3.11

**Failed Tests:**
1. `test_active_when_crypto_short` - AssertionError
2. `test_evaluates_closed_picks_at_issue` - AssertionError
3. `test_smart_when_passes_smart_gate` - AssertionError ('REJECTED' != 'SMART')
4. `test_default_off_active_gate_no_short_specific_rejection` - AssertionError
5. `test_luxalgo_filters_downsized_to_5` - AssertionError

**Pattern:** Smart gate and crypto short regime gate assertion failures.

---

## Workflow Failure Summary

| Workflow | Total | Success | Failed | Cancelled | Failure Rate |
|----------|-------|---------|--------|-----------|--------------|
| CI Tests | 11 | 0 | 9 | 0 | **100%** |
| audit-dashboard.yml | 1 | 0 | 1 | 0 | **100%** |
| Crypto ML Edge GSD Scanner | 2 | 0 | 1 | 0 | **50%** |
| walkforward-gate | 1 | 0 | 1 | 0 | **100%** |
| Unified Audit Dashboard | 2 | 0 | 0 | 1 | 0% |
| Swarm Pick Review | 1 | 0 | 0 | 1 | 0% |
| Sports Betting | 1 | 0 | 0 | 1 | 0% |

### Intermittent Cancellations

Three workflows show cancellation patterns that may indicate:
- Resource contention (max runners exceeded)
- Timeout issues in long-running jobs
- Concurrency control conflicts

**Affected:**
- Unified Audit Dashboard (1 cancelled)
- Swarm Pick Review (1 cancelled)
- Sports Betting (1 cancelled)

---

## Specific Failure Root Causes

### 1. CI Tests - Smart Gate/Crypto Short Gate Failures

**Test Files:**
- `tests/test_classify_pick_quality_v2.py` - 3 test failures
- `tests/test_crypto_short_regime_gate.py` - 1 failure
- `tests/test_quality_gates_swarm_batch1_2026-05-09.py` - 1 failure

**Sample Failures:**
```
AssertionError: False is not true
test_smart_when_passes_smart_gate: 'REJECTED' != 'SMART'
test_luxalgo_filters_downsized_to_5: assert -8 == 5
```

**Likely Cause:** Recent changes to gating logic may have introduced regressions.

### 2. Audit Dashboard - Workflow File Reference

**Notable:** Workflow `.github/workflows/audit-dashboard.yml` is referenced directly by name, indicating it may have been triggered by workflow file modification.

### 3. Walkforward Gate - Failures Sync with CI Tests

**Timing:** Same branch as CI test failures, suggesting related code changes.

---

## Recommended Fixes

### Immediate (High Priority)

#### Fix 1: CI Test Regression
The tests `test_smart_when_passes_smart_gate` and crypto short regime gate tests are failing with assertion errors.

**Action:**
1. Review recent commits to smart gating logic
2. Verify test expectations match current implementation
3. Fix mismatch in `REJECTED` vs `SMART` classification

#### Fix 2: Add Workflow Timeout to CI Tests
```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 90  # Prevent indefinite hangs
    strategy:
      matrix:
        python-version: ['3.11', '3.12']
```

#### Fix 3: Add Continue-on-Error for Test Matrix
Allow 3.12 to continue even if 3.11 fails:
```yaml
    continue-on-error: ${ matrix.python-version == '3.12' }
``` ---

## Action Items for Agent Swarm

### Agent Tasks

**CI Test Fix Agent:**
- Investigate `test_classify_pick_quality_v2.py` failures
- Check `test_crypto_short_regime_gate.py` default OFF behavior
- Verify `test_quality_gates_swarm_batch1_2026-05-09.py` LuxAlgo filter sizing

**Cancelled Workflow Analysis Agent:**
- Check Unified Audit Dashboard for resource contention
- Verify Swarm Pick Review concurrency settings
- Review Sports Betting workflow timeout settings

**Workflow Resilience Agent:**
- Add timeout to CI Tests workflow (currently missing)
- Add retry for flaky network-dependent tests
- Implement proper test isolation

---

## Files to Review

1. `.github/workflows/ci-tests.yml` - Add timeout
2. `tests/test_classify_pick_quality_v2.py` - Fix assertion failures
3. `tests/test_crypto_short_regime_gate.py` - Check default gate behavior
4. `.github/workflows/unified-audit-dashboard.yml` - Add concurrency controls
5. `.github/workflows/swarm-pick-review.yml` - Review timeout settings

---

*Analysis based on authenticated GitHub API access - 2026-05-14*
