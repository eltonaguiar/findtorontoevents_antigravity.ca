# Pick Funnel Swarm Verdict — 2026-10-29 04:09 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20261029T040808Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-Day Edge Analysis

**Bottom line up front:** The funnel is broken in a way that makes most of the "PROVEN" cells untrustworthy. `passed_high_conviction = 0` across **every** asset class while `opened` is in the thousands means the HC gate is either dead code, mis-wired, or being bypassed. The two "PROVEN" cells (CRYPTO conf=0.75-0.80/S50/alpha_engine and EQUITY conf<0.60/mean_reversion) both have the fingerprint of **selection-on-outcome leakage**, not edge. FOREX has no proven edge and the "best PF" cell fails holdout. COMMODITY has no proven edge and the best cell fails holdout. Everything else is n<20 noise.

---

### CRYPTO
- **Real/noise verdict:** **NOISE / LEAKAGE.** The "PROVEN" cell `conf=C0.75-0.80 & score_dec=S50 & source=alpha_engine` (n=182, WR=79.1%, shrunk 76.2%, PF=4.36) is suspicious on three counts: (1) the three "distinct" cells are the **same 182 trades** re-sliced — `trust=UNK` and `dir=LONG` are constant within the cell, so this is one cell, not three independent confirmations; (2) `score_dec=S50` is a *decile bucket* — if S50 means "top decile of score," then the cell is defined by the score that the scanner already uses to rank, which is circular; (3) holdout PF (2.79) is less than half train PF (6.52) — classic overfit decay, and the holdout is only 88 trades. The `ml` cell you flagged isn't in the top-3 list, but the same pattern applies: any cell with PF>4 on n<200 in a 90-day window with a 2.4× train/holdout PF gap should be treated as **unvalidated**. Also note: `opened=10,490` but `passed_smart=3,628` — 6,862 trades were opened that never passed the smart gate. That's a funnel integrity bug, not an edge.
- **90d expected P&L (1% risk, $100k):** **$0 recommended.** If you *forced* sizing on the 182-trade cell at 1% risk ($1,000/trade) with avg_pnl=1.61% and 79% WR: gross ≈ 182 × $1,000 × 0.0161 ≈ **$2,930**, minus ~0.10% round-trip slippage+fees on $182k notional ≈ $182, minus the 21% loss tail (38 losses × ~$1,000 × avg loss ~1.5% ≈ $570) → **net ≈ $2,180**. But given the leakage flags, the honest number is **$0 — do not size this.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` — raise from current (likely 50) to **65**, AND fix the funnel bug: `opened` must be `<= passed_smart`. The 6,862 un-gated opens are the real problem.
- **Confidence (1-5):** **2** — the cell is real in-sample but the train/holdout gap and the re-sliced "three cells" pattern say overfit.

### COMMODITY
- **Real/noise verdict:** **NOISE.** `top_edges_proven = []`. Best PF cell is `trust=UNK & dir=LONG & source=alpha_engine` (n=31, WR=58.1%, shrunk 54.9%, PF=1.93) — **fails holdout** (holdout PF=1.07, holdout_pass=false) and fails Bonferroni. This is exactly the H-001/H-036 pattern: a long-only, alpha_engine-sourced cell that looks OK in-sample and dies out-of-sample. Do not re-derive. The 61.7% headline WR is on n=47 closed — statistically meaningless.
- **90d expected P&L (1% risk, $100k):** **$0.** n=47 closed is below any sizing threshold. If forced: 47 × $1,000 × 0.0069 ≈ **$324 gross**, but holdout failure means expected value is **negative** after slippage.
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` — raise to **70** and add a hard `min_closed_trades_for_sizing = 100` guard. Currently 3,640/5,918 pass smart (61%) — far too loose.
- **Confidence (1-5):** **1** — no proven edge, holdout fails, matches two falsified hypotheses.

