# Live-pick excess returns — the "unknown" column, measured

**Agent:** buffy (Codebuff) · **Date:** 2026-11-15
**Tool:** [`tools/pick_excess.py`](../../tools/pick_excess.py) · **Artifact:** [`artifacts/pick_excess_returns.json`](artifacts/pick_excess_returns.json)
**Source data:** `audit_dashboard/data/dashboard_data.json`, `picks.recent_closed`, generated `2026-10-19T19:40:11Z`

---

## 1. What was unknown, and what it is now

`SPEC_EQUITY.md` said, correctly at the time, that the repo's single-stock picks had **no
excess-return number** — so their edge was `unknown`, not proven and not refuted. The same was true
for ETF and CRYPTO live picks. That gap is now closed: every closed pick in those three classes is
compared against its class beta over the pick's **own holding window**, and the aggregate is reported
with a t-stat that cannot be inflated by batch-fired picks.

| Class | Picks scored | Distinct windows | Mean pick | Mean β over same window | **Excess** | t (clustered) | Excess win rate |
|---|---:|---:|---:|---:|---:|---:|---:|
| **EQUITY** | 653 | 386 | +0.45% | +0.21% | **+0.24pp** | **0.96** | 46.1% |
| **ETF** | 475 | 261 | +0.16% | +0.09% | **+0.06pp** | **−0.22** | 46.7% |
| **CRYPTO** | 1,017 | 241 | +0.46% | +1.75% | **−1.29pp** | **−4.60** | 42.5% |

Read this as: **EQUITY and ETF live picks are statistically indistinguishable from simply holding
their beta.** The point estimate is positive but |t| < 1, so the honest verdict is *no demonstrated
edge*, not *a small edge*. **CRYPTO live picks are materially worse than holding BTC** — −1.29pp per
pick at t = −4.60, i.e. the picks lose ~1.3pp against the benchmark each time they fire, and the
benchmark beat them in 57.5% of picks.

That last line is the substantive finding of this document. The crypto book is not merely
unproven against beta; on this sample it is **negative** against beta.

---

## 2. Method, fixed before results were seen

* **Trade universe:** every closed EQUITY/ETF/CRYPTO pick with usable entry and exit prices — 3,263
  picks in total.
* **Pick return:** the dashboard's own convention, so numbers reconcile with `pnl_pct`:
  `long = exit/entry − 1`, `short = entry/exit − 1`. Where the recomputed return disagrees with
  `pnl_pct` by more than 0.5pp, the pick is excluded and counted as a data-quality miss.
* **Benchmark:** the class beta, not a peer strategy — **SPY** for EQUITY and ETF, **BTC-USD** for
  CRYPTO, daily adjusted close.
* **Window:** last close **on or before** the signal date → last close **on or before** the close
  date. If those resolve to the same trading day the pick has no measurable benchmark window and is
  excluded, never scored as zero excess.
* **Excess:** `pick return − benchmark return`, in percentage points. A short that profits while SPY
  rises has positive excess; that is the entire purpose of comparing against beta.

### Coverage (all exclusions are counted, none are silently dropped)

| Outcome | Picks | Share of 3,263 |
|---|---:|---:|
| Scored | **2,145** | **65.7%** |
| Window collapsed (entry and exit resolve to the same benchmark close) | 1,056 | 32.3% |
| Recomputed return differs from `pnl_pct` by > 0.5pp (ledger data-quality miss) | 49 | 1.5% |
| No usable entry/exit price | 9 | 0.3% |
| Unparseable dates | 4 | 0.1% |

The 1,056 collapsed windows are a **structural limit**, not a bug: comparing an intraday hold to a
daily benchmark has no defensible answer, and inventing one (e.g. treating same-day excess as 0)
would bias every fast strategy toward "no edge". Median hold by class: EQUITY 120h, ETF 98h,
CRYPTO 9.4h — so this exclusion necessarily bites hardest on the fastest crypto rules.

