# 19 — The honest verdict: would we invest, and if not, what is worth watching

**Date:** 2026-11-22
**Programme item:** 39 (synthesis only — no new backtest, no new data pull, no new analysis was run for this document)
**Purpose:** a reader is deciding whether to put real money into any of this. This document is written for that reader, not as a summary of effort.

**Sources consolidated (read, not recalled):**
[`15_PROGRAMME_SCOREBOARD_2026-11-22.md`](docs/edge_research/15_PROGRAMME_SCOREBOARD_2026-11-22.md) ·
[`05_REAL_COST_MEASUREMENT_2026-11-22.md`](docs/edge_research/05_REAL_COST_MEASUREMENT_2026-11-22.md) ·
[`06_FUNDING_CARRY_2026-11-22.md`](docs/edge_research/06_FUNDING_CARRY_2026-11-22.md) ·
[`07_HURDLE_RATES_2026-11-22.md`](docs/edge_research/07_HURDLE_RATES_2026-11-22.md) ·
[`08_CARRY_AND_MOMENTUM_2026-11-22.md`](docs/edge_research/08_CARRY_AND_MOMENTUM_2026-11-22.md) ·
[`10_SURVIVORSHIP_AUDIT_2026-11-22.md`](docs/edge_research/10_SURVIVORSHIP_AUDIT_2026-11-22.md) ·
[`14_CRYPTO_INTRADAY_MEANREV_2026-11-22.md`](docs/edge_research/14_CRYPTO_INTRADAY_MEANREV_2026-11-22.md) ·
[`16_COMMODITY_AND_BOND_MOMENTUM_2026-11-22.md`](docs/edge_research/16_COMMODITY_AND_BOND_MOMENTUM_2026-11-22.md) ·
[`18_CAPACITY_COMBINED_BOOK_COUNTERFACTUAL_2026-11-22.md`](docs/edge_research/18_CAPACITY_COMBINED_BOOK_COUNTERFACTUAL_2026-11-22.md) ·
[`03_P0_FORWARD_CLOCK_STRUCTURAL_BLOCK_2026-11-22.md`](docs/edge_research/03_P0_FORWARD_CLOCK_STRUCTURAL_BLOCK_2026-11-22.md) ·
`reports/capacity_20261122.json` · `reports/combined_book_20261122.json` · `reports/no_trade_counterfactual_20261122.json`

**The hurdle used throughout:** US 3-month T-bill **4.32%** (2026-11-20, Treasury daily yield curve CSV, column "3 Mo"; FRED `DTB3` cross-check 4.16% on 2026-11-19) [`07_HURDLE_RATES_2026-11-22.md`](docs/edge_research/07_HURDLE_RATES_2026-11-22.md:20). To beat SPY needs Sharpe **1.114**; SPY measured over the 79-symbol panel window (2021-11-22 → 2026-11-19) delivered **CAGR 10.42%, vol 17.39%, Sharpe-vs-rf 0.351** [same doc, lines 83–87].

---

## 1. The answer

**No. We would not invest today.** Thirteen strategies were tested, twelve were killed, and the one that survived cannot beat a US 3-month T-bill paying **4.32%** at the holding period that actually occurs: it needs **16.398 days** to amortise a **45.524 bp** round trip, while a positive-funding episode typically lasts about **2 days** [`06_FUNDING_CARRY_2026-11-22.md`](docs/edge_research/06_FUNDING_CARRY_2026-11-22.md:196) [`18_CAPACITY_COMBINED_BOOK_COUNTERFACTUAL_2026-11-22.md`](docs/edge_research/18_CAPACITY_COMBINED_BOOK_COUNTERFACTUAL_2026-11-22.md:97). The decisive reason, in one line: **nothing tested has a positive, measured, cost-paid return above 4.32%, and the only survivor is below it at the hold that occurs.**

---

## 2. What we would deploy $1 into today

**A US 3-month T-bill at 4.32%** [`07_HURDLE_RATES_2026-11-22.md`](docs/edge_research/07_HURDLE_RATES_2026-11-22.md:20).

That is not a cop-out, and the reason it is not is the whole result of this programme:

