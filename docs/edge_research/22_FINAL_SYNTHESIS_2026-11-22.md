# 22 — Final synthesis: INVESTABLE / NOT_INVESTABLE / UNKNOWN

**Date:** 2026-11-22
**Programme item:** 50 (closing document of the round — synthesis only; no new backtest, no new data pull, no re-derivation)
**Purpose:** for each asset class and each strategy, exactly one of three verdicts, with the evidence, and without blurring "we tested it and it failed" into "we never measured what it would cost".

**The hurdle used throughout:** US 3-month T-bill **4.32%** (2026-11-20, Treasury daily yield curve CSV, column "3 Mo"; FRED `DTB3` cross-check 4.16% on 2026-11-19) [`07_HURDLE_RATES_2026-11-22.md`](docs/edge_research/07_HURDLE_RATES_2026-11-22.md:20). Beat-SPY requires Sharpe **1.114** (standing bar); SPY on the 79-symbol panel window (2021-11-22 → 2026-11-19) delivered **CAGR 10.42%, vol 17.39%, Sharpe-vs-rf 0.351** [same doc, lines 83–87]. SPY's Sharpe is window-dependent (0.351 / 1.114 / 0.911 / 0.987) and every comparison below names its window.

**Sources read for this document (not recalled):** [`19_HONEST_VERDICT_2026-11-22.md`](docs/edge_research/19_HONEST_VERDICT_2026-11-22.md) · [`15_PROGRAMME_SCOREBOARD_2026-11-22.md`](docs/edge_research/15_PROGRAMME_SCOREBOARD_2026-11-22.md) + [`reports/programme_scoreboard_20261122.json`](reports/programme_scoreboard_20261122.json) · [`18_CAPACITY_COMBINED_BOOK_COUNTERFACTUAL_2026-11-22.md`](docs/edge_research/18_CAPACITY_COMBINED_BOOK_COUNTERFACTUAL_2026-11-22.md) · [`21_VERIFICATION_AND_CI_GUARD_2026-11-22.md`](docs/edge_research/21_VERIFICATION_AND_CI_GUARD_2026-11-22.md) + [`reports/verification_20261122.json`](reports/verification_20261122.json) · [`plans/2026-11-22-phase2-profitability-plan.md`](plans/2026-11-22-phase2-profitability-plan.md) · [`10_SURVIVORSHIP_AUDIT_2026-11-22.md`](docs/edge_research/10_SURVIVORSHIP_AUDIT_2026-11-22.md) · [`03_P0_FORWARD_CLOCK_STRUCTURAL_BLOCK_2026-11-22.md`](docs/edge_research/03_P0_FORWARD_CLOCK_STRUCTURAL_BLOCK_2026-11-22.md) · [`05_REAL_COST_MEASUREMENT_2026-11-22.md`](docs/edge_research/05_REAL_COST_MEASUREMENT_2026-11-22.md) · [`06_FUNDING_CARRY_2026-11-22.md`](docs/edge_research/06_FUNDING_CARRY_2026-11-22.md) · [`07_HURDLE_RATES_2026-11-22.md`](docs/edge_research/07_HURDLE_RATES_2026-11-22.md) · [`08_CARRY_AND_MOMENTUM_2026-11-22.md`](docs/edge_research/08_CARRY_AND_MOMENTUM_2026-11-22.md) · [`14_CRYPTO_INTRADAY_MEANREV_2026-11-22.md`](docs/edge_research/14_CRYPTO_INTRADAY_MEANREV_2026-11-22.md) · [`16_COMMODITY_AND_BOND_MOMENTUM_2026-11-22.md`](docs/edge_research/16_COMMODITY_AND_BOND_MOMENTUM_2026-11-22.md) · [`20_COMS_CHECK5_ROUND_VERDICT_2026-11-22.md`](docs/edge_research/20_COMS_CHECK5_ROUND_VERDICT_2026-11-22.md) · [`02_DEEP_REVIEW_2026-11-22.md`](docs/edge_research/02_DEEP_REVIEW_2026-11-22.md) · [`docs/audit_review_2026-11-22/`](docs/audit_review_2026-11-22/README.md)

---

# Part 1 — THE ONE-LINE ANSWER

**Nothing in this programme is investable today: zero of fourteen strategy rows clears a 4.32% T-bill after cost with a positive CI on excess return; funding carry is the one item that is marginal and unresolved (it needs a 16.398-day hold to amortise a 45.524 bp round trip while a positive-funding episode typically lasts about two days); and the rest is either confidently dead or genuinely unknown.**

---

# Part 2 — PER-STRATEGY VERDICT TABLE

**How to read the three verdicts.** `INVESTABLE` requires a positive CI on excess return with cost paid. `NOT_INVESTABLE` means tested, measured, negative, and closable. `UNKNOWN` means not measured, or measured with a hole that could reverse the answer, and it is *not* silently folded into `NOT_INVESTABLE`.

**The move rule applied below (stated so it can be checked):** a strategy that was killed on **zero-cost** grounds stays `NOT_INVESTABLE` at high confidence, because cost cannot rescue a negative gross edge. A strategy that was killed on **assumed-cost** grounds, in an asset class whose cost was never measured, and whose break-even cost is inside the plausible range of real cost, moves to `UNKNOWN`. A strategy whose decisive number exists only in Markdown, with no machine-readable source, is also marked `UNKNOWN` on provenance. A strategy whose break-even is orders of magnitude above any plausible cost does **not** move: the unmeasured cost cannot reverse it.

