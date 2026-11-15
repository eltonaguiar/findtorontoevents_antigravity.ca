# Pick Funnel Swarm Verdict — 2026-11-15 04:06 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20261115T040634Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-Day Edge Analysis

Before per-class verdicts, three structural facts dominate everything below:

1. **`passed_high_conviction = 0` for every single class.** The HC gate (`score>=80, conf>=0.75, trust>=60`) is dead code on this data. Nothing has ever cleared it. That's the single biggest finding in the funnel.
2. **`opened` >> `passed_smart` in most classes** (CRYPTO 9808 opened vs 3615 smart; FOREX 24884 vs 25518; EQUITY 5708 vs 227; BOND 1149 vs 1). The "smart" gate is not actually gating opens — the funnel is leaking. Either `opened` counts pre-gate signals or the gate is bypassed downstream. This is a data-integrity bug, not an edge question.
3. **`trust=UNK` dominates every "PROVEN" cell.** Every single proven cell across EQUITY, FOREX, and the best CRYPTO cell is `trust=UNK`. That means the trust dimension is not populated for the trades that are winning — which is either (a) a scoring bug where trust is never computed for `alpha_engine`/`regime_terminal` sources, or (b) the "proven" cells are actually "unclassified" cells that happen to be the bulk of volume. Either way, "PROVEN" here is not a trust-validated edge; it's a source-validated edge with trust missing.

---

### CRYPTO
- **Real/noise verdict:** **NOISE / not proven.** `top_edges_proven` is empty. The best cell (`trust=UNK & rr=RR1.5-2.0 & source=alpha_engine`, n=197, WR 59.4%, shrunk 58.5%, PF 2.02) fails Bonferroni (`bonferroni_pass: false`) and its holdout PF collapses from train 2.50 → holdout 1.26. That's a classic overfit signature: the train window is doing the work. `wr_z=2.64` is not survivable across the ~dozens of cells scanned. The `ml` cell you flagged isn't even in the top-3 here — the top cells are all `alpha_engine` RR1.5-2.0 LONG. No leakage flag needed because there's no edge to leak. Overall class WR 44.67% on n=2279 decisive is a **losing class**.
- **90d expected P&L (1% risk, $100k):** **−$2,300 to −$4,600.** At 44.67% WR with typical RR ~1.5-2.0, expectancy per trade is roughly −0.1% to −0.2% of notional; 2293 closed × 1% risk × negative edge ≈ **−$2.3k to −$4.6k** net of costs. If you'd only traded the "best" cell (n=197, PF 2.02, avg +1.13%), gross ≈ +$2.2k, but after 0.1% round-trip slippage on 197 trades ≈ −$200, and the holdout PF 1.26 says the live number is closer to +$500. **Do not size this.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` — raise it. The current smart gate passes 3615/12101 = 30% of scans, which is far too permissive for a class with 44.67% WR. Set to a value that cuts pass rate to ~10% (roughly the top decile of score). If the constant is currently 50, set to **65**. Also: `hc_filter.js` `HC_MIN_TRUST` is unreachable because trust is UNK — fix trust population first, or the HC gate stays at 0 forever.
- **Confidence (1-5):** **1**

