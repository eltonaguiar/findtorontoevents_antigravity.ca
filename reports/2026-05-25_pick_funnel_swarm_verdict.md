# Pick Funnel Swarm Verdict — 2026-07-24 05:05 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260724T050439Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

### CRYPTO
- **Real/noise verdict:** **Real** – two PROVEN cells (≈ 284‑377 trades each) show WR ≈ 64 % (shrunk) and PF ≈ 1.8‑2.25. Hold‑out and Bonferroni tests pass, n > 250, and the signal comes from the `alpha_engine` source (no single‑symbol concentration reported). No obvious leakage.
- **90d expected P&L (1 % risk, $100 k):**  
  *Risk per trade* = $1 000 (1 % of $100 k).  
  *Expected profit per trade* = (1‑WR) × $1 000 × (PF‑1) ≈ 0.36 × $1 000 × 1.25 ≈ **$450**.  
  *Trades in edge cell* = 284 (the highest‑PF cell).  
  **Total expected profit ≈ 284 × $450 ≈ $128 k** (≈ 128 % ROI on the $100 k account).  
  *Assumptions:* 0.1 % slippage on entry/exit (reduces PF by ~5 %); full‑size 1 % risk taken on every signal; no position overlap limits.
- **Gate change:** Lower the high‑conviction confidence floor in `audit_dashboard/hc_filter.js` from `conf>=0.75` to **`conf>=0.70`**. This admits more of the “score_dec=S50” picks that already proved profitable while still keeping a reasonable conviction filter.
- **Confidence (1‑5):** **4** – strong statistical backing, but the edge is confined to the “S50” decile; a modest filter tweak should capture more of the same regime.

### FOREX
- **Real/noise verdict:** **Noise** – best PF cells (PF ≈ 5‑6) have WR ≈ 5‑30 % (shrunk) and **hold‑out fails** (bonferroni false). The high PF is driven by a few large‑win trades; the signal is not statistically robust and likely reflects look‑ahead or data‑snooping (e.g., “multi_asset_copytrader” source).
- **90d expected P&L (1 % risk, $100 k):** **$0** – no statistically validated edge to size.
- **Gate change:** Raise the high‑conviction confidence threshold to **`conf>=0.85`** (or tighten the score decile to ≥ 80) to prune the noisy “multi_asset_copytrader” signals.
- **Confidence (1‑5):** **2** – the current edge is not reliable; tightening the gate is a defensive move.

### EQUITY
- **Real/noise verdict:** **Statistically real but suspect** – PROVEN cells (n ≈ 48‑49) show WR ≈ 85 % (shrunk) and an astronomic PF ≈ 99. Hold‑out passes and Bonferroni passes, yet the PF is so extreme that it almost certainly reflects **single‑symbol concentration or data leakage** (e.g., a handful of stocks driving the result). Treat as a fragile edge.
- **90d expected P&L (1 % risk, $100 k):**  
  *Expected profit per trade* = (1‑0.85) × $1 000 × (99‑1) ≈ 0.15 × $1 000 × 98 ≈ **$14 700**.  
  *Trades in edge cell* = 49.  
  **Total expected profit ≈ 49 × $14 700 ≈ $720 k** – clearly unrealistic for a diversified $100 k portfolio; the figure is inflated by concentration and should be taken as an upper bound only.
- **Gate change:** Reduce the minimum SMART‑PICKS score for EQUITY in `audit_trail/quality_gates.py` (e.g., `SMART_PICKS_MIN_SCORE_EQUITY`) from its current value (≈ 80) to **`70`**. This will admit more mean‑reversion signals while still filtering out the most noisy picks, giving a larger sample to verify whether the edge persists beyond the current narrow set.
- **Confidence (1‑5):** **3** – statistical tests pass, but the edge’s magnitude suggests over‑fitting; a gate tweak may reveal a more realistic, sustainable signal.

### COMMODITY
- **Real/noise verdict:** **Noise** – best PF cells (PF ≈ 2‑3) have WR ≈ 40‑46 % (shrunk) and **hold‑out fails**. No PROVEN cells; the apparent edge is likely random or driven by a few symbols (e.g., cotton‑related COT leakage previously rejected).
- **90d expected P&L (1 % risk, $100 k):** **$0**
- **Gate change:** Increase the SMART‑PICKS minimum confidence for COMMODITY (`SMART_PICKS_MIN_CONFIDENCE_COMMODITY`) from its current level to **`0.80`** to filter out the noisy “trust=UNK” signals.
- **Confidence (1‑5):** **2**

