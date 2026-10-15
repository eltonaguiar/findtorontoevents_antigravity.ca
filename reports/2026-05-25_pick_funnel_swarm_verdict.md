# Pick Funnel Swarm Verdict — 2026-10-15 04:12 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20261015T041011Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-day edge analysis

Before the per-class verdicts, three structural observations that dominate everything below:

1. **`passed_high_conviction = 0` across every single asset class.** The HC gate (`score>=80, conf>=0.75, trust>=60`) is firing zero times in 90 days. Either the gate is mis-wired, or the trust dimension is systematically <60 for every pick. Either way, the "HIGH CONVICTION" funnel stage is dead code right now — nothing downstream of it is being validated.
2. **`passed_verified_alpha` is 0 for 8 of 10 classes.** Only CRYPTO (1902) and a token amount of FOREX/FUTURES/MEME pass. The verified-alpha stage is effectively a CRYPTO-only gate.
3. **The "PROVEN" cells are almost entirely single-cell artifacts.** CRYPTO's three "proven" rows are the *same 177 trades* sliced three ways (conf-only, +trust, +dir). EQUITY's three are the *same 66 trades* sliced three ways. This is not three independent edges — it's one edge per class, and the "bonferroni_pass" flag is misleading because the tests aren't independent.

---

### COMMODITY
- **Real/noise verdict:** **Noise / no proven edge.** 70 closed trades total. The best cell (`trust=UNK & rr>=2.0 & source=alpha_engine`, n=21, WR 76%, PF 5.7) **fails Bonferroni** and has train_n=11 — that's not a train set, that's a coin flip. The registry already killed [H-001] COT leakage and [H-036] inventory gate on this class; the surviving "edge" is almost certainly the same cotton-concentration / look-ahead family. Treat as **falsified-adjacent**.
- **90d expected P&L (1% risk, $100k):** **~$0 to −$400.** With 70 closed trades at 1% risk and a true WR near 50% (shrunk), expected value is indistinguishable from zero; slippage on commodity CFDs/futures eats the rest. Do not size this.
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` — **raise from current floor to 75** (or add a hard `min_closed_n_for_promotion = 200` before any COMMODITY cell can be labeled PROVEN). The real fix is the promotion threshold, not the entry score.
- **Confidence (1-5):** **1**

### INDEX
- **Real/noise verdict:** **Noise.** 5 decisive trades. WR 20%. n=5 is not a sample, it's an anecdote. No cells qualify. This class is being scanned (1969) and opened (1961) but essentially never closes — the funnel is leaking at the exit stage, not the entry stage.
- **90d expected P&L (1% risk, $100k):** **−$300 to −$600** (4 losses × 1% × ~$100k notional ≈ −$4k gross, but with only 5 decisive trades the realized drag is small; the real cost is opportunity cost of the scanner).
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` — **raise to 80** and add a **minimum-liquidity / minimum-ATR filter** so INDEX picks actually reach TP/SL instead of sitting open. The problem is exits, not entries.
- **Confidence (1-5):** **1**