**Row set: 14 rows** = the 11 strategy families named in the item-50 brief + N1's three low-turnover rules (R1, R2, R3). The programme's own counts are 9 (scoreboard) and 13 (doc 18), and the composition of the 13 was never settled [`19_HONEST_VERDICT_2026-11-22.md`](docs/edge_research/19_HONEST_VERDICT_2026-11-22.md:143-148); this document fixes its row set explicitly rather than inheriting an ambiguous one.

| # | Strategy | Asset class | Tested how (cost basis) | Decisive number | VERDICT | Confidence | What would change it |
|---|---|---|---|---|---|---|---|
| 1 | FX momentum (63d/21d) | FOREX | 110-pair panel, quintile L/S, 21d hold, n=4,092 pair-rebalances. **No PF computed; cost basis not stated.** Decisive figures exist **only** in [`block2_r21_forex_carry_trend.md`](docs/edge_research/block2_r21_forex_carry_trend.md:47-50), not in `reports/low_turnover_20261122.json` | mean net **−36.88 bp**, gross **−26.88 bp**, null **0.0** pct | **UNKNOWN** (provenance) | Low on the number; high on the kill if the number is right | A machine-readable R21 report reproducing −36.88 bp. If it does, this is `NOT_INVESTABLE` at high confidence on zero-cost grounds (the gross itself is negative) |
| 2 | FX mean-reversion (5d/5d, R22) | FOREX | 55 dedup pairs, 403 windows, 8,866 pair-rebalances. **10 bp round trip assumed**; FX spread now **MEASURED but Sunday-reopen (upper bound)**: USD-major median-of-medians **7.533 bp** (range 1.95–12.52), all-pairs median **7.99 bp**. Figure traceable to [`reports/fx_meanrev_cost_sweep/sweep.json`](reports/fx_meanrev_cost_sweep/sweep.json), not to the N1 JSON | gross **+4.30 bp**, net **−5.70 bp @10bp**, break-even **4.3038 bp**; at 0 bp net **+4.30** (CI-LB +1.75, CANDIDATE), at 20 bp net **−15.70**; window-clustered CI at 1 bp **[−4.32, +11.09]** | **UNKNOWN** | Medium | The measured upper-bound cost (~7.5–8 bp) is ~1.75–1.9× the 4.3038 bp break-even, so at measured cost it is KILL; only a weekday spread below ~2.6 bp (the median-trade break-even) *and* a clustered CI-LB above 0 would flip it. Even at 1 bp the clustered CI includes zero |
| 3 | Equity breakout (donchian / VT pattern sweep) | EQUITY | 13 US ETFs/mega-caps, daily, next-bar open, 1,941 round trips. PF at 0 / 5 / 25 bp/side. **Equity cost UNMEASURED.** Null percentile and selection alpha come from an independent 15-ETF D7 test, a different population | PF **1.2865 @ 0 bp/side**; PF **1.2206 @ 5 bp/side**; PF **0.9917 @ 25 bp/side**; break-even **24.5945 bp/side**; random-entry null **69.8th** pct (N=20) / **71.4th** (N=55); selection-alpha **CI-LB −0.285% / −0.296%** | **NOT_INVESTABLE** | High | A pre-registered re-test with null ≥ 95 and alpha CI-LB > 0. **Not** a cheaper cost assumption |
| 4 | FX carry (quintile) | FOREX | 11 currencies, 95 months, 2 long / 2 short by short rate. Cost sweep 0–10 bp/month; **no PF computed**; FX cost now **MEASURED but Sunday-reopen (upper bound)** ~7.5–8 bp round trip | **Sharpe −0.126 vs 4.32%**; CAGR **3.38% vs 4.32%**; null **98.2**; break-even **468.5 bp**; excess vs SPY **−3.04% [−8.28%, +2.29%]** | **NOT_INVESTABLE** | High | A regime filter that removes the crash months (worst month −7.55%) or a carry measure that is not beaten by cash. A measured FX cost cannot do it: the 468.5 bp margin is ~60× the measured ~7.5 bp |
| 5 | Cross-venue basis (delta-neutral) | CRYPTO | BTC 1-minute, 720 minutes of 3-venue overlap. Threshold built from **measured** all-in taker round trips (Binance 20.00 bp, KuCoin 20.48 bp, Kraken 52.02 bp) | **0.00%** of 720 minutes above threshold (all 3 pairs); Binance↔KuCoin median **−0.2427 bp** vs a **40.48 bp** threshold | **NOT_INVESTABLE** | High (cost-honest) | A venue pair whose *measured* round trip falls below ~5 bp, or a dislocation ~100× today's median basis |
| 6 | 12-1 momentum (long/short) | Multi-asset (79 symbols) | 48 monthly rebalances. **5 bp/side base, 15 bp/side stress** (equity/ETF cost `UNMEASURED`); no PF computed | null **1.6** (98.4% of random-rank portfolios did better); CAGR **−25.45% vs 4.32%**; maxDD **−82.3%**; excess vs SPY **[−72.6%, −0.003%]** | **NOT_INVESTABLE** | High | Nothing at this cost basis: it is a null-percentile kill, not a cost kill. The long-only variant is a separate `UNKNOWN` (null 41.4, excess CI spans zero) |
| 7 | Crypto intraday mean-reversion | CRYPTO | 10 symbols, 4h bars, 5,400 trades. **20 bp MEASURED** base; sweep 0–60 bp | PF **0.815 @ 0 bp**, PF **0.691 @ 20 bp**; break-even **0 bp**; null **0.0**; excess CI **[−72.37%, −30.37%]**; CAGR −38.89% vs 4.32% | **NOT_INVESTABLE** | Very high (cleanest kill) | An independent window where it is profitable *before* cost at null ≥ 95 |
| 8 | Commodity momentum (V1 L/S, V2 long-only, V3 long-only + filter) | COMMODITY | 7 futures front-month series, 48 monthly rebalances. **5 bp/side ASSUMED**; commodity cost `UNMEASURED` | V1 PF **0.757 @ 5 bp/side** (CAGR −7.13% vs 4.32%); V2 PF **1.114 @ 5 bp/side** (CAGR +0.47% vs 4.32%); V3 PF **1.074 @ 5 bp/side** (CAGR −0.67% vs 4.32%); break-even **0 bp/side**; null 30.2 / 33.1 / 25.2 | **UNKNOWN** — data-corrupted | Medium | A roll-adjusted, back-adjusted continuous series with commission charged. Then the 0 bp/side break-even becomes quotable |
| 9 | Bond momentum (B1 time-series, B2 cross-sectional L/S, B3 duration timing via TLT) | BOND | 10 bond ETFs, 49 monthly rebalances. **5 bp/side ASSUMED**; ETF cost `UNMEASURED`; **dividend-adjustment method flagged `UNMEASURED`** | B1 PF **1.312 @ 5 bp/side** *beside* Sharpe **−0.550**, null **2.0** (B1 only); B2 PF **0.743 @ 5 bp/side**, Sharpe −1.699; B3 PF **0.737 @ 5 bp/side**, Sharpe −1.063, skew −1.452; break-even **0 bp/side** | **UNKNOWN** | Medium | A total-return series with one declared, reconciled dividend method plus measured ETF spreads. Do not quote B1's PF at any cost basis without Sharpe −0.550 and maxDD beside it |
| 10 | Funding carry (delta-neutral long spot / short perp) | CRYPTO | 5 symbols, 6.2–7.2 years of real 8h funding, four taker fills. Pair round trip **45.524 bp @ 1× ($10k), 91.048 bp @ 2×, MEASURED** (perp spread assumed = spot spread) | break-even hold **16.398 d** vs median episode **1.93–2.33 d**; net **+2.42% APR at 30 d vs 4.32%**, **+6.24% APR at 90 d vs 4.32%**, **−3.12% APR at 30 d at 2× vs 4.32%**, **−3.73% APR at 14 d vs 4.32%**; gross **+7.93% APR (mean) / 8.16% (median)**, last 12 months **1.75% APR**, all vs 4.32%; capacity **$29,438/symbol**; survivorship **UNSAFE** | **UNKNOWN** | Medium-high that it is not investable now | A funding regime persisting ≥ 16.4 d; maker fills at ≤ 5.4–6.5 bp pair round trip; 27–32× more capacity (90 d needs $796k–$944k/symbol); a historical universe to clear the UNSAFE flag |
| 11 | Commodity term-structure carry | COMMODITY | **Not runnable:** one continuous front-month series on disk; roll yield `(front − second)/second` needs two contracts. Commodity cost `UNMEASURED` | **zero second-month contract series** | **UNKNOWN** (`BLOCKED_DATA`) | n/a | A second-month contract series, or a real futures curve. Synthesising one from the front month is forbidden (it invents the signal) |
| 12 | N1 R1 multi-asset 12-month momentum | Multi-asset | 79 symbols, annual rebalance. **5 bp/side base, 15 bp/side stress.** Machine-readable: [`reports/low_turnover_20261122.json`](reports/low_turnover_20261122.json) | CAGR **18.05% vs 4.32%** but null **61.2**; Sharpe 0.590; excess vs SPY +0.97 pp | **NOT_INVESTABLE** | Medium-high | Null ≥ 95 on a point-in-time universe |
| 13 | N1 R2 US sector momentum | ETF | 4 sector ETFs, quarterly. **5 bp/side base.** Machine-readable: same JSON | CAGR **5.76% vs 4.32%**; null **35.4**; excess vs SPY **−11.3 pp** | **NOT_INVESTABLE** | Medium-high | Null ≥ 95 with a measured ETF cost |
| 14 | N1 R3 SPY 200-day trend (Faber) | ETF | Daily signal, ~2–5 trades/yr. **5 bp/side base.** Machine-readable: same JSON | CAGR **10.24% vs 4.32%**, but SPY buy-and-hold was 17.07% in the eval window; null **53.4**; excess **−6.8 pp** | **NOT_INVESTABLE** | Medium-high | It already loses to buy-and-hold SPY. Nothing plausible changes that |

