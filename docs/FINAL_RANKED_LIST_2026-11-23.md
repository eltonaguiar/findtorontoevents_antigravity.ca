# FINAL RANKED LIST — for a human with real money

**Date:** 2026-11-23
**Backed by:** `reports/{per_class_evidence,equity_cost_hml,turnover_cost_consequence,quant_metrics_dsr_pbo,hml_result,crypto_funding_carry}.json`
**Hurdle:** 4.32%/yr (`HURDLE_TBILL_APR = 0.0432`) — the bar cash already clears.

---

## The answer in one paragraph

**Buy a broad index ETF and hold it.** Not because it has an edge — it does not; we proved
that — but because it is the only vehicle where the fee arithmetic does not eat the
hurdle, and because everything else we tested either fails on its own numbers or cannot be
measured yet. **Proven edges in this programme: 0.** Every active row below is unproven, so
the ranking is a decision about *cost and risk*, not about alpha.

## What is measured vs what is not

| Input | Status |
|---|---|
| Questrade trade tariff ($0 stock/ETF, $9.95 MF, bond $5k min, FX 1.5%) | **VERIFIED** from Questrade's own pages 2026-11-23 |
| EQUITY round trip **4.98 bp** | **MEASURED** — n=191 names, 238,810 daily + 356,271 minute bars |
| ETF round trip **1–2 bp** | **MEASURED** (4.98 used as a conservative stand-in below) |
| CRYPTO 12.60 bp / FOREX 7.53 bp | **MEASURED** (FOREX = upper bound) |
| Turnover/yr per class | **MEASURED** — identical-criteria grid, top pick per class |
| Mutual-fund / ETF **MERs** | **NOT measured by us** — published industry ranges, marked INFO |

I will not present a MER as if we measured it. The MER ranges below are the only numbers in
this document we have not verified ourselves.

---

## Per-class vehicle choice

| # | Class | Vehicle to use | Fee arithmetic (on $100k, 10 yrs) | Turnover drag | Hold style |
|---|---|---|---|---|---|
| 1 | **ETF** | **The ETF itself** | MER 0.03–0.25% → **$300–2,500**; $0 commission; 1–2 bp spread | **0.99 bp/yr = 0.2% of hurdle** | **BUY AND HOLD** |
| 2 | **STOCKS** | **Broad index ETF**; direct single names only with a proven edge (we have none) | ETF wrapper **$300–2,500**; direct ≈ **$50** one-off at 4.98 bp + $0 ongoing | 2.98 bp/yr = 0.7% | **BUY AND HOLD** |
| 3 | **COMMODITY** | Futures or commodity ETF | ETF wrapper $300–2,500; futures execution **UNMEASURED** | 5.96 bp/yr (PROXY) | **DO NOT HOLD** — PF 0.31, WR 11%, n=28 |
| 4 | **BOND** | **Bond ETF**; direct bonds need $5,000 min and retail spread is **UNMEASURED** | Bond ETF MER 0.05–0.35% → **$500–3,500**; direct = spread only (unknown) | 34.94 bp/yr (PROXY) | **DO NOT HOLD** — n=8, unrankable |
| 5 | **MUTUAL FUNDS** | **Index MF only where no ETF exists.** Never active | Index MF MER 0.30–0.60% → **$3,000–6,000**; active 1.5–2.2% → **$15,000–22,000**; +$9.95/trade | n/a (cost question) | **AVOID ACTIVE** |
| 6 | **FOREX** | **None** | n/a — retail spread + 7.53 bp/round trip | **56.93 bp/yr = 13.2% of hurdle** | **DO NOT TRADE** — PF 0.55, SR −0.03 |
| 7 | **CRYPTO (carry)** | None | 12.60 bp/round trip; net yield 3.07% < 4.32% hurdle | 10.46 bp/yr | **DO NOT HOLD** — DEAD |
| 8 | **CRYPTO (directional)** | None | — | — | **DO NOT TRADE** — ledger broken, SR −0.21 |
| 9 | **OPTIONS** | None available to us | $0 commission + $0.99/contract verified, but **no chain history** | — | **UNKNOWN** |
| 10 | **PREDICTION MARKETS** | Direct on Polymarket/Kalshi (no wrapper) | Different metric: Brier/calibration, not bp | — | **UNKNOWN** |
| 11 | **PRIVATE CREDIT** | None — no data | — | — | **UNKNOWN** |

