# Round 3 Review — D.E. Shaw lens (event-driven + alt-data)

## 1. OVER-weighted

The merge promotes COT positioning to "unanimous highest-conviction edge" (Strong Convergence #1, lines 13-24) as if it were a proprietary alt-data find. COT is a weekly CFTC public release with T+3 staleness — half the systematic CTA universe (DBMF, KMLM, AHL) already extracts the same signal. Treating it as DE-Shaw-grade alt-data inflates conviction; it is consensus-trend-following dressed up. The merge also leans hard on COT to justify a single-contract CT=F live promo on n=750 — the breadth-of-bets is one instrument, not a class.

## 2. UNDER-weighted

Cross-sectional **EQUITY earnings PEAD** appears only as a Day-1 sleeve in the priority table (line 87) and gets no synthesis treatment, even though it is the one place this stack has structurally-mispriced alt-data exposure: estimize, EPS-revision velocity, post-call transcript sentiment, options-skew pre-event. Zero mention of options IV-rank, dark-pool prints, or 13F drift — all cheaper to source than the COT lift currently being celebrated.

## 3. BLIND SPOT across all 7 personas

**Nobody costed the data and infrastructure bill.** The merge ships CPCV+PBO+DSR enforcement, tick warehouse, HMM regime gating, per-class calibrators, stacked LGBM+XGB+CatBoost, PEAD sleeve, FX triangular pairs — without a single line on storage, compute, or vendor spend. A tick warehouse for EQUITY top-100 alone is ~2-4 TB/yr at Polygon/Databento rates ($300-1,500/mo). Per-class calibrators + CPCV blow up training compute 10-20x vs current single-fold. We are also one Yahoo/yfinance rate-limit-tightening or COT-format-change away from a silent data outage with no failover — the resolver-v2 bug pattern repeating. No persona named vendor concentration risk or a $/edge-bp budget. The whole plan assumes free infra.

---

**Summary (30w):** Merge over-weights COT-as-alt-data (it's public + crowded) and under-weights equity PEAD + options-skew. Universal blind spot: nobody budgeted storage, compute, or data-vendor concentration risk.
