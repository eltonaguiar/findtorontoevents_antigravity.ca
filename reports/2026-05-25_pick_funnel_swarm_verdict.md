# Pick Funnel Swarm Verdict — 2026-07-26 05:08 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260726T050838Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

### CRYPTO
- **Real/noise verdict:** **Real** – The two “PROVEN” cells each have n ≈ 300‑400 closed trades, Bayesian‑shrunk win‑rate ≈ 63 % (well above the 55 % threshold), profit‑factor ≈ 2.0 + and both **hold‑out** and **Bonferroni** tests pass. No obvious single‑symbol concentration is visible in the dump, and the signal comes from the core `alpha_engine` (no external data leakage).  
- **90d expected P&L (1 % risk, $100 k):**  
  *Assumptions*: 1 % risk = $1 000 max loss per trade, slippage ≈ 0.05 % per trade (≈ $50).  
  Expected net per trade = (1‑WR) × (PF‑1) × 1 % ≈ 0.358 × 1.204 % ≈ 0.431 % → $4.31 per $1 000 risk.  
  With 310 closed trades → **$133 600 gross**, minus $15 500 slippage ≈ **$118 000 net**.  
- **Gate change:** lower the client‑side trust threshold in `audit_dashboard/hc_filter.js`  
  ```js
  const TRUST_MIN = 30;   // from 60 → 30
  ```  
  This admits the “trust=UNK” edge cells that currently sit below the HC gate, unlocking the bulk of the proven CRYPTO edge.  
- **Confidence (1‑5):** **4**

### EQUITY
- **Real/noise verdict:** **Real but fragile** – The “PROVEN” cells have an astronomical profit‑factor ≈ 147 and win‑rate ≈ 98 % with **hold‑out** and **Bonferroni** passes, but the sample is tiny (n ≈ 53). The extreme PF suggests possible concentration on a handful of symbols or a regime that may not persist; flag for **single‑symbol concentration** risk.  
- **90d expected P&L (1 % risk, $100 k):**  
  *Assumptions*: 1 % risk = $1 000 loss per trade, slippage ≈ 0.10 % per trade ($100).  
  Expected net per trade = (1‑WR) × (PF‑1) × 1 % ≈ 0.0189 × 146.288 % ≈ 2.764 % → $27.64 per $1 000 risk.  
  With 53 closed trades → **$146 500 gross**, minus $5 300 slippage ≈ **$141 200 net**.  
- **Gate change:** relax the confidence gate in `audit_dashboard/hc_filter.js` to let more EQUITY picks through:  
  ```js
  const CONF_MIN = 0.70;   // from 0.75 → 0.70
  ```  
  This will admit the mean‑reversion edge (which currently sits just below the 0.75 confidence cut).  
- **Confidence (1‑5):** **3**

### COMMODITY
- **Real/noise verdict:** **Noise** – No cell meets the “PROVEN” criteria; the best PF (≈ 3.0) fails hold‑out and Bonferroni tests, and win‑rates hover around 45‑50 %. Likely over‑fitting or data leakage (the earlier rejected COT‑positioning hypothesis is a reminder).  
- **90d expected P&L (1 % risk, $100 k):** **$0** (no statistically reliable edge).  
- **Gate change:** none – keep current thresholds; lowering them would only admit more noisy signals.  
- **Confidence (1‑5):** **1**

### INDEX
- **Real/noise verdict:** **Noise** – Only 7 closed trades total, no proven edge, win‑rate ≈ 43 %, PF ≈ 1.0. Sample too thin to be actionable.  
- **90d expected P&L (1 % risk, $100 k):** **$0**.  
- **Gate change:** none.  
- **Confidence (1‑5):** **1**

### FOREX
- **Real/noise verdict:** **Noise** – Highest PF (≈ 6.2) still fails hold‑out and Bonferroni; win‑rates 19‑28 % and the cells rely on a “consensus” source that previously showed leakage. The edge is not statistically robust.  
- **90d expected P&L (1 % risk, $100 k):** **$0**.  
- **Gate change:** none – tightening the confidence/trust gates would avoid the spurious consensus signal.  
- **Confidence (1‑5):** **1**

### FUTURES
- **Real/noise verdict:** **Noise** – Only 24 closed trades, PF ≈ 1.6, hold‑out fails. No statistically reliable edge.  
- **90d expected P&L (1 % risk, $100 k):** **$0**.  
- **Gate change:** none.  
- **Confidence (1‑5):** **1**

### BOND
- **Real/noise verdict:** **Noise** – PF < 1, win‑rate ≈ 15 %, hold‑out fails. No edge.  
- **90d expected P&L (1 % risk, $100 k):** **$0**.  
- **Gate change:** none.  
- **Confidence (1‑5):** **1**

