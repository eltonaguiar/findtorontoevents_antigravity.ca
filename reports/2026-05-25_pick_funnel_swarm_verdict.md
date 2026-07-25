# Pick Funnel Swarm Verdict — 2026-07-25 05:03 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260725T050342Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

### CRYPTO
- **Real/noise verdict:** **Real** – 301 closed trades, WR shrunk = 63.86 % (well above the 55 % PROVEN floor), PF = 2.26, Bonferroni‑adjusted p‑value < 0.05. No obvious look‑ahead or single‑symbol concentration; the hold‑out set (204 trades) also passes.
- **90d expected P&L (1 % risk, $100 k):**  
  Expected net per trade = (Win % × PF − Loss % ) × 1 % = (0.638 × 2.26 − 0.362) × 1 % ≈ 1.08 % of account.  
  301 trades × 1.08 % × $100 k ≈ **$324 k** (≈ 3.2 × account size).  
  *Assumptions:* 1 % risk per trade, no position‑size scaling, slippage = 0.05 % of notional, execution at mid‑price.
- **Gate change:** lower the HC filter score cut‑off so the S50 cells are admitted.  
  `hc_filter.js` → `const MIN_SCORE = 80;` → **`MIN_SCORE = 50`**.
- **Confidence (1‑5):** **4** – strong statistical backing, but still monitor for regime shift.

### COMMODITY
- **Real/noise verdict:** **Noise** – no PROVEN cells; the highest‑PF cell (PF ≈ 2.93) fails the hold‑out test (WR z = ‑0.717) and is driven by a handful of cotton‑type contracts (see rejected H‑001). Likely sample‑noise/leakage.
- **90d expected P&L (1 % risk, $100 k):** **≈ $0** – no reliable edge to monetize.
- **Gate change:** tighten the smart‑pick score floor to cut low‑quality signals.  
  `quality_gates.py` → `SMART_PICKS_MIN_SCORE_COMMODITY = 60;` → **`= 70`**.
- **Confidence (1‑5):** **2** – data suggest the apparent edge evaporates in out‑of‑sample.

### INDEX
- **Real/noise verdict:** **Noise** – only 7 closed trades, no PROVEN cells, win‑rate ≈ 43 % (below the 55 % PROVEN threshold). Sample too small to claim an edge.
- **90d expected P&L (1 % risk, $100 k):** **≈ $0**.
- **Gate change:** raise the smart‑pick score requirement to reduce spurious picks.  
  `quality_gates.py` → `SMART_PICKS_MIN_SCORE_INDEX = 65;` → **`= 80`**.
- **Confidence (1‑5):** **1** – insufficient data.

### FOREX
- **Real/noise verdict:** **Noise** – best PF cells (PF ≈ 6.2) have very low win‑rates (≈ 20‑30 %) and fail the hold‑out WR test (negative Z‑scores). The “consensus” source appears to be a copy‑trader with poor risk‑adjusted performance.
- **90d expected P&L (1 % risk, $100 k):** **≈ $0**.
- **Gate change:** lower the confidence threshold to admit more trades (may reveal a true edge if the current filter is discarding useful signals).  
  `hc_filter.js` → `const MIN_CONF = 0.75;` → **`= 0.70`**.
- **Confidence (1‑5):** **2** – current metrics indicate a weak, noisy signal.

### ETF
- **Real/noise verdict:** **Noise** – 23 closed trades, no PROVEN cells, win‑rate 8.7 % (far below 55 %). PF not reported (likely < 1). No actionable edge.
- **90d expected P&L (1 % risk, $100 k):** **≈ $0**.
- **Gate change:** increase the smart‑pick score floor to prune low‑quality ETF ideas.  
  `quality_gates.py` → `SMART_PICKS_MIN_SCORE_ETF = 55;` → **`= 80`**.
- **Confidence (1‑5):** **1**.

### UNKNOWN
- **Real/noise verdict:** **Noise** – only 10 closed trades, 0 % win‑rate, no PROVEN cells. Likely filler category.
- **90d expected P&L (1 % risk, $100 k):** **≈ $0**.
- **Gate change:** raise the trust threshold to exclude “UNK” trust altogether.  
  `hc_filter.js` → `const MIN_TRUST = 60;` → **`= 80`**.
- **Confidence (1‑5):** **1**.

### EQUITY
- **Real/noise verdict:** **Likely Leakage / Over‑fit** – 50‑trade “mean‑reversion LONG” cell shows 100 % win‑rate and PF = 99, which is implausibly high even after Bayesian shrinkage (WR shrunk = 85.7 %). The hold‑out set is tiny (33 trades) and the extreme PF suggests a single‑symbol or data‑leakage effect (e.g., a one‑off rally). Treat as noise until the concentration is verified.
- **90d expected P&L (1 % risk, $100 k):** **Not trustworthy** – theoretical calculation would be > $3 M, but the signal is almost certainly spurious.
- **Gate change:** tighten the trust requirement to filter out “UNK” trust, which is where the suspicious cell lives.  
  `hc_filter.js` → `const MIN_TRUST = 60;` → **`= 80`**.
- **Confidence (1‑5):** **2** – statistical flags (Bonferroni pass) are outweighed by implausible magnitude and possible concentration.

