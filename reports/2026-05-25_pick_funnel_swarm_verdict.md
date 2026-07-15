# Pick Funnel Swarm Verdict — 2026-07-15 05:01 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260715T050123Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

### EQUITY
- **Real/noise verdict:** The three “PROVEN” cells all meet the Bayesian‑shrunk win‑rate (≈ 83 %) and profit‑factor (≈ 99) thresholds with n ≈ 40 – 39, so statistically they pass the edge‑validation tests.  However the fact that *trust* is “UNK” and every trade in the cell is a win (40/40) is a classic red‑flag for look‑ahead or data‑leakage (e.g., the signal may be using post‑trade information or a single ticker that happened to rally).  I would flag this edge as **high‑risk of leakage** and recommend a deeper audit of the underlying symbols and timestamps before deployment.
- **90d expected P&L (1 % risk, $100 k):**  
  Avg PnL % ≈ 1.144 % → $1 144 per closed trade.  
  Closed‑trade count = 391 → **≈ $447 k** gross profit over 90 days (before slippage, transaction costs, and possible over‑fit draw‑down).  
  Assuming a modest 0.10 % slippage per trade (≈ $100) the net would be ≈ $447 k – $39 k = **$408 k**.
- **Gate change:** Lower the trust‑threshold in `audit_dashboard/hc_filter.js` (or the corresponding constant in `audit_trail/quality_gates.py`) to allow `trust=UNK`.  
  Example: `HC_TRUST_MIN_EQUITY = 0` (instead of the current 60).  
- **Confidence (1‑5):** 3 – statistically significant but high suspicion of leakage.

### CRYPTO
- **Real/noise verdict:** The single “PROVEN” cell (trust = UNK, dir = LONG, score_dec = S50) has n = 311, WR_shrunk ≈ 65 % and PF ≈ 1.83, comfortably above the PROVEN thresholds.  The sample size is large enough to deem the edge real, and there is no obvious single‑symbol concentration (the cell spans many symbols and the score‑decile filter is a genuine pre‑trade metric).  This edge appears **statistically robust**.
- **90d expected P&L (1 % risk, $100 k):**  
  Avg PnL % ≈ 0.684 % → $684 per closed trade.  
  Closed‑trade count = 3 259 → **≈ $2.23 M** gross profit.  
  Assuming 0.15 % slippage per trade (≈ $150) the net would be ≈ $2.23 M – $489 k = **$1.74 M**.
- **Gate change:** Reduce the minimum score‑decile requirement for crypto in `audit_trail/quality_gates.py` (or the JS filter) from the current 80‑point cut‑off to 50.  
  Example: `SMART_PICKS_MIN_SCORE_CRYPTO = 50` (instead of 80).  
- **Confidence (1‑5):** 4 – solid edge with ample data, modest risk of regime shift.

### FOREX
- **Real/noise verdict:** No “PROVEN” cells; the best PF cells fail the Bonferroni‑adjusted test (PF ≈ 5.35 but WR ≈ 7 % and WR_z = ‑17).  The high PF is driven by a tiny win‑rate and is therefore **noise / over‑fit**.
- **90d expected P&L (1 % risk, $100 k):** $0 (no statistically validated edge).
- **Gate change:** No single gate will create a real edge; the current filters already block the noisy cells.  Further tightening (e.g., require WR ≥ 55 %) would simply keep the noise out.
- **Confidence (1‑5):** 1 – no actionable edge.

### COMMODITY
- **Real/noise verdict:** No “PROVEN” cells; top PF cells have WR ≈ 50 % and PF ≈ 0.94, well below the PROVEN thresholds.  The edge is **sample‑noise**.
- **90d expected P&L (1 % risk, $100 k):** $0.
- **Gate change:** No gate adjustment will produce a statistically real edge; the data suggest the commodity signal is not viable.
- **Confidence (1‑5):** 1.

### ETF
- **Real/noise verdict:** No “PROVEN” cells; closed‑trade count is tiny (23) and win‑rate 8.7 % → noise.
- **90d expected P&L (1 % risk, $100 k):** $0.
- **Gate change:** None needed; the signal should remain disabled.
- **Confidence (1‑5):** 1.

