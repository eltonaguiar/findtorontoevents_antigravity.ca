# Pick Funnel Swarm Verdict — 2026-11-26 02:35 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20261126T023530Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-day Edge Analysis

Before per-class verdicts, three cross-cutting observations that drive everything below:

1. **The HC gate is dead.** `passed_high_conviction = 0` in every single class. `hc_filter.js` at score≥80 / conf≥0.75 / trust≥60 is filtering out 100% of picks. Either the trust score never reaches 60 (likely — see "trust=UNK" dominating every edge cell), or the score distribution never reaches 80. This is the single biggest structural finding.
2. **"trust=UNK" is the dominant dimension in every PROVEN cell.** That means the trust score is either unpopulated or below the lowest band for the vast majority of picks. Any "edge" conditioned on trust=UNK is really "edge conditioned on *no trust signal*" — which is a red flag, not a feature.
3. **The FOREX `consensus`/`regime_terminal` cell and the CRYPTO `ml`/`alpha_engine` cell are the two the user flagged.** I'll address both explicitly. The FOREX one has holdout_n=2 — that is not a holdout, that is a coin flip. The CRYPTO one is the only cell in the entire dataset that survives train/holdout with meaningful n on both sides.

---

### FOREX
- **Real/noise verdict:** **NOISE / LEAKAGE-SUSPECT.** The only "best PF" cell is `trust=UNK & conf=C>=0.90 & fam=regime` (n=39, WR 87%, PF 11.5). But: holdout_n=**2**, holdout_pf=1.18, holdout_pass=**false**. A 39-trade cell with 2 holdout trades is not a validated edge — it's a train-set artifact. The `regime_terminal` source with conf≥0.90 is almost certainly a small number of regime-flip events clustered in one macro window (likely a single FX pair, probably JPY or a carry-unwind episode). The class-level WR is 48.85% on n=520 — i.e., **the class as a whole is a coin flip**. `top_edges_proven` is empty. There is no FOREX edge. The 87% cell is exactly the kind of thing the user warned about: don't invent edges. This is not an edge.
- **90d expected P&L (1% risk, $100k):** **~$0 to −$1,500.** At 48.85% WR on 520 decisive trades with typical FX R:R ~1:1, expectancy is roughly −0.02R/trade × 520 × $1,000 = **−$1,040**, plus slippage. If you *did* size up the 39-trade "regime" cell at 1% risk, expected P&L is ~+$2,600 on paper but the holdout says it's noise — treat as $0.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` — raise from current (likely ~50) to **65**, and add a hard `MIN_TRUST_SCORE_FOREX = 40` so trust=UNK picks are excluded from the smart funnel entirely. The 26,609/27,154 pass rate (98%) is the problem: the gate is not gating.
- **Confidence (1-5):** **1** — no edge, and the one "edge" cell fails holdout.

---

