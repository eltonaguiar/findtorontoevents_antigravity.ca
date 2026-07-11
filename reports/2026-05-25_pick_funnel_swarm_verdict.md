# Pick Funnel Swarm Verdict — 2026-07-11 05:03 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260711T050324Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

### CRYPTO  
- **Real/noise verdict:** **Real edge** – the single “PROVEN” cell (trust = UNK & dir = LONG & score_dec = S50) has n = 282, WR ≈ 65 % (shrunken), PF = 1.87, hold‑out pass = true and Bonferroni = true.  No obvious look‑ahead or single‑symbol concentration (the win‑rate is spread over many symbols).  
- **90d expected P&L (1 % risk, $100 k):** **≈ $82 k**  
  *Assumptions:* $1 k risk per trade, loss = $1 k, average win = 0.948 × $1 k ≈ $948.  Expected profit per trade = 0.292 × $1 k ≈ $292 → 282 trades → $82 344.  Slippage ignored (average‑size crypto trades are liquid enough that 0.1 % slippage ≈ $100 per trade would still leave a positive expectancy).  
- **Gate change:** **`SMART_PICKS_MIN_SCORE_DEC_CRYPTO = 50`** (currently 60).  Lowering the minimum score‑decile to 50 lets the “S50” bucket through the Smart‑Picks gate, increasing the volume of this proven edge.  
- **Confidence (1‑5):** **4**  

### EQUITY  
- **Real/noise verdict:** **Real edge** – three “PROVEN” cells all satisfy n ≥ 38, WR_shrunk ≈ 80 %+, PF ranging 9.4 → 32.2, hold‑out = true, Bonferroni = true.  The families (mean‑reversion, low‑confidence + S40) are orthogonal, so leakage is unlikely.  
- **90d expected P&L (1 % risk, $100 k):** **≈ $65 k**  
  *Assumptions:* $1 k risk per trade, loss = $1 k.  
  - Mean‑reversion LONG cell (n = 39, PF = 32.2, win = 38): expected profit ≈ $800 per trade → $31.2 k.  
  - Low‑conf S40 cell (n = 38, PF = 9.41, win = 36): expected profit ≈ $442 per trade → $16.8 k.  
  - Same stats for the “trust = UNK & conf < 0.60 & S40” cell → another $16.8 k.  
  Total ≈ $64.8 k.  Slippage of 0.05 % (≈ $5 per trade) is negligible relative to the expectancy.  
- **Gate change:** **`CONFIDENCE_MIN = 0.60`** in `audit_dashboard/hc_filter.js` (currently 0.75).  The proven edges sit in the C < 0.60 band; lowering the confidence threshold captures them without sacrificing the high‑conviction filter.  
- **Confidence (1‑5):** **4**  

### FOREX  
- **Real/noise verdict:** **Noise** – no “PROVEN” cells; the best PF (≈ 5.1) fails the hold‑out test (WR ≈ 9 % and negative Z‑score).  The high PF is driven by a handful of large wins that do not survive out‑of‑sample validation, indicating look‑ahead/over‑fitting.  
- **90d expected P&L (1 % risk, $100 k):** **$0** (edge not statistically reliable).  
- **Gate change:** **N/A** – tightening the confidence gate (e.g., `CONFIDENCE_MIN = 0.80`) would prune the noisy high‑PF cells; the current edge would not survive anyway.  
- **Confidence (1‑5):** **2**  

### COMMODITY  
- **Real/noise verdict:** **Noise** – no “PROVEN” cells; best PF ≈ 1.21 with hold‑out = false and Bonferroni = false.  The signal is essentially break‑even and fails out‑of‑sample validation.  
- **90d expected P&L (1 % risk, $100 k):** **$0**.  
- **Gate change:** **N/A** – the current quality gate already filters out low‑confidence picks; further raising the `SMART_PICKS_MIN_SCORE_COMMODITY` would not improve expectancy.  
- **Confidence (1‑5):** **2**  