### INDEX
- **Real/noise verdict:** No “PROVEN” cells; n = 8, WR = 62.5 % but far below the required n ≥ 20.  **Noise**.
- **90d expected P&L (1 % risk, $100 k):** $0.
- **Gate change:** None.
- **Confidence (1‑5):** 1.

### FUTURES
- **Real/noise verdict:** No “PROVEN” cells; n = 23, WR ≈ 48 % → noise.
- **90d expected P&L (1 % risk, $100 k):** $0.
- **Gate change:** None.
- **Confidence (1‑5):** 1.

### BOND
- **Real/noise verdict:** No “PROVEN” cells; PF ≈ 0.56, WR ≈ 13 % – clearly **noise**.
- **90d expected P&L (1 % risk, $100 k):** $0.
- **Gate change:** None.
- **Confidence (1‑5):** 1.

### UNKNOWN
- **Real/noise verdict:** No “PROVEN” cells; only 10 closed trades with 0 % win‑rate – **noise**.
- **90d expected P&L (1 % risk, $100 k):** $0.
- **Gate change:** None.
- **Confidence (1‑5):** 1.

### MEME
- **Real/noise verdict:** Single trade (n = 1) with 100 % win‑rate – insufficient sample size; **noise**.
- **90d expected P&L (1 % risk, $100 k):** $0.
- **Gate change:** None.
- **Confidence (1‑5):** 1.

---

## SYSTEM‑WIDE Conclusion
- **Scale‑up today:** **CRYPTO** – the only class with a statistically validated, high‑sample‑size edge (PF ≈ 1.83, WR_shrunk ≈ 65 %).  Adjust the score‑decile gate to 50 and allocate capital (e.g., 20 % of the $100 k account) to the long‑direction UNK‑trust signal.  Expected net profit ≈ $1.7 M over the next 90 days (subject to market regime and execution costs).
- **Demote / kill:** **EQUITY** – despite passing the formal PROVEN test, the edge is almost certainly a leakage artifact (all‑wins, unknown trust).  Until the data‑pipeline audit clears the “UNK” trust flag, this signal should be **mutated out** per the MUTATION_THREE_AXIS_PROTOCOL (e.g., set `HC_TRUST_MIN_EQUITY` to a high value so the cell is excluded).  All other classes (FOREX, COMMODITY, ETF, INDEX, FUTURES, BOND, UNKNOWN, MEME) show no statistically real edge and should remain disabled.

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