### BOND
- **Real/noise verdict:** **Noise** – no PROVEN cells; best PF ≈ 0.56 with negative WR Z‑scores, and win‑rate ≈ 13 %. The signal is weak and loss‑heavy.
- **90d expected P&L (1 % risk, $100 k):** **≈ $0**.
- **Gate change:** raise the trust threshold (currently UNK) to eliminate low‑confidence bond picks.  
  `hc_filter.js` → `const MIN_TRUST = 60;` → **`= 80`**.
- **Confidence (1‑5):** **1**.

### FUTURES
- **Real/noise verdict:** **Noise** – only 24 closed trades, PF ≈ 1.64, win‑rate ≈ 43 %, hold‑out PF fails. No PROVEN cells; likely random variation.
- **90d expected P&L (1 % risk, $100 k):** **≈ $0**.
- **Gate change:** raise the smart‑pick score floor to prune marginal futures ideas.  
  `quality_gates.py` → `SMART_PICKS_MIN_SCORE_FUTURES = 55;` → **`= 70`**.
- **Confidence (1‑5):** **1**.

### MEME
- **Real/noise verdict:** **Noise** – single closed trade (win), but n = 1 is far below any statistical threshold. No edge.
- **90d expected P&L (1 % risk, $100 k):** **≈ $0**.
- **Gate change:** disable the MEME class entirely (set `ENABLE_MEME = False` in `quality_gates.py`).
- **Confidence (1‑5):** **1**.

---

## SYSTEM‑WIDE Conclusion
- **Scale‑up today:** **CRYPTO** – the only class with a statistically robust, out‑of‑sample‑validated edge (PF ≈ 2.3, WR ≈ 64 %). Adjusting the HC filter to admit S50 scores should unlock the full edge and can be deployed with the 1 % risk sizing described.
- **Demote / mutate:** **EQUITY** – the apparent “edge” is almost certainly a leakage or single‑symbol artifact (PF ≈ 99, 100 % win‑rate). Reduce its exposure by tightening the trust gate (MIN_TRUST = 80) and treat the class as “under investigation” per the MUTATION_THREE_AXIS_PROTOCOL. All other classes should remain at current exposure (i.e., effectively zero) until a genuine PROVEN edge emerges.

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### CRYPTO
- Real/noise verdict: Real. Two cells show n=301-394, WR_shrunk 63-64%, PF 1.8-2.3, holdout_pass true, bonferroni true, positive wr_z; no obvious leakage.
- 90d expected P&L (1% risk, $100k): $2,840 (assume 300 trades at 1% risk, avg +0.85% net per trade after 0.1% slippage).
- Gate change: SMART_PICKS_MIN_SCORE_CRYPTO = 50
- Confidence (1-5): 4

### COMMODITY
- Real/noise verdict: Noise. No proven cells; best_pf cells have n<100, negative wr_z, holdout fail, bonferroni fail.
- 90d expected P&L (1% risk, $100k): -$1,120 (negative expectancy after slippage on 500+ trades).
- Gate change: SMART_PICKS_MIN_TRUST_COMMODITY = 70
- Confidence (1-5): 5

### INDEX
- Real/noise verdict: Noise. n_closed=7; zero proven or best_pf cells.
- 90d expected P&L (1% risk, $100k): $0 (no actionable edge).
- Gate change: SMART_PICKS_MIN_SCORE_INDEX = 80
- Confidence (1-5): 5

### FOREX
- Real/noise verdict: Noise. High PF cells have WR<30%, negative wr_z <-4, holdout fail; matches rejected leakage patterns.
- 90d expected P&L (1% risk, $100k): -$2,150 (high volume, negative expectancy).
- Gate change: HC_FILTER_MIN_CONF_FOREX = 0.85
- Confidence (1-5): 5

### ETF
- Real/noise verdict: Noise. n_closed=23; zero proven cells.
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: SMART_PICKS_MIN_SCORE_ETF = 75
- Confidence (1-5): 5

### UNKNOWN
- Real/noise verdict: Noise. n_closed=10; zero cells.
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: SMART_PICKS_MIN_SCORE_UNKNOWN = 90
- Confidence (1-5): 5

### EQUITY
- Real/noise verdict: Noise (likely leakage). 100% WR on n=50 with PF=99 is implausible; single-symbol concentration probable.
- 90d expected P&L (1% risk, $100k): $0 (reject all cells).
- Gate change: SMART_PICKS_MIN_SCORE_EQUITY = 85
- Confidence (1-5): 5

### BOND
- Real/noise verdict: Noise. n=20-21 cells show PF<1, negative wr_z, holdout fail.
- 90d expected P&L (1% risk, $100k): -$380 (negative expectancy).
- Gate change: SMART_PICKS_MIN_TRUST_BOND = 80
- Confidence (1-5): 5

### FUTURES
- Real/noise verdict: Noise. n=21-24 cells; holdout fail, bonferroni fail.
- 90d expected P&L (1% risk, $100k): $0 (no stable edge).
- Gate change: SMART_PICKS_MIN_SCORE_FUTURES = 70
- Confidence (1-5): 5

### MEME
- Real/noise verdict: Noise. n_closed=1; zero cells.
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: SMART_PICKS_MIN_SCORE_MEME = 95
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale CRYPTO today (only class with statistically validated, holdout-passed edges). Demote EQUITY and COMMODITY per MUTATION_THREE_AXIS_PROTOCOL (mutate gates first, then kill flows). All other classes have no deployable edge.
