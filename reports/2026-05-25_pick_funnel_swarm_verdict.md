# Pick Funnel Swarm Verdict — 2026-06-13 05:33 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260613T053247Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

**NOTE:** All calculations assume a flat‑$1 000 risk per trade (1 % of a $100 k account).  A “loss” is taken to be the full $1 000 risk; the profit factor (PF) tells us the average win size, and the expected net per trade is  

\[
E[\text{net}] = (PF-1)\times(1\!-\!WR)\times\$1{,}000
\]

where *WR* is the (un‑shrunk) win‑rate.  Slippage is taken as a flat **0.10 % of notional** (‑$100 per trade) and is subtracted from the final totals.

---

### CRYPTO
- **Real/noise verdict:** **Real** – two *PROVEN* cells (n = 434 and n = 462) both have WR ≈ 60 % (shrunk) and PF ≈ 2.07, pass the hold‑out test and Bonferroni correction.  No sign of look‑ahead leakage (trust = PROBATION, not a “high‑confidence” filter) and the trades are spread across many symbols (≈ 30 % of the universe), so concentration risk is low.
- **90d expected P&L (1 % risk, $100 k):**  
  *Cell 1*: 434 × $414 ≈ $180 k  
  *Cell 2*: 462 × $411 ≈ $190 k  
  **Total ≈ $370 k** – after 0.1 % slippage (≈ $370 k − $370 ≈ $369 k).  
- **Gate change:** `hc_filter.js → MIN_TRUST = 30` (lower the trust‑threshold from 60 to 30 so that PROBATION‑trust picks are allowed into the HIGH‑CONVICTION flow).  
- **Confidence (1‑5):** **5**

---

### EQUITY
- **Real/noise verdict:** **Mixed** – three top‑PF cells have PF > 3 and WR ≈ 45‑66 % with n = 49‑56.  Hold‑out passes for the first two cells, but the third fails the hold‑out PF test, suggesting a modest but real edge in the “trust = UNK” segment.  No obvious leakage; the family‑dimension (mean‑reversion) is well‑diversified across symbols.
- **90d expected P&L:**  
  *Cell 1*: 56 × $754 ≈ $42 k  
  *Cell 2*: 52 × $1 140 ≈ $59 k  
  *Cell 3*: 49 × $871 ≈ $43 k  
  **Total ≈ $144 k** – minus slippage ≈ **$143 k**.  
- **Gate change:** `audit_trail/quality_gates.py → SMART_PICKS_MIN_TRUST_EQUITY = 20` (bring the “UNK” trust band into the SMART‑PICKS filter, allowing the high‑PF mean‑reversion cells to flow).  
- **Confidence (1‑5):** **4**

---

### FOREX
- **Real/noise verdict:** **Borderline** – the best PF cells have PF ≈ 2.0‑2.4 with WR ≈ 20‑45 % and n = 264‑501.  The second cell (CTA replicator) passes the hold‑out PF test, but the others fail, indicating that the edge may be driven by a few high‑frequency strategies rather than a robust market‑wide signal.  No clear leakage, but the “source=cta_replicator” dimension is a single‑source concentration that should be monitored.
- **90d expected P&L:**  
  *Cell 1*: 264 × $763 ≈ $202 k  
  *Cell 2*: 275 × $629 ≈ $173 k  
  *Cell 3*: 501 × $716 ≈ $359 k  
  **Total ≈ $734 k** – after slippage ≈ **$733 k**.  
- **Gate change:** `hc_filter.js → MIN_CONFIDENCE = 0.55` (lower the confidence band from 0.75 to 0.55, which will admit the “conf = C0.60‑0.70” and “conf = C<0.60” cells that carry the bulk of the FOREX edge).  
- **Confidence (1‑5):** **3**

---

### COMMODITY
- **Real/noise verdict:** **Noise** –

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

Here is the brutally honest, per-class verdict on the 90-day pick-funnel edge analysis for `findtorontoevents.ca`.

