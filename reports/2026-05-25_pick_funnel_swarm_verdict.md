# Pick Funnel Swarm Verdict — 2026-09-19 04:09 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260919T040943Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-day edge analysis

Before per-class verdicts, three system-wide red flags that color everything below:

1. **`passed_high_conviction = 0` in every single class.** The HC gate (score≥80, conf≥0.75, trust≥60) is effectively dead. Every "edge" you're about to read about is *below* your own conviction bar. That's a gate-design problem, not a market problem.
2. **`opened` >> `passed_smart` in most classes** (EQUITY 4780 opened vs 227 smart; FOREX 22529 vs 22975 — actually inverted; BOND 483 vs 7; INDEX 1573 vs 1425). The funnel is not gating what it opens. The "passed_smart" counter and the "opened" counter are measuring different things.
3. **`trust=UNK` dominates every PROVEN cell.** Every single "proven" edge in EQUITY, FOREX, CRYPTO, COMMODITY is `trust=UNK`. That means the trust dimension is not discriminating — it's a constant. Any cell that includes `trust=UNK` is really just the cell without trust. Treat those as duplicates, not independent confirmations.

---

### EQUITY
- **Real/noise verdict:** **NOISE / LEAKAGE.** The "PROVEN" cell is `fam=mean_reversion & score_dec=S40`, n=71, WR=98.59%, PF=226. All three "top edges" are the *same 71 trades* sliced three ways (trust, conf, dir are all constants within the cell — that's why they're identical). PF=226 with avg_pnl=1.27% and 70/71 wins is not a strategy, it's a **data artifact**. Most likely causes: (a) `score_dec=S40` is a decile bucket that's capturing a single symbol or a single date cluster, (b) exit logic is booking wins on a stale mark, (c) mean_reversion on EQUITY with 98% WR is the classic "held through earnings, marked at last print" signature. The train/holdout split (35/36) is *not* independent — it's a time split of the same 71 trades, so holdout_pass=true is meaningless here. **Do not trade this.**
- **90d expected P&L (1% risk, $100k):** **$0.** Not deploying. If forced to size the artifact: 71 trades × 1% × 1.27% avg = ~$900 gross, but I'd expect 100% of that to be given back on the first real fill.
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` — raise from current floor to **65**, and add a hard `MIN_UNIQUE_SYMBOLS_PER_CELL = 5` guard in `quality_gates.py` before any cell is allowed to be labeled PROVEN. The 71-trade cell almost certainly has <5 unique tickers.
- **Confidence (1-5):** **1**

---

### FOREX
- **Real/noise verdict:** **MOSTLY REAL, ONE CELL IS SUSPECT.** The headline cell `conf=C0.75-0.80 & rr=RR1.0-1.5 & fam=mean_reversion` (n=139, WR=66.9%, shrunk 64.8%, PF=2.78, holdout PF=1.42) is **plausible** — mean reversion on FX at tight RR with mid-confidence is a known effect, and the holdout degradation (3.47 → 1.42) is exactly what you'd expect from a real-but-decaying edge. Bonferroni passes. **However**, the `best_pf_overall` cell `... & dir=LONG & source=multi_asset_copytrader` (n=35, PF=4.67, bonferroni_pass=**false**) is the one to distrust — n=35, single source, LONG-only, and it fails multiple-testing correction. That's the "consensus copytrader" cell you flagged. **Do not treat it as proven.** The 139-trade cell is the only FOREX edge I'd defend.
- **90d expected P&L (1% risk, $100k):** Using the 139-trade cell only: 139 × $1,000 × 0.276% avg = **~$3,840 gross**. Apply 0.5 pip slippage on entry+exit (~0.02% round-trip on majors) → **~$3,600 net**. If you also include the 35-trade copytrader cell at half-size, add ~$700 but with wide error bars.
- **Gate change:** `SMART_PICKS_MIN_CONF_FOREX` — **pin to 0.75** (currently the cell that works is exactly at the 0.75-0.80 band; anything below is the 47.55% class-wide WR). Also add `REQUIRE_BONFERRONI_PASS = True` for any cell promoted to "PROVEN" — this kills the copytrader cell automatically.
- **Confidence (1-5):** **3**

---

### CRYPTO
- **Real/noise verdict:** **REAL, BUT THE PF IS INFLATED BY A SINGLE SOURCE.** `conf=C0.75-0.80 & score_dec=S50 & source=alpha_engine` (n=214, WR=76.6%, shrunk 74.4%, PF=4.06, holdout PF=4.46, bonferroni_pass=true). This is the strongest cell in the entire dataset — n is large, holdout *improves*, Bonferroni passes. **But**: `source=alpha_engine` is doing all the work. The cell without `source` (i.e., `conf=C0.75-0.80 & score_dec=S50`) is not shown, which means the edge is concentrated in one source. That's a **single-source concentration risk**, not necessarily leakage. The `ml` cell you mentioned isn't in the top-3 — if it exists elsewhere with PF>5, treat it as suspect until you can show it survives a source-ablation test. **Verdict: real edge, but you must verify it's not one strategy family inside alpha_engine.**
- **90d expected P&L (1% risk, $100k):** 214 × $1,000 × 1.45% avg = **~$31,000 gross**. Crypto slippage is brutal — assume 0.15% round-trip on liquid majors, 0.5%+ on alts. Blended ~0.25% → **~$25,600 net**. This is the only class where the dollar number is material.
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` — **raise to 55** (the S50 decile is where the edge lives; S40 and below is the 46% class-wide WR). Also add `REQUIRE_SOURCE_DIVERSITY = 2` before promoting any cell to PROVEN, so you don't over-fit to alpha_engine.
- **Confidence (1-5):** **4**

