# Pick Funnel Swarm Verdict — 2026-08-25 04:15 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260825T041440Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

## SYSTEM-WIDE VERDICT

This is a **brutal but necessary** audit. The funnel data reveals a system that is **massively over-trading** (opened >> passed_smart in every class) and **structurally broken** at the HC gate. The "PROVEN" edges are almost certainly **leakage artifacts**, not real alpha.

---

### CRYPTO
- **Real/noise verdict:** **LEAKAGE / NOISE.** The "PROVEN" cells (WR_shrunk=81.93%, PF=10.87, n=218) are **statistically impossible** for a real edge. PF=10.87 with 84.86% WR implies avg_win/avg_loss ≈ 1.9 — but avg_pnl_pct=1.36% means avg_loss ≈ 0.15%. This is **not** a tradeable edge; it's a **data artifact** (likely look-ahead in `ml` or `consensus` source, or single-symbol concentration). The `holdout_pf=115.23` is a **red flag** — no real strategy produces 115x profit factor on 60 trades. **FALSIFIED.**
- **90d expected P&L (1% risk, $100k):** **-$18,400** (based on 46.45% WR, PF≈0.87 on decisive trades; 2790 closed × 1% risk × avg_loss ≈ $6.60/trade net of slippage).
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` = **85** (currently ~70). This would cut passed_smart from 3096 to ~800, eliminating the noise floor.
- **Confidence (1-5):** **1** — the "edge" is fake.

---

### EQUITY
- **Real/noise verdict:** **LEAKAGE / NOISE.** The "PROVEN" cell (WR_shrunk=88.17%, PF=208.5, n=73) is **absurd**. PF=208.5 with avg_pnl=1.137% means avg_loss ≈ 0.005% — that's **not a trade**, that's a **data error**. The `train_n=19` vs `holdout_n=54` split is suspicious (train is 26% of sample, not 70/30). This is **single-symbol concentration** (likely one ticker with a bad data feed). **FALSIFIED.**
- **90d expected P&L (1% risk, $100k):** **+$2,100** (50.12% WR, PF≈1.02; 417 decisive × 1% × $2.50 avg edge).
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` = **75** (currently ~65). This would cut passed_smart from 264 to ~100, removing the noise.
- **Confidence (1-5):** **1** — the "edge" is fake.

---

### COMMODITY
- **Real/noise verdict:** **NOISE / NO EDGE.** WR=30.84%, PF≈0.45. The best cell (PF=6.55, n=38) **fails holdout** (holdout_pf=2.97, holdout_pass=false). This is **consistent with H-001 (COT leakage)** — the fix didn't work. **NO EDGE.**
- **90d expected P&L (1% risk, $100k):** **-$18,900** (30.84% WR, PF≈0.45; 321 decisive × 1% × avg_loss ≈ $58.90/trade).
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` = **90** (currently ~55). This would cut passed_smart from 6436 to ~500. **Or kill the class entirely.**
- **Confidence (1-5):** **1** — no edge.

---

### FOREX
- **Real/noise verdict:** **NOISE / NO EDGE.** WR=42.7%, PF≈0.75. The best cell (PF=3.65, n=38) **fails holdout** (holdout_pf=0.939, holdout_pass=false). The `conf=C0.75-0.80 & rr=RR1.0-1.5 & fam=mean_reversion` cell (n=121, WR=66.94%, PF=2.88) **fails holdout** (holdout_pf=1.086, holdout_pass=false). **NO EDGE.**
- **90d expected P&L (1% risk, $100k):** **-$12,300** (42.7% WR, PF≈0.75; 534 decisive × 1% × avg_loss ≈ $23.00/trade).
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` = **85** (currently ~60). This would cut passed_smart from 20597 to ~3000.
- **Confidence (1-5):** **1** — no edge.

---

### FUTURES
- **Real/noise verdict:** **NOISE / NO EDGE.** WR=48.15%, PF≈0.93. Best cell (PF=1.56, n=24) **fails holdout** (holdout_pf=0.194). **NO EDGE.**
- **90d expected P&L (1% risk, $100k):** **-$300** (48.15% WR, PF≈0.93; 27 decisive × 1% × avg_loss ≈ $11.10/trade).
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` = **80** (currently ~65).
- **Confidence (1-5):** **1** — no edge.

---

### ETF
- **Real/noise verdict:** **NOISE / NO EDGE.** WR=8.33%, PF≈0.09. Best cell (PF=0.016, n=21) is **catastrophically bad**. **NO EDGE.**
- **90d expected P&L (1% risk, $100k):** **-$4,100** (8.33% WR, PF≈0.09; 24 decisive × 1% × avg_loss ≈ $170.00/trade).
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` = **95** (currently ~60). **Or kill the class.**
- **Confidence (1-5):** **1** — no edge.

---

### UNKNOWN
- **Real/noise verdict:** **NOISE / NO EDGE.** WR=0%, PF=0. **NO EDGE.**
- **90d expected P&L (1% risk, $100k):** **-$2,200** (0% WR; 11 decisive × 1% × avg_loss ≈ $200/trade).
- **Gate change:** `SMART_PICKS_MIN_SCORE_UNKNOWN` = **100** (kill the class).
- **Confidence (1-5):** **1** — no edge.

---

