# Index + Bond Allocation — Robustness Research Note

**Date:** 2026-11-20
**Status:** Research note / test protocol — **not** a performance claim, not financial advice.
**Scope:** How to verify that a "low-cost broad index fund + bonds" allocation is a durable strategy rather than a fluke of one market or one period, with fees included and compared against a plain buy-and-hold benchmark.

---

## 0. TL;DR

1. A **low-cost broad index fund + bond** portfolio **is** a buy-and-hold strategy. It earns **beta** (market return), not **alpha** (skill-based excess). So the goal is *not* to "beat buy-and-hold" — that framing is circular. The correct question is: **which allocation delivers the most robust risk-adjusted *real* return across markets and periods, after fees?**
2. To prove it "isn't a fluke," run **four tests the worry demands**: (a) different **markets/regions**, (b) different **time periods** (including bad ones), (c) **fees included net-of-cost**, and (d) comparison to a **simple buy-and-hold** benchmark (100% equity and a static target-date style glide).
3. The evidence base (SPIVA, UBS/DMS Global Investment Returns) consistently shows: **most active managers underperform their index over long horizons**, and a broad, low-cost, globally diversified index+bond mix is the **highest-probability path to positive real return** — precisely because it is boring beta, not clever alpha.
4. This note defines the **pre-registered test protocol** so any future backtest can be judged pass/fail honestly. A clean "it holds up across all four tests" is a valid result; so is a clean "it fails in market X" — both are deliverables.

---

## 1. Why the framing matters (avoid the circular test)

"Compare it to a simple buy-and-hold" sounds like a test, but a passive index+bond allocation **is** buy-and-hold. If you rebalance periodically, that is the only active decision in the whole strategy.

The honest decomposition:

| Question | Wrong bar | Right bar |
|----------|-----------|-----------|
| Is this a good strategy? | Does it beat buy-and-hold? (circular — it *is* buy-and-hold) | Does it deliver the **best risk-adjusted real return** among reasonable passive allocations, after fees? |
| Is it a fluke? | Did it do well in one backtest? | Does it hold **across regions, across regimes, and net of costs**, vs a static benchmark? |
| Should I add bonds? | Do bonds raise return? | Do bonds **reduce drawdown and sequence-of-returns risk** enough to justify their lower expected return, given your horizon and risk tolerance? |

**Key insight:** Bonds are not there to *increase* return. They are there to *reduce* the worst-case drawdown and the risk of being forced to sell equities at the bottom. Whether that trade is worth it is a **risk-preference** decision, not a return-maximisation one.

---

## 2. The strategy under test

Define it precisely so it can be replicated. A defensible default:

| Component | Specification | Rationale |
|-----------|---------------|-----------|
| Equity core | Broad, market-cap-weighted global or regional index fund | Lowest cost, widest diversification, no stock-picking |
| Fixed income | Broad investment-grade bond index (govt + aggregate) | Drawdown reduction, ballast |
| Allocation | Static target (e.g., 60/40, 80/20, or age-based glide) | Deterministic, no market-timing |
| Rebalance | Annual or threshold-based (e.g. ±5% drift) | Amortises cost, controls drift |
| Cost | Expense ratio + trading/rebalance cost + tax | Must be modelled explicitly (see §5) |

**Constraints that make it "low-cost broad":**
- Expense ratio ideally **< 0.10–0.20%** for equity, **< 0.15%** for bonds.
- No leverage, no derivatives, no single-country or single-sector concentration.
- Daily liquidity, transparent holdings.

If a proposed "index strategy" cannot state its expense ratio and rebalance rule, it is not testable.

---

## 3. The four robustness tests (the core of this note)

Each test must be **pre-registered** (written down before running) and reported even if it fails.

### Test A — Cross-market / cross-region

Run the same allocation on **each major market separately**, not just one:

- **US** (S&P 500 / CRSP US Total Market)
- **Developed ex-US** (MSCI EAFE / MSCI World ex-US)
- **Emerging markets** (MSCI EM)
- **Canada** (S&P/TSX, given CAD home currency)
- **Global blend** (MSCI ACWI / FTSE All-World)

**Pass condition:** the allocation is **positive in real terms after fees in the majority of regions** and does not depend on a single country's exceptional decade (e.g., US large-cap 2010–2020). If the whole result hinges on US outperformance, it is a **single-market artifact**, not a robust strategy.

**Watch for:** home-country bias (a Canadian investor over-weighting TSX and being underexposed to global growth) and currency effects (unhedged foreign equity adds FX volatility).

### Test B — Cross-time-period (including bad regimes)

Split history into **independent, non-overlapping windows** and also test the **worst** ones:

- Long-run (30–50+ years where data exists — DMS/UBS covers 35 markets since 1900).
- Rolling 10-year windows (to show dispersion of outcomes).
- **Named stress periods:** 1929–32 (Great Depression), 1973–74 (oil shock), 2000–02 (dot-com), 2008–09 (GFC), 2020 (COVID crash), 2022 (rate shock — stocks *and* bonds fell together).