### ETF
- **Real/noise verdict:** **Noise** – No proven cells, PF ≈ 0, win‑rate ≈ 9 %.  
- **90d expected P&L (1 % risk, $100 k):** **$0**.  
- **Gate change:** none.  
- **Confidence (1‑5):** **1**

### UNKNOWN
- **Real/noise verdict:** **Noise** – Only 10 closed trades, 0 % win‑rate, PF = 0.  
- **90d expected P&L (1 % risk, $100 k):** **$0**.  
- **Gate change:** none.  
- **Confidence (1‑5):** **1**

### MEME
- **Real/noise verdict:** **Noise** – Single trade (n = 1) with 100 % win‑rate, but no statistical power; cannot be used as an edge.  
- **90d expected P&L (1 % risk, $100 k):** **$0**.  
- **Gate change:** none.  
- **Confidence (1‑5):** **1**

---

## SYSTEM‑WIDE CONCLUSION
- **Scale‑up today:** **CRYPTO** – The most robust, statistically‑validated edge with a healthy sample size, solid PF, and a clear gate tweak that can immediately increase signal flow. Deploy the lowered trust threshold (`TRUST_MIN = 30`) and allocate capital (e.g., 30 % of the $100 k account) to the `alpha_engine` long picks in the S50 decile band.  
- **Demote / kill:** **EQUITY** – Although the mean‑reversion edge looks spectacular, its tiny sample (≈ 50 trades) and extreme PF raise red flags for over‑fitting and concentration. Until the sample expands and the edge is validated across multiple walk‑forward windows, pull EQUITY from the live pick funnel per the **MUTATION_THREE_AXIS_PROTOCOL** (move to “hold” status).  

All other asset classes should remain at current gate settings (or be tightened) because they show no statistically reliable edge over the past 90 days.

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

**### CRYPTO**
- Real/noise verdict: Real. Two cells show n=310-403, WR_shrunk 62.9-63.3%, PF 1.8-2.2, holdout_pass true, bonferroni true, positive wr_z. No obvious single-symbol concentration.
- 90d expected P&L (1% risk, $100k): $2,800 (uses avg_pnl_pct 0.69-0.96, ~300-400 trades, 0.4% net per trade after 0.15% slippage + 0.05% commission).
- Gate change: SMART_PICKS_MIN_SCORE_CRYPTO = 55
- Confidence (1-5): 4

**### EQUITY**
- Real/noise verdict: Noise/leakage. 98% WR and PF 147 on n=53 (train_n=17) is statistically impossible without single-symbol concentration or look-ahead. Rejected.
- 90d expected P&L (1% risk, $100k): $0 (edge is falsified).
- Gate change: SMART_PICKS_MIN_TRADES_EQUITY = 120
- Confidence (1-5): 5

**### COMMODITY**
- Real/noise verdict: Noise. No proven cells. Best PF cells have WR<47%, holdout_pass false, bonferroni false.
- 90d expected P&L (1% risk, $100k): -$1,900 (negative expectancy after costs).
- Gate change: SMART_PICKS_MIN_SCORE_COMMODITY = 70
- Confidence (1-5): 4

**### INDEX**
- Real/noise verdict: Noise. n_closed=7, no proven cells, empty best_pf.
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: SMART_PICKS_MIN_SCORE_INDEX = 75
- Confidence (1-5): 5

**### FOREX**
- Real/noise verdict: Noise. High PF driven by tiny wins + large losers; WR 5-28%, holdout_pass false, bonferroni false across all cells. Matches known rejected patterns.
- 90d expected P&L (1% risk, $100k): -$4,800 (strongly negative).
- Gate change: HC_FILTER_MIN_CONF = 0.82
- Confidence (1-5): 4

**### BOND**
- Real/noise verdict: Noise. n=31, all cells PF<0.6, WR<15%, holdout false.
- 90d expected P&L (1% risk, $100k): -$1,100.
- Gate change: SMART_PICKS_MIN_SCORE_BOND = 80
- Confidence (1-5): 5

**### ETF**
- Real/noise verdict: Noise. n=23, no proven cells, empty best_pf.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: SMART_PICKS_MIN_SCORE_ETF = 75
- Confidence (1-5): 5

**### FUTURES**
- Real/noise verdict: Noise. n=24, only one cell, holdout_pf 0.326, bonferroni false.
- 90d expected P&L (1% risk, $100k): -$400.
- Gate change: SMART_PICKS_MIN_SCORE_FUTURES = 70
- Confidence (1-5): 4

**### UNKNOWN / MEME**
- Real/noise verdict: Noise. n<=10, no proven cells.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: SMART_PICKS_MIN_SCORE_UNKNOWN = 80
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale CRYPTO today (only class with statistically credible, holdout-validated edges). Demote FOREX and COMMODITY per MUTATION_THREE_AXIS_PROTOCOL (mutate gates first, then kill flow if no improvement in 30 days). All other classes have zero usable edge.
