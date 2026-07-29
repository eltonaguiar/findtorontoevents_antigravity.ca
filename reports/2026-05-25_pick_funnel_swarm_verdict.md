# Pick Funnel Swarm Verdict — 2026-07-29 05:05 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260729T050511Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

### CRYPTO
- **Real/noise verdict:** **Real edge** – 319 closed trades, win‑rate ≈ 65 %, Bayesian‑shrunk WR ≈ 64 %, PF ≈ 2.26.  Hold‑out and Bonferroni tests pass, and the sample size is well above the 20‑trade minimum, so the signal looks statistically genuine.  No obvious leakage (the cell does **not** rely on a single symbol or on the “consensus” source that was previously flagged).  
- **90d expected P&L (1 % risk, $100 k):** ≈ **$140 k**  
  - Calculation: L = $1 000 (1 % risk).  Expected net per trade = (1‑WR) × L × (PF‑1) = 0.35 × 1 000 × 1.259 ≈ $441.  $441 × 319 ≈ $140 600.  
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO = 50` (currently 80).  Lowering the minimum score to the S50 decile lets the long‑direction, score‑decile = S50 picks through the high‑conviction filter.  
- **Confidence (1‑5):** **4**  

### EQUITY
- **Real/noise verdict:** **Suspicious – likely sample‑noise / leakage**.  Three “PROVEN” cells each have n ≈ 56‑57 and win‑rates ≈ 98 % with astronomic PF ≈ 150‑160.  Although the hold‑out passes Bonferroni, the tiny sample and the fact that all three cells share the same family/direction/source suggest a single‑symbol concentration or look‑ahead artefact.  The implied expected return (≈ $176 k) is unrealistically high for a $100 k account, signalling probable over‑fit.  
- **90d expected P&L (1 % risk, $100 k):** **≈ $176 k** (if the edge were genuine) – but treat this figure with extreme caution.  
- **Gate change:** `HC_TRUST_THRESHOLD = 0` (in `audit_dashboard/hc_filter.js`).  The proven cells all have `trust=UNK`; lowering the trust‑gate from 60 to 0 would admit these picks, exposing the apparent edge (and also revealing the over‑fit).  
- **Confidence (1‑5):** **3**  

### COMMODITY
- **Real/noise verdict:** **Noise** – No PROVEN cells.  The best PF (≈ 3.9) comes from a 51‑trade cell that fails hold‑out and Bonferroni tests; win‑rate ≈ 53 % and the signal is driven by a single decile (S50).  This is consistent with the previously rejected COT‑positioning hypothesis.  
- **90d expected P&L (1 % risk, $100 k):** **$0** (no statistically‑valid edge).  
- **Gate change:** none (no edge to lift).  
- **Confidence (1‑5):** **1**  

### FOREX
- **Real/noise verdict:** **Noise** – No PROVEN cells.  The highest PF (≈ 6.2) comes from a 121‑trade cell that fails hold‑out (negative Z‑score) and is based on the “consensus” source, which historically exhibited look‑ahead leakage.  Win‑rate ≈ 30 % and the edge is not statistically significant.  
- **90d expected P&L (1 % risk, $100 k):** **$0**.  
- **Gate change:** none.  
- **Confidence (1‑5):** **1**  

### INDEX
- **Real/noise verdict:** **Noise** – Only 7 closed trades total; no PROVEN cells and insufficient data to draw any conclusion.  
- **90d expected P&L (1 % risk, $100 k):** **$0**.  
- **Gate change:** none.  
- **Confidence (1‑5):** **1**  

### FUTURES
- **Real/noise verdict:** **Noise** – No PROVEN cells; the best PF (≈ 1.64) comes from a 21‑trade hold‑out that fails statistical tests (negative Z‑score).  
- **90d expected P&L (1 % risk, $100 k):** **$0**.  
- **Gate change:** none.  
- **Confidence (1‑5):** **1**  

### ETF
- **Real/noise verdict:** **Noise** – No PROVEN cells; only 23 closed trades with a negative PF overall.  
- **90d expected P&L (1 % risk, $100 k):** **$0**.  
- **Gate change:** none.  
- **Confidence (1‑5):** **1**  

### UNKNOWN
- **Real/noise verdict:** **Noise** – 10 closed trades, 0 % win‑rate, no PROVEN cells.  
- **90d expected P&L (1 % risk, $100 k):** **$0**.  
- **Gate change:** none.  
- **Confidence (1‑5):** **1**  

### BOND
- **Real/noise verdict:** **Noise** – No PROVEN cells; best PF is 0.56 with a win‑rate of 15 % and fails hold‑out.  
- **90d expected P&L (1 % risk, $100 k):** **$0**.  
- **Gate change:** none.  
- **Confidence (1‑5):** **1**  

### MEME
- **Real/noise verdict:** **Noise** – Single trade (n = 1) with 100 % win‑rate, but sample size far below the 20‑trade threshold; cannot be considered a reliable edge.  
- **90d expected P&L (1 % risk, $100 k):** **$0**.  
- **Gate change:** none.  
- **Confidence (1‑5):** **1**  

---

## SYSTEM‑WIDE CONCLUSION
- **Scale‑up today:** **CRYPTO** – The long‑direction, score‑decile = S50 edge passes all statistical guards, has a healthy sample size (n = 319), and delivers a realistic profit factor (~2.3).  Adjusting `SMART_PICKS_MIN_SCORE_CRYPTO` to 50 will unlock the edge for live deployment.  
- **Demote / mutate:** **ETF** – Consistently negative PF, zero win‑rate, and no statistically‑valid signal.  According to the *Mutation‑Three‑Axis Protocol*, this class should be moved to the “kill” bucket (gate thresholds tightened or source disabled).  

*All recommendations respect the previously rejected hypotheses; no re‑discovery of those signals is made.*

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

Here is the brutally honest audit of your 90-day pick-funnel, asset class by asset class.

---

### CRYPTO
- **Real/noise verdict:** **Real, but fragile.** The PROVEN cells (`dir=LONG & score_dec=S50 & source=alpha_engine`, n=319, WR_shrunk=64.01%, PF=2.259) pass Bonferroni and holdout. However, the `trust=UNK` variant (n=412, PF=1.85) is weaker. The PF of 2.259 is not suspiciously high for a decent mean-reversion or momentum edge in crypto; it is plausible. No look-ahead or single-symbol concentration flagged (the cell spans many symbols). **Edge is statistically real.**
- **90d expected P&L (1% risk, $100k):** $2,259. *Assumptions:* 319 trades, 1% risk ($1,000/trade), avg win $1,000 * 2.259 = $2,259, avg loss $1,000. WR=64.89% → net = (0.6489 * $2,259) - (0.3511 * $1,000) = $1,465 - $351 = **$1,114 net profit** over 90 days. Slippage: 2bps on crypto (tight), no material impact.
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` = 50 (currently likely lower). This forces the `score_dec=S50` filter upstream, reducing noise from lower-score picks.
- **Confidence (1-5):** 4

