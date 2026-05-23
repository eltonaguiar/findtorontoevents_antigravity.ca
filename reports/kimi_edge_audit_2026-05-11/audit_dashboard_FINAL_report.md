# Unified Audit Dashboard - COMPLETE Performance Data Extraction
## Source: https://findtorontoevents.ca/audit + dashboard_data.json
### Extraction Date: 2026-05-11
### Dashboard Version: v99.0 | JSON Generated: 2026-05-04T03:43:55Z

---

## 1. EXECUTIVE SUMMARY

The Antigravity Unified Audit Dashboard is a comprehensive financial prediction system tracking **130+ systems** generating picks across **7 asset classes** (Crypto, Equity, Forex, Commodity, ETF, Bond, Futures). The dashboard displays real-time performance metrics, walk-forward validation results, tier-2 proven strategies, and extensive alerting for degraded systems.

**Key Headline Metrics:**
- **Total Closed Picks**: 3,386 (filtered) / 29,258 (raw) / 9,627 (resolved)
- **Active Picks**: 50-61 (varies by quality gates)
- **Systems**: 13 active proven, 130+ total
- **Overall Win Rate**: 34.8-40.0%
- **Total PnL**: +949.43% (capped) / +986.01% (latest)
- **Profit Factor**: 1.49-1.51
- **Expectancy**: +0.28-0.29%
- **HF Net Sharpe**: 0.1229
- **HF Max Drawdown**: 680.66%
- **HF Calmar**: 0.1191

---

## 2. DB HEALTH METRICS

| Metric | Value | Status |
|--------|-------|--------|
| PnL Integrity (sampled) | 42.0% | RED (58,000/100,000 mismatch >1pp) |
| Ghost Rows (constant pnl_pct) | 655,000 | RED (18 cohorts) |
| Forward Validator Freshness | 840h | RED (last WON/LOST: 2026-04-02) |
| Phantom EXPIRED rows | 100.0% | RED (1 class, worst-case) |
| Raw-Pick Outcome Coverage | 0.09% | RED (121/136,374 resolved) |
| WON-vs-PnL contradiction | YES | RED (writer bug) |

**Action Required**: Red-tier metrics detected. See `reports/db_evidence_graded_final_2026-05-08.md`

---

## 3. ASSET CLASS HEALTH (Headline - Full History)

| Asset Class | Profit Factor | Win Rate | n (trades) | Tier Status | Notes |
|-------------|--------------|----------|------------|-------------|-------|
| **COMMODITY** | **2.08** | 48.7% | 816 | T2 PF confirmed | Post-resolver-v2, 7d clean |
| **BOND** | **1.72** | **55.6%** | 18 | Meets T2 thresholds | n<100 charter floor |
| **EQUITY** | **1.42** | **52.8%** | 428 | T2 candidate | Scale candidate |
| **ETF** | 1.20 | **53.4%** | 88 | Borderline T3 | n->100 needed |
| **CRYPTO** | 1.26 | 44.8% | 8,162 | Sub-T2 | quan_engine base (PF 0.66) not blocked |
| **FOREX** | **0.28** | 45.6% | 1,249 | Sub-floor (genuine) | NOT resolver noise; mutation required |

### Recent vs Headline Divergence (60-90d window)

| Asset Class | Headline PF | Recent PF | Headline n | Recent n |
|-------------|-------------|-----------|------------|----------|
| CRYPTO | 1.25 | 0.89 | 8,067 | 1,650 |
| COMMODITY | 1.78 | 1.09 | - | - |

---

## 4. HF STATS BY ASSET CLASS (Recent Window)

| Asset Class | n | Sharpe | Sortino | Net Sharpe | VaR 95% | CVaR 95% | Max DD% | Calmar | Ulcer Index | Win Rate | Profit Factor |
|-------------|---|--------|---------|------------|---------|----------|---------|--------|-------------|----------|---------------|
| **EQUITY** | 355 | **2.2286** | **3.8238** | **2.2221** | -10.29 | -8.04 | 71.37 | **3.3705** | 18.97 | **52.96%** | **1.437** |
| **BOND** | 17 | **1.9184** | **5.1251** | **1.8955** | -2.95 | -1.28 | 3.06 | **0.9285** | 1.34 | 47.06% | **1.601** |
| **ETF** | 77 | **0.6237** | 0.9634 | **0.6132** | -5.31 | -5.79 | 46.94 | 0.1964 | 26.82 | **51.95%** | 1.100 |
| **COMMODITY** | 590 | 0.2190 | 0.3579 | 0.1809 | -1.77 | -1.84 | 21.86 | 0.3099 | 6.74 | 42.54% | 1.086 |
| **FOREX** | 808 | -0.0382 | -0.0584 | -0.0529 | -4.62 | -3.12 | 70.18 | -0.0601 | 8.11 | 49.75% | 0.969 |
| **CRYPTO** | 1650 | **-0.6019** | -0.8459 | **-0.6133** | -5.94 | -4.89 | **674.67** | **-0.2584** | **351.34** | 37.52% | **0.893** |
| UNKNOWN | 3 | 6883.03 | None | 6699.73 | 0.08 | None | 0.00 | None | 0.00 | 100.0% | None |

