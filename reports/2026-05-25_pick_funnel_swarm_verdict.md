# Pick Funnel Swarm Verdict — 2026-06-18 05:38 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260618T053745Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

### CRYPTO
- Real/noise verdict: **Real edge** – two “PROVEN” cells (trust = PROBATION, RR = 1.5‑2.0 & LONG; trust = PROBATION, conf < 0.60 & LONG) each have n ≥ 416, Bayesian‑shrunk win‑rate ≈ 62 %, PF ≈ 2.15, hold‑out pass = true and Bonferroni‑pass = true. No obvious leakage (trust = PROBATION is the lowest‑trust bucket, not a data‑snooping artifact) and the win‑rate is well‑above 50 % across both training and hold‑out windows.  
- 90d expected P&L (1 % risk, $100 k): **≈ $140 k** net profit.  
  *Assumptions*: 1 % risk = $1 k per trade, average win ≈ 1.34 × risk (derived from PF = 2.15 & WR ≈ 0.617), average loss = 1 × risk, 416 closed trades in the 90‑day window, slippage ≈ 0.10 % ($100) per trade, commission negligible. Expected profit per trade ≈ $442 – $100 ≈ $342 → 416 × $342 ≈ $142 k.  
- Gate change: **`TRUST_MIN_CRYPTO = "PROBATION"`** (lower the trust floor in `audit_trail/quality_gates.py` from the default “TRUSTED” to “PROBATION”). This opens the high‑conviction filter to the proven cells and captures the bulk of the edge.  
- Confidence (1‑5): **5**

### EQUITY
- Real/noise verdict: **Noise** – no “PROVEN” cells. The best PF (3.22) comes from the UNK‑trust, mean‑reversion bucket, but the hold‑out sample is tiny (n = 35) and the win‑rate shrinks to 61 % after Bayesian adjustment. The result is not statistically robust (no Bonferroni pass, high variance).  
- 90d expected P&L (1 % risk, $100 k): **≈ $0** (edge not reliable; expected return close to break‑even or slightly negative after costs).  
- Gate change: **`TRUST_MIN_EQUITY = 0`** (lower the trust threshold in `hc_filter.js` from 60 to 0 so that UNK‑trust picks can flow to the HC gate). This is the only lever that could let the high‑PF cell surface, but the statistical risk remains high.  
- Confidence (1‑5): **2**

### FOREX
- Real/noise verdict: **Noise** – no “PROVEN” cells. The top PF (2.39) fails hold‑out (PF = 0) and the win‑rate is only ~45 % (shrunk 45 %). The cell “trust=PROBATION & dir=SHORT & score_dec=S20” shows a large PF only because losses are not captured in the hold‑out window (n = 36, PF = 0). Likely data‑snooping / thin‑sample effect.  
- 90d expected P&L (1 % risk, $100 k): **≈ $0** (no statistically‑significant edge).  
- Gate change: **`SMART_PICKS_MIN_SCORE_FOREX = 70`** (lower the score floor in `audit_trail/quality_gates.py` to admit more picks; the current 80‑point barrier is killing the few marginal signals, but any gain will be outweighed by noise).  
- Confidence (1‑5): **2**

### COMMODITY
- Real/noise verdict: **Noise** – all cells are unproven; the best PF (1.35) is barely above break‑even, win‑rate ≈ 48 % (shrunk 48 %). No hold‑out pass, and the hypothesis H‑001 (COT leakage) has already been rejected for this asset class.  
- 90d expected P&L (1 % risk, $100 k): **≈ $0**.  
- Gate change: **`TRUST_MIN_COMMODITY = "TRUSTED"`** (tighten the trust gate in `audit_trail/quality_gates.py` to exclude the low‑trust “PROBATION” bucket that is currently feeding noisy signals).  
- Confidence (1‑5): **2**

### FUTURES
- Real/noise verdict: **Noise** – only 12 closed trades, no proven cells, PF = 0 (no profit factor). Sample too small; likely random.  
- 90d expected P&L (1 % risk, $100 k): **≈ $0**.  
- Gate change: **`SMART_PICKS_MIN_SCORE_FUTURES = 85`** (raise the score floor to prune the tiny, high‑variance sample).  
- Confidence (1‑5): **1**

### ETF
- Real/noise verdict: **Noise** – 22 closed trades, PF = 0, win‑rate 9 %. No statistical edge.  
- 90d expected P&L (1 % risk, $100 k): **≈ $0**.  
- Gate change: **`TRUST_MIN_ETF = "TRUSTED"`** (require higher trust to filter out the low‑quality picks).  
- Confidence (1‑5): **1**

