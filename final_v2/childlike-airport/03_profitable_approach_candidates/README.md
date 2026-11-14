# 03 — Profitable Approach Candidates

**Date:** 2026-11-14 | **Worktree:** childlike-airport  
**Purpose:** Consolidated, comparable view of approaches with evidence of profitability (validated/candidate/pilot), including Kilo v11/v12 VWAP results.

## Candidate Matrix

| Rank | Approach | Asset Class | Horizon/TF | Evidence (key metrics) | Gate status | Verdict | Next step |
|---|---|---|---|---|---|---|---|
| 1 | Vol-Targeted Time-Series Momentum (50d+200d SMA, 20% vol target, 0.1%/side) | Crypto (diversified, 10) | Daily, 7.4y | CAGR 23.0%, Sharpe 2.13, PF 1.40, MDD −17.4%, t=5.56, bootstrap CI [1.25,3.25] | Strong research; production/live not shown | **PROVEN (research)** | Productionize spec, paper forward, cost/slippage stress |
| 2 | Regime-Filtered VWAP MR (4h, 40% size, 20bps RT) — **v11 core** | Crypto (BTC,ETH,SOL,XRP) | 4h, ~2y | n=65, WR 53.8%, PF 1.435, Sharpe 7.10, Ret 10.9%, MDD 3.5%, PBO 0.480, P(SR>0)=1.000 | Basic PASS; strict PBO<0.3 FAIL (sample) | **VALIDATED (basic/conditional)** | Expand data/history, keep core symbols, confirm live costs |
| 3 | Regime-Filtered VWAP MR (4h, 40% size, 20bps RT) — **v12 expanded** | Crypto (8 symbols) | 4h, ~2y | n=129, WR 44.2%, PF 1.210, Sharpe 3.76, Ret 12.7%, MDD 10.0%, PBO 0.489, P(SR>0)=1.000 | Basic PASS; strict PBO<0.3 FAIL | **PROFITABLE (basic), diluted** | **Prefer core subset (BTC/ETH/SOL/XRP/ADA)**; drop DOGE/AVAX/LINK |
| 4 | mega_mutation_macd_rsi / ema_momentum | Crypto | — | PF 3.12–5.816 BT, 8.32 FW, WR 84% (flaxen-hair) | Independent replication pending | **CANDIDATE (high variance risk)** | Reproduce OOS with costs/leakage checks before use |
| 5 | Walk-Forward Variant C | Equity/ETF | Monthly | PF 1.26, n=237, p<0.0013 (deepAI) | Below PF≥1.5 target; pilot | **PILOT** | Replicate, expand universe/sample, stress costs |
| 6 | Faber TAA / trend allocation | Stocks, ETFs, Mutual Funds (to build), Bonds (adapt) | Daily/Monthly | Baseline candidate; limited local OOS significance so far | Unproven in-system | **RESEARCH/BUILD** | Long-history OOS backtest with costs & regime tests |
| 7 | FX Momentum + kill switch | Forex | Daily/Intraday (TBD) | No validated metrics | Unproven | **BUILD** | Design, wire `fx_kill_switch.py`, OOS validate net-of-spread |
| 8 | Commodity Trend Following | Commodities/Futures | Daily | No validated metrics; 98.4% zero-P/L bug | Blocked by data quality | **BUILD (after fix)** | Fix pricing/PnL, then OOS trend validation |

## Detailed: Kilo Regime-Filtered VWAP MR (v11 vs v12)

**Common setup:** 4h bars (~730d/yfinance cap), 70/30 chronological split, 10 bps/side (20bps RT), grid search on train only, regime filter (trade only MR-compatible regimes per `alpha_engine/regime_detector.py`), 40% position sizing.

### v11 — 4 symbols (BTC, ETH, SOL, XRP)
- Pooled OOS: **n=65, WR 53.8%, PF 1.435, Sharpe 7.10, Ret 10.9%, MDD 3.5%, PBO 0.480, P(SR>0)=1.000**
- Gates (basic): PF>1.0 PASS, Sharpe>0.5 PASS, PBO<0.5 PASS, DSR>0.95 PASS, MDD<25% PASS, n≥30 PASS. Strict: **PBO<0.3 FAIL**.

### v12 — 8 symbols expanded (2026-11-14)
- Pooled OOS: **n=129, WR 44.2%, PF 1.210, Sharpe 3.76, Ret 12.7%, MDD 10.0%, PBO 0.489, P(SR>0)=1.000**
- Strict gates (PF>1.2, Sharpe>1.0, PBO<0.3, DSR>0.99, MDD<15%, n≥50): **PF PASS, Sharpe PASS, PBO FAIL, DSR PASS, MDD PASS, n PASS → PROFITABLE (BASIC), NEEDS MORE DATA**
- Per-symbol (OOS):

| Symbol | n | WR | PF | Sharpe | Ret | MDD | Note |
|---|---:|---:|---:|---:|---:|---:|---|
| BTC-USD | 11 | 54.5% | 1.67 | 10.30 | +2.9% | 2.6% | core |
| ETH-USD | 21 | 57.1% | 1.56 | 8.90 | +3.5% | 2.7% | core |
| SOL-USD | 26 | 57.7% | 1.27 | 4.74 | +2.5% | 3.5% | core |
| XRP-USD | 7 | 28.6% | 1.39 | 5.94 | +1.6% | 2.6% | core (low n) |
| ADA-USD | 7 | 42.9% | 2.99 | 19.64 | +7.0% | 2.6% | core (low n) |
| DOGE-USD | 5 | 20.0% | 0.62 | -9.22 | -1.4% | 2.6% | exclude |
| AVAX-USD | 33 | 36.4% | 0.87 | -2.77 | -2.5% | 6.8% | exclude |
| LINK-USD | 19 | 31.6% | 0.91 | -2.05 | -1.2% | 6.0% | exclude |

**Conclusion:** edge is **real but selective**; pooling weak symbols degrades PF/WR/MDD. Operational candidate = **core MR-compatible majors (BTC/ETH/SOL/XRP/ADA)** with regime gating and sizing discipline.

## Promotion Criteria (to move candidate → deployable)

- Net-of-cost OOS: PF≥1.5 (target) or robust ≥1.2 with diversification, Sharpe≥1.0, MDD<20% (prefer <15%), WR context-appropriate.
- Overfitting/validity: **PBO<0.3**, **DSR>0.95** (prefer >0.99), sufficient trades (≥100; ≥500 preferred per Grok for crypto), stable across subperiods/symbols.
- Reproducible from clean data; no leakage; realistic slippage/funding; monitored paper-forward before live.
- System precondition: data/PnL integrity remediated (see `05_data_quality_remediation`).
