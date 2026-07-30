# Pick Funnel Swarm Verdict — 2026-07-30 05:03 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260730T050244Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

**90‑day edge audit – pick‑funnel verdict**

---

### CRYPTO
- **Real/noise verdict:** **Real edge** – two “PROVEN” cells (n = 325 & 420) both have WR ≈ 64 % (shrunk ≈ 63 %), PF > 1.7, hold‑out and Bonferroni passes. No obvious look‑ahead or single‑symbol concentration; the signal is driven by the `score_dec=S50` decile from the Alpha Engine, which is a genuine model output.
- **90d expected P&L (1 % risk, $100 k):** **≈ $130 k** profit.  
  *How:* avg P&L ≈ 0.94 % per trade; with a 1 % max‑loss risk the position size is ≈ 0.43 × account, giving ≈ 0.41 % expected return per trade. 325 trades × 0.41 % ≈ 132 % of capital → $132 k (rounded to $130 k to allow for slippage & execution cost).  
- **Gate change:** `HC_SCORE_MIN_CRYPTO` (in `audit_dashboard/hc_filter.js`) → **50** (instead of the default 80). This opens the S50 decile that contains the proven edge.  
- **Confidence (1‑5):** **4**

---

### FOREX
- **Real/noise verdict:** **Noise** – no “PROVEN” cells. The highest PF (≈ 6.2) comes from a confidence band `C0.75‑0.80` but the hold‑out fails, WR‑shrunk ≈ 33 % and Z‑scores are strongly negative. The apparent PF is driven by a few large winners; the signal does not survive out‑of‑sample testing.
- **90d expected P&L (1 % risk, $100 k):** **$0** (no statistically reliable edge to size).
- **Gate change:** *None recommended* – lowering the confidence or score thresholds would only admit more noisy picks.
- **Confidence (1‑5):** **2**

---

### BOND
- **Real/noise verdict:** **Noise** – no “PROVEN” cells. PF ≤ 0.52, hold‑out fails, WR‑shrunk ≈ 30 % (negative Z). The few wins are outweighed by losses; the edge is not statistically significant.
- **90d expected P&L (1 % risk, $100 k):** **$0**
- **Gate change:** *None recommended*.
- **Confidence (1‑5):** **2**

---

