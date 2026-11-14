# Proof-of-Profitability Protocol (v1)

Goal: find and **prove** a profitable approach, not cherry-pick one. Every claim below is falsifiable and re-runnable.

## The bar (a strategy must clear ALL gates)

1. **Data purity** — trades come from a price-resolved, intrabar-truth-verified ledger. Exclude: frozen/unquoted rows (`current_price==entry`), the flat-3% placeholder cohort, the forward-seed frozen batch, zero-entry rows, and single-source artifacts (`single_source_pct ≥ 40%`).
2. **Sample size** — `n ≥ 100` for a per-strategy claim (n ≥ 30 only with PF CI strongly away from 1.0).
3. **Profit factor** — `PF > 1.5`, with a **paired-bootstrap 95% CI lower bound > 1.0** (`alpha_engine/benchmark_closed_ledger.py`).
4. **Expectancy significance** — `mean(trade PnL) > 0` with `z = mean/std·√n` and **Bonferroni/Holm correction across the FULL strategy universe (N = 683)**, α = 0.05/683 ≈ 7.3e-5.
5. **Win-rate plausibility** — WR must lie in a credible band. A "long" strategy with WR > 80% or PF > 5 is treated as a data artifact (frozen price / placeholder PnL) until proven otherwise, not as edge.
6. **Out-of-sample** — walk-forward OOS windows profitable ≥ 67% (`walkforward_validator.py`); no look-ahead (intrabar-replay clean).
7. **Autocorrelation** — `autocorr_flag == OK`; deflated Sharpe with `n_trials = 683` (not 80); `DSR > 0.95`.
8. **Costs** — net of slippage + fees, not gross.
9. **Not single-source** — the edge must persist across >1 source/regime, not one emitter.

## Iteration loop

```
fix data (purity) → re-evaluate → rank candidates by honest PF·CI → validate OOS → keep/kill
```

Each iteration is a dated, committed artifact in `research/ITERATION-NNN.md` with the exact commands + numbers. No number is claimed without the tool that produced it.

## Honest starting state (from the 2026-11-14 audit)

0/9 asset classes money-ready; policy-clean aggregate PF 0.94; anti-overfit 69/80 OVERFIT_LIKELY. The current "profitable" surfaces are frozen-price/fabricated artifacts (87–97% WR, PF 10–56 on crypto) and are **excluded by gate 1**, not evidence of edge.
