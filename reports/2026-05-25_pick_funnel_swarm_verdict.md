# Pick Funnel Swarm Verdict — 2026-08-08 04:24 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260808T042425Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

**90‑day edge audit – per‑asset‑class verdict**

```
### CRYPTO
- Real/noise verdict: **Real** – three PROVEN cells pass hold‑out & Bonferroni tests (n = 233‑274, WR_shrunk ≈ 65‑66 %, PF ≈ 2.1‑2.5).  No obvious look‑ahead or single‑symbol concentration; the “trust=UNK” label simply reflects that the trust‑gate (≥60) is currently blocking these picks.
- 90d expected P&L (1 % risk, $100 k account): **≈ $3,700**  
  *Assumptions*: 1 % risk = $1 k per trade; avg. net P&L per proven trade ≈ 0.75 % of risk (weighted avg of the three cells); ~500 unique proven trades over 90 d → 500 × 0.75 % × $1 k ≈ $3.7 k. Slippage is ignored (all trades assumed filled at model price).
- Gate change: **HC_TRUST_MIN** (in `audit_dashboard/hc_filter.js`) → lower from **60** to **0** (or at least to **30**) so that “trust=UNK” picks pass the high‑conviction filter.
- Confidence (1‑5): **4**

```
### FOREX
- Real/noise verdict: **Real** – three PROVEN cells satisfy the statistical thresholds (n = 112‑120, WR_shrunk ≈ 65‑66 %, PF ≈ 3.0‑3.1).  The very high PF = 8.07 cell fails hold‑out, so it is treated as noise.  No leakage detected; the edge lives in the “trust=UNK” band.
- 90d expected P&L (1 % risk, $100 k account): **≈ $900**  
  *Assumptions*: weighted avg. net P&L ≈ 0.30 % of risk; ~300 unique proven trades → 300 × 0.30 % × $1 k ≈ $900. Slippage ignored.
- Gate change: **HC_TRUST_MIN** → lower from **60** to **0** (or ≤ 30) to admit the “trust=UNK” cells.
- Confidence (1‑5): **3**

```
### EQUITY
- Real/noise verdict: **Real** – three PROVEN cells (n = 64 each) pass all tests with WR_shrunk ≈ 87 % and an astronomical PF ≈ 173.  The win‑rate (98 %) and PF are so high that a single‑symbol or data‑leakage risk cannot be ruled out without symbol‑level inspection, but statistically the edge survives hold‑out and Bonferroni correction.
- 90d expected P&L (1 % risk, $100 k account): **≈ $690**  
  *Assumptions*: avg. net P&L ≈ 1.07 % of risk; 64 unique proven trades → 64 × 1.07 % × $1 k ≈ $690. Slippage ignored.
- Gate change: **HC_TRUST_MIN** → lower from **60** to **0** (or ≤ 30) to let the “trust=UNK” equity picks through the HC filter.
- Confidence (1‑5): **4** (high statistical strength but flagged for possible concentration/leakage).

```
### COMMODITY
- Real/noise verdict: **Noise** – no PROVEN cells.  The best‑PF cell (PF ≈ 6.1, n = 34) fails the hold‑out test (PF = 2.5 on hold‑out, Bonferroni = false) and is therefore a likely false‑positive / over‑fitted signal.
- 90d expected P&L (1 % risk, $100 k account): **$0**
- Gate change: none that would create a statistically‑valid edge; the current gates are already too permissive for the only candidate signal.
- Confidence (1‑5): **1**

```
### ETF
- Real/noise verdict: **Noise** – only one cell, fails hold‑out (PF = 0.02) and Bonferroni; no statistical edge.
- 90d expected P&L: **$0**
- Gate change: none (no edge to rescue).
- Confidence: **1**

```
### BOND
- Real/noise verdict: **Noise** – all candidate cells fail hold‑out (PF ≤ 0.47) and Bonferroni; no edge.
- 90d expected P&L: **$0**
- Gate change: none.
- Confidence: **1**

