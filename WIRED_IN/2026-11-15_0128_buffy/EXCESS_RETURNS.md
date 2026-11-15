# Live-Pick Excess Returns — measured

**Regenerated:** 2026-11-15 · **Tool:** [`tools/pick_excess.py`](../../tools/pick_excess.py) · **Artifact:** [`artifacts/pick_excess_returns.json`](artifacts/pick_excess_returns.json)

Every other document in this folder says the live EQUITY / ETF / CRYPTO picks have `unknown`
excess. This one replaces that with a number, measured per pick against the class beta over the
pick's own holding window.

---

## 1. Result

| Class | Picks scored | Independent windows | Mean pick | Mean β | **Excess** | Excess WR | t (clustered) | t (naive) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| EQUITY | 674 | 407 | +0.44% | +0.20% | **+0.238pp** | 45.7% | 0.97 | 1.14 |
| ETF | 498 | 279 | +0.08% | +0.06% | **+0.023pp** | 45.0% | −0.62 | 0.21 |
| CRYPTO | 1,825 | 884 | +0.20% | +1.00% | **−0.795pp** | 40.9% | **−3.65** | −5.83 |

Read it against the benchmark, never on its own:

- **EQUITY**: +0.24pp per pick over holding SPY, t = 0.97. Not an edge, not a hole — **indistinguishable
  from beta**. But note the shape: mean **+0.24pp** while median is **−0.61pp** and only **45.7%** of
  picks beat their benchmark. The positive mean is a right tail, not a typical trade.
- **ETF**: +0.02pp, t = −0.62. **No measurable edge**; the median pick (−0.17pp) is negative.
- **CRYPTO**: picks return +0.20% on average while simply holding BTC over the same windows returned
  **+1.00%**. That is **−0.795pp per pick**, t = **−3.65**. The crypto book is a statistically
  significant way to underperform its own benchmark.

None of the three classes shows a positive excess that survives its own t-statistic.

---

## 2. Why the crypto number is smaller than in the previous run (−1.29pp → −0.795pp)

Not an improvement. **Coverage changed.** The previous run could only score windows of at least one
full trading day, so 20-minute scalps were excluded as `window_collapsed`. Adding an hourly
benchmark fallback brought **852 sub-day picks** back into the sample:

| Class | Sub-day picks recovered | Their mean excess | Multi-day picks only | All picks (this run) |
|---|---:|---:|---:|---:|
| EQUITY | 21 of 674 | +0.215pp | +0.238pp | +0.238pp |
| ETF | 23 of 498 | **−0.833pp** | +0.064pp | +0.023pp |
| CRYPTO | 808 of 1,825 | −0.173pp | **−1.290pp** | −0.795pp |

The multi-day crypto subset reproduces the previously published **−1.290pp exactly**, which is the
consistency check that matters: the method did not drift, only its coverage widened. The 808
recovered crypto picks are *less bad* than the multi-day ones, so adding them **dilutes** the class
mean toward zero. Reporting −0.795pp without this table would look like the book improved. It did not.

---

## 3. Where the crypto shortfall actually comes from

54 crypto strategies, **−1,451.6pp** cumulative excess. It is not spread evenly — it is concentrated
in a handful of rules:

| Strategy | Picks | Windows | Mean excess | t (clustered) | Share of shortfall |
|---|---:|---:|---:|---:|---:|
| MomentumEMA | 73 | 37 | **−11.56pp** | **−7.84** | **58.2%** |
| clone_hl_copy_lb_None | 17 | 2 | −17.65pp | n/a | 20.7% |
| hs_Auros_66M | 8 | 1 | −17.93pp | n/a | 9.9% |
| clone_hl_copy_PensionFund_24M | 8 | 2 | −11.91pp | n/a | 6.6% |
| st_fear_greed_contrarian (Revival) | 3 | 1 | −18.04pp | n/a | 3.7% |
| hs_ABC_41M | 3 | 1 | −18.00pp | n/a | 3.7% |
| luxalgo_confluence | 1,173 | 579 | −0.03pp | −1.89 | 2.6% |

**The top six account for more than the entire shortfall** (their total is −1,491.0pp against a class
total of −1,451.6pp). The other 48 strategies net **+39.4pp** between them — i.e. the crypto book
*excluding* these six is roughly flat, not losing.

**Only `MomentumEMA` is both large and measurable.** It is 58.2% of the damage, has 37 independent
windows, and t = −7.84. Its excess win rate is **4.1%** — it beats BTC almost never, and its −11.56pp
mean is driven by the size of the misses rather than their frequency. This is the one rule whose
crypto allocation should be stopped on evidence.

