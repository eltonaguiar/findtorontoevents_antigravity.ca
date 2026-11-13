# Pick Funnel Swarm Verdict — 2026-11-13 04:07 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20261113T040724Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-day Edge Analysis

Before the per-class verdicts, three structural observations that color everything below:

1. **`passed_high_conviction = 0` across ALL 10 classes.** The HC gate (`score>=80 && conf>=0.75 && trust>=60`) is dead. Nothing in 90 days cleared it. That means the "HIGH CONVICTION" funnel is currently a null set — the dashboard is showing you Smart Picks, not HC picks. Any "HC edge" claim is untestable.
2. **`passed_proven = 0` across ALL classes.** The PROVEN gate is also dead. The `top_edges_proven` arrays are populated by the *analysis* layer, not the *gate* layer — so the gate is not actually routing on the edges the analysis found. That's a wiring bug, not an edge.
3. **`opened >> passed_smart` in every class** (e.g. CRYPTO 9,924 opened vs 3,635 passed_smart; FOREX 24,157 vs 24,771 — actually FOREX opened < passed_smart, which is the only class where the funnel is coherent). For CRYPTO/EQUITY/COMMODITY the "opened" count is ~2.7x the "passed_smart" count. **The gate is not gating.** Either `opened` is counting paper/shadow trades, or the gate is being bypassed. This is the single biggest integrity issue in the data.

---

### CRYPTO
- **Real/noise verdict:** **NOISE.** The only "best PF" cell is `trust=UNK & rr=RR1.5-2.0 & source=alpha_engine` with n=197, WR=59.4%, shrunk 58.5%, PF=2.02. That's a *plausible* cell — but: (i) `bonferroni_pass=false`, (ii) holdout PF collapses from train 2.47 → 1.32, (iii) `trust=UNK` means the trust dimension is unpopulated, so this is really just "alpha_engine RR1.5-2.0 LONG" — a single strategy family, single source, single direction. That's not an edge, that's one strategy having a good quarter. The three "top edges" are the *same cell* projected onto different dim subsets — n=197 counted three times. **No PROVEN cells exist.** The `ml` cell you flagged isn't even in the top-3 output, which means it either didn't clear n>=20 or the analysis layer suppressed it — either way, don't chase it. Class-level WR 44.8% on n=2,278 is a losing system.
- **90d expected P&L (1% risk, $100k):** **−$4,300 to −$6,800.** At 1% risk ($1,000/trade) × 2,278 decisive trades × (0.4482 − 0.50) × avg R ≈ −$5,500 central estimate. The "best cell" at n=197 would have made ~+$2,200 gross, but you can't isolate it without the gate fix, and slippage on 2,278 crypto trades at 5–10bps round-trip eats ~$1,100–2,200 of that. **Net: negative.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` — raise it. But the real fix is upstream: the `opened` (9,924) vs `passed_smart` (3,635) mismatch means the gate isn't binding. Set `SMART_PICKS_MIN_SCORE_CRYPTO = 72` (from whatever it is now) AND add a hard `if not passed_smart: skip` assertion in `production_scanner.py` before `opened` is incremented. Without that assertion, no threshold change matters.
- **Confidence (1-5):** **2.** Data integrity is broken; the one plausible cell is unproven and un-isolable.

---

