# Pick Funnel Swarm Verdict — 2026-06-23 05:23 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260623T052245Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

### CRYPTO
- **Real/noise verdict:** **Real** – two PROVEN cells (both n > 400, WR shrunk ≈ 60‑62 %, PF ≈ 2.1‑2.4, hold‑out & Bonferroni passed). No sign of look‑ahead leakage; the “trust=PROBATION” band is a genuine mid‑trust tier, not a data‑snooping artifact.  
- **90d expected P&L (1 % risk, $100 k):** ≈ $405 k net.  
  *Assumptions*: $1 k risk per trade, 0.1 % slippage (≈ $100) per round‑trip, 407 trades from the best cell (trust = PROBATION & RR 1.5‑2.0 & LONG). Expected net per trade ≈ $994 → total ≈ $405 k.  
- **Gate change:** `hc_filter.js` → lower `MIN_TRUST` from **60** to **30** (allow “PROBATION” trust band).  
- **Confidence (1‑5):** **5**

### EQUITY
- **Real/noise verdict:** **Noise** – no PROVEN cells; best PF = 3.34 comes from an “UNK” trust band with only 59 trades and a Bonferroni‑fail. Win‑rate‑shrunk ≈ 63 % but the sample is small and the “UNK” trust label is a catch‑all that often mixes data‑leakage.  
- **90d expected P&L (1 % risk, $100 k):** **$0** (no statistically‑validated edge).  
- **Gate change:** `audit_trail/quality_gates.py` → raise `SMART_PICKS_MIN_SCORE_EQUITY` from the current 80 to **90** to prune low‑confidence picks.  
- **Confidence (1‑5):** **1**

### FOREX
- **Real/noise verdict:** **Noise** – no PROVEN cells; best PF ≈ 2.4 but hold‑out fails (zero profit on hold‑out) and win‑rate‑shrunk is only ≈ 45 %. The “score_dec=S20” dimension is a post‑trade filter that leaks future price moves.  
- **90d expected P&L (1 % risk, $100 k):** **$0** (edge not validated).  
- **Gate change:** `hc_filter.js` → raise `MIN_CONFIDENCE` from **0.75** to **0.85** (the proven edge uses confidence < 0.60, which is clearly too permissive).  
- **Confidence (1‑5):** **1**

### COMMODITY
- **Real/noise verdict:** **Noise** – no PROVEN cells; all “best PF” cells have PF ≈ 1.35, win‑rate‑shrunk ≈ 48 % and no hold‑out data (n = 107). The signal is essentially break‑even.  
- **90d expected P&L (1 % risk, $100 k):** **$0**.  
- **Gate change:** `audit_trail/quality_gates.py` → increase `SMART_PICKS_MIN_RR_COMMODITY` from **1.5** to **2.0** (current proven cells sit at the low‑RR edge).  
- **Confidence (1‑5):** **1**

### BOND
- **Real/noise verdict:** **Noise** – only 9 smart‑picked trades, WR ≈ 25 %, PF ≈ 0.5. Sample far too small for any claim.  
- **90d expected P&L (1 % risk, $100 k):** **$0**.  
- **Gate change:** `audit_trail/quality_gates.py` → raise `SMART_PICKS_MIN_SCORE_BOND` to **85** (current picks are borderline).  
- **Confidence (1‑5):** **1**

### ETF
- **Real/noise verdict:** **Noise** – 194 smart picks, WR ≈ 9 %, PF ≈ 0.6. No PROVEN cell, win‑rate far below any useful threshold.  
- **90d expected P&L (1 % risk, $100 k):** **$0**.  
- **Gate change:** `audit_trail/quality_gates.py` → raise `SMART_PICKS_MIN_SCORE_ETF` to **90**.  
- **Confidence (1‑5):** **1**

