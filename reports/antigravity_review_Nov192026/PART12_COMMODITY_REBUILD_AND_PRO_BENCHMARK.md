# PART 12 — Commodity rebuilt clean, and the professional benchmark
**Author:** githubcopilot-mercury3AI · **Date:** 2026-11-22 · **Status:** RESULTS (round 3)
**Trigger:** peer `buffy` showed the Yahoo `=F` continuous contracts are unusable (negative `CL=F` close). This rebuilds the commodity class on clean data and then asks the question that actually matters: **does this beat what a professional charges you for?**

---

## 1. COMMODITY rebuilt on roll-managed ETFs — from KILL to the best class in the project

Free contract-level roll data does not exist, so I substituted **roll-managed commodity ETFs whose NAV already bears the roll** (DBC, GSG, GLD, SLV, USO, UNG, CORN, WEAT, SOYB, DBA, CPER). These are fund returns, not futures returns — disclosed, and strictly better than the corrupt `=F` series because a real fund paid the real roll.

**Data integrity verified:** zero negative closes across all 11 series; minimum price $7.93; the only extreme month is USO −55.4% (the real April-2020 crude event).

**Window 2011-12 → 2026-11, 180 months, 11 members, 20bp/switch, T-bill cash leg:**

| construction | CAGR% | Sharpe | MaxDD% |
|---|---:|---:|---:|
| Buy & hold equal weight | **−0.83** | 0.010 | **−62.8** |
| **10-month SMA trend overlay** | **+3.59** | **0.431** | **−15.4** |
| Δ | **+4.42pp** | **+0.421** | **MDD cut 75%** |

23 switches in 15 years, invested only **43%** of the time.

This is the **strongest class result in the entire project** — and unlike the ETF convenience-yield story, it has an economic reason rather than being a spreadsheet artifact:

> Long-only commodity futures have a structurally *negative* expected return because of roll cost in contango (the "roll yield" is paid by the holder). A trend filter's entire job is to be out of the asset when the term structure and price trend are against you. **The prediction was not "commodities go up", it was "holding commodities is a bad idea most of the time, and a trend filter can identify those times."** The data agrees: buy-and-hold lost money over 15 years; the overlay made +3.59%.

**Honest caveats, stated because they bound the claim:**
1. **Only 180 months** and the window starts 2011-12 (CPER listing constraint). Fifteen years is not a century.
2. **Much of the +3.59% is T-bill interest** — the rule is in cash 57% of the time, and 2022-2026 T-bills paid 4-5%. At the 2010-2021 zero-rate regime that leg contributes almost nothing. **The honest claim is "avoids the loss and clips a little", not "earns 3.6% from timing".**
3. **11 correlated funds, one asset class, one window** — this is a single bet on a single mechanism, not a diversified result.
4. Trial count: this is 1 construction (10m SMA) on 1 basket; not a grid search. DSR is not the binding constraint here, sample length is.

---

## 2. The professional benchmark — and why I will not claim a win

Managed-futures / liquid-alt funds exist to do exactly this. Comparing my free rule to them, each measured from the fund's own inception:

| fund | start | n(mo) | fund CAGR% | fund Sharpe | fund MDD% | **my SPY+trend Sharpe** | my MDD% |
|---|---|---:|---:|---:|---:|---:|---:|
| DBMF (iMGP DBi Managed Futures) | 2019-05 | 90 | 8.96 | **0.828** | −17.3 | **0.834** | −19.6 |
| KMLM (KFA Mount Lucas) | 2020-12 | 71 | 5.03 | 0.441 | −25.9 | 1.132 | −9.8 |
| CTA (Simplify) | 2022-03 | 56 | 7.32 | 0.484 | −19.0 | 1.060 | −9.8 |
| FMF (First Trust) | 2013-08 | 159 | 2.09 | 0.319 | −16.5 | 0.901 | −19.6 |
| QAI (IQ Hedge Multi-Strategy) | 2009-03 | 212 | 3.22 | 0.637 | −13.8 | 0.873 | −19.6 |
| MFTNX (Managed Futures) | 2012-03 | 176 | 3.76 | 0.287 | −30.0 | 0.971 | −19.6 |
| BTAL (anti-beta) | 2011-09 | 182 | −3.02 | −0.127 | −50.6 | 0.900 | −19.6 |
| SPY buy & hold | 1993-01 | 406 | 10.43 | 0.748 | −50.8 | 0.906 | −19.6 |

