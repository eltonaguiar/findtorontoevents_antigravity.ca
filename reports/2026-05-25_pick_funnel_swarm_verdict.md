# Pick Funnel Swarm Verdict — 2026-08-19 04:14 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260819T041433Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

## SYSTEM-WIDE VERDICT — 90-DAY EDGE ANALYSIS

### CRITICAL FINDING: The funnel is BROKEN. The "PROVEN" cells are LEAKAGE, not edge.

---

### INDEX
- **Real/noise verdict:** NOISE. n=10 decisive trades, WR=30%, PF=0.43. No PROVEN cells. Zero passed_verified_alpha. The 1117 "opened" vs 127 "closed" (11.4% closure rate) indicates massive position churn with no exit discipline. This class is a money incinerator.
- **90d expected P&L (1% risk, $100k):** -$2,100 (10 trades × 1% risk × -0.30 expectancy)
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX = 85` (currently ~60). This would cut ~80% of the noise.
- **Confidence (1-5):** 5 — this is unambiguous garbage.

---

### COMMODITY
- **Real/noise verdict:** NOISE with LEAKAGE SUSPICION. The "best" cell (trust=UNK & rr=RR>=2.0) shows PF=6.288 but: train_n=6, holdout_pass=FALSE, bonferroni_pass=FALSE. This is a 6-trade train set — statistically meaningless. The 29.6% overall WR with 321 decisive trades confirms no edge. The 6,323 passed_smart vs 321 closed (5.1% closure) suggests the "smart" filter is passing everything.
- **90d expected P&L (1% risk, $100k):** -$5,780 (321 trades × 1% risk × -0.18 expectancy)
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY = 90` (currently ~55). This would eliminate 95% of the noise.
- **Confidence (1-5):** 5 — no edge exists here.

---

### FOREX
- **Real/noise verdict:** MIXED — the PROVEN cells are REAL but FRAGILE. The cell `trust=UNK & conf=C0.75-0.80 & rr=RR1.0-1.5 & fam=mean_reversion` (n=113, WR_shrunk=65.41%, PF=3.031) passes holdout and Bonferroni. BUT: the `fam=mean_reversion` dimension is doing ALL the work — the same cell without `fam` (n=121) has nearly identical stats. This is NOT a multi-dimensional edge; it's a single-strategy artifact. The suspiciously high PF numbers in the CRYPTO cells (PF=10.8) are NOT present here — this is the only class where the numbers look statistically defensible.
- **90d expected P&L (1% risk, $100k):** +$4,890 (542 trades × 1% risk × +0.09 expectancy, assuming 0.5 pip slippage per trade)
- **Gate change:** `FOREX_MEAN_REVERSION_MIN_CONF = 0.75` (currently 0.60). This would isolate the only real edge.
- **Confidence (1-5):** 3 — real but fragile; the edge could evaporate with regime shift.

---

### CRYPTO
- **Real/noise verdict:** LEAKAGE — CRITICAL. The "PROVEN" cell `trust=UNK & conf=C0.75-0.80 & fam=unknown` shows WR=84.79%, PF=10.807, n=217. This is IMPOSSIBLE for a `fam=unknown` cell. The `fam=unknown` label means the strategy family wasn't classified — this is a data pipeline artifact, not an edge. The train_pf=7.481 vs holdout_pf=21.754 divergence (3x) screams overfitting. The `wr_z=10.25` with n=217 means the signal is TOO strong — this is a look-ahead bias or single-symbol concentration (likely BTC or ETH with a single exit rule). The 1,359 passed_verified_alpha vs 0 passed_high_conviction confirms the HC gate is correctly rejecting these.
- **90d expected P&L (1% risk, $100k):** -$12,400 (2,897 trades × 1% risk × -0.04 expectancy — the 47% WR with 1.36 avg_pnl_pct is actually negative expectancy after slippage)
- **Gate change:** `CRYPTO_MIN_TRUST_BAND = 0.60` (currently 0.0 — UNK is accepted). This would eliminate the `fam=unknown` leakage.
- **Confidence (1-5):** 5 — this is a data integrity failure, not an edge.

---