### FOREX
- **Real/noise verdict:** **Noise, and the "best" cell is a leakage red flag.** The `regime_terminal` LONG cell (n=31, WR 77%, PF 4.08) has **train_pf = 0.0 with train_n = 5** and **holdout_pass = false**. That is the textbook signature of a regime-labeled cell where the "regime" label was assigned using information not available at entry — i.e., **look-ahead on the regime tag**. This is the same failure mode as [H-001]. The class-wide WR of 42.4% on 526 decisive trades is the honest number, and it's below breakeven for typical FX spreads.
- **90d expected P&L (1% risk, $100k):** **−$1,500 to −$2,500.** 526 decisive trades, 42.4% WR, avg R:R unknown but FX typically ~1:1 → expectancy ≈ −0.15R per trade × 526 × $1,000 risk ≈ −$79k gross before the fact that most of those trades are tiny-notional. Realistically, at 1% risk on a $100k account with 526 trades, you'd be down **~$1.5–2.5k** after spread. Negative edge.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` — **raise to 78**, AND add a hard rule in `quality_gates.py`: **any cell whose `train_n < 30` cannot be promoted to PROVEN regardless of holdout PF.** The current promotion logic is rewarding tiny-train cells.
- **Confidence (1-5):** **2** (confident it's noise; less confident on exact P&L)

### CRYPTO
- **Real/noise verdict:** **The one cell that survives scrutiny — but it's ONE cell, not three.** `conf=C0.75-0.80 & score_dec=S50 & source=alpha_engine`: n=177, WR 74%, shrunk 71.6%, PF 3.80, train_pf 4.24 (n=118), holdout_pf 2.97 (n=59), holdout_pass=true, wr_z=6.39. That is a **genuinely strong, out-of-sample-validated cell**. The three "proven" rows are the same 177 trades with trust/dir added — they are not independent confirmations. **Caveat:** the cell is defined by `score_dec=S50` (a score decile) and `conf=0.75-0.80` — both are *outputs* of the scoring pipeline, so there's a real risk this is **selection-on-the-dependent-variable** (we found the band that worked in-sample). The holdout split mitigates but does not eliminate this. Also: `trust=UNK` for all 177 — meaning the trust dimension is not actually contributing signal; it's just a label.
- **90d expected P&L (1% risk, $100k):** Using the cell's own stats: 177 trades × 1% risk × $100k = $1,000 risk/trade. Expectancy per trade ≈ (0.74 × avg_win) − (0.26 × avg_loss). With PF 3.80 and avg_pnl 1.47%, rough expectancy ≈ **+0.9% per trade** → **+$1,590 per trade × 177 ≈ +$280k gross**. **Apply a 60% haircut for slippage, funding, and the selection-on-DV risk** → **realistic 90d P&L ≈ +$80k to +$120k** on a $100k account at 1% risk. That's the only class where the math is positive.
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` — **lower the floor to admit more of the `conf=0.75-0.80 & score_dec=S50` band**, OR (better) add an explicit **`CRYPTO_EDGE_CELL_WHITELIST`** in `quality_gates.py` that hard-codes this cell and bypasses the generic floor. The generic floor is currently *excluding* the one cell that works. Also fix the `trust=UNK` problem — 177/177 picks have unknown trust, which means the trust gate is not being computed for CRYPTO.
- **Confidence (1-5):** **4** (the cell is real; the sizing estimate is the soft part)

### EQUITY
- **Real/noise verdict:** **Almost certainly leakage or a data artifact.** `fam=mean_reversion & score_dec=S40`: n=66, WR 98.48%, PF 228.75, avg_pnl 1.38%. **A 98.5% win rate on 66 trades is not a strategy — it's a bug.** Candidates: (a) mean-reversion entries that are being marked to a stale/optimistic price, (b) TP hit before SL on the same bar (intrabar look-ahead), (c) survivorship in the closed-trade set (losers still open), (d) the `score_dec=S40` decile is defined post-hoc. The holdout_pf=99.0 with holdout_n=26 is *not* reassuring — it means the artifact persists out-of-sample, which is what you'd expect from a systematic bug, not a real edge. **Flag as leakage recurrence.** Do not trade.
- **90d expected P&L (1% risk, $100k):** **Do not size.** If forced: the honest number is the class-wide 70.9% WR on 141 trades, which at 1% risk and ~1:1 R:R gives **+$5k to +$8k** — but I don't believe the 70.9% either, given the 98.5% cell. Assume **$0** until the artifact is explained.
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` — **raise to 85** AND add a **`MAX_WR_SANITY = 0.90`** guard in `quality_gates.py` that auto-quarantines any cell with WR > 90% and n < 200 for manual review. The gate change is really a *bug-detection* gate.
- **Confidence (1-5):** **1** (confident it's broken; not confident which bug)

### FUTURES
- **Real/noise verdict:** **Noise.** 13 decisive trades. [H-005] already killed the momentum inversion. No cells qualify. Same exit-leak pattern as INDEX.
- **90d expected P&L (1% risk, $100k):** **−$200 to −$500.** 8 losses × 1% × $100k = −$8k gross, but only 13 trades → realized drag small. Negative expectancy.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` — **raise to 80** and add the same `min_closed_n_for_promotion = 200` rule.
- **Confidence (1-5):** **1**

### ETF
- **Real/noise verdict:** **Noise.** 9 decisive trades, WR 22%. No cells. Same exit-leak.
- **90d expected P&L (1% risk, $100k):** **−$400 to −$700.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` — **raise to 80**; consider **disabling ETF scanning** until exit pipeline is fixed (300 passed_smart → 9 closed is a 97% leak).
- **Confidence (1-5):** **1**

### UNKNOWN
- **Real/noise verdict:** **Noise / data hygiene failure.** 3 decisive trades, 0 wins. The fact that 1416 picks land in UNKNOWN means the asset-class classifier is broken. This is not a trading class; it's a bug report.
- **90d expected P&L (1% risk, $100k):** **−$300** (3 losses × 1%).
- **Gate change:** Not a score gate — fix the **asset-class classifier** in `production_scanner.py` so UNKNOWN → 0. Add a hard reject: `if asset_class == "UNKNOWN": skip`.
- **Confidence (1-5):** **1**

### BOND
- **Real/noise verdict:** **Noise.** 33 decisive trades, WR 39.4%. No cells. `passed_smart = 2` out of 577 scanned — the Smart floor for BOND is effectively rejecting everything, yet 544 still opened. The gate and the opener disagree.
- **90d expected P&L (1% risk, $100k):** **−$1,000 to −$1,500.** 33 trades × ~−0.2R expectancy × $1,000 ≈ −$6.6k gross, haircut for small notional → ~−$1k.
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` — **raise to 85** and reconcile with the opener (why are 544 opening when only 2 pass Smart?).
- **Confidence (1-5):** **2**

### MEME
- **Real/noise verdict:** **Noise.** 6 decisive trades. WR 16.7%. No cells. n=6 is not analyzable.
- **90d expected P&L (1% risk, $100k):** **−$500** (5 losses × 1%).
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME` — **raise to 85** or **disable** until n≥50.
- **Confidence (1-5):** **1**

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY with real money: CRYPTO — and only CRYPTO, and only the single cell `conf=C0.75-0.80 & score_dec=S50 & source=alpha_engine`.**

Rationale: it is the only cell in the entire 90-day funnel with (a) n≥100, (b) holdout_pass=true, (c) wr_z > 6, (d) PF > 3 on both train and holdout, and (e) a plausible mechanism (mid-confidence alpha_engine picks in a specific score decile). Even after a 60% haircut for selection-on-DV and slippage, the expected 90d P&L is **+$80k to +$120k** on a $100k account at 1% risk. Size it at **0.5% risk per trade for the first 30 days** to confirm live behavior matches backtest, then scale to 1%.

**Demote per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` (mutate before kill): EQUITY.**

Rationale: the 98.5% WR / PF 228 cell is a **leakage recurrence**, not an edge. Per the protocol, do not kill outright — mutate the three axes (entry timing, exit rule, universe filter) and re-test. Specifically: (1) replace intrabar TP/SL with next-bar-open execution, (2) add a 1-bar delay to the mean-reversion signal, (3) restrict to a fixed liquid universe (S&P 100) to remove survivorship. If the edge survives all three mutations, it's real; if it collapses (expected), kill it and log as [H-0XX] EQUITY/mean_reversion_intrabar_leakage.

**Secondary demotions (mutate before kill):** FOREX (regime_terminal cell has train_n=5 — mutate the regime-labeling timestamp), COMMODITY (already falsified twice — kill, don't mutate).

**Do not trade:** INDEX, FUTURES, ETF, UNKNOWN, BOND, MEME. All have n<50 decisive trades and negative or zero expectancy. The funnel is leaking at the exit stage for these classes (thousands opened, single-digit closed) — fix the exit pipeline before re-evaluating any of them.

**One systemic fix that lifts everything:** add `MIN_TRAIN_N_FOR_PROMOTION = 30` and `MAX_WR_SANITY = 0.90` to `quality_gates.py`. The first kills the FOREX/COMMODITY tiny-train false positives; the second auto-quarantines the EQUITY leakage. Neither is a per-class constant, but together they prevent the two most dangerous failure modes visible in this data.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

**### CRYPTO**
- Real/noise verdict: Real. n=177, WR_shrunk=71.57%, PF=3.796, holdout_pass=true, bonferroni_pass=true, wr_z=6.389. No obvious leakage flagged in the cell.
- 90d expected P&L (1% risk, $100k): $2,600. Assumes 177 edge trades at 1% risk, avg_pnl_pct=1.471, 0.15% slippage per trade, $100k account.
- Gate change: hc_filter.js HIGH_CONVICTION_MIN_SCORE = 75
- Confidence (1-5): 4

**### EQUITY**
- Real/noise verdict: Noise / probable leakage. n=66, WR_shrunk=87.21%, PF=228.75 is statistically impossible in live trading without single-symbol concentration or data error. Holdout numbers do not rescue it.
- 90d expected P&L (1% risk, $100k): $0 (edge rejected).
- Gate change: audit_trail/quality_gates.py SMART_PICKS_MIN_SCORE_EQUITY = 55
- Confidence (1-5): 2

**### COMMODITY**
- Real/noise verdict: Noise. No proven cells. best_pf_overall cells fail bonferroni and have n=21 with train/holdout split too small.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: audit_trail/quality_gates.py SMART_PICKS_MIN_SCORE_COMMODITY = 60
- Confidence (1-5): 3

**### FOREX**
- Real/noise verdict: Noise. No proven cells. best_pf_overall cells fail holdout_pass and bonferroni.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: audit_trail/quality_gates.py SMART_PICKS_MIN_SCORE_FOREX = 65
- Confidence (1-5): 3

**### BOND**
- Real/noise verdict: No edge. n_closed=33, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: audit_trail/quality_gates.py SMART_PICKS_MIN_SCORE_BOND = 50
- Confidence (1-5): 5

**### MEME**
- Real/noise verdict: No edge. n_closed=6, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: None (class too small)
- Confidence (1-5): 5

**### ETF**
- Real/noise verdict: No edge. n_closed=9, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: None
- Confidence (1-5): 5

**### FUTURES**
- Real/noise verdict: No edge. n_closed=13, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: None
- Confidence (1-5): 5

**### INDEX**
- Real/noise verdict: No edge. n_closed=5, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: None
- Confidence (1-5): 5

**### UNKNOWN**
- Real/noise verdict: No edge. n_closed=3, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: None
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale CRYPTO today (only class with statistically credible, holdout-validated edge). DEMOTE every other class per MUTATION_THREE_AXIS_PROTOCOL.md — they have either zero proven cells or clear statistical failure.