### The PF register (every PF with its cost basis, and nothing unlabelled)

- Equity breakout: **1.2865 @ 0 bp/side**, **1.2206 @ 5 bp/side**, **0.9917 @ 25 bp/side** (the 25 bp sweep row is 0.99597; the difference is a 6-trade data refresh, n 1941 vs 1935).
- Crypto intraday mean-reversion: **0.815 @ 0 bp**, **0.691 @ 20 bp**.
- Commodity momentum: **0.757 / 1.114 / 1.074 @ 5 bp/side (assumed)**.
- Bond momentum: **1.312 / 0.743 / 0.737 @ 5 bp/side (assumed)**.
- The published equity-breakout claim **PF 1.479 with no stated cost basis** is `UNREPRODUCED` (measured PF ≈ 1.00, WR 40.6% vs published 50.2%) and must never be quoted as a result.
- No other PF exists in this round. Funding carry, FX carry, basis, 12-1 momentum and the N1 rules report no PF, and no PF is invented for them.

### Per-row reasoning that the table compresses

**Equity breakout (row 3) — why `NOT_INVESTABLE` and not `UNKNOWN`.** Equity cost was never measured, so the *cost-honest* version of this verdict is `UNKNOWN`. I did not rely on cost. I relied on the cost-independent grounds: the observed Sharpe sits at the **69.8th / 71.4th percentile** of a random-entry null, and selection alpha is negative with a CI lower bound of **−0.285% / −0.296%** [`02_DEEP_REVIEW_2026-11-22.md`](docs/edge_research/02_DEEP_REVIEW_2026-11-22.md:31). A rule that is indistinguishable from random entry and loses to simply holding the same ETFs is not rescued by a cheaper fill. **Caveat on provenance:** the 0 bp/side PF 1.2865 comes from the 13-symbol pod sweep, while the null percentile and alpha come from the independent 15-ETF D7 test. They are two experiments that fail the same way, not one number.

