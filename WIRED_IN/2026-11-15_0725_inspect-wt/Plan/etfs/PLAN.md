# Pre-Registered Experiment Plan — ETFs (`E1_ETF_DualMom_VolTarget`)

- **Trial ID:** `E1` (`Plan/etfs/PLAN.md`)
- **Gap Filled (citing `00_inventory.csv` / `harvested_ideas/etfs.md`):** Prior ETF attempts failed on short holding periods (`tools/per_class_cost_gate.py`: `267%` cost/PnL) and missing `yfinance` deps (`requirements.txt`). While `final_v4/inspect-wt/03_risk_management/backtest_rotation.py` tested `v1-v4` returns, it lacked **10-step proof validation** (circular block bootstrap, 200-run permutation shuffle control, WFO parameter neighborhood heatmap, Bull/Bear/Sideways × Vol regime decomposition, DSR at `N=9`/`N=646`, and Canadian tax friction).
- **Hypothesis:** A monthly 12-1 dual-momentum ETF rotation with inverse-12m-volatility weighting and a 12% annual volatility target outperforms `60/40 SPY/AGG` on risk-adjusted return (Sharpe, Calmar, MaxDD) and cuts `SPY B&H` crash drawdown by $\ge 20\%$, surviving costs, regime splits, and shuffle nullification.
- **Data Source:** `final_v4/inspect-wt/03_risk_management/yahoo_monthly.json` (11 tickers, 166 monthly closes `2013-01` → `2026-10`, SHA-256 hashed).
- **Universe:** `SPY, EFA, EEM, TLT, IEF, GLD, VNQ, DBC, QQQ, IWM` (cash earns `rf = 2.5%/yr`).
- **Timeframe & Cadence:** Monthly (`21` trading days; rebalance at month-end close $t-1$, held through month $t$, zero lookahead).
- **Method & Pre-Registered Parameter Grid (for WFO stability heatmap only):**
  - Lookback $L \in \{9, 12, 15\}$ months (primary pre-registered: `12-1`, i.e., `close[t-1] / close[t-13] - 1`).
  - Top-$K \in \{2, 3, 4\}$ assets above `rf` (primary: `K=2`), inverse-12m-vol weights capped at `50%`, 12% annual portfolio vol target (`s = min(1, 0.12 / trailing_12m_vol)`).
- **Cost & Canadian Tax Model:** `5 bps` one-way (`10 bps` round-trip turnover); Canadian non-registered cap-gains tax (`26.76%` Ontario top marginal at 50% inclusion on positive calendar realized gains) vs `0%` TFSA/RRSP.
- **Benchmarks:** `60/40 SPY/AGG` (monthly rebalanced) and `SPY Buy-and-Hold`.
- **Proof Standard Tests Targeted (§6):** All 10 steps (`Temporal`, `WFO`, `DSR N=9 & N=646`, `Plain + Block MC`, `Friction + Breakeven`, `Bootstrap CI & t-stat`, `Regime Split`, `200-run Shuffle Control`, `Tracker Registration`, `Seed=42 Reproducibility`).

