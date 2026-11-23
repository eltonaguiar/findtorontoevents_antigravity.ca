# 25 — DRAFT ranked list, 2026-11-23 window: twelve asset classes through the eligibility gate

**Rung:** DRAFT (deadline 03:50Z).
**Plan executed:** [`24_EXECUTION_PLAN_2026-11-23.md`](docs/edge_research/24_EXECUTION_PLAN_2026-11-23.md:511) (branch `plan/execution-2026-11-23`, sha `086583427e13`).
**Rule of this document:** every number carries a `[SRC:]` marker or is written `UNMEASURED` with a reason. No number is invented, no cost is assumed, and no class is re-opened.

**Eligibility gate (from the plan, applied mechanically):** a class produces a ranked entry only if **all four** hold —
(1) a measured cost exists, (2) it clears its per-class kill rule, (3) it survives 2× measured cost, (4) a CI on net return exists.

---

## 1. The eligibility table, all 12 classes

Costs are round-trip (RT) upper bounds unless stated; `COMMISSION_UNKNOWN` everywhere. `LB(c)` is the plan's ranking key `(LB95(NetCAGR_cc) − 4.32%) / UB95(σ_net,cc)`.

| # | CLASS | measured cost | kill-rule status | 2×-cost survival | CI on net return | ELIGIBLE? | rank key LB(c) |
|---|---|---|---|---|---|---|---|
| 1 | EQUITY | **12.0749 bp RT** (6.0375/side, 13 syms) | **FAIL** — dead: breakout PF 0.9917 @25 bp/side | **FAIL** (already fails at 1×) | exists but spans zero: excess-CAGR **[−46.32%, +32.31%]**, alpha CI-LB −0.285% | **NO** | n/a (undefined by gates 2–3) |
| 2 | ETF | **6.7122 bp RT** median (14 names) | **NO CANDIDATE** — no ETF strategy ever specified | UNMEASURED (stress 13.4244 bp; nothing to survive it) | **NO** (`NO_STRATEGY_WITH_CI`) | **NO** | n/a (no CI) |
| 3 | INDEX | **8.0325 bp RT** median (4 names; subset of ETF) | **FAIL** — SPY 200-day null 53.4 < 95, excess −6.8 pp | UNMEASURED (stress 16.065 bp) | **NO** | **NO** | n/a (no CI) |
| 4 | BOND / MUTUAL_FUND | **UNMEASURED** (bond: none; backtest used 5 bp/side *assumed*; mutual fund: none) | **FAIL** — break-even **0 bp/side**, Sharpe −0.550 / −1.699 / −1.063 | **FAIL** (fails at 1×, so at 2×) | **NO** (bootstrap CI is excess-vs-SPY, negative and excluding zero: B1 [−30.00%, −4.14%]) | **NO** | n/a (no cost, no CI) |
| 5 | COMMODITY / FUTURES | **UNMEASURED** | **FAIL** — PF 0.757 / 1.114 / 1.074 at 0 bp break-even | **FAIL** | **NO** | **NO** | n/a (no cost, no CI) |
| 6 | FOREX | **7.533 bp RT** (upper bound, Sunday 22:00Z reopen) | **FAIL** — break-even 4.3038 < 7.533; momentum null 0.0 pct | **FAIL** (shortfall 10.76 bp at 15.066) | exists but includes zero: **[−4.32, +11.09]** at 1 bp | **NO** | n/a (fails 2–3) |
| 7 | CRYPTO | **20.0–52.0 bp RT** all-in (taker 10 bp/side + spread) | **PENDING_N** — pilot 0 closed; other families dead | **PENDING** (enforced by construction; no fills yet) | **NO** forward (`UNMEASURED`); non-pod H-119 net PF CI-LB 0.9213 | **NO** | n/a (no CI) |
| 8 | MEME | **6.7938 bp** (DOGE only) | **FAIL** — 1 of 3 names quotable, rule needs ≥2 | UNMEASURED (stress 13.5876 bp, DOGE only) | **NO** | **NO** | n/a (no CI) |
| 9 | PENNY_STOCK | **UNMEASURED** (`aggregate: null`, 0 instruments) | **FAIL** — none quotable | UNMEASURED (no cost to double) | **NO** | **NO** | n/a (no cost, no CI) |
| 10 | SPORTS | **UNMEASURED** | **FAIL** — no measured margin/fee; no confirmable edge (event-clustered CI-LB −9.1%) | UNMEASURED | **NO** | **NO** | n/a (no cost, no CI) |
| 11 | FUNDING-BASIS CARRY | **45.524 bp RT** (1×) | **FAIL** — 2.89% of episodes reach the 16.398-day break-even (< 5%); net APR ≤ 4.32% | **FAIL** (91.048 bp doubles the break-even hold) | **NO** | **NO** | n/a (fails 2–3) |
| 12 | FX CARRY | **7.533 bp per roll** (upper bound) | **FAIL** — Sharpe **−0.126** ≤ 0 | UNMEASURED (15.066 bp is still ~31× below the 468.4739 bp break-even) | exists but includes zero vs SPY: **[−8.28%, +2.29%]** | **NO** | n/a (fails 2–3) |

