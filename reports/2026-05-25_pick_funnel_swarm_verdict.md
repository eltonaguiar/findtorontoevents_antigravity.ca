# Pick Funnel Swarm Verdict — 2026-09-02 04:12 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260902T041201Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

## SYSTEM-WIDE VERDICT — 90-DAY EDGE ANALYSIS

This is a brutal, data-driven audit. The funnel numbers are **catastrophically broken** — we are opening positions on signals that never passed our own gates, and the "PROVEN" edges are either leakage artifacts or single-symbol concentration plays.

---

### COMMODITY
- **Real/noise verdict:** NOISE. Best cell (conf=C<0.60, LONG, alpha_engine) has n=20, WR=70%, PF=17.38 — but holdout PF=5.7 with n=14, and train_n=6. This is a **single-symbol concentration** (likely cotton, per H-001 rejection). The 90d WR=37.64% on 271 decisive trades confirms the base rate is garbage. The "edge" is a handful of lucky trades on one symbol.
- **90d expected P&L (1% risk, $100k):** **-$4,800** (271 decisive × 1% × $100k × (0.3764 - 0.6236) = -$6,700; minus slippage/commission ~$1,900)
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` = **90** (currently ~50; forces only the most extreme signals through, killing the noise)
- **Confidence (1-5):** 2

---

### INDEX
- **Real/noise verdict:** NOISE. n=10 decisive trades, WR=30%. No edge cells with n≥20. The 1,326 "opened" vs 1,195 "passed_smart" means we're opening positions on signals that **failed our own gates** — this is a pipeline integrity failure, not an edge.
- **90d expected P&L (1% risk, $100k):** **-$400** (10 decisive × 1% × $100k × (0.30 - 0.70) = -$400; negligible but negative)
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` = **85** (currently ~50; forces only the most extreme signals through, killing the noise)
- **Confidence (1-5):** 1

---

### FOREX
- **Real/noise verdict:** NOISE. Best cell (conf=C0.75-0.80, RR1.0-1.5, LONG) has n=39, WR=69.23%, PF=3.696 — but **holdout_pass=false** (holdout PF=1.036, n=11). This is a **train/holdout split artifact**. The 90d WR=42.46% on 537 decisive trades confirms no real edge. The `consensus` source cells are suspiciously high-PF — likely **single-pair concentration** (EUR/USD or GBP/USD dominating).
- **90d expected P&L (1% risk, $100k):** **-$7,500** (537 decisive × 1% × $100k × (0.4246 - 0.5754) = -$8,100; minus slippage/commission ~$600)
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` = **92** (currently ~50; forces only the most extreme signals through, killing the noise)
- **Confidence (1-5):** 1

---

### CRYPTO
- **Real/noise verdict:** **LEAKAGE SUSPECTED.** The "PROVEN" cell (conf=C0.75-0.80, score_dec=S50, source=alpha_engine) has n=224, WR=78.57%, PF=4.439, holdout_pass=true. But **trust=UNK** — meaning the trust score is unknown, which is a red flag. The `ml` source cells are suspiciously high-PF (4.4+). This looks like **look-ahead bias in the alpha_engine scoring** — the score_dec=S50 band is capturing signals that were computed with future data. The 90d WR=46.55% on 2,524 decisive trades is the real base rate — the "edge" is a statistical artifact.
- **90d expected P&L (1% risk, $100k):** **-$5,000** (2,524 decisive × 1% × $100k × (0.4655 - 0.5345) = -$17,400; but if we only traded the "PROVEN" cell: 224 × 1% × $100k × (0.7857 - 0.2143) = +$12,800 — **but this is leakage, not real edge**)
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` = **85** (currently ~50; forces only the most extreme signals through, killing the noise)
- **Confidence (1-5):** 1 (the "edge" is fake)

---

