# Pre-Registered Experiment Plan — Multi-Asset (`MA1` & `MA2`)

- **Trial IDs:** `MA1` (`MA1_VariantC_MetaSelector`) and `MA2` (`MA2_MultiAsset_RiskParity_Combo`)
- **Gap Filled (citing `00_inventory.csv` / `harvested_ideas/multi_asset.md`):**
  - `MA1`: `final_2026_11_14/inspect-wt/06_profitable_approach/walkforward_v6.py` showed Variant C beats random strategy selection (`p < 0.0013`), but had **not** been passed through circular block bootstrap, Canadian tax & 2× friction stress, repo-wide `N=646` DSR, or permutation shuffle control on trade outcomes.
  - `MA2`: Directly tests **`negative_result_diagnosis.md` §5** ("Portfolio-Level Combination"): pooling weakly correlated sleeves ($\rho < 0.3$)—specifically `E1` (Equity/Multi-Asset Dual Momentum), `B1` (Bond Duration Rotation), `CM1` (Gold/Commodity Trend), and Cash—using inverse-volatility risk-parity weighting with cascaded DSR over both $N_{\text{new}}=9$ and $N_{\text{repo}}=646$.
- **Hypotheses:**
  - `MA1`: Monthly top-6 strategy selection (`train_n >= 20, train_PF > 1.3`, strictly prior months) outperforms a random strategy subset net of `10 bps` extra round-trip friction, though sample size (`7–8` OOS calendar months) classifies it as a Near-Miss until $\ge 60$ monthly/regime trades accumulate cleanly.
  - `MA2`: Combining 4 low-correlation sleeves (`E1`, `B1`, `CM1`, and `TLT/IEF` defensive carry) raises portfolio Sharpe and reduces Max Drawdown relative to individual sleeves and `60/40`, surviving cascaded DSR, block bootstrap, shuffle control, and all macro regimes.
- **Data Sources:** `live_dashboard_payload.json` (`3,500` closed rows `2026-02-21` → `2026-11-14`) for `MA1`; `yahoo_monthly.json` (`166` months `2013-01` → `2026-10`) for `MA2`.
- **Benchmarks:** Random 6-strategy selector + `0%` null (`MA1`); `60/40 SPY/AGG` & `SPY B&H` (`MA2`).
- **Proof Standard Tests Targeted (§6):** All 10 steps with explicit cascaded DSR calculation.