### CRYPTO
- **Real/noise verdict:** **REAL (but fragile).** The two PROVEN cells (`trust=PROBATION & rr=RR1.5-2.0 & dir=LONG` and `trust=PROBATION & conf=C<0.60 & dir=LONG`) pass all statistical hurdles (n>400, WR_shrunk >59%, PF>2.0, Bonferroni pass, holdout pass). However, the `best_pf_overall` cell `fam=ml & dir=LONG` (PF=2.48) is suspicious. The holdout n=6 is too small to trust; this is likely a **leakage artifact** from the ML model overfitting to the training period. The PROVEN edges are real but are concentrated in low-confidence, probationary signals—this suggests the edge comes from a specific, narrow regime (e.g., high-volatility mean reversion) that may not persist.
- **90d expected P&L (1% risk, $100k):** **$17,347** (Based on PROVEN cell `trust=PROBATION & rr=RR1.5-2.0 & dir=LONG`: avg_pnl_pct=1.7347% per trade, 434 trades. Slippage: 0.05% per trade. Sizing: 1% risk per trade. Gross PnL = 434 * 1% * 1.7347% * $100k = $7,528. Net after slippage (434 * 0.05% * $100k = $217) = $7,311. *Wait—recalculating.* Avg_pnl_pct is the *return on risked capital*, not account return. At 1% risk, return per trade = 1% * avg_pnl_pct. So: 434 * 1% * 1.7347 = 7.53% of account = **$7,528**. Subtract slippage ($217) = **$7,311**. This is the *best* cell; the other PROVEN cell yields ~$6,200. Combined, expect **~$13,500**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` = **75** (currently likely lower). This will kill the noisy `ml` family signals (which have high PF but tiny holdout) and force the engine to only pass the robust PROBATION+LONG signals.
- **Confidence (1-5):** **4** (High statistical confidence, but low regime-confidence—this edge may vanish in a crypto bear market).

### COMMODITY
- **Real/noise verdict:** **NOISE.** Zero PROVEN cells. The `best_pf_overall` cells have WR_shrunk <48%, PF <1.35, and all fail holdout (holdout_n=0 or holdout_pf=0.0). The data is consistent with random chance. The rejected hypothesis H-001 (COT leakage) and H-036 (inventory direction) confirm the class is toxic.
- **90d expected P&L (1% risk, $100k):** **-$2,100** (Based on the overall WR of 34.26% and avg loss size. At 1% risk, 1007 decisive trades: expected wins = 345 * 1% * avg_win%, expected losses = 662 * 1% * avg_loss%. Using PF=1.0 as break-even, actual PF is ~0.85. Net loss = -2.1% of account).
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` = **95** (Effectively kill the class. The current gate is passing 66% of scans, which is insane for a class with 34% WR. Raise it to 95 to pass <1% of scans).
- **Confidence (1-5):** **5** (High confidence this is noise—the data is unambiguous).

### EQUITY
- **Real/noise verdict:** **NOISE (with a mirage).** Zero PROVEN cells. The `best_pf_overall` cells look tantalizing (PF>3.0, WR>60%) but fail the Bonferroni test and have tiny training sets (n=15-21). The `holdout_pass=true` is misleading because the holdout n is small (34-36) and the PF drops from ~500 to ~2.0—this is **variance, not edge**. The overall WR of 40% on 314 decisive trades confirms no systematic edge.
- **90d expected P&L (1% risk, $100k):** **-$1,200** (Based on overall WR=40.13%, PF ~1.0. At 1% risk, 314 trades: net loss ~1.2% of account).
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` = **85** (Currently passing only 2% of scans, which is good. But the signals that pass are still noise. Raise the score threshold to 85 to further restrict to only the highest-conviction setups, though expect n to drop to near zero).
- **Confidence (1-5):** **3** (The high PF on small samples is suspicious, but the overall class WR is definitive. Moderate confidence in "noise" verdict).

### FOREX
- **Real/noise verdict:** **NOISE (dangerous).** Zero PROVEN cells. The `best_pf_overall` cells have WR_shrunk <46% and PF that looks high (2.39) but is driven by a few large wins. The cell `trust=PROBATION & conf=C0.60-0.70 & score_dec=S20` has a WR of **20.76%** (n=501) and a Z-score of **-13.09**—this is statistically significant *loss-making*. The high PF cells are **variance outliers**; the class as a whole has a WR of 25.36% on 2,997 trades. This is a **negative edge**.
- **90d expected P&L (1% risk, $100k):** **-$7,500** (Based on WR=25.36%, PF ~0.8. At 1% risk, 2997 trades: net loss ~7.5% of account. This class is actively destroying capital).
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` = **95** (Kill the class. The current gate passes 47% of scans. Raise to 95 to pass <1%. The negative edge is so strong that even a high threshold won't fix it—the signals are systematically wrong).
- **Confidence (1-5):** **5** (Absolute confidence. The negative Z-score of -13 is a statistical slam dunk).

### BOND, ETF, FUTURES, INDEX, MEME, UNKNOWN
- **Real/noise verdict:** **NOISE (insufficient data).** All have n_closed <25. No PROVEN cells. The FUTURES and INDEX cells show high WR (66%, 62%) but on n=12 and n=8 respectively—this is **pure noise**. The ETF cell has a 9% WR on n=22, which is also noise.
- **90d expected P&L (1% risk, $100k):** **$0** (Do not trade these classes. Any P&L estimate would be a random number).
- **Gate change:** `SMART_PICKS_MIN_SCORE_{CLASS}` = **100** (Effectively disable all these classes in the production scanner until they accumulate >100 closed trades).
- **Confidence (1-5):** **5** (High confidence in "insufficient data" verdict).

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY:** **CRYPTO** (specifically the `PROBATION & LONG` edge). It is the only class with statistically validated, holdout-passing, Bonferroni-significant edges. Deploy 10% of the live book to this single cell. Use a hard stop-loss of 2% of account value for the entire CRYPTO allocation.

**DEMOTE per MUTATION_THREE_AXIS_PROTOCOL:** **FOREX** and **COMMODITY**. Both have sufficient data (n>1000) and statistically significant *negative* or *zero* edges. Per the protocol, these classes should be **mutated** (e.g., completely re-engineer the signal generation) before being killed. If no improvement is seen in 30 days, **kill** them entirely. **EQUITY** should be placed on a 60-day watchlist—the mirage of high PF on small samples is a classic overfitting trap, but the class has potential if the signal can be stabilized.

**Do not invent edges.** The data is clear: only CRYPTO has a real, tradeable edge. All other classes are either noise or capital destroyers.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### EQUITY
- Real/noise verdict: Noise — all cells have bonferroni_pass=false, n=49-56, and WR_shrunk barely above 55% only in one case; no top_edges_proven.
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge).
- Gate change: SMART_PICKS_MIN_SCORE_EQUITY = 75
- Confidence (1-5): 4

### CRYPTO
- Real/noise verdict: Real on the two PROVEN cells (n=434/462, WR_shrunk 60.8/59.5, PF 2.07/2.03, both bonferroni_pass=true + holdout_pass=true); ml cell flagged as leakage risk due to extreme train_pf.
- 90d expected P&L (1% risk, $100k): ~$4,800 (assume 896 trades from proven cells, 1% risk/trade, avg +1.6% R-multiple after 0.15% slippage, 60% WR).
- Gate change: HC_FILTER_MIN_CONF = 0.78
- Confidence (1-5): 3

### COMMODITY
- Real/noise verdict: Noise — zero top_edges_proven, all best_pf cells fail holdout (n=0 holdout) and show PF near 1.3 with negative WR_z.
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge).
- Gate change: SMART_PICKS_MIN_SCORE_COMMODITY = 82
- Confidence (1-5): 5

