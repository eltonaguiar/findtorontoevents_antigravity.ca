# M1 provenance repair — 12.07 bp was real, its artifact was stale

**Date:** 2026-11-22T23:10Z · **Tool:** [`tools/equity_cost_measure.py`](../tools/equity_cost_measure.py) ·
**Artifact:** [`reports/equity_cost_measurement/equity_cost_20261122.json`](../reports/equity_cost_measurement/equity_cost_20261122.json) ·
**Tripwire:** [`tests/test_m1_cost_provenance.py`](../tests/test_m1_cost_provenance.py)

## Diagnosis: (a) STALE ARTIFACT

The number is a real measurement; the committed artifact was from a run that skipped the
measurement and overwrote the good run's output.

### Evidence that decides it

1. **The quoted per-name values reproduce exactly from a live re-run.** Re-running
   `measure_spread()` on yfinance 1-min bars, period=5d (the same 2026-11-16..20 window,
   which is immutable history), gives KO 5.2354 (quoted 5.24), NVDA 20.9972 (21.0),
   JNJ 6.7508 (6.75), PG 5.2759 (5.28), QQQ 12.0749 (12.07), SPY 8.3139 (8.31). These are
   not plausible-looking numbers a fabricator would pick; they are the deterministic
   output of the estimator on that window.
2. **The median is 12.0749 bp over the 13-name POD universe** (AAPL 8.23, AMZN 13.04,
   GOOGL 12.80, META 14.10, MSFT 12.12, NVDA 21.00, QQQ 12.07, SPY 8.31, XLE 7.39,
   XLF 6.11, XLK 14.21, XLV 5.78, XLY 7.31). M1 quoted 12.07 bp as "median over the
   13-name breakout universe" — exactly this.
3. **Mutually exclusive code paths (rules out (c)).** In `main()`, the yfinance spread
   loop writes `out["spread"][sym] = rec` and then `spread_aggregate` is derived from
   those records; the `else` branch sets `out["spread"] = {"status":
   "SKIPPED_OFFLINE_OR_NO_KEY"}`. The committed artifact has ONLY the `status` key in
   `spread` and `n_symbols_with_data: 0` in `spread_aggregate` — i.e. it is the `else`
   branch. The yfinance result did not land in a different field; there was no yfinance
   result in that run. So this is not a partial run hiding the number elsewhere.
4. **The gate explains the overwrite.** The loop was guarded by `if not a.offline and key:`
   with `key = os.environ.get("TIINGO_API_KEY", "")`. `measure_spread()` uses yfinance and
   needs no key, yet a process without `TIINGO_API_KEY` took the `else` branch and rewrote
   `equity_cost_20261122.json` as `SKIPPED_OFFLINE_OR_NO_KEY` over a prior good run.
5. **Timeline.** Artifact mtime 22:50:26Z; write-up mtime 22:50:43Z. The prose was written
   17 s after the stale artifact, quoting an earlier run. The artifact embeds
   `generated_utc: 2026-11-22T22:49:21Z` with `proof_bar.measured: "no measured cost
   available"`, while `break_even_bp_per_side` for the pod is 14.5838 and the 5bp/25bp proof
   bars are present — a run that did the cost curve but skipped the spread.

Cross-check: M3's `class_cost_20261122.json` (yfinance, 22:59Z) independently contains
`QQQ: 12.074926303113397` under the ETF label, consistent with M1's number.

## Before / after

| field | before (22:49:21Z) | after (regenerated 23:08Z) |
|---|---|---|
| `spread` | `{"status": "SKIPPED_OFFLINE_OR_NO_KEY"}` | 20 per-name records |
| `spread_aggregate.n_symbols_with_data` | **0** | **13** |
| `spread_aggregate.range_upper_bound_rt_bp_median` | **null** | **12.0749 bp** |
| `spread_aggregate.measured_cost_per_side_used_bp` | **null** | **6.0375 bp** |
| `spread_aggregate.corwin_schultz_rt_bp_median` | null | 1.5033 bp |
| `spread_aggregate.provenance_self_check` | (absent) | **PASS** |
| `spread_aggregate.per_name_rt_bp` | (absent) | 13 values inline |
| `spread_aggregate.bar_interval` / `window` | (absent) | `1m` / `2026-11-16..2026-11-20` |
| `proof_bar.measured` | `{"status": "no measured cost available"}` | full run at 6.0375 bp |
| `sources.intraday_bars` | Tiingo IEX (wrong — the loop uses yfinance) | yfinance primary, Tiingo fallback |

The regenerated artifact records source (`yfinance period=5d interval=1m (Yahoo)`),
endpoint, per-symbol `fetched_utc`, the date window, bar interval, the symbol list, and
per-name values — so a future reader can reproduce it.

## Re-derived numbers

### Cost curve (PF always with Sharpe and maxDD), D7 N=20 / N=55 and the pod