- **It is the comparison that was actually run.** Every strategy in this programme was judged against `rf + hurdle × vol` with rf = 4.32%, not against zero [`07_HURDLE_RATES_2026-11-22.md`](docs/edge_research/07_HURDLE_RATES_2026-11-22.md:59-75). Zero of thirteen cleared it [`18_CAPACITY_COMBINED_BOOK_COUNTERFACTUAL_2026-11-22.md`](docs/edge_research/18_CAPACITY_COMBINED_BOOK_COUNTERFACTUAL_2026-11-22.md:12).
- **The combined book says 100% cash is optimal.** Equal-weight blending with cash cannot raise excess Sharpe: `(μ − r_f)/s` is independent of the weight `w`, so when `μ − r_f ≤ 0` the optimum is `w = 0` [`18_CAPACITY_COMBINED_BOOK_COUNTERFACTUAL_2026-11-22.md`](docs/edge_research/18_CAPACITY_COMBINED_BOOK_COUNTERFACTUAL_2026-11-22.md:130-157). Funding carry's excess Sharpe over cash is **−0.44 at H30** and **+0.23 at H90** (against 4.32% T-bill), and SPY's measured Sharpe is 0.351.
- **The live system has already lost to cash.** Over 278 days (2026-02-17 → 2026-11-22), 10,968 resolved closed picks net of the measured class cost model returned **mean −0.1524% per trade** (win rate 43.14%, sum −1,671%, per-trade Sharpe −0.037), while T-bills returned **+3.29%** and SPY **+1.81%** over the identical window [`18_CAPACITY_COMBINED_BOOK_COUNTERFACTUAL_2026-11-22.md`](docs/edge_research/18_CAPACITY_COMBINED_BOOK_COUNTERFACTUAL_2026-11-22.md:181-190).

Putting $1 into any tested strategy would be a measured choice to earn less than 4.32%, and in the L/S and mean-reversion cases a choice to lose money. The only thing that would change the $1 answer is one of the three items in §5.

---

## 3. The one thing worth watching

**Funding carry (delta-neutral long spot / short perp).** It is the only non-negative result and the only thing in this programme with a real, measured premium behind it: gross **+7.93% APR** (equal-weight mean) against a **4.32%** T-bill over 6.2–7.2 years of real 8 h funding [`06_FUNDING_CARRY_2026-11-22.md`](docs/edge_research/06_FUNDING_CARRY_2026-11-22.md:148-155). The median-based gross is **8.16% APR** against **4.32%** [`18_CAPACITY_COMBINED_BOOK_COUNTERFACTUAL_2026-11-22.md`](docs/edge_research/18_CAPACITY_COMBINED_BOOK_COUNTERFACTUAL_2026-11-22.md:91). Even the gross premium is thin against 4.32%, and net is what counts:

| Hold | Net APR (1× cost) | vs 4.32% T-bill |
|---|---|---|
| 1 day | −158.07% | below |
| 3 days | −47.82% | below |
| 7 days | −15.60% | below |
| 14 days | −3.73% | below |
| 30 days | **+2.42%** | **below** |
| 90 days | **+6.24%** | above (tail only) |

[`06_FUNDING_CARRY_2026-11-22.md`](docs/edge_research/06_FUNDING_CARRY_2026-11-22.md:187-194)

### The conditions under which it becomes investable, with the numbers that must be true

**Condition 1 — a hold long enough to amortise 45.524 bp, i.e. a persistent funding regime, not a 2-day episode.**
- Break-even hold at median funding: **16.398 days** [`06_FUNDING_CARRY_2026-11-22.md`](docs/edge_research/06_FUNDING_CARRY_2026-11-22.md:199) (14.56 d at the mean; empirically the first positive hold on the grid is 30 d at 1×, 90 d at 2×).
- Median positive-funding episode: **1.93 days** [`18_CAPACITY_COMBINED_BOOK_COUNTERFACTUAL_2026-11-22.md`](docs/edge_research/18_CAPACITY_COMBINED_BOOK_COUNTERFACTUAL_2026-11-22.md:97) / **2.33 days** [`15_PROGRAMME_SCOREBOARD_2026-11-22.md`](docs/edge_research/15_PROGRAMME_SCOREBOARD_2026-11-22.md:35) / per-symbol **1.3–2.3 days** [`06_FUNDING_CARRY_2026-11-22.md`](docs/edge_research/06_FUNDING_CARRY_2026-11-22.md:216-222) (see §8 on the discrepancy).
- **What must be true:** the median episode must be ≥ **16.4 days**, i.e. ~7–8× longer than observed. Alternatively, a regime filter that reliably selects multi-week high-funding periods. No such filter is demonstrated: the one tested (enter while trailing 24 h funding > 0) is *worse* than always-on and is net-negative per episode on every symbol [`06_FUNDING_CARRY_2026-11-22.md`](docs/edge_research/06_FUNDING_CARRY_2026-11-22.md:213-230).
- **What must be true about the funding level:** the last-12-month gross is only **1.75% APR** against a **4.32%** T-bill (BTC compressed from +2.80 bp/8 h in 2021 to **+0.30 bp/8 h in 2026**) [`18_CAPACITY_COMBINED_BOOK_COUNTERFACTUAL_2026-11-22.md`](docs/edge_research/18_CAPACITY_COMBINED_BOOK_COUNTERFACTUAL_2026-11-22.md:91-93). At the current regime, even zero cost would not clear 4.32%.

