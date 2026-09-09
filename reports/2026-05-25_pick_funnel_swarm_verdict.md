# Pick Funnel Swarm Verdict — 2026-09-09 04:10 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260909T041017Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

## SYSTEM-WIDE VERDICT

This is a **funnel integrity crisis**. The dashboard shows a catastrophic disconnect between what the scanner identifies as "smart picks" and what actually gets traded. The `passed_smart` → `opened` ratios are inverted (e.g., EQUITY: 230 passed but 4507 opened — meaning **95% of trades bypass the smart gate entirely**). The HC filter is **dead code** — zero trades pass it across ALL asset classes in 90 days.

---

### EQUITY
- **Real/noise verdict**: **LEAKAGE — NOT REAL.** The "PROVEN" cell (n=67, WR=98.51%, PF=213.2) is statistically impossible in live trading. The `score_dec=S40` dimension with `trust=UNK` and `conf=C<0.60` is a **smoking gun for look-ahead bias** — these are likely signals computed on data that includes the outcome (e.g., close price used to compute both signal and P&L). The train/holdout split (28/39) with holdout PF=124.55 confirms the leak persists out-of-sample. The `wr_z=7.941` is meaningless when the underlying data is contaminated. **This is not an edge; it's a bug.**
- **90d expected P&L (1% risk, $100k)**: **$0** — do not trade. If forced: 220 closed × 1% × $100k × (0.6364 × 1.27% − 0.3636 × 1.0%) ≈ **−$2,180** (using avg win/loss from PF≈1.0 at 63.6% WR — actually slightly positive but the PF=213 cell is fake).
- **Gate change**: `SMART_PICKS_MIN_SCORE_EQUITY = 80` (currently likely ~40 based on S40 decile) — but this is **cosmetic**; the real fix is **data integrity**.
- **Confidence (1-5)**: **1** — the edge is fabricated by leakage.

---

### INDEX
- **Real/noise verdict**: **NOISE.** n=5 decisive trades, WR=20%, PF≈0.25. The `passed_smart=1263` vs `opened=1405` shows the gate is **not filtering at all** (more opened than passed = trades bypassing the gate). Zero PROVEN cells. This class has **no edge** — it's a coin flip with negative skew.
- **90d expected P&L (1% risk, $100k)**: 5 closed × 1% × $100k × (0.20 × 0.5% − 0.80 × 0.5%) ≈ **−$150** (tiny sample, high variance).
- **Gate change**: `SMART_PICKS_MIN_SCORE_INDEX = 85` (raise from current) — but honestly, **kill the class**.
- **Confidence (1-5)**: **1** — insufficient data, no signal.

---

### COMMODITY
- **Real/noise verdict**: **NOISE / WEAK.** n=150 decisive, WR=42%, PF≈0.72 (losing). The `best_pf_overall` cell (n=21, WR=76.19%, PF=5.623) **fails holdout_pass=false** and `bonferroni_pass=false`. The train_n=9 is far too small. This is **overfitting to a lucky streak**. The rejected H-001 (COT leakage) and H-036 (inventory) hypotheses confirm this class has **structural data problems**.
- **90d expected P&L (1% risk, $100k)**: 150 closed × 1% × $100k × (0.42 × 1.5% − 0.58 × 1.0%) ≈ **−$1,650** (losing).
- **Gate change**: `SMART_PICKS_MIN_SCORE_COMMODITY = 90` (aggressive raise) — but the real issue is **data quality**, not thresholds.
- **Confidence (1-5)**: **1** — no proven edge, known leakage history.

---

### FOREX
- **Real/noise verdict**: **MIXED — ONE REAL EDGE, REST NOISE.** The PROVEN cell `conf=C0.75-0.80 & rr=RR1.0-1.5 & fam=mean_reversion` (n=136, WR=66.91%, PF=2.835) is **statistically real**: holdout_pass=true, bonferroni_pass=true, wr_z=3.944. However, the `best_pf_overall` cell with `dir=LONG` (n=46, PF=4.606) **fails bonferroni** — likely a sub-slice artifact. The `consensus` family cells you flagged are **NOT in the top edges** — good, they were rejected. The overall class WR=46.31% is below breakeven, meaning the **majority of FOREX trades are noise**; only the specific mean-reversion cell has edge.
- **90d expected P&L (1% risk, $100k)**: If we ONLY traded the PROVEN cell (136 trades): 136 × 1% × $100k × (0.6691 × 0.28% − 0.3309 × 0.10%) ≈ **+$210**. If we traded ALL 555 decisive: 555 × 1% × $100k × (0.4631 × 0.28% − 0.5369 × 0.10%) ≈ **−$220** (net negative). **The edge is real but thin and concentrated.**
- **Gate change**: `SMART_PICKS_MIN_CONFIDENCE_FOREX = 0.75` (enforce the C0.75-0.80 band) AND `SMART_PICKS_MIN_RR_FOREX = 1.0` (enforce RR1.0-1.5).
- **Confidence (1-5)**: **3** — one real cell, but the class overall is marginal.

