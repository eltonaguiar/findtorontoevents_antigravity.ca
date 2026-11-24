# Pick Funnel Swarm Verdict — 2026-11-24 04:41 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20261124T044106Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-Day Edge Analysis

**TL;DR:** Only **CRYPTO** has a defensible, holdout-passing, Bonferroni-passing edge. **EQUITY** looks spectacular but is almost certainly a single-cell artifact (n=34, PF=120, holdout n=23) — treat as unproven until it survives a second 90-day window. **FOREX** has a real-looking regime cell that fails holdout (n=2). Everything else is noise or too thin to call. **Zero classes pass the HC gate** — that's the biggest structural finding.

---

### EQUITY
- **Real/noise verdict:** **NOISE / LEAKAGE-SUSPECT.** The three "PROVEN" cells are the *same 34 trades* re-sliced three ways (`trust=UNK & rr>=2 & mean_reversion` ≡ `rr>=2 & mean_reversion & LONG` ≡ `rr>=2 & mean_reversion & alpha_engine`). That's one cell, not three independent confirmations — the Bonferroni pass is inflated by treating them as separate tests. PF=120.6 with avg_pnl=1.58% and WR=97% is not a plausible trading edge; it's the signature of a **stop/target accounting bug** (e.g., wins booked at target, losses not booked, or a look-ahead on the mean-reversion entry). Holdout n=23 with PF=99 is *not* independent validation — it's the same 34 trades split 11/23. **Flag as leakage recurrence candidate** (similar shape to H-001: tiny n, single family, implausible PF). Also note: `opened=6008` vs `scanned=6207` vs `passed_smart=222` — the funnel is inverted; 97% of scanned names are "opened" despite only 3.6% passing Smart. That's a logging bug, not a strategy.
- **90d expected P&L (1% risk, $100k):** **$0.** Do not size this. If forced to model the cell at face value: 34 trades × 1% × 1.58% avg = **~$537** — but the number is meaningless given the accounting suspicion. Realistic expectation after fixing the bug: **negative to flat**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` — raise from current to **~85** and add a hard `n_closed >= 100` requirement before any cell is promoted to PROVEN. The current 222/6207 (3.6%) pass rate is fine; the problem is downstream promotion logic, not the floor.
- **Confidence (1-5):** **1**

---

### CRYPTO
- **Real/noise verdict:** **REAL (with caveats).** This is the only class where the PROVEN cell is defensible: `trust=UNK & conf=0.75–0.80 & source=alpha_engine`, n=188, WR_shrunk=62.98%, PF=1.80, **holdout n=79 with holdout PF=2.15**, wr_z=3.94, Bonferroni pass. The three "cells" are again the same 188 trades re-sliced (trust/conf/source vs conf/dir/source vs trust/conf/dir/source) — so it's **one** edge, not three. But one edge with n=188 and a genuine 79-trade holdout is credible. **Caveat:** the edge lives at conf 0.75–0.80, *below* the HC gate's 0.75 floor — meaning the HC gate is filtering *out* the only proven crypto edge. That's a gate-design bug, not a market finding. The `ml` cell you flagged isn't in the PROVEN list — good, because PF>10 on ml cells is almost always leakage; if it appears in a future run, kill it on sight.
- **90d expected P&L (1% risk, $100k):** 188 trades × 1% risk × avg_pnl 0.64% = **~$1,203 gross**. Apply 15% slippage/fee haircut on crypto (taker fees + funding): **~$1,020 net**. At 2% risk sizing (still within Kelly for a 63% WR / 1.8 PF edge): **~$2,040 net**. This is the number I'd actually underwrite.
- **Gate change:** `HC_MIN_CONFIDENCE` in `hc_filter.js` — **lower from 0.75 to 0.70** *for CRYPTO only*, OR add a class-conditional override so the 0.75–0.80 band isn't excluded. Currently the HC gate is anti-correlated with the proven edge. Also: `SMART_PICKS_MIN_SCORE_CRYPTO` is clearly too loose (4383/12195 = 36% pass) — tighten to **~75** to cut the 44.6% WR tail.
- **Confidence (1-5):** **4**

---

### COMMODITY
- **Real/noise verdict:** **NOISE.** n_closed=50, no PROVEN cells. Best cell (`trust=UNK & rr>=2 & LONG`) has n=27, WR_shrunk=57.45%, PF=3.53, but **bonferroni_pass=false** and wr_z=1.35 — that's a 1-in-6 fluke, not an edge. Holdout n=15 is too small to confirm. **Critically:** this is the same shape as **H-001 (COT leakage)** — `trust=UNK` + `rr>=2` + LONG + alpha_engine, tiny n, PF>3. The registry says COT was fixed and killed; if this cell is the post-fix residue, it's still noise. Do not re-promote.
- **90d expected P&L (1% risk, $100k):** **$0.** 27 trades × 1% × 1.18% = ~$318 at face value, but bonferroni-fail means expected value is ~0 after multiple-testing correction.
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` — raise to **~80** (currently 3668/5683 = 65% pass, absurdly loose). Also add a `MIN_CLOSED_FOR_PROMOTION = 100` global constant; COMMODITY at n=50 should never surface a "best cell."
- **Confidence (1-5):** **1**