### CRYPTO
- **Real/noise verdict:** **REAL, but modest — and the PF is inflated by the R:R distribution, not by win rate.** The cell `trust=UNK & conf=C0.75-0.80 & source=alpha_engine` has n=188, WR 64.4%, wr_shrunk 63.0%, PF 1.80, train_pf 1.62 (n=117), holdout_pf 2.21 (n=71), holdout_pass=**true**, wr_z=3.94, bonferroni_pass=**true**. This is the **only cell in the entire dataset** that survives train/holdout with meaningful n on both sides and a Bonferroni correction. That is a genuine, if modest, edge. **However:** (i) it is conditioned on `trust=UNK`, meaning the trust score is not adding information — the edge is really "alpha_engine + conf 0.75–0.80 + LONG"; (ii) the class-level WR is 44.25% on n=2,120, so this cell is a *subset* that outperforms a losing class — the class is still net-negative; (iii) PF 1.80 is not "suspiciously high" — it's consistent with a 63% WR and ~1:1 R:R. The user's suspicion about "CRYPTO ml cells" — there is no `ml` cell in the data provided; the alpha_engine cell is the one. It is **not** leakage-suspect on its face, but the `trust=UNK` conditioning is a smell: it suggests the trust score is broken, and the "edge" may be an artifact of how trust is computed (e.g., trust defaults to UNK for a specific source/strategy combo that happens to be good).
- **90d expected P&L (1% risk, $100k):** On the 188-trade cell at 1% risk ($1,000/trade), avg_pnl_pct=0.6438% → ~$644/trade × 188 = **~$121,000 gross**, minus ~0.1% slippage/fees per trade (~$188/trade × 188 = ~$35,000) → **~$85,000 net**. But this is *only* the cell; the class as a whole (2,120 decisive trades at 44.25% WR) is **net negative**: roughly −0.11R/trade × 2,120 × $1,000 = **−$233,000**. So the honest answer: **the class is a net loser; the cell is a real but small pocket of edge that is currently drowned by the rest of the class.** If you traded *only* the cell: ~+$85k. If you traded the class as-is: ~−$233k.
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` — raise to **70**, AND add a source-conditional floor: `MIN_SCORE_CRYPTO_ALPHA_ENGINE = 60` (keep alpha_engine flowing) while `MIN_SCORE_CRYPTO_OTHER = 75` (starve the rest). The 4,763/12,661 (37.6%) smart pass rate is too loose given the class WR is 44%. Also fix the trust score so `trust=UNK` is not the dominant band — that is a data-quality bug, not a gate.
- **Confidence (1-5):** **3** — the cell is real; the class is not.

---

### EQUITY
- **Real/noise verdict:** **LEAKAGE-SUSPECT — do not trade.** The cell `trust=UNK & rr=RR>=2.0 & fam=mean_reversion` has n=32, WR 96.88%, PF **112.8**, avg_pnl 1.57%, train_pf 34.4 (n=10), holdout_pf 99.0 (n=22), holdout_pass=true, wr_z=5.30, bonferroni_pass=true. **PF 112 is not a real edge — it is a data artifact.** A PF of 112 means average win / average loss ≈ 112:1, which is impossible in liquid equity mean-reversion unless (a) losses are being truncated to near-zero (stop-loss not being recorded, or P&L computed on a different basis than entry/exit), (b) the "loss" bucket is empty because losing trades are being classified as "open" or "expired" rather than "closed," or (c) there is look-ahead in the R:R≥2.0 filter (e.g., R:R computed *after* the trade resolves). The fact that `trust=UNK` is the conditioning dimension again points to a broken trust score. **This is the single most suspicious cell in the dataset.** The class-level WR of 71.9% on n=121 is also implausibly high for equity mean-reversion over 90 days — likely the same artifact. The `passed_smart` rate of 223/6,239 (3.6%) is the only sane number here.
- **90d expected P&L (1% risk, $100k):** **$0 — do not size.** If the PF 112 were real, 32 trades × 1% × 1.57% avg = ~$50k, but it is not real. Treat as $0 until the P&L accounting is audited.
- **Gate change:** **Do not change a gate — fix the P&L accounting first.** The gate change that matters is in `production_scanner.py`: audit how `avg_pnl_pct` and `pf` are computed for EQUITY mean_reversion. If losses are being dropped, `SMART_PICKS_MIN_SCORE_EQUITY` is irrelevant. Once fixed, set `SMART_PICKS_MIN_SCORE_EQUITY = 70` (currently 223/6,239 pass — 3.6% — which is actually reasonable, so the gate is not the problem; the accounting is).
- **Confidence (1-5):** **1** — PF 112 is a bug, not an edge.

---

### ETF
- **Real/noise verdict:** **NO EDGE — sample too small.** n_closed=13, WR 38.46%, no proven cells, no best_pf cells. 13 trades is not a sample. The 265/307 smart pass rate (86%) is a gate that isn't gating, but with n=13 there is nothing to conclude.
- **90d expected P&L (1% risk, $100k):** **~−$300** (13 trades × 1% × −0.23R ≈ −$300). Noise.
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` — raise to **70** to stop the 86% pass rate, but this is housekeeping, not edge-lifting.
- **Confidence (1-5):** **1** — no sample.

---