---

## MUTUAL FUND vs INDEX FUND vs ETF vs DIRECT — the explicit 4-way

Same $100,000, ten years, **no compounding assumed** so the arithmetic is checkable.

| Vehicle | Ongoing MER | MER cost | Trade cost | **Total 10 yr** | vs ETF |
|---|---|---|---|---|---|
| **ETF (index)** | 0.10% (midpoint, INFO) | $1,000 | ~$50 (4.98 bp round trip, MEASURED) | **≈ $1,050** | — |
| **Direct stocks/index basket** | 0% | $0 | ~$50 one-off, but rises with every rebalance | **≈ $50** | 21× cheaper, **but** requires a proven selection edge — we have 0 |
| **Index mutual fund** | 0.45% (INFO) | $4,500 | $20 ($9.95×2, VERIFIED) | **≈ $4,520** | 4.3× more |
| **Active mutual fund** | 1.85% (INFO) | $18,500 | $20 | **≈ $18,520** | **17.6× more** |

**Two things this shows that matter more than the ordering:**

1. **Active management must out-earn the index by ~1.40%/yr before tax just to break even**
   (1.85% − 0.45%) — and by ~1.75%/yr to match a 0.10% ETF. Our entire programme, 146
   pre-registered hypotheses deep, has produced **zero** measured edges of that size. Buying
   active is a bet on a manager's skill we have no way to verify and no evidence to expect.
2. **An active MF MER of 1.85% is 185 bp/yr — 43% of the entire 432 bp hurdle**, consumed
   before a single trade. A vehicle cannot be recommended when it spends nearly half the
   hurdle on itself.

**Direct holding is cheapest on fees and worst on evidence.** At 0% MER it wins the
arithmetic outright — but it only pays if you can pick, and our cross-class momentum
selection scored **DSR 0.319 at the honest N=90, with SR\* 1.259 exceeding our best 1.05**.
Fees saved are real; selection alpha is not.

---

## Top three: BUY AND HOLD vs ENTRY WITH TP/SL

| Rank | Class | Verdict | Turnover cost consequence |
|---|---|---|---|
| **1** | **ETF** | **BUY AND HOLD** | 0.2 round trips/yr × 4.98 bp = **0.99 bp/yr**, **0.2% of the hurdle**. Timing is essentially free of cost — and still not worth doing, because there is no timing edge. |
| **2** | **STOCKS (index)** | **BUY AND HOLD** | 0.6 round trips/yr × 4.98 bp = **2.98 bp/yr**, 0.7% of hurdle. Adding TP/SL to a passive index position would raise turnover for no measured benefit. |
| **3** | **COMMODITY** | **DO NOT HOLD** | 1.2 round trips/yr × 4.97 bp (PROXY) = 5.96 bp/yr — the cost is not the problem; PF 0.31 with 57% of the book in one contract is. |

**Why BUY AND HOLD for #1 and #2, stated as a cost argument rather than a preference:**
entry-with-TP/SL only earns its keep if the timing signal has positive expectancy. Ours does
not — the identical-criteria momentum rule died at DSR 0.319 (N=90). So a TP/SL overlay
would add turnover (and the AA-triggered whipsaw risk) while adding **no** measured return.
For FOREX the point is stark: its top pick turns over **7.6×/yr**, and at 7.53 bp that is
**57 bp/yr — 13.2% of the hurdle paid to a class that returns −3.4%**. Turnover is where a
losing strategy quietly becomes a worse one.

---

## What this list does not claim

- **0 proven edges.** HML KILLED, crypto carry DEAD, cross-class momentum 0/6 after
  deflation. The ranking is about cost, risk and vehicle — not alpha.
- **MERs are not ours.** Marked INFO throughout.
- **One instrument per class** in the backtests (AAPL, SPY, BTC-USD, EURUSD_X, GC_F, TLT).
  That limits generalisation and is why the deflation killed it.
- **Past 5 years only**, and a period unusually kind to trend.

Zero capital sanctioned. Not investment advice.
