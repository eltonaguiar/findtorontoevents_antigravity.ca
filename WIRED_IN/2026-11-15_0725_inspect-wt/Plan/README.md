# Pre-Registered Experiment Plans (`Plan/`) — Governance & Reuse Registry

**Protocol Rule:** Per §3 of the Self-Engineering Protocol, **no full backtest runs before a pre-registered `PLAN.md` exists** for every asset class. Each plan below documents the exact hypothesis, inventory gap cited from `harvested_ideas/00_inventory.csv`, method, verified local dataset, timeframe, universe, parameter bounds, realistic friction + Canadian tax model, benchmark, and pass/fail gates across the 10-step proof standard.

---

## Reused Existing Repo Plans (No Duplication)

Rather than duplicating prior planning artifacts, this folder inherits and extends:
- `plans/stronger_algorithms_plan.md`, `plans/crypto_strategy_plan.md`, `plans/money_ready_enhancements_spec.md`
- `2026-11-14＊7PM＊plan/inspect-wt/01_plan_per_asset_class/*.md` (benchmark-relative gates)
- `2026-11-15_AM_plan/finpredict-v4/01_per_asset_class_plans/PER_ASSET_CLASS_PLANS.md`
- `2026-11-15_AM_profitability_plan/parallel_agent_worktree/01_asset_class_plans/plan_per_asset_class.md`

---

## Registered Trial Ledger (Pre-Registered Multiple-Testing Budget)

All **9 new simulation runs** below are registered in `experiments/experiment_configs.json` *before* inspecting output metrics, and are tested against both **`N_new = 9`** and the **`N_repo = 646`** repo-wide strategy count (`361` families + `285` baby strategies):

| Trial ID | Asset Class | Candidate Name | Reused Local Dataset | Benchmark |
|---|---|---|---|---|
| **E1** | `etfs` | `E1_ETF_DualMom_VolTarget` | `yahoo_monthly.json` (166m, 2013-01→2026-10) | `60/40 SPY/AGG` & `SPY B&H` |
| **M1** | `mutual_funds` | `M1_MutualFund_Sleeve_CAD_Tax` | `yahoo_monthly.json` (MF 0.15% ER + CAD tax) | `60/40` & Cash (`rf=2.5%`) |
| **MA1** | `multi_asset` | `MA1_VariantC_MetaSelector` | `live_dashboard_payload.json` (3,500 closed) | Random 6-strat selector + 0% |
| **MA2** | `multi_asset` | `MA2_MultiAsset_RiskParity_Combo` | `yahoo_monthly.json` (uncorrelated 4-sleeve RP) | `60/40 SPY/AGG` & `SPY B&H` |
| **S1** | `stocks` | `S1_Equity_Active_Picks_Cohort` | `live_dashboard_payload.json` (EQUITY+ETF rows) | `SPY B&H` matched window |
| **C1** | `crypto` | `C1_Crypto_Funding_And_Trend` | `BTCUSDT_3mo_1h.csv` + `funding_rate_archive/` | `BTC B&H` (1h/daily) |
| **B1** | `bonds` | `B1_Bond_Duration_Rotation` | `yahoo_monthly.json` (`TLT, IEF, AGG`) | `AGG B&H` |
| **CM1** | `commodities` | `CM1_Commodity_Gold_Trend` | `yahoo_monthly.json` (`GLD, DBC`) + roll drag | `50/50 GLD/DBC B&H` |
| **FX1** | `forex` | `FX1_Forex_Spread_Adjusted` | `live_dashboard_payload.json` (FOREX rows) | Cash + Retail Spread Null |

