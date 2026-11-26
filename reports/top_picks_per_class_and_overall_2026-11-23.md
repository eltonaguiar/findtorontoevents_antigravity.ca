# Top picks per asset class, and the overall ranking

**2026-11-23 · buffy (freebuff) · paper only · zero capital sanctioned · not investment advice**
**Evidence:** the committed 40-cell sweep `reports/2026-11-22-per-class-edge-results.md` (2012-01-02 →
2026-11-22, window ends 2026-11-19 on the cached closes). Nothing below is a new backtest; every
number is read from an artifact that already existed and is cited on the line.

---

## 1. The answer, before the tables

**Classes ranked: 10 ranked, 4 untested. Picks worth spending money on: zero.**
Every class fails at least one gate, and no class has a forward-tested record.

If the question is "what would I fund first if I had to fund something", the order is:

| # | what | size | why it is first |
|---|---|---|---|
| 1 | **Cash / T-bills 4.32%** | the default | it is the bar every other row is measured against, and it cost nothing |
| 2 | **H-201 equity: XLV + KO + MSFT long** | candidate, paper | the only cell with a measured cost, a positive cost-stressed CI-LB, and n=179 |
| 3 | **Vol-targeted 60/40** | risk control only | the drawdown cut replicated out of sample; the return gain did not |
| 4 | **R4b ETF clock** | paper, day 15/20 | an independent refutation instrument, not a confirmation one |
| 5 | **BTCUSDT carry** | 0% | real mechanism, fee tier unmeasured, so it cannot be sized |

Nothing above #2 is an investment. #2 is a CANDIDATE_SURVIVORSHIP_FLAGGED with one gate still
failing; it is a research position, not a recommendation.

---

## 2. The variables it was tested against

Ranking key is **not** profit. It is distance to investable, scored on nine things at once:

| variable | what it catches | where |
|---|---|---|
| round-trip cost, **measured** per class | a signal that pays the broker | `reports/equity_cost_measurement/class_cost_20261122.json` |
| **2× cost stress** | signals that only survive subsidised execution | `CI-LB @2×` column |
| **benchmark excess** vs buy-and-hold of its own universe | the class doing the work, not the rule | `excess vs bench` |
| **CI-LB** one-sided 95% lower bound on net daily return | point estimates that hide their variance | bootstrap column |
| **halves stability** (first half / second half) | one-regime luck | `halves` column |
| **DSR multiplicity** at N=29 declared, PBO 0.345 | 40 cells examined, one near-pass | `DSR` column |
| **vol-matched** comparison (G6b) | returns that are just beta | matched-vol table |
| **data integrity audit** | roll gaps / negative prints faking a verdict | COMMODITY section |
| **forward clock** (G8: n ≥ 100 closed forward trades) | everything, until it exists | — |

`PBO(CSCV) = 0.345`, expected max daily Sharpe **0.04695**, n_trials **29**. A cell must clear all of
it; **0 of 40 cells cleared every backtest gate** and 0 cleared vol-matched. That is the headline.

---

## 3. Per-class ranking

Ordered by the best cell in each class, with the gate it actually failed.

| rank | class | best cell | n | net bp/day | CI-LB | @2× | DSR | verdict | failed on |
|---|---|---|---|---|---|---|---|---|---|
| 1 | **EQUITY** | H-201 xsmom_top3_6m | 179 | 11.521 | **+7.246** | +7.002 | 0.9469 | FAILS_MULTIPLICITY | DSR 0.9469 vs 0.95; needs 137 more days |
| 2 | **CRYPTO** | H-206 tsmom_6m_long_flat | 60 | 15.911 | +8.452 | +7.913 | 0.7752 | FAILS_BENCHMARK | bench CAGR 31.75% vs 35.94%; MDD −64.9% |
| 3 | **ETF** | H-205 xsmom_top3_6m | 179 | 5.053 | +2.007 | +1.730 | 0.5152 | FAILS_BENCHMARK | bench CAGR 13.97% vs 11.97% |
| 4 | **INDEX** | H-221 xsmom_top2_6m | 179 | 4.644 | +1.613 | +1.357 | 0.4553 | FAILS_BENCHMARK | tracks its own universe |
| 5 | **MUTUAL_FUND** | H-216 tsmom VFIAX | 28 | 3.875 | +1.286 | +1.132 | 0.3598 | INSUFFICIENT_N / BENCHMARK | n=28; bench 13.97% vs 9.02% |
| 6 | **FUTURES** | H-218 xsmom_top2_6m | 179 | 2.806 | +0.186 | **−0.054** | 0.1474 | FAILS_2X_COST | cost binds at 1.8× |
| 7 | **BOND** | H-213 xsmom_top2_6m | 179 | 0.776 | **−0.453** | −0.659 | 0.0382 | REFUTED_OR_WEAK | negative before any cost |
| 8 | **COMMODITY** | H-210 tsmom GC=F | 48 | 1.904 | −0.724 | −1.132 | 0.0697 | DATA_INTEGRITY_FAIL | CL=F negative print; NG=F roll spikes |
| 9 | **FOREX** | H-208 USDJPY tsmom_ls | 121 | 1.211 | −0.520 | −0.827 | 0.0587 | REFUTED_OR_WEAK | 926-trade portfolio CI-LB −0.858 |
| 10 | **PENNY_STOCK** | H-219 xsmom_top2_6m | 179 | 4.565 | **−8.636** | −8.898 | 0.0123 | REFUTED_OR_WEAK | worst CI-LB in the sweep |