### Why the t-stat is clustered

Picks closed on the same pair of days share one market move and are **not independent**. A naive
per-pick t-stat therefore overstates significance whenever a strategy fires in batches. Each
`(entry_day, exit_day)` window is collapsed to its mean excess and the t-stat is computed over
windows. The difference is not cosmetic:

| Class | Naive per-pick t | Clustered t | Verdict change |
|---|---:|---:|---|
| EQUITY | +1.12 | 0.96 | no |
| ETF | **+0.56** | **−0.22** | **sign flips** |
| CRYPTO | −6.19 | −4.60 | no (magnitude drops 26%) |

`ETF` flips sign under the correct unit of observation. Any claim resting on the naive number would
have been wrong.

One strategy demonstrates the failure mode in full: `hs_Auros_66M` has 8 picks that are all the same
six-month window (identical entry day, exit day and return), so it has **one** independent
observation and the tool reports `n/a` rather than a t-stat of −169,292.

---

## 3. Strategy-level detail

Headline requires n ≥ 5. Best and worst of 57 strategies:

| Strategy | n | Windows | Excess | t (clustered) | Excess WR |
|---|---:|---:|---:|---:|---:|
| `bb-squeeze-breakout-scout` | 6 | 5 | +3.52pp | 0.84 | 50.0% |
| `vix-mean-rev-scout` | 8 | 6 | +2.23pp | 1.49 | 62.5% |
| `donchian-stock-breakout` | 42 | 39 | +2.01pp | 1.45 | 59.5% |
| `vwap-reversion-scout` | 28 | 25 | +1.96pp | **1.99** | 60.7% |
| `gap-and-go-stocks` | 21 | 20 | +1.68pp | 1.11 | 47.6% |
| … | | | | | |
| `fibonacci-bounce-scout` | 12 | 12 | −2.95pp | −2.70 | 8.3% |
| `MomentumEMA` | 73 | 37 | −11.56pp | −7.84 | 4.1% |
| `clone_hl_copy_PensionFund_24M` | 8 | 2 | −11.91pp | −0.54 | 12.5% |
| `clone_hl_copy_lb_None` | 17 | 2 | −17.65pp | −7.57 | 0.0% |
| `hs_Auros_66M` | 8 | **1** | −17.93pp | n/a | 0.0% |

`vwap-reversion-scout` is the only row in the top group reaching t ≈ 2 on 25 independent windows.
That is a **lead worth forward-testing**, not a proven edge: 25 windows clears no multiple-testing
correction across 57 strategies, and the 5% bar for 57 trials is roughly |t| > 2.9.

---

## 4. What this does and does not establish

**Does:** fills the `unknown` cells. EQUITY/ETF picks now have a measured, non-significant positive
excess; CRYPTO picks have a measured, significant negative excess against BTC. `SPEC_EQUITY.md` and
`SPEC_CRYPTO.md` cite these numbers instead of saying "unknown".

**Does not:** establish portfolio-level performance. Per-pick excess is an average over trades of
unequal size, overlapping in time and with no capital constraint — it is not the return of a
portfolio that held them. A strategy can have positive per-pick excess and negative portfolio
return if it sizes up after losses. Treat §3 as a screen for what to forward-test, not as a track
record.

**Also does not:** resolve the 1,056 excluded picks. Measuring those needs intraday benchmark bars
(hourly SPY/BTC), which this repo does not cache. That is the next data dependency if fast rules are
to be judged at all.

---

## 5. Reproduce

```bash
python3 tools/pick_excess.py                       # -> reports/pick_excess_returns.json
python3 tools/pick_excess.py --classes EQUITY --min-n 10
```

Benchmark series are cached under `data/cache/pick_excess/` using explicit `period1`/`period2`
epochs — the `range=max&interval=1d` form silently returns monthly bars and would corrupt every
window that spans a month boundary.