### COMMODITY
- **Real/noise verdict:** **NOISE — and the one candidate cell fails holdout.** Best cell `trust=UNK & fam=mean_reversion & dir=LONG` has n=20, WR 65%, wr_shrunk 57.5%, PF 5.09, but holdout_pass=**false**, bonferroni_pass=**false**, wr_z=1.34. n=20 with 5 train / 15 holdout is not a validation. The class-level WR of 61.54% on n=52 is the only positive class-level number in the dataset, but n=52 is too small to trust, and the 3,685/5,673 (65%) smart pass rate is far too loose. **Note the H-001 and H-036 rejections:** COMMODITY has a history of leakage (COT look-ahead) and harness rejection (inventory direction). The current mean_reversion/LONG cell is a *different* signal, but given the class's track record, treat with extreme skepticism.
- **90d expected P&L (1% risk, $100k):** **~+$1,500** on paper (52 trades × 1% × ~0.29R), but holdout fails — treat as **$0**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` — raise to **70** (from ~50), and add `MIN_N_FOR_PROMOTION_COMMODITY = 100` so no cell is promoted on n<100.
- **Confidence (1-5):** **2** — class WR looks positive but n is too small and the cell fails holdout.

---

### BOND
- **Real/noise verdict:** **NO EDGE.** n_closed=31, WR 38.71%, no proven cells, no best_pf cells. 2/1,280 smart pass rate (0.16%) — the gate is essentially closed, which is correct given the class is losing. Nothing to salvage.
- **90d expected P&L (1% risk, $100k):** **~−$700** (31 trades × 1% × −0.23R). Noise.
- **Gate change:** Leave `SMART_PICKS_MIN_SCORE_BOND` where it is (effectively closed). If anything, add `BOND_ENABLED = False` until a real signal is found.
- **Confidence (1-5):** **1** — no edge.

---

### PREDICTION_MARKET
- **Real/noise verdict:** **NO DATA.** n_closed=0. 358 scanned, 18 smart-passed, 0 closed. Cannot evaluate. The 358 opened / 0 closed is itself a bug — either resolution is not being recorded or the market horizon exceeds 90 days.
- **90d expected P&L (1% risk, $100k):** **$0** — no closed trades.
- **Gate change:** None — fix resolution recording first.
- **Confidence (1-5):** **1** — no data.

---

### FUTURES
- **Real/noise verdict:** **NO EDGE.** n_closed=16, WR 37.5%, no proven cells. Note **H-005** (futures_momentum_anti_signal) is a formally rejected hypothesis — do not re-derive. 102/143 smart pass rate (71%) is too loose for a class with 37.5% WR.
- **90d expected P&L (1% risk, $100k):** **~−$400** (16 trades × 1% × −0.25R). Noise.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` — raise to **70**.
- **Confidence (1-5):** **1** — no edge.

---

### INDEX
- **Real/noise verdict:** **NO DATA.** n_closed=1. 1,538/2,137 smart pass rate (72%) with 1 closed trade is a resolution/recording bug, not an edge. The 100% WR is a single trade.
- **90d expected P&L (1% risk, $100k):** **$0** — n=1.
- **Gate change:** None — fix resolution recording.
- **Confidence (1-5):** **1** — no data.

---

### UNKNOWN
- **Real/noise verdict:** **NO EDGE — and this is a data-quality alarm.** n_closed=5, WR 0%. 1,162 opened / 5 closed. The "UNKNOWN" class is where picks land when asset-class tagging fails. 1,167 scanned is 2.3% of total volume — not trivial. This is a tagging bug, not a class.
- **90d expected P&L (1% risk, $100k):** **~−$500** (5 trades × 1% × −1.0R). Noise.
- **Gate change:** Fix asset-class tagging in `production_scanner.py` — do not gate; route.
- **Confidence (1-5):** **1** — no edge, data bug.

---

### MEME
- **Real/noise verdict:** **NO EDGE.** n_closed=5, WR 40%. 12 scanned total. Nothing to evaluate.
- **90d expected P&L (1% risk, $100k):** **~−$100**. Noise.
- **Gate change:** None — too small to matter.
- **Confidence (1-5):** **1** — no sample.

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY with real money: CRYPTO — but only the `alpha_engine` + conf 0.75–0.80 + LONG cell, and only at reduced size (0.5% risk, not 1%).** It is the only cell in the entire dataset that survives train/holdout with meaningful n on both sides (n=117 train, n=71 holdout), passes Bonferroni, and has a plausible PF (1.80, not 112). Expected P&L on the cell alone at 1% risk is ~+$85k net of slippage over 90d; at 0.5% risk, ~+$42k. **Do not trade the CRYPTO class as a whole** — it is net −$233k. The gate change to make this actionable is `SMART_PICKS_MIN_SCORE_CRYPTO = 70` plus a source-conditional floor that keeps alpha_engine flowing while starving other sources.

**Demote per MUTATION_THREE_AXIS_PROTOCOL (mutate before kill): EQUITY.** The PF 112 cell is a P&L-accounting bug, not an edge, and the class-level 71.9% WR on n=121 is implausible. Do not kill the class — mutate the accounting first (audit `avg_pnl_pct` and `pf` computation in `production_scanner.py` for mean_reversion), then re-evaluate. If the accounting is fixed and the edge disappears (which I expect), then kill. **Second demotion: FOREX** — 48.85% WR on n=520 is a coin flip, and the one "edge" cell has holdout_n=2. Mutate the trust score (fix `trust=UNK` dominance) before killing, because the trust score being broken may be masking a real signal — but do not size up FOREX today.

**The single most important fix is not a gate — it is the trust score.** `trust=UNK` is the dominant conditioning dimension in every PROVEN cell across every class. That means the trust score is either unpop

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)
