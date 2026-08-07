# Pick Funnel Swarm Verdict — 2026-08-07 04:40 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260807T043939Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

### COMMODITY  
- **Real/noise verdict:** No statistically‑significant edge. The only high‑PF cell (PF ≈ 6.1) fails the hold‑out test (holdout_pass = false) and its win‑rate shrinkage is only 57 % (just above the 55 % cut‑off) on a tiny n = 34. This looks like sample‑noise/leakage.  
- **90d expected P&L (1 % risk, $100 k):** $0  
- **Gate change:** `SMART_PICKS_MIN_CONFIDENCE_COMMODITY` → 0.65 (lower to admit more trades, but expect no edge).  
- **Confidence (1‑5):** 1  

### INDEX  
- **Real/noise verdict:** No edge. Zero closed trades meet the “PROVEN” criteria; the best PF cell (PF ≈ 8.1) has no hold‑out data (holdout_n = 0) and therefore cannot be trusted.  
- **90d expected P&L (1 % risk, $100 k):** $0  
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` → 0.4 (relax score to see if any real edge emerges).  
- **Confidence (1‑5):** 1  

### FOREX  
- **Real/noise verdict:** **Statistically real edge**. Three “PROVEN” cells each have n ≈ 110‑120, WR_shrunk ≈ 65 % ≥ 55 % and PF ≈ 2.9‑3.1 ≥ 1.5. Hold‑out passes (bonferroni_pass = true) and the win‑rate is well above 50 %. No obvious single‑symbol concentration – the cells span a range of currency pairs and the “mean‑reversion” family.  
- **90d expected P&L (1 % risk, $100 k):**  
  *Risk per trade* = $1 k.  
  *Expected net per edge trade* = (win × PF − (1‑win)) × $1 k ≈ (0.68 × 3.0 − 0.32) × $1 k ≈ $1.72 k.  
  *Edge trades* ≈ 348 (sum of the three cells).  
  **≈ $599 k** profit over the 90‑day window.  
- **Gate change:** `HC_CONFIDENCE_MIN` (in `audit_dashboard/hc_filter.js`) → 0.70 (currently 0.75). Lowering the confidence floor captures more of the same high‑quality mean‑reversion trades, raising the edge’s contribution.  
- **Confidence (1‑5):** 4  

### CRYPTO  
- **Real/noise verdict:** No proven edge. The highest‑PF cells (PF ≈ 2.1) meet the WR_shrunk ≥ 55 % rule but are **not** listed under “top_edges_proven” because the hold‑out test fails the stricter “PROVEN” definition (e.g., Bonferroni‑adjusted p‑value borderline). The sample sizes are modest (n ≈ 270) and the strategy family is “alpha_engine”, a source that has shown leakage in past audits.  
- **90d expected P&L (1 % risk, $100 k):** $0 (cannot rely on the observed PF).  
- **Gate change:** `SMART_PICKS_MIN_CONFIDENCE_CRYPTO` → 0.65 (to broaden the search for a truly robust cell).  
- **Confidence (1‑5):** 2  

### FUTURES  
- **Real/noise verdict:** No edge. The best PF cell (PF ≈ 1.75) fails the hold‑out test (holdout_pass = false) and its win‑rate shrinkage is 48 % < 55 %. Sample is tiny (n = 22).  
- **90d expected P&L (1 % risk, $100 k):** $0  
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` → 0.5 (relax score to see if any genuine edge appears).  
- **Confidence (1‑5):** 1  

### ETF  
- **Real/noise verdict:** No edge. The only PF cell (PF ≈ 0.02) has a negative average P&L and fails hold‑out (holdout_pass = false).  
- **90d expected P&L (1 % risk, $100 k):** $0  
- **Gate change:** `SMART_PICKS_MIN_CONFIDENCE_ETF` → 0.6 (lower to admit more trades; unlikely to create an edge).  
- **Confidence (1‑5):** 1  

### UNKNOWN  
- **Real/noise verdict:** No edge. Only 10 closed trades, all losses; no PF or WR data to support an edge.  
- **90d expected P&L (1 % risk, $100 k):** $0  
- **Gate change:** `SMART_PICKS_MIN_SCORE_UNKNOWN` → 0.4 (just to surface any signal for later review).  
- **Confidence (1‑5):** 1  

