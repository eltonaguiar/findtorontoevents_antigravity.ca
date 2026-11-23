# Cross-class backtest under identical entry criteria — and why the flattering numbers are not an edge yet

**Date:** 2026-11-23
**Tool:** `tools/cross_class_momentum_backtest.py`
**Artifact:** `reports/cross_class_backtest.json` + `reports/cross_class_returns/*.json`

## The identical rule

Comparing a value book to a carry trade to a trend rule is meaningless unless the entry
rule, rebalance clock and cost treatment match. Every class runs the **same** rule:

> **Time-series momentum** — hold when the trailing L-day return is > 0, else cash.
> Rebalance every H trading days. Grid: L ∈ {21,63,126,189,252} × H ∈ {5,10,21} = **15 configs**.

Only the instrument and the measured cost differ, because those are class properties.
IS = first 70%, OOS = last 30%. Top pick = best **in-sample** Sharpe, OOS reported untouched.

## Results

| Class | Instrument | Top pick | IS SR | OOS SR | OOS net | OOS DD | turn/yr | >hurdle |
|---|---|---|---|---|---|---|---|---|
| EQUITY | AAPL | L252/H21 | 0.41 | **1.40** | **+34.17%** | −13.80% | 0.6 | True |
| ETF | SPY | L189/H21 | 0.98 | **1.21** | **+16.00%** | −8.88% | 0.2 | True |
| CRYPTO | BTC-USD | L252/H10 | 1.08 | −1.05 | −20.57% | −48.68% | 0.8 | False |
| FOREX | EURUSD_X | L21/H10 | 0.52 | −0.87 | −3.41% | −8.46% | 7.6 | False |
| COMMODITY | GC_F | L252/H5 | 1.29 | 0.63 | +13.45% | −25.13% | 1.2 | True |
| BOND | TLT | L21/H10 | 0.14 | −1.43 | −8.89% | −15.86% | 7.0 | False |

## These are NOT edges, and it would be negligent to present them as such

Four things make this result untrustworthy, and all four are recorded before the DSR/PBO
pass rather than after it:

1. **One instrument per class.** AAPL ≠ EQUITY, SPY ≠ ETF, BTC-USD ≠ CRYPTO. With n=1
   there is no diversification of idiosyncratic luck, so a single name's bull run becomes
   the "class result". A proper test needs a cross-section and equal weighting.
2. **15 configs per class, selected on IS.** Picking the best of 15 by in-sample Sharpe is
   exactly the setup that manufactures OOS winners. That is what PBO measures.
3. **OOS is only ~30% of 5 years ≈ 1.5 years.** One regime. Momentum on a trending asset
   inside a bull market is the single most common false positive in this literature.
4. **Two costs are proxies.** COMMODITY and BOND execution are UNMEASURED (4.97 bp borrowed
   from EQUITY). Their rows are flagged `PROXY` and cannot support a promotion.

Note also that **OOS Sharpe exceeds IS Sharpe** for EQUITY, ETF and COMMODITY. That is not
a good sign — it usually means the OOS window was unusually favourable to trend, not that
the rule improved.

## What this block is actually for

It produces the six return matrices (`reports/cross_class_returns/*.json`, 90 config-series
total) that the DSR/PBO pass needs. The honest verdict on "is there an edge" is **not**
decided here.

Zero capital sanctioned. Not investment advice.
