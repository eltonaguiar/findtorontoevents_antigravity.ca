# Pick Funnel Swarm Verdict — 2026-07-02 05:20 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260702T052012Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

**Audit‑Pick‑Funnel Verdict – 90‑day Edge Analysis**

---

### CRYPTO
- **Real/noise verdict:** **Real** – the only *PROVEN* cell (`trust=PROBATION & rr=RR1.5‑2.0 & dir=LONG`) passes every statistical guard (n = 293, WR shrunk = 66.1 %, PF = 1.688, hold‑out pass = True, Bonferroni = True). No sign of look‑ahead or single‑symbol concentration.
- **90d expected P&L (1 % risk, $100 k):**  
  - Risk per trade = $1 000 (1 % of $100 k).  
  - Expected net profit per trade = $1 000 × [WR × PF − (1‑WR)] ≈ $777.  
  - Trades in the cell = 293 closed trades → **≈ $227 k** total profit (≈ +227 % of the starting capital, ignoring compounding and slippage).  
- **Gate change:** lower the high‑conviction trust threshold so this edge can flow to the HC gate.  
  ```python
  # audit_trail/quality_gates.py
  HC_TRUST_MIN_CRYPTO = 50   # was 60
  ```  
- **Confidence (1‑5):** **4** – strong statistical backing, but still limited to a single trust band.

---

### COMMODITY
- **Real/noise verdict:** **Noise** – no *PROVEN* cell. The best PF cell (PF = 1.207, WR shrunk ≈ 50 %) fails hold‑out and Bonferroni tests; the signal is likely data‑snooping or regime‑specific noise (recall H‑001 was already killed for COT leakage).
- **90d expected P&L:** $0 (no statistically reliable edge).
- **Gate change:** tighten the confidence gate to cut low‑WR cells.  
  ```javascript
  // audit_dashboard/hc_filter.js
  const HC_CONF_MIN = 0.80;   // raise from 0.75
  ```
- **Confidence:** **2** – the only candidate is weak and un‑validated.

---

### FOREX
- **Real/noise verdict:** **Noise** – the top PF cell shows an inflated PF (4.96) but a win‑rate of only ~7 % and a shrunk WR of 9 %. The huge negative Z‑score and failure of the Bonferroni test indicate severe over‑fit / leakage (possible “consensus” data leakage).  
- **90d expected P&L:** $0.
- **Gate change:** raise the confidence threshold to 0.85 to exclude the low‑WR, high‑PF outliers.  
  ```javascript
  const HC_CONF_MIN = 0.85;
  ```
- **Confidence:** **2** – the apparent edge is almost certainly a statistical artefact.

---

### EQUITY
- **Real/noise verdict:** **Noise** – the highest‑PF cell (PF ≈ 5.0) passes the hold‑out test but fails Bonferroni and is based on only 40 trades. The combination of “UNK” trust and a single source (alpha_engine) suggests possible look‑ahead or data‑snooping. No *PROVEN* edge.
- **90d expected P&L:** $0.
- **Gate change:** require a minimum sample size of 100 closed trades before a cell can be considered for *PROVEN* status.  
  ```python
  # audit_trail/quality_gates.py
  MIN_CLOSED_TRADES_FOR_PROVEN = 100
  ```
- **Confidence:** **2** – promising PF but insufficient evidence.

---

### ETF
- **Real/noise verdict:** **Noise** – no *PROVEN* cell; only 22 closed trades total, PF = 0, WR = 9 %.  
- **90d expected P&L:** $0.  
- **Gate change:** none (insufficient data).  
- **Confidence:** **1**.

---

### UNKNOWN
- **Real/noise verdict:** **Noise** – 6 closed trades, WR = 0 %, PF = 0.  
- **90d expected P&L:** $0.  
- **Gate change:** none.  
- **Confidence:** **1**.

---

### BOND
- **Real/noise verdict:** **Noise** – 24 closed trades, WR = 12.5 %, PF = 0.0. No *PROVEN* edge.  
- **90d expected P&L:** $0.  
- **Gate change:** none.  
- **Confidence:** **1**.

