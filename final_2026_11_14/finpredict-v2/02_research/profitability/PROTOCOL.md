# Pre-Registered Protocol — Profitability Research

**Version:** 1.0 (locked before any backtest result is inspected)
**Created:** 2026-11-14T18:15Z
**Status:** active
**Rule:** any change to data, universe, split, cost, metric, or gate creates a new version
(`PROTOCOL_v2.md`, etc.) and is recorded in `HYPOTHESES.md`. No retro-editing of a locked protocol.

## 1. Objective

Determine whether any systematic approach in this repository's domain (crypto, ETFs, equities, FX)
produces a **net-of-cost, out-of-sample** edge that is distinguishable from luck after correcting
for the number of hypotheses tested. A negative result is a valid and publishable outcome.

## 2. Data sources (named, public)

| Class | Source | URL | Notes |
|---|---|---|---|
| Crypto | Binance Vision monthly klines (primary) | `https://data.binance.vision/data/spot/monthly/klines/<SYM>/1d/` | UTC daily bars; official archive |
| Crypto | Binance spot API (fallback / current month) | `https://api.binance.com/api/v3/klines` | paginate 1000 bars |
| ETF / equity | Stooq daily CSV | `https://stooq.com/q/d/l/?s=<sym>.us&i=d` | split/dividend-adjusted close where available |
| FX | Frankfurter (ECB) | `https://api.frankfurter.app/<start>..<end>?from=USD&to=CAD` | daily reference rates |

Yahoo is **not** used as a primary source (HTTP 429 observed). Any fallback is recorded in the run
manifest. Raw data is cached under `data/cache/` (gitignored); the manifest (symbol, source, rows,
first/last date, SHA-256) is committed.

## 3. Universe (fixed ex ante)

- **Crypto majors (10):** BTCUSDT, ETHUSDT, BNBUSDT, SOLUSDT, XRPUSDT, ADAUSDT, DOGEUSDT,
  LTCUSDT, LINKUSDT, DOTUSDT.
  - Symbols enter the cross-section only from their first available bar; no backfill.
  - If a symbol has <180 daily bars at a rebalance date, it is excluded (no lookahead).
- **ETFs (4):** SPY, EFA, AGG, BIL (cash proxy).
- **Equities (2):** SPY, QQQ for the RSI2 test (ETF proxies for US equity).
- **FX (2):** USDCAD, NZDUSD (validation only; not a primary strategy in v1).

## 4. Splits

- **Train / design:** 2018-01-01 through 2023-12-31.
- **Out-of-sample (OOS):** 2024-01-01 through the last complete bar at run time.
- Parameters are chosen **only** on train. OOS is evaluated once per version. If a version is
  revised after seeing OOS, the next version's OOS starts at the revision date (rolling OOS), and
  the prior OOS is demoted to "seen" and no longer counts as clean.

## 5. Execution and costs

- Signals use the close of bar `t`; positions apply from bar `t+1`. No same-bar execution.
- Daily bars only; no intraday assumptions.
- **Costs per side:** crypto **10 bps**, ETF **5 bps**, FX **2 bps**. A round trip pays twice.
- Optional stress: 2× the base cost. A candidate that only survives at 1× is not promoted.
- No shorting in v1 unless the hypothesis explicitly says so; borrow/funding costs are ignored only
  where the strategy is long-only or flat.
- Position sizing: fully invested when long, 0 when flat, except the vol-scaled variant which caps
  exposure at 1.5× and uses no leverage beyond that cap.

## 6. Metrics (reported for train and OOS separately)

CAGR, annualized volatility, Sharpe (rf=0, 365 for crypto / 252 for ETF), Sortino, max drawdown,
Calmar, hit rate, profit factor, turnover (annualized), average exposure, number of position
changes / round trips, and buy-and-hold benchmark metrics for the same asset/universe.

## 7. Acceptance gates (all must pass for "PROVED")

1. **OOS net Sharpe ≥ 1.0** and **≥ benchmark Sharpe + 0.30**.
2. **OOS net CAGR > 0** and **OOS net total return > benchmark** over the same window.
3. **n ≥ 30 OOS trades** (position changes or round trips, as declared per hypothesis).
4. **Deflated Sharpe Ratio (DSR) ≥ 0.95**, with `N` = number of candidates tested in the version
   (not a hand-picked subset).
5. **PBO < 0.50** where the candidate set permits CSCV; if not computable, state why and use the
   bootstrap + DSR gates.
6. **Bootstrap 5th-percentile Sharpe > 0** (block bootstrap, 2,000 resamples, block 20).
7. **2× cost stress:** OOS Sharpe still ≥ 0.5 and still > benchmark.
8. **Parameter stability:** the sign of the edge must not depend on a single parameter value;
   report a small neighbourhood grid on train only.
9. **No lookahead / survivorship:** data is point-in-time; delisted/missing symbols are excluded
   at the time they disappear, not backfilled.

Any failure → verdict **NOT PROVED** for that version, with the failing gate recorded.

## 8. Multiple-testing control

- Every candidate tested in a version is counted in `N`, including failures.
- Bonferroni and BH-FDR are applied across all candidates in the version.
- A candidate that is "significant" only because it was selected after seeing OOS is rejected.
- The hypothesis registry (`HYPOTHESES.md`) records the exact count and status.

## 9. Anti-overfitting rules

- Maximum 2 free parameters per hypothesis in v1; any additional parameter requires a new version.
- No per-symbol tuning in v1.
- No dropping of bad years or bad regimes.
- Parameter grids are evaluated on train only; the OOS result for the pre-declared central value is
  the headline, not the best grid cell.
- Every version publishes its failures, not only its winners.

## 10. Versioning and publication

- Each run writes `runs/v<k>/manifest.json`, `results.json`, `REPORT.md`, and `equity_curves.csv`.
- `HYPOTHESES.md` is updated with status: `UNTESTED`, `TESTING`, `NOT_PROVED`, `PROVISIONAL`,
  `PROVED`, `RETIRED`.
- Publication target: `research/profitability/` on `origin/main`, via a clean branch from fresh
  `origin/main`; only this folder is committed.
- A "PROVED" claim requires an independent replication by a separate subagent (same code, fresh
  data pull) and an adversarial review before publication.

## 11. Known limitations (declared before results)

- Daily data cannot capture intraday fills; slippage may be worse than modeled.
- Binance spot history excludes delisted pairs; the fixed majors universe mitigates but does not
  eliminate survivorship.
- Funding/borrow costs are not modeled for short or leveraged positions.
- Stooq adjusted-close methodology is not identical to CRSP; results are indicative.
- Crypto trades 24/7; ETF/equity results follow exchange calendars.
