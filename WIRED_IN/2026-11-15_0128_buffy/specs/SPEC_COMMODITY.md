# Algorithm Specification — COMMODITY

**Agent:** buffy (Codebuff) · **Date:** 2026-11-15
**Status:** `MEASURED — REJECTED`

---

## 1. Scope, stated honestly

The repo's `COMMODITY` class has 54 ledger rows and its PF is not computable as a strategy result
(insufficient verified marks). What I measured is the only commodity exposure with a clean series and a
textbook rule: **GLD inside a 3-asset dual-momentum selection**, and a separate check of GLD as a
standalone hold is *not* present (gold has no earnings, no cash flow, and no natural expected return, so
"hold gold" is a currency/real-rate bet rather than a strategy).

| Field | Value |
|---|---|
| Instrument | `GLD` (SPDR Gold Shares), monthly adjusted close |
| Sample | 2004-12-01 → 2026-11-13 · 265 monthly periods (GLD starts 2004-11) |
| Cost | 6 bps/side |
| Benchmark | Matched exposure in SPY + T-bill (same rule as every row) |
| Rule | 12-month momentum, best of {SPY, TLT, GLD} if positive, else cash |

This is the `DUALMOM_3` rule; GLD is a candidate, not a mandate.

---

## 2. Rule — exact, as implemented

```text
At each month-end close i (i >= 12, otherwise flat):

    m_SPY = close_SPY[i] / close_SPY[i-12] - 1
    m_TLT = close_TLT[i] / close_TLT[i-12] - 1
    m_GLD = close_GLD[i] / close_GLD[i-12] - 1

    best = argmax(m_SPY, m_TLT, m_GLD)

    if m_best <= 0:  weight = 0        # nothing has positive momentum -> T-bills
    else:            weight[best] = 1.0

    hold for month i -> i+1
```

- Single-asset concentration by construction: at most one of the three is held.
- No volatility targeting, no rebalancing within the month, no shorting.

---

## 3. Measured result

`DUALMOM_3` overall (GLD included as a candidate):

| Metric | Full | In-sample | Out-of-sample |
|---|---:|---:|---:|
| CAGR | 8.13% | 8.97% | 7.30% |
| Excess vs matched benchmark | **−1.88%/yr** | **+2.55%** | **−6.34%** |
| Sharpe | 0.45 | — | — |
| Max drawdown | −30.0% | — | — |
| DSR (N=5 monthly) | 0.94 | — | — |
| Round trips | 55 | — | — |
| Average exposure | 0.92 | — | — |

**The in-sample/out-of-sample sign flip is the finding.** A rule that shows +2.55%/yr in the first
half and −6.34%/yr in the second half has not been validated by its full-sample number; the full-sample
figure (−1.88%) is the average of a success and a failure, which is what regime overfit looks like when
you report only the average.

At 2× costs: CAGR 7.85% (−0.29pp), Sharpe 0.44. Cost is not the issue; the signal is.

---

## 4. Why gold in a momentum menu fails here

1. **Gold's return is real-rate driven**, and 12-month price momentum is a poor proxy for real-rate
   direction — it enters after the move, which is exactly when real rates are about to revert.
2. **The menu is too small.** Three candidates, one held, 55 switches: the rule is making a
   concentrated single-asset bet 55 times and paying for it.
3. **GLD's 2004 start shortens the joint sample** to 22 years, which includes only two complete gold
   cycles.

---

## 5. Elimination

Eliminated in the backtest. Re-admission would require the commodity test to be **cross-sectional**
(rank a basket of 10–15 commodity ETFs or futures by momentum) rather than a 3-asset menu, with roll
yield modelled — otherwise the result is a single-instrument timing bet, not a commodity strategy.

See `ELIMINATION_LOG.md` §2.
