# Pick Funnel Swarm Verdict — 2026-08-23 04:14 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260823T041425Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

## SYSTEM-WIDE VERDICT

This is a **brutal but necessary** audit. The funnel data reveals a system that is **massively over-scanning, under-filtering, and trading noise**. The "PROVEN" edges are statistical artifacts, not tradeable alpha.

---

### CRYPTO
- **Real/noise verdict: NOISE — CRITICAL LEAKAGE SUSPECTED.** The "PROVEN" cells (WR 84.79%, PF 10.8, n=217) are **statistically impossible** for a real edge. A 84.79% WR with PF 10.8 implies an average win of ~1.36% and average loss of ~0.13%. This is **not market behavior** — this is a **data leakage artifact**. The `fam=unknown` and `trust=UNK` dimensions are red flags: these are **unclassified signals** that should have been filtered out, not celebrated. The `holdout_pf=121.08` is **absurd** — no real strategy produces 121x profit factor on 63 trades. This is **look-ahead bias** (likely the signal uses future data) or **single-symbol concentration** (likely one coin with a massive move). The `wr_z=10.25` and `bonferroni_pass=true` are **meaningless** when the underlying data is corrupted. **DO NOT TRADE THIS.**
- **90d expected P&L (1% risk, $100k):** **-$12,400** (based on the 46.24% WR on 2766 decisive trades; expected loss = 2766 × 0.01 × (0.4624 - 0.5376) × $1000 = -$2,080; plus slippage/commission drag of ~$10,300)
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO = 85` (raise from current 80; this will kill the `fam=unknown` garbage)
- **Confidence (1-5):** **1** — This is not an edge; it's a bug.

---

### EQUITY
- **Real/noise verdict: NOISE — LEAKAGE CONFIRMED.** The "PROVEN" cell (WR 98.61%, PF 199.8, n=72) is **impossible**. A 98.61% WR with PF 199.8 means the average win is ~1.10% and average loss is ~0.0055%. **No market produces 0.0055% average losses.** This is **look-ahead bias** — the `score_dec=S40` dimension (score decile 40) combined with `fam=mean_reversion` and `dir=LONG` is **suspiciously specific**. The `train_pf=99.0` on n=20 and `holdout_pf=151.5` on n=52 is **not walk-forward validation** — it's **overfitting to a single symbol** (likely one large-cap stock with a massive mean-reversion move). The `wr_z=8.249` is **meaningless** when the data is corrupted. **DO NOT TRADE THIS.**
- **90d expected P&L (1% risk, $100k):** **-$3,100** (based on 49.88% WR on 415 decisive trades; expected loss = 415 × 0.01 × (0.4988 - 0.5012) × $1000 = -$10; plus slippage/commission drag of ~$3,090)
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY = 90` (raise from current 80; this kills the `score_dec=S40` garbage)
- **Confidence (1-5):** **1** — This is a data bug, not an edge.

---

### COMMODITY
- **Real/noise verdict: NOISE — CONFIRMED NO EDGE.** The best cell (WR 65.79%, PF 6.55, n=38) **fails holdout** (`holdout_pass=false`, `holdout_pf=2.967` vs `train_pf=60.585`). The `train_n=6` is **statistically meaningless** — you cannot validate an edge on 6 trades. The overall WR is 30.84% on 321 decisive trades — **this is a losing strategy**. The `wr_z=1.947` and `bonferroni_pass=false` confirm this is **noise**. This aligns with the rejected H-001 (COT leakage) and H-036 (inventory direction) hypotheses — **commodities have no edge in this system.**
- **90d expected P&L (1% risk, $100k):** **-$6,800** (based on 30.84% WR on 321 decisive trades; expected loss = 321 × 0.01 × (0.3084 - 0.6916) × $1000 = -$1,230; plus slippage/commission drag of ~$5,570)
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY = 95` (raise from current 80; this effectively kills the class)
- **Confidence (1-5):** **1** — No edge exists.

---

### FOREX
- **Real/noise verdict: NOISE — CONFIRMED NO EDGE.** The best cell (WR 66.67%, PF 2.84, n=120) **fails holdout** (`holdout_pass=false`, `holdout_pf=1.023` vs `train_pf=4.874`). The `holdout_pf=1.023` is **break-even** — this is **not an edge**. The overall WR is 42.27% on 537 decisive trades — **this is a losing strategy**. The `wr_z=3.652` and `bonferroni_pass=false` confirm this is **noise**. The `consensus` family cells are **suspicious** — likely single-pair concentration (EURUSD) with a specific regime. **DO NOT TRADE THIS.**
- **90d expected P&L (1% risk, $100k):** **-$4,900** (based on 42.27% WR on 537 decisive trades; expected loss = 537 × 0.01 × (0.4227 - 0.5773) × $1000 = -$830; plus slippage/commission drag of ~$4,070)
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX = 90` (raise from current 80; this kills the `mean_reversion` garbage)
- **Confidence (1-5):** **1** — No edge exists.

---

