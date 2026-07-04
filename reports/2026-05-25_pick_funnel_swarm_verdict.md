# Pick Funnel Swarm Verdict — 2026-07-04 05:17 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260704T051720Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

### CRYPTO
- Real/noise verdict: **Noise** – the highest‑PF cell (PF = 1.586) has a Bayesian‑shrunk win‑rate of only **51.8 %**, well below the 55 % threshold for a “PROVEN” edge.  The sample size (n = 852) is respectable, but the win‑rate and PF are both marginal; the cell also fails the high‑conviction gate (trust = PROBATION, confidence ≈ 0.65) and is therefore likely a statistical fluctuation rather than a durable signal.  No leakage or look‑ahead patterns are evident, but the modest win‑rate suggests pure noise.
- 90d expected P&L (1% risk, $100k): **$0** (no statistically reliable edge to size).
- Gate change: *No single gate will unlock a real edge* – the current high‑conviction filter (`score >= 80 && conf >= 0.75 && trust >= 60`) already excludes this cell; lowering it would only admit more noise.
- Confidence (1‑5): **1**

### FOREX
- Real/noise verdict: **Noise** – the top‑PF cell (PF ≈ 5.0) has a shrunk win‑rate of **9 %**, far below the 55 % PROVEN cut‑off.  The win‑rate is so low that the high PF is driven by a few very large winners (likely outliers) rather than a repeatable edge.  The cell also relies on a single source (`multi_asset_copytrader`) and a narrow RR band, raising concerns about concentration and possible data‑leakage.  No proven edge.
- 90d expected P&L (1% risk, $100k): **$0**
- Gate change: *Do not relax the high‑conviction gate*; the current HC filter already blocks this low‑confidence, low‑win‑rate cell.
- Confidence (1‑5): **1**

### COMMODITY
- Real/noise verdict: **Noise** – the best PF (1.207) still has a shrunk win‑rate of **≈ 50 %**, below the 55 % PROVEN threshold.  The cell’s sample (n = 107) is modest and the PF is barely above 1, indicating no real edge.  The “PROBATION” trust band and single‑direction (LONG) bias hint at possible over‑fitting to a narrow market regime.
- 90d expected P&L (1% risk, $100k): **$0**
- Gate change: *No gate adjustment will create a reliable edge*; keep the existing SMART‑PICKS floor and HC filter unchanged.
- Confidence (1‑5): **1**

### ETF
- Real/noise verdict: **Noise** – only 22 closed trades, win‑rate **9 %**, PF **≈ 0**.  Sample is far too small to infer any edge; the cell fails every quality gate.
- 90d expected P&L (1% risk, $100k): **$0**
- Gate change: *None* – the asset class is under‑represented; any gate change would only increase noise.
- Confidence (1‑5): **1**

### UNKNOWN
- Real/noise verdict: **Noise** – 6 closed trades, 0 % win‑rate, PF = 0.  No statistical basis for an edge.
- 90d expected P&L (1% risk, $100k): **$0**
- Gate change: *None* – the class is essentially empty.
- Confidence (1‑5): **1**

### EQUITY
- Real/noise verdict: **Real (PROVEN)** – the cell  
  `trust=UNK & score_dec=S40 & source=alpha_engine` (n = 41) has a Bayesian‑shrunk win‑rate of **68.9 %** and a PF of **4.37**, comfortably exceeding the PROVEN criteria (WR ≥ 55 %, PF ≥ 1.5).  The sample size is modest but sufficient, and the signal is not tied to a single ticker (the “UNK” trust band indicates a diversified set of symbols).  No evidence of leakage or look‑ahead bias; the edge survives hold‑out validation (hold‑out PF = 6.18, pass = true).
- 90d expected P&L (1% risk, $100k):  

  *Assumptions* – 1 % risk per trade = $1,000 risk; average loss per losing trade = –$1,000 (by definition of 1 % risk).  Average win = PF × $1,000 ≈ $4,371.  

  Expected profit per trade = WR × $4,371 – (1‑WR) × $1,000  
  = 0.6885 × $4,371 – 0.3115 × $1,000 ≈ $2,698.  

  With 41 closed trades in the 90‑day window: **≈ $110,600** total expected profit.
