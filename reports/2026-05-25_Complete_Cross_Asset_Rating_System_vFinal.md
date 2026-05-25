# Complete Cross-Asset 1-10 Pick Rating System + Quant Vetting
**Version:** Final (2026-05-25)  
**Status:** Consolidated deliverable after 3-round swarm review + deep DB investigation + rigorous Quant critique

---

## Executive Summary

This document consolidates the full body of work from the session:

- 6 realistic hedge-fund personas for idea generation across asset classes.
- A unified, explainable **1-10 pick rating / tier list system** using five sub-scores (Edge_Quality, Regime_Fit, Calibration, Risk_Adjusted, Diversification) + class-specific factors.
- Concrete algorithm designs for **all major asset classes** (Equity, ETF, Crypto, Forex, Commodity, Futures, Bond) plus a strict high-risk bucket for Penny Stocks, Cheap Stocks, and IPOs.
- Grounding in actual database findings from `ejaguiar1_stocks` (top edge concentrated in narrow strategies like `ml_crypto_predictor` and `mega_mutation`; broad scores like `elite_score` show near-zero correlation with realized PnL).
- Full Quant vetting against a professional 4-phase institutional workflow (Data Intake → Exploratory Analysis → Model Development → Production-Ready Implementation).
- Clear remediation recommendations for the Smart Picks feature on `/audit` (currently running on stale April 30 data with self-admitted unverifiable edge).

The system is designed to be:
- Regime-aware and calibration-corrected (directly addressing documented inversion and concentration problems).
- Persona-tunable.
- Auditable and production-wirable (with explicit first callers and self-backtest requirements).

---

## 1. The Six Hedge Fund Personas

1. **Elena Vargas** — Global Macro PM (regime + geopolitics + liquidity overlays)
2. **Marcus Chen** — Quantitative Factor PM (statistical purity, regime filters, narrow proven edges)
3. **Priya Sharma** — Fundamental L/S Analyst (bottom-up quality + catalysts + technical timing)
4. **David Okonkwo ("D-Risk")** — Risk & Volatility Overlay (MDD control, correlation, tail hedging)
5. **Sofia Reyes** — Thematic/Growth Allocator (secular trends + momentum + flows)
6. **Jian Li** — Sector/Event-Driven Specialist (deep industry + catalyst timing on proven patterns)

Each persona has different optimal weightings on the same sub-score framework.

---

## 2. Unified 1-10 Rating Framework (Core Design)

**Sub-Scores (0-10 each):**
- **Edge_Quality** — Historical closed performance of the generating strategy/family (anchored in real DB + edge_stability/pf_registry data; only narrow proven families qualify as "Golden Signals").
- **Regime_Fit** — Alignment with class-specific regime signals (VIX+YC for Equity, BTC dominance + real yields for Crypto, term structure + COT for Commodities, etc.).
- **Calibration** — Historical accuracy of similar signals in the current regime (explicit fix for confidence inversion).
- **Risk_Adjusted** — Inverse of expected drawdown/volatility in the regime.
- **Diversification** — Penalty for strategy-family and symbol concentration.

**Composite** = weighted average (weights persona-tunable) → normalized to 1-10.

**Tiering:** S (9.0+), A (7.5–8.9), B (6.0–7.4), C (4.0–5.9), D (<4.0)

**Hard Rules (Anti-Patterns):**
- No raw "confidence" without Calibration correction.
- New strategy families require n ≥ 30 resolved + WR ≥ 50% before any meaningful Edge_Quality.
- Golden Signals list is narrow and class-specific.

---

## 3. Rating Algorithms by Asset Class

### Equity
- Heavy weight on proven breakout/contraction families (donchian, rs-breakout, vol-contraction scouts from 05-16 validation: 72–78% WR, PF 6.4–7.1).
- Regime_Fit dominated by VIX + Yield Curve filter (82.14% WR / PF 25.51 / MDD 2.28% in best backtest config).
- Strong Calibration emphasis due to documented inversion.

### ETF
- Similar to Equity but with higher emphasis on sector rotation + flow signals.
- Regime_Fit remains very high weight (ETFs are excellent vehicles for expressing proven macro regimes).

### Crypto
- Regime_Fit: BTC dominance + real yields/DXY + Fear & Greed extremes.
- Edge_Quality: Funding rate arbitrage + on-chain momentum + narrow proven families (e.g., `ml_crypto_predictor` and `mega_mutation` showed the strongest realized edge in DB analysis: +1.88% to +2.64% avg PnL).
- Very heavy Risk_Adjusted + liquidity filters. Most names capped at 6–7 unless multiple structural factors align.

### Forex
- Regime_Fit: DXY strength + interest rate differentials + COT extremes.
- Edge_Quality: Carry + COT positioning families (DB showed `alpha_engine` and `non_crypto_consensus` as relatively better, while broad copy-trader systems were deeply negative).
- Extremely conservative overall. Acts as a natural kill-switch for weak classes.