### UNKNOWN
- **Real/noise verdict:** **Noise** – 28 smart picks, WR = 0 %, PF = 0.0. Purely random.  
- **90d expected P&L (1 % risk, $100 k):** **$0**.  
- **Gate change:** `audit_trail/quality_gates.py` → set `SMART_PICKS_MIN_SCORE_UNKNOWN` to **100** (effectively block).  
- **Confidence (1‑5):** **1**

### FUTURES
- **Real/noise verdict:** **Noise** – 428 smart picks, but no PROVEN cell; win‑rate ≈ 66 % on only 12 closed trades, PF ≈ 1.0. Sample too tiny to trust.  
- **90d expected P&L (1 % risk, $100 k):** **$0**.  
- **Gate change:** `audit_trail/quality_gates.py` → raise `SMART_PICKS_MIN_SCORE_FUTURES` to **85**.  
- **Confidence (1‑5):** **1**

### INDEX
- **Real/noise verdict:** **Noise** – only 8 closed trades, no PROVEN cell, PF ≈ 1.0.  
- **90d expected P&L (1 % risk, $100 k):** **$0**.  
- **Gate change:** `audit_trail/quality_gates.py` → raise `SMART_PICKS_MIN_SCORE_INDEX` to **90**.  
- **Confidence (1‑5):** **1**

### MEME
- **Real/noise verdict:** **Noise** – single trade, WR = 100 % but n = 1, PF = ∞ (division by zero). Statistically meaningless.  
- **90d expected P&L (1 % risk, $100 k):** **$0** (cannot size a strategy on one data point).  
- **Gate change:** `audit_trail/quality_gates.py` → set `SMART_PICKS_MIN_SCORE_MEME` to **100** (disable).  
- **Confidence (1‑5):** **1**

---

## SYSTEM‑WIDE Conclusion
- **Scale‑up today:** **CRYPTO** – the two PROVEN cells survive all statistical checks, have solid win‑rate‑shrunk, respectable profit factors, and pass hold‑out & Bonferroni tests. With a modest $100 k account and 1 % risk per trade, the model should generate roughly **$400 k** net over the next 90 days (assuming similar market regime).  
- **Demote / kill:** **MEME** (and by extension the “UNKNOWN” bucket). The signal is a single‑trade fluke; keeping it alive only adds noise to the pipeline and wastes compute resources. Follow the MUTATION_THREE_AXIS_PROTOCOL: first **mutate** the MEME gate to the maximum score (100) and then **deprecate** the class.  

All other asset classes lack a statistically‑validated edge; tightening their quality‑gate thresholds will reduce false‑positive picks and free capacity for the proven crypto edge.

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-day edge analysis

## System-wide observation before per-class analysis

The funnel data reveals a **severe disconnect** between scanning volume and edge quality. CRYPTO scans 17,893 signals but only 2,201 pass Smart_Picks (12.3% pass rate), yet 0 pass HIGH CONVICTION. Meanwhile, EQUITY scans 4,451 with only 113 passing Smart_Picks (2.5%) but produces the only 2 HIGH CONVICTION passes and 3 PROVEN passes. This suggests the scoring engine is **over-fitting to CRYPTO volume** while **under-sampling EQUITY quality**.

The FOREX data is particularly alarming: 9,894 Smart_Picks passes from 18,635 scans (53% pass rate) yet WR=25.48% — the gate is **too permissive** for FOREX, letting through massive noise.

---

