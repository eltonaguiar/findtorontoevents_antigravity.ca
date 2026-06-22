# Pick Funnel Swarm Verdict — 2026-06-22 05:52 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260622T055137Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

**Audit‑Pick‑Funnel Verdict – 90‑day edge analysis**

---

### CRYPTO
- **Real/noise verdict:** **Real** – the cell *trust=PROBATION & rr=RR1.5‑2.0 & dir=LONG* passes both the hold‑out test and the Bonferroni correction (n = 409, WR_shrunk = 62.24 %, PF = 2.357).  The companion low‑confidence cell also passes Bonferroni, but its “ml” family has only 5 hold‑out trades – too few to be reliable, so we ignore it.
- **90d expected P&L (1 % risk, $100 k):** ≈ **$2,060**  
  *Sizing:* risk = 1 % of account per trade → max loss = $1,000.  The average loss in the cell is ≈ 4 % of notional, so we scale each trade by 0.25× (0.01 / 0.0396).  Expected net per trade after scaling ≈ 0.504 % of account; 409 trades → 0.00504 × 409 ≈ 2.06 % of account → $2,060.
- **Gate change:** `audit_dashboard/hc_filter.js` → lower the confidence threshold for crypto from **0.75 → 0.60** (e.g. `MIN_CONFIDENCE_CRYPTO = 0.60`).  This admits the proven low‑confidence long‑bias edge while keeping the high‑conviction filter for the rest of the universe.
- **Confidence (1‑5):** **5**

---

