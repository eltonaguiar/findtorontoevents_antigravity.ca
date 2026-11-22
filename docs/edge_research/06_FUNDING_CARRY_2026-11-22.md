# 06 — Funding-rate carry: delta-neutral long-spot / short-perp

**Date:** 2026-11-22
**Programme items:** 9 (build + test), 10 (metrics + break-even), 30 (basis at 4h), 47 (2× cost stress)
**Tool:** [`tools/funding_carry_backtest.py`](../../tools/funding_carry_backtest.py)
**Structured output:** [`reports/funding_carry_20261122.json`](../../reports/funding_carry_20261122.json)
(1× cost), [`reports/funding_carry_20261122_2x.json`](../../reports/funding_carry_20261122_2x.json) (2× cost)
**Raw pulls:** `reports/funding_carry_raw/` (funding + 4h perp/spot klines per symbol)
**Reproduce:** `python3 tools/funding_carry_backtest.py --cost-mult 1.0` (and `--cost-mult 2.0`)

---

## 0. Pre-declared rule (written BEFORE the run)

This section was written before the backtest was executed and is not edited afterwards.
Every parameter below was fixed in advance; nothing is tuned to the result.

### Position

Delta-neutral pair, **equal notional** at entry: **long spot**, **short USDT-M perpetual**,
same asset, same exchange (Binance). The directional bet is removed by construction: a price
move up or down hits both legs equally, so PnL is funding received, plus the change in the
perp–spot basis, minus fees.

### Symbols (5, chosen by liquidity, not by result)

`BTCUSDT, ETHUSDT, SOLUSDT, BNBUSDT, XRPUSDT`

Justification fixed in advance: these are the five Binance assets that appear in the measured
spot order-book table of [`05_REAL_COST_MEASUREMENT_2026-11-22.md`](05_REAL_COST_MEASUREMENT_2026-11-22.md)
(so their cost is measured, not assumed), and all five have deep USDT-M perp markets.

### Window

**All available funding history** published by Binance for each symbol, from the first record
through the run time (2026-11-22T12:00Z). Using everything avoids any window-selection choice.
The **trailing 12 months** (2025-11-22 → 2026-11-22) is reported as a sub-window for the recent
regime. Actual achieved range per symbol is reported in §2.

### Holding periods (fixed grid)

`H ∈ {1, 3, 7, 14, 30, 90}` days, plus the continuous **always-on** hold over the whole window.
Funding settles every 8h (3 intervals/day); a hold of H days spans `3H` intervals.

### Entry conditions (two, both pre-declared)

- **A — always-on:** in the position continuously for the whole window. Measures the
  *unconditional* carry premium.
- **B — positive-trailing:** in the position only while the trailing 24h funding sum
  (3 settled intervals) is **> 0**; exit when it is ≤ 0. The decision at interval *i* uses
  funding up to and including interval *i* only (no look-ahead), and the position is held for
  the following interval.

### Arithmetic (fixed in advance)

Per interval, with perp quantity `q` and perp price `Pp`:

1. **Funding** `= Σ f_i × q × Pp_i` over intervals held, for the short leg. Positive `f` pays the
   short; negative `f` charges it. Sign is kept, never floored at zero.
2. **Basis** `= N × (b_entry − b_exit)` where `b = (Pp − Ps)/Ps`. Entering with the perp rich
   (`b > 0`) and unwinding at a lower basis is a gain; a widening basis is a loss. This is the
   exact mark-to-market of the two legs (derivation: short perp PnL `−(Pp'−Pp)q` plus long spot
   PnL `+(Ps'−Ps)q` `= q[(Pp−Ps) − (Pp'−Ps')] = N(b_entry − b_exit)`, to first order).
3. **Cost:** opening both legs and closing both legs = **four taker fills**. Per leg round trip
   = 20bp taker fee (10bp/side, measured) + measured spot round-trip spread at **$10k** notional
   from [`reports/cost_measurement_20261122.json`](../../reports/cost_measurement_20261122.json).
   Pair round trip = 2 × that. The perp spread is **assumed equal to the spot spread** (perp books
   were not measured) — flagged as an assumption; it is < 2bp for majors and does not move the
   verdict, which is dominated by the 40bp of fees.
   **Reference size: $10k notional.** $100k is reported as sensitivity.
4. **No rebalancing** of the pair as the legs drift. Documented limitation, not a tuned choice.

### Metrics (all pre-declared)

Gross funding APR, net APR after cost amortised over the actual holding period, funding-stream
volatility (annualised), Sharpe (`mean/sd × √(3·365)`), max drawdown of the cumulative curve,
the funding-rate distribution (mean, median, % positive, worst), the **break-even holding period**
(cost ÷ funding earned per day, reported at the mean and the median funding rate and as the
empirical smallest H on the grid with positive mean net), and the 4h basis statistics.

