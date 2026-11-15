# Algorithm Specification — ETF / index exposure (Faber 10-month SMA)

**Agent:** buffy (Codebuff) · **Date:** 2026-11-15
**Status:** `MEASURED — SURVIVES AS RISK MANAGEMENT, NOT AS ALPHA` · **Primary pick**

---

## 1. Instrument and class

| Field | Value |
|---|---|
| Instrument | `SPY` (SPDR S&P 500 ETF), adjusted close (dividends + splits) |
| Class | ETF (this rule is an *index-timing overlay*; it holds one ETF or T-bills) |
| Data source | Yahoo chart API, `interval=1mo`, `events=div,splits`, `adjclose` |
| Sample | 2004-12-01 → 2026-11-13 · 265 monthly periods · 22.08 years |
| Cash leg | 13-week T-bill (`^IRX`), monthly mean of daily annualised rate ÷ 12 |
| Cost | **6 bps per side** on every weight change |
| Benchmark | Matched exposure: `exposure × SPY + (1 − exposure) × T-bill` |

Gold (`GLD`) and long Treasuries (`TLT`) are the same rule's alternates in the momentum specs; see
`SPEC_COMMODITY.md` and `SPEC_BOND.md`.

---

## 2. Rule — exact, as implemented

```text
At each month-end close i (data up to and including i only):

    SMA10(i) = mean( close[i-9 .. i] )        # 10 monthly closes, current month included

    if i < 10:              weight = 0.0      # warm-up: no signal, hold T-bills
    elif close[i] > SMA10:  weight = 1.0      # fully long SPY next month
    else:                   weight = 0.0      # fully in T-bills next month

    position earns the return of month i → i+1
```

- **Long/flat only.** No shorting, no leverage, no partial sizing, no stop-loss other than the signal.
- **Signal is evaluated on month-end data and acted on for the following month** — no same-bar execution.
- Textbook parameters, **not tuned**: the 10-month lookback comes from Faber (2007), *A Quantitative
  Approach to Tactical Asset Allocation*. No other lookback was searched, so there is no lookback
  selection to correct for.

---

## 3. Parameters

| Parameter | Value | Why this value |
|---|---|---|
| Lookback | 10 months | Literature default; pre-registered before the run |
| Warm-up | 10 periods | A 10-month mean is undefined before month 11 |
| Rebalance | Monthly, month-end | Matches the signal frequency; daily would add cost without information |
| Weight | 0 or 1 | Binary; sizing logic would add a second free parameter |
| Cost/side | 6 bps | Commission + spread + slippage for a liquid SPY-size position |
| Cash yield | T-bill (`^IRX`) | Cash is not assumed to yield zero |

---

## 4. Measured result

| Metric | Full sample | In-sample 2003-01→2015-12 | Out-of-sample 2016-01→2026-11 |
|---|---:|---:|---:|
| CAGR | **8.33%** | 8.30% | 8.36% |
| Excess vs matched benchmark | **−0.09%/yr** | −0.06% | −0.12% |
| Sharpe | **0.66** | — | — |
| Max drawdown | **−21.8%** | — | — |
| Deflated Sharpe (N=5 monthly trials) | **0.99** | — | — |
| Round trips | 33 | — | — |
| Average exposure | 0.78 | — | — |
| Information ratio | −1.304 | — | — |
| Excess t-stat | −6.13 | — | — |
| Benchmark CAGR (matched exposure) | 8.43% | — | — |

At **2× costs**: CAGR 8.23% (−0.10pp), Sharpe 0.65 (−0.01), max drawdown −22.1%. The rule is
cost-insensitive; it is not paying the market for its signal.

### What the −0.09% actually is

33 switches × 6 bps = **1.98% total cost**; 1.98% ÷ 22.08 years = **0.0897%/yr**. That is the entire
excess deficit to four significant figures. The overlay does not lose to buy-and-hold for any reason
except the cost of trading the signal. Stated the other way: **it converts a −50.8% drawdown into a
−21.8% drawdown for 0.09%/yr.**

This is why the t-stat is −6.13 despite a trivial mean: the matched-exposure benchmark built from the
*realised* exposure path is a cost-free clone of the same position, so the tracking error is only the
cost stream. A large |t| here means "reliably one basis point cheaper to do nothing", not "noisy".
See `BACKTEST_AND_RESEARCH.md` §4 for the general caveat this implies.

---

## 5. Why it is worth anything

| Criterion | Buy & hold | FABER10 | Difference |
|---|---:|---:|---:|
| CAGR | 10.76% | 8.33% | −2.43pp |
| Max drawdown | −50.8% | −21.8% | **+29.0pp** |
| Sharpe | 0.65 | 0.66 | +0.01 |
| Return per unit of drawdown | 0.212 | 0.382 | **+0.170** |

The CAGR gap is mostly cash drag (average exposure 0.78 — the rule is out of the market 22% of the
time by construction). The risk-adjusted comparison is the meaningful one, and it is a wash on
Sharpe with a materially better drawdown.

---

## 6. What would promote this to a capital decision

- [ ] Forward ledger: **200 months** of live monthly signal (16.7 years) for a 0.20 Sharpe claim;
      39 months is the minimum for a 0.40 Sharpe claim at 95%.
- [ ] Realised drawdown in the forward window ≤ 60% of buy-and-hold's — the actual claim.
- [ ] Cost per switch measured, not assumed, on the broker being used.
- [ ] Tax drag quantified (monthly switches are short-term in a taxable account; this rule is only
      sensible in a tax-sheltered account).

Until the first box is ticked, this is a **risk-management overlay**, not a pick with an expected
return premium.

---

## 7. Known failure modes

1. **Whipsaw regimes** (2009, 2011, 2015–16, 2020): the rule re-enters after the bounce, paying two
   costs and missing the first leg. It does not fail catastrophically; it bleeds.
2. **Slow bear markets with strong rallies above the 10-month SMA** (2022): the signal can re-enter
   into a resumed decline.
3. **Single-asset concentration.** This is one ETF. Nothing here is diversified across the equity
   class.
4. **The sample contains one of each regime.** One 22-year window is one draw; it is not 22 tests.
