# Pick Funnel Swarm Verdict — 2026-11-09 04:08 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20261109T040746Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-Day Edge Analysis

Before the per-class verdicts, three structural facts dominate everything below:

1. **`passed_high_conviction = 0` across every single asset class.** The HC gate (`score>=80, conf>=0.75, trust>=60`) is *never* satisfied. Either the score distribution never reaches 80, or `trust>=60` is unreachable because almost every cell is `trust=UNK`. The dashboard's "HIGH CONVICTION" tab is dead code in production.
2. **`opened` >> `passed_smart` in most classes** (CRYPTO 10,128 opened vs 3,712 passed_smart; FOREX 23,215 vs 23,849; BOND 1,006 vs 1). The funnel is not actually gating opens — the "passed_smart" counter and the "opened" counter are measuring different populations. This is a **funnel integrity bug**, not an edge question.
3. **`trust=UNK` dominates every "proven" cell.** A trust band of UNKNOWN cannot be a real edge dimension — it means the trust score was never computed for those picks. Any cell keyed on `trust=UNK` is a proxy for "picks that bypassed the trust pipeline," which is a leakage smell, not a signal.

---

### CRYPTO
- **Real/noise verdict:** The `conf=C0.75-0.80 & source=alpha_engine` cell (n=229, WR_shrunk 63.45%, PF 2.13, holdout PF 1.46, bonferroni_pass=true) is the **only cell in the entire report that survives honest scrutiny**. Holdout PF dropping from 3.09 → 1.46 is exactly what you want to see (train overfit, holdout still positive). This is plausibly real but modest. The `rr=RR1.5-2.0` cell (PF 2.14) **fails holdout (1.135) and bonferroni** — do not cite it. The `ml` cell you flagged isn't in this dump; if it exists elsewhere with PF>5, treat it as leakage until proven otherwise. **Verdict: one real edge, narrow, ~63% shrunk WR.**
- **90d expected P&L (1% risk, $100k):** 229 trades × $1,000 risk × (0.6345 × avg_win_R − 0.3655 × 1R). With PF 2.13, avg_win_R ≈ 2.13 × 0.3655/0.6345 ≈ 1.23R. Expectancy ≈ 0.6345×1.23 − 0.3655×1 = **+0.415R/trade**. 229 × $1,000 × 0.415 ≈ **+$95,000 gross**, minus ~15% slippage/fees on 229 round-trips (~$8–12k) → **≈ +$83,000 net**. Caveat: this assumes the 229 historical trades are representative and non-overlapping; crypto positions often cluster, so effective n is lower.
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` — but the real fix is upstream: **add a `trust != UNK` requirement to the Smart_Picks scorer in `production_scanner.py`** so the edge cell becomes `trust=KNOWN & conf=0.75-0.80 & source=alpha_engine`. If forced to name one constant: set `SMART_PICKS_MIN_CONF_CRYPTO = 0.75` (currently likely 0.60) to concentrate flow into the proven band.
- **Confidence (1-5):** 3

### COMMODITY
- **Real/noise verdict:** **Noise.** Best cell (n=29, WR_shrunk 57.14%, PF 2.04) **fails holdout (1.137) and bonferroni**. n=40 closed total over 90 days is not enough to establish anything. The `score_dec=S50` cells are worse (holdout PF 0.65). And per H-001, this class has a documented history of COT look-ahead leakage producing fake 85% WR — the current 67.5% headline WR on n=40 is exactly the shape of that failure mode recurring. **Do not trade.**
- **90d expected P&L (1% risk, $100k):** $0 (no tradeable edge; if you traded the best cell anyway, expectancy ≈ +0.15R × 29 × $1,000 ≈ +$4,350 gross, but holdout says negative → **−$2,000 to +$4,000, i.e. noise**).
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` — raise to **75** and add a hard `n_closed >= 100` requirement before any cell is promoted to PROVEN. Currently the class is being scored on 40 trades.
- **Confidence (1-5):** 1

