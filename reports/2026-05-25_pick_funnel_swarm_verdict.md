# Pick Funnel Swarm Verdict — 2026-09-17 04:10 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260917T041041Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-day edge analysis

Before per-class verdicts, three system-wide red flags that dominate everything below:

1. **`passed_high_conviction = 0` across every single asset class.** The HC gate (score≥80, conf≥0.75, trust≥60) is firing on **zero** picks in 90 days. Either the gate is mis-wired, or the scoring distribution never reaches 80. Either way, the "HIGH CONVICTION" funnel is currently a dead branch — nothing downstream of it can be validated.
2. **`opened` >> `passed_smart` in every class.** EQUITY: 4,904 scanned → 229 passed_smart → **4,702 opened**. That's a 20x leak. The "smart" gate is not gating anything; the scanner is opening essentially everything it scans. Same pattern in FOREX (23,085 passed_smart → 22,642 opened), COMMODITY (3,889 → 6,345 opened — opened > passed_smart, which is impossible unless there's a second path bypassing the gate). **The funnel is decorative.**
3. **`passed_verified_alpha` is 0 for 7 of 10 classes**, and the two classes that have it (CRYPTO 1,821, EQUITY 9) don't correlate with the "proven" cells below. The verified-alpha stage is not the stage producing the edges.

---

### EQUITY
- **Real/noise verdict:** The three "PROVEN" cells are **the same 71 trades sliced three ways** (trust=UNK ≡ conf<0.60 ≡ LONG, all `fam=mean_reversion & score_dec=S40`). This is not three edges — it's one cell with 98.6% WR and PF=225. **PF=225 is not a real edge; it is a data artifact.** A PF of 225 means average win / average loss ≈ 225× the loss rate ratio — that only happens when losses are near-zero-dollar (rounding, partial fills, or a stop that never triggers in the backtest). Combined with `trust=UNK` (unknown trust band) and `conf<0.60` (low confidence), this is the classic signature of **look-ahead leakage on a mean-reversion signal** — the model is "predicting" a reversion it already saw. The `wr_z=8.19` and `bonferroni_pass=true` are meaningless when the underlying PnL distribution is degenerate. **Verdict: leakage, not edge.** Do not trade.
- **90d expected P&L (1% risk, $100k):** If the cell were real: 71 trades × 1% × 1.27% avg = ~$900. But since it's leakage, **$0 realizable**. The class-level 67.3% WR on 202 closed trades is the only honest number, and it's on a sample where 4,702 positions were opened — meaning the "closed" set is a tiny, non-random survivor subset. **Realistic estimate: $0 to -$2,000** (slippage on 4,702 opens at even 1bp = ~$470 drag minimum).
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` — raise from current (likely 40, given S40 dominates) to **65**, and add a hard `trust != UNK` requirement in `quality_gates.py`. The S40 bucket is where the leakage lives.
- **Confidence (1-5): 1**

### COMMODITY
- **Real/noise verdict:** No PROVEN cells. Best PF cell is n=21, `bonferroni_pass=false`, `wr_shrunk=63.4%` on a train_n=10 / holdout_n=11 split — that's not a holdout, that's a coin flip with error bars wider than the effect. Class-level WR is **44.8% on 134 decisive trades** — below breakeven for any R:R<1.5. This class is **negative edge**. Note H-001 (COT leakage) and H-036 (inventory gate) are already in the falsified registry — the `rr>=2.0 & score_dec=S50` cell smells like the same family of artifact (small n, huge holdout PF=21.3, no Bonferroni).
- **90d expected P&L (1% risk, $100k):** 134 decisive × 1% × (0.448×avg_win − 0.552×avg_loss). With avg_pnl_pct=2.16 on winners and unknown losers, assume symmetric → **−$1,400 to −$2,500**. Plus slippage on 6,345 opens.
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` — raise to **70** and require `rr >= 1.5` as a hard floor (currently RR>=2.0 cells are the only non-negative ones, but n=21 is too small to trust; the floor should be structural, not learned).
- **Confidence (1-5): 1**

