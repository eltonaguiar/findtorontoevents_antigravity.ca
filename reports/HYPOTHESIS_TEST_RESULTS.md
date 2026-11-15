# Hypothesis-Test Results — Robust Improvements Only (finpredict-v4)

**Date:** 2026-11-15
**Harness:** `tools/hypothesis_test_harness.py`
**Protocol:** for each asset class, form a testable hypothesis → test against its buy-and-hold baseline on **untouched out-of-sample data** (last 40% of history; first 60% never used for signal design) → keep only robust improvements.

**Costs:** 10bp round-trip on position changes.
**Baseline:** buy-and-hold of the class benchmark (SPY / QQQ / IWM / TLT / GLD / BTC / ETH).

---

## Results (on the untouched TEST slice)

| Hyp | Class | Ticker | Signal | test Sharpe | baseline Sharpe | test MaxDD | Verdict |
|-----|-------|--------|--------|-------------|-----------------|------------|---------|
| h1 | EQUITY | SPY | sma200 | 0.93 | 0.86 | -10.2% | **ROBUST** |
| h2 | EQUITY | QQQ | sma200 | 0.97 | 0.79 | -12.8% | **ROBUST** |
| h3 | EQUITY | SPY | sma50cross | 0.94 | 0.86 | -16.9% | **ROBUST** |
| h4 | ETF | IWM | sma200 | 0.31 | 0.49 | -16.6% | REJECTED |
| h5 | ETF | SPY | momentum | 0.96 | 0.86 | -11.2% | **ROBUST** |
| h6 | BOND | TLT | sma200 | -1.19 | -0.46 | -38.1% | REJECTED |
| h7 | COMMODITY | GLD | sma200 | 1.01 | 0.95 | -21.1% | **ROBUST** |
| h8 | CRYPTO | BTC | sma200 | 0.57 | 0.46 | -37.7% | **ROBUST** |
| h9 | CRYPTO | ETH | sma200 | 0.28 | 0.29 | -44.5% | REJECTED |
| h10 | FOREX | ^DXY | sma200 | — | — | — | INSUFFICIENT_DATA (delisted) |
| h11 | EQUITY | SPY | mom6 | 0.96 | 0.86 | -11.2% | **ROBUST** |

---

## Robust improvements kept (7)

1. **EQUITY sma200 (SPY)** — trend filter beats buy-and-hold on untouched data (Sharpe 0.93 vs 0.86).
2. **EQUITY sma200 (QQQ)** — strongest equity trend (Sharpe 0.97 vs 0.79).
3. **EQUITY sma50cross (SPY)** — faster trend, robust but deeper drawdown.
4. **EQUITY mom6 (SPY)** — 6-month momentum, robust.
5. **ETF momentum (SPY)** — momentum on the index (Sharpe 0.96 vs 0.86).
6. **COMMODITY sma200 (GLD)** — gold trend filter (Sharpe 1.01 vs 0.95).
7. **CRYPTO sma200 (BTC)** — BTC trend filter (Sharpe 0.57 vs 0.46); high drawdown but improved.

---

## Rejected / not kept
- **ETF IWM sma200 (h4)** — no edge vs buy-and-hold on untouched data.
- **BOND TLT sma200 (h6)** — trend filter made it worse (negative Sharpe both ways); bonds are carry, not trend.
- **CRYPTO ETH sma200 (h9)** — no edge vs B&H.
- **FOREX (h10)** — no usable benchmark series (delisted); blocked.

---

## Meaning
The **trend/momentum family is robust across EQUITY (SPY/QQQ), ETF (SPY momentum), gold, and BTC** — consistent with the Faber 200-day MA thesis and the earlier backtest. Bonds and small-caps (IWM) do NOT respond to trend filters on untouched data; those hypotheses are correctly rejected.

These robust signals are what the live emitter should use (VTI/QQQ/SPY trend + GLD trend + BTC trend), replacing any signal that did not beat baseline OOS.
