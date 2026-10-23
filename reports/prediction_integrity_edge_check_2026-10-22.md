# Prediction-integrity edge check, 2026-10-22

## Conclusion

**No independently verified winning asset class has been established.**
No gates, allocations, blacklists, or real trading instructions were changed.
This investigation evaluated existing recorded outcomes; it did not optimize
new thresholds or run a new strategy backtest.

## Sources and method

- Live `/audit/data/money_ready_verdict.json`, generated
  `2026-10-22T20:38:45.925100+00:00`.
- Live `/audit/data/hyro_pick_performance.json`, generated
  `2026-10-22T20:33:17.747184+00:00`.
- Live `/audit/data/hyrotrader_journal.json`.
- Production MySQL `at_signal_outcomes` and `at_raw_picks`, using canonical
  credentials and a session explicitly configured `TRANSACTION READ ONLY`.
- Current GitHub-main `alpha_engine/data/closed_picks.json`, 510 rows.
- Actual strategy, adapter, scanner and Hyro validation source.

The existing intrabar sidecars restrict results to TP_HIT/SL_HIT. They exclude
unresolved/expired observations and are not, by themselves, complete
cost-inclusive investable-portfolio results. Counts below are observations,
not established independent trades.

## Whole-class check

| Class | Decisive n | WR | PF |
|---|---:|---:|---:|
| CRYPTO | 3563 | 35.64% | 0.8914 |
| FOREX | 568 | 31.69% | 0.6465 |
| EQUITY | 233 | 56.65% | 0.8642 |
| COMMODITY | 229 | 40.17% | 1.0256 |
| FUTURES | 48 | 41.67% | 1.061 |
| ETF | 30 | 0% | 0 |
| BOND | 21 | 9.52% | 0.5281 |

These are the verdict's `classes.<class>.intrabar_truth` values, not stale
headline ledger aggregates. A positive gross PF barely above one is not
high-profit/low-risk evidence.

## AAPL reversal: apparent standout fails live-signal provenance

The decisive AAPL reversal subset has n=113, wins=107, PF=49.300.
Across all its outcome statuses there are 114 observations but only 12 distinct
entry prices. Monthly observation counts are May 5, June 25, July 29, August 24,
September 17 and October 14. June alone has only two distinct entry prices.
Distinct entry prices are a diagnostic, not a valid replacement for trade IDs
and an overlap-aware portfolio simulation.

Observed source defect:
`EquityTwoDayRsiReversalStrategy.generate_signals()` loops through all bars
from index 200 onward. The live adapter forwarded all returned history.
`_signal_to_dict()` dropped `timestamp` and `bar_index`, and set `timeframe=1h`.
This independently reproduces a route from historical setup to misleading
current prediction. It does not establish that every repeated-price row has
this cause; historical rows require separate reconstruction.

Prepared repair: require the signal timestamp to match the latest input bar,
retain its timestamp and daily metadata, and leave the research generator's
historical output unchanged. Six regression tests failed before the repair.

## Other adequate-size existing strategy cohorts

Screen: decisive TP_HIT/SL_HIT records grouped by asset class and strategy,
n>=50, ranked by gross PF. This is exploratory selection, not held-out proof.

| Candidate | n | Gross PF | Why not established |
|---|---:|---:|---|
| FOREX / regime_accumulation | 50 | 2.649 | Only 14 distinct entry prices; losing May, July and August cohorts; no rows after September 25 |
| COMMODITY / futures_momentum | 62 | 1.533 | May 28-June 12 only; May 0/5 wins; no recent forward sample |
| CRYPTO / regime_mild_bear | 148 | 1.270 | Below target before costs; September n=54, PF=0.524 |
| CRYPTO / luxalgo_confluence | 1084 | 1.088 | Below target before costs |

The conspicuous AAPL result is addressed above. No other n>=50 cohort in this
screen supplied a clean, current, multi-window Tier-2 candidate.

The separately circulated claim of a strong equity-short sleeve is **not
corroborated by the entry-anchored cohort examined here**: EQUITY LONG has
n=218, wins=126, PF=0.855; EQUITY SHORT has n=15, wins=6, PF=0.973.
These are different cohorts from legacy raw-ledger analyses; their numbers
cannot be substituted for one another. A 90-day equity-short thesis remains
a hypothesis until its original cohort is reconstructed and replayed.

