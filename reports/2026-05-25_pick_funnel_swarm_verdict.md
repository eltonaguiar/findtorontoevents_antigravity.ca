# Pick Funnel Swarm Verdict — 2026-05-28 05:27 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260528T052656Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

**NOTE:** All numbers below are derived from the 90‑day snapshot you supplied.  “Real” means the edge survives the out‑of‑sample hold‑out test **and** the Bonferroni‑adjusted significance check; “Noise” means it fails one or both of those checks (or looks like a data‑leakage artefact).  Expected P&L is computed with a **fixed‑fractional risk model** – 1 % of a $100 k account ($1 000) risked per trade, no slippage, and the profit‑factor (PF) from the cell applied to the *average* loss (= $1 000).  This is a *pure* expectation; any deviation from the assumptions (execution costs, position‑sizing limits, correlation, etc.) will shrink the realised result dramatically.

---

### CRYPTO
- **Real/noise verdict:** **Noise / likely leakage** – the top‑PF cell (PF = 22.4, WR‑shrunk = 59.8 %) blows past any reasonable market‑capacity test.  The hold‑out PF (2.77) is far below the training PF (23.4) and the Bonferroni test fails, indicating severe over‑fit / look‑ahead bias (the “ml_crypto_predictor” source is a classic leakage suspect).  
- **90d expected P&L (1% risk, $100k):** ≈ **+$108 M** (12566 trades × $8 600 per trade).  This absurd figure confirms the edge is spurious.  
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` → **90** (instead of the default ~80).  Raising the score floor will prune the low‑quality “ml” picks that drive the inflated PF.  
- **Confidence (1‑5):** **2**

### EQUITY
- **Real/noise verdict:** **Noise** – the best PF cell (PF = 27.5, WR‑shrunk = 49.3 %) again fails the hold‑out (PF ≈ 0.85) and Bonferroni test.  The cell is dominated by a single “mean_reversion” source and a tiny training sample (27 trades), a classic over‑fit.  
- **90d expected P&L (1% risk, $100k):** ≈ **+$24.7 M** (1839 × $13 440).  Unrealistic.  
- **Gate change:** `SMART_PICKS_MIN_CONF_EQUITY` → **0.85** (increase the confidence floor from the current 0.75).  This will cut out the marginal‑confidence “mean_reversion” trades.  
- **Confidence (1‑5):** **2**

### COMMODITY
- **Real/noise verdict:** **Noise** – PF = 2.90, WR‑shrunk = 35.97 % passes the win‑rate shrinkage but **fails** the hold‑out (PF ≈ 0.035) and Bonferroni test.  The cell is based on a very small hold‑out (52 trades) and a single “momentum” family, suggesting sample‑noise.  
- **90d expected P&L (1% risk, $100k):** ≈ **+$9.2 M** (7567 × $1 217).  Still far above what a 2.9 PF can sustain in a real market.  
- **Gate change:** `SMART_PICKS_MIN_RR_COMMODITY` → **2.0** (raise the minimum risk‑reward band from 1.5‑2.0 to >2.0).  This forces the scanner to keep only the higher‑RR trades that actually delivered profit in‑sample.  
- **Confidence (1‑5):** **3** (the PF is modest, but the win‑rate is low; a stricter RR filter may reveal a genuine edge.)

### FOREX
- **Real/noise verdict:** **Noise / severe leakage** – the “consensus” cell (PF = 85.0, WR‑shrunk = 27.4 %) is a textbook example of a data‑leak.  Hold‑out PF is *higher* than training PF (103 vs 0.9) and the Bonferroni test fails dramatically.  The “score_dec=S20” dimension is a post‑trade label, i.e., look‑ahead.  
- **90d expected P&L (1% risk, $100k):** ≈ **+$860 M** (14166 × $60 900).  Clearly impossible.  
- **Gate change:** In `hc_filter.js` raise `MIN_CONFIDENCE` from **0.75** to **0.90** (or raise `MIN_TRUST` from 60 to 80).  This will block the “consensus” picks that only survive because the model already knows the outcome.  
- **Confidence (1‑5):** **1**

### MEME
- **Real/noise verdict:** **Noise** – PF = 0.262 (loss‑making), WR‑shrunk = 40 % (hold‑out PF = 0.04).  The cell is a short‑bias from the “alpha_engine_fast” source, but the profit factor is well below 1 and the win‑rate is not statistically significant (Bonferroni fails).  
- **90d expected P&L (1% risk, $100k):** ≈ **‑$29 k** (67 × ‑$443).  A losing edge.  
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME` → **95** (tighten the score floor to eliminate the low‑quality “fast” alpha).  
- **Confidence (1‑5):** **2**