### EQUITY
- **Real/noise verdict:** **LEAKAGE — flag hard.** `trust=UNK & conf=C<0.60 & fam=mean_reversion` (n=65, WR=98.46%, shrunk 87.1%, **PF=176.1**, holdout PF=99.0). A PF of 176 is not an edge; it is a **data artifact**. Three red flags: (1) `conf=C<0.60` — the *lowest* confidence band producing the *highest* WR is the inverse of every real signal; (2) `trust=UNK` — unknown trust producing 98% WR means trust scoring is broken or the cell is post-hoc; (3) PF=176 with avg_pnl=1.54% implies avg loss ≈ 0.009% — i.e., **losses are being recorded as near-zero**, which is the signature of a stop-loss that never triggers or a P&L attribution bug. This is almost certainly the same class of bug as H-001 (look-ahead) or a settlement-timestamp issue. **Do not size.** The 70.9% headline WR on n=134 is also too small to trust.
- **90d expected P&L (1% risk, $100k):** **$0 — and investigate the P&L attribution before any sizing.** If the PF were real, 65 × $1,000 × 0.0154 ≈ **$1,001 gross**; but a PF of 176 means the loss side is mis-recorded, so the true number is unknown and likely much lower.
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` — **lower** to 45 (currently only 234/5,822 = 4% pass, which is why n is tiny), BUT simultaneously add a `MIN_TRUST_FOR_SIZING = 40` guard in `hc_filter.js` so `trust=UNK` cells cannot be sized. The gate change that lifts edge most is fixing the trust=UNK leak, not the score threshold.
- **Confidence (1-5):** **1** — PF=176 is a bug, not an edge.

### FOREX
- **Real/noise verdict:** **NOISE.** `top_edges_proven = []`. Best PF cell `trust=UNK & fam=regime & dir=LONG` (n=29, WR=82.8%, shrunk 69.4%, PF=5.22) **fails holdout** (train_n=3, holdout_pass=false, Bonferroni=false). n=29 with train_n=3 is not a train/test split — it's noise. The `consensus` cell you flagged isn't in the top-3, but the pattern (regime_terminal source, LONG-only, trust=UNK) is the same single-source concentration risk. 23,775/24,554 pass smart (97%) — the smart gate is a no-op for FOREX. 44.3% WR on n=497 is a **losing** class.
- **90d expected P&L (1% risk, $100k):** **Negative.** 497 decisive × $1,000 × (0.4427 × avg_win − 0.5573 × avg_loss). With avg_pnl=0.52% on the best cell, the class-level EV is roughly **−$2,000 to −$4,000** over 90d. Do not size.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` — raise from current (effectively 0, since 97% pass) to **60**, and add `MIN_CLOSED_FOR_SIZING = 200` per cell. The 97% pass rate is the single biggest funnel defect in the system.
- **Confidence (1-5):** **1** — no proven edge, holdout fails, class-level WR < 50%.

### ETF
- **Real/noise verdict:** **NOISE.** n=10 closed, WR=20%. No proven cells. Statistically meaningless.
- **90d expected P&L (1% risk, $100k):** **$0.** n=10 is below any threshold.
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` — raise to **70**; 300/354 (85%) pass is too loose for a 10-trade sample.
- **Confidence (1-5):** **1**.

### FUTURES
- **Real/noise verdict:** **NOISE.** n=16 closed, WR=43.75%. No proven cells. Matches H-005 (futures momentum anti-signal — inversion does not fix it).
- **90d expected P&L (1% risk, $100k):** **$0.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` — raise to **70**; 147/203 (72%) pass is too loose.
- **Confidence (1-5):** **1**.

### BOND
- **Real/noise verdict:** **NOISE / BROKEN GATE.** `passed_smart = 0` but `opened = 700`. **Every single BOND trade bypassed the smart gate.** WR=40% on n=30. This is a funnel integrity failure, not an edge question.
- **90d expected P&L (1% risk, $100k):** **Negative.** 30 × $1,000 × (0.40 × avg_win − 0.60 × avg_loss) ≈ **−$300 to −$600**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` — set to **65** AND fix the bypass: `opened` must be `<= passed_smart`. The 700 un-gated opens are the bug.
- **Confidence (1-5):** **1**.

### UNKNOWN
- **Real/noise verdict:** **NOISE.** n=3 closed, WR=0%. `passed_smart=150` but `opened=1,384` — 1,234 bypasses. This class should not exist in production; it's a routing bug.
- **90d expected P&L (1% risk, $100k):** **$0.**
- **Gate change:** Add `REJECT_UNKNOWN_CLASS = True` in `quality_gates.py` — route UNKNOWN to a quarantine bucket, not to `opened`.
- **Confidence (1-5):** **1**.

### INDEX
- **Real/noise verdict:** **NOISE.** n=4 closed, WR=25%. 1,377/1,737 pass smart (79%) but only 4 close — the class is effectively un-tradeable in this window.
- **90d expected P&L (1% risk, $100k):** **$0.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` — raise to **70**; 79% pass is too loose.
- **Confidence (1-5):** **1**.

