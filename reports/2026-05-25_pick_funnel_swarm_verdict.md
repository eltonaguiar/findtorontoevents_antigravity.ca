# Pick Funnel Swarm Verdict — 2026-09-04 04:10 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260904T041021Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

## SYSTEM-WIDE VERDICT — 90-DAY EDGE ANALYSIS

### EQUITY
- **Real/noise verdict**: **REAL BUT SUSPICIOUSLY PERFECT** — The mean_reversion/S40 cell (n=69, WR_shrunk=87.64%, PF=217.3) is statistically significant (z=8.07, Bonferroni pass) BUT a 98.55% raw WR with PF=217 is **not a real edge — it's a data artifact**. This pattern (near-perfect WR, massive PF, all LONG) is classic **look-ahead leakage or survivorship bias**. The train/holdout split (28/41) shows consistency, but real edges don't produce 98.55% WR on 69 trades. **Flag as leakage recurrence** — likely the "opened" count (4364) vs "passed_smart" (233) mismatch means the funnel is capturing trades that never went through the quality gates.
- **90d expected P&L (1% risk, $100k)**: **$0 — DO NOT TRADE THIS CELL**. If forced: 69 trades × 1% risk × avg_win ~1.25% × 98.55% WR ≈ **$8,500** but this is phantom P&L from a broken signal.
- **Gate change**: `SMART_PICKS_MIN_SCORE_EQUITY` = **85** (raise from current to force higher-quality signals through the funnel — currently 233 passed_smart but 4364 opened means the gate isn't filtering)
- **Confidence (1-5)**: **1** — This is a leakage red flag, not an edge.

---

### COMMODITY
- **Real/noise verdict**: **NOISE** — Best cell (rr=RR>=2.0, n=38, WR_shrunk=63.79%, PF=7.199) fails Bonferroni (z=2.595 < critical ~3.5). Train/holdout PF (13.03/3.87) shows massive decay. The overall class WR is 36.54% (n=208) — **below breakeven**. The 4956 passed_smart vs 0 passed_verified_alpha confirms the smart gate is passing garbage. **No proven edge exists.**
- **90d expected P&L (1% risk, $100k)**: **-$2,100** (208 closed × 1% risk × 36.54% WR × avg_win 1.5% − 63.46% × avg_loss 1.5% ≈ −$2,100)
- **Gate change**: `SMART_PICKS_MIN_SCORE_COMMODITY` = **90** (currently passing 67.6% of scanned — should be <10%)
- **Confidence (1-5)**: **1** — No edge, actively bleeding money.

---

### FOREX
- **Real/noise verdict**: **NOISE** — Best cell (conf=C0.75-0.80 & rr=RR1.0-1.5 & dir=LONG, n=41, WR_shrunk=63.93%, PF=3.967) fails Bonferroni (z=2.655). Train/holdout PF (5.68/1.90) shows 66% decay. The 21993 passed_smart out of 23136 scanned (95% pass rate) means the smart gate is **completely non-discriminatory**. Overall WR 43.13% (n=524) is below breakeven. **No proven edge.**
- **90d expected P&L (1% risk, $100k)**: **-$3,800** (524 closed × 1% risk × 43.13% WR × avg_win 0.8% − 56.87% × avg_loss 0.8% ≈ −$3,800)
- **Gate change**: `SMART_PICKS_MIN_SCORE_FOREX` = **85** (currently passing 95% — should be <20%)
- **Confidence (1-5)**: **1** — The gate is a sieve, not a filter.

---

### CRYPTO
- **Real/noise verdict**: **REAL BUT NARROW** — The conf=C0.75-0.80 & score_dec=S50 & source=alpha_engine cell (n=220, WR_shrunk=75.42%, PF=4.249) is statistically significant (z=8.226, Bonferroni pass). Train/holdout PF (3.31/6.43) shows **improvement** in holdout — this is the strongest signal in the entire dataset. However, **all three "proven" cells are the same underlying signal** (the dir=LONG and trust=UNK variants are subsets/supersets). The 1771 passed_verified_alpha vs 0 passed_high_conviction means the HC gate (score>=80, conf>=0.75, trust>=60) is **too strict on trust** — these trades have conf=0.75-0.80 but trust=UNK, so they're being filtered out.
- **90d expected P&L (1% risk, $100k)**: **+$8,900** (220 trades × 1% risk × 75.42% WR × avg_win 1.47% − 24.58% × avg_loss 0.35% ≈ $8,900). Assumes 0.1% slippage per trade.
- **Gate change**: `HC_MIN_TRUST_CRYPTO` = **0** (in `hc_filter.js` — currently trust>=60 is blocking these proven trades; the trust=UNK dimension doesn't hurt performance)
- **Confidence (1-5)**: **4** — Real edge, but narrow (only 220 trades in 90d). The 1771 verified_alpha vs 0 HC gap is the smoking gun.

---

### ETF
- **Real/noise verdict**: **NOISE** — n=9 closed trades, WR=11.11%. No edge. The 275 passed_smart vs 0 verified_alpha confirms gate failure.
- **90d expected P&L (1% risk, $100k)**: **-$700** (9 trades × 1% risk × 11.11% WR ≈ −$700)
- **Gate change**: `SMART_PICKS_MIN_SCORE_ETF` = **95** (kill the class — only 315 scanned in 90d, not enough volume)
- **Confidence (1-5)**: **1** — No edge, insufficient data.

---

### FUTURES
- **Real/noise verdict**: **NOISE** — n=23, WR=47.83%, best cell fails holdout (holdout_pass=false). No proven edge. The 106 passed_smart vs 1 verified_alpha confirms gate failure.
- **90d expected P&L (1% risk, $100k)**: **-$100** (23 trades × 1% risk × 47.83% WR ≈ −$100)
- **Gate change**: `SMART_PICKS_MIN_SCORE_FUTURES` = **90**
- **Confidence (1-5)**: **1** — No edge.

---

### UNKNOWN
- **Real/noise verdict**: **NOISE** — n=9, WR=0%. No edge. The 172 passed_smart vs 0 verified_alpha confirms the class is misclassified garbage.
- **90d expected P&L (1% risk, $100k)**: **-$900** (9 trades × 1% risk × 0% WR ≈ −$900)
- **Gate change**: **KILL THE CLASS** — set `SMART_PICKS_MIN_SCORE_UNKNOWN` = **100** (never pass)
- **Confidence (1-5)**: **1** — No edge, actively destructive.

---

### BOND
- **Real/noise verdict**: **NOISE** — n=23, WR=21.74%. No edge. The 16 passed_smart vs 0 verified_alpha confirms gate failure.
- **90d expected P&L (1% risk, $100k)**: **-$1,300** (23 trades × 1% risk × 21.74% WR ≈ −$1,300)
- **Gate change**: `SMART_PICKS_MIN_SCORE_BOND` = **95**
- **Confidence (1-5)**: **1** — No edge.

---

### INDEX
- **Real/noise verdict**: **NOISE** — n=9, WR=22.22%. No edge. The 1195 passed_smart vs 0 verified_alpha confirms the gate is passing everything.
- **90d expected P&L (1% risk, $100k)**: **-$700** (9 trades × 1% risk × 22.22% WR ≈ −$700)
- **Gate change**: `SMART_PICKS_MIN_SCORE_INDEX` = **95**
- **Confidence (1-5)**: **1** — No edge.

---

### MEME
- **Real/noise verdict**: **NOISE** — n=4, WR=25%. Insufficient data. No edge.
- **90d expected P&L (1% risk, $100k)**: **-$300** (4 trades × 1% risk × 25% WR ≈ −$300)
- **Gate change**: `SMART_PICKS_MIN_SCORE_MEME` = **95**
- **Confidence (1-5)**: **1** — No edge, insufficient data.

---

## SYSTEM-WIDE CONCLUSION

### SCALE UP TODAY: **CRYPTO** (narrowly)
The conf=C0.75-0.80 & score_dec=S50 & source=alpha_engine cell is the **only statistically proven edge** in the entire dataset (z=8.226, Bonferroni pass, holdout PF=6.43). The fix is simple: **lower HC_MIN_TRUST_CRYPTO from 60 to 0** in `hc_filter.js`. This would unlock ~1771 verified_alpha trades that are currently blocked. Expected 90d P&L at 1% risk: **+$8,900** on the proven cell alone, potentially **+$30,000+** if the broader verified_alpha pool (1771 trades) maintains similar characteristics.

### DEMOTE / KILL: **COMMODITY, FOREX, ETF, FUTURES, BOND, INDEX, UNKNOWN, MEME**
Per `docs/MUTATION_THREE_AXIS_PROTOCOL.md`:
- **COMMODITY**: MUTATE — the rr=RR>=2.0 cell shows promise (PF=7.2) but needs more data. Set SMART_PICKS_MIN_SCORE_COMMODITY=90 and re-test in 30d.
- **FOREX**: KILL — 95% pass rate through smart gate means the gate is meaningless. The class has 524 closed trades with 43.13% WR — no amount of filtering will fix a fundamentally broken signal.
- **ETF, FUTURES, BOND, INDEX, UNKNOWN, MEME**: KILL — insufficient data (n<25) and WR below breakeven. These classes are burning capital on noise.

### CRITICAL WARNINGS:
1. **EQUITY mean_reversion cell is LEAKAGE, not edge** — 98.55% WR with PF=217 is impossible in live trading. Investigate the funnel mismatch (233 passed_smart vs 4364 opened) immediately.
2. **The funnel is broken** — Across all classes, `opened` >> `passed_smart`. This means trades are being opened WITHOUT passing through the quality gates. The gates are decorative, not functional.
3. **The HC gate is too strict on trust** — CRYPTO's proven edge has trust=UNK, but HC_MIN_TRUST=60 blocks it. Trust is not a predictor of performance in this dataset.

### FINAL VERDICT:
**Only CRYPTO has a real, tradeable edge.** Everything else is noise or leakage. Fix the CRYPTO trust gate, kill the dead classes, and investigate the EQUITY leakage before scaling anything.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

**### CRYPTO**
- Real/noise verdict: Real edge. n=219-220 closed trades, WR_shrunk 75.4-75.7%, PF 4.25 with clean train/holdout split and bonferroni pass. No obvious single-symbol concentration or timestamp leakage visible.
- 90d expected P&L (1% risk, $100k): ~$8,400 (220 trades × 1.47% avg edge after 0.15% slippage/commissions, 1% risk per trade).
- Gate change: `SMART_PICKS_MIN_SCORE_CRYPTO` = 50
- Confidence (1-5): 4

**### EQUITY**
- Real/noise verdict: Sample-noise / leakage. n=69 but WR 98.55% (shrunk 87.6%) and PF 217 are statistically impossible without single-symbol concentration or look-ahead. Mean-reversion S40 cell is rejected.
- 90d expected P&L (1% risk, $100k): -$2,100 (edge collapses out-of-sample; expect mean-reversion to revert to ~48% WR).
- Gate change: `SMART_PICKS_MIN_SCORE_EQUITY` = 65
- Confidence (1-5): 5

**### FOREX**
- Real/noise verdict: Noise. n=41 cells fail bonferroni; holdout PF drops sharply. No proven cells.
- 90d expected P&L (1% risk, $100k): $0 (no reliable edge after multiple-testing correction).
- Gate change: `HC_FILTER_MIN_CONF` = 0.82
- Confidence (1-5): 4

**### COMMODITY**
- Real/noise verdict: Noise. n=38 cells fail bonferroni; holdout degradation visible. Matches prior rejected COT/inventory hypotheses.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: `SMART_PICKS_MIN_TRUST_COMMODITY` = 70
- Confidence (1-5): 4

**### FUTURES / BOND / ETF / INDEX / MEME / UNKNOWN**
- Real/noise verdict: Noise. All n≤23 or empty proven lists; no cells survive shrinkage + holdout + bonferroni.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: `HC_FILTER_MIN_SCORE` = 75 (global)
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale CRYPTO today (only class with statistically credible, holdout-validated edge). Demote EQUITY immediately per MUTATION_THREE_AXIS_PROTOCOL (mutate the mean-reversion S40 path before any further capital allocation). All other classes produce zero or negative expectancy after proper correction.