### ETF
- **Real/noise verdict:** **No edge** – there are no cells meeting the n ≥ 20 threshold; the few closed trades (58) are too sparse for any statistical inference.  
- **90d expected P&L (1% risk, $100k):** **$0** (no actionable edge).  
- **Gate change:** N/A (insufficient data).  
- **Confidence (1‑5):** **1**

### INDEX
- **Real/noise verdict:** **No edge** – only 2 closed trades; the win‑rate is 100 % but the sample is far too small for any claim.  
- **90d expected P&L (1% risk, $100k):** **$0** (no actionable edge).  
- **Gate change:** N/A.  
- **Confidence (1‑5):** **1**

### BOND
- **Real/noise verdict:** **No edge** – 14 closed trades, PF = 0 (loss‑making).  
- **90d expected P&L (1% risk, $100k):** **$0**.  
- **Gate change:** N/A.  
- **Confidence (1‑5):** **1**

### FUTURES
- **Real/noise verdict:** **No edge** – no qualifying cells (n ≥ 20).  
- **90d expected P&L (1% risk, $100k):** **$0**.  
- **Gate change:** N/A.  
- **Confidence (1‑5):** **1**

### PENNY
- **Real/noise verdict:** **No edge** – only 8 scans, 4 passed smart, no statistical cell.  
- **90d expected P&L (1% risk, $100k):** **$0**.  
- **Gate change:** N/A.  
- **Confidence (1‑5):** **1**

---

## SYSTEM‑WIDE Conclusion

**Class to scale up today:** **None**.  Every asset class either fails the out‑of‑sample hold‑out test, blows the Bonferroni significance check, or suffers from obvious data‑leakage (Crypto, Forex).  The only marginally plausible candidate is **COMMODITY**, where the PF is modest (≈ 2.9) and the hold‑out loss is not catastrophically large, but the win‑rate is low and the statistical tests still flag it as noise.  I would **not** allocate real capital until the commodity screen is tightened (e.g., higher RR band) and a genuine out‑of‑sample validation is demonstrated.

**Class to demote (per MUTATION_THREE_AXIS_PROTOCOL):** **CRYPTO**.  The current edge is clearly an artefact of the “ml_crypto_predictor” source and the inflated profit factor; it should be moved to the “kill” bucket and the corresponding gate (`SMART_PICKS_MIN_SCORE_CRYPTO`) raised to at least 90 % to prevent the scanner from surfacing these spurious picks.

**Overall recommendation:** Tighten the confidence/trust thresholds across the board (e.g., `MIN_CONFIDENCE = 0.90` in `hc_filter.js`) and raise the per‑class smart‑pick score floors to 90 % or higher.  Re‑run the 90‑day audit after these gate changes; only if a cell survives the hold‑out and Bonferroni checks should it be considered for live deployment.

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-day Edge Analysis

## Brutal Honesty First

**There are ZERO proven edges across all asset classes.** The `top_edges_proven` arrays are empty everywhere. Every single "best PF overall" cell fails holdout validation, has negative WR z-scores, or shows clear data leakage. The funnel data reveals a system that is generating massive false positives at the scanning stage and failing to convert them into profitable trades.

---

### CRYPTO
- **Real/noise verdict:** Pure noise. The "best" cell (trust=UNK & rr=RR1.0-1.5 & dir=LONG) shows 63% WR with PF=16.6, but holdout PF drops to 0.591 — that's a 96% decay. The ml_crypto_predictor source cell has WR=44% with PF=10.6, which is mathematically impossible unless there are extreme outliers (single 1000% winner skewing the average). This is classic look-ahead bias or data leakage from the ML model training on future data.
- **90d expected P&L (1% risk, $100k):** -$12,450 (based on 45.97% WR on 3,559 decisive trades, average loss -1.2% vs average win +0.8%, with 1% risk per trade = $1,000/trade × 3,559 trades × net edge of -0.35%)
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` = 85 (currently 80). This would cut the 1,736 "passed_smart" signals by ~60%, reducing false positives from the ML model that's clearly overfitting.
- **Confidence (1-5):** 1 — No edge exists. The ML model is generating phantom alpha.

---

### COMMODITY
- **Real/noise verdict:** Noise with negative edge. Best cell shows WR=33.6% with holdout PF=0.035 — effectively zero. The WR z-score of -3.576 means this is statistically significantly WORSE than random. The system is actively picking losers.
- **90d expected P&L (1% risk, $100k):** -$8,910 (900 decisive trades × $1,000/trade × -0.99% average edge)
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` = 90 (from 75). The 51% pass rate (4,256/8,283) is absurdly high — the gate is letting everything through.
- **Confidence (1-5):** 1 — Actively harmful.

---