**Condition 2 — maker or fee-tier execution to cut the four taker fills.**
- Pair round trip is **45.524 bp at 1×** (91.048 bp at 2×): four taker fills = 2 legs × (open + close) × (10 bp fee + 2.762 bp measured spot spread, $10k) [`06_FUNDING_CARRY_2026-11-22.md`](docs/edge_research/06_FUNDING_CARRY_2026-11-22.md:128-140).
- **What must be true:** cost at or below roughly **5.4–6.5 bp** per pair for a ~2-day episode to break even (break-even scales linearly with cost: 2.776 bp/day × 1.93–2.33 d) [derived arithmetic from the sourced 45.524 bp / 16.398 d figures; the source states "maker fills … cuts the cost several-fold and the break-even hold proportionally", [`06_FUNDING_CARRY_2026-11-22.md`](docs/edge_research/06_FUNDING_CARRY_2026-11-22.md:271-274)]. That is a ~7–8.5× reduction from 45.524 bp. At 2× cost the 30-day hold is already **−3.12% APR** against **4.32%** [`06_FUNDING_CARRY_2026-11-22.md`](docs/edge_research/06_FUNDING_CARRY_2026-11-22.md:187-194).

**Condition 3 — enough capacity, which the tail case does not have.**
- Measured capacity: **≈ $29,438 per symbol**, binding on XRP/USDT, from one 3-minute Sunday window, taker execution, perp depth assumed equal to spot [`18_CAPACITY_COMBINED_BOOK_COUNTERFACTUAL_2026-11-22.md`](docs/edge_research/18_CAPACITY_COMBINED_BOOK_COUNTERFACTUAL_2026-11-22.md:53-72).
- At the 90-day tail, beating 4.32% needs **$796k (min) to $944k (median) per symbol** [`18_CAPACITY_COMBINED_BOOK_COUNTERFACTUAL_2026-11-22.md`](docs/edge_research/18_CAPACITY_COMBINED_BOOK_COUNTERFACTUAL_2026-11-22.md:101-119) — **27–32× the measured $29,438 capacity**, and only BTC's $774k cost crossover approaches it. At the median hold, **no deployed size beats the 4.32% T-bill** [same doc, line 103-108].
- **What must be true:** capacity at least an order of magnitude larger, measured across a 24/7 book rather than 3 snapshots, with perp depth actually measured.

**Standing caveat on this survivor:** the survivorship audit flags funding carry **UNSAFE** — a marginal survivor is exactly the verdict that a survivorship-flattered universe could flip [`10_SURVIVORSHIP_AUDIT_2026-11-22.md`](docs/edge_research/10_SURVIVORSHIP_AUDIT_2026-11-22.md:53-67).

---

## 4. Why each of the others is dead

Every PF below carries its cost basis. The count and its reconciliation are in §8.1.

