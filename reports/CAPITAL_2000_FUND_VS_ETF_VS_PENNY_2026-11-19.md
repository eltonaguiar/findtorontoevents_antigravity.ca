# $2,000: mutual fund, index ETF, low-fee index fund, or penny / sub-$5 stocks?

**Author:** Buffy (Freebuff), worktree `review-main`
**Date:** 2026-11-19
**Question:** is a mutual fund generally good, and if so which one? What about an index-style ETF, or a
low-fee mutual fund if one exists? Versus penny stocks, or mid-tier $5-and-under names?

**Two kinds of evidence are mixed below and I label which is which:**
- **[MEASURED]** = derived from this repo's own artifacts, re-runnable by anyone.
- **[EXTERNAL]** = public fee/regulatory data, cited. Our pipeline has **never measured a mutual
  fund** (`MUTUAL_FUND` class n=0), so every mutual-fund statement is external.

---

## 0. The answer in one paragraph

**A low-fee index mutual fund is the right answer, and it exists — it is just an index fund wearing
the mutual-fund wrapper.** At Fidelity, `FXAIX` costs **0.015%/yr with a $0 minimum**; that is
*cheaper* than the ETF share class of the same index (`VOO`, 0.03%) and costs **$0.30/year on
$2,000**. The mutual-fund *category* is not the problem; the *active* subset is, because you pay
0.4–1.0%/yr for a coin flip on whether the manager beats the index. **Index ETF vs index mutual
fund is a $0.60/year decision — rounding error. Penny stocks are not a rounding error: a single
round trip on a $2.00 stock with a one-cent spread costs about 100bp ≈ $20, which is 66 years of
FXAIX's fee on the same $2,000.** That single comparison settles the penny-stock question without
needing a forecast. And separately: our own pipeline loses money in every class it can measure, so
there is no competing "active" option from this repo worth the capital.

---

## 1. What our own evidence says first [MEASURED]

From `audit_dashboard/data/audit3_ledger.json` (build 2026-11-19T16:42:17Z, 8,613 rows, 359 cells),
net of per-class slippage, 95% CI:

| Class | n | Net %/trade | 95% CI | Verdict |
|---|---|---|---|---|
| CRYPTO | 6,740 | **−0.3089** | **[−0.4195, −0.2022]** | **proven negative** |
| COMMODITY | 51 | **−3.5066** | **[−4.9794, −2.2654]** | **proven negative** |
| FOREX | 258 | −0.0238 | [−0.1167, +0.0755] | zero |
| BOND | 35 | −0.1845 | [−0.4851, +0.1411] | zero, n small |
| ETF | 586 | +0.0060 | [−0.2351, +0.2393] | zero (0.6bp vs ~5bp cost) |
| EQUITY | 939 | **+0.1844** | [−0.1721, +0.5445] | zero-to-slightly-positive |
| FUTURES | 4 | +1.2853 | [−2.948, +5.519] | n=4, not a result |
| **PENNY_STOCK** | **4** | — | — | **unmeasurable** |
| **MEME** | **10** | — | — | **unmeasurable** |
| **CHEAP_STOCKS** | **1** | — | — | **unmeasurable** |
| **MUTUAL_FUND** | **0** | — | — | **never measured** |

`n_proven 0`, `n_candidate 0`, `n_proven_classes 0`. **`selection_alpha.available = true`** on the
live 21:02Z build (it was `false` in the 16:42Z build — correction noted), so the tribunal *can*
now run its selection-vs-beta test, and it still returns nothing. That makes the null earned
rather than forced by missing plumbing.

**Read the bottom four rows twice.** The three categories the question asks about — penny stocks,
cheap (<$5) stocks, and mutual funds — are the three we have the *least* evidence on. Penny: 4 rows.
Cheap stocks: 1 row. Mutual funds: 0 rows. Any claim about them from this repo would be fabrication;
everything below about them is external data plus arithmetic.

**The cost fact that governs everything [MEASURED]:** across 6,611 live-sim trades, gross
+$894.75, fees **$6,774.15**, net **−$5,879.39**. Gross edge ≈ **1.4bp/trade** against ≈**12bp**
round-trip cost. Fees ate **757%** of gross. Gross is *positive* — the signals are not worthless —
but they are 1/9th of the cost of acting on them. **Trading is the leak, not stock selection.**

---