### BOND  
- **Real/noise verdict:** **Noise** – no “PROVEN” cells; all PF ≤ 0.56, hold‑out fails, negative Z‑scores.  The few trades are loss‑heavy.  
- **90d expected P&L (1 % risk, $100 k):** **$0**.  
- **Gate change:** **N/A** – raising the `SMART_PICKS_MIN_SCORE_BOND` (or adding a minimum PF filter) would simply discard the current unprofitable picks.  
- **Confidence (1‑5):** **2**  

### FUTURES  
- **Real/noise verdict:** **Noise** – only 21 closed trades, no “PROVEN” cells, PF ≈ 0, hold‑out fails.  Sample size far too small to claim an edge.  
- **90d expected P&L (1 % risk, $100 k):** **$0**.  
- **Gate change:** **N/A** – the `SMART_PICKS_MIN_RR_FUTURES` could be increased to require RR ≥ 2.0, which would eliminate the current loss‑making picks.  
- **Confidence (1‑5):** **1**  

### ETF  
- **Real/noise verdict:** **Noise** – 23 closed trades, no “PROVEN” cells, PF ≈ 0, win‑rate 8 %.  No statistical edge.  
- **90d expected P&L (1 % risk, $100 k):** **$0**.  
- **Gate change:** **N/A** – tightening the `SMART_PICKS_MIN_SCORE_ETF` (currently low) would remove the few weak signals.  
- **Confidence (1‑5):** **2**  

### INDEX  
- **Real/noise verdict:** **Noise** – 8 closed trades, no “PROVEN” cells, PF ≈ 0, win‑rate 62 % but tiny sample; WR_shrunk not significant.  
- **90d expected P&L (1 % risk, $100 k):** **$0**.  
- **Gate change:** **N/A** – raise the minimum R‑R band (`SMART_PICKS_MIN_RR_INDEX = 1.5`) to avoid low‑return picks.  
- **Confidence (1‑5):** **1**  

### MEME  
- **Real/noise verdict:** **Noise** – only a single closed trade (win), no statistical basis.  
- **90d expected P&L (1 % risk, $100 k):** **$0** (cannot size a strategy on a single observation).  
- **Gate change:** **N/A** – the class should be disabled entirely.  
- **Confidence (1‑5):** **1**  

### UNKNOWN  
- **Real/noise verdict:** **Noise** – 8 closed trades, 0 % win‑rate, no “PROVEN” cells.  The class is essentially garbage.  
- **90d expected P&L (1 % risk, $100 k):** **$0**.  
- **Gate change:** **N/A** – set `SMART_PICKS_MIN_SCORE_UNKNOWN = 100` (or remove the class).  
- **Confidence (1‑5):** **1**  

---

## SYSTEM‑WIDE Conclusion  

**Scale‑up today:** **EQUITY** – the three proven cells deliver a combined expected profit of roughly **$65 k** over 90 days on a $100 k account with 1 % risk per trade, and the statistical tests (hold‑out, Bonferroni) are clean.  Lowering the confidence threshold to 0.60 will unlock the full edge without introducing obvious noise.

**Demote / kill:** **UNKNOWN** (and, by extension, MEME, FUTURES, BOND, ETF, INDEX, COMMODITY, FOREX).  These classes have no statistically validated edge, many fail out‑of‑sample checks, and some exhibit clear leakage or over‑fitting.  They should be removed from the production pipeline per the *MUTATION_THREE_AXIS_PROTOCOL* before any capital is allocated.  

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

Here is the brutally honest, per-class verdict on the 90-day pick-funnel data for findtorontoevents.ca.

---

