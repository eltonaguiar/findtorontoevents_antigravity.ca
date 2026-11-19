# Pick Funnel Swarm Verdict — 2026-11-19 04:41 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20261119T044107Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-Day Edge Analysis

**Bottom line up front:** The funnel is broken in a way that makes most "edges" untrustworthy. `passed_high_conviction = 0` across **every** asset class over 90 days means the HC gate (`score>=80, conf>=0.75, trust>=60`) is effectively dead code — nothing reaches it. Meanwhile `opened` ≈ `scanned` in most classes (FOREX: 26,283/27,657 = 95%; COMMODITY: 5,747/5,787 = 99%; EQUITY: 5,678/5,786 = 98%), which means the "Smart" gate is passing ~everything and the funnel is not filtering. The only class where `passed_smart` is meaningfully < `scanned` is CRYPTO (3,871/11,821 = 33%) and EQUITY (227/5,786 = 4%) — and EQUITY's 4% pass rate is the only one that looks like a real gate.

The "PROVEN" cells are almost all `trust=UNK`. That is a red flag, not a feature: the trust dimension is unpopulated, so every "edge" is really a 2- or 3-way slice of an unlabeled bucket. Treat all `trust=UNK` cells as **unverified provenance**, not as validated edges.

---

### COMMODITY
- **Real/noise verdict:** **NOISE / no edge.** n=40 closed over 90d is far below the n≥20-per-cell threshold for any single cell to be meaningful, and the best cell (`trust=UNK & dir=LONG & source=alpha_engine`, n=30, WR_shrunk 56%, PF 1.87) fails Bonferroni and has holdout n=13 with PF 1.42 — that's a coin flip with a tailwind. The 65% headline WR is on 40 trades; the 95% CI on 26/40 is roughly [48%, 79%]. Not distinguishable from 50%. **Also flag:** H-001 (COT leakage) and H-036 (inventory gate) are both COMMODITY hypotheses that were killed — the class has a documented history of leakage-driven fake edges. Do not trust any COMMODITY cell until provenance is audited.
- **90d expected P&L (1% risk, $100k):** **$0.** Do not size. If forced to model the "best" cell at 1% risk ($1,000/trade) × 30 trades × avg_pnl 0.66% × 1% risk fraction ≈ **+$198 gross**, minus ~$5–10/trade slippage on 30 trades ≈ **+$0 to +$50 net**. Statistically indistinguishable from zero.
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` — raise from current (effectively ~0, since 3,782/5,787 pass) to **≥70**, and add a hard `MIN_CLOSED_TRADES_FOR_PROMOTION = 100` before any COMMODITY cell can be labeled PROVEN.
- **Confidence (1-5):** **1**

### FOREX
- **Real/noise verdict:** **NOISE, and the top cell is almost certainly leakage.** The `trust=UNK & conf=C>=0.90 & fam=regime` cell (n=38, WR 89.5%, PF **14.4**) is the textbook signature of look-ahead: holdout_n=2, holdout_pass=false, and the "edge" is entirely in the training window (train_pf 13.6 on n=36). A PF of 14 on FX is not a real edge — it's a timestamp bug or a regime label that peeks. **This is the same failure mode as H-001.** The class-level 51.2% WR on 453 decisive trades is a coin flip. `passed_verified_alpha = 9` out of 27,010 is the only honest number in the row: the verified-alpha gate is correctly rejecting ~99.97% of FOREX.
- **90d expected P&L (1% risk, $100k):** **$0.** At 51.2% WR with unknown avg R, expected value is ~0 minus costs. Modeling 453 decisive trades × 1% risk × (0.512 − 0.488) × avg_R ≈ **+$0 to +$200 gross**, minus FX spread/slippage (~0.5–1 pip × 453) ≈ **−$200 to +$0 net**. Do not size.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` — raise to **≥75** (currently passing 97.7% of scans). Also add a `REGIME_LABEL_LOOKAHEAD_GUARD` that rejects any `fam=regime` pick whose label timestamp is ≥ the bar close. The regime cell must be quarantined until provenance is proven.
- **Confidence (1-5):** **1**

