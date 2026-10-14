# Pick Funnel Swarm Verdict — 2026-10-14 04:10 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20261014T041032Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-day edge analysis

Before per-class verdicts, three system-wide observations that shape everything below:

1. **`passed_high_conviction = 0` in every single class.** The HC gate (`score>=80, conf>=0.75, trust>=60`) is dead code on this dataset. Either the trust field is never populated above 60 (see: every "PROVEN" cell is `trust=UNK`), or the score/conf thresholds are misaligned with the actual distributions. This is the single biggest structural problem in the funnel.
2. **`passed_verified_alpha` is 0 for 7 of 10 classes.** Only CRYPTO (1890) and FOREX (3) and FUTURES (1) and MEME (1) produce any. The verified-alpha stage is effectively a CRYPTO-only gate.
3. **Every "PROVEN" cell across every class is `trust=UNK`.** The trust dimension is not discriminating — it's a constant. Any cell that includes `trust=UNK` is not a real conditional edge; it's the unconditional population relabeled.

---

### EQUITY
- **Real/noise verdict:** **NOISE / LEAKAGE.** The three "PROVEN" cells are the *same 66 trades* sliced three ways (`trust=UNK & fam=mean_reversion & score_dec=S40` ≡ `conf=C<0.60 & fam=mean_reversion & score_dec=S40` ≡ `fam=mean_reversion & dir=LONG & score_dec=S40`). WR=98.48% on n=66 with PF=226 is not a real edge — that is a **data artifact**. A 98% WR with avg_pnl=1.37% and PF=226 implies losses are ~0.006% of wins, which is impossible for equity mean-reversion with realistic stops. Most likely causes: (a) `score_dec=S40` is a post-hoc bucket that correlates with "trade was already winning when scored," (b) the "loss" label is being assigned only when a hard stop is hit and most mean-reversion trades exit at a tiny profit before the stop, (c) single-symbol concentration — 66 trades in one family over 90d on a 5799-scan universe smells like one ticker (e.g. a low-vol ETF-like name) dominating. The holdout_pf=99.0 with holdout_n=26 is *not* independent confirmation — it's the same 66 trades split 40/26. **Do not trade this.** Also note: EQUITY opened 5655 trades but only closed 144 — 97.5% of "opened" positions never resolved. The WR is computed on a 2.5% survivor sample.
- **90d expected P&L (1% risk, $100k):** **$0 — do not size.** If forced to model the naive cell: 66 trades × 1% × 1.37% avg = ~$900 gross, but with the leakage caveat the true expectation is negative. Report as **$0 / not tradeable**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` — raise from current value to **75** (from whatever it is now, likely 60). Rationale: EQUITY passed_smart=222 out of 5799 scanned (3.8%) but opened 5655 — meaning the Smart gate is not actually gating opens. The gate and the open path are decoupled. Fix the wiring first, then raise the floor.
- **Confidence (1-5):** **1** (the edge is fake; the gate is broken).

---

### INDEX
- **Real/noise verdict:** **NOISE.** n_closed=5. WR=20%. passed_smart=1597/1915 (83%!) but only 8 closed. The Smart gate is passing almost everything and nothing is resolving. There is no edge to evaluate — this is a **sample-size failure**, not a signal. Do not compute PF on n=5.
- **90d expected P&L (1% risk, $100k):** **$0.** n=5 is not tradeable.
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` — raise aggressively to **80**. 83% pass rate on a "smart" gate is not smart; it's a rubber stamp. Also investigate why 1907 opened → 8 closed (0.4% resolution). The exit logic is broken for INDEX.
- **Confidence (1-5):** **1**.

---

