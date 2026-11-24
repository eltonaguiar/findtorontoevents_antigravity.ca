# Per-class mechanism / counterparty audit

**Date:** 2026-11-23T07:42Z · **Author:** Kilo · Paper only. Rule: *"if you cannot name the loser, you are the loser."*
Machine-readable: `reports/mechanism_audit.json`.

| Class | Best pick | Mechanism | Counterparty (the loser) | Verdict |
|---|---|---|---|---|
| **FOREX** | **AUDJPY long** (n34, DSR 0.815) | **G10 carry** — AUD yield > JPY funding cost | **JPY-funded carry traders squeezed in risk-off** | **REAL MECHANISM, NEAREST MISS** |
| STOCKS | CVX (n35, 0.318) | energy/commodity momentum + value tilt | index/ESG rebalancers underweight energy | BETA/TILT, UNPROVEN |
| ETF | SOXX (n37, 0.004) | semiconductor-cycle beta | late-cycle sellers | BETA, NOT ALPHA |
| CRYPTO | ETH (n155, 0.064) | BTC/ETH beta + reflexive momentum | leveraged late longs | WEAK/UNPROVEN |
| BOND | SGOV | T-bill carry (~4%) | (risk-free — no loser to exploit) | **THE BAR, NOT A PICK** |
| MUTUAL_FUND | VTSAX | equity risk premium (beta) | liquidity sellers | BETA — fees decide |
| COMMODITY | none | **no credible mechanism** | cannot name a loser | DEAD |
| OPTIONS / FUTURES / PREDICTION | none | no data / no measured edge | — | UNRANKABLE |

## The synthesis (the point of doing this)
**Only FX carry (AUDJPY) pairs a documented risk premium with the best DSR in the programme** — 0.815, about 14 trades
from the 0.95 gate. Every other class is either **beta** (ETF/FUND/BOND — you are buying the market, not an edge), an
**unproven factor tilt** (STOCKS), **unproven momentum** (CRYPTO), or has **no mechanism at all** (COMMODITY).

**Consequence:** the FX data feed is the **highest-value procurement**, not because FX "looks good", but because it is the
single place where a real, nameable mechanism and a near-passing statistic coincide. If any edge exists in this estate, the
cheapest test of it is to let AUDJPY accrue the ~14 trades it needs (requires restoring fx_prices past 2026-02-09).

## FOREX cost choice (7.533 vs 4.98 bp)
COST_OF_RECORD lists FOREX **7.533 bp** (upper bound, thin Sunday reopen) and FOREX_WEEKDAY **4.98 bp**. My picks are not
Sunday-reopen-specific, so **4.98 is the better central estimate**, but I **gate on 7.533 (conservative)** so a passing
verdict is trustworthy either way. At either cost AUDJPY's +51 bp gross survives; the blocker is DSR/n, not cost.

*Paper only. Not investment advice.*

---

## Wrapper addendum 2026-11-24 — the beta rows must name the Canadian wrapper
The ETF / MUTUAL_FUND / BOND rows above are **beta**, and for a Canadian investor the *vehicle* is decided separately:
**Canadian-listed, CAD-traded** low-MER index ETF (VFV/XUS or XEQT/VEQT) by default — no FX conversion cost and **not
US-situs** (no US estate-tax exposure); US-listed VOO only in an RRSP (treaty-exempt withholding) with cheap FX. See
`US_VS_CAD_WRAPPER_DECISION_2026-11-24.md`. This does not change any mechanism verdict — it changes *what you buy* to
capture the beta, not *whether* there is alpha (there is none above the detection floor).