**Overall HF**: n=3,500 | Sharpe=0.1345 | Sortino=0.204 | Net Sharpe=0.1229 | VaR 95=-5.83 | CVaR 95=-5.38 | CVaR 99=-10.62 | Max DD=680.66% | Calmar=0.1191 | Ulcer=332.05 | WR=43.17% | PF=1.032 | PSR=0.5177

---

## 5. HF ROLLING CURRENT (30d Window)

| Metric | Value |
|--------|-------|
| Window | 30 days (ending 2026-04-22) |
| Trades | 3,134 |
| Sharpe | 0.173 |
| Sortino | 0.259 |
| Net Sharpe | 0.161 |
| Max Drawdown | 721.91% |
| CVaR 95 | -4.70 |
| CVaR 99 | -10.44 |
| Win Rate | 42.98% |
| Ulcer Index | 362.71 |

---

## 6. TIER DEFINITIONS

| Tier | Profit Factor | Win Rate | Max Drawdown | Description |
|------|--------------|----------|--------------|-------------|
| T1 (Renaissance) | >2.0 | >55% | <10% | Highest grade |
| T2 (Institutional) | >1.5 | >50% | <20% | Institutional grade |
| T3 (Retail-OK) | >1.2 | >48% | <30% | Acceptable for retail |

---

## 7. WALK-FORWARD OUT-OF-SAMPLE METRICS

### Dashboard Display (by class)

| Class | Folds | OOS WR | OOS Sharpe | Decay | Consistency | Worst-fold WR |
|-------|-------|--------|------------|-------|-------------|---------------|
| **CRYPTO** | 25 | 46.1% | **1.833** | -0.4 | 68.0% | 27.0% |
| **EQUITY** | 8 | **64.1%** | **6.555** | +3.9 | 87.5% | 40.0% |
| **ETF** | 4 | **76.2%** | **11.372** | +28.8 | **100.0%** | 70.0% |
| **FOREX** | 52 | 40.4% | **-3.504** | -1.9 | 48.1% | **2.0%** |

### Walk-Forward ETF Detail (12 folds)

| Metric | Value |
|--------|-------|
| OOS WR | 61.7% (+/- 23.4%) |
| OOS Sharpe | 6.368 (+/- 16.882) |
| Decay | 10.8 |
| Consistency | 66.7% |
| Worst-fold WR | 20.0% |
| Best-fold WR | 100.0% |

---

## 8. TIER-2 PROVEN STRATEGIES (DETAILED)

### 8a. signal_validation (STRICT TIER 2)

| Metric | Value |
|--------|-------|
| Tier | Tier 2 (clears institutional sized-up floor) |
| Strict T2 | YES |
| Win Rate | 63.0% |
| Profit Factor | 2.58 |
| Max Drawdown | 12.0% |
| Expectancy | 1.0% |
| Total PnL | +183.24% |
| n (forward) | 184 |
| n (closed) | 393 |
| Wins/Losses | 116/68 |
| Asset Classes | CRYPTO, FOREX |
| Status | active |
| 90d Sparkline (last 5) | ...164.46, 177.46, 185.21, 184.14 |

### 8b. mega_mutation (BUILDING)

| Metric | Value |
|--------|-------|
| Tier | Building (n=79 below 100-pick floor) |
| Strict T2 | NO |
| Win Rate | **67.1%** |
| Profit Factor | **3.16** |
| Max Drawdown | 35.96% |
| Expectancy | 2.29% |
| Total PnL | +180.67% / +241.06% (90d peak) |
| n (forward) | 79 |
| n (closed) | 137 |
| Wins/Losses | 53/26 |
| Asset Class | CRYPTO |
| Status | active |

### 8c. rl_agent (BUILDING)