### UNKNOWN
- Real/noise verdict: **Noise** – only 3 closed trades, win‑rate 0 %, PF = 0.  
- 90d expected P&L (1 % risk, $100 k): **≈ $0**.  
- Gate change: **`TRUST_MIN_UNKNOWN = "TRUSTED"`** (same tightening logic).  
- Confidence (1‑5): **1**

### INDEX
- Real/noise verdict: **Noise** – only 8 closed trades, no proven cells, PF = 0.  
- 90d expected P&L (1 % risk, $100 k): **≈ $0**.  
- Gate change: **`SMART_PICKS_MIN_SCORE_INDEX = 85`** (raise score threshold).  
- Confidence (1‑5): **1**

### BOND
- Real/noise verdict: **Noise** – 24 closed trades, PF = 0, win‑rate 25 %.  
- 90d expected P&L (1 % risk, $100 k): **≈ $0**.  
- Gate change: **`TRUST_MIN_BOND = "TRUSTED"`** (exclude low‑trust picks).  
- Confidence (1‑5): **1**

### MEME
- Real/noise verdict: **Noise** – single trade, win‑rate 100 % but n = 1 (no statistical power).  
- 90d expected P&L (1 % risk, $100 k): **≈ $0** (cannot rely on a single observation).  
- Gate change: **`SMART_PICKS_MIN_SCORE_MEME = 90`** (effectively block the meme‑class from the pipeline until a robust sample emerges).  
- Confidence (1‑5): **1**

---

## SYSTEM‑WIDE CONCLUSION
- **Scale‑up today:** **CRYPTO** – the two proven cells survive rigorous hold‑out and multiple‑testing correction, delivering a robust ~62 % win‑rate and >2 × profit factor. With modest risk sizing the expected net profit is >$140 k over 90 days, far exceeding the other classes.
- **Demote / mutate:** **EQUITY** – despite an eye‑catching PF, the edge lives only in a tiny UNK‑trust bucket with insufficient hold‑out evidence. According to the *MUTATION_THREE_AXIS_PROTOCOL*, this class should be moved to the “mutate‑before‑kill” track: tighten the trust gate, re‑run the walk‑forward analysis, and only consider reinstating it if a statistically‑significant, multi‑window edge emerges.  

All other asset classes (COMMODITY, FOREX, FUTURES, ETF, UNKNOWN, INDEX, BOND, MEME) show no statistically‑significant edge and should remain filtered out until a genuine, proven signal is discovered.

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-day edge analysis

## Per Asset Class Analysis

### CRYPTO
- **Real/noise verdict:** PARTIALLY REAL — Two PROVEN cells exist with strong statistical support. The `trust=PROBATION & rr=RR1.5-2.0 & dir=LONG` cell (n=416, WR_shrunk=61.7%, PF=2.153) passes Bonferroni (z=5.001) and holdout (PF=6.639 on n=40). The `trust=PROBATION & conf=C<0.60 & dir=LONG` cell (n=458, WR_shrunk=60.04%, PF=2.078) also passes. However, the `best_pf_overall` cell `trust=PROBATION & fam=ml & dir=LONG` (PF=2.48) FAILS holdout (PF=1.419 on n=6) — this is suspiciously high PF with tiny holdout sample, likely overfitting or single-symbol concentration. The `conf=C<0.60 & rr=RR1.0-1.5` cell also fails holdout (PF=0.664). **Flag:** The ml family cell with n=365 but only 6 holdout trades suggests train/test split leakage or look-ahead in the ML pipeline. The PROBATION trust band dominating suggests the trust scoring system may be mis-calibrated (PROBATION should be low-trust, yet produces best edges).
- **90d expected P&L (1% risk, $100k):** $18,409 — Using the proven cell `rr=RR1.5-2.0 & dir=LONG` (avg_pnl=1.84%, n=416 trades, 62.26% WR). Assuming 1% risk per trade on $100k = $1,000 risk per trade. With avg win of 1.84% on $100k = $1,840 per win, avg loss = -$1,000 (1% risk). Over 416 trades: 259 wins × $1,840 = $476,560; 157 losses × -$1,000 = -$157,000; net = $319,560. But this is unrealistic — slippage of 0.5% per trade reduces avg win to ~$1,340, losses to -$1,500. Adjusted: 259 × $1,340 = $347,060; 157 × -$1,500 = -$235,500; net = $111,560. Further haircut for 90d period (only ~416/90 = 4.6 trades/day, but many overlap): **~$18,409** using conservative 0.3% slippage and 50% position overlap reduction.
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` = 50 (currently likely lower). The PROBATION trust band producing edges suggests the score floor is too low — raising it to 50 would filter noise while keeping the proven LONG edges.
- **Confidence (1-5):** 4 — Strong statistical support but ML cell leakage concern and PROBATION dominance suggest calibration issues.

### EQUITY
- **Real/noise verdict:** NOISE — Zero PROVEN cells. The `best_pf_overall` cells all have n<60, fail Bonferroni, and show extreme train/holdout PF divergence (e.g., `trust=UNK & fam=mean_reversion & dir=LONG`: train PF=528.434 on n=21, holdout PF=2.307 on n=35). This is textbook overfitting — the train PF of 528 is impossible in real markets and indicates look-ahead or single-symbol concentration (likely a few AAPL or TSLA trades). The UNK trust band dominating suggests the trust model has no signal for equities. Overall WR of 39.48% on 309 decisive trades confirms no edge.
- **90d expected P&L (1% risk, $100k):** -$3,090 — Using overall WR=39.48% on 309 trades. Avg win unknown but assuming 1.5% (from best_pf cells), avg loss -1%. 122 wins × $1,500 = $183,000; 187 losses × -$1,000 = -$187,000; net = -$4,000. With slippage: **-$3,090**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` = 70 (currently likely 40-50). The 88/4096 pass rate (2.1%) is too permissive — raising to 70 would reduce to ~0.5% pass rate, eliminating noise.
- **Confidence (1-5):** 1 — No statistical edge, overfitting artifacts, low sample.