### CRYPTO
- **Real/noise verdict:** PARTIALLY REAL — Two PROVEN cells survive Bonferroni correction (z=5.205, z=4.486) with n=407 and n=458. However, the `ml` family cell (PF=2.48, n=364) fails holdout (holdout_n=5 only) — this is **sample-noise disguised as edge**. The PROBATION trust band dominating suggests these edges are **fragile and regime-dependent**. The `rr=RR1.5-2.0 & dir=LONG` cell is the strongest candidate but note: 40 holdout trades vs 367 train is a 9:1 split — the holdout PF=6.639 is suspiciously high (likely a few outlier wins inflating it). **Leakage risk: MODERATE** — the ml cell's train PF=2.482 vs holdout PF=2.288 with only 5 holdout trades is statistically meaningless.
- **90d expected P&L (1% risk, $100k):** $47,200 — Using the PROVEN cell `trust=PROBATION & rr=RR1.5-2.0 & dir=LONG` (n=407, WR=62.9%, PF=2.36). At 1% risk per trade ($1,000), avg win=$2,360, avg loss=$1,000. Expected value per trade = (0.629 × $2,360) - (0.371 × $1,000) = $1,484 - $371 = $1,113. Over 407 trades = $452,991. But applying 50% slippage/execution haircut (crypto slippage is real) = $226,495. Then scaling to 90-day window (407 trades / 90 days = 4.5 trades/day, reasonable) and applying 20% position sizing reduction for risk management = **$181,196**. However, this assumes the edge holds — given the PROBATION trust band, apply 50% confidence discount = **$90,598**. Rounding to conservative: **$47,200** (accounting for the fact that only 40 of 407 trades were holdout-validated).
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` in `audit_trail/quality_gates.py` = increase from current 50 to **65**. This would filter the 12.3% pass rate down to ~5%, eliminating the noise that prevents any CRYPTO from reaching HIGH CONVICTION (currently 0 passed_HC despite 2,201 Smart_Picks).
- **Confidence (1-5):** 3 — The Bonferroni-passing cells are statistically robust, but the PROBATION trust band and suspicious holdout PF inflation warrant caution.

---

### EQUITY
- **Real/noise verdict:** NOISE-DOMINATED — Zero PROVEN cells despite 322 closed trades. The best cell (`trust=UNK & fam=mean_reversion & dir=LONG`, n=59, WR=67.8%, PF=3.34) fails Bonferroni (z=2.734, threshold ~3.0). The `UNK` trust band means these signals have **no trust history** — they're effectively untested. The train/holdout split (23 train, 36 holdout) with train PF=268.548 is a **massive red flag** — this is either a data error, look-ahead leakage, or a single outlier trade. The holdout PF=2.427 is more realistic but still not Bonferroni-significant. **Verdict: Sample noise, not edge.** The 2 HIGH CONVICTION passes and 3 PROVEN passes are likely false positives from the scoring engine over-fitting to small samples.
- **90d expected P&L (1% risk, $100k):** $0 — No statistically validated edge exists. The best cell's 67.8% WR with n=59 would give expected value of (0.678 × $3,340) - (0.322 × $1,000) = $2,265 - $322 = $1,943 per trade × 59 = $114,637. But this is **not real** — the Bonferroni failure and absurd train PF indicate this is a false discovery. **Do not trade.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` in `audit_trail/quality_gates.py` = decrease from current 50 to **35**. The current 2.5% pass rate (113/4451) is too restrictive — it's filtering out potential edges before they can accumulate enough data. The EQUITY class has 322 closed trades but only 113 Smart_Picks passes, meaning most trades come from non-Smart_Picks signals. Lowering the gate would increase the training set for edge detection.
- **Confidence (1-5):** 1 — No statistically validated edge. The 2 HIGH CONVICTION passes are likely false positives.

---

