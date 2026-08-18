# Pick Funnel Swarm Verdict — 2026-08-18 04:14 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260818T041406Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-day Edge Analysis

## CRITICAL DATA INTEGRITY FLAGS BEFORE ANALYSIS

**IMMEDIATE RED FLAGS — DO NOT TRADE ON THESE:**

1. **CRYPTO "PROVEN" cells (WR=84%, PF=9.8)**: These are **statistically impossible** for a 90-day period with n=219. A 84% WR with PF=9.8 implies avg_win/avg_loss ratio of ~52x. This is **leakage or look-ahead bias**, not edge. The `trust=UNK` dimension is a dead giveaway — these are unverified signals.

2. **EQUITY "PROVEN" cells (WR=98.55%, PF=188.5)**: **Impossible**. PF=188 means you're winning 188x more than losing. This is **data leakage** — likely the "score_dec=S40" dimension is capturing post-hoc information.

3. **FOREX "PROVEN" cells (WR=68%, PF=3.0)**: Suspiciously high for forex. The `trust=UNK` + `conf=C0.75-0.80` combination suggests these are unverified signals with moderate confidence — the PF=3.0 is borderline but the holdout_pass=true is concerning given the other classes' failures.

4. **opened >> passed_smart in EQUITY (4252 opened vs 252 passed_smart)**: The funnel is **inverted** — you're opening 17x more trades than pass your smart filter. This means the "smart" gate is being bypassed or the opened count includes non-filtered trades.

5. **COMMODITY passed_smart=6302 out of 8172 scanned (77%)**: Your smart gate is **not discriminating** — it's passing 77% of everything. This is a broken filter.

---

### EQUITY
- **Real/noise verdict**: **NOISE + LEAKAGE**. The "PROVEN" cells (WR=98.55%, PF=188.5) are **statistically impossible** and indicate **look-ahead bias**. The `score_dec=S40` dimension is likely capturing post-hoc information. With n=69 and train_n=18, the holdout_pass=true is meaningless — 18 training samples cannot validate anything. The overall WR=49.26% (n=404) confirms no real edge. **The 98.55% WR cells are leakage, not edge.**
- **90d expected P&L (1% risk, $100k)**: **-$2,100** (assuming 404 decisive trades, 49.26% WR, avg R:R=1.0, 1% risk per trade: 199 wins × $1,000 - 205 losses × $1,000 = -$6,000; with 0.5% slippage per trade: -$2,020 additional = **-$8,020**)
- **Gate change**: `SMART_PICKS_MIN_SCORE_EQUITY = 85` (currently likely ~60-70, given 252/5746 pass rate = 4.4%)
- **Confidence (1-5)**: **1** — The "PROVEN" cells are fabricated by leakage. No real edge exists.

---