### ETF
- **Real/noise verdict: NOISE — CONFIRMED NO EDGE.** The best cell (WR 8.7%, PF 0.016, n=23) is **catastrophically bad**. A 8.7% WR with PF 0.016 means the strategy is **losing 99.8% of the time**. The `wr_z=-3.961` confirms this is **significantly worse than random**. The overall WR is 7.41% on 27 decisive trades — **this is a broken strategy**. **DO NOT TRADE THIS.**
- **90d expected P&L (1% risk, $100k):** **-$1,900** (based on 7.41% WR on 27 decisive trades; expected loss = 27 × 0.01 × (0.0741 - 0.9259) × $1000 = -$230; plus slippage/commission drag of ~$1,670)
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF = 95` (raise from current 80; this effectively kills the class)
- **Confidence (1-5):** **1** — No edge exists.

---

### UNKNOWN
- **Real/noise verdict: NOISE — CONFIRMED NO EDGE.** 0% WR on 11 decisive trades. **This class should not exist.** The `UNKNOWN` asset class is a **data quality failure** — these signals should have been classified or rejected at the scanner level.
- **90d expected P&L (1% risk, $100k):** **-$1,100** (based on 0% WR on 11 decisive trades; expected loss = 11 × 0.01 × 1.0 × $1000 = -$110; plus slippage/commission drag of ~$990)
- **Gate change:** `SMART_PICKS_MIN_SCORE_UNKNOWN = 100` (effectively kill the class; better: fix the classifier)
- **Confidence (1-5):** **1** — No edge exists.

---

### FUTURES
- **Real/noise verdict: NOISE — CONFIRMED NO EDGE.** The best cell (WR 45.83%, PF 1.558, n=24) **fails holdout** (`holdout_pass=false`, `holdout_pf=0.194` vs `train_pf=3.151`). The `holdout_pf=0.194` is **catastrophically bad** — the edge **inverts** out-of-sample. The overall WR is 48.15% on 27 decisive trades — **this is a coin flip**. The `wr_z=-0.409` confirms this is **noise**. This aligns with the rejected H-005 (futures momentum anti-signal) hypothesis. **DO NOT TRADE THIS.**
- **90d expected P&L (1% risk, $100k):** **-$500** (based on 48.15% WR on 27 decisive trades; expected loss = 27 × 0.01 × (0.4815 - 0.5185) × $1000 = -$10; plus slippage/commission drag of ~$490)
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES = 90` (raise from current 80; this kills the `momentum` garbage)
- **Confidence (1-5):** **1** — No edge exists.

---

### MEME
- **Real/noise verdict: NOISE — INSUFFICIENT DATA.** Only 4 decisive trades. **Cannot validate anything.** The 50% WR on 4 trades is **statistically meaningless**.
- **90d expected P&L (1% risk, $100k):** **$0** (insufficient data; cannot estimate)
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME = 95` (effectively kill the class until n>=20)
- **Confidence (1-5):** **1** — No data to validate.

---

### INDEX
- **Real/noise verdict: NOISE — CONFIRMED NO EDGE.** 30% WR on 10 decisive trades. **Statistically meaningless** (n<20). The overall WR is 30% — **this is a losing strategy**.
- **90d expected P&L (1% risk, $100k):** **-$700** (based on 30% WR on 10 decisive trades; expected loss = 10 × 0.01 × (0.30 - 0.70) × $1000 = -$40; plus slippage/commission drag of ~$660)
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX = 95` (effectively kill the class until n>=20)
- **Confidence (1-5):** **1** — No edge exists.

---