### CRYPTO
- **Real/noise verdict:** **Real, but fragile.** The single PROVEN cell (`trust=UNK & dir=LONG & score_dec=S50`, n=282, WR_shrunk=65.23%, PF=1.865) passes Bonferroni and holdout. However, the funnel is catastrophic: **0** signals pass the HIGH CONVICTION gate. The system is generating 16k scans but the client-side filter kills everything. The "best" edges are all from `trust=UNK` (unknown trust), which is a red flag for systematic risk. The `ml` cells you flagged are not present in this data; the high PF cells here are from `luxalgo` and `RR1.5-2.0` SELLs, which have low WR (52%) and fail Bonferroni. **Do not confuse high PF with edge**—these are low-frequency, high-variance outliers.
- **90d expected P&L (1% risk, $100k):** **$0.00.** No signals pass the HC gate. If we traded the PROVEN cell alone (n=282, WR=66.3%, avg win=+0.71%, avg loss=-0.71% implied by PF=1.865), expected net profit = 282 * (0.663 * 0.0071 - 0.337 * 0.0071) * $1,000 = **$652**. But this ignores the 0 HC pass rate—the system is not actually recommending these trades.
- **Gate change:** `hc_filter.js` → `MIN_SCORE_HIGH_CONVICTION = 70` (currently 80). The PROVEN cell has score_dec=S50, which maps to a score of ~50, far below 80. Lowering to 70 would capture this edge while still filtering noise.
- **Confidence (1-5):** 2. The edge is real in backtest but the production pipeline is misaligned.

---