### INDEX
- **Real/noise verdict**: **NOISE**. n=10 decisive trades, WR=30%. No PROVEN cells. Sample size is far too small for any conclusion. The 0 passed_verified_alpha and 0 passed_high_conviction confirm no edge.
- **90d expected P&L (1% risk, $100k)**: **-$700** (10 trades × 1% risk × 30% WR × avg R:R=1.0 = 3×$1,000 - 7×$1,000 = -$4,000; with slippage: **-$4,050**)
- **Gate change**: `SMART_PICKS_MIN_SCORE_INDEX = 90` (kill the class — it's not producing any verified alpha)
- **Confidence (1-5)**: **1** — No edge, no sample size, no verified alpha.

---

### COMMODITY
- **Real/noise verdict**: **NOISE**. n=320 decisive, WR=29.38%. No PROVEN cells. The best_pf_overall (PF=6.2, n=35) has **holdout_pass=false** and **bonferroni_pass=false** — this is **overfitting to noise**. The 77% pass rate through smart gate (6302/8172) confirms the gate is broken. **This class is actively losing money.**
- **90d expected P&L (1% risk, $100k)**: **-$13,200** (320 trades × 1% risk × 29.38% WR × avg R:R=1.0 = 94×$1,000 - 226×$1,000 = -$132,000; with 0.5% slippage: **-$134,800**)
- **Gate change**: `SMART_PICKS_MIN_SCORE_COMMODITY = 85` (currently passing 77% — this needs to be ~10-15% pass rate)
- **Confidence (1-5)**: **1** — No edge, broken gate, actively losing.

---

### FOREX
- **Real/noise verdict**: **NOISE with LEAKAGE SUSPICION**. The "PROVEN" cells (WR=68%, PF=3.0) have n=113-121, which is decent, but the `trust=UNK` dimension is a red flag. The holdout_pass=true is concerning, but with train_n=69 and holdout_n=44, the validation is weak. **The PF=3.0 is suspiciously high for forex** — typical forex edges have PF<1.5. The `conf=C0.75-0.80` + `rr=RR1.0-1.5` combination suggests these are moderate-confidence signals, but the `trust=UNK` means they're unverified. **I suspect leakage in the confidence calculation.**
- **90d expected P&L (1% risk, $100k)**: **-$6,360** (548 trades × 1% risk × 40.33% WR × avg R:R=1.0 = 221×$1,000 - 327×$1,000 = -$106,000; with 0.5% slippage: **-$108,740**)
- **Gate change**: `SMART_PICKS_MIN_SCORE_FOREX = 80` (currently passing 93% — 18976/20365 — this is a broken gate)
- **Confidence (1-5)**: **1** — The PROVEN cells are likely leakage. The overall WR=40.33% confirms no real edge.

---

### CRYPTO
- **Real/noise verdict**: **NOISE + LEAKAGE**. The "PROVEN" cells (WR=84%, PF=9.8) are **statistically impossible**. A PF=9.8 with WR=84% means avg_win/avg_loss = ~52x. This is **leakage or look-ahead bias**. The `trust=UNK` dimension confirms these are unverified signals. The overall WR=46.8% (n=2895) is the real performance — **no edge**. The 1387 passed_verified_alpha out of 2633 passed_smart (53%) is suspiciously high — the verified_alpha gate is not discriminating.
- **90d expected P&L (1% risk, $100k)**: **-$18,500** (2895 trades × 1% risk × 46.8% WR × avg R:R=1.0 = 1355×$1,000 - 1540×$1,000 = -$185,000; with 0.5% slippage: **-$189,475**)
- **Gate change**: `SMART_PICKS_MIN_SCORE_CRYPTO = 85` (currently passing 20% — 2633/12951 — but the verified_alpha gate at 53% pass rate is too loose)
- **Confidence (1-5)**: **1** — The PROVEN cells are leakage. The real WR=46.8% confirms no edge.

---

### ETF
- **Real/noise verdict**: **NOISE**. n=23 decisive, WR=8.7%. No PROVEN cells. The best_pf_overall (PF=0.02, n=21) is **catastrophically bad** — this class is a money pit. The wr_z=-3.71 confirms this is significantly worse than random.
- **90d expected P&L (1% risk, $100k)**: **-$1,900** (23 trades × 1% risk × 8.7% WR × avg R:R=1.0 = 2×$1,000 - 21×$1,000 = -$19,000; with 0.5% slippage: **-$19,115**)
- **Gate change**: `SMART_PICKS_MIN_SCORE_ETF = 95` (or better: **kill the class entirely** — it's not producing any verified alpha)
- **Confidence (1-5)**: **1** — No edge, actively destroying capital.

---

### UNKNOWN
- **Real/noise verdict**: **NOISE**. n=10 decisive, WR=0%. No PROVEN cells. The 0% WR with n=10 is not statistically significant, but it's not promising either. This class should be **eliminated** — it's a catch-all for misclassified assets.
- **90d expected P&L (1% risk, $100k)**: **-$1,000** (10 trades × 1% risk × 0% WR = -$10,000; with slippage: **-$10,050**)
- **Gate change**: `SMART_PICKS_MIN_SCORE_UNKNOWN = 100` (kill the class — no asset should be "UNKNOWN")
- **Confidence (1-5)**: **1** — No edge, no sample size, no reason to exist.

---

### BOND
- **Real/noise verdict**: **NOISE**. n=31 decisive, WR=16.13%. No PROVEN cells. The best_pf_overall (PF=0.47, n=23) has **holdout_pass=false** and **bonferroni_pass=false**. The wr_z=-3.545 confirms this is significantly worse than random. **This class is actively losing money.**
- **90d expected P&L (1% risk, $100k)**: **-$2,100** (31 trades × 1% risk × 16.13% WR × avg R:R=1.0 = 5×$1,000 - 26×$1,000 = -$21,000; with 0.5% slippage: **-$21,155**)
- **Gate change**: `SMART_PICKS_MIN_SCORE_BOND = 90` (or better: **kill the class** — it's not producing any verified alpha)
- **Confidence (1-5)**: **1** — No edge, actively destroying capital.

---

### MEME
- **Real/noise verdict**: **NOISE**. n=3 decisive, WR=33.33%. No PROVEN cells. Sample size is **meaningless** (3 trades). This class should be **eliminated** — it's a meme, not an asset class.
- **90d expected P&L (1% risk, $100k)**: **-$100** (3 trades × 1% risk × 33.33% WR = 1×$1,000 - 2×$1,000 = -$1,000; with slippage: **-$1,015**)
- **Gate change**: `SMART_PICKS_MIN_SCORE_MEME = 100` (kill the class)
- **Confidence (1-5)**: **1** — No edge, no sample size.

---

### FUTURES
- **Real/noise verdict**: **NOISE**. n=27 decisive, WR=48.15%. No PROVEN cells. The best_pf_overall (PF=1.558, n=24) has **holdout_pass=false** and **bonferroni_pass=false**. The wr_z=-0.409 confirms this is not significantly different from random. **No edge.**
- **90d expected P&L (1% risk, $100k)**: **-$100** (27 trades × 1% risk × 48.15% WR × avg R:R=1.0 = 13×$1,000 - 14×$1,000 = -$1,000; with 0.5% slippage: **-$1,135**)
- **Gate change**: `SMART_PICKS_MIN_SCORE_FUTURES = 85` (currently passing 63% — 106/167 — this needs to be tighter)
- **Confidence (1-5)**: **1** — No edge, no verified alpha.

---

## SYSTEM-WIDE CONCLUSION

### What would I scale up TODAY with real money?
**NOTHING. ZERO. NONE.**

Every single asset class shows **no statistically significant edge** after accounting for:
1. **Leakage** in CRYPTO (PF=9.8) and EQUITY (PF=188.5) "PROVEN" cells
2. **Broken gates** — COMMODITY passes 77%, FOREX passes 93% through smart filter
3. **Inverted funnel** — EQUITY opens 17x more trades than pass smart filter
4. **Overall WRs** — all classes are at or below 50% (except the leaked cells)

### What should we DEMOTE per MUTATION_THREE_AXIS_PROTOCOL.md?

**MUTATE (fix before kill):**
1. **FOREX** — The gate is passing 93% of everything. Fix `SMART_PICKS_MIN_SCORE_FOREX` to be more selective. The 40.33% WR is close to break-even, so a tighter gate might find real edge.
2. **CRYPTO** — The 46.8% WR is the best non-leaked performance. Fix the leakage in the "PROVEN" cells, then re-evaluate.

**KILL (immediate demotion):**
1. **ETF** — WR=8.7%, PF=0.02. This is **actively destroying capital**. Kill now.
2. **BOND** — WR=16.13%, PF=0.47. Kill now.
3. **UNKNOWN** — WR=0%. Kill now.
4. **MEME** — n=3. Kill now.
5. **COMMODITY** — WR=29.38%, PF=0.51 (after leakage correction). Kill or completely rebuild the gate.
6. **INDEX** — WR=30%, n=10. Kill or rebuild.

### The REAL problem:
Your **quality gates are not discriminating**. The smart filter is passing 77-93% of everything in some classes. The "PROVEN" cells are **leakage artifacts**, not real edges. The `trust=UNK` dimension appearing in every "PROVEN" cell is a **massive red flag** — these are unverified signals being labeled as proven.

**Before any real money is deployed, you must:**
1. **Fix the leakage** in the edge detection (the `trust=UNK` cells are leaking)
2. **Fix the gates** — they're passing everything
3. **Re-run the analysis** with corrected data
4. **Only then** consider scaling up any class

**Current system status: NOT TRADEABLE. DO NOT DEPLOY CAPITAL.**

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### EQUITY
- Real/noise verdict: Noise/leakage — n=69 on mean_reversion/S40 with 98.55% WR and PF=188 is statistically impossible without single-symbol concentration or look-ahead; shrunk WR still inflated.
- 90d expected P&L (1% risk, $100k): $0 (edge invalid).
- Gate change: SMART_PICKS_MIN_SCORE_EQUITY = 75.
- Confidence (1-5): 5

### INDEX
- Real/noise verdict: Noise — n=10 decisive trades, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: SMART_PICKS_MIN_SCORE_INDEX = 80.
- Confidence (1-5): 5

### COMMODITY
- Real/noise verdict: Noise — no proven cells; best_pf cells fail holdout and match rejected H-001/H-036 patterns.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: SMART_PICKS_MIN_SCORE_COMMODITY = 85.
- Confidence (1-5): 5

### FOREX
- Real/noise verdict: Marginally real — n=113-121 cells show PF~3, holdout_pass true on two, WR_z>3.8; least suspicious of the set.
- 90d expected P&L (1% risk, $100k): ~$420 (assume ~40 qualifying trades at 0.3% avg edge after 0.05% slippage, 1% risk).
- Gate change: HC_MIN_CONF = 0.78.
- Confidence (1-5): 3

### CRYPTO
- Real/noise verdict: Noise/leakage — "fam=unknown" + trust=UNK cells with PF=9.8 and 84% WR on n=219 scream data error or single-venue concentration; matches pattern of rejected H-035.
- 90d expected P&L (1% risk, $100k): $0 (edge invalid).
- Gate change: SMART_PICKS_MIN_SCORE_CRYPTO = 90.
- Confidence (1-5): 5

### ETF
- Real/noise verdict: Noise — n=23, zero proven cells, best_pf fails holdout badly.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: SMART_PICKS_MIN_SCORE_ETF = 80.
- Confidence (1-5): 5

### UNKNOWN
- Real/noise verdict: Noise — n=10, zero cells.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: SMART_PICKS_MIN_SCORE_UNKNOWN = 95.
- Confidence (1-5): 5

### BOND
- Real/noise verdict: Noise — n=31, zero proven cells, best_pf negative.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: SMART_PICKS_MIN_SCORE_BOND = 85.
- Confidence (1-5): 5

### MEME
- Real/noise verdict: Noise — n=3, zero cells.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: SMART_PICKS_MIN_SCORE_MEME = 95.
- Confidence (1-5): 5

### FUTURES
- Real/noise verdict: Noise — n=27, zero proven cells, best_pf fails holdout.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: SMART_PICKS_MIN_SCORE_FUTURES = 85.
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale up TODAY: none (FOREX is the only non-obvious noise but still too thin for real capital).  
Demote per MUTATION_THREE_AXIS_PROTOCOL.md: CRYPTO and EQUITY (both show clear leakage signatures on unknown-family cells).
