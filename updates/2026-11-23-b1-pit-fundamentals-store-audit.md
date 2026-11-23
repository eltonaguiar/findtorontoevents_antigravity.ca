# B1 — is there a point-in-time fundamentals store?

**Date:** 2026-11-23
**Question:** does any point-in-time (PIT) fundamentals store exist in this repo?
**Answer:** **No populated store exists. A genuine PIT *source* does, and the repo is
~80% plumbed to it.**

---

## What does not exist

| Checked | Result |
|---|---|
| `data/fundamentals/` (the path `fundamentals_fetcher.py` writes to) | **does not exist** — the fetcher has never been run to disk |
| Any populated fundamentals cache | none (`data/cache/hml_fundamentals` is my own, built today) |
| A production `fundamentals_history_provider` | **none** — implemented only in `tests/test_value_backtest.py:282` for *synthetic* tests |
| Vendor fundamentals store (SimFin / Sharadar / Compustat / WRDS) | not present |
| Fundamentals tables in MySQL | not found in the searches above |

The HML test I ran today worked around this by reading yfinance annual balance sheets
and applying a hard 90-day reporting lag. That is a **conservative assumption standing
in for a filing date**, not real PIT data.

## What does exist — and it is better than expected

**1. A PIT contract already exists.** `alpha_engine/value_backtest.py` defines:

```
fundamentals_history_provider(ticker, as_of_date)
    -> must return the snapshot visible AS OF as_of_date
       (i.e. period_end <= that date)
```

and documents its own discipline in the header: *"period_end ≤ T - 90d (90-day SEC
reporting lag floor)"*. So the programme already knows the right rule; the interface is
in place and nothing implements it.

**2. A free, genuine PIT source exists.** `alpha_engine/fundamentals_fetcher.py` reads
**SEC EDGAR `companyfacts`** as its primary source (yfinance as fallback). I verified
EDGAR directly rather than trusting the adapter's docstring:

```
AAPL, us-gaap StockholdersEquity
  268 facts, 268/268 carry a 'filed' date
  keys per fact: accn, end, filed, form, fp, frame, fy, val
  filed-date coverage: 2009-07-22 .. 2026-11-03
```

`filed` is the **actual SEC filing date**. That is strictly better than my 90-day
assumption: for AAPL FY2026 (`end=2026-09-26`, `filed=2026-11-03`) the true lag was
**38 days**, not 90. Using `filed` makes a backtest genuinely point-in-time instead of
approximately so.

## The two specific gaps in the existing adapter

1. **It has never been run.** The cache path `data/fundamentals/{ticker}/latest.json`
   does not exist on disk, so there is no history to query.
2. **It discards the best field.** The parser reads `item.get("end")` but never reads
   `item.get("filed")`. The one field that makes PIT rigorous is parsed past.

## A trap to avoid when this is built

EDGAR `companyfacts` can carry **several values for the same `period_end`**, stamped
with the accession in which they appeared — including later **restatements**. In the
AAPL sample both the FY2024 and FY2025 10-K facts show `filed=2026-11-03`, because that
is the filing in which they last appeared.

The correct PIT rule is therefore: for each `period_end`, use the **value as first filed
(earliest `filed`)**. Taking the latest-filed value would back-fill a restated number
into a period before the restatement was public — look-ahead of the subtlest kind. This
is the same class of error as the DSR artifact and the FX charge: a plausible-looking
number that is wrong in a known direction.

## What this means for the programme

B1 is **not** "value investing is untestable here". It is:

- today's HML result used an *approximate* PIT rule (90-day lag) on *survivor-conditioned*
  fundamentals — and still returned gross +0.11%/yr, killed by a wide margin;
- a true PIT rebuild is **feasible for free**, using a source we already have an adapter
  for, needing two changes (persist to disk; parse `filed`, earliest-first);
- doing that would tighten the test but cannot plausibly rescue it: the gross premium is
  ~0.11% against a 4.32% hurdle, and the residual survivor bias runs the *favourable*
  way already.

**So: rebuild PIT before trusting any *future* value test, but do not rebuild it hoping
to rescue HML — the gap is 4.2 percentage points of gross return, which no data cleaning
supplies.**

## Status

B1 remains **PARTIALLY CLEARED**, with the remaining work now specific and scoped:
persist the EDGAR fetch, parse `filed` earliest-first, and implement
`fundamentals_history_provider` against it.
