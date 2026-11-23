# Repo-wide total-return audit — how many return computations use raw Close?

**Date:** 2026-11-23 · **Author:** Kilo · Tool: `tools/audit_total_return.py` → `reports/total_return_audit.json`.

## Headline
- **333 files** index `["Close"]` **without** `auto_adjust`/`Adj Close`; **226 files** do adjust (OK).
- Of the 333: **67 are crypto-only (EXEMPT — no dividends, Close==Adj Close)**, **7 need review**.
- **231 are flagged equity/ETF/bond-context (EXPOSED)** — but the classifier is a **heuristic and over-counts**
  (`yfinance`/`fund` substrings match crypto files), so **231 is an UPPER BOUND**.
- The **credible blast radius is the ~49 files whose names clearly indicate equity/bond/dividend**
  (e.g. `alpha_engine/bond_*.py`, `cheap_stock_momentum.py`, `value_*`, `*_dividend*`). Each such file, if it computes
  holding-period returns from raw Close, **understates by the dividend yield — measured ~2–4%/yr** (SPY +1.94, VTV +2.78,
  DVY +3.78, VBR +2.23 in `CONTEST/ROUND_01_2026-11-23/VALUE_TOTALRETURN_CHECK.md`).

## Status
- The **value pipeline is fixed** (`value_screener_runner` + `equity_price_failover` now `auto_adjust=True`; regression
  test added).
- **Crypto/FX backtests are unaffected** (no dividends) — they should stay on raw Close or explicit prices.
- **Not blindly patched:** changing 49 production files is risky; each needs a per-file check that it (a) computes a
  *return* (not a current-price valuation ratio, where raw Close is correct) and (b) trades a dividend-paying instrument.

## Fix recipe (per affected file)
```python
# raw Close return (WRONG for dividends):
df = yf.Ticker(t).history(start=..., end=...)
ret = df["Close"].pct_change()
# adjusted total-return:
df = yf.Ticker(t).history(start=..., end=..., auto_adjust=True)  # or use Adj Close
ret = df["Close"].pct_change()   # now total-return
```
**Do NOT** apply this to valuation-ratio uses (P/E, P/B) — those correctly use the current raw price.

## Recommendation
Triage the 49 named equity/bond files first; add `auto_adjust=True` to any that feed return math; keep crypto unchanged.
This is a systemic hygiene item, not an emergency: every affected equity backtest is biased **downward** by the dividend
yield, which makes the estate look *worse* than it is — the opposite of the usual optimistic-bias failure.

*Paper only. Not investment advice.*
