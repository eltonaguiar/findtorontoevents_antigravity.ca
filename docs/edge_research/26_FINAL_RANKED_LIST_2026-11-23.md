# 26 — FINAL ranked list, 2026-11-23 window: the answer, twelve class verdicts, and the vehicle question

**Rung:** FINAL (deadline 05:50Z).
**Inputs, read from committed blobs, not the working tree:**
[`24_EXECUTION_PLAN_2026-11-23.md`](docs/edge_research/24_EXECUTION_PLAN_2026-11-23.md:1) (PLAN, sha `086583427e13`, branch `plan/execution-2026-11-23`) and
[`25_DRAFT_RANKED_LIST_2026-11-23.md`](docs/edge_research/25_DRAFT_RANKED_LIST_2026-11-23.md:1) (DRAFT, sha `cc15fc2b063`, branch `draft/ranked-list-2026-11-23`).
**Rule of this document:** every number carries a `[SRC:]` marker or is written `UNMEASURED` with a reason. No number is invented, no cost is assumed, no class is re-opened, and no purchase is proposed.

---

## 1. The answer

**The ranked list is EMPTY: 0 entries, and there is no real-money recommendation for a human in this programme today.** All 12 asset classes fail at least one of the four eligibility gates (measured cost, per-class kill rule, 2×-cost survival, a CI on net return), so the ranking key `LB(c)` is undefined for every one of them; that is the whole answer, not a provisional one. If an operator forced a choice anyway, the least-refuted exposure on measured evidence is **FX CARRY**, because it is the only class whose deciding statistic is a hurdle rather than a cost or an absent measurement (Sharpe vs the 4.32% T-bill **−0.126**, break-even **468.4739 bp** against ~7.5 bp of measured cost), and its interval on excess return, while spanning zero at **[−8.28%, +2.29%]**, has the narrowest width and the least negative point estimate of the three classes that have any interval at all. **That forced pick is not a recommendation and must not be read as one:** its lower bound is negative, its kill rule fails at `Sharpe ≤ 0`, and it has zero forward evidence, so it cannot be ranked. The one thing the window *can* answer cleanly is a vehicle question, and even there the answer is a cost ordering, not an investment: on measured round-trip cost, **ETF 6.7122 bp < broad-index ETF proxy 8.0325 bp < direct equity 12.0749 bp**, with the mutual-fund leg `UNMEASURED` because no mutual-fund fee data exists in this repo.

---

## 2. Twelve per-class verdicts

Verdict vocabulary is fixed: `KILLED` / `NOT_INVESTABLE` / `PENDING_N` / `BLOCKED_MISSING_DATA` / `DEAD-NOT-REOPENED`. Gate numbers refer to the plan's four gates: **(1)** measured cost exists, **(2)** clears the per-class kill rule, **(3)** survives 2× measured cost, **(4)** a CI on net return exists.

### 2.1 EQUITY — `DEAD-NOT-REOPENED`

- **Deciding number:** breakout profit factor **0.9917 at 25 bp/side** (below 1 even at that cost), with the value family at **+0.11%/yr gross** and a measured RT cost of **12.0749 bp** (6.0375 bp/side, 13 symbols, Corwin-Schultz 1.5033 bp, `provenance_self_check PASS`). [SRC: [`23_DEFINITIVE_ANSWER_2026-11-22.md`](docs/edge_research/23_DEFINITIVE_ANSWER_2026-11-22.md:182); [`equity_cost_20261122.json`](reports/equity_cost_measurement/equity_cost_20261122.json:2043), [`equity_cost_20261122.json`](reports/equity_cost_measurement/equity_cost_20261122.json:2045), [`equity_cost_20261122.json`](reports/equity_cost_measurement/equity_cost_20261122.json:2049); HML preregistration §8 table, "Gross annual +0.11%"]
- **Gates failed:** (2) kill rule, (3) 2× cost (already fails at 1×), and (4) in substance — the excess-CAGR interval **[−46.32%, +32.31%]** spans zero with a point of −14.25% vs SPY. [SRC: [`equity_cost_20261122.json`](reports/equity_cost_measurement/equity_cost_20261122.json:2066)]
- **What would change it:** a strategy whose out-of-sample net-return CI-LB on committed capital clears 4.32% at 2 × 12.0749 = 24.1498 bp RT. A tighter fill cannot flip a PF below 1 at zero cost.