**Pass condition:** the allocation survives the majority of regimes with **positive long-run real return**, and its **worst drawdown is tolerable** vs the equity-only benchmark (bonds should visibly cut the max drawdown). A strategy that only works in the 1982–2021 bond bull market is **not robust** — 2022 proved bonds can lose alongside equities when rates rise.

### Test C — Fees included (net-of-cost)

Gross returns are a fiction. Every result must be **net of**:

| Cost | Typical retail magnitude | Where it bites |
|------|--------------------------|----------------|
| Fund expense ratio | 0.03%–0.20% (index) vs 0.5%–1.5% (active) | Compounds every year |
| Trading / spread / rebalance | 0.02%–0.10% per rebalance | Annual or threshold rebalances |
| Tax (on distributions/gains) | Varies by account & jurisdiction | Can dominate the whole edge |
| Platform / advisory fee | 0%–1%+ | Often the largest silent drag |

**Pass condition:** the strategy keeps a **positive real return after all fees**. Report the **breakeven cost level** — the fee at which the edge disappears. If the margin is thin (< 2× the modelled cost), it is fragile.

**Fees are the single most reliable predictor of active-fund underperformance.** SPIVA reports returns *net of fees* — and the long-horizon underperformance rates are brutal (see §4).

### Test D — Compare to a simple buy-and-hold benchmark

Define two benchmarks up front:

1. **100% equity buy-and-hold** (e.g., global equity index) — the growth benchmark.
2. **A static index+bond buy-and-hold** at a comparable allocation — the "is the rebalance/glide adding anything?" benchmark.

**Pass condition:** the studied allocation is judged on **risk-adjusted** terms (Sharpe / Sortino / max drawdown / recovery time / worst 12-month), **not** raw return. Bonds will usually *lower* raw return; the question is whether they lower *risk* by more. If the allocation does not improve the risk-adjusted profile or the worst-case outcome versus 100% equity, then bonds are not earning their place for that investor.

---

## 4. What the evidence base says (verifiable figures)

These are cited, not invented. Treat each as a dated data point, not a permanent law.

### Active management vs the index (SPIVA)

- **SPIVA U.S. Scorecard Year-End 2025**, Report 1a — *percentage of active funds underperforming their benchmark:*
  - **All domestic funds vs S&P Composite 1500:** 79.83% (1y), 91.47% (5y), 90.43% (10y), **95.01% (20y)**.
  - **All large-cap funds vs S&P 500:** 78.78% (1y), 88.96% (5y), 85.59% (10y), **92.89% (20y)**.
  - Source: S&P Dow Jones Indices, *SPIVA U.S. Scorecard Year-End 2025*, Report 1a (net-of-fee returns).
- **SPIVA Year-End 2024:** 65% of active large-cap U.S. equity funds underperformed the S&P 500 in 2024, vs a **64% average annual rate over the 24-year history** of the scorecard. Over the **15 years ending Dec 2024, there were no categories in which a majority of active managers outperformed.**
- **Why this matters here:** it is direct evidence that *paying for skill* rarely beats *owning the index cheaply* over long horizons — which is exactly the case for the low-cost broad index core.

### Long-run asset returns (DMS / UBS Global Investment Returns)

- **UBS Global Investment Returns Yearbook 2025** (built on the DMS database, 35 markets since 1900): global equity investors have enjoyed an **annualized real return of ~3.5%** with an **equity risk premium vs bills of ~4.3%** over the long run — while stressing that equity returns are volatile and **very long histories are needed** to understand what long-run returns can and cannot predict.
- **Implication:** the long-run real return of equities is a *small, hard-won premium over cash* that only shows up over decades, and it is volatile. A bond sleeve trims that volatility at the cost of some expected return — the trade the allocation must justify.

### What is NOT claimed here

This note does **not** quote a specific backtest CAGR for a specific index+bond mix. Fabricating a precise "60/40 returned X%" number without a reproducible data source and execution convention would violate the same standard this note is defining. Any future run must produce its own numbers, net of fees, with the data cache committed.

---

## 5. Test protocol (pre-registration template)

Fill this in **before** running any backtest. A result without a pre-registered protocol is an anecdote.

```
STRATEGY_ID:            index_bond_<alloc>_<rebalance>
HYPOTHESIS:             A <X>/<Y> low-cost global equity + bond mix delivers positive
                        real return after fees with a smaller worst drawdown than 100% equity,
                        robustly across regions and regimes.
UNIVERSE:               <index funds per region>
TIMEFRAME:              <start> .. <end>, plus named stress windows
REBALANCE:              annual | threshold +-N%
COST MODEL:             ER + spread + rebalance + tax + platform fee = <total bps/yr>
BENCHMARKS:             100% global equity B&H ; static <X>/<Y> B&H
PASS CRITERIA:
  A. Cross-region: positive real return in >= majority of regions, net of fees
  B. Cross-period: survives named stress windows; worst DD < equity-only DD
  C. Net-of-fee: positive real return after all costs; breakeven cost >= 2x modelled
  D. vs benchmark: better risk-adjusted profile OR smaller worst-case than 100% equity
FAIL means:             report as a clean negative for that test; do not tune to pass
EXECUTION CONVENTION:   monthly vs annual rebalance, bar-close, lag applied
DATA CACHE:             <committed csv path>
SEED:                   <int> (in config, not command line)
```

