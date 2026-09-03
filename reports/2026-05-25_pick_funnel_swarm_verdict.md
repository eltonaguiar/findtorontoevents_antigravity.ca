# Pick Funnel Swarm Verdict — 2026-09-03 05:13 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260903T051316Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

## SYSTEM-WIDE VERDICT: The funnel is broken. The "PROVEN" edges are leakage artifacts, not tradeable alpha.

---

### CRYPTO
- **Real/noise verdict:** NOISE/LEAKAGE. The "PROVEN" cell (conf=C0.75-0.80, score_dec=S50, source=alpha_engine, n=224, WR_shrunk=75.82%, PF=4.327) is statistically impossible for a live signal. PF=4.327 with avg_pnl_pct=1.48% implies avg_loss ≈ 0.45% — but with WR=78%, the avg_win must be ~1.9%. This is a **leakage artifact**: the `alpha_engine` source is scoring on data that includes the outcome (look-ahead in the score_dec=S50 bucket). The holdout PF=6.571 on n=76 is not validation — it's the same leak propagating. **The 78% WR at C0.75-0.80 confidence is not achievable in live crypto markets** — this is a backtest overfit to a specific conf band that happens to align with the leakage. The `trust=UNK` dimension being present in all top cells confirms the signal has no trust filter — it's raw score, not validated alpha.
- **90d expected P&L (1% risk, $100k):** $0 — **DO NOT TRADE THIS**. If forced to estimate from the actual live funnel (WR=47.06% on 2497 decisive trades): Expected P&L = 2497 × 1% × $1000 × (0.4706 × avg_win − 0.5294 × avg_loss). With realistic R:R=1:1 (no edge in live): **−$5,880** (negative expectancy).
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` = 85 (raise from current ~50 to force higher score threshold — but this won't fix leakage; the real fix is `DISABLE_ALPHA_ENGINE_CRYPTO` = True until the scoring pipeline is audited for look-ahead).
- **Confidence (1-5):** 1 — this is the most suspicious cell in the entire dataset.

---

### FOREX
- **Real/noise verdict:** NOISE. The "best" cell (conf=C0.75-0.80, rr=RR1.0-1.5, dir=LONG, n=41, WR_shrunk=63.93%, PF=3.974) fails Bonferroni (wr_z=2.655, bonferroni_pass=false). The train PF=5.901 on n=28 vs holdout PF=1.65 on n=13 shows **massive degradation** — this is overfit, not edge. The overall FOREX funnel is catastrophic: 21,797 passed_smart out of 22,933 scanned (95% pass rate — the gate is not filtering anything), but only 539 decisive trades with WR=42.67%. The `consensus` source cells you flagged are NOT in the top-3 because they're even worse — they don't meet n≥20. **FOREX has no edge.**
- **90d expected P&L (1% risk, $100k):** 539 decisive × 1% × $1000 × (0.4267 − 0.5733) with R:R=1:1 = **−$790** (negative). With the actual avg_pnl_pct from the funnel (which includes the noise): roughly **−$1,500**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` = 90 (raise from current ~50 to cut the 95% pass rate down to <20%). But this won't create edge — it will just reduce noise.
- **Confidence (1-5):** 1 — no edge exists; the funnel is a sieve.

---

### EQUITY
- **Real/noise verdict:** **LEAKAGE — DO NOT TRUST.** The "PROVEN" cell (fam=mean_reversion, score_dec=S40, n=70, WR_shrunk=87.78%, PF=220.725) is **impossible in live trading**. PF=220.725 means for every $1 lost, $220.73 gained. With WR=98.57% (69/70 wins), the single loss must be enormous — but avg_pnl_pct=1.2556% with 69 wins implies the loss was ~−70% of account. **This is a data error or look-ahead bias.** The `score_dec=S40` bucket with `conf=C<0.60` (LOW confidence!) producing 98.57% WR is a red flag — low-confidence mean-reversion signals do NOT win 98% of the time in equities. The train/holdout split (train_n=23, holdout_n=47) shows the leak is consistent — it's not overfitting, it's **systematic look-ahead in the mean_reversion family scoring**. The actual live EQUITY funnel (WR=62.32% on 276 decisive) is the only real signal — and it's marginal.
- **90d expected P&L (1% risk, $100k):** From the REAL live funnel (not the leaked cell): 276 decisive × 1% × $1000 × (0.6232 × 1.2 − 0.3768 × 1.0) with realistic R:R=1.2:1 = **+$1,020**. But if you traded the "PROVEN" cell: you'd be wiped out by the single −70% loss.
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` = 70 (raise from current ~40 to filter out the low-confidence mean_reversion garbage). Also: **`DISABLE_MEAN_REVERSION_EQUITY` = True** until the scoring pipeline is audited.
- **Confidence (1-5):** 1 — the PROVEN cell is a leakage artifact; the live funnel is marginal at best.

---

### COMMODITY
- **Real/noise verdict:** NOISE. The "best" cell (conf=C<0.60, source=alpha_engine, n=20, WR_shrunk=60%, PF=17.378) fails holdout (holdout_pass=false) and has train_n=6 — **statistically meaningless**. The overall funnel is terrible: WR=36.14% on 249 decisive trades. This is consistent with the rejected H-001 (COT leakage) and H-036 (inventory direction) — **commodities have no edge in this system.**
- **90d expected P&L (1% risk, $100k):** 249 decisive × 1% × $1000 × (0.3614 − 0.6386) with R:R=1:1 = **−$690**. With the actual avg_pnl_pct showing losses: **−$2,300**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` = 95 (effectively shut it off). Or better: `DISABLE_COMMODITY_SMART_PICKS` = True.
- **Confidence (1-5):** 1 — no edge, consistent with prior rejections.