### COMMODITY
- Real/noise verdict: **Noise — no PROVEN edges exist.** The best cells show WR ~50% with PF < 1.0, holdout_pass=false, and bonferroni_pass=false. The 29.28% overall WR on 765 decisive trades confirms no edge. The rejected H-001 (COT look-ahead) and H-036 (inventory direction) further confirm this class is unreliable.
- 90d expected P&L (1% risk, $100k): **-$2,890** (765 decisive trades × 1% risk × $100k × (0.2928 WR - 0.7072 loss rate × 1.0 avg loss) = 765 × $1,000 × (0.2928 - 0.7072) = -$317,000? Wait — recalc: 224 wins, 541 losses. Avg win = +1.0R, avg loss = -1.0R (assuming 1:1 R:R typical). P&L = 224 × $1,000 - 541 × $1,000 = -$317,000. But that's absurd — the WR is so low that 1% risk sizing would blow the account. Realistic: max 0.25% risk per trade given negative expectancy. Expected P&L = -$79,250. **Verdict: negative expectancy, do not trade.**
- Gate change: `SMART_PICKS_MIN_SCORE_COMMODITY` = 95 (raise from current 80 to filter out noise; currently 72.4% pass rate is too permissive)
- Confidence (1-5): **1** — no statistical evidence of edge; rejected hypotheses confirm data leakage history

### FOREX
- Real/noise verdict: **Noise — zero PROVEN edges.** The "best" cells show bonferroni_pass=false, holdout_pass=false, and suspicious PF values (5.35, 4.043, 3.51) with WR below 58%. The `rr=RR1.5-2.0 & dir=LONG & source=multi_asset_copytrader` cell with n=423, WR=7.33%, PF=5.35 is a classic **leakage signal**: extremely low WR but high PF means a few massive winners are distorting the metric — likely a single outlier trade or data error. The 28.08% overall WR on 2,137 decisive trades confirms no systematic edge.
- 90d expected P&L (1% risk, $100k): **-$937,000** (600 wins × $1,000 - 1,537 losses × $1,000 = -$937,000). Even at 0.1% risk: -$93,700. **Negative expectancy — do not trade.**
- Gate change: `SMART_PICKS_MIN_SCORE_FOREX` = 90 (raise from 80; current 67.6% pass rate floods the funnel with noise)
- Confidence (1-5): **1** — zero PROVEN edges, suspicious outlier-driven PF values, massive negative expectancy

### EQUITY
- Real/noise verdict: **Real edge, but fragile.** The PROVEN cells show 100% WR on n=40, WR_shrunk=83.33%, PF=99.0, bonferroni_pass=true, holdout_pass=true. However, this is suspicious: 40/40 wins with avg_pnl_pct=1.14% suggests either (a) a genuine micro-edge in mean reversion, or (b) **single-symbol concentration** — all 40 trades could be the same stock (e.g., SPY mean reversion during low-volatility regime). The 44.25% overall WR on 391 decisive trades is respectable but not exceptional. **Flag: verify these 40 trades are not all the same symbol.**
- 90d expected P&L (1% risk, $100k): **+$3,910** (173 wins × $1,000 - 218 losses × $1,000 = -$45,000? No — 44.25% WR means negative expectancy at 1:1 R:R. But avg_pnl_pct=1.14% on wins vs unknown loss size. If avg loss = -0.8%: P&L = 173 × $1,140 - 218 × $800 = $197,220 - $174,400 = +$22,820. **Cautiously positive, but only if the 40/40 cell generalizes.** Realistic: +$5,000 to +$15,000 given small sample.
- Gate change: `SMART_PICKS_MIN_SCORE_EQUITY` = 70 (lower from 80 to capture more mean reversion signals; currently only 3.8% pass rate is too restrictive)
- Confidence (1-5): **3** — PROVEN edges exist but sample is small (n=40) and may be single-symbol concentrated

### CRYPTO
- Real/noise verdict: **Real edge, statistically robust.** The PROVEN cell `trust=UNK & dir=LONG & score_dec=S50` has n=311, WR=66.24%, WR_shrunk=65.26%, PF=1.826, bonferroni_pass=true, holdout_pass=true. The 46.39% overall WR on 3,259 decisive trades is the best among major classes. The 1,417 verified_alpha passes (54% of smart picks) indicate strong signal capture. **This is the most reliable edge in the system.**
- 90d expected P&L (1% risk, $100k): **+$1,265,000** (1,512 wins × $1,000 - 1,747 losses × $1,000 = -$235,000? No — avg_pnl_pct=0.6841% on wins, assume avg loss = -0.5%. P&L = 1,512 × $684 - 1,747 × $500 = $1,034,208 - $873,500 = +$160,708. But the PROVEN cell alone (n=311, WR=66.24%, PF=1.826) suggests better. At 1% risk on only the PROVEN cell trades: 206 wins × $1,000 - 105 losses × $1,000 = +$101,000. **Realistic total: +$150,000 to +$250,000.**
- Gate change: `SMART_PICKS_MIN_SCORE_CRYPTO` = 60 (lower from 80 to capture more LONG signals in the S50 score band; currently only 16.5% pass rate is too restrictive)
- Confidence (1-5): **5** — large sample (n=311), statistical significance (z=5.728), holdout validation passed, bonferroni corrected

### ETF
- Real/noise verdict: **Noise — insufficient data.** Only 23 decisive trades, 8.7% WR. No PROVEN edges. The 2 wins vs 21 losses on n=23 is statistically significant (p<0.001) but in the wrong direction — this is an anti-edge. **Do not trade.**
- 90d expected P&L (1% risk, $100k): **-$19,000** (2 × $1,000 - 21 × $1,000 = -$19,000)
- Gate change: `SMART_PICKS_MIN_SCORE_ETF` = 95 (effectively disable; current 53.4% pass rate is meaningless with n=481 scanned)
- Confidence (1-5): **1** — no edge, tiny sample, negative WR

### UNKNOWN
- Real/noise verdict: **Noise — data quality issue.** 0% WR on 10 decisive trades, but 572 opened vs 10 closed suggests most trades are still open or were never executed. The UNKNOWN class likely contains misclassified assets. **Fix classification, don't trade.**
- 90d expected P&L (1% risk, $100k): **-$10,000** (0 × $1,000 - 10 × $1,000 = -$10,000)
- Gate change: Add classification validation gate in `alpha_engine/production_scanner.py` to reject UNKNOWN assets before scoring
- Confidence (1-5): **1** — data quality issue, not a tradable class

### INDEX
- Real/noise verdict: **Noise — insufficient data.** 62.5% WR on only 8 decisive trades. No PROVEN edges. The 5 wins vs 3 losses is not statistically significant (p=0.36). **Do not trade.**
- 90d expected P&L (1% risk, $100k): **+$2,000** (5 × $1,000 - 3 × $1,000 = +$2,000, but variance is extreme)
- Gate change: `SMART_PICKS_MIN_SCORE_INDEX` = 85 (raise from 80; current 65.8% pass rate is too permissive for n=634)
- Confidence (1-5): **1** — tiny sample, no statistical significance

### FUTURES
- Real/noise verdict: **Noise — insufficient data.** 47.83% WR on only 23 decisive trades. No PROVEN edges. The rejected H-005 confirms momentum strategies fail here. **Do not trade.**
- 90d expected P&L (1% risk, $100k): **-$1,000** (11 × $1,000 - 12 × $1,000 = -$1,000)
- Gate change: `SMART_PICKS_MIN_SCORE_FUTURES` = 90 (raise from 80; current 84.5% pass rate is too permissive)
- Confidence (1-5): **1** — tiny sample, no edge, rejected hypotheses

### BOND
- Real/noise verdict: **Noise — negative edge.** 12.9% WR on 31 decisive trades. Best cells show WR=9.5-15% with PF<0.6. This is a statistically significant anti-edge (p<0.001). **Inverse would be profitable, but don't — too few trades.**
- 90d expected P&L (1% risk, $100k): **-$23,000** (4 × $1,000 - 27 × $1,000 = -$23,000)
- Gate change: `SMART_PICKS_MIN_SCORE_BOND` = 95 (effectively disable; current 6.2% pass rate is already low but still produces negative edge)
- Confidence (1-5): **1** — statistically significant negative edge, tiny sample

### MEME
- Real/noise verdict: **Noise — insufficient data.** 100% WR on 1 decisive trade. No PROVEN edges. **Do not trade.**
- 90d expected P&L (1% risk, $100k): **+$1,000** (1 × $1,000 - 0 × $1,000 = +$1,000, but meaningless)
- Gate change: `SMART_PICKS_MIN_SCORE_MEME` = 95 (effectively disable; n=6 scanned is negligible)
- Confidence (1-5): **1** — single trade, no statistical significance

---

## SYSTEM-WIDE CONCLUSION

### Scale Up TODAY with Real Money:
**CRYPTO** — This is the only class with statistically robust, holdout-validated, bonferroni-corrected PROVEN edges. The 46.39% overall WR on 3,259 trades is the best in the system. The `trust=UNK & dir=LONG & score_dec=S50` cell (n=311, WR=66.24%, PF=1.826) is the single strongest signal. **Recommend allocating 40-60% of trading capital to CRYPTO LONG signals with score_dec=S50.**

### DEMOTE per MUTATION_THREE_AXIS_PROTOCOL:
**FOREX** and **COMMODITY** should be **mutated before killed**. Both have:
- Zero PROVEN edges after 90 days
- Overall WR below 30% on large samples (2,137 and 765 decisive trades)
- Rejected hypotheses confirming data leakage (H-001 for COMMODITY)
- Suspicious PF values suggesting outlier-driven metrics

**Proposed mutation for FOREX:** Restrict to only `source=multi_asset_copytrader` signals with `conf>=0.80` and `rr>=2.0` — the current 67.6% pass rate is flooding the funnel with noise. If after 30 days no PROVEN edges emerge, **kill FOREX entirely.**

**Proposed mutation for COMMODITY:** Restrict to only `trust=PROBATION` signals (currently the only band with any n>20 cells) and require `conf>=0.80`. The 72.4% pass rate is too permissive. If after 30 days no PROVEN edges emerge, **kill COMMODITY entirely.**

**EQUITY** is a **hold with caution** — the 40/40 cell is promising but needs verification it's not single-symbol concentration. Recommend manual review of those 40 trades before scaling.

**All other classes (ETF, UNKNOWN, INDEX, FUTURES, BOND, MEME)** should be **immediately killed** — insufficient data, no edges, and in BOND's case, a statistically significant anti-edge.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### COMMODITY
- Real/noise verdict: noise (no proven cells; best_pf PF<1.0, holdout failures, known COT leakage history)
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge)
- Gate change: SMART_PICKS_MIN_SCORE_COMMODITY = 999 (disable)
- Confidence (1-5): 5

### FOREX
- Real/noise verdict: noise (no proven cells; best_pf show holdout failures + negative WR_z)
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge)
- Gate change: HC_MIN_CONF = 0.90 (raise to choke low-quality flow)
- Confidence (1-5): 5

### EQUITY
- Real/noise verdict: noise/leakage (100% WR on n=40 with PF=99 is impossible; single-symbol concentration or alpha_engine bug)
- 90d expected P&L (1% risk, $100k): $0 (reject all cells)
- Gate change: SMART_PICKS_MIN_SCORE_EQUITY = 999 (disable)
- Confidence (1-5): 5

### CRYPTO
- Real/noise verdict: statistically real (n=311, WR_shrunk=65.26, PF=1.826, holdout_pass=true, bonferroni_pass=true)
- 90d expected P&L (1% risk, $100k): +$2,120 (311 trades × 1% risk × 0.6841% avg_pnl, 0.2% slippage, 0.1% commission)
- Gate change: HC_MIN_SCORE = 50 (lower to capture S50 band)
- Confidence (1-5): 4

### ETF
- Real/noise verdict: noise (n=23 total, no proven cells, PF<<1)
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge)
- Gate change: SMART_PICKS_MIN_SCORE_ETF = 999 (disable)
- Confidence (1-5): 5

### UNKNOWN
- Real/noise verdict: noise (n=10, no edges)
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge)
- Gate change: none (class should be dropped)
- Confidence (1-5): 5

### INDEX
- Real/noise verdict: noise (n=8, no edges)
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge)
- Gate change: SMART_PICKS_MIN_SCORE_INDEX = 999 (disable)
- Confidence (1-5): 5

### FUTURES
- Real/noise verdict: noise (n=23, no edges, prior momentum inversion rejected)
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge)
- Gate change: SMART_PICKS_MIN_SCORE_FUTURES = 999 (disable)
- Confidence (1-5): 5

### BOND
- Real/noise verdict: noise (n=31, best_pf PF<0.6, negative WR_z)
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge)
- Gate change: SMART_PICKS_MIN_SCORE_BOND = 999 (disable)
- Confidence (1-5): 5

### MEME
- Real/noise verdict: noise (n=1, no edges)
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge)
- Gate change: none (class should be dropped)
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale CRYPTO today (only proven cell meeting all statistical gates). DEMOTE EQUITY, COMMODITY, FOREX, BOND, FUTURES, ETF, INDEX, UNKNOWN, MEME per MUTATION_THREE_AXIS_PROTOCOL.md (no surviving edges after leakage rejection).