---

## 6. Metrics that decide pass/fail

Report **all** of these for every region and regime — never a single headline number:

- **Compound annual growth rate (CAGR)** — nominal and **real** (after inflation).
- **Volatility** (annualised st-dev).
- **Sharpe** and **Sortino** (excess over cash / over downside deviation), **net of fees**.
- **Max drawdown** and **recovery time** — the metric bonds most improve.
- **Worst rolling 12-month** return — sequence-of-returns risk.
- **% of rolling 10-year windows with positive real return** — robustness, not average.
- **Breakeven fee** — the cost at which the edge vanishes.
- **Turnover** and **tax drag**.

**A strategy passes only if it is positive on a risk-adjusted basis *and* its worst-case is tolerable *and* it clears fees with margin.** Excelling on one lens while failing another is a fail, not a "qualified pass."

---

## 7. Pitfalls that manufacture false confidence

- **Single-market overfit** — a result driven by US large-cap 2010–2020 is not global evidence. Always test ex-US and EM separately.
- **Survivorship bias** — index returns are survivorship-free by construction, but *fund* comparisons must use the full opportunity set at period start (SPIVA's methodology does this; naive comparisons do not).
- **Recency bias** — the 1982–2021 bond bull market made bonds look like free drawdown insurance; **2022 broke that** (stocks and bonds fell together as rates rose). Test the rate-shock regime explicitly.
- **Ignoring currency** — an unhedged foreign-equity sleeve adds FX volatility; a Canadian investor sees USD/EUR moves as part of the return.
- **Ignoring tax** — in taxable accounts, tax drag can exceed the entire expense-ratio edge; model it.
- **Gross-return fantasy** — any result quoted gross of fees is meaningless at retail scale.
- **Home bias** — over-weighting the domestic market (e.g., TSX ≈ a few percent of global market cap) concentrates sector risk (financials/energy in Canada).
- **Confusing beta with alpha** — a passive index strategy's return is market beta. Calling it "beating the market" is a category error; the correct claim is "capturing the market's long-run real return at minimum cost."

---

## 8. Verification status (per this repo's proof standard)

| Claim | Status | Basis |
|-------|--------|-------|
| Most active funds underperform over long horizons | **VERIFIED (cited)** | SPIVA U.S. Year-End 2025 / 2024 scorecards |
| Long-run global equity real return ≈ 3.5%, ERP ≈ 4.3% | **VERIFIED (cited)** | UBS Global Investment Returns Yearbook 2025 (DMS) |
| Bonds cut drawdown but can co-move with equities in rate shocks | **VERIFIED (cited / 2022 evidence)** | 2022 rate-shock regime; broader fixed-income record |
| A specific index+bond mix returns precisely X% | **NOT CLAIMED** | Requires a reproducible, fee-net, data-cached backtest — see §5 |
| This allocation is "the best" | **NOT CLAIMED** | Depends on horizon, risk tolerance, currency, tax; it is a *robust default*, not an optimum |

**What this note is:** a testable protocol plus cited evidence for *why* a low-cost broad index+bond mix is the sensible baseline, and *how* to prove it isn't a fluke.

**What it is not:** a backtest result, a recommendation to buy, or a guarantee. Run §5 honestly, in your own currency and tax situation, before acting.

---

## 9. Sources

- S&P Dow Jones Indices, *SPIVA U.S. Scorecard Year-End 2025*, Report 1a — https://www.spglobal.com/spdji/en/documents/spiva/spiva-us-year-end-2025.pdf
- S&P Dow Jones Indices, *SPIVA U.S. Scorecard Year-End 2024* — https://www.spglobal.com/spdji/en/documents/spiva/spiva-us-year-end-2024.pdf
- UBS, *Global Investment Returns Yearbook 2025* (DMS database, 35 markets since 1900) — https://www.ubs.com/global/en/investment-bank/insights-and-data/2025/global-investment-returns-yearbook-2025.html
- Cambridge Centre for Endowment Asset Management (CEAM), *Global Investment Returns* project — https://www.jbs.cam.ac.uk/centres/ceam/research/investing-over-the-long-term/global-investment-returns/
- Aswath Damodaran, *Annual Returns on Stock, T.Bonds and T.Bills: 1928 – Current* (NYU Stern) — https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/histretSPX.html

---

*Written as a research note following this repository's proof standard: no performance claim without out-of-sample data, net-of-fee treatment, a named benchmark, and a stated execution convention. A clean negative result on any test above is a valid deliverable.*