### COMMODITY
- **Real/noise verdict:** **Noise.** Zero PROVEN cells. The "best" cell (`trust=PROBATION & rr=RR1.5-2.0 & dir=LONG & score_dec=S50`, n=107) has WR=50.47%, PF=1.207, and **no holdout data** (holdout_n=0). This is a train-only artifact. The overall WR for the class is 31.28%—worse than a coin flip. The rejected H-001 (COT look-ahead) and H-036 (inventory direction) confirm this class is structurally broken.
- **90d expected P&L (1% risk, $100k):** **-$3,200.** 892 decisive trades at 31.28% WR with avg win/loss implied by PF=1.144 (from the best cell) gives: 892 * (0.3128 * 0.00144 - 0.6872 * 0.00144) * $1,000 = -$3,200. This is a slow bleed.
- **Gate change:** `audit_trail/quality_gates.py` → `SMART_PICKS_MIN_SCORE_COMMODITY = 999` (effectively disable). The class has no edge and is consuming compute.
- **Confidence (1-5):** 5 (confident it's noise).

---

### FOREX
- **Real/noise verdict:** **Noise with a dangerous mirage.** Zero PROVEN cells. The "best" cells have **negative WR z-scores** (e.g., -18.5 for the top cell). The high PF values (5.117, 4.053) are a textbook example of **low-frequency, high-win-size outliers** masking a terrible WR (8-29%). The `multi_asset_copytrader` source is generating these—likely a few massive wins on tiny sample sizes. The overall WR is 29.36%. **Do not trade this.**
- **90d expected P&L (1% risk, $100k):** **-$5,800.** 2578 decisive trades at 29.36% WR with avg win/loss implied by the top cell's PF=5.117 (but WR=8.18%) gives: 2578 * (0.2936 * 0.005 - 0.7064 * 0.005) * $1,000 = -$5,800. The actual number is worse because the high-PF cells have even lower WR.
- **Gate change:** `hc_filter.js` → `MIN_CONFIDENCE_HIGH_CONVICTION = 0.90` (currently 0.75). The current 0.75 threshold is letting in garbage. Raising to 0.90 would kill 99% of signals, which is appropriate.
- **Confidence (1-5):** 5 (confident it's noise).

---

### EQUITY
- **Real/noise verdict:** **Real and strong.** Three PROVEN cells, all with WR_shrunk > 79%, PF > 9.4, Bonferroni pass, and holdout pass. The top cell (`fam=mean_reversion & dir=LONG & source=alpha_engine`, n=39, WR=97.44%, PF=32.2) is extraordinary. However, **n=39 is small**—this could be a single stock (e.g., repeated mean-reversion on TSLA). The funnel shows only 2 signals pass HC, but 3 pass PROVEN—this suggests the HC gate is too strict for this specific edge. The overall WR of 43.96% is dragged down by the rest of the class.
- **90d expected P&L (1% risk, $100k):** **$11,700.** If we trade the top 3 PROVEN cells (n=39+38+38=115 trades, avg WR ~95%, avg PF ~17), expected profit = 115 * (0.95 * 0.01 - 0.05 * 0.01) * $1,000 = **$10,350**. Adding the remaining 274 trades at 43.96% WR (implied PF ~1.2) gives ~$1,350. Total: **$11,700**. This assumes 1% risk per trade and 0.1% slippage.
- **Gate change:** `hc_filter.js` → `MIN_SCORE_HIGH_CONVICTION = 40` for EQUITY only (currently 80). The PROVEN cells have score_dec=S40, which maps to ~40. Lowering to 40 would capture these edges while still filtering the 95% of garbage.
- **Confidence (1-5):** 4. Strong signal, but small n and potential single-stock concentration need monitoring.

---

### ETF
- **Real/noise verdict:** **Noise.** Zero PROVEN cells. n=23 closed trades, WR=8.7%. The sample is too small to draw conclusions, but the direction is clearly negative.
- **90d expected P&L (1% risk, $100k):** **-$200.** 23 trades at 8.7% WR is a rounding error. Not worth trading.
- **Gate change:** `audit_trail/quality_gates.py` → `SMART_PICKS_MIN_SCORE_ETF = 999` (disable). The class has insufficient data and no edge.
- **Confidence (1-5):** 3 (low confidence due to tiny sample, but direction is clear).

---

### BOND
- **Real/noise verdict:** **Noise.** Zero PROVEN cells. n=30 closed trades, WR=10%. The "best" cells have negative PF and negative z-scores. This is a losing class.
- **90d expected P&L (1% risk, $100k):** **-$400.** 30 trades at 10% WR. Negligible but negative.
- **Gate change:** `audit_trail/quality_gates.py` → `SMART_PICKS_MIN_SCORE_BOND = 999` (disable).
- **Confidence (1-5):** 4.

---

### UNKNOWN
- **Real/noise verdict:** **Noise.** n=8 closed trades, WR=0%. No data to analyze. Likely misclassified signals.
- **90d expected P&L (1% risk, $100k):** **$0.** Do not trade.
- **Gate change:** `audit_trail/quality_gates.py` → `SMART_PICKS_MIN_SCORE_UNKNOWN = 999` (disable).
- **Confidence (1-5):** 5.

---

### FUTURES
- **Real/noise verdict:** **Inconclusive.** n=21 closed trades, WR=52.38%. The sample is too small (n<20 for edge analysis). The funnel shows 292 pass Smart but 0 pass HC—the gate is too strict.
- **90d expected P&L (1% risk, $100k):** **$0.** Too few trades to estimate.
- **Gate change:** `hc_filter.js` → `MIN_SCORE_HIGH_CONVICTION = 50` for FUTURES (currently 80). Let more signals through to build a statistically meaningful sample.
- **Confidence (1-5):** 1 (no confidence—need more data).

---

### INDEX
- **Real/noise verdict:** **Inconclusive.** n=8 closed trades, WR=62.5%. Tiny sample. The funnel shows 374 pass Smart but 0 pass HC.
- **90d expected P&L (1% risk, $100k):** **$0.** Too few trades.
- **Gate change:** Same as FUTURES—lower HC threshold to 50 to build sample.
- **Confidence (1-5):** 1.

---

### MEME
- **Real/noise verdict:** **Noise.** n=1 closed trade. Statistically meaningless.
- **90d expected P&L (1% risk, $100k):** **$0.**
- **Gate change:** Disable.
- **Confidence (1-5):** 5.

---

## SYSTEM-WIDE CONCLUSION

### Scale Up TODAY with Real Money:
**EQUITY.** It is the only class with statistically validated, holdout-passing, Bonferroni-passing edges. The `mean_reversion & LONG & alpha_engine` cell is the strongest signal in the entire system. Start with 0.5% risk per trade (not 1%) until n>100 to confirm it's not a single-stock artifact. Allocate 80% of capital here.

### DEMOTE per MUTATION_THREE_AXIS_PROTOCOL:
**COMMODITY** and **FOREX** should be **mutated before killed**. They have the largest sample sizes (892 and 2578 decisive trades) and the worst performance (31% and 29% WR). The protocol says: mutate the signal generation (e.g., switch from `multi_asset_copytrader` to a different source for FOREX, or kill the `luxalgo` family for COMMODITY). If after one mutation cycle (30 days) WR does not exceed 45%, **kill both classes entirely**. They are currently destroying capital.

**CRYPTO** is a special case: the edge is real but the production pipeline is misconfigured. Fix the HC gate first, then re-evaluate. Do not scale up until the funnel shows >10 signals passing HC per week.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### EQUITY
- Real/noise verdict: Noise/leakage — 97% WR on n=39 with PF=32 is statistically impossible without single-symbol concentration or look-ahead; holdout/train split too small and extreme to trust.
- 90d expected P&L (1% risk, $100k): $0 (edge is spurious; real deployment would produce large drawdowns).
- Gate change: SMART_PICKS_MIN_SCORE_EQUITY = 75
- Confidence (1-5): 5

### CRYPTO
- Real/noise verdict: Real — n=282, WR_shrunk=65%, PF=1.865 passes holdout and Bonferroni; modest but stable.
- 90d expected P&L (1% risk, $100k): $2,100 (282 trades × 0.71% avg edge after 0.15% slippage, 1% risk).
- Gate change: HC_FILTER_MIN_CONF = 0.78
- Confidence (1-5): 4

### FOREX
- Real/noise verdict: Noise — zero proven cells; all best_pf cells show negative WR z-scores and failed holdouts.
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge).
- Gate change: SMART_PICKS_MIN_SCORE_FOREX = 85
- Confidence (1-5): 5

### COMMODITY
- Real/noise verdict: Noise — zero proven cells; all candidates fail holdout or show PF near 1.0.
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge).
- Gate change: SMART_PICKS_MIN_SCORE_COMMODITY = 80
- Confidence (1-5): 5

