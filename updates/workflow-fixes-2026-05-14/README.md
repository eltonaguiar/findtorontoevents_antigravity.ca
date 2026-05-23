# Workflow Fixes Package - 2026-05-14

## Overview
This directory contains fix patterns and templates for GitHub Actions workflow reliability issues identified in the analysis.

## Files
- **TIMEOUT_FIXES.md** - Guide for adding timeout settings
- **RETRY_LOGIC_TEMPLATE.md** - Retry patterns for API calls
- **API_FALLBACK_PATTERN.md** - Fallback chain implementation
- **README.md** - This file

## Priority Workflows for Fixes

### Critical (Fix First)
1. **CI Tests** - 100% failure rate, needs immediate investigation
2. **Alpha Engine Live** - Large complex workflow with multiple API deps
3. **Autonomous Trading** - No timeout, trading ops

### High Priority
4. **Actions Failure Guardian** - Monitoring workflow without its own timeout
5. **Audit Dashboard** - Intermittent failures and cancellations
6. All workflows with API single-point-of-failure

### Medium Priority
7. **Large workflows needing decomposition** (26 files)
8. Performance optimization for slow-running jobs

## Implementation Approach

1. Test fixes locally with `act` or on a branch
2. Start with timeout fixes (lowest risk)
3. Add retry logic progressively
4. Implement API fallbacks with fallback testing
5. Decompose large workflows incrementally

## Swarm Deployment

To deploy agent swarm for automated fixes:

```bash
# Option A: Using ruflo orchestrator
python .ruflo/orchestrator.py --swarm workflow-resilience

# Option B: Using tools/swarm
python tools/swarm/run_agents.py --config agents/workflow_resilience_agents.json
```
