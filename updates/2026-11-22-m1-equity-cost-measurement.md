# M1 — EQUITY/ETF cost measurement

> ## ⚠️ CORRECTION NOTICE (provenance repair, 2026-11-22T23:10Z)
>
> **Diagnosis (a): stale artifact.** The 12.07 bp figure is a **REAL measurement**,
> but the artifact committed at 22:49:21Z could not support it: it recorded
> `spread.status = SKIPPED_OFFLINE_OR_NO_KEY`, `spread_aggregate.n_symbols_with_data = 0`,
> and `proof_bar.measured = "no measured cost available"`. The write-up (mtime 22:50:43Z)
> was authored *after* that artifact, quoting numbers from an earlier successful run whose
> output had been overwritten.
>
> **Root cause:** [`tools/equity_cost_measure.py`](../tools/equity_cost_measure.py) gated the
> yfinance spread loop on `if not a.offline and key:` where `key = TIINGO_API_KEY` — even
> though `measure_spread()` uses yfinance and needs no key. A key-less re-run therefore took
> the `else` branch and overwrote the good artifact with `SKIPPED_OFFLINE_OR_NO_KEY`.
>
> **What was wrong:** the artifact, not the number. **What it is now:** the gate is fixed
> (only `--offline` skips the spread; top-of-book alone still requires the Tiingo key), and the
> artifact was regenerated live from yfinance 1-min bars (2026-11-16..20, period=5d):
> `n_symbols_with_data = 13`, median RT bound **12.0749 bp**, per-side **6.0375 bp**,
> Corwin-Schultz **1.5033 bp**, `provenance_self_check = PASS`, with per-name values recorded
> inline. Every per-name value quoted below reproduces exactly (KO 5.235→5.24, NVDA 20.997→21.0,
> JNJ 6.751→6.75, PG 5.276→5.28, QQQ 12.075→12.07).
>
> **One figure below was ALSO wrong and is corrected:** the "measured 6.04 bp" proof-bar row
> previously duplicated the 5 bp row (null 10.2, excess CAGR −12.69% [−45.23%, +34.54%],
> CAGR +6.88%) because no measured run existed. The true 6.04 bp run is **null 10.2nd
> percentile, excess CAGR −14.25% [−46.32%, +32.31%], CAGR +5.33%, required 28.54%,
> NOT_INVESTABLE**. The verdict is unchanged; the row is now honest.
>
> **No conclusion is withdrawn.** The D7 kill is cost-independent and the pod's break-even
> (14.58 bp/side) still exceeds measured cost. See
> [`2026-11-22-m1-provenance-repair.md`](2026-11-22-m1-provenance-repair.md).

**Date:** 2026-11-22 · **Tool:** [`tools/equity_cost_measure.py`](../tools/equity_cost_measure.py) ·
**Artifact:** [`reports/equity_cost_measurement/equity_cost_20261122.json`](../reports/equity_cost_measurement/equity_cost_20261122.json)

Research measurement, not a feature. Read-only, no orders.

## What was ASSUMED before

`COST_BP_PRIMARY = 25.0` at [`tools/pod_equity_breakout_backtest.py:51`](../tools/pod_equity_breakout_backtest.py:51)
— "the hypothesis's own stated equity slippage". It was never measured. Other
assumptions in circulation: 5 bp/side (D7 family), 4 bp/side (N1 base),
8 bp round trip (pod emitter), and 10 bp round trip (`tools/data/transaction_costs.json`,
whose EQUITY note says "commission-free broker + typical bid-ask spread" with no source).

## What is MEASURED now

Source: **yfinance 1-minute bars, `period=5d`**, 2026-11-16 → 2026-11-20, fetched
2026-11-22T22:43Z. Tiingo IEX was the intended source but its **hourly request
allocation was exhausted** (`HTTP 429`), so the independent Yahoo path was used;
Tiingo IEX remains the documented fallback. 1,950 bars per symbol, regular session.

Three estimators per name, deliberately not collapsed to one number:

| Estimator | What it is | Reading |
|---|---|---|
| **Median 1-min bar range** | An *upper bound*: at any instant bid and ask both lie in `[low, high]`, so the round-trip quoted spread ≤ high−low | **12.07 bp** round trip (median over the 13-name breakout universe) |
| **Corwin–Schultz** | Range-based point estimate | **1.50 bp** round trip (median); pooled 0.0 because 40–47% of pairs floor at zero |
| **Roll** | Return-autocovariance estimate | Mostly 0 (positive autocovariance); structurally invalid at 1-min resolution, kept for the record |

**Per-side cost used for the re-cost: 6.04 bp** = half the 12.07 bp upper bound.
This is deliberately the *pessimistic* choice: the true NBBO is tighter than a
1-minute bar range, and Corwin–Schultz (1.50 bp) points much lower. The honest claim
is therefore "**equity RT cost is at most ~12 bp, plausibly ~1.5–3 bp**", not a single
false-precision constant.

### Top-of-book: BLOCKED

Live NBBO was attempted at 2026-11-22T22:43Z and returned `HTTP 429` / null bid-ask
(2026-11-22 is a Sunday; US session closed). Recorded as **`BLOCKED_NO_LIVE_NBBO`**,
never as zero. The range upper bound above is what stands in for it.

### Commission: `COMMISSION_UNKNOWN`

