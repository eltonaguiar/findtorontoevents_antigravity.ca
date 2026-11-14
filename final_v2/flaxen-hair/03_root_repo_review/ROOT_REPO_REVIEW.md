# Root Repo Review — final_v2

**Date:** 2026-11-14 | **Worktree:** flaxen-hair | **Repo:** /home/eaguiar2015/findtorontoevents_antigravity.ca

This document reviews newly modified files in the root repo since the last audit, with focus on profitability-relevant changes.

## Newly Modified Files (last 120 minutes)

### Profitability Research Program (PRIORITY)

| File | Status | Relevance |
|------|--------|-----------|
| `research/profitability/README.md` | Modified | Program overview: 23 candidates, NONE PROVED |
| `research/profitability/HYPOTHESES.md` | Modified | 23 hypothesis registry with statuses |
| `research/profitability/SCORECARD.md` | Modified | Goal scorecard: 7.0/10 overall, 0/10 profitability proof |
| `research/profitability/runs/v4/VERDICT.md` | Modified | Funding carry: NOT_PROVED (0/3) |
| `research/profitability/runs/v3/VERDICT.md` | Modified | Breadth: NOT_PROVED (0/8) |
| `research/profitability/runs/v2/VERDICT.md` | Modified | v1+v2: NOT PROVED, H10 exploratory |
| `research/profitability/validation/VWAP_VERDICT.md` | Modified | Peer VWAP claim FALSIFIED |

### Data Files Modified

| File | Status | Relevance |
|------|--------|-----------|
| `genome/data/darwin_portfolios.json` | Modified | Portfolio data |
| `genome/data/mape_archive.json` | Modified | MAPE archive |
| `genome/data/ae_active_picks.json` | Modified | Active picks |
| `genome/data/onchain_cache.json` | Modified | On-chain cache |
| `genome/data/mape_active_picks.json` | Modified | MAPE active picks |
| `genome/data/gp_active_picks.json` | Modified | GP active picks |
| `genome/data/ensemble_active_picks.json` | Modified | Ensemble active picks |

### Worktree Data Modified

| File | Status | Relevance |
|------|--------|-----------|
| `.kilo/worktrees/finpredict/dashboard/live_picks.json` | Modified | Live picks dashboard |
| `.kilo/worktrees/finpredict/mercury2/data/metrics_report.json` | Modified | Metrics report |

## Profitability Research Program — Complete Findings

### All 23 Hypotheses (from HYPOTHESES.md)

