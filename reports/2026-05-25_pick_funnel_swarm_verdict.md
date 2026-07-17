# Pick Funnel Swarm Verdict — 2026-07-17 05:04 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260717T050349Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

**NOTE:** All calculations are back‑of‑the‑envelope estimates based on the statistics you supplied.  No new data were mined and no “invented” edges are presented.

---

## COMMODITY
- **Real/noise verdict:** *No statistically proven edge.*  The best PF (2.61) comes from a cell with only 79 trades and a Bonferroni‑failed hold‑out (p ≈ 0.2).  The win‑rate (≈ 43 %) is far below the 55 % Bayesian threshold, so the signal is indistinguishable from noise.
- **90d expected P&L (1 % risk, $100 k):** $0
- **Gate change:** – (none needed – the class has no edge)
- **Confidence (1‑5):** 1  

---

## FOREX
- **Real/noise verdict:** *No statistically proven edge.*  The highest PF (5.74) is from a cell with 147 trades, but the win‑rate is only 29 % (shrunken ≈ 32 %) and the hold‑out fails the Bonferroni test.  The “consensus”‑type cells that show PF > 5 are driven by a handful of outlier trades and are not robust.
- **90d expected P&L (1 % risk, $100 k):** $0
- **Gate change:** – (none – no edge)
- **Confidence (1‑5):** 1  

---

## CRYPTO
- **Real/noise verdict:** *Statistically real edge.*  The cell **trust=UNK & dir=LONG & score_dec=S50** has:
  - **n = 323** closed trades (well above the 20‑trade minimum),
  - **WR_shrunk = 65.9 %** (well above the 55 % Bayesian cut‑off),
  - **PF = 1.979** (significant, with a Z‑score = 6.06 and Bonferroni‑pass),
  - No obvious single‑symbol concentration (the data set is diversified across many crypto pairs).
  Hence the signal survives both in‑sample and out‑of‑sample validation and is unlikely to be leakage.
- **90d expected P&L (1 % risk, $100 k):**  
  - Loss‑rate = 1 – 0.669 = 0.331  
  - Expected % per trade = L × (PF – 1) × 1 % = 0.331 × 0.979 × 1 % ≈ 0.324 %  
  - 323 trades × 0.324 % ≈ 104.8 % of the account → **≈ $104,800** profit.  
  (Assumes 1 % max‑loss per trade, no slippage, and that the risk size stays at 1 % of the *current* equity.)
- **Gate change:** Lower the high‑conviction filter so this edge can pass the front‑end gate.  
  ```js
  // hc_filter.js
  const MIN_SCORE = 50;      // was 80
  const MIN_CONF  = 0.60;    // was 0.75
  const MIN_TRUST = 0;       // keep as‑is (trust=UNK passes)
  ```
- **Confidence (1‑5):** 5  

---

## INDEX
- **Real/noise verdict:** *No statistically proven edge.*  Only 8 closed trades; win‑rate 62 % but PF = 1.0 (no profit).  Sample too tiny to be reliable.
- **90d expected P&L (1 % risk, $100 k):** $0
- **Gate change:** – (none)
- **Confidence (1‑5):** 1  

---

## EQUITY
- **Real/noise verdict:** *Statistically significant *but* highly suspect.*  
  The three “PROVEN” cells all have **n ≈ 40**, **WR_shrunk ≈ 83 %**, and an astronomic **PF ≈ 99** because **win‑rate = 100 %**.  Such a perfect win record in a live‑trade set is a classic red flag for data leakage, look‑ahead, or extreme symbol concentration (e.g., a single mean‑reversion ticker that happened to be flat during the 90‑day window).  The Bonferroni test passes, but the sample is tiny and the underlying model (mean‑reversion from `alpha_engine`) is known to be fragile.  Verdict: *edge likely noise / leakage*.
- **90d expected P&L (1 % risk, $100 k):** $0 (we would not allocate capital until the leakage risk is cleared)
- **Gate change:** – (no gate will rescue a potentially leaky signal)
- **Confidence (1‑5):** 2  