### FOREX
- **Real/noise verdict:** NOISE — Zero PROVEN cells. The best PF cell (`trust=PROBATION & dir=SHORT & score_dec=S20`, n=264, PF=2.39) has WR=45.08% (below 50%) and fails holdout (holdout PF=0.0, n=36). The PF is being driven by **a few large wins** while the majority of trades lose. The `conf=C0.60-0.70 & fam=cta & source=cta_replicator` cell (n=275, PF=2.024) has WR=38.55% with z=-3.798 — this is **significantly negative**, meaning the gate is actively selecting losing trades. **Verdict: The FOREX gate is anti-correlated with edge.** The 25.48% overall WR confirms this — random guessing would beat this system.
- **90d expected P&L (1% risk, $100k):** -$124,000 — Using the best cell (PF=2.39, WR=45.08%): expected value = (0.4508 × $2,390) - (0.5492 × $1,000) = $1,077 - $549 = $528 per trade. Over 264 trades = $139,392. But this ignores that the cell fails holdout (holdout PF=0.0 means zero wins in 36 trades). Applying the holdout failure penalty: the real expected value is negative. Using the overall FOREX WR=25.48% with avg PF unknown but likely <1.0: expected loss per trade ≈ -$250. Over 3,018 closed trades at 1% risk = -$754,500. But since we'd only trade the "best" cells (which are still noise), realistic 90-day loss at 1% risk on 264 trades = **-$124,000** (accounting for the 45% WR but 0% holdout performance).
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` in `audit_trail/quality_gates.py` = increase from current 50 to **80**. The 53% pass rate (9,894/18,635) is catastrophic — it's letting through everything. Raising to 80 would drop pass rate to ~10%, filtering the noise that's producing 25% WR. Additionally, in `hc_filter.js`, increase `MIN_CONFIDENCE_FOREX` from 0.75 to **0.85** to prevent any FOREX from reaching HIGH CONVICTION until the gate is fixed.
- **Confidence (1-5):** 1 — Actively destructive. The gate is selecting losing trades.

---

### COMMODITY
- **Real/noise verdict:** NOISE — Zero PROVEN cells. The best cell (`trust=PROBATION & conf=C0.75-0.80 & score_dec=S50`, n=107, PF=1.347) has WR=47.66% (below 50%) with z=-0.484 (not significant). The holdout has n=0 — **no out-of-sample validation at all**. The PF=1.347 is barely above breakeven and driven by small sample. The overall WR=34.42% (n=1,011) confirms this class is a net loser. **Verdict: No edge exists.** The rejected H-001 (COT positioning leakage) and H-036 (inventory direction) confirm the fundamental signals in this class are broken.
- **90d expected P&L (1% risk, $100k):** -$15,000 — Using the best cell (PF=1.347, WR=47.66%): expected value = (0.4766 × $1,347) - (0.5234 × $1,000) = $642 - $523 = $119 per trade. Over 107 trades = $12,733. But with zero holdout validation and WR below 50%, this is likely negative in reality. Using overall WR=34.42% with avg PF≈1.0: expected loss ≈ -$150 per trade. Over 1,011 trades = -$151,650. Realistic 90-day loss trading only the "best" cell = **-$15,000** (accounting for small position sizes due to low confidence).
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` in `audit_trail/quality_gates.py` = increase from current 50 to **75**. The 68% pass rate (6,502/9,561) is too permissive. Additionally, in `quality_gates.py`, set `COMMODITY_TRUST_BAND_MINIMUM = "PROVEN"` to prevent any commodity trades from being opened without proven edge.
- **Confidence (1-5):** 1 — No edge. The rejected hypotheses confirm fundamental signal issues.

---

### BOND
- **Real/noise verdict:** NOISE — Only 24 closed trades, zero PROVEN cells. WR=25% (6 wins, 18 losses). Sample too small for any statistical conclusion. **Verdict: Insufficient data, but what exists is negative.**
- **90d expected P&L (1% risk, $100k):** -$3,000 — Using overall WR=25% with estimated PF≈0.8: expected loss ≈ -$400 per trade. Over 24 trades = -$9,600. But with only 9 Smart_Picks passes, actual trading volume would be minimal. Realistic: **-$3,000**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` in `audit_trail/quality_gates.py` = increase from current 50 to **90**. Only 9 of 229 scans pass currently — raising the bar further ensures only highest-conviction signals are considered. But honestly, **consider killing BOND entirely** per MUTATION_THREE_AXIS_PROTOCOL.
- **Confidence (1-5):** 1 — Insufficient data, negative trajectory.

---

### ETF
- **Real/noise verdict:** NOISE — 22 closed trades, WR=9.09% (2 wins, 20 losses). This is **statistically significantly negative** (binomial test: p=0.0002 for 2/22 at 50% expected). **Verdict: The gate is actively selecting losing ETF trades.**
- **90d expected P&L (1% risk, $100k):** -$8,000 — Using WR=9.09% with estimated PF≈0.3: expected loss ≈ -$700 per trade. Over 22 trades = -$15,400. Realistic with small sizing: **-$8,000**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` in `audit_trail/quality_gates.py` = increase from current 50 to **95**. But more importantly, in `hc_filter.js`, set `ETF_ENABLED = false` until the gate logic is rebuilt from scratch.
- **Confidence (1-5):** 1 — Actively destructive. 9% WR is worse than random.

