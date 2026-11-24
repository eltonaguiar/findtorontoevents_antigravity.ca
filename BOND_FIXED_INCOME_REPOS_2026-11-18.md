# Bond/Fixed-Income GitHub Repo Scout — 2026-11-18

Scope: sovereign bond futures / cash bonds, yield curve, carry/roll-down, term premium, TIPS vs nominals, credit, convertibles, bond ETFs, rates vol. Verified via GitHub REST API metadata only (no source clone/read). **No fabricated repos** — every entry below was fetched from `api.github.com`.

## Top 5 ranking

| # | Repo | ★ | Last commit | License | Verdict |
|---|------|---|-------------|---------|---------|
| 1 | [QuantConnect/Lean](https://github.com/QuantConnect/Lean) | 22,596 | 2026-11-18 | Apache-2.0 | VIABLE |
| 2 | [mortada/fredapi](https://github.com/mortada/fredapi) | 1,675 | 2026-01-28 | Apache-2.0 | VIABLE (data source) |
| 3 | [enthought/pyql](https://github.com/enthought/pyql) | 1,355 | 2026-07-17 | NOASSERTION | PARTIAL |
| 4 | [epogrebnyak/data-ust](https://github.com/epogrebnyak/data-ust) | 30 | 2022-03-12 | none | PARTIAL (stale data, no license) |
| 5 | [lballabio/QuantLib](https://github.com/lballabio/QuantLib) | 7,778 | 2026-11-18 | NOASSERTION | PARTIAL (pricing lib, not strategy) |

## Full repo list

- `mortada/fredapi` — Python API for FRED/ALFRED. VIABLE data source for DGS/CMT/term-premium. Biggest reason NOT to work: it is a data client, no strategy, no backtest; we still must write the signal logic ourselves.
- `QuantConnect/Lean` — full algorithmic trading engine with US Treasury yield curve data marketplace examples (`YieldCurveAlgorithm.py`, `TreasuryFuturesStrategy.py`, `BondPortfolioDurationTargeting.py`). VIABLE but requires the LEAN engine + cloud data subscriptions; heavy integration cost.
- `enthought/pyql` — Cython QuantLib wrappers. PARTIAL: gives pricing/curves but steep C++ build and no strategy layer.
- `lballabio/QuantLib` — QuantLib C++ library. PARTIAL: pricing/curves only; NOASSERTION license; Python binding maintenance is a burden.
- `ahgperrin/PyCurve` — yield-curve interpolation/parameterization. PARTIAL; last commit 2021-08-28 — effectively stale.
- `epogrebnyak/data-ust` — clean US Treasuries yield curve data. PARTIAL; last commit 2022-03-12; no license declared.
- `open-source-modelling/Nelson_Siegel_Svensson_python` — NSS curve fitting. PARTIAL math lib.
- `simicd/smith-wilson-py` — Smith-Wilson fitting. PARTIAL; last commit 2024-09-03.
- `werleycordeiro/Dynamic_Nelson_Siegel_Svensson_Kalman_Filter` — NSS fitting/forecasting. PARTIAL; last commit 2021-02-25.
- `skasim/yield-curve` — Jupyter notebooks on yield-curve forecasting. DECORATIVE; no license.
- `mrbcuda/ustyc` — US Treasury yield curve retrieval. PARTIAL data; last commit 2020-05-27; NOASSERTION license.
- `JMA1911/macro-driven-fixed-income-trading` — macro-driven Treasury ETF strategies with backtesting. PARTIAL; 2 stars; no license; single-author unverified.
- `SAY-5/quantbacktest` — vectorized fixed-income factor backtests over 10y bond yields. DECORATIVE; 0 stars; "cuts research time 60%" is marketing copy, no OOS evidence.
- `shiki-jiang/fixed-income-portfolio-management` — portfolio construction + backtesting. DECORATIVE; 0 stars; no license.
- `hocine-chabane/quant-research-backtester` — long/short yield-curve strategies in Numba. DECORATIVE; 0 stars; no license.
- `chen-bowen/Flattener_Trading_Strategy` — zero-coupon bond flattener. DECORATIVE; 5 stars; last commit 2018-01-06; no license.
- `RoyRongStevens/US-Treasury-Bond-Futures` — Treasury bond futures strategy. DECORATIVE; 2 stars; last commit 2019-03-01; no license.
- `lzinga/us-gov-open-data-mcp` — MCP server for 40+ US gov data APIs incl. Treasury & FRED. PARTIAL plumbing; MIT; last commit 2026-11-02.

## What we already have vs what this adds

We already have (internal): `BONDS_EDGE_VERDICT_2026-11-17.md` with 3 qualified EDGE configs (IEF `bond_yield_curve_slope` LONG n=108 PF=1.35; TLT `cta_cross_asset_tsmom` SHORT n=57 PF=128.53; IEF `cta_cross_asset_tsmom` SHORT n=34 PF=183.66), plus the CROSS_DB_DATA_QUALITY_MATRIX showing the `bonds`/`equities`/`etfs`/`mutual_funds`/`crypto` DBs are UNREACHABLE (MySQL 1045) and only `ejaguiar1_stocks` proxy is usable.

What external repos add: **data plumbing only** — `fredapi` for FRED DGS/CMT/term-premium, `data-ust` for clean historical curve, `QuantConnect/Lean` as a reference engine. Nothing here ships a falsifiable, OOS-tested edge matching our qualified configs. No repo provides TIPS/nominal breakeven, CDS/IG/HY, convertibles, or rates-vol strategy logic with testable code.

## Dead / stale / hallucination-prone flags

- `chen-bowen/Flattener_Trading_Strategy` — last commit 2018-01-06 (dead).
- `RoyRongStevens/US-Treasury-Bond-Futures` — last commit 2019-03-01 (dead).
- `mrbcuda/ustyc` — last commit 2020-05-27 (stale).
- `werleycordeiro/...` — last commit 2021-02-25 (stale).
- `ahgperrin/PyCurve` — last commit 2021-08-28 (stale).
- `epogrebnyak/data-ust` — last commit 2022-03-12 (stale data; verify freshness before use).
- `skasim/yield-curve` — last commit 2022-09-02 (stale).
- `simicd/smith-wilson-py` — last commit 2024-09-03 (aging).
- `SAY-5/quantbacktest`, `shiki-jiang/...`, `hocine-chabane/...` — 0 stars, no license, marketing-style descriptions; treat as hallucination-prone until code is read.
- `JMA1911/macro-driven-fixed-income-trading` — 2 stars, no license; single-author, unverified claims of "robust risk management."

## Proven-edge verdict

**NONE as of 2026-11-18.** No repo ships a falsifiable, out-of-sample-tested edge matching our qualified configs. All are data libs, curve-fitting math, or toy backtesters with survivorship bias.

## Next concrete experiment

Clone `epogrebnyak/data-ust` + install `mortada/fredapi`; build a minimal yield-curve-slope backtest on IEF (n≥30, PF≥1.25) through the `ejaguiar1_stocks` proxy; walk-forward test 2023–2026 OOS only; report PF and MaxDD. If PF<1.25 or MaxDD>15%, abandon the bond-yield-curve-slope hypothesis and pivot to TLT/IEF cross-asset TSMOM replication using Lean's `TreasuryFuturesStrategy.py` as the reference skeleton.