### 2.2 ETF — `BLOCKED_MISSING_DATA` (no strategy has ever been specified)

- **Deciding number:** **6.7122 bp RT** median over 14 names (SHY 0.6144 … SOXX 22.9049; max/min 37.2775). Verified by recomputation: sorted median = (6.1146 + 7.3099)/2 = 6.7122; 22.9049/0.6144 = 37.2775. [SRC: [`class_cost_20261122.json`](reports/equity_cost_measurement/class_cost_20261122.json:723), [`class_cost_20261122.json`](reports/equity_cost_measurement/class_cost_20261122.json:747)]
- **Gates failed:** (2) and (3) are not evaluable and (4) fails outright — `NO_STRATEGY_WITH_CI`. The DRAFT's search of the six ETF-bearing report files found walk-forward (n=11, PF 2.746), a forward pilot with `n_closed: 0`, an exit-rule A/B delta CI, and no net-return CI anywhere. [SRC: `docs/edge_research/25_DRAFT_RANKED_LIST_2026-11-23.md` §2.1]
- **What would change it:** any specified ETF strategy with a forward ledger and a net-return CI clearing 4.32% at 2 × 6.7122 = 13.4244 bp. Today there is cost and no strategy.

### 2.3 INDEX — `NOT_INVESTABLE`

- **Deciding number:** SPY 200-day trend, **null percentile 53.4** (bar ≥ 95) and **excess vs SPY −6.8 pp**. [SRC: [`23_DEFINITIVE_ANSWER_2026-11-22.md`](docs/edge_research/23_DEFINITIVE_ANSWER_2026-11-22.md:193)]
- **Gates failed:** (2), (4); (3) `UNMEASURED` (stress 16.065 bp). Cost is measured: **8.0325 bp** median over SPY 8.3139, QQQ 12.0749, IWM 7.7512, DIA 5.5896. [SRC: [`class_cost_20261122.json`](reports/equity_cost_measurement/class_cost_20261122.json:965)]
- **What would change it:** a trend rule that beats SPY *before* cost and carries a net-return CI. INDEX is an alias of ETF in the programme's own record, so it inherits §2.2's answer.

### 2.4 BOND / MUTUAL_FUND — `DEAD-NOT-REOPENED` (bond momentum); mutual-fund leg `BLOCKED_MISSING_DATA`

- **Deciding number:** break-even **0 bp/side** on all three variants, with Sharpe **−0.550 / −1.699 / −1.063** beside PF 1.312 / 0.743 / 0.737 and maxDD −5.81% / −5.31% / −11.64%. [SRC: [`bond_momentum_20261122.json`](reports/bond_momentum_20261122.json:152), [`bond_momentum_20261122.json`](reports/bond_momentum_20261122.json:183), [`bond_momentum_20261122.json`](reports/bond_momentum_20261122.json:482), [`bond_momentum_20261122.json`](reports/bond_momentum_20261122.json:509), [`bond_momentum_20261122.json`](reports/bond_momentum_20261122.json:551), [`bond_momentum_20261122.json`](reports/bond_momentum_20261122.json:578)]
- **Gates failed:** (1) for the bond class as a cost (none measured; the backtest used 5 bp/side **assumed**), (2) at any cost, (3) trivially, (4) in the sense that matters (the bootstrap is excess-vs-SPY and excludes zero on the negative side: B1 [−30.00%, −4.14%]).
- **What would change it:** a measured bond cost plus a strategy with positive Sharpe at that cost, and a mutual-fund fee schedule that does not exist here.

### 2.5 COMMODITY / FUTURES — `DEAD-NOT-REOPENED` (momentum); term-structure carry `BLOCKED_MISSING_DATA`

