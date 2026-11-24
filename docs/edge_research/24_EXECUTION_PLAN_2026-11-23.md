# 24 — Execution plan, 2026-11-23 window: twelve asset classes, eight fields each, one cross-class ranked list

**Window:** 01:50Z–05:50Z, 2026-11-23.
**Ladder:** 02:05Z PLAN → 03:50Z DRAFT → 05:50Z FINAL. **No extensions.**
**This document is the PLAN rung.** The DRAFT rung fills the gaps marked `UNMEASURED` *only where a file
already on disk can fill them*; the FINAL rung freezes the ranked list.

**Nothing in this plan claims a class is investable.** The expected output of the window is a ranked list
of the least-refuted candidates, **or an empty list**. An empty list is a permitted and honest result.

**Read this first:** every figure below is either quoted from an artifact with its source, or written
`UNMEASURED` with the reason. No number in this document is computed for the first time here, except
arithmetic that is shown inline as `a × b = c` on two supplied figures.

---

## 0. How to read this document

### 0.1 Conventions

- **`gate`** = the metric is a PASS/FAIL gate. **`info`** = INFORMATIONAL, reported but never decisive.
- **`UNMEASURED`** = no measurement exists on disk. The reason is always given; it is never a zero.
- **Trial count** = the number of strategy variants declared for the class *before* any result is seen.
  Where the historical grid size is not recorded, the field says `UNMEASURED` rather than guessing.
- **ETA** = minutes of *authoring and verification effort* to complete that class's DRAFT section. It is
  **not** new research. A class whose strategy verdict is already frozen (dead, or `NOT_INVESTABLE`)
  carries **no ETA**: its section is a fixed tombstone written now, and nothing further is spent on it.
- **Committed capital** = deployed notional + cash collateral required to hold it (see the Overall section).
- **Cost** = round-trip (RT) unless a per-side figure is stated. All costs are **upper bounds** from
  1-minute bar ranges, **not** NBBO. `COMMISSION_UNKNOWN` for every class.

### 0.2 Class index

| # | Class | Strategy status in the programme record | ETA (min) |
|---|---|---|---|
| 1 | EQUITY | dead — value (HML), PEAD post-2006, breakout | 0 |
| 2 | ETF | no candidate ever specified; cost measured | 15 |
| 3 | INDEX | alias of ETF; SPY 200-day trend `NOT_INVESTABLE` | 0 |
| 4 | BOND / MUTUAL_FUND | bond momentum dead; mutual-fund cost unmeasured | 15 |
| 5 | COMMODITY / FUTURES | dead — momentum (0 bp/side) and selection; carry `BLOCKED_MISSING_DATA` | 0 |
| 6 | FOREX | dead — momentum, and mean-reversion at measured cost | 0 |
| 7 | CRYPTO | carry dead; intraday mean-rev killed; one observe pod live | 25 |
| 8 | MEME | no candidate; one quotable cost (DOGE) | 10 |
| 9 | PENNY_STOCK | no instrument, no cost | 10 |
| 10 | SPORTS | nothing measured at all | 15 |
| 11 | FUNDING-BASIS CARRY | `NOT_INVESTABLE` (opportunity frequency) | 0 |
| 12 | FX CARRY | `NOT_INVESTABLE` (hurdle, break-even 468.4739 bp) | 0 |

**ETA arithmetic.** 15 (ETF) + 15 (BOND/MUTUAL_FUND) + 25 (CRYPTO) + 10 (MEME) + 10 (PENNY_STOCK) +
15 (SPORTS) = **90 min**, plus **10 min** to recompute the cross-class ranking at the end = **100 min**.
Posted at the 02:05Z PLAN rung, 100 min ends at **03:45Z**, five minutes inside the 03:50Z DRAFT rung; the
05:50Z FINAL rung then has 120 min of review slack. Started from now (~00:50Z) the same 100 min ends at
~02:30Z. Both fit.

---

## 1. EQUITY

**Verdict status: DEAD for this window.** Three separate equity families are dead and are **not re-opened**:
HML/value (**+0.11%/yr gross**), large-cap PEAD post-2006, and equity breakout (null **10.2nd** percentile at
measured cost vs **≥95 required**). [SRC: operator dead-list, this brief; [`23_DEFINITIVE_ANSWER_2026-11-22.md`](docs/edge_research/23_DEFINITIVE_ANSWER_2026-11-22.md:146)]

- **(a) METHODOLOGY** — technical (cross-sectional signal + breakout) and fundamental (value) were both
  tested. Neither survives cost. Why: the measured RT cost is **12.0749 bp upper bound** (**6.0375 bp/side**,
  Corwin-Schultz 1.5033 bp, 13 symbols, `provenance_self_check PASS`), and the class's own break-evens are
  only **14.5838 bp/side** (equity pod) and **24.5945 bp/side** (breakout). At 12.0749 bp RT, a strategy
  turning over 10×/yr pays `10 × 12.0749 = 120.7 bp/yr`; at 100×/yr it pays `1,207.5 bp/yr` (12.07%).
  [SRC: [`equity_cost_20261122.json`](reports/equity_cost_measurement/equity_cost_20261122.json:1978); [`programme_scoreboard_20261122.json`](reports/programme_scoreboard_20261122.json)]
- **(b) APPROACH** — **backtest only**, and it is closed. SAMPLE WINDOW: mixed and partly unrecorded — the
  breakout published claim covers **2021-04..2026-04** (n=245) while the sweep also reports a **pre-2021
  out-of-sample** segment (break-even 23.91 bp/side there vs 24.5945 all-history); the HML window is in its
  own preregistration. REBALANCE FREQUENCY: `UNMEASURED` for the breakout sweep (1,935 trades; the grid is
  not in the supplied evidence); HML is annual by construction of a value portfolio (preregistration).
  LOOK-AHEAD: `UNMEASURED` for these runs — no execution-lag statement is recorded for the equity breakout
  sweep, and the published PF 1.479 was **unreproduced** (measured ≈1.00).
  [SRC: [`15_PROGRAMME_SCOREBOARD_2026-11-22.md`](docs/edge_research/15_PROGRAMME_SCOREBOARD_2026-11-22.md:34), [`HML_VALUE_TEST_2026-11-22.md`](docs/preregistration/HML_VALUE_TEST_2026-11-22.md:123)]
- **(c) STRATEGIES + TRIAL COUNT** — named in the record: equity breakout (donchian / VT pattern sweep);
  HML value family; 12-1 momentum L/S (multi-asset, 79 symbols, one row); N1 R1 multi-asset momentum,
  R2 sector momentum, R3 SPY 200-day trend (**three** rows, different universes). Variants for the
  breakout sweep and the HML family: `UNMEASURED` (grid size not recorded). **For this window N = 0 new
  variants. This number IS the trial count, declared up front.**
  [SRC: [`block4_n1_low_turnover.md`](docs/edge_research/block4_n1_low_turnover.md:56)]
