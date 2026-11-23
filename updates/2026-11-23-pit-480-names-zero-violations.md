# PIT scaled to 480 names: 0 look-ahead violations, and two new defects

**Date:** 2026-11-23
**Backlog:** B1, B2, B3 (+ B5 deferred) in `docs/BACKLOG_100_2026-11-23.md`
**Files:** `tools/edgar_pit_fundamentals.py` (hardened), `tools/pit_lookahead_audit.py` (new), `reports/pit_filing_lag.json`, `reports/pit_lookahead_audit_2026-11-23.json`
**Result:** 480 tickers / 32,049 periods / **30,332 PIT-usable**. Look-ahead audit: **0 exclusion violations, 0 visibility violations, 0 tickers affected** — the `as_of` contract holds at scale. Two new defects found and fixed along the way.

---

## Measured at scale (480 names)

| metric | 12-name sample | 480-name run |
|---|---:|---:|
| PIT-usable periods | 775 | **30,332** |
| excluded artefacts | 28 (3.49%) | 1,717 (5.36%) |
| median lag | 34d | **35d** |
| p10 | 26d | 25d |
| p90 | 31d | **54d** |
| genuine look-ahead on a 90d proxy | 1.16% | **0.6%** |
| days of public data wasted by a 90d proxy | 56 | 55 |

Note the universe is **480, not 500**: `data/earnings` contains only 480 tickers with a resolvable CIK. Recorded rather than silently rounded up (backlog I6).

## Defect 1 — a negative filing lag, i.e. a fact filed before its period ended

The run printed `range -59..176d`. A fact cannot be filed before the period it reports has ended, so I inspected the tail rather than accepting the summary:

```
lag  ticker  period_end   filed       form  tag
-59  ROP     2009-12-31   2009-11-02  10-Q  StockholdersEquityIncluding...
```

Exactly **1 record in 30,333 (0.003%)** — an EDGAR mis-tag for ROP. Small, but it is a genuine **look-ahead leak**: `as_of("2009-11-02")` would have returned a period ending 2009-12-31, i.e. two months of future data.

**Fix:** the usable window is now `0 <= lag <= 180`. The smallest genuine lag in the whole store is 8d (16d in the original sample), so nothing legitimate is lost.

## Defect 2 — a cached `usable_for_pit` flag outlived the rule that produced it

After tightening the rule I re-ran `--report` and it **still printed `range -59..176d`**. The report was reading the stored `usable_for_pit` boolean written under the *old* rule.

This is the same defect class as a hard-coded promotion list in a dashboard generator, and as the `.pyc`-style stale artifact: **a cached derived field silently outlives the rule that produced it**, so the fix looks applied while the reported number is unchanged.

**Fix:** a single `is_usable(lag_days)` function, and `as_of()` and `report()` both **recompute** from `lag_days` instead of trusting the stored flag. Post-fix the range is `8..176d` and the usable count moves 30,333 → 30,332.

## My own stability check was too lenient — and the code now says so

The B3 question was "was the 12-name sample special?". First version judged on **median drift only**: 34d vs 35d = 1d = declared STABLE.

That verdict was wrong. The sample's **p90 was 31d against the full 54d — 23 days short**. A stable median hid a shifted tail, which is precisely the failure mode of a small sample: it looks representative in the middle and is unrepresentative at the edge.

**Fix:** the audit judges median **and** p90, and now prints:

```
median drift  1d
p90 drift     23d
verdict       TAIL UNSTABLE -- median agrees but p90 does not;
              the 12-name sample understated the tail
```

Consequence for the earlier PIT 2a write-up: its "1.16% look-ahead" is directionally right but its p90 of 51d was already optimistic — the full-store p90 is 54d. The look-ahead rate at scale is **0.6%**, i.e. the 12-name sample *overstated* look-ahead while *understating* tail lag. Both are small-sample artefacts in opposite directions, which is a good argument for never publishing a distribution from 12 points.

## How it was verified

```
python3 tools/pit_lookahead_audit.py
  tickers audited          480
  usable facts probed      30332
  exclusion violations     0     <- fact never visible the day before filing
  visibility violations    0     <- never returns a record filed after the as-of date
  tickers with violations  0     -> PASS

python3 -m pytest tests/test_edgar_pit_fundamentals.py -q   ->  8 passed
```

The audit probes **two different properties per fact**: exclusion (the market did not know it yet) and visibility (no later amendment leaked backwards). A provider could pass one and fail the other, so both are checked.

## Not done

- **B5** — `hml_pit_backtest.py` still uses `REPORTING_LAG_DAYS = 90`. Changing it alters a pre-registered test's inputs and needs its own preregistration, per backlog B5.
- **B6** — tag coverage (how many names report neither equity tag) not yet quantified.
- **B7** — fiscal-year misalignment test on a non-December year end not yet written.
- **B8** — universe survivorship: still `BLOCKED`, needs external constituent history.

Zero capital sanctioned. Paper only. Not investment advice.