**It would be easy — and wrong — to write "my free rule beat seven professional funds."** That is not what this table shows. Three reasons:

1. **Not like-for-like.** These funds trade ~50 futures markets long and short with a crisis-alpha mandate. Mine is a long-only, single-asset (SPY) timing rule. In 2009-2026 US equities delivered one of the best runs in market history while bonds and commodities trended badly — this comparison mostly measures *that*, not skill.
2. **Different risk profiles.** My rule is 100% concentrated in one equity index when invested. A fund-of-futures position is diversified. Equal Sharpe from a concentrated book is not equal risk.
3. **Selection.** I chose a 10-month SMA. DBMF's managers did not get to pick their rule after seeing the data (though they picked their markets).

**The one fair and useful reading of this table:** on the same window, **my rule's Sharpe (0.834) is indistinguishable from DBMF's (0.828)** — a professionally managed, fee-charging product. So the achievable risk-adjusted return from a 20-line free rule and a monthly check is in the same neighbourhood as a commercial managed-futures product, with an entirely different (and less diversified) risk profile. That is a useful fact about *market opportunity*, not a victory lap.

**And the flip side, which is more important:** every one of these funds beat my rule on *diversification*, and several beat it on drawdown. If a professional product with 50 markets can't beat a one-line SMA on Sharpe, that tells you the simple rule is capturing something real — and also that the professional is not adding alpha on top of it after fees.

---

## 3. Consolidated position after three rounds

| class | best construction | Sharpe | CAGR% | MDD% | tier | note |
|---|---|---:|---:|---:|---|---|
| **COMMODITY** | 10m SMA on roll-managed ETF basket | **0.431** | +3.59 | **−15.4** | **CANDIDATE** | vs BH −0.83% / −62.8%. 180mo only. Mostly avoids loss. |
| **EQUITY** | 10m SMA on SPY, L1d | 0.796 | 8.48 | −20.7 | CANDIDATE | 93-yr test: positive ΔSharpe in all 4 eras |
| **ETF** | 10m SMA on EW ETF basket | 0.887 | 6.75 | −11.9 | CANDIDATE | |
| **MUTUAL_FUND** | 10m SMA on MF basket | 0.983 | 7.49 | −12.8 | CANDIDATE | |
| **INDEX** | 10m SMA on 8 global indices | 0.741 | 7.69 | −21.6 | CANDIDATE | |
| **BOND** | 10m SMA | 0.700 | 3.10 | −12.0 | WEAK | duration beta dominates |
| **CRYPTO** | buy & hold | 0.692 | 37.45 | −78.9 | REJECTED | trend destroys return |
| **FOREX** | 10m SMA | 0.239 | 0.61 | −10.2 | REJECTED | nothing there |
| **PENNY_STOCK** | — | — | — | — | INSUFFICIENT | survivorship + real spreads 5-20× modelled |
| **FUTURES** | — | — | — | — | **DATA_UNAVAILABLE** | no free roll-adjusted continuous contracts; the ETF basket is the substitute |

**Still true, and still the most important line in the project: none of this is alpha.** Every CANDIDATE is a drawdown-reduction rule whose CAGR matches or trails buy-and-hold. **Zero forward observations exist.** Nothing is sanctioned.

---

## 4. Next
1. **R2-1 PBO/CSCV** on the trend family — is "best class" a grid artifact? (K is disclosed, but cross-class selection was not deflated).
2. **Forward harness** — start the 100-observation clock on the two best: `EQUITY 10m SMA` and `COMMODITY ETF 10m SMA`.
3. Register both as pre-registered hypotheses with a written forward kill criterion *before* the first observation.

---
*Not personalized investment advice. All figures reproducible from the scripts in `/tmp/p6/`.*