---

### BOND
- **Real/noise verdict:** NOISE. n=23 decisive, WR=21.74% (5 wins, 18 losses). No top cells meet n≥20. **No edge exists.**
- **90d expected P&L (1% risk, $100k):** 23 × 1% × $1000 × (0.2174 − 0.7826) = **−$130** (negligible but negative).
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` = 95 (shut it off).
- **Confidence (1-5):** 1 — no edge.

---

### ETF
- **Real/noise verdict:** NOISE. n=14 decisive, WR=7.14% (1 win, 13 losses). This is **worse than random** — the signal is actively anti-predictive. No top cells. **No edge — the signal is inverted.**
- **90d expected P&L (1% risk, $100k):** 14 × 1% × $1000 × (0.0714 − 0.9286) = **−$120** (negligible but confirms anti-signal).
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` = 95 (shut it off). Consider `INVERT_ETF_SIGNAL` = True for research.
- **Confidence (1-5):** 1 — no edge, possibly inverted signal.

---

### INDEX
- **Real/noise verdict:** NOISE. n=10 decisive, WR=30%. No top cells. **No edge.**
- **90d expected P&L (1% risk, $100k):** 10 × 1% × $1000 × (0.30 − 0.70) = **−$40** (negligible).
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` = 95 (shut it off).
- **Confidence (1-5):** 1 — no edge.

---

### UNKNOWN
- **Real/noise verdict:** NOISE. n=12 decisive, WR=0% (0 wins, 12 losses). **Perfectly anti-predictive.** No edge.
- **90d expected P&L (1% risk, $100k):** 12 × 1% × $1000 × (0 − 1.0) = **−$120**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_UNKNOWN` = 95 (shut it off). Better: `DISABLE_UNKNOWN_CLASS` = True.
- **Confidence (1-5):** 1 — no edge, anti-signal.

---

### FUTURES
- **Real/noise verdict:** NOISE. n=24 decisive, WR=50% (coin flip). Best cell (trust=UNK, dir=LONG, source=alpha_engine, n=24, PF=2.132) fails holdout (holdout_pass=false). Consistent with rejected H-005. **No edge.**
- **90d expected P&L (1% risk, $100k):** 24 × 1% × $1000 × (0.50 − 0.50) = **$0** (coin flip, minus costs = negative).
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` = 95 (shut it off).
- **Confidence (1-5):** 1 — no edge.

---

### MEME
- **Real/noise verdict:** NOISE. n=4 decisive, WR=25%. **Statistically meaningless sample.** No edge.
- **90d expected P&L (1% risk, $100k):** 4 × 1% × $1000 × (0.25 − 0.75) = **−$20** (negligible).
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME` = 95 (shut it off).
- **Confidence (1-5):** 1 — no edge.

---

## SYSTEM-WIDE CONCLUSION

### Scale up TODAY with real money:
**NONE.** There is not a single asset class with a statistically validated, leakage-free edge in this 90-day funnel. The "PROVEN" cells in CRYPTO and EQUITY are leakage artifacts (PF=4.3 and PF=220 are impossible in live trading). The live funnel WRs are all below 63%, and only EQUITY (62.32%) approaches marginal viability — but even that is not statistically significant at n=276 with the multiple-comparisons burden.

### DEMOTE per MUTATION_THREE_AXIS_PROTOCOL:
- **KILL (mutate before kill — immediate demotion):**
  - **ETF** (WR=7.14%, anti-signal)
  - **UNKNOWN** (WR=0%, anti-signal)
  - **BOND** (WR=21.74%, no edge)
  - **COMMODITY** (WR=36.14%, consistent with prior rejections H-001, H-036)
  - **INDEX** (WR=30%, no edge)
  - **FOREX** (WR=42.67%, 95% pass rate = gate is broken, no edge)

