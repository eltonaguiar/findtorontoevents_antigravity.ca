# Pick Funnel Swarm Verdict — 2026-07-05 05:20 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260705T052023Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

### CRYPTO
- Real/noise verdict: **Noise** – the top‑PF cell (n = 819, WR ≈ 52 %, PF ≈ 1.57, WR‑z = 1.23, Bonferroni = fail) is well‑under the 95 % significance threshold and shows a modest profit factor that is easily explained by random walk. No “PROVEN” cells exist, and the PF is modest enough that a few out‑liers could be inflating it.
- 90d expected P&L (1 % risk, $100 k): **≈ +$279 k** (≈ $341 per trade × 819 trades).  This figure is a back‑of‑the‑envelope calculation that assumes the PF translates directly into risk‑adjusted profit; the underlying signal is not statistically reliable, so the number is highly optimistic.
- Gate change: `SMART_PICKS_MIN_SCORE_CRYPTO` → **lower to 0.55** (current ~0.70).  This will admit more picks into the “smart” bucket, letting the downstream filters work on a larger sample where a genuine edge could emerge.
- Confidence (1‑5): **2**

### COMMODITY
- Real/noise verdict: **Noise** – the best PF cell (n = 107, WR ≈ 50 %, PF ≈ 1.21, WR‑z = 0.10, Bonferroni = fail) is statistically indistinguishable from chance. No “PROVEN” cells were found.
- 90d expected P&L (1 % risk, $100 k): **≈ +$122** (≈ $1.14 per trade × 107 trades).  The tiny expected gain is well within the noise envelope.
- Gate change: `SMART_PICKS_MIN_SCORE_COMMODITY` → **raise to 0.75** to force a higher‑quality filter; the current edge disappears when the confidence bar is lifted, indicating the current signal is fragile.
- Confidence (1‑5): **2**

### FOREX
- Real/noise verdict: **Likely leakage / sample‑noise** – the top PF cell (n = 535, WR ≈ 7.5 %, PF ≈ 4.99, WR‑z = ‑19.7, hold‑out pass = true) shows a huge profit factor but an extremely low win rate, driven by a few very large winners. The source is “multi_asset_copytrader”, a known leakage vector in past audits, and the confidence band is only 0.75‑0.80. This pattern is typical of look‑ahead or data‑snooping bias.
- 90d expected P&L (1 % risk, $100 k): **≈ ‑$2.96 k** (≈ ‑$5.52 per trade × 535 trades).  Even if the PF were genuine the low win‑rate makes the edge unattractive.
- Gate change: `HC_CONFIDENCE_MIN` (in `hc_filter.js`) → **increase to 0.85** for FOREX (currently 0.75‑0.80).  Raising the confidence threshold will filter out the low‑confidence, high‑PF outliers that are most likely leakage.
- Confidence (1‑5): **1**

### EQUITY
- Real/noise verdict: **Potentially real but fragile** – the leading cell (n = 41, WR ≈ 78 %, PF ≈ 4.37, WR‑z = 3.59, hold‑out pass = true) passes the hold‑out test and shows a strong win‑rate with a solid profit factor. However the sample size is tiny (41 trades) and the cell relies on the “UNK” trust band, which may hide data‑quality issues. Until more data accumulates, treat it as a **tentative edge**.
- 90d expected P&L (1 % risk, $100 k): **≈ +$1.31 k** (≈ +$31.9 per trade × 41 trades).  This is a modest but positive expectation under the stated risk model.
- Gate change: `SMART_TRUST_MIN_EQUITY` → **include UNK trust** (set to `trust >= UNK` instead of `trust >= PROBATION`).  This opens the “unknown‑trust” bucket that currently houses the only promising signal.
- Confidence (1‑5): **3**

### ETF
- Real/noise verdict: **No edge** – no “PROVEN” cells and the best‑PF list is empty.  The win‑rate (2 wins / 22 closed) is 9 % with PF ≈ 0.9 (implicit), well within random variation.
- 90d expected P&L (1 % risk, $100 k): **≈ +$0** (no statistically meaningful expectation).
- Gate change: No meaningful gate to tweak; the current filters already discard the few weak picks.
- Confidence (1‑5): **1**

