# 2026-11-15 — WIRED_IN Multi-Asset Quant Audit, 10-Step Proof Suite & Repo Archaeology

## Summary
Executed a full Phase 0–7 quantitative audit and 10-step proof protocol across all 8 asset classes (`Stocks, Crypto, Forex, Bonds, ETFs, Mutual Funds, Commodities, Multi-Asset`) on `origin/main`, storing all artifacts in `WIRED_IN/2026-11-15_0725_inspect-wt/`.

## What Was Built & Verified
1. **Repository Archaeology (`harvested_ideas/`):**
   - Built [repo_miner.py](file:///e:/findtorontoevents_antigravity.ca/WIRED_IN/2026-11-15_0725_inspect-wt/harvested_ideas/repo_miner.py) and mined `11,821` of `44,800` tracked files on `origin/main` into `00_inventory.csv` (`6,639` categorized rows) and `dependencies_summary.json` (`30` manifests, `120` unique packages).
   - Compiled [01_failures_taxonomy.md](file:///e:/findtorontoevents_antigravity.ca/WIRED_IN/2026-11-15_0725_inspect-wt/harvested_ideas/01_failures_taxonomy.md), [02_methods_catalogue.md](file:///e:/findtorontoevents_antigravity.ca/WIRED_IN/2026-11-15_0725_inspect-wt/harvested_ideas/02_methods_catalogue.md), and all 8 asset-class harvests plus pre-registered `Plan/<asset_class>/PLAN.md` specifications.
2. **Seeded 10-Step Non-Negotiable Proof Suite (`experiments/run_proof_suite.py`, `SEED=42`):**
   - Verified clean execution (exit `0`) producing [experiment_results.json](file:///e:/findtorontoevents_antigravity.ca/WIRED_IN/2026-11-15_0725_inspect-wt/experiments/experiment_results.json), [PROOF_SUMMARY_TABLE.md](file:///e:/findtorontoevents_antigravity.ca/WIRED_IN/2026-11-15_0725_inspect-wt/proof/PROOF_SUMMARY_TABLE.md), WFO fold/heatmap sweeps, `2,000`-path plain & circular block bootstrap CIs, `DSR(N=9 & N=646)`, White's Reality Check, Holm-Bonferroni, Canadian tax (`0%` TFSA vs `26.76%` Cap Gains vs `53.53%` Ordinary), `Bull/Bear/Sideways x High/Low Vol` regimes, and `200`-run permutation shuffle controls.
   - **Verified Results (`0 / 9` `PROVEN`):**
     - `M1` (`Mutual Funds` `12-1` `0.15%` MER) and `E1` (`ETFs` `12-1` `10 bps` RT): **`PROMISING (NEAR-MISS)`** (`7/10` gates; Net CAGR `+7.49%` / `+7.31%`, Sharpe `0.450` / `0.436`, Block MC `93.5%` / `91.6%` positive, WFE `3.50` / `3.83`, yet `t=1.67/1.62`, `DSR_646=0.029/0.026`, `Shuffle p=0.655` vs `SPY_BH +12.82%` / `60-40 +7.31%`).
     - `CM1` (`GLD/DBC` Monthly): **`REJECT`** (`7/10` gates, `+9.08%` net, Sharpe `0.593`, `PF 1.99`, **`Shuffle p=0.0050`**, failed pre-registered IS WFO due to `2013-2019` commodity bear `IS Sharpe -0.403`).
     - `MA2` (`3.99%` net, `0.269` Sharpe), `MA1` (`Variant C`, `n=237`, `p_random=0.055`, `5/10`), `S1` (`EQUITY`, IS `+2.43` -> OOS `-0.694`, `5/10`), `B1` (`+0.74%` net, `-0.203` Sharpe, `5/10`), `C1` (`-24.93%` CAGR, `-2.58` Sharpe; live `1,966` picks `-0.551%/trade` net; OKX BTC funding `+0.29%/yr` net), `FX1` (`-1.04%` CAGR, `-1.965` Sharpe, `breakeven 4.2 bps < 8.0 bps`, `19` `EURUSDT` leaks): all **`REJECT`**.
3. **Multi-Horizon Tracker & Governance Reports:**
   - Built [build_tracker.py](file:///e:/findtorontoevents_antigravity.ca/WIRED_IN/2026-11-15_0725_inspect-wt/tracker/build_tracker.py) -> generated `predictions_tracker.csv` (`69` rows across `<=1d`, `1d-3mo`, `>3mo`) and Tufte-styled `predictions_tracker.html`.
   - Authored [Summary.MD](file:///e:/findtorontoevents_antigravity.ca/WIRED_IN/2026-11-15_0725_inspect-wt/Summary.MD), [AUDIT_REPORT.md](file:///e:/findtorontoevents_antigravity.ca/WIRED_IN/2026-11-15_0725_inspect-wt/AUDIT_REPORT.md), [STRATEGY_SHORTLIST.md](file:///e:/findtorontoevents_antigravity.ca/WIRED_IN/2026-11-15_0725_inspect-wt/STRATEGY_SHORTLIST.md), [PROOF_PROTOCOL.md](file:///e:/findtorontoevents_antigravity.ca/WIRED_IN/2026-11-15_0725_inspect-wt/PROOF_PROTOCOL.md), and [negative_result_diagnosis.md](file:///e:/findtorontoevents_antigravity.ca/WIRED_IN/2026-11-15_0725_inspect-wt/negative_result_diagnosis.md).

## Verification Commands
- `python WIRED_IN/2026-11-15_0725_inspect-wt/harvested_ideas/repo_miner.py --scan-root e:\findtorontoevents_antigravity.ca\.fix-wt` -> exit `0` (`11,821` files scanned, `6,639` inventory rows, `30` manifests).
- `python WIRED_IN/2026-11-15_0725_inspect-wt/experiments/run_proof_suite.py` -> exit `0` (all 9 strategies + 7 benchmarks evaluated, `SEED=42`).
- `python WIRED_IN/2026-11-15_0725_inspect-wt/tracker/build_tracker.py` -> exit `0` (`69` rows CSV, `33,696` bytes HTML).