The `clone_hl_*` and `hs_*` rows are **unmeasurable**, not proven bad: `clone_hl_copy_lb_None`'s
−17.65pp rests on **2 windows** (17 picks that are clones of the same two days), and `hs_Auros_66M`
on **1**. A t-statistic is not reported below 5 windows for exactly this reason — an earlier version of
this tool printed t = **−63.47** for a 2-window group, which is what two similarly bad days look like,
not an edge.

**Bulk is not the problem.** `luxalgo_confluence` is 64% of all crypto picks (1,173 of 1,825) yet
contributes 2.6% of the shortfall, at −0.03pp per pick.

---

## 4. Crypto strategies that are (weakly) positive

Six crypto rules show positive mean excess on at least 8 independent windows. **None is significant**,
and this is the honest way to report them — as candidates for a forward clock, not as edges:

| Strategy | Windows | Mean excess | t (clustered) |
|---|---:|---:|---:|
| funding-rate-reversal | 14 | +0.95pp | 0.16 |
| orderbook-imbalance | 14 | +0.21pp | 0.27 |
| crypto_liquidity_wick_reversal_v1 | 43 | +0.16pp | 0.61 |
| strong consensus (alpha_engine, quan_engine) | 43 | +0.13pp | 0.73 |
| momentum_breakout | 47 | +0.11pp | 0.32 |
| multi_period_rsi_confluence_eth | 25 | +0.08pp | 0.24 |

The leading candidate for the equity side is `vwap-reversion-scout` (+1.96pp on 25 windows,
t = 1.99), which is now on a pre-registered forward clock — see [`FORWARD_TEST.md`](FORWARD_TEST.md).

---

## 5. Method

```text
pick_return    = exit/entry - 1        (long)
               = entry/exit - 1        (short)      # the dashboard's own convention
bench_return   = last close on/before entry  ->  last close on/before exit
excess_pp      = pick_return - bench_return         # percentage points
benchmark      = EQUITY -> SPY, ETF -> SPY, CRYPTO -> BTC-USD
```

Why the class beta and not a peer strategy: a peer comparison answers "is this rule better than that
rule", and the question here is "did the pick beat simply owning the exposure". A SHORT that profits
while SPY rises has **positive** excess, which is the point.

**Sub-day windows.** If entry and exit resolve to the same trading day there is no daily benchmark
window, and the pick falls back to **Yahoo 60-minute bars** (last bar at or before each timestamp,
requiring strictly increasing timestamps). 852 picks were recovered this way. Anything still
unseparable — 204 picks — is excluded as `window_collapsed` and **never scored as zero excess**.

**Independence.** Picks closed on the same pair of days share one market move. Every reported t is
therefore computed over `(entry_day, exit_day)` windows, not over picks. The naive per-pick t is shown
beside it to make the overstatement visible: ETF's naive t is **+0.21** while its clustered t is
**−0.62** — the same data, opposite sign. Reporting only the naive figure would have claimed an ETF
edge that does not exist. Below 5 windows no t is reported at all.

**Exclusions** (all counted, none silently dropped): benchmark window collapsed 204, ledger price and
`pnl_pct` disagree by more than 0.5pp 49, missing or non-positive price 9, unparseable dates 4.

---

## 6. Coverage

| | Count |
|---|---:|
| Scored | **2,997** of 3,263 closed EQUITY/ETF/CRYPTO picks (91.8%) |
| — daily benchmark | 2,145 |
| — hourly benchmark | 852 |
| Excluded | 266 (204 window collapsed, 49 pnl mismatch, 9 no price, 4 no dates) |

---

## 7. Limits — what this number is not

- **Not a portfolio return.** Trades overlap with no capital constraint, so summing excess is not what
  an account would have earned. These are per-trade statistics.
- **Benchmark, not risk-adjusted peer.** Excess vs SPY/BTC says nothing about whether the pick used
  more or less risk to get there.
- **Short-sample rules stay unmeasured.** Several crypto rows have 1–2 windows after clustering; they
  are named above as unmeasurable rather than ranked.
- **Signal timestamps are assumed to be about fill time.** The ledger stores `timestamp`/`entry_time`;
  a pick priced well away from where the market traded then would distort its own excess. The
  `pnl_mismatch` filter (49 picks) catches the worst of this, not all of it.
- **Hourly bars are unadjusted.** Correct for a sub-day difference from a single series; irrelevant to
  multi-day picks, which use adjusted daily closes.
