# H-149 delisting exits, H-150 quarterly TTM signal, and a registry guard

**Date:** 2026-11-21
**Files:** `tools/h149_midcap_gross_profitability.py`, `tools/h150_ttm_gpa.py`,
`tests/test_registry_duplicate_keys.py`,
`reports/h149_midcap_gross_profitability_2026-11-21.{md,json}`,
`reports/h150_ttm_validation.json`, `reports/hypothesis_registry.json`
**Status:** delisting measured (nothing truncated at exit); TTM signal validated at
91% 10-K agreement; registry duplicate keys now fail CI

## 1. Registry guard

Two edits in this session shipped duplicate JSON keys — a second `"verdict"` and
then seven copies of `"stress_net_edge_pct"`. `json.load()` silently keeps the
last one, so the file "parsed" while `status` said REJECTED and
`result.verdict` said UNTESTED.

`tests/test_registry_duplicate_keys.py` parses with `object_pairs_hook` and fails
on any duplicate key inside any object. It also asserts `status == result.verdict`
for H-149, which is the exact contradiction the duplication produced.

## 2. Delisting returns (H-149)

The bottom bucket's 49 observations (mean −15.74%) looked like truncation, so the
exit rule changed: a price series that ends inside the holding window now exits at
its **last available close** with a declared **−30%** haircut (Shumway/Warther
convention), instead of the record being silently dropped. The haircut is a
parameter (`delist_haircut_pct`) and the payload reports the bottom bucket with
and without it.

Result: **0 of 10,230 records exit on their last trade**, and the bottom bucket is
identical both ways (n=49, −15.74%). The full re-run reproduced §4/§5 exactly.

The truncation is real but one level earlier: 759 names clear the fundamentals
filter and only 711 have any price series, so **48 names are dropped at entry** —
the failures are warrants, units and delisted tickers (`XBPEW`, `NEOVW`, `NIVFW`,
`AIDX`, `LIVG`). They never enter the book and therefore cannot appear in the
bottom bucket. Both legs of the +17.78% long/short spread remain survivor subsets;
recovering those names needs a delisted-ticker price source, not a code change.

## 3. Quarterly TTM GP/A (H-150)

`tools/h150_ttm_gpa.py` implements the pre-registered H-150 signal — GP/A from
quarterly statements filed strictly before the as-of date — and validates it
before any backtest.

The trap is that 10-Q facts mix quarterly (~90 day) and year-to-date (~180/270
day) durations. The numerator is the sum of the last four facts whose duration is
80–100 days. Two guards matter, and the first version had neither:

* **non-overlap** — a quarter may not start before the previous one ended;
* **tiling** — for validation, the four quarters must span the fiscal year they
  are compared against.

| rule | comparable pairs | within 1% | max error |
|---|---|---|---|
| ends spaced 60–130 days (first attempt) | 254 | 82.28% | 206% |
| + non-overlap + tiling | 225 | **91.11%** | 206% |

225 pairs from 30 companies, median relative error **0.0**, p90 0.49%, 94.2%
within 5%. The residual failures are restatement vintages — CIK 62996 (15.1% and
17.7% for 2013 and 2017) and CIK 8947 (53.6% for FY2021), where the annual fact
comes from a later amendment than the quarters available at filing time.

**Conclusion:** the TTM framing is sound for ~91% of pairs, and the failures are
identifiable rather than silent. The H-150 backtest is still unrun — next-open
entry, the 20–60 calendar-day exit and the top-quintile book are the remaining
pieces.

## Verification

- `pytest tests/test_registry_duplicate_keys.py tests/test_hypothesis_status.py`
  → 12 passed.
- `--self-check` on the H-149 tool still reports `unmodified=True`.
- Both artifacts parse; the registry parses under the strict duplicate-key hook.
- The H-149 re-run reproduced the committed economics exactly (10,230 records,
  71 windows ≥80, 66 scored, 4+/11−, net +0.9598%, factor alpha t=0.04).

## Limitations

- The 48 never-priceable names cannot be recovered without a delisted-ticker
  price source; entry-side survivorship therefore remains.
- TTM validation covers 30 of 95 companies that returned facts (250 sampled);
  a full-sample pass is a longer run, not a different method.
- `companies_checked` is low because many random SEC filers are absent from
  `company_tickers.json` or report no `us-gaap:GrossProfit`.
