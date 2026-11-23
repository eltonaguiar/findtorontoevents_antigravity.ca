# PRE-REGISTRATION — H-242: does the 44-name H-201 edge survive a 10-year window?

**Filed:** 2026-11-23, before the run. **Rule:** M-107. **Status at filing:** REGISTERED, UNTESTED.

## Why

H-241 closed the survivorship question in a way nobody expected: the delisting stress is
**1.27 bp/day** while the baseline 95% CI half-width is **12.673 bp**. So H-201's outstanding blocker
is not the delisting flag — it is that five years of data cannot resolve a ±12.7 bp interval.
The single highest-value action is therefore **more history**, not more data sources.

The 44-name PIT universe currently starts 2021-11-22 because that is where its cached bars start.
Yahoo serves 10 years of daily bars for **all 44 names plus SPY** (verified 2026-11-23:
2,514 rows each, 2016-11-21 → 2026-11-20, zero missing). This hypothesis spends that extension.

## Construction

- **Universe:** the same 44-name list from `reports/pit_equity_universe_20261122.json`. Unchanged —
  no name added, none removed, so the only thing that changes versus H-236 is **time**.
- **Rule:** unchanged — `xsmom(lookback=126, top_k=3, rebal_days=21, cost_bps=10/side)`, SPY benchmark.
- **Windows, both reported:**
  - **W10** = 2016-11-21 .. 2026-11-20 (full 10 years).
  - **W5** = 2021-11-22 .. 2026-11-19 (the H-236 window), re-run from the same pipeline as a control.
- **Data:** `data/cache/pit_10y/` populated once from yfinance `period="10y"`, `auto_adjust=True`;
  the raw close series are cached so the run is reproducible offline.

## Test statistic

Mean net daily return in bp, block bootstrap 95% CI (block 5, 2,000 resamples, seed 7), plus mean
excess vs SPY and its CI — identical estimator to H-236 so the two are directly comparable.

## Acceptance (fixed before the run)

- **WIDENS_OR_HOLDS** iff the W10 CI lower bound is > 0 *and* the W10 CI is at least 25% narrower than
  the W5 CI from the same run. (The narrowing is the point; a wider interval on more data would mean
  the two periods disagree and must be reported as such.)
- **STILL_UNRESOLVED** iff the W10 CI upper bound > 0 but lower bound ≤ 0 — more history, same verdict,
  and the report must say the interval was still too wide.
- **REFUTED** iff the W10 CI upper bound ≤ 0.
- **INVALID** if the W5 control does not reproduce H-236's published 9.407 bp/day / −3.147 CI-LB
  (within rounding) on the same dates. If the control fails, the pipeline differs and nothing else counts.

## Stated in advance

- This **adds a trial**. N declared rises and every cell's deflation bar moves with it; that cost is
  accepted here rather than hidden.
- It **cannot** legalise survivorship: the 10-year universe is still today's 44 names. The flag goes
  from `BOUNDED` to `BOUNDED (longer window)`, never `CLEAN`.
- A pass on W10 when W5 failed must be reported as **period-dependent**, with both numbers side by
  side. It would not make H-201 investable, and no allocation follows from it.