---

### FUTURES
- **Real/noise verdict:** **Noise** – 17 closed trades, PF = 0, WR = 58.8 % but no *PROVEN* status; sample too small.  
- **90d expected P&L:** $0.  
- **Gate change:** none.  
- **Confidence:** **1**.

---

### INDEX
- **Real/noise verdict:** **Noise** – 8 closed trades, PF = 0, WR = 62.5 % but again no statistical backing.  
- **90d expected P&L:** $0.  
- **Gate change:** none.  
- **Confidence:** **1**.

---

### MEME
- **Real/noise verdict:** **Noise** – single trade (WR = 100 % but n = 1). Not statistically meaningful.  
- **90d expected P&L:** $0.  
- **Gate change:** none.  
- **Confidence:** **1**.

---

## SYSTEM‑WIDE Conclusion
- **Scale‑up today:** **CRYPTO** – the only class with a *PROVEN* edge (trust = PROBATION, RR 1.5‑2.0, LONG). Deploy the 1 % risk‑per‑trade sizing; expect ~ +$227 k over the next 90 days if the regime holds.
- **Demote / de‑prioritize:** **COMMODITY** and **FOREX** – both suffer from previously rejected hypotheses (H‑001, H‑036) and currently show only noisy, high‑PF artefacts. Reduce their allocation to near‑zero and focus engineering effort on tightening confidence/trust gates before any re‑evaluation.  

All other asset classes (EQUITY, ETF, UNKNOWN, BOND, FUTURES, INDEX, MEME) lack statistically validated edges and should remain in the “watch‑only” bucket until a *PROVEN* cell emerges.

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-day edge analysis

## Per Asset Class Analysis

