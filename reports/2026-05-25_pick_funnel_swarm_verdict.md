# Pick Funnel Swarm Verdict — 2026-10-20 04:10 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20261020T040943Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-day Edge Analysis

Before the per-class verdicts, three structural observations that color everything below:

1. **`passed_high_conviction = 0` across every single asset class.** The HC gate (`score>=80, conf>=0.75, trust>=60`) is firing on **zero** trades in 90 days. Either the gate is misconfigured (trust>=60 is unreachable because most cells are `trust=UNK`), or the scoring distribution never reaches 80. This is the single biggest finding — the "HIGH CONVICTION" funnel is dead.
2. **`opened` >> `passed_smart` in every class** (e.g. EQUITY 5606 opened vs 220 passed_smart; FOREX 23121 vs 23587 — the only class where they're close). The dashboard is opening trades that never passed the smart gate. The funnel is not actually gating.
3. **The "PROVEN" cells are almost all the same trade.** In EQUITY, all three "top edges" are the *identical* 65-trade cell (mean_reversion, S40, LONG, conf<0.60, trust=UNK) sliced three ways. In CRYPTO, all three are the *identical* 185-trade cell (conf 0.75–0.80, S50, alpha_engine, LONG, trust=UNK). This is **not** three independent confirmations — it's one cell reported three times. Bonferroni "pass" on a single cell is meaningless when the cell was selected post-hoc from a large grid.

---

### EQUITY
- **Real/noise verdict:** **NOISE / LEAKAGE.** The 65-trade cell (WR 98.46%, PF 235.55) is not a real edge. PF of 235 means average win is ~235× average loss — that is physically impossible for a mean-reversion equity strategy with 1.44% avg PnL. This is almost certainly a **stop/target accounting bug** (e.g. losses recorded as 0, or wins marked at target while losers never close) or **look-ahead in the S40 score decile** (S40 = bottom score decile winning 98% is the opposite of what a score should do — a red flag for label leakage). The train/holdout split (133 → 99 PF) is *too* stable, which is itself suspicious — real edges decay. **Do not trade this.** The 70% headline WR on 137 closed trades is also suspect given the opened/closed ratio (5606 opened, 137 closed = 2.4% close rate; the closed sample is not representative).
- **90d expected P&L (1% risk, $100k):** **$0 — do not deploy.** If forced to mark-to-model the reported cell: 65 trades × 1% × $100k × 1.44% avg = ~$93.6k, but this is fictional given the leakage. Realistic expectation from the non-leaked 137-trade sample at 70% WR with unknown R:R: **indeterminate, likely negative after costs.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` — raise from current floor to **≥ 55** and add a hard `trust != UNK` requirement in `quality_gates.py`. The S40 (bottom decile) winning 98% proves the score is inverted or leaked; block S40 entirely until audited.
- **Confidence (1-5):** **1** (the edge is fake; the 70% headline is unrepresentative).

### COMMODITY
- **Real/noise verdict:** **NOISE.** 65 closed trades, 55.38% WR, no PROVEN cells. The best cell (RR>=2.0, alpha_engine, n=21, PF 4.3) **fails Bonferroni** and has train_n=11 — that's not a sample, that's a coin flip. Note the rejected H-001 (COT leakage) and H-036 (inventory) — this class has a documented history of leakage. The 3696/5915 passed_smart rate (62%) is far too permissive; the gate is not filtering.
- **90d expected P&L (1% risk, $100k):** **~$0 to slightly negative.** 65 trades × 1% × $100k × (55.4% × avg_win − 44.6% × avg_loss). With PF ~1.1 implied by 55% WR and unknown R:R, expect **−$2k to +$3k** before slippage; after 2–3 bps slippage on 65 trades, **≈ $0.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` — raise to **≥ 60** (currently passing 62% of scans is indefensible). Also add `rr >= 2.0` as a hard pre-filter in `quality_gates.py` since the only non-noise cell lives there.
- **Confidence (1-5):** **2** (no edge, but not actively harmful).

### FOREX
- **Real/noise verdict:** **NOISE — and the "best" cell is a textbook small-sample artifact.** The `regime/LONG/regime_terminal` cell has n=31, **train_n=5**, train_pf=0.0, holdout_pf=9.487, **holdout_pass=false, bonferroni_pass=false**. A train PF of 0.0 with 5 trades means the "edge" exists entirely in the holdout — that is the definition of overfitting to a regime window. The 42.21% headline WR on 533 decisive trades is a **losing** class. 23587/24447 passed_smart (96.5%!) means the smart gate is doing literally nothing for FOREX. This is the worst-configured class in the funnel.
- **90d expected P&L (1% risk, $100k):** **Negative.** 533 decisive trades at 42.2% WR. Even at 1.5:1 R:R, expectancy = 0.422×1.5 − 0.578×1 = −0.045R per trade → 533 × 1% × $100k × (−0.045) ≈ **−$24k** before slippage. FOREX slippage is real (1–2 pips); add ~$5–8k. **Net ≈ −$30k.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` — raise from current (passing 96.5%) to **≥ 65**, and add a **minimum train_n ≥ 20** requirement before any cell is eligible for promotion. The 96.5% pass rate is the smoking gun.
- **Confidence (1-5):** **1** (actively losing money; gate is broken).

### CRYPTO
- **Real/noise verdict:** **PLAUSIBLY REAL — the only class with a defensible edge, but the PF is inflated.** The 185-trade cell (conf 0.75–0.80, S50, alpha_engine, LONG) has: n=185, WR 75.68%, **wr_shrunk 73.17%**, PF 4.045, train_pf 4.519 / holdout_pf 3.317 (holdout_pass=true), wr_z 6.986, bonferroni_pass=true. This is the **only** cell in the entire dataset that survives holdout + Bonferroni + shrinkage. That said: (i) PF 4.0 is high but not impossible for a tight conf-band crypto momentum cell; (ii) the cell is `trust=UNK` — meaning the trust gate isn't contributing, the edge is purely conf+score+source; (iii) **single-source concentration risk**: it's all `alpha_engine`, so if that source has a bug, the edge evaporates. The 45.09% headline WR on 2462 trades is dragged down by the non-S50, non-0.75–0.80 trades — the edge is **narrow**, not class-wide. **This is the one to scale, carefully.**
- **90d expected P&L (1% risk, $100k):** 185 trades × 1% × $100k × 1.51% avg PnL = **~$279k gross**. Apply realistic crypto slippage (5–10 bps round-trip on 185 trades ≈ $9–18k) and a 20% haircut for the PF-inflation risk → **~$220–250k net.** Even at half the reported edge, **~$110–140k.** This is the only class where the math is positive.
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` — **lower** to **50** (to capture the S50 cell) but add a **hard `conf >= 0.75 AND conf < 0.80` band** and `source == alpha_engine` in `quality_gates.py`. Currently 3571/13007 (27%) pass smart but the edge lives in a ~1.4% slice; the gate is too coarse. Also fix `hc_filter.js`: `trust>=60` is unreachable (all edges are `trust=UNK`), so HC never fires — **change `trust>=60` to `trust>=0` (or remove) and rely on `score>=80 && conf>=0.75`** to actually surface the crypto edge.
- **Confidence (1-5):** **4** (real but narrow; needs source-diversity check).

### ETF
- **Real/noise verdict:** **NOISE.** 9 closed trades, 22.22% WR. n=9 is not a sample. No cells. 304/355 passed_smart (86%) — gate is a no-op.
- **90d expected P&L (1% risk, $100k):** **≈ −$1k** (9 trades, 22% WR, tiny sample; statistically meaningless).
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` — raise to **≥ 70** or **disable ETF picks entirely** until n≥30 closed. 86% pass rate is indefensible.
- **Confidence (1-5):** **1** (no data, no edge).

### INDEX
- **Real/noise verdict:** **NOISE.** 5 closed trades, 20% WR. 1485/1828 passed_smart (81%). No cells.
- **90d expected P&L (1% risk, $100k):** **≈ −$1k** (5 trades; noise).
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` — raise to **≥ 70** or disable. 81% pass rate.
- **Confidence (1-5):** **1** (no data).

### UNKNOWN
- **Real/noise verdict:** **NOISE / DATA HYGIENE FAILURE.** 3 closed trades, 0% WR. 152/1417 passed_smart. The existence of an "UNKNOWN" asset class with 1417 scans and 1414 opened trades is a **classification bug** — these should be routed or dropped, not traded.
- **90d expected P&L (1% risk, $100k):** **≈ −$300** (3 trades, all losses; noise).
- **Gate change:** In `quality_gates.py`, add `if asset_class == "UNKNOWN": return False` — **hard-drop UNKNOWN at the scanner level.** 1414 opened trades from an unclassified bucket is a data-integrity emergency.
- **Confidence (1-5):** **1** (data bug, not a strategy).

### BOND
- **Real/noise verdict:** **NOISE.** 33 closed, 39.39% WR, no cells. 1/573 passed_smart (0.17%) — the gate is *too tight* here (opposite problem from FOREX), but the 540 opened trades bypassed it anyway. Losing class.
- **90d expected P&L (1% risk, $100k):** **Negative.** 33 trades at 39.4% WR → expectancy ≈ −0.1R → **≈ −$3k** before costs.
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` — the 0.17% pass rate suggests the floor is mis-set; **lower to a level that passes ~10–15%** (calibrate to the 90th percentile of bond scores) OR **disable BOND** until n≥50 closed. Given 39% WR, disabling is safer.
- **Confidence (1-5):** **1** (losing, tiny sample).

### FUTURES
- **Real/noise verdict:** **NOISE.** 16 closed, 43.75% WR, no cells. Note rejected H-005 (futures momentum anti-signal) — this class has a documented failure. 149/200 passed_smart (74.5%).
- **90d expected P&L (1% risk, $100k):** **≈ −$1k** (16 trades, 44% WR; noise).
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` — raise to **≥ 65**; 74.5% pass rate is too loose. Given H-005, consider **disabling** until a new hypothesis is registered.
- **Confidence (1-5):** **1** (no edge, prior failure).

### MEME
- **Real/noise verdict:** **NOISE.** 7 closed, 14.29% WR. 13/29 passed_smart. No cells. This is a lottery-ticket class with no statistical basis.
- **90d expected P&L (1% risk, $100k):** **≈ −$600** (7 trades, 14% WR; noise).
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME` — **disable MEME entirely** (set floor to 100 / unreachable) until n≥50 closed and WR>50%. 7 trades is not a strategy.
- **Confidence (1-5):** **1** (no data, no edge).

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY with real money: CRYPTO — and only CRYPTO, and only the narrow cell.**
The `conf 0.75–0.80 & score_dec S50 & source=alpha_engine & LONG` cell is the **only** signal in the entire 90-day dataset that survives holdout (train PF 4.52 → holdout PF 3.32), Bonferroni (wr_z 6.99), and Bayesian shrinkage (73.17% shrunk WR on n=185). Expected 90d P&L at 1% risk on $100k: **~$220–250k net** after slippage. **Caveats before scaling:** (1) it's single-source (`alpha_engine`) — verify that source has no look-ahead by replaying 10 random trades against raw timestamps; (2) it's `trust=UNK` — the trust gate contributes nothing, so don't credit it; (3) size at **0.5% risk, not 1%**, for the first 30 days to confirm live-vs-backtest parity, then step to 1%.

**DEMOTE per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` (mutate before kill): FOREX.**
FOREX is the clearest case for demotion-not-kill: 533 decisive trades at **42.21% WR** (a losing class), 96.5% smart-pass rate (gate is a no-op), and the only "best" cell has **train_n=5, train_pf=0.0, holdout_pass=false, bonferroni_pass=false** — a textbook overfit. Per the three-axis protocol, **mutate first**: (Axis 1 — gate) raise `SMART_PICKS_MIN_SCORE_FOREX` to ≥65 and require `train_n ≥ 20` for cell promotion; (Axis 2 — source) audit `regime_terminal` source for the 5-trade train window; (Axis 3 — sizing) cut FOREX to 0.25% risk during mutation. If after 30 days the mutated gate still shows WR < 48%, **kill FOREX** and reallocate to CRYPTO.

**Also demote (kill, not mutate): UNKNOWN, MEME, ETF, INDEX.** These have n<10 closed trades and/or 0% WR — they are data-hygiene failures, not strategies. `UNKNOWN` in particular (1414 opened trades from an unclassified bucket) is a **scanner bug** that must be fixed before any further funnel analysis is trustworthy.

**The meta-finding:** `passed_high_conviction = 0` in all 10 classes means the HC gate in `hc_filter.js` (`score>=80, conf>=0.75, trust>=60`) is **structurally unreachable** because every real edge lives at `trust=UNK`. Fix `hc_filter.js` first — change `trust>=60` to `trust>=0` (or drop the trust dimension) — or the "HIGH CONVICTION" funnel will remain permanently empty and the dashboard will keep surfacing the un-gated `opened` trades instead of the actual edges.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### EQUITY
- Real/noise verdict: Noise/leakage. n=65 with 64 wins and PF=235 is statistically impossible in live trading; indicates data error, single-symbol concentration, or look-ahead bias rather than a real edge.
- 90d expected P&L (1% risk, $100k): $0 (edge is invalid; any forward deployment would likely produce large losses once leakage is removed).
- Gate change: SMART_PICKS_MIN_SCORE_EQUITY = 75
- Confidence (1-5): 5

### CRYPTO
- Real/noise verdict: Marginally real. n=185, WR_shrunk=73.17%, PF=4.045 with holdout_pass=true and bonferroni_pass=true is credible, though PF remains elevated and should be monitored for single-exchange concentration.
- 90d expected P&L (1% risk, $100k): ~$8,400 (185 trades × ~1.51% avg win, 1% risk sizing, 0.15% slippage per trade, 75% win rate on decisive trades).
- Gate change: HC_FILTER_MIN_CONF = 0.78
- Confidence (1-5): 4

### FOREX
- Real/noise verdict: Noise. No proven cells; best_pf cells fail holdout and bonferroni, consistent with rejected hypotheses in the registry.
- 90d expected P&L (1% risk, $100k): -$2,100 (negative expectancy on the 533 closed trades).
- Gate change: SMART_PICKS_MIN_SCORE_FOREX = 65
- Confidence (1-5): 5

### COMMODITY
- Real/noise verdict: Noise. No proven cells; best_pf cells fail bonferroni and align with previously rejected COT/inventory hypotheses.
- 90d expected P&L (1% risk, $100k): -$800
- Gate change: SMART_PICKS_MIN_SCORE_COMMODITY = 70
- Confidence (1-5): 5

### FUTURES
- Real/noise verdict: No edge. n_closed=16 is too small; no proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_FUTURES = 80
- Confidence (1-5): 5

### BOND
- Real/noise verdict: No edge. n_closed=33 with zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_BOND = 75
- Confidence (1-5): 5

### ETF
- Real/noise verdict: No edge. n_closed=9 with zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_ETF = 80
- Confidence (1-5): 5

### INDEX
- Real/noise verdict: No edge. n_closed=5 with zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_INDEX = 80
- Confidence (1-5): 5

### UNKNOWN
- Real/noise verdict: No edge. n_closed=3 with zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_UNKNOWN = 80
- Confidence (1-5): 5

### MEME
- Real/noise verdict: No edge. n_closed=7 with zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_MEME = 85
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale CRYPTO today (only class with a statistically defensible proven edge that survives holdout). Demote EQUITY immediately per MUTATION_THREE_AXIS_PROTOCOL.md — its metrics are incompatible with live execution and should be mutated to zero allocation before any further review. All other classes have no actionable edge.
