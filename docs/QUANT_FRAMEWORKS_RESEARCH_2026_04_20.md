# Quant Frameworks + Datasets Research — 2026-04-20

Scope: open-source repos relevant to Phase 4 (risk-adjusted metrics) and Phase 6 (MFE/MAE) of the v1.1 enforcement + scoring plan. Only actively-maintained, permissively-licensed, non-obvious additions are included.

## 1. General quant / backtesting frameworks

| Repo | URL | Stars (approx) | Last updated | Use for | License |
|---|---|---|---|---|---|
| NautilusTrader | https://github.com/nautechsystems/nautilus_trader | ~6–7k | Apr 2026 (v1.225.0) | Event-driven backtester w/ order-book replay + latency modeling; reference for exchange-accurate fills in crypto phase | LGPL-3.0 (copy-left, link-only OK) |
| VectorBT (OSS) | https://github.com/polakowo/vectorbt | ~5k | 2026 | Numba-accelerated grid/parameter sweeps; ideal for Phase 4 metric sweeps across thousands of strategy variants | Apache-2.0 |
| Zipline-Reloaded | https://github.com/stefan-jansen/zipline-reloaded | ~1.5k | 2026 | Daily-bar equity backtests, pipeline API for factor research | Apache-2.0 |
| Backtesting.py | https://github.com/kernc/backtesting.py | ~6k | 2026 | Quick single-asset sanity checks; easy to embed in CI | AGPL-3.0 (avoid bundling) |
| QuantConnect Lean | https://github.com/QuantConnect/Lean | ~11k | 2026 | Reference architecture only (C#-first) | Apache-2.0 |

Notes: `backtrader` is effectively stale (maintenance-mode). Avoid `mlfinlab` main — re-licensed to proprietary/all-rights-reserved (was BSD-3 in 2019).

## 2. Strategy creation / combinatorial generation

| Repo | URL | Stars | Last updated | Use for | License |
|---|---|---|---|---|---|
| Microsoft Qlib | https://github.com/microsoft/qlib | ~15k | 2026 | Full ML pipeline: alpha mining, RL, portfolio opt, now with RD-Agent automation | MIT |
| AI4Finance FinRL-Trading (FinRL-X) | https://github.com/AI4Finance-Foundation/FinRL-Trading | ~10k (family) | 2026 | RL policies as challenger strategies; paper-trading validation hooks | MIT |
| Alphalens-Reloaded | https://github.com/stefan-jansen/alphalens-reloaded | ~500 | 2026 | IC / factor decile tearsheets for Phase 4 attribution | Apache-2.0 |
| Pyfolio-Reloaded | https://github.com/stefan-jansen/pyfolio-reloaded | ~500 | 2026 | Standardized tearsheets, rolling-window risk, returns attribution | Apache-2.0 |
| Spectre | https://github.com/Heerozh/spectre | ~700 | 2025/26 | GPU-accelerated factor library + backtester | Apache-2.0 |

## 3. Per-asset-class datasets + tooling

| Repo | URL | Asset | Use for | License |
|---|---|---|---|---|
| CCXT | https://github.com/ccxt/ccxt | Crypto | 100+ exchanges, funding rates, OHLCV; our crypto leg already leans here | MIT |
| TickVault | https://github.com/keyhankamyar/TickVault | Forex/Crypto/Metals | Resume-capable Dukascopy tick downloader for FX + commodity backfill | MIT |
| duka / dukascopy | https://github.com/giuse88/duka | Forex/CFD/Commodity | CLI tick-data puller; complements TwelveData | MIT |
| fredapi | https://github.com/mortada/fredapi | Bond/Macro | Yield-curve series (DGS2, DGS10, T10Y2Y), CPI, fed-funds | BSD-2 |
| pyfredapi | https://github.com/gw-moore/pyfredapi | Bond/Macro | Full endpoint coverage + ALFRED vintage data (point-in-time correct) | MIT |
| datasets/bond-yields-us-10y | https://github.com/datasets/bond-yields-us-10y | Bond | Pre-packaged monthly 10Y series, auto-updated | PDDL |
| pandas-datareader (Stooq) | https://github.com/pydata/pandas-datareader | Equity/ETF/Intl | Non-US equity + index history free; fallback for yfinance gaps | BSD-3 |
| OpenBB Platform | https://github.com/OpenBB-finance/OpenBB | Multi | Unified adapter over 350+ providers; useful wrapper for gap-filling | AGPL-3.0 (isolate via subprocess/HTTP) |

## 4. Hedge-fund / institutional-style repos

| Repo | URL | Use for | License |
|---|---|---|---|
| awesome-quant (curated) | https://github.com/wilsonfreitas/awesome-quant | Discovery index, keep as bookmark | CC |
| awesome-ai-in-finance | https://github.com/georgezouq/awesome-ai-in-finance | LLM + DL finance curation | CC |
| JPMorgan pyRMT / fincal ecosystem | (various JPM open-source) | Random-matrix-theory covariance cleaning | varies |
| Two Sigma flint / thunder-gbm | https://github.com/twosigma | Time-series joins, tree-models — mostly Apache-2.0 | Apache-2.0 |