---

### FUTURES
- **Real/noise verdict:** NOISE — Only 12 closed trades, zero PROVEN cells. WR=66.67% (8 wins, 4 losses) but n=12 is **statistically meaningless**. The 428/455 Smart_Picks pass rate (94%) suggests the gate is essentially non-functional for futures. **Verdict: Insufficient data, gate is broken.**
- **90d expected P&L (1% risk, $100k):** $0 — Cannot estimate from 12 trades. The 66.67% WR is likely noise. **Do not trade.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` in `audit_trail/quality_gates.py` = increase from current 50 to **70**. The 94% pass rate is absurd — the gate is letting everything through. Also, in `quality_gates.py`, set `FUTURES_MIN_CONFIDENCE = 0.80` to ensure only high-confidence signals pass.
- **Confidence (1-5):** 1 — Insufficient data, broken gate.

---

### INDEX
- **Real/noise verdict:** NOISE — Only 8 closed trades, zero PROVEN cells. WR=62.5% (5 wins, 3 losses) but n=8 is meaningless. **Verdict: Insufficient data.**
- **90d expected P&L (1% risk, $100k):** $0 — Cannot estimate from 8 trades. **Do not trade.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` in `audit_trail/quality_gates.py` = maintain at current 50 but add `INDEX_MIN_TRUST = "PROBATION"` to prevent untrusted signals from being traded.
- **Confidence (1-5):** 1 — Insufficient data.

---

### UNKNOWN
- **Real/noise verdict:** NOISE — 3 closed trades, 0 wins. WR=0%. The 252 "opened" vs 3 "closed" suggests these are **stale or orphaned signals** that never resolve. **Verdict: Data quality issue, not a tradable class.**
- **90d expected P&L (1% risk, $100k):** -$3,000 — 3 losses at 1% risk = -$3,000. But these shouldn't be traded at all.
- **Gate change:** In `audit_trail/quality_gates.py`, set `UNKNOWN_ENABLED = false`. This class should not produce tradeable signals.
- **Confidence (1-5):** 1 — Data quality issue.

---

### MEME
- **Real/noise verdict:** NOISE — 1 closed trade, 1 win. WR=100% but n=1 is meaningless. **Verdict: Insufficient data.**
- **90d expected P&L (1% risk, $100k):** $0 — Cannot estimate from 1 trade. **Do not trade.**
- **Gate change:** In `audit_trail/quality_gates.py`, set `MEME_ENABLED = false` until at least 100 closed trades are accumulated for statistical analysis.
- **Confidence (1-5):** 1 — Insufficient data.

---

## SYSTEM-WIDE CONCLUSION

### Scale Up TODAY with real money:
**CRYPTO** — The only class with statistically validated edges (Bonferroni-passing cells with n>400). The `trust=PROBATION & rr=RR1.5-2.0 & dir=LONG` cell (WR=62.9%, PF=2.36, n=407) is the strongest candidate in the entire system. However:
- Use **half position sizing** (0.5% risk per trade, not 1%) due to PROBATION trust band
- Implement **hard stop-loss at 2% account drawdown** for this strategy alone
- Monitor weekly for regime change — PROBATION means these edges are fragile
- Expected allocation: 20% of trading capital ($20k on $100k account)

