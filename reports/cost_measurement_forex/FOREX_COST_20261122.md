# FOREX cost measurement — 2026-11-22

**Status: `MEASURED_UPPER_BOUND`** (not a representative session). Spread only; commission `COMMISSION_UNKNOWN`.

- **Endpoint:** `https://api.tiingo.com/tiingo/fx/top?tickers=<csv>&token=$TIINGO_API_KEY` (live top-of-book, via [`tools/fx_cost_sampler.py`](../../tools/fx_cost_sampler.py))
- **Windows:** 21:41:51Z–21:53:14Z (17 polls, *pre-open*) and 21:55:16Z–22:19:4xZ (48 polls, *straddles the 22:00Z Sunday open*)
- **Raw samples:** [`fx_top_of_book_samples.json`](fx_top_of_book_samples.json), [`fx_top_of_book_samples_window2.json`](fx_top_of_book_samples_window2.json)
- **Structured summary:** [`FOREX_COST_20261122.json`](FOREX_COST_20261122.json)

`full_spread_bp = (ask − bid) / mid × 1e4`. Round-trip = full spread (pay it on entry and exit); half-spread = one-way.

## Post-open spreads (22:00Z–22:19Z, 38 samples/pair), bp of mid

| pair | min | median | max | mean | sd | unique prices | read |
|---|---|---|---|---|---|---|---|
| EUR/USD | 3.826 | 3.826 | 3.826 | 3.826 | 0.00 | 1 | tightest major, but frozen |
| USD/CAD | 1.952 | 1.952 | 1.952 | 1.952 | 0.00 | 1 | tightest, frozen |
| USD/JPY | 2.017 | 6.686 | 7.377 | 5.672 | 1.53 | 21 | ticks |
| EUR/JPY | 7.240 | 7.987 | 10.340 | 8.234 | 0.75 | 12 | cross |
| AUD/USD | 5.436 | 8.38 | 13.584 | 9.769 | 3.21 | 28 | wild swings |
| USD/CHF | 9.762 | 9.762 | 23.566 | 10.897 | 4.18 | 5 | spikes to 23.6bp |
| GBP/USD | 9.774 | 12.52 | 14.512 | 12.423 | 1.23 | 16 | wide |
| EUR/GBP | 10.626 | 15.15 | 22.433 | 16.709 | 3.45 | 31 | widest cross |

All-pairs aggregate (n=304): min 1.952 / median 7.99 / mean 8.52 / max 23.566 bp.
Six USD majors, median of their medians: **7.533 bp** (mean 7.188; range 1.952–12.52).

## Why this is an upper bound, not the answer

1. **It is the Sunday reopen.** The FX week opens 22:00Z Sunday. Pre-open samples (21:41–21:53Z) are indicative only; the post-open book is real but thin.
2. **Frozen books.** EUR/USD and USD/CAD held a single price for all 38 post-open samples; USD/CHF showed only 5 distinct prices. A live weekday book reprices far more often.
3. **Wild variance.** AUD/USD ranged 5.4–13.6 bp and USD/CHF spiked to 23.6 bp within 20 minutes. High sample-to-sample variance is the thin-book signature.
4. **Commission not included** (and not assumed to be zero).

A weekday London/NY-overlap run of the same probe is the missing measurement. Until it exists, FOREX cost is *measured once, as an upper bound*, and the FOREX verdicts stay `UNKNOWN`.