### EQUITY
- **Real/noise verdict:** **Real edge** – three “PROVEN” cells (n ≈ 56‑57) with WR ≈ 98 % (shrunk ≈ 86 %), PF ≈ 158, hold‑out and Bonferroni passes. The signal is the `fam=mean_reversion` family from the Alpha Engine, long direction only. The extremely high PF is supported by a very low loss rate (≈ 1.75 % of trades) and modest average loss (~0.40 % of position), so the edge survives out‑of‑sample.
- **90d expected P&L (1 % risk, $100 k):** **≈ $155 k** profit.  
  *How:* avg P&L ≈ 1.10 % per trade; with a 1 % max‑loss risk the position size is ≈ 2.5 × account (≈ 2.5 % of capital per trade). Expected return per trade ≈ 2.75 % of capital. 57 trades × 2.75 % ≈ 156 % of capital → $156 k (rounded to $155 k to allow for execution frictions).
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` (in `audit_trail/quality_gates.py`) → **50** (instead of the current higher threshold). This admits the S50 decile where the mean‑reversion edge lives.
- **Confidence (1‑5):** **4**

---

### COMMODITY
- **Real/noise verdict:** **Noise** – no “PROVEN” cells. Best PF ≈ 3.9 but hold‑out fails, WR‑shrunk ≈ 52 % with a non‑significant Z‑score. The signal does not survive statistical testing.
- **90d expected P&L (1 % risk, $100 k):** **$0**
- **Gate change:** *None recommended*.
- **Confidence (1‑5):** **2**

---

### INDEX
- **Real/noise verdict:** **Noise** – only 7 closed trades, no proven cells, insufficient data.
- **90d expected P&L (1 % risk, $100 k):** **$0**
- **Gate change:** *None recommended*.
- **Confidence (1‑5):** **1**

---

### FUTURES
- **Real/noise verdict:** **Noise** – no “PROVEN” cells; best PF ≈ 1.64 but hold‑out fails, WR‑shrunk ≈ 46 % with negative Z. Edge does not hold out‑of‑sample.
- **90d expected P&L (1 % risk, $100 k):** **$0**
- **Gate change:** *None recommended*.
- **Confidence (1‑5):** **2**

---

### UNKNOWN
- **Real/noise verdict:** **Noise** – only 10 closed trades, no proven cells, WR = 0 %.
- **90d expected P&L (1 % risk, $100 k):** **$0**
- **Gate change:** *None recommended*.
- **Confidence (1‑5):** **1**

---

### ETF
- **Real/noise verdict:** **Noise** – 23 closed trades, no proven cells, WR ≈ 8.7 %, PF ≈ 0.0.
- **90d expected P&L (1 % risk, $100 k):** **$0**
- **Gate change:** *None recommended*.
- **Confidence (1‑5):** **1**

---

### MEME
- **Real/noise verdict:** **Noise** – single trade, cannot assess statistically.
- **90d expected P&L (1 % risk, $100 k):** **$0**
- **Gate change:** *None recommended*.
- **Confidence (1‑5):** **1**

---

## SYSTEM‑WIDE Conclusion

**Scale‑up

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

Here is the brutally honest, edge-by-edge verdict on the 90-day pick funnel for `findtorontoevents.ca`.

### CRYPTO
- **Real/noise verdict:** **Real, but fragile.** The two PROVEN cells (`dir=LONG & score_dec=S50 & source=alpha_engine` and `trust=UNK & dir=LONG & score_dec=S50`) are statistically robust (n=325–420, WR_shrunk ~63–64%, PF >1.7, Bonferroni pass). However, the `best_pf_overall` list shows that adding the `trust=UNK` dimension *fails* holdout validation (PF drops from 2.479 to 2.052). This suggests the edge is concentrated in the `alpha_engine` source, not in the `trust` band. The high PF (2.15) is suspiciously good for a 90-day sample; check for single-symbol concentration (e.g., BTC perpetuals) or stale price data. **No leakage detected**, but the edge is narrow.
- **90d expected P&L (1% risk, $100k):** $2,151. Assumptions: 325 trades, 1% risk per trade ($1,000), average win $2,151 (PF=2.151), average loss $1,000. Slippage: 0.05% per trade ($50). Net: $2,151 - $16,250 (slippage) = **-$14,099** (slippage kills this edge at 1% risk).
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` = 50 (currently likely lower). This forces all CRYPTO picks to pass the S50 score threshold, which is the core of the proven edge.
- **Confidence (1-5):** 3

### FOREX
- **Real/noise verdict:** **Noise.** Zero PROVEN edges. The `best_pf_overall` cells show PF >5.0 but with WR <30% and negative Z-scores (e.g., Z=-17.15). This is a classic **high-PF, low-WR trap** — a few massive winners mask a sea of losers. The `multi_asset_copytrader` source is likely picking up a single lucky outlier trade. The holdout validation fails on every cell. **Do not trade.**
- **90d expected P&L (1% risk, $100k):** -$5,490. Assumptions: 1,082 trades, 1% risk, WR=23.38%, PF=0.30 (implied from WR/PF). Slippage: 0.02% ($20). Net: -$5,490.
- **Gate change:** `HC_FILTER_MIN_CONFIDENCE_FOREX` = 0.85 (raise from 0.75). This would kill the `C0.75-0.80` band that is producing the false high-PF signals.
- **Confidence (1-5):** 1

### EQUITY
- **Real/noise verdict:** **Real, but likely overfitted.** The PROVEN cells (`fam=mean_reversion & dir=LONG & source=alpha_engine`) show WR_shrunk=85.71%, PF=158.089, n=57. This is **too good to be true**. A PF of 158 implies a single loss of $1,000 and 57 wins averaging $158,000 each. This is almost certainly a **single-symbol concentration** (e.g., a penny stock or a single mean-reversion event on a low-liquidity ticker). The holdout PF (117.275) confirms the pattern persists, but the train_n=17 is tiny. **Flag for manual review of the underlying symbols.**
- **90d expected P&L (1% risk, $100k):** $158,089. Assumptions: 57 trades, 1% risk, PF=158.089. Slippage: 0.1% ($100). Net: $158,089 - $5,700 = **$152,389**. (This is unrealistic; real-world slippage on a single-symbol concentration would be catastrophic.)
- **Gate change:** `SMART_PICKS_MIN_TRUST_EQUITY` = 60 (raise from current). This would force the `trust=UNK` band to be excluded, which is the only dimension that fails holdout in the top cells.
- **Confidence (1-5):** 2 (highly suspicious)

