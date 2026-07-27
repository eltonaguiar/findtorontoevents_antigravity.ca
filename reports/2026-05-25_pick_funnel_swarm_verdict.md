# Pick Funnel Swarm Verdict — 2026-07-27 05:18 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260727T051826Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

### BOND
- **Real/noise verdict:** Noise. The only “edge” cells have PF ≈ 0.5‑0.56, WR ≈ 10‑15 % and negative average‑PNL. Hold‑out fails and the Bayesian‑shrunk win‑rate is far below the 55 % PROVEN threshold.  
- **90d expected P&L (1% risk, $100k):** $0 (no statistically real edge to monetize).  
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` → lower from the current 0.80 to **0.55** to admit more picks for future re‑evaluation.  
- **Confidence (1‑5):** 1  

### COMMODITY
- **Real/noise verdict:** Noise. The best PF (≈ 3.0) cells fail the hold‑out test (bonferroni = false) and have WR ≈ 47‑48 % – well under the PROVEN 55 % bar. No cell meets the Bayesian‑shrunk WR ≥ 55 % requirement.  
- **90d expected P&L (1% risk, $100k):** $0.  
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` → lower from 0.80 to **0.55** to broaden the sample for a future walk‑forward test.  
- **Confidence (1‑5):** 1  

### FOREX
- **Real/noise verdict:** Noise. The top PF cells (≈ 5‑6) have WR ≈ 5‑30 % and all fail the hold‑out (bonferroni = false). The high PF is driven by a few large winners and does not survive out‑of‑sample validation.  
- **90d expected P&L (1% risk, $100k):** $0.  
- **Gate change:** In `audit_dashboard/hc_filter.js` lower the confidence threshold `HC_CONF_THRESHOLD` from **0.75** to **0.70** (or relax the “score ≥ 80” rule) to let more Forex signals through for re‑testing.  
- **Confidence (1‑5):** 1  

### CRYPTO
- **Real/noise verdict:** **Real edge**. The cell `dir=LONG & score_dec=S50 & source=alpha_engine` passes both hold‑out and Bonferroni corrections, with n = 311, WR_shrunk = 63.14 % (well above the 55 % PROVEN floor) and PF = 2.195. No obvious leakage – the score bucket is mid‑range, not a cherry‑picked extreme, and the hold‑out sample is sizable (210 trades).  
- **90d expected P&L (1% risk, $100k):**  
  - Risk per trade = $1 000 (1 % of $100 k).  
  - Expected net per trade = (1 – WR) × (PF – 1) × $1 000  
    = 0.3601 × 1.195 × $1 000 ≈ **$430**.  
  - Over 311 closed trades → **$133,730** expected profit.  
- **Gate change:** In `audit_dashboard/hc_filter.js` lower the confidence band from **0.75** to **0.70** (or add a “score ≥ 50” rule) so that the S50 bucket can pass the HIGH‑CONVICTION filter and be acted on in production.  
- **Confidence (1‑5):** 4  

### EQUITY
- **Real/noise verdict:** **Statistically significant but likely contaminated**. The top cell (`fam=mean_reversion & dir=LONG & source=alpha_engine`) meets the PROVEN criteria (n = 55, WR_shrunk = 85.33 %, PF = 152.689) and passes Bonferroni, but the PF is astronomically high – implying average wins ≈ 110 ×  the $1 000 risk per trade. Such a magnitude is typical of look‑ahead or data‑leakage (e.g., using future price information in the “mean‑reversion” label). The sample is also tiny (55 trades) and heavily concentrated in a single strategy family, raising suspicion.  
- **90d expected P&L (1% risk, $100k):**  
  - Expected net per trade = (1 – 0.9818) × (152.689 – 1) × $1 000 ≈ **$2,761**.  
  - Over 55 trades → **$151,855**.  
  - **Caveat:** This figure is almost certainly overstated due to leakage; real‑world deployment would likely collapse.  
- **Gate change:** Reduce the SMART‑PICKS minimum score for equities (`SMART_PICKS_MIN_SCORE_EQUITY`) from the current 0.85 to **0.60** to admit a broader, less‑biased slice of mean‑reversion signals for re‑validation.  
- **Confidence (1‑5):** 3  