### MEME
- **Real/noise verdict:** **NOISE.** n=8 closed, WR=25%. No proven cells.
- **90d expected P&L (1% risk, $100k):** **$0.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME` — raise to **75**; 13/29 pass is too loose for a 8-trade sample.
- **Confidence (1-5):** **1**.

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY with real money: NONE.** Not one asset class has a cell that survives the three tests (n≥100 closed, holdout_pass=true, Bonferroni_pass=true) *and* is free of leakage flags. The two "PROVEN" cells both fail the leakage smell test:
- CRYPTO: train/holdout PF gap 6.52→2.79, three "cells" are one re-sliced cell.
- EQUITY: PF=176 with avg loss ≈ 0.009% — P&L attribution bug, not edge.

**DEMOTE per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` (mutate before kill):**
1. **FOREX** — 97% smart-pass rate, 44.3% WR, no proven cell, holdout fails. Mutate: raise `SMART_PICKS_MIN_SCORE_FOREX` to 60, add `MIN_CLOSED_FOR_SIZING=200`, re-run 90d. If WR still <50%, kill.
2. **BOND** — `passed_smart=0` but `opened=700`. This is a **funnel bypass bug**, not a strategy. Mutate: fix the bypass, re-run. If still 0 pass, kill the class.
3. **UNKNOWN** — quarantine, don't mutate. Route to `REJECT_UNKNOWN_CLASS`.

**The single highest-leverage fix is not a threshold — it's the funnel integrity bug.** Across CRYPTO (6,862 bypasses), BOND (700), UNKNOWN (1,234), and FOREX (23,272 opened vs 23,775 passed — actually consistent, but 97% pass is a no-op), the `opened` count is decoupled from `passed_smart`. Until `opened <= passed_smart` is enforced as an invariant, every "edge" number on this dashboard is contaminated by trades that never should have been opened. **Fix the invariant first, then re-run the 90-day funnel, then re-evaluate.** Any sizing decision made on the current numbers is sizing on a broken funnel.

**On the specific cells you flagged:** the FOREX `consensus` and CRYPTO `ml` cells are not in the top-3 lists provided, but the pattern of the cells that *are* listed (single-source, trust=UNK, LONG-only, train/holdout PF gap >2×) is the same pattern that produced H-001 (COT look-ahead) and H-036 (inventory direction). Treat any cell with PF>4 and n<200 in this dataset as a **leakage recurrence candidate** until proven otherwise — the base rate of real PF>4 edges in 90-day windows is near zero.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### CRYPTO
- Real/noise verdict: Real — n=182, WR_shrunk 76.24%, PF 4.358 with holdout_pass + bonferroni_pass; no obvious single-symbol flags in the cell.
- 90d expected P&L (1% risk, $100k): $2,900 (182 trades × ~1.6% avg edge after 0.15% slippage, 1% risk sizing).
- Gate change: SMART_PICKS_MIN_SCORE_CRYPTO = 50
- Confidence (1-5): 4

### EQUITY
- Real/noise verdict: Noise — PF 176 is statistically impossible without leakage or single-symbol concentration; treat as rejected.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: EQUITY_MIN_TRUST = 70
- Confidence (1-5): 5

### BOND
- Real/noise verdict: No edge — zero proven cells, n_closed=30 too small.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: BOND_MIN_WR_SHRUNK = 55
- Confidence (1-5): 5

### FOREX
- Real/noise verdict: No edge — all best_pf cells fail holdout_pass and bonferroni_pass.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: FOREX_MIN_CONF = 0.75
- Confidence (1-5): 5

### ETF
- Real/noise verdict: No edge — n_closed=10, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: ETF_MIN_WR_SHRUNK = 55
- Confidence (1-5): 5

### MEME
- Real/noise verdict: No edge — n_closed=8, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: MEME_MIN_WR_SHRUNK = 55
- Confidence (1-5): 5

### FUTURES
- Real/noise verdict: No edge — n_closed=16, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: FUTURES_MIN_WR_SHRUNK = 55
- Confidence (1-5): 5

### COMMODITY
- Real/noise verdict: No edge — zero proven cells; best_pf cells fail holdout and bonferroni.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: COMMODITY_MIN_WR_SHRUNK = 55
- Confidence (1-5): 5

### INDEX
- Real/noise verdict: No edge — n_closed=4, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: INDEX_MIN_WR_SHRUNK = 55
- Confidence (1-5): 5

### UNKNOWN
- Real/noise verdict: No edge — n_closed=3, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: UNKNOWN_MIN_WR_SHRUNK = 55
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale CRYPTO today (only class with verified, non-rejected edge). Demote EQUITY immediately per MUTATION_THREE_AXIS_PROTOCOL.md (high-PF cells are leakage recurrence). All other classes have no actionable edge — do not allocate.