### Verdict thresholds (pre-declared)

- **INVESTABLE** — net APR at 1× cost > 0 *and* > the risk-free-ish 0 hurdle across the always-on
  hold, with break-even hold < the median time a positive-funding regime persists.
- **MARGINAL** — net APR > 0 at 1× but ≤ 0 at 2×, or net APR > 0 only for H ≥ 30 days.
- **KILL** — net APR ≤ 0 at 1× cost for every pre-declared H.

### Item 47 (2× cost stress)

The entire analysis is re-run at **2× the measured cost** (PROVEN_T2 standing requirement).
Both the 1× and 2× tables are reported.

---

## 1. Data source and endpoints

Every number comes from these endpoints, pulled 2026-11-22 and cached under
`reports/funding_carry_raw/` (funding `<SYM>.json`, perp/spot `klines_4h_<SYM>_{perp,spot}.json`):

| Data | Endpoint | Rows |
|---|---|---|
| Funding history | `GET https://fapi.binance.com/fapi/v1/fundingRate?symbol=<SYM>&startTime=<ms>&limit=500` | 6,858–7,891 per symbol |
| Perp 4h klines | `GET https://fapi.binance.com/fapi/v1/klines?symbol=<SYM>&interval=4h` | 13,563–15,781 |
| Spot 4h klines | `GET https://api.binance.com/api/v3/klines?symbol=<PAIR>&interval=4h` | same window |

**Achieved date ranges** (funding, 8h intervals, ~100% continuous):

| Symbol | Range | Years | Intervals |
|---|---|---|---|
| BTCUSDT | 2019-09-10 → 2026-11-22 | 7.2 | 7,891 |
| ETHUSDT | 2019-11-27 → 2026-11-22 | 7.0 | 7,657 |
| SOLUSDT | 2020-09-14 → 2026-11-22 | 6.2 | 6,858 |
| BNBUSDT | 2020-02-10 → 2026-11-22 | 6.8 | 7,432 |
| XRPUSDT | 2020-01-06 → 2026-11-22 | 6.9 | 7,537 |

**The 12-month minimum is exceeded by 6× on every symbol.** No data was geo-blocked;
nothing is BLOCKED.

**Two API behaviours found and handled** (not assumptions, observed):
- The endpoint caps a page at **500 rows** whatever `limit` is requested, so history must be
  paginated on `startTime`. The first pull silently returned only the latest 500 rows (~5
  months) because `startTime=0` is treated as absent. Fixed and re-pulled.
- `markPrice` is **blank before 2023-11** in Binance's own history. It is unused here (perp
  prices come from klines); the funding *rate* is present for every row.

## 2. Cost figure and its provenance

Pair round trip = **four taker fills** = 2 legs × (open + close).

| Component | Value | Source |
|---|---|---|
| Taker fee per side | 10 bp | [`reports/cost_measurement_20261122.json`](../../reports/cost_measurement_20261122.json) `taker_fee_bp_per_side.binance` |
| Leg round trip (fee) | 20 bp | 2 × 10 bp |
| Leg round trip (all-in incl. spread, $10k) | **22.762 bp** | same file, `all_in_round_trip_bp` median across Binance spot symbols |
| **Pair round trip (1×)** | **45.524 bp** | 2 × 22.762 |
| **Pair round trip (2× stress, item 47)** | **91.048 bp** | × 2 |

At **$100k** notional the pair cost is 58.398 bp (the spread widens, the fee is unchanged);
at $100k the net APRs below fall by ~1.6–1.7 percentage points. The pre-declared reference
size is $10k.

**Assumption, flagged:** the perp spread is assumed equal to the measured spot spread
(perp books were not measured). For majors this is < 2 bp and cannot change the verdict,
which is driven by the 40 bp of fees.

## 3. Funding-rate distribution and gross funding APR

| Symbol | Mean 8h | Median 8h | % positive | Worst 8h | Gross funding APR | Last-12mo APR | Last-12mo % pos |
|---|---|---|---|---|---|---|---|
| BTCUSDT | +1.042 bp | +0.928 bp | 85.8% | −30.00 bp | **+11.41%** | +3.44% | 76.9% |
| ETHUSDT | +1.238 bp | +0.987 bp | 86.1% | −35.63 bp | **+13.55%** | +2.34% | 72.1% |
| SOLUSDT | +0.026 bp | +0.812 bp | 71.4% | −200.00 bp | **+0.28%** | −0.11% | 56.5% |
| BNBUSDT | +0.002 bp | 0.000 bp | 26.8% | −58.44 bp | **+0.02%** | +2.72% | 43.7% |
| XRPUSDT | +1.312 bp | +1.000 bp | 79.6% | −50.25 bp | **+14.37%** | +0.38% | 54.8% |
| **Equal-weight mean** | | | 70.0% | | **+7.93%** | | |