### EQUITY
- **Real/noise verdict:** **LEAKAGE — do not trade.** The `rr=RR>=2.0 & fam=mean_reversion` cell shows n=37, WR=97.3%, PF=131.6, holdout PF=99.0. **PF=131 is not a real edge; it is a data artifact.** A PF of 131 means average win / average loss ≈ 131:1 — that happens when (a) losers are being truncated to near-zero (stop-loss not recorded, or P&L capped), (b) winners are being marked at a stale/optimistic price, or (c) the "loss" bucket is mislabeled. The holdout PF=99.0 on n=21 is the tell: 21 holdout trades with essentially zero losses is not a strategy, it's a bookkeeping error. **This is exactly the pattern H-001 (COT look-ahead) and H-009/H-011 (options) showed before they were killed.** Flag as leakage recurrence. Class WR 72.4% on n=105 is also suspiciously high for equity mean-reversion — real equity MR sits at 55–62%.
- **90d expected P&L (1% risk, $100k):** **$0 — do not deploy.** If you *did* deploy at face value: 105 trades × $1,000 × (0.7238 − 0.50) × avg R ≈ +$23,500. **That number is fake.** The PF=131 cell alone would imply ~$58k on 37 trades, which is physically impossible at 1% risk. The honest answer is: **unknown until the P&L accounting is audited.** Do not size on this.
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` is irrelevant until the P&L bug is fixed. The gate change is in the *accounting*: add a `MAX_PF_SANITY = 10.0` assertion in the edge-analysis layer that quarantines any cell with PF > 10 for manual review before it can be promoted to PROVEN. In `quality_gates.py`, add `EQUITY_MAX_PF_QUARANTINE = 10.0`.
- **Confidence (1-5):** **1.** This is the most dangerous class in the dataset because the headline WR looks great and the PF is impossible.

---

### COMMODITY
- **Real/noise verdict:** **NOISE.** Best cell `trust=UNK & dir=LONG & source=alpha_engine`: n=28, WR=64.3%, shrunk 58.3%, PF=2.14 — but **holdout PF=1.14 on n=13, holdout_pass=false, bonferroni_pass=false.** Train PF 4.02 → holdout 1.14 is a textbook overfit. The other two cells are the same trades re-projected. Class WR 70.3% on n=37 is a tiny sample; n=37 is below the n>=20 threshold for *one* cell, let alone a class verdict. **No PROVEN cells.** Also note H-001 and H-036 both killed COMMODITY signals — this class has a history of leakage and harness rejection. Treat any positive COMMODITY cell as suspect by default.
- **90d expected P&L (1% risk, $100k):** **+$1,500 to +$2,800** at face value (37 trades × $1,000 × 0.2027 × avg R ≈ +$2,100), but **holdout says ~$0.** Honest estimate: **$0 to +$1,000**, and only if the holdout degradation is regime, not overfit. Given H-001/H-036 history, assume $0.
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` — but the real issue is `passed_smart=3,664` out of `scanned=5,779` (63% pass rate) while `opened=5,742` (99% of scanned). The gate is passing almost everything and then opening almost everything. Set `SMART_PICKS_MIN_SCORE_COMMODITY` up by ~10 points and add a `COMMODITY_MIN_HOLDOUT_PF = 1.3` requirement before any cell is promoted.
- **Confidence (1-5):** **2.** Small n, failed holdout, class has a leakage history.

---

### FOREX
- **Real/noise verdict:** **SUSPICIOUS — likely leakage or single-source concentration.** The `trust=UNK & conf=C>=0.90 & fam=regime` cell: n=38, WR=89.5%, shrunk 75.9%, PF=14.4, holdout PF=99.0 on n=10, **bonferroni_pass=true**. This is the only cell in the entire dataset that passes Bonferroni. That should make you *more* suspicious, not less. PF=14.4 with holdout PF=99.0 on n=10 means the holdout had zero losses — same artifact pattern as EQUITY. `source=regime_terminal` is a single source; `fam=regime` is a single family. n=38 with 34 wins is a 4-loss sample. **This is almost certainly a single-symbol or single-regime concentration** (e.g. one FX pair in a trending window, or a terminal-state strategy that only fires in one macro regime). The `consensus` cell you flagged isn't in the output — but the `regime_terminal` cell is the same shape. **Do not promote.** Class WR 51.9% on n=432 is a coin flip; the "edge" is 38 trades out of 432.
- **90d expected P&L (1% risk, $100k):** **+$400 to +$900** at class level (432 trades × $1,000 × 0.0185 × avg R ≈ +$650). The "proven" cell at face value would be ~+$2,600 on 38 trades, but holdout PF=99 is not real. **Honest: ~+$500, and that's within noise of zero.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` — but the binding issue is `passed_smart=24,771` out of `scanned=25,438` (97.4% pass rate). The FOREX gate is a rubber stamp. Set `SMART_PICKS_MIN_SCORE_FOREX` up by 15+ points, and add `FOREX_MAX_SINGLE_SOURCE_SHARE = 0.40` so no single source (e.g. `regime_terminal`) can dominate a cell.
- **Confidence (1-5):** **2.** Bonferroni pass is real but the PF=14/holdout=99 pattern is the same artifact as EQUITY.