Rows 2 and 3 are not independent evidence: INDEX is an alias of ETF in the programme's own record, and the four index proxies are ETFs.

### The ranked list

**EMPTY.** 0 entries. No class clears all four gates, so `LB(c)` is undefined for all twelve. This is the plan's expected output and a permitted one: an empty list is the correct answer when no candidate has a lower bound.

Three classes do have *some* CI on return (EQUITY, FOREX, FX CARRY) but each fails gate (2), and two of the three intervals include zero anyway. No class has a CI on net return **on committed capital** after measured cost that clears its kill rule.

### What would change the list, one line per class

1. **EQUITY** — a strategy whose OOS net-return CI-LB on committed capital clears 4.32% at 2 × 12.0749 bp; today PF is below 1 even at 0 bp/side, so no fill improvement flips it.
2. **ETF** — any specified ETF strategy with a forward ledger and a net-return CI clearing 4.32% at 2 × 6.7122 bp; today there is no strategy at all, only cost.
3. **INDEX** — a trend rule that beats SPY *before* cost (currently −6.8 pp) and carries a net-return CI; it is an ETF alias, so it inherits row 2's answer.
4. **BOND / MUTUAL_FUND** — a measured bond cost plus a strategy with positive Sharpe at that cost (currently −0.55 at **0 bp**), and a mutual-fund fee schedule, which does not exist in the repo.
5. **COMMODITY / FUTURES** — roll-adjusted, back-adjusted continuous series with a pre-declared roll rule and per-contract commission, then a strategy with PF > 1 at 0 bp; the series on disk are roll-corrupted.
6. **FOREX** — a break-even above 7.533 bp RT measured at a representative (London/NY-overlap) time plus a net-return CI-LB above zero; the overlap cost run is scheduled Mon 2026-11-23 13:48Z, outside this window.
7. **CRYPTO** — 100 closed forward rows on the pod's own hypothesis with net PF CI-LB > 1.0, IR ≥ 0.5 and split-half stability; the earliest day-30 checkpoint is 2026-12-19.
8. **MEME** — a second quotable meme name with a tick grid finer than its price moves (so a median exists), then a strategy with a CI.
9. **PENNY_STOCK** — at least one penny instrument in the cost sample, then a strategy; today the universe is empty.
10. **SPORTS** — a measured bookmaker margin or exchange fee, closing-line capture, and settled outcomes, then a net-return CI; none of the three exists.
11. **FUNDING-BASIS CARRY** — funding episodes long enough to reach the break-even hold (median episode is 0.67–2.0 days vs 16.398 needed), or a cost fall that shrinks the break-even; opportunity frequency, not cost, is the binding term.
12. **FX CARRY** — a net-return CI-LB above 4.32% against a Sharpe of −0.126; the hurdle (468.4739 bp), not cost, sets the verdict.

---

## 2. The six live classes

### 2.1 ETF (ETA 15)

**Per-name RT spreads, quoted from the artifact** [`reports/equity_cost_measurement/class_cost_20261122.json`](reports/equity_cost_measurement/class_cost_20261122.json) (`classes.ETF.aggregate.range_ub_rt_bp.per_name_rt_bp`, 14 names, 1-min bar range upper bound, NOT NBBO), sorted ascending:

SHY 0.6144 · AGG 1.0507 · TLT 2.5126 · GLD 5.3234 · DIA 5.5896 · XLV 5.7847 · XLF 6.1146 · XLY 7.3099 · XLE 7.3870 · IWM 7.7512 · SPY 8.3139 · QQQ 12.0749 · XLK 14.2149 · SOXX 22.9049