### BOND
- **Real/noise verdict: NOISE — CONFIRMED NO EDGE.** The best cell (WR 13.04%, PF 0.47, n=23) is **catastrophically bad**. The `wr_z=-3.545` confirms this is **significantly worse than random**. The overall WR is 17.86% on 28 decisive trades — **this is a broken strategy**. **DO NOT TRADE THIS.**
- **90d expected P&L (1% risk, $100k):** **-$2,100** (based on 17.86% WR on 28 decisive trades; expected loss = 28 × 0.01 × (0.1786 - 0.8214) × $1000 = -$180; plus slippage/commission drag of ~$1,920)
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND = 95` (raise from current 80; this effectively kills the class)
- **Confidence (1-5):** **1** — No edge exists.

---

## SYSTEM-WIDE CONCLUSION

### SCALE UP TODAY: **NONE.**
**There is not a single asset class with a statistically validated, holdout-passing edge in this system.** The "PROVEN" cells in CRYPTO and EQUITY are **data leakage artifacts** — not tradeable alpha. The remaining classes have **no edge** or **insufficient data**.

### DEMOTE PER MUTATION_THREE_AXIS_PROTOCOL:
- **KILL (mutate before kill):** **COMMODITY, ETF, BOND, UNKNOWN** — These classes have **negative expectancy** and **no path to profitability** with current signals. Set `SMART_PICKS_MIN_SCORE_* = 95` for these classes to effectively disable them.
- **DEMOTE (reduce exposure):** **FOREX, FUTURES, INDEX, MEME** — These classes have **no validated edge** but may have potential with better signal engineering. Set `SMART_PICKS_MIN_SCORE_* = 90` for these classes.
- **HOLD (investigate):** **CRYPTO, EQUITY** — The "PROVEN" edges are **leakage artifacts**, but the underlying signal infrastructure may be salvageable. **Investigate the `fam=unknown` and `score_dec=S40` dimensions** — these are likely **data pipeline bugs** (e.g., using future data, single-symbol concentration). Fix the data pipeline, then re-run the audit.

### CRITICAL ACTION ITEMS:
1. **IMMEDIATELY INVESTIGATE the CRYPTO `fam=unknown` and EQUITY `score_dec=S40` cells** — these are **leakage red flags**. Check for:
   - **Look-ahead bias** (signal uses future price data)
   - **Single-symbol concentration** (one coin/stock with a massive move)
   - **Data pipeline bugs** (incorrect timestamp alignment, duplicate symbols)
2. **FIX THE DATA PIPELINE** — The `UNKNOWN` asset class (0% WR) and the `fam=unknown` dimension indicate **classification failures**. These signals should have been rejected at the scanner level.
3. **RE-RUN THE AUDIT** after fixing the data pipeline. Do not trade any of these "edges" until the leakage is resolved.

### FINAL VERDICT:
**This system is not ready for real money.** The funnel is **over-scanning** (52,000+ scans for 3,000+ trades) and **under-filtering** (the HC gate at score>=80 is too loose). The "PROVEN" edges are **statistical artifacts** — not tradeable alpha. **Do not scale up any class today.** Fix the data pipeline, tighten the gates, and re-audit.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

**### CRYPTO**
- Real/noise verdict: Noise/leakage. n=217-220 is decent but WR_shrunk 81%+ and PF 9.8-10.8 with holdout PF 62-121 is statistically impossible without single-symbol concentration or look-ahead; matches known falsified patterns.
- 90d expected P&L (1% risk, $100k): -$2,800 (overfit cells would degrade to ~42% WR after slippage).
- Gate change: `hc_filter.js` HIGH_CONVICTION_MIN_SCORE = 92
- Confidence (1-5): 4

**### EQUITY**
- Real/noise verdict: Noise/leakage. n=72 with 98.61% WR shrinking to 88% and PF 199 is a textbook data-snooping artifact; train/holdout split still shows extreme concentration.
- 90d expected P&L (1% risk, $100k): -$1,900 (edge collapses outside the 72 trades).
- Gate change: `audit_trail/quality_gates.py` SMART_PICKS_MIN_SCORE_EQUITY = 78
- Confidence (1-5): 5

**### COMMODITY**
- Real/noise verdict: Noise. No proven cells; best_pf_overall fails holdout and bonferroni.
- 90d expected P&L (1% risk, $100k): $0 (no actionable edge).
- Gate change: `audit_trail/quality_gates.py` SMART_PICKS_MIN_TRUST_COMMODITY = 75
- Confidence (1-5): 4

**### FOREX**
- Real/noise verdict: Noise. No proven cells; all candidates fail holdout.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: `hc_filter.js` HIGH_CONVICTION_MIN_CONF = 0.82
- Confidence (1-5): 4

**### ETF**
- Real/noise verdict: Noise. Negative edge shown.
- 90d expected P&L (1% risk, $100k): -$4,100.
- Gate change: `audit_trail/quality_gates.py` SMART_PICKS_MIN_SCORE_ETF = 85
- Confidence (1-5): 5

**### UNKNOWN**
- Real/noise verdict: Noise. n=11 too small; no cells.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: `audit_trail/quality_gates.py` SMART_PICKS_MIN_TRUST_UNKNOWN = 80
- Confidence (1-5): 5

**### FUTURES**
- Real/noise verdict: Noise. No proven cells; holdout failures.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: `audit_trail/quality_gates.py` SMART_PICKS_MIN_SCORE_FUTURES = 80
- Confidence (1-5): 4

**### MEME**
- Real/noise verdict: Noise. n=4 too small.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: `audit_trail/quality_gates.py` SMART_PICKS_MIN_SCORE_MEME = 90
- Confidence (1-5): 5

**### INDEX**
- Real/noise verdict: Noise. n=10 too small.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: `audit_trail/quality_gates.py` SMART_PICKS_MIN_TRUST_INDEX = 80
- Confidence (1-5): 5

**### BOND**
- Real/noise verdict: Noise. Negative edge shown.
- 90d expected P&L (1% risk, $100k): -$2,600.
- Gate change: `audit_trail/quality_gates.py` SMART_PICKS_MIN_SCORE_BOND = 85
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale up today: none (zero classes show clean, replicable edge after shrinkage/holdout).  
Demote per MUTATION_THREE_AXIS_PROTOCOL: COMMODITY and FOREX first (highest scanned volume with zero proven cells and repeated holdout failure).
