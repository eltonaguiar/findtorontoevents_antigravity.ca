# Pick Funnel Swarm Verdict — 2026-09-20 04:10 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260920T041006Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-day edge analysis

Before per-class verdicts, three system-wide red flags that color every number below:

1. **`passed_high_conviction = 0` in every single class.** The HC gate (`score>=80, conf>=0.75, trust>=60`) is dead code. Nothing in 90 days has cleared it. That means the "HIGH CONVICTION" label on the dashboard is currently a lie — either the thresholds are unreachable given upstream score distributions, or `trust>=60` is never satisfied (note every "proven" cell is `trust=UNK`).
2. **`opened` >> `passed_smart` in every class.** EQUITY: 5,009 opened vs 230 passed_smart. FOREX: 22,380 vs 22,806 (ok). CRYPTO: 10,111 vs 3,242. COMMODITY: 6,243 vs 3,769. The funnel is not actually gating opens — `opened` is tracking a different pipeline than `passed_smart`. Any "edge" claim downstream of `passed_smart` is suspect because the trades that actually opened did not all pass that gate.
3. **`trust=UNK` dominates every "proven" cell.** If trust is unknown, the trust dimension is not filtering anything — it's a null bucket masquerading as a dimension. Every "proven" cell that includes `trust=UNK` is really just the cell without trust.

---

### EQUITY
- **Real/noise verdict:** **NOISE / LEAKAGE.** The `fam=mean_reversion & score_dec=S40` cell shows WR=98.55% (68/69), PF=219.3, holdout PF=99.0. This is not an edge — this is a broken P&L accounting or a look-ahead in the mean-reversion exit logic. A 98.5% WR with PF 219 across 69 trades is physically impossible in liquid equity markets with realistic fills. The `conf=C<0.60` variant is the same 69 trades re-sliced (identical n, wins, PF) — the "edge" is one cell, not three. `trust=UNK` confirms no trust filter is active. Treat as a data-integrity bug, not a signal. Also note: 5,009 opened vs 191 closed — 96% of equity positions are still open, so the WR is computed on a tiny, likely non-random survivor subset.
- **90d expected P&L (1% risk, $100k):** **$0 — do not size this.** If forced to model the reported cell at face value: 69 trades × 1% × $100k = $69k risked; at PF 219 the "expected" return is absurd (~$15M), which is itself the proof it's broken. Realistic estimate after fixing the accounting bug: negative, because the underlying class WR is 66.5% on n=191 with 96% of positions unclosed.
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` — raise from current value to **≥ 70** and add a hard `trust != UNK` requirement in `hc_filter.js` (`trust >= 60` is already there but is being bypassed because trust is UNK, not <60). The real fix is upstream: make `trust` default to a low value, not `UNK`, so the HC gate actually fires.
- **Confidence (1-5):** **1**

---

### FOREX
- **Real/noise verdict:** **WEAK / PARTIALLY REAL, but the headline PF is inflated.** The `conf=C0.75-0.80 & rr=RR1.0-1.5 & fam=mean_reversion` cell: n=132, WR=68.2%, shrunk 65.8%, PF=2.97, holdout PF=1.34 (n=33). Holdout PF of 1.34 is the honest number — the train PF of 3.91 is overfit. Bonferroni passes, wr_z=4.18, so it's not pure noise, but the edge is roughly **half** what the headline suggests. The `dir=LONG` variant (n=46, PF=4.40) **fails Bonferroni** — do not trust it. The FOREX `consensus` cell you flagged isn't in this JSON, but the pattern here (train PF ~3× holdout PF) is the classic signature of the same problem: the model is fitting to a regime that didn't persist. Also: 22,380 opened vs 1,437 closed — 94% still open, so WR is on a 6% survivor slice.
- **90d expected P&L (1% risk, $100k):** Using the honest holdout PF of 1.34 on the proven cell: 132 trades × 1% × $100k = $132k risked. At PF 1.34, net edge ≈ 0.34 × $132k / (1+1.34) ≈ **$19k gross**, minus ~$3–5k slippage/spread on 132 FX round-trips (assume 0.5–1 pip on majors, 2–3 pips on crosses). **Net ≈ $14–16k over 90d.** But this assumes the 94% unclosed book resolves at the same WR — it won't. Haircut to **$5–8k** as a realistic forward estimate.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` — raise to **≥ 65** and add `rr >= 1.0` as a hard floor (the proven cell is entirely RR1.0–1.5; RR<1.0 is where the 49% class WR lives). In `hc_filter.js`, the `conf>=0.75` threshold is correct but is being diluted by `trust=UNK` — fix trust defaulting.
- **Confidence (1-5):** **3**

---