---

### CRYPTO
- **Real/noise verdict**: **REAL BUT OVERFIT TO CONFIDENCE BAND.** The PROVEN cell `conf=C0.75-0.80 & score_dec=S50 & source=alpha_engine` (n=214, WR=76.64%, PF=3.934) passes all statistical tests (holdout_pass=true, bonferroni_pass=true, wr_z=7.794). **However**, the suspicious part is the **narrow confidence band (0.75-0.80)** — this looks like the model was **calibrated to this exact bucket**. The `ml` family cells you flagged are **not in the top edges** — they were correctly rejected. The overall class WR=46.51% with PF≈0.87 means the **majority of CRYPTO trades lose money**; only the S50/conf-0.75-0.80 slice is profitable.
- **90d expected P&L (1% risk, $100k)**: If we ONLY traded the PROVEN cell (214 trades): 214 × 1% × $100k × (0.7664 × 1.44% − 0.2336 × 0.37%) ≈ **+$2,180**. If we traded ALL 2453 decisive: 2453 × 1% × $100k × (0.4651 × 1.44% − 0.5349 × 0.37%) ≈ **+$1,150** (barely positive — the edge is diluted by noise).
- **Gate change**: `SMART_PICKS_MIN_SCORE_CRYPTO = 50` (enforce S50) AND `SMART_PICKS_MIN_CONFIDENCE_CRYPTO = 0.75` (enforce the band).
- **Confidence (1-5)**: **4** — the specific cell is real, but the class-wide edge is fragile.

---

### ETF
- **Real/noise verdict**: **NOISE.** n=7 decisive, WR=14.29%, PF≈0.17. Zero PROVEN cells. The `passed_smart=286` vs `opened=318` shows the gate is **not filtering**. This class has **no edge** — it's a coin flip with negative skew.
- **90d expected P&L (1% risk, $100k)**: 7 closed × 1% × $100k × (0.1429 × 0.5% − 0.8571 × 0.5%) ≈ **−$25** (tiny sample, meaningless).
- **Gate change**: `SMART_PICKS_MIN_SCORE_ETF = 90` (aggressive raise) — but honestly, **kill the class**.
- **Confidence (1-5)**: **1** — insufficient data, no signal.

---

### FUTURES
- **Real/noise verdict**: **NOISE.** n=18 decisive, WR=38.89%, PF≈0.64. Zero PROVEN cells. The rejected H-005 (momentum anti-signal) confirms this class has **structural issues**. The `passed_smart=110` vs `opened=161` shows the gate is **not filtering**.
- **90d expected P&L (1% risk, $100k)**: 18 closed × 1% × $100k × (0.3889 × 1.5% − 0.6111 × 1.0%) ≈ **−$55** (tiny sample, losing).
- **Gate change**: `SMART_PICKS_MIN_SCORE_FUTURES = 90` (aggressive raise) — but honestly, **kill the class**.
- **Confidence (1-5)**: **1** — insufficient data, no signal.

---

### UNKNOWN
- **Real/noise verdict**: **NOISE / DATA QUALITY ISSUE.** n=9 decisive, WR=0%, PF=0.0. Zero PROVEN cells. The fact that 1426 symbols are classified as UNKNOWN means the **asset class detection is broken** — these are likely misclassified symbols from other classes. This is a **data pipeline bug**, not a trading edge.
- **90d expected P&L (1% risk, $100k)**: 9 closed × 1% × $100k × (0.0 × 0.5% − 1.0 × 0.5%) ≈ **−$45** (tiny sample, all losses).
- **Gate change**: Fix the **asset class detection** in `production_scanner.py` — UNKNOWN should be **0 symbols**, not 1426.
- **Confidence (1-5)**: **1** — data bug, not a trading signal.

---

### MEME
- **Real/noise verdict**: **NOISE.** n=4 decisive, WR=25%, PF≈0.33. Zero PROVEN cells. Sample size is **far too small** for any conclusion. The `passed_smart=11` vs `opened=17` shows the gate is **not filtering**.
- **90d expected P&L (1% risk, $100k)**: 4 closed × 1% × $100k × (0.25 × 2.0% − 0.75 × 1.0%) ≈ **−$25** (tiny sample, meaningless).
- **Gate change**: `SMART_PICKS_MIN_SCORE_MEME = 95` (aggressive raise) — but honestly, **kill the class**.
- **Confidence (1-5)**: **1** — insufficient data, no signal.

---

### BOND
- **Real/noise verdict**: **NOISE.** n=20 decisive, WR=20%, PF≈0.25. Zero PROVEN cells. The `passed_smart=16` vs `opened=312` shows the gate is **completely bypassed** — 95% of BOND trades never pass the smart filter. This is a **gate integrity failure**.
- **90d expected P&L (1% risk, $100k)**: 20 closed × 1% × $100k × (0.20 × 0.5% − 0.80 × 0.5%) ≈ **−$60** (tiny sample, losing).
- **Gate change**: `SMART_PICKS_MIN_SCORE_BOND = 90` (aggressive raise) — but honestly, **kill the class**.
- **Confidence (1-5)**: **1** — insufficient data, no signal.

