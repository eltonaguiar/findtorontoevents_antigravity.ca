# final_v3 — childlike-airport

**Date:** 2026-11-14  
**Reviewer:** Kilo (childlike-airport)  
**Scope:** Cross-review of files modified today (local + GitHub commits on `origin/main`), all `final_v2` packages, `2026-11-14/*` audit/research folders, `research/profitability/*`, and relevant untracked financial-prediction artifacts.

## Decision (evidence-based)
- **No asset class or strategy is money-ready/proven-profitable today** in the live/aggregate system. Common blockers: broken/stale PnL & data pipeline, zombie/expired pollution, near-empty audit trail, single-source concentration, benchmark-relative alpha not proven, and multiple-testing/overfitting risks.
- **Most credible candidates to pursue (research → paper):**
  1. **Crypto (daily, diversified): Vol-Targeted Time-Series Trend (TSMOM)** — strongest long-horizon research evidence (ITERATION-005: 7.4y, CAGR 23.0%, Sharpe 2.13, PF 1.40, MDD −17.4%, bootstrap CI [1.25,3.25]); complementary to MR.
  2. **Crypto (intraday 4h, selective): Regime-Filtered VWAP Mean Reversion** — basic-validated but conditional (v11 n=65 PF 1.435 Sharpe 7.10 MDD 3.5% PBO 0.480; v12 n=129 PF 1.210 Sharpe 3.76 MDD 10.0% PBO 0.489, core BTC/ETH/SOL/XRP/ADA profitable, DOGE/AVAX/LINK not). **Not strict-T2** (PBO<0.3 unmet).
- **Beyond mutual funds (pragmatic, high-probability if built correctly):** **low-cost broad-market index trend/rotation** on liquid ETFs/equities (Faber TAA / sector-neutral QVM-style) — ample history, low fees, easy to validate; currently research/pilot only (Variant C pilot PF 1.26 n=237 p<0.0013).
- **Mutual funds (highest-probability low-capital subset, infrastructure exists but NOT a live proven pick class):** no-load, $0-min, ultra-low-ER broad index funds (e.g. **FXAIX 0.015% ER, FSKAX 0.015%, SWPPX 0.02%, SWTSX 0.03%, FXNAX 0.025% bonds**, all $0 min, $0 load/12b-1 per `alpha_engine/data/mutual_fund_metadata.csv`). Current ranker output highlights **SWPPX (T1, score 87.1, ER 0.02%, $0 min)** and **FSKAX (T2, 79.0, ER 0.015%, $0 min)**. *Requires connecting to a live/validated allocation signal; past/risk metrics ≠ guaranteed profit.*

## Contents
- `00_common_themes/` — cross-review themes, bugs, and deeper-investigation items (with sources)
- `01_improvement_plan/` — broad TODO plan: general, GitHub Actions, asset-class-specific, and backtest/simulation per proposed fix
- `02_subq_comparison/` — SubQ-style coverage/comparison matrix and recommendation gate
- `03_focus_and_profitability/` — prioritized focus, 1–2 profitable targets beyond MF, and low-capital/low-fee MF subset
- `04_backtest_simulation/` — simulation specs for each proposed algorithm fix (acceptance criteria)
- `05_evidence/` — reviewed-file inventory and key citations

## Hard Gates Before Any “Profitable” / Deployment Claim
Net-of-realistic-costs OOS: PF≥1.5 target (≥1.2 contextual), Sharpe≥1.0, MDD<20% (prefer <15%), **PBO<0.3**, **DSR>0.95** (prefer >0.99), sufficient n (≥100; ≥500 preferred crypto), stability across subperiods/regimes/symbols, no leakage, benchmark-relative justification, and a monitored paper-forward window. **Fix data integrity first** (see `01_improvement_plan` / `00_common_themes`).