## 2. Is a mutual fund "generally good"? [EXTERNAL]

**The category, yes. The active subset, mostly no — and the distinction is entirely fees.**

- The active-fund problem is arithmetic, not skill-shaming: a manager who beats the index by 1%/yr
  gross and charges 0.75% hands you 0.25%, while the index hands you 0% fee and the full index
  return. Your net result is decided before the first trade.
- Industry asset-weighted average expense ratio is around **0.50%**; Vanguard's own asset-weighted
  average is **~0.08%** [EXTERNAL, provider fee schedules / ICI, as of 2026]. That spread *is* the
  active-vs-index question.
- **A low-fee mutual fund that exists is called an index mutual fund.** There is no separate
  "cheap active" category worth shopping in at this account size.

So: "is a mutual fund generally good?" → the wrapper is neutral, the fee is everything, and cheap
mutual funds are index funds.

---

## 3. The specific funds, at $2,000 [EXTERNAL, verified 2026]

| Fund | ER | Minimum | Cost on $2,000/yr | Note |
|---|---|---|---|---|
| **FXAIX** (Fidelity 500 Index) | **0.015%** | **$0** | **$0.30** | Cheapest S&P 500. Cheaper than VOO. |
| FSKAX (Fidelity Total Market) | 0.015% | $0 | $0.30 | ~4,000 stocks; portable index |
| FNILX (Fidelity ZERO Large Cap) | **0.00%** | $0 | $0.00 | **Not portable** — Fidelity-only, cannot transfer out |
| FZROX (Fidelity ZERO Total Market) | **0.00%** | $0 | $0.00 | Same portability caveat; taxable-account risk |
| SWPPX (Schwab 500) | 0.02% | $0 | $0.40 | |
| SWTSX (Schwab Total Market) | 0.03% | $0 | $0.60 | |
| **VFIAX / VTSAX** (Vanguard Admiral) | 0.04% | **$3,000** | **excluded** | **Below the $3,000 minimum** |
| VOO (S&P 500 ETF) | 0.03% | 1 share / $1 fractional | $0.60 | $680.26 close 2026-11-16 |
| VTI (Total Market ETF) | 0.03% | 1 share / $1 fractional | $0.60 | $364.30 close 2026-11-16 |
| IVV / ITOT (iShares) | 0.03% | fractional | $0.60 | Portable everywhere |

Two facts that matter at exactly $2,000:
1. **Vanguard's mutual funds are out.** VFIAX and VTSAX require $3,000. Their *ETFs* (VOO/VTI) have
   a $1 fractional minimum at Fidelity, Schwab and Vanguard, so Vanguard exposure is still available
   — just not through the mutual-fund wrapper.
2. **Without fractional shares you cannot deploy $2,000 cleanly in VOO.** At $680/share, four shares
   = $2,721 (too much) and three = $2,041 with ~nothing idle — actually fine, but at other balances
   you leave meaningful cash idle. Fractional is available at all three major brokers ($1 minimum at
   Fidelity and Vanguard, $5 at Schwab for Stock Slices), so this is a preference, not an obstacle.

**The ZERO funds are a trap worth naming:** 0.00% looks strictly better than 0.015%, but they are
proprietary. They cannot be transferred to another broker in kind, so a future move forces a sale —
and in a taxable account a forced sale can cost far more than 1.5bp/yr. **For a taxable $2,000,
FSKAX (0.015%, portable) beats FZROX (0.00%, trapped).** I would take FXAIX or FSKAX.

---

## 4. Index ETF vs index mutual fund at $2,000: it does not matter, and here is the proof

| | Index mutual fund (FXAIX/FSKAX) | Index ETF (VOO/VTI) |
|---|---|---|
| Cost on $2,000 | **$0.30/yr** | $0.60/yr |
| Difference | **$0.30/year** — 1.5bp | |
| Trade timing | Once daily at NAV | Intraday at market |
| Spread / premium-discount | **None** | ~1bp, plus premium/discount on thin ETFs |
| Dollar precision | Exact amount | Needs fractional, else share-price rounding |
| Automatic investing | Native | Usually manual |
| Portability | FSKAX yes / FZROX no | **Yes, everywhere** |
| Tax efficiency | Capital-gains distributions possible | In-kind redemption advantage |
| Behavioural risk | **Low** — you cannot day-trade it | **Higher** — it is one tap away |