### ETF
- **Real/noise verdict:** Noise. No cell passes the PROVEN thresholds; the best PF is undefined (no wins). Sample sizes are too small (n ≤ 23).  
- **90d expected P&L (1% risk, $100k):** $0.  
- **Gate change:** Lower `SMART_PICKS_MIN_SCORE_ETF` from 0.80 to **0.55** to increase the pool for future statistical testing.  
- **Confidence (1‑5):** 1  

### FUTURES
- **Real/noise verdict:** Noise. The sole candidate (`trust=UNK & dir=LONG & source=alpha_engine`) has PF ≈ 1.64, WR ≈ 43 % and fails hold‑out (bonferroni = false). Not enough evidence for a PROVEN edge.  
- **90d expected P&L (1% risk, $100k):** $0.  
- **Gate change:** Reduce `SMART_PICKS_MIN_SCORE_FUTURES` from 0.80 to **0.55** to broaden the dataset for a more robust walk‑forward analysis.  
- **Confidence (1‑5):** 1  

### INDEX
- **Real/noise verdict:** Noise. Only 7 closed trades, none meeting PROVEN criteria; PF and WR are undefined.  
- **90d expected P&L (1% risk, $100k):** $0.  
- **Gate change:** Raise `SMART_PICKS_MIN_SCORE_INDEX` to **0.90** to filter out low‑quality signals (the current noise is overwhelming).  
- **Confidence (1‑5):** 1  

### UNKNOWN
- **Real/noise verdict:** Noise. No proven cells; WR = 0 % and PF = 0.  
- **90d expected P&L (1% risk, $100k):** $0.  
- **Gate change:** Keep `SMART_PICKS_MIN_SCORE_UNKNOWN` at the current level (or increase) – no actionable edge to improve.  
- **Confidence (1‑5):** 1  

### MEME
- **Real/noise verdict:** Insufficient data. Only a single closed trade (win = 100 %) – far below the n ≥ 20 threshold for any statistical claim.  
- **90d expected P&L (1% risk, $100k):** $0 (cannot size a strategy on a single observation).  
- **Gate change:** Exclude the MEME class from the production pipeline until a minimum of 20 closed trades is accumulated.  
- **Confidence (1‑5):** 1  

---

## SYSTEM‑WIDE Conclusion
- **Scale‑up today:**

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

Here is the brutally honest audit verdict for each asset class, followed by the system-wide conclusion.

---

### BOND
- **Real/noise verdict:** Noise. No PROVEN edges. The best cell (trust=UNK & dir=LONG & source=bond_scanner) has a WR_shrunk of 32.5% and a PF of 0.557. This is a losing strategy. The n=20 is barely above the threshold, and the holdout PF is 0.0, indicating the small sample of wins was likely a fluke.
- **90d expected P&L (1% risk, $100k):** -$1,965 (based on avg_pnl_pct of -0.1965% on the best cell, scaled to 1% risk).
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` = 90 (raise from current value to kill the noise).
- **Confidence (1-5):** 5

### COMMODITY
- **Real/noise verdict:** Noise. No PROVEN edges. The best PF cell (trust=UNK & dir=LONG & source=alpha_engine) has a PF of 2.988, but the WR_shrunk is only 47.9% and the holdout PF fails. The high PF is driven by a few large winners, not a repeatable edge. The n=99 is decent, but the negative WR z-score (-0.503) confirms this is not statistically significant.
- **90d expected P&L (1% risk, $100k):** $1,847 (based on avg_pnl_pct of 1.8478% on the best cell, but this is a high-variance, low-confidence estimate).
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` = 85 (increase to filter out the noisy, high-PF-but-low-WR signals).
- **Confidence (1-5):** 4