### COMMODITY
- **Real/noise verdict:** **NOISE.** `top_edges_proven` empty. Best cell n=27, holdout PF 1.14 (train 3.75) — holdout fails. Second cell holdout PF 0.65. Third cell holdout PF 0.65. Every "best" cell has `holdout_pass: false`. The 69.44% class WR is on **n=36 closed** — that's not a sample, that's an anecdote. Note H-001 (COT leakage) and H-036 (inventory gate) are both formally killed; do not re-derive. The `trust=UNK & dir=LONG & source=alpha_engine` cell is the same shape as the killed COT cell (LONG, alpha_engine, UNK trust) — **flag as potential leakage recurrence** and do not promote.
- **90d expected P&L (1% risk, $100k):** **$0 — do not trade.** n=36 is below any reasonable minimum. If forced: 36 trades × 1% × (+0.8% avg) ≈ **+$290 gross**, minus slippage ≈ **+$200**, with a confidence interval that spans negative. Not actionable.
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` — the smart gate passes 3708/5826 = **64%** of scans. That's not a gate, that's a pass-through. Raise to cut to ~15% pass rate. If currently 50, set to **70**. Also add a hard `MIN_CLOSED_TRADES_FOR_PROMOTION = 100` before any cell can be labeled PROVEN.
- **Confidence (1-5):** **1**

### FOREX
- **Real/noise verdict:** **SUSPICIOUS — likely leakage or single-source concentration.** The `regime` / `regime_terminal` cell (n=38, WR 89.47%, shrunk 75.86%, PF **14.45**, holdout PF **99.0**) is the cell you flagged and you're right to. PF 14.45 with holdout PF 99.0 on n=10 holdout is not a real edge — it's either (a) a single-symbol or single-regime concentration (38 trades is ~1 trade per 2.4 days, plausibly one pair), (b) a look-ahead in `regime_terminal` labeling (regime assigned after the fact), or (c) a P&L calculation bug where losers are being dropped. `bonferroni_pass: true` is meaningless when the underlying data is contaminated. **Do not trade this cell.** The class-level 51.61% WR on n=436 is a coin flip — that's the real FOREX number.
- **90d expected P&L (1% risk, $100k):** **≈ $0 to −$500.** 51.61% WR at ~1:1 RR is breakeven minus costs. 436 trades × 1% × ~0% edge − slippage ≈ **−$400 to −$900**. The "proven" cell would imply +$2.6k gross if real, but it isn't real.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` — smart gate passes **25518/26187 = 97.4%** of scans. This is the worst gate in the system. It is not filtering anything. Raise to cut to ~20% pass rate. If currently 50, set to **72**. Separately, add a `REGIME_TERMINAL_LOOKAHEAD_GUARD` that rejects any trade where regime label timestamp > entry timestamp — this is the specific leakage vector.
- **Confidence (1-5):** **1** (on the "proven" cell); **3** on "class is a coin flip"

### EQUITY
- **Real/noise verdict:** **LEAKAGE — do not trade.** The `mean_reversion` / RR>=2.0 cell (n=37, WR **97.3%**, shrunk 80.7%, PF **131.9**, holdout PF **99.0**) is not a real edge. 36/37 wins with PF 132 is the signature of either (a) look-ahead in the mean-reversion entry (entering after the reversion has already happened), (b) a P&L bug where losing trades are excluded from the cell, or (c) single-symbol concentration (37 trades over 90d ≈ 1 per 2.4 days — plausibly one ticker). `bonferroni_pass: true` is again meaningless on contaminated data. The class-level 72.38% WR on n=105 is also suspiciously high for equity mean-reversion and should be audited for the same leakage. **This is the most dangerous cell in the report because it looks the most real.**
- **90d expected P&L (1% risk, $100k):** **$0 — do not trade until leakage audit passes.** If the cell were real: 37 × 1% × 1.59% avg ≈ **+$590 gross**. But PF 132 is not real; the honest number is unknown and likely negative after the leakage is fixed.
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` — smart gate passes **227/5813 = 3.9%**, which is actually the tightest gate in the system. The problem here is not the gate, it's the **cell-level leakage**. Add a `MEAN_REVERSION_ENTRY_TIMESTAMP_AUDIT` that rejects any trade where the reversion signal is computed on a bar that closes after entry. Do not loosen the gate.
- **Confidence (1-5):** **1** (on the cell); **2** on "class has any edge"

### INDEX
- **Real/noise verdict:** **NO DATA.** n_closed = 1. 100% WR on one trade is not a statistic. `passed_smart` 1633/2132 = 76.6% pass rate is again a pass-through gate. No edge claim possible.
- **90d expected P&L (1% risk, $100k):** **$0 — insufficient data.** One trade × 1% × unknown ≈ **±$100**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` — raise to cut pass rate from 76.6% to ~20%. If currently 50, set to **70**. Also add `MIN_CLOSED_TRADES_FOR_CLASS_PROMOTION = 30` so INDEX can't be reported as a class until it has data.
- **Confidence (1-5):** **1**

