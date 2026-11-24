# What a human should actually buy — CORRECTED

**Date:** 2026-11-23 · **Supersedes:** `FUNDS_WHAT_TO_BUY_2026-11-23.md` (Kilo's original)
**Tool:** `tools/fund_deep_dive.py` (schema v2) · **Data:** adjusted closes 2021-11-15 → 2026-11-13, 1,254 daily returns
**Branch:** `feat/fund-deep-dive-fixes-2026-11-23`

> **Paper only. Not investment advice.** Beta/buying analysis, not an edge claim.
> Past five years, bull-heavy, taxes not modelled. Reproduce: `python3 tools/fund_deep_dive.py --anchors`

---

## Errata — what the first review got wrong

The peer review (subq) was **directionally right but 4 of 12 claims were false**. Each was
checked against the code or the data, not taken on assertion.

| Review claim | Verdict | Evidence |
|---|---|---|
| Code is markdown-mangled, cannot run | **REFUTED** | `py_compile` clean; reproduces every number. The garbling was transcript rendering. |
| "Fee gap over-predicts the FXAIX−SPY gap" | **REFUTED — unit error** | Compared **5-year** fee drag (0.40pp) to the **per-year** gap (0.17pp). Same units: 0.17pp/yr ≈ 0.85pp over 5y **>** 0.40pp. The gap *exceeds* the fee, not the reverse. |
| "No tax drag modelled" | **REFUTED** | The original had a dedicated §"The mutual-fund catch": capital-gains distributions, taxable vs registered. |
| "No minimums / practicality" | **REFUTED** | Original covered $0 / $3,000 / fractional shares. |

The review also **missed four real defects**, fixed here: the Sortino denominator, the additive
net-CAGR, the population stdev, and the Python ≥3.11 dependency.

## Errata — what the original document got wrong

| # | Original claim | Correction |
|---|---|---|
| 1 | "Sharpe 0.728" for FXAIX, "0.714" SPY | Those were `(μ−MER)/σ`, **not Sharpe**. True excess-of-cash: **0.457** and **0.443**. |
| 2 | SGOV Sharpe 15.886 | Undefined. Emitted as `null` now. |
| 3 | 60/40 at 7.05%, "monthly rebalance" | The code rebalanced **daily**; `rebal` was ignored. True monthly: **6.91%**. |
| 4 | "FXAIX net CAGR +0.17pp higher — durable" | The **gross** advantage **flips sign** between halves (+0.099 → −0.021). Only the **fee** is durable. |
| 5 | "60/40 gives up return for a shallower hole" | True **trailing**, but BND's forward **distribution yield is 4.11%** (not YTM — see the correction below), against a −0.29% trailing CAGR. On current yields bonds are expected to *contribute*, which changes the forward case. |

---

## The measured table (corrected)

Cash hurdle **R_f = 3.81%/yr** (SGOV trailing net CAGR).

| instrument | MER | net CAGR | vol | Sharpe | Sortino | max DD |
|---|---:|---:|---:|---:|---:|---:|
| **Fidelity 500 Index (FXAIX)** MF | 0.015% | 11.66% | 17.2% | **0.457** | 0.652 | **−24.5%** |
| **SPDR S&P 500 (SPY)** ETF | 0.0945% | 11.48% | 17.3% | **0.443** | 0.634 | **−24.5%** |
| Fidelity ZERO Total Mkt (FZROX) MF | 0.00% | 10.74% | 17.6% | 0.393 | 0.560 | −25.12% |
| Vanguard Total Mkt (VTI) ETF | 0.03% | 10.49% | 17.7% | 0.379 | 0.539 | −25.36% |
| Vanguard Total Stock (VTSAX) MF | 0.04% | 10.48% | 17.6% | 0.379 | 0.539 | −25.36% |
| **Vanguard Total Bond (BND)** ETF | 0.03% | -0.32% | 6.1% | **−0.680** | −0.932 | **−17.31%** |
| **iShares 0-3mo T-bill (SGOV)** ETF | 0.09% | 3.81% | 0.2% | **n/a (cash)** | n/a | **−0.03%** |

Note how the correction bites: BND's Sharpe goes from a harmless −0.02 to **−0.68** — over the
window it destroyed value *against cash*, which the original table hid.

## If you spend in CAD — the largest term in this report

`python3 tools/fund_cad_view.py` (artifact: `reports/fund_cad_view.json`). USD/CAD went
**1.2545 → 1.4248** over the window, i.e. CAD weakened about **2.59%/yr**.

| fund | USD net CAGR | CAD net CAGR | FX effect | CAD Sharpe | CAD vol | CAD max DD |
|---|---:|---:|---:|---:|---:|---:|
| SPY | 11.48% | **14.37%** | +2.89 | 0.429 | 18.35% | −22.61% |
| FXAIX | 11.66% | **14.55%** | +2.89 | 0.443 | 18.19% | −22.57% |
| VTI | 10.49% | 13.36% | +2.87 | 0.368 | 18.62% | −24.09% |
| BND | −0.32% | 2.27% | +2.59 | −0.494 | 8.56% | −13.27% |
| SGOV | 3.81% | 6.50% | +2.69 | n/a (cash) | 6.05% | −6.33% |

**The currency effect is roughly 33x the fee edge.** This entire report spends most of its length
resolving a 0.0795pp/yr question while, for a CAD holder, the unhedged currency exposure was worth
~2.9pp/yr — and it went the *favourable* way. Ranking FXAIX against SPY to two decimals while
leaving currency unmentioned would be measuring the wrong thing carefully.

Three things this does **not** say:

1. **It is not a forecast.** CAD weakening over this window was a windfall. A CAD holder of unhedged
   USD assets is running a currency position; the same series reversed would subtract a similar
   amount. Nothing here predicts CAD.
2. **The CAD cash hurdle rose too — to 6.50%.** Holding T-bills via SGOV also gained from the FX
   move, which is why the CAD Sharpe ratios stay close to the USD ones. The *excess* return is what
   matters, and it barely changed. Adding FX to both the asset and the benchmark largely cancels in
   the ratio.
3. **Hedging is approximated, not measured.** A hedged share class removes the FX term and pays
   forward points; the tool uses an assumed carry of −1.0%/yr (a parameter, not a data point) and
   labels the output as approximate.

The practical reading: **decide currency exposure deliberately, then pick the cheapest vehicle for
it.** The vehicle choice is a rounding error next to the currency decision.

## Precision — the point estimates are far less certain than they look

Moving-block bootstrap (21-day blocks, 1,000 draws, fixed seed), 90% intervals on CAGR:

| fund | CAGR (gross) | 90% CI |
|---|---:|---|
| SPY | 11.59% | **[−0.10, 24.92]** |
| FXAIX | 11.67% | **[0.01, 25.02]** |
| FZROX | 10.74% | [−1.07, 24.39] |
| VTI | 10.53% | [−1.33, 24.09] |
| VTSAX | 10.52% | [−1.36, 24.03] |
| BND | −0.29% | [−4.75, 4.17] |
| SGOV | 3.90% | [3.57, 4.27] |

Equity CAGR intervals span ~25 percentage points. **Ranking equity funds on 5-year CAGR is not
supported by this data.** Only the cash series is tight.

### The interval width depends on a choice I made (block length)

A reviewer objected that a 21-day moving block is too short for equity returns, since
autocorrelation runs for weeks to months, and that the intervals should therefore be too *narrow*.
That is testable, so it was tested (`tools/fund_block_sensitivity.py`):

| block | ~blocks | SPY 90% width | BND 90% width |
|---:|---:|---:|---:|
| 5 | 250 | 26.11 | 8.42 |
| **21 (used)** | 59 | **25.02** | **8.93** |
| 63 | 19 | 23.40 | 9.73 |
| 126 | 9 | 21.75 | 8.17 |
| 252 | 4 | 18.81 | 7.38 |

**The objection's direction does not hold.** For SPY the width *shrinks* as blocks lengthen
(26.11 → 18.81), so the 21-day choice is not producing too-narrow an interval — it sits near the
wide end. What is true is that the width moves by roughly ±29% depending on the block, so the
choice should be disclosed rather than treated as canonical. One trap worth naming: at block=252
there are only ~4 blocks, so a narrow interval there reflects *few* effective samples, not more
information.

The conclusion this strengthens is the existing one: don't rank funds on point estimates from this
window, and don't read 2 decimal places as precision.

## Step 0 — the account wrapper decides this, not the fund

**(plan item E10.)** The original document asked "mutual fund or ETF?" first. That is the wrong
first question. Whether the fee edge in the next section is worth anything, and whether the cheaper
fund is even *purchasable*, depends on which account the money sits in. Answer this first.

### The two facts that reorder everything

1. **ETF vs MF is a tax question in a taxable account and a cost question everywhere else.** ETFs
   create and redeem in kind, so they rarely distribute capital gains; a mutual fund must sell
   securities to meet redemptions and distributes the gains to every holder. In a taxable account
   that difference can exceed the MER gap. In a tax-sheltered account it is worth **exactly zero** —
   so the only thing left to compare is the expense ratio.
2. **The funds named in this report may not be available to you at all — and the reason is legal, not
   commercial.** FXAIX, FZROX and VTSAX are US-domiciled mutual funds. For a Canadian resident the
   binding obstacle is **PFIC** (Passive Foreign Investment Company) treatment: a non-Canadian fund
   held by a Canadian is a PFIC, taxed punitively with no step-up in basis. Brokers block them
   because of that, not out of caprice. FZROX additionally is a Fidelity loss-leader offered only in
   US Fidelity accounts. If you are investing from Canada, most of the fund-specific conclusions
   here do not apply as written — the transferable conclusion is the *method*, not the ticker.

3. **For a non-US person, the account wrapper can matter more than the expense ratio.** Two things
   routinely outrank a 0.08pp fee difference and are not modelled in the numbers below:
   - **US estate tax.** US-situs assets held by a non-resident alien are exposed to US estate tax
     above a low exemption threshold (~US$60,000). A Canadian holding US-domiciled funds directly
     can face a charge that dwarfs any MER saving. Inside an RRSP this is generally not an issue;
     in a taxable account it can make Canadian-domiciled exposure the correct choice despite a
     higher fee.
   - **Currency.** A CAD-based investor's return is CAD/USD-sensitive. Unhedged versus hedged share
     classes move that exposure, and currency moves can swamp a 0.2–0.5% fee advantage in a single
     year. **This is now measured rather than just flagged** — see "If you spend in CAD" below,
     where over this window the FX term was about 33x the fee edge.

### What the wrapper implies

| account | tax on distributions | is the fee comparison still meaningful? | what to optimise |
|---|---|---|---|
| US taxable brokerage | **yes**, MFs distribute gains | yes — and the ETF's in-kind structure often beats the fee edge | tax efficiency, then MER |
| US Roth IRA / 401(k) / traditional IRA | no | yes, undiluted | **MER only** — FZROX/FXAIX win outright |
| Canadian TFSA | no Canadian tax on growth | yes — but a separate US tax drag applies on top | MER, **and** avoid US-domiciled holdings (no treaty relief in a TFSA) |
| Canadian RRSP | deferred | yes, undiluted | MER; US-domiciled is *preferred* here (treaty relief) |
| Canadian taxable | yes | yes — but the MF's distributions can swamp it | tax efficiency, then MER, **and** check US estate-tax exposure |

### The Canadian withholding wrinkle (flag, not advice)

US-domiciled funds pay US dividend withholding to non-residents. Under the Canada–US treaty an
**RRSP is exempt**; a **TFSA is not**, so roughly 15% of the US **dividend** — not capital gains,
not interest — is lost permanently inside a TFSA. The exemption also depends on the correct
**W-8BEN** declaration being on file. This partially inverts the naive answer: in a TFSA you may
want Canadian-domiciled (or swap-based) exposure even at a higher MER, while in an RRSP the
US-domiciled fund is the efficient choice.

Note the two effects are separate and should not be netted into one "does the fee edge survive"
figure: the MER gap is a cost, withholding is a tax. A 0.08pp fee advantage is real even when a 15%
dividend drag is larger — they simply get added, not compared.

**I have not verified this against current CRA/IRS guidance in this session** — treat it as a
question to confirm with a tax professional, not a conclusion.

### Sizing the withholding drag against the fee edge

The report otherwise spends its length on a **0.0795pp/yr** fee difference. The withholding
question was left as an unverified paragraph; it is arithmetic, so it is sized here
(`tools/fund_withholding_cost.py`, artifact `reports/fund_withholding.json`).

| holding | distribution yield | 15% treaty drag | 30% no-treaty | x fee edge |
|---|---:|---:|---:|---:|
| SPY (US equity) | 1.00% | 0.150 pp | 0.300 pp | 1.9x |
| VTI (US total market) | 1.06% | 0.159 pp | 0.318 pp | 2.0x |
| VEA-equivalent (intl equity) | 2.46% | 0.369 pp | 0.738 pp | 4.6x |
| BND (bond interest) | 4.11% | 0.000 pp | 0.000 pp | 0.0x |
| SGOV (T-bill interest) | 3.64% | 0.000 pp | 0.000 pp | 0.0x |

**The withholding cost on the equity sleeve is 1.9x to 4.6x the fee edge**, and it lands only
on the equity sleeve. Two consequences:

1. A single blended withholding number for a 60/40 would be **wrong** — US-source portfolio
   interest paid to a non-resident is generally exempt, so the bonds contribute nothing to this
   drag while carrying the largest distribution yield. Quoting "15% of the portfolio yield"
   would overstate it badly on a bond-heavy mix.
2. **A TFSA is the worst home for US-domiciled equity** in this list: no treaty relief, so the
   drag is real and permanent. An RRSP is exempt, which is why the domicile preference flips
   between the two accounts.

These rates (30% statutory / 15% treaty) are verified figures; their *applicability* to a given
account is **not verified in this session**, and `tax_treatment_verified: false` is recorded in
the artifact rather than left implicit.

### Why this is section zero and not a footnote

Four of the five original "what should I buy" recommendations are conditional on a US tax-sheltered
account. If you are in a Canadian taxable account the ranking changes; if you are in a TFSA the
*domicile* decision can outweigh the MER decision entirely. Leading with the fund comparison invites
the reader to apply a conclusion that was never computed for their situation.

> **Jurisdiction decided (2026-11-24):** this report answers for a **Canadian resident**. The
> reasoning, the alternatives weighed, and what would change if that is wrong are in
> `docs/edge_research/JURISDICTION_DECISION_2026-11-24.md`. The US-taxpayer case is kept as a
> short appendix. The measured numbers below were computed in USD and are correct as USD
> numbers; "If you spend in CAD" converts them.

## Step 1 — does a mutual fund beat the ETF? (only asked after the wrapper)

Given a tax-sheltered US wrapper, the fee comparison is the whole comparison. Paired bootstrap on the
*difference* series (the correct test; separate intervals prove nothing for two near-identical
series):

| pair | gross | fee advantage | **net** | distinguishable from zero? |
|---|---:|---:|---:|---|
| FXAIX − SPY | +0.051 | +0.0795 | **+0.131** | **No** |
| FZROX − VTI | +0.192 | +0.0300 | +0.222 | No |
| VTI − VTSAX | +0.013 | +0.0100 | +0.023 | No |

Split in half:

| FXAIX − SPY | gross | net | distinguishable? |
|---|---:|---:|---|
| H1 (2021-11 → 2024-11) | +0.099 | **+0.178** | No |
| H2 (2024-11 → 2026-11) | **−0.021** | **+0.059** | No |

**The defensible claim:** the fee edge (0.0795pp/yr) is contractual and keeps the *net* gap
positive in both halves. The *realised* outperformance is noise and changed sign mid-window. You
cannot demonstrate FXAIX "beat" SPY from this data — you can only show it is cheaper.

## Risk — rebalancing matters, and not in the direction expected

60/40 SPY/BND, 5bp spread on the traded fraction:

| schedule | CAGR | vol | Sharpe | max DD | turnover |
|---|---:|---:|---:|---:|---:|
| **buy & hold** | **7.45%** | 11.66% | **0.306** | −20.92% | 0.00 |
| daily (1d) | 7.03% | 11.17% | 0.282 | −20.59% | 2.28 |
| monthly (21d) | 6.91% | 11.09% | 0.273 | −20.73% | 0.45 |
| quarterly (63d) | 6.78% | 11.04% | 0.262 | −20.87% | 0.17 |

The review predicted daily rebalancing would *overstate* a 60/40 via volatility harvesting. In
this window the **opposite** held: more frequent rebalancing **lowered** return, because it kept
buying a falling bond sleeve. The harvesting effect is real but its **sign depends on the relative
performance of the sleeves** — it is not a free lunch.

The reviewer's arithmetic concern is fair and worth stating explicitly: the measured table shows
**geometric** net CAGRs (FXAIX 11.66% − SPY 11.48% = 0.18pp), while the paired table shows the
**arithmetic** annualised mean of the daily difference series (0.131pp). These are different
estimands and are not expected to match:

- geometric CAGRs: $(V_T/V_0)^{1/T} - 1$, compounded
- paired figure: $\overline{r_A - r_B} \times 252$, an arithmetic average

The paired figure is the right one for "is the difference distinguishable from zero", because it
bootstraps the *difference* series and the two legs are near-perfectly correlated — resampling each
fund separately would badly overstate the uncertainty. The geometric table is the right one for "what
would I have earned". Neither is wrong; quoting one against the other is.

## The glide path (D6/D7) — bonds were pure drag in this window

`python3 tools/fund_glide_path.py` walks the equity allocation from 100/0 down to 40/60:

| equity/bond | CAGR (gross) | CAGR (net) | vol | Sharpe | max DD |
|---|---:|---:|---:|---:|---:|
| 100/0 | 11.59% | 11.48% | 17.33% | **0.443** | −24.50% |
| 90/10 | 10.61% | 10.51% | 15.91% | 0.421 | −23.52% |
| 80/20 | 9.59% | 9.50% | 14.49% | 0.393 | −22.61% |
| 70/30 | 8.54% | 8.46% | 13.07% | 0.356 | −21.74% |
| 60/40 | 7.45% | 7.37% | 11.66% | 0.306 | −20.92% |
| 50/50 | 6.31% | 6.24% | 10.28% | 0.236 | −20.09% |
| 40/60 | 5.11% | 5.06% | 8.95% | 0.139 | −19.26% |

**Sharpe falls monotonically as bonds are added.** In this window every bond allocation
*reduced* risk-adjusted return, because BND's excess return over cash was negative
(Sharpe −0.68). Adding a negatively-performing sleeve lowers volatility less than it lowers
return — the diversification benefit was smaller than the drag.

Quarterly rebalancing is worse at every mix (60/40: 6.71% net vs 7.37% buy-and-hold), with
0.17 turnover — consistent with the rebalancing table above: rebalancing kept buying the
falling sleeve.

**Read this against the forward anchors, not on its own.** On a forward BND distribution yield of
4.11% (a floor — true YTM is typically higher) versus a 4.15% cash rate, a bond sleeve is roughly
neutral-to-positive going forward — subject to duration risk, since a rate rise hits price before
yield helps. So this table's monotonic Sharpe decline is a statement about the *past five years of
rising rates*, not a general law. This is the SPY/BND line only — it is not the efficient frontier
over all assets, and a point further left may exist.

## Forward anchors (current, not trailing)

Fetched 2026-11-23 via `--anchors`; snapshot committed at
`reports/fund_forward_anchors.json` so these are traceable to a dated fetch
rather than a session artifact:

- **Cash (13-week T-bill, ^IRX): 4.15%** as of 2026-11-23 — vs 3.81% trailing SGOV
- **BND distribution yield: 4.11%** (trailing twelve months) — vs −0.29% trailing CAGR

> **Correction.** An earlier version of this section called 4.11% BND's "yield-to-maturity".
> It is not. The number comes from yfinance's `yield` field, which is the **distribution yield**
> over the trailing year. For a bond fund trading at a discount the true YTM is typically
> **higher** than the distribution yield, so the labelling understated the forward bond case —
> it did not create it. The true YTM is not available from this data source and is **not fetched
> here**; treat 4.11% as a conservative floor, not an estimate of YTM.

**This is still the single largest correction — but it is not a forecast.** BND's forward yield of
~4.1% (at minimum) compares with a −0.29% trailing CAGR, which is why the original "60/40 gives up
return" reading was misleading.

**The qualifier matters as much as the number.** A yield-to-maturity is the expected return only if
the fund is held for roughly its duration, coupons are reinvested at that yield, and yields do not
change. BND's duration is around six years, so a 1pp rise in yields is roughly a 6% price fall —
price risk dominates over any 1-3 year horizon. Treating 4.11% as "what bonds will return next
year" would be a mistake, and an independent review was right to flag the first draft for implying
it. The defensible statement is narrower: **a bond sleeve is no longer expected to be a guaranteed
loss at current yields**, not that it is expected to earn ~4% annually.

## Futures — explicitly out of scope

The request mentioned futures. They are **not** analysed, and adjusted closes are the wrong input
for them: a continuous futures series embeds roll assumptions that a share-price series does not,
and the relevant economics (roll yield, contango/backwardation, margin, financing) are absent from
this dataset. Doing this properly needs front-month settlements and roll dates. **Out of scope —
requires contract-level data.** Treat any futures conclusion from this dataset as invalid.

## The answer for a Canadian resident (the decision this report now makes)

Per `docs/edge_research/JURISDICTION_DECISION_2026-11-24.md`, this report answers for a Canadian
resident. The US-domiciled funds above are unusable for that holder on PFIC grounds, so the
recommendation is tested on funds a Canadian can actually buy —
`python3 tools/fund_cad_home.py` (artifact `reports/fund_cad_home.json`).

TSX-listed, priced in CAD, cash hurdle = CASH.TO net 3.17%/yr:

| ticker | MER | gross CAGR | net CAGR | vol | Sharpe | max DD | what it is |
|---|---:|---:|---:|---:|---:|---:|---|
| VFV.TO | 0.09% | 14.31% | **14.21%** | 15.35% | **0.719** | −22.19% | S&P 500, CAD, unhedged |
| ZSP.TO | 0.09% | 14.31% | 14.21% | 15.41% | 0.717 | −22.25% | S&P 500, CAD, unhedged |
| VUN.TO | 0.17% | 13.10% | 12.90% | 15.85% | 0.615 | −23.67% | US total market, CAD |
| XEQT.TO | 0.20% | 12.62% | 12.39% | 13.53% | 0.682 | −19.06% | all-equity, CAD |
| ZAG.TO | 0.09% | 0.63% | 0.54% | 6.62% | −0.397 | −15.46% | aggregate bond, CAD |
| CASH.TO | 0.11% | 3.28% | 3.17% | 0.59% | n/a (cash) | −0.80% | high-interest savings, CAD |

**The wrapper costs nothing for the core holding — it is cheaper.** VFV.TO/ZSP.TO at 0.09% are
*below* SPY's 0.0945%, so a Canadian gets S&P 500 exposure, in CAD, without PFIC, at a lower fee
than the US-listed ETF this report spent its length comparing. The cost only appears in the other
sleeves:

| CAD-listed | vs US-listed | wrapper cost |
|---|---|---:|
| VFV.TO / ZSP.TO | SPY | −0.0045 pp/yr (**cheaper**) |
| VUN.TO | VTI | +0.1400 pp/yr |
| ZAG.TO | BND | +0.0600 pp/yr |
| CASH.TO | SGOV | +0.0200 pp/yr |

So the Canadian answer is: **VFV.TO or ZSP.TO as the core**, accept ~0.14pp of wrapper cost if you
want total-market breadth (VUN) rather than the S&P 500, and expect the bond sleeve (ZAG) to have
been a drag in this window (Sharpe −0.397) for the same reason BND was — the trailing window, not a
law.

Two things this table does **not** settle:

- **A CAD-listed unhedged fund embeds USD exposure inside a CAD wrapper.** That is a different
  exposure from holding a USD fund and converting at the broker, and the two should not be
  conflated. VFV's 14.21% is partly the same currency windfall measured in "If you spend in CAD".
- **MER is not total cost.** Withholding on the fund's own US dividends is levied inside the ETF
  (a Canadian-domiciled fund is generally not a PFIC and not subject to the TFSA withholding
  problem, which is precisely its advantage), but the fund still pays US withholding at the fund
  level. That drag is not modelled here and is the next thing to measure.

## Decision table

| vehicle | type | MER | minimum | tax efficiency (taxable) | fractional | best fit |
|---|---|---:|---|---|---|---|
| FZROX | index MF | 0.00% | $0 (US Fidelity only) | low (can distribute gains) | n/a (MF) | max-cost-efficiency, registered |
| FXAIX | index MF | 0.015% | $0 | low | n/a (MF) | core S&P 500 holding |
| VTSAX | index MF | 0.04% | $3,000 | low | n/a (MF) | total market, Vanguard |
| VTI | ETF | 0.03% | 1 share | **high** (in-kind) | usually | total market, taxable |
| SPY | ETF | 0.0945% | 1 share | high | usually | liquidity/trading, not buy-and-hold |
| BND | ETF | 0.03% | 1 share | high | usually | bond sleeve |
| SGOV | ETF | 0.09% | 1 share | high | usually | cash parking |

## Bottom line

1. **Currency exposure first, if you do not spend in USD.** Over this window it was worth ~2.9pp/yr
   — about 33x the fee question. Pick hedged or unhedged deliberately; the vehicle choice is a
   rounding error next to it. (And it is not a forecast: the same move reversed costs the same.)
2. **Then the account wrapper (Step 0).** Four of the five recommendations are conditional on a US
   tax-sheltered account.
3. **Then the vehicle (Step 1).** Broad low-cost index. Same beta everywhere; choose the lowest total
   cost you can actually access.
4. **MF vs ETF is a tax-and-minimum question, not a return question.** The fee edge is real
   (~0.08pp/yr); the return edge is unmeasurable here.
5. **Risk:** 100% equity returned ~11.5%/yr in USD with a −24.5% drawdown. If you cannot hold through
   that, a 60/40 is defensible — and on *current* yields more defensible than the trailing numbers
   suggest, subject to duration risk.
6. **Do not rank funds on 5-year CAGR.** The intervals overlap almost completely, and their width
   moves ~29% depending on a block-length choice.

## What would change this answer

- **CAD strengthening** instead of weakening — would subtract ~2.9pp/yr from an unhedged CAD
  holder's return and could dominate everything else in this report
- Cash falling well below ~2% (raises the equity hurdle back to favourable)
- A sustained rise in yields from here: helps a bond sleeve's forward return but hits its price
  first, over roughly BND's six-year duration
- A sustained drop in the net gap making the fee advantage negative
- A tax regime where MF capital-gains distributions exceed the fee edge (plan items E2–E6, needs
  jurisdiction)

## Still open

Plan: `docs/edge_research/FUND_DEEP_DIVE_TODO_2026-11-23.md` (173 items, 15 sections).

- **E3–E6: DECIDED 2026-11-24** — Canadian resident; see
  `docs/edge_research/JURISDICTION_DECISION_2026-11-24.md`. No longer blocked; the US-taxpayer
  case is an appendix.
- **G3–G7 (blocked):** futures need contract-level data (front-month settlements + roll dates).
- Peer reviews run: two rounds against a local model and one against a non-local model. They found
  the two-estimand question, four Step 0 omissions, the forward-return overstatement, and one claim
  that did not survive testing (block length). A second independent external review has not been run.
- The Canadian withholding statement in Step 0 is flagged as unverified — confirm before relying on it.
- Hedging cost in the CAD section is an assumed carry parameter, not a measured forward curve.
- **Resolved since this report was first drafted:** L1 (dividends reinvested — proven via SGOV
  control), the gross/net field confusion, the mislabelled bond yield, and currency (previously
  "unmodelled", now measured).
