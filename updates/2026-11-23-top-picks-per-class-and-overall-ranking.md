# Per-class top picks, overall ranking, fees, ML audit, gainer predictability

**Date:** 2026-11-23 · **Author:** buffy (freebuff) · **Type:** analysis (no code changed)

## What this adds

A single document that answers four questions the estate had answered only in fragments:
per-class top picks, the overall ranking of what is worth funding, the fee/minimum question for
mutual funds, and whether top gainers are predictable at daily/weekly/monthly horizons.

Document: `reports/top_picks_per_class_and_overall_2026-11-23.md`.

## What was changed

Nothing executable. No strategy, no threshold, no universe, no trial count. No backtest was run for
this document — every figure is read from an artifact that already existed and is cited inline. The
new monthly-gainer power figure (§7) is a closed-form binomial sample-size calculation, not a test.

## Findings

- **0 of 10 ranked classes are investable; 4 classes untested (MEMECOIN, OPTIONS,
  PREDICTION_MARKET, PRIVATE_CREDIT) and left UNKNOWN rather than declared dead.**
- Overall order: cash 4.32% → H-201 equity (XLV/KO/MSFT) → vol-targeted 60/40 as risk control →
  R4b clock (refutation only) → BTC carry at 0%.
- **Mutual funds rank 5th and are dominated, not merely worse**: best cell 9.02% CAGR against
  13.97% for buy-and-hold of its own universe, daily NAV only, no measurable fee schedule, while the
  ETF share class of the same index costs **6.7122 bp** round trip. The expense ratio was never the
  binding problem; the benchmark excess is.
- ML: four systems, none with OOS edge (v1.2 Sharpe −2.799; gainer ML AUC 0.537; v4 samples of
  5–11 trades). Root cause is the validation-production gap, not the model families.
- Gainer predictability: **daily null (AUC 0.537), weekly null (1.0× crypto, 1.08× equity holdout
  lift)**, monthly not run — 24 months of data against a 48-month requirement for a 2× lift.

## How it was verified

- Every number traced to a committed artifact: `reports/2026-11-22-per-class-edge-results.md`,
  `reports/equity_cost_measurement/{class,equity}_cost_20261122.json`,
  `reports/weekly_winners_2026-11-15.md`, `crypto_ml_edge/AUDIT.md`, `alpha_engine/mf_screener.py`.
- Arithmetic recomputed by hand where quoted (MF benchmark gap 13.97 − 9.02 = 4.95pp; cost floor
  614/12.0749 = 50.9× on equity total, 30.7× against the assumed 10 bp; monthly power n ≈ 48).
- Ranked list cross-checked against the independent peer list
  `docs/edge_research/26_FINAL_RANKED_LIST_2026-11-23.md`: it also returns **0 eligible**, and the
  same three-vehicle cost ordering (ETF 6.7122 < index proxy 8.0325 < direct equity 12.0749). Two
  independent reviews agreeing on "empty" is the useful signal.
- No tests run because no code changed; the three suites covering the power work stay green
  (33 passed) from the previous change.

## Limits

No fill prices exist; equity cost is disputed and flagged; PIT is survivorship-flagged; crypto cost
is assumed 20 bp; the four untested classes have no verdict. Nothing here is advice or a purchase.