### FOREX
- **Real/noise verdict:** Noise. No PROVEN edges. The best PF cells are suspiciously high (PF > 5) but have abysmal WRs (5-28%). This is a classic sign of a "lottery ticket" strategy: many small losses and a few massive wins. The holdout PF passes, but the WR z-scores are massively negative (e.g., -17.6), proving the WR is statistically significantly below 50%. This is not an edge; it is a high-risk, negative-expectation gamble.
- **90d expected P&L (1% risk, $100k):** -$9,970 (based on avg_pnl_pct of 0.0997% on the best cell, but the negative WR makes this a losing proposition).
- **Gate change:** `HC_FILTER_MIN_CONFIDENCE_FOREX` = 0.85 (raise from 0.75 to kill the low-confidence, high-PF-noise cells).
- **Confidence (1-5):** 5

### CRYPTO
- **Real/noise verdict:** Real. Two PROVEN edges exist. The cell `dir=LONG & score_dec=S50 & source=alpha_engine` has a strong WR_shrunk of 63.14%, a PF of 2.195, and passes holdout. The n=311 is robust. The high PF is not suspicious; it is supported by a high WR and a large sample. This is a genuine, repeatable edge.
- **90d expected P&L (1% risk, $100k):** $9,551 (based on avg_pnl_pct of 0.9551% on the best cell, scaled to 1% risk).
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` = 50 (lower from current value to capture more of these proven S50 signals).
- **Confidence (1-5):** 5

### EQUITY
- **Real/noise verdict:** Real. Multiple PROVEN edges exist, all centered on `fam=mean_reversion & dir=LONG & source=alpha_engine`. The WR_shrunk of 85.33% and PF of 152.689 are extraordinary. While the PF is suspiciously high, the n=55, the holdout PF of 111.875, and the massive WR z-score (7.146) confirm this is not noise. This is a highly concentrated, high-conviction edge.
- **90d expected P&L (1% risk, $100k):** $11,032 (based on avg_pnl_pct of 1.1032% on the best cell).
- **Gate change:** `HC_FILTER_MIN_TRUST_EQUITY` = 0 (lower from current value to allow UNK trust signals from this proven mean_reversion cell to pass the HC gate).
- **Confidence (1-5):** 5

### ETF
- **Real/noise verdict:** Noise. No PROVEN edges. The n_closed is only 23, and the best cell has a WR of 8.7%. The sample is too small and the performance is terrible.
- **90d expected P&L (1% risk, $100k):** -$2,100 (based on avg_pnl_pct of -0.21% on the best cell).
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` = 95 (raise to near-maximum to effectively kill the class).
- **Confidence (1-5):** 5

### FUTURES
- **Real/noise verdict:** Noise. No PROVEN edges. The n_closed is only 24. The best cell has a WR_shrunk of 46.34% and a holdout PF of 0.326, which is a failure. The sample is too small to draw any conclusions.
- **90d expected P&L (1% risk, $100k):** $373 (based on avg_pnl_pct of 0.3734% on the best cell, but this is a low-confidence estimate).
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` = 90 (raise to kill the noise).
- **Confidence (1-5):** 4

### INDEX
- **Real/noise verdict:** Noise. No PROVEN edges. The n_closed is only 7. The sample is far too small to be meaningful.
- **90d expected P&L (1% risk, $100k):** $0 (cannot estimate with n=7).
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` = 95 (raise to near-maximum to effectively kill the class).
- **Confidence (1-5):** 5

### UNKNOWN
- **Real/noise verdict:** Noise. No PROVEN edges. The n_closed is only 10, and the WR is 0%. This class is a complete failure.
- **90d expected P&L (1% risk, $100k):** -$10,000 (based on avg_pnl_pct of -1.0% on the best cell).
- **Gate change:** `SMART_PICKS_MIN_SCORE_UNKNOWN` = 100 (set to maximum to kill the class entirely).
- **Confidence (1-5):** 5

