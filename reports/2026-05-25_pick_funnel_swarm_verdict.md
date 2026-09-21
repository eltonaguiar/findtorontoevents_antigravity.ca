# Pick Funnel Swarm Verdict — 2026-09-21 04:12 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260921T041152Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-day edge analysis

Before the per-class verdicts, three cross-cutting observations that shape everything below:

1. **The funnel is broken at the top.** `passed_high_conviction = 0` for *every* class. The HC gate (`score>=80, conf>=0.75, trust>=60`) is dead code in production — nothing has ever cleared it in 90 days. That's not a "tight gate," that's a mis-wired gate.
2. **`opened` >> `passed_smart` in every class** (e.g. EQUITY 5284 opened vs 220 passed_smart; FOREX 22294 vs 22701 — the only class where they roughly match). The scanner is opening trades that never passed the Smart gate. Either the funnel telemetry is wrong or the gate is advisory-only. Either way, the "passed_smart" column is not what's actually being traded.
3. **`passed_verified_alpha` is 0 for 8 of 10 classes.** Only CRYPTO (1785) and FUTURES/MEME (1 each) have any. So "verified alpha" is effectively a CRYPTO-only concept right now.

---

### EQUITY
- **Real/noise verdict:** **NOISE / LEAKAGE.** The "PROVEN" cell `fam=mean_reversion & score_dec=S40` shows WR=98.55% (68/69), PF=219.3, and — the tell — `conf=C<0.60`. A mean-reversion strategy with *low* confidence producing a 219x profit factor is not an edge, it's a labeling artifact. The `score_dec=S40` bucket is almost certainly a post-hoc score decile assigned *after* outcome, or the "win" definition is being computed on a subset where losers were reclassified (e.g. timeouts excluded, or a single symbol like a low-float name that gapped). n=69 with 68 wins and holdout_pf=99.0 is the classic signature of a deterministic outcome (e.g. "did price touch entry±ε within 1 bar" on a mean-reverting ticker). **Do not trade this.** Flag as leakage recurrence of the H-001 pattern (single-instrument concentration + timestamp issue).
- **90d expected P&L (1% risk, $100k):** **$0** — do not deploy. If you naively sized the 69 trades at 1% risk with avg_pnl=1.27%, you'd "expect" ~$870 gross, but the number is not real.
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` — raise from current value to **≥65** and add a hard `min_confidence >= 0.65` requirement. The current gate is admitting `conf<0.60` mean-reversion trades that are the source of the fake edge.
- **Confidence (1-5):** **1**

### FOREX
- **Real/noise verdict:** **MARGINALLY REAL, but fragile.** The headline cell `conf=C0.75-0.80 & rr=RR1.0-1.5 & fam=mean_reversion` has n=124, WR_shrunk=65.97%, PF=3.115, holdout_pf=1.339 (n=33). The holdout PF collapse from 4.29 → 1.34 is the honest signal: the train edge is real-ish, the holdout is barely above breakeven. The `dir=LONG` sub-cell (n=43, PF=5.795) **fails Bonferroni** — treat as noise. The class-level WR of 48.99% (267W/278L) is a coin flip. **The only defensible statement: FOREX mean-reversion at conf 0.75–0.80 with RR 1.0–1.5 has a small, decaying edge.** The "consensus" cell you flagged isn't in the top-3 here, but the pattern (high PF on small n, holdout collapse) is the same family.
- **90d expected P&L (1% risk, $100k):** Using the *proven* cell only (n=124, avg_pnl=0.31%, 1% risk = $1,000/trade): **~$385 gross**, minus ~$250 in spread/commission on 124 FX round-trips (assume 2 pips on $100k = $20/trade × 124 = $2,480 — wait, that kills it). Recompute: at $100k notional, 1% risk = $1,000 risk, avg win 0.31% of notional = $310. 85 wins × $310 = $26,350; 39 losses × ~$1,000 = $39,000. **Net negative before costs.** The PF=3.1 is on *R-multiples*, not dollars — the avg_pnl_pct of 0.31% is the real number and it's below the cost floor. **Expected P&L: -$15k to -$25k.** Do not deploy.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` — raise to **≥70** and add `min_rr >= 1.5`. The RR1.0-1.5 bucket is where the fake edge lives; forcing RR≥1.5 removes it.
- **Confidence (1-5):** **2**