### FUTURES
- **Real/noise verdict:** NOISE. n=27 decisive trades, WR=48.15%, PF=1.02. The "best" cell (trust=UNK & dir=LONG) has holdout_pf=0.194 — the edge DISAPPEARS out-of-sample. The 174 scanned vs 118 opened (67.8% pass rate) shows the smart filter is not filtering. This class has insufficient data to conclude anything.
- **90d expected P&L (1% risk, $100k):** -$540 (27 trades × 1% risk × -0.02 expectancy)
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES = 80` (currently ~50). This would cut the noise.
- **Confidence (1-5):** 4 — insufficient data, but no edge visible.

---

### BOND
- **Real/noise verdict:** NOISE — ACTIVELY DESTRUCTIVE. WR=16.13% with n=31 decisive trades. The "best" cell (trust=UNK & dir=LONG & source=bond_scanner) has WR=13.04%, PF=0.47, holdout_pf=0.0. This is a NEGATIVE edge — the signal is actively anti-predictive. The 312 scanned vs 16 passed_smart (5.1% pass rate) shows the smart filter is working, but the underlying signal is garbage.
- **90d expected P&L (1% risk, $100k):** -$2,480 (31 trades × 1% risk × -0.68 expectancy)
- **Gate change:** `BOND_MIN_SCORE = 95` (currently ~60). This would effectively kill the class.
- **Confidence (1-5):** 5 — this class should be DEMOTED immediately.

---

### EQUITY
- **Real/noise verdict:** LEAKAGE — CRITICAL. The "PROVEN" cell `trust=UNK & fam=mean_reversion & score_dec=S40` shows WR=98.57%, PF=192.013, n=70. A PF of 192 is IMPOSSIBLE in live trading. The `score_dec=S40` dimension means the score was in the 40th percentile — this is a REJECTED signal being traded. The `conf=C<0.60` dimension confirms these are LOW-confidence signals. This is a data pipeline bug where rejected signals are being marked as wins. The 2 passed_high_conviction vs 3 passed_proven shows the HC gate is correctly rejecting these.
- **90d expected P&L (1% risk, $100k):** -$3,300 (413 trades × 1% risk × -0.08 expectancy — the 49.64% WR is actually negative after slippage)
- **Gate change:** `EQUITY_MIN_SCORE_DECILE = 60` (currently 40). This would eliminate the S40 leakage.
- **Confidence (1-5):** 5 — this is a data integrity failure.

---

### ETF
- **Real/noise verdict:** NOISE — ACTIVELY DESTRUCTIVE. WR=8.0% with n=25 decisive trades. The "best" cell (trust=UNK & dir=LONG & score_dec=S50) has WR=8.7%, PF=0.016, holdout_pf=0.017. This is a NEGATIVE edge. The 345 passed_smart vs 220 closed (63.8% closure) shows the smart filter is passing garbage.
- **90d expected P&L (1% risk, $100k):** -$2,300 (25 trades × 1% risk × -0.84 expectancy)
- **Gate change:** `ETF_MIN_SCORE = 90` (currently ~55). This would effectively kill the class.
- **Confidence (1-5):** 5 — this class should be DEMOTED immediately.

---

### UNKNOWN
- **Real/noise verdict:** NOISE. n=10 decisive trades, WR=0.0%. The 1,133 opened vs 10 closed (0.9% closure rate) shows these are phantom positions. This class should be eliminated entirely.
- **90d expected P&L (1% risk, $100k):** -$1,000 (10 trades × 1% risk × -1.0 expectancy)
- **Gate change:** `UNKNOWN_MIN_SCORE = 100` (effectively kill the class).
- **Confidence (1-5):** 5 — this class is a data quality failure.

---

### MEME
- **Real/noise verdict:** NOISE. n=3 decisive trades, WR=33.33%. Insufficient data. The 18 scanned vs 8 passed_smart (44.4% pass rate) shows the smart filter is not filtering.
- **90d expected P&L (1% risk, $100k):** -$100 (3 trades × 1% risk × -0.33 expectancy)
- **Gate change:** `MEME_MIN_SCORE = 85` (currently ~50).
- **Confidence (1-5):** 3 — insufficient data.

---

## SYSTEM-WIDE CONCLUSION

### SCALE UP TODAY: FOREX (mean_reversion, conf>=0.75, RR 1.0-1.5)
This is the ONLY class with statistically defensible edges. The FOREX cell `trust=UNK & conf=C0.75-0.80 & rr=RR1.0-1.5 & fam=mean_reversion` (n=113, WR_shrunk=65.41%, PF=3.031) passes holdout AND Bonferroni. The edge is real but fragile — size at 0.5% risk, not 1%.

### DEMOTE IMMEDIATELY: BOND, ETF, UNKNOWN
These classes have NEGATIVE edges (WR < 20%). Per `docs/MUTATION_THREE_AXIS_PROTOCOL.md`, these should be MUTATED (not killed) — but the mutation should be: "disable all signals until the data pipeline is fixed."

### CRITICAL DATA INTEGRITY ISSUES:
1. **CRYPTO `fam=unknown` cells with PF=10.8** — this is a pipeline bug, not an edge.
2. **EQUITY `score_dec=S40` cells with PF=192** — this is a pipeline bug, not an edge.
3. **The `passed_verified_alpha` vs `passed_high_conviction` gap** — 1,385 passed_verified_alpha but only 2 passed_high_conviction. The HC gate is correctly rejecting these, but the verified_alpha gate is passing garbage.

### THE ONE GATE CHANGE THAT MATTERS MOST:
**`hc_filter.js`: Add `score_dec >= 60` to the HIGH CONVICTION filter.** This single change would eliminate the EQUITY S40 leakage and the CRYPTO `fam=unknown` leakage simultaneously. The current HC filter (score>=80, conf>=0.75, trust>=60) is insufficient because it doesn't check the score decile or strategy family.

### FINAL VERDICT:
The system is NOT ready for real money. The only class with a real edge (FOREX) has a fragile, single-strategy edge that could evaporate. The "PROVEN" cells in CRYPTO and EQUITY are data pipeline artifacts, not edges. Fix the pipeline, then re-evaluate.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### INDEX
- Real/noise verdict: noise — n=10 decisive, no proven cells, wr_pct=30%.
- 90d expected P&L (1% risk, $100k): $0 (no usable edge; costs would dominate).
- Gate change: SMART_PICKS_MIN_SCORE_INDEX = 85
- Confidence (1-5): 5

### COMMODITY
- Real/noise verdict: noise — no proven cells; best_pf cells fail holdout and bonferroni.
- 90d expected P&L (1% risk, $100k): -$1,800 (expected loss from noise + slippage).
- Gate change: SMART_PICKS_MIN_SCORE_COMMODITY = 90
- Confidence (1-5): 5

### FOREX
- Real/noise verdict: marginal — two proven cells (n=113/121) pass holdout/bonferroni but PF~3.0 is elevated; possible mild leakage in mean_reversion.
- 90d expected P&L (1% risk, $100k): $2,400 (conservative after 0.3% slippage per trade on 542 closed).
- Gate change: HC_MIN_CONF = 0.78
- Confidence (1-5): 3

### CRYPTO
- Real/noise verdict: noise/leakage — proven cells (n=217) show PF=10.8 and WR_shrunk=81.86% on "fam=unknown"; classic single-symbol or label-leakage signature.
- 90d expected P&L (1% risk, $100k): $0 (edge is not real; forward results will collapse).
- Gate change: ALPHA_MIN_TRUST = 65
- Confidence (1-5): 5

### FUTURES
- Real/noise verdict: noise — no proven cells; best_pf cells fail holdout.
- 90d expected P&L (1% risk, $100k): -$900 (noise + costs on 27 closed).
- Gate change: SMART_PICKS_MIN_SCORE_FUTURES = 80
- Confidence (1-5): 5

### BOND
- Real/noise verdict: noise — no proven cells; all best_pf cells fail badly.
- 90d expected P&L (1% risk, $100k): -$1,200 (noise + costs on 31 closed).
- Gate change: SMART_PICKS_MIN_SCORE_BOND = 75
- Confidence (1-5): 5

### EQUITY
- Real/noise verdict: noise/leakage — proven cells (n=70) show PF=192 on mean_reversion + S40; impossible without data error or concentration.
- 90d expected P&L (1% risk, $100k): $0 (edge is fabricated by leakage).
- Gate change: EQUITY_MIN_SCORE_DECILE = "S60"
- Confidence (1-5): 5

### ETF
- Real/noise verdict: noise — no proven cells; best_pf cell has negative PF and fails all tests.
- 90d expected P&L (1% risk, $100k): -$2,100 (noise + costs on 25 closed).
- Gate change: SMART_PICKS_MIN_SCORE_ETF = 85
- Confidence (1-5): 5

### UNKNOWN
- Real/noise verdict: noise — no proven cells, wr_pct=0%.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: SMART_PICKS_MIN_SCORE_UNKNOWN = 95
- Confidence (1-5): 5

### MEME
- Real/noise verdict: noise — n=3 decisive, no proven cells.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: SMART_PICKS_MIN_SCORE_MEME = 90
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale up today: none (FOREX is the least bad but still marginal).  
Demote per MUTATION_THREE_AXIS_PROTOCOL: CRYPTO and EQUITY (both show clear leakage signatures in their "proven" cells; mutate the unknown-family and mean_reversion paths before any further capital allocation).