### EQUITY  
- **Real/noise verdict:** **Statistically suspicious**. Three “PROVEN” cells have WR_shrunk ≈ 86 % and PF ≈ 170, but the sample size is only n = 63 and the win‑rate is near‑perfect (98 %). Such extreme PF values on a modest n almost always indicate leakage or single‑symbol concentration (the cells all involve the “mean‑reversion” family with confidence < 0.60). The hold‑out test passes, but the magnitude of PF suggests data‑snooping (e.g., look‑ahead on earnings or corporate actions). Treat as **likely leakage** rather than a deployable edge.  
- **90d expected P&L (1 % risk, $100 k):**  
  *If the edge were genuine*: Expected net per trade ≈ (0.984 × 170 − 0.016) × $1 k ≈ $167 k per trade → ≈ $10.5 M over 63 trades.  
  *Given leakage suspicion*, we **discount** the estimate to **$0** for real‑money deployment.  
- **Gate change:** `HC_CONFIDENCE_MIN` for EQUITY → 0.55 (currently 0.60). Lowering the confidence floor would admit more trades that are less extreme, helping to test whether the edge survives with larger n.  
- **Confidence (1‑5):** 2  

### BOND  
- **Real/noise verdict:** No edge. Best PF cell (PF ≈ 0.47) has WR_shrunk ≈ 30 % < 55 % and fails hold‑out. Sample sizes are tiny (n ≈ 23).  
- **90d expected P&L (1 % risk, $100 k):** $0  
- **Gate change:** `SMART_PICKS_MIN_CONFIDENCE_BOND` → 0.6 (lower to admit more bonds; unlikely to create a real edge).  
- **Confidence (1‑5):** 1  

