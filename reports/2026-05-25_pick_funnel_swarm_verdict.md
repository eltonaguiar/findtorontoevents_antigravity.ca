# Pick Funnel Swarm Verdict — 2026-06-15 05:49 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260615T054917Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

**NOTE:** All numbers are rounded to the nearest sensible unit.  
Assumptions used for the P&L estimate (see each class below):  

* 1 % of the $100 k account is the maximum loss **per trade** (risk‑of‑ruin is ignored).  
* The “average % PnL” reported for a cell is expressed **per unit of risk** (i.e. a 1 % risk trade that wins on average returns the quoted % of the account).  
* Slippage / commission = **0.20 % of the account per trade** (≈ 2 bps on the notional, typical for crypto‑spot & futures).  
* Trades are assumed independent and fully executed (no position‑size limits).  

---

### COMMODITY
- **Real/noise verdict:** No PROVEN cells. The best PF (1.35) and WR (≈ 48 %) are well below the PROVEN thresholds. Likely pure noise.  
- **90d expected P&L (1 % risk, $100 k):** $0 (no actionable edge).  
- **Gate change:** *None* – there is no edge to amplify.  
- **Confidence (1‑5):** 1  

### EQUITY
- **Real/noise verdict:** No PROVEN cells. The top PF (3.22) comes from a small sample (n = 56) and fails the “PROVEN” Bayesian‑shrink test (WR ≈ 62 % but the hold‑out window is tiny). Risk of look‑ahead / symbol concentration is high.  
- **90d expected P&L:** $0 (no statistically‑validated edge).  
- **Gate change:** *None* – edge not proven.  
- **Confidence:** 1  

### FOREX
- **Real/noise verdict:** No PROVEN cells. Highest PF (2.39) is paired with a WR ≈ 45 % (well under 55 %). The “consensus” cell (trust = PROBATION, conf = C0.60‑0.70) shows a huge PF but the hold‑out PF collapses to 0, indicating severe over‑fit or data‑leakage.  
- **90d expected P&L:** $0.  
- **Gate change:** *None* – edge not validated.  
- **Confidence:** 1  

### CRYPTO
- **Real/noise verdict:** **PROVEN** – two cells pass the Bayesian‑shrink WR ≥ 55 % and PF ≥ 1.5 test, have n ≥ 20, and both hold‑out and Bonferroni checks are true.  
  * Cell A – trust = PROBATION, rr = RR1.5‑2.0, dir = LONG (n = 419, WR = 62.3 %, PF = 2.17).  
  * Cell B – trust = PROBATION, conf < 0.60, dir = LONG (n = 458, WR = 60.5 %, PF = 2.08).  
  No obvious single‑symbol concentration is visible from the summary; a deeper symbol‑level audit is still recommended.  
- **90d expected P&L (1 % risk, $100 k):**  

  *Average % PnL per 1 % risk trade* ≈ 1.86 % (Cell A).  
  *Net after slippage* = 1.86 % – 0.20 % = 1.66 % of the account per trade.  

  Trades in Cell A over the 90‑day window = 419.  

  **Total expected profit** = 419 × 1.66 % ≈ 696 % of the account ≈ **$696 k**.  

  (If we conservatively cap the number of trades to 300 to reflect realistic execution capacity, the estimate falls to ≈ $500 k.)  
- **Gate change:** Lower the HC‑gate trust threshold so that PROBATION‑trust picks can flow to the HIGH‑CONVICTION layer.  

  ```js
  // audit_dashboard/hc_filter.js
  const MIN_TRUST = 50;   // was 60
  ```  

  This will admit the two proven crypto cells into the HC‑filter, unlocking the edge for live deployment.  
- **Confidence:** 5  

### FUTURES
- **Real/noise verdict:** No PROVEN cells (n = 12, PF = 1.0, WR = 66 % but sample too tiny). Edge is not statistically reliable.  
- **90d expected P&L:** $0.  
- **Gate change:** *None*.  
- **Confidence:** 1  

### BOND
- **Real/noise verdict:** No PROVEN cells (WR = 25 %).  
- **90d expected P&L:** $0.  
- **Gate change:** *None*.  
- **Confidence:** 1  

### ETF
- **Real/noise verdict:** No PROVEN cells (WR = 9 %).  
- **90d expected P&L:** $0.  
- **Gate change:** *None*.  
- **Confidence:** 1  

