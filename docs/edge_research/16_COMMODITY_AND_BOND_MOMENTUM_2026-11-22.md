# 16 — Commodity futures momentum (item 33) and bond/rate momentum (item 34)

**Date:** 2026-11-22
**Programme items:** 33 (commodity futures momentum), 34 (bond/rate momentum)
**Hurdle document:** [`07_HURDLE_RATES_2026-11-22.md`](07_HURDLE_RATES_2026-11-22.md)
**Structured output:** [`reports/commodity_momentum_20261122.json`](../../reports/commodity_momentum_20261122.json),
[`reports/bond_momentum_20261122.json`](../../reports/bond_momentum_20261122.json)

The bar (doc 07): cash pays **4.32%** (US 3-mo T-bill), SPY measured Sharpe **0.351**,
beat-SPY needs Sharpe **1.114**. A strategy is judged against `rf + hurdle × vol`, never
against zero.

---

## 0. Pre-declared rules — written BEFORE any run

These two paragraphs were fixed before the tools were executed. Nothing below was edited
after seeing results; if anything had to change, the changed test would be declared void.

### 0.1 Item 33 — commodity futures momentum

> **ITEM 33 RULE.** Universe = the 7 commodity futures with continuous front-month daily
> closes in `data/cache/asset_class_review`: `CL_F, GC_F, HG_F, NG_F, SI_F, ZC_F, ZS_F`.
> Formation = trailing **252-trading-day** return ending at each month-end close. Rank
> cross-sectionally at each month-end; with 7 symbols the terciles are the **top 3 (long)**
> and **bottom 3 (short)**, equal weight 1/3 each, the middle symbol unheld. Hold one month,
> rebalance at month-end. Cost is charged on traded notional: `bp/side × Σ|Δw|`. Variants:
> **V1 long/short** (base), **V2 long-only** top 3 (cash earns the 4.32% risk-free rate),
> **V3 long-only with absolute filter** (hold a top-3 name only if its trailing 252-day
> return is > 0, else cash). **Sign-skip:** V1 shorts a negative-momentum name because it is
> *rank*-selected, not *sign*-selected; V2/V3 go **flat**, never short. Cost sweep
> **2/5/10/20 bp per side**; base **5 bp/side**. Kill: Sharpe-vs-rf < 0.5 at 10 bp/side, OR
> (null percentile < 95 AND the excess-vs-SPY 95% CI includes 0). MARGINAL: null ≥ 95 with
> CI including 0. EDGE: null ≥ 95 and CI lower bound > 0.

**Why item 33 is runnable when item 17 was not.** Item 17 (commodity *term-structure
carry*) was BLOCKED_DATA because roll yield `(front − second)/second` needs two contracts at
the same date and only one continuous front-month series exists on disk. Momentum is a
function of the **single** front-month price path alone — no second contract is required.
Different signal, same data, legitimately different verdict.

### 0.2 Item 34 — bond / rate momentum

> **ITEM 34 RULE.** Tradeable-instrument tests on the 10 bond ETFs in
> `data/cache/asset_class_review` (`TLT, IEF, SHY, TLH, AGG, BND, LQD, TIP, JNK, HYG`) over
> their common window. Formation = **12-1 month return** (months t−12…t−2, skipping t−1).
> **B1 (primary, time-series):** each month-end hold equal weight every ETF whose 12-1
> return > 0, else cash at 4.32%. **Sign-skip = flat, no shorting** (shorting bonds costs
> financing above rf and is impractical for this capital base; the cash leg pays rf).
> **B2 (cross-sectional, diagnostic):** long top 3 / short bottom 3 by 12-1 return.
> **B3 (duration timing, mapped):** long TLT when the FRED `DGS10` month-end yield is below
> its level 3 months earlier, else cash. B3 is an **untradeable signal** (a yield cannot be
> traded); it is mapped through TLT, so its cost is TLT's ETF cost and its P&L is TLT's
> P&L, not the yield's. Cost sweep **2/5/10/20 bp per side**, base **5 bp/side**.
> **INSUFFICIENT** if the window lacks a sustained rising-rate period or has < 24 rebalances.

### 0.3 Shared statistical protocol

- **Random null:** ≥ 500 shuffles (1,000 used), same universe, same number of positions,
  same holding period and cost; only the rank→symbol assignment is shuffled each month.
  Reported as the percentile of the strategy's Sharpe within the null distribution.