### FOREX
- **Real/noise verdict:** The `conf=C>=0.90 & fam=regime & source=regime_terminal` cell (n=40, WR_shrunk 73.33%, PF 9.27) is the **most suspicious number in the report**. PF 9.27 on 40 trades with holdout n=10 and holdout PF=99.0 (i.e., zero losses in holdout) is a textbook **small-sample / single-regime artifact**. `regime_terminal` as a source name suggests a terminal-state signal that fires rarely and may be look-ahead (regime labeled after the fact). The 85% raw WR with 34/40 wins is plausible for a regime filter but PF 9.27 implies avg_win/avg_loss ≈ 9×, which is not credible for FX. **Treat as leakage or single-symbol concentration until proven.** The class-level 52.24% WR on n=425 is the honest number — that's a coin flip minus costs.
- **90d expected P&L (1% risk, $100k):** If the regime cell is real: 40 × $1,000 × ~0.55R ≈ **+$22,000**. If it's leakage (my base case): **−$5,000 to +$5,000** on the class-level 52% WR after spread. **Report $0 as the honest estimate.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` — raise to **80** AND add `min_holdout_n >= 30` to the PROVEN promotion rule in `quality_gates.py`. The current rule promotes on holdout_n=10.
- **Confidence (1-5):** 2 (on the edge being real: 1)

### BOND
- **Real/noise verdict:** **No edge.** 1 passed_smart out of 1,037 scanned, 38.71% WR on n=31. The gate is correctly rejecting almost everything — but 1,006 "opened" trades means the gate isn't actually blocking opens. This is a funnel bug, not a signal.
- **90d expected P&L (1% risk, $100k):** **−$3,000 to −$5,000** (38.7% WR is a losing strategy at 1:1 R:R).
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` — set to **999** (effectively disable) until the funnel integrity bug is fixed. Do not open bond trades.
- **Confidence (1-5):** 1

### EQUITY
- **Real/noise verdict:** The `conf=C<0.60 & fam=mean_reversion` cell (n=61, WR 98.36%, PF 173) is **almost certainly leakage or a data artifact**. 60/61 wins with PF 173 is not a real equity mean-reversion edge — it's either (a) look-ahead in the mean-reversion signal, (b) a survivorship/delisting bias, or (c) a single-symbol concentration (one stock that went up 60 times). The fact that `trust=UNK` is a dimension confirms these picks bypassed the trust pipeline. **Flag as leakage recurrence.** The class-level 68.85% WR on n=122 is more believable but still small-n.
- **90d expected P&L (1% risk, $100k):** If the cell is real (it isn't): 61 × $1,000 × ~1.5R ≈ +$91,500. **Honest estimate: $0** — do not trade until the leakage is ruled out.
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` — raise to **75** AND add a `max_single_symbol_pct <= 0.20` constraint to the PROVEN promotion rule. The 98% WR cell is almost certainly one ticker.
- **Confidence (1-5):** 1 (on the edge being real)

### ETF
- **Real/noise verdict:** **No edge.** n=10 closed, 10% WR. Nothing to say.
- **90d expected P&L (1% risk, $100k):** **−$8,000 to −$9,000** (10% WR on 10 trades at 1:1).
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` — set to **999** (disable). 10 trades is not a sample.
- **Confidence (1-5):** 1

### INDEX
- **Real/noise verdict:** **No edge / no data.** n=1 closed. 100% WR on one trade is meaningless.
- **90d expected P&L (1% risk, $100k):** **$0** (no sample).
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` — set to **999** (disable) until n>=30.
- **Confidence (1-5):** 1

### UNKNOWN
- **Real/noise verdict:** **No edge.** n=3, 0% WR. This class shouldn't exist — it's a routing bug in the asset classifier. 1,307 scanned, 1,304 opened, 3 closed. The classifier is failing on ~10% of the universe.
- **90d expected P&L (1% risk, $100k):** **−$3,000** (0/3).
- **Gate change:** Fix the asset classifier in `production_scanner.py` — route UNKNOWN to a quarantine bucket, not to opens. No constant to name; this is a bug fix.
- **Confidence (1-5):** 1

### FUTURES
- **Real/noise verdict:** **No edge.** n=16, 37.5% WR. Per H-005, futures momentum was already investigated and failed. Nothing here contradicts that.
- **90d expected P&L (1% risk, $100k):** **−$4,000** (37.5% WR on 16 trades).
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` — set to **999** (disable).
- **Confidence (1-5):** 1

### MEME
- **Real/noise verdict:** **No edge.** n=9, 33% WR. 27 scanned total. Not a class, a rounding error.
- **90d expected P&L (1% risk, $100k):** **−$3,000** (33% WR on 9 trades).
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME` — set to **999** (disable).
- **Confidence (1-5):** 1

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY with real money: CRYPTO — and only CRYPTO, and only the `conf=0.75-0.80 & source=alpha_engine` cell.** It is the only cell in the report that passes holdout (PF 1.46), passes bonferroni, has n=229 (adequate), and has a shrunk WR (63.45%) that is consistent with the raw WR (64.63%) — i.e., not a small-sample artifact. Expected 90d P&L at 1% risk on $100k ≈ **+$83,000 net**. Size at half-Kelly initially (0.5% risk) until the next 30-day window confirms holdout PF >= 1.3.