---

### ETF
- **Real/noise verdict:** **NO EDGE.** n=10 closed, WR=10%, PF not shown (no cells). This is a 1-win, 9-loss sample. There is nothing to analyze. The class should not be in the funnel at all — 319 scanned, 278 passed_smart (87% pass rate), 309 opened, 10 closed. The gate is passing everything and the outcomes are terrible.
- **90d expected P&L (1% risk, $100k):** **−$800 to −$1,200** (10 trades × $1,000 × (0.10 − 0.50) × avg R ≈ −$1,000). Small dollar amount, but the *rate* is catastrophic.
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` — raise aggressively, or better, **set `ETF_ENABLED = False`** in `quality_gates.py` until n>=50 closed trades exist. A 10% WR on n=10 is not a strategy, it's a bug.
- **Confidence (1-5):** **4** (high confidence there is no edge — the sample is small but the direction is unambiguous).

---

### FUTURES
- **Real/noise verdict:** **NO EDGE.** n=16 closed, WR=37.5%, no cells. H-005 already killed futures momentum (inversion doesn't fix it). 174 scanned, 125 passed_smart (72%), 158 opened, 16 closed. Same pattern: gate passes, outcomes lose.
- **90d expected P&L (1% risk, $100k):** **−$2,000** (16 trades × $1,000 × (0.375 − 0.50) × avg R ≈ −$2,000). Small n, but negative.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` — raise, or `FUTURES_ENABLED = False` until n>=50. Given H-005, the burden of proof is high.
- **Confidence (1-5):** **3.** Small n but consistent with prior kill.

---

### MEME
- **Real/noise verdict:** **NO EDGE.** n=7 closed, WR=42.9%, no cells. 22 scanned, 10 passed_smart, 15 opened, 7 closed. This is a toy sample. Do not draw conclusions; do not trade.
- **90d expected P&L (1% risk, $100k):** **−$500** (7 trades × $1,000 × (0.4286 − 0.50) × avg R ≈ −$500). Noise.
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME` — raise, or `MEME_ENABLED = False`. n=7 is not a class.
- **Confidence (1-5):** **3.** Too small to be sure, but no evidence of edge.

---

### BOND
- **Real/noise verdict:** **NO EDGE.** n=31 closed, WR=38.7%, no cells. 1,158 scanned, 1 passed_smart (0.09% pass rate — the gate is *too tight* here, opposite of every other class), 1,127 opened, 31 closed. The gate passes 1 pick but opens 1,127 — **the gate is being bypassed entirely for BOND.** That's a wiring bug, not a strategy.
- **90d expected P&L (1% risk, $100k):** **−$3,500** (31 trades × $1,000 × (0.3871 − 0.50) × avg R ≈ −$3,500). Negative.
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` — but the real fix is the bypass: `if not passed_smart: skip` assertion in `production_scanner.py`. The gate value is irrelevant if it's not enforced.
- **Confidence (1-5):** **3.** Negative WR is clear; the bypass bug is the headline.

---