| ID | Hypothesis | Universe | Status | Best Metric |
|----|------------|----------|--------|-------------|
| H1 | BTC 200d TSMOM | BTCUSDT | NOT_PROVED | Sharpe 0.60 |
| H2 | ETH 200d TSMOM | ETHUSDT | NOT_PROVED | Sharpe 0.47 |
| H3 | XS crypto momentum | 10 majors | NOT_PROVED | Sharpe -0.00 |
| H4 | Crypto RSI(2) | BTC/ETH/SOL | NOT_PROVED | Sharpe 0.06 |
| H5 | ETF dual momentum | SPY/EFA/AGG/BIL | NOT_PROVED | Sharpe 0.99, n=6 |
| H6 | Vol-scaled BTC TSMOM | BTCUSDT | NOT_PROVED | Sharpe 0.55 |
| H7 | Equity RSI(2) | SPY/QQQ | NOT_PROVED | Sharpe 1.50, CAGR 17.6% vs 18.6% B&H |
| H8 | Sector RSI(2)+trend+cash | 10 sectors | NOT_PROVED | Sharpe 1.04, DSR 0.603 |
| H9 | International RSI(2)+cash | 10 countries | NOT_PROVED | Sharpe 0.31 |
| H10 | Core RSI(2)+T-bill cash | SPY/QQQ | NOT_PROVED (exploratory) | Sharpe 1.83, CAGR 22.0% |
| H11 | Sector RSI(2)+trend+cash | 10 sectors | NOT_PROVED | Sharpe 1.04, DSR 0.529 |
| H12 | Sector 12-1 momentum+cash | 10 sectors | NOT_PROVED | Sharpe 1.14, n=22 |
| H13 | Crypto XS momentum (top quintile) | 30 pairs | NOT_PROVED | Sharpe -0.18 |
| H14 | Crypto short-term reversal | 30 pairs | NOT_PROVED | Sharpe -0.36 |
| H15 | Crypto TSMOM breadth | 20 pairs | NOT_PROVED | Sharpe 0.20 |
| H16 | ETF XS momentum (top 3) | 50 ETFs | NOT_PROVED | Sharpe 0.98 vs 1.18 bench |
| H17 | ETF short-term reversal | 50 ETFs | NOT_PROVED | Sharpe 0.76 vs 1.18 bench |
| H18 | ETF TSMOM breadth | 20 ETFs | NOT_PROVED | Sharpe 1.00, WF 0.37 |
| H19 | Country rotation | 12 country ETFs | NOT_PROVED | Sharpe 0.76, n=22 |
| H20 | Crypto momentum + BTC trend | 30 pairs | NOT_PROVED | Sharpe -0.08 |
| H21 | Funding carry top 5 | 30 perps | NOT_PROVED | Sharpe 6.42, below cash |
| H22 | Funding carry BTC only | BTC perp | NOT_PROVED | Sharpe 14.24, n=10 <30 |
| H23 | Funding carry top 10 | 30 perps | NOT_PROVED | Sharpe 8.34, below cash |

### Version Results

| Version | Candidates | Best Result | Verdict |
|---------|------------|-------------|---------|
| v1 | 7 | H7 RSI2: Sharpe 1.50, CAGR 17.6% vs 18.6% B&H | NOT_PROVED |
| v2 | +5 | H10 RSI2+cash: Sharpe 1.83, CAGR 22.0% | NOT_PROVED (contaminated OOS) |
| v3 | +8 | H16 ETF XS momentum: Sharpe 0.98 vs 1.18 bench | NOT_PROVED (0/8) |
| v4 | +3 | H22 BTC funding: Sharpe 14.24, 4.8% capital-adjusted | NOT_PROVED (n=10 <30) |

### Scorecard (7.0/10 overall)

| Criterion | Weight | Score |
|-----------|--------|-------|
| Pre-registration | 15% | 9/10 |
| Data provenance | 15% | 7/10 |
| Candidate breadth | 15% | 8/10 |
| Statistical controls | 20% | 9/10 |
| Independent replication | 10% | 8/10 |
| Verdict honesty | 15% | 10/10 |
| **Actual profitability proof** | **10%** | **0/10** |

### Key Conclusions from Profitability Research

1. **No approach is PROVED** — honest negative result after exhaustive testing
2. **H10 came closest** but failed on OOS contamination, effective N≈38, single-day dependence, execution fragility
3. **H22 BTC funding carry** has real signal (DSR 1.0) but is capital-intensive and doesn't beat cash after realistic capital
4. **Peer VWAP claim FALSIFIED** — annualization error, PBO not PBO, DSR not DSR, intrabar stops ignored
5. **Contest winners = survivorship bias** — not proof of repeatable method
6. **Keyless data hypothesis space is exhausted** — need intraday/order-book/options/venue data for new edge families

## Files to Copy to final_v2/03_root_repo_review/

The following profitability research files should be copied:
- research/profitability/README.md
- research/profitability/HYPOTHESES.md
- research/profitability/SCORECARD.md
- research/profitability/runs/v4/VERDICT.md
- research/profitability/runs/v3/VERDICT.md
- research/profitability/runs/v2/VERDICT.md
- research/profitability/validation/VWAP_VERDICT.md
- research/profitability/PROTOCOL_v4.md
