# Elimination Log — hilarious-seer Worktree
**Generated:** 2026-11-15T01:26:00Z  
**Purpose:** Detailed rationale for why each asset class, strategy, and approach was rejected or downgraded.

---

## Elimination Methodology

Every candidate was evaluated against the money-ready gate contract:
1. **Statistical significance:** n ≥ 100 decisive trades (TP/SL only; EXPIRED excluded)
2. **Profitability:** PF ≥ 1.5, WR ≥ 55%, expectancy > 0 with bootstrap 95% CI lower bound > 0
3. **Risk:** MaxDD < 20%
4. **Multiple testing:** PBO ≤ 0.55, SPA p < 0.10, FDR q = 0.10 with ≥1 survivor
5. **Source concentration:** No source > 40% (target) / > 60% (hard cap)
6. **Regime-direction:** No LONG in RISK_OFF
7. **Net of costs:** Expectancy > 0 after slippage + fees
8. **Recency:** Data < 48h old

Fail any one gate → elimination or downgrade to lower tier.

---

## Asset Class Eliminations

### CRYPTO — Active Strategies ELIMINATED; Passive Hold Conditional

**Status:** ACTIVE strategies ELIMINATED; PILOT status for regime-filtered VWAP MR only

**Evidence:**
- Live ledger: n=2,069, WR=45.7%, PF=1.31, mean_pnl=+0.385%
- After-cost: cost_multiple=-1.421x (fails 3x gate)
- Stop-fill analysis (audit_trail/stop_fill.py): 1,360/1,468 SL_HIT rows exited NOT at declared stop
- Mean planned risk: 1.919% of entry; mean realized loss: 2.990% — 1.56x overshoot
- CRYPTO class total loss: -837.8pp; stop-fill slippage: +828.0pp (98.8% of loss from fill location)
- Inverse mutations (inverse_luxalgo_confluence): 2,267 rows, 2,231 EXPIRED, 2,255 pnl=0.0 = zombie rows
- 3,377 EXPIRED picks in active_raw; 485 null current_price (87.4% of active_raw)

**Elimination Rationale:**
1. Stop-fill slippage makes every risk metric downstream meaningless. R-multiples, breakeven WR, required R:R all computed as if stops filled at plan. They don't.
2. After-cost net is negative. Even gross edge is insufficient to overcome 0.3% round-trip cost.
3. Zombie rows (EXPIRED with pnl=0, null current_price) inflate n and distort statistics.
4. Single-source concentration: claude_gainer_st = 91.7% of Smart Picks (artifact edge).
5. Dashboard WR 78.93% vs DB raw 39.38% = EXPIRED→WON mislabeling (survivorship bias).

**Exception:** Regime-filtered VWAP MR (peer kilo) passes Sharpe/PF/MDD gates but needs forward test with stop-fill fix before any capital.

---

### EQUITY — Active Strategies ELIMINATED; Passive Beta Only

**Status:** Active strategies ELIMINATED; FULL_LIVE for passive beta only

**Evidence:**
- Live ledger: n=680, WR=48.2%, PF=1.23, mean_pnl=+0.486%, cost_multiple=+3.23x
- Connors RSI-2 backtest (simulations/prove_equity_rsi2.py):
  - Total Return: -12.6% (2010-2026)
  - PF: 0.99
  - MaxDD: -46.0%
  - Benchmark SPY: +345.7%
- Dual Momentum backtest (simulations/prove_dual_momentum.py):
  - AnnRet: 9.1% vs SPY 14.7%
  - Sharpe: 0.40 vs SPY 0.73
  - MaxDD: -23.9% vs SPY -34.2%
  - No drawdown benefit vs benchmark
- Peer childlike-airport backtest: SPY connors_rsi2 PF=76.92, n=6 (statistically insignificant)
- 37/49 closed PnL=0% rows are FABRICATED_FLAT (exit_price = entry_price)

**Elimination Rationale:**
1. Connors RSI-2 FAILED every metric vs buy-and-hold. Negative total return over 16 years.
2. Dual Momentum does not improve on SPY on either return or risk-adjusted basis.
3. Peer backtests with n<10 are statistically meaningless (sampling error dominates).
4. FABRICATED_FLAT rows mean 75% of "closed" data is not actually marked to market.
5. Even the gross cost_multiple=3.23x is suspect because entry_time is blank for 49.9% of closed ledger.