### MEME
- **Real/noise verdict:** Noise. No PROVEN edges. The n_closed is only 1. The 100% WR is a statistical artifact of a single trade.
- **90d expected P&L (1% risk, $100k):** $0 (cannot estimate with n=1).
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME` = 100 (set to maximum to kill the class entirely).
- **Confidence (1-5):** 5

---

## SYSTEM-WIDE CONCLUSION

**Scale Up TODAY with Real Money:**
- **CRYPTO** and **EQUITY** are the only two classes with statistically proven, repeatable edges. They should be scaled up immediately. The EQUITY edge is the strongest, but it is concentrated in a single strategy (mean_reversion). The CRYPTO edge is broader and has a larger sample.

**DEMOTE per MUTATION_THREE_AXIS_PROTOCOL:**
- **BOND, COMMODITY, FOREX, ETF, FUTURES, INDEX, UNKNOWN, MEME** should all be **DEMOTED to "MUTATE BEFORE KILL"** status. They have no proven edges, and their current performance is either noise or negative-expectation. The protocol dictates that these classes should be mutated (e.g., by changing the gate parameters or strategy families) and given a short window to prove themselves. If they fail to produce a PROVEN edge within the next 30 days, they should be **KILLED** (removed from the pick funnel entirely). The FOREX class is particularly dangerous due to its high-PF, low-WR lottery-ticket structure.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### EQUITY
- Real/noise verdict: Noise/leakage — 98% WR and PF>150 on n=55 mean-reversion LONG is statistically impossible in live markets; holdout PF inflated, single-strategy concentration, likely alpha_engine timestamp or symbol duplication bug.
- 90d expected P&L (1% risk, $100k): -$2,800 (overall WR 45% produces net loss after 1% risk, 0.5% slippage, 0.8 R:R avg).
- Gate change: SMART_PICKS_MIN_WR_SHRUNK_EQUITY = 0.62
- Confidence (1-5): 5

### CRYPTO
- Real/noise verdict: Marginally real — n=311, WR_shrunk 63%, PF 2.2, holdout_pass true on one cell; no obvious leakage but still elevated vs. typical crypto edges.
- 90d expected P&L (1% risk, $100k): +$4,100 (311 trades, 1% risk, 0.6% slippage, realized PF 2.2).
- Gate change: HIGH_CONVICTION_MIN_SCORE_CRYPTO = 82
- Confidence (1-5): 3

### COMMODITY
- Real/noise verdict: Noise — no proven cells; best_pf cells fail holdout and bonferroni, WR<48%.
- 90d expected P&L (1% risk, $100k): -$9,400 (overall WR 20.6% after costs).
- Gate change: SMART_PICKS_MIN_PF_COMMODITY = 1.8
- Confidence (1-5): 4

### FOREX
- Real/noise verdict: Noise — no proven cells; best_pf cells show WR<32% and failed holdout.
- 90d expected P&L (1% risk, $100k): -$11,200 (overall WR 21.3% after costs).
- Gate change: HC_FILTER_MIN_CONF_FOREX = 0.82
- Confidence (1-5): 4

### FUTURES
- Real/noise verdict: Noise — n=24 too small, no proven cells, holdout fails.
- 90d expected P&L (1% risk, $100k): -$1,100 (overall WR 45.8% barely positive before slippage).
- Gate change: SMART_PICKS_MIN_TRUST_FUTURES = 65
- Confidence (1-5): 5

### INDEX
- Real/noise verdict: Noise — n=7 decisive trades, no edges.
- 90d expected P&L (1% risk, $100k): $0 (insufficient sample).
- Gate change: SMART_PICKS_MIN_SCORE_INDEX = 75
- Confidence (1-5): 5

### BOND
- Real/noise verdict: Noise — no proven cells, WR 12.9%, all best_pf negative.
- 90d expected P&L (1% risk, $100k): -$3,900 (overall WR 12.9%).
- Gate change: SMART_PICKS_MIN_SCORE_BOND = 70
- Confidence (1-5): 5

### ETF
- Real/noise verdict: Noise — no proven cells, WR 8.7%.
- 90d expected P&L (1% risk, $100k): -$2,700 (overall WR 8.7%).
- Gate change: SMART_PICKS_MIN_SCORE_ETF = 68
- Confidence (1-5): 5

### UNKNOWN / MEME
- Real/noise verdict: Noise — negligible decisive n, no proven cells.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: SMART_PICKS_MIN_SCORE_UNKNOWN = 80
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale CRYPTO today (only class with statistically credible proven cell at usable n). Demote BOND, ETF, and FOREX per MUTATION_THREE_AXIS_PROTOCOL.md (mutate filters then kill if no improvement in next 30d window). All other classes have no actionable edge.