**Arithmetic shown:**
- median of 14 = mean of the 7th and 8th values = (6.1146 + 7.3099) / 2 = 13.4245 / 2 = **6.7122 bp**. (The 13.4245 here is a coincidence with the 2× stress number; it is not the same quantity.)
- max/min = 22.9049 / 0.6144 = **37.2775** (the artifact's own `ratio_max_to_min` is 37.2775, so my arithmetic reproduces it).

**Is there any ETF strategy with a measured net return and a CI?** Search: `grep -rl 'ETF' reports/ --include='*.json'` piped into a grep for CI keys returned six files; each was opened. The ETF strategy evidence they hold is:
- `etf_dual_momentum` lab walk-forward (`verified_strategies/WALKFORWARD_REPORT.json`): OOS n=11, PF 2.746, Sharpe 0.819 — **no CI on net return**;
- forward pilot (`verified_strategies/paper_pilot/etf_forward_stats.json`): `n_closed: 0`, gates `n<100`, `pf<1.5` — **no forward net return at all**;
- `exit_ab_paper_2026-11-19.json`: ETF n=261, but the CI is on *exit-rule delta* (−0.5153, +0.0884), not on net return;
- `alpha_slice_scan_2026-11-19.json`: ETF alpha −0.1194%, best surviving slice +0.4463% — no ETF net-return CI;
- `h147_beta_hedge_2026-11-20.json`: ETF n=4 — too small for a CI;
- `bond_momentum_20261122.json`: ETFs used as bond instruments, not an ETF strategy.

Verdict: **`NO_STRATEGY_WITH_CI`**. ETF therefore cannot be ranked; only the vehicle comparison is answerable.

**Vehicle comparison (passive exposure).** Measured evidence:
- **ETF: 6.7122 bp RT** median (14 names) [`class_cost_20261122.json`].
- **Index fund / index proxy: 8.0325 bp RT** median (SPY 8.3139, QQQ 12.0749, IWM 7.7512, DIA 5.5896) — in this programme the index proxy *is* an ETF sample, so "index fund" and "ETF" collapse to the same measurement [`class_cost_20261122.json`].
- **Direct holding of constituents:** no basket cost was measured. Scaling the measured per-side equity cost, ≈ **N × 6.0375 bp per side** of aggregate traded notional for N names (25% of the equity sample is already ETF names, and the basket's name count multiplies both cost and tracking effort) [`reports/equity_cost_measurement/equity_cost_20261122.json` `spread_aggregate.measured_cost_per_side_used_bp`].
- **Mutual fund: `UNMEASURED`.** No mutual-fund instrument, spread, or fee schedule exists in this programme: `findmutualfunds2/` holds only three PHP scripts, and `reports/capacity_20261122.json` records MUTUAL_FUND as `INSUFFICIENT_MEASUREMENT` ("order-book depth / all-in cost for this asset class was never measured"). A published expense ratio is **not** assumed, in either direction.

**Verdict:** on measured evidence the **low-cost ETF wins** the vehicle comparison (6.7122 bp beats the 8.0325 bp index-proxy median and the 12.0749 bp upper bound for direct equity trading, and it needs one position instead of N). The **mutual-fund leg is unanswerable** without a fee schedule this programme does not have. This is a statement about *vehicle cost for a passive exposure*, not a recommendation to buy anything.

### 2.2 BOND / MUTUAL_FUND (ETA 15)

Verified against [`reports/bond_momentum_20261122.json`](reports/bond_momentum_20261122.json) (`tests.*.metrics`, `pf_base`, `breakeven_bp_per_side_sharpe_zero` at line 183):

| variant | PF | Sharpe vs rf | maxDD | CAGR | skew | time in market |
|---|---|---|---|---|---|---|
| B1 time-series long-only | **1.3121** | **−0.5497** | **−5.81%** | **+1.631%** | −0.2413 | 89.8% |
| B2 cross-sectional L/S | **0.7431** | **−1.6985** | −5.31% | **−1.28%** | −0.5028 | (n/r) |
| B3 duration timing → TLT | **0.7366** | **−1.0628** | −11.64% | **−2.05%** | **−1.4523** | 34.7% |

Break-even is **0 bp/side** on all three (line 183), so they lose even free, and the backtest's own cost basis is "5 bp/side **ASSUMED**", not measured. The paraphrases in the brief (B1 PF 1.312 / −0.550 / −5.81% / +1.63%; B2 0.743 / −1.699 / −1.28%; B3 0.737 / −1.063 / skew −1.452) **match the JSON exactly**. Verified extra: B3's maxDD (−11.64%) and B2's maxDD (−5.31%) are the two figures the paraphrase omitted.

Bootstrap excess vs SPY excludes zero on the negative side for all three (B1 [−30.00%, −4.14%]; B2 [−35.57%, −4.25%]; B3 [−35.48%, −6.01%]).

**Verdict:** fails gate (2) at **any** cost. Mutual-fund exposure: `UNMEASURED` (no fee data) → cannot rank.

### 2.3 CRYPTO (ETA 25)

The only live paper pilot is `crypto_intraday_sim` ([`verified_strategies/paper_pilot/crypto_intraday_sim_state.json`](verified_strategies/paper_pilot/crypto_intraday_sim_state.json), last run 2026-11-20T01:43Z; log `crypto_intraday_sim_paper_log.jsonl`).

- **n:** **3 rows, all OPEN, 0 CLOSED.** `n_closed = 0` in every guardrail (`vwap_reversion`, `bollinger_mr`, `btc_4h_rsi_macd`), each with judgment `no_judgment: n<20`. The pod's own hypothesis `H-2026-11-19-01` has **0 forward rows** in the confirmatory ledger [`reports/forward_observations.jsonl`](reports/forward_observations.jsonl) (432 lines; 430 are on non-pod H-119).

> **Update 2026-11-23:** the pilot log now shows 5 CLOSE rows (close dates 2026-11-20 to 2026-11-22; entry timestamps 2026-11-19T16:00Z to 2026-11-20T20:00Z). The "0 closed" figure was accurate when written; see `verified_strategies/paper_pilot/crypto_intraday_sim_paper_log.jsonl` on `origin/main` (12 rows: 5 CLOSE, 7 OPEN). The verdict below is unchanged: 5 closes is far below the n >= 100 gate, so the class remains `PENDING_N`.
- **Net PF CI-LB:** `UNMEASURED` — with zero closed rows there is no PF, hence no CI. (The pre-lag lab PF was 1.323; the lagged replay was 0.957 [`reports/hypothesis_registry.json` H-2026-11-19-01].)
- **IR vs matched BTC/ETH benchmark:** `UNMEASURED` (no closed rows).
- **Kill triggers** (frozen in [`12_OBSERVE_TO_PRE_REGISTERED_DECISION_MEMO_2026-11-22.md`](docs/edge_research/12_OBSERVE_TO_PRE_REGISTERED_DECISION_MEMO_2026-11-22.md:112)): **not fired, and not evaluable** — `n` is too small for every clause. The day-30 / day-60 CI-LB check cannot be run without closes; the n ≥ 100 clause needs 100 closed rows.
- **Earliest resolution:** the day-30 checkpoint from registration (2026-11-19) is **2026-12-19**, day-60 is **2027-01-18**; the date for n ≥ 100 is `UNMEASURED` (0 closes so far, no observed close rate).

**Verdict: `PENDING_N`**, not ranked.

Context, not a candidate: the non-pod lead H-119 has 430 ledger rows, all backfilled and quarantined; its gates fail (net PF CI-LB **0.9213** ≤ 1.0, IR **0.043** < 0.5, benchmark coverage 0.798 < 0.90) and it is marked non-promotable [`docs/edge_research/13_H119_LIVE_VERIFICATION_2026-11-22.md`]. Separately, the crypto intraday mean-reversion family is dead: PF 0.815 at 0 bp and 0.691 at 20 bp RT [`docs/edge_research/14_CRYPTO_INTRADAY_MEANREV_2026-11-22.md`].

### 2.4 MEME (ETA 10)

From [`class_cost_20261122.json`](reports/equity_cost_measurement/class_cost_20261122.json) `classes.MEME`:
- **DOGE-USD 6.7938 bp** — quotable (10.3% zero-range bars, `suspect: false`);
- **SHIB-USD 0.00 bp** — **tick-truncated**: 84.3% zero-range bars, only 53/55 distinct high/low values, `suspect: true`; the artifact itself says this 0.00 must NOT be quoted as a zero spread;
- **PEPE-USD** — blocked, reason `empty` (no data).

**Quotable count = 1.** Frozen rule: kill if fewer than 2 quotable names. **1 < 2 → KILLED.** No MEME strategy backtest attempted.

### 2.5 PENNY_STOCK (ETA 10)

`classes.PENNY_STOCK.aggregate = null`, universe `[]`, blocked `NO_INSTRUMENT_IN_REPO` ("an empty universe stays empty; no number is borrowed from another class") [`class_cost_20261122.json`]. Frozen rule: kill if none quotable. **0 quotable → KILLED.**

### 2.6 SPORTS (ETA 15)

Exact searches run, and what each returned:
- `ls reports/ | grep -i sport` → 15 documents (April–June 2026 odds/settlement audits and manual pick verifications), e.g. `SPORTS_DEVIG_EV_VERDICT_2026-06-22.md`, `MANUAL_SPORTS_PICKS_VERIFICATION_*.json`, `SPORTSBET_DB_AUDIT_*`.
- `grep -rl 'SPORTS' reports/ --include='*.json'` → only `hypothesis_registry.json` and `session_feedback_swarm_2026_05_12.json`.
- `class_cost_20261122.json` → `'SPORTS' in classes` is **False** (only ETF, INDEX_alias_of_ETF, MEME, PENNY_STOCK are measured).
- `ls docs/edge_research/*SPORT*` → nothing.
- Field scan of the three `MANUAL_SPORTS_PICKS_VERIFICATION_*.json` → counts of `spread`, `vig`, `margin`, `commission`, `cost` are **all 0**.

**Correction to the expected label, stated rather than smoothed over:** this is **not** strictly `KILLED_NO_DATA`, because historical odds data does exist. What is absent is a **measured price of participation** (bookmaker margin or exchange fee) and any data with closing lines or settled outcomes. The one study that ran on it found no confirmable edge: n=1,039 +EV bets over 46 events, ROI +8.68% point but **event-clustered CI-LB −9.1%**, n_events 46 < 100, stale-snapshot odds [`reports/SPORTS_DEVIG_EV_VERDICT_2026-06-22.md`].

**Verdict: `KILLED_NO_COST`** (no cost figure, no confirmable edge; the plan's rule "kill if no dataset **and** no cost figure" is satisfied on the cost limb and the data limb is refuted rather than empty). Not ranked.

---

## 3. Where the two tallies meet

The programme's 14-row strategy tally is enforced at `0 INVESTABLE / 11 NOT_INVESTABLE / 3 UNKNOWN (14 rows)` and this document does not alter it: its 12-row table is a *class* view, not a strategy-row view, so the two are different row sets and not in conflict. No new tally claim is introduced here. (The split is disputed in older documents; the 14-row total is not.)

---

## 4. `UNMEASURED` register

| Item | Why it is unmeasured |
|---|---|
| Bond cost | No bond spread measurement; the backtest used 5 bp/side **assumed**. |
| Mutual-fund cost / expense ratio | No mutual-fund instrument or fee schedule in the repo (`findmutualfunds2/` is 3 PHP scripts; capacity report: `INSUFFICIENT_MEASUREMENT`). |
| Commodity / futures cost | No per-contract commission or tick measurement; series are roll-corrupted. |
| Penny-stock cost | Empty universe, `aggregate: null`. |
| Sports margin / fee | No bookmaker margin or exchange fee captured; odds are a stale snapshot. |
| Crypto forward net PF, CI-LB, IR | 0 closed pilot rows. |
| 2×-cost survival for ETF / INDEX / MEME / PENNY / SPORTS / FX CARRY | No strategy (or no cost) to run the stress against; stress numbers are quoted where they exist. |
| `IR` for every class | No matched-benchmark forward series was computed for any class in this window. |
| `LB(c)` for all 12 | Gate (4) fails, so the ranking key is undefined. |

## 5. Corrections to prior summaries

1. **Verified unchanged:** ETF per-name spreads, median 6.7122, max/min 37.2775; INDEX 8.0325 and its four names; MEME SHIB 84.3% zero-range; PENNY `aggregate: null`; B1/B2/B3 PF, Sharpe, maxDD, CAGR, skew; bond break-even 0 bp/side.
2. **Path detail, not a number change:** the per-name ETF spreads live at `classes.ETF.aggregate.range_ub_rt_bp.per_name_rt_bp`, not directly under `aggregate`.
3. **SPORTS label:** the expected `KILLED_NO_DATA` is refined to `KILLED_NO_COST`, because odds data exists while cost does not (searches above).
4. **Unreconciled, both stated:** for H-119, doc 12 reports "recomputed PF CI-LB 0.775–0.850" while doc 13 reports "net PF CI-LB 0.9213". These are different computations at different dates; I did not reconcile them and I quote both rather than pick one.

---

PROVENANCE: one file, authored 2026-11-23 in this session; every figure traced to `reports/equity_cost_measurement/class_cost_20261122.json`, `reports/equity_cost_measurement/equity_cost_20261122.json`, `reports/bond_momentum_20261122.json`, `reports/cost_measurement_20261122.json`, `reports/funding_carry_opportunity_frequency_20261122.json`, `reports/fx_carry_20261122.json`, `reports/forward_observations.jsonl`, `reports/hypothesis_registry.json`, `reports/capacity_20261122.json`, `verified_strategies/paper_pilot/*`, `docs/edge_research/12,13,14,24_*.md` or written `UNMEASURED`.