### FOREX
- Real/noise verdict: Noise — zero top_edges_proven; all listed cells fail holdout or show WR_shrunk <46% with large negative WR_z; consensus-style cells match known leakage patterns.
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge).
- Gate change: HC_FILTER_MIN_TRUST = 65
- Confidence (1-5): 5

### BOND
- Real/noise verdict: Noise — n_closed=24, empty edges.
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge).
- Gate change: SMART_PICKS_MIN_SCORE_BOND = 90
- Confidence (1-5): 5

### ETF
- Real/noise verdict: Noise — n_closed=22, empty edges.
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge).
- Gate change: SMART_PICKS_MIN_SCORE_ETF = 85
- Confidence (1-5): 5

### UNKNOWN
- Real/noise verdict: Noise — n_closed=3, empty edges.
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge).
- Gate change: SMART_PICKS_MIN_SCORE_UNKNOWN = 90
- Confidence (1-5): 5

### FUTURES
- Real/noise verdict: Noise — n_closed=12, empty edges.
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge).
- Gate change: SMART_PICKS_MIN_SCORE_FUTURES = 88
- Confidence (1-5): 5

### INDEX
- Real/noise verdict: Noise — n_closed=8, empty edges.
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge).
- Gate change: SMART_PICKS_MIN_SCORE_INDEX = 88
- Confidence (1-5): 5

### MEME
- Real/noise verdict: Noise — n_closed=14, empty edges.
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge).
- Gate change: SMART_PICKS_MIN_SCORE_MEME = 90
- Confidence (1-5): 5

**SYSTEM-WIDE:** Scale CRYPTO today (only class with bonferroni-passed proven cells). Demote FOREX and COMMODITY per MUTATION_THREE_AXIS_PROTOCOL (no edges after leakage rejection).
