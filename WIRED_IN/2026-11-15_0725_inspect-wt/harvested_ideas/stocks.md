# Harvested Ideas — Stocks / Equities

**Asset Class:** `EQUITY` (and `PENNY_STOCK`)  
**Inventory Coverage (`00_inventory.csv`):** `279` pure `EQUITY` files, `197` `CRYPTO|EQUITY`, `74` `EQUITY|ETF` (`550+` files total).

---

## 1. What Was Already Tried in the Repo
- **Technical & Breakout Scanners (`alpha_engine/`):** `rs-breakout-scout`, `donchian-stock-breakout`, `vwap-reversion-scout`, `mtf-align-scout`, `momentum-factor`, `regime_terminal` (`alpha_engine/config.py:27-42`, `DEFAULT_UNIVERSE` of 35 mega-cap US equities + 3 ETFs; `DIVIDEND_ARISTOCRATS` of 20 stocks).
- **PEAD / Earnings & Fundamental Factors:** `alpha_engine/features/earnings_features.py`, `alpha_engine/features/valuation.py`, `alpha_engine/features/fundamental.py`, `updates/index.html:58` (`data/earnings/*/latest.json` PEAD shadow via `equity_earnings_loader`, enforcing `max_age_days=14`).
- **Kimi Equity Research:** `KIMI_STRATS_V3.MD:71-120` (Sloan Accrual Quality Factor, Opportunistic Insider Cluster Alpha), `KIMI_INTEGRATION_STATUS.md:11` (`EarningsMomentumV1_6GateLead` and `SupportBounceV1_6GateLead` on penny stocks).
- **Connors RSI(2) & Bollinger Mean Reversion:** `2026-11-15_AM_profitability_plan/.../SIMULATION_RESULTS.md` and `WIRED_IN/2026-11-15_0128_buffy/BACKTEST_AND_RESEARCH.md`.

## 2. Observed Results & Suspected Failure Modes
- **Canonical Live Readiness:** `TESTING_PROTOCOL.MD:21` reports `EQUITY`: `n_resolved=43, WR=30.2%, PF=0.156, MDD=98.2%` (`INSUFFICIENT_DATA`). `PENNY_STOCK`: `n=1, WR=0%, PF=0.0` (`INSUFFICIENT_DATA`).
- **Benchmark Gate Failure (`NO_ALPHA_BETA`):** PR `#773` / `alpha_engine/validation/run_equity_edge_test.py` showed live equity picks had $t = 1.05$, median pick `-0.57%` vs `SPY`, with `54%` underperforming `SPY` buy-and-hold.
- **Post-2020 RSI(2) Breakdown:** `RSI2_MeanReversion` over 2020–2025 lost `-118%` to `-186%` across SPY/QQQ/IWM (`QQQ WR=8.51%, PF=0.022`); `RSI2_SPY` over 2001–2026 yielded `CAGR=0.21%`, `excess=-2.30%`, `Sharpe=-0.64`.
- **Failure Modes:** #3 Survivorship bias (`DEFAULT_UNIVERSE` fixed in 2026), #6 Regime dependence (2020–2025 tech drift crushed mean-reversion shorts/longs), #9 Wrong objective (ignoring `SPY` beta), #8 Small sample (`n=43`).

## 3. Research Gap for Phase 3 (`Plan/stocks/PLAN.md`)
- Audit the **live active/closed equity cohort** (`live_dashboard_payload.json` `EQUITY` subset, $n \ge 100$ across `rs-breakout-scout`, `donchian-stock-breakout`, `vwap-reversion-scout`) **strictly OOS against `SPY` buy-and-hold**, plus **Canadian brokerage friction ($0–$9.95/trade / 10 bps RT) + Canadian tax drag (50% capital gains vs ordinary income)**, **circular block bootstrap**, **regime split**, and **200-run permutation shuffle control**.

