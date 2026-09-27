# Pick Funnel Swarm Verdict — 2026-09-27 04:10 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260927T041024Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-day edge analysis

Before the per-class verdicts, three system-wide observations that color everything below:

1. **The funnel is broken at the top.** `passed_high_conviction = 0` for every single class. The HC gate (score≥80, conf≥0.75, trust≥60) is firing on literally zero picks across 46,000+ scans. Either the gate is mis-wired, or the scoring distribution never reaches 80. Either way, "HIGH CONVICTION" is currently a dead label — nothing on the dashboard is HC.
2. **`opened` >> `passed_smart` in every class.** EQUITY: 5,348 opened vs 253 passed_smart. FOREX: 21,450 vs 21,785 (ok). CRYPTO: 10,262 vs 3,283. COMMODITY: 5,910 vs 3,498. This means the "Smart Picks" gate is **not** the gate that controls what actually gets opened. The dashboard is showing a funnel that doesn't match the trade ledger. That's a reporting bug or a bypass path — either way, the funnel numbers below the `passed_smart` row are not trustworthy as a filter.
3. **`passed_verified_alpha` is 0 for EQUITY, COMMODITY, ETF, INDEX, BOND, UNKNOWN** — i.e. the "verified alpha" tier is empty for 6 of 10 classes. Only CRYPTO (1,805) and FOREX (2) have anything there.

---