No broker statement and no fill-level commission data exist in the repo. The 10 bp
figure in `transaction_costs.json` is an unsourced assumption. A zero-commission
claim cannot be verified here, so it is not made.

### Borrow: zero for THIS family

The pod family is **long-only by construction** — `backtest_symbol()` skips any signal
whose direction is not `LONG`/`BUY` ([`tools/pod_equity_breakout_backtest.py:104`](../tools/pod_equity_breakout_backtest.py:104)).
No short leg, no borrow. A hypothetical short leg would be **`BORROW_UNKNOWN`** (no
borrow rate is in the repo).

### Slippage beyond the spread: negligible at the family's size

Median daily share volume measured on the 13 names (AAPL 112.2M, NVDA 2,222.8M,
SPY 173.3M, …). At a $100k book over 13 names (~$7.7k/name), **order/ADV is
2.2e-7 to 8.8e-6** (≈ 1e-5 at most). At that participation there is no market
impact to speak of, so "spread plus nothing" is justified with numbers rather
than asserted.

## The cost curve (PF never quoted alone)

D7 Donchian rule, 15 ETFs/equities, 2021-11 → 2026-11, cached daily bars:

| cost/side | N=20 PF | N=20 Sharpe | N=20 maxDD | N=55 PF | N=55 Sharpe | N=55 maxDD |
|---|---|---|---|---|---|---|
| 0 bp | 1.595 | 0.493 | −77.0% | 1.741 | 0.549 | −57.8% |
| **6.04 bp (measured)** | **1.529** | **0.449** | **−79.2%** | **1.668** | **0.514** | **−59.8%** |
| 10 bp | 1.469 | 0.412 | −80.3% | 1.594 | 0.469 | −61.1% |
| 25 bp | 1.304 | 0.290 | −84.4% | 1.404 | 0.349 | −65.5% |

The N=20 row at 5 bp reproduces D7 exactly (Sharpe 0.452, mean +1.117%/trade,
maxDD −78.7%) — the harness is the same harness. **Break-even is not reached by 25 bp**
for either N: the 25 bp constant was *not* what killed this rule on this data.

The **actual pod strategy** (VT pattern sweep, real code, 13-name pod universe,
276 trades on cached 5y bars) is weaker and **does** cross:

| cost/side | PF | Sharpe | maxDD | net/trade |
|---|---|---|---|---|
| 0 bp | 1.163 | 0.319 | −62.2% | +0.292% |
| **6.04 bp** | **1.088** | **0.166** | **−68.1%** | **+0.156%** |
| 15 bp | 0.996 | −0.009 | −74.3% | −0.008% |
| 25 bp | 0.901 | −0.228 | −80.1% | −0.208% |

**Break-even for the pod: 14.58 bp/side** on this window. Measured cost (6.04 bp,
upper bound) is *below* it. Note this is the 5-year window, not the all-history window
where break-even was 24.59 bp.

## The proof bar on the measured-cost survivor

The pod at measured cost is a survivor, so the full bar was applied (null 500
shuffles, bootstrap 10,000 resamples on excess CAGR vs SPY, judged against the
**4.32% T-bill** hurdle with hurdle Sharpe 1.114):

| run | null percentile | excess CAGR vs SPY (95% CI) | CAGR | required return | verdict |
|---|---|---|---|---|---|
| **measured 6.04 bp** | **10.2** | −12.69% [−45.23%, +34.54%] | +6.88% | 28.54% | **NOT_INVESTABLE** |
| 5 bp | 10.2 | −12.69% [−45.23%, +34.54%] | +6.88% | 28.54% | NOT_INVESTABLE |
| 25 bp | 6.8 | −39.05% [−63.65%, −3.30%] | −19.47% | 28.54% | NOT_INVESTABLE |

It fails the decisive control: the observed Sharpe sits at the **10.2nd percentile**
of random entries, not above the 95th, and its CAGR (+6.88%) is far below the 28.54%
required to clear T-bills at this volatility. **Cheaper cost did not save it.**

**In-sample PF 1.2206 at 5 bp is not evidence.** It is in-sample, with no null, no
CI, and no survivorship control. Any one of those can produce it; together they
cannot make a verdict.

## Survivorship

[`tools/pit_universe.py`](../tools/pit_universe.py): 79 symbols on disk, 15 present at the
earliest date, 35 at the latest. The gap is a **lower bound** on survivorship (the
tool only removes first/last-close censoring; it cannot remove
delisting-with-poor-returns bias). The 13-name pod universe is today's list, so its
backtest is survivorship-flattered and any positive result is unsafe.

## What remains UNKNOWN

- **Top-of-book NBBO spread** (market closed at sampling; no historical NBBO entitlement here).
- **Commission / fill quality** (no broker statement or fill data).
- **Borrow rate for any short leg** (the family does not short, so not needed for it).
- The 12.07 bp is an upper bound, not a measurement of the quote.

## How verified

- `python3 -c "import py_compile; py_compile.compile('tools/equity_cost_measure.py', doraise=True)"` → ok.
- The N=20 5 bp row reproduces D7's published Sharpe 0.452 / mean 1.117% / maxDD −78.7%.
- The artifact records the endpoint, sample timestamps and every refusal (`COMMISSION_UNKNOWN`,
  `BLOCKED_NO_LIVE_NBBO`) inline.