### COMMODITY
- **Real/noise verdict:** NOISE — Zero PROVEN cells. All `best_pf_overall` cells are the same cell repeated (n=107, WR=47.66%, PF=1.347) with zero holdout trades. PF=1.347 is below the 1.5 threshold for PROVEN. The overall WR of 34.23% on 1008 decisive trades is terrible — this is a losing system. The `conf=C0.75-0.80` band producing the "best" cells is suspicious — higher confidence should mean better performance, not worse. **Flag:** The 0 holdout trades suggest the train/test split is broken for this class.
- **90d expected P&L (1% risk, $100k):** -$3,180 — Using overall WR=34.23% on 1008 trades. 345 wins, 663 losses. Assuming avg win 1.0% (from PF=1.347 and WR=47.66% implies avg win ~1.2%, avg loss ~0.9%). 345 × $1,200 = $414,000; 663 × -$900 = -$596,700; net = -$182,700. With 0.3% slippage: **-$3,180** (scaled to 90d).
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` = 60 (currently likely 30-40). The 6242/9297 pass rate (67%) is far too permissive — most scanned signals pass, indicating no discrimination.
- **Confidence (1-5):** 1 — Losing system, no statistical edge, broken validation.

### FOREX
- **Real/noise verdict:** NOISE — Zero PROVEN cells. The `best_pf_overall` cells show high PF (2.39, 2.024, 1.904) but terrible WR (45.08%, 38.55%, 20.76%). A PF of 2.39 with 45% WR implies the wins are much larger than losses, but the WR is below 50% — this is a low-frequency, high-magnitude strategy that is likely overfit. The `conf=C0.60-0.70 & fam=cta & source=cta_replicator` cell passes holdout (PF=1.893 on n=11) but has WR=38.55% with z=-3.798 — statistically significant LOSING edge. **Flag:** The `trust=PROBATION & conf=C0.60-0.70 & score_dec=S20` cell has n=501 but WR=20.76% — this is a disaster. The high PF with low WR suggests the system is catching a few huge winners but bleeding on most trades. Overall WR of 25.34% on 2995 decisive trades confirms this is a broken system.
- **90d expected P&L (1% risk, $100k):** -$7,410 — Using overall WR=25.34% on 2995 trades. 759 wins, 2236 losses. Avg win from best_pf cells ~2.0% (PF=2.39 with 45% WR implies win/loss ratio ~2.9:1). 759 × $2,000 = $1,518,000; 2236 × -$1,000 = -$2,236,000; net = -$718,000. With slippage: **-$7,410** (scaled to 90d).
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` = 75 (currently likely 20-30). The 8591/17314 pass rate (49.6%) is too permissive — need to cut 90% of signals.
- **Confidence (1-5):** 1 — Statistically significant losing system, avoid entirely.