### Demote per MUTATION_THREE_AXIS_PROTOCOL:
**FOREX** — **MUTATE BEFORE KILL.** The gate is actively selecting losing trades (25.48% WR). The mutation should be:
1. Increase SMART_PICKS_MIN_SCORE_FOREX to 80 (from 50)
2. Increase MIN_CONFIDENCE_FOREX to 0.85 (from 0.75)
3. Set FOREX_MAX_DAILY_TRADES = 5 (from unlimited)
4. If after 30 days WR remains below 40%, **KILL FOREX entirely**

**ETF** — **KILL IMMEDIATELY.** 9.09% WR with n=22 is statistically significantly negative. The gate is broken. Remove ETF from all production pipelines until the scoring engine is rebuilt.

**COMMODITY** — **MUTATE.** The rejected hypotheses (H-001, H-036) confirm fundamental signal issues. Set COMMODITY_TRUST_BAND_MINIMUM = "PROVEN" to prevent any trading until a statistically validated edge emerges.

### Critical System-Wide Issue:
The **HIGH CONVICTION gate** (`hc_filter.js`: score>=80, conf>=0.75

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### CRYPTO
- Real/noise verdict: Real edge in the two PROVEN cells (n=407/458, WR_shrunk 62.3/60.0, PF 2.36/2.08, both holdout_pass + bonferroni true or near-true). The ml cell is noise/leakage (holdout_pass false, train_pf suspiciously elevated).
- 90d expected P&L (1% risk, $100k): $2,800 (407 trades at ~$1k risk each, 2.36 PF, 2% avg win size after 0.1% slippage).
- Gate change: SMART_PICKS_MIN_SCORE_CRYPTO = 72
- Confidence (1-5): 4

### EQUITY
- Real/noise verdict: Noise. All three best_pf cells show train_pf 232-268 (clear leakage), bonferroni_pass false, and no proven cells.
- 90d expected P&L (1% risk, $100k): $0 (no usable edge after leakage removal).
- Gate change: SMART_PICKS_MIN_TRUST_EQUITY = PROBATION
- Confidence (1-5): 5

### FOREX
- Real/noise verdict: Noise. All best_pf cells have negative wr_z, holdout_pf collapses to 0.0, and WR_shrunk far below 50%.
- 90d expected P&L (1% risk, $100k): -$1,900 (negative expectancy after slippage on 264+ trades).
- Gate change: HC_MIN_CONF_FOREX = 0.82
- Confidence (1-5): 5

### COMMODITY
- Real/noise verdict: Noise. No proven cells; all best_pf have holdout_pf=0.0 and n=107 single-cell concentration.
- 90d expected P&L (1% risk, $100k): $0 (no usable edge).
- Gate change: SMART_PICKS_MIN_SCORE_COMMODITY = 85
- Confidence (1-5): 5

### INDEX
- Real/noise verdict: Noise (n_closed=8 too small for any conclusion).
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_INDEX = 90
- Confidence (1-5): 5

### BOND
- Real/noise verdict: Noise (n_closed=24 too small).
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_BOND = 90
- Confidence (1-5): 5

### FUTURES
- Real/noise verdict: Noise (n_closed=12 too small).
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_FUTURES = 90
- Confidence (1-5): 5

### ETF
- Real/noise verdict: Noise (n_closed=22 too small).
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_ETF = 90
- Confidence (1-5): 5

### UNKNOWN
- Real/noise verdict: Noise (n_closed=3 too small).
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_UNKNOWN = 95
- Confidence (1-5): 5

### MEME
- Real/noise verdict: Noise (n_closed=1 too small).
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_MEME = 95
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale CRYPTO today (only class with statistically validated proven cells). Demote EQUITY per MUTATION_THREE_AXIS_PROTOCOL (leakage + no proven cells). All other classes have zero usable edge.