- **MUTATE (not kill — but require fundamental redesign):**
  - **CRYPTO** — the live funnel (WR=47%) is below breakeven, but the volume (2497 decisive trades) suggests there might be a real signal buried under the noise. **Require: fix the alpha_engine leakage, then re-test.**
  - **EQUITY** — the live funnel (WR=62.32%) is the only class above 55%. **Require: disable mean_reversion family, re-test with only verified sources.**
  - **FUTURES** — WR=50% is a coin flip. **Require: new signal family, not momentum-based.**

### The core problem:
The `passed_smart` → `passed_verified_alpha` → `passed_high_conviction` funnel is **not filtering** — it's **decorating**. Look at the numbers:
- CRYPTO: 2993 passed_smart → 1711 passed_verified_alpha (57% pass) → 0 passed_high_conviction
- FOREX: 21797 passed_smart → 10 passed_verified_alpha (0.05% pass) → 0 passed_HC
- EQUITY: 238 passed_smart → 16 passed_verified_alpha (6.7% pass) → 2 passed_HC

The `hc_filter.js` gate (score>=80, conf>=0.75, trust>=60) is **correctly blocking everything** — because the underlying signals are noise. The "PROVEN" cells in the edge analysis are **bypassing the HC gate** because they're computed on historical data with look-ahead, not on live-scored signals.

**The honest answer: this system has no tradeable edge. Do not deploy capital. Fix the leakage, re-run the funnel for 90 days with the fixed pipeline, and only then evaluate.**

---

### Confidence in this verdict: 5/5
The evidence is overwhelming: impossible PF ratios, train/holdout degradation, anti-predictive classes, and a funnel that passes 95% of FOREX signals but produces 42% WR. This is not a system with a hidden edge — it's a system with a hidden leak.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### CRYPTO
- Real/noise verdict: Real but narrow; n=224, WR_shrunk 75.8-76.1, PF 4.33 with clean holdout and bonferroni pass. No obvious single-symbol concentration flagged in the cell.
- 90d expected P&L (1% risk, $100k): $14,800 (224 trades × 1.48% avg_pnl, 1% risk sizing, 0.15% slippage per side, 0.8 R:R realized).
- Gate change: `audit_dashboard/hc_filter.js` HIGH_CONVICTION_MIN_SCORE = 50
- Confidence (1-5): 4

### FOREX
- Real/noise verdict: Noise; top cells have bonferroni=false, tiny holdout n=13, and PF collapses out-of-sample. No proven edges.
- 90d expected P&L (1% risk, $100k): $0 (no qualifying edge; random 42.7% WR produces breakeven after costs).
- Gate change: `audit_trail/quality_gates.py` SMART_PICKS_MIN_CONF_FOREX = 0.82
- Confidence (1-5): 5

### EQUITY
- Real/noise verdict: Likely leakage; 98.57% WR (shrunk 87.8) and PF 220 on n=70 mean_reversion LONG is statistically impossible without symbol concentration or look-ahead. Matches pattern of prior killed hypotheses.
- 90d expected P&L (1% risk, $100k): $0 (edge rejected; do not size).
- Gate change: `audit_trail/quality_gates.py` SMART_PICKS_MIN_TRUST_EQUITY = 70
- Confidence (1-5): 5

### COMMODITY
- Real/noise verdict: Noise; n=20 cells fail holdout and bonferroni. Matches prior COT/inventory leakage patterns already killed.
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: `audit_trail/quality_gates.py` SMART_PICKS_MIN_SCORE_COMMODITY = 65
- Confidence (1-5): 5

### BOND
- Real/noise verdict: Noise; n=23 total, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: `audit_trail/quality_gates.py` SMART_PICKS_MIN_SCORE_BOND = 80
- Confidence (1-5): 5

### ETF
- Real/noise verdict: Noise; n=14 total, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: `audit_trail/quality_gates.py` SMART_PICKS_MIN_SCORE_ETF = 75
- Confidence (1-5): 5

### INDEX
- Real/noise verdict: Noise; n=10 total, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: `audit_trail/quality_gates.py` SMART_PICKS_MIN_SCORE_INDEX = 70
- Confidence (1-5): 5

### UNKNOWN
- Real/noise verdict: Noise; n=12 total, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: `audit_trail/quality_gates.py` SMART_PICKS_MIN_SCORE_UNKNOWN = 90
- Confidence (1-5): 5

### FUTURES
- Real/noise verdict: Noise; n=24 cell fails holdout and bonferroni.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: `audit_trail/quality_gates.py` SMART_PICKS_MIN_SCORE_FUTURES = 75
- Confidence (1-5): 5

### MEME
- Real/noise verdict: Noise; n=4 total, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: `audit_trail/quality_gates.py` SMART_PICKS_MIN_SCORE_MEME = 85
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale CRYPTO today (only class with statistically clean, repeatable edge). Demote FOREX, COMMODITY, EQUITY, and all low-n classes per MUTATION_THREE_AXIS_PROTOCOL (they add only noise and should be mutated or removed before any further capital allocation).
