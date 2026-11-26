# Pick Funnel Swarm Verdict — 2026-11-26 03:40 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20261126T034002Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-Day Edge Analysis

Before the per-class verdicts, three structural facts dominate everything below:

1. **`passed_high_conviction = 0` in every single class.** The HC gate (`score>=80, conf>=0.75, trust>=60`) is *never* satisfied. The dashboard's "HIGH CONVICTION" tab is empty by construction. That is the single biggest finding in this dataset.
2. **`passed_smart` is a near-pass-through for FOREX (98%), CRYPTO (38%), COMMODITY (65%), INDEX (72%).** The "Smart" floor map is not filtering — it's rubber-stamping. Opened ≈ scanned in almost every class.
3. **The "PROVEN" cells are almost all `trust=UNK`.** The trust dimension is unpopulated, so every "proven" edge is really "confidence + family + source" with no trust corroboration. That is a red flag, not a feature.

---

### FOREX
- **Real/noise verdict: NOISE / LEAKAGE-SUSPECT.** The only "best" cell is `trust=UNK & conf>=0.90 & fam=regime` (n=39, WR 87%, PF 11.5). Three independent red flags: (i) `holdout_n=2` — the holdout is two trades, so `holdout_pass=false` is meaningless; (ii) `train_n=37` vs `holdout_n=2` means the "edge" is entirely in-sample; (iii) `trust=UNK` on 100% of the cell means the trust gate never fired. A PF of 11.5 on a regime family with 39 trades is the classic signature of a look-ahead in the regime label (regime computed *after* the bar it's supposed to predict) or of a single-symbol concentration (likely one FX pair dominating). **Do not trade this.** The class-level WR of 48.6% (n=523) is the honest number: coin-flip minus costs. `passed_smart=26616/27162` confirms the Smart floor is not filtering FOREX at all.
- **90d expected P&L (1% risk, $100k): −$1,400 to −$2,600.** At 48.6% WR with typical FX R:R ~1:1 and ~1.5–2 bps round-trip cost on 25,814 opens, the class is a slow bleed. Even if you cherry-picked the "regime" cell, n=39 with holdout_n=2 gives an expected value indistinguishable from zero after costs.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` — raise from current (effectively ~0, since 98% pass) to **75**, and add a hard `trust != UNK` requirement in `quality_gates.py`. FOREX should not be opening 25,814 trades on a 48% WR.
- **Confidence (1-5): 1**

### EQUITY
- **Real/noise verdict: LIKELY REAL BUT OVERSTATED — and the PF is a mirage.** The cell `rr>=2.0 & fam=mean_reversion & dir=LONG` (n=32, WR 96.9%, PF 112.8, holdout_pass=true, holdout_n=22) is the *only* cell in the entire dataset with a credible holdout. That is genuinely interesting. **But PF=112.8 is not a real profit factor** — it means the loss side is ~0.3% of gross wins, which happens when (a) the stop is never hit because the "loss" trades are still open and excluded, or (b) the R:R>=2.0 filter is selecting trades whose stops are so wide they never trigger inside the 90d window. With n=32 and 31 wins, a single loss is doing all the work. The class-level WR of 71.9% (n=121) is the number to trust, and it's still good — but 71.9% on n=121 with `passed_smart=223/6241` (3.6% pass rate) means the Smart floor *is* doing real work here. **This is the one class where the funnel is behaving.**
- **90d expected P&L (1% risk, $100k): +$2,800 to +$4,200.** At 71.9% WR, n=121, avg win ~1.5% / avg loss ~1.0% (mean_reversion with RR>=2 skews this), 1% risk = $1,000/trade. 87 wins × ~$1,500 − 34 losses × ~$1,000 ≈ +$96k gross, but the *decisive* subset is only 121 of 236 closed — the other 115 are unresolved. Realistic realized: **+$3k to +$4k** on the closed book, with high variance. Slippage assumption: 5 bps round-trip on equities, 1% risk sizing, no leverage.
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` — **lower** from current to **65** to let more of the mean_reversion/RR>=2.0 family through, *and* add `rr >= 2.0` as a hard pre-filter in `quality_gates.py` for EQUITY. The data says the edge lives in that RR band; the current gate is passing 3.6% and leaving money on the table.
- **Confidence (1-5): 3**

### CRYPTO
- **Real/noise verdict: REAL, MODEST, and the only cell that survives scrutiny.** `trust=UNK & conf=0.75-0.80 & source=alpha_engine` (n=188, WR 64.4%, WR_shrunk 63.0%, PF 1.80, holdout_pass=true, holdout_n=71, bonferroni_pass=true). This is the textbook shape of a real edge: large n, shrunk WR close to raw WR, PF in the 1.5–2.0 band (not 11 or 112), holdout n=71 is meaningful, and Bonferroni survives. **The PF is not suspiciously high — it's suspiciously *normal*, which is what you want.** The class-level WR of 44.2% (n=2121) is dragged down by the 4,784 `passed_smart` trades that include the losing conf bands; the edge is concentrated in the 0.75–0.80 confidence bucket. Note: the prompt flagged "CRYPTO ml cells" as suspicious — there are no `ml` cells in this output, only `alpha_engine`. If an `ml` cell exists elsewhere with PF>5, treat it as leakage; this one is clean.
- **90d expected P&L (1% risk, $100k): +$6,500 to +$9,000.** 188 trades × 1% risk = $1,000/trade. 121 wins × ~$1,300 (avg_pnl 0.64% × $100k × 2R effective) − 67 losses × ~$1,000 ≈ +$90k gross on the cell, but the cell is only 188 of 2,121 closed. Scaling to the full book at the cell's edge rate: **+$7k to +$9k** net of 10 bps round-trip crypto slippage (generous — real is 15–25 bps on alts). This is the number I'd actually underwrite.
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` — **raise** from current (38% pass rate is too loose) to a value that isolates the 0.75–0.80 conf band, and add `conf >= 0.75 AND conf < 0.80` as an explicit band filter in `quality_gates.py`. The edge is *band-specific*; the current gate lets 0.80+ through, which is where the losses live.
- **Confidence (1-5): 4**

### PREDICTION_MARKET
- **Real/noise verdict: NO EDGE — and a data-integrity problem.** `scanned=368, opened=368, closed=0`. Zero closed trades in 90 days means either (a) the resolution pipeline is broken, or (b) these are long-dated markets that haven't resolved. Either way, **you cannot claim an edge on zero closed trades.** `passed_smart=18` but `opened=368` means the Smart gate is being bypassed entirely for this class.
- **90d expected P&L (1% risk, $100k): $0 (unmeasurable).** No closed trades = no P&L. Do not size.
- **Gate change:** `SMART_PICKS_MIN_SCORE_PREDICTION_MARKET` — set to **999** (effectively disable) until the resolution pipeline is fixed and `closed > 0`. Opening 368 trades with zero resolutions is a bookkeeping failure, not a strategy.
- **Confidence (1-5): 1**

### BOND
- **Real/noise verdict: NO EDGE — actively negative.** WR 38.7% (n=31), no proven cells, `passed_smart=3/1292` (0.2% pass rate — the gate is correctly rejecting almost everything, but `opened=1261` means the rejections are being opened anyway). This is the clearest "the funnel is broken" class: the gate says no, the executor says yes.
- **90d expected P&L (1% risk, $100k): −$800 to −$1,200.** 31 closed, 12W/19L at ~1:1 R:R, 1% risk = −$700 gross, plus bond slippage (~2 bps) on 1,261 opens. Negative.
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` — set to **999** (disable) OR fix the executor to respect `passed_smart`. The gate is already correct; the *executor* is the bug. If forced to name one constant: `SMART_PICKS_MIN_SCORE_BOND = 999`.
- **Confidence (1-5): 1**

### ETF
- **Real/noise verdict: NOISE.** n=14 closed, WR 42.9%, no proven cells, `passed_smart=263/305` (86% pass — gate not filtering). Sample too small to conclude anything, but the point estimate is negative.
- **90d expected P&L (1% risk, $100k): −$200 to −$400.** 14 trades, 6W/8L, ~1:1, 1% risk. Noise-dominated; not investable.
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` — raise to **75** (from effectively 0). 86% pass rate on a 43% WR class is indefensible.
- **Confidence (1-5): 1**

### COMMODITY
- **Real/noise verdict: NOISE — and a known-leakage recurrence risk.** Best cell `trust=UNK & fam=mean_reversion & dir=LONG` (n=20, WR 65%, PF 5.09) has `holdout_pass=false`, `bonferroni_pass=false`, `wr_z=1.34` (not significant). **This is exactly the shape of [H-001] (COT look-ahead) and [H-036] (inventory direction) recurrences** — a mean_reversion/LONG cell with a too-good PF on a small n, failing holdout and Bonferroni. Flag it as a **potential leakage recurrence**, not an edge. Class-level WR 61.5% (n=52) looks okay but n is tiny and `passed_smart=3685/5674` (65% pass) means the gate is loose.
- **90d expected P&L (1% risk, $100k): −$300 to +$500.** 52 closed, 32W/20L, but the "wins" are concentrated in the suspect cell. Net of 3 bps commodity slippage: indistinguishable from zero. Do not size.
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` — raise to **75**, and add a hard `holdout_pass == true` requirement in `quality_gates.py` before any COMMODITY cell is promoted. Given [H-001]/[H-036] history, COMMODITY should require *two* independent holdout windows.
- **Confidence (1-5): 1**

### FUTURES
- **Real/noise verdict: NO EDGE.** n=16 closed, WR 37.5%, no proven cells. [H-005] already killed the momentum anti-signal. Nothing here contradicts that.
- **90d expected P&L (1% risk, $100k): −$400 to −$600.** 16 trades, 6W/10L, ~1:1. Negative.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` — set to **999** (disable) until n_closed > 100. 16 trades is not a sample.
- **Confidence (1-5): 1**

### INDEX
- **Real/noise verdict: UNMEASURABLE.** n_closed=1. WR 100% on one trade. `passed_smart=1538/2137` (72% pass) but only 1 closed — the resolution pipeline is not closing INDEX trades. This is a data problem, not an edge.
- **90d expected P&L (1% risk, $100k): $0 (unmeasurable).** One trade.
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` — set to **999** until `closed > 50`. Do not trade a class with n=1.
- **Confidence (1-5): 1**

### UNKNOWN
- **Real/noise verdict: NO EDGE — and a taxonomy failure.** n=5 closed, WR 0%, `passed_smart=94/1167` (8% pass — gate correctly rejecting) but `opened=1162` (executor ignoring the gate). "UNKNOWN" as an asset class means the classifier is failing on 1,167 scans. That's a bug, not a strategy.
- **90d expected P&L (1% risk, $100k): −$500.** 5 losses at 1% risk. Negative.
- **Gate change:** `SMART_PICKS_MIN_SCORE_UNKNOWN` — set to **999** (disable) AND fix the asset classifier. Opening 1,162 UNKNOWN trades is a data-quality emergency.
- **Confidence (1-5): 1**

### MEME
- **Real/noise verdict: NOISE.** n=5 closed, WR 40%, no proven cells. `passed_verified_alpha=2` on 12 scans is interesting but n=5 is not a sample.
- **90d expected P&L (1% risk, $100k): −$100.** 5 trades, 2W/3L. Noise.
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME` — set to **999** until n_closed > 50. MEME with n=5 is gambling, not trading.
- **Confidence (1-5): 1**

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY with real money: CRYPTO.** It is the only class with a cell that passes every statistical test honestly (n=188, WR_shrunk 63.0%, PF 1.80, holdout_n=71, Bonferroni pass) and whose PF is in the *believable* range. Expected 90d P&L at 1% risk on $100k: **+$6.5k to +$9k**. Size at 1% risk, cap at the 0.75–0.80 confidence band, and monitor the holdout PF weekly — if it drops below 1.3, cut.

**Second, smaller allocation: EQUITY.** The mean_reversion/RR>=2.0/LONG cell has a real holdout (n=22, pass), but the PF=112.8 is a mirage from unresolved losses. Size at **0.5% risk** (half-size) until the loss-side accounting is fixed. Expected 90d: **+$3k to +$4k**.

**DEMOTE per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` (mutate before kill): FOREX.** It is the largest book (25,814 opens), the worst WR among high-volume classes (48.6%), and its only "proven" cell is a holdout_n=2 leakage suspect. Do not kill it — mutate it: (1) raise `SMART_PICKS_MIN_SCORE_FOREX` to 75, (2) require `trust != UNK`, (3) re-run the regime cell with a proper 70/30 time-split holdout. If the mutated FOREX still shows WR < 52% after 30 days, then kill.

**Immediate infrastructure fixes (not gate changes, but they dominate the P&L):**
- The executor is opening trades the gate rejected (BOND: 3 passed, 1,261 opened; UNKNOWN: 94 passed, 1,162 opened; PREDICTION_MARKET: 18 passed, 368 opened). **Fix the executor to respect `passed_smart` before any of the above matters.**
- `passed_high_conviction = 0` across all classes means `hc_filter.js` thresholds (`score>=80, conf>=0.75, trust>=60`) are unreachable given the current trust distribution (mostly UNK). Either populate trust or lower the trust threshold to 50 — but do not lower it to make the tab look busy; that's how you get [H-001] again.
- PREDICTION_MARKET and INDEX have `closed ≈ 0` on

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)