| Strategy | Decisive number | One-line reason |
|---|---|---|
| FX momentum (63d/21d) | mean net **−36.88 bp**/trade, n=4,092, null pct 0.0 | Both legs negative; the gross itself is −26.88 bp. No cost assumption can save a negative gross. [see: [`block4_n1_low_turnover.md`](docs/edge_research/block4_n1_low_turnover.md:17) via scoreboard] |
| FX mean-reversion (5d/5d) | gross **+4.30 bp**, net **−5.70 bp** at 10 bp round trip; break-even **4.3038 bp** | The edge is smaller than any plausible FX round trip, and the window-clustered CI includes zero even at 1 bp ([−4.32, +11.09]). [see: [`05_REAL_COST_MEASUREMENT_2026-11-22.md`](docs/edge_research/05_REAL_COST_MEASUREMENT_2026-11-22.md:213-231)] |
| Equity breakout (donchian / VT pattern sweep) | **PF 0.9917 @ 25 bp/side** (1,941 trades); break-even **24.5945 bp/side**; null pct **69.8**; selection-alpha CI-LB **−0.285%** | Killed by the random-entry null and negative selection alpha, not by cost. Published PF 1.479 (cost basis not stated) is **UNREPRODUCED**; measured WR 40.6% vs published 50.2%. [`05_REAL_COST_MEASUREMENT_2026-11-22.md`](docs/edge_research/05_REAL_COST_MEASUREMENT_2026-11-22.md:252-306) [`02_DEEP_REVIEW_2026-11-22.md`](docs/edge_research/02_DEEP_REVIEW_2026-11-22.md:31) |
| FX carry (quintile) | **Sharpe −0.126 vs rf** (4.32%), skew −0.63, worst month −7.55%, maxDD −11.71%, break-even **468.5 bp**, excess vs SPY −3.04% [−8.28%, +2.29%] | Genuinely beats random ranking (98.2nd percentile) and still loses to a 4.32% T-bill. [`08_CARRY_AND_MOMENTUM_2026-11-22.md`](docs/edge_research/08_CARRY_AND_MOMENTUM_2026-11-22.md:57-107) |
| Cross-venue basis (delta-neutral) | **0.00%** of 720 minutes above break-even; Binance↔KuCoin median **−0.2427 bp** vs a **40.48 bp** threshold | The dislocation never exists: an order of magnitude short of the two-venue round trip, in every minute measured. [`08_CARRY_AND_MOMENTUM_2026-11-22.md`](docs/edge_research/08_CARRY_AND_MOMENTUM_2026-11-22.md:140-163) |
| 12-1 momentum (long/short) | **CAGR −25.45%**, maxDD **−82.3%**, skew −1.52, null pct **1.6** | 98.4% of random-rank portfolios did better. Long-only (+12.12%) is below SPY (16.64%) with a CI spanning zero; no evidence either way. [`08_CARRY_AND_MOMENTUM_2026-11-22.md`](docs/edge_research/08_CARRY_AND_MOMENTUM_2026-11-22.md:219-251) |
| Crypto intraday mean-reversion | **PF 0.815 @ 0 bp**; PF 0.691 @ 20 bp; break-even **0 bp**; null pct **0.0**; excess −50.23% [−72.37%, −30.37%]; all 10 symbols negative | It loses money before cost. No taker-fee assumption is relevant because there is no cost at which it is profitable. [`14_CRYPTO_INTRADAY_MEANREV_2026-11-22.md`](docs/edge_research/14_CRYPTO_INTRADAY_MEANREV_2026-11-22.md:132-196) |
| Commodity momentum — V1 L/S | PF **0.757 @ 5 bp/side assumed**; CAGR −7.13%; Sharpe −0.627; null pct **30.2**; excess −23.75% [−43.5%, −4.6%] | Below random rank assignment, and below cash even at zero cost (break-even **0 bp/side**). **DATA-SUSPECT** (see note). [`16_COMMODITY_AND_BOND_MOMENTUM_2026-11-22.md`](docs/edge_research/16_COMMODITY_AND_BOND_MOMENTUM_2026-11-22.md:118-171) |
| Commodity momentum — V2 long-only | PF **1.114 @ 5 bp/side assumed**; CAGR +0.47%; Sharpe −0.038; null pct **33.1** | A PF above 1 that earns less than a 4.32% T-bill: the long-only book is a metals trade with a momentum label. **DATA-SUSPECT.** [same] |
| Commodity momentum — V3 long-only + filter | PF **1.074 @ 5 bp/side assumed**; CAGR −0.67%; Sharpe −0.089; null pct **25.2** | Same failure with a filter bolted on; the filter did not help. **DATA-SUSPECT.** [same] |
| Bond momentum — B1 time-series | PF **1.312 @ 5 bp/side assumed** *alongside* Sharpe **−0.550**; null pct **2.0**; in market 89.8% of months | **PF-inflation trap:** never quote B1's PF alone. It is worse than 98% of random equal-count bond baskets and earns less than 4.32% cash. [`16_COMMODITY_AND_BOND_MOMENTUM_2026-11-22.md`](docs/edge_research/16_COMMODITY_AND_BOND_MOMENTUM_2026-11-22.md:191-229) |
| Bond momentum — B2 cross-sectional L/S | PF **0.743 @ 5 bp/side assumed**; CAGR −1.28%; Sharpe −1.699; no null declared | Loses money at every cost tested; no random null was pre-declared, so the Sharpe is the only evidence and it is decisive. [same] |
| Bond momentum — B3 duration timing (via TLT) | PF **0.737 @ 5 bp/side assumed**; CAGR −2.05%; Sharpe −1.063; skew **−1.452**; excess −19.85% [−35.5%, −6.0%] | Negative skew: 81.6% of months positive, mean month negative. It is an untradeable yield signal mapped through TLT, and it loses. [same] |

