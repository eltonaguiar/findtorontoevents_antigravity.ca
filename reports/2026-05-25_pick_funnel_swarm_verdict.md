# Pick Funnel Swarm Verdict — 2026-06-21 05:39 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260621T053842Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

### CRYPTO
- **Real/noise verdict:** **Real** – two PROVEN cells pass the Bonferroni‑adjusted test (n = 410 and n = 458, WR ≈ 62 % shrunk, PF ≈ 2.1‑2.4). Sample size is ample, win‑rate is well above 50 % and the profit‑factor is comfortably > 2. No obvious leakage (trust = PROBATION is a deliberately low‑trust bucket, but the signal survives the hold‑out).  
- **90d expected P&L (1 % risk, $100 k):**  
  *Cell 1* (trust = PROBATION, RR = 1.5‑2.0, LONG): 410 trades × $1 000 × 1.099 % ≈ **$4.12 M**.  
  *Cell 2* (trust = PROBATION, conf < 0.60, LONG): 458 trades × $1 000 × 0.847 % ≈ **$388 k**.  
  **Combined expected profit ≈ $4.5 M** over the 90‑day window (assuming flat‑risk, no compounding, and modest slippage of 0.05 % per trade).  
- **Gate change:** lower the HC‑filter trust requirement so that “PROBATION” trades are allowed. In `audit_dashboard/hc_filter.js` set `MIN_TRUST = 30` (instead of the current 60).  
- **Confidence (1‑5):** **5** – statistical tests, hold‑out validation and ample trade count all support a genuine edge.

### EQUITY
- **Real/noise verdict:** **Noise** – no PROVEN cells; the best PF‑only cells fail the Bonferroni test and have tiny training samples (n ≈ 50). The win‑rate on decisive trades is only ~40 % and PF is not reliably > 1.  
- **90d expected P&L (1 % risk, $100 k):** Using the decisive set (314 trades, WR ≈ 40 %, assume PF ≈ 1): expected loss ≈ (0.401‑0.599) × $1 000 ≈ ‑$198 per trade → **‑$62 k** over 314 trades (or ≈ ‑$600 k if we naïvely scale to all 3 021 closed trades).  
- **Gate change:** raise the SMART‑PICKS minimum score for EQUITY (`SMART_PICKS_MIN_SCORE_EQUITY`) from its current level to a stricter value (e.g., +5) to prune low‑quality signals.  
- **Confidence (1‑5):** **2** – the data do not support a reliable edge.

### COMMODITY
- **Real/noise verdict:** **Noise** – no PROVEN cells; the top PF cells have n = 107, WR ≈ 48 % and PF ≈ 1.35, but they fail hold‑out and Bonferroni checks. Likely over‑fitted or leakage (the only signal uses a narrow confidence band that was previously flagged in H‑036).  
- **90d expected P&L:** With WR ≈ 34 % (overall) and PF ≈ 1, expected per‑trade drift is negative (~‑0.3 %); over 1 008 closed trades → **‑$300 k** (flat‑risk).  
- **Gate change:** tighten the confidence band requirement in `audit_trail/quality_gates.py` – raise `COMMODITY_MIN_CONF = 0.80` (currently allowing 0.75‑0.80).  
- **Confidence (1‑5):** **2**.

### FOREX
- **Real/noise verdict:** **Noise** – no PROVEN cells. The highest‑PF cell (trust = PROBATION, SHORT, S20) has PF = 2.39 but fails hold‑out (PF = 0 on hold‑out) and the win‑rate is only ~45 %. The “consensus” cell (conf = 0.60‑0.70, fam = cta) shows PF ≈ 2.0 but again fails Bonferroni.  
- **90d expected P&L:** Overall decisive WR ≈ 25 % (loss‑heavy). Assuming PF ≈ 1, expected loss ≈ ‑$200 per trade → **‑$600 k** over 3 004 closed trades.  
- **Gate change:** increase the minimum confidence for FOREX in `audit_trail/quality_gates.py` – set `FOREX_MIN_CONF = 0.80`.  
- **Confidence (1‑5):** **2**.