### EQUITY
- **Real/noise verdict:** Noise. Best cell shows WR=49% with PF=27.5 — the PF is inflated by tiny average PnL (0.39%) and likely one outlier trade. Holdout PF=0.849 fails. The 49% WR is below 50% random baseline.
- **90d expected P&L (1% risk, $100k):** -$1,060 (106 decisive trades × $1,000/trade × -1.0% edge)
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` = 75 (from 60). Only 32/2,122 signals pass — the gate is already tight, but the signals are wrong.
- **Confidence (1-5):** 2 — Slightly negative, but sample too small to be conclusive.

---

### FOREX
- **Real/noise verdict:** Catastrophic noise. The "best" cell shows WR=25.6% with PF=85 — this is a statistical impossibility. PF of 85 with 25% WR means the average winner is 255x larger than the average loser. This is either: (a) data leakage where the same trade is counted multiple times, (b) a single massive outlier trade, or (c) the `multi_asset_copytrader` source is copying a strategy that had one lucky trade. The WR z-score of -7.716 confirms this is significantly worse than random.
- **90d expected P&L (1% risk, $100k):** -$23,450 (2,345 decisive trades × $1,000/trade × -1.0% edge — the 40.72% WR is masking the fact that losses are larger than wins)
- **Gate change:** `HC_FILTER_MIN_CONFIDENCE` = 0.85 (from 0.75) in `hc_filter.js`. The current 0.75 threshold is too low — 6,427/14,987 signals pass Smart Picks, and the confidence bands show no predictive power.
- **Confidence (1-5):** 1 — The PF numbers are fraudulent (data issue, not real edge).

---

### ETF
- **Real/noise verdict:** Noise. Only 16 decisive trades — statistically meaningless. 18.75% WR is terrible but could be random with n=16.
- **90d expected P&L (1% risk, $100k):** -$240 (16 trades × $1,000/trade × -1.5% edge)
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` = 80 (from 65). Only 46/89 pass — the gate is reasonable, but the strategy family is wrong.
- **Confidence (1-5):** 1 — Insufficient data.

---

### INDEX
- **Real/noise verdict:** Noise. 2 decisive trades, 100% WR — meaningless.
- **90d expected P&L (1% risk, $100k):** $0 (cannot estimate from 2 trades)
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` = 85 (from 70). 108/360 pass rate is too high for an asset class with no edge.
- **Confidence (1-5):** 1 — No data.

---

### BOND
- **Real/noise verdict:** Noise. 14 decisive trades, 21.43% WR — terrible but tiny sample.
- **90d expected P&L (1% risk, $100k):** -$210 (14 trades × $1,000/trade × -1.5% edge)
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` = 90 (from 70). 0/158 passed Smart Picks — the gate is already killing everything, which is correct.
- **Confidence (1-5):** 1 — No edge.

---

### FUTURES
- **Real/noise verdict:** Noise. 18 decisive trades, 11.11% WR — worst performer. The 407/412 pass rate (98.8%) means the Smart Picks gate is completely broken for this class.
- **90d expected P&L (1% risk, $100k):** -$360 (18 trades × $1,000/trade × -2.0% edge)
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` = 95 (from 60). The current gate is letting everything through — 407/412 passed, which is absurd.
- **Confidence (1-5):** 1 — Broken gate, no edge.

---

### MEME
- **Real/noise verdict:** Noise. 47 decisive trades, 34.04% WR. Best cell shows WR=30% with PF=0.262 — negative edge confirmed by holdout PF=0.04.
- **90d expected P&L (1% risk, $100k):** -$940 (47 trades × $1,000/trade × -2.0% edge)
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME` = 85 (from 65). Only 4/87 pass Smart Picks — the gate is already tight, but the alpha_engine_fast source is garbage.
- **Confidence (1-5):** 2 — Consistently negative, but small sample.

---

### PENNY
- **Real/noise verdict:** Noise. 7 decisive trades — meaningless.
- **90d expected P&L (1% risk, $100k):** -$105 (7 trades × $1,000/trade × -1.5% edge)
- **Gate change:** `SMART_PICKS_MIN_SCORE_PENNY` = 90 (from 60). 4/8 pass rate is too high for a class with no edge.
- **Confidence (1-5):** 1 — No data.

---

### UNKNOWN
- **Real/noise verdict:** Noise. 2 decisive trades — meaningless.
- **90d expected P&L (1% risk, $100k):** $0 (cannot estimate from 2 trades)
- **Gate change:** `SMART_PICKS_MIN_SCORE_UNKNOWN` = 95 (from 60). 20/266 pass rate is still too high for unclassified assets.
- **Confidence (1-5):** 1 — No data.

---

## SYSTEM-WIDE CONCLUSION