### CRYPTO
- **Real/noise verdict:** **REAL, and the only class I'd touch.** The cell `conf=C0.75-0.80 & dir=LONG & score_dec=S50 & source=alpha_engine` has n=207, WR_shrunk=74.01%, PF=3.945, **holdout_pf=4.099 (n=39)**, wr_z=7.576, **bonferroni_pass=true**. Holdout PF *exceeding* train PF is unusual and worth a leakage check, but the cell is narrow (one source, one conf band, one score decile) and the n is large enough that Bonferroni survival is meaningful. The `trust=UNK` variant is identical (n=208) — meaning trust is not discriminating here, which is itself a finding: the trust score is not adding information on CRYPTO. **Caveat:** the "ml" cell you flagged isn't in the top-3, but the `source=alpha_engine` concentration (100% of the proven edge) means this is a single-source edge. If alpha_engine degrades, the edge vanishes.
- **90d expected P&L (1% risk, $100k):** 207 trades × 1% risk = $1,000 risk/trade. 158 wins × avg_pnl 1.44% × $100k = $2,275/wait — recompute properly. At $100k notional, 1% risk = $1,000. Avg win = 1.44% × $100k = $1,440. 158 × $1,440 = $227,520. 49 losses × $1,000 = $49,000. **Gross ≈ $178,500.** Subtract slippage: crypto round-trip ~0.15% × $100k = $150/trade × 207 = $31,050. **Net ≈ $147,000.** Even at 50% haircut for regime change: **~$70k.** This is the only class where the math survives costs.
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` — **lower** to admit more of this cell, OR better: add a `source_whitelist = ["alpha_engine"]` for CRYPTO and set `SMART_PICKS_MIN_CONF_CRYPTO = 0.75`. The current gate is passing 3242 smart picks but only 1785 verified-alpha — the gap is where the edge is being diluted.
- **Confidence (1-5):** **4**

### COMMODITY
- **Real/noise verdict:** **NOISE.** Best cell n=21, holdout_n=11, **bonferroni_pass=false**, wr_z=2.4. The `rr=RR>=2.0 & score_dec=S50` cell has holdout_pf=21.3 on 11 trades — that's not an edge, that's 11 coin flips that happened to land. Class WR 44.36% (59W/74L) is below breakeven. **This class has no edge.** The H-001 and H-036 rejections already told us this; the current data confirms it.
- **90d expected P&L (1% risk, $100k):** **Negative.** 59 wins × ~$1,000 = $59k; 74 losses × $1,000 = $74k. **Net ≈ -$15k** before costs, worse after.
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` — raise to **≥75** and require `min_rr >= 2.0` AND `min_n_historical >= 50` for the cell. Effectively: stop trading COMMODITY until a cell with n≥50 and holdout_pass=true appears.
- **Confidence (1-5):** **1**

### ETF
- **Real/noise verdict:** **NOISE.** n_closed=7. WR=14.29%. No proven cells. Not enough data to say anything except "don't trade this."
- **90d expected P&L (1% risk, $100k):** **~-$5k** (1 win, 6 losses at $1k risk each).
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` — raise to **≥80** (effectively disable until n≥30).
- **Confidence (1-5):** **1**

### UNKNOWN
- **Real/noise verdict:** **NOISE / DATA HYGIENE FAILURE.** 1420 scanned, 1410 opened, 10 closed, 0 wins. The fact that 1410 trades were opened in an "UNKNOWN" class means the classifier is broken. This isn't a strategy problem, it's a routing problem.
- **90d expected P&L (1% risk, $100k):** **-$10k** (0W/10L).
- **Gate change:** Add a hard reject in `production_scanner.py`: `if asset_class == "UNKNOWN": skip`. Do not open trades you can't classify.
- **Confidence (1-5):** **1**

### FUTURES
- **Real/noise verdict:** **NOISE.** n_closed=18, no proven cells. H-005 already killed the momentum inversion. Nothing here.
- **90d expected P&L (1% risk, $100k):** **~-$4k** (7W/11L).
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` — raise to **≥80** (disable until n≥50).
- **Confidence (1-5):** **1**

### BOND
- **Real/noise verdict:** **NOISE.** n_closed=25, WR=24%, no proven cells. 7 passed_smart out of 506 scanned — the gate is already rejecting almost everything, which is correct.
- **90d expected P&L (1% risk, $100k):** **~-$13k** (6W/19L).
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` — keep high, add `min_confidence >= 0.70`. Effectively disabled.
- **Confidence (1-5):** **1**

### INDEX
- **Real/noise verdict:** **NOISE.** n_closed=7, 0 wins. 1425 passed_smart out of 1580 scanned — the gate is passing 90% of INDEX picks, which is the opposite of a gate.
- **90d expected P&L (1% risk, $100k):** **~-$4k** (0W/4L).
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` — raise to **≥75**. The current gate is a rubber stamp.
- **Confidence (1-5):** **1**

