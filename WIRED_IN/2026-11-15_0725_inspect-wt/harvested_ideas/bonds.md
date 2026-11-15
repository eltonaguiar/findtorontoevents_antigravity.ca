# Harvested Ideas — Bonds / Fixed Income

**Asset Class:** `BOND` (Treasuries, Investment Grade, TIPS, Credit)  
**Inventory Coverage (`00_inventory.csv`):** `71` `BOND|ETF` files + bond-specific scripts (`requirements-bond-data.txt`, `reports/bond_n_ramp_analysis_2026-06-05.md`, `alpha_engine/asset_class.py:28-35` defining 14 `BOND_SYMBOLS`: `TLT, IEF, SHY, LQD, AGG, BND, HYG, JNK, SJNK, BKLN, EMB, TIP, MUB, IGIB`).

---

## 1. What Was Already Tried in the Repo
- **Duration & Credit Scanners:** Basic technical picks emitted on `TLT`, `IEF`, `AGG`, `BND`, `SGOV` (`live_pnl_tracker.py` showed daily re-inserts of always-on `SGOV/BND/TLT` picks).
- **Kimi Fixed-Income Research (`KIMI_STRATS_V3.MD:27-28`):** Agency MBS Prepayment Speed Momentum, SOFR Futures Term Structure Carry, PIMCO-style yield-curve momentum / `TLT-IEF` mean reversion (`updates/index.html:90`).
- **Asset-Class Normalization Fix:** `alpha_engine/asset_class.py:51-52` separated `BOND_SYMBOLS` (`TLT, IEF, ...`) ahead of `ETF_SYMBOLS` so bond ETFs weren't misclassified as equity ETFs.
- **Rotation Engine (`final_v4/inspect-wt/03_risk_management/backtest_rotation.py`):** Included `TLT`, `IEF`, and `AGG` as defensive/60-40 benchmark sleeves.

## 2. Observed Results & Suspected Failure Modes
- **Canonical Live Readiness (`TESTING_PROTOCOL.MD:28`):** `BOND` (`n=0` clean resolved picks as of 2026-05-31). Live `updates/index.html:90` notes 159 / 167 closed trades were `2026-06-04` backfill contamination; real pre-backfill was 16 trades in 3 months. Live Nov 2026 14d recompute showed `BOND PF = 0.05` (`memory/2026-11-14.md:27`).
- **Silent Dependency Bug (`requirements.txt:18-22`):** `yfinance` was undeclared, causing bond scanners in CI to crash with `ImportError` and emit **0 picks**.
- **Failure Modes:** #8 Insufficient Sample Size ($n=18\text{--}35$ live vs $n \ge 100$ floor; structural slow-cadence asset), #7 Implementation Gap (`yfinance` missing + always-on duplicate inserts), #2 Backfill Contamination (`2026-06-04`).

## 3. Research Gap for Phase 3 (`Plan/bonds/PLAN.md`)
- Replace intraday/short-term TP/SL bond picks with a **166-month (2013–2026) Duration & Yield-Regime Rotation (`TLT` / `IEF` / `Cash` at 2.5% `rf`)** evaluated against **`AGG` Buy-and-Hold** and **T-Bill Cash**, measuring whether lagged 12-1 duration momentum beats `AGG` after **0.05% one-way cost + Canadian interest/capital-gains tax**, and checking **Sample-Size / Monte Carlo significance** (honestly classifying `B1` if $n$ months is too short to statistically beat `AGG` on Sharpe).

