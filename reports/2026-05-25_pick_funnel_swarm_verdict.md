# Pick Funnel Swarm Verdict — 2026-11-11 04:07 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20261111T040648Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-Day Edge Analysis

**Bottom line up front:** The funnel is broken at the *opened* stage, not the *scored* stage. Every class shows `opened ≈ scanned` (e.g. EQUITY 5,771 opened vs 5,880 scanned, but only 230 passed_smart). The scoring gates are cosmetic — they don't gate execution. The "PROVEN" cells are almost all `trust=UNK` with tiny n and implausible PFs. I do not believe most of them. Details below.

---

### EQUITY
- **Real/noise verdict:** **NOISE / LEAKAGE.** The `rr=RR>=2.0 & fam=mean_reversion` cell shows WR=97.37% (37/38), PF=134.7, holdout PF=99.0 on n=21. A PF of 134 is not a real edge — it is a data artifact. Three tells: (1) `trust=UNK` on 100% of the cell, meaning the trust gate never fired; (2) holdout PF (99.0) > train PF (55.0), which is the opposite of what a real edge does under walk-forward; (3) n=38 with 37 wins is the signature of a **stop/target mislabeling or a look-ahead in the mean_reversion exit logic** — likely the "win" is being recorded when the target is hit intra-bar before the stop, or the R:R is being computed post-hoc. This is the same failure mode as H-001 (COT leakage): a clean-looking cell that collapses on timestamp fix. **Do not trade this.** The class-level WR of 70.6% on n=109 is also suspect for the same reason — 109 closed out of 5,771 opened means 98% of picks never resolved, so the WR is a survivor-biased sample.
- **90d expected P&L (1% risk, $100k):** **$0.** I would not size this. If forced to mark-to-model the *reported* cell: 38 trades × 1% × $100k × 1.58% avg PnL ≈ **$60k**, but that number is fiction given the leakage flag. Realistic expectation after fixing the exit logic: **negative to flat**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` — currently the class passes 230/5,880 (3.9%) through Smart but opens 5,771 (98%). The gate is not wired to execution. Set `SMART_PICKS_MIN_SCORE_EQUITY = 75` **and** wire `passed_smart` to the `opened` counter so unscored picks cannot open. Also add a hard `trust != UNK` requirement for EQUITY mean_reversion until the exit logic is audited.
- **Confidence (1-5):** **1** (that the edge is real). 4 that it's leakage.

---

### COMMODITY
- **Real/noise verdict:** **NOISE.** No PROVEN cells. Best PF overall is 2.14 on n=28 but **holdout PF = 1.14 and holdout_pass = false**, bonferroni_pass = false. The class-level WR of 69.2% is on n=39 closed out of 5,697 opened — a 0.7% resolution rate. This is not an edge; it's a tiny sample of survivors. Note the H-001 history: COMMODITY has already been burned once by COT look-ahead, and the `trust=UNK & dir=LONG & source=alpha_engine` cell here has the same shape (high train PF, collapsing holdout). Treat as a **potential leakage recurrence** until proven otherwise.
- **90d expected P&L (1% risk, $100k):** **$0.** Not sizeable. The reported cell would imply ~28 × 1% × $100k × 0.85% ≈ **$24k**, but holdout says the edge is gone.
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` — currently passes 3,618/5,736 (63%) through Smart, which is absurdly permissive. Set to **80** and require `holdout_pass == true` on any cell before it can be promoted to a sizing tier.
- **Confidence (1-5):** **1**.

---