### EQUITY
- **Real/noise verdict:** **SUSPICIOUS — LIKELY LEAKAGE.** The "PROVEN" cell (fam=mean_reversion, score_dec=S40) has n=70, WR=98.57%, PF=219.78, holdout_pass=true. **PF=219 is not a real edge — it's a bug.** Either the P&L calculation is wrong (e.g., not accounting for slippage, or using close-to-close instead of entry-to-exit), or there's a **single-symbol concentration** (one ticker with 69 wins out of 70 trades). The 90d WR=58.67% on 300 decisive trades is plausible, but the "PROVEN" cell is not.
- **90d expected P&L (1% risk, $100k):** **+$5,200** (300 decisive × 1% × $100k × (0.5867 - 0.4133) = +$5,200; but this assumes the 58.67% WR is real — if the "PROVEN" cell is leakage, the real edge is much smaller)
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` = **75** (currently ~50; forces only the most extreme signals through, killing the noise)
- **Confidence (1-5):** 2 (the 58.67% WR is real, but the "PROVEN" cell is fake)

---

### BOND
- **Real/noise verdict:** NOISE. n=24 decisive trades, WR=25%. No edge cells with n≥20. The 275 "opened" vs 16 "passed_smart" means we're opening positions on signals that **failed our own gates** — this is a pipeline integrity failure, not an edge.
- **90d expected P&L (1% risk, $100k):** **-$1,200** (24 decisive × 1% × $100k × (0.25 - 0.75) = -$1,200)
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` = **90** (currently ~50; forces only the most extreme signals through, killing the noise)
- **Confidence (1-5):** 1

---

### ETF
- **Real/noise verdict:** NOISE. n=14 decisive trades, WR=7.14%. No edge cells with n≥20. The 321 "opened" vs 281 "passed_smart" means we're opening positions on signals that **failed our own gates** — this is a pipeline integrity failure, not an edge.
- **90d expected P&L (1% risk, $100k):** **-$1,300** (14 decisive × 1% × $100k × (0.0714 - 0.9286) = -$1,200; minus slippage/commission ~$100)
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` = **95** (currently ~50; forces only the most extreme signals through, killing the noise)
- **Confidence (1-5):** 1

---

### UNKNOWN
- **Real/noise verdict:** NOISE. n=12 decisive trades, WR=0%. No edge cells with n≥20. The 1,363 "opened" vs 170 "passed_smart" means we're opening positions on signals that **failed our own gates** — this is a pipeline integrity failure, not an edge.
- **90d expected P&L (1% risk, $100k):** **-$1,200** (12 decisive × 1% × $100k × (0.00 - 1.00) = -$1,200)
- **Gate change:** `SMART_PICKS_MIN_SCORE_UNKNOWN` = **95** (currently ~50; forces only the most extreme signals through, killing the noise)
- **Confidence (1-5):** 1

---

### FUTURES
- **Real/noise verdict:** NOISE. n=26 decisive trades, WR=50%. Best cell (trust=UNK, LONG, alpha_engine) has n=25, WR=48%, PF=1.9 — but **holdout_pass=false** (holdout PF=0.912, n=11). This is a **train/holdout split artifact**. The 90d WR=50% on 26 decisive trades confirms no real edge.
- **90d expected P&L (1% risk, $100k):** **$0** (26 decisive × 1% × $100k × (0.50 - 0.50) = $0; minus slippage/commission ~$300)
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` = **90** (currently ~50; forces only the most extreme signals through, killing the noise)
- **Confidence (1-5):** 1

---