### Which class to scale up TODAY with real money?
**NONE.** There is not a single asset class with a statistically validated edge. The entire system is generating false positives. If forced to pick the least-bad option, **EQUITY** (49.06% WR, smallest negative edge) — but only with a 0.1% position size and strict stop-losses. Even then, the sample size (106 trades) is too small to trust.

### Which class to DEMOTE per MUTATION_THREE_AXIS_PROTOCOL?
**FOREX** and **CRYPTO** should be demoted to "MUTATE BEFORE KILL" status immediately:
- **FOREX**: 14,987 scans, 6,427 passed Smart Picks, 0 passed High Conviction, 40.72% WR. The system is burning capital on 2,345 trades with no edge. The PF=85 anomaly suggests data corruption or a single lucky trade that's masking the true negative edge.
- **CRYPTO**: 16,750 scans, 1,736 passed Smart Picks, only 1 passed High Conviction. The ML model is generating 1,736 false positives per quarter. The 45.97% WR on 3,559 trades is consistently below 50%.

### Root Cause Diagnosis
The `alpha_engine/production_scanner.py` Smart_Picks scoring is generating too many false positives (average 30-50% pass rate across classes). The `hc_filter.js` HIGH CONVICTION gate (score>=80, conf>=0.75, trust>=60) is too lenient — only 1/16,750 CRYPTO signals passed, but that 1 signal didn't even have a proven edge. The `audit_trail/quality_gates.py` per-class floors are set too low, especially for FUTURES (98.8% pass rate) and COMMODITY (51% pass rate).

### Recommended Immediate Actions
1. **Kill FOREX and CRYPTO trading** until the ML model is retrained with proper walk-forward validation
2. **Raise all SMART_PICKS_MIN_SCORE thresholds** by 10-15 points
3. **Fix the PF calculation** — PF=85 with 25% WR is mathematically impossible and indicates a bug
4. **Increase HC_FILTER_MIN_CONFIDENCE** to 0.85 and add a minimum trade count (n>=50) before considering any edge "proven"
5. **Implement a 30-day cooldown** on any strategy family that shows holdout PF < 0.5

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### CRYPTO
- Real/noise verdict: noise (no proven cells; all listed edges fail holdout or Bonferroni, extreme PF driven by outliers or possible single-symbol concentration in ml_crypto_predictor)
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge; realized WR ~46% on decisive trades implies net loss after costs)
- Gate change: SMART_PICKS_MIN_SCORE_CRYPTO = 82
- Confidence (1-5): 4

### EQUITY
- Real/noise verdict: noise (no proven cells; mean_reversion cells show failed holdout, PF inflated by tiny train n=27)
- 90d expected P&L (1% risk, $100k): $0
- Gate change: HC_MIN_CONFIDENCE = 0.78
- Confidence (1-5): 3

### COMMODITY
- Real/noise verdict: noise (no proven cells; momentum cells have WR_shrunk 36%, failed holdout, negative wr_z)
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_TRUST = 55
- Confidence (1-5): 3

### INDEX
- Real/noise verdict: noise (n=2 decisive trades, no edges)
- 90d expected P&L (1% risk, $100k): $0
- Gate change: HC_MIN_SCORE = 85
- Confidence (1-5): 2

### ETF
- Real/noise verdict: noise (n=16 decisive, no edges)
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_ETF = 75
- Confidence (1-5): 2

### UNKNOWN
- Real/noise verdict: noise (n=2 decisive, no edges)
- 90d expected P&L (1% risk, $100k): $0
- Gate change: HC_MIN_TRUST = 65
- Confidence (1-5): 2

### BOND
- Real/noise verdict: noise (n=14 decisive, no edges)
- 90d expected P&L (1% risk, $100k): $0
- Gate change: HC_MIN_CONFIDENCE = 0.78
- Confidence (1-5): 2

### FUTURES
- Real/noise verdict: noise (n=18 decisive, no edges)
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_FUTURES = 80
- Confidence (1-5): 2

### MEME
- Real/noise verdict: noise (no proven cells; single edge fails holdout with negative expectancy)
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_MEME = 85
- Confidence (1-5): 3

### FOREX
- Real/noise verdict: noise (no proven cells; consensus cells show WR 25-26%, failed holdout, extreme PF from leakage or look-ahead)
- 90d expected P&L (1% risk, $100k): $0
- Gate change: HC_MIN_CONFIDENCE = 0.78
- Confidence (1-5): 4

### PENNY
- Real/noise verdict: noise (n=7 decisive, no edges)
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_PENNY = 80
- Confidence (1-5): 2

**SYSTEM-WIDE CONCLUSION**  
Scale up today: none. Demote per MUTATION_THREE_AXIS_PROTOCOL: FOREX and CRYPTO (highest volume but clearest leakage signals and failed statistical gates). All other classes already produce zero usable edge.