- **Bootstrap CI:** 10,000 paired resamples of the monthly return pairs (strategy, SPY);
  excess CAGR = CAGR(resample) − CAGR(SPY resample), 2.5/97.5 percentiles.
- **Metrics:** CAGR = `(V_end/V_start)^(12/n) − 1`; vol = `std(monthly)×√12`;
  Sharpe-vs-rf = `mean(monthly − rf/12)/std(monthly) × √12` with rf = 4.32%/yr.
- **Return basis:** all returns are price returns of the instrument (futures/ETF), no
  dividends except where the ETF series itself is adjusted (see inventory).

---
## 1. Data inventory (what was actually on disk)

### Item 33

| Item | Value |
|---|---|
| Directory | `data/cache/asset_class_review/` |
| Commodity futures | **7**: `CL_F` (crude), `GC_F` (gold), `HG_F` (copper), `NG_F` (nat gas), `SI_F` (silver), `ZC_F` (corn), `ZS_F` (soybeans) |
| Format | `Date,Open,High,Low,Close,Volume`, one continuous front-month series each |
| Aligned rows (inner join) | **1,256** daily closes |
| Range | **2021-11-22 → 2026-11-20** |
| `commodity_price_cache/` | **does not exist** in this workspace — nothing to read |
| First usable rebalance | **2022-11-30** (after the 252-day formation window) |
| Rebalances used | **48** monthly |

Not commodities, so excluded from the universe: `ES_F`, `NQ_F`, `YM_F` (equity index).

### Item 34

| Item | Value |
|---|---|
| Bond ETFs | **10**: `TLT, IEF, SHY, TLH, AGG, BND, LQD, TIP, JNK, HYG` |
| ETF range | **2021-11-22 → 2026-11-19**, 1,254 daily closes each |
| Treasury yields | `data/rates_cache/DGS2.csv` (1976-06-01→2026-11-19), `DGS5.csv` and `DGS10.csv` (1962-01-02→2026-11-19), fetched from `https://fred.stlouisfed.org/graph/fredgraph.csv?id=<series>` — **HTTP 200** for all three |
| Last yields | DGS2 4.76%, DGS5 4.86%, DGS10 5.04% (2026-11-19) |
| First usable rebalance | **2022-10-31** (after the 12-month formation window) |
| Rebalances used | **49** monthly |

The treasury snapshot in doc 07 is *not* a time series and was not used as one; the FRED history above is.

---

## 2. Cost provenance and assumption

**Cost is UNMEASURED for commodity futures and for bond ETFs in this programme.** It is not borrowed from the crypto number. The treatment is the pre-declared one: sweep **2 / 5 / 10 / 20 bp per side**, report the **break-even cost**, and label every verdict **conditional on the assumption**.

Why 5 bp/side is the base:
- **Commodity futures:** retail commission is ~$2–4 round turn per contract. For a $50k-notional contract that is ≲1 bp, so 5 bp/side is a *generous* allowance for commission alone. The reason to allow more is **slippage on roll dates**, which is real and unmeasured. 5 bp/side is a plausible middle; 20 bp/side is the stress case.
- **Bond ETFs:** liquid treasury ETFs (`TLT`, `IEF`, `SHY`) trade at ~1–2 bp; `HYG`, `LQD`, `JNK` are wider and much wider in stress. 5 bp/side is plausible-to-generous for the treasuries and optimistic for the credit ETFs; the sweep covers that.

The cost sweep moves **cost only**. No parameter, universe, lookback or holding period changes between sweep points.

---

## 3. Item 33 results

SPY buy-and-hold over the same window: **16.62% CAGR, Sharpe 0.911, maxDD −8.3%**.

| Variant | CAGR | Vol | Sharpe vs rf | MaxDD | Skew | Worst month | PF (5bp) | Null pct | Excess vs SPY [95% CI] |
|---|---|---|---|---|---|---|---|---|---|
| V1 long/short | **−7.13%** | 16.5% | **−0.627** | **−28.2%** | **−0.734** | −15.73% | 0.757 | **30.2** | −23.75% [−43.5%, −4.6%] |
| V2 long-only | **+0.47%** | 24.3% | **−0.038** | **−36.6%** | −0.312 | −17.95% | 1.114 | **33.1** | −16.14% [−39.9%, +10.5%] |
| V3 long-only + filter | **−0.67%** | 24.0% | **−0.089** | **−36.6%** | −0.286 | −17.95% | 1.074 | **25.2** | −17.29% [−40.9%, +8.9%] |