**FX carry (row 4) — the wrinkle that must stay attached.** Null percentile **98.2** means the ranking *does* beat random assignment of the same currencies (null mean Sharpe −0.85). It is a real carry premium with a real crash profile (skew −0.63, worst month −7.55%, maxDD −11.71%) and it still earns CAGR 3.38% against a 4.32% T-bill. Beating random is not the bar; beating cash is. Its cost-honest restatement is `UNKNOWN` in the strict sense (no FX spread measured), but break-even cost is **468.5 bp**, so no plausible FX cost can reverse the answer, and the verdict stays closed.

**FX momentum and FX mean-reversion (rows 1–2) — the provenance wrinkle.** Neither figure is in `reports/low_turnover_20261122.json`, whose rules are R1 multi-asset momentum, R2 sector momentum and R3 SPY 200-day. FX momentum's numbers exist only in Markdown; FX mean-reversion's exist in [`reports/fx_meanrev_cost_sweep/sweep.json`](reports/fx_meanrev_cost_sweep/sweep.json) but not in the N1 JSON. The scoreboard's row count therefore overstates how much of this is machine-verifiable: **2 of 9 rows** in doc 15 are `NUMBER_NOT_FOUND_IN_SOURCE` [`15_PROGRAMME_SCOREBOARD_2026-11-22.md`](docs/edge_research/15_PROGRAMME_SCOREBOARD_2026-11-22.md:171-180). FX momentum is the weaker of the two and is marked `UNKNOWN`; FX mean-reversion is `UNKNOWN` for the different, cost-driven reason that its 4.3038 bp break-even sits inside the plausible FX cost range and its clustered CI includes zero even at 1 bp.

**Commodity momentum (row 8) — why `UNKNOWN` and not `NOT_INVESTABLE`.** The arithmetic says break-even **0 bp/side**, i.e. none of the three variants clears a 4.32% T-bill even with free trading. But buffy's roll-artifact objection was **substantiated**, not withdrawn: `CL=F` has a negative close (−37.63, 2020-04-20) making `pct_change` meaningless; `ZC=F` prints about **−23.6%** on 07-15 in three separate years; `NG=F` has recurring same-month-day spikes across six years, 55–163 moves > 8% [`20_COMS_CHECK5_ROUND_VERDICT_2026-11-22.md`](docs/edge_research/20_COMS_CHECK5_ROUND_VERDICT_2026-11-22.md:116-132). Mercury3 reproduced the negative-`CL=F` finding in their own cache and withdrew their commodity rows; buffy reproduced Mercury3's rebuild and ran the rule under her CI-LB gate, which came back negative on every variant with the halves flipping sign. Two independent witnesses closed it **NO CANDIDATE**. The arithmetic rests on corrupted inputs, so the verdict is `UNKNOWN — data-corrupted, needs roll-adjusted series`. On the ETF-proxy rebuild the series are clean and the edge is still absent, but that is a different test on different instruments.