---

## ETF
- **Real/noise verdict:** *No statistically proven edge.*  Best PF = ‑ (none) and only 23 closed trades; win‑rate 8 % – clearly noise.
- **90d expected P&L (1 % risk, $100 k):** $0
- **Gate change:** – (none)
- **Confidence (1‑5):** 1  

---

## UNKNOWN
- **Real/noise verdict:** *No edge.*  Only 10 closed trades, 0 % win‑rate.
- **90d expected P&L (1 % risk, $100 k):** $0
- **Gate change:** – (none)
- **Confidence (1‑5):** 1  

---

## BOND
- **Real/noise verdict:** *No statistically proven edge.*  PF ≈ 0.56, win‑rate ≈ 12 %, and hold‑out fails.  Sample (31 trades) is too small.
- **90d expected P&L (1 % risk, $100 k):** $0
- **Gate change:** – (none)
- **Confidence (1‑5):** 1  

---

## FUTURES
- **Real/noise verdict:** *No statistically proven edge.*  PF ≈ 1.64, win‑rate ≈ 40 %, but hold‑out fails and n = 24 is tiny.
- **90d expected P&L (1 % risk, $100 k):** $0
- **Gate change:** – (none)
- **Confidence (1‑5):** 1  

---

## MEME
- **Real/noise verdict:** *No edge.*  Single trade, 100 % win – not enough data.
- **90d expected P&L (1 % risk, $100 k):** $0
- **Gate change:** – (none)
- **Confidence (1‑5):** 1  

---

# SYSTEM‑WIDE CONCLUSION

**Scale‑up today:** **CRYPTO** – the long‑only, unknown‑trust, score‑decile S50 cell shows a robust, statistically validated edge (PF ≈ 2, WR ≈ 66 %).  With ~300 trades in 90 days, the expected return at 1 % risk per trade is roughly **$105 k** on a $100 k account, comfortably exceeding typical risk‑adjusted targets.  Implement the gate relaxation (score ≥ 50, confidence ≥ 0.60) to let this edge flow to the live picker.

**Demote / kill:** **EQUITY** – despite passing the Bayesian WR threshold, the 100 % win‑rate and absurd PF ≈ 99 on only ~40 trades strongly suggest data leakage or extreme concentration.  Until a rigorous out‑of‑sample validation (different symbols, longer horizon) is performed, this signal should be removed from the production pipeline.

All other asset classes currently lack any statistically proven edge; keep them at the existing gate settings and monitor for future discoveries.

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

Here is the brutally honest audit of your 90-day pick funnel.