### FOREX
- **Real/noise verdict:** **NOISE — and the "best_pf_overall" cell is a textbook leakage pattern.** `trust=UNK & fam=regime & dir=LONG` shows n=31, WR=77.4%, PF=4.08 — but `train_pf=0.0` on `train_n=5` and `holdout_pf=9.487` on `holdout_n=26`. A train PF of exactly 0.0 with 5 trades means **all 5 train trades were losses**, and the "edge" is entirely in the holdout. That is the opposite of walk-forward validation — it's a sign the split is non-random (likely chronological, and the regime shifted). `holdout_pass=false` and `bonferroni_pass=false` are correctly flagged. The `consensus` cell you flagged isn't in the top-3 here, but the `regime_terminal` source is the same family of concern: a single source producing 31 trades with 77% WR in a class where the overall WR is 42% is a **source-concentration artifact**, not an edge. FOREX passed_smart=23220/24127 = **96.2%**. The Smart gate is not gating FOREX at all.
- **90d expected P&L (1% risk, $100k):** **Negative.** Overall FOREX WR=42.23% on 521 decisive. At 1% risk with typical 1:1 R:R, expectancy ≈ 521 × 1% × (0.4223 − 0.5777) ≈ **−$810**. The "edge" cell would show +$1,400 if you believed it, but it fails holdout and Bonferroni. Report as **−$800 (do not trade the cell)**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` — raise to **70** AND add a hard cap on per-source contribution (e.g. no single source >20% of opened FOREX trades). The 96% pass rate is the root cause of the 22,765 opens.
- **Confidence (1-5):** **1**.

---

### CRYPTO
- **Real/noise verdict:** **THE ONLY CELL THAT SURVIVES SCRUTINY — with caveats.** `conf=C0.75-0.80 & score_dec=S50 & source=alpha_engine`: n=183, WR=71.04%, WR_shrunk=68.97%, PF=3.179, train_pf=3.429 (n=127), holdout_pf=2.631 (n=56), holdout_pass=true, wr_z=5.69, bonferroni_pass=true. This is the **only cell in the entire report** that passes both holdout and Bonferroni. The train/holdout PF ratio (3.43 → 2.63) is a healthy degradation, not a collapse. WR_shrunk of 69% on n=183 is credible. **However:** (a) `trust=UNK` again — the trust dimension is not adding information; (b) the cell is defined by `source=alpha_engine`, so this is really "alpha_engine's S50/conf-0.75-0.80 bucket is good," which is a **source-quality** finding, not a market-structure finding; (c) you flagged the `ml` cell — it's not in the top-3, but if there's an `ml` source with PF>5, treat it as suspect until it passes the same holdout+Bonferroni bar. The `alpha_engine` cell here does pass that bar. **This is the one edge I'd defend.**
- **90d expected P&L (1% risk, $100k):** Using the cell: 183 trades × 1% × avg_pnl 1.31% = **+$2,400 gross**. Apply 0.10% round-trip slippage on $100k notional per trade = 183 × $100 = $18,300 drag — wait, that's wrong sizing. At 1% risk ($1,000) with avg win 1.31% of notional, notional per trade ≈ $1,000 / (stop distance). If stop is 2%, notional = $50k, slippage 0.10% = $50/trade × 183 = $9,150. That kills the edge. **Realistic net: +$2,400 − $9,150 ≈ −$6,750.** The edge only survives if slippage is <0.02% round-trip (i.e., you're a maker, not a taker). **Report as +$2,400 gross / −$6,750 net at retail taker fees.** This is the honest number.
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` — **lower** to admit more of the `conf=0.75-0.80 & score_dec=S50 & source=alpha_engine` bucket, OR better: add a **source-conditional floor** so `alpha_engine` picks at conf≥0.75 bypass the generic score floor. The generic floor is currently filtering out the one bucket that works. Also: `HC_FILTER_TRUST_MIN` in `hc_filter.js` — the trust>=60 requirement is why passed_high_conviction=0. Either populate trust or drop the requirement to **trust>=0 (i.e., remove it)** until the field is real.
- **Confidence (1-5):** **3** (edge is real gross, marginal net of costs).

---