**Bond momentum (row 9) — the PF-inflation trap.** B1 shows **PF 1.312 @ 5 bp/side (assumed)** beside Sharpe **−0.550** and a null percentile of **2.0**. The PF is inflated because the strategy sits in cash 10.2% of months and the denominator counts only closed losing positions while the equity curve bleeds. Never quote B1's PF alone. The verdict is `UNKNOWN` because the ETF return series itself is suspect: ETF cost is `UNMEASURED` and the dividend-adjustment method was flagged `UNMEASURED` (the ETF `Close` behaves as dividend-adjusted; SHY proves it, since rates rose ~4% yet it gained +10.4% over 5 years, which is only possible with coupons reinvested) [`16_COMMODITY_AND_BOND_MOMENTUM_2026-11-22.md`](docs/edge_research/16_COMMODITY_AND_BOND_MOMENTUM_2026-11-22.md:225). Note the null 2.0 belongs to B1 only; B2 and B3 declared no null [`19_HONEST_VERDICT_2026-11-22.md`](docs/edge_research/19_HONEST_VERDICT_2026-11-22.md:169-171).

**Funding carry (row 10) — the most interesting row, and still not a yes.** This is the one row where cost is *honest* (crypto is the only measured class) and the answer is still not a yes. Gross is **+7.93% APR** (equal-weight mean) against a **4.32%** T-bill, and even that gross premium is thin; the median is **8.16% APR** against 4.32%, and the last 12 months are **1.75% APR** against 4.32% because BTC funding compressed from +2.80 bp/8h in 2021 to **+0.30 bp/8h in 2026**. Net at 30 d is **+2.42% APR against 4.32%** (below cash) and at 90 d is **+6.24% APR against 4.32%** (above cash, tail only); at 2× cost the 90-day figure is **+4.40% APR against 4.32%** and the 30-day figure is **−3.12% APR against 4.32%**. The deciding number is **16.398 days of break-even hold vs a 1.93–2.33 day median positive-funding episode**: at the median hold, no deployed size beats the 4.32% T-bill, and the excess Sharpe over cash is **−0.44 at H30**. It is `UNKNOWN` rather than `NOT_INVESTABLE` because the premium is real and positive at long holds, and `UNKNOWN` rather than `INVESTABLE` because there is no positive CI on excess return at any hold that actually occurs.

---

# Part 3 — PER-ASSET-CLASS ROLLUP

**The taxonomy, read from the dossier set rather than assumed.** The canonical list is 8 classes in [`alpha_engine/money_ready_verdict.py:255`](alpha_engine/money_ready_verdict.py:255) (including MUTUAL_FUND, no MEME); the `/audit` payload carries 11 keys; the `/audit3` ledger has 7 buckets [`docs/audit_review_2026-11-22/00_SURFACE_BASELINE.md`](docs/audit_review_2026-11-22/00_SURFACE_BASELINE.md:89-93). The item-50 taxonomy of 12 (CRYPTO, EQUITY, ETF, BOND, COMMODITY, FOREX, FUTURES, MEME, PENNY_STOCK, INDEX, SPORTS, MUTUAL_FUND) is a superset used below; MEMECOIN is the taxonomy's MEME.

| Asset class | Strategies tested (rows from Part 2) | Verdict rollup | Transaction cost ever measured? |
|---|---|---|---|
| **CRYPTO** | Funding carry (10), cross-venue basis (5), crypto intraday mean-rev (7) | 0 INVESTABLE / **2 NOT_INVESTABLE** / **1 UNKNOWN** | **MEASURED** — spot taker 10 bp/side (Binance, BinanceUS, KuCoin) and 26 bp (Kraken), spread walked $1k–$1M on 2026-11-22. Caveat: one Sunday snapshot, and perp spread was *assumed* equal to spot |
| **EQUITY** | Equity breakout (3) | **1 NOT_INVESTABLE** | **UNMEASURED** |
| **ETF** | N1 R2 (13), N1 R3 (14) | **2 NOT_INVESTABLE** | **UNMEASURED** |
| **BOND** | Bond momentum B1/B2/B3 (9) | **1 UNKNOWN** | **UNMEASURED** |
| **COMMODITY** | Commodity momentum (8), commodity term-structure carry (11) | **2 UNKNOWN** | **UNMEASURED** |
| **FOREX** | FX momentum (1), FX mean-rev (2), FX carry (4) | 0 INVESTABLE / **1 NOT_INVESTABLE** / **2 UNKNOWN** | **MEASURED (upper bound)** — live top-of-book sampled at the Sunday 22:00Z reopen: USD-major median **7.533 bp** round trip, all-pairs median **7.99 bp**; thin book, so a weekday run is still owed ([`reports/cost_measurement_forex/`](reports/cost_measurement_forex/FOREX_COST_20261122.md)) |
| **FUTURES** | none in this row set (commodity futures are classed COMMODITY here) | no verdict | **UNMEASURED** |
| **MEME** | none | no verdict | **UNMEASURED** (a 30 bp round-trip constant is charged; measured slippage is not) |
| **PENNY_STOCK** | none | no verdict | **UNMEASURED** (30 bp constant charged) |
| **INDEX** | none (it is an ETF alias that leaks rows out of the denominator) | no verdict | **UNMEASURED** — no cost model exists for it |
| **SPORTS** | none | no verdict | **UNMEASURED** (out of scope) |
| **MUTUAL_FUND** | none | no verdict | **UNMEASURED** (0.08 configured, never populated) |
| *Multi-asset (cross-class, not one of the 12)* | 12-1 momentum (6), N1 R1 (12) | **2 NOT_INVESTABLE** | Mixed; cost assumed per class |

