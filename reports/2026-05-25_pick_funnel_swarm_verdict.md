# Pick Funnel Swarm Verdict — 2026-09-05 04:10 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260905T040933Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

## SYSTEM-WIDE DIAGNOSTIC — CRITICAL DATA INTEGRITY ISSUES

Before per-class analysis, I must flag **severe funnel inconsistencies** that undermine the entire dataset:

1. **EQUITY**: `opened=4440` vs `passed_smart=235` — 4,205 trades opened that FAILED the smart gate. This is either a massive execution bug or the funnel is measuring different populations.
2. **FOREX**: `passed_smart=22,310` out of `23,461` scanned (95% pass rate) — the smart gate is not filtering at all.
3. **CRYPTO**: `opened=10,141` vs `passed_smart=3,122` — 7,019 trades opened that failed the gate.
4. **COMMODITY**: `opened=7,043` vs `passed_smart=4,974` — 2,069 trades opened that failed the gate.
5. **UNKNOWN**: `opened=1,391` vs `passed_smart=175` — 1,216 trades opened that failed the gate.

**The `opened` column appears to represent ALL trades taken, not just those passing the smart gate.** This means the win rates and edge calculations are computed on a population that includes trades that should have been filtered out. The "PROVEN" cells may be artifacts of this contamination.

---

### EQUITY
- **Real/noise verdict**: **LIKELY LEAKAGE / DATA ERROR**. The `mean_reversion & score_dec=S40` cell shows WR=98.55% (68/69 wins), PF=218.25, avg_pnl=1.26%. This is statistically impossible for real markets. With n=69 and 68 wins, the binomial probability of this occurring by chance is ~10^-15. The train/holdout split (27/42) with holdout PF=129.4 confirms this is not a stable edge — it's a data artifact. The `conf=C<0.60` dimension is particularly suspicious: low-confidence trades showing 98% win rate is a classic sign of look-ahead bias or mislabeled outcomes. **The 4,205 trades opened that failed the smart gate suggest the "closed" population (231) is a tiny, non-representative subset.**
- **90d expected P&L (1% risk, $100k)**: **$0 — DO NOT TRADE**. If forced: 231 closed × 1% risk × $1,000 = $2,310 risked. At 64.07% WR with avg_win≈avg_loss (PF≈1.78 implied), expected P&L ≈ $2,310 × (0.6407 × 0.78 - 0.3593 × 1.0) ≈ **+$325**. But this assumes the WR is real, which it is not.
- **Gate change**: `SMART_PICKS_MIN_SCORE_EQUITY = 70` (currently likely ~50-60). This would filter the 4,205 rogue trades and force the funnel to only count gated trades.
- **Confidence (1-5)**: **1** — Data integrity compromised; edge is artifact.

---

### FOREX
- **Real/noise verdict**: **NOISE**. Zero PROVEN cells. The best cell (`conf=C0.75-0.80 & rr=RR1.0-1.5 & dir=LONG`) has n=41, WR_shrunk=63.93%, PF=3.967, but `bonferroni_pass=false` and `wr_z=2.655` (below 3.0 threshold). The train/holdout PF collapse (5.68 → 1.903) confirms instability. The 95% smart-gate pass rate means the gate is not discriminating — the entire FOREX population is being traded indiscriminately. The 527 decisive trades out of 1,430 closed (37%) suggests massive non-decisive noise. **The suspiciously high PF numbers you flagged are NOT present in this data — the best PF is 3.967, which is plausible but not statistically significant after multiple-comparison correction.**
- **90d expected P&L (1% risk, $100k)**: 527 decisive × 1% risk × $1,000 = $5,270 risked. At 43.26% WR with avg_win≈avg_loss (PF≈0.76), expected P&L ≈ $5,270 × (0.4326 × 0.76 - 0.5674 × 1.0) ≈ **-$1,255**. Negative edge confirmed.
- **Gate change**: `SMART_PICKS_MIN_SCORE_FOREX = 80` (currently likely ~30-40 given 95% pass rate). This would cut the 22,310 "passed" to a meaningful subset.
- **Confidence (1-5)**: **1** — No edge; gate is broken.

---

