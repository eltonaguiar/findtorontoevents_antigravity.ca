# Profitability Research Program

Independent, pre-registered search for a net-of-cost, out-of-sample edge. This is separate from the
existing `/audit` surfaces and does not use their picks as inputs.

**Status: NOT PROVED.** 12 candidates + a 27-cell parameter grid were tested. One exploratory
candidate (H10) passed the mechanical gates but failed the strict proof standard on OOS
contamination, effective multiple testing, single-day dependence, execution lag, and regime
dependence. Full reasoning: `runs/v2/VERDICT.md`.

## Headline results

| Candidate | OOS Sharpe | OOS CAGR | Benchmark Sharpe | Status |
|---|---:|---:|---:|---|
| H10 SPY/QQQ RSI(2) + T-bill cash | **1.83** | **22.0%** | 1.02 | **NOT_PROVED (exploratory)** |
| H7 SPY/QQQ RSI(2), no cash | 1.50 | 17.6% | 1.02 | NOT_PROVED |
| H8 Sector RSI(2) + cash | 1.16 | 17.2% | 1.09 | NOT_PROVED |
| H12 Sector 12-1 momentum + cash | 1.14 | 16.7% | 1.09 | NOT_PROVED |
| H5 ETF dual momentum | 0.99 | 16.2% | 0.99 | NOT_PROVED |
| H1 BTC 200d TSMOM | 0.60 | 16.5% | 0.56 | NOT_PROVED |
| H6 BTC vol-scaled TSMOM | 0.55 | 14.1% | 0.56 | NOT_PROVED |
| H2 ETH 200d TSMOM | 0.47 | 11.5% | 0.22 | NOT_PROVED |
| H9 International RSI(2) + cash | 0.31 | 4.1% | 0.90 | NOT_PROVED |
| H4 Crypto RSI(2) | 0.06 | −4.6% | 0.34 | NOT_PROVED |
| H3 XS crypto momentum | −0.00 | −19.2% | 0.22 | NOT_PROVED |
| H11 Sector RSI(2) + trend + cash | 1.04 | 11.5% | 1.09 | NOT_PROVED |

## Why H10 is not a proof

- Created as a post-hoc cash variant of H7 on the **same already-seen OOS window** (protocol §4).
- At effective `N≈38` (including the parameter grid): **DSR 0.9365 < 0.95**, Bonferroni fails.
- Removing the single best day (2025-04-09, +11.20%) drops DSR to **0.8993**.
- A 2-day execution lag drops Sharpe to **0.696**; 3-day to **0.477**.
- Clean 2016-2017 holdout: Sharpe 1.755 / CAGR 7.46% vs B&H 2.835 / 25.76%.
- ~83% of capital sits in T-bills; the 22% CAGR leans on the 2024-2026 high-rate regime.

## Layout

```
PROTOCOL.md                 locked pre-registration + Addendum 1 (Nasdaq fallback)
HYPOTHESES.md               registry, statuses, version log
backtest.py                 costs, train/OOS metrics, bootstrap, DSR, PBO
strategies.py               candidate implementations
data/loader.py              Binance / Nasdaq / Treasury loaders (cache gitignored)
run_v1.py, run_v2.py        versioned runs
validate_h10.py             robustness: dividends, yearly, grid, costs, lag, risk-matched
runs/v1/                    results.json, REPORT.md, oos_returns.csv
runs/v2/                    results.json, REPORT.md, ROBUSTNESS.md, VERDICT.md, weights, returns
validation/                 independent replication + adversarial statistical review
forward/                    forward paper-validation ledger and rules
```

## Reproduce

```bash
cd research/profitability
python3 run_v1.py          # ~1 min cached; re-downloads if cache is empty
python3 run_v2.py          # ~1-2 min cached
python3 validate_h10.py    # robustness
```

Data sources: Binance Vision/API (crypto), Nasdaq quote API (ETFs), Treasury.gov 13-week bill
(risk-free cash). No API keys. Cache under `data/cache/` (gitignored); manifests in
`data/manifest.json`.

## Next step

Forward validation only: `forward/README.md`. Parameters are frozen. Any change is a new version
and a new ledger. Do not size real capital on H10 based on the retrospective result.