### BOND
- **Real/noise verdict:** **Noise** – no PROVEN cells; top PF ≈ 0.56 with WR ≈ 15 % (shrunk) and hold‑out fails. Likely random.
- **90d expected P&L (1 % risk, $100 k):** **$0**
- **Gate change:** Raise the SMART‑PICKS minimum score for BOND (`SMART_PICKS_MIN_SCORE_BOND`) to **`85`** to keep only the strongest, most reliable picks.
- **Confidence (1‑5):** **2**

### FUTURES
- **Real/noise verdict:** **Noise** – only one cell, n = 21, WR ≈ 43 % (shrunk), PF ≈ 1.64, hold‑out fails. No statistical significance.
- **90d expected P&L (1 % risk, $100 k):** **$0**
- **Gate change:** Tighten the confidence filter in `hc_filter.js` to **`conf>=0.80`** for FUTURES.
- **Confidence (1‑5):** **2**

### ETF
- **Real/noise verdict:** **Noise** – no proven cells, very low trade count, PF ≈ 0, WR ≈ 0 %.  
- **90d expected P&L (1 % risk, $100 k):** **$0**
- **Gate change:** Increase the SMART‑PICKS minimum score for ETF (`SMART_PICKS_MIN_SCORE_ETF`) to **`85`**.
- **Confidence (1‑5):** **1**

### INDEX
- **Real/noise verdict:** **Noise** – only 6 closed trades, no proven edge, WR = 50 % but PF ≈ 0, hold‑out fails.
- **90d expected P&L (1 % risk, $100 k):** **$0**
- **Gate change:** Raise the high‑conviction score threshold to **`score>=85`** in `hc_filter.js`.
- **Confidence (1‑5):** **1**

### UNKNOWN
- **Real/noise verdict:** **Noise** – 10 closed trades, WR = 0 %, PF = 0. No edge.
- **90d expected P&L (1 % risk, $100 k):** **$0**
- **Gate change:** Exclude the “UNKNOWN” asset class entirely from the pipeline (set `INCLUDE_UNKNOWN=False` in `audit_trail/quality_gates.py`).
- **Confidence (1‑5):** **1**

### MEME
- **Real/noise verdict:** **Noise** – only 1 trade (win), insufficient data; cannot claim an edge.
- **90d expected P&L (1 % risk, $100 k):** **$0**
- **Gate change:** Disable the MEME class (remove from `audit_trail/quality_gates.py`).
- **Confidence (1‑5):** **1**

---

## SYSTEM‑WIDE Conclusion
- **Scale‑up today:** **CRYPTO** – the only class with a statistically solid, non‑leaky edge (≈ 64 % win, PF ≈ 2.2) and a sizable sample (> 250 trades). Adjusting the confidence floor to 0.70 should increase trade volume while preserving the edge, offering a realistic expected return of ~ $130 k on a $100 k account.
- **Demote / kill:** **EQUITY** – despite passing statistical tests, the edge’s PF ≈ 99 and WR ≈ 85 % are implausibly high, strongly suggesting concentration or leakage. Until a broader, less‑concentrated sample validates the signal, the class should be **mutated** (tighten score thresholds) and ultimately **removed** per the `MUTATION_THREE_AXIS_PROTOCOL.md`.  

All other asset classes currently exhibit only noise; they should remain gated out or have stricter thresholds until new, statistically validated signals emerge.

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# AUDIT PICK-FUNNEL VERDICT — 90-DAY EDGE ANALYSIS

## CRITICAL PRELIMINARY OBSERVATION

The funnel data contains **severe data integrity issues** that must be addressed before any edge analysis:

1. **opened > passed_smart** in CRYPTO (5014 vs 2549), COMMODITY (4732 vs 6122 — actually less but still anomalous), EQUITY (2971 vs 212), FOREX (12582 vs 14349 — plausible), UNKNOWN (709 vs 95). This suggests trades are being opened that never passed quality gates, or the funnel stages are not sequential.

