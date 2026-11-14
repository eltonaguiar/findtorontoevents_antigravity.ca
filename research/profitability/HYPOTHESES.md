# Hypothesis Registry

Every candidate tested is listed here. `N` for multiple-testing includes all rows with status
`TESTING` or later. No failure is removed.

| ID | Hypothesis | Universe | Params | Status | Final OOS evidence |
|---|---|---|---|---|---|
| H1 | BTC 200d TSMOM, long/flat | BTCUSDT | 200d, 10 bps | **NOT_PROVED** | Sharpe 0.60, CAGR 16.5%, n=29; no edge over B&H |
| H2 | ETH 200d TSMOM, long/flat | ETHUSDT | 200d, 10 bps | **NOT_PROVED** | Sharpe 0.47, CAGR 11.5%, n=21 |
| H3 | XS crypto momentum, weekly top-3 | 10 majors | 28d, top 3, 10 bps | **NOT_PROVED** | Sharpe −0.00, CAGR −19.2% |
| H4 | Crypto RSI(2) | BTC/ETH/SOL | 10/50/5, 10 bps | **NOT_PROVED** | Sharpe 0.06, CAGR −4.6% |
| H5 | ETF dual momentum | SPY/EFA/AGG/BIL | 12m, monthly, 5 bps | **NOT_PROVED** | Sharpe 0.99, n=6, fails n≥30 |
| H6 | Vol-scaled BTC TSMOM | BTCUSDT | 200d/20d, 40% target, 1.5x cap | **NOT_PROVED** | Sharpe 0.55, no edge over B&H |
| H7 | Equity RSI(2) | SPY/QQQ | 10/50/5, 5 bps | **NOT_PROVED** | Sharpe 1.50, CAGR 17.6% vs 18.6% B&H; fails absolute return |
| H8 | Sector-ETF RSI(2) + T-bill cash | 10 sectors | 10/50/5, 5 bps | **NOT_PROVED** | Sharpe 1.16, DSR 0.603, fails DSR/benchmark |
| H9 | International-ETF RSI(2) + cash | 10 countries | 10/50/5, 5 bps | **NOT_PROVED** | Sharpe 0.31, CAGR 4.1% |
| H10 | Core RSI(2) + T-bill cash | SPY/QQQ | 10/50/5, 5 bps | **NOT_PROVED (exploratory)** | Sharpe 1.83, CAGR 22.0%, DSR 0.978 at N=12, p=0.00194; PBO 0.106 OOS-only / 0.417 full-sample; fails at effective N≈38 (0.9365), ex-top-1 (0.8993), and 2-day lag (0.696); OOS contaminated per §4 |
| H11 | Sector RSI(2) + trend + cash | 10 sectors | 200d trend, 10/50/5 | **NOT_PROVED** | Sharpe 1.04, DSR 0.529 |
| H12 | Sector 12-1 momentum + cash | 10 sectors | 252d, top 3, monthly | **NOT_PROVED** | Sharpe 1.14, n=22, DSR 0.589 |

## Version log

### v1 — 2026-11-14
- Protocol v1.0; N=7.
- Train **2018-01-01..2023-12-31**; OOS **2024-01-01..2026-11-13**.
- Result: 0/7 passed all gates. H7 failed only absolute return (17.6% vs 18.6% B&H).
- Reports: `runs/v1/REPORT.md`, `runs/v1/results.json`, `runs/v1/oos_returns.csv`.
- Data-source addendum 1: Stooq blocked, Nasdaq used for ETFs (pre-result).

### v2 — 2026-11-14
- Added 5 candidates (N=12 cumulative): H8–H12.
- Added T-bill yield on idle cash using Treasury.gov 13-week coupon-equivalent.
- H10 mechanically passed all gates (Sharpe 1.83, CAGR 22.0%, DSR 0.978 at N=12, p=0.00194; PBO 0.106 OOS-only / 0.417 full-sample,
  PBO 0.106 over all 12 on the common calendar, 2× cost Sharpe ~1.68).
- **Adversarial review downgraded H10 to NOT_PROVED**: post-hoc H7 variant on the already-seen
  OOS; effective N≈38 -> DSR 0.9365; ex-best-day DSR 0.8993; 2-day-lag Sharpe 0.696; clean
  2016-2017 holdout underperforms B&H; ~83% of capital in T-bills means the CAGR leans on the
  2024-2026 high-rate regime.
- Reports: `runs/v2/REPORT.md`, `runs/v2/ROBUSTNESS.md`, `runs/v2/VERDICT.md`,
  `validation/REPLICATION_H10.md`, `validation/STATS_REVIEW_H10.md`.

## Status definitions

- `UNTESTED` — declared, no run yet.
- `TESTING` — included in the current run and counted in N.
- `NOT_PROVED` — failed at least one acceptance gate, or failed the clean-OOS/multiple-testing
  integrity review. Exact failures are in the run report.
- `PROVISIONAL` — passed all gates and awaits a genuinely clean forward OOS.
- `PROVED` — passed all gates + clean forward OOS + independent replication + adversarial review.
- `RETIRED` — explicitly abandoned; stays in N for all later corrections.

## Current conclusion

**No approach is PROVED.** The retrospective search (12 candidates + 27-cell parameter grid) is
exhausted for proof purposes. H10 is the strongest candidate but is an exploratory, regime- and
execution-sensitive T-bill-carry/timing sleeve, not a proven edge. The only valid path to proof is
the forward paper test in `forward/README.md`.
