# 09 — Backtest/Simulation Plan, Execution, and Results

**Generated (UTC):** 2026-11-15T00:41:10.737748+00:00  
**Type:** model-based simulations (GBM + regime-switching toy), deterministic seed `20261115`.  
**Claim level:** demonstrates *plausible* backtest/simulation behavior under stated assumptions; **not** proof of live profitability or future performance.

## 1. Plan (created & executed)

| # | Simulation | Purpose | Output |
|---|---|---|---|
| 1 | Equity buy-and-hold proxy (SPY-like) | Benchmark / beta path | CAGR, Sharpe, MDD, P(positive), P(beat cash) |
| 2 | 60/40 balanced (monthly rebalance, low cost) | Risk-managed core allocation path | same metrics + vs equity |
| 3 | Bonds defensive proxy | Ballast behavior | same metrics |
| 4 | Dual-momentum toy (regime-switching) | Show drawdown control logic vs B&H in trend/crash regimes | median CAGR/MDD, MDD-improved share |
| 5 | Net-of-cost sensitivity grid | Prove marginal gross edges die after realistic costs | expectancy/PF_net by WR/PF/cost bps |

**Execution:** `python3 09_backtest_simulations/run_simulations.py` (stdlib only). Artifacts: `simulation_results.json`, `simulation_summary.csv`, `cost_sensitivity.csv`.

## 2. Core results (2000 paths, 10y horizon, RF=3%)

| Strategy | Median CAGR | P10/P90 CAGR | Median Sharpe | Median MDD | Worst-decile MDD | P(>0) | P(beat cash 3%) |
|---|---:|---:|---:|---:|---:|---:|---:|
| Equity B&H proxy (mu 9%, vol 15%, 5bps cost) | 6.95% | 0.77% / 13.37% | 0.34 | -29.45% | -43.09% | 92.20% | 78.70% |
| 60/40 equity/bonds rebalance monthly (5bps cost) | 5.99% | 2.11% / 10.14% | 0.37 | -17.68% | -26.16% | 97.45% | 83.15% |
| Bonds defensive proxy (mu 4%, vol 5%) | 3.76% | 1.61% / 5.89% | 0.18 | -9.16% | -13.98% | 98.80% | 67.70% |

### 2b. Dual-momentum toy (model regime test)

- Buy&Hold risky median CAGR 7.26%, median MDD -42.30%
- Dual-momentum median CAGR 12.96%, median MDD -18.15%
- MDD improved vs B&H in 99.70% of paths; positive-CAGR share 100.00%

## 3. Net-of-cost sensitivity (active strategies)

- Scenarios tested: 80; net-negative: 59. Marginal gross edges (PF<=1.1 or WR<=50%) frequently turn net-negative at 10-30bps RT costs.
- Example (gross PF 1.10, WR 50%, 20bps RT): expectancy turns negative / PF_net < 1 in grid — **costs erase marginal edges**.

| Gross WR | Gross PF | RT cost (bps) | Exp gross (R) | Exp net (R) | PF_net | Net>0 |
|---:|---:|---:|---:|---:|---:|:---:|
| 0.45 | 1.10 | 5 | 0.055 | 0.005 | 1.009 | Y |
| 0.45 | 1.10 | 10 | 0.055 | -0.045 | 0.926 | N |
| 0.45 | 1.10 | 20 | 0.055 | -0.145 | 0.780 | N |
| 0.45 | 1.10 | 30 | 0.055 | -0.245 | 0.657 | N |
| 0.45 | 1.30 | 5 | 0.165 | 0.115 | 1.199 | Y |
| 0.45 | 1.30 | 10 | 0.165 | 0.065 | 1.107 | Y |
| 0.45 | 1.30 | 20 | 0.165 | -0.035 | 0.947 | N |
| 0.45 | 1.30 | 30 | 0.165 | -0.135 | 0.811 | N |
| 0.45 | 1.50 | 5 | 0.275 | 0.225 | 1.390 | Y |
| 0.45 | 1.50 | 10 | 0.275 | 0.175 | 1.289 | Y |
| 0.45 | 1.50 | 20 | 0.275 | 0.075 | 1.114 | Y |
| 0.45 | 1.50 | 30 | 0.275 | -0.025 | 0.965 | N |
| 0.50 | 1.10 | 5 | 0.050 | 0.000 | 1.000 | N |
| 0.50 | 1.10 | 10 | 0.050 | -0.050 | 0.909 | N |
| 0.50 | 1.10 | 20 | 0.050 | -0.150 | 0.750 | N |
| 0.50 | 1.10 | 30 | 0.050 | -0.250 | 0.615 | N |
| 0.50 | 1.30 | 5 | 0.150 | 0.100 | 1.190 | Y |
| 0.50 | 1.30 | 10 | 0.150 | 0.050 | 1.091 | Y |
| 0.50 | 1.30 | 20 | 0.150 | -0.050 | 0.917 | N |
| 0.50 | 1.30 | 30 | 0.150 | -0.150 | 0.769 | N |
| 0.50 | 1.50 | 5 | 0.250 | 0.200 | 1.381 | Y |
| 0.50 | 1.50 | 10 | 0.250 | 0.150 | 1.273 | Y |
| 0.50 | 1.50 | 20 | 0.250 | 0.050 | 1.083 | Y |
| 0.50 | 1.50 | 30 | 0.250 | -0.050 | 0.923 | N |

## 4. Interpretation (honest)

- **Core path supported in simulation:** low-cost diversified 60/40 shows high P(>0) and P(beat cash) with substantially smaller median/worst-decile MDD than equity-only — consistent with a **risk-managed beta/ballast** approach (not prediction alpha).
- **TAA/absolute-momentum logic** can reduce drawdowns in trend/crash-like regimes in-model; real-world benefit depends on costs, whipsaw, and regime behavior (must be forward-validated vs buy-and-hold benchmark).
- **Active sleeves**: without verified gross edge and strict cost control, net expectancy is fragile. This reinforces: fix measurement/fills/costs, then demand net benchmark-relative proof.

## 5. What this does NOT prove

- No guarantee of live profitability, no validated alpha for repo strategies, no bypass of OOS/DSR/PBO/forward gates. Assumptions (mu/sigma/correlations/costs/regimes) may not match future markets. Outperforming SPY/buy-and-hold in reality remains an empirical question requiring forward, net, benchmark-relative evidence.

## 6. Next steps

- Run on **trusted, reconciled historical data** (canonical cohort) once measurement/QA is fixed; compare vs SPY total return net of costs.
- Apply forward-test tracking protocol (`10_forward_test_protocol/FORWARD_TEST_TRACKING_PROTOCOL.md`) with kill/hold rules.