```
### FUTURES
- Real/noise verdict: **Noise** – no PROVEN cells; best PF = 1.55 (n = 23) fails hold‑out and Bonferroni.
- 90d expected P&L: **$0**
- Gate change: none.
- Confidence: **1**

```
### INDEX
- Real/noise verdict: **Noise** – no PROVEN cells; trade count too low for any reliable inference.
- 90d expected P&L: **$0**
- Gate change: none.
- Confidence: **1**

```
### UNKNOWN
- Real/noise verdict: **Noise** – no PROVEN cells; essentially random.
- 90d expected P&L: **$0**
- Gate change: none.
- Confidence: **1**

```
### MEME
- Real/noise verdict: **Noise** – only one closed trade, insufficient data.
- 90d expected P&L: **$0**
- Gate change: none.
- Confidence: **1**
```

---

## SYSTEM‑WIDE conclusion

**Scale‑up candidate:** **CRYPTO** – it has the largest volume of statistically‑validated trades (≈ 500 proven picks) and a positive expected P&L (~ $3.7 k) while staying comfortably below the high‑PF, low‑sample regime of EQUITY.  Raising the trust threshold to admit “trust=UNK” picks will immediately unlock this edge.

**Demote / de‑prioritise:** **COMMODITY** – despite a relatively high scan‑to‑pass rate, there is **no statistically‑significant edge** after the hold‑out test.  Continuing to allocate resources to commodity picks adds noise and risk without expected return; it should be moved to the “mutation‑three‑axis” kill list per the protocol.  

*All other classes (ETF, BOND, FUTURES, INDEX, UNKNOWN, MEME) similarly lack a proven edge and should remain at the current low‑priority or be retired until a new, statistically‑validated signal emerges.*

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

## SYSTEM-WIDE VERDICT: 90-DAY EDGE ANALYSIS

### CRYPTO
- **Real/noise verdict:** The three PROVEN cells are statistically real (n=233-275, WR_shrunk 65-66%, PF 2.1-2.5, holdout_pass=true, Bonferroni_pass=true). However, the `trust=UNK` dimension is a red flag — it means these edges exist in signals with NO trust history, which could indicate the edge is an artifact of how trust is assigned rather than genuine alpha. The `score_dec=S50` cell (n=233, WR=67.8%, PF=2.53) is the strongest, but the train/holdout PF drop (3.92→1.53) suggests some overfitting. The `conf=C0.75-0.80 & dir=LONG & source=alpha_engine` cell (n=274, WR=66.4%, PF=2.17) is more robust with better holdout stability (2.75→1.94). **Verdict: REAL but fragile — the edge is concentrated in LONG signals with moderate confidence, but the trust=UNK dimension suggests the edge may not persist once trust is properly assigned.**
- **90d expected P&L (1% risk, $100k):** $12,400. Assumptions: 1% risk per trade, $100k notional, 0.05% slippage per trade, 233 trades at 67.8% WR with avg win +1.01% and avg loss -0.40% (PF=2.53). Expected profit = 233 × (0.678 × 1.01% - 0.322 × 0.40%) × $100k × 0.95 (slippage) = $12,400. This is the best risk-adjusted edge in the entire system.
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` = 50 (currently likely 60+). The `score_dec=S50` cell shows the edge is in the S50 decile, not higher scores. Lowering the threshold to capture this decile would increase volume without sacrificing quality.
- **Confidence (1-5):** 4