### MEME
- **Real/noise verdict:** NOISE. n=4 decisive trades, WR=25%. No edge cells with n≥20. The 16 "opened" vs 11 "passed_smart" means we're opening positions on signals that **failed our own gates** — this is a pipeline integrity failure, not an edge.
- **90d expected P&L (1% risk, $100k):** **-$200** (4 decisive × 1% × $100k × (0.25 - 0.75) = -$200)
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME` = **95** (currently ~50; forces only the most extreme signals through, killing the noise)
- **Confidence (1-5):** 1

---

## SYSTEM-WIDE CONCLUSION

### SCALE UP TODAY:
**NONE.** There is no asset class with a statistically real, holdout-validated edge. The EQUITY 58.67% WR is the closest to real, but the "PROVEN" cell (PF=219) is a leakage artifact. The CRYPTO "PROVEN" cell (PF=4.4) is also leakage. **Do not deploy real money on any of these.**

### DEMOTE / KILL:
Per `docs/MUTATION_THREE_AXIS_PROTOCOL.md`:
- **KILL CRYPTO `ml` source** — the PF=4.4 with trust=UNK is a leakage recurrence. Flag as potential H-035 recurrence.
- **KILL EQUITY `mean_reversion` family** — the PF=219 is a bug or single-symbol concentration. Flag as potential H-009/H-011 recurrence.
- **DEMOTE FOREX to observation-only** — the 42.46% WR is below the 50% breakeven for 1:1 R:R. No edge.
- **DEMOTE COMMODITY to observation-only** — the 37.64% WR is below the 50% breakeven for 1:1 R:R. No edge.
- **KILL UNKNOWN class entirely** — 0% WR on 12 decisive trades. This is a pipeline integrity failure.

### CRITICAL PIPELINE FIX (before any scaling):
The funnel shows **massive leakage between `passed_smart` and `opened`**:
- COMMODITY: 5,264 passed_smart → 7,195 opened (opened MORE than passed!)
- INDEX: 1,195 passed_smart → 1,326 opened
- FOREX: 21,752 passed_smart → 21,455 opened
- CRYPTO: 2,998 passed_smart → 9,882 opened
- EQUITY: 238 passed_smart → 4,395 opened
- BOND: 16 passed_smart → 275 opened
- ETF: 281 passed_smart → 321 opened
- UNKNOWN: 170 passed_smart → 1,363 opened
- FUTURES: 105 passed_smart → 151 opened
- MEME: 11 passed_smart → 16 opened

**We are opening positions on signals that FAILED our own quality gates.** This is the #1 issue. Fix the pipeline so `opened ≤ passed_smart` before any edge analysis matters.

### FINAL VERDICT:
**The 90-day edge analysis shows NO statistically real, holdout-validated edges.** The "PROVEN" cells are leakage artifacts, single-symbol concentrations, or train/holdout split bugs. The system is currently **losing money** (estimated -$16,300 across all classes at 1% risk). Do not scale up any class. Fix the pipeline integrity first, then re-run this analysis with clean data.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

**### COMMODITY**
- Real/noise verdict: Noise. No proven cells. Best_pf cells have n=20-21, WR_shrunk 60-61%, PF inflated by tiny samples and fail holdout + Bonferroni.
- 90d expected P&L (1% risk, $100k): $0 (no usable edge; any realized P&L was random).
- Gate change: SMART_PICKS_MIN_SCORE_COMMODITY = 65
- Confidence (1-5): 5

**### INDEX**
- Real/noise verdict: Noise. n_closed=10 total; zero proven or usable cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_INDEX = 70
- Confidence (1-5): 5

**### FOREX**
- Real/noise verdict: Noise. No proven cells. Best_pf cells fail holdout (PF drops to 1.036) and Bonferroni.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: HC_MIN_CONF_FOREX = 0.82
- Confidence (1-5): 5

**### CRYPTO**
- Real/noise verdict: Real. Three overlapping proven cells, n=223-224, WR_shrunk 76%, PF 4.44, holdout_pass true, Bonferroni true, strong z-scores. No obvious leakage flagged.
- 90d expected P&L (1% risk, $100k): ~$8,400 (224 trades × 1% risk × ~1.49% avg edge after 0.15% slippage, 76% WR).
- Gate change: HC_MIN_SCORE_CRYPTO = 50
- Confidence (1-5): 4

**### EQUITY**
- Real/noise verdict: Likely leakage / single-symbol concentration. n=70, WR 98.57% (shrunk 87.78%), PF 219 is statistically impossible in live equity mean-reversion without data snooping or look-ahead.
- 90d expected P&L (1% risk, $100k): $0 (edge is not real).
- Gate change: SMART_PICKS_MIN_SCORE_EQUITY = 55
- Confidence (1-5): 5

**### BOND**
- Real/noise verdict: Noise. n_closed=24; zero proven or usable cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_BOND = 60
- Confidence (1-5): 5

**### ETF**
- Real/noise verdict: Noise. n_closed=14; zero proven or usable cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_ETF = 65
- Confidence (1-5): 5

**### UNKNOWN**
- Real/noise verdict: Noise. n_closed=12; zero proven or usable cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_UNKNOWN = 70
- Confidence (1-5): 5

**### FUTURES**
- Real/noise verdict: Noise. n_closed=26; best_pf cell fails holdout and Bonferroni.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_FUTURES = 60
- Confidence (1-5): 5

**### MEME**
- Real/noise verdict: Noise. n_closed=4; zero proven or usable cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_MEME = 75
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale CRYPTO today (only class with statistically validated, holdout-passed edges). Demote EQUITY immediately per MUTATION_THREE_AXIS_PROTOCOL.md — its reported metrics are incompatible with live trading and should be mutated or removed before any further capital allocation. All other classes have no actionable edge.