- **Deciding number:** PF **0.757 / 1.114 / 1.074** at a **0 bp/side** break-even (Sharpe vs rf −0.627 / −0.038 / −0.089). [SRC: [`23_DEFINITIVE_ANSWER_2026-11-22.md`](docs/edge_research/23_DEFINITIVE_ANSWER_2026-11-22.md:189) for PF; [`commodity_momentum_20261122.json`](reports/commodity_momentum_20261122.json:88) for Sharpe]
- **Gates failed:** (1) (no futures cost measured), (2), (3), (4). Term-structure carry additionally fails on data: no second-month contract series exists on disk.
- **What would change it:** roll-adjusted, back-adjusted continuous series with a pre-declared roll rule and per-contract commission, then a strategy with PF > 1 at 0 bp. The series on disk are roll-corrupted (CL=F negative close −37.63 on 2020-04-20; NG=F 92 moves > 8%).

### 2.6 FOREX — `NOT_INVESTABLE`

- **Deciding number:** mean-reversion break-even **4.3038 bp RT** against measured cost **7.533 bp** (median of six major pair medians; all-pairs median 7.99 bp) — a **3.23 bp shortfall** per round trip; FX momentum is also dead at **−26.88 bp gross** (null 0.0 percentile). [SRC: [`FOREX_COST_20261122.json`](reports/cost_measurement_forex/FOREX_COST_20261122.json:36), [`sweep.json`](reports/fx_meanrev_cost_sweep/sweep.json:7), [`forex_carry_trend_20261122.json`](reports/forex_carry_trend_20261122.json:31)]
- **Gates failed:** (2), (3) (at 2 × 7.533 = 15.066 bp the shortfall is 10.76 bp), (4) — the window-clustered CI at 1 bp is **[−4.319, +11.086]**, which includes zero. [SRC: [`sweep.json`](reports/fx_meanrev_cost_sweep/sweep.json:10)]
- **What would change it:** a break-even above 7.533 bp at a representative London/NY-overlap time plus a net-return CI-LB above zero. The overlap cost run is scheduled for Mon 2026-11-23 13:48Z, outside this window.

### 2.7 CRYPTO — `PENDING_N`

- **Deciding number:** **0 closed forward rows** (3 rows open) on the live paper pod, so there is no PF and no CI; all-in RT is **20.0016 bp** at Binance (taker 10 bp/side) rising to ~52 bp at Kraken. [SRC: [`cost_measurement_20261122.json`](reports/cost_measurement_20261122.json:18), [`cost_measurement_20261122.json`](reports/cost_measurement_20261122.json:58), `docs/edge_research/25_DRAFT_RANKED_LIST_2026-11-23.md` §2.3]
- **Gates failed:** (4) forward; (2)/(3) are `PENDING` by construction (every fill pays 2× measured slippage, and CI-LB must exceed 0 at day 30/60).
- **What would change it:** 100 closed forward rows on the pod's own hypothesis with net PF CI-LB > 1.0, IR ≥ 0.5 and split-half stability. Earliest day-30 checkpoint is 2026-12-19.

### 2.8 MEME — `KILLED`

- **Deciding number:** **1 quotable name of 3** (DOGE 6.7938 bp; SHIB 0.00 bp is tick-truncated at 84.3% zero-range bars and 53/55 distinct high/low values; PEPE empty) against a frozen rule needing ≥ 2. [SRC: [`class_cost_20261122.json`](reports/equity_cost_measurement/class_cost_20261122.json), `classes.MEME.per_name`]
- **Gates failed:** (2), (4); (3) `UNMEASURED` (stress 13.5876 bp on DOGE only).
- **What would change it:** a second quotable meme name on a tick grid finer than its price moves, then a strategy with a CI.

### 2.9 PENNY_STOCK — `KILLED`

- **Deciding number:** `classes.PENNY_STOCK.aggregate = null`, universe `[]`, blocked `NO_INSTRUMENT_IN_REPO` — **0 quotable instruments**. [SRC: [`class_cost_20261122.json`](reports/equity_cost_measurement/class_cost_20261122.json), `classes.PENNY_STOCK`]
- **Gates failed:** (1), (2), (3), (4).
- **What would change it:** at least one penny instrument in a cost sample, then a strategy.

### 2.10 SPORTS — `KILLED`

