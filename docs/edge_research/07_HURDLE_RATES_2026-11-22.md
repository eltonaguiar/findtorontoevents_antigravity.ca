# 07 — The honest hurdle: risk-free rates and the required-return table

**Date:** 2026-11-22
**Programme items:** 12 (fetch actual risk-free yields), 13 (required-return table, GIC proxy honesty)
**Why this document exists:** every verdict in this programme so far was measured
against **zero**. That is the wrong bar. Cash currently pays ~4.3% with no
volatility, so a strategy that returns 3% while swinging 30% is *worse* than
doing nothing. This document replaces "zero" with a sourced hurdle that every
future verdict is judged against.

---

## 1. Actual risk-free yields, with sources

All values pulled 2026-11-22 from live endpoints. Nothing is estimated or
carried over from an earlier round.

| Instrument | Yield | As-of date | Exact source URL |
|---|---|---|---|
| US 3-month T-bill (secondary market) | **4.32%** | 2026-11-20 | `https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/2026/all?type=daily_treasury_yield_curve&field_tdr_date_value=2026&page&_format=csv` (column "3 Mo") |
| US 3-month T-bill (FRED DTB3, cross-check) | 4.16% | 2026-11-19 | `https://fred.stlouisfed.org/graph/fredgraph.csv?id=DTB3` |
| US 2-year Treasury | **4.63%** | 2026-11-20 | Treasury daily yield curve CSV (column "2 Yr") |
| US 5-year Treasury | **4.71%** | 2026-11-20 | Treasury daily yield curve CSV (column "5 Yr") |
| US 10-year Treasury | **4.92%** | 2026-11-20 | Treasury daily yield curve CSV (column "10 Yr") |
| US 2-year (FRED DGS2, cross-check) | 4.76% | 2026-11-19 | `https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS2` |
| US 5-year (FRED DGS5, cross-check) | 4.86% | 2026-11-19 | `https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS5` |
| US 10-year (FRED DGS10, cross-check) | 5.04% | 2026-11-19 | `https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS10` |
| Canada 2-year GoC benchmark | **3.30%** | 2026-11-19 | `https://www.bankofcanada.ca/valet/observations/BD.CDN.2YR.DQ.YLD/json` |
| Canada 3-year GoC benchmark | **3.40%** | 2026-11-19 | `https://www.bankofcanada.ca/valet/observations/BD.CDN.3YR.DQ.YLD/json` |
| Canada 5-year GoC benchmark | **3.53%** | 2026-11-19 | `https://www.bankofcanada.ca/valet/observations/BD.CDN.5YR.DQ.YLD/json` |
| Canada 10-year GoC benchmark | **3.81%** | 2026-11-19 | `https://www.bankofcanada.ca/valet/observations/BD.CDN.10YR.DQ.YLD/json` |
| Bank of Canada overnight target (policy rate) | 2.50% | 2026-11-19 | `https://www.bankofcanada.ca/valet/observations/V39079/json` |

**Which source worked, in the order the instructions specified:**
1. **Treasury CSV** — worked (HTTP 200, full 2026 daily curve). *Primary source for the USD hurdle.*
2. **FRED CSV** — worked this round (DTB3/DGS2/DGS5/DGS10 all returned). Note the
   earlier round's HTTP/2 error did **not** reproduce; FRED is reachable today and
   is used only as a cross-check. Treasury and FRED differ by ~0.1–0.17pp because
   of different as-of dates (11-20 vs 11-19) and slightly different curve
   construction, not a data error.
3. **Bank of Canada valet** — worked for the benchmark bond yields and the
   overnight target. *Primary source for the CAD hurdle.*

**CAD 1-year:** the 1-year GoC benchmark series was **not** found under the names
tried (`BD.CDN.1YR.DQ.YLD` returns empty). It is reported as **not obtained** rather
than guessed. 2y/3y/5y/10y are sourced.

## 2. GIC rates

**GIC rates were not fetched.** They are posted per-institution (bank by bank)
and there is no free machine-readable feed that can be fetched reliably here.
Per the instruction, the **GoC benchmark is used as a proxy and is clearly
labelled as a proxy** — it is *not* a GIC quote. A real 5-year GIC in Canada
typically prices off the 5y GoC plus a spread, so 3.53% is a floor-ish proxy,
not a marketable GIC rate. **No GIC number is invented anywhere in this document.**

## 3. The required-return table

This is the table every future verdict is judged against:

`required_return = rf + hurdle_sharpe × volatility`

Using **rf = 4.32%** (US 3-month T-bill, the cash alternative for a USD-denominated
strategy) and **rf = 2.50%** (BoC overnight target, the CAD cash alternative):

| Volatility | USD, hurdle Sharpe 0.5 | USD, hurdle Sharpe 1.0 | CAD, hurdle Sharpe 0.5 | CAD, hurdle Sharpe 1.0 |
|---|---|---|---|---|
| 10% | 9.32% | 14.32% | 7.50% | 12.50% |
| 20% | 14.32% | 24.32% | 12.50% | 22.50% |
| 30% | 19.32% | 34.32% | 17.50% | 32.50% |
| 50% | 29.32% | 54.32% | 27.50% | 52.50% |

Read it as: *a strategy with 30% volatility must earn at least 19.3% a year before
it clears a mediocre-Sharpe (0.5) bar over cash, and 34.3% to clear a good (1.0) bar.*

## 4. Bottom line

- **To beat simply holding T-bills, a strategy needs Sharpe > 0** (vs the risk-free
  rate). That is the *minimum*. Because T-bills carry essentially zero volatility,
  any strategy with volatility must earn `rf + 0 × vol = rf` just to tie, and
  strictly more to win on a risk-adjusted basis.
- **To beat SPY** a strategy needs to exceed SPY's risk-adjusted return. On the
  eval window SPY's Sharpe was **1.114** (the programme's standing figure). Re-measured
  on the 79-symbol panel window (2021-11-22 → 2026-11-19) SPY delivered
  **CAGR 10.42%, vol 17.39%, Sharpe-vs-rf 0.351** — a much tougher five years than
  the window behind the 1.114 figure. Both are reported: the programme bar is
  **Sharpe 1.114**, and a strategy must clear it to be said to "beat SPY".
- The practical consequence for this round: **a carry strategy earning 3.4% with 7.4%
  volatility has Sharpe −0.13** and is beaten by T-bills. Any result below the
  cash line in §3 is not an edge, whatever it looks like against zero.