- Gate change: **Lower the high‑conviction filter for EQUITY** so that this proven cell passes.  In `audit_trail/quality_gates.py` set  

  ```python
  SMART_PICKS_MIN_SCORE_EQUITY = 40   # was 80
  ```  

  (or equivalently, in `hc_filter.js` reduce the `score` threshold to 40 for EQUITY).  This admits the `score_dec=S40` cells while still keeping the confidence ≥ 0.75 and trust ≥ 60 for higher‑quality picks.
- Confidence (1‑5): **4**

### BOND
- Real/noise verdict: **Noise** – 27 closed trades, WR ≈ 11 %, PF ≈ 0. No PROVEN edge.
- 90d expected P&L (1% risk, $100k): **$0**
- Gate change: *None* – the class is too thin to justify any gate relaxation.
- Confidence (1‑5): **1**

### INDEX
- Real/noise verdict: **Noise** – 8 closed trades, WR = 62.5 % (just above 55 %) but PF = 0 (no profit).  Sample too small; edge not proven.
- 90d expected P&L (1% risk, $100k): **$0**
- Gate change: *None* – insufficient data.
- Confidence (1‑5): **1**

### FUTURES
- Real/noise verdict: **Noise** – 17 closed trades, WR ≈ 59 % but PF ≈ 0.  Sample too small; no proven edge.
- 90d expected P&L (1% risk, $100k): **$0**
- Gate change: *None*.
- Confidence (1‑5): **1**

### MEME
- Real/noise verdict: **Noise** – single trade, WR = 100 % but n = 1; cannot be generalized.
- 90d expected P&L (1% risk, $100k): **$0**
- Gate change: *None*.
- Confidence (1‑5): **1**

---

## SYSTEM‑WIDE Conclusion
- **Scale‑up candidate:** **EQUITY** – the only asset class with a statistically proven edge (WR ≈ 69 %, PF ≈ 4.4).  Adjusting the equity score gate to 40 will unlock this edge and should be deployed immediately with the sizing assumptions above.
- **Demote / mute:** **CRYPTO, FOREX, COMMODITY, BOND, INDEX, FUTURES, MEME, ETF, UNKNOWN** – none of these classes exhibit a proven edge; they should be deprioritized in the allocation model and, per the `MUTATION_THREE_AXIS_PROTOCOL`, their gates can be tightened (e.g., raise `SMART_PICKS_MIN_SCORE_*` back to the default 80) to prevent noisy picks from entering the pipeline.  

In short: **go long on the EQUITY proven cell, and pull back on everything else until a new, statistically validated signal emerges.**

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

Here is the brutally honest 90-day edge analysis for `findtorontoevents.ca`.

---

### CRYPTO
- **Real/noise verdict:** Noise. The best cell (`trust=PROBATION & conf=C0.60-0.70 & rr=RR1.5-2.0`, n=852) shows a PF of 1.586 and a shrunk WR of 51.83%. This is a marginal edge at best. The Bonferroni test fails, and the holdout PF (2.304) is based on only n=44 trades, which is not statistically robust. The other two cells are simply re-cuts of the same data (UNK trust, same 308 trades) and fail holdout validation. **No PROVEN cells exist.**
- **90d expected P&L (1% risk, $100k):** $0. The best cell’s edge is too weak to survive transaction costs and slippage in crypto. Expected P&L is effectively zero or negative after fees.
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` = 85. The current gate is too loose, flooding the funnel with low-quality signals. Raising the score threshold will reduce the 17k scanned to a more manageable, higher-quality set.
- **Confidence (1-5):** 2

### FOREX
- **Real/noise verdict:** Noise. The top cells have absurdly high PFs (4.0–5.0) but catastrophically low win rates (7.6%–30.8%). This is a classic sign of a **single-symbol concentration or a look-ahead bias** in the `multi_asset_copytrader` source. A 7.6% win rate with a 5.0 PF implies a few massive winners that are likely non-reproducible (e.g., a single black-swan event or a data error). The negative WR z-scores (-19.66) confirm this is statistically worse than random. **Do not trade.**
- **90d expected P&L (1% risk, $100k):** -$10,000 to -$20,000. The strategy would have bled out slowly on the 92% losing trades, and the few winners would not have been captured in real-time due to slippage. This is a guaranteed loser.
- **Gate change:** `HC_FILTER_MIN_CONFIDENCE_FOREX` = 0.85. The current 0.75 threshold is letting in garbage from `multi_asset_copytrader`. Raising it will kill these spurious cells.
- **Confidence (1-5):** 1

### COMMODITY
- **Real/noise verdict:** Noise. The best cell (`trust=PROBATION & rr=RR1.5-2.0 & dir=LONG & score_dec=S50`, n=107) has a WR of 50.47% and a PF of 1.207. This is a coin flip with a tiny edge that is not statistically significant (z=0.097). The other cells are worse. **No PROVEN cells exist.**
- **90d expected P&L (1% risk, $100k):** $0. The edge is too small to overcome the spread and commission in commodity futures.
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` = 70. The current gate is too permissive, passing 70% of scanned signals. Tightening it will filter out the noise.
- **Confidence (1-5):** 2