### FUTURES
- **Real/noise verdict:** **Noise** – only 12 decisive trades, no PROVEN cells, win‑rate 66 % but PF ≈ 1 (no profit factor advantage). Sample too small to trust.  
- **90d expected P&L:** With PF ≈ 1, expected per‑trade drift ≈ ‑$200 → **‑$2.4 k** (12 trades).  
- **Gate change:** raise `FUTURES_MIN_SCORE` to prune the tiny sample; e.g., require `SMART_PICKS_MIN_SCORE_FUTURES += 5`.  
- **Confidence (1‑5):** **1**.

### ETF
- **Real/noise verdict:** **Noise** – 22 decisive trades, win‑rate 9 %, PF ≈ 1. No statistical edge.  
- **90d expected P&L:** Expected loss ≈ ‑$200 per trade → **‑$4.4 k**.  
- **Gate change:** increase `ETF_MIN_CONF = 0.80` (currently lower).  
- **Confidence (1‑5):** **1**.

### BOND
- **Real/noise verdict:** **Noise** – 24 decisive trades, win‑rate 25 %, PF ≈ 1. No edge.  
- **90d expected P&L:** Expected loss ≈ ‑$200 per trade → **‑$4.8 k**.  
- **Gate change:** raise `BOND_MIN_TRUST` to exclude low‑trust picks.  
- **Confidence (1‑5):** **1**.

### INDEX
- **Real/noise verdict:** **Noise** – only 8 decisive trades, win‑rate 62 % but PF ≈ 1, sample far too small.  
- **90d expected P&L:** Roughly break‑even; expected profit ≈ +$0 (±$1 k).  
- **Gate change:** require at least 20 decisive trades before a cell is considered; adjust `MIN_DECISIVE_TRADES = 20`.  
- **Confidence (1‑5):** **1**.

### UNKNOWN
- **Real/noise verdict:** **Noise** – 3 decisive trades, 0 % win‑rate.  
- **90d expected P&L:** Expected loss ≈ ‑$3 k.  
- **Gate change:** filter out “UNKNOWN” asset class entirely (`IGNORE_ASSET_CLASS = ["UNKNOWN"]`).  
- **Confidence (1‑5):** **1**.

### MEME
- **Real/noise verdict:** **Noise** – single trade, 100 % win but no statistical basis.  
- **90d expected P&L:** One trade → $1 000 profit (but not repeatable).  
- **Gate change:** exclude “MEME” from production (`IGNORE_ASSET_CLASS = ["MEME"]`).  
- **Confidence (1‑5):** **1**.

---

## SYSTEM‑WIDE Conclusion
- **Scale‑up today:** **CRYPTO** – the two PROVEN cells demonstrate a robust, statistically‑validated edge with a combined expected profit of > $4 M on a $100 k flat‑risk account. The most impactful immediate improvement is to lower the HC‑filter trust threshold (`MIN_TRUST = 30`) so that the “PROBATION” bucket is allowed to flow to the live pick list.
- **Demote / mutate:** **EQUITY** and **FOREX** – both classes lack any PROVEN edge and show negative expected returns under the current risk model. According to the MUTATION_THREE_AXIS_PROTOCOL, they should be **mutated** (tighten score/confidence thresholds) before being killed outright. The next step is to raise the SMART‑PICKS minimum scores (`SMART_PICKS_MIN_SCORE_EQUITY` and `SMART_PICKS_MIN_SCORE_FOREX`) and increase the minimum confidence bands (`FOREX_MIN_CONF = 0.80`). This will prune the noisy signals and prevent capital erosion while we search for a genuine edge.

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-day edge analysis

## CRITICAL PRELIMINARY OBSERVATION

The funnel data contains **severe logical inconsistencies** that must be addressed before any edge analysis:

1. **CRYPTO**: `passed_smart` (2,163) < `opened` (2,199) — impossible unless trades are opened without passing Smart_Picks
2. **EQUITY**: `passed_smart` (98) vs `opened` (1,267) — 13x more opened than passed
3. **COMMODITY**: `passed_smart` (6,426) vs `opened` (2,180) — only 34% of passed picks are opened
4. **FOREX**: `passed_smart` (9,416) vs `opened` (3,063) — only 33% opened
5. **UNKNOWN**: `passed_smart` (24) vs `opened` (228) — 9.5x more opened than passed

**Conclusion**: The funnel stages are NOT sequential. Trades are being opened from multiple entry points, not just through the Smart_Picks → Verified_Alpha → High_Conviction pipeline. The `passed_*` columns appear to track different signal sources, not a strict funnel.

---

### CRYPTO
- **Real/noise verdict**: NOISE — The "PROVEN" cells are statistical artifacts from data leakage. The `trust=PROBATION & rr=RR1.5-2.0 & dir=LONG` cell shows WR=62.93%, PF=2.368 on n=410, but the holdout PF=6.639 on only n=40 is absurdly high — this is either a cherry-picked holdout set or look-ahead bias. The `trust=PROBATION & conf=C<0.60 & dir=LONG` cell (n=458, WR=60.48%) has holdout PF=1.673 on n=25 — insufficient sample. The `fam=ml` cell (PF=2.48) fails holdout (PF=1.419 on n=6). **None of these edges survive rigorous testing.** The overall WR=49.2% on 3,746 decisive trades confirms no edge exists at the aggregate level.
- **90d expected P&L (1% risk, $100k)**: $0 — No tradeable edge identified. If forced to trade the "best" cell (PROBATION/LONG/RR1.5-2.0) with 410 trades at 1% risk ($1,000/trade), expected P&L = 410 × ($1,000 × 2.368 PF × 0.6293 WR) ≈ $610,000. **This is a fantasy number** — the holdout failure and suspicious PF inflation make this unrealizable.
- **Gate change**: `SMART_PICKS_MIN_SCORE_CRYPTO` = 85 (increase from current 80). The current gate passes 12.2% of scans (2,163/17,736) — too permissive. Raising to 85 would filter to ~8% pass rate, eliminating low-confidence noise.
- **Confidence (1-5)**: 1 — Data integrity issues, no reproducible edge, suspicious holdout metrics.

---

### EQUITY
- **Real/noise verdict**: NOISE — Zero PROVEN cells. The "best" cell (`trust=UNK & fam=mean_reversion & dir=LONG`, n=57, WR=66.67%, PF=3.263) has train PF=528.434 on n=21 — this is **obvious overfitting/leakage**. A PF of 528 is impossible in real markets. The holdout PF=2.346 on n=36 is more realistic but still suspicious. The other two "best" cells also have absurd train PFs (34.822, 374.183) with tiny training samples (n=15-21). Overall WR=40.13% on 314 decisive trades confirms **negative edge**.
- **90d expected P&L (1% risk, $100k)**: -$12,560 — Based on aggregate WR=40.13% and estimated PF≈0.85 (from win/loss ratio: 126 wins vs 188 losses, avg win ≈ avg loss). 314 trades × ($1,000 × 0.85 PF × 0.4013 WR - $1,000 × 0.5987) = -$12,560.
- **Gate change**: `SMART_PICKS_MIN_SCORE_EQUITY` = 90 (increase from current 80). Current pass rate is 2.3% (98/4,288) — already strict, but the quality is terrible. Raising to 90 would pass <1% of scans, effectively killing the class until the alpha engine improves.
- **Confidence (1-5)**: 1 — Negative edge, data leakage in "best" cells, no PROVEN edges.

---