### COMMODITY
- **Real/noise verdict:** NO PROVEN edges. The best cell (n=34, WR=61.8%, PF=6.11) fails holdout (holdout_pass=false), has train_n=6 (tiny), and wr_z=1.371 (not significant). The train PF of 60.6 is absurd — this is pure noise with 6 training samples. The overall class WR of 24.75% (n=404) is catastrophic. **Verdict: NOISE — no statistically real edge exists.**
- **90d expected P&L (1% risk, $100k):** -$4,100. Assumptions: 1% risk, $100k, 0.05% slippage, 404 trades at 24.75% WR with avg win +0.50% and avg loss -0.30% (estimated from PF<1). Expected loss = 404 × (0.2475 × 0.50% - 0.7525 × 0.30%) × $100k × 0.95 = -$4,100. The class is a money-loser.
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` = 80 (raise from current). This would eliminate the 6,107 signals that pass Smart but produce 24.75% WR. Only the top 5% of signals should be considered, and even then, the edge is unproven.
- **Confidence (1-5):** 2

### EQUITY
- **Real/noise verdict:** The PROVEN cell (n=64, WR=98.4%, PF=172.8) is statistically real but **SUSPICIOUS**. A 98.4% WR with PF=172.8 is not a trading edge — it's a data error. The `conf=C<0.60 & fam=mean_reversion` cell with 63 wins out of 64 trades is either: (a) a look-ahead bias where the signal is derived from the outcome, (b) a single-symbol concentration (e.g., one stock that always wins), or (c) a data pipeline bug. The holdout PF of 138.15 confirms this is not a real edge — no strategy produces 138x returns on 48 holdout trades. **Verdict: LEAKAGE — this is not a real edge, it's a data artifact. Do NOT trade this.**
- **90d expected P&L (1% risk, $100k):** $0 (DO NOT TRADE). If you naively traded this, the expected P&L would be $6,900 (64 trades × 98.4% WR × 1.07% avg win × $100k × 0.95), but this is fictional — the edge will not persist out-of-sample because it's a data error.
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` = 60 (keep current). More importantly, add a **sanity check** in `production_scanner.py` to flag any cell with WR>90% and PF>10 for manual review — this is a leakage detector, not a gate.
- **Confidence (1-5):** 1 (the edge is real in the data but NOT real in reality)

### FOREX
- **Real/noise verdict:** The three PROVEN cells are statistically real (n=111-120, WR_shrunk 65-66%, PF 2.9-3.1, holdout_pass=true, Bonferroni_pass=true). The `trust=UNK & conf=C0.75-0.80 & rr=RR1.0-1.5 & fam=mean_reversion` cell (n=112, WR=68.8%, PF=3.15) is the strongest with excellent holdout stability (2.47→3.53). However, the `best_pf_overall` cells with PF=8.07 (n=55, WR=63.6%) are **NOT PROVEN** — they fail holdout (holdout_n=0) and Bonferroni. These are likely overfit to the training data. **Verdict: REAL for the mean_reversion cells, NOISE for the cta cells.** The mean_reversion edge is genuine but the cta edge is overfit.
- **90d expected P&L (1% risk, $100k):** $3,200. Assumptions: 1% risk, $100k, 0.05% slippage, 112 trades at 68.8% WR with avg win +0.31% and avg loss -0.10% (PF=3.15). Expected profit = 112 × (0.688 × 0.31% - 0.312 × 0.10%) × $100k × 0.95 = $3,200. This is modest but real.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` = 50 (lower from current). The edge is in the S50 decile with mean_reversion family — lowering the threshold to capture this decile would increase volume. Also add `FAMILY_FILTER_FOREX = ["mean_reversion"]` to exclude cta signals which are overfit.
- **Confidence (1-5):** 3

### ETF
- **Real/noise verdict:** NO PROVEN edges. The best cell (n=21, WR=9.5%, PF=0.02) is catastrophically bad — 2 wins out of 21 trades. The overall class WR of 12.0% (n=25) is worse than random. **Verdict: NOISE — the class is actively harmful.**
- **90d expected P&L (1% risk, $100k):** -$2,100. Assumptions: 1% risk, $100k, 0.05% slippage, 25 trades at 12% WR with avg win +0.50% and avg loss -0.30%. Expected loss = 25 × (0.12 × 0.50% - 0.88 × 0.30%) × $100k × 0.95 = -$2,100.
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` = 90 (raise dramatically). The class has no edge — only the absolute highest-confidence signals should be considered, and even then, expect losses.
- **Confidence (1-5):** 1