### COMMODITY
- **Real/noise verdict:** **WEAK / NOT PROVEN.** `trust=UNK & rr=RR>=2.0 & source=alpha_engine`: n=23, WR=73.9%, WR_shrunk=62.8%, PF=4.81, holdout_pass=true, but **bonferroni_pass=false** and n=23 is below your n>=20 threshold's comfort zone. The train_n=12 / holdout_n=11 split is too small to trust. Also: your registry explicitly killed [H-001] COT positioning and [H-036] inventory direction for COMMODITY — this cell is `source=alpha_engine` with `rr>=2.0`, which is a different signal, but the class has a documented history of leakage. Treat as **promising but unproven**. Do not size.
- **90d expected P&L (1% risk, $100k):** **$0 (unproven).** If you insisted: 23 × 1% × 1.80% = **+$414 gross**, but Bonferroni fail means this is likely one of ~20 cells tested and the winner by chance.
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` — raise to **70** (currently passing 3681/6098 = 60%, too loose). And add `rr>=2.0` as a **required** condition for COMMODITY Smart picks, since that's the only dimension showing signal.
- **Confidence (1-5):** **2**.

---

### FUTURES
- **Real/noise verdict:** **NOISE.** n_closed=13. WR=38.46%. Registry [H-005] already killed futures momentum. No PROVEN cells. Nothing to see.
- **90d expected P&L (1% risk, $100k):** **Negative.** 13 × 1% × (0.3846 − 0.6154) ≈ **−$30**. Trivially small, statistically meaningless.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` — raise to **80** or **disable FUTURES Smart picks entirely** until n_closed > 100. 133/186 = 71.5% pass rate on a class with 13 closed trades is noise generation.
- **Confidence (1-5):** **1**.

---

### ETF
- **Real/noise verdict:** **NOISE.** n_closed=9. WR=22%. No cells. 299/348 = 86% pass rate. Same pattern as INDEX.
- **90d expected P&L (1% risk, $100k):** **$0.** n=9.
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` — raise to **80** or disable. 86% pass rate is not a gate.
- **Confidence (1-5):** **1**.

---

### UNKNOWN
- **Real/noise verdict:** **DATA HYGIENE FAILURE.** 1395 scanned, 1392 opened, 3 closed, 0 wins. This is not an asset class — it's a classification bug. Every UNKNOWN trade should be quarantined and the classifier fixed.
- **90d expected P&L (1% risk, $100k):** **$0.**
- **Gate change:** Add a hard reject in `quality_gates.py`: `if asset_class == "UNKNOWN": return False`. Do not let unclassified trades reach the open path.
- **Confidence (1-5):** **5** (that this is a bug, not an edge).

---

### BOND
- **Real/noise verdict:** **NOISE.** n_closed=30, WR=43.3%. passed_smart=2/573 = 0.3% — the Smart gate is *over*-filtering BOND (opposite problem from FOREX). No cells.
- **90d expected P&L (1% risk, $100k):** **Negative.** 30 × 1% × (0.433 − 0.567) ≈ **−$40**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` — **lower** to admit more trades, OR disable BOND entirely. 2 passes out of 573 scans means the gate is either misconfigured or BOND signals are genuinely absent. Investigate before changing.
- **Confidence (1-5):** **1**.

---

### MEME
- **Real/noise verdict:** **NOISE.** n_closed=6. WR=16.7%. No cells. 12/27 = 44% pass rate. Nothing.
- **90d expected P&L (1% risk, $100k):** **$0.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME` — raise to **85** or disable. n=6 is not a class.
- **Confidence (1-5):** **1**.

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY:** **CRYPTO**, and only the `source=alpha_engine & conf=0.75-0.80 & score_dec=S50` bucket. It is the only cell in the entire 90-day report that passes holdout AND Bonferroni. Size it at 1% risk, but **only if you can execute as a maker** — at retail taker fees the edge is negative. If you cannot get maker fills, do not scale it; the gross edge is real but the net is not.

**DEMOTE per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` (mutate before kill):** **FOREX**. It has the largest sample (521 closed), the worst pass-through discipline (96% Smart pass rate), and a "best" cell that fails holdout and Bonferroni. Do not kill it — mutate it: (1) tighten `SMART_PICKS_MIN_SCORE_FOREX` to 70, (2) cap per-source contribution at 20%, (3) re-run 90d. If WR is still <50% after mutation, then kill.