### COMMODITY
- **Real/noise verdict:** Noise. No PROVEN cells. The best PF (2.613) comes from a cell with only 4 training samples and fails holdout. The `conf=C0.75-0.80` cell shows a PF of 1.304 with a 0.0471% avg PnL — that’s a rounding error, not an edge. The overall decisive WR of 27.07% is below the 30% threshold for random noise in most futures markets.
- **90d expected P&L (1% risk, $100k):** -$2,850 (665 decisive trades × 1% risk × $100k × (0.2707 - 0.5) = 665 × $1,000 × -0.2293). Slippage assumption: 0.5 ticks per trade, which would add another ~$3,325 in costs. Net: **-$6,175**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` = 85 (currently 80). This would filter out the 2,398 scans that passed Smart but produced no HC picks, likely eliminating the low-conviction noise that dominates the 27% WR.
- **Confidence (1-5):** 2

### FOREX
- **Real/noise verdict:** Noise. Zero PROVEN cells. The best PF (5.736) is a statistical mirage: `conf=C0.75-0.80 & dir=LONG & source=multi_asset_copytrader` has a WR of only 29.25% but a PF of 5.736. This is a classic **low-WR, high-PF trap** — the PF is driven by a few massive outliers (likely single-symbol concentration on EUR/USD during a specific volatility event). The holdout fails (train PF=0.162, holdout PF=6.361), confirming instability. The overall WR of 26.75% is abysmal.
- **90d expected P&L (1% risk, $100k):** -$4,215 (1,813 decisive trades × 1% risk × $100k × (0.2675 - 0.5) = 1,813 × $1,000 × -0.2325). Slippage: 0.2 pips per trade (~$2 per trade) = -$3,626. Net: **-$7,841**.
- **Gate change:** `SMART_PICKS_MIN_CONFIDENCE_FOREX` = 0.85 (currently 0.75). The `conf=C0.75-0.80` cells are the worst offenders — raising the floor to 0.85 would kill the 147-trade cell with 29% WR and the 412-trade cell with 6% WR.
- **Confidence (1-5):** 1

### CRYPTO
- **Real/noise verdict:** Real, but fragile. One PROVEN cell: `trust=UNK & dir=LONG & score_dec=S50` (n=323, WR_shrunk=65.89%, PF=1.979, holdout_pass=true, bonferroni_pass=true). This is statistically significant (z=6.064). However, the PF of 1.979 is suspiciously high for a 66% WR cell — it implies the average win is ~2× the average loss. This could indicate **single-symbol concentration** (likely BTC or ETH during the Q1 2025 rally). The `best_pf_overall` cells with PF=1.62 and n=426 are not PROVEN (bonferroni fail), suggesting the edge is narrow.
- **90d expected P&L (1% risk, $100k):** +$5,850 (3,195 decisive trades × 1% risk × $100k × (0.4617 - 0.5) = 3,195 × $1,000 × -0.0383). Wait — the overall WR is 46.17%, which is *below* 50%. The PROVEN cell is only 323 of 3,195 trades. If we size only the PROVEN cell: 323 × 1% × $100k × (0.6589 - 0.5) = 323 × $1,000 × 0.1589 = **+$51,325**. But this assumes you can identify and trade only those 323 signals. Realistically, you’d trade the whole class: **-$122** (3,195 × $1,000 × -0.0383). Slippage: 0.1% per trade (~$10) = -$31,950. Net: **-$32,072** for the whole class, or **+$19,375** if you isolate the PROVEN cell.
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` = 50 (currently 80). The PROVEN cell is `score_dec=S50` (score 50-59). Your current gate at 80 is *missing the only real edge*. Lowering to 50 would capture the 323-trade cell. Alternatively, add a gate in `hc_filter.js`: `score_dec >= 50 && score_dec < 60` for CRYPTO LONG.
- **Confidence (1-5):** 4 (for the specific cell), 2 (for the class overall)

### EQUITY
- **Real/noise verdict:** Real, but suspicious. Three PROVEN cells, all with 100% WR and PF=99.0. This is **too perfect**. The `fam=mean_reversion` cells with n=41 and 100% WR are almost certainly **leakage or look-ahead bias**. The avg PnL of 1.14% per trade with zero losses over 41 trades is not realistic in equities. Possible causes: (1) the `alpha_engine` source is using future data to score, (2) the trades are on a single symbol (e.g., TSLA) during a specific event, or (3) the `mean_reversion` strategy is actually a market-making strategy that captures the spread but is not scalable. The overall WR of 43.54% (395 decisive trades) is below 50%, confirming the class is not profitable as a whole.
- **90d expected P&L (1% risk, $100k):** -$2,550 (395 decisive trades × 1% risk × $100k × (0.4354 - 0.5) = 395 × $1,000 × -0.0646). Slippage: 0.05% per trade (~$5) = -$1,975. Net: **-$4,525**. If the PROVEN cells are real (they aren’t), the P&L would be +$41,000, but I’m not betting on that.
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` = 60 (currently 80). The PROVEN cells have `conf=C<0.60`, meaning your current confidence gate is *excluding* the only cells that look good. But given the 100% WR is suspicious, I’d instead add a **max position size gate** in `alpha_engine/production_scanner.py`: `MAX_SYMBOL_WEIGHT_EQUITY = 0.1` to prevent single-symbol concentration.
- **Confidence (1-5):** 1 (the PROVEN cells are likely leakage), 3 (the class has potential if the leakage is fixed)

### ETF
- **Real/noise verdict:** Noise. Zero PROVEN cells. WR of 8.7% (2 wins out of 23 decisive trades) is catastrophic. The class should be killed immediately.
- **90d expected P&L (1% risk, $100k):** -$950 (23 decisive trades × 1% risk × $100k × (0.087 - 0.5) = 23 × $1,000 × -0.413). Slippage: 0.03% per trade (~$3) = -$69. Net: **-$1,019**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` = 95 (effectively disabling the class). Or simply set `ETF_ENABLED = False` in `quality_gates.py`.
- **Confidence (1-5):** 5 (high confidence this class is dead)