### COMMODITY
- **Real/noise verdict**: NOISE — Zero PROVEN cells. The "best" cells are all the same cell repeated with different dimension combinations (`trust=PROBATION & conf=C0.75-0.80 & score_dec=S50`, n=107, WR=47.66%, PF=1.347). This is **below 50% WR with PF barely above 1.0** — not an edge. The holdout has n=0 (all data used for training), which is a methodological failure. Overall WR=34.23% on 1,008 decisive trades confirms **strong negative edge**.
- **90d expected P&L (1% risk, $100k)**: -$19,152 — Based on aggregate WR=34.23% and PF≈0.78 (345 wins vs 663 losses). 1,008 trades × ($1,000 × 0.78 PF × 0.3423 WR - $1,000 × 0.6577) = -$19,152.
- **Gate change**: `SMART_PICKS_MIN_SCORE_COMMODITY` = 85 (increase from current 75). Current pass rate is 67.8% (6,426/9,481) — **far too permissive**. Raising to 85 would pass ~30%, eliminating the noise floor. Also consider `MIN_CONFIDENCE_COMMODITY` = 0.70 (increase from 0.60).
- **Confidence (1-5)**: 1 — Negative edge, no PROVEN cells, methodological failure in best cell analysis.

---

### FOREX
- **Real/noise verdict**: NOISE — Zero PROVEN cells. The "best" cells are **catastrophically bad**: WR=20.76% (n=501, PF=1.904) with holdout PF=0.0 on n=290 — the edge completely disappears out of sample. The WR=38.55% cell (n=275, PF=2.024) has holdout PF=1.893 on n=11 — insufficient sample. The WR=45.08% cell (n=264, PF=2.39) has holdout PF=0.0 on n=36 — **zero profitability out of sample**. Overall WR=25.43% on 3,004 decisive trades confirms **extremely strong negative edge**.
- **90d expected P&L (1% risk, $100k)**: -$44,060 — Based on aggregate WR=25.43% and PF≈0.51 (764 wins vs 2,240 losses). 3,004 trades × ($1,000 × 0.51 PF × 0.2543 WR - $1,000 × 0.7457) = -$44,060.
- **Gate change**: `SMART_PICKS_MIN_SCORE_FOREX` = 92 (increase from current 70). Current pass rate is 51.9% (9,416/18,154) — **extremely permissive**. Raising to 92 would pass <10%, drastically reducing false signals. Also implement `MAX_DAILY_FOREX_PICKS` = 50 to prevent over-trading.
- **Confidence (1-5)**: 1 — Strong negative edge, holdout failures, no PROVEN cells.

---

### FUTURES
- **Real/noise verdict**: NOISE — Zero PROVEN cells. Only 12 decisive trades total — **insufficient data** for any conclusion. The 66.67% WR is meaningless on n=12.
- **90d expected P&L (1% risk, $100k)**: $0 — Cannot estimate with n=12. Historical performance suggests no edge.
- **Gate change**: `SMART_PICKS_MIN_SCORE_FUTURES` = 80 (maintain current). The issue is insufficient volume, not gate quality.
- **Confidence (1-5)**: 1 — Insufficient data.

---

### ETF
- **Real/noise verdict**: NOISE — Zero PROVEN cells. WR=9.09% on 22 decisive trades is **catastrophic**. Only 2 wins vs 20 losses.
- **90d expected P&L (1% risk, $100k)**: -$18,000 — 22 trades × ($1,000 × 0.09 PF × 0.0909 WR - $1,000 × 0.9091) = -$18,000 (assuming avg loss = avg win).
- **Gate change**: `SMART_PICKS_MIN_SCORE_ETF` = 95 (increase from current 75). Current pass rate is 44.5% (188/422) — too permissive for a class with proven negative edge. Consider **killing the class entirely**.
- **Confidence (1-5)**: 1 — Strong negative edge, tiny sample.

---