### COMMODITY
- **Real/noise verdict:** **Noise.** Zero PROVEN edges. The `best_pf_overall` cells show PF=3.893 but WR=52.94% and Z=0.42 (not significant). The train_n=5 is laughably small. This is a **sample-noise artifact**. The rejected hypothesis H-001 (COT look-ahead) and H-036 (inventory direction) confirm the asset class has no stable edge.
- **90d expected P&L (1% risk, $100k):** -$2,610. Assumptions: 522 trades, 1% risk, WR=21.07%, PF=0.27. Slippage: 0.03% ($30). Net: -$2,610.
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` = 70 (raise from current). This would kill the S50 band that is producing the false positive.
- **Confidence (1-5):** 1

### INDEX
- **Real/noise verdict:** **Noise.** Only 7 closed trades. Zero PROVEN edges. The WR=42.86% is meaningless. **Do not trade.**
- **90d expected P&L (1% risk, $100k):** -$70. Assumptions: 7 trades, 1% risk, WR=42.86%, PF=0.75. Slippage: 0.01% ($10). Net: -$70.
- **Gate change:** `HC_FILTER_MIN_TRUST_INDEX` = 80 (raise from current). This would kill all INDEX picks until trust is established.
- **Confidence (1-5):** 1

### FUTURES
- **Real/noise verdict:** **Noise.** Only 24 closed trades. Zero PROVEN edges. The `best_pf_overall` cell shows PF=1.641 but WR=42.86% and Z=-0.654. The holdout PF (0.326) fails. Rejected hypothesis H-005 confirms futures momentum is dead.
- **90d expected P&L (1% risk, $100k):** -$240. Assumptions: 24 trades, 1% risk, WR=45.83%, PF=0.85. Slippage: 0.05% ($50). Net: -$240.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` = 60 (raise from current). This would kill the S50 band.
- **Confidence (1-5):** 1

### BOND
- **Real/noise verdict:** **Noise.** Only 33 closed trades. Zero PROVEN edges. The `best_pf_overall` cells show negative PF and negative Z-scores. **Do not trade.**
- **90d expected P&L (1% risk, $100k):** -$330. Assumptions: 33 trades, 1% risk, WR=15.15%, PF=0.18. Slippage: 0.02% ($20). Net: -$330.
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` = 80 (raise from current). This would kill all BOND picks.
- **Confidence (1-5):** 1

### ETF
- **Real/noise verdict:** **Noise.** Only 23 closed trades. Zero PROVEN edges. WR=8.7%. **Do not trade.**
- **90d expected P&L (1% risk, $100k):** -$230. Assumptions: 23 trades, 1% risk, WR=8.7%, PF=0.10. Slippage: 0.01% ($10). Net: -$230.
- **Gate change:** `HC_FILTER_MIN_CONFIDENCE_ETF` = 0.90 (raise from current). This would kill all ETF picks.
- **Confidence (1-5):** 1

### UNKNOWN
- **Real/noise verdict:** **Noise.** Only 10 closed trades. WR=0%. **Do not trade.**
- **90d expected P&L (1% risk, $100k):** -$100. Assumptions: 10 trades, 1% risk, WR=0%, PF=0.0. Slippage: 0.01% ($10). Net: -$100.
- **Gate change:** `SMART_PICKS_MIN_SCORE_UNKNOWN` = 100 (effectively kill the class).
- **Confidence (1-5):** 1

### MEME
- **Real/noise verdict:** **Noise.** Only 1 closed trade. WR=100% is meaningless. **Do not trade.**
- **90d expected P&L (1% risk, $100k):** $0. Assumptions: 1 trade, 1% risk, WR=100%, PF=∞. Slippage: 0.1% ($100). Net: $0.
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME` = 100 (effectively kill the class).
- **Confidence (1-5):** 1

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY:** **CRYPTO** (with caution). It is the only asset class with statistically validated, holdout-passing edges. However, the edge is narrow (S50, LONG, alpha_engine) and slippage-sensitive. Use 0.5% risk per trade, not 1%.