**Demote per MUTATION_THREE_AXIS_PROTOCOL (mutate before kill):**
- **EQUITY** — the 98% WR / PF 173 cell is a leakage recurrence (trust=UNK + mean_reversion + n=61 is the exact shape of H-001's COT failure). Mutate: add `trust != UNK` and `max_single_symbol_pct <= 0.20` to the promotion rule, re-run 90d, and if the cell collapses to WR<55%, kill the mean_reversion family for equities.
- **FOREX** — the PF 9.27 regime cell is a small-sample artifact (holdout n=10). Mutate: require `holdout_n >= 30` for PROVEN, re-run, and if the regime cell doesn't survive, kill `regime_terminal` as a source.
- **COMMODITY** — already has a documented leakage history (H-001). Mutate: require `n_closed >= 100` for any cell to be promoted; the current 40-trade sample is not a basis for anything.

**Do not scale:** BOND, ETF, INDEX, UNKNOWN, FUTURES, MEME — all have n<35 closed and no cell passing holdout. These are not "small edges," they are "no data." Disable their Smart_Picks gates (set min score to 999) until the funnel integrity bug (opened >> passed_smart) is fixed and n>=100 per class.

**The single most important fix is not a gate constant — it's the funnel integrity bug.** `opened` exceeds `passed_smart` in 7 of 10 classes. Until that's resolved, every "edge" number in this report is computed on a population that the gates did not actually filter. Fix the counter before trusting any of the above.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### EQUITY
- Real/noise verdict: Noise/leakage — n=61 but PF=173 and WR_shrunk=86% on mean_reversion is statistically impossible in live equity data; single-symbol concentration or label bug almost certain.
- 90d expected P&L (1% risk, $100k): $0 (edge invalid; do not trade).
- Gate change: SMART_PICKS_MIN_SCORE_EQUITY = 75
- Confidence (1-5): 5

### CRYPTO
- Real/noise verdict: Marginally real on the C0.75-0.80 alpha_engine cells (n=229, WR_shrunk=63.45, PF=2.13, holdout_pass=true); best_pf_overall cells fail holdout and Bonferroni so treat as noise.
- 90d expected P&L (1% risk, $100k): ~$2,800 (assume 0.8% avg realized edge after 0.15% slippage + 0.1% commission on 229 trades).
- Gate change: hc_filter.js MIN_CONF = 0.78
- Confidence (1-5): 3

### FOREX
- Real/noise verdict: Noise — n=40 regime cell shows PF=9.267; this magnitude on regime_terminal source is classic look-ahead or single-pair concentration.
- 90d expected P&L (1% risk, $100k): $0 (edge invalid).
- Gate change: SMART_PICKS_MIN_TRUST = 65
- Confidence (1-5): 4

### COMMODITY
- Real/noise verdict: No edge — zero proven cells; best_pf_overall cells all fail holdout and Bonferroni.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_COMMODITY = 80
- Confidence (1-5): 5

### BOND
- Real/noise verdict: No edge — n=31 total closed, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_BOND = 70
- Confidence (1-5): 5

### ETF
- Real/noise verdict: No edge — n=10 closed, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_ETF = 75
- Confidence (1-5): 5

### FUTURES
- Real/noise verdict: No edge — n=16 closed, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_FUTURES = 70
- Confidence (1-5): 5

### MEME
- Real/noise verdict: No edge — n=9 closed, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_MEME = 80
- Confidence (1-5): 5

### INDEX
- Real/noise verdict: No edge — n=1 closed.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_INDEX = 70
- Confidence (1-5): 5

### UNKNOWN
- Real/noise verdict: No edge — n=3 closed.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_UNKNOWN = 70
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale CRYPTO today (only class with any holdout-passed cells at usable n). Demote EQUITY and FOREX per MUTATION_THREE_AXIS_PROTOCOL.md — both show clear leakage signatures and should be mutated (or ring-fenced) before any further capital allocation. All other classes have insufficient data; leave at current gates.