### UNKNOWN
- **Real/noise verdict:** No PROVEN cells (WR = 0 %).  
- **90d expected P&L:** $0.  
- **Gate change:** *None*.  
- **Confidence:** 1  

### INDEX
- **Real/noise verdict:** No PROVEN cells (n = 8).  
- **90d expected P&L:** $0.  
- **Gate change:** *None*.  
- **Confidence:** 1  

### MEME
- **Real/noise verdict:** Single trade (WR = 100 % but n = 1). Statistically meaningless.  
- **90d expected P&L:** $0.  
- **Gate change:** *None*.  
- **Confidence:** 1  

---

## SYSTEM‑WIDE CONCLUSION

**Scale‑up today:** **CRYPTO** – the only asset class with statistically‑validated “PROVEN” edges, solid PF > 2, and a sizable sample (≈ 420 closed trades). Adjusting the HC trust threshold (MIN_TRUST = 50) will let the edge flow into production, and the projected P&L (≈ $500‑$700 k on a $100 k account) justifies a controlled live‑trading pilot.

**Demote / mutate:** **EQUITY**, **FOREX**, **COMMODITY** – each lacks any PROVEN edge despite large scan volumes. According to the *MUTATION_THREE_AXIS_PROTOCOL*, these classes should be moved to the “mutation” bucket for further feature engineering or retired from the pick‑funnel until a new, statistically‑significant signal emerges.  

All other classes (FUTURES, BOND, ETF, UNKNOWN, INDEX, MEME) are already low‑volume or noise‑dominated and should remain out of the live‑trading pipeline.

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

Here is the brutally honest audit of the pick-funnel verdict based on the 90-day data.

---

### COMMODITY
- **Real/noise verdict:** Noise. Zero PROVEN edges. The "best" cells (n=107) show WR_shrunk ~48% and PF=1.347, which is below the PROVEN threshold (PF>=1.5). The holdout PF is 0.0 (no holdout data), indicating no out-of-sample validation. This is sample noise, not an edge.
- **90d expected P&L (1% risk, $100k):** $-1,200. Assuming 1009 decisive trades, 1% risk per trade ($1,000), WR=34.29%, avg win=+1.5R, avg loss=-1R. Expected P&L = 1009 * (0.3429*1.5 - 0.6571*1.0) * $1,000 = 1009 * (-0.1429) * $1,000 = -$144,186. However, the actual closed P&L from the funnel shows 346 wins vs 663 losses. If avg win=+1.5R and avg loss=-1R, P&L = (346*1.5 - 663*1.0) * $1,000 = (519 - 663) * $1,000 = -$144,000. **Corrected estimate: -$144,000.** This is a losing class.
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` = 95. The current gate is too loose, letting through 6,111 signals that produce no edge. Raising the score threshold to 95 would drastically reduce false positives.
- **Confidence (1-5):** 1

### EQUITY
- **Real/noise verdict:** Noise. Zero PROVEN edges. The "best" cells (n=56, n=53, n=49) have small sample sizes and fail Bonferroni correction. The high PF values (3.2, 3.0) are driven by tiny training sets (n=21, n=16, n=15) and are classic overfitting. The holdout PFs (2.3, 1.96, 2.1) are promising but not statistically significant given the small n. This is sample noise.
- **90d expected P&L (1% risk, $100k):** $-2,000. 310 decisive trades, WR=39.68%. P&L = 310 * (0.3968*1.5 - 0.6032*1.0) * $1,000 = 310 * (-0.008) * $1,000 = -$2,480. **Corrected estimate: -$2,480.** Slightly negative, not worth trading.
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` = 90. The current gate passes only 89 out of 4,062 scans (2.2% pass rate), which is already very strict. However, the 89 signals still produce no edge. The issue is not the gate but the signal quality. No gate change will fix this.
- **Confidence (1-5):** 1

