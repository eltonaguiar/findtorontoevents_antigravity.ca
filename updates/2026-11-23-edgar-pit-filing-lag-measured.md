# PIT filing lags measured from EDGAR — and a correction to my own 90-day proxy claim

**Date:** 2026-11-23
**Register item:** `docs/UNMEASURED_REGISTER_2026-11-23.md` priority #1 — **PIT 2a: wire EDGAR `filed` dates**
**Files:** `tools/edgar_pit_fundamentals.py` (new), `tests/test_edgar_pit_fundamentals.py` (new, 8 tests), `reports/pit_filing_lag.json` (generated), `data/fundamentals_pit/*.json` (12 tickers)
**Verdict:** the 90-day reporting-lag proxy in `tools/hml_pit_backtest.py` is **mostly safe and partly wrong** — safe on 98.8% of periods, look-ahead on **1.16%**, and it needlessly discards **56 days** of already-public information on the median period.

---

## What was broken

`tools/hml_pit_backtest.py` carried a hardcoded constant:

```python
REPORTING_LAG_DAYS = 90
```

with `fundamental_asof(funds, date, lag)` requiring `period_end + lag <= date`. 90 days was **assumed, never measured**. Two opposite failure modes follow from a single constant, and only one of them was ever discussed:

1. **Too short** → a fact is used before it was public → look-ahead, inflating the backtest.
2. **Too long** → a fact that *was* public is withheld → the strategy trades on stale book value → *understating* any value signal.

Fix #2 is invisible in results; it just makes value look weaker than it was. That is the more likely direction of bias here, and it was never considered.

## What was changed

`tools/edgar_pit_fundamentals.py`:

- Fetches `https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json` (SEC free API), UA `findtorontoevents-research contact@findtorontoevents.ca`, paced 0.16 s/req (~6 req/s, under SEC's 10 req/s ceiling).
- `pit_history()` keeps the **EARLIEST `filed` per `period_end`** — anti-restatement. A later amendment must not retroactively change what a real-time investor saw.
- `as_of(ticker, date)` is the only PIT-safe accessor. It filters on `filed <= date` and **never** on `period_end`.
- Tags: `StockholdersEquity` and `StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest`.
- New `ARTIFACT_LAG_DAYS = 180` guard (see the correction below).

## The correction — my first number was wrong by 18×

First run reported **4.61% of periods filed after 90 days** and I was about to publish "a 90-day proxy would be look-ahead on 4.61%". Inspecting the 8 largest lags killed that:

| lag | ticker | period_end | filed |
|---:|---|---|---|
| 1157d | ADM | 2007-06-30 | 2010-08-30 |
| 1152d | ACN | 2007-08-31 | 2010-10-26 |
| 1152d | ABNB | 2018-12-31 | 2022-02-25 |
| 1148d | ADBE | 2006-12-01 | 2010-01-22 |

These are **not late filings**. They are XBRL-adoption artefacts (a 2006–07 fiscal year first appearing in machine-readable form in a 2009–10 filing) plus ABNB's pre-IPO retrospective. Real late filings don't take 3 years.

After excluding `lag > 180d`: **775 PIT-usable periods, median 34d, p10 23d, p90 51d, range 16–134d, genuine look-ahead 9/775 = 1.16%.**

Lesson: a distribution's tail is where the estimator fails. I computed a summary statistic before checking whether the extreme values were real, and it changed the answer by a factor of 18.

## Measured result (12 tickers, 803 periods, 775 usable)

- median lag **34 days**, p10 23d, p90 51d, max 134d
- 90-day proxy is **look-ahead on 1.16%** of periods (9/775) — small but not zero
- 90-day proxy **wastes 56 days** on the median period
- Excluded 28/803 (3.49%) as adoption/pre-IPO artefacts

## Does this rescue the HML test? No.

`docs/preregistration/HML_VALUE_TEST_2026-11-22.md` killed HML on **gross** return: gross **+0.11%**, net **+0.02%**, SE 6.65%, 95% UB **+10.96%** vs hurdle **4.32%**. The kill was driven by the *signal*, not by look-ahead and not by cost. A more precise filing lag cannot move that result — it can only shave the PIT error term, which is bounded by the 1.16% exposure measured above.

So PIT 2a's value is **infrastructure for the next fundamental test**, not a rescue for the last one. Recording this explicitly so nobody re-runs HML expecting a different verdict.

## How it was verified

```
python3 -m pytest tests/test_edgar_pit_fundamentals.py -q   ->  8 passed
python3 tools/edgar_pit_fundamentals.py --limit 12          ->  775 usable / 28 artefacts / 1.16% look-ahead
```

The 8 tests pin the properties that must never regress:

- `test_restatement_resolves_to_earliest_filed_value` — same `period_end` filed twice returns the **original** (100.0), not the restatement (90.0)
- `test_as_of_never_returns_a_future_filed_fact` — one day before a filing the earlier value is returned; on the filing date the new one becomes visible
- `test_as_of_returns_none_before_any_filing`
- `test_as_of_skips_artefacts` — a 2007 period filed in 2010 never becomes visible
- `test_xbrl_adoption_lag_is_flagged_not_used` — 1157d flagged `usable_for_pit=False`
- `test_lag_is_filed_minus_period_end`, `test_normal_lag_is_usable`, `test_as_of_unknown_ticker_is_none`

## Not yet done

- Only **12 tickers** populated (the register asks for 500). `--limit 500` is a ~90 s fetch; store is ~12 KB/ticker so 500 ≈ 6 MB. Not run in this block.
- `hml_pit_backtest.py` still uses the 90-day constant. Swapping it for `as_of()` is a separate change because it alters a pre-registered test's inputs; it needs its own pre-registration note rather than a silent edit.
- Tag coverage varies by company; names that don't report `StockholdersEquity` fall back to the NCI-inclusive tag and some report neither.

Zero capital sanctioned. Paper only. Not investment advice.