### BOND
- **Real/noise verdict:** Noise. Zero PROVEN cells. WR of 12.9% (4 wins out of 31 decisive trades). The best PF is 0.557 (negative edge). The `rr=RR>=2.0` cells have PF=0.0 — meaning every trade with a 2:1 R:R lost money. This is a systematic negative edge.
- **90d expected P&L (1% risk, $100k):** -$1,150 (31 decisive trades × 1% risk × $100k × (0.129 - 0.5) = 31 × $1,000 × -0.371). Slippage: 0.01% per trade (~$1) = -$31. Net: **-$1,181**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` = 95 (effectively disabling the class).
- **Confidence (1-5):** 5

### FUTURES
- **Real/noise verdict:** Noise. Zero PROVEN cells. Only 24 decisive trades — insufficient sample size. WR of 45.83% is not statistically different from 50% (z=-0.894).
- **90d expected P&L (1% risk, $100k):** -$100 (24 decisive trades × 1% risk × $100k × (0.4583 - 0.5) = 24 × $1,000 × -0.0417). Slippage: 0.5 ticks per trade (~$5) = -$120. Net: **-$220**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` = 85 (tighten until sample size reaches 100+).
- **Confidence (1-5):** 2

### INDEX
- **Real/noise verdict:** Noise. Only 8 decisive trades — statistically meaningless. WR of 62.5% is based on 5 wins and 3 losses.
- **90d expected P&L (1% risk, $100k):** +$100 (8 decisive trades × 1% risk × $100k × (0.625 - 0.5) = 8 × $1,000 × 0.125). Slippage: 0.1% per trade (~$10) = -$80. Net: **+$20**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` = 80 (keep as-is, but do not scale).
- **Confidence (1-5):** 1

### UNKNOWN
- **Real/noise verdict:** Noise. 0% WR (0 wins out of 10 decisive trades). The class is a data quality issue — these are unclassified assets that should not be traded.
- **90d expected P&L (1% risk, $100k):** -$500 (10 decisive trades × 1% risk × $100k × (0.0 - 0.5) = 10 × $1,000 × -0.5). Net: **-$500**.
- **Gate change:** `UNKNOWN_ENABLED = False` in `quality_gates.py`.
- **Confidence (1-5):** 5

### MEME
- **Real/noise verdict:** Noise. 1 decisive trade (1 win, 0 losses). Sample size is laughable.
- **90d expected P&L (1% risk, $100k):** +$100 (1 trade × 1% risk × $100k × (1.0 - 0.5) = 1 × $1,000 × 0.5). Slippage: 0.5% per trade (~$50) = -$50. Net: **+$50**.
- **Gate change:** `MEME_ENABLED = False`.
- **Confidence (1-5):** 1

---

## SYSTEM-WIDE CONCLUSION

### Scale Up TODAY (real money):
**CRYPTO — but only the PROVEN cell.** The `trust=UNK & dir=LONG & score_dec=S50` cell (n=323, WR_shrunk=65.89%, PF=1.979, holdout_pass=true) is the only statistically validated edge in the entire system. However, I would:
1. **Limit to 0.5% risk per trade** (not 1%) due to crypto volatility.
2. **Cap position size at 2% of notional** to avoid single-symbol concentration.
3. **Set a 30-day stop-loss on the strategy** — if the next 30 trades have WR < 55%, kill it.

Expected monthly P&L: ~$8,500 (assuming 30 trades/month at 0.5% risk, 65% WR, 1.98 PF).

### Demote / Kill (per MUTATION_THREE_AXIS_PROTOCOL.md):
**ETF, BOND, UNKNOWN** — these three classes should be **killed immediately**. They have:
- WR below 15% (ETF: 8.7%, BOND: 12.9%, UNKNOWN: 0%)
- Zero PROVEN cells
- Negative or zero PF in all top cells
- Insufficient sample sizes to justify further mutation

**FOREX** — **demote to MUTATION phase** (not kill yet). The `conf=C0.75-0.80 & score_dec=S50 & source=multi_asset_copytrader` cell has a holdout PF of 4.568 and WR of 59.59%, but fails bonferroni. This is a candidate for further mutation — try splitting by `rr` band or adding a volatility filter.

**EQUITY** — **demote to INVESTIGATION phase**. The 100% WR cells are suspicious and likely leakage. Before scaling, run a full symbol-level audit to check for single-symbol concentration and timestamp alignment.

### Final Verdict:
Your system has **one real edge** (CRYPTO LONG score 50-59) and **seven noise classes**. The 90-day P&L for the entire system (if traded equally) would be approximately **-$54,000** (including slippage). The only profitable path is to isolate the CRYPTO cell, kill ETF/BOND/UNKNOWN, and put FOREX/EQUITY on probation.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### CRYPTO
- Real/noise verdict: Real (n=323 closed, WR_shrunk 65.89, PF 1.979; holdout_pass + bonferroni_pass both true; no obvious leakage flags).
- 90d expected P&L (1% risk, $100k): $2,850 (323 trades × 1% risk × 0.787% avg pnl, 0.15% slippage, 0.10% commission).
- Gate change: SMART_PICKS_MIN_SCORE_CRYPTO = 55
- Confidence (1-5): 4

### EQUITY
- Real/noise verdict: Noise/leakage (n=41, WR=100%, PF=99; impossible without single-symbol concentration or data error; reject).
- 90d expected P&L (1% risk, $100k): $0 (edge discarded).
- Gate change: SMART_PICKS_MIN_SCORE_EQUITY = 70
- Confidence (1-5): 5

### FOREX
- Real/noise verdict: Noise (no proven cells; all best_pf cells fail holdout_pass or bonferroni_pass; WR_shrunk too low).
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: HC_MIN_CONF = 0.82
- Confidence (1-5): 5

### COMMODITY
- Real/noise verdict: Noise (no proven cells; all candidates fail holdout_pass).
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: SMART_PICKS_MIN_SCORE_COMMODITY = 65
- Confidence (1-5): 5

### INDEX
- Real/noise verdict: Noise (n_closed=8 too small; no proven cells).
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: SMART_PICKS_MIN_SCORE_INDEX = 75
- Confidence (1-5): 5

### ETF
- Real/noise verdict: Noise (n_closed=23 too small; no proven cells; WR 8.7%).
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: SMART_PICKS_MIN_SCORE_ETF = 70
- Confidence (1-5): 5

### BOND
- Real/noise verdict: Noise (n_closed=31 too small; all best_pf cells negative PF and fail holdout).
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: SMART_PICKS_MIN_SCORE_BOND = 80
- Confidence (1-5): 5

### FUTURES
- Real/noise verdict: Noise (n_closed=24 too small; only candidate fails holdout_pass).
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: SMART_PICKS_MIN_SCORE_FUTURES = 75
- Confidence (1-5): 5

### UNKNOWN / MEME
- Real/noise verdict: Noise (n_closed ≤10; zero proven cells).
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: SMART_PICKS_MIN_SCORE_UNKNOWN = 90
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale CRYPTO today (only class with statistically validated edge). Demote EQUITY per MUTATION_THREE_AXIS_PROTOCOL.md (mutate the mean_reversion family first, then kill if WR_shrunk collapses). All other classes have no usable edge.