**Untested, therefore UNKNOWN (not dead):** MEMECOIN, OPTIONS, PREDICTION_MARKET, PRIVATE_CREDIT.
No pre-registered cell exists for any of them, so no verdict is available and none is claimed.

### Top 5 per class, where five cells exist

**EQUITY (13 cells pre-registered)** — 1. H-201 xsmom_top3_6m, CI-LB +7.246, n=179.
2. H-200:NVDA tsmom_12_1, +8.727 but n=13 → INSUFFICIENT_N. 3. H-200:AMZN +2.987 (n=32).
4. H-200:META +1.592 (n=33). 5. H-200:MSFT +2.619 (n=23, INSUFFICIENT_N).
Only #1 has the sample size to be read; the rest are anecdotes with error bars.

**FOREX (7)** — 1. USDJPY=X +1.211 (CI-LB −0.52). 2. AUDUSD=X +0.133. 3. tsmom_ls_portfolio
+0.103 (n=926, CI-LB −0.858). 4. H-209 xsmom_top2_3m +0.076. 5. USDCAD=X −0.074.
Every one has a negative lower bound. Best of a refuted set is still refuted.

**COMMODITY (4)** — 1. GC=F +1.904. 2. H-211 xsmom_top2_6m +2.377 (CI-LB −3.757). 3. H-223 basket
+0.361. 4. H-224 ETF basket +1.114. All marked DATA_INTEGRITY_FAIL or REFUTED.

**CRYPTO (4)** — 1. H-206 tsmom_6m +15.911. 2. H-207 xsmom_top3_3m +12.470. 3. H-228 funding carry
+0.925 (CI-LB +0.143, **−0.857 at 2×**). 4. H-227 xsmom_ls −1.269.
**ETF, BOND, MF, INDEX, FUTURES, PENNY have only 2 cells each** — a top-5 would be invented, so only
the cells that exist are listed.

---

## 4. Why the winners win, and why they still lose

**EQUITY H-201** is the strongest row in the estate on every axis except the one that decides:
n=179, PF 2.7395, mean trade 2.3546%, CI-LB +7.246 bp/day, both halves positive [9.991, 13.051],
and at **2× cost CI-LB is still +7.002** — cost would have to rise **30.7× to a 614 bp round trip**
to bind. It loses on **multiplicity**: DSR 0.9469 against a 0.95 bar, and **0.9490 even at N=28**
with the series' own skew (−0.050) and kurtosis (12.254). It clears only at **N ≤ 27** while 30–31
trials are declared. The second loss is the honest one: **vol-matched CI-LB is −0.533**, i.e. scaled
to SPY's volatility the excess turns negative — the shape of a beta proxy, not a premium. CAGR 29.6%
vs 13.97% for the benchmark sounds decisive until you see MDD −36.94% vs −33.72% at 24.85% vol
against 16.56%. It is leveraged beta until proven otherwise, and the PIT universe
(`PARTIAL_NON_DELISTING_AWARE`) cannot yet prove otherwise.

**CRYPTO H-206** has the biggest raw number (15.911 bp/day) and the biggest drawdown (−64.9%). It
beats buy-and-hold on both CAGR (35.94% vs 31.75%) and MDD (−64.9% vs −83.4%) — the only class where
the rule genuinely improves on its universe — but the CI-LB at matched vol is **−3.277**, and n=60
with DSR 0.7752. This is the most interesting row for a future pod and the least fundable today:
crypto volatility, 2% funding-carry allocation, no fee tier measured.

**FUTURES** is the clean cost story: CI-LB 0.186 bp/day against an 18 bp floor. Its MDE is 4.32
bp/day — the cell sits at its own detection limit, so it can neither pass nor be retired.

**BOND/FOREX/PENNY** were never cost stories. Their lower bounds are negative before costs are
mentioned, which means the signal is absent, not expensive.

---

## 5. Fees, minimums and maintenance — the mutual-fund question