- **(d) METRICS** — Sharpe (gate, `UNMEASURED`) · Sortino (info, `UNMEASURED`) · max drawdown (gate,
  `UNMEASURED` for equity breakout) · profit factor (gate, **0.9917 @25 bp/side**, FAIL) · **deflated Sharpe
  with N (gate, N=0 this window → not applicable; historical N `UNMEASURED`, so DSR is `UNMEASURED`)** ·
  **PBO via CSCV (gate, `UNMEASURED`)** · walk-forward efficiency (gate, `UNMEASURED`) · information ratio
  vs matched benchmark (gate, `UNMEASURED`; excess vs SPY for the N1 rows is negative) · **2x-cost survival
  (gate, FAIL: the class already fails at 1× measured cost)** · turnover per year (info, `UNMEASURED`) ·
  capacity at intended size (info, `UNMEASURED` — never tested) · CI on net return (gate, excess-CAGR CI
  **[−46.32%, +32.31%]** at measured cost; alpha CI-LB −0.285%).
- **(e) DATA** — yfinance 1-min `period=5d` plus cached CSVs **2021-11-22..2026-11-19**. Point-in-time: **NO**
  (every list is a today's-constituents list). Lag: none established. `COMMISSION_UNKNOWN`.
  [SRC: [`10_SURVIVORSHIP_AUDIT_2026-11-22.md`](docs/edge_research/10_SURVIVORSHIP_AUDIT_2026-11-22.md:18)]
- **(f) EXECUTION STYLE** — **no top pick: nothing survives.** If one existed it would be **ENTRY WITH TP/SL**
  (the signals are short-horizon), and the cost consequence would be `turnover/yr × 12.0749 bp` RT
  (commission excluded, `COMMISSION_UNKNOWN`). A buy-and-hold of one round trip per year costs 12.0749 bp/yr.
- **VEHICLE COMPARISON (mutual fund vs index fund vs ETF vs direct holding)** — at measured RT cost:
  **ETF 6.7122 bp** < **INDEX proxy 8.0325 bp** < **direct equity 12.0749 bp (upper bound)**. **Mutual fund:
  `UNMEASURED`** — no expense ratio or spread for any mutual fund exists in this programme, so it cannot be
  ranked, and it is not assumed to be either cheap or expensive.
- **(g) KILL RULE** (frozen, numeric, before any result) — reuse HML's: kill if OOS annualised net return on
  committed capital **≤ 4.3%**, or one-sided 95% **upper bound ≤ 4.3%**; the binding bar is **4.32%**
  ([`tools/capacity_model.py:49`](tools/capacity_model.py:49)). Also reuse the pod's forward rule: **CI-LB ≤ 0
  at 2× slippage at day 30 or day 60 → pod ends**; at n ≥ 100 kill if **net PF CI-LB ≤ 1.0**, **IR < 0.5** vs a
  matched BTC/ETH benchmark, or split-half unstable. Breakout additionally required null **≥95**.
  [SRC: [`HML_VALUE_TEST_2026-11-22.md`](docs/preregistration/HML_VALUE_TEST_2026-11-22.md:123), [`12_OBSERVE_TO_PRE_REGISTERED_DECISION_MEMO_2026-11-22.md`](docs/edge_research/12_OBSERVE_TO_PRE_REGISTERED_DECISION_MEMO_2026-11-22.md:113)]
- **(h) ETA** — **0 min. Dead, not re-opened, no ETA.** Re-opening is unjustified because the family fails at
  zero or near-zero cost (breakout PF 0.9917 at 25 bp/side, PF 1.2865 even at 0 bp/side), so no fill
  improvement can flip the sign, and value is +0.11%/yr gross before cost against a 4.32% hurdle.

---

## 2. ETF

**Verdict status: no strategy was ever specified for this class.** Cost is measured; that is all that exists.

- **(a) METHODOLOGY** — `UNMEASURED`: an ETF is a wrapper, so the methodology is the underlying's, and no ETF
  strategy has been specified in this programme. The only measured fact is cost: **6.7122 bp RT** median over
  14 names (SHY 0.6144 … SOXX 22.9049). Cost is what constrains the choice: at 6.7122 bp RT a vehicle held
  for a year pays 6.7122 bp/yr, and a vehicle traded monthly pays `12 × 6.7122 = 80.5 bp/yr`.
  [SRC: [`class_cost_20261122.json`](reports/equity_cost_measurement/class_cost_20261122.json)]
- **(b) APPROACH** — **backtest only**, and no backtest exists. SAMPLE WINDOW: `UNMEASURED` (none specified).
  REBALANCE FREQUENCY: `UNMEASURED`. LOOK-AHEAD AVOIDED: `UNMEASURED` — no rule exists to lag.
- **(c) STRATEGIES + TRIAL COUNT** — none named. **N = 0. This number IS the trial count, declared up front.**
- **(d) METRICS** — Sharpe (gate, `UNMEASURED`) · Sortino (info, `UNMEASURED`) · max drawdown (gate,
  `UNMEASURED`) · profit factor (gate, `UNMEASURED`) · **deflated Sharpe with N (gate, N=0 → not applicable;
  `UNMEASURED`)** · **PBO via CSCV (gate, `UNMEASURED`)** · walk-forward efficiency (gate, `UNMEASURED`) ·
  information ratio vs matched benchmark (gate, `UNMEASURED`) · **2x-cost survival (gate, `UNMEASURED`:
  2 × 6.7122 = 13.4244 bp RT is the stress number, but there is no strategy to survive it)** · turnover per
  year (info, `UNMEASURED`) · capacity at intended size (info, `UNMEASURED`) · CI on net return (gate,
  `UNMEASURED`).
- **(e) DATA** — yfinance 1-min `period=5d` + cached CSVs 2021-11-22..2026-11-19 (cost sample: 2026-11-16..20).
  Point-in-time: **NO**. Lag: none established. `COMMISSION_UNKNOWN`.
- **(f) EXECUTION STYLE** — **no top pick.** The only measured-cost action available is **BUY AND HOLD**:
  one round trip per year at **6.7122 bp** (`turnover 1/yr × 6.7122 bp`).
- **VEHICLE COMPARISON** — **ETF 6.7122 bp** (measured) vs **INDEX FUND**: in this programme the index proxy
  *is* an ETF sample (SPY/QQQ/IWM/DIA), measured at **8.0325 bp**, so "index fund" and "ETF" collapse to the
  same measurement; **direct holding** of the constituents costs **12.0749 bp** (upper bound); **mutual fund
  `UNMEASURED`**.
- **(g) KILL RULE** (frozen) — a candidate is killed (never ranked) unless its one-sided 95% **lower bound** on
  net return on committed capital is **> 4.32%** *after* 2× measured cost (**13.4244 bp RT**). With no
  candidate, the class is recorded and not ranked.
- **(h) ETA** — **15 min**: verify the ETF cost artifact, write the vehicle matrix, and record the absence of
  any ETF candidate in the 14-row set.

---

## 3. INDEX

**Verdict status: alias of ETF.** Doc 23 records INDEX as an alias of the ETF class. Its one tested strategy,
N1 R3 (SPY 200-day trend), is **`NOT_INVESTABLE`** (null 53.4, excess vs SPY −6.8 pp).

- **(a) METHODOLOGY** — technical (trend following, 200-day). It does not suit the class at this cost: the
  200-day rule's excess is **−6.8 pp** against SPY before any cost is charged, and RT cost is **8.0325 bp**
  over 4 names (SPY 8.3139, QQQ 12.0749, IWM 7.7512, DIA 5.5896). [SRC: [`class_cost_20261122.json`](reports/equity_cost_measurement/class_cost_20261122.json)]
- **(b) APPROACH** — **backtest only**. SAMPLE WINDOW: `UNMEASURED` in the supplied evidence. REBALANCE
  FREQUENCY: daily signal on a 200-day average (the rule's nature), trades `UNMEASURED`. LOOK-AHEAD:
  `UNMEASURED`; a 200-day average on a close-to-close series is only lag-safe if the signal executes next
  bar, and no such statement is recorded.
- **(c) STRATEGIES + TRIAL COUNT** — N1 R3, SPY 200-day trend: **1** variant. **This number IS the trial
  count, declared up front.** No new variant this window (N = 0 new).
- **(d) METRICS** — Sharpe (gate, `UNMEASURED`) · Sortino (info, `UNMEASURED`) · max drawdown (gate,
  `UNMEASURED`) · profit factor (gate, `UNMEASURED`) · **deflated Sharpe with N (gate, N=1 → `UNMEASURED`)** ·
  **PBO via CSCV (gate, `UNMEASURED`)** · walk-forward efficiency (gate, `UNMEASURED`) · information ratio vs
  matched benchmark (gate, **excess vs SPY −6.8 pp**, fails) · **2x-cost survival (gate, `UNMEASURED`;
  2 × 8.0325 = 16.065 bp RT)** · turnover per year (info, `UNMEASURED`) · capacity at intended size (info,
  `UNMEASURED`) · CI on net return (gate, `UNMEASURED`).
- **(e) DATA** — yfinance 1-min + cached CSVs; the index panel is SPY/QQQ/IWM/DIA. Point-in-time: **NO**.
  Lag: `UNMEASURED`. `COMMISSION_UNKNOWN`.
- **(f) EXECUTION STYLE** — **no top pick.** Buy-and-hold at 8.0325 bp RT per year is the measured-cost action.
- **VEHICLE COMPARISON** — **INDEX FUND vs ETF collapse to one measurement** here because the four index proxies
  *are* ETFs (8.0325 bp); **direct holding** of the index is not possible except by replication at 12.0749 bp
  (equity sample); **mutual fund `UNMEASURED`**.
- **(g) KILL RULE** (frozen) — kill if one-sided 95% **LB** on net return on committed capital **≤ 4.32%**, or if
  the null percentile is **< 95** (observed 53.4). [SRC: [`23_DEFINITIVE_ANSWER_2026-11-22.md`](docs/edge_research/23_DEFINITIVE_ANSWER_2026-11-22.md:193)]
- **(h) ETA** — **0 min.** The class has a tested and killed strategy; there is nothing to author beyond this tombstone.

---

## 4. BOND / MUTUAL_FUND

**Verdict status: bond momentum DEAD (break-even 0 bp/side), not re-opened.** Mutual-fund cost is `UNMEASURED`.

- **(a) METHODOLOGY** — technical (momentum) was tested on the bond side and failed at **zero cost**, so the
  methodology question is not decidable from edge: B1 PF 1.312 sits beside Sharpe **−0.550** and maxDD −5.81%
  (10.2% of months in cash, time in market 89.8%), B2 PF 0.743 / Sharpe −1.699, B3 PF 0.737 / Sharpe −1.063.
  Cost cannot discriminate because bond cost is **`UNMEASURED`**.
  [SRC: [`16_COMMODITY_AND_BOND_MOMENTUM_2026-11-22.md`](docs/edge_research/16_COMMODITY_AND_BOND_MOMENTUM_2026-11-22.md:104), [`bond_momentum_20261122.json`](reports/bond_momentum_20261122.json:183)]
- **(b) APPROACH** — **backtest only**. SAMPLE WINDOW: `UNMEASURED` (bond ETF history not stated in the supplied
  evidence). REBALANCE FREQUENCY: `UNMEASURED`. LOOK-AHEAD: `UNMEASURED`.
- **(c) STRATEGIES + TRIAL COUNT** — B1/B2/B3 = **3 variants, counted as ONE row** (one dataset, one artifact,
  one verdict). **This number IS the trial count, declared up front.** New variants this window: 0.
  [SRC: [`16_COMMODITY_AND_BOND_MOMENTUM_2026-11-22.md`](docs/edge_research/16_COMMODITY_AND_BOND_MOMENTUM_2026-11-22.md:47)]
- **(d) METRICS** — Sharpe (gate, **−0.550 / −1.699 / −1.063**, FAIL) · Sortino (info, `UNMEASURED`) · max
  drawdown (gate, **−5.81%** B1, FAIL) · profit factor (gate, **1.312 / 0.743 / 0.737**) · **deflated Sharpe
  with N (gate, N=3, `UNMEASURED`)** · **PBO via CSCV (gate, `UNMEASURED`)** · walk-forward efficiency (gate,
  `UNMEASURED`) · information ratio vs matched benchmark (gate, `UNMEASURED`) · **2x-cost survival (gate,
  FAIL: break-even is 0 bp/side, so it fails at 1× and at 2×)** · turnover per year (info, `UNMEASURED`) ·
  capacity at intended size (info, `UNMEASURED`) · CI on net return (gate, `UNMEASURED`).
- **(e) DATA** — front-month continuous futures and bond ETFs. Point-in-time: **NO**. Lag: `UNMEASURED`.
  `COMMISSION_UNKNOWN`. For a mutual fund: no data at all.
- **(f) EXECUTION STYLE** — **no top pick.** If one existed, bond positions are held, so **BUY AND HOLD** would
  apply; cost consequence is `UNMEASURED turnover × UNMEASURED bond cost` = `UNMEASURED`.
- **VEHICLE COMPARISON** — the only measured number is the **bond ETF**: SHY at **0.6144 bp RT**, the cheapest
  instrument measured anywhere in this programme (low end of the 14-name ETF sample). **Bond mutual fund
  `UNMEASURED`. Bond index fund `UNMEASURED`. Direct bonds `UNMEASURED`.** They cannot be ranked; the ETF is
  the only one with a number, and having a number is not the same as being better.
- **(g) KILL RULE** (frozen) — kill if **Sharpe-vs-rf < 0.5 at 10 bp/side** (the programme's commodity-family
  bar, reused), or net return on committed capital **≤ 4.32%**. Observed Sharpe is negative at 0 bp/side.
  [SRC: [`16_COMMODITY_AND_BOND_MOMENTUM_2026-11-22.md`](docs/edge_research/16_COMMODITY_AND_BOND_MOMENTUM_2026-11-22.md:32)]
- **(h) ETA** — **15 min**, spent on the vehicle matrix only (mutual fund vs index fund vs ETF vs direct
  bonds), **not** on re-opening bond momentum.

---

## 5. COMMODITY / FUTURES

**Verdict status: DEAD, not re-opened.** Commodity momentum (V1/V2/V3, break-even **0 bp/side** on both
criteria) and commodity selection (**−5.57% to −3.57%**) are dead. Term-structure carry is
`BLOCKED_MISSING_DATA` and also gets no time this window.

- **(a) METHODOLOGY** — technical (momentum), tested and failed at zero cost; fundamental (term structure)
  cannot be tested because the curve does not exist on disk. Why it does not suit the class: cost is
  **`UNMEASURED`**, and the strategies that were testable lose money even *free* (V1 PF 0.757, V2 1.114,
  V3 1.074; CAGR −7.13% / +0.47% / −0.67% against 4.32%).
  [SRC: [`16_COMMODITY_AND_BOND_MOMENTUM_2026-11-22.md`](docs/edge_research/16_COMMODITY_AND_BOND_MOMENTUM_2026-11-22.md:104), [`commodity_momentum_20261122.json`](reports/commodity_momentum_20261122.json:88)]
- **(b) APPROACH** — **backtest only**, on front-month continuous futures. SAMPLE WINDOW: `UNMEASURED` in the
  supplied evidence. REBALANCE FREQUENCY: `UNMEASURED`. LOOK-AHEAD: `UNMEASURED`. Critically, the series are
  **roll-corrupted**, so the backtest is not merely unlagged, it is on the wrong prices: CL=F has a negative
  close (−37.63 on 2020-04-20), ZC=F prints ≈−23.6% on 07-15 in three separate years, NG=F has recurring
  same-month-day spikes (55–163 moves > 8% across six years); the doc-23 table records CL=F 17 moves > 8%,
  ZC=F −13.1% (07-15-2022) and −16.8% (07-17-2023), NG=F 92 moves > 8%.
  [SRC: [`23_DEFINITIVE_ANSWER_2026-11-22.md`](docs/edge_research/23_DEFINITIVE_ANSWER_2026-11-22.md:187)]
- **(c) STRATEGIES + TRIAL COUNT** — V1, V2, V3 = **3 variants, counted as ONE row**. **This number IS the
  trial count, declared up front.** Term-structure carry: 1 variant, untestable. New this window: 0.
  [SRC: [`16_COMMODITY_AND_BOND_MOMENTUM_2026-11-22.md`](docs/edge_research/16_COMMODITY_AND_BOND_MOMENTUM_2026-11-22.md:28)]
- **(d) METRICS** — Sharpe (gate, `UNMEASURED`; break-even Sharpe = 0 bp/side) · Sortino (info, `UNMEASURED`) ·
  max drawdown (gate, `UNMEASURED`) · profit factor (gate, **0.757 / 1.114 / 1.074**, FAIL as a family) ·
  **deflated Sharpe with N (gate, N=3, `UNMEASURED`)** · **PBO via CSCV (gate, `UNMEASURED`)** · walk-forward
  efficiency (gate, `UNMEASURED`) · information ratio vs matched benchmark (gate, `UNMEASURED`) · **2x-cost
  survival (gate, FAIL: break-even 0 bp/side)** · turnover per year (info, `UNMEASURED`) · capacity at
  intended size (info, `UNMEASURED`) · CI on net return (gate, `UNMEASURED`).
- **(e) DATA** — front-month continuous futures. Point-in-time: **NO**. Lag: `UNMEASURED`. `COMMISSION_UNKNOWN`.
- **(f) EXECUTION STYLE** — **no top pick.** Futures are margined and rolled, so any real version would be
  **ENTRY WITH TP/SL** plus a roll; cost consequence is `UNMEASURED turnover × UNMEASURED cost per contract`.
- **VEHICLE COMPARISON** — **futures (`UNMEASURED` cost) vs commodity ETF (`UNMEASURED`) vs commodity mutual
  fund (`UNMEASURED`) vs index fund (`UNMEASURED`) vs direct holding (physical: not in scope)**. No vehicle in
  this class has a measured cost, so no ranking is possible.
- **(g) KILL RULE** (frozen) — **Sharpe-vs-rf < 0.5 at 10 bp/side** (existing). Observed at 5 bp/side: V1
  Sharpe below zero by construction of a 0 bp break-even.
- **(h) ETA** — **0 min. Dead, not re-opened, no ETA.** Re-opening commodity momentum needs
  "roll-adjusted, back-adjusted continuous futures series built from individual contract months with an
  explicit, pre-declared roll rule, plus commission and slippage charged per contract"; re-opening
  term-structure carry needs "a genuine futures curve (at least two simultaneous contract months per
  commodity per date) for a multi-year history". Neither exists on disk, and a roll rule chosen after seeing
  the prices would manufacture the signal.
  [SRC: [`23_DEFINITIVE_ANSWER_2026-11-22.md`](docs/edge_research/23_DEFINITIVE_ANSWER_2026-11-22.md:119)]

---

## 6. FOREX

**Verdict status: DEAD, not re-opened.** FX momentum is **−26.88 bp gross** (net −36.88 bp, n=4,092, null
0.0 percentile). FX mean-reversion is dead **at measured cost**: break-even is **4.3038 bp RT** while measured
cost is **7.533 bp** median-of-medians (all-pairs median 7.99 bp) — `7.533 > 4.3038`, a 3.23 bp shortfall per
round trip.

- **(a) METHODOLOGY** — technical (momentum 63d/21d, mean-reversion 5d/5d). Why it fails: the spread alone,
  measured at the Sunday 22:00Z reopen (a **`MEASURED_UPPER_BOUND`**, not representative), is 7.533 bp RT,
  larger than the mean-reversion break-even. `COMMISSION_UNKNOWN` can only make it worse.
  [SRC: [`FOREX_COST_20261122.md`](reports/cost_measurement_forex/FOREX_COST_20261122.md), [`sweep.json`](reports/fx_meanrev_cost_sweep/sweep.json:7)]
- **(b) APPROACH** — **backtest only**. SAMPLE WINDOW: `UNMEASURED` for the momentum run (n=4,092 trades);
  mean-reversion is 5-day formation / 5-day holding; FX carry is **95 months, 11 currencies**. REBALANCE
  FREQUENCY: every 5 days (mean-reversion), monthly (carry). LOOK-AHEAD: `UNMEASURED`.
- **(c) STRATEGIES + TRIAL COUNT** — FX momentum (63d/21d), FX mean-reversion (5d/5d), FX carry (quintile).
  Variants: `UNMEASURED`. **N = 0 new this window. This number IS the trial count, declared up front.**
- **(d) METRICS** — Sharpe (gate, `UNMEASURED` for momentum/mean-rev) · Sortino (info, `UNMEASURED`) · max
  drawdown (gate, `UNMEASURED`) · profit factor (gate, `UNMEASURED`) · **deflated Sharpe with N (gate,
  `UNMEASURED`)** · **PBO via CSCV (gate, `UNMEASURED`)** · walk-forward efficiency (gate, `UNMEASURED`) ·
  information ratio vs matched benchmark (gate, `UNMEASURED`) · **2x-cost survival (gate, FAIL: at 2 × 7.533 =
  15.066 bp the shortfall against the 4.3038 bp break-even is 10.76 bp)** · turnover per year (info,
  `UNMEASURED`) · capacity at intended size (info, `UNMEASURED`) · CI on net return (gate, window-clustered CI
  at 1 bp **[−4.32, +11.09]** includes zero).
- **(e) DATA** — Tiingo `fx/top`; FRED DTB3/DGS10. Point-in-time: **NO**. Lag: `UNMEASURED`.
  `COMMISSION_UNKNOWN`.
- **(f) EXECUTION STYLE** — **no top pick.** Spot FX would be **ENTRY WITH TP/SL**; cost consequence
  `turnover/yr × 7.533 bp` (upper bound).
- **VEHICLE COMPARISON** — **direct spot FX 7.533 bp** measured (upper bound); **FX ETF `UNMEASURED`**;
  **FX mutual fund `UNMEASURED`**; **index fund: not applicable** (no index-fund wrapper exists in this
  programme's evidence).
- **(g) KILL RULE** (frozen) — kill if break-even cost **≤ measured RT cost** (4.3038 ≤ 7.533 → dead), or if the
  CI on net return includes zero at 1 bp (observed [−4.32, +11.09]). For carry: hurdle **468.4739 bp**.
- **(h) ETA** — **0 min. Dead, not re-opened, no ETA.** One caveat, stated and not acted on: a weekday
  London/NY-overlap cost measurement is **already scheduled** ([`.github/workflows/fx-cost-overlap.yml`](.github/workflows/fx-cost-overlap.yml),
  first fire Mon 2026-11-23 13:48Z) and is outside this window. It is a cost measurement, not a strategy
  re-open. Its chained strategy re-run will record `CHAIN_FAILED` because `tools/fx_meanrev_research.py` is
  absent from `main`; the cost measurement itself is unaffected.
  [SRC: [`2026-11-23-fx-chain-missing-module-blocker.md`](updates/2026-11-23-fx-chain-missing-module-blocker.md)]

---

## 7. CRYPTO

**Verdict status: two families dead, one observe pod live.** Crypto carry is dead (**−11 bp/tick**); crypto
intraday mean-reversion is killed (PF **0.815 at 0 bp**, break-even 0 bp); cross-venue basis is killed (0.00%
of 720 minutes above the 40.48 bp measured threshold).

- **(a) METHODOLOGY** — technical (mean-reversion on 4h bars; the live pod is VWAP reversion LONG). It suits
  the class only at a horizon longer than intraday, because the taker fee dominates: **10 bp/side** on
  Binance/BinanceUS/KuCoin and 26 bp on Kraken, while BTC/USDT top half-spread is 0.00082 bp. All-in RT is
  **~20.0 bp to ~52.0 bp**. A 4h-bar intraday loop that takes 6 round trips a day pays `6 × 20 = 120 bp/day`.
  [SRC: [`cost_measurement_20261122.json`](reports/cost_measurement_20261122.json)]
- **(b) APPROACH** — **both**: a lab backtest (OOS n=516) followed by a **paper-only** forward observation.
  No live capital. SAMPLE WINDOW: `UNMEASURED` for the lab; forward min n = **100 closed rows after
  registration**. REBALANCE FREQUENCY: 4h bars, signal-driven entry (z in [1.5, 2.5]). LOOK-AHEAD AVOIDED:
  enter at the **next bar open** after the signal close (1-bar lag, never same-bar), intrabar first-touch
  stops, **2× measured slippage** on every fill, no discretionary overrides.
  [SRC: [`12_OBSERVE_TO_PRE_REGISTERED_DECISION_MEMO_2026-11-22.md`](docs/edge_research/12_OBSERVE_TO_PRE_REGISTERED_DECISION_MEMO_2026-11-22.md:109)]
- **(c) STRATEGIES + TRIAL COUNT** — VWAP reversion LONG (`H-2026-11-22-VWAP-REVERSION-LAGGED-01`): **1**
  variant. **This number IS the trial count, declared up front.** Dead families listed above add no trials.
- **(d) METRICS** — Sharpe (gate, lab **3.102** OOS, `info` because it is a lab figure) · Sortino (info,
  `UNMEASURED`) · max drawdown (gate, `UNMEASURED`) · profit factor (gate, **0.957 at the 1-bar lag**, FAIL
  against the ≥1.0 requirement) · **deflated Sharpe with N (gate, N=1, lab DSR 21.4)** · **PBO via CSCV (gate,
  lab 0.18 same-bar but **0.84–0.97** at the 1-bar lag → FAIL)** · walk-forward efficiency (gate,
  `UNMEASURED`) · information ratio vs matched BTC/ETH benchmark (gate, must be ≥ 0.5) · **2x-cost survival
  (gate, enforced by construction: every fill pays 2× measured slippage; CI-LB must be > 0 at day 30/60)** ·
  turnover per year (info, `UNMEASURED`) · capacity at intended size (info, `UNMEASURED`) · CI on net return
  (gate, `UNMEASURED` forward).
- **(e) DATA** — ccxt `fetch_order_book(limit=1000)`; Binance `fapi/v1/fundingRate`. Point-in-time: **not
  established**. Lag: 1 bar (enforced by the rule).
- **(f) EXECUTION STYLE** for the top pick (the pod) — **ENTRY WITH TP/SL** (intrabar first-touch stops). Cost
  consequence: `turnover/yr × 20.0–52.0 bp` RT.
- **VEHICLE COMPARISON** — **direct spot 20.0–52.0 bp** all-in measured; **crypto ETF `UNMEASURED`**;
  **crypto mutual fund `UNMEASURED`**; **index fund: not applicable**.
- **(g) KILL RULE** (frozen) — **CI-LB ≤ 0 at 2× slippage at day 30 or day 60 → pod ends.** At n ≥ 100: kill if
  **net PF CI-LB ≤ 1.0**, or **IR < 0.5** vs a matched BTC/ETH benchmark, or split-half unstable.
- **(h) ETA** — **25 min** to write the pod's frozen spec, its lag-adjusted numbers (PF 0.957, PBO 0.84–0.97),
  and the note that its same-bar lab evidence does not survive the lag.

---

## 8. MEME

**Verdict status: no candidate; cost only partly measurable.**

- **(a) METHODOLOGY** — `UNMEASURED`: no meme strategy has been specified. Cost is the binding fact and it is
  only partly known: DOGE-USD **6.7938 bp** is the only quotable figure; SHIB's 0.00 bp is **tick-truncated**
  (84.3% zero-range bars) and is treated as unusable, and PEPE has no data. An average spread would be
  manufactured, so none is given. [SRC: [`class_cost_20261122.json`](reports/equity_cost_measurement/class_cost_20261122.json)]
- **(b) APPROACH** — **backtest only**, and none exists. SAMPLE WINDOW / REBALANCE / LOOK-AHEAD: `UNMEASURED`.
- **(c) STRATEGIES + TRIAL COUNT** — none named. **N = 0. This number IS the trial count, declared up front.**
- **(d) METRICS** — Sharpe (gate, `UNMEASURED`) · Sortino (info, `UNMEASURED`) · max drawdown (gate,
  `UNMEASURED`) · profit factor (gate, `UNMEASURED`) · **deflated Sharpe with N (gate, N=0 → `UNMEASURED`)** ·
  **PBO via CSCV (gate, `UNMEASURED`)** · walk-forward efficiency (gate, `UNMEASURED`) · information ratio vs
  matched benchmark (gate, `UNMEASURED`) · **2x-cost survival (gate, `UNMEASURED`: 2 × 6.7938 = 13.5876 bp
  RT on DOGE only)** · turnover per year (info, `UNMEASURED`) · capacity at intended size (info,
  `UNMEASURED`) · CI on net return (gate, `UNMEASURED`).
- **(e) DATA** — yfinance 1-min + cached CSVs. Point-in-time: **NO**. Lag: `UNMEASURED`. `COMMISSION_UNKNOWN`.
- **(f) EXECUTION STYLE** — **no top pick.** Buy-and-hold on DOGE at 6.7938 bp RT per year is the only measured action.
- **VEHICLE COMPARISON** — **direct holding 6.7938 bp** (DOGE only); **ETF `UNMEASURED`**; **mutual fund
  `UNMEASURED`**; **index fund: not applicable**.
- **(g) KILL RULE** (frozen) — kill if no meme instrument has a usable measured spread by the DRAFT rung, i.e.
  if the tick-truncation defect is not resolved (currently 1 of 3 names quotable, below the 2 needed for any median).
- **(h) ETA** — **10 min** to record the tick-truncation defect and the single-name cost, and to state that no candidate exists.

---

## 9. PENNY_STOCK

**Verdict status: `UNMEASURED`.**

- **(a) METHODOLOGY** — `UNMEASURED`: the class has **0 instruments** in the cost sample (`aggregate: null`),
  so neither technical nor fundamental methodology can be judged against a measured cost.
  [SRC: [`class_cost_20261122.json`](reports/equity_cost_measurement/class_cost_20261122.json)]
- **(b) APPROACH** — **backtest only**, and none exists. SAMPLE WINDOW / REBALANCE / LOOK-AHEAD: `UNMEASURED`.
- **(c) STRATEGIES + TRIAL COUNT** — none named. **N = 0. This number IS the trial count, declared up front.**
- **(d) METRICS** — Sharpe (gate, `UNMEASURED`) · Sortino (info, `UNMEASURED`) · max drawdown (gate,
  `UNMEASURED`) · profit factor (gate, `UNMEASURED`) · **deflated Sharpe with N (gate, N=0 → `UNMEASURED`)** ·
  **PBO via CSCV (gate, `UNMEASURED`)** · walk-forward efficiency (gate, `UNMEASURED`) · information ratio vs
  matched benchmark (gate, `UNMEASURED`) · **2x-cost survival (gate, `UNMEASURED`: no cost to double)** ·
  turnover per year (info, `UNMEASURED`) · capacity at intended size (info, `UNMEASURED`) · CI on net return
  (gate, `UNMEASURED`).
- **(e) DATA** — none: 0 instruments. Point-in-time: **NO** (no universe at all). Lag: `UNMEASURED`.
  `COMMISSION_UNKNOWN`.
- **(f) EXECUTION STYLE** — **no top pick.** No measured-cost action exists.
- **VEHICLE COMPARISON** — **direct holding `UNMEASURED`** (no instrument); **ETF / mutual fund / index fund:
  `UNMEASURED`**. Nothing can be ranked.
- **(g) KILL RULE** (frozen) — kill if no penny instrument with a measured spread exists by the DRAFT rung (currently true: 0 instruments).
- **(h) ETA** — **10 min** to record the empty universe and what one instrument would be needed to change it.

---

## 10. SPORTS

**Verdict status: nothing measured at all.**

- **(a) METHODOLOGY** — `UNMEASURED`: no sports dataset, no cost measurement, and no strategy has been run in
  this programme. The cost/horizon reasoning that applies to securities does not transfer without a measured
  price of participation (a bookmaker margin or exchange fee), and none exists here.
- **(b) APPROACH** — `UNMEASURED` (no backtest and no paper run exist). SAMPLE WINDOW / REBALANCE /
  LOOK-AHEAD: `UNMEASURED`.
- **(c) STRATEGIES + TRIAL COUNT** — none named. **N = 0. This number IS the trial count, declared up front.**
- **(d) METRICS** — Sharpe (gate, `UNMEASURED`) · Sortino (info, `UNMEASURED`) · max drawdown (gate,
  `UNMEASURED`) · profit factor (gate, `UNMEASURED`) · **deflated Sharpe with N (gate, N=0 → `UNMEASURED`)** ·
  **PBO via CSCV (gate, `UNMEASURED`)** · walk-forward efficiency (gate, `UNMEASURED`) · information ratio vs
  matched benchmark (gate, `UNMEASURED`) · **2x-cost survival (gate, `UNMEASURED`)** · turnover per year (info,
  `UNMEASURED`) · capacity at intended size (info, `UNMEASURED`) · CI on net return (gate, `UNMEASURED`).
- **(e) DATA** — `UNMEASURED`: no source was supplied for this class. Point-in-time: **NO** by default (no
  universe exists). Lag: `UNMEASURED`. `COMMISSION_UNKNOWN`.
- **(f) EXECUTION STYLE** — **no top pick.**
- **VEHICLE COMPARISON** — not applicable in the fund sense; **all four wrappers `UNMEASURED`**.
- **(g) KILL RULE** (frozen) — kill if no dataset **and** no cost figure exist by the DRAFT rung (03:50Z). Then the class is recorded `UNMEASURED` and not ranked.
- **(h) ETA** — **15 min** to record the absence of data, cost and strategy, and to list the minimum dataset that would make it testable.

---

## 11. FUNDING-BASIS CARRY (crypto)

**Verdict status: `NOT_INVESTABLE`, not re-opened.** Break-even hold is **16.398 days** at median funding,
while the median episode lasts **0.67–2.0 days**; only **2.89%** (82 of 2,838) of episodes reach it and 0.39%
(11) reach 90 days. Pair RT cost is **45.524 bp** at 1× and 91.048 bp at 2×.
[SRC: [`funding_carry_opportunity_frequency_20261122.json`](reports/funding_carry_opportunity_frequency_20261122.json:3)]

- **(a) METHODOLOGY** — fundamental/market-structure (carry) with a mechanical entry/exit. Why it fails: the
  cost is per round trip and the edge is per day; at 45.524 bp RT the hold must be long, and the opportunities are short.
- **(b) APPROACH** — **backtest only**. SAMPLE WINDOW: `UNMEASURED` (5 symbols; 214 BTC episodes). REBALANCE
  FREQUENCY: the hold-period grid 1/3/7/14/30/90 days. LOOK-AHEAD: `UNMEASURED`.
- **(c) STRATEGIES + TRIAL COUNT** — delta-neutral perp basis: **6 hold-period variants** (counted from the
  six reported net APRs), **counted as ONE row**. If the true grid was larger, N is understated.
  **This number IS the trial count, declared up front.**
  [SRC: [`15_PROGRAMME_SCOREBOARD_2026-11-22.md`](docs/edge_research/15_PROGRAMME_SCOREBOARD_2026-11-22.md:35)]
- **(d) METRICS** — Sharpe (gate, **−61.23 (1d), +0.555 (30d), +0.740 (90d)**, FAIL against 4.32% at every hold
  below 90d) · Sortino (info, `UNMEASURED`) · max drawdown (gate, **−1077.4% (1d), −24.19% (30d), −17.11%
  (90d)**, FAIL) · profit factor (gate, not reported → `UNMEASURED`) · **deflated Sharpe with N (gate, N=6,
  `UNMEASURED`)** · **PBO via CSCV (gate, `UNMEASURED`)** · walk-forward efficiency (gate, `UNMEASURED`) ·
  information ratio vs matched benchmark (gate, `UNMEASURED`) · **2x-cost survival (gate, FAIL at short holds:
  cost doubles to 91.048 bp, doubling the break-even hold)** · turnover per year (info, `365/hold_days`:
  12.17 at 30d) · capacity at intended size (info, XRP **$29,438**; ceiling **$699–1,837/yr** vs a **$1,272**
  T-bill) · CI on net return (gate, `UNMEASURED`).
- **(e) DATA** — Binance `fapi/v1/fundingRate` + order book (ccxt). Point-in-time: **not established**. Lag: `UNMEASURED`.
- **(f) EXECUTION STYLE** — **BUY AND HOLD** the basis pair (delta-neutral, held to capture funding). Cost
  consequence: `turnover × 45.524 bp`. At a 30-day hold, `12.17 × 45.524 = 553.8 bp/yr` (5.54%) of cost against
  a gross 7.93% APR → net ≈ 2.39%, consistent with the reported **+2.42%** at 30d.
- **VEHICLE COMPARISON** — **direct (perp + spot) 45.524 bp** measured; **crypto ETF `UNMEASURED`**;
  **mutual fund `UNMEASURED`**; **index fund: not applicable**.
- **(g) KILL RULE** (frozen) — kill if net APR at the best hold period **≤ 4.32%**, or if **< 5%** of funding
  episodes last ≥ break-even (observed 2.89%). Both bind.
- **(h) ETA** — **0 min.** `NOT_INVESTABLE`; not re-opened. Re-opening is unjustified because the deciding number is
  opportunity frequency (2.89%), which no cost or execution improvement changes, and the capacity ceiling is below the T-bill.

---

## 12. FX CARRY

**Verdict status: `NOT_INVESTABLE`, not re-opened.** Sharpe **−0.126** vs 4.32%, gross CAGR +3.38%, vol 7.43%,
worst month −7.55%, random-ranking null 98.2nd percentile, excess vs SPY CI **[−3.04%: −8.28%, +2.29%]**,
break-even **468.4739 bp**.
[SRC: [`fx_carry_20261122.json`](reports/fx_carry_20261122.json:112)]

- **(a) METHODOLOGY** — fundamental (rate differential, carry) with a technical trend leg (63d/21d, the FX momentum row).
  Why it fails: the break-even is 468.4739 bp while measured RT cost is ~7.533 bp, so cost is ~62× below the
  break-even (`468.4739 / 7.533 ≈ 62.2`; doc 23 rounds this to "60×") and the verdict is set by the hurdle, not by cost.
- **(b) APPROACH** — **backtest only**. SAMPLE WINDOW: **95 months**, 11 currencies. REBALANCE FREQUENCY:
  monthly (cost sweep 0–10 bp/month). LOOK-AHEAD: `UNMEASURED`.
- **(c) STRATEGIES + TRIAL COUNT** — carry quintile (1 row) plus the momentum variant (a separate row, §6).
  Variant count across the cost sweep/hold grid: `UNMEASURED`. **N = 0 new this window. This number IS the trial
  count, declared up front.**
- **(d) METRICS** — Sharpe (gate, **−0.126**, FAIL), Sortino (info, `UNMEASURED`), max drawdown (gate,
  `UNMEASURED`; worst month −7.55%), profit factor (gate, not reported → `UNMEASURED`), **deflated Sharpe with N
  (gate, N `UNMEASURED` → `UNMEASURED`)**, **PBO via CSCV (gate, `UNMEASURED`)**, walk-forward efficiency (gate,
  `UNMEASURED`), information ratio vs matched benchmark (gate, `UNMEASURED`; excess vs SPY CI spans zero),
  **2x-cost survival (gate, `UNMEASURED`: 2 × 7.533 = 15.066 bp is still 31× below the break-even)**, turnover
  per year (info, 12 rolls), capacity at intended size (info, `UNMEASURED`), CI on net return (gate,
  **[−8.28%, +2.29%]** vs SPY).
- **(e) DATA** — Tiingo FX; FRED DTB3/DGS10. Point-in-time: **NO**. Lag: `UNMEASURED`. `COMMISSION_UNKNOWN`.
- **(f) EXECUTION STYLE** — **no top pick.** Carry is **BUY AND HOLD** by nature; cost consequence at 12 rolls/yr
  is `12 × 7.533 = 90.4 bp/yr` (upper bound), small against the hurdle and therefore not the reason for the verdict.
- **VEHICLE COMPARISON** — **direct spot carry 7.533 bp per roll** measured (upper bound); **FX ETF
  `UNMEASURED`**; **mutual fund `UNMEASURED`**; **index fund: not applicable**.
- **(g) KILL RULE** (frozen) — kill if **Sharpe-vs-rf ≤ 0**, or net return on committed capital **≤ 4.32%**, or
  **break-even cost ≤ measured RT cost** (observed 468.4739 vs 7.533: not the binding constraint).
- **(h) ETA** — **0 min.** `NOT_INVESTABLE`; not re-opened.

---

## Overall — one cross-class ranked list

### The criterion, stated as one formula

**Risk-adjusted net return on committed capital.** Operationally, the key for a class `c` is the
**Sharpe-vs-policy-rate** construct on committed capital:

```
S(c)   = ( NetCAGR_cc(c) − r_f ) / σ_net,cc(c)            r_f = 4.32%
LB(c)  = ( LB95(NetCAGR_cc(c)) − r_f ) / UB95(σ_net,cc(c))   ← the ranking key
```

- `NetCAGR_cc(c)` = annualised net return on committed capital after measured cost (the 2×-cost figure is
  reported separately as a gate, never averaged in).
- `σ_net,cc(c)` = annualised realised volatility of the daily net P&L of committed capital.
- **Committed capital** = deployed notional + cash collateral required to hold it (the HML preregistration's
  benchmark convention, §4: "committed capital including cash collateral", not a bare T-bill yield).
- **Collateral convention.** Base case: collateral earns **4.32%** ([`tools/capacity_model.py:49`](tools/capacity_model.py:49)).
  Conservative case: collateral earns **0%** and the forgone interest is **booked as a cost**, so `r_f` is
  charged twice in effect. Both are reported; the conservative case is what the FINAL rung ranks on if they differ.
- `LB(c)` divides the **lower** bound of return by the **upper** bound of vol: both sides are made worse at once,
  which is the only honest way to take a lower bound of a ratio.

### Eligibility, decided before ranking

A class produces a ranked entry **only if all four hold**:

1. a **measured cost** exists (else the 2×-cost gate is `UNMEASURED` and the class is ineligible);
2. it clears its **per-class kill rule** (§1–§12(g));
3. it **survives 2× cost**;
4. a **CI on net return** exists (else `LB(c)` is undefined).

**Dead classes produce no ranked entries.** An **empty ranked list is a permitted, honest output** — and given
the settled tally it is the expected one for this window.

### The ranking, applied

| Rank | Class | LB(c) | Why |
|---|---|---|---|
| — | *none* | `UNMEASURED` | No class has a CI on net return, so `LB(c)` is undefined for all 12. The list is **empty**. |

An empty list is not a failure of the plan; it is the correct answer when no candidate has a lower bound.

### Tie-breaks, in the order adopted

1. **Higher one-sided 95% lower bound on net excess return** (bp/yr) — money first, before vol normalisation.
2. **Lower turnover per year at measured cost** — fewer bp of measured cost to be wrong about.
3. **Larger margin over the 2×-cost gate** (break-even ÷ 2×measured cost) — *surviving* 2× cost is an
   eligibility gate, so the tie-break is the margin, not the pass.
4. **Larger deflated Sharpe with N.**
5. **Higher capacity headroom at intended size** (`UNMEASURED` sorts last; capacity has never been tested).

Why this order: (1) is the quantity the operator actually cares about; (2)–(3) are cost exposure, which is the
dominant measured term in every class; (4) is multiple-testing credibility; (5) is size, the least measured of all.

### Why the lower bound and not the point estimate

A class with a **wide** CI has a point estimate that is mostly noise. Ranking on point estimates would let a
class with three observations and a wide interval outrank one with a tight interval around a slightly smaller
number, purely by luck of the draw. Ranking on `LB(c)` makes width a penalty: the wider the interval, the lower
the key. That is why no composite score averages across metrics either — an average lets one strong metric
compensate for a failed gate. The key is a single number and the tie-breaks are lexicographic, never additive.

No cross-class portfolio is formed. The classes share neither instruments nor point-in-time status, so
"combining" them would combine unmeasured things.

---

## Caveats that apply to every line above

- **The tally split is disputed; the row count is not.** This plan asserts **`0 INVESTABLE / 11
  NOT_INVESTABLE / 3 UNKNOWN (14 rows)`**, matching the enforced test. Doc 23 lines 9–10 carry an older
  correction note saying 10/4:
  > The note says `0 INVESTABLE / 10 NOT_INVESTABLE / 4 UNKNOWN` TALLY-HISTORICAL-OK: it is a correction note,
  > and the table and doc 15 say 11/3. The 14-row total is stable; the split is not. This plan flags the
  > discrepancy rather than hiding it.
- **`COMMISSION_UNKNOWN` for every class.** No commission is included in any cost figure above.
- **Point-in-time integrity is not established for ANY class.** Every list is a today's-constituents list, so
  every backtest number carries that caveat. The **0.0 pp/yr survivorship gap is zero by construction** (both
  ends are the same 79-symbol set): it is a **lower bound, not a null**. [SRC: [`10_SURVIVORSHIP_AUDIT_2026-11-22.md`](docs/edge_research/10_SURVIVORSHIP_AUDIT_2026-11-22.md:18)]
- **Capacity has never been tested.** Every "capacity at intended size" above is `UNMEASURED` except funding
  carry's single XRP datapoint ($29,438).
- **Nothing here is investable.** Cost figures are 1-minute-bar upper bounds, not NBBO; live NBBO for the
  equity-family classes is `BLOCKED_NO_LIVE_NBBO`.
- **INDEX is an alias of ETF** in the programme's own record, so rows 2 and 3 are not independent evidence.

---

TALLY: 0 INVESTABLE / 11 NOT_INVESTABLE / 3 UNKNOWN (14 rows)
