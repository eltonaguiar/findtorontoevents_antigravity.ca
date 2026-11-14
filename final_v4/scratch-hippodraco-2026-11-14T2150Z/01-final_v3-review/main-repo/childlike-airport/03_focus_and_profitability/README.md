# 03 — Focus Decision & Profitability Targets

**Date:** 2026-11-14 | **Basis:** `00_common_themes`, `02_subq_comparison`, strict validation gates.

## 1. Prioritized Focus

| Priority | Focus | Rationale | Success signal |
|---|---|---|---|
| **P0** | Data/PnL integrity + CI/observability | Metrics untrustworthy (stale/zombies/fake PnL, empty audit trail, workflow issues) | Reconciled PnL, fresh SLA, audit/regime live, CI green |
| **P1** | **Crypto — Vol-Targeted TSMOM** | Strongest diversified research (7.4y CAGR 23.0%, Sharpe 2.13, PF 1.40, MDD −17.4%, CI [1.25,3.25]) | Reproduced net-of-cost OOS, benchmark/bear robust, paper pass |
| **P1** | **Crypto — Regime-Filtered VWAP-MR core** (BTC,ETH,SOL,XRP,ADA) | Basic-validated, selective (v11 PF 1.435 Sharpe 7.10 MDD 3.5% n=65; v12 PF 1.210 Sharpe 3.76 MDD 10% n=129, PBO ~0.489) | >730d data, PBO<0.3, cost/fill stress, core stable, paper |
| **P2** | **Stocks/ETFs — Faber TAA or sector-neutral QVM** | Long history, low cost/turnover, non-crypto diversifier | Net-of-cost risk-matched outperformance |
| **P2** | **Mutual funds — low-capital/low-fee indexed allocation** | $0-min/ultra-low ER + existing MF infra; needs wired validated signal | Wired class + OOS/paper net-of-fee |
| **P3** | Variant C, mega_mutation replication | Upside but contested/unreplicated | Independent reproduction clears gates |
| **Defer** | Bonds, Forex, Commodities | Unvalidated / blocked | Post-fix/build proof |

## 2. ≥1–2 Profitable Asset Classes Beyond Mutual Funds (to validate)
> Evidence-backed **targets**, not claims of current live profitability.

| Target | Why plausible | Must prove | Confidence |
|---|---|---|---|
| **1) Crypto (trend): Vol-Targeted TSMOM** | Diversified trend premium, long sample, positive bootstrap CI | Net-of-cost/funding OOS alpha vs benchmark across regimes, stable PBO/DSR/MDD, paper | Medium-High (research) |
| **2) Crypto (selective MR): Regime-Filtered VWAP-MR core** | Positive OOS PF/Sharpe/DSR with regime filter+sizing in liquid majors | PBO<0.3 with more data, intrabar-realistic fills, cost stress, stability, paper | Medium |
| **2b alt) Stocks/ETFs: low-fee trend/TAA** | Deep history, low fees/turnover, regime-aware diversifier | Net-of-cost risk-adjusted outperformance, MDD control | Medium |

**Recommendation:** **Crypto TSMOM + Crypto VWAP-MR core** as primary 1–2; **Equity/ETF TAA** in parallel.

## 3. Mutual Funds — Highest Probability, Least Money-In / Lowest Fees / Least Capital
**Caveat:** MF infra exists (`alpha_engine/data/mutual_fund_metadata.csv`, `mutual_fund_ranker.py`, `fund_holdings_deriver.py`, WF/rankings) but **no wired, live, proven allocation class**. Low-cost index funds offer structural cost advantage — **not guaranteed alpha**.

**Criteria:** $0 min initial, no load, no 12b-1, ER ≤0.20% (prefer ≤0.05%), broad/liquid, large AUM/track record.

| Ticker | Fund | Category | ER | Min | Load/12b-1 | Note |
|---|---|---|---:|---:|---|---|
| **FXAIX** | Fidelity 500 Index | US Large Blend | **0.015%** | **$0** | 0/0 | Core US, lowest ER |
| **FSKAX** | Fidelity Total Market Index | US Total Market | **0.015%** | **$0** | 0/0 | Broadest US; T2 (79.0) |
| **SWPPX** | Schwab S&P 500 Index | US Large Blend | **0.02%** | **$0** | 0/0 | **T1 (87.1)** |
| **SWTSX** | Schwab Total Stock Market Index | US Total Market | **0.03%** | **$0** | 0/0 | Broad US |
| **FSMDX** | Fidelity Mid Cap Index | US Mid Cap | **0.025%** | **$0** | 0/0 | Diversifier |
| **FSSNX** | Fidelity Small Cap Index | US Small Cap | **0.025%** | **$0** | 0/0 | Diversifier |
| **FXNAX** | Fidelity US Bond Index | US Agg Bond | **0.025%** | **$0** | 0/0 | Low-fee ballast |
| **FSGGX** | Fidelity Global ex-US Index | Intl Dev | **0.055%** | **$0** | 0/0 | Intl diversification |
| **SWISX** | Schwab International Index | Intl Dev | **0.06%** | **$0** | 0/0 | Intl developed |

*Vanguard Admiral (e.g. VFIAX/VTSAX ~0.04% ER) are low-fee but often $3,000 min — exclude from least-capital tier.*

**Approach:** baseline low-cost buy-hold/rebalance of subset; **validate** trend/TAA/risk-on-off overlay (NAV walk-forward, next-NAV fills, net-of-fee, paper). Benefit stated as **cost/capital efficiency**, not guaranteed alpha.

## 4. Focus Statement
1. **P0:** fix integrity & CI. 2. **Validate/paper beyond MF:** **Crypto TSMOM + VWAP-MR core** (+ **Equity/ETF TAA**). 3. **Wire/validate low-capital/low-fee MF allocation** (FXAIX/FSKAX/SWPPX/SWTSX/FXNAX core) — promote only with evidence.