---

### BOND
- **Real/noise verdict:** **NO EDGE.** n_closed=31, WR=38.7%, PF<1 implied. `passed_smart=1` out of 1255 scanned — the Smart gate is correctly rejecting bonds, but `opened=1224` means the funnel is bypassing the gate entirely. This is a **funnel integrity bug**, not a strategy question.
- **90d expected P&L (1% risk, $100k):** **Negative.** 31 trades × 1% × (negative expectancy) ≈ **–$150 to –$300**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` — the issue isn't the threshold, it's that `opened` (1224) >> `passed_smart` (1). Fix the funnel so `opened ⊆ passed_smart`. If that's not a bug, **disable BOND entirely** until the funnel is repaired.
- **Confidence (1-5):** **1**

---

### PREDICTION_MARKET
- **Real/noise verdict:** **INSUFFICIENT DATA.** n_closed=0. 242 scanned, 18 passed smart, 0 closed. Cannot evaluate. Do not size.
- **90d expected P&L (1% risk, $100k):** **$0** (no closed trades).
- **Gate change:** None yet — need resolution data. Add a `MIN_CLOSED_FOR_EVAL = 30` gate before PM appears on the dashboard at all.
- **Confidence (1-5):** **1**

---

### FOREX
- **Real/noise verdict:** **NOISE (holdout-fail).** The `trust=UNK & conf>=0.90 & regime` cell has n=39, WR_shrunk=74.58%, PF=11.5, wr_z=4.64, bonferroni_pass=true — **but holdout n=2, holdout PF=1.18, holdout_pass=false.** That's the textbook definition of in-sample overfit: 37 train trades, 2 holdout trades. The PF=11.5 is driven by a handful of regime_terminal trades. **Do not size.** Also: `passed_smart=26455/26994 = 98%` — the Smart gate is a no-op for FOREX. That's the real problem: 25,661 opened, 1,333 closed, WR 49.2% — a coin flip with fees.
- **90d expected P&L (1% risk, $100k):** **~$0 to slightly negative.** 498 decisive × 1% × ~0% edge − fees ≈ **–$200 to –$500**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` — raise from current (effectively 0) to **~70**. A 98% pass rate is not a gate. This single change would cut ~20k low-quality opens and is the highest-leverage fix in the whole system.
- **Confidence (1-5):** **1**

---

### ETF
- **Real/noise verdict:** **NOISE.** n_closed=11. WR=36.4%. No cells. Too thin.
- **90d expected P&L (1% risk, $100k):** **Negative**, ~**–$50** (11 trades, sub-40% WR).
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` — raise to **~80**; 265/301 = 88% pass is not a gate.
- **Confidence (1-5):** **1**

---

### FUTURES
- **Real/noise verdict:** **NOISE.** n_closed=16, WR=37.5%. No cells. Note **H-005** already killed futures_momentum inversion — do not re-derive.
- **90d expected P&L (1% risk, $100k):** **Negative**, ~**–$80**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` — raise to **~80**; 107/151 = 71% pass is too loose.
- **Confidence (1-5):** **1**