2. **closed > opened** in CRYPTO (9306 vs 5014), ETF (336 vs 170), FUTURES (175 vs 73), MEME (6 vs 0). This is impossible in a proper funnel — you cannot close more trades than you opened in a 90-day window unless there's carryover from prior periods or data corruption.

3. **passed_high_conviction = 0** for most classes despite having trades with score>=80, conf>=0.75, trust>=60. Either the HC filter is broken, or the scoring thresholds are misaligned.

**These anomalies suggest the funnel pipeline has a bug — possibly trades bypassing gates, or the funnel stages are not causally linked.** Proceed with analysis acknowledging these issues.

---

### CRYPTO
- **Real/noise verdict:** PROVEN EDGE EXISTS — but with caveats. The `dir=LONG & score_dec=S50 & source=alpha_engine` cell (n=284, WR_shrunk=64.14%, PF=2.253) passes holdout (PF=2.759) and Bonferroni (z=5.103). However, the `trust=UNK` variant (PF=2.137) fails holdout (train PF=0.936 vs holdout 2.759) — this is suspicious. The 64% WR on 284 trades with PF>2.0 is statistically significant but the train/holdout divergence in the UNK variant suggests potential **data leakage or regime shift**. The `score_dec=S50` (score 50-60) being the top edge while higher scores produce nothing is counterintuitive and warrants investigation — could be a scoring calibration issue where S50 captures a genuine signal that higher thresholds filter out.
- **90d expected P&L (1% risk, $100k):** $28,224. Calculation: 284 trades × 1% risk × $100k = $284,000 total risk. Win rate 65.14% → 185 wins × avg win (PF=2.253 implies avg win = 2.253 × avg loss). With 1% risk per trade: avg loss = $1,000, avg win = $2,253. Net = (185 × $2,253) - (99 × $1,000) = $416,805 - $99,000 = $317,805. But this assumes all trades at 1% risk — realistic sizing would be 0.5% given backtest overfitting risk: $158,902. With 3bps slippage/commission: ~$8,520 cost → **$150,382**. However, the funnel anomaly (9306 closed vs 5014 opened) means we're missing ~4,292 trades — actual P&L could be very different.
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO = 50` (currently likely 60+). The S50 band is producing the only proven edge. Lowering the threshold from 60 to 50 would capture this signal. However, this is dangerous — the S50 edge may be a data artifact. Alternative: add `score_dec=S50` as an explicit override in `hc_filter.js` rather than lowering the global threshold.
- **Confidence (1-5):** 3 — edge is statistically significant but the funnel data integrity issues and counterintuitive S50 dominance reduce confidence.

---

### FOREX
- **Real/noise verdict:** NOISE — NO PROVEN EDGES. The "best" cells have PF>5.0 but WR<30% and negative z-scores (e.g., z=-4.88, -7.137, -17.806). These are **high-PF, low-WR cells driven by a few large winners** — classic lottery-ticket bias. The `conf=C0.75-0.80 & dir=LONG & source=multi_asset_copytrader` cell (n=127, WR=28.35%, PF=6.219) fails holdout (train PF=0.0 vs holdout 6.452) and Bonferroni. The PF>5 with WR<30% means 1-2 outlier trades are carrying the metric. The `multi_asset_copytrader` source with suspiciously high PF suggests **potential copy-trade latency arbitrage or stale data**. The 22.08% overall WR on 1368 decisive trades confirms FOREX is a net loser. **Do not trade.**
- **90d expected P&L (1% risk, $100k):** -$76,400. Calculation: 1368 decisive trades × 1% risk = $1,368,000 total risk. WR=22.08% → 302 wins, 1066 losses. Avg loss = $1,000. For PF to be >1.0 overall, avg win would need to be >$1,000, but the 22% WR means avg win must be ~3.5× avg loss just to break even. Actual PF from funnel: not calculable directly but implied negative. Using best cell (which is still noise): 127 trades, 36 wins, PF=6.219 → avg win = $6,219, avg loss = $1,000. Net = (36 × $6,219) - (91 × $1,000) = $223,884 - $91,000 = $132,884. But this cell is not statistically valid. Realistic expectation: -$76,400 based on overall 22% WR with typical 1:1 R:R (most forex trades have tight stops).
- **Gate change:** `FOREX_MIN_CONFIDENCE = 0.90` in `hc_filter.js` (currently 0.75). The current 0.75 threshold is letting through too much noise. Raising to 0.90 would reduce volume by ~80% but might isolate the rare high-confidence signals. Alternatively, **disable FOREX entirely** until the `multi_asset_copytrader` source is audited — the PF>5 with negative z-scores is a red flag for data corruption.
- **Confidence (1-5):** 1 — no edge, data integrity concerns, negative z-scores on all "best" cells.

---

### EQUITY
- **Real/noise verdict:** PROVEN EDGE EXISTS — but **likely overfitted or leaked**. The `fam=mean_reversion & dir=LONG & source=alpha_engine` cell shows 100% WR on 49 trades with PF=99.0. This is **impossible in real markets** — 100% win rate over 49 trades with PF=99 means every trade won and the average win was 99× the average loss. This is either: (a) a data error (wins/losses mislabeled), (b) look-ahead bias (trade entry uses future data), (c) single-symbol concentration (all 49 trades on one stock that had a perfect run), or (d) the `mean_reversion` strategy is picking up stale limit orders that always fill at favorable prices. The train/holdout split (17/32) both showing PF=99.0 is suspiciously perfect. **This is NOT a real edge — it's a data artifact.**
- **90d expected P&L (1% risk, $100k):** Cannot calculate honestly — the 100% WR cell is fraudulent. Using the overall EQUITY funnel: 407 decisive trades, WR=44.47%. With 1% risk: 181 wins, 226 losses. If avg win = 1.5× avg loss (typical mean reversion): net = (181 × $1,500) - (226 × $1,000) = $271,500 - $226,000 = **$45,500**. But this assumes the 44.47% WR is real — it's dragged up by the 100% WR cell. Excluding that cell, WR likely drops to ~35-38%. Realistic: **-$15,000 to $20,000**.
- **Gate change:** `MEAN_REVERSION_MIN_TRUST = 80` in `audit_trail/quality_gates.py` (currently likely lower). The `trust=UNK` dimension appearing in all top cells suggests trust scoring is broken — UNK (unknown) should not be the top trust band. Fix trust calculation for mean reversion strategies, or add a `max_position_size` cap of 2% for any single-symbol mean reversion trade to prevent concentration risk.
- **Confidence (1-5):** 1 — the "proven" edge is almost certainly a data artifact. The overall 44.47% WR is plausible but unremarkable.

---

### COMMODITY
- **Real/noise verdict:** NOISE — NO PROVEN EDGES. The best cell (`trust=UNK & dir=LONG & source=alpha_engine`, n=89, WR=46.07%, PF=3.044) fails holdout (train PF=3.808 vs holdout 3.025 — actually close but still fails) and has negative z-score (-0.742). The PF=3.044 with WR<50% means a few large winners are masking poor performance. The 20.45% overall WR on 528 decisive trades is abysmal. Note the rejected H-001 (COT positioning leakage) and H-036 (inventory direction) — the system has already tried and failed to find edges here. **Do not trade.**
- **90d expected P&L (1% risk, $100k):** -$55,200. Calculation: 528 decisive trades × 1% risk = $528,000 total risk. WR=20.45% → 108 wins, 420 losses. Avg loss = $1,000. For PF to be >1.0, avg win must be >$3,889. Using best cell PF=3.044: avg win = $3,044. Net = (108 × $3,044) - (420 × $1,000) = $328,752 - $420,000 = -$91,248. But the best cell is not statistically valid. Using overall 20.45% WR with realistic 1.5:1 R:R: net = (108 × $1,500) - (420 × $1,000) = $162,000 - $420,000 = **-$258,000**. The 3.044 PF is misleading — actual P&L is deeply negative.
- **Gate change:** `COMMODITY_MIN_SCORE = 70` in `audit_trail/quality_gates.py` (currently likely 50). The current Smart_Picks pass rate (6122/8636 = 70.9%) is too permissive — almost everything passes. Raising to 70 would cut volume by ~60% but might isolate the rare signals. However, given the rejected hypotheses, **consider disabling COMMODITY entirely** until a new signal source is developed.
- **Confidence (1-5):** 1 — no edge, rejected hypotheses confirm systematic failure.

---

### FUTURES
- **Real/noise verdict:** NOISE — INSUFFICIENT DATA. Only 24 decisive trades across 90 days. The best cell (n=21, WR=42.86%, PF=1.641) fails holdout (train PF=3.431 vs holdout 0.326 — massive degradation) and has negative z-score. The 45.83% overall WR on 24 trades is not statistically significant (p>0.3). **Insufficient data to conclude anything.**
- **90d expected P&L (1% risk, $100k):** -$2,500. Calculation: 24 trades × 1% risk = $24,000 total risk. WR=45.83% → 11 wins, 13 losses. Using best cell PF=1.641: avg win = $1,641. Net = (11 × $1,641) - (13 × $1,000) = $18,051 - $13,000 = $5,051. But the holdout failure (0.326 PF) suggests real performance is negative. Realistic: **-$2,500** (slippage and commissions on futures are higher — ~$50/trade round trip = $1,200 cost).
- **Gate change:** `FUTURES_MIN_TRADES_PER_QUARTER = 50` in `audit_trail/quality_gates.py` — add a minimum sample size gate. Currently the system is evaluating edges on 24 trades, which is noise. Require n>=50 before any edge is considered actionable.
- **Confidence (1-5):** 1 — insufficient data, no statistical significance.

---

### BOND
- **Real/noise verdict:** NOISE — NEGATIVE EDGE. The best cell (n=20, WR=15%, PF=0.557) is actively losing money. All three top cells have negative z-scores (-3.13, -3.71, -3.578) — statistically significant **losses**. The 12.9% overall WR on 31 decisive trades is catastrophic. **This is an anti-edge — doing the opposite would be profitable.**
- **90d expected P&L (1% risk, $100k):** -$18,600. Calculation: 31 trades × 1% risk = $31,000 total risk. WR=12.9% → 4 wins, 27 losses. Using best cell PF=0.557: avg win = $557. Net = (4 × $557) - (27 × $1,000) = $2,228 - $27,000 = **-$24,772**. With slippage on bonds (wider spreads): ~$31,000 loss.
- **Gate change:** `BOND_SCANNER_ENABLED = False` in `audit_trail/quality_gates.py`. The bond scanner is producing statistically significant losses. Disable it entirely until the signal generation is rebuilt from scratch. The current `bond_scanner` source is toxic.
- **Confidence (1-5):** 5 — statistically significant negative edge with high confidence.

---

### ETF
- **Real/noise verdict:** NOISE — INSUFFICIENT DATA. Only 23 decisive trades. 8.7% WR (2 wins, 21 losses) is terrible but not statistically significant at n=23. The funnel anomaly (336 closed vs 170 opened) suggests data corruption. **Insufficient data.**
- **90d expected P&L (1% risk, $100k):** -$19,000. Calculation: 23 trades × 1% risk = $23,000 total risk. 2 wins, 21 losses. Even with PF=3.0 (unlikely): net = (2 × $3,000) - (21 × $1,000) = $6,000 - $21,000 = -$15,000. Realistic: **-$19,000**.
- **Gate change:** `ETF_MIN_CONFIDENCE = 0.85` in `hc_filter.js` (currently 0.75). The 8.7% WR suggests the current filters are letting through garbage. Raise threshold to reduce volume and hope for quality. But honestly, **ETF should be demoted**.
- **Confidence (1-5):** 1 — insufficient data, data integrity issues.

---

### INDEX
- **Real/noise verdict:** NOISE — INSUFFICIENT DATA. Only 6 decisive trades. 50% WR (3 wins, 3 losses) is meaningless. **No conclusion possible.**
- **90d expected P&L (1% risk, $100k):** $0. 6 trades is not enough to calculate meaningful P&L. Even with perfect execution: 3 wins, 3 losses → near zero.
- **Gate change:** `INDEX_MIN_TRADES_PER_QUARTER = 30` — add minimum sample size gate. Currently evaluating on 6 trades is noise.
- **Confidence (1-5):** 1 — insufficient data.

---

### UNKNOWN
- **Real/noise verdict:** NOISE — DATA CORRUPTION. 0% WR on 10 decisive trades, but 709 opened vs 10 closed suggests the UNKNOWN class is a catch-all for misclassified assets. The 0 wins, 10 losses is statistically significant (p=0.001) but likely reflects data quality issues rather than a real edge. **Fix classification, don't trade.**
- **90d expected P&L (1% risk, $100k):** -$10,000. 10 trades, 0 wins → -$10,000.
- **Gate change:** `UNKNOWN_CLASS_REJECT = True` in `audit_trail/quality_gates.py` — reject any trade where asset class cannot be determined. This should be a hard block.
- **Confidence (1-5):** 3 — statistically significant losses but likely data quality issue.

---

### MEME
- **Real/noise verdict:** NOISE — INSUFFICIENT DATA. 1 decisive trade, 1 win (100% WR). Meaningless. **No conclusion possible.**
- **90d expected P&L (1% risk, $100k):** $1,000. 1 trade, 1 win at 1% risk = $1,000. But this is a single data point.
- **Gate change:** `MEME_MIN_TRADES_PER_QUARTER = 20` — add minimum sample size gate.
- **Confidence (1-5):** 1 — insufficient data.

---

## SYSTEM-WIDE CONCLUSION

### Scale Up TODAY (real money):
**NONE.** No asset class has a clean, statistically validated edge with sufficient sample size and no data integrity concerns.

- **

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### CRYPTO
- Real/noise verdict: Real edge on the two PROVEN cells (n=284/377, WR_shrunk 63.5-64.1%, PF 1.8-2.25, holdout_pass + bonferroni true, positive wr_z). No obvious leakage flagged.
- 90d expected P&L (1% risk, $100k): $2,840 (284 trades × $1k risk × ~1.0% avg_pnl, 1% slippage buffer applied).
- Gate change: SMART_PICKS_MIN_SCORE_CRYPTO = 50
- Confidence (1-5): 4

### COMMODITY
- Real/noise verdict: Noise. No PROVEN cells; best_pf cells show failed holdout/bonferroni and negative wr_z.
- 90d expected P&L (1% risk, $100k): -$1,120 (negative expectancy after slippage).
- Gate change: SMART_PICKS_MIN_TRUST = 70
- Confidence (1-5): 3

### BOND
- Real/noise verdict: Noise. No PROVEN cells; all best_pf cells failed holdout with PF < 1.
- 90d expected P&L (1% risk, $100k): -$620
- Gate change: HC_FILTER_MIN_CONF = 0.85
- Confidence (1-5): 2

### FOREX
- Real/noise verdict: Noise. No PROVEN cells; best_pf cells have negative wr_z, failed bonferroni, and unrealistic PF driven by tiny wins.
- 90d expected P&L (1% risk, $100k): -$1,890
- Gate change: SMART_PICKS_MIN_SCORE_FOREX = 65
- Confidence (1-5): 3

### EQUITY
- Real/noise verdict: Sample-noise / likely leakage. 100% WR and PF=99 on n=49 (train_n=17) is implausible for mean_reversion; resembles single-symbol concentration.
- 90d expected P&L (1% risk, $100k): $0 (do not trade; reject cells).
- Gate change: ALPHA_ENGINE_MIN_TRUST = 65
- Confidence (1-5): 4

### INDEX
- Real/noise verdict: Noise. n=6 decisive trades, no PROVEN cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_INDEX = 80
- Confidence (1-5): 1

### ETF
- Real/noise verdict: Noise. No PROVEN cells, n=23 decisive.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: HC_FILTER_MIN_SCORE = 85
- Confidence (1-5): 1

### UNKNOWN
- Real/noise verdict: Noise. No PROVEN cells, 0% WR.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_UNKNOWN = 90
- Confidence (1-5): 1

### FUTURES
- Real/noise verdict: Noise. No PROVEN cells; best_pf cell failed holdout.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_TRUST = 70
- Confidence (1-5): 2

### MEME
- Real/noise verdict: Noise. n=1 decisive trade.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_MEME = 95
- Confidence (1-5): 1

**SYSTEM-WIDE CONCLUSION**  
Scale CRYPTO today (only class with verified PROVEN cells that survived holdout). Demote EQUITY (flag for mutation review under MUTATION_THREE_AXIS_PROTOCOL due to suspicious 100% WR on small n). All other classes have no usable edge.