### MEME
- **Real/noise verdict:** **NOISE.** n_closed=4. Nothing to say.
- **90d expected P&L (1% risk, $100k):** **~-$2k** (1W/3L).
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME` — raise to **≥85** (effectively disable).
- **Confidence (1-5):** **1**

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY: CRYPTO only.** The `conf=C0.75-0.80 & dir=LONG & score_dec=S50 & source=alpha_engine` cell is the only one in the entire dataset that survives Bonferroni, has n>200, has holdout PF > train PF, and has an avg_pnl_pct (1.44%) that clears realistic crypto costs. Size it at 1% risk per trade, cap at 5 concurrent positions, and monitor the alpha_engine source for degradation. Expected 90d P&L: **~$70k–$147k** depending on regime.

**DEMOTE per MUTATION_THREE_AXIS_PROTOCOL: COMMODITY.** It has already been killed twice (H-001, H-036), the current data shows no proven cells, and the best cell fails Bonferroni. Per the protocol, mutate before kill: the mutation axis to try is **source** — restrict COMMODITY to `source=alpha_engine` only (matching the CRYPTO edge) and re-test in 30 days. If no cell with n≥50 and holdout_pass=true emerges, kill the class.

**Everything else (EQUITY, FOREX, ETF, UNKNOWN, FUTURES, BOND, INDEX, MEME):** Do not deploy real money. The EQUITY "98.55% WR" cell is a leakage recurrence — flag it to the hypothesis registry as a potential H-001-family artifact and audit the `score_dec=S40` labeling logic before trusting any EQUITY edge. FOREX is the only other class with a *possibly* real edge, but the holdout PF collapse (4.29 → 1.34) and the cost math make it a paper-trade-only candidate for now.

**The single highest-leverage fix:** the HC gate is returning 0 for every class. Either the thresholds (`score>=80, conf>=0.75, trust>=60`) are miscalibrated against the actual score distribution, or `hc_filter.js` is not being invoked. Fix the telemetry before trusting any of the "passed_high_conviction" columns — right now they're telling you nothing.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

**### EQUITY**
- Real/noise verdict: Noise/leakage. 98.55% WR and 219 PF on n=69 mean_reversion trades is statistically impossible without single-symbol concentration or data bug; rejected per protocol.
- 90d expected P&L (1% risk, $100k): $0 (edge is artifact).
- Gate change: SMART_PICKS_MIN_SCORE_EQUITY = 65
- Confidence (1-5): 5

**### FOREX**
- Real/noise verdict: Mostly noise. Holdout PF collapses (4.286 → 1.339) on the strongest cell; bonferroni fails on best_pf cells; no stable edge after shrinkage.
- 90d expected P&L (1% risk, $100k): -$1,800 (expected negative expectancy once slippage applied).
- Gate change: HC_MIN_CONF = 0.82
- Confidence (1-5): 4

**### CRYPTO**
- Real/noise verdict: Real. n=207–208, WR_shrunk 73.7–74%, PF 3.94, holdout passes, bonferroni passes, wr_z >7; only class with credible multi-cell evidence.
- 90d expected P&L (1% risk, $100k): +$11,400 (assume 1% risk/trade, 0.4% avg slippage, 1.44% avg win size on 208 trades).
- Gate change: SMART_PICKS_MIN_SCORE_CRYPTO = 48
- Confidence (1-5): 4

**### COMMODITY**
- Real/noise verdict: Noise. All cells have bonferroni=false and n=21; matches previously rejected COT/inventory patterns.
- 90d expected P&L (1% risk, $100k): $0 (edge is artifact).
- Gate change: SMART_PICKS_MIN_SCORE_COMMODITY = 70
- Confidence (1-5): 5

**### FUTURES / BOND / ETF / INDEX / MEME / UNKNOWN**
- Real/noise verdict: No edge. All n_closed ≤25; zero proven cells; results indistinguishable from noise.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: HC_MIN_TRUST = 75
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale CRYPTO today (only class with statistically credible, holdout-validated edges). Demote EQUITY immediately per MUTATION_THREE_AXIS_PROTOCOL.md — its “edge” is leakage and must be mutated before any further capital allocation. All other classes have no actionable edge.
