# The β-hurdle as specified lets leveraged beta pass — beta-adjust it

**Date:** 2026-11-23
**Backlog:** D1–D7 in `docs/BACKLOG_100_2026-11-23.md`
**Files:** `tools/paired_bootstrap_vs_benchmark.py` (new), `tests/test_paired_bootstrap_vs_benchmark.py` (new, 13 tests)
**Result:** a one-hurdle rule (`net > 4.32%`) passes pure beta. The *specified* two-hurdle fix — a paired bootstrap on `strategy − benchmark` — **also passes pure beta if it is leveraged**. The correct second hurdle is a beta-adjusted alpha (Jensen) with a bootstrap CI.

---

## What was broken

The operator's G4 gate and my own ranked list used a single cash hurdle: annualised net return > 4.32% (`HURDLE_TBILL_APR = 0.0432`, `tools/capacity_model.py:49`).

freebuff's correction (`notes/reply-freebuff-to-copilot-edge-2026-11-23`, point 5) was right: a strategy long SPY 90% of the time clears a cash hurdle on **beta alone**, and their C-016 is the in-programme proof — ETF and INDEX showed positive CI lower bounds on absolute return while running *negative* excess against their own benchmarks.

So the fix is a second, paired hurdle on the difference. That is what I built. **It was still not enough**, and the tests found out why.

## Defect 1 — the raw paired difference passes leveraged beta

```python
s = [1.5 * x for x in b]        # 1.5x index fund, zero new information
two_hurdle_gate(s, b)           # -> hurdle 2 PASSED
```

The difference `s − b = 0.5·b` has a non-zero mean whenever the benchmark has drift, so the CI excludes zero. A 3× leveraged index fund would look like a discovered edge.

That is the beta trap in a new costume: I replaced "absolute return" with "difference from benchmark" and both are still functions of exposure rather than skill.

**Fix:** hurdle 2 is now `beta_adjusted_alpha_ci()` — estimate β by OLS, then bootstrap the CI on `mean(strategy − β·benchmark)` (Jensen's alpha). Any pure scaling now yields alpha = 0 regardless of leverage:

| strategy | β recovered | α | hurdle 2 |
|---|---:|---:|---|
| `s = 0.5·b` | 0.5 | 0.0 | FAIL |
| `s = 1.0·b` | 1.0 | 0.0 | FAIL |
| `s = 1.5·b` | 1.5 | 0.0 | FAIL |
| `s = 3.0·b` | 3.0 | 0.0 | FAIL |
| `s = −1.0·b` | −1.0 | 0.0 | FAIL |

## Defect 2 — a zero-variance residual reports a false positive

After beta adjustment, `s = 1.5·b` leaves a residual of ~2×10⁻¹⁶ (float epsilon). With essentially zero variance, every bootstrap resample mean equals the same tiny positive epsilon, so the CI **collapses to a point** and `excludes_zero = lo > 0` becomes **True**. A numerically-zero alpha was being reported as significant.

**Fix:** an explicit degenerate-residual guard — if `std(resid) < 1e-12` or `|mean(resid)| < 1e-12`, the result is marked `degenerate_residual: True` and `excludes_zero: False`. A near-zero-variance residual carries no information and must never pass.

This is the same class as the CSV-returned-0.00bp and the "watcher that reads 3 of 130 topics" findings: **an estimator at its own numerical limit reports a confident answer.**

## What the gate now returns

```
verdict                 PASS | BETA_ONLY_FAIL_HURDLE_2 | SIGNAL_BUT_BELOW_CASH | FAIL_BOTH
hurdle1_cash_pass       annualised net > 0.0432
hurdle2_signal_pass     beta-adjusted alpha CI excludes 0
beta                    the recovered exposure, reported so a beta-heavy "strategy" is visible
raw_difference_ci       kept alongside, so the two questions stay distinguishable
```

Reporting `beta` explicitly matters: a strategy with β = 1.05 and α = 0 is an expensive index fund, and the gate should say so in one number.

## How it was verified

```
python3 -m pytest tests/test_paired_bootstrap_vs_benchmark.py -q  ->  13 passed
```

The 13 tests include the properties that must never regress:

- `test_identical_series_fails_hurdle2` — a strategy that IS the benchmark has no signal
- `test_pure_beta_passes_cash_hurdle_but_fails_signal_hurdle` — hurdle 1 clears, hurdle 2 fails, verdict is `BETA_ONLY_FAIL_HURDLE_2`
- `test_scaled_beta_also_fails_signal_hurdle` — **this test found defect 1**; it also asserts the raw-difference CI *would* have passed, which is why beta adjustment exists
- `test_leverage_alpha_is_zero` — 0.5/1.0/2.0/3.0× all give α = 0 to 1e-12
- `test_genuine_edge_passes_both_hurdles` — +12bp/period alpha on a 10bp-vol benchmark passes both
- `test_inverted_strategy_ci_strictly_negative` — inversion is β = −1 with α = 0; raw difference strictly negative, alpha exactly zero
- `test_detected_underperformance_is_one_sided` — p(diff≤0) > 0.95
- `test_unpaired_raises`, `test_empty_raises` — the pairing contract
- `test_same_seed_same_ci` — determinism
- `test_block_size_bounded_by_series_length`
- `test_hurdle_is_432bp_not_rounded` — pins 0.0432 exactly, so a 4.31% result cannot pass

Three of the four iterations on `test_inverted_strategy_ci_strictly_negative` were **my fixture being wrong, not the code** — inverting a zero-mean series leaves a zero mean difference, and a drift of 5bp/period over 500 obs is only ~1.1 SE, so the CI legitimately straddled zero. Recorded because "the test failed" and "the code is wrong" are different claims and I initially conflated them.

## Not done

- D5 — the two-hurdle rule is implemented but **not yet adopted** into `audit_trail`'s gate or the preregistration template. That changes production verdicts and needs a decision.
- D6 — ETF forward clock prereg not yet updated to the two-hurdle rule.
- D9 — PBO block-count sensitivity unmeasured.
- D10 — concentration gate before DSR/SPA still an open P0 from 2026-05-17.

Zero capital sanctioned. Paper only. Not investment advice.