### COMMODITY
- **Real/noise verdict:** **Noise.** Zero PROVEN cells. The best PF (3.893) is driven by n=51, WR=52.94%, which fails Bonferroni and holdout. The high PF is a small-sample artifact (few losses, but tiny n). The rejected H-001 (COT look-ahead) and H-036 (inventory) confirm this class has no stable edge. **Do not trade.**
- **90d expected P&L (1% risk, $100k):** $0 (no edge to size). If forced: negative due to 21% WR on decisive trades.
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` = 100 (effectively kill the class in Smart_Picks). Or set `COMMODITY_ENABLED = False` in `production_scanner.py`.
- **Confidence (1-5):** 1

### INDEX
- **Real/noise verdict:** **Noise.** n_closed=7. Zero PROVEN cells. Insufficient data. The 42.86% WR is meaningless. **Do not trade.**
- **90d expected P&L (1% risk, $100k):** $0.
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` = 100 (kill).
- **Confidence (1-5):** 1

### FOREX
- **Real/noise verdict:** **Noise / Anti-edge.** Zero PROVEN cells. The best PF (6.235) is a mirage: WR=29.75%, n=121, fails Bonferroni and holdout. The high PF comes from a few large winners amidst many small losers — classic lottery-ticket distribution. The `rr=RR1.5-2.0 & dir=LONG` cell (n=385, WR=5.19%, PF=5.404) is a statistical disaster (WR_z = -17.585). **This is a losing class. Do not trade.**
- **90d expected P&L (1% risk, $100k):** -$4,455 (based on the WR_z = -17.585 cell: 385 trades, 5.19% WR, avg win $5,404, avg loss $1,000 → net = (0.0519 * $5,404) - (0.9481 * $1,000) = $280 - $948 = -$668 per trade * 385 = -$257k. But you would never size this. Realistic: $0 because you should not trade it.)
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` = 100 (kill). Or set `FOREX_ENABLED = False`.
- **Confidence (1-5):** 1

### EQUITY
- **Real/noise verdict:** **Real, but suspiciously high.** The PROVEN cell (`fam=mean_reversion & dir=LONG & source=alpha_engine`, n=57, WR_shrunk=85.71%, PF=158.089) passes Bonferroni and holdout. However, a PF of 158 is **pathological** for a 90-day sample. This strongly suggests **leakage, look-ahead bias, or single-symbol concentration.** The `trust=UNK` variant (n=56) is identical — likely the same trades. **Flag for immediate investigation.** Do not size until you verify the underlying trades are not all one stock (e.g., TSLA) or using future data.
- **90d expected P&L (1% risk, $100k):** $1,102 (based on avg_pnl_pct=1.1024% per trade, 57 trades, 1% risk = $1,000/trade → $1,102 * 10 = $11,020 gross, but this is likely a data error). Realistic: **$0 until leakage is ruled out.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` = 80 (raise from current lower value to reduce false positives, but the real fix is debugging the 158 PF).
- **Confidence (1-5):** 2 (due to high suspicion of leakage)