- **Deciding number:** **no measured margin or fee**, and the one study that ran found n=1,039 +EV bets over 46 events with ROI +8.68% point but **event-clustered CI-LB −9.1%** (n_events 46 < 100). [SRC: [`SPORTS_DEVIG_EV_VERDICT_2026-06-22.md`](reports/SPORTS_DEVIG_EV_VERDICT_2026-06-22.md:8)]
- **Gates failed:** (1), (2), (4).
- **What would change it:** a measured bookmaker margin or exchange fee, closing-line capture, and settled outcomes.

### 2.11 FUNDING-BASIS CARRY (crypto) — `NOT_INVESTABLE`

- **Deciding number:** only **82 of 2,838 episodes (2.889%)** last the **16.398-day** break-even, and **11 (0.388%)** reach 90 days. Recomputed from the per-symbol counts: 523+525+656+442+692 = 2,838 episodes; 28+19+16+1+18 = 82; 2+5+2+0+2 = 11. Pair RT cost is **45.524 bp** (91.048 bp at 2×). [SRC: [`funding_carry_opportunity_frequency_20261122.json`](reports/funding_carry_opportunity_frequency_20261122.json:3), [`funding_carry_opportunity_frequency_20261122.json`](reports/funding_carry_opportunity_frequency_20261122.json:362)]
- **Gates failed:** (2) (freak frequency < 5%), (3) (2× cost doubles the required hold), (4).
- **What would change it:** funding episodes long enough to reach the break-even hold, or a cost fall that shrinks it. Opportunity frequency, not cost, is the binding term.

### 2.12 FX CARRY — `NOT_INVESTABLE`

- **Deciding number:** Sharpe vs the 4.32% T-bill **−0.126** (gross CAGR +3.3817%, vol 7.4329%, worst month −7.55%), break-even **468.4739 bp**, random-ranking null 98.2nd percentile. [SRC: [`fx_carry_20261122.json`](reports/fx_carry_20261122.json:54), [`fx_carry_20261122.json`](reports/fx_carry_20261122.json:112)]
- **Gates failed:** (2) (`Sharpe ≤ 0`), (4) in substance — excess CAGR vs SPY CI **[−8.28%, +2.29%]** spans zero (point −3.04%). [SRC: [`fx_carry_20261122.json`](reports/fx_carry_20261122.json:120)]
- **What would change it:** a net-return CI-LB above 4.32% against a Sharpe of −0.126. The hurdle, not cost, sets the verdict.

---

## 3. The final ranked list

**RANKED LIST: 0 entries.**

**The mechanical reason.** The ranking key is `LB(c) = (LB95(NetCAGR_cc) − 4.32%) / UB95(σ_net,cc)`. Gate (4) requires a CI on net return *on committed capital*; no class has one (`UNMEASURED` for all 12), so both the numerator and the denominator are undefined for every class and the key cannot be evaluated. Independently, gate (1) fails for 4 classes (BOND, COMMODITY, PENNY_STOCK, SPORTS: no measured cost), gate (2) fails for 9 (EQUITY, INDEX, BOND, COMMODITY, FOREX, MEME, PENNY_STOCK, SPORTS, FUNDING-BASIS CARRY), and gate (3) fails or is unmeasurable for every class. No gate is cleared by any class, so there is nothing to sort.

### 3.1 "If you forced a pick": the three classes that at least have a CI

Only EQUITY, FOREX and FX CARRY have any interval on return at all. Their `LB(c)` is computed as far as the data allows, and the arithmetic is shown rather than the answer asserted.

