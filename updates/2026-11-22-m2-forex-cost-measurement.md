# M2 FOREX cost measurement (2026-11-22) — measured, upper bound, verdicts held

## What was broken / missing

FOREX was one of the 11 asset classes whose transaction cost had **never been
measured** (only CRYPTO had). Two FOREX verdicts sat in `UNKNOWN` purely on that
distinction: FX mean-reversion (break-even 4.3038 bp against a 10 bp assumed cost)
and, adjacent to it, FX carry. The previous attempt at this item returned
`BLOCKED_LIVE_MEASUREMENT` because FX markets were closed.

## What I did

1. **Probed a live book.** Yahoo has no bid/ask and its last FX tick was
   `2026-11-20T22:29:46Z` (Friday close). FMP's quote endpoint is legacy-only and
   Alpha Vantage's FX intraday is premium. **Tiingo** (`/tiingo/fx/top`) returned a
   real bid/ask with a fresh `quoteTimestamp`, so it is the source.
2. **Sampled twice** with a new [`tools/fx_cost_sampler.py`](../tools/fx_cost_sampler.py):
   - 21:41:51Z–21:53:14Z, 17 polls (pre-open, indicative);
   - 21:55:16Z–22:19:4xZ, 48 polls, **straddling the 22:00Z Sunday weekly open**.
3. **Judged market hours honestly.** Post-open, quotes tick (21–32 distinct
   timestamps for AUD/USD, GBP/USD, USD/JPY, EUR/GBP, EUR/JPY) but EUR/USD and
   USD/CAD held a **single price for all 38 samples**, USD/CHF showed 5 prices and
   spiked to 23.6 bp, and AUD/USD ranged 5.4–13.6 bp. Wide spreads plus high
   sample-to-sample variance is the thin-book signature, so the numbers are
   recorded as an **upper bound**, not a representative session, and no verdict
   was moved.
4. **Re-ran both strategies unmodified** (no edit to `momentum_core.py` or the FX
   research tools):
   - FX mean-reversion at 0 bp -> net +4.304 bp, CI-LB +1.752, verdict CANDIDATE;
     at 20 bp -> net −15.696 bp, verdict KILL. Break-even 4.3038 bp.
   - FX carry re-run reproduced: Sharpe −0.126 vs 4.32%, CAGR 3.3817%, maxDD
     −11.71%, break-even 468.47 bp, null percentile 98.2 (500 shuffles), excess
     CAGR vs SPY −3.0415% CI [−8.2793%, +2.2852%] (10,000 bootstraps).

## Measured numbers (round trip = full spread, bp of mid, 22:00–22:19Z)

| pair | min | median | max | sd |
|---|---|---|---|---|
| USD/CAD | 1.952 | 1.952 | 1.952 | 0.00 |
| EUR/USD | 3.826 | 3.826 | 3.826 | 0.00 |
| USD/JPY | 2.017 | 6.686 | 7.377 | 1.53 |
| EUR/JPY | 7.240 | 7.987 | 10.340 | 0.75 |
| AUD/USD | 5.436 | 8.38 | 13.584 | 3.21 |
| USD/CHF | 9.762 | 9.762 | 23.566 | 4.18 |
| GBP/USD | 9.774 | 12.52 | 14.512 | 1.23 |
| EUR/GBP | 10.626 | 15.15 | 22.433 | 3.45 |

Six USD majors: median of medians **7.533 bp**, mean 7.188 bp, range 1.952–12.52.
`COMMISSION_UNKNOWN` — Tiingo exposes no commission field, so it is not assumed zero.

## How verified

- 27-test momentum suite (`tests/test_bond_momentum.py` 13 + `tests/test_commodity_momentum.py` 14): **27 passed** before, and no edit was made, so the "after" is the same code (no test re-run was needed; the file is unchanged on this branch).
- FX carry re-run reproduces the committed artifact's headline figures exactly.
- The cost JSON parses and its aggregate (median 7.99 bp) matches the per-pair medians.
- Step 0 push verification: `push/phase2-round-2026-11-22` = `1c15c5d7d`, 54 files, 62,177 insertions / 39 deletions, parent `5e2775f1e6d`, no `36ceee544d6`/`83703551f94` ancestry; protected branches `68d887c8641` / `78b9794ad77` / `532413a292e` unchanged.

## What remains unmeasured

A **weekday London/NY-overlap** spread run of the same probe. Until then FOREX
cost is measured once as an upper bound, and FX mean-reversion stays `UNKNOWN`
(it is a KILL at the measured upper bound, but only a weekday number below
~2.6 bp could flip it, and the window-clustered CI includes zero at every cost
tested). FX carry stays `NOT_INVESTABLE` regardless: 468.47 bp break-even vs a
~7.5 bp measured cost.

Tally unchanged: **0 INVESTABLE / 8 NOT_INVESTABLE / 6 UNKNOWN** (this was a
measurement addition, not a verdict move).