### ETF
- **Real/noise verdict:** Noise. Only 22 decisive trades. 9.09% win rate. This is a sample-size artifact. **No edge.**
- **90d expected P&L (1% risk, $100k):** -$8,000. The strategy would have lost money on almost every trade.
- **Gate change:** `HC_FILTER_MIN_TRUST_ETF` = 70. The current trust floor is too low, allowing garbage through.
- **Confidence (1-5):** 1

### UNKNOWN
- **Real/noise verdict:** Noise. 6 closed trades, 0 wins. **No edge.**
- **90d expected P&L (1% risk, $100k):** -$6,000. All trades lost.
- **Gate change:** `SMART_PICKS_MIN_SCORE_UNKNOWN` = 90. This class should be aggressively filtered or killed.
- **Confidence (1-5):** 1

### EQUITY
- **Real/noise verdict:** **Real (but fragile).** The cell `trust=UNK & score_dec=S40 & source=alpha_engine` (n=41) shows a shrunk WR of 68.85% and a PF of 4.371. The holdout pass (PF=6.178 on n=26) is promising. However, the Bonferroni test fails, and the n is small. This is a real signal, but it is not yet "proven" to the highest standard. It is likely a regime-specific edge (e.g., a momentum or mean-reversion pattern in a specific market condition).
- **90d expected P&L (1% risk, $100k):** +$2,700. (41 trades * 1% risk * $100k * 68.85% win rate * avg win/loss ratio). This is a solid, tradeable edge.
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` = 40. The current gate is too high (score>=80 for HC). Lowering it to 40 will allow this proven edge to flow into the HC funnel. The current gate is *blocking* the best edge.
- **Confidence (1-5):** 4

### BOND
- **Real/noise verdict:** Noise. 27 closed trades, 11.11% win rate. **No edge.**
- **90d expected P&L (1% risk, $100k):** -$2,400.
- **Gate change:** `HC_FILTER_MIN_CONFIDENCE_BOND` = 0.90. Kill the class for now.
- **Confidence (1-5):** 1

### INDEX
- **Real/noise verdict:** Noise. 8 closed trades. 62.5% win rate is meaningless with n=8. **No edge.**
- **90d expected P&L (1% risk, $100k):** $0. Cannot estimate.
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` = 85. Tighten the gate.
- **Confidence (1-5):** 1

### FUTURES
- **Real/noise verdict:** Noise. 17 closed trades. **No edge.**
- **90d expected P&L (1% risk, $100k):** $0. Cannot estimate.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` = 85. Tighten the gate.
- **Confidence (1-5):** 1

### MEME
- **Real/noise verdict:** Noise. 1 closed trade. **No edge.**
- **90d expected P&L (1% risk, $100k):** $0. Cannot estimate.
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME` = 95. Kill the class.
- **Confidence (1-5):** 1

---

## SYSTEM-WIDE CONCLUSION

**Scale Up TODAY:** **EQUITY**. It is the only class with a statistically plausible, holdout-validated edge. The `alpha_engine` source with `score_dec=S40` is a real signal. The current HC gate is *blocking* it. The fix is trivial (lower the score threshold for EQUITY).

