# Harvested Ideas — Commodities & Futures

**Asset Class:** `COMMODITY` / `FUTURES`  
**Inventory Coverage (`00_inventory.csv`):** `56` pure `COMMODITY_FUTURES` files, `137` `CRYPTO|COMMODITY_FUTURES`, `116` `FOREX|COMMODITY_FUTURES` (`alpha_engine/asset_class.py:62-69`: `GC, SI, HG, PL, PA, ALI, CL, NG, HO, RB, ZC, ZS, ZW, KC, SB, CC, CT, XAUUSD, XAGUSD`).

---

## 1. What Was Already Tried in the Repo
- **COT & Managed Futures Scanners:** `multi_asset_cot`, `futures_bb_mean_reversion`, `cta_cross_asset_tsmom`, `combined_confidence_strategy`, `etf_managed_futures_proxy` (`DBMF`/`KMLM` daily paper pilot in `updates/index.html:45`).
- **Oil Futures Removal:** `alpha_engine/config.py:19` notes `"OIL": "CL=F"` was explicitly commented out after **26 futures trades produced `3.8% WR, -29.82% PnL`** ("worse than random").
- **Kimi Commodity Research (`KIMI_STRATS_V3.MD:26`, `KIMI_INTEGRATION_STATUS.md:14`):** Gold Lease Squeeze Capture, 300d commercial COT direction, seasonal spreads.

## 2. Observed Results & Suspected Failure Modes
- **Canonical Live Readiness (`TESTING_PROTOCOL.MD:23,25`):** `COMMODITY` (`n=7, WR=57.1%, PF=3.870` -> `INSUFFICIENT_DATA`, gold concentration `57.1%` single-source); `FUTURES` (`n=12, WR=16.7%, PF=0.536`, `91.7%` single-source -> `INSUFFICIENT_DATA`).
- **Backfill Artifact (`updates/index.html:88`):** `reports/deep_dive_commodity_2026-06-05.md` revealed **5,960 commodity rows on `2026-06-04` were resolver backfill**, wiping out all commodity T2 candidates (`0/6` post-filter).
- **422% Cost-to-PnL Blowout (`tools/per_class_cost_gate.py:9`):** Modelled round-trip transaction costs were **422%** of average trade PnL for `COMMODITY` and **72%** for `FUTURES`.
- **COT Re-Test Failure:** `memory/2026-11-15.md` & `ELIMINATION_RATIONALE.md:47` document that the **COT feature test failed 4/4** when audited cleanly.
- **Failure Modes:** #4 Cost & Roll-Yield Blindness (continuous futures omit roll cost), #2 Backfill Artifact (`2026-06-04`), #3 Single-Asset Concentration (`GC`/Gold), #8 Small Clean $N$.

## 3. Research Gap for Phase 3 (`Plan/commodities/PLAN.md`)
- Test **Candidate `CM1_Commodity_Gold_Trend`** — a simple, parameter-free **12-1 Absolute Momentum Trend on `GLD` & `DBC`** (spot gold proxy + broad commodity basket proxy) with an **explicit `50 bps/yr` futures roll-yield + contango friction penalty on `DBC`** and `0.05%` rebalancing cost, measured against **50/50 `GLD/DBC` Buy-and-Hold** across all 10 proof steps (`yahoo_monthly.json`, 2013–2026).