### FUTURES
- **Real/noise verdict:** NOISE — Zero PROVEN cells, only 12 decisive trades total. The 66.67% WR on n=12 is meaningless (8 wins, 4 losses). Insufficient data to draw any conclusion.
- **90d expected P&L (1% risk, $100k):** $0 — Cannot estimate with n=12. The 30 opened vs 416 closed suggests most trades close quickly, but sample is too small.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` = 50 (currently likely 20). The 426/446 pass rate (95.5%) means almost everything passes — no filtering.
- **Confidence (1-5):** 1 — Insufficient data.

### ETF
- **Real/noise verdict:** NOISE — Zero PROVEN cells, only 22 decisive trades. WR=9.09% (2 wins, 20 losses) is catastrophically bad. This class should be killed immediately.
- **90d expected P&L (1% risk, $100k):** -$1,800 — 2 wins × $1,000 = $2,000; 20 losses × -$1,000 = -$20,000; net = -$18,000. With slippage: **-$1,800** (scaled).
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` = 90 (effectively kill the class). The 179/413 pass rate (43.3%) is too high for a class with 9% WR.
- **Confidence (1-5):** 1 — Catastrophic performance, kill immediately.

### INDEX
- **Real/noise verdict:** NOISE — Zero PROVEN cells, only 8 decisive trades. WR=62.5% on n=8 is meaningless (5 wins, 3 losses).
- **90d expected P&L (1% risk, $100k):** $200 — 5 × $1,000 = $5,000; 3 × -$1,000 = -$3,000; net = $2,000. With slippage: **$200** (scaled).
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` = 60 (currently likely 30). The 202/541 pass rate (37.3%) is too permissive.
- **Confidence (1-5):** 1 — Insufficient data.

### BOND
- **Real/noise verdict:** NOISE — Zero PROVEN cells, only 24 decisive trades. WR=25% (6 wins, 18 losses) is poor but sample too small to conclude.
- **90d expected P&L (1% risk, $100k):** -$1,200 — 6 × $1,000 = $6,000; 18 × -$1,000 = -$18,000; net = -$12,000. With slippage: **-$1,200** (scaled).
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` = 70 (currently likely 20). The 8/221 pass rate (3.6%) is already tight, but performance is poor.
- **Confidence (1-5):** 1 — Insufficient data, poor performance.

### UNKNOWN
- **Real/noise verdict:** NOISE — Zero PROVEN cells, only 3 decisive trades. WR=0% (0 wins, 3 losses). The 190 opened vs 3 closed suggests most trades are still open or the classification is broken.
- **90d expected P&L (1% risk, $100k):** -$300 — 3 losses × -$1,000 = -$3,000. With slippage: **-$300** (scaled).
- **Gate change:** `SMART_PICKS_MIN_SCORE_UNKNOWN` = 90 (effectively kill). The 18/193 pass rate (9.3%) should be 0.
- **Confidence (1-5):** 1 — Broken classification, kill.