### CRYPTO
- **Real/noise verdict**: **MIXED — ONE REAL EDGE, BUT CONTAMINATED**. The `conf=C0.75-0.80 & score_dec=S50 & source=alpha_engine` cell shows n=221, WR_shrunk=75.1%, PF=4.065, holdout_pass=true, bonferroni_pass=true, wr_z=8.141. This is statistically robust. However: (a) the `trust=UNK` dimension appearing in the top cells means trust is NOT contributing — the edge exists regardless of trust band; (b) the 7,019 trades opened that failed the smart gate contaminate the broader population; (c) the 1,806 `passed_verified_alpha` vs 0 `passed_high_conviction` suggests the HC gate (score≥80, conf≥0.75, trust≥60) is filtering out ALL crypto trades — yet the edge cell has conf=0.75-0.80, which should pass. **The HC gate is likely checking a different confidence variable than what's stored in the edge cells.**
- **90d expected P&L (1% risk, $100k)**: If we ONLY traded the proven cell (n=221): 221 × 1% risk × $1,000 = $2,210 risked. At 75.1% WR with PF=4.065, avg_win = 4.065 × avg_loss. Expected P&L ≈ $2,210 × (0.751 × 4.065/(1+4.065) - 0.249 × 1/(1+4.065)) × (1+4.065) ≈ **+$4,850**. But this requires the HC gate to actually pass these trades — currently it doesn't.
- **Gate change**: `HC_FILTER_MIN_CONFIDENCE = 0.75` (currently likely 0.75 but checking wrong variable) AND `HC_FILTER_MIN_SCORE = 50` (currently 80 — the edge cell has score_dec=S50, not S80). The score_dec=S50 means the score is in the 50-59 range, which fails the current ≥80 threshold.
- **Confidence (1-5)**: **3** — Edge is real but gate configuration prevents capture.

---

### COMMODITY
- **Real/noise verdict**: **NOISE / LEAKAGE RECURRENCE RISK**. Zero PROVEN cells. The best cell (`rr=RR>=2.0 & source=alpha_engine`) has n=38, WR_shrunk=63.79%, PF=7.199, but `bonferroni_pass=false`, `wr_z=2.595`, and train/holdout PF collapse (13.027 → 3.869). The n=38 is below the n≥50 threshold for reliability. **Given H-001 (COT look-ahead) and H-036 (inventory direction) were both rejected, and this cell shows high PF with low n, I flag this as potential leakage recurrence — the `source=alpha_engine` dimension may be picking up the same contaminated signals.**
- **90d expected P&L (1% risk, $100k)**: 207 decisive × 1% risk × $1,000 = $2,070 risked. At 36.23% WR with PF≈0.57, expected P&L ≈ $2,070 × (0.3623 × 0.57 - 0.6377 × 1.0) ≈ **-$890**. Negative edge.
- **Gate change**: `SMART_PICKS_MIN_SCORE_COMMODITY = 75` (currently likely ~50). Additionally, add timestamp validation to ensure no pre-publication data usage per H-001.
- **Confidence (1-5)**: **1** — No edge; potential leakage.

---

### ETF
- **Real/noise verdict**: **NOISE — INSUFFICIENT DATA**. n=9 closed trades, WR=11.11% (1 win). Zero PROVEN cells. The 279 `passed_smart` vs 9 `closed` (3.2% closure rate) suggests most ETF signals never reach decisive outcomes. Cannot conclude anything from n=9.
- **90d expected P&L (1% risk, $100k)**: 9 × 1% risk × $1,000 = $90 risked. At 11.11% WR, expected P&L ≈ $90 × (0.111 × 0.5 - 0.889 × 1.0) ≈ **-$72**. Negligible but negative.
- **Gate change**: `SMART_PICKS_MIN_SCORE_ETF = 65` (currently likely ~50). But more importantly, require `MIN_CLOSED_TRADES = 30` before any ETF signal is actionable.
- **Confidence (1-5)**: **1** — No data to support any edge.

---