### CRYPTO
- **Real/noise verdict:** **REAL BUT NARROW — and the `ml` cell you flagged is not in this JSON, which is itself suspicious.** The proven cell `conf=C0.75-0.80 & score_dec=S50 & source=alpha_engine`: n=211, WR=76.3%, shrunk 74.0%, PF=4.00, train PF=3.89, holdout PF=4.34 (n=40). This is the **only cell in the entire report where holdout PF > train PF** — that's the opposite of overfitting and is genuinely encouraging. wr_z=7.64, Bonferroni passes. **However:** the cell is defined by `score_dec=S50` (a score decile) and `source=alpha_engine` — this is essentially "alpha_engine picks in the 0.75–0.80 confidence band." That's a strategy-family-level claim, not a market-structure edge, and it's vulnerable to alpha_engine's own model drift. The absence of the `ml` cell from this JSON means either it was filtered out (good) or the report is incomplete (bad). **Do not trust any CRYPTO `ml` cell with PF > 5 without a leakage audit** — ML cells in crypto are the #1 source of look-ahead via feature timestamps.
- **90d expected P&L (1% risk, $100k):** 211 trades × 1% × $100k = $211k risked. At PF 4.00, net edge ≈ 3.00 × $211k / 5.00 ≈ **$127k gross**. Crypto slippage is brutal: assume 10–20 bps round-trip on liquid majors, 50+ bps on alts. If the cell is mostly majors, ~$8–12k slippage; if alts, $25–40k. **Net ≈ $90–115k over 90d** on the proven cell alone. This is the one number in the report I'd actually underwrite — with the caveat that 10,111 opened vs 2,526 closed means 75% of the book is still open and the WR could regress.
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` — **lower** it (not raise) to capture more of the 0.75–0.80 conf band, but add a hard `source == 'alpha_engine'` filter and a `score_dec == S50` filter in `hc_filter.js`. The edge is concentrated; the gate should be *narrower on dimensions*, not *higher on score*. Also: fix `trust=UNK` defaulting so the HC gate can actually fire.
- **Confidence (1-5):** **4**

---

### COMMODITY
- **Real/noise verdict:** **NOISE.** No proven cells. Best PF cell is `rr=RR>=2.0 & score_dec=S50`: n=21, WR=76.2%, shrunk 63.4%, PF=5.62, **Bonferroni FAILS**, holdout n=11. n=21 with 11 holdout trades is not a sample — it's an anecdote. And this is the exact class where [H-001] (COT look-ahead) and [H-036] (inventory direction) were already killed. The `rr>=2.0` cell is likely the same cotton-concentration artifact from H-001 resurfacing under a different slice. **Flag as potential leakage recurrence.** Class WR is 44.0% on n=134 — below coin-flip.
- **90d expected P&L (1% risk, $100k):** **$0 — do not size.** At class WR 44% and PF < 1, expected P&L is negative. If you must model: 134 trades × 1% × $100k = $134k risked, at PF ~0.8 → **–$15k to –$25k**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` — **raise aggressively to ≥ 80** (effectively disable the class until the COT/inventory leakage is fully purged and re-validated). Per `MUTATION_THREE_AXIS_PROTOCOL.md`, this is a **demote-and-mutate** candidate, not a kill — the class has structural reasons to work (carry, roll yield) that the current signal set isn't capturing.
- **Confidence (1-5):** **1**

---

### FUTURES
- **Real/noise verdict:** **NOISE / INSUFFICIENT DATA.** n_closed=18. No proven cells. Class WR 38.9%. [H-005] already killed the momentum inversion. Nothing here is tradeable.
- **90d expected P&L (1% risk, $100k):** **$0.** n=18 is not a sample.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` — **raise to ≥ 85** (effectively off) until n_closed > 100. Do not mutate yet — you don't have enough data to know what to mutate.
- **Confidence (1-5):** **1**

---

### ETF
- **Real/noise verdict:** **NOISE.** n_closed=7, WR=14.3%. 325 opened, 7 closed. This is not a class — it's a rounding error.
- **90d expected P&L (1% risk, $100k):** **$0.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` — **raise to ≥ 85** (off) until n_closed > 50.
- **Confidence (1-5):** **1**

---

### UNKNOWN
- **Real/noise verdict:** **DATA-INTEGRITY BUG, not a class.** 1,424 scanned, 1,414 opened, 10 closed, 0 wins. The fact that `UNKNOWN` is a bucket at all means the asset-class classifier is failing on ~5% of the universe. Every `trust=UNK` cell in the proven lists is downstream of this bug.
- **90d expected P&L (1% risk, $100k):** **$0.**
- **Gate change:** Not a gate — fix the classifier in `production_scanner.py` so `UNKNOWN` is never emitted. Route unknowns to a quarantine queue, not to `opened`.
- **Confidence (1-5):** **5** (that this is a bug)

---

### BOND
- **Real/noise verdict:** **NOISE.** n_closed=25, WR=24.0%. No proven cells. 482 opened, 25 closed.
- **90d expected P&L (1% risk, $100k):** **$0.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` — **raise to ≥ 85** (off) until n_closed > 100.
- **Confidence (1-5):** **1**

---

### INDEX
- **Real/noise verdict:** **NOISE.** n_closed=7, WR=0.0%. 1,573 opened, 7 closed. Same as ETF.
- **90d expected P&L (1% risk, $100k):** **$0.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` — **raise to ≥ 85** (off) until n_closed > 50.
- **Confidence (1-5):** **1**