### CRYPTO
- **Real/noise verdict:** **One real edge, one suspicious cell.** The PROVEN cell `trust=UNK & conf=C0.75-0.80 & score_dec=S50` (n=192, WR_shrunk 63.7%, PF 1.71, holdout_pass=true, Bonferroni pass) is the **only** cell in the entire dataset that survives holdout + multiple-testing correction with meaningful n. That is a genuine, if modest, edge. **However:** the `best_pf_overall` cell `trust=UNK & rr=RR1.5-2.0 & source=alpha_engine` (PF 1.82, n=174) fails Bonferroni and has holdout PF 1.27 — treat as suggestive, not proven. **Flag:** the user's prompt mentions a "CRYPTO `ml` cell" with suspiciously high PF — it is **not in this dataset**, which means either it was already filtered out or it's in a different slice. If it exists elsewhere, quarantine it: ML cells with PF > 3 on crypto are almost always feature leakage (target encoding, future-bar features, or survivorship in the training set). The class-level 44.9% WR on 2,181 decisive trades is **below coin-flip** — the class as a whole loses money; only the narrow conf-band cell wins.
- **90d expected P&L (1% risk, $100k):** Model only the PROVEN cell: 192 trades × $1,000 risk × avg_pnl 0.695% × (1% risk fraction) ≈ **+$1,335 gross**. Apply crypto slippage/fees (~0.1–0.2% round-trip on notional, ~$10–20/trade × 192) ≈ **−$2,000 to −$3,800**. **Net ≈ −$700 to −$2,500.** The edge is real but **does not survive realistic crypto transaction costs at 1% risk sizing.** To make it positive you need either (a) larger avg_pnl per trade, (b) lower fees (maker-only), or (c) sizing up only on the conf 0.75–0.80 band and skipping the rest.
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` — raise to **≥65** (currently 3,871/11,821 = 33% pass; tightening to ~15% pass would concentrate capital on the conf 0.75–0.80 band). Also add `CRYPTO_MIN_CONF_BAND = [0.75, 0.80]` as a hard filter for any auto-sized pick.
- **Confidence (1-5):** **3** (the cell is real; the class is not)

### EQUITY
- **Real/noise verdict:** **SUSPICIOUS — likely leakage or single-symbol concentration.** The PROVEN cell `trust=UNK & rr=RR>=2.0 & fam=mean_reversion` has **WR 97.4%, PF 136, n=38, holdout_pass=true, Bonferroni pass**. A PF of 136 is not a real edge — it is a bug. Possible causes: (1) `rr=RR>=2.0` is being computed from *realized* R rather than *planned* R (look-ahead), (2) the mean_reversion family is concentrated in 1–2 symbols that happened to trend, (3) the holdout split is not time-ordered. **The fact that all three "top" cells are the same 38 trades with different dimension labels confirms this is one cell, not three independent edges.** Also note: `passed_smart = 227 / 5,786 = 3.9%` — the Smart gate is doing real work here, but `opened = 5,678` means 5,451 picks bypassed Smart entirely. That's a funnel integrity bug. **Do not trade this cell until the RR computation is audited.**
- **90d expected P&L (1% risk, $100k):** **$0 (do not size).** If the cell were real at face value: 38 × $1,000 × 1.60% ≈ **+$608 gross**. But PF 136 is not real; assume the true edge is ~0 until audited. **Expected: $0.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` — keep at current (it's the only gate working), but add `EQUITY_RR_MUST_BE_PLANNED_NOT_REALIZED = True` and `EQUITY_MAX_SINGLE_SYMBOL_CONCENTRATION = 0.20`. The RR>=2.0 cell must be re-derived with planned R before it can be promoted.
- **Confidence (1-5):** **1** (the cell is almost certainly fake)

### PREDICTION_MARKET
- **Real/noise verdict:** **NO DATA.** n=10 scanned, 0 closed. Cannot evaluate. Do not promote, do not demote — **quarantine** until n≥30 closed.
- **90d expected P&L (1% risk, $100k):** **$0** (no closed trades).
- **Gate change:** `SMART_PICKS_MIN_SCORE_PREDICTION_MARKET` — leave at current; add `MIN_CLOSED_TRADES_FOR_EVALUATION = 30` so this class is auto-flagged as "insufficient data" rather than silently passing.
- **Confidence (1-5):** **1**

### BOND
- **Real/noise verdict:** **NOISE / negative edge.** 38.7% WR on 31 decisive trades. `passed_smart = 1 / 1,170` — the Smart gate is correctly rejecting 99.9% of BOND picks, but `opened = 1,139` means they're being opened anyway. This is a **funnel integrity failure**: the gate says no, the executor says yes. The class is losing money and the gate is being ignored.
- **90d expected P&L (1% risk, $100k):** **Negative.** 31 trades × $1,000 × (0.387 − 0.613) × avg_R ≈ **−$200 to −$400 gross**, minus costs ≈ **−$300 to −$500 net**. Do not size.
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` — raise to **≥80** AND fix the executor to **respect the Smart gate** (currently `opened` ≫ `passed_smart`). The gate change is worthless if the executor ignores it.
- **Confidence (1-5):** **1**

### ETF
- **Real/noise verdict:** **NOISE / negative edge.** 12.5% WR on 8 decisive trades. n=8 is far too small to conclude anything, but the direction is bad. `passed_smart = 269 / 307 = 88%` — gate is passing almost everything.
- **90d expected P&L (1% risk, $100k):** **Negative, but n too small to size.** 8 trades × $1,000 × (0.125 − 0.875) × avg_R ≈ **−$300 to −$600 gross**. Do not size.
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` — raise to **≥70**; add `MIN_CLOSED_TRADES_FOR_EVALUATION = 30`.
- **Confidence (1-5):** **1**

### UNKNOWN
- **Real/noise verdict:** **NOISE / data quality failure.** 0% WR on 5 trades. The existence of an `UNKNOWN` asset class with 1,261 scanned picks is itself a bug — these should be classified or rejected at ingest. `passed_smart = 108 / 1,261 = 8.6%` but `opened = 1,256` — again, executor ignoring gate.
- **90d expected P&L (1% risk, $100k):** **$0** (n too small, and the class shouldn't exist).
- **Gate change:** Add `REJECT_UNCLASSIFIED_ASSET_CLASS = True` in `quality_gates.py` — UNKNOWN picks should never reach the executor.
- **Confidence (1-5):** **1**

### INDEX
- **Real/noise verdict:** **NO DATA.** n=1 closed. Cannot evaluate.
- **90d expected P&L (1% risk, $100k):** **$0** (n=1).
- **Gate change:** `MIN_CLOSED_TRADES_FOR_EVALUATION = 30` (same as above).
- **Confidence (1-5):** **1**

### FUTURES
- **Real/noise verdict:** **NOISE / negative edge.** 37.5% WR on 16 decisive trades. `passed_smart = 113 / 158 = 72%` — gate passing most. **Flag:** H-005 (futures_momentum_anti_signal) was killed — the class has a documented history of failed signal inversions. Do not re-derive.
- **90d expected P&L (1% risk, $100k):** **Negative.** 16 × $1,000 × (0.375 − 0.625) × avg_R ≈ **−$150 to −$300 gross**. Do not size.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` — raise to **≥70**; add `MIN_CLOSED_TRADES_FOR_EVALUATION = 30`.
- **Confidence (1-5):** **1**

### MEME
- **Real/noise verdict:** **NOISE.** 33.3% WR on 6 decisive trades. n=6 is meaningless. `passed_verified_alpha = 2 / 15` — the verified-alpha gate is correctly rejecting most MEME picks, but `opened = 9` means 7 bypassed it.
- **90d expected P&L (1% risk, $100k):** **$0** (n too small).
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME` — raise to **≥75**; add `MIN_CLOSED_TRADES_FOR_EVALUATION = 30`.
- **Confidence (1-5):** **1**

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY with real money: NONE.** Not one asset class has a cell that survives (a) holdout, (b) Bonferroni, (c) realistic transaction costs, and (d) provenance audit. The closest is **CRYPTO's `conf=C0.75-0.80 & score_dec=S50` cell** (n=192, WR_shrunk 63.7%, PF 1.71, holdout_pass=true, Bonferroni pass) — but at 1% risk sizing with realistic crypto fees, it is **net negative**. The only way to make it positive is to (i) size up only on that conf band, (ii) use maker-only execution to cut fees, and (iii) accept that the class-level 44.9% WR means you are trading a narrow pocket of edge inside a losing class. **That is a paper-trade candidate, not a real-money candidate.**

**Demote per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` (mutate before kill):**

1. **BOND** — 38.7% WR, gate ignored by executor. **Mutate:** enforce `SMART_PICKS_MIN_SCORE_BOND ≥ 80` AND fix executor to respect gate. If after 30 days the class still has <45% WR on n≥30, kill.
2. **FUTURES** — 37.5% WR, H-005 already killed the momentum inversion. **Mutate:** raise `SMART_PICKS_MIN_SCORE_FUTURES ≥ 70` and add a `FUTURES_MIN_HOLDOUT_PF = 1.2` requirement. If no cell passes in 30 days, kill.
3. **ETF** — 12.5% WR on n=8. **Mutate:** raise `SMART_PICKS_MIN_SCORE_ETF ≥ 70` and require `MIN_CLOSED_TRADES_FOR_EVALUATION = 30` before any promotion. If n<30 in 30 days, kill.
4. **UNKNOWN** — should not exist. **Kill at ingest** (`REJECT_UNCLASSIFIED_ASSET_CLASS = True`). This is not a mutation, it's a bug fix.
5. **COMMODITY** — 65% WR on n=40 is not distinguishable from 50%, and the class has two killed leakage hypotheses (H-001, H-036). **Mutate:** raise `SMART_PICKS_MIN_SCORE_COMMODITY ≥ 70` and require `MIN_CLOSED_TRADES_FOR_PROMOTION = 100`. Do not promote any cell until provenance is audited.


### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### COMMODITY
- Real/noise verdict: Noise — n=40 total closed, top cells n=20-30 with holdout failures or bonferroni=false; PFs modest but no proven cells survive scrutiny.
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge; any live use would be random).
- Gate change: SMART_PICKS_MIN_SCORE_COMMODITY = 65
- Confidence (1-5): 4

### FOREX
- Real/noise verdict: Noise — n=453 decisive but top cells n=38 with holdout_n=2, holdout_pass=false; PF=14.449 is leakage/overfit artifact (tiny holdout, regime_terminal source concentration).
- 90d expected P&L (1% risk, $100k): -$420 (random walk around 51% WR after slippage).
- Gate change: HC_MIN_CONF = 0.82
- Confidence (1-5): 5

### CRYPTO
- Real/noise verdict: Marginally real — one proven cell n=192, WR_shrunk=63.68, PF=1.709, holdout_pass=true, bonferroni=true; other high-PF cells are weaker but this one holds.
- 90d expected P&L (1% risk, $100k): $1,180 (assume 1% risk/trade, 0.15% avg slippage, ~180 qualifying trades).
- Gate change: SMART_PICKS_MIN_SCORE_CRYPTO = 52
- Confidence (1-5): 3

### EQUITY
- Real/noise verdict: Noise/leakage — PF=136 on n=38 with train_n=12 is classic overfit; matches pattern of rejected EQUITY hypotheses (options/gamma/IV).
- 90d expected P&L (1% risk, $100k): -$310 (expect reversion to ~50% WR).
- Gate change: HC_MIN_TRUST = 70
- Confidence (1-5): 5

### PREDICTION_MARKET
- Real/noise verdict: No edge — n_closed=0.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_PREDICTION = 80
- Confidence (1-5): 5

### BOND
- Real/noise verdict: No edge — n=31, no proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_BOND = 75
- Confidence (1-5): 5

### ETF
- Real/noise verdict: No edge — n=8.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_ETF = 70
- Confidence (1-5): 5

### UNKNOWN
- Real/noise verdict: No edge — n=5.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_UNKNOWN = 80
- Confidence (1-5): 5

### INDEX
- Real/noise verdict: No edge — n=1.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_INDEX = 80
- Confidence (1-5): 5

### FUTURES
- Real/noise verdict: No edge — n=16, matches rejected futures hypotheses.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_FUTURES = 75
- Confidence (1-5): 5

### MEME
- Real/noise verdict: No edge — n=6.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_MEME = 80
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale CRYPTO today (only class with a holdout-validated proven cell). Demote EQUITY per MUTATION_THREE_AXIS_PROTOCOL (overfit PFs + prior rejected hypotheses).
