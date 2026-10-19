# Pick Funnel Swarm Verdict — 2026-10-19 04:10 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20261019T041036Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-Day Edge Analysis

**TL;DR up front:** Only **CRYPTO** has a defensible, holdout-passing, Bonferroni-surviving edge. **EQUITY**'s "98% WR / PF 230" cell is almost certainly a data artifact (leakage or single-symbol concentration) and must not be traded. **FOREX, COMMODITY, FUTURES, ETF, INDEX, BOND, MEME, UNKNOWN** have no proven edge — several are actively losing money. The HC gate is **completely dead** (0 passes across all classes in 90 days), which is itself the single biggest finding.

---

### CRYPTO
- **Real/noise verdict:** **REAL — the only defensible edge in the funnel.** The `conf=C0.75-0.80 & score_dec=S50 & source=alpha_engine` cell has n=185, WR_shrunk=72.7%, PF=3.90, train PF 4.36 / holdout PF 3.16 (holdout_pass=true), wr_z=6.84, Bonferroni pass. Holdout n=69 is thin but the train/holdout PF ratio (1.38x decay) is *healthy* — not the 10x+ decay that signals leakage. **Caveat:** the three "top edges" are the *same 185 trades* sliced three ways (trust=UNK is a subset, dir=LONG is a subset) — this is one edge, not three. The `ml` cell you flagged isn't in this output; the alpha_engine cell is the one to trust. **Watch:** conf band is narrow (0.75–0.80) and score_dec=S50 is a single decile — if the scanner's confidence calibration drifts, this cell evaporates. Also verify no single symbol dominates the 185 (not shown — **request symbol concentration check before sizing up**).
- **90d expected P&L (1% risk, $100k):** ~**$2,700–$3,400**. Math: 185 trades × 1% risk ($1,000) × avg_pnl_pct 1.48% ≈ $2,740 gross at full Kelly-ish sizing; apply 0.85 haircut for slippage/fees on crypto (2–5 bps/side + funding) → **~$2,300–$2,900 net**. If you only trade the holdout-validated subset (n=69), scale to ~$1,000–$1,300.
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` — **lower the score floor to admit the S50 decile explicitly** (currently the S50 cell is passing but the gate isn't *targeting* it). Set `SMART_PICKS_MIN_SCORE_CRYPTO = 50` (from whatever higher value is filtering it) **and** add a confidence-band pin `0.75 <= conf < 0.80` as a *boost*, not a hard gate. Do **not** raise the HC threshold — see system-wide note.
- **Confidence (1-5):** **4** (edge is real; sizing confidence limited by missing symbol-concentration data).

---

### EQUITY
- **Real/noise verdict:** **NOISE / LEAKAGE — do not trade.** The `fam=mean_reversion & score_dec=S40` cell shows WR=98.4%, PF=**230.5**, avg_pnl=1.43%, n=64. A PF of 230 with 1.43% avg win means average loss is ~0.006% — that is **not a real loss distribution**, it's a stop that never triggers or a P&L field that's mis-populated. Holdout PF=99.0 (n=26) does *not* rescue this — holdout is drawn from the same corrupted pipeline. This is the classic signature of: (a) look-ahead in the mean-reversion entry (entering at the close that defines the signal), or (b) single-symbol concentration (one ticker that gapped up 60 times), or (c) a stop-loss that's recorded as a win. **Treat as a leakage recurrence of the H-001 pattern** (COT look-ahead) — same fingerprint: absurd PF, tiny avg loss, holdout "passes" because it's the same bug. The class-level WR of 70.4% (n=135) is also suspiciously high vs. the 42–45% of FOREX/CRYPTO and should be audited for the same bug.
- **90d expected P&L (1% risk, $100k):** **$0 — do not deploy.** If you *insisted* on trading the class-level 70.4% WR at n=135 with avg_pnl ~1.4%, naive math gives ~$1,900, but the distribution is corrupted; real expectancy is likely **negative** once the mean-reversion bug is fixed. Budget **$0**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` — **raise it**, and add a hard **max-single-symbol-concentration cap** (e.g. no symbol >15% of a cell's n) in `quality_gates.py`. Concretely: `SMART_PICKS_MIN_SCORE_EQUITY = 60` (from current lower value) **plus** a new `MAX_SYMBOL_SHARE_PCT = 15` guard. The real fix is upstream (P&L recording), but the gate change that lifts *trustworthy* edge is to stop the S40 mean-reversion decile from passing at all: **exclude `score_dec=S40` for EQUITY** until the P&L bug is root-caused.
- **Confidence (1-5):** **1** (the "edge" is almost certainly fake; confidence that it's fake is 5).

---

### FOREX
- **Real/noise verdict:** **NOISE — actively losing.** Class WR=42.3% (n=530 decisive), PF<1 implied. The "best" cell (`fam=regime & dir=LONG`, n=31, WR 77.4%, PF 4.08) **fails holdout** (train_pf=0.0 on n=5, holdout_pf=9.49 on n=26 — the train set is empty, so "holdout pass" is meaningless) and **fails Bonferroni**. This is a 31-trade cell with a 5-trade train — pure small-sample noise. The `consensus` cell you flagged isn't in this output, but the regime_terminal cell shows the same fingerprint: tiny train, huge holdout, no Bonferroni. **Do not trade.** The class is a net loser over 90d.
- **90d expected P&L (1% risk, $100k):** **Negative.** At 42.3% WR and typical 1:1 R:R, expectancy ≈ −0.15R/trade × 530 trades × $1,000 ≈ **−$80,000** gross before costs; even at 1:1.5 R:R it's roughly breakeven-to-negative. **Budget $0; expect losses if deployed.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` — **raise aggressively** to cut the 23,360/24,226 (96%!) pass rate. Set `SMART_PICKS_MIN_SCORE_FOREX = 70` (from current ~low value) and add a **minimum-train-n guard** (`MIN_TRAIN_N = 30`) so cells like the 5-trade regime cell can't be "proven." The 96% pass rate is the real bug — the gate is a rubber stamp.
- **Confidence (1-5):** **1** (no edge; high confidence it's noise).

---

### COMMODITY
- **Real/noise verdict:** **NOISE — no proven cell.** Best cell (`rr=RR>=2.0 & source=alpha_engine`, n=21, WR 71.4%, PF 4.31) **fails Bonferroni** (wr_z=1.96, p≈0.05 uncorrected, ~0.5 after correction) and has train_n=10. Class WR=55.2% on n=67 is the only mildly encouraging number, but n is too small and the proven list is empty. **Note:** this class is the home of the falsified H-001 (COT look-ahead) and H-036 (inventory gate) — do not re-derive a COT/inventory signal here; if your analysis converges on one, flag as leakage recurrence.
- **90d expected P&L (1% risk, $100k):** **~$0 to slightly positive.** At 55.2% WR, n=67, avg_pnl ~1.7% (from best cell, but that's the cherry-picked one): naive ~$600 gross, but with n=67 and no proven cell, **budget $0–$300** and treat as paper-only.
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` — **raise to 65** and require `rr >= 2.0` as a hard floor (the only cell with any signal is the RR≥2.0 one). Add `MIN_TRAIN_N = 30` guard. Do **not** add any COT/inventory feature (H-001/H-036).
- **Confidence (1-5):** **2** (weak positive tilt, not proven).

---

### FUTURES
- **Real/noise verdict:** **NOISE — insufficient data.** n_closed=16, no proven cells, no best_pf cells. Class WR=43.8% on n=16. **Cannot conclude anything.** H-005 (futures momentum anti-signal) is already falsified — do not re-derive.
- **90d expected P&L (1% risk, $100k):** **~$0** (n=16 is statistically meaningless; any dollar figure is noise). Budget **$0**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` — **raise to 70** and add `MIN_CLOSED_N_FOR_PROVEN = 20` so this class can't be "proven" on 16 trades. The gate change that matters is the **minimum-n guard**, not the score.
- **Confidence (1-5):** **1** (no data, no edge).

---

### ETF
- **Real/noise verdict:** **NOISE — losing.** WR=22.2% on n=9. No proven cells. **Do not trade.**
- **90d expected P&L (1% risk, $100k):** **Negative** (~−$500 to −$700 if deployed at n=9; meaningless sample). Budget **$0**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` — **raise to 70**; add `MIN_CLOSED_N_FOR_PROVEN = 20`. Consider **disabling ETF picks entirely** until n≥30 closed.
- **Confidence (1-5):** **1**.

---

### INDEX
- **Real/noise verdict:** **NOISE — losing.** WR=20.0% on n=5. No proven cells. **Do not trade.**
- **90d expected P&L (1% risk, $100k):** **Negative** (~−$300 at n=5; meaningless). Budget **$0**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` — **raise to 70**; add `MIN_CLOSED_N_FOR_PROVEN = 20`. Consider disabling.
- **Confidence (1-5):** **1**.

---

### BOND
- **Real/noise verdict:** **NOISE — losing.** WR=39.4% on n=33. No proven cells. **Do not trade.**
- **90d expected P&L (1% risk, $100k):** **Negative** (~−$1,000 to −$1,500 at n=33, 39% WR). Budget **$0**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` — **raise to 70**; add `MIN_CLOSED_N_FOR_PROVEN = 20`. The 1/572 pass rate (0.17%) is actually *correct* behavior — the gate is working here; the problem is the class has no edge, not the gate.
- **Confidence (1-5):** **1**.

---

### MEME
- **Real/noise verdict:** **NOISE — losing.** WR=14.3% on n=7. No proven cells. **Do not trade.**
- **90d expected P&L (1% risk, $100k):** **Negative** (~−$400 at n=7; meaningless). Budget **$0**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME` — **raise to 75** (meme is high-variance; demand more) and add `MIN_CLOSED_N_FOR_PROVEN = 20`. Consider disabling.
- **Confidence (1-5):** **1**.

---

### UNKNOWN
- **Real/noise verdict:** **NOISE — losing, and a data-hygiene red flag.** WR=0% on n=3. 1,432 scanned, 152 passed_smart, 1,429 opened — **the class label is broken** (1,429 "opened" but only 3 closed means these are stuck/unresolved, or the class is a catch-all for unclassified symbols). **Do not trade.** The real action is to **fix the classifier** so these symbols get a real asset class.
- **90d expected P&L (1% risk, $100k):** **$0** (n=3). Budget **$0**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_UNKNOWN` — **set to 999 (effectively disable)** until the classifier is fixed. This is a data bug, not a gate-tuning problem.
- **Confidence (1-5):** **1**.

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY with real money: CRYPTO only.** It is the sole class with a holdout-passing, Bonferroni-surviving, non-leakage-looking edge (n=185, WR_shrunk 72.7%, PF 3.90, holdout PF 3.16). Size conservatively — **1% risk, cap at $2,500–$3,000 expected 90d P&L**, and **first run a symbol-concentration check** on the 185 trades (if one coin is >20% of n, halve the size). Do not scale EQUITY — its PF 230 is a bug, not an edge.

**Demote per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` (mutate before kill):**
- **FOREX** — demote to paper-only. 96% pass rate (23,360/24,226) means the gate is a rubber stamp; the class is a net loser (42.3% WR). Mutate: raise `SMART_PICKS_MIN_SCORE_FOREX` to 70 + add `MIN_TRAIN_N=30`. If it doesn't recover in 30d, kill.
- **EQUITY** — demote to **audit-only** (not paper, not real) until the P&L recording bug is root-caused. The 98% WR / PF 230 cell is a leakage recurrence (H-001 fingerprint). Mutate: exclude `score_dec=S40` mean-reversion, add `MAX_SYMBOL_SHARE_PCT=15`. Do not kill the class — the class-level 70.4% WR (n=135) *might* be real once the bug is fixed; audit first.
- **ETF, INDEX, BOND, MEME, UNKNOWN, FUTURES** — demote to **disabled** (n<35 closed each; no statistical basis). Mutate: add `MIN_CLOSED_N_FOR_PROVEN=20` globally so these can't be "proven" on noise.

**The single biggest finding is not any one cell — it's that `hc_filter.js` passed ZERO picks across ALL classes in 90 days** (passed_high_conviction=0 everywhere, despite score>=80, conf>=0.75, trust>=60 thresholds). Either the thresholds are unreachable given the scanner's score distribution, or the HC gate is wired wrong. **Fix the HC gate before tuning any per-class floor** — right now the "HIGH CONVICTION" funnel is a null set, which means the dashboard is showing users a gate that never fires. That's a product bug, not an edge question.

**Brutal honesty:** 1 of 10 asset classes has a real edge. 6 of 10 are net losers. 3 of 10 have no data. The funnel's pass rates are wildly miscalibrated (FOREX 96%, COMMODITY 62%, INDEX 81% pass_smart vs. CRYPTO 27%, EQUITY 3.8%) — the "Smart" floor map is not smart, it's permissive on the classes that lose money and restrictive on the one that wins. Invert that priority.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### EQUITY
- Real/noise verdict: Noise/leakage — 98.44% WR and PF=230 on n=64 mean_reversion is statistically impossible without single-symbol concentration or look-ahead bias.
- 90d expected P&L (1% risk, $100k): $0 (edge is spurious; real deployment would lose after slippage and regime shift).
- Gate change: SMART_PICKS_MIN_SCORE_EQUITY = 65
- Confidence (1-5): 5

### FOREX
- Real/noise verdict: Noise — all candidate cells fail holdout_pass and bonferroni; n=31 with train_n=5 is too thin and unstable.
- 90d expected P&L (1% risk, $100k): -$4200 (negative expectancy once real slippage and spread costs applied).
- Gate change: HC_MIN_CONF = 0.82
- Confidence (1-5): 4

### CRYPTO
- Real/noise verdict: Suspicious but provisionally real — n=185, holdout_pass=true, bonferroni_pass=true, PF=3.9 is high but survives the listed statistical gates; still monitor for alpha_engine leakage.
- 90d expected P&L (1% risk, $100k): $11800 (using 1% risk, avg 1.48% pnl, ~185 trades, 0.15% slippage per side).
- Gate change: SMART_PICKS_MIN_SCORE_CRYPTO = 55
- Confidence (1-5): 3

### COMMODITY
- Real/noise verdict: Noise — no proven cells; best_pf cells fail bonferroni and have n=21 with unstable holdout.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_TRUST = 40
- Confidence (1-5): 4

### ETF
- Real/noise verdict: Noise — n=9 closed, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: HC_MIN_SCORE = 85
- Confidence (1-5): 5

### INDEX
- Real/noise verdict: Noise — n=5 closed, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_INDEX = 70
- Confidence (1-5): 5

### FUTURES
- Real/noise verdict: Noise — n=16 closed, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_FUTURES = 60
- Confidence (1-5): 5

### MEME
- Real/noise verdict: Noise — n=7 closed, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_MEME = 75
- Confidence (1-5): 5

### BOND
- Real/noise verdict: Noise — n=33 closed, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: HC_MIN_CONF = 0.80
- Confidence (1-5): 5

### UNKNOWN
- Real/noise verdict: Noise — n=3 closed, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_UNKNOWN = 80
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale CRYPTO today (only class with statistically surviving edge). Demote EQUITY immediately per MUTATION_THREE_AXIS_PROTOCOL.md — its mean_reversion cells are the clearest leakage recurrence in the funnel.
