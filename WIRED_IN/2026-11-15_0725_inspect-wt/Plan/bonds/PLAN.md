# Pre-Registered Experiment Plan — Bonds (`B1_Bond_Duration_Rotation`)

- **Trial ID:** `B1` (`Plan/bonds/PLAN.md`)
- **Gap Filled (citing `00_inventory.csv` / `harvested_ideas/bonds.md`):** Prior bond scripts (`audit_dashboard/data/bond_duration_rotation_backtest.json` using `^TNX-^FVX`, `bond_connors_rsi2_backtest.json`, `bond_hyg_lqd_v1.json`) were one-shot static runs without circular block bootstrap, 200-run permutation shuffle control, DSR at `N=9`/`N=646`, WFO parameter stability sweeps, or Canadian fixed-income ordinary-interest tax friction. Meanwhile `live_dashboard_payload.json` shows only `n=35` closed `BOND` picks (`TESTING_PROTOCOL.MD`: live `BOND n=0` at freeze, 2026-06-04 backfill contamination).
- **Hypothesis:** Causal monthly 12-1 dual-momentum duration rotation over liquid bond ETFs `{TLT, IEF, AGG}` with cash fallback (`rf = 2.5%/yr`) reduces catastrophic long-duration drawdown (2022 `TLT` rate-hike crash) vs. static `TLT` Buy-and-Hold and improves Calmar/MaxDD vs. static `AGG`, though low bond volatility limits excess return over `rf` after Canadian interest/cap-gains friction.
- **Data Source:**
  - Primary bar-level backtest: `final_v4/inspect-wt/03_risk_management/yahoo_monthly.json` (`TLT, IEF, AGG`, 181 raw closes `2011-12` → `2026-11`, producing `166` full closed OOS months `2013-01` → `2026-10`).
  - Live cohort cross-check: `live_dashboard_payload.json` (`BOND` closed picks, `n=35`).
- **Universe & Timeframe:** Monthly (`21` trading days; signal computed at month `t-1`, held through month `t`, zero lookahead).
- **Signal Construction & Pre-Registered Parameter Grid:**
  - Lookback `L in {6, 9, 12}` months (primary pre-registered: `L=12`, skip 1 month: `close[t-1] / close[t-13] - 1`).
  - Top-`K in {1, 2}` bond ETF with highest positive `L`-month excess return over `rf` (`(1+0.025)^(L/12)-1`); otherwise `100%` cash earning `rf = 2.5%/yr`. Optional vol-cap scalar `min(1, 0.10 / trailing_12m_vol)`.
- **Cost & Canadian Tax Model:** `5 bps` one-way (`10 bps` round-trip turnover); Canadian non-registered cap-gains `26.76%` on positive calendar ETF turnover gains AND `53.53%` sensitivity on ordinary coupon/cash interest yields vs. `0%` TFSA/RRSP.
- **Benchmarks:** `AGG` Buy-and-Hold (core aggregate bond benchmark) and `TLT` Buy-and-Hold (long duration benchmark).
- **Pre-Registered Failure Criteria:** Fail if post-cost WFO Sharpe does not clear `DSR >= 0.95` at `N=9` and `N=646`, OR block-bootstrap 95% CI of excess return over `rf` spans zero, OR shuffle control p-value `>= 0.05`.
- **Proof Standard Tests Targeted (§6):** All 10 steps (`Temporal`, `WFO`, `DSR N=9 & N=646`, `Plain + Block MC`, `Friction + Breakeven`, `Bootstrap CI & t-stat`, `Regime Split`, `200-run Shuffle Control`, `Tracker Registration`, `Seed=42 Reproducibility`).