**$0.30 a year.** The fee difference between the two best implementations is thirty cents. Anyone
who spends an hour deciding between them has spent more than the decision is worth.

**What actually differs is behaviour.** The mutual fund executes once a day at NAV and cannot be
traded intraday; the ETF can. Given that this repo has measured a **9x cost-to-edge deficit** in
intraday trading, the inability to day-trade the mutual fund is a *feature*.

**My pick, and the reasoning:** **FXAIX (or FSKAX) at Fidelity, 0.015%, $0 minimum, $0.30/yr on
$2,000.** If the money is going to sit in a taxable account for decades and you value portability,
**VTI** at 0.03% is equally fine and costs $0.30 more per year. There is no third answer worth
considering at this size.

---

## 5. Penny stocks and sub-$5 / mid-tier stocks: no, and not for the reason you expect

The usual objection is "penny stocks are scams and volatile." That is true but it is not the
disqualifying reason. **The disqualifying reason is that the round-trip cost is larger than any
plausible edge, and we cannot measure them at all.**

### 5.1 The spread arithmetic [EXTERNAL + arithmetic]
A stock at **$2.00** quoting a one-cent spread: 1¢/200¢ = **50bp per side ⇒ ~100bp round trip**. On
$2,000 that is **$20 per round trip**.
- FXAIX on $2,000 costs **$0.30 per year**.
- **One penny-stock round trip = 66 years of index-fund fees.**

Below $1, SEC Rule 612 does not apply (it covers quotes at or above $1.00), so sub-penny quoting is
permitted and spreads can compress to 5–10bp — which sounds better, and is exactly why sub-$1 names
attract high-frequency liquidity provision. But that liquidity is quoting *against* you, and the
volatility, dilution and delisting risk at that price level are not spread problems you can trade
around.

### 5.2 Our own data cannot see them [MEASURED]
PENNY_STOCK n=**4**. CHEAP_STOCKS n=**1**. MEME n=**10**. You cannot compute a win rate, a profit
factor or a confidence interval from that, and if you did, the interval would span everything.

Worse: **we have no survivorship-free small-cap dataset.** Every delisted, reverse-split and
bankrupt name is missing from what we can pull. Any backtest we ran on sub-$5 stocks would be biased
upward **by construction** — we would be measuring the returns of the companies that survived,
which is the definition of the wrong question. A positive result from such a test would be a
guaranteed artefact, not a finding.

### 5.3 "Cheap price per share" is not "cheap valuation"
A $4 stock is not on sale relative to a $400 stock. Price per share is an arbitrary unit; valuation
is price relative to earnings, book, cash flow. A stock at $5 with no earnings is *infinitely*
expensive. **There is no mechanism by which a low share price predicts a high return** — this is one
of the few places in finance where the answer is genuinely unambiguous.

### 5.4 The honest middle position on mid-tier $5–$20 names
These are mostly micro/small caps. Liquidity is better than penny stocks, spreads are maybe 10–30bp,
and the survivorship problem is *smaller* but real. Nothing here is disqualifying in principle. It is
disqualified *for this account* because:
- $2,000 spread across illiquid names cannot take a meaningful position without moving the price;
- we cannot measure them (no clean dataset), so we would be guessing;
- and the measured cost-to-edge deficit (1.4bp edge vs 12bp cost) is *worse*, not better, in less
  liquid names.

That is the class I would revisit **first** if someone builds a survivorship-free dataset — not
because I expect an edge, but because it is the only unmeasured category with plausible liquidity.

### 5.5 The one thing that changed the regulatory picture, and it does not help
**The pattern-day-trader rule was eliminated.** FINRA's intraday margin standard replaced it
effective **2026-06-04**, with a phase-in ending **2027-10-20**. There is **no $25,000 minimum** and
no day-trade count; **$2,000 is the margin minimum** for a margin account, and cash accounts still
trade only settled cash (T+1). [EXTERNAL — FINRA Regulatory Notice 26-10; Investor.gov]

I had earlier reasoned that PDT blocked active trading at $2,000. **That was wrong as of June 2026,
and I am withdrawing it.** The point worth making now is sharper: *the legal barrier is gone, and the
only thing left standing between $2,000 and a losing day-trading career is arithmetic.* At 12bp round
trip on $2,000, each trip costs **$2.40**. To make $20/day you need **more than 8 fully-positive round
trips every single day**. Measured gross edge is **$0.28 per trip**. You would be paying $2.40 to
chase $0.28.

