# Piotroski F-score backtest — INVALID due to look-ahead bias

**Date:** 2026-05-13
**Tool:** `tools/backtest_piotroski_fscore.py`
**Spec:** 9-factor Piotroski 2000; long F-score ≥ 7 basket buy-and-hold
**Backtest period:** 2020-01-01 → 2026-05-13

## Result

| Strategy | Total% | Sharpe | MDD% |
|---|---:|---:|---:|
| F-score ≥ 7 basket (9 stocks: AAPL/BMY/CSCO/DUK/MA/PG/UNH/V/WMT) | +124.7 | 0.79 | 29.2 |
| SPY benchmark | +148.6 | 0.81 | 33.7 |
| **Excess** | **-24.0%** | -0.02 | -4.5 |

Sharpe parity, MDD slightly better, but absolute return UNDERPERFORMS.

## Why this backtest is INVALID

**yfinance .info / .financials / .balance_sheet / .cashflow are point-in-time TODAY.**

We compute F-score from CURRENT (2026-05) financial statements, then apply as if those F-scores were known throughout 2020-2026. This is **look-ahead bias** — the strategy "knows" which stocks would have F=7 by today, then trades on that signal in the past.

True academic Piotroski 2000 backtests require **point-in-time** Compustat / CRSP — fundamentals as they were filed (with up to 90-day reporting lag) — which yfinance free tier does NOT provide.

## Implication

The -24% underperformance vs SPY is **not** a falsification of Piotroski's edge claim. It's a measurement artifact — we picked 9 stocks that survived 2020-2026 and HAPPEN to have strong fundamentals NOW. They underperformed mega-cap tech (NVDA/TSLA/AMZN) which dominate SPY's return.

Equally, the +124.7% basket return is meaningless because:
1. Survivorship: only stocks still listed in 2026 are in the universe
2. Look-ahead: only stocks with F=7 TODAY are picked
3. Hardcoded 50-ticker universe is post-survivor

## What can be salvaged

- The `compute_fscore()` function is correct Piotroski implementation
- Can be wired as a **forward-only** screening filter — score new stock at scan time, hold if F ≥ 7
- Cannot backtest historically without paid point-in-time fundamentals data

## Recommendation

DO NOT ship Piotroski as a backtest-validated strategy. Wire as forward-only screening filter if needed; quality bias is real but unmeasurable on free-tier data.

## Pattern: yfinance fundamental data limitations

Same lesson as BOND overlays failing because yfinance doesn't have FRED OAS spreads — free-tier data has structural blind spots for **point-in-time** strategies. Workable for price-based momentum/regime overlays; broken for fundamentals-based value/quality.

## Files

- `tools/backtest_piotroski_fscore.py` (kept; computes correct F-scores, just can't backtest historically)
- `audit_dashboard/data/piotroski_fscore_backtest.json` (output preserved as artifact, not edge claim)

NFA. No production change.