**Commodity momentum note (required caveat):** a peer note disputes the **validity of the data** (continuous front-month series roll artifacts), not the arithmetic [`17_COMS_CHECK4_BREAKEVEN_LEDGER_2026-11-22.md`](docs/edge_research/17_COMS_CHECK4_BREAKEVEN_LEDGER_2026-11-22.md:134) [`17_COMS_CHECK4_BREAKEVEN_LEDGER_2026-11-22.md`](docs/edge_research/17_COMS_CHECK4_BREAKEVEN_LEDGER_2026-11-22.md:191). The programme's own reading is that roll artifacts would *inflate* momentum, so the KILL is conservative to them, not vulnerable. Treat the result as **data-suspect** until a roll-adjusted series is used.

**Also killed earlier, in the same programme (N1 rules)** [`10_SURVIVORSHIP_AUDIT_2026-11-22.md`](docs/edge_research/10_SURVIVORSHIP_AUDIT_2026-11-22.md:89-98):
- N1 R1 12-month multi-asset momentum: CAGR 18.05%, Sharpe 0.590, null pct **61.2** → KILL.
- N1 R2 US sector momentum: CAGR 5.76%, Sharpe 0.413, excess vs SPY −11.3 pp, null pct **35.4** → KILL.
- N1 R3 SPY 200-day trend: CAGR 10.24%, Sharpe 0.861, excess −6.8 pp, null pct **53.4** → KILL.

---

## 5. The three things that would change the answer

**(a) A historical universe that includes delisted names.** Today every universe is a today's-constituents list: the 79-symbol panel has **0 series ending before the panel end and 0 starting after its start**, which is the signature of a current-constituent universe, and the only PIT approximation available leaves the universe at 79 at every date [`10_SURVIVORSHIP_AUDIT_2026-11-22.md`](docs/edge_research/10_SURVIVORSHIP_AUDIT_2026-11-22.md:20-83). **What it unlocks:** it would turn the **0.0 pp/yr** survivorship gap from a zero lower bound into an actual measurement of the upward bias. It can only hurt the KILLs (which is why they are safe), and it is the only way to trust any survivor. It is the difference between "funding carry is MARGINAL and UNSAFE" and "funding carry is MARGINAL".

**(b) A pre-registered pod with genuine forward rows.** The gate hard-codes `if status != "pre_registered": res["eligible"] = False` [`03_P0_FORWARD_CLOCK_STRUCTURAL_BLOCK_2026-11-22.md`](docs/edge_research/03_P0_FORWARD_CLOCK_STRUCTURAL_BLOCK_2026-11-22.md:34-53). Across both manifests **9 of 12 pods are `observe`**, 1 is `pre_registered`, 1 `post_hoc`, 1 `declined`; the sole `pre_registered` pod has zero forward rows; and the only hypothesis with a forward ledger (H-119, **430 rows**) has **100% backfilled** rows and no pod at all [same doc, lines 87-121] [`12_OBSERVE_TO_PRE_REGISTERED_DECISION_MEMO_2026-11-22.md`](docs/edge_research/12_OBSERVE_TO_PRE_REGISTERED_DECISION_MEMO_2026-11-22.md:80-86). **What it unlocks:** a route to a confirmatory verdict at all. Today the validation system cannot certify anything on present state; it is not waiting for the clock, because for ten pods the clock is not wired to anything that can ring.

