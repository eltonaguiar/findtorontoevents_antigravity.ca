# PLAN — CRYPTO (majors vs alts, excess vs BTC-USD)

**Status:** plan only. No new code written for this plan yet.

## Hypothesis

> Intraday-to-multi-day directional picks in BTC and ETH earn positive **excess** over simply
> holding BTC-USD over the same window; altcoin picks do not.

Registered as a hypothesis to be filed in `reports/hypothesis_registry.json` (rule M-107) before
any backtest runs. This plan does not assert the outcome.

## Gap it fills

- Inventory row: `BT:walkforward` (1,853 files) and `STAT:dsr` (756) exist, but the closed crypto
  ledger has **never been benchmark-adjusted** — `tools/pick_excess.py` exists, the join has not
  been run on CRYPTO.
- The prior in `state/forward_test/plan.json` mixes majors and alts, so a majors-only edge is
  invisible in every report to date.

## Method

1. Recompute the 2,070 closed CRYPTO rows as `excess_pp` vs BTC-USD using
   `tools/pick_excess.py` conventions (last close on/before entry day, same for exit).
2. Cluster on `(entry_day, exit_day)`; exclude collapsed same-day windows (they are 31% of the
   ledger and cannot be benchmarked from daily closes).
3. Split majors (BTC, ETH) from alts; report n, mean/median excess, clustered t, bootstrap CI.
4. Only if the majors CI excludes zero: walk-forward on a fixed universe with
   `alpha_engine/rigorous_backtest_harness.py`.

## Data

- Picks: `audit_dashboard/data/dashboard_data.json` (`picks.recent_closed`).
- Benchmark: `audit_dashboard/data/benchmark_prices.json` (BTC-USD, 683 daily bars from
  2025-01-01).

## Universe / timeframe / parameters

Universe: BTCUSDT, ETHUSDT (majors); everything else = alts. Timeframe: 1h–4h signal, 1d–3d hold.
Parameters: none tuned in stage 1 (it is a measurement, not a search). Stage 2 allows a single
walk-forward sweep over entry threshold only, with the count of configurations recorded for DSR.

## Cost model

6 bps/side on notional, both legs (`DEFAULT_FEE_BPS_PER_SIDE`), plus a 2× sensitivity run.
Funding is excluded in stage 1 and stated as excluded.

## Benchmark

BTC-USD daily closes, same window per pick. For alts, the same BTC benchmark is used deliberately
(an alt must beat holding BTC, not holding itself).

## Proof items this is designed to pass

G1 (chronological, no tuning in stage 1), G6 (clustered t + bootstrap CI), G8 (shuffle control on
the pick dates), G3 (configuration count stated). G2/G4/G5/G7/G9/G10 come in stage 2 only if
stage 1 survives.