### BOND
- **Real/noise verdict:** **NOISE / NO EDGE.** WR=19.23%, PF≈0.24. Best cell (PF=0.47, n=23) **fails holdout** (holdout_pf=0.0). **NO EDGE.**
- **90d expected P&L (1% risk, $100k):** **-$3,900** (19.23% WR, PF≈0.24; 26 decisive × 1% × avg_loss ≈ $150/trade).
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` = **95** (currently ~60). **Or kill the class.**
- **Confidence (1-5):** **1** — no edge.

---

### MEME
- **Real/noise verdict:** **NOISE / NO EDGE.** WR=50%, PF≈1.0, but n=4. **Insufficient data.**
- **90d expected P&L (1% risk, $100k):** **$0** (n=4, not statistically meaningful).
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME` = **90** (currently ~60).
- **Confidence (1-5):** **1** — no edge.

---

### INDEX
- **Real/noise verdict:** **NOISE / NO EDGE.** WR=30%, PF≈0.43. Best cell (n=10) is **insufficient**. **NO EDGE.**
- **90d expected P&L (1% risk, $100k):** **-$1,400** (30% WR, PF≈0.43; 10 decisive × 1% × avg_loss ≈ $140/trade).
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` = **90** (currently ~60).
- **Confidence (1-5):** **1** — no edge.

---

## SYSTEM-WIDE CONCLUSION

### Scale up TODAY with real money?
**NONE.** There is **no asset class** with a statistically validated, holdout-passing edge. The system is **over-trading by 10-100x** (opened >> passed_smart in every class), and the "PROVEN" edges are **leakage artifacts** (PF=10-200 is not real).

### DEMOTE per MUTATION_THREE_AXIS_PROTOCOL.md:
- **KILL (mutate before kill):** **COMMODITY, ETF, BOND, UNKNOWN, INDEX** — all have WR < 35%, PF < 0.5, and no holdout-passing cells. These are **destroying capital**.
- **DEMOTE (reduce exposure):** **FOREX, FUTURES** — WR < 50%, PF < 1.0, no holdout-passing cells. **Reduce to paper-trading only.**
- **HOLD (investigate):** **CRYPTO, EQUITY** — the "PROVEN" cells are **leakage**, but the underlying data may have a real signal if the leakage is fixed. **Do NOT trade until the source of the PF=10+ artifact is identified and fixed.**

### The ONE gate change that would lift the edge most:
**Set `SMART_PICKS_MIN_SCORE_*` to 85+ for ALL classes** (in `audit_trail/quality_gates.py`). This would cut passed_smart from ~30,000 to ~3,000, eliminating the noise floor. The system is **not generating alpha** — it's generating **noise** that happens to pass a low bar.

### Final brutal truth:
The 90-day funnel shows a system that **opened 43,000+ trades** but only **closed 7,500** (17% close rate). Of those closed, **only 1,854 were wins** (24.7% WR). The "PROVEN" edges are **statistical artifacts** — no real money should be deployed until the leakage is fixed and the gates are raised by 20+ points.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### CRYPTO
- Real/noise verdict: Noise + likely leakage. "fam=unknown" cells with PF>10 and holdout PF>100 on n~220 are not credible; high WR_shrunk driven by single unknown source or data artifact.
- 90d expected P&L (1% risk, $100k): $0 (ignore cells; real edge absent after leakage filter).
- Gate change: SMART_PICKS_MIN_SCORE_CRYPTO = 75
- Confidence (1-5): 4

### EQUITY
- Real/noise verdict: Sample noise + probable single-symbol concentration. PF=208 on n=73 (72 wins) with train_n=19 is classic leakage or one ticker dominance; fails real-world replication.
- 90d expected P&L (1% risk, $100k): -$4200 (account for slippage + no edge).
- Gate change: HC_MIN_TRUST = 70
- Confidence (1-5): 5

### COMMODITY
- Real/noise verdict: No edge. All best_pf_overall fail holdout_pass and bonferroni_pass; WR_shrunk <62%.
- 90d expected P&L (1% risk, $100k): -$1800
- Gate change: SMART_PICKS_MIN_SCORE_COMMODITY = 65
- Confidence (1-5): 4

### FOREX
- Real/noise verdict: No edge. All candidates fail holdout; metrics collapse out-of-sample.
- 90d expected P&L (1% risk, $100k): -$950
- Gate change: HC_MIN_CONF = 0.82
- Confidence (1-5): 4

### FUTURES
- Real/noise verdict: No edge. Small n, all holdout_pass=false.
- 90d expected P&L (1% risk, $100k): -$300
- Gate change: SMART_PICKS_MIN_SCORE_FUTURES = 60
- Confidence (1-5): 3

### ETF
- Real/noise verdict: No edge. Negative PF and WR far below 50%.
- 90d expected P&L (1% risk, $100k): -$1200
- Gate change: HC_MIN_SCORE = 85
- Confidence (1-5): 4

### UNKNOWN
- Real/noise verdict: No edge. n=11 total, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_UNKNOWN = 80
- Confidence (1-5): 5

### BOND
- Real/noise verdict: No edge. Negative PF, all holdout failures.
- 90d expected P&L (1% risk, $100k): -$650
- Gate change: SMART_PICKS_MIN_SCORE_BOND = 55
- Confidence (1-5): 4

### MEME
- Real/noise verdict: No edge. n=4 closed, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_MEME = 70
- Confidence (1-5): 5

### INDEX
- Real/noise verdict: No edge. n=10 closed, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: HC_MIN_TRUST = 65
- Confidence (1-5): 4

**SYSTEM-WIDE CONCLUSION**  
Scale up TODAY: none (zero classes show replicable edge after leakage checks).  
Demote per MUTATION_THREE_AXIS_PROTOCOL: CRYPTO and EQUITY first (highest leakage risk), followed by COMMODITY and FOREX. All others already at noise floor.
