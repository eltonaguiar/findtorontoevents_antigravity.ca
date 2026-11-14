# Profitability Research Program

Independent, pre-registered search for a net-of-cost, out-of-sample edge. This is separate from the
existing `/audit` surfaces and does not use their picks as inputs.

**Status: NOT PROVED.** 23 candidates across four versions. One exploratory candidate (H10) passed
the v1/v2 mechanical gates but failed the strict proof standard; v3 breadth and v4 funding carry
also failed. Full reasoning: `runs/v2/VERDICT.md`, `runs/v3/VERDICT.md`, `runs/v4/VERDICT.md`,
`SCORECARD.md`.

## Headline results

| Candidate | OOS Sharpe | OOS CAGR | Benchmark | Status |
|---|---:|---:|---:|---|
| H22 BTC funding carry | **14.24** | 7.2% (4.8% at 1.5× capital) | 4.5% cash | NOT_PROVED (n=10) |
| H21 top-5 funding carry | **6.42** | 5.6% (3.7% at 1.5× capital) | 4.5% cash | NOT_PROVED (below cash) |
| H23 top-10 funding carry | **8.34** | 6.2% (4.1% at 1.5× capital) | 4.5% cash | NOT_PROVED (below cash) |
| H10 SPY/QQQ RSI(2)+cash | 1.83 | 22.0% | 18.6% B&H | NOT_PROVED (contaminated OOS) |
| H7 SPY/QQQ RSI(2) | 1.50 | 17.6% | 18.6% B&H | NOT_PROVED |
| H16 ETF XS momentum | 0.98 | 29.6% | 1.18 Sharpe | NOT_PROVED |
| H18 ETF TSMOM breadth | 1.00 | 12.0% | 0.99 Sharpe | NOT_PROVED |
| H17 ETF XS reversal | 0.76 | 15.2% | 1.18 Sharpe | NOT_PROVED |
| H19 Country momentum | 0.76 | 16.8% | 0.99 Sharpe | NOT_PROVED |
| H1 BTC 200d TSMOM | 0.60 | 16.5% | 0.56 Sharpe | NOT_PROVED |
| H6 BTC vol-scaled TSMOM | 0.55 | 14.1% | 0.56 Sharpe | NOT_PROVED |
| H2 ETH 200d TSMOM | 0.47 | 11.5% | 0.22 Sharpe | NOT_PROVED |
| H15 Crypto TSMOM breadth | 0.20 | −2.9% | 0.06 Sharpe | NOT_PROVED |
| H9 Intl RSI(2)+cash | 0.31 | 4.1% | 0.90 Sharpe | NOT_PROVED |
| H4 Crypto RSI(2) | 0.06 | −4.6% | 0.34 Sharpe | NOT_PROVED |
| H3 XS crypto momentum | −0.00 | −19.2% | 0.22 Sharpe | NOT_PROVED |
| H13 Crypto XS momentum (30 pairs) | −0.18 | −31.9% | −0.01 Sharpe | NOT_PROVED |
| H20 Crypto momentum + BTC trend | −0.08 | −21.3% | −0.01 Sharpe | NOT_PROVED |
| H14 Crypto XS reversal | −0.36 | −44.3% | −0.01 Sharpe | NOT_PROVED |

## Why nothing is proved

- **H10**: post-hoc cash variant of H7 on the same seen OOS; DSR fails at effective N≈38 (0.9365),
  ex-best-day (0.8993), and 2-day lag (0.696); clean 2016-17 holdout underperforms B&H.
- **v3 breadth**: best candidate (H16) underperformed its own ETF benchmark (0.98 vs 1.18); Reality
  Check p=0.488; no momentum/reversal edge across 30 crypto pairs and 50 ETFs.
- **v4 funding carry**: real low-vol carry (DSR 1.0) but capital-intensive. At 1.5× capital,
  top-5/top-10 return 3.7–4.1% vs 4.5% cash; BTC-only returns 4.8% but has 10 rebalances (<30).

## Layout

```
PROTOCOL.md, PROTOCOL_ADDENDUM_1.md, PROTOCOL_v3.md, PROTOCOL_v4.md
HYPOTHESES.md               registry (23 candidates), statuses, version log
SCORECARD.md                goal scoring + TradingView selection argument
backtest.py                 costs, train/OOS metrics, bootstrap, DSR, PBO
strategies.py               candidates (TSMOM, RSI2, XS, carry weights)
data/loader.py              Binance spot/funding, Nasdaq, Treasury loaders
run_v1.py ... run_v4.py     versioned runs
validate_h10.py             robustness for the v2 candidate
runs/v1..v4/                results, reports, verdicts, returns, weights
validation/                 independent replication + adversarial statistical review (v1/v2)
forward/                    frozen forward ledger (H10)
```

## Reproduce

```bash
cd research/profitability
python3 run_v1.py
python3 run_v2.py
python3 run_v3.py
python3 run_v4.py
python3 validate_h10.py
```

Data sources: Binance Vision/API (spot + funding), Nasdaq quote API (ETFs), Treasury.gov 13-week
bill (cash). No API keys. Cache under `data/cache/` (gitignored); manifests in
`data/manifest.json`.

## Next step

Forward validation only for any candidate you choose to promote; parameters are frozen.
`forward/README.md` documents the H10 ledger. For a contest-style edge, new data is required:
intraday/order-book, options/vol-risk-premium, or venue-level capital/funding data.