| Class | The CI that exists | `LB95(NetCAGR_cc)` (numerator input) | `UB95(σ_net,cc)` (denominator input) | `LB(c)` |
|---|---|---|---|---|
| EQUITY | excess CAGR vs SPY **[−46.32%, +32.31%]**, point −14.25% [`equity_cost_20261122.json`](reports/equity_cost_measurement/equity_cost_20261122.json:2066) | `UNMEASURED` — the CI is excess-vs-SPY, not net CAGR on committed capital | `UNMEASURED` | **undefined** |
| FOREX | mean net bp per trade at **1 bp** cost, window-clustered **[−4.319, +11.086]** [`sweep.json`](reports/fx_meanrev_cost_sweep/sweep.json:10) | `UNMEASURED` — bp per trade cannot be annualised without a trades-per-year count, which is not recorded | `UNMEASURED` | **undefined** |
| FX CARRY | excess CAGR vs SPY **[−8.28%, +2.29%]**, point −3.04% [`fx_carry_20261122.json`](reports/fx_carry_20261122.json:120) | point only: gross CAGR 3.3817% − 12 rolls × 7.533 bp = 0.9040% → **2.4777%** (a point, not a lower bound) | point vol **7.4329%**, so `UB95(σ) ≥ 7.4329%` | **`LB(c) ≤ (2.4777% − 4.32%) / 7.4329% = −0.248`** |

**Arithmetic for the FX CARRY row, shown:** `3.3817 − (12 × 0.07533) = 3.3817 − 0.9040 = 2.4777`; `(2.4777 − 4.32) / 7.4329 = −1.8423 / 7.4329 = −0.2479`. The `≤` holds because the denominator can only be larger than the point vol (`UB95 ≥ point`), which can only make the ratio more negative.

**None of the three is a recommendation.** All three intervals include zero, all three fail their class kill rule (§2.1, §2.6, §2.12), and for two of the three the numerator that `LB(c)` needs does not exist. The FX CARRY row is the least negative of an all-negative set; it is not a pick.

---

## 4. The vehicle question, answered properly

Mutual fund vs index fund vs ETF vs direct holding. All figures are round-trip (RT) 1-minute-bar range upper bounds, not NBBO; `COMMISSION_UNKNOWN` everywhere.

| Vehicle | Measured RT cost | Basis |
|---|---|---|
| **ETF** | **6.7122 bp** median, 14 names (SHY 0.6144 … SOXX 22.9049) | [`class_cost_20261122.json`](reports/equity_cost_measurement/class_cost_20261122.json:723) |
| **"Index fund" (in fact a broad-index ETF proxy)** | **8.0325 bp** median of SPY 8.3139, QQQ 12.0749, IWM 7.7512, DIA 5.5896 | [`class_cost_20261122.json`](reports/equity_cost_measurement/class_cost_20261122.json:965) |
| **Direct holding** | **12.0749 bp** RT upper bound ≈ N × 6.0375 bp/side of traded notional for N names | [`equity_cost_20261122.json`](reports/equity_cost_measurement/equity_cost_20261122.json:2043) |
| **Mutual fund** | **`UNMEASURED`** | no instrument, no spread, no fee schedule; `reports/capacity_20261122.json` records MUTUAL_FUND `INSUFFICIENT_MEASUREMENT` |

**Ordering on measured evidence:** ETF (6.7122) < broad-index ETF proxy (8.0325) < direct equity (12.0749) < mutual fund (`UNMEASURED`, so it sorts last by rule, not by measurement).

**Two corrections to how these numbers are usually quoted:**
1. The "index fund" row is not a separate vehicle. The four index proxies *are* ETFs, so that row is a broad-index ETF sample, and its 8.0325 bp is a subset median of the same 14-name ETF sample, not independent evidence. [SRC: [`class_cost_20261122.json`](reports/equity_cost_measurement/class_cost_20261122.json:751), `INDEX_alias_of_ETF`]
2. **37.2775 is a ratio, not a spread.** It is max/min of the ETF sample (22.9049 / 0.6144); the widest measured ETF RT spread is **22.9049 bp** (SOXX). A sentence that speaks of "a 37 bp-spread ETF" has conflated the two. Both values stated: ratio **37.2775**, widest spread **22.9049 bp**.

**The mutual-fund gap, stated as a gap.** A mutual fund could beat even the widest measured ETF if its all-in fee were below the difference (for SOXX: below 22.9049 bp RT-equivalent). That is a testable question and this programme has not answered it, because it has no mutual-fund fee data at all. **No expense ratio is assumed, in either direction** — not 0.1%, not 1%: assuming one would be inventing the deciding number.

**What the ordering does not say.** It is a statement about the cost of holding a passive exposure, not a recommendation to buy anything: none of the four vehicles has a strategy with a CI on net return, so none of them produces a ranked entry.