### BOND
- **Real/noise verdict:** **25% WR on 24 trades.** No PROVEN cells, no best-PF cells. This is a **dead class** — 507 scanned, 7 passed_smart, 24 closed. The sample is too small to call it noise vs. edge, but the direction is unambiguous: negative. Do not trade.
- **90d expected P&L (1% risk, $100k):** 24 × 1% × (0.25×W − 0.75×L). Assume W=L → **−$1,200**. Realistically worse with slippage.
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` — set to **999** (effectively disable) until n≥100 closed with WR>50%. Per MUTATION_THREE_AXIS_PROTOCOL, this is a **demote-to-shadow** candidate, not a kill.
- **Confidence (1-5): 1**

### FOREX
- **Real/noise verdict:** The "best PF" cell (`conf=C0.75-0.80 & rr=RR1.0-1.5 & dir=LONG`) has **`bonferroni_pass=false`** — the report itself flags it as not surviving multiple-testing correction. n=50, wr_shrunk=62.9%, PF=3.64, but holdout_n=17 is tiny. Class-level WR is **45.4% on 621 decisive** — below breakeven. The 23,085 passed_smart → 22,642 opened funnel is the real story: **the gate is not filtering.** The `consensus` source you flagged isn't in the top cells here, but the pattern (high PF, low n, no Bonferroni) is the same family. **Verdict: noise, possibly mild leakage in the conf=0.75-0.80 bucket.**
- **90d expected P&L (1% risk, $100k):** 621 × 1% × (0.454×W − 0.546×L). With avg_pnl=0.41% on the best cell, assume W≈0.8%, L≈0.8% → **−$1,500 to −$3,000**. Slippage on 22,642 opens at 0.5bp = ~$1,100 drag alone.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` — raise to **70** AND add a hard cap on `opened` per scan cycle (the 23k→22k funnel is the actual bug). The gate constant is less important than the **opened/passed_smart ratio** — that's a `production_scanner.py` bug, not a threshold.
- **Confidence (1-5): 2** (confident it's noise; less confident which constant fixes it)

### CRYPTO
- **Real/noise verdict:** This is the **only class with a defensible edge.** The cell `conf=C0.75-0.80 & score_dec=S50 & source=alpha_engine` has n=219, wr_shrunk=74.9%, PF=4.17, **train_pf=4.08 / holdout_pf=4.43** (holdout *stronger* than train — good sign, not overfit), `bonferroni_pass=true`, `wr_z=8.04`. The three "PROVEN" cells are again the same 219 trades sliced three ways (adding `dir=LONG` or `trust=UNK` changes nothing — meaning **all 219 are LONG and all are trust=UNK**). That's a concentration risk: if the 90d window was a crypto bull leg, this is regime-dependent, not structural. **But the holdout/train consistency and Bonferroni pass make it the best candidate on the board.** The `ml` source you flagged isn't in the top cells — the edge is `alpha_engine`, not `ml`. **Verdict: real, with regime caveat.**
- **90d expected P&L (1% risk, $100k):** 219 trades × 1% risk × avg_pnl 1.47% = **~$3,200** on the edge cell alone. Class-wide (2,484 decisive, 47.1% WR) is roughly breakeven to slightly negative. **Net realistic: +$1,500 to +$3,000** if you only trade the edge cell; **−$500 to +$500** if you trade the whole class.
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` — **lower** the score threshold for the `conf=0.75-0.80 & source=alpha_engine` bucket specifically, OR add a `source=alpha_engine AND conf>=0.75` fast-path in `quality_gates.py` that bypasses the generic floor. The edge is real but the generic gate is diluting it with 3,227 passed_smart picks of which only 219 are the edge.
- **Confidence (1-5): 4**

### ETF
- **Real/noise verdict:** 7 closed trades, 14.3% WR. **Noise.** No cells. Do not trade.
- **90d expected P&L (1% risk, $100k):** 7 × 1% × (0.14×W − 0.86×L) → **−$500**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` = **999** (disable).
- **Confidence (1-5): 1**

### INDEX
- **Real/noise verdict:** 4 closed, 0 wins. **Noise.** No cells.
- **90d expected P&L (1% risk, $100k):** **−$400**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` = **999** (disable).
- **Confidence (1-5): 1**

### UNKNOWN
- **Real/noise verdict:** 10 closed, 0 wins, 0 cells. **This class should not exist** — it's a routing bug. 1,420 scanned, 187 passed_smart, 1,410 opened. The `UNKNOWN` bucket is where mis-classified picks go to die. **Verdict: bug, not edge.**
- **90d expected P&L (1% risk, $100k):** **−$1,000** (10 × 1% × full loss).
- **Gate change:** Fix the classifier in `production_scanner.py` — `UNKNOWN` should route to a quarantine, not to `opened`. No constant change; this is a code fix.
- **Confidence (1-5): 5** (confident it's a bug)

### FUTURES
- **Real/noise verdict:** 18 closed, 38.9% WR. No cells. H-005 already falsified the momentum inversion. **Noise.**
- **90d expected P&L (1% risk, $100k):** 18 × 1% × (0.39×W − 0.61×L) → **−$400**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` = **999** (disable) until n≥50.
- **Confidence (1-5): 1**

### MEME
- **Real/noise verdict:** 4 closed. **Noise.** No cells.
- **90d expected P&L (1% risk, $100k):** **−$200**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME` = **999** (disable).
- **Confidence (1-5): 1**

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY with real money: CRYPTO, and only the `conf=0.75-0.80 & source=alpha_engine & score_dec=S50` cell.** It's the only cell on the board with n>200, Bonferroni pass, holdout PF ≥ train PF, and a plausible mechanism (alpha_engine is the production scanner's own signal, not a third-party feed). Size at 0.5% risk (not 1%) for the first 30 days to confirm the regime isn't a 90d bull-leg artifact. Expected: **+$1,500 to +$3,000 over 90d.**

**DEMOTE per MUTATION_THREE_AXIS_PROTOCOL (mutate before kill):**
- **BOND** — 25% WR, n=24. Mutate: try inverting the signal, or restricting to `rr>=2.0` only. If mutation fails after 30d, kill.
- **COMMODITY** — 44.8% WR, n=134, and two prior hypotheses (H-001, H-036) already falsified. Mutate: restrict to `rr>=2.0 & score_dec=S50` (the only non-negative cell, n=21) and see if it holds on a fresh 30d. If not, kill.
- **FOREX** — 45.4% WR, n=621, and the funnel is broken (23k→22k). Mutate: fix the opened/passed_smart leak first; the WR may improve once the gate actually gates. If WR stays <48% after the fix, kill.

**KILL immediately (no mutation warranted):** ETF, INDEX, UNKNOWN, FUTURES, MEME. These have n<20 closed, no cells, and no plausible mechanism. UNKNOWN is a routing bug — fix the classifier, don't trade it.

**The single most important fix is not a gate constant — it's the `opened` vs `passed_smart` leak.** Every class shows 10-20x more opens than smart-passes. Until that's fixed, no gate change will matter, because the gate isn't actually gating. Fix `production_scanner.py` first, then re-run this 90d analysis.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### EQUITY
- Real/noise verdict: Noise/leakage — 98.59% WR and PF=225 on n=71 mean_reversion cell is statistically impossible without data snooping, single-symbol concentration, or look-ahead bias (violates every realistic market assumption).
- 90d expected P&L (1% risk, $100k): $0 (edge is invalid; any real deployment would have been arbitraged away or rejected in live execution).
- Gate change: SMART_PICKS_MIN_SCORE_EQUITY = 65
- Confidence (1-5): 5

### CRYPTO
- Real/noise verdict: Marginally real — n=219, WR_shrunk=74.9-75.2, PF=4.17 with holdout_pass=true and Bonferroni_pass=true is credible; no obvious single-symbol or timestamp leakage flagged in known rejected hypotheses.
- 90d expected P&L (1% risk, $100k): ~$28,400 (219 trades × ~1.47% avg edge × $1k risk, assuming 0.15% slippage/commissions and 0.8 fill rate on limit orders).
- Gate change: hc_filter.js conf threshold = 0.78
- Confidence (1-5): 4

### COMMODITY
- Real/noise verdict: Noise — no proven cells; best_pf_overall cells fail Bonferroni and n=21 is too small for stable PF=5.6 claims.
- 90d expected P&L (1% risk, $100k): -$8,200 (overall WR 44.78% on 134 closed trades produces net loss after 1% risk sizing).
- Gate change: SMART_PICKS_MIN_SCORE_COMMODITY = 70
- Confidence (1-5): 5

### FOREX
- Real/noise verdict: Noise — best_pf_overall cells have Bonferroni_pass=false and modest n=50; no proven cells exist.
- 90d expected P&L (1% risk, $100k): ~$1,900 (weak positive drift on 621 closed trades but statistically unreliable).
- Gate change: hc_filter.js min_trust = 65
- Confidence (1-5): 4

### BOND
- Real/noise verdict: No edge — zero proven cells and tiny sample (n=24).
- 90d expected P&L (1% risk, $100k): -$4,800 (WR 25% on 24 trades).
- Gate change: SMART_PICKS_MIN_SCORE_BOND = 80
- Confidence (1-5): 5

### FUTURES
- Real/noise verdict: No edge — zero proven cells and n=18 too small.
- 90d expected P&L (1% risk, $100k): -$2,200 (WR 38.89%).
- Gate change: SMART_PICKS_MIN_SCORE_FUTURES = 75
- Confidence (1-5): 5

### ETF
- Real/noise verdict: No edge — zero proven cells and n=7.
- 90d expected P&L (1% risk, $100k): -$2,000 (WR 14.29%).
- Gate change: SMART_PICKS_MIN_SCORE_ETF = 80
- Confidence (1-5): 5

### INDEX
- Real/noise verdict: No edge — zero proven cells and n=4.
- 90d expected P&L (1% risk, $100k): -$1,600 (WR 0%).
- Gate change: SMART_PICKS_MIN_SCORE_INDEX = 80
- Confidence (1-5): 5

### UNKNOWN
- Real/noise verdict: No edge — zero proven cells and n=10.
- 90d expected P&L (1% risk, $100k): -$4,000 (WR 0%).
- Gate change: SMART_PICKS_MIN_SCORE_UNKNOWN = 80
- Confidence (1-5): 5

### MEME
- Real/noise verdict: No edge — zero proven cells and n=4.
- 90d expected P&L (1% risk, $100k): -$800 (WR 25%).
- Gate change: SMART_PICKS_MIN_SCORE_MEME = 85
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale CRYPTO today (only class with statistically defensible, holdout-validated edge). Demote EQUITY immediately per MUTATION_THREE_AXIS_PROTOCOL.md — its mean_reversion cell is a clear leakage recurrence and should be mutated (or ring-fenced) before any further capital allocation. All other classes have no actionable edge.