Three things this table says that the mean hides:
- **The carry premium is real but decaying.** BTC funding averaged +2.80 bp/8h in 2021 and
  **+0.30 bp/8h in 2026**; ETH +3.43 → +0.20. The last-12mo APR is a third to a tenth of the
  full-window APR. The full-window number is a historical average, not what is on offer now.
- **BNB is structurally different:** funding is positive only 26.8% of the time and has been
  net *negative* most intervals since 2022. Holding the short perp there is a cost, not a carry.
- **The tail is fat.** SOL's worst interval is −200 bp (the −2%/8h floor → −219%/yr if it persisted).
  A strategy positive on average with a tail like that is not automatically safe.

Whole-window, funding-only versus marked-to-market (funding + basis change, no entry cost),
so you can see whether basis moves dominate:

| Symbol | Funding-only APR | MTM APR | Funding Sharpe | MTM Sharpe | MTM maxDD |
|---|---|---|---|---|---|
| BTCUSDT | +11.41% | +11.42% | +16.91 | +4.30 | −3.32% |
| ETHUSDT | +13.55% | +13.57% | +15.29 | +5.95 | −2.48% |
| SOLUSDT | +0.28% | +0.31% | +0.10 | +0.03 | −54.79% |
| BNBUSDT | +0.02% | +0.08% | +0.02 | +0.02 | −30.91% |
| XRPUSDT | +14.37% | +14.50% | +12.30 | +3.74 | −4.57% |

The funding-only Sharpe (+12 to +17) is an artefact of funding being a near-constant positive
drip with low variance; it is **not** a tradable Sharpe. The marked-to-market Sharpe (+3.7 to
+6.0) is the honest one, and the max drawdowns (up to −54.8% on SOL) are what a real position
would have felt. Neither includes the entry/exit cost below.

## 4. The central result: net APR by holding period (items 10, 47)

Gross funding APR is **cost-independent** (+7.93% at every H — the same funding, just amortised
over different holds). Only the net changes. Non-overlapping holds, equal-weight across symbols.

| Hold H | Gross APR | Net APR 1× (45.5 bp) | Sharpe 1× | maxDD 1× | Net APR 2× (91.0 bp) | Sharpe 2× | maxDD 2× |
|---|---|---|---|---|---|---|---|
| 1 day | +7.93% | **−158.07%** | −61.2 | −1077% | **−324.23%** | −126.1 | −2211% |
| 3 days | +7.93% | **−47.82%** | −14.7 | −325% | **−103.21%** | −32.5 | −702% |
| 7 days | +7.94% | **−15.60%** | −3.4 | −117% | **−39.34%** | −9.2 | −267% |
| 14 days | +7.94% | **−3.73%** | −0.4 | −52% | **−15.60%** | −2.6 | −116% |
| 30 days | +7.95% | **+2.42%** | +0.6 | −24% | **−3.12%** | −0.3 | −48% |
| 90 days | +8.01% | **+6.24%** | +0.7 | −17% | **+4.40%** | +0.6 | −20% |

**Break-even holding period** (the decisive number):

- At the mean funding rate: **≈17 days** (BTC 14.6, ETH 12.3, XRP 11.6, SOL 588, BNB 8,006 days).
- At the **median** funding rate: **≈16.4 days** aggregate.
- Empirically, the first H on the grid with positive net is **30 days** at 1× and **90 days** at 2×.

Per-symbol net APR (1× / 2×) shows the whole picture is carried by BTC, ETH and XRP; SOL and
BNB are negative at every H:

| Symbol | H=7d | H=30d | H=90d |
|---|---|---|---|
| BTCUSDT | −12.2 / −35.9% | +5.9 / +0.4% | +9.6 / +7.8% |
| ETHUSDT | −10.1 / −33.8% | +7.8 / +2.3% | +11.8 / +10.0% |
| XRPUSDT | −8.8 / −32.5% | +9.1 / +3.5% | +13.0 / +11.2% |
| SOLUSDT | −23.3 / −47.0% | −5.4 / −11.0% | −1.5 / −3.4% |
| BNBUSDT | −23.6 / −47.4% | −5.3 / −10.9% | −1.7 / −3.6% |

**Entry condition B (enter while trailing 24h funding > 0) is worse than always-on**, and this
is the most damning result:

| Symbol | Episodes | Median length | Gross/episode | Net/episode | % episodes profitable |
|---|---|---|---|---|---|
| BTCUSDT | 214 | 2.3 d | +0.391% | −0.057% | 11.7% |
| ETHUSDT | 219 | 2.0 d | +0.439% | −0.014% | 8.7% |
| SOLUSDT | 315 | 1.3 d | +0.193% | −0.236% | 6.3% |
| BNBUSDT | 204 | 2.3 d | +0.261% | −0.165% | 14.7% |
| XRPUSDT | 301 | 1.7 d | +0.345% | −0.102% | 7.6% |

