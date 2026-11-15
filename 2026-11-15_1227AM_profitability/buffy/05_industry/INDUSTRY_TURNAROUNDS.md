# 05 — How Firms Went from "Can't Find an Edge" to "Trust Us With Real Money"

**Date:** 2026-11-15 · **Author:** Buffy

Five cases with real, checkable outcomes, then the transferable pattern. Sourced numbers are attributed;
where a figure is secondary reporting I say so.

---

## 1. AQR — the drawdown that nearly killed it, and what actually saved it

**What happened.** AQR peaked at roughly **$226bn AUM in 2018**, then hit the "quant winter." It lost
roughly **half its assets**; only about a third of that decline came from performance — the rest was
redemptions. Headcount fell ~40%. Its flagship then returned **+43.5% in 2022** and AQR recovered
performance well before it recovered assets; it never recaptured the 2018 peak.
*(AUM/flow figures: secondary reporting, collateral.com and Institutional Investor; treat as directional.)*

**What they actually did.**
1. **Kept publishing through the drawdown.** Asness wrote continuously — academic papers and a public
   blog — deliberately framed to be challenged rather than to reassure.
2. **Made the loss explicable.** Allocators who stayed could justify the position to their own
   investment committees. That is the mechanism: *a drawdown you can explain is survivable; one you
   can't is a redemption.*
3. **Did not abandon the process mid-drawdown.** They re-underwrote the factors and held the thesis.

**Transferable.** Publish the negative result as loudly as the positive one. This repo already does the
opposite: dashboards surface win rates, and the 48% forged rows are invisible until someone audits.
**A firm that hides its measurement failures cannot survive the drawdown that exposes them.**

---

## 2. Man Group / Man AHL — what a world-class CTA actually earns

**Measured, from the issuer's own fact sheet** (Man AHL Alpha (AUD) Class A, 30 Oct 2026):
**10-year annualised 4.86%**, since-inception 4.94%, volatility **9.02%**, **Sharpe 0.24**,
**max drawdown −18.91%** (13 months long, 8 months to recover), 22 total drawdowns.
*(Primary source: man.com fund documentation.)*

**Why this matters more than any contest.** Man AHL is one of the most sophisticated systematic managers
on earth, and its long-run Sharpe is **0.24**. Any pitch claiming Sharpe 2–4 from a home-grown system is
claiming to be 8–16× better than Man AHL, with worse data and no execution desk. That is the calibration
check every "proven strategy" in this repo should be measured against.

**Transferable.** A realistic institutional bar is Sharpe ~0.3–0.5 with maxDD under ~20%. The repo's own
go/no-go of "Sharpe ≥1.0" is *above* what a top-tier CTA delivers — ambitious but defensible for a small
agile book; "Sharpe 3.76" (the falsified VWAP claim) was never plausible.

---

## 3. Renaissance / Medallion — the ceiling, and why it's not a template

Medallion is widely reported at roughly **66% gross annualised**. *(Secondary source; Renaissance does
not publish this. Treat as folklore-grade.)*

**What is verifiable and relevant:** Medallion is **closed to outside capital**, capacity-capped, and
returns capital to investors rather than scaling. Its edge is thousands of small, short-horizon,
highly-diversified statistical signals with world-class execution and cost control.

**Transferable.** The lesson is not "find signals like Renaissance." It is: **the edge lives in execution
and cost control, and the strategy is capacity-limited by design.** A 361-strategy system with 15–30 bps
crypto costs and no fill model is the exact inverse of that.

---

## 4. The credibility infrastructure — how "trustworthy" is manufactured

Firms people trust with real money did not get there by publishing backtests. They built **verification
infrastructure**:

| Mechanism | What it does | Repo equivalent |
|---|---|---|
| **GIPS** (CFA Institute standards) | Audited, composite-level, time-weighted returns; prevents cherry-picking accounts | none |
| **Independent administrator / custodian** | NAV computed by a third party, not the manager | none — the resolver grades its own homework |
| **Audited financials** | Annual third-party audit | n/a |
| **Published methodology** | Enough detail to be replicated and criticised | partial (docs exist, numbers don't reconcile) |
| **SEC Marketing Rule (2020)** | 1/5/10-year net-of-fee returns required; 1-year can't stand alone; no cherry-picked hypotheticals | n/a |
| **Capacity statements** | "We will close at $X" — a trust signal, not a limitation | absent |

**The pattern:** every one of these removes the manager's ability to grade itself. This repo's core
failure is exactly that — `outcome_resolver.py` writes both the trade and the mark, and it writes
`exit_price = entry_price` 3,350 times. **No amount of strategy work fixes a self-graded ledger.**

---

## 5. Risk-management firms — the businesses built on measurement, not prediction

| Firm | Product | Lesson |
|---|---|---|
| **RiskMetrics** (J.P. Morgan, 1994) | VaR methodology, published free | Standardising a *measurement* created an industry; the measurement was the product |
| **MSCI Barra** | Factor risk models | Decomposing return into factors is what makes "alpha" falsifiable |
| **Moody's KMV** | Expected default frequency | Turned a judgment into a calibrated probability with a published error rate |
| **Numerix / QuantLib** | Pricing & risk analytics | Open reference implementations became the trust layer |

**Transferable.** All four sell **the ability to check a claim**, not the claim itself. The profitable
move for this project is the same: make the ledger independently checkable (exit-vs-date-close, published
cohort definitions, reproducible JSON), and the strategy question becomes answerable by anyone.

---

## 6. The pattern, distilled

Six things every trustworthy transition had in common:

1. **A single, audited source of truth** for performance — not five dashboards disagreeing.
2. **Independent verification** of the number the manager reports.
3. **Explicit cost and capacity accounting** — net-of-fee, capacity-capped.
4. **Published negatives** — the drawdown, the failure, the abandoned strategy.
5. **A falsifiable claim with a pre-committed threshold.**
6. **Survival through a drawdown** with the thesis intact and explicable.

This repo has (1) partially — and it is contradicted three ways on CRYPTO — and (2)–(6) not at all.
That is the actual distance between "struggling to find profitability" and "trustworthy."

---

## 7. What is NOT transferable, and would be a mistake to copy

- **"Hire PhDs and buy data"** — capital-intensive; the repo's problem is not model capacity, it is 48% forged marks.
- **"Run more strategies"** — with 361 already tested and ~18 expected false positives, adding strategies *widens* the multiple-testing problem.
- **"Win a contest"** — one audited year is not a track record; the organiser says so itself.
- **"Copy Medallion's signals"** — not published, capacity-capped, execution-dependent.

The cheapest credible step available here is the one every firm above did first: **make the numbers
auditable by someone other than the person producing them.**

---

### Sources

- World Cup Trading Championships — organiser standings, [worldcupchampionships.com](https://www.worldcupchampionships.com/), reproduced by [completetradersedge.com](https://completetradersedge.com/world-cup-trading-championships) (accessed 2026-11-15)
- Man AHL Alpha (AUD) Class A fact sheet, 30 Oct 2026 — man.com (primary)
- AQR drawdown/flows — collateral.com, Institutional Investor, Business Insider (secondary)
- GIPS — CFA Institute; SEC Marketing Rule (2020, compliance 2022) — public rule text
- RiskMetrics Technical Document (1994); MSCI Barra; Moody's KMV — public product documentation