---

## 5. The two open discrepancies

### 5(i) Doc 23's tally: 11/3 is correct, 10/4 is stale

I counted the rows of doc 23's final-accounting table (`^| N | ...` rows, N = 1..14, no gaps, no repeats) and classified each by its verdict column:

| # | Row | Verdict |
|---|---|---|
| 1 | FX momentum (63d/21d) | NOT_INVESTABLE |
| 2 | FX mean-reversion (5d/5d) | **UNKNOWN** |
| 3 | Equity breakout | NOT_INVESTABLE |
| 4 | FX carry (quintile) | NOT_INVESTABLE |
| 5 | Cross-venue basis | NOT_INVESTABLE |
| 6 | 12-1 momentum L/S | NOT_INVESTABLE |
| 7 | Crypto intraday mean-rev | NOT_INVESTABLE |
| 8 | Commodity momentum V1/V2/V3 | **UNKNOWN** (`BLOCKED_MISSING_DATA`) |
| 9 | Bond momentum B1/B2/B3 | NOT_INVESTABLE |
| 10 | Funding carry | NOT_INVESTABLE |
| 11 | Commodity term-structure carry | **UNKNOWN** (`BLOCKED_MISSING_DATA`) |
| 12 | N1 R1 multi-asset momentum | NOT_INVESTABLE |
| 13 | N1 R2 sector momentum | NOT_INVESTABLE |
| 14 | N1 R3 SPY 200-day trend | NOT_INVESTABLE |

**Count: 14 rows, 0 INVESTABLE, 11 NOT_INVESTABLE, 3 UNKNOWN.** The 11/3 figure on line 195 of doc 23 and line 196 of doc 15 is correct, and the correction note at doc 23 lines 9–10 is stale. So is the prose line further down doc 23 that says "the UNKNOWN count is unchanged at 4".

**Why the note is stale rather than wrong when written:** the row that moved was funding carry, `UNKNOWN → NOT_INVESTABLE` on a new measurement (2.89% episode frequency), per the measurement note under the table. The note's 10/4 was a count of an earlier table; the current table is 11/3. The enforced test's own comment records the same move (`10/4 -> 11/3`).

I did **not** edit doc 23: it is not my file, and editing a document that the tally test parses risks the tally test. The finding is recorded here instead.

### 5(ii) The H-119 pod: (a) different computations of the same thing

**Both figures are correct for their own population; neither is "the" H-119 PF CI-LB."**

- **`0.775–0.850`** comes from [`h119_ledger_audit.json`](reports/h119_ledger_audit/h119_ledger_audit.json) `acceptance_clean_rows`: it is a **range across two price conventions on the CLEAN subset**, `ci_lb` **0.77545** for `resolver_exit_px` and **0.84994** for `exit_px`, at n=422 of 430 rows (8 rows screened for a >10% resolver-vs-exit mismatch), 367 symbol-day clusters, 16 bp RT charged, own bootstrap (4000 resamples, seed 20261122).
- **`0.9213`** is the promotion gate's `pf_ci_lb` for H-119 in [`audit3_ledger.json`](audit_dashboard/data/audit3_ledger.json) `forward_gate.hypotheses.H-119`, computed by [`pf_ci_lower.py`](tools/pf_ci_lower.py:1) on **ALL 430 rows**, `exit_px`, symbol-day clusters, B=2000, seed 42, alpha 0.05. The population overlap is provable by identity: that gate's `net_pf` **1.1147149111870513** equals the audit's `all_exit_px.net_pf` **1.1147149111870511** to 16 digits.
- **A third layer, stated so nobody collapses the two:** on the *same* 430-row `exit_px` series the audit's own bootstrap reports `ci_lb` **0.88239** [SRC: [`h119_ledger_audit.json`](reports/h119_ledger_audit/h119_ledger_audit.json) `acceptance_all_rows.all_exit_px.ci_lb`] while the gate reports **0.9213** — a difference of resample count and seed alone (4000/20261122 vs 2000/42), with no population difference at all.

Labelled distinctly, and neither figure overwritten:

| Label | Value | Population | Price | Bootstrap |
|---|---|---|---|---|
| `PF-CI-LB(clean, resolver_exit_px)` | 0.7755 | 422 clean rows | resolver_exit_px | B=4000, seed 20261122 |
| `PF-CI-LB(clean, exit_px)` | 0.8499 | 422 clean rows | exit_px | B=4000, seed 20261122 |
| `PF-CI-LB(all 430, exit_px, audit)` | 0.8824 | 430 rows | exit_px | B=4000, seed 20261122 |
| `PF-CI-LB(all 430, exit_px, gate)` | **0.9213** | 430 rows | exit_px | B=2000, seed 42 |

All four are below 1.0, so the H-119 conclusion (non-promotable, quarantined) is unchanged whichever is quoted. What would settle the presentation question is a single published convention: one row set, one price convention, one bootstrap, quoted everywhere.

---

## 6. What this window did NOT do

- **No capacity test.** Capacity has never been tested for any class; the only datapoint in the programme is funding carry's XRP $29,438.
- **No point-in-time reconstruction.** Every universe is a today's-constituents list; the 0.0 pp/yr survivorship gap is zero by construction (same 79-symbol set at both ends) and is a lower bound, not a null.
- **No commission measurement.** `COMMISSION_UNKNOWN` for all 12 classes; every cost is a spread/bar-range upper bound.
- **No mutual-fund fee data.** No expense ratio, no load, no 12b-1, no spread for any mutual fund.
- **No forward evidence for any class.** The only forward ledger rows in the programme belong to the quarantined H-119 lead; the live pod has 0 closed rows.
- **No live order, no capital, no data purchase, and no model change.** Nothing in this document places, sizes, or authorises a trade.
- Also absent, and worth naming: no NBBO (1-minute-bar upper bounds only), no benchmark-matched information ratio for any class, and no deflated Sharpe or PBO for any class.

---

## 7. Provenance

PROVENANCE: one file, authored 2026-11-23 in this session, as the FINAL rung of the 4-hour window.
Inputs read from committed blobs: `docs/edge_research/24_EXECUTION_PLAN_2026-11-23.md` at `086583427e13`, `docs/edge_research/25_DRAFT_RANKED_LIST_2026-11-23.md` at `cc15fc2b063`.
Figures traced to: `reports/equity_cost_measurement/class_cost_20261122.json`, `reports/equity_cost_measurement/equity_cost_20261122.json`, `reports/bond_momentum_20261122.json`, `reports/commodity_momentum_20261122.json`, `reports/cost_measurement_forex/FOREX_COST_20261122.json`, `reports/fx_meanrev_cost_sweep/sweep.json`, `reports/fx_carry_20261122.json`, `reports/funding_carry_opportunity_frequency_20261122.json`, `reports/cost_measurement_20261122.json`, `reports/h119_ledger_audit/h119_ledger_audit.json`, `audit_dashboard/data/audit3_ledger.json`, `reports/SPORTS_DEVIG_EV_VERDICT_2026-06-22.md`, `docs/edge_research/12,13,15,23_*.md`, `docs/preregistration/HML_VALUE_TEST_2026-11-22.md`; everything else is written `UNMEASURED` with its reason.
Corrections made in this document, both values stated: (1) "25% of the equity sample is ETF names" → **7 of 13 = 53.8%** [SRC: `equity_cost_20261122.json` `spread_aggregate.universe_symbols`]; (2) FUNDING-BASIS CARRY "net APR ≤ 4.32%" → the artifact's `capacity_arithmetic` gives **net APR 6.24% at the 90-day hold** and **2.42% at 30 days**, so the claim holds only for the 30-day hold, and the binding kill is the **2.889% < 5%** episode frequency, not the APR [SRC: `funding_carry_opportunity_frequency_20261122.json:363`]; (3) "37 bp-spread ETF" → **37.2775 is the max/min ratio**, the widest measured spread is **22.9049 bp** (§4).
Not independently re-derived in this window, carried from doc 23 and marked as such: the equity alpha CI-LB −0.285% and the breakout PF 0.9917.

TALLY: 0 INVESTABLE / 11 NOT_INVESTABLE / 3 UNKNOWN (14 rows)