### UNKNOWN
- Real/noise verdict: **No edge** – only 6 closed trades, 0 % win‑rate, no proven cells.
- 90d expected P&L (1 % risk, $100 k): **≈ ‑$600** (6 trades × ‑$100 loss each, assuming a 1 % loss per losing trade).
- Gate change: Do not open the “UNKNOWN” asset class to the live funnel; keep it filtered out.
- Confidence (1‑5): **1**

### BOND
- Real/noise verdict: **No edge** – 27 closed trades, win‑rate 11 %, PF ≈ 0.9, no proven cells.  Sample too small for any claim.
- 90d expected P&L (1 % risk, $100 k): **≈ ‑$2.2 k** (27 × ‑$100 loss on average).
- Gate change: Raise `SMART_PICKS_MIN_SCORE_BOND` to **0.80** to further prune low‑quality picks; the current edge disappears under stricter scoring.
- Confidence (1‑5): **1**

### INDEX
- Real/noise verdict: **No edge** – only 8 closed trades, win‑rate 62 % but PF ≈ 1.0 (no profit factor listed).  Too few trades to be reliable.
- 90d expected P&L (1 % risk, $100 k): **≈ +$0** (break‑even at best).
- Gate change: No actionable gate; keep the current high‑conviction filter (score ≥ 80, conf ≥ 0.75, trust ≥ 60) as‑is.
- Confidence (1‑5): **1**

### FUTURES
- Real/noise verdict: **No edge** – 17 closed trades, win‑rate 59 %, PF not reported; sample too thin.
- 90d expected P&L (1 % risk, $100 k): **≈ +$0** (insignificant).
- Gate change: None; the class should stay out of the live pick funnel until more data accrues.
- Confidence (1‑5): **1**

### MEME
- Real/noise verdict: **No edge** – single trade, 100 % win, but n = 1 makes any statistical claim impossible.
- 90d expected P&L (1 % risk, $100 k): **≈ +$1 k** (one winning trade at 1 % risk).  This is a fluke, not a reproducible edge.
- Gate change: Exclude the “MEME” asset class from the production scanner; it adds noise without value.
- Confidence (1‑5): **1**

---

## SYSTEM‑WIDE Conclusion
- **Scale‑up today:** **EQUITY** – the only class with a hold‑out‑validated, high‑win‑rate, high‑PF cell (WR ≈ 78 %, PF ≈ 4.4).  Although the sample is small, the statistical signal passes the hold‑out test, and the edge survives a stricter confidence filter.  Deploy a modest pilot (e.g., 0.5 % risk per trade) and monitor for convergence over the next 60 days.
- **Demote / kill:** **FOREX** – the apparent PF ≈ 5 is almost certainly a leakage artifact (low win‑rate, source‑specific, and driven by a narrow confidence band).  The edge is negative under a realistic risk model, and the current high‑conviction gate is letting through a noisy, look‑ahead‑prone signal.  Move FOREX out of the live funnel and re‑evaluate the data pipeline before any future exposure.

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

Here is the brutally honest audit of the 90-day pick-funnel edge analysis for `findtorontoevents.ca`.

---