### BOND
- **Real/noise verdict**: NOISE — Zero PROVEN cells. WR=25.0% on 24 decisive trades is negative edge, but sample too small for confidence.
- **90d expected P&L (1% risk, $100k)**: -$6,000 — 24 trades × ($1,000 × 0.50 PF × 0.25 WR - $1,000 × 0.75) = -$6,000.
- **Gate change**: `SMART_PICKS_MIN_SCORE_BOND` = 85 (increase from current 70). Current pass rate is 4.0% (9/226) — already strict, but quality is poor.
- **Confidence (1-5)**: 1 — Negative edge, insufficient data.

---

### INDEX
- **Real/noise verdict**: NOISE — Zero PROVEN cells. Only 8 decisive trades — **completely insufficient data**. The 62.5% WR is meaningless.
- **90d expected P&L (1% risk, $100k)**: $0 — Cannot estimate with n=8.
- **Gate change**: `SMART_PICKS_MIN_SCORE_INDEX` = 80 (maintain current). Volume is the issue, not gate quality.
- **Confidence (1-5)**: 1 — Insufficient data.

---

### UNKNOWN
- **Real/noise verdict**: NOISE — Zero PROVEN cells. WR=0.0% on 3 decisive trades. **No data.**
- **90d expected P&L (1% risk, $100k)**: $0 — Cannot estimate.
- **Gate change**: `SMART_PICKS_MIN_SCORE_UNKNOWN` = 95 (effectively kill the class). The fact that 228 trades were opened from UNKNOWN classification is a **systemic data quality issue**.
- **Confidence (1-5)**: 1 — No data, classification failure.

---

### MEME
- **Real/noise verdict**: NOISE — Zero PROVEN cells. Only 1 decisive trade. **No data.**
- **90d expected P&L (1% risk, $100k)**: $0 — Cannot estimate.
- **Gate change**: `SMART_PICKS_MIN_SCORE_MEME` = 95 (effectively kill the class). MEME classification should be deprecated.
- **Confidence (1-5)**: 1 — No data.

---

## SYSTEM-WIDE CONCLUSION

### Scale Up TODAY with Real Money: **NONE**

**Brutal honesty**: Every single asset class shows **negative or non-existent edge**. The system is generating losses across the board:
- FOREX: -$44k/90d (worst)
- COMMODITY: -$19k/90d
- EQUITY: -$13k/90d
- ETF: -$18k/90d (on tiny volume)
- CRYPTO: ~$0 (noise, not edge)

**Total estimated 90-day P&L at 1% risk/$100k**: **-$100k+** — the system would have lost its entire notional in 90 days.

### DEMOTE per MUTATION_THREE_AXIS_PROTOCOL:

**KILL (immediate demotion to HARNESS_REJECTED)**:
1. **FOREX** — WR=25.43%, PF≈0.51, n=3,004. Strongest negative edge. All "best" cells fail holdout. **Kill immediately.**
2. **ETF** — WR=9.09%, PF≈0.09, n=22. Catastrophic performance. **Kill immediately.**
3. **COMMODITY** — WR=34.23%, PF≈0.78, n=1,008. Strong negative edge. **Kill immediately.**

**MUTATE (reduce allocation, require re-validation)**:
4. **EQUITY** — WR=40.13%, PF≈0.85, n=314. Negative edge but smaller sample. **Reduce to 10% allocation, require 90-day re-validation.**
5. **CRYPTO** — WR=49.2%, PF≈1.0, n=3,746. No edge (noise). **Reduce to 25% allocation, require PROVEN edge discovery.**

**OBSERVE (insufficient data)**:
6. **FUTURES** — n=12
7. **INDEX** — n=8
8. **BOND** — n=24
9. **MEME** — n=1
10. **UNKNOWN** — n=3

**All classes with n<100 should be HARNESS_REJECTED until they accumulate sufficient data.**

### Critical System Issues to Fix Before Any Real Money Deployment:

1. **Funnel data integrity**: The `passed_*` vs `opened` inconsistencies suggest multiple trade entry paths not captured by the funnel. Fix the tracking before trusting any metrics.

