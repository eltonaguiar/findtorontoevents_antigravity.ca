# Protocol v3 — Breadth, Walk-Forward, CPCV, Reality Check

**Status:** locked before any v3 result is inspected.
**Supersedes:** none; extends `PROTOCOL.md` v1.0.
**Why:** v1/v2 were too narrow (2–10 assets), used a single OOS window, and lacked CPCV/SPA.
Contest winners are a selection effect; documented edges require breadth and multiple-testing control.

## 1. Data

| Class | Source | Universe | Notes |
|---|---|---|---|
| Crypto | Binance API/Vision | up to 30 liquid USDT pairs | point-in-time; symbol enters from first bar; no backfill |
| ETF/equity | Nasdaq quote API | up to 40 liquid ETFs (US sectors, countries, factors, bonds, commodities) | price-only; ~10y cap; declared limitation |
| Cash | Treasury.gov 13-week bill | daily | idle-cash yield and risk-free proxy |
| FX | Frankfurter | not used in v3 core | carry requires rate data not sourced |

Symbols with <252 daily bars at a rebalance are excluded. No survivorship backfill.

## 2. Splits and validation

- **Design/train:** 2018-01-01..2023-12-31.
- **Primary OOS:** 2024-01-01..last complete bar.
- **Walk-forward:** rolling 3-year train, 1-year test, step 1 year; aggregate the 2021–2026 test
  folds (crypto symbols entering later use their available folds).
- **CPCV:** 6 contiguous blocks, purge 5 trading days, embargo 5 trading days; all 20 train/test
  combinations; report the distribution of OOS Sharpe and PBO.
- **Reality Check / SPA:** stationary bootstrap, 5,000 resamples, mean block 20; null = no
  candidate beats the benchmark after centering; report the max-statistic p-value.
- **Clean forward:** the frozen ledger in `forward/`; any v3 candidate promoted to PROVISIONAL must
  run there for ≥90 days / ≥30 rebalances before PROVED.

## 3. Costs and execution

- Crypto 10 bps per side; ETF 5 bps per side; 2× stress.
- Signals at close t; positions from t+1. Monthly/weekly strategies rebalance at the next session.
- No shorting except the explicitly long-short candidate; borrow/funding not modeled (declared).
- Execution-lag gate: an extra day (daily) or extra period (weekly/monthly) must retain ≥1.0 OOS
  Sharpe and beat the benchmark.

## 4. Candidate registry (v3, cumulative N = 12 + 8 = 20)

| ID | Hypothesis | Universe | Rebalance | Signal | Costs |
|---|---|---|---|---|---|
| H13 | Crypto XS momentum, long top quintile | 30 pairs | weekly | 28d return | 10 bps |
| H14 | Crypto short-term reversal, long losers | 30 pairs | weekly | 7d return bottom quintile | 10 bps |
| H15 | Crypto TSMOM breadth, vol-targeted | 20 pairs | monthly | 12m trend | 10 bps |
| H16 | ETF XS momentum, top 3 | 40 ETFs | monthly | 12-1 momentum | 5 bps |
| H17 | ETF short-term reversal, long losers | 40 ETFs | weekly | 5d return bottom decile | 5 bps |
| H18 | Multi-asset TSMOM, vol-targeted | 20 ETFs | monthly | 12m trend | 5 bps |
| H19 | Country rotation, top 3 | 12 country ETFs | monthly | 12-1 momentum | 5 bps |
| H20 | Crypto momentum + BTC trend filter | 30 pairs | weekly | top quintile only if BTC>200d SMA | 10 bps |

All parameters are fixed here. No per-symbol tuning. Any change creates H2x and a new version.

## 5. Acceptance gates (all must pass for PROVED)

1. Primary OOS net Sharpe ≥1.0 and ≥ benchmark + 0.30.
2. Primary OOS net CAGR >0 and total return > benchmark.
3. ≥30 rebalances/trades in OOS.
4. Walk-forward aggregate OOS Sharpe ≥0.8 and > benchmark.
5. CPCV median OOS Sharpe ≥0.5 and PBO <0.5.
6. Reality Check / SPA p <0.05 across all 20 candidates.
7. DSR ≥0.95 at cumulative N=20 (and at N=20+grid looks).
8. Bootstrap 5th-percentile Sharpe >0 (block 20, 2,000 resamples).
9. 2× cost Sharpe ≥0.5 and > benchmark.
10. Execution-lag: extra-day/period Sharpe ≥1.0 and > benchmark.
11. Parameter stability: central parameter survives a small train-only neighbourhood.

Failure of any gate → NOT_PROVED for that candidate. All failures stay in N.

## 6. Anti-overfitting

- No OOS inspection before the run is complete; all candidates reported.
- No parameter selection on OOS; grids are train-only.
- Every candidate, including failures, is counted in SPA/DSR/Bonferroni.
- The v3 universe is fixed here; adding symbols later is a new version.

## 7. Deliverables

`runs/v3/{results.json,REPORT.md,VERDICT.md,oos_returns.csv,weights/}` and updates to
`HYPOTHESES.md`, `SCORECARD.md`, and `README.md`. Independent replication + adversarial review for
any candidate that passes.