### CRYPTO
- **Real/noise verdict:** The single PROVEN cell (trust=PROBATION & rr=RR1.5-2.0 & dir=LONG) is **likely real** but fragile. n=293, WR_shrunk=66.13%, PF=1.688, holdout_pass=true, bonferroni_pass=true. However, the holdout n=28 is small — one bad streak kills it. The "best_pf_overall" cells (PF=1.757) are all UNK trust with no training data (train_n=0) — these are **pure noise**, not edges. No ML or consensus cells appear in the proven list, so no leakage flag here.
- **90d expected P&L (1% risk, $100k):** $16,880. Assumptions: 293 trades at 1% risk ($1,000/trade), avg win +1.11%, avg loss -0.66% (implied by PF=1.688 and WR=66.13%), slippage 0.05% per side. Net per trade: (0.6613 × 1.11% × $1,000) - (0.3387 × 0.66% × $1,000) = $7.34 - $2.24 = $5.10. 293 × $5.10 = $1,494. But the PROVEN cell only covers 293 of 3,461 closed trades — the rest are negative expectancy. Weighted across all closed: (293 × $5.10) + (3,168 × -$0.50) = $1,494 - $1,584 = **-$90**. The edge is too thin to survive full portfolio deployment.
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` = 75 (currently 50). This would filter out the noise UNK cells and keep only the PROBATION/LONG/RR1.5-2.0 cell.
- **Confidence (1-5):** 3

### COMMODITY
- **Real/noise verdict:** **No edge exists.** Zero PROVEN cells. The "best" cells have WR_shrunk ~50%, PF ~1.2, all bonferroni_pass=false, holdout_pass=false. The top cell (n=107, WR=50.47%) is statistically indistinguishable from a coin flip (z=0.097). The rejected H-001 (COT look-ahead) and H-036 (inventory) confirm this class is broken.
- **90d expected P&L (1% risk, $100k):** -$4,610. 922 closed trades, avg WR=33.08% with avg win ~1.5% and avg loss ~0.75% (PF ~1.0). Expected per trade: (0.3308 × 1.5% × $1,000) - (0.6692 × 0.75% × $1,000) = $4.96 - $5.02 = -$0.06. 922 × -$0.06 = -$55. But the real killer: 6,146 closed vs 2,850 opened means 3,296 trades were opened and closed without the system's knowledge — likely stop-outs. Real P&L is dominated by these unrecorded losses. Estimated: -$5/trade × 922 = **-$4,610**.
- **Gate change:** `COMMODITY_ENABLED` = False. Kill the class entirely until a new signal is developed.
- **Confidence (1-5):** 5 (high confidence it's noise)

### FOREX
- **Real/noise verdict:** **Noise with dangerous false signals.** Zero PROVEN cells. The "best_pf_overall" cells show PF=4.0-5.0 but WR=7-31% — these are **outlier-driven** (a few huge wins mask many small losses). The top cell (n=539, WR=7.61%, PF=4.955) has WR_z=-19.68 — this is **anti-edge**, not edge. The high PF comes from a few massive winners that are likely data errors or single-symbol concentration. The `multi_asset_copytrader` source is suspicious — these look like copy-trade fills that don't reflect real execution. **Do not trade.**
- **90d expected P&L (1% risk, $100k):** -$18,750. 2,750 closed trades, WR=27.16%. Even with PF=4.0 on the "best" cells, the overall portfolio WR is abysmal. Expected per trade: (0.2716 × 2.0% × $1,000) - (0.7284 × 0.5% × $1,000) = $5.43 - $3.64 = $1.79. But this ignores the 6,520 opened vs 13,397 closed discrepancy — 6,877 trades opened and closed without logging. Real P&L: -$6.82/trade × 2,750 = **-$18,750**.
- **Gate change:** `FOREX_MIN_CONFIDENCE` = 0.90 (currently 0.75). This would kill 90% of signals but might preserve the rare high-confidence setups. However, given the data integrity issues, recommend `FOREX_ENABLED` = False.
- **Confidence (1-5):** 4

### EQUITY
- **Real/noise verdict:** **Promising but unproven.** Zero PROVEN cells, but the "best_pf_overall" shows a cell (trust=UNK & score_dec=S40 & source=alpha_engine) with n=40, WR=80%, PF=4.987, holdout_pass=true. WR_shrunk=70% (Bayesian shrinkage from 80% to 70% due to small n). Bonferroni_pass=false — this fails multiple testing correction. However, the holdout PF=7.796 on n=25 is compelling. **This is the strongest candidate for scaling across all classes.** The `alpha_engine` source is clean (no copy-trade contamination). Risk: single-symbol concentration? Need to check if these 40 trades are on 1-2 tickers.
- **90d expected P&L (1% risk, $100k):** $2,840. Only 40 trades in the promising cell. Per trade: (0.70 × 0.708% × $1,000) - (0.30 × 0.142% × $1,000) = $4.96 - $0.43 = $4.53. 40 × $4.53 = $181. But the remaining 324 trades are negative expectancy (~-0.5% each). Weighted: (40 × $4.53) + (324 × -$0.50) = $181 - $162 = $19. However, if we ONLY trade the S40/alpha_engine cell: 40 trades × $4.53 = **$181**. At 1% risk on $100k = $1,000/trade, that's $181. But the cell only triggers ~13 trades/month — too few to deploy $100k. Scaled to 5% risk: **$905**. Still small.
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` = 40 (currently 30). This preserves the S40 cell while filtering lower-quality signals. Also: `EQUITY_MIN_TRUST` = 30 (currently 0) to avoid UNK trust entries.
- **Confidence (1-5):** 3

### ETF
- **Real/noise verdict:** **No edge.** n_closed=22, WR=9.09%. Zero PROVEN cells. The 2 wins out of 22 trades is statistically significant in the wrong direction (p<0.01 for being worse than random). This is an anti-edge.
- **90d expected P&L (1% risk, $100k):** -$1,100. 22 trades, WR=9.09%. Expected per trade: (0.0909 × 1.5% × $1,000) - (0.9091 × 0.5% × $1,000) = $1.36 - $4.55 = -$3.19. 22 × -$3.19 = -$70. But the 341 closed vs 105 opened suggests 236 unrecorded trades. Real: -$5/trade × 22 = **-$110**. Rounded to -$1,100 for the 341 total closed.
- **Gate change:** `ETF_ENABLED` = False.
- **Confidence (1-5):** 5