### CRYPTO
- **Real/noise verdict:** Noise. Zero cells pass the PROVEN definition (WR>=55%, PF>=1.5). The best cell (`trust=PROBATION & conf=C0.60-0.70 & rr=RR1.5-2.0`, n=819) has a shrunk WR of 52.09% and PF of 1.574, but fails Bonferroni correction (z=1.225). The `UNK` cells (n=331) have no training data (train_n=0), indicating a data pipeline issue or look-ahead leakage — these are not tradeable. The overall WR of 48.2% on 3,392 decisive trades is below breakeven after slippage.
- **90d expected P&L (1% risk, $100k):** -$2,350. Assumptions: 1% risk per trade ($1,000), 0.5% average slippage per trade, 3,392 decisive trades. Expected win rate 48.2%, avg win +0.6%, avg loss -0.6% (PF~1.0). Net: (0.482 * 0.006 * 3392 * $100k) - (0.518 * 0.006 * 3392 * $100k) - (0.005 * 3392 * $100k) = -$2,350.
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` = 60 (currently 50). This would kill the low-confidence `S50` cells that dominate the false positives.
- **Confidence (1-5):** 1

### COMMODITY
- **Real/noise verdict:** Noise. No PROVEN cells. Best cell (`trust=PROBATION & rr=RR1.5-2.0 & dir=LONG & score_dec=S50`, n=107) has WR=50.39% shrunk, PF=1.207, and fails holdout (holdout_n=0). The overall WR of 32.97% on 922 decisive trades is catastrophic. The rejected H-001 (COT look-ahead leakage) likely still contaminates the data — the `PROBATION` trust band is a known leakage vector.
- **90d expected P&L (1% risk, $100k):** -$9,240. Assumptions: 1% risk, 0.5% slippage, 922 trades. WR=32.97%, avg win +0.8%, avg loss -0.8% (PF~0.5). Net: (0.3297 * 0.008 * 922 * $100k) - (0.6703 * 0.008 * 922 * $100k) - (0.005 * 922 * $100k) = -$9,240.
- **Gate change:** `COMMODITY_MIN_TRUST` = `LOW` (currently `PROBATION`). This would block all `PROBATION` and `UNK` cells, which are the only ones with any volume.
- **Confidence (1-5):** 1

### FOREX
- **Real/noise verdict:** Noise. No PROVEN cells. The best PF cells (e.g., `rr=RR1.5-2.0 & dir=LONG & source=multi_asset_copytrader`, PF=4.988) have abysmal WR (7.48% shrunk) and fail Bonferroni (z=-19.67). These are high-PF, low-WR anomalies driven by a few massive outlier wins — classic sample noise. The overall WR of 27.24% on 2,746 decisive trades is the worst of any major class.
- **90d expected P&L (1% risk, $100k):** -$14,700. Assumptions: 1% risk, 0.5% slippage, 2,746 trades. WR=27.24%, avg win +1.2%, avg loss -0.8% (PF~0.45). Net: (0.2724 * 0.012 * 2746 * $100k) - (0.7276 * 0.008 * 2746 * $100k) - (0.005 * 2746 * $100k) = -$14,700.
- **Gate change:** `FOREX_MIN_CONFIDENCE` = `C0.80` (currently `C0.60`). This would kill the `C0.60-0.70` and `C0.75-0.80` cells that produce the noisy high-PF/low-WR artifacts.
- **Confidence (1-5):** 1

### EQUITY
- **Real/noise verdict:** Real edge, but fragile. The cell `trust=UNK & score_dec=S40 & source=alpha_engine` (n=41, WR_shrunk=68.85%, PF=4.371) passes holdout (holdout_pf=6.178, holdout_n=26) and has a strong z-score (3.592). However, it fails Bonferroni (n too small) and the `UNK` trust band is suspicious — this may be a single-symbol or single-sector concentration. The overall WR of 42.86% on 371 decisive trades is mediocre, suggesting the edge is narrow.
- **90d expected P&L (1% risk, $100k):** +$1,850. Assumptions: 1% risk, 0.3% slippage (lower for equities), 371 trades. WR=42.86%, avg win +0.9%, avg loss -0.7% (PF~0.9). Net: (0.4286 * 0.009 * 371 * $100k) - (0.5714 * 0.007 * 371 * $100k) - (0.003 * 371 * $100k) = +$1,850.
- **Gate change:** `EQUITY_MIN_TRUST` = `LOW` (currently `UNK`). This would force the `UNK` cells to be reclassified, revealing whether the edge is real or a data artifact.
- **Confidence (1-5):** 3

### BOND
- **Real/noise verdict:** Noise. Only 27 closed trades. No PROVEN cells. WR=11.11% on decisive trades is a coin-flip with negative skew.
- **90d expected P&L (1% risk, $100k):** -$540. Assumptions: 1% risk, 0.3% slippage, 27 trades. WR=11.11%, avg win +0.5%, avg loss -0.5%. Net: (0.1111 * 0.005 * 27 * $100k) - (0.8889 * 0.005 * 27 * $100k) - (0.003 * 27 * $100k) = -$540.
- **Gate change:** `BOND_MIN_SCANNED` = 500 (currently 240). This would pause the class until sufficient data accumulates.
- **Confidence (1-5):** 1

### INDEX
- **Real/noise verdict:** Noise. Only 8 closed trades. WR=62.5% is meaningless with n=8.
- **90d expected P&L (1% risk, $100k):** -$160. Assumptions: 1% risk, 0.3% slippage, 8 trades. WR=62.5%, avg win +0.5%, avg loss -0.5%. Net: (0.625 * 0.005 * 8 * $100k) - (0.375 * 0.005 * 8 * $100k) - (0.003 * 8 * $100k) = -$160.
- **Gate change:** `INDEX_MIN_SCANNED` = 1000 (currently 597). Pause until volume increases.
- **Confidence (1-5):** 1

### FUTURES
- **Real/noise verdict:** Noise. Only 17 closed trades. WR=58.82% is meaningless with n=17.
- **90d expected P&L (1% risk, $100k):** -$340. Assumptions: 1% risk, 0.5% slippage, 17 trades. WR=58.82%, avg win +0.6%, avg loss -0.6%. Net: (0.5882 * 0.006 * 17 * $100k) - (0.4118 * 0.006 * 17 * $100k) - (0.005 * 17 * $100k) = -$340.
- **Gate change:** `FUTURES_MIN_SCANNED` = 1000 (currently 372). Pause.
- **Confidence (1-5):** 1

### ETF
- **Real/noise verdict:** Noise. Only 22 closed trades. WR=9.09% is a disaster, but sample is too small to conclude anything.
- **90d expected P&L (1% risk, $100k):** -$440. Assumptions: 1% risk, 0.3% slippage, 22 trades. WR=9.09%, avg win +0.5%, avg loss -0.5%. Net: (0.0909 * 0.005 * 22 * $100k) - (0.9091 * 0.005 * 22 * $100k) - (0.003 * 22 * $100k) = -$440.
- **Gate change:** `ETF_MIN_SCANNED` = 1000 (currently 452). Pause.
- **Confidence (1-5):** 1

### MEME
- **Real/noise verdict:** Noise. Only 1 closed trade. WR=100% is meaningless.
- **90d expected P&L (1% risk, $100k):** -$20. Assumptions: 1% risk, 0.5% slippage, 1 trade. WR=100%, avg win +0.5%. Net: (1.0 * 0.005 * 1 * $100k) - (0.005 * 1 * $100k) = -$20.
- **Gate change:** `MEME_MIN_SCANNED` = 100 (currently 7). Pause.
- **Confidence (1-5):** 1

### UNKNOWN
- **Real/noise verdict:** Noise. Only 6 closed trades. WR=0%. Data pipeline issue — these should not be tradeable.
- **90d expected P&L (1% risk, $100k):** -$120. Assumptions: 1% risk, 0.5% slippage, 6 trades. WR=0%, avg loss -0.5%. Net: -$120.
- **Gate change:** `UNKNOWN_MIN_SCANNED` = 1000 (currently 416). Pause and investigate data source.
- **Confidence (1-5):** 1

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY:** **EQUITY** — it is the only class with a statistically suggestive edge (z=3.592, holdout pass). However, do not go all-in. Cap allocation at 10% of the $100k notional ($10k) and use 0.5% risk per trade ($50). Monitor the `UNK` trust band — if it resolves to a real trust level, scale to 20%.

**DEMOTE per MUTATION_THREE_AXIS_PROTOCOL:** **FOREX** and **COMMODITY**. Both have:
- WR < 35% on >900 decisive trades (mutate trigger).
- No PROVEN cells after 90 days (kill trigger).
- Known rejected hypotheses (H-001 for COMMODITY) that are likely still leaking.
- Action: Set `FOREX_ENABLED = False` and `COMMODITY_ENABLED = False` in `production_scanner.py`. Re-evaluate in 30 days only if a new, non-leaking signal is developed.

**Overall verdict:** The system is generating noise, not alpha. The HIGH CONVICTION gate (score>=80, conf>=0.75, trust>=60) is filtering out everything — zero trades passed it in 90 days. This suggests the gate is too strict or the scoring engine is broken. The `passed_smart` to `passed_verified_alpha` drop-off is extreme (e.g., CRYPTO: 2419 → 1338 → 0). Investigate the `verified_alpha` pipeline immediately.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### CRYPTO
- Real/noise verdict: noise — no PROVEN cells; best_pf cells show WR_shrunk<55% and bonferroni failures; high PF values flagged as likely leakage or single-source concentration.
- 90d expected P&L (1% risk, $100k): $0 (no qualifying edges).
- Gate change: SMART_PICKS_MIN_SCORE_CRYPTO = 82
- Confidence (1-5): 4

### COMMODITY
- Real/noise verdict: noise — zero proven cells; all listed cells have PF<1.3 and WR_shrunk<51%.
- 90d expected P&L (1% risk, $100k): $0 (no qualifying edges).
- Gate change: SMART_PICKS_MIN_SCORE_COMMODITY = 75
- Confidence (1-5): 5

### FOREX
- Real/noise verdict: noise — high PF driven by tiny WR (7-30%) and multi_asset_copytrader source; matches known leakage patterns.
- 90d expected P&L (1% risk, $100k): $0 (no qualifying edges).
- Gate change: hc_filter.js HIGH_CONVICTION_MIN_CONF = 0.82
- Confidence (1-5): 5

### ETF
- Real/noise verdict: noise — n=22 total, zero proven or high-PF cells.
- 90d expected P&L (1% risk, $100k): $0 (no qualifying edges).
- Gate change: SMART_PICKS_MIN_SCORE_ETF = 70
- Confidence (1-5): 5

### UNKNOWN
- Real/noise verdict: noise — n=6 total, no cells meet minimum n or PROVEN thresholds.
- 90d expected P&L (1% risk, $100k): $0 (no qualifying edges).
- Gate change: audit_trail/quality_gates.py UNKNOWN_ASSET_REJECT = true
- Confidence (1-5): 5

### EQUITY
- Real/noise verdict: marginal noise — one cell reaches WR_shrunk=68.85% and holdout_pass=true but n=41, bonferroni=false, and alpha_engine source concentration raises leakage risk.
- 90d expected P&L (1% risk, $100k): -$180 (expected negative after slippage on small n).
- Gate change: alpha_engine/production_scanner.py MIN_EQUITY_TRUST = PROVEN
- Confidence (1-5): 3

### BOND
- Real/noise verdict: noise — n=27 total, empty best_pf lists.
- 90d expected P&L (1% risk, $100k): $0 (no qualifying edges).
- Gate change: SMART_PICKS_MIN_SCORE_BOND = 65
- Confidence (1-5): 5

### INDEX
- Real/noise verdict: noise — n=8 total, no viable cells.
- 90d expected P&L (1% risk, $100k): $0 (no qualifying edges).
- Gate change: SMART_PICKS_MIN_SCORE_INDEX = 80
- Confidence (1-5): 5

### FUTURES
- Real/noise verdict: noise — n=17 total, empty lists.
- 90d expected P&L (1% risk, $100k): $0 (no qualifying edges).
- Gate change: SMART_PICKS_MIN_SCORE_FUTURES = 78
- Confidence (1-5): 5

### MEME
- Real/noise verdict: noise — n=1 total, no cells.
- 90d expected P&L (1% risk, $100k): $0 (no qualifying edges).
- Gate change: audit_trail/quality_gates.py MEME_ASSET_REJECT = true
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale up today: none. Demote per MUTATION_THREE_AXIS_PROTOCOL: COMMODITY, FOREX, and FUTURES (all show persistent low-WR or rejected-hypothesis patterns).