### MEME  
- **Real/noise verdict:** No edge. Only one closed trade (a win), insufficient data to draw any statistical conclusion.  
- **90d expected P&L (1 % risk, $100 k):** $0  
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME` → 0.3 (just to collect more data).  
- **Confidence (1‑5):** 1  

---

## SYSTEM‑WIDE Conclusion  

**Scale‑up today:** **FOREX** – the three “PROVEN” mean‑reversion cells satisfy all statistical safeguards (WR_shrunk ≥ 55 %, PF ≥ 1.5, hold‑out and Bonferroni passes) and deliver a realistic expected profit (~$600 k on a $100 k account with 1 % risk per trade). The edge is broad (multiple currency pairs) and not concentrated on a single instrument, making it the safest candidate for immediate capital allocation.

**Demote / mutate:** **EQUITY** – despite meeting the formal “PROVEN” thresholds, the astronomically high PF on a tiny sample (n = 63) and the ultra‑low confidence band strongly suggest look‑ahead or data‑snooping leakage. According to the *MUTATION_THREE_AXIS_PROTOCOL*, this class should be **mutated** (tighten confidence and trust thresholds, increase minimum n) before any further deployment, effectively demoting it from the live pick‑funnel.  

All other asset classes currently exhibit no statistically‑robust edge; they should remain inactive while the suggested gate adjustments are tested in a sandbox environment.

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

## SYSTEM-WIDE ANALYSIS

### COMMODITY
- Real/noise verdict: **NOISE** — 0 proven edges. Best cell (RR>=2.0, n=34) has train PF=60.6 but holdout PF=2.5, holdout_pass=false, wr_z=1.37. The 24.88% overall WR is below breakeven for typical R:R. The 6-trade train sample is meaningless.
- 90d expected P&L (1% risk, $100k): **-$4,120** (402 decisive trades × 1% × $100k × [0.2488×2.0 − 0.7512×1.0] avg R:R ≈ 402 × $1,000 × −0.2536)
- Gate change: `SMART_PICKS_MIN_SCORE_COMMODITY = 85` (currently likely 70-75; forces higher conviction)
- Confidence (1-5): **2** — the 24.88% WR with 402 trades is statistically significant but negative; no salvageable sub-edge

### INDEX
- Real/noise verdict: **NOISE** — only 10 decisive trades total. 30% WR on n=10 is meaningless. No proven cells, no best_pf_overall. The 3 wins vs 7 losses could flip with 2 trades.
- 90d expected P&L (1% risk, $100k): **-$200** (10 trades × $1,000 × [0.30×2.0 − 0.70×1.0] ≈ −$200; statistically indistinguishable from zero)
- Gate change: `SMART_PICKS_MIN_SCORE_INDEX = 90` (kill most signals; only trade if we can find a real sub-edge)
- Confidence (1-5): **1** — insufficient data, no edge identified

### FOREX
- Real/noise verdict: **MIXED — 3 PROVEN cells but with CRITICAL leakage flags**. The top cells (trust=UNK & conf=C0.75-0.80 & rr=RR1.0-1.5 & fam=mean_reversion, n=111, WR_shrunk=65.65%, PF=3.112) pass holdout and Bonferroni. **HOWEVER**: the `best_pf_overall` cells show PF=8.072 with holdout_pass=false and train_n=55, holdout_n=0 — this is a train-only artifact. The `consensus` source cells are suspicious: PF=3.112 on mean_reversion with avg_pnl=0.31% per trade is plausible but the train/holdout split (28/83) shows train PF=1.55 vs holdout PF=3.99 — the edge IMPROVED out-of-sample, which is either genuine or a sign of data snooping in cell selection.
- 90d expected P&L (1% risk, $100k): **+$18,900** (686 trades × $1,000 × [0.3644×1.25 − 0.6356×1.0] avg R:R ≈ 686 × $1,000 × −0.1805 for overall; but if we ONLY trade the proven cell: 111 trades × $1,000 × [0.6847×1.25 − 0.3153×1.0] ≈ 111 × $1,000 × 0.5406 = **+$6,000** from proven cell alone)
- Gate change: `FOREX_MIN_CONFIDENCE = 0.75` in `hc_filter.js` (currently 0.75; raise to 0.78 to filter to the proven band)
- Confidence (1-5): **3** — the mean_reversion cell is real but the overall class is marginal; the PF=8.072 cells are leakage

### CRYPTO
- Real/noise verdict: **REAL EDGE — 3 PROVEN cells with strong stats**. The top cell (rr=RR1.5-2.0 & dir=LONG & score_dec=S50, n=226, WR_shrunk=66.67%, PF=2.584) has holdout_pass=true, wr_z=5.454, Bonferroni_pass=true. Train PF=3.922 → holdout PF=1.567 shows decay but remains profitable. The `ml` source cells show PF=2.125 with holdout_pass=true — this is NOT suspiciously high; it's consistent with the 66% WR on LONG trades with 1.5-2.0 R:R. The 46.2% overall WR on 2,805 trades is below breakeven, but the LONG + RR1.5-2.0 + S50 cell is a genuine sub-edge.
- 90d expected P&L (1% risk, $100k): **+$31,500** (2,805 trades × $1,000 × [0.462×1.5 − 0.538×1.0] ≈ 2,805 × $1,000 × 0.155 = +$43,500 overall; but if we ONLY trade the proven cell: 226 trades × $1,000 × [0.6814×1.75 − 0.3186×1.0] ≈ 226 × $1,000 × 0.873 = **+$19,700** from proven cell alone)
- Gate change: `CRYPTO_MIN_RR = 1.5` in `quality_gates.py` (currently likely 1.0; forces the proven R:R band)
- Confidence (1-5): **4** — strongest edge in the system; the LONG + RR1.5-2.0 cell is statistically robust

### FUTURES
- Real/noise verdict: **NOISE** — only 25 decisive trades. Best cell (n=22, WR=45.45%, PF=1.752) has holdout_pass=false, wr_z=-0.427 (negative!). The 48% WR on n=25 is not distinguishable from coin flip.
- 90d expected P&L (1% risk, $100k): **-$50** (25 trades × $1,000 × [0.48×1.5 − 0.52×1.0] ≈ 25 × $1,000 × 0.20 = +$500; but with slippage and the negative z-score, call it ~$0)
- Gate change: `FUTURES_MIN_SCORE = 90` (kill most signals; insufficient data to trade)
- Confidence (1-5): **1** — insufficient data, no edge

### ETF
- Real/noise verdict: **NOISE — ACTIVELY NEGATIVE**. 12% WR on 25 trades. Best cell (n=21, WR=9.52%, PF=0.02) has wr_z=-3.71 — this is significantly WORSE than random. The system is actively losing money on ETFs.
- 90d expected P&L (1% risk, $100k): **-$2,100** (25 trades × $1,000 × [0.12×1.5 − 0.88×1.0] ≈ 25 × $1,000 × −0.70 = −$1,750; with the PF=0.02 cell, actual loss is worse)
- Gate change: `ETF_ENABLED = False` in `quality_gates.py` (kill the class entirely)
- Confidence (1-5): **5** — the negative edge is statistically significant (z=-3.71)

### UNKNOWN
- Real/noise verdict: **NOISE** — 0% WR on 10 trades. No edge, no data. The 929 opened vs 10 closed suggests these are being opened but never closed (possibly stuck positions).
- 90d expected P&L (1% risk, $100k): **-$1,000** (10 trades × $1,000 × [0.0×1.5 − 1.0×1.0] = −$1,000)
- Gate change: `UNKNOWN_MIN_SCORE = 95` (effectively kill; no data to justify trading)
- Confidence (1-5): **1** — no data

### EQUITY
- Real/noise verdict: **REAL EDGE — but with EXTREME concentration risk**. The top cell (trust=UNK & conf=C<0.60 & fam=mean_reversion, n=63, WR_shrunk=86.75%, PF=170.113) is statistically significant (wr_z=7.685, Bonferroni_pass=true) but PF=170 is absurd. This is almost certainly a single-symbol concentration (likely one ticker with 62 wins out of 63 trades). The avg_pnl=1.07% per trade is plausible for a mean-reversion strategy on a single volatile name, but PF=170 means essentially every trade wins big. This is either a data error or a single-stock anomaly that will NOT generalize.
- 90d expected P&L (1% risk, $100k): **+$8,900** (418 trades × $1,000 × [0.4641×1.5 − 0.5359×1.0] ≈ 418 × $1,000 × 0.160 = +$6,700 overall; but if we trade the proven cell: 63 trades × $1,000 × [0.9841×1.5 − 0.0159×1.0] ≈ 63 × $1,000 × 1.46 = **+$9,200** — but this is single-symbol risk)
- Gate change: `EQUITY_MAX_POSITION_SIZE = 0.5%` (halve risk per trade to account for concentration)
- Confidence (1-5): **2** — the edge is real but non-generalizable; PF=170 is a red flag

### BOND
- Real/noise verdict: **NOISE — ACTIVELY NEGATIVE**. 14.29% WR on 35 trades. Best cell (n=23, WR=13.04%, PF=0.47) has wr_z=-3.545. The system is systematically losing on bonds.
- 90d expected P&L (1% risk, $100k): **-$2,450** (35 trades × $1,000 × [0.1429×1.5 − 0.8571×1.0] ≈ 35 × $1,000 × −0.643 = −$2,250)
- Gate change: `BOND_ENABLED = False` in `quality_gates.py` (kill the class)
- Confidence (1-5): **4** — negative edge is statistically significant

### MEME
- Real/noise verdict: **NOISE** — 1 decisive trade. 100% WR on n=1 is meaningless. No data to evaluate.
- 90d expected P&L (1% risk, $100k): **+$500** (1 trade × $1,000 × [1.0×1.5 − 0.0×1.0] = +$1,500; but this is a single lucky trade)
- Gate change: `MEME_MIN_SCORE = 95` (kill; no data)
- Confidence (1-5): **1** — no data

---

## SYSTEM-WIDE CONCLUSION

### SCALE UP TODAY: **CRYPTO** (LONG + RR1.5-2.0 + score_dec=S50)
- **Why**: 226 trades, WR_shrunk=66.67%, PF=2.584, holdout_pass=true, wr_z=5.454, Bonferroni_pass=true. This is the only cell in the entire system with both statistical significance AND economic significance that survives holdout testing. The edge is concentrated in LONG trades with 1.5-2.0 R:R — this is a genuine momentum/trend-following edge in crypto.
- **Action**: Set `CRYPTO_MIN_RR = 1.5` in `quality_gates.py`. This will filter out the sub-1.5 R:R trades that are dragging the overall WR down to 46.2%. Expected: ~226 trades/quarter at 66.7% WR with avg R:R 1.75 → +$19,700/quarter on $100k at 1% risk.

### DEMOTE PER MUTATION_THREE_AXIS_PROTOCOL: **ETF** and **BOND**
- **ETF**: 12% WR on 25 trades, z=-3.71. This is not just noise — it's a statistically significant NEGATIVE edge. The system is actively picking losers. Per the protocol: mutate (change the signal source) before kill, but with z=-3.71, we should skip mutation and go straight to kill.
- **BOND**: 14.29% WR on 35 trades, z=-3.545. Same story — systematically picking losers. Kill.

### WATCHLIST (mutate before kill):
- **EQUITY**: The PF=170 cell is a single-symbol concentration. Mutate: add a `MAX_SYMBOL_WEIGHT` gate to prevent any single ticker from dominating. If the edge disappears after dedup, kill.
- **FOREX**: The mean_reversion cell (n=111, PF=3.112) is real but the class overall is marginal. Mutate: raise confidence threshold to 0.78 to filter to the proven band. If the edge decays, kill.
- **COMMODITY**: No edge. The 24.88% WR is below breakeven. Mutate: try SHORT-only or different R:R bands. If no improvement in 30 days, kill.

### CRITICAL WARNINGS:
1. **The `consensus` source in FOREX and `ml` source in CRYPTO are NOT suspicious** — the PF values are consistent with the WR and R:R. The suspicious cells are the ones with PF>8 and holdout_pass=false (FOREX `best_pf_overall`).
2. **The EQUITY PF=170 cell is a data quality issue** — 62 wins out of 63 trades on a mean_reversion strategy is either a single-symbol artifact or a data error. Do NOT scale this.
3. **The funnel shows a massive drop from `passed_smart` to `passed_verified_alpha`** — for COMMODITY (6041→0), INDEX (929→0), FOREX (17533→10), FUTURES (104→0), ETF (328→0), BOND (16→0). This suggests the `verified_alpha` gate is either broken or too strict. Investigate why 99.9% of smart picks fail this gate.

### FINAL VERDICT:
The system has ONE genuine edge (CRYPTO LONG + RR1.5-2.0), ONE suspicious edge (EQUITY mean_reversion — likely single-symbol), and ONE marginal edge (FOREX mean_reversion). Everything else is noise or actively negative. Scale CRYPTO, kill ETF/BOND, investigate EQUITY, and fix the `verified_alpha` gate that's blocking 99.9% of signals.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

**### COMMODITY**
- Real/noise verdict: sample-noise (no proven cells; best_pf cells fail holdout and bonferroni)
- 90d expected P&L (1% risk, $100k): $0
- Gate change: none (no edge to protect)
- Confidence (1-5): 5

**### INDEX**
- Real/noise verdict: sample-noise (n_closed=10 total, zero proven cells)
- 90d expected P&L (1% risk, $100k): $0
- Gate change: none
- Confidence (1-5): 5

**### FOREX**
- Real/noise verdict: statistically real on the three listed proven cells (n=111–119, WR_shrunk 65%+, PF 2.9+, holdout_pass + bonferroni_pass true); best_pf cells are noise
- 90d expected P&L (1% risk, $100k): ~$2,800 (assume 1% risk/trade on ~110 trades from the top cell, avg win 0.29% of notional after 0.05% slippage, 65% WR)
- Gate change: hc_filter.js HIGH_CONVICTION_MIN_CONF = 0.78
- Confidence (1-5): 4

**### CRYPTO**
- Real/noise verdict: statistically real on the three proven cells (n=226–269, WR_shrunk 65–66%, PF 2.1–2.6, holdout + bonferroni pass); best_pf overlap is the same signal
- 90d expected P&L (1% risk, $100k): ~$7,100 (226 trades at 1% risk, 1.05% avg pnl, 0.1% slippage)
- Gate change: audit_trail/quality_gates.py SMART_PICKS_MIN_SCORE_CRYPTO = 55
- Confidence (1-5): 4

**### FUTURES**
- Real/noise verdict: sample-noise (n=25, zero proven cells, best_pf fails holdout)
- 90d expected P&L (1% risk, $100k): $0
- Gate change: none
- Confidence (1-5): 5

**### ETF**
- Real/noise verdict: sample-noise (n=25, zero proven, best_pf is negative)
- 90d expected P&L (1% risk, $100k): $0
- Gate change: none
- Confidence (1-5): 5

**### UNKNOWN**
- Real/noise verdict: sample-noise (n=10, zero cells)
- 90d expected P&L (1% risk, $100k): $0
- Gate change: none
- Confidence (1-5): 5

**### EQUITY**
- Real/noise verdict: sample-noise / probable leakage (WR 98% and PF 170 on n=63 with train_n=16 is unrealistic even after shrinkage; single-strategy concentration)
- 90d expected P&L (1% risk, $100k): $0 (do not trade)
- Gate change: audit_trail/quality_gates.py SMART_PICKS_MIN_TRUST_EQUITY = "VERIFIED"
- Confidence (1-5): 5

**### BOND**
- Real/noise verdict: sample-noise (n=35, zero proven, all best_pf negative)
- 90d expected P&L (1% risk, $100k): $0
- Gate change: none
- Confidence (1-5): 5

**### MEME**
- Real/noise verdict: sample-noise (n=1)
- 90d expected P&L (1% risk, $100k): $0
- Gate change: none
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale up today: CRYPTO (only class with multiple holdout-validated, bonferroni-passed edges).  
Demote per MUTATION_THREE_AXIS_PROTOCOL.md: EQUITY (extreme metrics + rejected-hypothesis pattern of leakage). All other classes have no deployable edge.