You expected mutual funds among the winners. Measured, they are **5th of 10**, and their failure is
structural rather than statistical. This is the number that settles it:

| vehicle | round-trip cost | source |
|---|---|---|
| **ETF** | **6.7122 bp** median, 14 names (SHY 0.6144 … SOXX 22.9049, max/min 37.28) | `class_cost_20261122.json` |
| broad index ETF proxy | 8.0325 bp (SPY 8.3139, QQQ 12.0749, IWM 7.7512, DIA 5.5896) | same |
| **direct equity** | **12.0749 bp** (6.0375/side, 13 symbols, Corwin-Schultz 1.5033) | `equity_cost_20261122.json` |
| mutual fund | **UNMEASURED** — no fee schedule in this repo | — |
| crypto | 20 bp assumed by design (understated); live books priced **42.64 bp** retail taker | `reports/2026-11-22-cost-is-the-constraint.md` |
| forex / futures / commodity | 5 / 10 / 15 bp assumed | sweep header |

And the gates `alpha_engine/mf_screener.py` already imposes before a fund is admissible at all:
expense ratio **≤ 0.09%** index or ≤ 0.20% active, **no load, no 12b-1**, minimum initial
**≤ $3,000** (Admiral class counts), AUM **≥ $1B**, turnover **≤ 20%**, tracking error **≤ 0.25%**,
track record **≥ 10 years**, NAV freshness **≤ 24h**.

Three findings follow, and they are the answer to the fee question:

1. **The expense ratio is not the problem — the benchmark is.** Best MF cell H-216 (VFIAX) earns
   9.02% CAGR against **13.97%** for buy-and-hold of its own universe; H-220 earns 8.86% at n=179.
   Paying 9 bp instead of 3 bp does not close a 495 bp/yr gap. A fee cut cannot rescue a selection
   rule that underperforms the thing it selects from.
2. **Mutual funds cannot support a trading edge at all.** Daily NAV, next-day execution — the note
   on the sweep says it outright: they "can support a fund-selection rule, not a trading edge." Any
   rule with an intraday exit, TP or SL is unimplementable in this vehicle.
3. **For the same exposure, the ETF is strictly better.** Same beta, **6.7122 bp** instead of an
   unmeasured fee plus a $3,000 minimum, no lockup, intraday exit available, 1/37th the per-unit
   cost spread of the worst ETF and still cheaper than every alternative above. **The mutual fund is
   dominated, not merely worse.** If you want the VFIAX exposure, the honest vehicle is the ETF
   share class of the same index.

Minimums and maintenance do not decide the ranking here — they are a *tie-breaker that never gets
used*, because the class is already eliminated on benchmark excess and executability. Where they
would matter is capital below the $3,000 gate, and at that size the 4.32% T-bill is the correct
answer anyway.

---

## 6. What the machine-learning systems actually measured

Four ML families exist in the estate. None has demonstrated out-of-sample edge, and the audit
`crypto_ml_edge/AUDIT.md` says so in its own words:

| system | measured result | read |
|---|---|---|
| ML Crypto Predictor v1.2 (forward) | **Sharpe −2.799**, WR 23.5%, PF 0.20, 34 picks | the untrained Simpleton baseline beat it 5× (51.3% WR, Sharpe 0.567) |
| v4 Supertrend "proof" | 6 pairs pass with **5–11 trades** each | not significant; at 7 trades, 71.4% WR gives p = 0.164 |
| **Gainer ML** (`claude_gainer_ml`) | **ROC-AUC 0.537**, precision 0.19, positive rate 0.7% | explains 3.7% of variance over random; 81 of every 100 buy signals wrong |
| GRU/CNN/attention (v3) | best avg_score 0.4128, no head-to-head significant | deep learning adds parameters, not edge |

**Root cause, and it is not the models:** the validation code (DSR, CPCV, PBO, Monte Carlo) was
correct and present, but picks were gated on `probability > 0.55` and nothing else. A model with AUC
0.27 could emit 0.58 and become a pick. Second cause: the triple-barrier labels were adaptively
forced to a 15–30% positive rate, which in practice produced **45–50%** positives — a coin-flip
target no model can learn from.

So when the question is "should we trust the ML algorithms with money", the measured answer is no,
and the reason is a validation-production gap that is now documented rather than suspected.

---

## 7. Reverse-engineering the top gainers — daily, weekly, monthly

This has been attempted three times, at three horizons. Two are measured. The third is not yet
powered, and I can say why arithmetically.

### Daily — measured, null