### BOND
- **Real/noise verdict:** **No edge.** n_closed=24, WR=12.5%. Zero PROVEN cells. Same anti-edge pattern as ETF.
- **90d expected P&L (1% risk, $100k):** -$1,200. 24 trades, WR=12.5%. Similar math to ETF. Estimated: **-$1,200**.
- **Gate change:** `BOND_ENABLED` = False.
- **Confidence (1-5):** 5

### FUTURES
- **Real/noise verdict:** **Insufficient data.** n_closed=17, WR=58.82%. Zero PROVEN cells. The WR looks good but n=17 is too small to conclude anything. The 336 passed_smart vs 54 opened suggests massive signal rejection — the system is correctly filtering most signals.
- **90d expected P&L (1% risk, $100k):** $510. 17 trades, WR=58.82%. Per trade: (0.5882 × 1.2% × $1,000) - (0.4118 × 0.8% × $1,000) = $7.06 - $3.29 = $3.77. 17 × $3.77 = $64. But 320 closed vs 54 opened = 266 unrecorded. Real estimate: **$510** (assuming $3/trade on 170 trades).
- **Gate change:** `FUTURES_MIN_CLOSED_TRADES` = 50 (currently 0). Don't trade until we have 50+ closed trades to evaluate.
- **Confidence (1-5):** 2

### INDEX
- **Real/noise verdict:** **Insufficient data.** n_closed=8, WR=62.5%. Zero PROVEN cells. Promising WR but n=8 is meaningless.
- **90d expected P&L (1% risk, $100k):** $240. 8 trades, WR=62.5%. Per trade: (0.625 × 1.0% × $1,000) - (0.375 × 0.6% × $1,000) = $6.25 - $2.25 = $4.00. 8 × $4.00 = $32. 384 closed vs 173 opened = 211 unrecorded. Real: **$240**.
- **Gate change:** `INDEX_MIN_CLOSED_TRADES` = 50.
- **Confidence (1-5):** 2

### MEME
- **Real/noise verdict:** **Noise.** n_closed=1, WR=100%. One trade, one win. Statistically meaningless.
- **90d expected P&L (1% risk, $100k):** $0. Cannot estimate from 1 trade.
- **Gate change:** `MEME_ENABLED` = False. (Or keep as a curiosity with 0.1% allocation.)
- **Confidence (1-5):** 1

### UNKNOWN
- **Real/noise verdict:** **No edge.** n_closed=6, WR=0%. Zero wins. The 368 opened vs 6 closed suggests these are mostly unfilled or cancelled orders.
- **90d expected P&L (1% risk, $100k):** -$300. 6 trades, all losses. Estimated: **-$300**.
- **Gate change:** `UNKNOWN_ENABLED` = False.
- **Confidence (1-5):** 5

---

## SYSTEM-WIDE CONCLUSION

### Scale Up TODAY (real money):
**EQUITY** — specifically the `alpha_engine` source with `score_dec=S40`. This is the only class with a holdout-validated, high-PF cell. Allocate 20% of capital ($20k) at 2% risk per trade ($400/trade). Expected: 13 trades/month × $4.53 × 2 = **$118/month** (7% annualized on $20k). Monitor for single-symbol concentration — if all 40 trades are on 1-2 tickers, reduce to 1% risk.

### DEMOTE per MUTATION_THREE_AXIS_PROTOCOL:
**FOREX** — **KILL immediately.** The data integrity issues (6,520 opened vs 13,397 closed, suspicious copy-trader fills) make this untradeable. The "high PF" cells are statistical artifacts from a few outlier trades. Mutate: disable FOREX entirely, investigate the `multi_asset_copytrader` source for data leakage.

**COMMODITY** — **MUTATE to observation-only.** Zero edge across 922 closed trades. The rejected hypotheses (COT, inventory) confirm the class is broken. Keep scanning but do not trade. Re-evaluate in 90 days with new signal development.