### FOREX
- **Real/noise verdict:** Noise. Zero PROVEN edges. The "best" cells show WR_shrunk below 50% and negative WR_z scores (e.g., -13.09), indicating statistically significant *losses*. The PF values (2.39, 2.02, 1.90) are suspiciously high given the low WR. This is a classic sign of a few large wins masking many small losses. The `consensus` cell (conf=C0.60-0.70 & fam=cta & source=cta_replicator) has a holdout PF of 1.893 (n=11), which is promising but the WR is 38.55% — this is a high-variance, low-WR strategy that will bleed in drawdown. **Do not trade.**
- **90d expected P&L (1% risk, $100k):** $-12,000. 2,996 decisive trades, WR=25.37%. P&L = 2996 * (0.2537*1.5 - 0.7463*1.0) * $1,000 = 2996 * (-0.365) * $1,000 = -$1,093,540. **Corrected estimate: -$1,093,540.** This is a catastrophic loss. The class is a money pit.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` = 100. This would effectively kill all FOREX signals. The current gate passes 8,206 out of 16,916 scans (48.5% pass rate), which is far too permissive for a class with no edge.
- **Confidence (1-5):** 1

### CRYPTO
- **Real/noise verdict:** Real edge. Two PROVEN cells with strong statistics:
    - `trust=PROBATION & rr=RR1.5-2.0 & dir=LONG`: n=419, WR_shrunk=61.73%, PF=2.172, holdout PF=6.639 (n=40), WR_z=5.031, Bonferroni pass.
    - `trust=PROBATION & conf=C<0.60 & dir=LONG`: n=458, WR_shrunk=60.04%, PF=2.078, holdout PF=1.673 (n=25), WR_z=4.486, Bonferroni pass.
    - **Suspicious cells:** The `ml` cell (PF=2.48, n=366) fails holdout (holdout PF=1.419, n=6). The `conf=C<0.60 & rr=RR1.0-1.5` cell (PF=2.131, n=331) also fails holdout (holdout PF=0.664, n=26). These are likely overfitted. The PROVEN cells are robust.
- **90d expected P&L (1% risk, $100k):** $120,000. 3,863 decisive trades, WR=48.98%. P&L = 3863 * (0.4898*1.5 - 0.5102*1.0) * $1,000 = 3863 * (0.2245) * $1,000 = $867,000. **Corrected estimate: $867,000.** This is a massive edge. However, the PROVEN cells (n=419 and n=458) represent only ~23% of the decisive trades. If we only trade those cells: P&L = (419+458) * (0.61*1.75 - 0.39*1.0) * $1,000 = 877 * (0.6775) * $1,000 = $594,000. **More realistic estimate: $594,000.**
- **Gate change:** `HC_FILTER_MIN_CONFIDENCE_CRYPTO` = 0.60. The current HC gate (conf>=0.75) is too strict for CRYPTO. The PROVEN edge exists at `conf=C<0.60`. Lowering the confidence threshold to 0.60 would capture the PROVEN cells while still filtering out noise.
- **Confidence (1-5):** 5

### FUTURES
- **Real/noise verdict:** Noise. n_closed=12, too small to draw any conclusion. The 66.67% WR is meaningless.
- **90d expected P&L (1% risk, $100k):** $0. Cannot estimate with n=12.
- **Gate change:** No change. The class has insufficient data.
- **Confidence (1-5):** 1

### BOND
- **Real/noise verdict:** Noise. n_closed=24, WR=25%. No edge.
- **90d expected P&L (1% risk, $100k):** $-1,000. 24 trades, WR=25%. P&L = 24 * (0.25*1.5 - 0.75*1.0) * $1,000 = 24 * (-0.375) * $1,000 = -$9,000. **Corrected estimate: -$9,000.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` = 100. Kill the class.
- **Confidence (1-5):** 1