### FUTURES
- Real/noise verdict: Noise — n=21 total, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge).
- Gate change: SMART_PICKS_MIN_SCORE_FUTURES = 90
- Confidence (1-5): 5

### BOND
- Real/noise verdict: Noise — n=30 total, all best_pf cells negative expectancy.
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge).
- Gate change: SMART_PICKS_MIN_SCORE_BOND = 90
- Confidence (1-5): 5

### ETF
- Real/noise verdict: Noise — n=23 total, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge).
- Gate change: SMART_PICKS_MIN_SCORE_ETF = 90
- Confidence (1-5): 5

### INDEX
- Real/noise verdict: Noise — n=8 total, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge).
- Gate change: SMART_PICKS_MIN_SCORE_INDEX = 90
- Confidence (1-5): 5

### MEME
- Real/noise verdict: Noise — n=1 total, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge).
- Gate change: SMART_PICKS_MIN_SCORE_MEME = 95
- Confidence (1-5): 5

### UNKNOWN
- Real/noise verdict: Noise — n=8 total, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge).
- Gate change: SMART_PICKS_MIN_SCORE_UNKNOWN = 95
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale CRYPTO today (only class with a verified, modest edge). Demote EQUITY immediately per MUTATION_THREE_AXIS_PROTOCOL (suspected leakage recurrence). All other classes have no edge — apply score floors and stop allocating.
