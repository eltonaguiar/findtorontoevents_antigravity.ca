# Framework Answers — Asset-Class Inventory, Probability Ranking, Profitability Framework, Risk Overlay
**Date:** 2026-11-15  
**Source:** combines the November 14 final plan (`final_v4/scratch-hippodraco-2026-11-14T2150Z/04-synthesis/FINAL_FINDINGS.md`), `money-maker-readyv2`, `docs/ALL_STRATEGIES.md`, and the profitable-approach audit (`PROFITABLE_APPROACH_v1.md`).  
**Status:** Answers only — no capital deployment.

---

## A. Thorough list of asset classes the system has attempted to predict

The live system (alpha_engine, quan_engine, audit dashboard at findtorontoevents.ca/audit, HyroTrader, and related pipelines) continuously scans and generates picks across these classes. Coverage and data quality vary sharply.

| Asset Class | Status / Coverage | Historical notes (older snapshots) | Recent reality (plan + live) | Key strategies / sources |
|-------------|-------------------|------------------------------------|------------------------------|--------------------------|
| CRYPTO | Highest volume | Elite strats PF 2.3–4; overall dragged lower | Sub-T2; recent PF ~0.74, WR ~33% | ML predictors, copy-trader, battleground, KIMI, etc. |
| EQUITY (US) | Active | PF ~1.41, WR ~53%, n~400+ | Recent PF ~0.70; best candidate for testing | multi_asset, stocks_competition, ml_gatekeeper |
| COMMODITY / FUTURES | Active | PF ~1.78, WR ~47%, n~750 | Better historical PF; still unproven | CTA, COT, multi-asset |
| ETF | Sparse upstream | PF ~1.24, WR ~55%, n~87 | Zero live picks; SPY sometimes miscategorized as equity | etf_strategies.py |
| BOND | Very sparse | PF ~1.72, WR ~56%, n=18 | Accumulating; n far below floor | bond_strategies.py + FRED |
| FOREX | Active but poor | PF 0.27 (sub-floor); high n | Recent PF ~0.85; mutation-before-kill | Copy-trader + CTA paths |
| MUTUAL FUNDS | Zero coverage | Infrastructure does not exist | Explicitly blocked; needs full build (NAV cache, ranker, metadata, etc.) | findmutualfunds2 folder exists but empty of production path |

Other related surfaces: HyroTrader (prop challenge tracker), Mercury 2, Crypto ML Edge, Claude Gainer, DNA Genome, AI tournament, etc. Main dashboard tabs of interest remain Active Picks and Closed Picks, with supporting GitHub Actions and MySQL historical tracking.

**Classes NOT predicted:** MUTUAL FUNDS (zero coverage — class id −1, dropped by ML gate). PENNY_STOCK / MEMECOIN exist but are weak/blocked.

---

## B. Which classes have the highest probability of profitability with lower risk?

Your intuition about mutual funds and ETFs is directionally correct for *lower risk* and *higher probability of positive expected returns over long horizons*, but it is **not an edge from the prediction system**. It is mostly market beta (equity risk premium, bond yields) plus low costs. Active timing or stock-picking signals on top of them have not been proven here.

### Realistic ranking (probability of positive real returns + lower permanent capital-loss risk)

1. **Low-cost broad index ETFs + passive mutual funds** (buy-and-hold or simple rebalance)  
   Highest practical probability of profitability with lowest risk among liquid assets. Capture the equity risk premium (and bond income) over multi-year periods. Criteria: ER ≤0.10–0.20%, high AUM, low turnover (≤20%/yr), long track record, R² ≥0.99 vs index. This is allocation and cost discipline, **not** ML prediction.

2. **EQUITY** (systematic, after proper validation)  
   Highest-priority research slot in the final plan. Only class with a pre-registered benchmark test path vs SPY total return and some positive cost-margin signals. Still unproven; requires n≥500, PF≥1.15 after costs, clean OOS.

3. **COMMODITY / selective BOND** (low-frequency)  
   Better historical PF numbers than crypto/forex, but low n and cost/execution issues block them. Lower risk than crypto when sized properly.

4. **ETF tactical / long-term quality single stocks** (e.g., NVDA-style)  
   Possible satellite, not core. Concentration and volatility raise permanent-loss risk. Long-term holding of quality growth has worked historically; daytrading/scalping has not (costs + overfitting dominate).