### UNKNOWN
- **Real/noise verdict:** NO PROVEN edges. n=10 closed trades, 0 wins, 10 losses. **Verdict: NOISE — no edge exists.**
- **90d expected P&L (1% risk, $100k):** -$1,000. Assumptions: 1% risk, $100k, 0.05% slippage, 10 trades at 0% WR. Expected loss = 10 × (0 × 0.50% - 1.0 × 0.30%) × $100k × 0.95 = -$1,000.
- **Gate change:** `SMART_PICKS_MIN_SCORE_UNKNOWN` = 100 (effectively disable). The class should not be traded at all.
- **Confidence (1-5):** 1

### FUTURES
- **Real/noise verdict:** NO PROVEN edges. The best cell (n=23, WR=43.5%, PF=1.55) fails holdout (holdout_pass=false) and has negative wr_z (-0.625). The second cell (n=20, WR=30%, PF=0.91) is worse than random. **Verdict: NOISE — no edge exists.**
- **90d expected P&L (1% risk, $100k):** -$300. Assumptions: 1% risk, $100k, 0.05% slippage, 26 trades at 46.15% WR with avg win +0.50% and avg loss -0.30%. Expected loss = 26 × (0.4615 × 0.50% - 0.5385 × 0.30%) × $100k × 0.95 = -$300.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` = 80 (raise). The class has no proven edge — only the top signals should be considered.
- **Confidence (1-5):** 1

### INDEX
- **Real/noise verdict:** NO PROVEN edges. n=10 closed trades, 3 wins, 7 losses. **Verdict: NOISE — insufficient data, no edge.**
- **90d expected P&L (1% risk, $100k):** -$200. Assumptions: 1% risk, $100k, 0.05% slippage, 10 trades at 30% WR. Expected loss = 10 × (0.30 × 0.50% - 0.70 × 0.30%) × $100k × 0.95 = -$200.
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` = 80 (raise). The class has no edge.
- **Confidence (1-5):** 1

### BOND
- **Real/noise verdict:** NO PROVEN edges. The best cell (n=23, WR=13%, PF=0.47) is terrible. The overall class WR of 14.29% (n=35) is worse than random. **Verdict: NOISE — the class is actively harmful.**
- **90d expected P&L (1% risk, $100k):** -$1,500. Assumptions: 1% risk, $100k, 0.05% slippage, 35 trades at 14.29% WR with avg win +0.50% and avg loss -0.30%. Expected loss = 35 × (0.1429 × 0.50% - 0.8571 × 0.30%) × $100k × 0.95 = -$1,500.
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` = 90 (raise dramatically). The class has no edge.
- **Confidence (1-5):** 1

### MEME
- **Real/noise verdict:** NO PROVEN edges. n=1 closed trade, 1 win. **Verdict: NOISE — insufficient data.**
- **90d expected P&L (1% risk, $100k):** $0 (insufficient data). 1 trade at 100% WR is meaningless.
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME` = 100 (effectively disable). The class has no data to support trading.
- **Confidence (1-5):** 1

---

## SYSTEM-WIDE CONCLUSION

### SCALE UP TODAY: **CRYPTO** (LONG, conf 0.75-0.80, score_dec=S50)
- **Why:** The only class with a statistically proven, holdout-validated edge (n=233, WR=67.8%, PF=2.53, holdout_pass=true, Bonferroni_pass=true). The edge is concentrated in LONG signals with moderate confidence and S50 score decile. Expected P&L of $12,400 over 90 days at 1% risk is the best risk-adjusted return in the system.
- **Action:** Lower `SMART_PICKS_MIN_SCORE_CRYPTO` to 50 to capture the S50 decile. Add a filter for `dir=LONG` and `conf>=0.75` in `hc_filter.js`. This should increase volume by ~30% while maintaining quality.

### DEMOTE / MUTATE: **COMMODITY, ETF, BOND, UNKNOWN**
- **Why:** All four classes have WR < 25% with n>25 closed trades. They are actively losing money. Per `docs/MUTATION_THREE_AXIS_PROTOCOL.md`, these should be **mutated before kill** — try different signal families, different confidence bands, or different R:R targets. If mutation doesn't produce a proven edge within 30 days, kill the class.
- **Action:** Set `SMART_PICKS_MIN_SCORE_COMMODITY` = 80, `SMART_PICKS_MIN_SCORE_ETF` = 90, `SMART_PICKS_MIN_SCORE_BOND` = 90, `SMART_PICKS_MIN_SCORE_UNKNOWN` = 100. This will reduce exposure to these classes by 80-90%.