### Commodity
- Shift emphasis to structural factors: term structure/contango, roll yield, COT, seasonal.
- Regime_Fit: Inflation/growth + USD regime.
- Note: Historically strong (PF 4.31 in edge_stability) but recent data collapsed — requires dedicated structural engine rather than equity-style momentum logic.

### Futures
- Route through most relevant class (Equity index futures → Equity logic; energy/ag → Commodity logic) + add roll-yield and contract-specific liquidity overlay.

### Bonds
- Primarily defensive. Tiny historical n. Only elevated in extreme rate-volatility regimes.

### High-Risk Bucket (Penny Stocks, Cheap Stocks, IPOs)
**Separate strict module** (most names should score 1–4):
- Edge_Quality: Near-zero base (almost no proven historical families on these names).
- Heavy Risk_Adjusted + structural penalties:
  - Hard liquidity floor (ADV minimum).
  - Dilution risk (recent offerings, ATM, convertibles).
  - Promoter/SEC/auditor flags.
  - Lockup expiration risk (for IPOs).
  - Short interest + borrow availability.
- Only exceptional catalyst + clean structure + liquidity cases allowed above 6.
- Treated as tactical satellite allocation only.

---

## 4. Quant Vetting Against Professional Workflow

The full proposed system was stress-tested by a senior quant reviewer against the exact 4-phase institutional process you provided.

**Summary of Critique:**
- **Phase 1 (Data Intake)**: Weakest area. Framework assumes cleaner historical inputs than currently exist (resolver gaps, small resolved n, `sp_*` tables empty, pre-v2 pollution). Would amplify noise if fed raw data.
- **Phase 2 (Exploratory)**: Partial credit. Correctly diagnoses inversion and concentration but does not yet mandate fresh purged EDA + sub-strategy decomposition before scoring.
- **Phase 3 (Model Development)**: Conceptually strong (sub-scores, Golden Signals/narrow edge focus, persona tunability, anti-patterns). However, risks creating another broad score layer on top of narrow, fragile edges.
- **Phase 4 (Production)**: Strongest area (explicit wiring plan, first callers in `production_scanner.py` and `regime_position_sizer.py`, self-backtest requirement, feature flags). Still blocked by upstream data quality.

**Key Recommendations from Vetting:**
- Implement the 30-day MVP (Equity Golden Signals + Quant weights + one column in scanner + self-backtest on the 252 closed trades) behind a strict flag first.
- Fix resolver gaps and sp_* freshness before expanding to other classes.
- Complete Forex mutation rescue and Commodity structural engine before full cross-asset rollout.
- For the high-risk bucket: Treat as a filter more than a rating system (most names 1–4 by design).

**Concrete Example Provided (Momentum + Macro Pipeline):**
ATR-normalized momentum with macro regime overlay, only boosting narrow proven families in favorable conditions. Full pseudo-code available in the subagent output.

**Risk-Budgeting Pitfalls Identified:**
Static correlations, liquidity/vol mismatch across buckets (especially penny/IPO), look-ahead in live portfolio_state, non-stationary edge, failure to integrate mutation/kill gates.

**Robust Validation Process Recommended:**
Purged/embargoed walk-forward with regime-stratified folds, monotonic lift requirement for high-rated buckets, calibration plots, concentration impact measurement, and live sandbox testing before any production wiring.

---

## 5. Smart Picks Remediation Recommendations (from DB + Code Audit)

1. **Immediate**: Stop prominently featuring Smart Picks or make staleness extremely visible (large red banner when feed >4–6 hours old).
2. **High Priority**: Either deprecate the current presentation or relabel it clearly as "Experimental Unverified Overlay."
3. **Data Quality**: Fix the database-backed `sp_*` pipeline or explicitly document that the feature runs on a static file.
4. **Transparency**: Add prominent warnings that historical edge cannot be verified due to missing fields in closed records.
5. **Longer Term**: Only promote once resolver gaps are closed, fields are properly logged going forward, and the selection shows monotonic lift in a clean out-of-sample test on resolved data.

---

## 6. Implementation Path (Wiring)

- Module: `alpha_engine/pick_rating_engine.py`
- First production caller: `production_scanner.py` (attach score/tier/drivers before emission).
- Second caller: `regime_position_sizer.py` (use Diversification + Risk_Adjusted for dynamic sleeves).
- Mandatory: Self-backtest report on clean resolved data before any PR merge.
- Feature flag + opt-in initially.

Any PR must contain a clear **Wiring Plan** section.

---

## 7. Final Deliverables from This Session

- Master consolidated specification (this document).
- Living transcript of the 3-round swarm review process (`reports/2026-05-25_swarm_review_transcript.md`).
- Supporting deep-dive reports (UI audit, DB edge analysis, persona survey, etc.).

**Status:** All planned work (designs + high-risk bucket + full Quant vetting against professional workflow + DB grounding + remediation) is complete.

---

*End of Final Consolidated Report*