**Exception:** Passive beta (VTI/BND 60/40) is deployable as benchmark capture, not alpha.

---

### ETF — ELIMINATED

**Status:** ELIMIDATED

**Evidence:**
- Live ledger: n=503, WR=44.3%, PF=1.07, mean_pnl=-0.165%, cost_multiple=+0.404x
- Best peer result: ETF TSMOM Sharpe 1.00, but PBO 0.36-0.59, SPA p=0.488, DSR<0.95
- After-cost net per trade: -0.0596% (loses money after 0.1% round-trip cost)
- Single-source concentration: 1.0 (100% from one source)

**Elimination Rationale:**
1. Cost_multiple=0.404x << 3x gate. Mean_pnl=0.0404% per trade cannot overcome costs.
2. PBO/SPA/FDR gates not passed. Bootstrap CI crosses zero.
3. 100% single-source = no independent confirmation.
4. No forward-test candidates with n≥10.

---

### FOREX — ELIMINATED

**Status:** ELIMINATED

**Evidence:**
- Live ledger: n=187, WR=40.3%, PF=0.66, mean_pnl=-0.528%, cost_multiple=-1.938x
- forex_rate_cache/*.json stale since 2026-06-06 (161d)
- fetch_prices.php returns HTTP 404 (dead since 2026-04-29)
- Only 123/691 OPEN rows have non-zero PnL
- PnL unit confusion: mercury2 writes RATIO*100; outcome_resolver writes RATIO; dashboard prints raw with % sign

**Elimination Rationale:**
1. Negative expectancy at -0.155% gross, -0.235% after cost.
2. Price feed dead for 161 days. No mark-to-market possible.
3. PnL unit split-brain means even the recorded numbers are unreliable.
4. 8 sign contradictions + 15 calc mismatches in DB.

---

### BOND — ELIMINATED

**Status:** ELIMINATED

**Evidence:**
- Live ledger: n=35, WR=33.3%, PF=0.56, mean_pnl=-0.2207%, cost_multiple=-4.414x
- After-cost net per trade: -0.2707%
- No forward-test candidates

**Elimination Rationale:**
1. n=35 < 100 minimum for statistical significance.
2. WR 33.3% << 55% gate.
3. PF 0.56 << 1.5 gate.
4. Negative expectancy gross and net.

---

### COMMODITY — ELIMINATED

**Status:** ELIMINATED

**Evidence:**
- Live ledger: n=7, WR=50.0%, PF=1.03, mean_pnl=+0.897%, cost_multiple=-3.984x
- commodity_price_cache/*.json stale since 2026-06-06 (161d)
- No forward-test candidates

**Elimination Rationale:**
1. n=7 << 100 minimum. Statistically meaningless.
2. Cost_multiple=-3.984x (negative due to insufficient sample gate).
3. Price feed dead for 161 days.

---

### FUTURES — ELIMINATED

**Status:** ELIMINATED

**Evidence:**
- Live ledger: n=1, WR=0.0%, PF=0.00, mean_pnl=-0.675%
- No strategies tested

**Elimination Rationale:**
1. n=1. No statistical basis.
2. No validated strategies exist.

---

### MUTUAL_FUND — NOT_BUILT

**Status:** NOT_BUILT

**Evidence:**
- No MUTUAL_FUND class in asset_class.py
- No coverage in any data source

**Elimination Rationale:**
1. Infrastructure does not exist.
2. Not a prediction class in this system.

---

## Strategy Eliminations

### Connors RSI-2 (SPY)
**Eliminated by:** Backtest simulation  
**Date:** 2026-11-15  
**Evidence:** simulations/prove_equity_rsi2.py — total return -12.6% vs SPY +345.7%, PF 0.99, MaxDD -46.0%  
**Rationale:** Underperforms buy-and-hold by 358pp over 16 years. MaxDD worse than benchmark. No edge.

### Dual Momentum (Faber Tactical Allocation)
**Eliminated by:** Backtest simulation  
**Date:** 2026-11-15  
**Evidence:** simulations/prove_dual_momentum.py — AnnRet 9.1% vs SPY 14.7%, Sharpe 0.40 vs 0.73  
**Rationale:** Does not improve on SPY in return, Sharpe, or drawdown. Transaction costs and whipsaw losses erode any theoretical benefit.

### Keltner Compression v2 (XLF) — childlike-airport peer
**Eliminated by:** Insufficient sample  
**Date:** 2026-11-15  
**Evidence:** backtest_results.json — PF=10.00, WR=100%, n=5  
**Rationale:** n=5 is statistically meaningless. With 5 trades, 100% WR could easily be sampling noise. DSR cannot be computed.

### BTC Funding Carry (H22) — protocol v4
**Eliminated by:** Insufficient sample  
**Date:** 2026-11-14  
**Evidence:** n=10 < 30 minimum; capital-adjusted CAGR below T-bill for top-5/top-10  
**Rationale:** Funding rate arbitrage requires larger universe and longer track record.

### ETF TSMOM (H18) — protocol v3
**Eliminated by:** Multiple testing failure  
**Date:** 2026-11-14  
**Evidence:** PBO 0.36-0.59, SPA p=0.488, DSR<0.95, bootstrap CI crosses zero  
**Rationale:** Sharpe 1.00 is in-sample curve-fit. Does not survive out-of-sample scrutiny.

### H10 SPY/QQQ RSI(2) — protocol v1-v2
**Eliminated by:** OOS contamination + single-day dependence  
**Date:** 2026-11-14  
**Evidence:** Sharpe 1.83, CAGR 22% but effective N≈38, DSR 0.9365 (<0.95), single-day dependence, execution fragility  
**Rationale:** High Sharpe is driven by a few outlier days. Effective sample size too small for DSR gate.

### All CRYPTO ML Reviver Strategies (except inverse_ml_enhanced)
**Eliminated by:** Anti-skill evidence + data quality  
**Date:** 2026-11-14  
**Evidence:** CRYPTO anti-skill dominant; 3,377 EXPIRED picks; 2,267 inverse-mutation zombies; 485 null prices  
**Rationale:** The strategy universe is so large (361 families + 285 baby strategies + mutation lab) that ~260 lucky PF>1.5 survivors are expected at p=5% by chance alone. No FDR correction applied.

---

## Data Quality Eliminations

### EXPIRED→WON Mislabeling
**Impact:** WR inflation across all classes  
**Evidence:** tools/resolver_hygiene_check.py flags EXPIRED status tagged WON; dashboard CRYPTO WR 78.93% vs DB raw 39.38%  
**Action:** RELABEL required before any statistical analysis is valid.

### FABRICATED_FLAT Closes
**Impact:** 37/49 closed PnL=0% rows are fabricated (exit_price = entry_price)  
**Evidence:** pnl_zero_validator.py (peer inspect-wt)  
**Action:** Mark-to-market required. These rows must be re-resolved with live prices.

### Frozen Prices
**Impact:** 87.4% of active_raw have blank current_price; forex/commodity caches 161d stale  
**Evidence:** db_freshness.json, price cache mtimes  
**Action:** Price refresh pipeline must be restored before any live PnL is trustworthy.

### PnL Unit Split-Brain
**Impact:** mercury2 writes RATIO*100; outcome_resolver writes RATIO; dashboard prints raw+%  
**Evidence:** ML-AUDIT.md lines 58-67; 8 sign contradictions + 15 calc mismatches  
**Action:** Harmonize PnL unit contract across all writers.

---

## Summary Table

| What | Count | Status |
|------|-------|--------|
| Asset classes evaluated | 8 | 0 money-ready |
| Strategies tested (backtest) | 3 local + 42 peer | 0 pass live-capital gates |
| Peer hypotheses reviewed | 23 | 0 proved |
| Closed picks audited | 3,500+ | 37/49 PnL=0% fabricated |
| Active picks evaluated | 4,310 | 87.4% null current_price |
| Stop-fill SL_HIT rows analyzed | 1,468 | 1,360 late fill (92.6%) |
| Zombie rows identified | 2,267 | inverse_mutations EXPIRED pnl=0 |
| Money-ready verdict | — | **0/166 cells** |

---

*No capital deployed. All eliminations are documented and reversible if forward evidence changes.*