| Metric | Value |
|--------|-------|
| Tier | Building (n=5 below 100-pick floor) |
| Win Rate | 60.0% |
| Profit Factor | 2.54 |
| Max Drawdown | 2.14% |
| Expectancy | 1.27% |
| Total PnL | +6.36% |
| n (forward) | 5 |
| n (closed) | 10 |
| Wins/Losses | 3/2 |
| Asset Class | CRYPTO |
| Status | monitoring |

---

## 9. ASSET CLASS SUMMARY (Smart Pick Thresholds)

| Asset Class | Active | Smart | Avg Score | Forward WR | Threshold Pass | Min Score | Min FWR | Min Trades |
|-------------|--------|-------|-----------|------------|----------------|-----------|---------|------------|
| **CRYPTO** | 38 | 0 | 51.95 | 38.9% | FALSE | 65.0 | 62% | 10 |
| **EQUITY** | 12 | 2 | 32.83 | 38.2% | FALSE | 40.0 | 50% | 5 |
| **FOREX** | 6 | 0 | 29.83 | 47.3% | FALSE | 40.0 | 46% | 3 |
| **COMMODITY** | 0 | 0 | 0.00 | 0.0% | TRUE | 40.0 | 50% | 0 |
| **FUTURES** | 0 | 0 | 0.00 | 0.0% | TRUE | 45.0 | 50% | 0 |
| **BOND** | 0 | 0 | 0.00 | 0.0% | TRUE | 35.0 | 50% | 0 |
| **ETF** | 4 | 0 | 22.75 | 11.6% | FALSE | 40.0 | 50% | 0 |

---

## 10. FLAGGED DEGRADED SYSTEMS (HIGH ALERTS)

| System | Rolling 7d WR | Baseline WR | Drop | Action |
|--------|--------------|-------------|------|--------|
| cta_cross_asset_tsmom | 29% | 45% | >20% | REDUCE |
| myfxbook_retail_contrarian | 14-33% | 46-54% | >20% | REDUCE |
| ig_contrarian_sentiment | 19-20% | 45% | >20% | REDUCE |
| forex_rsi2_mean_reversion | 9-18% | 44-49% | >20% | REDUCE |
| futures_momentum | 4-20% | 42-45% | >20% | REDUCE |
| st_multi_day_momentum | 47% | 68% | >20% | REDUCE |
| macd_rsi_m048 | 53% | 73% | >20% | REDUCE |
| ema_momentum_m006 | 36% | 56% | >20% | REDUCE |
| luxalgo_confluence | 34% | 45% | >20% | REDUCE |
| hs_lb_None | 0% | 34% | >20% | REDUCE |
| crypto_vwap_volprofile_reversion_v1 | 0% | 32% | >20% | REDUCE |
| stocks_rsi2_pullback | 42% | 73% | >20% | REDUCE |
| ensemble | 27% | 41% | >20% | REDUCE |
| goldmine_1x_consensus | 12% | 30% | >20% | REDUCE |
| MomentumEMA | 46% | 67% | >20% | REDUCE |
| gainer_compression_relaxed_mut | 8% | 32% | >20% | REDUCE |
| signal_engine_momentum_mut | 30% | 50% | >20% | REDUCE |

---

## 11. CLOSED PICKS PERFORMANCE

### 11a. Headline Metrics

| Metric | Value |
|--------|-------|
| Total Closed Picks | 3,382-3,386 |
| Win Rate | 34.8-35.0% |
| Total PnL | +949.43% to +986.01% |
| Excl. Outliers (+/-10% cap) | +773.66% to +810.25% (27 capped) |
| EW Compound (+/-500 cap, chrono) | +360,456% to +516,065% |
| Rolling 100 | +107.58% to +217.79% |
| Annualized Geomean | +9999.00% |
| Median Trade | -0.00% |
| Profit Factor | 1.49-1.51 |
| Expectancy | +0.28% to +0.29% |
| Avg Win / Avg Loss | +2.46-2.48% / -1.35% |
| W / L / F | 1178-1183 / 1440-1448 / 759-760 |
| Systems | 12-13 |

### 11b. Smart Snapshot

| Metric | Value |
|--------|-------|
| Smart Snapshot WR | 48.9% |
| Swing Picks | 49% (135) |
| Verified Alpha | 16-17 (27-34% of active) |
| Audited Source WR | 64.2-66.1% (13-15 covered) |
| Verified Realized WR | 33.8-34.2% (2520-2731 trades) |

### 11c. Mercury Validation