---

### COMMODITY
- **Real/noise verdict:** **NOISE.** `top_edges_proven` is **empty**. The `best_pf_overall` cell (`rr=RR>=2.0 & score_dec=S50`, n=21, PF=5.62) fails Bonferroni and has n=21 — that's below your own n≥20 threshold's spirit. Class-wide WR is 44%. This is consistent with the falsified H-001 (COT leakage) and H-036 (inventory direction) — the class has no stable edge. **Do not deploy.**
- **90d expected P&L (1% risk, $100k):** **$0.** If you forced the n=21 cell: 21 × $1,000 × 2.16% = ~$450 gross, but with n=21 and no Bonferroni pass, the 95% CI on that WR spans roughly 53%-91%. Expected value is indistinguishable from zero after slippage.
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` — **raise to 70** (effectively demote the class until a new hypothesis clears the registry). Per `MUTATION_THREE_AXIS_PROTOCOL.md`, this is a **mutate-before-kill** candidate: try (axis 1) restricting to non-cotton, non-ag, (axis 2) requiring RR≥2.0 AND conf≥0.75, (axis 3) source-diversity≥2. If none of the three mutations produces n≥50 with Bonferroni pass in 30 days, kill.
- **Confidence (1-5):** **1**

---

### BOND
- **Real/noise verdict:** **NOISE.** n_closed=25, no proven cells, class WR=24%. `passed_smart`=7 out of 508 scanned — the gate is already rejecting almost everything, which is correct. The 483 "opened" vs 7 "passed_smart" is a funnel-integrity bug, not an edge.
- **90d expected P&L (1% risk, $100k):** **$0.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` — **raise to 75** and add `MIN_CLOSED_FOR_PROMOTION = 50` so BOND can't be promoted on n=25.
- **Confidence (1-5):** **1**

---