### FOREX
- **Real/noise verdict:** **SUSPICIOUS — likely single-source concentration.** The `conf=C>=0.90 & fam=regime & source=regime_terminal` cell: n=40, WR=85%, PF=9.27, holdout PF=99.0 on n=10. A PF of 9.27 with holdout PF of 99.0 on 10 trades is not a statistical result — it's **one or two trades dominating the holdout**. The `source=regime_terminal` tag is a red flag: it's a single strategy family, and the cell is 100% `trust=UNK`. This is the classic "one symbol / one regime / one source" concentration that the prompt asked me to flag. The class-level WR of 51.7% on n=431 (out of 23,546 opened — 1.8% resolution) is the honest number, and it's a coin flip. **The 85% cell is not tradeable.**
- **90d expected P&L (1% risk, $100k):** **$0.** Reported cell would imply 40 × 1% × $100k × 0.63% ≈ **$25k**, but with n=10 holdout and PF=99, the confidence interval spans negative to +$200k. Not sizeable.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` — currently passes 24,178/24,821 (97.4%) through Smart. This is the single most broken gate in the funnel. Set to **85** and add a `source != regime_terminal` exclusion until that source is independently validated on n>=100 holdout. Also cap `passed_smart` at 5% of scanned per class as a sanity check.
- **Confidence (1-5):** **1** that the 85% cell is real. 3 that FOREX has *some* edge at the class level (51.7% is at least plausible for a mean-reverting FX book, but not proven).

---

### CRYPTO
- **Real/noise verdict:** **WEAK BUT PLAUSIBLY REAL — the only class with a defensible cell.** The `trust=UNK & conf=C0.75-0.80 & source=alpha_engine` cell: n=214, WR=63.1%, WR_shrunk=62.0%, PF=1.81, **holdout PF=1.63 on n=124, holdout_pass=true, bonferroni_pass=true, wr_z=3.83**. This is the only cell in the entire dataset that survives Bonferroni correction *and* has a holdout that is both large and directionally consistent with train. The `rr=RR1.5-2.0` cell has higher PF (2.12) but **fails Bonferroni** (p not corrected) and has a holdout PF of 1.21 on n=83 — still positive, but weaker. The class-level WR of 45.7% on n=2,303 (out of 10,004 opened — 23% resolution, by far the best resolution rate in the funnel) is the honest number, and it's below 50%. **The edge is real but narrow: it lives in the conf 0.75–0.80 band, LONG, alpha_engine source, and it is a ~62% WR / 1.8 PF cell, not a 90% WR cell.** The `ml` cells the prompt warned about are not in this output — good, because they'd be the same leakage shape as EQUITY.
- **90d expected P&L (1% risk, $100k):** Using the defensible cell: 214 trades × 1% × $100k × 0.72% avg PnL ≈ **$154k gross**. Apply realistic slippage (see assumptions) and a 30% haircut for the fact that the cell is `trust=UNK` (i.e., we don't actually know the trust distribution inside it): **~$95k–$110k net**. This is the only class where I'd put a number on the table.
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` — currently passes 3,669/12,307 (29.8%) through Smart, but 2,226 pass verified_alpha and 0 pass HC. The HC gate (`hc_filter.js`: score>=80, conf>=0.75, trust>=60) is **killing the one real edge** because the edge lives at `trust=UNK` and `conf=0.75-0.80`. **Change `hc_filter.js` `MIN_TRUST` from 60 to 0 for CRYPTO only, and add a `conf` band carve-out: `(conf >= 0.75 && conf < 0.80 && source == 'alpha_engine')` bypasses the trust requirement.** This is the single highest-leverage change in the whole audit.
- **Confidence (1-5):** **3.5** that the cell is real. 2 that it survives live slippage at scale.

---

### BOND
- **Real/noise verdict:** **NO EDGE.** n=31 closed, WR=38.7%, no PROVEN cells, no best-PF cells. 1,072 opened out of 1,103 scanned — the gate is doing nothing. This class should not be in the funnel.
- **90d expected P&L (1% risk, $100k):** **Negative.** At 38.7% WR and unknown R:R, expect **-$5k to -$15k** if sized at 1% per trade on 31 resolved trades. Do not size.
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` — set to **999** (effectively disable) until a bond-specific edge is found. Or remove BOND from the scanner entirely.
- **Confidence (1-5):** **5** that there is no edge.

---

### ETF
- **Real/noise verdict:** **NO EDGE — actively harmful.** n=10 closed, WR=10%, 1 win / 9 losses. 306 opened out of 316 scanned. This is the worst WR in the funnel and the sample is too small to be anything but noise, but the direction is unambiguous: **the ETF gate is anti-predictive.**
- **90d expected P&L (1% risk, $100k):** **Negative.** ~**-$8k** on 10 resolved trades at 1% risk. Do not size.
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` — set to **999** (disable). The class passes 277/316 (87.7%) through Smart, which is the opposite of what a gate should do.
- **Confidence (1-5):** **5** that there is no edge.