2. **Holdout methodology**: Multiple "best" cells have n=0 holdout or holdout PF=0.0. The train/holdout split is either broken or the holdout set is too small. Implement minimum holdout n=30 requirement.

3. **PF inflation**: Train PFs of 528, 374, 34 on n=15-21 are **impossible** in real markets. This is either data leakage, look-ahead bias, or a calculation bug. Investigate immediately.

4. **Bonferroni correction**: Only 2 cells pass Bonferroni correction (both CRYPTO), and both are suspicious. The multiple testing problem is severe — with thousands of cells tested, false positives are guaranteed.

5. **Gate permissiveness**: FOREX (51.9% pass rate) and COMMODITY (67.8% pass rate) are letting through too much noise. Tighten gates across the board.

**Recommendation**: Do NOT deploy real money. Fix the data pipeline, fix the holdout methodology, fix the gate thresholds, and re-run the analysis after 90 days of clean data collection.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### CRYPTO
- Real/noise verdict: Real (two PROVEN cells pass n>400, WR_shrunk>60, PF>2.0, holdout_pass, bonferroni_pass; no obvious single-symbol leakage flagged).
- 90d expected P&L (1% risk, $100k): $11,400 (410+458 trades at ~1.8% avg edge after 0.15% slippage, 1% risk = $1k/trade).
- Gate change: SMART_PICKS_MIN_SCORE_CRYPTO = 72
- Confidence (1-5): 4

### EQUITY
- Real/noise verdict: Noise (no PROVEN cells; best_pf cells show train_pf inflation >30x holdout, bonferroni fails, n<60).
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge).
- Gate change: SMART_PICKS_MIN_TRUST_EQUITY = "VERIFIED"
- Confidence (1-5): 3

### COMMODITY
- Real/noise verdict: Noise (no PROVEN; all best_pf cells fail holdout, n=107 single cell, matches rejected H-001/H-036 patterns).
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge).
- Gate change: SMART_PICKS_MIN_SCORE_COMMODITY = 85
- Confidence (1-5): 4

### FOREX
- Real/noise verdict: Noise (no PROVEN; all best_pf cells fail holdout or bonferroni, WR_shrunk<46, matches consensus leakage risk).
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge).
- Gate change: hc_filter.js MIN_CONF = 0.82
- Confidence (1-5): 4

### FUTURES
- Real/noise verdict: Noise (n_closed=12, no PROVEN or best_pf cells).
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge).
- Gate change: SMART_PICKS_MIN_SCORE_FUTURES = 90
- Confidence (1-5): 5

### ETF
- Real/noise verdict: Noise (n_closed=22, no PROVEN or best_pf cells).
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge).
- Gate change: SMART_PICKS_MIN_SCORE_ETF = 90
- Confidence (1-5): 5

### INDEX
- Real/noise verdict: Noise (n_closed=8, no PROVEN or best_pf cells).
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge).
- Gate change: SMART_PICKS_MIN_SCORE_INDEX = 90
- Confidence (1-5): 5

### BOND
- Real/noise verdict: Noise (n_closed=24, no PROVEN or best_pf cells).
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge).
- Gate change: SMART_PICKS_MIN_SCORE_BOND = 90
- Confidence (1-5): 5

### UNKNOWN
- Real/noise verdict: Noise (n_closed=3, no PROVEN or best_pf cells).
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge).
- Gate change: SMART_PICKS_MIN_SCORE_UNKNOWN = 90
- Confidence (1-5): 5

### MEME
- Real/noise verdict: Noise (n_closed=1, no PROVEN or best_pf cells).
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge).
- Gate change: SMART_PICKS_MIN_SCORE_MEME = 90
- Confidence (1-5): 5

**SYSTEM-WIDE**: Scale CRYPTO today (only class with verified PROVEN cells). Demote FOREX and COMMODITY per MUTATION_THREE_AXIS_PROTOCOL.md (mutate filters before kill).