Every PF above is **at 5 bp/side assumed cost**. PF is undefined for a series with no losing months; none of these hit that.

### Cost sweep (cost varied only)

| Cost | V1 CAGR / Sharpe / PF | V2 CAGR / Sharpe / PF | V3 CAGR / Sharpe / PF |
|---|---|---|---|
| 2 bp | −7.01% / −0.619 / 0.761 | +0.59% / −0.033 / 1.118 | −0.55% / −0.084 / 1.078 |
| 5 bp | −7.13% / −0.627 / 0.757 | +0.47% / −0.038 / 1.114 | −0.67% / −0.089 / 1.074 |
| 10 bp | −7.33% / −0.639 / 0.750 | +0.29% / −0.045 / 1.107 | −0.86% / −0.097 / 1.067 |
| 20 bp | −7.73% / −0.664 / 0.736 | −0.08% / −0.060 / 1.095 | −1.24% / −0.112 / 1.054 |

### Break-even cost

**0 bp/side for all three variants** on both criteria (Sharpe = 0 and CAGR = rf): even at *zero* cost none of them clears the risk-free rate. Make-believe free trading does not rescue them, so the cost assumption is not what decides these verdicts.

### Random-rank null (1,000 shuffles, same universe/count/holding/cost)

| Variant | Real Sharpe | Null mean | Null p95 | Percentile |
|---|---|---|---|---|
| V1 | −0.627 | −0.364 | +0.466 | **30.2** |
| V2 | −0.038 | +0.124 | +0.674 | **33.1** |
| V3 | −0.089 | +0.156 | +0.711 | **25.2** |

All three sit **below** the 95th percentile: they do not beat random rank assignment. V1 is *worse* than ~70% of random portfolios.

### Per-symbol contribution (V1, gross return points)

| Symbol | P&L | Share of gross |
|---|---|---|
| NG_F | −0.237 | 29% |
| CL_F | −0.219 | 27% |
| GC_F | +0.171 | 21% |
| SI_F | +0.094 | 11% |
| HG_F | −0.071 | 9% |
| ZS_F | +0.021 | 3% |
| ZC_F | +0.010 | 1% |

**No single symbol dominates, but the losses are concentrated in two:** nat gas and crude are 56% of gross P&L and both lose. Metals (gold + silver) are the only positive contributors. In V2/V3, gold is 31%/28% and silver 23%/22% of gross positive P&L, so the long-only variants are effectively a metals trade wearing a momentum label.

### Reading item 33

- 7 symbols into terciles is 3 long / 3 short, so each commodity is 1/3 of a leg: concentration is structurally high and the "portfolio" is really 3 bets.
- Shorting was impractical for this capital base in the long-only variants, but V1 shows the short leg itself is the problem: it is the *losers* that keep losing.
- **Sample limitation:** 5 years, 48 rebalances, one window that includes the 2022 commodity spike. A 252-day formation is a long lookback for a 4-year usable sample.

### Verdict item 33