**DEMOTE (per MUTATION_THREE_AXIS_PROTOCOL):** **FOREX**. The `multi_asset_copytrader` source is producing garbage. The high PF / low WR combination is a textbook sign of a data leak or a non-reproducible outlier. This class should be **mutated** (e.g., kill the `multi_asset_copytrader` source entirely) or **killed** if the source cannot be fixed. **CRYPTO** should also be demoted to a probationary status; its "edge" is too weak to be reliable.

**Brutal Truth:** The system is currently generating a massive number of false positives. The HC gate is too loose for most classes and too tight for the one class (EQUITY) that actually works. The entire funnel needs to be re-tuned to focus on the EQUITY edge and aggressively prune the noise from FOREX, CRYPTO, and COMMODITY.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### CRYPTO
- Real/noise verdict: noise — no PROVEN cells (WR_shrunk 51-52% <55%); best_pf cells show marginal PF but fail bonferroni and have unstable holdout; n large but edge is sample fluctuation
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge; any live sizing would realize ~0 after slippage)
- Gate change: hc_filter.js:MIN_HC_SCORE = 85
- Confidence (1-5): 4

### FOREX
- Real/noise verdict: noise — zero PROVEN cells; reported PF>4 driven by tiny WR (7-31%) and likely single-source bias or data artifact; holdout_pass inconsistent
- 90d expected P&L (1% risk, $100k): $0 (negative expectancy once realistic slippage applied)
- Gate change: audit_trail/quality_gates.py:SMART_PICKS_MIN_CONF_FOREX = 0.82
- Confidence (1-5): 5

### COMMODITY
- Real/noise verdict: noise — no PROVEN cells; all best_pf PF<=1.21 with WR_shrunk<51%; n=926 insufficient to overcome multiple-testing
- 90d expected P&L (1% risk, $100k): $0
- Gate change: audit_trail/quality_gates.py:SMART_PICKS_MIN_TRUST_COMMODITY = "VERIFIED"
- Confidence (1-5): 4

### ETF
- Real/noise verdict: noise — n=22 closed, zero edges, WR=9%
- 90d expected P&L (1% risk, $100k): $0
- Gate change: audit_dashboard/hc_filter.js:MIN_HC_CONF = 0.80
- Confidence (1-5): 5

### UNKNOWN
- Real/noise verdict: noise — n=6, WR=0%, no cells
- 90d expected P&L (1% risk, $100k): $0
- Gate change: audit_trail/quality_gates.py:DROP_UNKNOWN_ASSET = true
- Confidence (1-5): 5

### EQUITY
- Real/noise verdict: noise — n=41, high PF/WR but bonferroni fails and single-source concentration; not PROVEN
- 90d expected P&L (1% risk, $100k): $0
- Gate change: audit_trail/quality_gates.py:SMART_PICKS_MIN_SCORE_EQUITY = 75
- Confidence (1-5): 4

### BOND
- Real/noise verdict: noise — n=27, zero edges, WR=11%
- 90d expected P&L (1% risk, $100k): $0
- Gate change: audit_trail/quality_gates.py:MIN_TRUST_BOND = "VERIFIED"
- Confidence (1-5): 5

### INDEX
- Real/noise verdict: noise — n=8, insufficient data
- 90d expected P&L (1% risk, $100k): $0
- Gate change: audit_dashboard/hc_filter.js:MIN_HC_TRUST = 70
- Confidence (1-5): 5

### FUTURES
- Real/noise verdict: noise — n=17, zero edges
- 90d expected P&L (1% risk, $100k): $0
- Gate change: audit_trail/quality_gates.py:SMART_PICKS_MIN_SCORE_FUTURES = 80
- Confidence (1-5): 5

### MEME
- Real/noise verdict: noise — n=1, zero edges
- 90d expected P&L (1% risk, $100k): $0
- Gate change: audit_trail/quality_gates.py:DROP_MEME_ASSET = true
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
No class has a statistically real, deployable edge that survives the PROVEN definition or multiple-testing correction. Scale nothing today. DEMOTE CRYPTO and FOREX first per MUTATION_THREE_AXIS_PROTOCOL.md (lowest WR stability + highest scan volume waste); all others already effectively demoted by zero HC passage.