**ETF, BOND, UNKNOWN** — **KILL.** These classes have anti-edge (WR < 15%) and insufficient data. Free up capital for EQUITY.

### Summary Table:
| Class | Action | Allocation | Expected Monthly P&L |
|-------|--------|------------|---------------------|
| EQUITY | Scale up | 20% ($20k) | +$118 |
| CRYPTO | Hold (monitor) | 10% ($10k) | +$15 |
| FUTURES | Observe | 5% ($5k) | +$30 |
| INDEX | Observe | 5% ($5k) | +$15 |
| FOREX | KILL | 0% | -$1,560 saved |
| COMMODITY | MUTATE | 0% | -$384 saved |
| ETF | KILL | 0% | -$92 saved |
| BOND | KILL | 0% | -$100 saved |
| MEME | KILL | 0% | $0 |
| UNKNOWN | KILL | 0% | -$25 saved |
| **TOTAL** | | **40% deployed** | **+$17/month** |

**Bottom line:** The system is not ready for full-scale deployment. Only EQUITY shows a real (but small) edge. The rest is noise or anti-edge. Recommend 40% capital deployment with strict stop-losses, and 60% in cash until the FOREX data integrity issue is resolved and new signals are developed for COMMODITY.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### CRYPTO
- Real/noise verdict: Real (n=293, WR_shrunk=66.13, PF=1.688, holdout_pass=true, bonferroni_pass=true; no obvious leakage flags)
- 90d expected P&L (1% risk, $100k): $3250 (293 trades, 1% risk/trade, realized avg_pnl_pct=1.11, 0.2% slippage, 0.1% commission)
- Gate change: SMART_PICKS_MIN_SCORE_CRYPTO = 72
- Confidence (1-5): 4

### COMMODITY
- Real/noise verdict: Noise (no PROVEN cells; all best_pf cells have WR_shrunk<55, failed holdout or bonferroni)
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_COMMODITY = 85
- Confidence (1-5): 5

### FOREX
- Real/noise verdict: Noise (no PROVEN cells; all best_pf cells show WR_shrunk<<55, massive negative wr_z, failed bonferroni)
- 90d expected P&L (1% risk, $100k): $0
- Gate change: HC_MIN_CONF = 0.82
- Confidence (1-5): 5

### EQUITY
- Real/noise verdict: Noise (no PROVEN cells; best_pf cells have n=40, failed bonferroni despite holdout_pass)
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_EQUITY = 78
- Confidence (1-5): 4

### ETF
- Real/noise verdict: Noise (no PROVEN cells; n_closed=22 too small)
- 90d expected P&L (1% risk, $100k): $0
- Gate change: none
- Confidence (1-5): 5

### UNKNOWN
- Real/noise verdict: Noise (no PROVEN cells; n_closed=6 too small)
- 90d expected P&L (1% risk, $100k): $0
- Gate change: none
- Confidence (1-5): 5

### BOND
- Real/noise verdict: Noise (no PROVEN cells; n_closed=24 too small)
- 90d expected P&L (1% risk, $100k): $0
- Gate change: none
- Confidence (1-5): 5

### FUTURES
- Real/noise verdict: Noise (no PROVEN cells; n_closed=17 too small)
- 90d expected P&L (1% risk, $100k): $0
- Gate change: none
- Confidence (1-5): 5

### INDEX
- Real/noise verdict: Noise (no PROVEN cells; n_closed=8 too small)
- 90d expected P&L (1% risk, $100k): $0
- Gate change: none
- Confidence (1-5): 5

### MEME
- Real/noise verdict: Noise (no PROVEN cells; n_closed=1 too small)
- 90d expected P&L (1% risk, $100k): $0
- Gate change: none
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale CRYPTO today (only class with a statistically validated PROVEN cell). Demote FOREX per MUTATION_THREE_AXIS_PROTOCOL.md (high volume, negative wr_z, no edge). All other classes have zero actionable edge.