**KILL** for V1, V2 and V3 (decisive: Sharpe at 10 bp/side is negative for all three; null percentile 25–33 < 95; V1's excess-vs-SPY CI excludes zero on the negative side). **Conditional** on the cost assumption and the 5-year sample; but since break-even cost is 0 bp, cost is not what kills it.

---

## 4. Item 34 results

SPY buy-and-hold over the same window: **17.80% CAGR, Sharpe 0.987**.

Buy-and-hold bond references (zero cost, same window) — note every bond ETF has a **negative Sharpe vs a 4.32% T-bill**, which is the rate regime talking:

| ETF | CAGR | Sharpe vs rf | MaxDD |
|---|---|---|---|
| TLT | −0.4% | −0.259 | −20.2% |
| IEF | +2.6% | −0.213 | −8.8% |
| SHY | +3.7% | −0.381 | −0.9% |
| AGG | +3.9% | −0.053 | −6.2% |
| LQD | +4.9% | +0.097 | −7.9% |
| JNK | +7.4% | +0.543 | −2.9% |
| HYG | +7.1% | +0.521 | −2.7% |

| Test | CAGR | Vol | Sharpe vs rf | MaxDD | Skew | Worst month | PF (5bp) | Null pct | Excess vs SPY [95% CI] |
|---|---|---|---|---|---|---|---|---|---|
| B1 time-series long-only | **+1.63%** | 4.7% | **−0.550** | −5.8% | −0.241 | −3.15% | 1.312 | **2.0** | −16.17% [−30.0%, −4.1%] |
| B2 cross-sectional L/S | **−1.28%** | 3.3% | **−1.699** | −5.3% | −0.503 | −2.44% | 0.743 | n/a (no null declared) | −19.09% [−35.6%, −4.3%] |
| B3 yield-timing → TLT | **−2.05%** | 5.9% | **−1.063** | −11.6% | **−1.452** | −5.45% | 0.737 | n/a (no null declared) | −19.85% [−35.5%, −6.0%] |

B1 was in the market **89.8%** of months; B3 **34.7%**.

### Cost sweep (cost only)

| Cost | B1 CAGR / Sharpe | B2 CAGR / Sharpe | B3 CAGR / Sharpe |
|---|---|---|---|
| 2 bp | +1.77% / −0.522 | −1.11% / −1.641 | −1.95% / −1.046 |
| 5 bp | +1.63% / −0.550 | −1.28% / −1.699 | −2.05% / −1.063 |
| 10 bp | +1.40% / −0.596 | −1.57% / −1.795 | −2.22% / −1.091 |
| 20 bp | +0.95% / −0.688 | −2.14% / −1.987 | −2.56% / −1.146 |

### Break-even cost

**0 bp/side for B1, B2 and B3** on the Sharpe criterion: none clears a 4.32% T-bill even at zero cost. Cost is not the deciding factor.

### Random null (B1, 1,000 shuffles, same count/hold/cost)

Real Sharpe −0.550, null mean −0.327, null p95 −0.151, **percentile 2.0** — B1 is worse than 98% of random equal-count bond baskets. The rule's ETF selection has no value; the 2.0 percentile says it is actively worse than random within this window.

### Sample check (the negative-skew trap)

DGS10 over the tested window ran **3.30% → 5.31% (max) → 5.04% (end)**, starting at 4.10%. A rising-rate period **is** present (the 2022-23 bear). But it is **one** sustained bear: a single episode cannot distinguish a robust bond-timing rule from a lucky one. B3's skew of **−1.45** with a −11.6% maxDD is exactly the negative-skew profile the brief warned about: 81.6% of its months were positive, yet the mean month is negative.

### Reading item 34

- **All three bond-momentum rules lose to cash**, and the buy-and-hold ETFs are mostly negative in Sharpe too: in this window the asset class itself, not the rule, is the problem.
- B1 (the only rule with a null) is at the **2nd percentile**: worse than random.
- **B3 is an untradeable signal mapped through TLT.** Its P&L and its cost belong to TLT, not to the yield signal. It is reported as a mapping, not as a tradeable yield strategy.
- **Conditional caveat:** the ETF `Close` behaves as a dividend-adjusted series (proven for SHY: short duration, rates up ~4%, yet +10.4% over 5 years is only possible with coupons reinvested). The adjustment method is **UNMEASURED**, so absolute CAGRs carry that uncertainty; relative and null comparisons do not.

### Verdict item 34

**KILL** for B1, B2 and B3 (decisive: all Sharpe-vs-rf negative at every cost, break-even 0 bp, excess-vs-SPY CI excludes zero on the negative side; B1 null at the 2nd percentile). **Conditional** on the ETF-cost assumption, the UNMEASURED dividend-adjustment method, and a window with a single bond bear.

---

## 5. What would change my mind

- **Item 33:** a longer history (15–20 years across multiple commodity supercycles) with the same rule, and a positive null percentile. The metals leg is the only thread worth pulling: a metals-only long-only momentum test, pre-registered separately, could differ from this 7-commodity mix.
- **Item 34:** a window containing *two* independent rising-rate episodes, plus measured (not assumed) ETF spreads. B1's 2nd-percentile null would have to move above 95 before the rule deserved another look.
- **Both:** an actual measurement of futures/ETF transaction cost would let these verdicts become unconditional instead of conditional. Right now none of the six rules is close enough to break-even for cost to matter, so that measurement would likely confirm rather than overturn the KILLs.