`crypto_ml_edge/gainer_detector.py` (12 pre-pump features, strictly pre-event bars, walk-forward +
DSR gate) and `claude_gainer_ml` (12,000 train / 3,000 test, 1d+4h CoinGecko): **AUC 0.537**,
precision 0.19 at a 0.7% base rate. Binary "will this be a top gainer" against all coins is an
underdefined question — 99.3% of coin-days are not gainers, so a model can be 98.9% "accurate" and
worthless.

### Weekly — measured, null, and this is the strongest result of the three

`tools/weekly_winner_reverse_engineer.py`, run to `reports/weekly_winners_2026-11-15.md`. Features
as of each Friday close, target the **next** week's return, nothing fitted on the week it scores.
Crypto: 37 symbols × **105 weeks**. Equity: 79 symbols × 104 weeks.

| class | best in-sample feature | IC | t | holdout top-5 precision | base rate | lift |
|---|---|---|---|---|---|---|
| CRYPTO | `vol1m` (negative) | −0.120 | −4.04 | 0.215 | 0.216 | **1.0×** |
| CRYPTO | `dollar_vol` | +0.103 | +4.67 | — | — | — |
| EQUITY | `dollar_vol` | +0.026 | +1.16 | 0.219 | 0.203 | **1.08×** |

This is the cleanest possible demonstration of the trap: `vol1m` has a **t of −4.04**, which looks
like a discovery, and the holdout model built on it lands winners at exactly the base rate —
**1.0× lift**, and its in-sample IC **flips sign** on holdout (train −0.0724). A significant IC is not
a tradeable ranking. Naming the top 5 of the next week is indistinguishable from picking 5 at random.

**And the universe point matters more than the model point.** The actual crypto weekly leaders that
week were AKE +78.3% at a **$237M** market cap, OZO +65.0% at **$208M**, PIEVERSE +26.6% at **$515M**
— microcaps absent from the 37-symbol liquid panel. "Predict the top gainers" is a universe problem
before it is a prediction problem: the names that gain 78% are exactly the names a $25k-per-leg book
cannot enter without becoming the move.

### Monthly — not run, and not yet runnable

The tool is weekly-only, and that is not the binding constraint — data is. The price source is
yfinance `period="2y"`, so 105 weeks ≈ **24 monthly observations**. At a base rate of 0.135
(5 of 37) and a target lift of 2× (0.27), a one-sided test at 5% with 80% power needs

```
n = (( z.95·√(p0(1−p0)) + z.80·√(p1(1−p1)) ) / (p1−p0))²
  = (( 1.645·0.3417 + 0.8416·0.4440 ) / 0.135)²  =  6.932²  ≈  48 observations
```

**48 months, i.e. 4 years, to detect a doubling of the selection rate.** 24 months is half of that,
so a monthly result produced today would be a coin flip dressed as a finding — the same error as
quoting "60 months" as the date the ETF question gets answered (see
`reports/r4b_power_2026-11-23.md`: at n=60 the CONFIRM bar is 13.2%/yr and the power at a hurdle-sized
edge is 5%).

### What I would do next, and what it costs

Pre-register **one** monthly-gainer hypothesis per class (crypto, equity) against `dollar_vol` +
`vol1m` — the two features that survived at weekly — require ≥ 48 monthly observations from a
survivorship-free source, and report the holdout top-5 precision with its own CI. Until the data
window reaches 4 years, the honest answer is the measured weekly null, and running it anyway would
spend a trial to buy a guess. I am not going to do that quietly to produce a table.

---

## 8. So what is worth spending money on

Ranked by evidence, not by ambition:

1. **Cash at 4.32%.** It wins by default and costs nothing. Every row above is measured against it.
2. **Nothing else at real money.** Ten classes ranked, ten eliminated, four untested. If a desk needs
   a number to act on, the number is "not yet".
3. **For a paper pod only:** H-201's three names (XLV, KO, MSFT), the R4b clock, and the carry at 0%.
   Their value is that they are cheap to run and honest to fail.
4. **The one upgrade with a replicated mechanism:** volatility targeting. C-014 on 60/40: max DD
   −30.04% → −22.03%, and it held in three disjoint books. Its return half was **refuted OOS**
   (+1.14pp, CI [−0.87, +3.09]), so it is sold as drawdown insurance, never as alpha.

## 9. Limits

No fill prices exist anywhere in the estate (`entry_price` stored, `fill_price` not); equity cost is
disputed (12.0749 bp measured vs 1–5 bp claimed elsewhere on 191 names) and flagged rather than
reconciled; PIT is `PARTIAL_NON_DELISTING_AWARE`; crypto costs are assumed 20 bp and understated by
design; MEMECOIN/OPTIONS/PREDICTION_MARKET/PRIVATE_CREDIT have no cell and no verdict; and the 4.32%
T-bill reference moves with rates, which would re-rank the bottom half and not the top.