### CRITICAL WARNINGS:
1. **EQUITY's 98.4% WR cell is LEAKAGE, not edge.** Do NOT trade it. Add a sanity check to flag any cell with WR>90% and PF>10 for manual review.
2. **FOREX's cta cells (PF=8.07) are overfit.** Only the mean_reversion cells are real. Add `FAMILY_FILTER_FOREX = ["mean_reversion"]`.
3. **The `trust=UNK` dimension in CRYPTO and FOREX is concerning.** These edges exist in signals with no trust history. Monitor whether the edge persists once trust is properly assigned.

### FINAL VERDICT:
The system has **one real edge** (CRYPTO LONG, conf 0.75-0.80, S50) and **one suspicious edge** (FOREX mean_reversion, conf 0.75-0.80, RR 1.0-1.5). Everything else is noise or leakage. Scale up CRYPTO, carefully test FOREX mean_reversion, and demote everything else. The system is not ready for broad deployment — it needs the gate changes above to focus capital on the proven edge.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

**### CRYPTO**
- Real/noise verdict: Real. Multiple cells show n>200, WR_shrunk 65-66%, PF 2.1-2.5, holdout_pass=true + bonferroni_pass=true. No obvious single-symbol concentration flagged in the data.
- 90d expected P&L (1% risk, $100k): ~$8,400 (using 274 trades at avg 0.63% pnl, 1% risk = $1k/trade, 0.3% slippage + 0.1% commission haircut applied).
- Gate change: `audit_dashboard/hc_filter.js` → raise `HIGH_CONVICTION_MIN_SCORE` from 80 to 82.
- Confidence (1-5): 4

**### FOREX**
- Real/noise verdict: Real. Three cells with n=111-120, WR_shrunk ~65.7%, PF 2.99-3.15, holdout_pass=true + bonferroni_pass=true. Mean-reversion + conf band looks stable.
- 90d expected P&L (1% risk, $100k): ~$2,900 (120 trades at avg 0.29% pnl, $1k risk/trade, 0.25% slippage).
- Gate change: `audit_trail/quality_gates.py` → set `SMART_PICKS_MIN_CONF_FOREX` = 0.72.
- Confidence (1-5): 4

**### COMMODITY**
- Real/noise verdict: Noise. No proven cells. Best_pf cells fail holdout, tiny train n=6, PF collapses out-of-sample.
- 90d expected P&L (1% risk, $100k): $0 (no usable edge).
- Gate change: `audit_trail/quality_gates.py` → raise `SMART_PICKS_MIN_TRUST_COMMODITY` to 70.
- Confidence (1-5): 5

**### EQUITY**
- Real/noise verdict: Noise / likely leakage. 98.44% WR on n=64 with 63 wins is statistically implausible without single-symbol concentration or look-ahead. Even though bonferroni passes, treat as contaminated.
- 90d expected P&L (1% risk, $100k): $0 (reject the edge).
- Gate change: `audit_trail/quality_gates.py` → add `EQUITY_MEAN_REVERSION_MAX_WIN_RATE` = 0.65 hard cap.
- Confidence (1-5): 5

**### INDEX / FUTURES / ETF / BOND / UNKNOWN / MEME**
- Real/noise verdict: Noise. All have n≤35, no proven cells, holdout failures or negative expectancy.
- 90d expected P&L (1% risk, $100k): $0 for each.
- Gate change: `audit_trail/quality_gates.py` → set `SMART_PICKS_MIN_N_CLOSED` = 80 for all non-CRYPTO/FOREX classes.
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale up **CRYPTO** today (multiple verified, holdout-passing edges with realistic PF).  
Demote **COMMODITY** and **EQUITY** per MUTATION_THREE_AXIS_PROTOCOL (no real edge after scrutiny; EQUITY especially risks leakage recurrence). All other classes stay at zero allocation.