**DEMOTE per MUTATION_THREE_AXIS_PROTOCOL:** **FOREX**, **COMMODITY**, **BOND**, **ETF**, **INDEX**, **FUTURES**, **UNKNOWN**, **MEME**. These classes have zero proven edges, negative expected P&L, and confirmed rejected hypotheses. They should be **mutated** (e.g., switch to a completely different signal family) or **killed** (removed from the pick funnel entirely). The `multi_asset_copytrader` source in FOREX is particularly dangerous — it produces high-PF illusions that will blow up an account.

**EQUITY** is a **watchlist item**. The PF=158 is a red flag for overfitting or single-symbol concentration. Do not scale until the underlying symbols are manually reviewed. If it's a single ticker, kill it.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### CRYPTO
- Real/noise verdict: Real. n=325/420 solid, WR_shrunk 62.95-63.77, PF 1.77-2.15, holdout_pass + bonferroni_pass true on multiple cells. No obvious leakage flags.
- 90d expected P&L (1% risk, $100k): $2,800 (uses observed avg_pnl_pct 0.67-0.94 on ~300 decisive trades from proven cells; 0.2% slippage + 0.1% commission per side baked in).
- Gate change: SMART_PICKS_MIN_SCORE_CRYPTO = 50
- Confidence (1-5): 4

### COMMODITY
- Real/noise verdict: Noise. No proven cells; best_pf cells show WR_shrunk ~52, PF inflated by tiny train_n=5, holdout_pass false, bonferroni false. Matches known COT leakage patterns.
- 90d expected P&L (1% risk, $100k): -$1,100 (negative expectancy after costs on 522 closed trades).
- Gate change: SMART_PICKS_MIN_TRUST_COMMODITY = 70
- Confidence (1-5): 5

### EQUITY
- Real/noise verdict: Noise. 98% WR / PF 158 on n=57 is statistically impossible without single-symbol concentration or look-ahead; holdout numbers still unrealistic.
- 90d expected P&L (1% risk, $100k): $0 (edge is artifact, not tradable).
- Gate change: ALPHA_ENGINE_MIN_MEAN_REV_WR = 65
- Confidence (1-5): 5

### INDEX
- Real/noise verdict: Noise. n_closed=7, no proven cells, empty best_pf.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: None (no edge exists)
- Confidence (1-5): 5

### FOREX
- Real/noise verdict: Noise. No proven cells; best_pf shows WR 5-30%, negative wr_z, holdout_pass false, bonferroni false. PF numbers are artifacts of low-win regimes.
- 90d expected P&L (1% risk, $100k): -$4,200 (negative expectancy on 1082 decisive trades).
- Gate change: HC_FILTER_MIN_CONF_FOREX = 0.82
- Confidence (1-5): 5

### ETF
- Real/noise verdict: Noise. n_closed=23, no proven cells, empty best_pf.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: None (no edge exists)
- Confidence (1-5): 5

### UNKNOWN
- Real/noise verdict: Noise. n_closed=10, no proven cells, empty best_pf.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: None (no edge exists)
- Confidence (1-5): 5

### FUTURES
- Real/noise verdict: Noise. n_closed=24, no proven cells; single best_pf cell fails holdout and bonferroni.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: None (no edge exists)
- Confidence (1-5): 5

### BOND
- Real/noise verdict: Noise. n_closed=33, no proven cells; best_pf cells show negative expectancy and failed stats.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: None (no edge exists)
- Confidence (1-5): 5

### MEME
- Real/noise verdict: Noise. n_closed=1, no proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: None (no edge exists)
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale up CRYPTO today (only class with multiple holdout-passed, bonferroni-passed proven cells). Demote EQUITY immediately (suspicious 98% WR cells are leakage recurrence) and COMMODITY (known COT-style failures). All other classes have zero usable edge.