Quantopian legacy (alphalens, pyfolio, empyrical, zipline) lives on through the `stefan-jansen` "Reloaded" forks — that's the maintained path.

## 5. Validation / governance frameworks

| Repo | URL | Use for | License |
|---|---|---|---|
| pypbo | https://github.com/esvhd/pypbo | Probability of Backtest Overfitting (Bailey/Lopez de Prado) + Deflated Sharpe | MIT |
| Probabilistic-Sharpe-Ratio | https://github.com/rubenbriones/Probabilistic-Sharpe-Ratio | PSR + Deflated SR reference implementation w/ notebooks | MIT |
| timeseriescv | https://github.com/sam31415/timeseriescv | Purged / combinatorial purged K-fold in sklearn style | MIT |
| skfolio | https://github.com/skfolio/skfolio | `WalkForward`, `CombinatorialPurgedCV`, stress tests, sklearn-compatible | BSD-3 |
| arch (bootstrap module) | https://github.com/bashtage/arch | Stationary / circular block bootstrap, MCS test | NCSA (permissive) |

## Recommendations — highest leverage for Phase 4 / Phase 6

1. **pypbo + Probabilistic-Sharpe-Ratio** — Phase 4 needs a Deflated Sharpe implementation; drop these into `audit_dashboard/metrics/deflated_sharpe.py` as a reference rather than a dep. ~200 LOC, MIT, zero runtime cost. Directly addresses the multiple-testing / selection-bias problem our strategy zoo already has.
2. **skfolio.WalkForward + CombinatorialPurgedCV** — Phase 4's validation harness. BSD-3, sklearn-compatible, drops in next to the existing `forward-test` loop. We already export closed CSVs; `fit/score` on purged folds is 1 afternoon of glue code.
3. **arch.bootstrap** — block-bootstrap for MFE/MAE confidence intervals in Phase 6. Circular block bootstrap is the right answer for path-dependent statistics; `arch` is the canonical Python implementation and is maintained by Kevin Sheppard.
4. **vectorbt (OSS)** — Phase 4 metric sweeps across thousands of (strategy, param) pairs. Keep as an offline research tool, not in the live dashboard path, so license/speed concerns don't matter.
5. **NautilusTrader (reference, not dep)** — study their `OrderMatchingEngine` + latency model to inform our crypto fill-realism audit. LGPL means we read it, not vendor it.

## Data-source tier list (complement to yfinance / Binance / CoinGecko / ExchangeRate-API / TwelveData / AlphaVantage / FMP)

- **Tier 1 add (high-value, low-friction)**:
  - `fredapi` / `pyfredapi` — closes our **BOND + macro** gap entirely (free, 800k+ series, ALFRED gives point-in-time).
  - Stooq via pandas-datareader — closes our **non-US equity + international index** gap.
- **Tier 2 add (targeted)**:
  - TickVault/duka — **FX + commodity tick** coverage beyond TwelveData's daily bars.
  - CME Group public daily settlements (CSV, no auth) — **commodity futures** settlements; we currently have none.
- **Tier 3 (nice-to-have)**:
  - OpenBB Platform as a unified failover wrapper (but isolate — AGPL).
  - datahub.io bond-yields-us-10y for a zero-key smoke dataset.

**Identified gaps:**
- **BOND**: we have nothing. FRED via `fredapi` is the obvious fix.
- **COMMODITY**: TwelveData gives daily bars but no term structure. CME public CSVs + Stooq futures tickers fill this.
- **Non-US equity**: yfinance coverage is patchy outside US/CA. Stooq + OpenBB's EODHD/FMP adapters help.
- **Crypto funding rates (historical archive)**: no canonical open dataset found — CCXT `fetch_funding_rate_history` per-exchange remains the path; we'd need to roll our own archive.

## Caveats

- **mlfinlab** (Hudson & Thames) — frequently cited but re-licensed to "all rights reserved" / proprietary. **Do not vendor.** Use `timeseriescv` and `pypbo` as permissive substitutes for CPCV and DSR respectively.
- **backtrader** — 11k+ stars but effectively abandoned; dependency drift and no 2026 commits of substance. Skip for new work.
- **Backtesting.py** — great ergonomics but **AGPL-3.0**; bundling it into our audit dashboard would virally relicense. Keep it in an isolated research notebook only.
- **NautilusTrader** — LGPL-3.0, not MIT. Fine as a separate process / CLI; do not statically link or vendor source.
- **OpenBB** — AGPL-3.0 on the core; same isolation rule as Backtesting.py. The "50k stars" figure conflates multiple repos — the real OSS repo is ~35k.
- **FinRL / FinRL-X** — impressive on paper but most published Sharpe numbers don't survive purged CV. Treat as a strategy-generation tool, not a validation authority.
- **QuantaAlpha / "AI-native" LLM-factor-mining repos** — interesting but largely unvalidated and young (<1 year, <1k stars). Watch, don't adopt.

---
_Compiled via WebSearch + GitHub metadata verification. Not committed. Do not treat star counts as exact — they're order-of-magnitude estimates from April 2026 snapshots._
