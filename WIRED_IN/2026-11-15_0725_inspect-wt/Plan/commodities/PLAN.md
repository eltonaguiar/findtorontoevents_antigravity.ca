# Pre-Registered Experiment Plan — Commodities (`CM1_Commodity_Gold_Trend`)

- **Trial ID:** `CM1` (`Plan/commodities/PLAN.md`)
- **Gap Filled (citing `00_inventory.csv` / `harvested_ideas/commodities.md`):** Prior commodity attempts collapsed due to crude oil blowups (`OIL` blacklisted at `3.8%` WR, `-29.82%` PnL in `alpha_engine/config.py`), proxy carry approximations (`audit_dashboard/data/commodity_carry_momo.json`: rolling-mean diff substituting for front/second-month roll), and `2026-06-04` backfill contamination (`5,960` rows). None were tested under strict OOS dual-momentum + vol-targeting + 200-run permutation shuffle + Canadian tax friction.
- **Hypothesis:** A causal monthly 12-1 dual-momentum trend selector on liquid commodities `{GLD, DBC}` with cash floor (`rf = 2.5%/yr`) and `12%` annual vol target outperforms passive `DBC` Buy-and-Hold on Calmar and MaxDD, while testing strictly whether Gold/broad-commodity trend survives `DSR(N=646)`, block bootstrap, and shuffle nullification.
- **Data Source:**
  - Primary bar-level backtest: `final_v4/inspect-wt/03_risk_management/yahoo_monthly.json` (`GLD, DBC`, `166` full closed OOS months `2013-01` → `2026-10`).
  - Live cohort cross-check: `live_dashboard_payload.json` (`COMMODITY` closed picks, `n=7` — flagged for severe sample scarcity).
- **Universe & Timeframe:** Monthly (`21` trading days; signal on month `t-1`, held through month `t`).
- **Signal Construction & Pre-Registered Parameter Grid:**
  - Lookback `L in {9, 12, 15}` months (primary: `12-1`, i.e., `close[t-1] / close[t-13] - 1`).
  - Volatility target `VT in {0.10, 0.12, 0.15}` (primary: `12%` annualized trailing 12m vol scalar capped at `1.0`).
  - Hold top-1 (`K=1`) between `{GLD, DBC}` if `mom_L > rf_L`, else `100%` cash at `rf = 2.5%/yr`.
- **Cost & Canadian Tax Model:** `10 bps` one-way (`20 bps` round-trip reflecting wider commodity/DBC spreads + ETF MER drift sensitivity); Canadian non-registered `26.76%` cap gains vs `0%` TFSA/RRSP.
- **Benchmarks:** `DBC` Buy-and-Hold and `GLD` Buy-and-Hold.
- **Pre-Registered Failure Criteria:** Reject profitability claim if DSR `< 0.95` at `N=646`, OR excess return over `rf` fails `p < 0.05` after block bootstrap, OR strategy fails to outperform `GLD` Buy-and-Hold risk-adjusted net of friction and taxes.
- **Proof Standard Tests Targeted (§6):** All 10 steps (`Temporal`, `WFO`, `DSR N=9 & N=646`, `Plain + Block MC`, `Friction + Breakeven`, `Bootstrap CI & t-stat`, `Regime Split`, `200-run Shuffle Control`, `Tracker Registration`, `Seed=42 Reproducibility`).