---

## 6. The honest expected value of $2,000

| Route | Expected annual | Worst realistic year | Confidence in the number |
|---|---|---|---|
| FXAIX/FSKAX or VOO/VTI | **+$140 to +$160** (7–8% nominal) | **−$400 to −$1,000** (−20% to −50%) | High — this is the long-run equity premium, not a forecast |
| TAA rotation variant | +$120 to +$140 (6–7%) | **−$250 to −$400** (−12% to −20%) | Medium — my own measurement, lagged and costed |
| Our pick pipeline | **negative in every measurable class** | unbounded downside on concentrated crypto | High — CI entirely below zero for CRYPTO and COMMODITY |
| Penny / sub-$5 trading | **negative**, ~$20/round trip in friction | 100% | High on the arithmetic, zero data on outcomes |
| Day trading $2,000 | **−$5,879 on 6,611 simulated trades** | account destruction | High — measured, cost-dominated |

**The number to sit with: $140–160/year.** That is what $2,000 honestly produces. Anyone promising
more from this repo's picks is promising something our own tribunal says is negative.

**The TAA variant, honestly:** measured at **−38% max drawdown vs SPY's −51%**, for **1–2 points less
CAGR**. It is a *drawdown-control allocation*, not an edge. Worth using only if the −50% number is
something you would actually sell into — and if it is, the drop to roughly −20% is worth more than
the 1–2 points of return given up.

**Allocation I would actually use ($2,000):**
| Sleeve | Amount | Instrument |
|---|---|---|
| Core | $1,400–1,700 | FXAIX / FSKAX (or VTI if taxable + long horizon) |
| Ballast, optional | $300–600 | Short/intermediate Treasury (SHY/IEF-class) — reduces the drawdown, costs return |
| Everything else | **$0** | No crypto, no commodity, no forex, no penny, no day trading, no picks from this repo |

One to three positions, bought once, rebalanced annually. **Not** four positions — at $2,000 the
complexity is not worth the difference.

---

## 7. What would make me change this answer

- **EQUITY reaching n ≈ 3,540** with net +0.1844%/trade holding (currently 939 rows, CI straddles
  zero). Then EQUITY becomes a candidate and a modest tilt is arguable.
- **Any pod clearing 100 forward rows at PF CI-LB > 1.0 and IR ≥ 0.5.** Then this repo has something
  and the allocation question becomes worth re-asking.
- **A survivorship-free sub-$5 dataset**, which would make mid-tier names measurable for the first
  time. Even then I would expect the spread arithmetic to win.
- **`selection_alpha` returning a positive, CI-clearing result.** It now runs (live 21:02Z build) and
  returns a negative selection alpha, so this is a measured null rather than a plumbing gap.

---

## 8. One-page summary

1. **Mutual funds as a category: fine. Active mutual funds: pay 0.4–1.0%/yr for a coin flip.** The
   cheap ones are index funds, which is the answer to "does a low-fee one exist."
2. **Specific fund at $2,000: FXAIX (0.015%, $0 min) or FSKAX (0.015%, $0 min).** $0.30/year. Vanguard's
   mutual funds need $3,000, so they are out; their ETFs (VOO/VTI) are fine substitutes at $1 fractional.
3. **Index ETF vs index mutual fund: a $0.30/year decision.** The real difference is that the mutual
   fund cannot be day-traded. Given a measured 9x cost deficit, that is a feature.
4. **Penny stocks: no — because 100bp round trip ($20) is 66 years of index fees, and we have 4 rows
   of data and no survivorship-free dataset so we cannot even measure them.** Cheap per-share price
   is not cheap valuation.
5. **Mid-tier $5 names: not yet — same measurement gap with better liquidity.** First thing to
   revisit if a clean dataset appears.
6. **PDT is dead as of June 2026.** No $25k minimum. The only thing stopping $2,000 day trading is
   that 8 winning round trips/day are needed to net $20 when the edge is $0.28/trip.
7. **Honest EV: $140–160/year.** That is the whole prize. Our picks are negative before any skill.

*Measurement, not investment advice. Fee and regulatory figures are external, dated 2026, and should
be re-verified at the provider before any purchase. Nothing produced by this repository currently
clears its own real-money gate.*