### ETF
- **Real/noise verdict:** **NOISE / negative edge.** 9.09% WR on n=11. That's not noise, that's a broken signal — 1 win in 11. Either the ETF strategy is inverted or the P&L sign is flipped. `passed_smart` 278/321 = 86.6% pass rate. No proven cells.
- **90d expected P&L (1% risk, $100k):** **−$800 to −$1,000.** 11 trades × 1% × (−9% edge) ≈ **−$1k**. Small n, but the direction is unambiguous.
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` — raise from current to cut pass rate from 86.6% to ~10%. If currently 50, set to **75**. Also flag ETF for **inversion audit** — 9% WR suggests the signal is anti-correlated with outcome.
- **Confidence (1-5):** **2** (small n, but direction is clear)

### BOND
- **Real/noise verdict:** **NOISE / negative edge.** 38.71% WR on n=31. `passed_smart` = **1/1180 = 0.08%** — the gate is essentially closed, yet 1149 trades opened. This is the clearest evidence of the funnel leak: the smart gate rejects 99.9% of BOND scans but 97% of them still get opened. Either `opened` is pre-gate or the gate is bypassed. No proven cells.
- **90d expected P&L (1% risk, $100k):** **−$600 to −$900.** 31 trades × 1% × (−0.5% to −0.8% edge) ≈ **−$700**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` is already effectively infinite (1 pass). The real fix is **`OPENED_TRADES_MUST_PASS_SMART_GATE = True`** — enforce that `opened` ⊆ `passed_smart`. This is a funnel-integrity fix, not a threshold change.
- **Confidence (1-5):** **2**

### UNKNOWN
- **Real/noise verdict:** **NOISE / broken classification.** 0% WR on n=3. 1300 scanned, 116 passed smart, 1297 opened. The `UNKNOWN` class is a classification failure — these should be routed to a real class or rejected. No edge claim possible.
- **90d expected P&L (1% risk, $100k):** **−$300.** 3 trades × 1% × (−100% edge) ≈ **−$300**.
- **Gate change:** `REJECT_UNKNOWN_ASSET_CLASS = True` — do not open trades with unclassified asset class. This is a data-hygiene gate, not a threshold.
- **Confidence (1-5):** **1**

### FUTURES
- **Real/noise verdict:** **NOISE.** 37.5% WR on n=16. `passed_verified_alpha` = 1. H-005 (futures momentum anti-signal) is formally killed — do not re-derive. No proven cells.
- **90d expected P&L (1% risk, $100k):** **−$400.** 16 trades × 1% × (−0.6% edge) ≈ **−$400**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` — raise to cut pass rate from 123/172 = 71.5% to ~15%. If currently 50, set to **70**.
- **Confidence (1-5):** **1**

### MEME
- **Real/noise verdict:** **NOISE.** 42.86% WR on n=7. `passed_verified_alpha` = 3 but no proven cells. n=7 is not a sample.
- **90d expected P&L (1% risk, $100k):** **−$100.** 7 trades × 1% × (−0.3% edge) ≈ **−$100**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME` — raise to cut pass rate from 9/21 = 43% to ~10%. If currently 50, set to **70**. Also consider `DISABLE_MEME_CLASS = True` until n>=100 closed.
- **Confidence (1-5):** **1**

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY with real money: NONE.** There is not a single asset class in this report with a statistically defensible edge. Every "PROVEN" cell is either (a) `trust=UNK` (trust dimension unpopulated — the cell is not trust-validated), (b) holdout-failing (COMMODITY, CRYPTO), or (c) PF > 14 with n < 40 (FOREX, EQUITY) which is the signature of leakage or single-symbol concentration, not edge. The class-level WRs that look positive (COMMODITY 69%, EQUITY 72%, INDEX 100%) are all on n ≤ 105 closed — anecdotes, not samples. The class-level WRs on real samples (CRYPTO 44.67% n=2279, FOREX 51.61% n=436) are losing or coin-flip.

**The honest answer to "which class would you scale up today" is: none. Do not deploy capital on this funnel.**