---

### INDEX
- **Real/noise verdict:** **NO DATA.** n_closed=1. WR=100% on n=1 is meaningless. 2140 opened, 1 closed — the funnel is broken for INDEX (positions aren't resolving).
- **90d expected P&L (1% risk, $100k):** **$0** (n=1).
- **Gate change:** Fix resolution pipeline before any gate change. `SMART_PICKS_MIN_SCORE_INDEX` is irrelevant until trades close.
- **Confidence (1-5):** **1**

---

### UNKNOWN
- **Real/noise verdict:** **NOISE / DATA HYGIENE FAILURE.** n_closed=5, WR=0%. 1193 scanned, 1188 opened — 99.6% of "unknown" names are being opened. This is a **classification bug**, not a strategy. Kill the UNKNOWN bucket at ingestion.
- **90d expected P&L (1% risk, $100k):** **–$50** (5 losses × 1%).
- **Gate change:** Add `REJECT_UNKNOWN_CLASS = True` in `quality_gates.py` — drop at scan time, don't let it reach the funnel.
- **Confidence (1-5):** **1**

---

### MEME
- **Real/noise verdict:** **NOISE.** n_closed=5. WR=40%. Too thin. 12 scanned, 7 opened — sample is meaningless.
- **90d expected P&L (1% risk, $100k):** **–$30**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME` — raise to **~85** or disable until n_closed>=30.
- **Confidence (1-5):** **1**

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY: CRYPTO only.** It is the sole class with a holdout-passing, Bonferroni-passing, n>=100 edge (`conf 0.75–0.80 & alpha_engine`, n=188, holdout PF=2.15). Size at **1% risk per trade, $100k notional → ~$1,000–$2,000 expected 90d P&L net of fees.** Do not exceed 2% risk until a second 90-day window confirms. **Immediate gate fix:** lower `HC_MIN_CONFIDENCE` to 0.70 for CRYPTO — the current 0.75 floor is *excluding* the only proven edge, which is the single most expensive bug in the system.

**DEMOTE per MUTATION_THREE_AXIS_PROTOCOL (mutate before kill):**
1. **FOREX** — 98% Smart pass rate is a no-op; mutate `SMART_PICKS_MIN_SCORE_FOREX` to ~70 and re-run 30d. If WR doesn't lift above 52%, kill.
2. **COMMODITY** — mutate `SMART_PICKS_MIN_SCORE_COMMODITY` to ~80; the current 65% pass rate is letting H-001-shaped noise through. If no cell survives with n>=100 and bonferroni_pass=true, kill.
3. **EQUITY** — **do not scale, do not kill yet.** The PF=120 cell is a leakage/accounting suspect (same 34 trades re-sliced 3×, holdout is not independent). Mutate by adding a `MIN_CLOSED_FOR_PROMOTION=100` and a `MAX_PF_SANITY=10` guard; if the cell survives both, it's real. If it collapses, it was a bug — and that's the most valuable finding of this audit.

**Structural finding (applies to all classes):** `opened` >> `passed_smart` in EQUITY (6008 vs 222), BOND (1224 vs 1), INDEX (2140 vs 1542), UNKNOWN (1188 vs 98). The funnel is **bypassing the Smart gate at the open step**. No gate change matters until `opened ⊆ passed_smart` is enforced. This is the #1 fix before any capital is deployed beyond the CRYPTO cell.

**Do not invent edges:** COMMODITY, BOND, ETF, FUTURES, INDEX, UNKNOWN, MEME, PREDICTION_MARKET have **no demonstrable edge** in this 90-day window. Say so on the dashboard.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)
