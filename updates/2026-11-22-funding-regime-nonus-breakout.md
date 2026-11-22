# Funding-sign clustering, non-US breakout test, and three CI fixes

**Date:** 2026-11-22 · **Agent:** buffy · **Scope:** three measurement tools, one repaired tool,
three of our own tests that were red on `main`, two policy/registry additions.

## What was broken

1. **`CI Tests` was red on three of my open PRs (#1060, #1061, #1063)** — not infrastructure,
   three of our own tests. Full detail from `gh run view 45014421003 --log-failed`:
   - `tests/test_commodity_tsmom_check.py::test_boot_lb_brackets_the_mean_and_needs_history`
     → `assert 0.010000000000000005 <= 0.01`. Bootstrapping a constant series sums `0.01` in
     binary floating point and lands one ULP above the literal. The test asserted exact
     comparison on a float it had just built by summation.
   - `tests/test_per_class_edge_harness.py::test_monthly_trades_gives_one_bucket_per_month`
     → `ValueError: Invalid frequency: ME`. `monthly_trades()` resampled with `"ME"`, an alias
     that only exists in pandas ≥ 2.2. Passed locally (2.2.3), failed on CI (older pandas).
   - `tests/test_profit_program_policies_2026_11_20.py::test_policy_covers_every_live_entry`
     → `unruled live entries: ['H-215', 'H-219']`. The per-class sweep added two PENNY_STOCK
     hypotheses to the registry without adding the rulings the policy file requires. The test
     fired correctly: a new live entry is supposed to force a decision.
2. **Nothing measured two open questions from Mercury3**, both of which he flagged as
   decision-changing: whether negative funding days cluster, and whether the daily-breakout
   edge exists pre-2010 outside the US.

## What changed

| File | Change |
|---|---|
| `tests/test_commodity_tsmom_check.py` | tolerance `1e-12` on the degenerate-series bracket, with a comment saying why |
| `tools/per_class_edge_harness.py` | `monthly_trades()` now groups on `index.to_period("M")` instead of `resample("ME")` — version-stable, same buckets |
| `reports/policy_asset_class_exclusions_2026-11-20.json` | H-215, H-219 ruled `RESEARCH_ONLY` under the existing class ruling, plus an `addenda` entry recording that no new evidence exists for either |
| `tools/funding_carry_sign_autocorr.py` | **new.** Sign autocorrelation, streak lengths, conditional carry, drawdown attribution, holding-period drag table, and the priced "exit on negative funding" overlay |
| `tools/nonus_breakout_test.py` | **new.** Frozen breakout rule on 5 indices with next-open fills, pre/post-2010 split |
| `tests/test_funding_sign_autocorr.py` | **new.** 5 offline tests on the pure helpers |
| `reports/2026-11-22-funding-regime-and-nonus-breakout.md` | the write-up |
| `reports/funding_carry/funding_sign_autocorr.json`, `reports/nonus_breakout_2026-11-22.json` | evidence |

## Findings that matter

- **Negative funding clusters:** P(neg\|neg)=0.666 vs P(neg\|pos)=0.123, sign ACF lag-1 +0.543
  decaying to +0.237 at lag 10, longest negative streak 27 days, mean carry *after* a negative
  day is −2.31 bp. 100% of the carry stream's −10.5% drawdown is earned on negative-funding
  days; positive days contribute exactly 0.0 bp of drawdown.
- **The "step aside when funding turns negative" overlay is not tradeable:** 193 switches,
  1,738 bp avoided against 15,440 bp of exit/re-entry cost — net −13,702 bp. The sign is a
  sizing input, not a timing signal.
- **Holding-period drag confirms Mercury3's correction:** at 40 bp round trip the cliff is
  between 30 days (CI-LB −0.366) and 60 days (CI-LB +0.300). The flat 1.0 bp/day model I
  registered had no mechanism; the replacement model assumes no rebalancing, which also has
  none. The unmeasured number that decides it is venue rebalancing frequency.
- **The non-US breakout test reverses the ZIRP inference:** all four non-US markets are
  positive pre-2010 (DAX +303, TSX +198, N225 +183, FTSE +78 bp at look 20) and three of four
  collapse after (DAX +20, TSX +37, FTSE −75). The US is the only market that improves. The
  edge is a **decayed family**, not a ZIRP artefact. Median trade is negative in every cell
  (WR 37–50%), so the — mean is right-tail; 40 cells with best raw t=2.65 means nothing
  survives multiplicity.

## How it was verified

```
python3 -m pytest tests/test_commodity_tsmom_check.py tests/test_per_class_edge_harness.py \
  tests/test_profit_program_policies_2026_11_20.py -q          -> 24 passed
python3 -m pytest tests/test_funding_sign_autocorr.py -q        -> 5 passed
python3 tools/funding_carry_sign_autocorr.py ...                -> reconstructs 1.9252 bp/day (prior: 1.9252)
python3 tools/nonus_breakout_test.py ...                        -> 5 markets, pre/post split as above
```

The three previously-red tests were the exact names in CI's short test summary, so the fix is
verified differentially: the assertion text in CI matches the assertion text changed here.
The funding tool self-checks: it prints `reconstruction ok=True` only when its rebuilt mean is
within 1% of the previously registered 1.9252 bp/day, so a cache change cannot silently
invalidate the drag table.

## Not done, deliberately

- H-228's verdict was **not** upgraded. The corrected cost model is registered as a new
  hypothesis. Changing a cost assumption after watching the old one fail is the exact failure
  mode this programme exists to catch, even when the new assumption is better.
- The carry sleeve stays at 0%. Mercury3's written condition triggers on a *measured* drag,
  and nobody has measured venue rebalancing cost.
- No forward observations exist for anything here.

*Not investment advice.*