5. **CRYPTO** (conditional)  
   Potential in isolated elite strategies, but overall drag from retired toxic paths, high volatility, and data/fill bugs. High risk.

6. **FOREX**  
   Currently the weakest.

Daytrading or scalping simulations can look attractive until realistic costs, slippage, and multiple-testing penalties are applied. Most retail attempts lose money.

---

## C. Framework for finding profitability despite the struggles

The system is research infrastructure, **not** a money-ready engine. Treat it that way.

### Step 1 — Fix measurement before anything else
Recompute PnL from entry/exit vs real market data (Binance, Nasdaq, er-api). Flag blank fields, open positions >72h, missing exit data, and cost leakage. The final plan's QA items (PnL=0% validation, blank-field severity, open/recently closed flags) are the right starting point.

Mandatory data-integrity filters (money-maker-readyv2, 2026-06-09) — apply ALL or numbers are worthless:
1. Exclude backfill labels: `resolver_version NOT LIKE 'backfill%'` AND `resolved_at IS NOT NULL`.
2. Exclude banned sources (Predictions, sandbox_opposite, rapid_fire, incubator_gainer, luxalgo_filters, multi_asset_copytrader, forex_copy_trader, signal_validation, multi_asset_cot, regime_terminal, multi_asset_scanner, myfxbook_retail_contrarian, ig_contrarian_sentiment).
3. Per-class sane-pnl guard: `ABS(pnl_pct) <= FOREX 20 / COMMODITY 30 / BOND 25 / CRYPTO 95 / else 50`.
4. Count EXPIRED as a NON-WIN: `WR = WON / (WON+LOST+EXPIRED+FLAT)`.
5. Require intrabar validation before trusting WR (`tools/reresolve_intrabar.py` — CRYPTO drops 52.3%→42.9%).
6. Require ≥3 distinct months at n≥30/month (reject single-snapshot artifacts).

### Step 2 — Separate beta capture from alpha generation
- **Core portfolio:** low-cost diversified ETFs/mutual funds (total market, international, short-duration bonds or T-bills for ballast). This is the highest-probability lower-risk path and does **not** require the prediction system to work.
- **Alpha research:** keep the scanners, but enforce the existing promotion gates. All classes currently fail them. Focus first on the EQUITY pre-registered SPY benchmark test.

### Step 3 — Strict research protocol
- Pre-register hypotheses (asset class, style, holding period, entry/exit rule, benchmark, cost assumptions, nb_trials).
- Require clean OOS, effective N, cost-adjusted PF, Sharpe/Sortino/Calmar/DSR thresholds, and forward n≥100–500.
- Kill or mutate paths that fail (FOREX already on mutation protocol).
- Build the missing mutual-fund and proper ETF infrastructure only if you want to test selection criteria rigorously; otherwise just hold the low-cost ones.

### Step 4 — Risk-management overlay (independent of signal quality)
Position sizing 1–2% risk per trade, quarter-Kelly max, ATR-based stops (e.g., 1.0× SL / 1.5× TP, min R:R 1.5:1), daily/weekly/monthly drawdown halt rules, and a separate risk dashboard (`audit_dashboard/risk_management.html`). These protect capital while the edge search continues.

### Step 5 — Practical prioritization order
1. Measurement and cost integrity.
2. EQUITY benchmark test vs SPY.
3. Crypto only after known fill bugs are fixed and a clean forward test runs.
4. Everything else remains blocked until arithmetic and data quality clear.
5. Parallel track: simple low-cost ETF/MF allocation as the actual money deployment vehicle.

---

## D. Honest bottom line

**No asset class is currently proven profitable.** 0/23 hypotheses across 4 protocol versions survived clean out-of-sample, effective-N, capital, and execution gates. Information coefficient ≈ 0, win rates ≈ 40%, accuracy below target. All 9 classes return `sizing_allowed: false`. **Do not deploy capital yet.**

The highest-probability lower-risk path is low-cost diversified index exposure (ETFs / mutual funds) plus disciplined risk rules, while the research continues under strict gates. The prediction system has generated a large volume of ideas and infrastructure. The missing piece is a single clean, pre-registered, cost-adjusted demonstration of edge against a transparent benchmark. Until that exists, the highest-probability lower-risk path is the boring one: diversified low-cost index exposure plus disciplined risk rules, while the research continues under strict gates.

---