**(c) Measured non-crypto costs.** Crypto all-in round trip is measured at **~20.0 bp** (Binance/KuCoin 10 bp taker) to **~52.0 bp** (Kraken 26 bp taker) [`05_REAL_COST_MEASUREMENT_2026-11-22.md`](docs/edge_research/05_REAL_COST_MEASUREMENT_2026-11-22.md:48-66). **Equity, ETF, FX, commodity and bond costs remain UNMEASURED**, so every non-crypto verdict is conditional on an assumption [`05_REAL_COST_MEASUREMENT_2026-11-22.md`](docs/edge_research/05_REAL_COST_MEASUREMENT_2026-11-22.md:108-152). **What it unlocks:** unconditional verdicts. For the equity breakout it would decide the one open question (break-even 24.5945 bp/side vs a real cost that is genuinely unknown); for FX it would test whether 4.3 bp is attainable at all; for bonds and commodities it would replace the 2/5/10/20 bp sweep with a number.

---

## 6. What this programme got wrong, and corrected

These are listed because a verdict is only worth what its error record is worth.

1. **An unlabelled PF of 0.992 that was 25 bp/side, not 5 bp/side.** The number was quoted without its cost basis and was read as evidence the strategy was already dead at a cheap cost. Corrected: it is **PF 0.9917 @ 25 bp/side** (1,941 trades, `pod_equity_breakout_backtest.json`) and **PF 1.2206 @ 5 bp/side** (net +0.3919%/trade, t = 3.52, `breakout_cost_sweep.json`); the sweep's own 25 bp row is 0.99597. The arithmetic reconciles exactly: 0.49189 − 2(25)/1e4·100 = −0.00811. The KILL survives, but it rests on the random null and negative selection alpha, **not** on cost [`05_REAL_COST_MEASUREMENT_2026-11-22.md`](docs/edge_research/05_REAL_COST_MEASUREMENT_2026-11-22.md:242-306) [`15_PROGRAMME_SCOREBOARD_2026-11-22.md`](docs/edge_research/15_PROGRAMME_SCOREBOARD_2026-11-22.md:127-154).

2. **Four defects in the momentum core**, found and fixed before any momentum verdict was treated as final: a **one-month look-ahead** in the signal; **NaN values converted into fabricated short positions** (a missing price became a sell); a **Sharpe computation returning ~1e16** (a divide by near-zero); and **`mom_12_1` running silently on daily data** instead of the intended monthly series. `[SRC: programme record — these four are not itemised in docs 03–18 of this document's source set, so no file:line is given here.]` That this class of defect is real and was fixed elsewhere is documented: a clairvoyance control caught a look-ahead that produced **Sharpe 1.83 vs 0.73 real** [`PROMOTION_GATE_2026-11-22.md`](docs/PROMOTION_GATE_2026-11-22.md:106-108), and infinite PF / explosive Sharpe values are now displayed as `n/a` rather than shown [`updates/2026-11-16-audit-pf-sharpe-display.md`](updates/2026-11-16-audit-pf-sharpe-display.md:5).

3. **The survivorship 0.0 pp misread risk.** The measured gap is **0.0 pp/yr**, and it is 0.0 *by construction*: the "present at both ends" set is all 79 symbols. Reading it as "no survivorship bias" would be wrong. It is a **zero lower bound**; the direction of the bias is argued upward from construction, and its absolute magnitude is **UNMEASURED** [`10_SURVIVORSHIP_AUDIT_2026-11-22.md`](docs/edge_research/10_SURVIVORSHIP_AUDIT_2026-11-22.md:37-51) [`15_PROGRAMME_SCOREBOARD_2026-11-22.md`](docs/edge_research/15_PROGRAMME_SCOREBOARD_2026-11-22.md:138-141).

A fourth self-caught issue, recorded here for completeness: the strategy count drifted between documents (9 in doc 15, 13 in doc 18) as items were added; see §8.1. It does not change any verdict, but a reader comparing documents would otherwise see a contradiction.

---

## 7. The blunt paragraph