### EQUITY
- **Real/noise verdict:** **NOISE / LEAKAGE.** The "PROVEN" cell `fam=mean_reversion & score_dec=S40` shows n=67, WR=98.51%, PF=213.95. A PF of 214 is not a real edge — it is a data artifact. Three red flags: (i) `trust=UNK` on 100% of the cell, meaning the trust dimension is undefined and the cell is really just `fam=mean_reversion & score_dec=S40`; (ii) `conf=C<0.60` — the edge is in the *lowest* confidence bucket, which is the classic signature of a mean-reversion strategy whose "losses" are being booked as wins by a stop/target inversion or a PnL sign bug; (iii) 66/67 wins with avg_pnl=+1.27% and PF=214 implies losses are ~0.006% — that is not a market, that is a rounding error. Treat as falsified. Do not size on this.
- **90d expected P&L (1% risk, $100k):** **$0.** Do not trade this cell. If you *had* traded the raw EQUITY book (162 closed, WR 65.4%, but avg_pnl unknown), a 1%-risk book with 65% WR and unknown R:R is roughly break-even to slightly positive — call it **+$1,500 to +$3,000** with wide error bars, but I would not underwrite it because the win/loss asymmetry is not reported.
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` — raise from current value to **≥ 55** and add a hard `trust != UNK` requirement. The S40 bucket is where the fake edge lives; the S50+ bucket is where real signal would be.
- **Confidence (1-5):** **1**

### FOREX
- **Real/noise verdict:** **NOISE.** `top_edges_proven` is empty — nothing passed the Bayesian-shrunk WR≥55% + PF≥1.5 bar with Bonferroni. The best cell (`rr=RR1.0-1.5 & fam=mean_reversion & dir=LONG & source=multi_asset_copytrader`, n=46, WR 58.7%, PF 2.84) has `wr_z=1.18` and `bonferroni_pass=false`. With 497 decisive trades and a class WR of 44.47%, this is a losing class. The `multi_asset_copytrader` source is a copy-trade feed — single-source concentration risk is high and the holdout n=23 is too small to trust. **No edge.**
- **90d expected P&L (1% risk, $100k):** **−$8,000 to −$12,000.** 497 decisive trades at 44.5% WR with typical 1:1 R:R and 1% risk = ~−0.11R per trade × 497 × $1,000 = **−$54,000** gross, but with realistic slippage on FX (0.5–1 pip) and the fact that many of these are likely small-size, I'd model **−$8k to −$12k** net. This class is bleeding.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` — raise to **≥ 70** AND add `source != multi_asset_copytrader` unless the source has its own verified track record. The current 21,785/22,770 pass rate (95.7%) means the gate is doing nothing.
- **Confidence (1-5):** **4** (confident it's noise)

### CRYPTO
- **Real/noise verdict:** **PARTIALLY REAL, but the headline cell is suspicious.** The `conf=C0.75-0.80 & score_dec=S50 & source=alpha_engine` cell (n=186, WR 74.2%, shrunk 71.8%, PF 3.64, holdout PF 4.28 on n=36, Bonferroni pass, wr_z=6.6) is the **only cell in the entire report that survives Bonferroni with a real holdout**. That is genuinely interesting. **However:** the cell is 100% `trust=UNK` (the trust dimension adds nothing), and the `score_dec=S50` bucket is narrow. The PF of 3.64 is high but not impossible for a 74% WR strategy with tight stops. The bigger concern is that `passed_verified_alpha=1,805` but `passed_high_conviction=0` — the HC gate is not seeing these. **Verdict: real but fragile; needs live confirmation, not more backtest.**
- **90d expected P&L (1% risk, $100k):** If you had traded *only* the proven cell (186 trades, 74% WR, avg_pnl +1.41%, PF 3.64): 186 × 1% × $100k × (0.74 × 1.41% − 0.26 × ~0.39%) ≈ 186 × $1,000 × 0.94% ≈ **+$17,500**. With 0.1% slippage per side on crypto (realistic for liquid majors, optimistic for alts): **+$14,000 to +$17,000**. The full CRYPTO book (2,410 decisive, 45.2% WR) is a loser: **−$15,000 to −$25,000**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` — **do not raise it.** Instead, add a new constant `SMART_PICKS_CONF_BAND_CRYPTO = (0.75, 0.80)` and route only that band to the "Smart Picks" surface. The edge is *narrow*, not *high*.
- **Confidence (1-5):** **3** (real signal, but small n and UNK trust)

### FUTURES
- **Real/noise verdict:** **NOISE.** n=17 closed, WR 29.4%, no proven cells, no best-PF cells. This is a sample too small to conclude anything except "don't trade it." Also note [H-005] already killed the futures momentum inversion.
- **90d expected P&L (1% risk, $100k):** **−$2,000 to −$4,000** (17 trades × 1% × $100k × −0.4R avg). Statistically meaningless.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` — set to **999** (effectively disable) until n≥100 closed. Do not mutate; just pause.
- **Confidence (1-5):** **5** (confident it's noise)

### COMMODITY
- **Real/noise verdict:** **NOISE, and likely a leakage recurrence.** The best cell (`trust=UNK & rr=RR1.5-2.0 & fam=mean_reversion`, n=24, WR 54.2%, PF 7.28) has `holdout_pass=false`, `bonferroni_pass=false`, `wr_z=0.41`. PF 7.28 on n=24 with a 54% WR means the win/loss ratio is ~6:1 — that is the exact signature of the [H-001] COT leakage (85% cotton concentration, PF inflated by a few outsized wins). **Flag as potential leakage recurrence.** Also [H-036] already killed the inventory direction gate.
- **90d expected P&L (1% risk, $100k):** **−$3,000 to −$6,000** (114 decisive, 43% WR). Do not trade the "best" cell.
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` — raise to **≥ 65** AND add a `max_single_symbol_concentration = 0.25` guard. The current 3,498/6,025 pass rate (58%) is too loose.
- **Confidence (1-5):** **4**

### ETF
- **Real/noise verdict:** **NOISE.** n=7 closed, WR 14.3%. No cells. Nothing to say.
- **90d expected P&L (1% risk, $100k):** **−$500 to −$1,000.** Meaningless.
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` — set to **999** (disable) until n≥50.
- **Confidence (1-5):** **5**

### UNKNOWN
- **Real/noise verdict:** **NOISE.** n=7, WR 0%. This is a data-hygiene problem, not a strategy. 1,412 scans landed in UNKNOWN — that's a classifier bug.
- **90d expected P&L (1% risk, $100k):** **−$700.** Meaningless.
- **Gate change:** Fix the asset-class classifier upstream; do not add a gate constant. Route UNKNOWN to a quarantine bucket.
- **Confidence (1-5):** **5**

### BOND
- **Real/noise verdict:** **NOISE.** n=34, WR 41.2%. The `source=bond_scanner` cell is actively bad (n=20, WR 10%, PF 0.052, wr_z=−3.58). The `dir=LONG & score_dec=S50` cell has `holdout_pass=false`. No edge.
- **90d expected P&L (1% risk, $100k):** **−$1,500 to −$2,500.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` — raise to **≥ 70** AND blacklist `source=bond_scanner` until it produces a positive-expectancy cell with n≥50.
- **Confidence (1-5):** **4**

### MEME
- **Real/noise verdict:** **NOISE.** n=4. Nothing.
- **90d expected P&L (1% risk, $100k):** **−$200.** Meaningless.
- **Gate change:** Disable until n≥30.
- **Confidence (1-5):** **5**

### INDEX
- **Real/noise verdict:** **NOISE.** n=5 closed, WR 20%. 1,496 passed_smart out of 1,696 scanned (88%) but only 8 closed — the gate is passing almost everything and nothing is resolving. This is a pipeline problem, not an edge.
- **90d expected P&L (1% risk, $100k):** **−$400.** Meaningless.
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` — raise to **≥ 70**; the 88% pass rate is absurd.
- **Confidence (1-5):** **5**

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY with real money: CRYPTO — but only the narrow cell.**
The `conf=C0.75-0.80 & score_dec=S50 & source=alpha_engine` cell is the only thing in this entire report that survives Bonferroni, has a real holdout (PF 4.28 on n=36), and has a plausible mechanism (mid-confidence, mid-score, alpha_engine source). Size it at **0.5% risk per trade, not 1%**, until you have 100+ live trades confirming the backtest. Expected 90d P&L on that cell alone: **+$7,000 to +$9,000** at half-size. Do **not** scale the full CRYPTO book — it's a 45% WR loser.

**DEMOTE per MUTATION_THREE_AXIS_PROTOCOL: FOREX.**
It is the largest book (21,450 opened, 1,320 closed), the worst WR among high-volume classes (44.5%), has zero proven cells, and its best cell fails Bonferroni. It is the single biggest source of negative expectancy in the system. Mutate before kill: (1) raise `SMART_PICKS_MIN_SCORE_FOREX` to 70, (2) blacklist `multi_asset_copytrader` as a source, (3) re-run 30d. If WR doesn't cross 50%, kill the class.

**Second demotion: COMMODITY.** The PF 7.28 cell is a leakage recurrence of [H-001]. Do not re-derive it. Mutate the gate to require symbol concentration < 25% and re-test.

**Immediate hygiene fixes (not gate changes):**
- The `passed_high_conviction = 0` across all classes means `hc_filter.js` is either mis-wired or the score distribution never reaches 80. Audit this before trusting any HC label.
- `opened` >> `passed_smart` in EQUITY/CRYPTO/COMMODITY means the funnel is not the gate. Fix the reporting path or the bypass.
- `passed_verified_alpha = 0` for 6/10 classes means the "verified alpha" tier is empty — either the verifier is broken or nothing qualifies. Either way, don't market it.

**Bottom line:** Of 10 asset classes, **1 has a real (narrow) edge (CRYPTO), 1 is a confirmed loser to demote (FOREX), 1 is a leakage recurrence (COMMODITY), and 7 are noise or too small to judge.** The dashboard is currently showing a funnel that does not match the trade ledger. Fix the plumbing before adding more gates.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### EQUITY
- Real/noise verdict: Noise/leakage — n=67 with 98.51% WR and PF=213.95 is statistically impossible without single-symbol concentration or data error; holdout numbers are still unrealistically high.
- 90d expected P&L (1% risk, $100k): $0 (edge is invalid; do not trade).
- Gate change: SMART_PICKS_MIN_SCORE_EQUITY = 65
- Confidence (1-5): 5

### FOREX
- Real/noise verdict: Noise — top cells have n~47, bonferroni_pass=false, and PF inflated by small sample; no cell meets PROVEN criteria.
- 90d expected P&L (1% risk, $100k): -$420 (negative expectancy after realistic slippage on 497 decisive trades).
- Gate change: HC_MIN_CONFIDENCE = 0.82
- Confidence (1-5): 4

### CRYPTO
- Real/noise verdict: Marginally real — n=186-189, WR_shrunk~71-72%, holdout_pass=true and bonferroni_pass=true on multiple cells; PF~3.6 is high but consistent across train/holdout.
- 90d expected P&L (1% risk, $100k): +$2,850 (based on 1% risk/trade, avg_pnl_pct~1.4, ~180 qualifying trades after 0.15% slippage).
- Gate change: SMART_PICKS_MIN_SCORE_CRYPTO = 55
- Confidence (1-5): 3

### FUTURES
- Real/noise verdict: No edge — n_closed=17, zero proven cells, all metrics below threshold.
- 90d expected P&L (1% risk, $100k): $0 (no qualifying trades).
- Gate change: SMART_PICKS_MIN_SCORE_FUTURES = 70
- Confidence (1-5): 5

### COMMODITY
- Real/noise verdict: Noise — n=24 cells fail holdout_pass and bonferroni_pass; PF numbers collapse out-of-sample.
- 90d expected P&L (1% risk, $100k): -$180 (negative after slippage on 114 decisive trades).
- Gate change: HC_MIN_TRUST = 65
- Confidence (1-5): 4

### ETF
- Real/noise verdict: No edge — n_closed=7, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: SMART_PICKS_MIN_SCORE_ETF = 75
- Confidence (1-5): 5

### UNKNOWN
- Real/noise verdict: No edge — n_closed=7, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: SMART_PICKS_MIN_SCORE_UNKNOWN = 80
- Confidence (1-5): 5

### BOND
- Real/noise verdict: Noise — n=21 cell fails holdout_pass and bonferroni_pass; PF=1.313 is marginal and unstable.
- 90d expected P&L (1% risk, $100k): -$95.
- Gate change: HC_MIN_CONFIDENCE = 0.80
- Confidence (1-5): 4

### MEME
- Real/noise verdict: No edge — n_closed=4, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: SMART_PICKS_MIN_SCORE_MEME = 85
- Confidence (1-5): 5

### INDEX
- Real/noise verdict: No edge — n_closed=5, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: SMART_PICKS_MIN_SCORE_INDEX = 80
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale up TODAY: CRYPTO (only class with multiple cells passing holdout + bonferroni at usable n).  
Demote per MUTATION_THREE_AXIS_PROTOCOL.md: EQUITY (clear leakage signature; mutate the mean_reversion S40 path to zero weight before any further allocation).
