# 2026-11-15 — measured live-pick excess returns, and a tested PREDICTION settlement resolver

**Agent:** buffy · **Branch:** `wired-in/buffy-2026-11-15`

## What was missing

1. Every doc in `WIRED_IN/2026-11-15_0128_buffy/` marked EQUITY / ETF / CRYPTO live-pick edge as
   `unknown`, because no excess-return number existed for anything other than the index rules. An
   unknown cell is honest but it is not an answer.
2. `SPEC_PREDICTION.md` said binary contracts were "not representable" by the resolver, so
   prediction-market calibration had never been computable at all.

## What changed

**`tools/pick_excess.py` (new).** Scores every closed EQUITY/ETF/CRYPTO pick in
`audit_dashboard/data/dashboard_data.json` against its class beta (SPY, SPY, BTC-USD) over the
pick's own holding window.

* Pick return uses the dashboard's convention so figures reconcile with `pnl_pct`; picks whose
  recomputed return disagrees by >0.5pp are counted and excluded.
* A pick whose entry and exit resolve to the same benchmark close has **no** measurable window and
  is excluded, never scored as zero excess.
* t-stats are computed over `(entry_day, exit_day)` clusters, not over picks. `agg()` reports both
  `t_stat` (naive) and `t_cluster`; the headline uses the clustered value.

**`tools/pm_binary.py` (new).** The PREDICTION class: binary settlement (`settle`), Kalshi's
round-up-to-the-cent fee, Polymarket zero taker fee, calibration statistics (`brier`, `log_loss`,
`reliability`, `ece`, skill vs base rate), a `settle` CLI that writes `state/pm_binary/settled.jsonl`,
a `fetch` path against Polymarket, and a 15-case `selftest`.

## Verified

```
python3 tools/pm_binary.py selftest                 -> 15/15 cases pass
python3 tools/pick_excess.py                        -> exit 0, 2,145 picks scored, writes JSON
python3 tools/pm_binary.py fetch --max-markets 12   -> 12 markets tried, 0 with price history
                                                       => calibration reported NOT MEASURED
```

## Results (see `WIRED_IN/2026-11-15_0128_buffy/EXCESS_RETURNS.md`)

| Class | Picks | Windows | Excess vs β | t (clustered) |
|---|---:|---:|---:|---:|
| EQUITY | 653 | 386 | +0.24pp | 0.96 |
| ETF | 475 | 261 | +0.06pp | −0.22 |
| CRYPTO | 1,017 | 241 | −1.29pp | −4.60 |

## Bugs found in my own first pass

* **ETF sign flip.** The naive per-pick t-stat was **+0.56**; the clustered t-stat is **−0.22**.
  Batch-fired picks that share a window were manufacturing significance. Fixed before any number
  was published.
* **Impossible t-stat, real cause.** `hs_Auros_66M` showed t = −169,292. Not a math error: 8 picks
  were one identical six-month window, so `n_windows = 1`. The tool now reports `n/a` for a single
  cluster instead of a huge t.
* **Wrong selftest expectation.** I asserted 96.5% for a 50¢ Kalshi winner; the fee rounds up to
  0.02 from 0.0175, so 96.0% is correct. The test was fixed, not the code — the expected value was
  the thing that was wrong.

## Notes / limits

* Per-pick excess is not portfolio return: trades overlap, sizes differ, no capital constraint.
  It is a screen for what to forward-test.
* 1,056 of 3,263 picks (32.3%) are excluded because an intraday hold has no daily-benchmark window.
  Judging fast rules needs intraday benchmark bars, which the repo does not cache.
* Polymarket's `prices-history` returns empty for every resolved market tried, including the 2024
  election ($1.5B volume). PREDICTION stays `NOT MEASURED` for a named, checkable data reason.
