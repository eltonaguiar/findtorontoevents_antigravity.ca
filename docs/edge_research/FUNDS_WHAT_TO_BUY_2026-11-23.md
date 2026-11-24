# What a human should actually buy — index funds / ETFs, measured

**Date:** 2026-11-23T09:42Z · **Author:** Kilo. **This is a BUYING analysis (beta), not an edge claim.**
Real data: adjusted closes 2021-11-15 → 2026-11-13 (1,254 daily returns). Tool: `tools/fund_deep_dive.py`.

> **Not investment advice. Past 5-yr returns; a bull-heavy window; taxes not modelled.**

## The measured table
| instrument | MER | net CAGR | vol | Sharpe | max DD |
|---|---:|---:|---:|---:|---:|
| **Fidelity 500 Index (FXAIX)** — index MF | 0.015% | **11.66%** | 17.2% | **0.728** | −24.5% |
| SPDR S&P 500 ETF (SPY) | 0.0945% | 11.49% | 17.3% | 0.714 | −24.5% |
| Fidelity ZERO Total Market (FZROX) | **0.00%** | 10.74% | 17.6% | 0.667 | −25.1% |
| Vanguard Total Market ETF (VTI) | 0.03% | 10.50% | 17.7% | 0.654 | −25.4% |
| Vanguard Total Stock MF (VTSAX) | 0.04% | 10.48% | 17.6% | 0.654 | −25.4% |
| Vanguard Total Bond ETF (BND) | 0.03% | −0.32% | 6.1% | −0.02 | −17.3% |
| iShares 0-3mo T-bill (SGOV) | 0.09% | 3.81% | 0.2% | (15.9*) | −0.03% |

\* SGOV's Sharpe is an artifact of near-zero variance — **not** comparable to equity Sharpe. It is the **cash hurdle (~3.8%/yr)**, not alpha.

## Simple portfolios (net of MER)
| portfolio | net CAGR | vol | Sharpe | max DD |
|---|---:|---:|---:|---:|
| 100% SPY (S&P 500) | 11.49% | 17.3% | 0.714 | −24.5% |
| 100% VTI (total market) | 10.50% | 17.7% | 0.654 | −25.4% |
| 80/20 SPY/BND | 9.28% | 14.2% | 0.697 | −22.4% |
| 60/40 SPY/BND | 6.98% | 11.2% | 0.660 | **−20.6%** |
| 100% SGOV (T-bill) | 3.81% | 0.2% | — | −0.03% |

## Does a mutual fund beat the ETF? Sometimes yes — on fees
- **FXAIX (index MF, 0.015%) vs SPY (ETF, 0.0945%)**: same index (MaxDD identical −24.5%; corr ~0.998). FXAIX net CAGR
  **+0.17 pp/yr** higher. Its **durable** edge is the **0.0795 pp/yr lower fee**; the remaining ~0.09 pp is
  tracking/dividend-timing noise that can reverse. **Fee is guaranteed; the rest is not.**
- **FZROX (0.00%) vs VTI (0.03%)**: FZROX +0.24 pp/yr net, Sharpe 0.667 vs 0.654 — same story, fee-driven.
- Fee drag per $100k over 5y: **FZROX $0, FXAIX ~$75, VTSAX ~$200, SPY ~$472.** That is the whole argument for low-MER.

## The mutual-fund catch you must weigh
Index **mutual funds can distribute capital gains** at year-end (taxable in a non-registered account); **ETFs mostly
don't** (in-kind creation/redemption). So an index MF's tiny fee edge can be **eaten by tax drag** in a *taxable*
account. In a **registered/tax-sheltered** account (TFSA/RRSP/Roth/IRA), the MF's fee edge is real and clean.
**Tax is NOT modelled here — flagged.**

## Bottom line — what to buy
1. **Core holding:** a **broad, low-cost index fund** — S&P 500 (**FXAIX** 0.015%, or **SPY/VOO** if you want an ETF) or
   total market (**FZROX 0.00%** / **VTI 0.03%**). Same beta; pick the lowest total cost you can access.
2. **MF vs ETF:** in a **tax-sheltered** account, a sub-0.05% index MF (FXAIX/FZROX) is as good as or better than the ETF
   and has no whole-share friction. In a **taxable** account, prefer the **ETF** (tax efficiency).
3. **Risk:** 100% equity returned ~11.5%/yr but had a **−24.5% drawdown**. If you cannot hold through that, **60/40**
   (7.0%/yr, −20.6% DD) or an 80/20 is the honest choice — you give up return for a shallower hole.
4. **Do not chase the programme's signals:** they are beta-dominant with no alpha above the detection floor
   (`docs/edge_research/ALPHA_GATE_POWER_CORRECTION_2026-11-23.md`). The index fund delivers the same beta, cheaper.

*Minimums/practicality:* FXAIX/FZROX $0 minimum at Fidelity; VTSAX $3,000 at Vanguard; ETFs trade intraday (fractional
shares now common). All four are rule-based index products, so the survivorship concern does not apply.

*Paper only. Not investment advice.*