The median positive-funding episode lasts **~2 days** and the break-even hold is **~17 days**.
So a signal that tells you "funding is positive right now" is telling you to enter an episode that
is, typically, **an eighth of the length you need to break even.** The total gross across all
episodes is strongly positive (+84% to +104%) but the total net is **negative on every symbol**
(−3% to −74%) because each entry pays 45 bp for ~2 days of carry. This is the clean statement of
why the premium is not harvestable with taker entries: **you would need to hold ~8× longer than
the regime persists.**

## 5. Basis at 4h resolution (item 30)

Perp−spot basis, 4h bars, over the same window:

| Symbol | n 4h bars | Mean | Median | SD | p1 | p99 | Min | Max |
|---|---|---|---|---|---|---|---|---|
| BTCUSDT | 15,781 | −1.46 bp | −3.77 bp | 6.82 | −8.59 | +16.10 | −185.8 | +332.0 |
| ETHUSDT | 15,313 | −0.95 bp | −3.72 bp | 7.05 | −8.80 | +20.03 | −252.2 | +139.4 |
| SOLUSDT | 13,563 | −3.10 bp | −4.15 bp | 33.54 | −27.28 | +27.34 | −1972.6 | +191.8 |
| BNBUSDT | 14,863 | +0.34 bp | +0.84 bp | 9.18 | −23.12 | +23.20 | −135.2 | +177.4 |
| XRPUSDT | 15,073 | −1.11 bp | −3.90 bp | 11.17 | −13.55 | +25.59 | −668.9 | +250.0 |

**Are basis excursions material relative to funding income? Mostly no, but not never.**
- Typical basis (median, SD) is **single-digit bp**, against a funding income of ~7% APR =
  ~1.9 bp/8h ≈ 5.7 bp/day on BTC. Comparable per interval, but the basis is mean-reverting
  rather than a sustained cost, so it does not compound against you the way fees do.
- Per hold, the **dispersion of basis change is 3–13% of the dispersion of funding income**
  (H=7d: 0.13×; H=90d: 0.03×), so over the horizons that matter basis is a minor noise term,
  not the thing that decides the strategy.
- The **tails do matter**: SOL's worst basis excursion is −1,973 bp (≈ −20%). A single such move
  on a 30-day hold wipes out multiple years of SOL funding. That is why SOL's MTM max drawdown is
  −54.8% while its funding max drawdown is −43.4%.
- **Direction of the residual:** the basis is on average slightly negative (perp below spot) for
  BTC/ETH/XRP, so entering long-spot/short-perp and unwinding at a *more* negative basis is, on
  average, a small *gain*, which is why the H=90 basis term is +0.02% rather than a drag.

## 6. Verdict

**MARGINAL, and only at long holds with taker fills.** The decisive number is the ratio
**break-even hold ≈ 17 days vs median positive-funding episode ≈ 2 days (≈ 8×)**.

Against the pre-declared thresholds:
- Not **KILL**: net APR is positive at 1× cost for H=30d (+2.42%) and H=90d (+6.24%).
- Not **INVESTABLE**: net APR is negative at 2× cost for H=30d (−3.12%), the break-even hold
  (~17 d) exceeds the typical regime length (~2 d), and the last-12mo gross APR (+1–3% on BTC/ETH)
  is a third of the full-window figure the positive net rests on.
- So **MARGINAL** by the pre-declared definition (positive at 1×, not at 2× for the shorter
  positive hold).

What would move it, stated without tuning the answer:
- **Maker fills.** The 40 bp of taker fees is the entire problem. Posting both legs as maker
  (or using a spot-futures margin account that nets the two legs) cuts the cost several-fold and
  the break-even hold proportionally. The strategy is a *cost* question, not a signal question.
- **Persistent high-funding regimes**, not "funding is positive now". The profitable window needs
  funding to stay elevated for weeks; the entry rule tested (trailing 24h > 0) does not identify
  those, and nothing here shows how to.

**Blunt summary:** the carry premium is real (BTC/ETH ~ +11–14% APR gross over 7 years, decaying
to ~2–3% in the last 12 months), but with taker entries the break-even hold is ~17 days while
positive funding typically persists ~2 days, so the delta-neutral carry is **not investable as
specified**; it needs maker fills or a regime filter that has not been demonstrated.

**Caveats:** no rebalancing of the pair as legs drift (the delta-neutrality is only exact at
entry); perp spread assumed = spot spread; funding-mean over a multi-year window is regime-
dependent and the recent regime is much weaker than the average; Sharpe at H≥30 is from few
non-overlapping trades (25–87 per symbol).
