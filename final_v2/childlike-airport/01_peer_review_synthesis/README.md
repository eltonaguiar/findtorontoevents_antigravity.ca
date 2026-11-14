# 01 — Peer Review Synthesis

**Date:** 2026-11-14  
**Reviewer:** Kilo (childlike-airport)  
**Inputs:** deepAI, ITERATION-005, Grok, flaxen-hair, hilarious-seer, scratch-hippodraco, plus Kilo local audit/research.

## 1. Peer-by-Peer Findings

### deepAI (audit branch `origin/audit/live-audit-2026-11-14`)
- **Strengths:** strongest data-integrity/ground-truth work (repricing of 624 picks, live audit artifacts).
- **Critical findings:** 81% of open picks showed fake 0% P/L; losses understated ~10x (claimed −106pp vs real −1,116pp); overall PF 0.80; 78.6% EXPIRED zombie rows in active_raw; regime coverage ~0.25%; 7 workflows failing.
- **Positive signal:** walk-forward Variant C (equity/ETF) PF 1.26, n=237, p<0.0013 — pilot-level edge, below PF≥1.5 target but statistically suggestive.
- **Assessment:** **Credible on system failure; cautious optimism on Variant C only after replication.**

### ITERATION-005
- **Contribution:** vol-targeted time-series momentum on 10 crypto over 7.4 years (50d+200d SMA, 20% vol target, 0.1% cost/side).
- **Results:** CAGR 23.0%, Sharpe 2.13, PF 1.40, MDD −17.4%, t=5.56, bootstrap Sharpe CI [1.25,3.25].
- **Assessment:** **Most compelling diversified research evidence.** Needs production implementation, realistic execution/slippage modeling, and live/paper forward test.

### Grok
- **Contribution:** implementation/roadmap framing and stricter validation targets (e.g. n≥500 crypto, PF≥1.5, Sharpe≥1.0, WR≥50%, MDD<20%, PBO<0.3, DSR>0.95).
- **Assessment:** **Useful bar-setting;** highlights that several candidates (VWAP v11/v12, Variant C) do not yet clear all strict gates (notably PBO/sample size/PF thresholds).

### flaxen-hair
- **Contribution:** `mega_mutation_macd_rsi` / `ema_momentum` (CRYPTO) reported PF 3.12–5.816 backtest, 8.32 forward, WR 84%.
- **Assessment:** **High-upside candidate but high skepticism required** (possible selection bias/leakage/forward-definition ambiguity). Must be independently reproduced OOS with costs and strict gates before promotion.

### hilarious-seer / scratch-hippodraco
- **Contribution:** peer review context and corroboration around validation discipline and data-quality concerns.
- **Assessment:** **Supportive/consistent** with the consensus that aggregate performance claims are unreliable without remediation.

### Kilo (childlike-airport)
- **Contribution:** ML/pick/DB audit (stale 172d snapshot, PnL sign/calc mismatches, missing asset classes, empty audit trail, sync bugs) and empirical strategy search.
- **Result:** Regime-Filtered VWAP MR (4h crypto). v11 (4 symbols, n=65): PF 1.435, Sharpe 7.10, MDD 3.5%, PBO 0.480, P(SR>0)=1.000. v12 (8 symbols, n=129): PF 1.210, Sharpe 3.76, MDD 10.0%, PBO 0.489, P(SR>0)=1.000; core profitable set BTC/ETH/SOL/XRP/ADA, losers DOGE/AVAX/LINK.
- **Assessment:** **Real but regime/symbol-dependent edge;** basic gates pass, strict PBO<0.3 fails due to sample/data horizon (yfinance 730d cap). Viable as a constrained candidate, not yet “proven” to strict T2.

## 2. Areas of Agreement

- **Aggregate system is unprofitable/unreliable today** (PF ~0.80 class, widespread fake/incorrect PnL, zombies, stale data).
- **Data integrity remediation is prerequisite** to any credible performance claim.
- **Profitable edges, if any, are narrow and strategy-specific**, not a property of the 683-strategy zoo.
- **Rigorous OOS validation, costs, and overfitting controls (PBO/DSR, sample size, MDD)** are mandatory.

## 3. Areas of Disagreement / Uncertainty

- **Strength/portability of specific edges:** deepAI Variant C (pilot), flaxen-hair mega_mutation (very strong but needs replication), Kilo VWAP (sensitive to symbol set/timeframe/regime filter).
- **How close we are to “production profitable”:** ITERATION-005 is strong in research; others range from pilot to basic-pass. None unanimously clear all strict T2 gates end-to-end.
- **Optimal crypto stack:** VWAP-MR (mean-reversion, regime-filtered) vs TSMOM (trend, vol-targeted) — likely complementary/ensemble, but untested together here.

## 4. Synthesized Verdict

| Claim | Status |
|---|---|
| “The platform is currently profitable” | **Rejected** (aggregate evidence) |
| “Statistically valid profitable approaches exist” | **Supported (component-level)** — TSMOM (strongest research), VWAP-MR (basic-validated, conditional), Variant C (pilot) |
| “Ready for live capital deployment” | **No** — requires data fixes, replication, paper trading, and strict-gate clearance |

## 5. Implications for final_v2

- Treat **ITERATION-005 TSMOM** and **Kilo Regime-Filtered VWAP-MR (core symbols)** as primary crypto candidates; **Variant C** as equity/ETF pilot.
- Require **independent reproduction + cost/slippage stress + expanded sample (resolve PBO)** before promotion.
- Prioritize `05_data_quality_remediation` and `06_statistical_validation_framework` as gates for `04_implementation_roadmap`.