## Hyro: small promising cohorts, not proof of an asset class

Actual-fill journal: `trades=[]`, `daily_summary=[]`.
Reported performance: 194 signals, 104 wins, 70 losses, five expired,
15 pending. Many records have `trigger=closed_pick:*`; these are imported
Alpha outcomes, not independent Hyro execution.

The two attractive recent groups are:

1. Empty strategy name: n=39, 33 wins, six losses, PF=11.003.
   Recorded dates October 14-22, 14 symbols. All 39 source records also have
   empty strategy names and no `source` or `source_system`. Their IDs begin
   `::<symbol>::<date>`. Confluence lists mention multiple other algorithms,
   but that is not enough to reconstruct the missing generating strategy.
2. `regime_mild_bear`: n=12, all wins, only DOT and ETH, October 14-18.
   No-loss PF is undefined; the current display's 999 is a sentinel, not a
   measured ratio.

### Unit-corrected cost sensitivity

Alpha's forward validator computes `pnl_pct=(exit-entry)/entry` for longs,
with the reversed sign for shorts. Hyro candle replay multiplies that ratio
by 100. The ingestion path previously did not normalize these units.
A source example: BAT entry 0.18619, exit 0.1842814416,
stored pnl_pct=-0.010251: this is about -1.0251%, not -0.010251%.

On the published closed-record cohorts, converting those fractional values
to percentage points and subtracting a flat 0.30 percentage-point
round-trip cost per trade gives:

| Group | Sum of trade returns before cost | Sum after cost | Net PF |
|---|---:|---:|---:|
| Anonymous n=39 | +58.518 pp | +46.818 pp | 7.120 |
| regime_mild_bear n=12 | +61.324 pp | +57.724 pp | Undefined: no losses |
| luxalgo_confluence n=50 | -343.240 pp | -358.240 pp | 0.161 |

These sums are **not portfolio return** and do not resolve concurrent exposure,
funding, per-symbol liquidity, adverse selection, fill availability, or the
reliability of imported outcomes. The positive groups survive this simple cost
stress; they must not be rejected based on the erroneous unnormalized units.
Neither passes attribution, independence, sample-size and forward-execution
requirements. Historical outcome labels were not retrospectively repaired.

Seven additional failing tests reproduced Hyro's mixed units, optimistic
same-candle TP/SL ordering, pre-entry/unclosed-candle use, premature expiry
and beyond-horizon expiry valuation. The local patch repairs those replay
semantics and known Alpha ingestion units. It does not make imported
closed-record outcomes equivalent to an independent first-touch replay.

## Acceptance before promotion

- Reconstruct the emitting algorithm and freeze its rule/universe; never infer
  a strategy name from whichever co-signal looks most profitable.
- Record first-observed timestamp and executable price, stable signal identity,
  and actual bar anchoring; keep historical/training events out of forward counts.
- At least 100 clean independent resolved trades and adequate observations in
  three calendar months; show unresolved and expired observations too.
- Cost-inclusive, exposure-constrained portfolio: PF>1.5, acceptable uncertainty,
  maximum drawdown below 20%, no dominant-symbol artifact; stress doubled costs.
- Chronological held-out validation and at least four weeks of new forward
  paper evidence before considering deployment for real-money sizing.
- Compare portfolio returns/drawdowns with same-window buy-and-hold benchmarks.
  Trade-return sums cannot establish that these picks beat mutual funds.

No newly tuned backtest was run; any new experiment must follow the existing
pre-registration policy before testing.

## Verification and deployment

Focused suite: 89 passed. Syntax compilation and scoped whitespace checks
passed. See the [fix update](../updates/2026-10-22-prediction-integrity-edge-verification.md)
for the exact command and production callers.

Changes are locally prepared; no claim is made that the live sites already
use them. No scanner, resolver, audit generator, DB mutation, or trade was run.

*Not financial advice. Research/educational only. Past performance does not guarantee future results.*
