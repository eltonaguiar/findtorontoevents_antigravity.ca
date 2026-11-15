# Pre-Registered Experiment Plan — Mutual Funds (`M1_MutualFund_Sleeve_CAD_Tax`)

- **Trial ID:** `M1` (`Plan/mutual_funds/PLAN.md`)
- **Gap Filled (citing `00_inventory.csv` / `harvested_ideas/mutual_funds.md`):** Mutual funds (`mf_`, `mf2_` DB tables in `tools/recon_uncharted_tables.py`) never received a live emitter (`alpha_engine/mutual_fund_ranker.py` is absent) and cannot use intraday TP/SL picks because NAV prices once daily at 16:00 ET with 30-day frequent-trading penalties.
- **Hypothesis:** Applying the **monthly** 12-1 dual-momentum + inverse-vol allocation (`E1` base) via low-cost index mutual fund share classes (`0.15%/yr` institutional/DIY MER drag, zero short-term redemption fees due to $\ge 30$-day hold cadence) outperforms `60/40` net of fees in TFSA/RRSP accounts and preserves positive after-tax alpha vs. cash in Canadian taxable accounts—whereas `1.80%/yr` Canadian active retail MERs erode excess Sharpe below viability.
- **Data Source:** `final_v4/inspect-wt/03_risk_management/yahoo_monthly.json` (`2013-01` → `2026-10`, 166 months).
- **Universe:** Low-ER index mutual-fund share equivalents for US Large/Tech/Small (`SPY/QQQ/IWM`), Int'l/EM (`EFA/EEM`), Treasuries (`TLT/IEF`), Real Assets (`VNQ/GLD/DBC`).
- **Timeframe & Cadence:** Monthly forward-NAV close (`>= 30` calendar days between trades; 0 redemption violations).
- **Parameter Grid:** Primary `L=12-1, K=2, ER=0.15%/yr`; sensitivity sweep on MER `{0.15%, 0.50%, 1.80%/yr}` to quantify Canadian MER breakeven.
- **Cost & Canadian Tax Model:** `0 bps` explicit fund-switch commission on no-load D-series/F-series platforms + `0.15%/yr` MER drag `(1-0.0015)**(1/12)` + Canadian taxable (`26.76%` cap gains) vs `0%` TFSA/RRSP.
- **Benchmarks:** `60/40 SPY/AGG` and Risk-Free Cash (`2.5%/yr`).
- **Proof Standard Tests Targeted (§6):** All 10 steps (`Temporal`, `WFO`, `DSR`, `Plain + Block MC`, `Friction/MER Breakeven`, `Significance`, `Regime Split`, `Shuffle Control`, `Tracker`, `Reproducibility`).