### FUTURES
- **Real/noise verdict:** **Noise.** n_closed=24. Zero PROVEN cells. The best cell (n=21, WR=42.86%, PF=1.641) fails holdout. Rejected H-005 confirms no edge. **Do not trade.**
- **90d expected P&L (1% risk, $100k):** $0.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` = 100 (kill).
- **Confidence (1-5):** 1

### ETF
- **Real/noise verdict:** **Noise.** n_closed=23. Zero PROVEN cells. WR=8.7% on decisive trades. **Do not trade.**
- **90d expected P&L (1% risk, $100k):** $0.
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` = 100 (kill).
- **Confidence (1-5):** 1

### UNKNOWN
- **Real/noise verdict:** **Noise.** n_closed=10. Zero PROVEN cells. 0% WR. **Do not trade.**
- **90d expected P&L (1% risk, $100k):** $0.
- **Gate change:** `SMART_PICKS_MIN_SCORE_UNKNOWN` = 100 (kill).
- **Confidence (1-5):** 1

### BOND
- **Real/noise verdict:** **Noise.** n_closed=31. Zero PROVEN cells. Best cell (n=20, WR=15%, PF=0.557) is negative expectancy. **Do not trade.**
- **90d expected P&L (1% risk, $100k):** $0.
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` = 100 (kill).
- **Confidence (1-5):** 1

### MEME
- **Real/noise verdict:** **Noise.** n_closed=1. Zero PROVEN cells. **Do not trade.**
- **90d expected P&L (1% risk, $100k):** $0.
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME` = 100 (kill).
- **Confidence (1-5):** 1

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY with real money:** **CRYPTO** (LONG, score_dec=S50, alpha_engine). It is the only class with a statistically real, Bonferroni-passing, holdout-passing edge with sufficient sample size (n=319). Use 1% risk per trade, $100k notional.

**DEMOTE per MUTATION_THREE_AXIS_PROTOCOL:** **COMMODITY, FOREX, INDEX, FUTURES, ETF, UNKNOWN, BOND, MEME.** All eight classes have zero PROVEN edges. They are consuming scan capacity and generating noise. Per the protocol, mutate (e.g., disable Smart_Picks scoring for these classes) before kill. Set `SMART_PICKS_MIN_SCORE_*` to 100 for each.

**EQUITY** is a **HOLD / INVESTIGATE** — the PF of 158 is a red flag for leakage. Do not size until you audit the 57 trades for single-symbol concentration or timestamp look-ahead. If clean, it is the strongest edge in the system. If dirty, demote to kill.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

**### EQUITY**
- Real/noise verdict: Noise/leakage. 98% WR and PF>150 on n=57 with train/holdout split is statistically impossible in live mean-reversion without single-symbol concentration or look-ahead; violates every realistic market regime.
- 90d expected P&L (1% risk, $100k): $0 (edge is spurious; any forward deployment will revert to ~45% WR and negative expectancy).
- Gate change: SMART_PICKS_MIN_SCORE_EQUITY = 92 (or disable mean_reversion LONG entirely for EQUITY).
- Confidence (1-5): 5

**### CRYPTO**
- Real/noise verdict: Real. n=319, WR_shrunk=64%, PF=2.26, holdout_pass=true, bonferroni_pass=true; the only cell that survives all filters without obvious leakage.
- 90d expected P&L (1% risk, $100k): ~$4,800 (assume ~3.5 trades/week at 1% risk, 0.98% avg win size, 0.4% slippage/commissions, PF decay to 1.9 in live).
- Gate change: passed_high_conviction threshold in hc_filter.js = 78 (currently 80) to capture more of the S50 LONG alpha_engine flow.
- Confidence (1-5): 4

**### COMMODITY**
- Real/noise verdict: Noise. No proven cells; best_pf_overall cells fail holdout and bonferroni; matches previously rejected COT/inventory hypotheses.
- 90d expected P&L (1% risk, $100k): $0 (or negative after slippage).
- Gate change: SMART_PICKS_MIN_SCORE_COMMODITY = 95 (effectively disable).
- Confidence (1-5): 5

**### FOREX**
- Real/noise verdict: Noise. All high-PF cells fail holdout and show negative WR_z; classic multi_asset_copytrader consensus leakage pattern.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: passed_verified_alpha minimum in quality_gates.py = 25 (currently too permissive).
- Confidence (1-5): 5

**### INDEX / FUTURES / BOND / ETF / UNKNOWN / MEME**
- Real/noise verdict: Noise. n_closed too low or no cells meet PROVEN criteria; all best_pf_overall fail holdout/bonferroni.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: passed_high_conviction threshold in hc_filter.js = 85 (stricter across non-CRYPTO).
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale CRYPTO only (the single surviving edge). Demote every other class per MUTATION_THREE_AXIS_PROTOCOL.md — they have zero validated edge and should be mutated (score floors raised or families disabled) before any further capital allocation.