| variant | cost/side | PF | Sharpe | maxDD | net/trade |
|---|---|---|---|---|---|
| D7 N=20 | 0 | 1.5952 | 0.4927 | −77.0% | +1.217% |
| D7 N=20 | **6.04** | **1.5175** | **0.4438** | **−79.1%** | **+1.096%** |
| D7 N=20 | 25 | 1.3044 | 0.2903 | −84.4% | +0.717% |
| D7 N=55 | 0 | 1.7407 | 0.5489 | −57.8% | +1.371% |
| D7 N=55 | **6.04** | **1.6501** | **0.5005** | **−59.8%** | **+1.251%** |
| D7 N=55 | 25 | 1.4040 | 0.3488 | −65.5% | +0.871% |
| pod | 0 | 1.1628 | 0.3190 | −62.2% | +0.292% |
| pod | **6.04** | **1.0916** | **0.1869** | **−67.6%** | **+0.171%** |
| pod | 25 | 0.9007 | −0.2279 | −80.1% | −0.208% |

### Break-even per variant

- D7 N=20: **none reached** (still positive at 25 bp).
- D7 N=55: **none reached** (still positive at 25 bp).
- pod (VT pattern sweep): **14.5838 bp/side**.

### Do the two claims still hold?

- "measured cost (6.04) below break-even (14.58)" → **YES** for the pod. For D7, break-even
  is not reached at all, so it is trivially above.
- "measured cost (6.04) below the assumed 25 bp" → **YES**.

### Survivor proof bar at the corrected measured cost

A survivor exists (pod at 6.04 bp is below its 14.58 bp break-even), so the full bar was
re-run at 6.0375 bp/side: **null 10.2nd percentile** (gate ≥95 → FAIL), **excess CAGR
−14.25% CI [−46.32%, +32.31%]** (spans zero), **CAGR +5.33%**, **required 28.54%**
(4.32% T-bill + 1.114 × vol), verdict **NOT_INVESTABLE**.

The earlier write-up's "measured 6.04 bp" row (null 10.2, excess CAGR −12.69% [−45.23%,
+34.54%], CAGR +6.88%) was a **duplicate of the 5 bp row**, because the artifact had no
measured run to quote. That row is corrected above; the verdict was and is NOT_INVESTABLE.

## Claims withdrawn

**None.** Nothing is withdrawn. The 12.07 bp (→ 6.04 bp/side), the 14.58 bp pod break-even,
"measured below break-even", "measured below 25 bp", and the NOT_INVESTABLE verdict all
survive. The one *corrected* figure is the measured-cost proof-bar row (a 5 bp duplicate),
which is now the true 6.04 bp run; it does not flip any verdict.

## Unaffected (re-confirmed)

- **D7 equity kill is cost-independent.** Random-entry null 69.8th (N=20) / 71.4th (N=55)
  percentile against a ≥95 requirement; selection-alpha CI-LB −0.285% / −0.296%; median
  −1.5% with 39% win rate; −60%/−80% max drawdowns; survivorship-flattered universe. These
  are computed at 5 bp/side and do not involve the 12.07 bp figure. The equity breakout
  family is **NOT_INVESTABLE for cost-independent reasons**, before and after this repair.
- **M3 triage: 0 of 6 UNKNOWN rows are cost-addressable.** That rests on 0 bp/side
  break-evens, a 468.5 bp break-even, a 16.398d holding-period mismatch, and missing
  second-month contract series — none depend on 12.07 bp.

## Programme tally (recomputed from row verdicts, not hand-edited)

**0 INVESTABLE / 8 NOT_INVESTABLE / 6 UNKNOWN** — unchanged. No row moved: the repair
changed a cost *measurement* and one proof-bar row's numbers, not any row's verdict.

## Guard against recurrence

[`tests/test_m1_cost_provenance.py`](../tests/test_m1_cost_provenance.py) adds
`assert_quoted_metric_supported(artifact, quoted_bp)`, which rejects a quoted spread
figure unless the cited artifact has `n_symbols_with_data > 0`, a non-null median, and a
median matching the quote within 0.01 bp. It is wired into the pytest suite (`testpaths =
tests` in `pytest.ini`) and includes an inline copy of the stale-artifact shape so the
regression is durable without network access.

Demonstrated fail-before / pass-after:

```
BEFORE (stale committed artifact 22:49:21Z) -> FAIL: a 12.07bp figure is quoted but the artifact has n_symbols_with_data=0 - no spread data to support it
AFTER  (regenerated 23:08Z)                 -> PASS (12.07bp supported)
4 passed in 0.11s
```

## How verified

- `python3 -c "import py_compile; py_compile.compile('tools/equity_cost_measure.py', doraise=True)"` → ok.
- `python3 tools/equity_cost_measure.py` (live, yfinance) → regenerated artifact with
  `n_symbols_with_data = 13`, median 12.0749 bp.
- `python3 -m pytest tests/test_m1_cost_provenance.py -q` → 4 passed.
- `tools/momentum_core.py` was **not** modified.