### UNKNOWN
- **Real/noise verdict:** **NOISE / DATA HYGIENE FAILURE.** 1418 scanned, 0 wins, 10 losses, WR=0%. "UNKNOWN" as an asset class means the classifier is broken. This is not a strategy problem, it's a **labeling bug**. Every trade in this bucket should be re-classified or dropped.
- **90d expected P&L (1% risk, $100k):** **$0.**
- **Gate change:** Add `REJECT_IF_ASSET_CLASS_UNKNOWN = True` in `production_scanner.py` before scoring. Do not let UNKNOWN trades reach the funnel at all.
- **Confidence (1-5):** **5** (that it's noise)

---

### FUTURES
- **Real/noise verdict:** **NOISE.** n_closed=16, no proven cells, WR=43.75%. Consistent with falsified H-005 (momentum anti-signal). Too small to conclude anything except "no edge."
- **90d expected P&L (1% risk, $100k):** **$0.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` — **raise to 70**, and require `MIN_CLOSED_FOR_PROMOTION = 50`.
- **Confidence (1-5):** **1**

---

### MEME
- **Real/noise verdict:** **NOISE.** n_closed=4. Statistically meaningless. WR=25%.
- **90d expected P&L (1% risk, $100k):** **$0.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME` — **raise to 80** (effectively disable until n≥50).
- **Confidence (1-5):** **1**

---

### ETF
- **Real/noise verdict:** **NOISE.** n_closed=7, WR=14.29%. Meaningless.
- **90d expected P&L (1% risk, $100k):** **$0.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` — **raise to 80**.
- **Confidence (1-5):** **1**

---

### INDEX
- **Real/noise verdict:** **NOISE.** n_closed=4, WR=0%. Meaningless.
- **90d expected P&L (1% risk, $100k):** **$0.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` — **raise to 80**.
- **Confidence (1-5):** **1**

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY with real money: CRYPTO only.**
- The `conf=C0.75-0.80 & score_dec=S50 & source=alpha_engine` cell is the only one in the entire dataset that has: n≥200, Bonferroni pass, holdout PF ≥ train PF, and a plausible mechanism (mid-confidence, mid-score, single disciplined source).
- Size at **0.5% risk per trade** (not 1%) for the first 30 days, because the source-concentration risk is real. Expected 90d P&L at 0.5%: **~$12,800 net**.
- **Do not** scale FOREX yet — the 139-trade cell is real but the holdout PF of 1.42 is thin; paper-trade it for 30 more days at 1% risk and re-evaluate.

**DEMOTE per `MUTATION_THREE_AXIS_PROTOCOL.md` (mutate before kill):**
- **COMMODITY** is the primary demote candidate. It has already had two hypotheses falsified (H-001, H-036), the class-wide WR is 44%, and the only "best" cell fails Bonferroni. Run the three-axis mutation (non-ag restriction / RR+conf tightening / source diversity) for 30 days. If no cell clears n≥50 + Bonferroni, kill the class.
- **EQUITY** is the secondary demote candidate — but for a different reason. The 98.59% WR cell is almost certainly a **leakage recurrence** (the signature matches H-001's pattern: extreme WR, single-bucket concentration, train/holdout split that isn't truly out-of-sample). Before mutating, audit the 71 trades for: unique symbol count, date clustering, and whether exits are marked-to-last vs marked-to-fill. If it's leakage, kill the cell and re-run the funnel; if it's real, it's the best edge in the book and you should be embarrassed it's not in HC.

**Two gate changes that matter more than any single constant:**
1. **`passed_high_conviction = 0` across all 10 classes** means `hc_filter.js` thresholds (score≥80, conf≥0.75, trust≥60) are miscalibrated against the actual score distribution. Either lower the score threshold to 70 or fix the trust dimension (which is `UNK` everywhere — it's not functioning). A gate that passes nothing is not a gate.
2. **`opened` >> `passed_smart`** in 7 of 10 classes means the funnel is not actually gating execution. Fix the wiring before you trust any of these WR numbers — right now you're measuring the WR of trades that *bypassed* your gates, not trades that *passed* them.

**Bottom line:** One real edge (CRYPTO, single source), one plausible edge (FOREX, decaying), one likely-leakage artifact (EQUITY), and seven classes with no edge. The honest answer to "do not invent edges" is: **you have one edge, and it's concentrated in one source.** Everything else is either noise or a bug.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### EQUITY
- Real/noise verdict: Noise/leakage — PF=226 and 98.59% WR on n=71 mean_reversion S40 cells are statistically impossible in live trading; violates every known market-efficiency bound and matches single-symbol concentration patterns seen in rejected hypotheses.
- 90d expected P&L (1% risk, $100k): $0 (edge is artifact; any real deployment would hit immediate slippage/widening and collapse to ~45% WR).
- Gate change: SMART_PICKS_MIN_SCORE_EQUITY = 65
- Confidence (1-5): 5

### FOREX
- Real/noise verdict: Marginally real on the mean_reversion C0.75-0.80 RR1.0-1.5 cell (n=139, WR_shrunk=64.78, PF=2.78, holdout_pass=true) but best_pf_overall cells fail bonferroni and show modest degradation; no clear leakage flag but not robust.
- 90d expected P&L (1% risk, $100k): ~$1,850 (assume ~45 qualifying trades/90d at 0.28% avg edge after 0.05% slippage, 1% risk).
- Gate change: HC_FILTER_MIN_CONF = 0.78
- Confidence (1-5): 3

### CRYPTO
- Real/noise verdict: Real on the alpha_engine C0.75-0.80 S50 LONG cells (n=213-214, WR_shrunk~74.5, PF=4.06, holdout_pass=true, bonferroni_pass=true); numbers are high but within crypto-volatility norms and survive walk-forward.
- 90d expected P&L (1% risk, $100k): ~$8,700 (assume ~70 qualifying trades/90d at 1.45% avg edge after 0.12% slippage, 1% risk).
- Gate change: SMART_PICKS_MIN_SCORE_CRYPTO = 52
- Confidence (1-5): 4

### COMMODITY
- Real/noise verdict: Noise — top cells have n=21, bonferroni=false, and PF inflated by holdout outlier; matches pattern of previously rejected inventory/COT signals.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: N/A
- Confidence (1-5): 5

### ETF
- Real/noise verdict: Noise — n=7 decisive trades, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: N/A
- Confidence (1-5): 5

### UNKNOWN
- Real/noise verdict: Noise — n=10 decisive trades, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: N/A
- Confidence (1-5): 5

### FUTURES
- Real/noise verdict: Noise — n=16 decisive trades, zero proven cells; prior futures_momentum hypothesis already rejected.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: N/A
- Confidence (1-5): 5

### BOND
- Real/noise verdict: Noise — n=25 decisive trades, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: N/A
- Confidence (1-5): 5

### INDEX
- Real/noise verdict: Noise — n=4 decisive trades, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: N/A
- Confidence (1-5): 5

### MEME
- Real/noise verdict: Noise — n=4 decisive trades, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: N/A
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale CRYPTO today (only class with statistically credible, holdout-validated edge large enough to survive 1% risk sizing). Demote EQUITY immediately per MUTATION_THREE_AXIS_PROTOCOL — its “edge” is a leakage recurrence that must be mutated (score floor + symbol diversification) before any further capital allocation. All other classes have insufficient or falsified signal; leave gates unchanged.
