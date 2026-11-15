# Algorithm Specification — ETF

**Worktree:** scratch-hippodraco  
**Asset Class:** ETF  
**Status:** PAPER CANDIDATE (SECONDARY) — hypothesis-grade, n at floor  
**T2 Gate Status:** Not yet T2-cleared; cleanest OOS profile in prior analysis

---

## 1. Algorithm Overview

**Strategy Name:** `etf-sector-rotation`  
**Type:** Sector rotation / dual momentum across ETF universe  
**Universe:** SPY, QQQ, IWM, XLF, XLE, XLK, XLV, XLI, XLB, XLP, XLU, XLRE, XLC, EFA, EEM, AGG, TLT (expand from current ~45 to ≥150)  
**Holding Period:** 1 month (monthly rebalance)  
**Lookback:** 12 months (momentum)  
**Skip:** 1 month (avoid lookahead/lookback distortion)  
**n_long:** 4–6 (top ETFs by momentum, equal weight)  
**Direction:** Long only  
**Rebalance Frequency:** Monthly  

---

## 2. Entry Rule

At each month-end:
1. Compute 12-month momentum (skipping most recent month) for each ETF in universe.
2. Select top n_long (4–6) by momentum score.
3. Equal weight across selected ETFs.
4. Enter at next month-open.

---

## 3. Exit Rule

1. **Scheduled exit:** Monthly re-rank and re-select; sell fallouts, buy entrants.
2. **Emergency stop:** Rolling 30-day drawdown > 30% → pause.
3. **Expense-ratio awareness:** ETF expense ratios (typically 0.03–0.20%/yr) reduce net return over multi-month holds; factor into cost model.

---

## 4. Position Sizing

- Equal weight across n_long positions.
- Max 2.5% of account per position (¼ Kelly cap).
- Concentration: no single ETF > 25% of strategy allocation.

---

## 5. Cost Model

| Component | Value | Basis |
|-----------|-------|-------|
| Commission | ~2.5 bps | IB-style |
| Spread | ~3–5 bps | ETF spreads tighter than individual stocks |
| Slippage | ~5–8 bps | Lower than single-stock due to liquidity |
| Expense ratio drag | ~0.10%/yr | Prorated per holding period |
| **Total round-trip** | **~15 bps** | Conservative estimate |

---

## 6. Benchmark

**Primary:** SPY total return.  
**Secondary:** Equal-weight ETF universe buy-and-hold.

---

## 7. T2 Gate Thresholds

| Metric | Threshold |
|--------|-----------|
| Profit Factor (post-cost) | ≥ 1.5 |
| Win Rate (EXPIRED-inclusive) | ≥ 50% |
| Max Drawdown | ≤ 20% |
| n resolved (forward) | ≥ 100 (currently n=45, at floor) |
| Sharpe (annualized) | ≥ 1.0 |
| Beat SPY total return | Yes |

---

## 8. Justification for ETF Selection

ETF is a secondary paper candidate because:
1. Cleanest OOS profile in prior analysis: WF consistency 100%, OOS WR 75%, decay +23% (improving).
2. Profitable approach backtest showed ETF n=120, PF 1.21 (+26.5pp) — **stale prior analysis**; current money_ready_verdict shows ETF n=45, PF=0.0216, WR=2.22% (INSUFFICIENT_DATA).
3. ETFs offer diversification within a single ticker, reducing single-name risk.
4. **Blocker:** n is at floor (n=45 per current verdict). Universe must be expanded to XLF/XLE/XLK + more to reach n ≥ 100 minimum, n ≥ 150 for OOS_READY promotion.
5. **PF is critically low:** 0.0216 vs 1.5 T2 floor — massive gap to close.

---

## 9. Data Requirements

- ETF daily closes (auto-adjusted for dividends/splits).
- Expense ratio data for each ETF (for cost modeling).
- Universe expansion list (XLF, XLE, XLK, etc.).

---

## 10. Risks & Caveats

- **n at floor:** Statistical power limited until universe expanded (n=45 current vs ≥100 needed).
- **Expense drag:** Multi-month holds incur ongoing expense ratio costs.
- **Sector concentration:** Top ETFs may be highly correlated (e.g., QQQ and XLK both tech-heavy).
- **Prior PF weak:** Historical PF 1.24 (< 1.5 T2 floor); current PF 0.0216 is far below.
- **PF vs WR gap:** WR=2.22% means nearly all trades are losses — structural issue, not just noise.

---