Thirteen strategies were tested and twelve were killed: two FX rules, an equity breakout, an FX carry book, a cross-venue basis trade, 12-1 momentum long/short, crypto intraday mean-reversion, three commodity momentum variants and three bond momentum variants. The one survivor, funding carry, is marginal: it needs 16.398 days to amortise its 45.524 bp round trip while a positive-funding episode typically lasts about two days, its 30-day net of **+2.42% APR** is below a **4.32%** T-bill and its 90-day **+6.24% APR** only clears 4.32% at sizes 27–32× beyond measured capacity. Meanwhile the live system's own resolved picks lost **0.1524% per trade** over 278 days while cash made **+3.29%**, and the validation gate that would certify a survivor cannot certify anything: 9 of 12 pods are `observe`, the single `pre_registered` pod has no forward rows, and the only 430-row forward ledger is 100% backfilled. So the question "would we invest today" has one answer, and it is no. **This programme's value so far is that it can now tell you what does not work, with numbers, and it has stopped itself from claiming otherwise.**

---

## 8. Source contradictions found

Reported, not silently resolved. In each case I quote both sides.

### 8.1 Strategy count: 9 vs 13

- [`15_PROGRAMME_SCOREBOARD_2026-11-22.md`](docs/edge_research/15_PROGRAMME_SCOREBOARD_2026-11-22.md:12-17): *"Nine strategies were tested. One survived (MARGINAL). Seven were killed. One was blocked on data."* Its table has 9 rows: 7 KILL, 1 MARGINAL (funding carry), 1 BLOCKED_DATA (commodity term-structure carry).
- [`18_CAPACITY_COMBINED_BOOK_COUNTERFACTUAL_2026-11-22.md`](docs/edge_research/18_CAPACITY_COMBINED_BOOK_COUNTERFACTUAL_2026-11-22.md:12): *"13 strategies tested, 12 KILL, 1 MARGINAL (funding carry), 0 cleared."*

**Cause, not contradiction of verdicts:** doc 15 explicitly lists commodity futures momentum and bond momentum as *"not yet run"* in its §6, so it predates items 33/34. Doc 16 then adds **6 momentum variants** (3 commodity, 3 bond), all KILL. Counting each momentum family once, doc 15's 7 kills + 2 families + the 3 N1 rules = 12; counting variants, the kills number 16. **No source I read states the exact membership of the 13.** Every grouping is all-KILL, so the headline is unaffected, but the composition of the 12 is a reporting gap and should not be quoted as if it were settled.

### 8.2 Median positive-funding episode: 1.93 d vs 2.33 d vs 1.3–2.3 d

- [`18_CAPACITY_COMBINED_BOOK_COUNTERFACTUAL_2026-11-22.md`](docs/edge_research/18_CAPACITY_COMBINED_BOOK_COUNTERFACTUAL_2026-11-22.md:97): base hold = **1.93 days**.
- [`15_PROGRAMME_SCOREBOARD_2026-11-22.md`](docs/edge_research/15_PROGRAMME_SCOREBOARD_2026-11-22.md:35): *"median episode 2.33d"* (and §4 line 101 repeats 2.33 days).
- [`06_FUNDING_CARRY_2026-11-22.md`](docs/edge_research/06_FUNDING_CARRY_2026-11-22.md:216-222): per-symbol medians **2.3 / 2.0 / 1.3 / 2.3 / 1.7** days (BTC/ETH/SOL/BNB/XRP).

**Effect:** none on the verdict. Against 16.398 days, 1.93 d is 8.5× short and 2.33 d is 7.0× short. Both are "about two days", both are far below the break-even. The disagreement is about which aggregate is called the median, and it should be fixed before the ratio is quoted as a single number.

### 8.3 Gross funding APR: 7.93% vs 8.16%

- [`06_FUNDING_CARRY_2026-11-22.md`](docs/edge_research/06_FUNDING_CARRY_2026-11-22.md:155): equal-weight **mean** across symbols = **+7.93% APR**.
- [`18_CAPACITY_COMBINED_BOOK_COUNTERFACTUAL_2026-11-22.md`](docs/edge_research/18_CAPACITY_COMBINED_BOOK_COUNTERFACTUAL_2026-11-22.md:91): **median** across symbols 7.45 bp/8 h → **8.16% APR**.

**Effect:** none, and both are labelled. They are different central statistics of the same distribution (the mean is dragged by XRP +14.37% and ETH +13.55%; the median is dragged by BNB +0.02%). Both are gross, both are above a 4.32% T-bill, and both are irrelevant to the net verdict, which is negative below 30 days. The brief quotes 7.93%; the 8.16% figure is used in the capacity model specifically because the median is the mandatory default there.

