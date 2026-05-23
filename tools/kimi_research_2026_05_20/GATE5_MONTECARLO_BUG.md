# Gate 5 Monte Carlo Bug — six_gate_validated_strategy.py

**Filed:** 2026-05-21  
**Severity:** HIGH — Gate 5 is a no-op; stress test does not validate path-dependence  
**File:** `tools/kimi_research_2026_05_20/six_gate_validated_strategy.py`  
**Status:** NOT FIXED — reference archive only, do not promote to production

---

## Symptom

Running `six_gate_validated_strategy.py` produces:

```json
"monte_carlo": {
  "mc_sharpe_5th": 2.5161,
  "mc_sharpe_median": 2.5161,
  "mc_sharpe_95th": 2.5161,
  "n_sims": 5000,
  "pass": true
}
```

All three percentiles are **identical** to the observed Sharpe. A genuine stress test would show variance across paths.

---

## Root Cause

The Monte Carlo shuffle is not adding noise to the returns before re-running the strategy.

**Expected behavior:**
```python
for sim in range(n_sims):
    shuffled = np.random.permutation(returns)  # or block-bootstrap
    sim_sharpe = compute_sharpe(shuffled)
    sharpe_distribution.append(sim_sharpe)
```

**Actual behavior (likely):** The shuffle is called but either:
1. The same seeded random state is reused each simulation, or
2. The shuffled returns are passed through the strategy's signal generation (which re-computes signals from scratch using the original data, not the shuffled returns), or
3. `mc_sharpe_5th` / `mc_sharpe_median` / `mc_sharpe_95th` all refer to the same scalar (the observed Sharpe), not percentiles of the distribution

The most likely cause: the stress test computes `run_backtest(shuffled_returns)` but `run_backtest()` ignores the passed-in returns and re-runs signal generation from `self.data` (the original price data), producing the same Sharpe every time.

---

## Why This Matters

Gate 5 is supposed to answer: **"Does the strategy's edge survive adverse path realizations?"**

With zero variance across 5000 paths, the test answers nothing. Any strategy — including pure noise — would pass Gate 5 as implemented. The gate provides false confidence.

Gate 6 (BH-FDR) partially compensates by testing against noise strategies on pure-noise data, but it tests a different question (selection bias correction, not path robustness).

---

## Fix (not yet implemented)

The stress test should:

1. **Separate signal generation from backtest execution** — generate signals once, then stress-test the return series only:
   ```python
   signals = strategy.generate_signals(data)  # fixed
   for sim in range(n_sims):
       shuffled_returns = block_bootstrap(observed_returns, block_size=5)
       sim_sharpe = compute_sharpe_from_returns(shuffled_returns * signals)
       distribution.append(sim_sharpe)
   ```

2. OR **stress-test market data**, not return series:
   ```python
   for sim in range(n_sims):
       stressed_data = apply_regime_shock(data)  # vol spike, correlation spike, etc.
       sim_returns = strategy.run_backtest(stressed_data)
       distribution.append(compute_sharpe(sim_returns))
   ```

3. Verify fix: `mc_sharpe_5th < mc_sharpe_median < mc_sharpe_95th` after fix.

---

## Impact on 6-Gate Results

| Gate | Affected? | Valid? |
|------|-----------|--------|
| 1 — Bootstrap Sharpe | No | Yes (correct block bootstrap) |
| 2 — t-test | No | Yes |
| 3 — Max Drawdown | No | Yes (but 0.24% DD on synthetic data is suspiciously low) |
| 4 — Walk-Forward | No | Yes |
| 5 — Monte Carlo | **YES** | **NO — no-op** |
| 6 — BH-FDR | No | Yes (correct null distribution) |

The strategy genuinely passes 5 of 6 gates on synthetic data. Gate 5 requires the fix above before the result is meaningful.

---

## Before Wiring to Production

- [ ] Fix Gate 5 Monte Carlo (see Fix section above)
- [ ] Re-run on real market data (yfinance or live feed), not synthetic
- [ ] Validate Gate 3 Max Drawdown on real data (0.24% is implausibly low)
- [ ] Wire-up check: grep for callers per CLAUDE.md Wire-Up Rule