---

### MEME
- **Real/noise verdict:** **NOISE.** n_closed=4. Not a class.
- **90d expected P&L (1% risk, $100k):** **$0.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME` — **raise to ≥ 90** (off).
- **Confidence (1-5):** **1**

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY with real money: CRYPTO, and only CRYPTO, and only the `source=alpha_engine & conf=0.75-0.80 & score_dec=S50` cell.** It is the only cell in the entire report where holdout PF > train PF, Bonferroni passes, and n is large enough (211) to be a sample. Size at 0.5% risk per trade (not 1%) for the first 30 days because 75% of the crypto book is still open and the WR could regress. Expected 90d P&L on the proven cell: **$90–115k gross, ~$75–95k net** after realistic crypto slippage.

**Demote-and-mutate per `MUTATION_THREE_AXIS_PROTOCOL.md`: COMMODITY.** It has structural reasons to work (carry, roll yield, term structure) that the current signal set is not capturing, and it has already had two hypotheses killed (H-001, H-036). Do not kill it — mutate the signal axis (replace COT/inventory with term-structure slope and roll-yield sign) and re-test. Raise `SMART_PICKS_MIN_SCORE_COMMODITY` to ≥ 80 in the meantime.

**Kill outright: FUTURES, ETF, INDEX, MEME, BOND, UNKNOWN.** These are not classes — they are data-integrity artifacts or n<30 noise. Do not spend mutation budget on them.

**Fix before anything else: the `trust=UNK` default and the `passed_high_conviction=0` dead gate.** Every "proven" cell in this report is `trust=UNK`, which means the trust dimension is not filtering. The HC gate at `score>=80, conf>=0.75, trust>=60` has fired zero times in 90 days across 10 asset classes — that is not a strict gate, that is a broken gate. Until `trust` defaults to a real value (not `UNK`) and the HC gate actually fires, the dashboard's "HIGH CONVICTION" label is meaningless and the funnel's `passed_high_conviction` column is a constant zero.

**One more thing:** the `opened` vs `passed_smart` mismatch (EQUITY 5,009 vs 230; CRYPTO 10,111 vs 3,242) means the funnel is not actually gating opens. Whatever is writing to `opened` is bypassing `passed_smart`. Until that's reconciled, every WR number in this report is computed on a book that did not pass the gate it claims to have passed. That is the single highest-leverage fix in the entire system.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### EQUITY
- Real/noise verdict: Noise — PF=219 and 98.55% WR on n=69 screams single-symbol concentration or leakage; violates every realistic distribution.
- 90d expected P&L (1% risk, $100k): $0 (edge invalid; any sizing produces drawdown).
- Gate change: SMART_PICKS_MIN_SCORE_EQUITY = 75
- Confidence (1-5): 5

### FOREX
- Real/noise verdict: Marginal real on mean-reversion cells (n=132, WR_shrunk 65.8%, holdout PF 1.34 still >1); best_pf cells fail Bonferroni so ignore.
- 90d expected P&L (1% risk, $100k): ~$1,800 (132 trades × ~0.29% avg pnl at 1% risk, after 0.05% slippage).
- Gate change: HC_FILTER_MIN_CONF = 0.78
- Confidence (1-5): 3

### CRYPTO
- Real/noise verdict: Suspicious but passes holdout; PF=4.0 on n=211 with stable train/holdout split is unusually clean — treat as provisional only.
- 90d expected P&L (1% risk, $100k): ~$28,500 (211 trades × ~1.44% avg pnl at 1% risk, 0.1% slippage).
- Gate change: SMART_PICKS_MIN_SCORE_CRYPTO = 55
- Confidence (1-5): 2

### COMMODITY
- Real/noise verdict: Noise — no proven cells; best_pf cells fail Bonferroni and n=21 too small.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_COMMODITY = 80
- Confidence (1-5): 5

### FUTURES
- Real/noise verdict: No edge — n_closed=18, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_FUTURES = 90
- Confidence (1-5): 5

### ETF
- Real/noise verdict: No edge — n_closed=7, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_ETF = 85
- Confidence (1-5): 5

### INDEX
- Real/noise verdict: No edge — n_closed=4, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_INDEX = 85
- Confidence (1-5): 5

### BOND
- Real/noise verdict: No edge — n_closed=25, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_BOND = 85
- Confidence (1-5): 5

### UNKNOWN
- Real/noise verdict: No edge — n_closed=10, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_UNKNOWN = 90
- Confidence (1-5): 5

### MEME
- Real/noise verdict: No edge — n_closed=4, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_MEME = 90
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale up TODAY: none (CRYPTO is the only candidate with any statistical footprint but still too new to size).  
Demote per MUTATION_THREE_AXIS_PROTOCOL: EQUITY (clear leakage signature) and FUTURES/ETF/INDEX/BOND/UNKNOWN/MEME (zero signal, kill volume).