| Metric | Value |
|--------|-------|
| Daily Volatility | 2.91% |
| Net Sharpe | 0.0894 (1.42 ann.) |
| Sortino | 0.1397 (2.22 ann.) |
| Sharpe (per-trade) | 0.1034 |
| Sharpe (per-trade, ann.) | 4.58 |
| Active PnL (Live) | -3.05% |
| Active W/L (Live) | 29/32 (48% green) |

---

## 12. TIMEFRAME PERFORMANCE (Capped Stats)

| Period | Trades | Raw PnL | Capped PnL | Median | Avg Trade | PF | Sharpe | Outliers |
|--------|--------|---------|------------|--------|-----------|-----|--------|----------|
| Last 24h | 227 | +174.24% | +50.77% | -0.54% | +0.77% | **1.78** | 0.076 | 8 |
| Last 7d | 1482 | +434.18% | +285.27% | -0.50% | +0.29% | 1.31 | 0.073 | 15 |
| Last 30d | 5033 | +1247.30% | +1044.67% | +0.00% | +0.25% | 1.33 | 0.088 | 33 |
| All Time | 9575 | +1119.34% | +1205.58% | -0.01% | +0.12% | 1.11 | 0.042 | 189 |

---

## 13. PERFORMANCE BY SYSTEM CATEGORY

| Category | Systems | Active | Closed | Wins | Losses | Win Rate | Total PnL | PF |
|----------|---------|--------|--------|------|--------|----------|-----------|-----|
| Proven Systems | 4 | 4 | 4,699 | 152 | 136 | **52.8%** | +127.45% | **1.68** |
| Sandbox (Unproven) | 46 | 102 | 8,522 | 1,381 | 1,567 | 46.8% | +2170.57% | **2.18** |
| Probation | 16 | 27 | 46,275 | 2,694 | 2,893 | 48.2% | +1937.52% | 1.26 |
| **WR >= 50% (min 5)** | **16** | **37** | **8,087** | **1,161** | **731** | **61.4%** | **+2601.83%** | **2.45** |
| WR < 50% (min 5) | 43 | 96 | 51,392 | 3,065 | 3,862 | 44.2% | +1636.68% | 1.19 |

**Key Insight**: Trading only systems with WR >= 50% yields **61.4% WR** and **+2601.83% total PnL** vs +1636.68% for WR < 50% systems.

---

## 14. CRYPTO PERFORMANCE BY TIER

### All Tiers
| Metric | Value |
|--------|-------|
| Win Rate | 46.5% |
| Total PnL | +506.23% |
| Active | 32 |
| Closed | 1451 |
| W/L/F | 675/775/1 |
| Profit Factor | 1.39 |
| Avg PnL/trade | 0.35% |

### S-Tier (75.0% WR, PF 7.22)
### A-Tier (45.5% WR, PF 1.39, +142.34%)
### B-Tier (52.2% WR, PF 1.65, +289.69%)
### C-Tier (39.6% WR, PF 1.10, +48.99%)

---

## 15. NON-CRYPTO PERFORMANCE

### Equities & Stocks (54.4% WR, PF 2.08, +360.39%)
### Forex (15.8% WR, PF 0.52, -91.58%) - **UNDERPERFORMING**
### Commodities (43.7% WR, PF 3.61, +123.21%)
### ETFs (58.2% WR, PF 1.58, +52.62%)
### Bonds (50.0% WR, PF 0.66, -1.53%)

---

## 16. SYSTEM CLEAN METRICS (Top Systems by PnL)

| System | Raw PnL | Capped PnL | n | PF | Sharpe/trade | Max DD | Top Symbol Concentration |
|--------|---------|------------|---|-----|-------------|--------|------------------------|
| **alpha_engine** | +363.32 | +35.71 | 1256 | 1.23 | 0.0083 | 194.03 | INJUSDT 89.2% |
| **mercury2** | +127.63 | +97.97 | 289 | 1.43 | 0.1122 | 194.03 | ENJUSDT 65.2% |
| **multi_asset_copytrader** | +31.50 | +31.50 | 1122 | 1.16 | 0.0254 | 49.86 | CT=F 126.2% |
| **battleground** | +5.07 | +5.07 | 151 | 1.07 | 0.0277 | 27.33 | ETHUSDT 101.4% |
| **multi_asset** | -3.10 | -3.10 | 75 | 0.77 | -0.075 | 7.80 | CL=F 193.5% |
| **multi_asset_cot** | -3.37 | -3.37 | 12 | 0.70 | -0.110 | 10.92 | KC=F 147.1% |