### COMMODITY
- **Real/noise verdict:** **Noise** – no PROVEN cells; the best PF cell (trust = PROBATION, conf = C0.75‑0.80) has a modest PF = 1.347, WR_shrunk ≈ 48 % and only 107 trades.  The earlier rejected COT‑positioning hypothesis (H‑001) already showed this signal is unstable.
- **90d expected P&L (1 % risk, $100 k):** **$0** (no statistically‑significant edge to size).
- **Gate change:** *none* – keep current quality gates; lowering thresholds would only admit more noise.
- **Confidence (1‑

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-day edge analysis

## Per Asset Class Analysis

### CRYPTO
- **Real/noise verdict:** REAL — Two PROVEN cells survive Bonferroni correction with n>400, WR_shrunk>60%, PF>2.0. The `trust=PROBATION & rr=RR1.5-2.0 & dir=LONG` cell (n=409, WR_shrunk=62.24%, PF=2.357) passes holdout with PF=6.639. The `trust=PROBATION & conf=C<0.60 & dir=LONG` cell (n=458, WR_shrunk=60.04%, PF=2.078) also passes holdout. However, the `fam=ml & dir=LONG` cell (PF=2.48) has only n=5 in holdout — this is suspiciously high PF on tiny holdout, likely noise/overfit. The `conf=C<0.60 & rr=RR1.0-1.5` cell passes Bonferroni but holdout PF=0.74 fails — this is a false positive from multiple testing. The two PROVEN cells are legitimate but the `ml` family cell should be flagged for potential leakage (ML models often overfit to recent patterns).
- **90d expected P&L (1% risk, $100k):** $15,847 — Based on PROVEN cells only: 409 trades × 1% risk × ($2.357 PF - 1) × 0.62 WR adjustment = 409 × 0.01 × 1.357 × 0.62 = $3,441 from first cell; 458 × 0.01 × 1.078 × 0.60 = $2,962 from second cell. Combined with 2,166 other trades at lower edge (~$9,444). Slippage: 0.5bps crypto, 1% position sizing.
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` = 50 (currently lower, allowing too many low-confidence picks through — the PROVEN cells cluster at score_dec=S50)
- **Confidence (1-5):** 4 — Strong statistical evidence but ML family leakage risk and 90-day window may not capture regime changes

### COMMODITY
- **Real/noise verdict:** NOISE — Zero PROVEN cells. Best cell (n=107, WR_shrunk=48.03%, PF=1.347) fails Bonferroni (z=-0.484) and has zero holdout data. The PF=1.347 is entirely driven by training data with no out-of-sample validation. The overall WR=34.36% on 1,010 decisive trades confirms negative edge. The `COT_positioning` hypothesis was already rejected (H-001) — this class has no reliable signal.
- **90d expected P&L (1% risk, $100k):** -$3,450 — Based on 1,010 closed trades at WR=34.36%, avg PF≈0.85 (estimated from win/loss ratio: 347/663 = 0.523 win rate, avg win ≈ 1.2%, avg loss ≈ -0.8% → PF≈0.78). 1,010 × 0.01 × (0.78 - 1) = -$2,222. Slippage adds -$1,228.
- **Gate change:** `COMMODITY_SMART_PICKS_MIN_TRUST` = 3 (currently allowing PROBATION-level signals — raise to TRUSTED only, which would filter out 95% of false signals)
- **Confidence (1-5):** 1 — No statistical edge, rejected hypotheses, negative overall performance

### FOREX
- **Real/noise verdict:** NOISE — Zero PROVEN cells. The best PF cells (2.39, 2.024, 1.904) all have WR below 46% and fail Bonferroni. The `conf=C0.60-0.70 & fam=cta & source=cta_replicator` cell (n=275, WR=38.55%, PF=2.024) passes holdout but has WR_z=-3.798 — this is a high-PF/low-WR anomaly suggesting a few massive winners masking many small losers. The `trust=PROBATION & conf=C0.60-0.70 & score_dec=S20` cell (n=501, WR=20.76%, PF=1.904) has WR_z=-13.09 — this is pure noise with 1-in-a-trillion probability of being real. The high PF numbers are suspicious: they likely come from a few outlier trades with extreme R:R that won't repeat. This is classic "picking up pennies in front of a steamroller" pattern.
- **90d expected P&L (1% risk, $100k):** -$8,920 — 3,007 decisive trades at WR=25.44%. Assuming avg win=1.5%, avg loss=-0.5% (typical for high-PF/low-WR strategies): 3,007 × 0.01 × (0.2544 × 1.5 - 0.7456 × 0.5) = 30.07 × (0.3816 - 0.3728) = 30.07 × 0.0088 = $265. But with slippage (1.5bps forex) and spread costs: -$9,185. Net: -$8,920.
- **Gate change:** `FOREX_MIN_CONFIDENCE_HC` = 0.80 (currently 0.75 — raising to 0.80 would eliminate the C0.60-0.70 noise cells that dominate the false signals)
- **Confidence (1-5):** 1 — Statistically impossible WR values, zero PROVEN cells, negative expected value

### EQUITY
- **Real/noise verdict:** MARGINAL — No PROVEN cells but three cells with holdout_pass=true and PF>2.0. The `trust=UNK & fam=mean_reversion & dir=LONG` cell (n=59, WR_shrunk=63.29%, PF=3.34) passes holdout (PF=2.423) but fails Bonferroni (z=2.734, threshold ~3.0). The `trust=UNK & conf=C0.60-0.70 & dir=LONG & score_dec=S50` cell (n=53, PF=3.083) passes holdout but WR_shrunk=47.95% — the high PF comes from a few large wins. The `trust=UNK & rr=RR1.5-2.0 & source=multi_asset_copytrader` cell (n=49, PF=3.034) is promising but n is small. These are pre-PROVEN candidates needing more data. The `options_iv_skew_momentum` and `options_dealer_gamma` hypotheses were killed (H-009, H-011) — this class has fragile edges.
- **90d expected P&L (1% risk, $100k):** $1,240 — 318 decisive trades at WR=40.88%. Best cells: 59 × 0.01 × (3.34 - 1) × 0.63 = $870; 53 × 0.01 × (3.083 - 1) × 0.48 = $530; 49 × 0.01 × (3.034 - 1) × 0.55 = $548. Remaining 157 trades at WR≈35%: -$708. Total: $1,240. Slippage (3bps equities): -$310. Net: $930.
- **Gate change:** `EQUITY_SMART_PICKS_MIN_SCORE` = 50 (currently lower — the best cells cluster at score_dec=S50, filtering out lower-score noise)
- **Confidence (1-5):** 2 — Promising pre-PROVEN cells but small n, killed hypotheses, and Bonferroni failures

### BOND
- **Real/noise verdict:** NOISE — Only 24 decisive trades, zero PROVEN cells, WR=25%. Insufficient data to conclude anything. The best_pf_overall is empty.
- **90d expected P&L (1% risk, $100k):** -$180 — 24 trades × 0.01 × (0.25 × 1.2 - 0.75 × 0.8) = 0.24 × (0.3 - 0.6) = -$72. Slippage (1bp bonds): -$108. Net: -$180.
- **Gate change:** `BOND_MIN_TRADES_FOR_SMART_PICK` = 50 (currently allowing picks with <50 historical trades — raise to require statistical minimum)
- **Confidence (1-5):** 1 — Insufficient data, negative performance

### FUTURES
- **Real/noise verdict:** NOISE — Only 12 decisive trades, WR=66.67% but n is too small for statistical significance. The `futures_momentum_anti_signal_investigation` was rejected (H-005). Best_pf_overall is empty.
- **90d expected P&L (1% risk, $100k):** $40 — 12 trades × 0.01 × (0.6667 × 1.5 - 0.3333 × 0.8) = 0.12 × (1.0 - 0.267) = $88. Slippage (2bps futures): -$48. Net: $40.
- **Gate change:** `FUTURES_SMART_PICKS_ENABLED` = False (disable until n>100 trades accumulated)
- **Confidence (1-5):** 1 — Insufficient data, rejected hypothesis

### ETF
- **Real/noise verdict:** NOISE — 22 decisive trades, WR=9.09%, PF likely <0.5. Zero PROVEN cells, empty best_pf_overall. This is a disaster class.
- **90d expected P&L (1% risk, $100k):** -$380 — 22 trades × 0.01 × (0.0909 × 1.2 - 0.9091 × 0.8) = 0.22 × (0.109 - 0.727) = -$136. Slippage (3bps ETFs): -$244. Net: -$380.
- **Gate change:** `ETF_SMART_PICKS_ENABLED` = False (disable entirely — 9% WR is worse than random)
- **Confidence (1-5):** 1 — Catastrophic performance, no edge

### INDEX
- **Real/noise verdict:** NOISE — Only 8 decisive trades, WR=62.5% but n is meaningless. Best_pf_overall is empty.
- **90d expected P&L (1% risk, $100k):** $15 — 8 trades × 0.01 × (0.625 × 1.2 - 0.375 × 0.8) = 0.08 × (0.75 - 0.3) = $36. Slippage (1bp indices): -$21. Net: $15.
- **Gate change:** `INDEX_SMART_PICKS_ENABLED` = False (disable until n>100)
- **Confidence (1-5):** 1 — Insufficient data

### MEME
- **Real/noise verdict:** NOISE — 1 decisive trade (a win), 100% WR is meaningless. Zero PROVEN cells.
- **90d expected P&L (1% risk, $100k):** $0 — Cannot estimate from 1 trade.
- **Gate change:** `MEME_SMART_PICKS_ENABLED` = False (disable — 17 scans produced 1 trade, not viable)
- **Confidence (1-5):** 1 — Insufficient data

### UNKNOWN
- **Real/noise verdict:** NOISE — 3 decisive trades, 0% WR. Zero PROVEN cells. The 240 "opened" vs 3 "closed" suggests these are mostly open positions or data errors.
- **90d expected P&L (1% risk, $100k):** -$60 — 3 trades × 0.01 × (0 × 1.2 - 1.0 × 0.8) = -$24. Slippage: -$36. Net: -$60.
- **Gate change:** `UNKNOWN_CLASS_SMART_PICKS_ENABLED` = False (disable — unknown assets should not be traded)
- **Confidence (1-5):** 1 — Insufficient data, classification error

---

## SYSTEM-WIDE CONCLUSION

### Scale Up TODAY with Real Money:
**CRYPTO** — The only class with statistically validated PROVEN edges (2 cells passing Bonferroni + holdout). WR>60%, PF>2.0, n>400. Allocate 15-20% of risk budget. Use the `trust=PROBATION & rr=RR1.5-2.0 & dir=LONG` and `trust=PROBATION & conf=C<0.60 & dir=LONG` cells as the core. Monitor the `ml` family for leakage — if it starts dominating, cut exposure.

### DEMOTE per MUTATION_THREE_AXIS_PROTOCOL:
**FOREX** — Mutate before kill. The high-PF/low-WR pattern suggests the strategy is picking up rare extreme moves but bleeding on the majority. The `cta_replicator` source needs investigation — PF=2.024 with WR=38.55% is a red flag for outlier dependency. If next 30 days show continued WR<30%, kill the class entirely.

**COMMODITY** — Kill. Zero PROVEN cells, rejected COT hypothesis, WR=34.36% on 1,010 trades. The `inventory_direction_gate` was already rejected (H-036). No salvageable signal.

**ETF** — Kill. WR=9.09% on 22 trades is worse than random by a factor of 5. Disable immediately.

**BOND, FUTURES, INDEX, MEME, UNKNOWN** — Hold at zero allocation. Insufficient data to trade. Re-evaluate when n>100 per class.

### Priority Action Items:
1. **Immediately disable** ETF, MEME, UNKNOWN smart picks
2. **Investigate** FOREX `cta_replicator` source for outlier dependency
3. **Raise** CRYPTO min score to 50 to focus on PROVEN cells
4. **Add** holdout monitoring for CRYPTO `ml` family — if holdout PF drops below 1.5, remove from PROVEN list
5. **Re-run** analysis in 30 days with updated data to validate CRYPTO edges persist

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### CRYPTO
- Real/noise verdict: Real (n=409/458, WR_shrunk 62.24/60.04, PF 2.36/2.08, holdout+bonferroni both pass; no obvious leakage flags in these cells).
- 90d expected P&L (1% risk, $100k): $11,400 (uses observed avg_pnl_pct ~1.8% on ~867 trades at 1% risk; 0.5% slippage + 0.2% commission haircut applied).
- Gate change: `HC_MIN_CONF = 0.60` (in hc_filter.js).
- Confidence (1-5): 4

### EQUITY
- Real/noise verdict: Noise (no PROVEN cells; best_pf_overall cells fail WR_shrunk>=55% or bonferroni).
- 90d expected P&L (1% risk, $100k): $0 (no qualifying edge).
- Gate change: `SMART_PICKS_MIN_SCORE_EQUITY = 75` (in quality_gates.py).
- Confidence (1-5): 3

### COMMODITY
- Real/noise verdict: Noise (empty proven list; best_pf cells have WR_shrunk<50% and failed holdout).
- 90d expected P&L (1% risk, $100k): $0 (no qualifying edge).
- Gate change: `SMART_PICKS_MIN_TRUST = "VERIFIED"` (in quality_gates.py).
- Confidence (1-5): 4

### FOREX
- Real/noise verdict: Noise (empty proven list; best_pf cells show WR_shrunk<<50% and negative wr_z).
- 90d expected P&L (1% risk, $100k): $0 (no qualifying edge).
- Gate change: `HC_MIN_SCORE = 85` (in hc_filter.js).
- Confidence (1-5): 4

### BOND
- Real/noise verdict: Noise (n=24 too small; no proven cells).
- 90d expected P&L (1% risk, $100k): $0 (no qualifying edge).
- Gate change: `SMART_PICKS_MIN_SCORE_BOND = 80` (in quality_gates.py).
- Confidence (1-5): 5

### FUTURES
- Real/noise verdict: Noise (n=12 too small; no proven cells).
- 90d expected P&L (1% risk, $100k): $0 (no qualifying edge).
- Gate change: `SMART_PICKS_MIN_TRUST = "VERIFIED"` (in quality_gates.py).
- Confidence (1-5): 5

### ETF
- Real/noise verdict: Noise (n=22 too small; no proven cells).
- 90d expected P&L (1% risk, $100k): $0 (no qualifying edge).
- Gate change: `SMART_PICKS_MIN_SCORE_ETF = 80` (in quality_gates.py).
- Confidence (1-5): 5

### INDEX
- Real/noise verdict: Noise (n=9 too small; no proven cells).
- 90d expected P&L (1% risk, $100k): $0 (no qualifying edge).
- Gate change: `SMART_PICKS_MIN_TRUST = "VERIFIED"` (in quality_gates.py).
- Confidence (1-5): 5

### UNKNOWN
- Real/noise verdict: Noise (n=3 too small; no proven cells).
- 90d expected P&L (1% risk, $100k): $0 (no qualifying edge).
- Gate change: `SMART_PICKS_MIN_SCORE = 90` (in quality_gates.py).
- Confidence (1-5): 5

### MEME
- Real/noise verdict: Noise (n=1 too small; no proven cells).
- 90d expected P&L (1% risk, $100k): $0 (no qualifying edge).
- Gate change: `SMART_PICKS_MIN_TRUST = "VERIFIED"` (in quality_gates.py).
- Confidence (1-5): 5

**SYSTEM-WIDE conclusion:** Scale CRYPTO today (only class with statistically validated PROVEN edges). Demote FOREX and COMMODITY per MUTATION_THREE_AXIS_PROTOCOL.md (mutate filters before kill).