**Blunt count: 11 of the 12 classes have `UNMEASURED` transaction cost.** Only CRYPTO has a measured number, and even there the measurement covers spot taker fees and spot depth on one Sunday snapshot while the perp leg's spread is assumed. Every non-crypto verdict in this document is therefore conditional on an assumption, even where the verdict is `NOT_INVESTABLE` on cost-independent grounds.

---

# Part 4 — THE THREE BUCKETS, COUNTED

Row set: the same 14 rows as Part 2.

### INVESTABLE: 0

No row has a positive CI on excess return with cost paid. The closest candidates are funding carry (excess Sharpe **−0.44 at H30**, +0.23 at H90 against a 4.32% T-bill, and SPY's measured panel Sharpe is 0.351) and N1 R1 (CAGR 18.05% vs 4.32% but null 61.2 and excess vs SPY only +0.97 pp). Neither has a positive CI on excess return. Nothing is promoted.

### NOT_INVESTABLE: 8

1. **Equity breakout (row 3)** — random-entry null 69.8th percentile and negative selection alpha (CI-LB −0.285%); killed despite a zero-cost PF of 1.2865.
2. **FX carry (row 4)** — Sharpe −0.126 against a 4.32% T-bill; a real carry premium that still loses to cash.
3. **Cross-venue basis (row 5)** — 0.00% of 720 minutes reached the *measured* two-venue round trip; the dislocation never exists.
4. **12-1 momentum L/S (row 6)** — null percentile 1.6; 98.4% of random-rank portfolios did better.
5. **Crypto intraday mean-reversion (row 7)** — PF 0.815 at 0 bp, break-even 0 bp, null 0.0; loses before cost.
6. **N1 R1 multi-asset momentum (row 12)** — null 61.2, excess vs SPY +0.97 pp.
7. **N1 R2 sector momentum (row 13)** — null 35.4, excess vs SPY −11.3 pp.
8. **N1 R3 SPY 200-day (row 14)** — null 53.4, excess vs SPY −6.8 pp, below buy-and-hold SPY.

### UNKNOWN: 6

1. **FX momentum (row 1)** — missing: a machine-readable report of the −36.88 bp result. Its figure lives only in Markdown.
2. **FX mean-reversion (row 2)** — missing: a *weekday* FX spread. Cost is now measured at the Sunday reopen (upper bound ~7.5–8 bp, ABOVE the 4.3038 bp break-even → KILL at measured cost), but a thin-book upper bound cannot close it; the clustered CI also includes zero at every cost tested. Only a weekday measurement below ~2.6 bp could.
3. **Commodity momentum (row 8)** — missing: roll-adjusted, back-adjusted continuous futures series with commission charged.
4. **Bond momentum (row 9)** — missing: measured ETF cost and a declared, reconciled dividend-adjustment method.
5. **Funding carry (row 10)** — missing: a funding regime persisting ≥ 16.4 days (or maker fills at ≤ 5.4–6.5 bp pair round trip), 27–32× more capacity, and a survivorship-clean universe.
6. **Commodity term-structure carry (row 11)** — missing: a second-month contract series.

### How many verdicts moved, and why

- **Moved from KILL to UNKNOWN on the cost-measurement distinction: 2** — FX mean-reversion and bond momentum. In both cases the strategy sat in an asset class whose cost was never measured, the kill rested on an assumed cost, and the break-even sat inside the plausible range of real cost.
- **Moved from KILL to UNKNOWN on the commodity data-integrity finding: 1 row covering 3 variants** — commodity momentum V1/V2/V3, because buffy's roll-artifact objection was substantiated and two independent witnesses closed it NO CANDIDATE.
- **Moved from KILL to UNKNOWN on source provenance: 1** — FX momentum, whose decisive number exists only in Markdown.
- **Not moved, and why:** equity breakout (killed on null and alpha, not cost), FX carry (break-even 468.5 bp, so cost cannot reverse it), 12-1 momentum (null-percentile kill), crypto intraday mean-rev (zero-cost kill at measured cost), cross-venue basis (cost-honest kill), and N1 R1/R2/R3 (null-percentile kills).
- **Already not KILL, still UNKNOWN:** funding carry (was MARGINAL) and commodity term-structure carry (was BLOCKED_DATA).

Total: 4 KILL verdicts moved to UNKNOWN, 6 rows are UNKNOWN, and 8 remain NOT_INVESTABLE.

**M2 FOREX cost note (2026-11-22, second asset class measured).** FOREX cost is no longer `UNMEASURED`: live top-of-book was sampled from Tiingo at the Sunday 22:00Z reopen. Spreads (round trip, bp of mid) ranged from 1.95 (USD/CAD) to 16.7 (EUR/GBP), with the six USD majors at a median of 7.533 bp. This is **measurement** of a real book, but a thin one (frozen pairs, high variance), so it is recorded as a **Sunday-reopen upper bound**, `COMMISSION_UNKNOWN`. **No verdict moved:** it is not a representative session. Had it been representative, FX mean-reversion would have resolved to `NOT_INVESTABLE` at measured cost (7.5 bp > 4.3038 bp break-even) and FX carry stays `NOT_INVESTABLE` regardless (468.5 bp break-even). The arithmetic was re-run at 0/10/20 bp and reproduces the published figures; the 27-test momentum suite passed unchanged (no edit to `momentum_core.py`).

**M2-residual FOREX cost scheduler (2026-11-22).** The remaining FOREX unknown was one weekday London/NY-overlap spread run, which only existed if a human re-ran it on a weekday. [`.github/workflows/fx-cost-overlap.yml`](.github/workflows/fx-cost-overlap.yml) now schedules it (weekdays, 13:00-16:00 UTC, six runs) and [`tools/fx_cost_sampler.py`](tools/fx_cost_sampler.py) `--overlap` mode measures, classifies and chains the FX mean-reversion re-run automatically. **A scheduled measurement is pending** - no overlap number exists yet. The sampler can write only `NOT_INVESTABLE` or `HUMAN_REVIEW_REQUIRED` (or `BLOCKED_NO_REPRESENTATIVE_SESSION` / `UNCHANGED_UNKNOWN`); `INVESTABLE` is unreachable by construction ([`updates/2026-11-22-m2-forex-cost-scheduler.md`](updates/2026-11-22-m2-forex-cost-scheduler.md)). A blocked run changes no verdict. Note: the window-clustered CI includes zero at every cost tested so far (at the Sunday upper bound 7.533 bp: [−10.85, +4.55]), so a representative cost alone may not close FX mean-reversion.

---

# Part 5 — WHAT THE PROGRAMME CAN NOW SAY THAT IT COULD NOT SAY BEFORE

Facts only, with the number that backs each.

1. **It can name the measured cost of crypto trading.** Taker fee **10 bp/side** on Binance/BinanceUS/KuCoin and **26 bp** on Kraken; all-in round trip **~20.0 bp** to **~52.0 bp**; BTC top-of-book spread **0.0016 bp**, i.e. the fee dominates the spread by four orders of magnitude; ADA round-trip spread walks **6.86 bp at $1k to 988.79 bp at $1M** [`05_REAL_COST_MEASUREMENT_2026-11-22.md`](docs/edge_research/05_REAL_COST_MEASUREMENT_2026-11-22.md:43-89).
2. **It can state every strategy's break-even cost.** Equity breakout **24.5945 bp/side**; funding carry **16.398 days**; FX carry **468.5 bp**; crypto intraday mean-rev **0 bp**; cross-venue basis **never met**; commodity momentum **0 bp/side**; bond momentum **0 bp/side**; FX mean-reversion **4.3038 bp** [`15_PROGRAMME_SCOREBOARD_2026-11-22.md`](docs/edge_research/15_PROGRAMME_SCOREBOARD_2026-11-22.md:89-101).
3. **It can prove four families fail before any cost is applied.** Crypto intraday mean-reversion (PF 0.815 at 0 bp), commodity momentum (break-even 0 bp/side on all three variants), bond momentum (break-even 0 bp/side on all three variants), and FX momentum (gross −26.88 bp, on the Markdown figure only). A fifth, 12-1 momentum, is dead by its null percentile (1.6) rather than by cost. "Break-even 0 bp/side" means none clears the 4.32% T-bill even with free trading.
4. **It can show its own live system lost money against cash.** Over 278 days (2026-02-17 → 2026-11-22), 10,968 resolved closed picks net of the measured class cost model returned **mean −0.1524% per trade** (win rate 43.14%, sum −1,671.5%, per-trade Sharpe −0.037), while T-bills at 4.32% APR returned **+3.29%** and SPY **+1.81%** over the identical window [`18_CAPACITY_COMBINED_BOOK_COUNTERFACTUAL_2026-11-22.md`](docs/edge_research/18_CAPACITY_COMBINED_BOOK_COUNTERFACTUAL_2026-11-22.md:181-190). Machinery cost is still `UNMEASURED`.
5. **It can demonstrate that its validation gate is structurally unable to certify.** The gate hard-codes `if status != "pre_registered": res["eligible"] = False` [`alpha_engine/audit3_tribunal.py:1642`](alpha_engine/audit3_tribunal.py:1642). Nine of twelve pods are `observe`, the single `pre_registered` pod has zero forward rows, and all 430 forward rows sit on H-119, which has no pod and is marked `"promotable": false` [`03_P0_FORWARD_CLOCK_STRUCTURAL_BLOCK_2026-11-22.md`](docs/edge_research/03_P0_FORWARD_CLOCK_STRUCTURAL_BLOCK_2026-11-22.md:100-130).
6. **It can fail its own CI guard correctly.** [`tools/digest_artifact_guard.py`](tools/digest_artifact_guard.py) returns **FAIL** for the ledger (`63609da5…`, no artifact), dashboard_data (`ed25b59c…`, no artifact) and live `/audit` (`e346e65f…`, hash mismatch after drifting to `5a6ff492…`), and PASS only for the local regen digest, whose file is absent from `origin/main` [`reports/verification_20261122.json`](reports/verification_20261122.json:94-108).

That is a negative result set with positive instrumentation behind it: six things are now measurable that were assumptions nine hours earlier.

---

# Part 6 — THE HONEST BOUNDARY

Some of this is genuinely unknowable with the data that exists, and the reason is structural, not effort. **No historical universe exists:** every universe in the repo is a today's-constituents list, the 79-symbol panel has zero series ending early and zero starting late, and the measured survivorship gap of **0.0 pp/yr** is zero *by construction* because the "present at both ends" set is all 79 symbols. It is a **zero lower bound**; the direction of the bias is argued upward from construction and its magnitude is `UNMEASURED` [`10_SURVIVORSHIP_AUDIT_2026-11-22.md`](docs/edge_research/10_SURVIVORSHIP_AUDIT_2026-11-22.md:37-51). That makes every KILL safe (bias flattered the strategies) and every survivor unsafe: funding carry is flagged **UNSAFE** for exactly this reason. **No measured non-crypto cost exists:** equity, ETF, FX, commodity, bond, futures, MEME, PENNY_STOCK, INDEX, SPORTS and MUTUAL_FUND cost is unmeasured, so 11 of 12 classes cannot produce an unconditional verdict. **The commodity series are roll-corrupted:** a continuous front-month series with a −37.63 print and a −23.6% recurring 07-15 print is not a price history, and no amount of arithmetic on it is evidence. **The digest is not reproducible by design:** it hashes the post-dedup, post-exclusion, post-cost-model row set after writing, so it identifies a snapshot, not a dataset version, and can never be a cross-surface reconciliation key. **The gate cannot certify:** ten pods are barred by status and the eleventh has no rows, so the machinery that would validate a survivor is itself unable to validate anything.

The single cheapest high-value measurement for the next round is the **weekday FX spread run** (M2 in the phase-2 plan): one weekday execution of an existing probe during the London/NY overlap, logging per-pair median spread in pips. It costs one session, it needs no new data source, and it converts the largest single assumption in this document into a fact: FX is the class with three tested strategies and zero measured cost, and its break-evens (4.3038 bp for mean-reversion, 468.5 bp for carry) are the ones that decide whether two of my six `UNKNOWN`s can ever close [`plans/2026-11-22-phase2-profitability-plan.md`](plans/2026-11-22-phase2-profitability-plan.md:28-41). **As of 2026-11-22 this is scheduled** ([`fx-cost-overlap.yml`](.github/workflows/fx-cost-overlap.yml)): it runs automatically in the overlap, so the measurement no longer waits on a human. It is still pending - no overlap number exists yet.

---

# Appendix A — contradictions carried forward

Reported, not silently resolved. Only the ones that affect a verdict above.

1. **Strategy count: 9 (scoreboard) vs 13 (doc 18) vs 14 (this document's fixed row set).** The scoreboard predates items 33/34 and the composition of the 13 was never stated. All groupings are all-KILL, so the headline is unaffected, but the membership should not be quoted as settled [`19_HONEST_VERDICT_2026-11-22.md`](docs/edge_research/19_HONEST_VERDICT_2026-11-22.md:143-148).
2. **Median positive-funding episode: 1.93 d vs 2.33 d vs 1.3–2.3 d.** Doc 18 says 1.93, the scoreboard 2.33, doc 6 gives per-symbol 2.3/2.0/1.3/2.3/1.7. Against a 16.398-day break-even the disagreement does not move the verdict (8.5× vs 7.0× short), but the aggregate should be fixed before the ratio is quoted as one number.
3. **Gross funding APR: 7.93% (equal-weight mean) vs 8.16% (median across symbols).** Different central statistics of the same distribution, both gross, both against 4.32%. The net verdict is negative below 30 days either way.
4. **Commodity momentum: arithmetic vs data validity.** Doc 17 argues roll artifacts *inflate* momentum and so the KILL is conservative; buffy and Mercury3 substantiated the artifacts and closed the class NO CANDIDATE. I did **not** choose silently: the direction of the artifact's effect is not established, so neither "conservative kill" nor "invalid test" can be asserted, and the verdict is `UNKNOWN`.
5. **Equity breakout PF: 0.9917 (backtest JSON) vs 0.99597 (sweep, 25 bp row) vs 0.992 (brief).** Same cost basis, 6-trade refresh apart. Quote 0.9917 @ 25 bp/side.
6. **Bond-momentum null percentile 2.0 belongs to B1 only.** B2 and B3 declared no null and are killed on Sharpe and on an excess-vs-SPY CI that excludes zero on the negative side.
7. **SPY Sharpe 0.351 / 1.114 / 0.911 / 0.987** are four windows, not four measurements of one thing. Every comparison above names its window.
8. **Funding-carry net at 30 d is +2.42% APR, which is below the 4.32% T-bill** — a number that reads positive and is a loss. It is an APR, not a total return, and it is compared to an APR.

---

## 9. Programme tally (settled)

TALLY: 0 INVESTABLE / 11 NOT_INVESTABLE / 3 UNKNOWN (14 rows)

Settled tally for the 14-row set, as of 2026-11-23 [SRC: docs/edge_research/23_DEFINITIVE_ANSWER_2026-11-22.md:195].
The per-family lines elsewhere in this document are subsets of the 14 rows, not competing totals; the row-level
accounting that reconciles them is in doc 23, "The final accounting".