---

### FUTURES
- **Real/noise verdict:** **NO EDGE.** n=16 closed, WR=37.5%, no PROVEN cells. Note H-005 already killed futures_momentum and confirmed inversion doesn't fix it. This class is a known graveyard.
- **90d expected P&L (1% risk, $100k):** **Negative.** ~**-$4k** on 16 resolved trades. Do not size.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` — set to **999** (disable) pending a new hypothesis. Do not re-run H-005.
- **Confidence (1-5):** **5** that there is no edge.

---

### MEME
- **Real/noise verdict:** **NO EDGE.** n=9 closed, WR=33.3%, no PROVEN cells. 17 opened out of 26 scanned — the smallest class and the worst resolution. Not enough data to conclude anything except "don't trade it."
- **90d expected P&L (1% risk, $100k):** **Negative.** ~**-$3k** on 9 resolved trades. Do not size.
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME` — set to **999** (disable). Revisit only if n_closed >= 100.
- **Confidence (1-5):** **5** that there is no edge.

---

### UNKNOWN
- **Real/noise verdict:** **DATA HYGIENE FAILURE, not an asset class.** n=3 closed, WR=0%. 1,311 opened out of 1,314 scanned. The fact that 1,314 picks have no asset class is a **pipeline bug**, not a trading signal. This is the single most alarming number in the dataset because it means ~5% of the funnel is unclassified and being opened anyway.
- **90d expected P&L (1% risk, $100k):** **$0** — but the real cost is that these 1,311 picks are polluting every class-level statistic above.
- **Gate change:** Add a hard `if asset_class == 'UNKNOWN': reject` in `production_scanner.py` before the Smart_Picks scoring step. This is not a threshold change; it's a missing guard.
- **Confidence (1-5):** **5** that this is a bug.

---

### INDEX
- **Real/noise verdict:** **INSUFFICIENT DATA.** n=1 closed, WR=100%. 2,074 opened out of 2,075 scanned. One trade is not a sample. The 100% WR is meaningless.
- **90d expected P&L (1% risk, $100k):** **$0** (n=1). Do not size.
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` — set to **999** (disable) until n_closed >= 50. The 1,578/2,075 (76%) Smart pass rate is meaningless with 1 resolution.
- **Confidence (1-5):** **5** that there is no conclusion to draw.

---

## Sizing & slippage assumptions (for the P&L numbers above)

- **Account:** $100k notional, 1% risk per trade = $1,000 max loss per position.
- **Position sizing:** risk-based, so position size = $1,000 / (entry − stop). Avg PnL% is applied to *notional*, not to risk, so the dollar figure is `n_trades × $1,000 × (avg_pnl_pct / avg_risk_pct)`. I used the reported `avg_pnl_pct` as a proxy for per-trade return on risk, which is the standard convention in these reports.
- **Slippage:** 5 bps per side for CRYPTO (liquid majors), 2 bps for EQUITY/FOREX, 10 bps for COMMODITY/FUTURES. Applied as a haircut to gross PnL.
- **Fees:** 2 bps round-trip for EQUITY/ETF, 1 bp for FOREX, 10 bps for CRYPTO.
- **Haircut for `trust=UNK`:** 30% reduction on any cell where 100% of trades are `trust=UNK`, because we cannot verify the trust distribution inside the cell and the gate that was supposed to filter it never fired.
- **Resolution-rate caveat:** For classes with <5% resolution (EQUITY, COMMODITY, FOREX, BOND, ETF, FUTURES, MEME, INDEX, UNKNOWN), the WR is computed on a survivor-biased sample. I have **not** extrapolated those WRs to the full opened population — that would be the single biggest analytical error available here.

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY: CRYPTO — and only CRYPTO, and only the narrow cell.**
The `conf=C0.75-0.80 & dir=LONG & source=alpha_engine` cell is the only signal in the entire 90-day dataset that survives Bonferroni correction, has a holdout n>=100, and has a holdout PF that is directionally consistent with train (1.63 vs 2.02). It is a ~62% WR / 1.8 PF edge, not a 90% WR edge, and it lives at `trust=UNK` — which means the current HC gate is *actively filtering it out*. The single highest-leverage change in this audit is the `hc_filter.js` carve-out for that cell. Expected 90d P&L at 1% risk: **~$95k–$110k net** after slippage and the UNK haircut. Confidence 3.5/5.

**Demote per MUTATION_THREE_AXIS_PROTOCOL: EQUITY.**
The 97.4% WR / PF=134 cell is a leakage artifact, not an edge — the holdout PF (99.0) exceeding train PF (55.0) is the tell. Per the protocol, **mutate before kill**: (1) audit the mean_reversion exit logic for intra-bar target-before-stop mislabeling; (2) re-run with `trust != UNK` enforced; (3) if the cell collapses to WR<55% / PF<1.2 after the fix, kill it. Do not size EQUITY until that audit is complete. The class-level 70.6% WR on n=109 is survivor-biased and should not be cited as evidence of edge.

**Also demote (disable, not mutate): BOND, ETF, FUTURES, MEME, INDEX, UNKNOWN.** These have no edge, insufficient data, or are pipeline bugs. The `UNKNOWN` bucket in particular is a data-hygiene failure that is polluting every other class statistic — fix the classifier before trusting any of the numbers above.

**The meta-finding:** Every class shows `op

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### EQUITY
- Real/noise verdict: noise — 97% WR / PF 134 on n=38 is leakage or single-symbol concentration; rejected per protocol.
- 90d expected P&L (1% risk, $100k): $0 (no usable edge).
- Gate change: SMART_PICKS_MIN_SCORE_EQUITY = 85
- Confidence (1-5): 5