### ETF
- **Real/noise verdict:** Noise. n_closed=22, WR=9.09%. No edge.
- **90d expected P&L (1% risk, $100k):** $-2,000. 22 trades, WR=9.09%. P&L = 22 * (0.0909*1.5 - 0.9091*1.0) * $1,000 = 22 * (-0.7727) * $1,000 = -$17,000. **Corrected estimate: -$17,000.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` = 100. Kill the class.
- **Confidence (1-5):** 1

### UNKNOWN
- **Real/noise verdict:** Noise. n_closed=3, WR=0%. No edge.
- **90d expected P&L (1% risk, $100k):** $0. Cannot estimate.
- **Gate change:** `SMART_PICKS_MIN_SCORE_UNKNOWN` = 100. Kill the class.
- **Confidence (1-5):** 1

### INDEX
- **Real/noise verdict:** Noise. n_closed=8, too small to draw any conclusion.
- **90d expected P&L (1% risk, $100k):** $0. Cannot estimate.
- **Gate change:** No change. Insufficient data.
- **Confidence (1-5):** 1

### MEME
- **Real/noise verdict:** Noise. n_closed=1, WR=100%. Meaningless.
- **90d expected P&L (1% risk, $100k):** $0. Cannot estimate.
- **Gate change:** No change. Insufficient data.
- **Confidence (1-5):** 1

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY with real money:** **CRYPTO** — specifically the PROVEN LONG cells with `trust=PROBATION` and either `rr=RR1.5-2.0` or `conf=C<0.60`. This is the only class with statistically validated, out-of-sample edge. Start with 0.5% risk per trade (not 1%) to account for slippage and regime change.

**DEMOTE per MUTATION_THREE_AXIS_PROTOCOL (mutate before kill):**
- **FOREX** — **KILL immediately.** The class has 16,916 scans, 8,206 passed smart, and produces a WR of 25.37% with a massive negative expected P&L. This is actively destroying capital. The `consensus` cell is a false positive. Set `SMART_PICKS_MIN_SCORE_FOREX = 100` to kill all signals.
- **COMMODITY** — **MUTATE.** The class has a large sample (n=1,009) but no edge. The current signals are noise. The gate is too loose (6,111 passed smart). Raise the score threshold to 95 and re-evaluate in 30 days. If no PROVEN edges emerge, kill.
- **EQUITY** — **MUTATE.** The class has a very low pass rate (2.2%) and still no edge. The signal generation is broken. Investigate the `multi_asset_copytrader` source — it is producing the only cells with high PF, but they are overfitted. If no improvement in 30 days, kill.
- **All other classes (BOND, ETF, FUTURES, INDEX, MEME, UNKNOWN)** — **KILL.** They have insufficient data or negative edge. They are wasting compute and dashboard space. Set their `SMART_PICKS_MIN_SCORE` to 100.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### CRYPTO
- Real/noise verdict: Both proven cells appear statistically real (n=419/458, WR_shrunk 61.7/60.0, PF>2.0, holdout_pass + bonferroni_pass true, solid WR_z). No obvious leakage flagged.
- 90d expected P&L (1% risk, $100k): $2,840 (419+458 trades at ~1.7% avg edge after 0.15% slippage, 1% risk/trade).
- Gate change: SMART_PICKS_MIN_SCORE_CRYPTO = 72
- Confidence (1-5): 4

### EQUITY
- Real/noise verdict: No proven cells. All best_pf_overall cells fail bonferroni or show train/holdout PF collapse (clear overfitting).
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge).
- Gate change: HC_MIN_TRUST = 70
- Confidence (1-5): 3

### COMMODITY
- Real/noise verdict: No proven cells. All listed cells are noise (WR_shrunk <50, failed holdout, negative WR_z).
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge).
- Gate change: SMART_PICKS_MIN_SCORE_COMMODITY = 85
- Confidence (1-5): 3

### FOREX
- Real/noise verdict: No proven cells. All best_pf_overall cells fail bonferroni or show catastrophic holdout collapse; consensus/ml-style signals already rejected in prior audits.
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge).
- Gate change: HC_MIN_CONF = 0.82
- Confidence (1-5): 3

### INDEX
- Real/noise verdict: No proven cells; n=8 is too small for any conclusion.
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge).
- Gate change: SMART_PICKS_MIN_SCORE_INDEX = 90
- Confidence (1-5): 2

### BOND
- Real/noise verdict: No proven cells; n=24 too small.
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge).
- Gate change: SMART_PICKS_MIN_SCORE_BOND = 90
- Confidence (1-5): 2

### FUTURES
- Real/noise verdict: No proven cells; n=12 too small.
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge).
- Gate change: SMART_PICKS_MIN_SCORE_FUTURES = 90
- Confidence (1-5): 2

### ETF
- Real/noise verdict: No proven cells; n=22 too small.
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge).
- Gate change: SMART_PICKS_MIN_SCORE_ETF = 90
- Confidence (1-5): 2

### UNKNOWN
- Real/noise verdict: No proven cells; n=3 too small.
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge).
- Gate change: SMART_PICKS_MIN_SCORE_UNKNOWN = 90
- Confidence (1-5): 1

### MEME
- Real/noise verdict: No proven cells; n=1 too small.
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge).
- Gate change: SMART_PICKS_MIN_SCORE_MEME = 90
- Confidence (1-5): 1

**SYSTEM-WIDE CONCLUSION**  
Scale CRYPTO today (only class with verified, holdout-passed edges). Demote FOREX and COMMODITY per MUTATION_THREE_AXIS_PROTOCOL.md (mutate filters then kill if no improvement in next 30d window). All other classes have zero usable edge.
