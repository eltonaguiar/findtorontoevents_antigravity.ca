# Crypto — Profitability Assessment & Recommendation

**Date:** 2026-11-14 | **Status:** Strongest component-level evidence, but conditional and not yet strict-T2 complete

## Current State (evidence)
- `data/live_picks.db`: CRYPTO 101 rows; all stale ~172d, with PnL/sign/calc defects and zombie/EXPIRED dominance in broader universe.
- Despite system-level failure, multiple independent analyses find **strategy-level** edges in crypto slices.

## Evidence of Edge

| Approach | Source | Key results | Verdict |
|---|---|---|---|
| Regime-Filtered VWAP Mean Reversion (4h, 40% sizing, 20bps RT) | Kilo v11 | BTC/ETH/SOL/XRP, n=65, WR 53.8%, PF **1.435**, Sharpe **7.10**, Ret 10.9%, MDD **3.5%**, PBO **0.480**, P(SR>0)=**1.000** | **PROFITABLE (basic)** — passes PF/Sharpe/MDD/DSR/trades; strict PBO<0.3 unmet |
| Regime-Filtered VWAP MR (4h, expanded) | Kilo v12 (2026-11-14 run) | 8 symbols pooled: n=129, WR 44.2%, PF **1.210**, Sharpe **3.76**, Ret 12.7%, MDD **10.0%**, PBO **0.489**, P(SR>0)=**1.000**. Per-symbol: BTC PF1.67/Sharpe10.30, ETH 1.56/8.90, SOL 1.27/4.74, XRP 1.39/5.94, ADA 2.99/19.64 (profitable core) vs DOGE 0.62, AVAX 0.87, LINK 0.91 (losers) | **PROFITABLE (basic), symbol-dependent** — adding weak symbols dilutes edge; strict PBO<0.3 fails |
| Vol-Targeted Time-Series Momentum (50d+200d SMA, 20% vol target, 0.1% cost/side) | ITERATION-005 | 10 crypto, 7.4y: CAGR **23.0%**, Sharpe **2.13**, PF **1.40**, MDD **−17.4%**, t=5.56, bootstrap CI **[1.25,3.25]** | **PROVEN in research** — strongest diversified evidence; needs production/live validation |
| mega_mutation_macd_rsi / ema_momentum | flaxen-hair | PF **3.12–5.816** backtest, **8.32** forward, WR **84%** | **CANDIDATE** — high potential but requires independent OOS reproduction, leakage/cost checks |

## Interpretation
- **VWAP-MR:** real mean-reversion edge when **regime-filtered** (MR-compatible regimes) and **position-sized** (40% in tests); raw/unfiltered variants degrade. Edge concentrated in liquid majors (BTC/ETH/SOL/XRP/ADA). PBO ~0.48-0.49 limited by sample/horizon (yfinance ~730d 4h cap).
- **TSMOM:** complementary trend edge, diversified and long-horizon — attractive core allocator if executed as specified.
- **Combination hypothesis:** MR (VWAP, regime-gated) + trend (vol-targeted TSMOM) may diversify; **not yet tested as an ensemble here**.

## Recommendation
- **Primary (near-term, controlled):** Deploy **Regime-Filtered VWAP MR** on **core symbols only (BTC, ETH, SOL, XRP, ADA)** in paper/shadow mode; keep 40% sizing, 20bps+ cost assumption, strict regime gating.
- **Primary (core research-to-prod):** Productionize **Vol-Targeted TSMOM** per ITERATION-005 spec and run forward/paper validation.
- **Candidate (replicate first):** Independently revalidate **mega_mutation_macd_rsi/ema_momentum** OOS with full costs.
- **Do not:** extrapolate v12 pooled (all 8) performance as-is; exclude persistent losers or require per-symbol positive expectancy.

## Gaps to Clear (strict/T2)
- Increase sample/history (exchange data > 730d) to drive **PBO < 0.3** and stabilize estimates.
- Confirm **net-of-realistic-fees/slippage/funding**; stress costs (e.g. 30–50bps RT).
- Reach/justify **PF≥1.5, WR≥50%** targets where applicable (v11 closer on PF; WR varies) and maintain **MDD<20%**.
- Live/paper forward period with monitoring before any capital allocation.