---

## 17. 2-HOUR TIMEFRAME STATS (Last 24h)

**Summary**: 56 opened | 230 closed | WR: 38.3% | Avg PnL: +0.41%

| Window (EST) | Opened | Closed | Avg PnL | WR |
|-------------|--------|--------|---------|-----|
| 05-11 14:25-16:25 | 9 | 4 | +2.30% | 50% |
| 05-11 12:25-14:25 | 37 | 17 | +1.64% | **88%** |
| 05-11 10:25-12:25 | 4 | 21 | +1.88% | 52% |
| 05-11 08:25-10:25 | 3 | 11 | -0.59% | 27% |
| 05-11 06:25-08:25 | 0 | 8 | +3.30% | 63% |
| 05-11 04:25-06:25 | 0 | 3 | +3.99% | **100%** |
| 05-11 02:25-04:25 | 0 | 8 | +1.05% | 38% |
| 05-11 00:25-02:25 | 0 | 9 | +7.08% | **78%** |
| 05-10 22:25-00:25 | 0 | 45 | -0.37% | 27% |
| 05-10 20:25-22:25 | 0 | 15 | +0.52% | 47% |
| 05-10 18:25-20:25 | 1 | 15 | +0.94% | 40% |
| 05-10 16:25-18:25 | 2 | 74 | -1.25% | 19% |

---

## 18. QUALITY GATES

| Metric | Value |
|--------|-------|
| Total Active Before Gates | 242 |
| Active After Gates | 61 |
| Smart Picks Count | 2-3 |
| Filtered Out | 181 |
| Score Safety Net Applied | 6 |
| Degradation - Severe | 9 strategies |
| Degradation - High | 3 strategies |
| Degradation - Lifting | 31 strategies |
| Strong Active Count | 21 |

---

## 19. BTC SCALPING AUDIT

| Metric | Value |
|--------|-------|
| Claimed WR | 91.67% |
| Real Match | 2/12 trades matched real BTC data |
| Best Backtest | 40.00% |
| Practical WR Target | 60-75% |
| Verdict | **NOT REPLICABLE** |

---

## 20. OPEN FORWARD TRADES BY SYSTEM

| System | Open | W/L | Avg P/L | Total P/L | Best Pick | Worst Pick |
|--------|------|-----|---------|-----------|-----------|------------|
| riseoftheclaw | 5 | 3/2 | +0.85% | +4.2% | DOGE-USD +3.74% | ADA-USD -0.28% |
| dna winner picks | 1 | 1/0 | +0.59% | +0.6% | JUPUSDT +0.59% | - |
| non crypto consensus | 1 | 1/0 | +0.26% | +0.3% | EURGBP=X +0.26% | - |
| ml gatekeeper | 8 | 5/3 | +0.12% | +1.0% | SOXX +3.42% | UBER -3.06% |
| battleground | 1 | 0/1 | -0.36% | -0.4% | - | XRPUSDT -0.36% |
| regime terminal | 4 | 1/3 | -0.42% | -1.7% | SOL-USD +1.67% | GOOGL -2.46% |
| tsmom strategy | 3 | 1/2 | -1.21% | -3.6% | ONDOUSDT +2.33% | OSMOUSDT -4.92% |
| ueps | 16 | 6/10 | -12.47% | -199.5% | TXN +1.20% | MDT -99.99% |

---

## 21. ISSUES & ERRORS

### Critical
- PnL Integrity: Only 42.0% (58K/100K mismatches)
- Ghost Rows: 655,000 rows with constant pnl_pct
- Forward Validator: 840h stale
- Outcome Coverage: Only 0.09% resolved
- WON-vs-PnL Contradiction: YES

### Degradation
- 18 HIGH-priority alerts for systems with >20% WR drop
- 4 MEDIUM alerts for inactive systems

### Concentration Risk
- USDCHF=X: 215.4% of total PnL impact
- alpha_engine: 89.2% from INJUSDT alone

---

## 22. FILES GENERATED

| File | Path |
|------|------|
| Full Page Screenshot | `/mnt/agents/output/audit_dashboard_full.png` |
| Complete Extraction Report | `/mnt/agents/output/audit_dashboard_complete_extraction.md` |

---

*Report compiled from live dashboard extraction, full-page screenshot, and dashboard_data.json deep analysis.*
*All data current as of 2026-05-11.*
*130+ systems tracked across 7 asset classes with 3,386+ closed picks.*
