# GitHub Actions Gate Design for Quant Trading System

You are a quantitative researcher and DevOps engineer with experience in trading system CI/CD.

## Context
A Python-based trading system needs GitHub Actions quality gates that:
- Run on every PR touching `audit_trail/quality_gates.py`, `alpha_engine/`, or `reports/`
- Validate that changes do not introduce lookahead bias in walk-forward validation
- Check that confidence score distributions are not inverted (higher score = lower WR)
- Gate that walk-forward eff-stability passes at least some fraction of test cases

Current test infrastructure:
- `pytest` test suite with ~4950 tests
- Walk-forward harness produces `reports/walk_forward_eff_stability.json`
- Hypothesis registry at `reports/hypothesis_registry.json`

## Task
Design 3 specific GitHub Actions job steps that would catch:
1. Lookahead bias regression (a new code change re-introduces lookahead)
2. Confidence score inversion (ml_score correlation with forward WR goes negative)
3. Walk-forward gate integrity (gate thresholds not silently weakened)

For each step:
- **Step name**
- **Trigger condition** (when to run)
- **Check logic** (what the step tests, in pseudocode)
- **Fail condition** (what triggers step failure)

Be specific and actionable. These should be implementable as real GHA steps.
