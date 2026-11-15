# Failure Taxonomy — Classification Method and Findings

**Canonical row-level data: `00_inventory.csv`** (30 rows, 9 columns, every `file_path` verified to exist with `path_verified=YES`). This file explains the classification scheme and the repo-wide patterns; it deliberately does **not** duplicate the table, so the two artifacts cannot drift apart.

## 1. The ten failure modes

| # | Failure mode | What it looks like | Permitted next move |
|---|---|---|---|
| 1 | Overfitting / data snooping | too many parameter trials, too few trades | new hypothesis, not a new parameter set |
| 2 | Look-ahead bias | future data leaked into a feature | fix the code, re-test (a bug, not a market fact) |
| 3 | Survivorship / universe bias | dead tickers removed, universe chosen after the fact | rebuild the universe point-in-time |
| 4 | Unrealistic cost model | no spread / slippage / funding / tax | re-cost before re-signalling |
| 5 | Weak signal-to-noise | edge too small vs volatility | lower turnover or different instrument |
| 6 | Regime dependence | works only in one market state | pre-register a regime trigger, stand aside otherwise |
| 7 | Implementation gap | backtest logic ≠ live execution | reconcile fills, then re-test |
| 8 | Insufficient sample | statistically inconclusive | extend history or lower frequency |
| 9 | Wrong objective optimised | raw return instead of risk-adjusted | re-specify the objective, restart |
| 10 | Risk-management failure | no stop discipline, over-leverage | fix risk before signal |

## 2. Verdicts (counts from `00_inventory.csv`)

- **ACTIONABLE: 0 / 30** — nothing passes all ten proof steps.
- **DEAD: 18 / 30** — fails a structural gate (shuffle control, walk-forward, temporal discipline, or multiple testing). Archived; must not be re-run with new parameters.
- **NEAR-MISS: 12 / 30** — passes structure, fails only significance/Monte-Carlo due to sample size or cost margin. May be re-tested by extending history or lengthening the paper test only.

## 3. Repo-wide patterns (the actual diagnosis)

1. **Look-ahead leaks in feature pipelines** (F2, F26; historically F9, F15) — the single most common code defect. Detectable only with a shuffle control, which the repo did not have until `proof/harness.py` was added.
2. **Walk-forward parameter drift** (F4, F7, F16, F21) — parameters optimised in-sample; OOS collapses. Fixed-parameter pre-registration removes this failure mode entirely.
3. **Friction erodes real edges** (F5, F8, F13, F20, F25) — the edge exists gross and dies net. At retail costs each extra round-trip per year is a tax, so short-horizon strategies need ~10× the per-trade edge.
4. **Multiple testing is unmeasured** — ~1,307 backtest-bearing files means nobody recorded the trial count. Every uncorrected Sharpe in the repo is therefore meaningless until the count is fixed. This is why the deflated-Sharpe gate rejects everything, correctly.
5. **Two promotion gates ship disabled** (F22) — `MONEY_READY_FDR_GATE=0`, `MONEY_READY_SINGLE_SOURCE_GATE=0`. Enforced check: `python proof/gate_audit.py --repo-root .` (currently exits 1).
6. **Prediction-market copy-trading fails structurally** (F10) — zero-sum, adverse selection, maker-taker fees, latency, size mismatch. Not a parameter problem; only maker/liquidity provision is testable.

## 4. What counts as new evidence

A row moves from DEAD only if the *code defect* behind it is fixed and the strategy is re-entered under a new `run_id` with a frozen config — never by changing a threshold until it passes. A NEAR-MISS moves only with more data or a longer forward test. No row has moved yet.