### FUTURES
- **Real/noise verdict**: **NOISE**. n=21 closed, WR=42.86%, PF=1.616. The best cell has `holdout_pass=false` and `wr_z=-0.654` (negative z-score). Zero PROVEN cells. The 1 `passed_verified_alpha` out of 108 `passed_smart` (0.9%) shows the verified alpha gate is nearly impossible to pass for futures. **H-005 was already rejected — this data confirms no futures edge exists.**
- **90d expected P&L (1% risk, $100k)**: 21 × 1% risk × $1,000 = $210 risked. At 42.86% WR with PF=1.616, expected P&L ≈ $210 × (0.4286 × 1.616/(1+1.616) - 0.5714 × 1/(1+1.616)) × (1+1.616) ≈ **-$15**. Essentially break-even with negative tilt.
- **Gate change**: `SMART_PICKS_MIN_SCORE_FUTURES = 85` (currently likely ~50). This would effectively kill futures trading, which is appropriate.
- **Confidence (1-5)**: **1** — No edge; confirmed by prior rejection.

---

### UNKNOWN
- **Real/noise verdict**: **NOISE — DATA QUALITY ISSUE**. n=9 closed, WR=0% (0 wins). Zero PROVEN cells. The 1,391 `opened` vs 175 `passed_smart` (8× more opened than passed) indicates the UNKNOWN class is receiving trades that should have been classified elsewhere. **The 0% WR with n=9 is consistent with random noise, but the funnel contamination suggests these trades may be misclassified from other classes.**
- **90d expected P&L (1% risk, $100k)**: 9 × 1% risk × $1,000 = $90 risked. At 0% WR, expected P&L ≈ **-$90**. Total loss.
- **Gate change**: `SMART_PICKS_MIN_SCORE_UNKNOWN = 90` (effectively kill). Better: fix asset classification so UNKNOWN is never populated.
- **Confidence (1-5)**: **1** — No edge; classification bug.

---

### BOND
- **Real/noise verdict**: **NOISE**. n=23 closed, WR=21.74%, PF≈0.28. Zero PROVEN cells. The 16 `passed_smart` out of 338 scanned (4.7% pass rate) shows the gate IS filtering, but the filtered signals still lose. The 315 `opened` vs 16 `passed_smart` (20× more opened than passed) confirms the funnel contamination.
- **90d expected P&L (1% risk, $100k)**: 23 × 1% risk × $1,000 = $230 risked. At 21.74% WR with PF≈0.28, expected P&L ≈ $230 × (0.2174 × 0.28 - 0.7826 × 1.0) ≈ **-$166**. Negative edge.
- **Gate change**: `SMART_PICKS_MIN_SCORE_BOND = 80` (currently likely ~50). This would cut the 315 rogue trades.
- **Confidence (1-5)**: **1** — No edge.

---

### INDEX
- **Real/noise verdict**: **NOISE — INSUFFICIENT DATA**. n=9 decisive (but 13 closed, 4 non-decisive), WR=22.22%. Zero PROVEN cells. The 1,195 `passed_smart` vs 13 `closed` (1.1% closure rate) shows INDEX signals rarely reach decisive outcomes. Cannot conclude anything from n=9.
- **90d expected P&L (1% risk, $100k)**: 9 × 1% risk × $1,000 = $90 risked. At 22.22% WR, expected P&L ≈ $90 × (0.222 × 0.5 - 0.778 × 1.0) ≈ **-$60**. Negligible but negative.
- **Gate change**: `SMART_PICKS_MIN_SCORE_INDEX = 75` (currently likely ~50). Require `MIN_CLOSED_TRADES = 30`.
- **Confidence (1-5)**: **1** — No data to support any edge.

---

### MEME
- **Real/noise verdict**: **NOISE — INSUFFICIENT DATA**. n=4 closed, WR=25%. Zero PROVEN cells. The 20 scanned instruments is far too small for any statistical conclusion. The 1 `passed_verified_alpha` out of 11 `passed_smart` (9%) shows some filtering, but n=4 closed trades is meaningless.
- **90d expected P&L (1% risk, $100k)**: 4 × 1% risk × $1,000 = $40 risked. At 25% WR, expected P&L ≈ $40 × (0.25 × 0.5 - 0.75 × 1.0) ≈ **-$25**. Negligible.
- **Gate change**: `SMART_PICKS_MIN_SCORE_MEME = 85` (effectively kill). MEME is too volatile and thinly traded for systematic edge.
- **Confidence (1-5)**: **1** — No data.

---

## SYSTEM-WIDE CONCLUSION