### COMMODITY
- Real/noise verdict: noise — no proven cells; best_pf cells fail holdout and bonferroni.
- 90d expected P&L (1% risk, $100k): $0 (no usable edge).
- Gate change: SMART_PICKS_MIN_SCORE_COMMODITY = 75
- Confidence (1-5): 5

### FOREX
- Real/noise verdict: noise — PF 9.267 on n=40 regime cells is statistically implausible and matches flagged leakage pattern.
- 90d expected P&L (1% risk, $100k): $0 (no usable edge).
- Gate change: HC_MIN_CONF_FOREX = 0.92
- Confidence (1-5): 5

### CRYPTO
- Real/noise verdict: real — n=214 cells show stable WR_shrunk 62%, PF 1.8, holdout_pass + bonferroni_pass.
- 90d expected P&L (1% risk, $100k): ~$18,400 (assume 0.72% avg edge per trade, 214 trades, 1% risk, 0.15% slippage).
- Gate change: SMART_PICKS_MIN_SCORE_CRYPTO = 72
- Confidence (1-5): 4

### BOND
- Real/noise verdict: noise — n=31 closed, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0 (no usable edge).
- Gate change: SMART_PICKS_MIN_SCORE_BOND = 80
- Confidence (1-5): 5

### ETF
- Real/noise verdict: noise — n=10 closed, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0 (no usable edge).
- Gate change: SMART_PICKS_MIN_SCORE_ETF = 80
- Confidence (1-5): 5

### UNKNOWN
- Real/noise verdict: noise — n=3 closed, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0 (no usable edge).
- Gate change: SMART_PICKS_MIN_SCORE_UNKNOWN = 80
- Confidence (1-5): 5

### INDEX
- Real/noise verdict: noise — n=1 closed, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0 (no usable edge).
- Gate change: SMART_PICKS_MIN_SCORE_INDEX = 80
- Confidence (1-5): 5

### FUTURES
- Real/noise verdict: noise — n=16 closed, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0 (no usable edge).
- Gate change: SMART_PICKS_MIN_SCORE_FUTURES = 80
- Confidence (1-5): 5

### MEME
- Real/noise verdict: noise — n=9 closed, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0 (no usable edge).
- Gate change: SMART_PICKS_MIN_SCORE_MEME = 80
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale CRYPTO today (only class with statistically credible, holdout-validated edges). Demote EQUITY and FOREX per MUTATION_THREE_AXIS_PROTOCOL.md (mutate the alpha_engine and regime_terminal paths before any further allocation). All other classes have no actionable edge.