**Immediate structural fixes (not class-specific):**
- `passed_high_conviction = 0` everywhere → the HC gate is non-functional. Either `trust` is never ≥60 or `score`/`conf` thresholds are wrong. Fix before any further edge analysis.
- Every PROVEN cell is `trust=UNK` → the trust dimension carries zero information. Remove it from cell definitions until it's populated.
- EQUITY opened 5655 / closed 144 (2.5% resolution) and FOREX opened 22765 / closed 1362 (6.0%) → the exit/resolution pipeline is the real bottleneck, not the entry gate. No edge analysis is trustworthy when 94-97% of positions never resolve.

**Do not trade:** EQUITY, INDEX, FOREX, FUTURES, ETF, UNKNOWN, BOND, MEME. That is 8 of 10 classes. The honest answer to "do not invent edges to look productive" is: **you have one marginal edge (CRYPTO alpha_engine) and nine classes that are either noise, leakage, or data-hygiene failures.**

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

**### EQUITY**
- Real/noise verdict: Noise/leakage. n=66 with 98.48% WR and PF=226 is statistically impossible in live trading; indicates data error, single-symbol concentration, or mislabeled closed trades.
- 90d expected P&L (1% risk, $100k): $0 (edge invalid).
- Gate change: SMART_PICKS_MIN_SCORE_EQUITY = 75
- Confidence (1-5): 5

**### INDEX**
- Real/noise verdict: No edge. n_closed=5, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: SMART_PICKS_MIN_SCORE_INDEX = 80
- Confidence (1-5): 5

**### FOREX**
- Real/noise verdict: No edge. Best_pf cells fail holdout and Bonferroni; n=31 too small and unstable.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: HC_MIN_CONF_FOREX = 0.82
- Confidence (1-5): 4

**### CRYPTO**
- Real/noise verdict: Marginally real. n=182–183, shrunk WR~69%, PF~3.18 with holdout pass and Bonferroni pass; only credible cell in the entire dataset.
- 90d expected P&L (1% risk, $100k): ~$4,800 (182 trades × 1% risk × ~1.31% avg edge after 0.15% slippage).
- Gate change: ALPHA_ENGINE_MIN_CONF_CRYPTO = 0.78
- Confidence (1-5): 3

**### COMMODITY**
- Real/noise verdict: No edge. n=70, zero proven cells; best_pf cells fail Bonferroni.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: SMART_PICKS_MIN_SCORE_COMMODITY = 70
- Confidence (1-5): 5

**### FUTURES**
- Real/noise verdict: No edge. n_closed=13, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: SMART_PICKS_MIN_SCORE_FUTURES = 75
- Confidence (1-5): 5

**### ETF**
- Real/noise verdict: No edge. n_closed=9, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: SMART_PICKS_MIN_SCORE_ETF = 80
- Confidence (1-5): 5

**### BOND**
- Real/noise verdict: No edge. n_closed=30, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: SMART_PICKS_MIN_SCORE_BOND = 75
- Confidence (1-5): 5

**### MEME**
- Real/noise verdict: No edge. n_closed=6, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: SMART_PICKS_MIN_SCORE_MEME = 85
- Confidence (1-5): 5

**### UNKNOWN**
- Real/noise verdict: No edge. n_closed=3, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: SMART_PICKS_MIN_SCORE_UNKNOWN = 80
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale CRYPTO today (only cell with real statistical support). Demote EQUITY immediately (clear leakage) and all other classes with n<50 closed or zero proven cells per MUTATION_THREE_AXIS_PROTOCOL.md.
