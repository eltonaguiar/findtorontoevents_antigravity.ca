# PLAN — EQUITY (SPY excess + cluster test)

**Status:** plan only. This is the highest-value missing number in the audit.

## Hypothesis

> Equity picks earn positive **excess** over SPY across the holding window, and that excess is not
> concentrated in a small number of calendar episodes.

## Gap it fills

- Inventory row: `STAT:significance` (3,777 files) and `DATA:market` (3,548 files) are abundant,
  yet no report on main computes SPY-excess for the 690 closed equity picks.
- `state/forward_test/plan.json` records four documented equity kills (`RSI2_SPY`, `DUALMOM_2/3`,
  `SIXTY_FORTY`) — those are backtest results, not ledger measurements.

## Method

1. Compute `excess_pp` vs SPY for all 690 rows (`tools/pick_excess.py` conventions).
2. Cluster on `(entry_day, exit_day)`; report the number of clusters — if 690 rows form e.g. 40
   clusters, the effective sample is 40 and every conclusion changes.
3. Report per-strategy and aggregate: n, mean/median excess, clustered t, bootstrap CI of the mean.
4. Survivorship check: the universe is rebuilt from gainers daily
   (`alpha_engine/data/dynamic_universe.json`); count how many symbols appear only after a large
   move. If that share is high, the sample is selected on the outcome and must be disclosed.

## Data

Picks: `dashboard_data.json`. Benchmark: SPY in `benchmark_prices.json` (469 bars,
2025-01-02 → 2026-11-13).

## Universe / timeframe / parameters

Universe: whatever the ledger contains (EQUITY only). Timeframe: mixed, 1d–7d holds. No
parameters are tuned — this is measurement.

## Cost model

6 bps/side both legs; 2× sensitivity. Slippage for illiquid names is NOT modelled in stage 1 and
must be disclosed (equity picks include penny names where 6 bps is optimistic).

## Benchmark

SPY daily closes, per-pick window.

## Proof items this is designed to pass

G1, G6, G8, plus a survivorship disclosure (G3 requires the configuration count; stage 1 has 0
configurations searched, which is its strength). G2/G4/G5/G7 are stage 2.
