# Harvested Ideas — ETFs

**Asset Class:** `ETF`  
**Inventory Coverage (`00_inventory.csv`):** `74` `EQUITY|ETF`, `71` `BOND|ETF`, `58` `FOREX|ETF` + `MULTI_ASSET` rotation scripts (`alpha_engine/asset_class.py:37-53`: broad `SPY/QQQ/IWM/DIA/VTI/VOO`, 11 sector SPDRs `XLB..XLU`, `EFA/EEM`, `VNQ/GLD/SLV/USO`, leveraged `SQQQ/TQQQ/UVXY`).

---

## 1. What Was Already Tried in the Repo
- **Short-Term ETF Technical Picks (`alpha_engine/`):** `rs-breakout-scout`, `donchian-stock-breakout`, `vwap-reversion-scout` firing on `SPY, QQQ, IWM, XLK` (`final_2026_11_14/inspect-wt` Variant C saw `ETF n=120, PF=1.21, +26.5pp`).
- **Kimi ETF Leads (`KIMI_INTEGRATION_STATUS.md:12`, `KIMI_STRATS_V3.MD:62-63`):** `etf_mom_rot_lb20_h*_vol_adj` (claiming `ci_low=2.513, MDD=-7.13%` on 180d window), Factor Crowding Rotation, Thematic ETF Flow Saturation Arbitrage.
- **Tactical / Dual-Momentum Allocation (`final_v4/inspect-wt/03_risk_management/backtest_rotation.py`, `tools/sim_path_forward.py`, `faber_dual_momentum_backtest.py`):**
  - `Faber 200d MA` (`2008–2026`): `CAGR=11.15%`, `Sharpe=1.01`, `MDD=-18.8%` vs `SPY B&H` (`CAGR=11.62%`, `Sharpe=0.79`, `MDD=-46.3%`).
  - `FABER10_SPY` (`2004–2026`): `CAGR=8.33%`, `Sharpe=0.66`, `MDD=-21.8%` vs `SPY B&H` (`10.76%`, `0.65`, `-50.8%`).
  - `166-month Rotation Sleeve v2 (12-1 mom + inv-vol + 12% vol target)`: `CAGR=8.6%`, `Sharpe=0.59`, `MDD=-19.9%` vs `60/40` (`7.3%`, `0.54`, `-21.0%`).
- **Managed Futures ETF Proxy (`updates/index.html:45`):** `DBMF`/`KMLM` daily paper pilot (`etf_managed_futures_proxy`).

## 2. Observed Results & Suspected Failure Modes
- **Canonical Live Active-Pick Verdict (`TESTING_PROTOCOL.MD:26`):** `ETF` (`n=4, WR=50.0%, PF=0.476` -> `INSUFFICIENT_DATA`). `tools/per_class_cost_gate.py:8` flagged ETF cost/PnL ratio at **267%** on short-horizon active picks!
- **Failure Modes:** #4 High Turnover Cost on Short Holds (267% cost/PnL), #7 Missing `yfinance` Dependency (`requirements.txt:21` starved ETF emitters), #9 Failing to Beat `SPY` Total Return in Secular Bulls (while excelling on crash drawdown).

## 3. Research Gap for Phase 3 (`Plan/etfs/PLAN.md`)
- Run the complete **10-step Proof Standard + Phase 5 Metric Suite** on **Candidate `E1_ETF_DualMom_VolTarget`** (10-ETF `SPY/EFA/EEM/TLT/IEF/GLD/VNQ/DBC/QQQ/IWM`, 12-1 momentum > `rf`, inverse-12m vol weights, 12% vol target) over **166 real monthly closes (2013–2026)**, explicitly adding **walk-forward parameter sweeps, 2,000-path circular block bootstrap, 200-run price permutation shuffle control, Bull/Bear/Sideways & High/Low Vol regime splits, DSR at $N=9$ and $N=646$, and Canadian TFSA vs. Non-Registered Capital-Gains tax drag**.