**Demote per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` (mutate before kill):**

1. **FOREX — DEMOTE FIRST.** It has the largest sample (n=436), the worst gate (97.4% pass rate), and the most suspicious "proven" cell (PF 14.45, holdout 99.0). Mutate: (a) add `REGIME_TERMINAL_LOOKAHEAD_GUARD`, (b) raise `SMART_PICKS_MIN_SCORE_FOREX` to cut pass rate to ~20%, (c) re-run 90d. If WR stays ~51% after mutation, kill the class.
2. **EQUITY — DEMOTE SECOND.** The mean-reversion cell is the most dangerous because it looks real (PF 132, bonferroni_pass true). Mutate: add `MEAN_REVERSION_ENTRY_TIMESTAMP_AUDIT` and re-run. If the cell collapses to PF < 2 after the audit, it was leakage — kill the cell, keep the class.
3. **CRYPTO — DEMOTE THIRD.** Largest volume, negative class WR, no proven cells. Mutate: raise `SMART_PICKS_MIN_SCORE_CRYPTO` to cut pass rate from 30% to ~10%, and fix trust population so `trust=UNK` stops dominating. Re-run 90d.
4. **COMMODITY, BOND, ETF, FUTURES, MEME, INDEX, UNKNOWN — KILL or FREEZE.** All have n < 40 closed, negative or undefined edge, and pass-through gates. Freeze opens until `MIN_CLOSED_TRADES_FOR_CLASS_PROMOTION = 100` is met.

**The single highest-leverage fix is not a threshold — it's the funnel-integrity bug.** `opened` >> `

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### CRYPTO
- Real/noise verdict: Noise. No PROVEN cells. Best_pf cells show holdout degradation (2.504→1.259) and fail Bonferroni; n=197 is modest but not stable.
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge; slippage + commissions would turn positive PF negative).
- Gate change: `HC_MIN_CONFIDENCE` = 0.82
- Confidence (1-5): 4

### COMMODITY
- Real/noise verdict: Noise. No PROVEN cells. Best_pf cells fail holdout and have n<30.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: `SMART_PICKS_MIN_SCORE_COMMODITY` = 72
- Confidence (1-5): 5

### FOREX
- Real/noise verdict: Likely noise/leakage. PROVEN cells have extreme PF (14.449) and 89% WR on n=38; regime_terminal source concentration suggests single-signal overfitting rather than robust edge.
- 90d expected P&L (1% risk, $100k): -$420 (expected after realistic 0.8-tick slippage on 38 trades at 1% risk).
- Gate change: `HC_MIN_TRUST` = 65
- Confidence (1-5): 3

### EQUITY
- Real/noise verdict: Noise/leakage. PROVEN cells show PF=131 on 36/37 wins; mean_reversion + RR>=2.0 screams single-symbol concentration or look-ahead.
- 90d expected P&L (1% risk, $100k): -$180 (edge collapses out-of-sample).
- Gate change: `SMART_PICKS_MIN_SCORE_EQUITY` = 68
- Confidence (1-5): 4

### INDEX
- Real/noise verdict: Noise (n=1).
- 90d expected P&L (1% risk, $100k): $0
- Gate change: `HC_MIN_SCORE` = 85
- Confidence (1-5): 5

### ETF
- Real/noise verdict: Noise (n=11, no PROVEN).
- 90d expected P&L (1% risk, $100k): $0
- Gate change: `SMART_PICKS_MIN_SCORE_ETF` = 65
- Confidence (1-5): 5

### BOND
- Real/noise verdict: Noise (n=31, no PROVEN).
- 90d expected P&L (1% risk, $100k): $0
- Gate change: `SMART_PICKS_MIN_SCORE_BOND` = 55
- Confidence (1-5): 5

### UNKNOWN
- Real/noise verdict: Noise (n=3).
- 90d expected P&L (1% risk, $100k): $0
- Gate change: `HC_MIN_CONFIDENCE` = 0.80
- Confidence (1-5): 5

### FUTURES
- Real/noise verdict: Noise (n=16, no PROVEN).
- 90d expected P&L (1% risk, $100k): $0
- Gate change: `SMART_PICKS_MIN_SCORE_FUTURES` = 70
- Confidence (1-5): 5

### MEME
- Real/noise verdict: Noise (n=7).
- 90d expected P&L (1% risk, $100k): $0
- Gate change: `HC_MIN_TRUST` = 70
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale up: none (zero classes have trustworthy, slippage-resistant edges that survive the known rejected hypotheses). Demote: EQUITY and FOREX first per MUTATION_THREE_AXIS_PROTOCOL.md — their PROVEN cells are the clearest leakage candidates and should be mutated (add symbol-level dedup + stricter regime filters) before any further capital allocation.