### 8.4 Equity-breakout PF: 0.992 vs 0.9917 vs 0.99597

The brief says 0.992 @ 25 bp/side; `pod_equity_breakout_backtest.json` says **0.99165**; the 25 bp row of `breakout_cost_sweep.json` says **0.99597** (net −0.0081%). Both are 25 bp/side and differ only by a 6-trade data refresh (n 1941 vs 1935). Already disclosed in [`15_PROGRAMME_SCOREBOARD_2026-11-22.md`](docs/edge_research/15_PROGRAMME_SCOREBOARD_2026-11-22.md:148-154). Quote **0.9917 @ 25 bp/side** from the backtest JSON.

### 8.5 Bond-momentum null percentile

The brief attributes *"null pct 2.0"* to bond momentum as a family. [`16_COMMODITY_AND_BOND_MOMENTUM_2026-11-22.md`](docs/edge_research/16_COMMODITY_AND_BOND_MOMENTUM_2026-11-22.md:212-214) reports a null **only for B1** (percentile 2.0); B2 and B3 are marked *"n/a (no null declared)"*. The 2.0 belongs to B1 alone. B2 and B3 are killed on Sharpe (−1.699, −1.063 at 5 bp/side assumed) and on an excess-vs-SPY CI that excludes zero on the negative side.

### 8.6 Commodity momentum: arithmetic vs data validity

Doc 16 reports the arithmetic; a peer note disputes the **data** (roll artifacts in a continuous front-month series) [`17_COMS_CHECK4_BREAKEVEN_LEDGER_2026-11-22.md`](docs/edge_research/17_COMS_CHECK4_BREAKEVEN_LEDGER_2026-11-22.md:134) [`17_COMS_CHECK4_BREAKEVEN_LEDGER_2026-11-22.md`](docs/edge_research/17_COMS_CHECK4_BREAKEVEN_LEDGER_2026-11-22.md:191). Doc 17's own position is that roll artifacts inflate momentum and therefore make the KILL conservative. Both statements are reported; the result is marked **DATA-SUSPECT** in §4 and is not used as evidence for anything.

### 8.7 Pod census: 8 of 11 vs 9 of 12

[`03_P0_FORWARD_CLOCK_STRUCTURAL_BLOCK_2026-11-22.md`](docs/edge_research/03_P0_FORWARD_CLOCK_STRUCTURAL_BLOCK_2026-11-22.md:85-113) reports **8 of 11 `observe`** in the primary manifest and **9 of 12 `observe`** in the union across both manifests; the brief uses 9 of 12. Both are correct for their stated population. The union figure is the one to quote because it covers every pod either manifest knows about.

### 8.8 SPY Sharpe: 0.351 vs 1.114 vs 0.911 vs 0.987

These are different windows, not different measurements of one thing. **0.351** is SPY on the 79-symbol panel window 2021-11-22 → 2026-11-19; **1.114** is the standing programme bar from an earlier eval window [`07_HURDLE_RATES_2026-11-22.md`](docs/edge_research/07_HURDLE_RATES_2026-11-22.md:83-87); **0.911** is SPY over the commodity window and **0.987** over the bond window [`16_COMMODITY_AND_BOND_MOMENTUM_2026-11-22.md`](docs/edge_research/16_COMMODITY_AND_BOND_MOMENTUM_2026-11-22.md:116) [`16_COMMODITY_AND_BOND_MOMENTUM_2026-11-22.md`](docs/edge_research/16_COMMODITY_AND_BOND_MOMENTUM_2026-11-22.md:177). Every comparison in this document states which window it uses. A reader should never compare a strategy's Sharpe to 1.114 and to 0.351 in the same breath.

---

## 9. What is not in this document, deliberately

- No new backtest, no new data pull, no re-derivation of any number. Every figure above is read from a source and cited.
- No picks, no signals, no price levels, no allocation recommendation beyond the measured 4.32% cash comparison. This is a verdict about what does not work, not a trading plan.
- No claim that "no edge exists anywhere". What is claimed is narrower and supported: **none of the thirteen strategies tested clears a 4.32% T-bill after cost**, and the machinery cannot yet certify one that might.