### Scale Up TODAY:
**CRYPTO** — but ONLY the specific cell: `conf=C0.75-0.80 & score_dec=S50 & source=alpha_engine`. This is the only statistically validated edge in the entire dataset (bonferroni_pass=true, holdout_pass=true, wr_z=8.141). However, I would NOT deploy until the HC gate is fixed to actually pass these trades. Current configuration (score≥80) excludes them.

### Demote per MUTATION_THREE_AXIS_PROTOCOL:
**FOREX** — 95% smart-gate pass rate means no filtering. 43.26% WR with negative PF. **MUTATE**: Fix the gate to actually discriminate (target <30% pass rate), then re-test. If still negative after 30 days, KILL.

**COMMODITY** — 36.23% WR, PF=0.57, and prior rejected hypotheses (H-001, H-036) suggest systemic data issues. **MUTATE**: Add timestamp validation and dedup, then re-test. If still negative, KILL.

**BOND** — 21.74% WR, PF=0.28. **KILL** immediately. No path to profitability.

**UNKNOWN** — 0% WR. **KILL** immediately. Fix classification bug.

**ETF, INDEX, MEME, FUTURES** — Insufficient data or confirmed no-edge. **DEMOTE** to observation-only status. Do not allocate capital.

### CRITICAL ACTION ITEMS (before any deployment):
1. **Fix the funnel**: The `opened` column must only count trades that passed the smart gate. Currently 15,000+ trades are being opened that fail the gate.
2. **Fix the HC gate**: `hc_filter.js` is checking score≥80, but the proven edge has score_dec=S50. Either lower the threshold or fix the score variable being checked.
3. **Investigate EQUITY mean_reversion**: 98.55% WR with PF=218 is impossible. This is either a data labeling error or look-ahead bias. Do NOT trade until root cause is identified.
4. **Add timestamp validation** to all sources to prevent pre-publication data usage (per H-001).

**Bottom line**: The only real edge in 90 days of data is CRYPTO at conf=0.75-0.80, score_dec=S50, source=alpha_engine. Everything else is noise, contamination, or insufficient data. The system has severe data integrity issues that must be fixed before any real-money deployment.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### EQUITY
- Real/noise verdict: Noise/leakage — 98.55% WR and PF=218 on n=69 is statistically impossible without single-symbol concentration or look-ahead; shrunk WR still inflated.
- 90d expected P&L (1% risk, $100k): $0 (edge invalid).
- Gate change: SMART_PICKS_MIN_SCORE_EQUITY = 65.
- Confidence (1-5): 5

### FOREX
- Real/noise verdict: Noise — no PROVEN cells; best cells fail Bonferroni and have small n=41 with unstable holdout.
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: HC_MIN_CONF = 0.82.
- Confidence (1-5): 4

### CRYPTO
- Real/noise verdict: Real — n=220-221, WR_shrunk 75%, PF=4.06, holdout_pass=true, Bonferroni=true across multiple overlapping cells; high but internally consistent.
- 90d expected P&L (1% risk, $100k): ~$28,500 (220 edge trades at ~1.45% avg pnl, 1% risk/trade, 0.15% slippage, 0.8 fill rate).
- Gate change: SMART_PICKS_MIN_SCORE_CRYPTO = 48.
- Confidence (1-5): 4

### COMMODITY
- Real/noise verdict: Noise — no PROVEN cells; best cells fail Bonferroni with n=38.
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: ALPHA_MIN_TRUST = 55.
- Confidence (1-5): 4

### ETF
- Real/noise verdict: Noise — n=9 decisive, zero PROVEN or viable cells.
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: N/A.
- Confidence (1-5): 5

### FUTURES
- Real/noise verdict: Noise — n=21, no PROVEN, holdout fails.
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: N/A.
- Confidence (1-5): 5

### UNKNOWN
- Real/noise verdict: Noise — n=9, empty edge lists.
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: N/A.
- Confidence (1-5): 5

### BOND
- Real/noise verdict: Noise — n=23, no PROVEN cells.
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: N/A.
- Confidence (1-5): 5

### INDEX
- Real/noise verdict: Noise — n=9, no PROVEN cells.
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: N/A.
- Confidence (1-5): 5

### MEME
- Real/noise verdict: Noise — n=4, no PROVEN cells.
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: N/A.
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale CRYPTO today (only class with statistically validated edge). Demote EQUITY (leakage risk) and FOREX (no edge) per MUTATION_THREE_AXIS_PROTOCOL.md.
