# Proof Assessment

**Worktree:** flaxen-hair_2026-11-14T2200 | **Sources:** research/profitability/* (v1-v4), remote financial files, source audits

## Scorecard Summary

| Criterion | Weight | Score | Basis |
|-----------|--------|-------|-------|
| Pre-registration | 15% | 9/10 | Protocol v1-v4 locked before results |
| Data provenance | 15% | 7/10 | Binance/Nasdaq/Treasury; manifests + SHA-256 |
| Candidate breadth | 15% | 8/10 | 23 candidates; 30 crypto pairs, 50 ETFs, 30 perps |
| Statistical controls | 20% | 9/10 | DSR, PBO/CSCV, Bonferroni/BH, bootstrap, walk-forward, Reality Check/SPA |
| Independent replication | 10% | 8/10 | v1/v2 replicated exactly + adversarial stats review |
| Verdict honesty | 15% | 10/10 | H10 downgraded; v3/v4 failures published; capital-adjusted gate used |
| **Process total** | **90%** | **7.7/10** | Strong process and breadth |
| **Actual profitability proof** | **10%** | **0/10** | No candidate survives clean-OOS + effective-N + capital + execution gates |
| **Overall** | **100%** | **7.0/10** | Good science, negative result |

## 23 Hypotheses — All NOT_PROVED

| ID | Hypothesis | Best Metric | Reason |
|----|------------|-------------|--------|
| H1 | BTC 200d TSMOM | Sharpe 0.60 | No edge over B&H |
| H2 | ETH 200d TSMOM | Sharpe 0.47 | No edge over B&H |
| H3 | XS crypto momentum | Sharpe −0.00 | Negative CAGR −19.2% |
| H4 | Crypto RSI(2) | Sharpe 0.06 | Negative CAGR −4.6% |
| H5 | ETF dual momentum | Sharpe 0.99, n=6 | Fails n≥30 |
| H6 | Vol-scaled BTC TSMOM | Sharpe 0.55 | No edge over B&H |
| H7 | Equity RSI(2) | Sharpe 1.50, CAGR 17.6% vs 18.6% B&H | Fails absolute return |
| H8 | Sector RSI(2)+trend+cash | Sharpe 1.04, DSR 0.603 | Fails DSR/benchmark |
| H9 | International RSI(2)+cash | Sharpe 0.31 | No edge |
| H10 | Core RSI(2)+T-bill cash | Sharpe 1.83, CAGR 22.0% | Contaminated OOS, effective N=38 |
| H11 | Sector RSI(2)+trend+cash | Sharpe 1.04, DSR 0.529 | Fails DSR |
| H12 | Sector 12-1 momentum+cash | Sharpe 1.14, n=22 | Fails n≥30, DSR 0.589 |
| H13 | Crypto XS momentum (top quintile) | Sharpe −0.18 | SPA p=0.488, negative |
| H14 | Crypto short-term reversal | Sharpe −0.36 | Negative CAGR −44.3% |
| H15 | Crypto TSMOM breadth | Sharpe 0.20 | Negative CAGR −2.9% |
| H16 | ETF XS momentum (top 3) | Sharpe 0.98 vs 1.18 bench | Underperforms benchmark |
| H17 | ETF short-term reversal | Sharpe 0.76 vs 1.18 bench | Underperforms benchmark |
| H18 | ETF TSMOM breadth | Sharpe 1.00, WF 0.37 | Weak walk-forward |
| H19 | Country rotation | Sharpe 0.76, n=22 | Fails n≥30 |
| H20 | Crypto momentum + BTC trend | Sharpe −0.08 | Negative CAGR −21.3% |
| H21 | Funding carry top 5 | Sharpe 6.42, capital-adjusted 3.7% | Below cash 4.5% |
| H22 | Funding carry BTC only | Sharpe 14.24, capital-adjusted 4.8% | n=10 < 30 |
| H23 | Funding carry top 10 | Sharpe 8.34, capital-adjusted 4.1% | Below cash 4.5% |

## Version Results

| Version | Candidates | Best Result | Verdict |
|---------|------------|-------------|---------|
| v1 | 7 | H7 RSI2: Sharpe 1.50, CAGR 17.6% vs 18.6% B&H | NOT_PROVED |
| v2 | +5 | H10 RSI2+cash: Sharpe 1.83, CAGR 22.0% | NOT_PROVED (contaminated OOS) |
| v3 | +8 | H16 ETF XS momentum: Sharpe 0.98 vs 1.18 bench | NOT_PROVED (0/8, SPA 0.488) |
| v4 | +3 | H22 BTC funding: Sharpe 14.24, 4.8% capital | NOT_PROVED (n=10 < 30) |

## Peer VWAP Claim — FALSIFIED

| Metric | Peer Claim | Independent | Basis |
|--------|-----------|-------------|-------|
| Trades | 129 (5 symbols) | 72 (5-symbol subset) | harness + saved JSON |
| Profit Factor | 1.210 | 0.810 with intrabar stops | 79/129 breached stops intrabar |
| Sharpe | 3.76 | ~1.18 (portfolio) | Annualization error |
| t-stat | z≈16 (DSR) | 0.912, p≈0.18 | Not significant |
| DSR | 1.0000 | 0.828 (N=1); 0.011 (N=960) | Not true DSR |
| PBO | 0.489 | 0.840–0.970 (CSCV) | Not PBO, bootstrap tail |
| OOS length | ~22 months | 7.18 months | Mislabelled |
| Total return | +12.7% | −17.4% with intrabar stops | Not profitable |

## Bottom Line

**0/23 hypotheses PROVED.** The keyless data hypothesis space is exhausted. The only forward-validated candidate is mega_mutation_macd_rsi on CRYPTO (PF 8.32, WR 84%, n=50 forward), which requires n≥100 forward confirmation before live capital.