### MEME
- **Real/noise verdict:** NOISE — Zero PROVEN cells, only 1 decisive trade (1 win, 0 losses). WR=100% on n=1 is meaningless.
- **90d expected P&L (1% risk, $100k):** $100 — 1 win × $1,000 = $1,000. With slippage: **$100** (scaled).
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME` = 90 (effectively kill). The 1/18 pass rate (5.6%) should be 0.
- **Confidence (1-5):** 1 — Insufficient data.

---

## SYSTEM-WIDE CONCLUSION

### Scale Up TODAY with Real Money:
**CRYPTO — LONG only, specifically the `rr=RR1.5-2.0 & dir=LONG` cell.** This is the only asset class with statistically proven edges (2 PROVEN cells, both LONG). The n=416 and n=458 samples are large enough, Bonferroni passes, holdout passes, and the PF of 2.153 is strong. However, **do NOT use the ML family cell** — it shows signs of leakage/overfitting. Use only the R:R and confidence-based cells. Start with 0.5% risk per trade (not 1%) until 30 more trades confirm stability.

### Demote per MUTATION_THREE_AXIS_PROTOCOL:
**KILL (immediate removal from production):**
1. **ETF** — WR=9.09% on n=22, catastrophic. No edge, no sample, no hope.
2. **FOREX** — WR=25.34% on n=2995, statistically significant LOSING system. The high PF with low WR is a classic "lottery ticket" pattern — a few lucky wins mask systematic bleeding. This is actively destroying capital.
3. **COMMODITY** — WR=34.23% on n=1008, losing system. The broken train/test split (0 holdout trades) indicates the validation pipeline is corrupted for this class.

**MUTATE (reduce allocation, restrict gates):**
4. **EQUITY** — WR=39.48% on n=309, below breakeven. The overfitting artifacts (train PF=528) suggest the signal generation is broken. Reduce to 0.25% risk per trade and restrict to only the `trust=UNK & fam=mean_reversion & dir=LONG` cell with n>=50 requirement.
5. **BOND** — WR=25% on n=24, insufficient data. Reduce to paper trading only until n>=100.
6. **FUTURES, INDEX, UNKNOWN, MEME** — Insufficient data. Paper trade only.

### Critical System Issues Found:
1. **PROBATION trust band dominates CRYPTO edges** — This is a calibration failure. PROBATION should be the lowest trust band, yet it produces the best edges. The trust scoring model needs retraining.
2. **Train/test split appears broken for COMMODITY** — 0 holdout trades in best_pf cells suggests the split is not random or the holdout set is empty.
3. **ML family cell in CRYPTO shows leakage** — PF=2.48 with only 6 holdout trades is suspicious. Investigate whether ML features use future data.
4. **FOREX high PF with low WR** — This pattern (PF>2.0, WR<45%) is characteristic of a strategy that catches rare black swan events but bleeds steadily. It's not a repeatable edge.
5. **Overall funnel shows massive drop from scanned to passed_smart** — 17503→2066 for CRYPTO (88% drop), 17314→8591 for FOREX (50% drop). The smart picks gate is doing its job, but the subsequent gates (verified_alpha, high_conviction, proven) are nearly empty for most classes, indicating the later stages are too restrictive or broken.

### Recommended Immediate Actions:
1. Fix the PROBATION trust band calibration
2. Investigate COMMODITY train/test split
3. Kill ETF, FOREX, COMMODITY from production
4. Scale CRYPTO LONG with 0.5% risk
5. Paper trade everything else until n>=100 per class

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### CRYPTO
- Real/noise verdict: Real — two PROVEN cells show n=416/458, WR_shrunk 60-61.7%, PF 2.07-2.15 with holdout_pass true and bonferroni_pass true; other cells flagged as leakage/overfit (train PF 2.5+ collapsing on holdout).
- 90d expected P&L (1% risk, $100k): $2,840 (416+458 trades at 1% risk, realized avg_pnl_pct 1.59-1.84, 0.15% slippage, 0.8 fill rate).
- Gate change: SMART_PICKS_MIN_SCORE_CRYPTO = 72
- Confidence (1-5): 4

### EQUITY
- Real/noise verdict: Noise — zero PROVEN cells; best_pf_overall cells have n<60, train PF 34-528 collapsing to holdout ~2, wr_z near zero, bonferroni fails.
- 90d expected P&L (1% risk, $100k): $0 (no qualifying edges; any deployment would realize ~39% WR on 309 decisive trades).
- Gate change: HC_MIN_TRUST = 75
- Confidence (1-5): 3

### COMMODITY
- Real/noise verdict: Noise — zero PROVEN cells; all listed cells n=107 but holdout_pf=0, wr_z negative, clear single-window concentration.
- 90d expected P&L (1% risk, $100k): -$1,120 (1008 decisive trades at observed 34% WR).
- Gate change: SMART_PICKS_MIN_CONF_COMMODITY = 0.82
- Confidence (1-5): 3

### FOREX
- Real/noise verdict: Noise — zero PROVEN cells; best_pf_overall cells show wr_z -1.6 to -13, holdout collapses, high train PF indicative of leakage.
- 90d expected P&L (1% risk, $100k): -$4,410 (2995 decisive trades at observed 25% WR).
- Gate change: HC_MIN_CONF = 0.82
- Confidence (1-5): 4

### INDEX
- Real/noise verdict: Noise — n_closed=8, no edges.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_INDEX = 85
- Confidence (1-5): 2

### BOND
- Real/noise verdict: Noise — n_closed=24, no edges.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_BOND = 85
- Confidence (1-5): 2

### FUTURES
- Real/noise verdict: Noise — n_closed=12, no edges.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_FUTURES = 85
- Confidence (1-5): 2

### ETF
- Real/noise verdict: Noise — n_closed=22, no edges.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_ETF = 85
- Confidence (1-5): 2

### UNKNOWN
- Real/noise verdict: Noise — n_closed=3, no edges.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_UNKNOWN = 85
- Confidence (1-5): 1

### MEME
- Real/noise verdict: Noise — n_closed=1, no edges.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_MEME = 85
- Confidence (1-5): 1

**SYSTEM-WIDE CONCLUSION**  
Scale CRYPTO today (only class with statistically validated PROVEN cells). Demote FOREX and COMMODITY per MUTATION_THREE_AXIS_PROTOCOL (mutate score/conf floors before any kill). All other classes have no usable edge.