### INDEX
- **Real/noise verdict:** **NO EDGE — n=1.** 2,075 scanned, 1,578 passed_smart (76%), 2,074 opened, 1 closed (a win). This is not a class; it's a single trade. The 100% WR is meaningless.
- **90d expected P&L (1% risk, $100k):** **$0** (n=1, no statistical basis). If you must: +$1,000 on one trade, which is noise.
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` — raise, or `INDEX_ENABLED = False` until n>=30. 76% pass rate on 2,075 scans with 1 close is a data pipeline problem, not a gate problem.
- **Confidence (1-5):** **4** (high confidence there is no edge — n=1 is not an edge).

---

### UNKNOWN
- **Real/noise verdict:** **NO EDGE — and a data-quality red flag.** n=3 closed, WR=0%, 1,308 scanned, 120 passed_smart, 1,305 opened, 3 closed. "UNKNOWN" as an asset class means the classifier is failing on 1,308 scans. That's a pipeline bug, not a strategy. Do not trade; fix the classifier.
- **90d expected P&L (1% risk, $100k):** **−$3,000** (3 trades × $1,000 × (0 − 0.50) × avg R ≈ −$1,500 to −$3,000). Noise.
- **Gate change:** `SMART_PICKS_MIN_SCORE_UNKNOWN` — irrelevant. The fix is upstream: `ASSET_CLASS_FALLBACK = "REJECT"` in the classifier, so unclassified scans are dropped rather than opened.
- **Confidence (1-5):** **4** (high confidence there is no edge — it's a classifier bug).

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY with real money: NONE.** Not one class has a cell that survives scrutiny. The only Bonferroni-passing cell (FOREX `regime_terminal`) has the same PF=14/holdout=99 artifact as the EQUITY leakage cell. The only plausible non-artifact cell (CRYPTO `alpha_engine` RR1.5-2.0) fails Bonferroni and collapses on holdout. **If forced to pick one to paper-trade for 30 days before real money: CRYPTO `alpha_engine` RR1.5-2.0 LONG, sized at 0.25% risk, with a hard kill if holdout PF < 1.2.** That is a *research* allocation, not a scale-up.

**DEMOTE per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` (mutate before kill):**

1. **EQUITY — demote to quarantine immediately.** The PF=131 cell is a leakage recurrence (same shape as H-001/H-009/H-011). Mutate axis: **P&L accounting** — audit how losses are recorded

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### CRYPTO
- Real/noise verdict: All best_pf cells are noise; n=197 is decent but bonferroni fails, holdout PF drops sharply to 1.316, and no proven cells exist. No leakage flags but nothing stable.
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge; any live use would likely lose after slippage).
- Gate change: SMART_PICKS_MIN_SCORE_CRYPTO = 72
- Confidence (1-5): 4

### EQUITY
- Real/noise verdict: Proven cells are almost certainly leakage or single-symbol concentration; PF=131 and WR_shrunk=80.7 on n=37 with tiny train_n=16 is statistically impossible in real equity data without look-ahead or cherry-picking.
- 90d expected P&L (1% risk, $100k): -$1,800 (expect reversal to ~45% WR once leakage removed).
- Gate change: hc_filter.js MIN_TRUST = 65
- Confidence (1-5): 5

### COMMODITY
- Real/noise verdict: No proven cells; best_pf cells fail holdout and bonferroni. Matches known rejected COT/inventory hypotheses patterns.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_COMMODITY = 80
- Confidence (1-5): 4

### FOREX
- Real/noise verdict: Proven cells (n=38) show extreme PF=14.4 and holdout PF=99 on n=10; this is classic small-sample overfitting or regime_terminal leakage, not real.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: hc_filter.js MIN_CONF = 0.92
- Confidence (1-5): 5

### ETF
- Real/noise verdict: n_closed=10 is too small; no proven or usable edges.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_ETF = 85
- Confidence (1-5): 3

### UNKNOWN
- Real/noise verdict: n_closed=3; pure noise, no edges.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_UNKNOWN = 90
- Confidence (1-5): 3

### BOND
- Real/noise verdict: n_closed=31; no proven cells, all noise.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_BOND = 75
- Confidence (1-5): 3

### INDEX
- Real/noise verdict: n_closed=1; no edge possible.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_INDEX = 90
- Confidence (1-5): 3

### FUTURES
- Real/noise verdict: n_closed=16; no proven cells, noise only.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_FUTURES = 80
- Confidence (1-5): 3

### MEME
- Real/noise verdict: n_closed=7; no usable edge.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_MEME = 85
- Confidence (1-5): 3

**SYSTEM-WIDE CONCLUSION**  
Scale up nothing today — every class either has zero proven edge or proven cells that are statistically invalid. DEMOTE CRYPTO and FOREX first per MUTATION_THREE_AXIS_PROTOCOL.md (they generate the highest volume of false positives and would cost the most in live slippage).