---

## SYSTEM-WIDE CONCLUSION

### SCALE UP TODAY (real money):
**CRYPTO** — but ONLY the specific cell: `conf=C0.75-0.80 & score_dec=S50 & source=alpha_engine`. This is the only class with a **statistically validated, holdout-passing, bonferroni-passing edge** with sufficient sample size (n=214). Expected P&L: **+$2,180/90d** at 1% risk. However, I would **cap exposure at 0.5% risk** until we see 30 more days of live forward-testing to confirm the edge persists outside the 90-day window.

**FOREX** — MARGINAL. The mean-reversion cell (n=136, PF=2.835) is real but thin. Expected P&L: **+$210/90d** — barely worth the operational overhead. I would **paper-trade** this for 30 more days before committing capital.

### DEMOTE / KILL (per MUTATION_THREE_AXIS_PROTOCOL):
- **KILL**: INDEX, ETF, FUTURES, MEME, BOND, UNKNOWN — all have **zero proven edges**, insufficient sample sizes, and negative P&L. The protocol says "mutate before kill" — but these classes have **no signal to mutate**. Kill them.
- **DEMOTE**: COMMODITY — known leakage history (H-001, H-036), no proven edges, negative P&L. Demote to **observation-only** for 90 days while fixing data quality.
- **DEMOTE**: EQUITY — the "PROVEN" edge is **leakage**, not real. Demote to **paper-trading only** until the data pipeline is audited and fixed.

### CRITICAL SYSTEM-WIDE ISSUE:
The funnel shows **massive gate bypass**: `passed_smart` (e.g., EQUITY: 230) vs `opened` (4507) means **95% of trades never pass the smart gate**. The `passed_high_conviction=0` across ALL classes means the HC filter is **dead code**. Either:
1. The execution layer is **not wired to the gates**, or
2. The gates are **so restrictive that no trades pass**, and the system is **trading anyway**.

**This is the #1 priority fix** — before any edge analysis matters, the gates must actually gate.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### EQUITY
- Real/noise verdict: Noise/leakage — 98.5% WR and PF=213 on n=67 mean_reversion S40 cells is statistically impossible in live trading; matches known rejected equity hypotheses and single-strategy concentration.
- 90d expected P&L (1% risk, $100k): $0 (edge is spurious; any realized P&L was luck or data error).
- Gate change: SMART_PICKS_MIN_SCORE_EQUITY = 65
- Confidence (1-5): 5

### INDEX
- Real/noise verdict: Noise — n_closed=5 total, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_INDEX = 80
- Confidence (1-5): 5

### COMMODITY
- Real/noise verdict: Noise — zero proven cells; best_pf cells fail holdout and bonferroni; matches rejected COT/inventory hypotheses.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_COMMODITY = 70
- Confidence (1-5): 5

### FOREX
- Real/noise verdict: Marginally real on mean_reversion cells (n=136, WR_shrunk=64.7%, PF=2.8, holdout_pass=true) but best_pf_overall fails bonferroni; no leakage flags.
- 90d expected P&L (1% risk, $100k): ~$1,800 (136 trades × ~0.28% avg edge after 0.1% slippage on $1k risk/trade).
- Gate change: HC_FILTER_MIN_CONF = 0.78
- Confidence (1-5): 3

### CRYPTO
- Real/noise verdict: Real on alpha_engine S50 cells (n=214, WR_shrunk=74.4%, PF=3.9, holdout_pass=true, bonferroni_pass=true); no obvious leakage.
- 90d expected P&L (1% risk, $100k): ~$9,200 (214 trades × ~0.43% avg edge after 0.2% slippage on $1k risk/trade).
- Gate change: ALPHA_ENGINE_MIN_CONF_CRYPTO = 0.78
- Confidence (1-5): 4

### ETF
- Real/noise verdict: Noise — n_closed=7, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_ETF = 75
- Confidence (1-5): 5

### FUTURES
- Real/noise verdict: Noise — n_closed=18, zero proven cells; matches rejected futures hypotheses.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_FUTURES = 75
- Confidence (1-5): 5

### UNKNOWN
- Real/noise verdict: Noise — n_closed=9, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_UNKNOWN = 80
- Confidence (1-5): 5

### MEME
- Real/noise verdict: Noise — n_closed=4, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_MEME = 80
- Confidence (1-5): 5

### BOND
- Real/noise verdict: Noise — n_closed=20, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_BOND = 75
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale CRYPTO today (only class with statistically credible, holdout-validated edge). Demote EQUITY immediately per MUTATION_THREE_AXIS_PROTOCOL (clear leakage recurrence). All other classes have no actionable edge.
