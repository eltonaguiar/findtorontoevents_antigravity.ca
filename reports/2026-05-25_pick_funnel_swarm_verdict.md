# Pick Funnel Swarm Verdict — 2026-09-26 04:10 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260926T041008Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-day edge analysis

Before per-class verdicts, three cross-cutting facts that dominate everything below:

1. **`passed_high_conviction = 0` in every single class.** The HC gate (`score>=80 & conf>=0.75 & trust>=60`) has never fired in 90 days. The "HIGH CONVICTION" funnel stage is dead code. Any edge you think you have is *not* being surfaced by HC.
2. **`passed_verified_alpha` is 0 for EQUITY, FOREX, COMMODITY, BOND, ETF, INDEX, UNKNOWN.** Only CRYPTO (1798) and a trickle of FUTURES/MEME pass. The verified-alpha gate is effectively a CRYPTO-only gate.
3. **`opened` >> `passed_smart` in every class** (e.g. EQUITY 5315 opened vs 252 passed_smart; FOREX 21507 vs 21828 — the only class where they roughly match). The funnel is not actually gating opens. Whatever `passed_smart` means, it is not the binding constraint on what gets traded. This is the single biggest structural problem in the report.

Also note: the prompt asks me to comment on "FOREX `consensus` and CRYPTO `ml` cells" — **neither appears in the supplied edge JSON.** The FOREX top cell is `multi_asset_copytrader`, and CRYPTO's is `alpha_engine`. I'll flag the cells that *are* present and note the mismatch.

---

### EQUITY
- **Real/noise verdict:** **NOISE / LEAKAGE.** The "PROVEN" cell `fam=mean_reversion & score_dec=S40` shows WR=98.55% (68/69), PF=220.8, holdout PF=99.0. A PF of 220 is not a trading edge — it is a data artifact. Three smoking guns: (i) `trust=UNK` on 100% of the cell, (ii) `conf=C<0.60` — the *lowest* confidence band producing the *highest* WR, which is inverted from every real signal, (iii) `score_dec=S40` is a low score decile. This is the classic signature of a **stale-price / look-ahead fill** (entry marked at a price that already reflects the move) or a **survivorship-filtered subset** where losers were dropped before the 90d window. The 40/29 train/holdout split both showing PF>99 means the leak is present in both halves — consistent with a systematic timestamp bug, not overfitting. **Do not trade this.** Treat as H-001-class leakage recurrence.
- **90d expected P&L (1% risk, $100k):** **$0 — do not deploy.** If you naively sized the 69 trades at 1% risk with the reported avg_pnl of +1.27%, you'd "expect" ~+$870. That number is fiction. Realistic post-leak-fix expectation for EQUITY mean_reversion at S40 is unknown but the class-level WR of 66.5% on n=164 with no verified-alpha pass suggests **near-zero to slightly negative** after costs.
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` — raise from current value to **≥55**, AND add a hard `trust != UNK` requirement in `quality_gates.py` for any cell claiming PROVEN status. The `trust=UNK` cells are where the leak lives.
- **Confidence (1-5):** **5** that the PROVEN cell is fake. **2** that EQUITY has any real edge at all.

---

### FOREX
- **Real/noise verdict:** **NOISE.** `top_edges_proven` is empty — correct call by the harness. The best cell (`rr=RR1.0-1.5 & fam=mean_reversion & dir=LONG & source=multi_asset_copytrader`) has n=46, WR_shrunk=56.06%, PF=2.838, but **`bonferroni_pass=false` and `wr_z=1.18`**. A z of 1.18 is not significant at any multiple-testing-corrected threshold. Class-level WR is 44.4% on n=1309 — a losing class. The `multi_asset_copytrader` source is a copy-trade feed; PF=2.8 on n=46 with z=1.18 is almost certainly a handful of correlated positions in the same currency pair (single-symbol concentration). The prompt's reference to a FOREX `consensus` cell doesn't match the data — flagging that the report may be mislabeled.
- **90d expected P&L (1% risk, $100k):** **Negative.** Class WR 44.4% with avg_pnl unknown but PF implied <1. At 1% risk × 1309 closed trades, even a -0.1% avg edge compounds to roughly **-$1,300 to -$3,000** before slippage. FOREX spreads on retail pairs (0.5–1.5 pips) will eat any marginal signal. **Do not deploy.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` — raise to **≥60** and add a **per-source cap** (max 20% of opens from any single `source`) to kill `multi_asset_copytrader` concentration. The 21,828 passed_smart out of 22,816 scanned (95.7% pass rate) means the FOREX gate is not gating.
- **Confidence (1-5):** **4** that FOREX has no deployable edge. **5** that the 95.7% pass rate is a bug.

---

### CRYPTO
- **Real/noise verdict:** **MOSTLY REAL, with one suspicious cell.** The `conf=C0.75-0.80 & dir=LONG & score_dec=S50 & source=alpha_engine` cell is the strongest in the entire report: n=187, WR=74.87%, WR_shrunk=72.46%, PF=3.679, **holdout PF=4.28 on n=36, holdout_pass=true, wr_z=6.80, bonferroni_pass=true**. That is a genuinely significant result — z=6.8 survives Bonferroni across the ~dozens of cells tested. The train/holdout consistency (3.50 → 4.28) is the opposite of overfitting. **However:** PF=3.68 with avg_pnl=+1.42% and WR=75% implies avg_win/avg_loss ≈ 1.23 — plausible for crypto longs in a 90d uptrend. The risk is **regime dependence**: 90 days of crypto beta. The `trust=UNK` variant is identical (n=188 vs 187) — meaning essentially all these trades are untrusted-source. That's a yellow flag, not a red one, because the holdout held. The prompt's reference to a CRYPTO `ml` cell doesn't appear in the data — if an `ml`-sourced cell exists elsewhere with PF>5, treat it as suspect until it shows the same train/holdout discipline.
- **90d expected P&L (1% risk, $100k):** Deployable. 187 trades × 1% risk × avg_pnl +1.42% = **+$2,655** on the edge cell alone. Scaling to the full CRYPTO book (2416 closed, class WR 45.4%) is negative — so **only the edge cell is tradeable**. Realistic net after 0.1% round-trip slippage on 187 trades: **+$2,300 to +$2,500**. If you restrict to the LONG-only variant (n=187), same number.
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` — **lower** to admit more `conf=0.75-0.80 & score_dec=S50` picks, OR (better) add an explicit **edge-cell allowlist** in `quality_gates.py` that bypasses the score floor for this exact cell signature. The current gate is passing 3255/12641 (25.8%) but the edge lives in a narrow 187-trade slice — the gate is too coarse.
- **Confidence (1-5):** **4** that the edge cell is real. **2** that it survives a regime flip.

---

### COMMODITY
- **Real/noise verdict:** **NOISE / LEAKAGE RECURRENCE.** `top_edges_proven` empty — correct. Best cell `rr=RR1.5-2.0 & score_dec=S50 & source=alpha_engine`: n=27, WR=48.15%, PF=4.281, but **train_pf=10.76 (n=13) vs holdout_pf=0.513 (n=14), holdout_pass=false**. This is textbook overfitting: the PF is entirely carried by 13 training trades. The holdout is a coin flip. This pattern — high PF, low WR, train/holdout divergence — is exactly the H-001 COT leakage signature (look-ahead on a data release). **Do not trade.** Class WR 42.2% on n=117 is a losing class.
- **90d expected P&L (1% risk, $100k):** **Negative.** 117 closed × 1% × implied negative avg = roughly **-$500 to -$1,500**. Do not deploy.
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` — raise to **≥65** and add a **mandatory holdout_pass=true** requirement before any COMMODITY cell is promoted to PROVEN. The current 3562/6101 (58.4%) pass rate is far too loose for a class with 42% WR.
- **Confidence (1-5):** **5** that COMMODITY has no edge. **5** that the top cell is overfit.

---

### BOND
- **Real/noise verdict:** **NOISE.** n=34 closed total — below any meaningful threshold. Best cell n=21, WR_shrunk=51.2%, PF=1.313, holdout_pass=false. Second cell is actively bad (WR=10%, PF=0.052). No edge.
- **90d expected P&L (1% risk, $100k):** **~$0 to -$200.** Not tradeable at n=34.
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` — raise to **≥70** (effectively disable until n≥100). Or set `SMART_PICKS_MIN_N_BOND = 100` as a hard floor.
- **Confidence (1-5):** **5** no edge.

---

### ETF
- **Real/noise verdict:** **NOISE.** n=7 closed, WR=14.3%. Statistically meaningless. 293/334 passed_smart (87.7%) — the gate is not gating.
- **90d expected P&L (1% risk, $100k):** **-$50 to -$100.** Not tradeable.
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` — raise to **≥70**, or disable ETF opens entirely until n≥50.
- **Confidence (1-5):** **5** no edge.

---

### UNKNOWN
- **Real/noise verdict:** **NOISE / DATA HYGIENE FAILURE.** n=7 closed, WR=0%. 1405 scanned, 1398 opened — the "UNKNOWN" bucket is a catch-all that bypasses classification. This is a **pipeline bug**, not an asset class.
- **90d expected P&L (1% risk, $100k):** **-$70.** Not tradeable.
- **Gate change:** Add a hard reject in `quality_gates.py`: `if asset_class == "UNKNOWN": return False`. Zero UNKNOWN opens.
- **Confidence (1-5):** **5** this is a bug.

---

### INDEX
- **Real/noise verdict:** **NOISE.** n=5 closed, WR=20%. 1509/1709 passed_smart (88.3%) — gate not gating.
- **90d expected P&L (1% risk, $100k):** **-$40.** Not tradeable.
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` — raise to **≥70** or disable.
- **Confidence (1-5):** **5** no edge.

---

### FUTURES
- **Real/noise verdict:** **NOISE.** n=17 closed, WR=29.4%. Consistent with H-005 (futures_momentum anti-signal FAILED to invert). No edge.
- **90d expected P&L (1% risk, $100k):** **-$120.** Not tradeable.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` — raise to **≥70** or disable.
- **Confidence (1-5):** **5** no edge.

---

### MEME
- **Real/noise verdict:** **NOISE.** n=4 closed. Not a class, a rounding error.
- **90d expected P&L (1% risk, $100k):** **-$30.** Not tradeable.
- **Gate change:** Disable MEME opens until n≥50.
- **Confidence (1-5):** **5** no edge.

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY with real money: CRYPTO — and only the single edge cell.**
`conf=C0.75-0.80 & dir=LONG & score_dec=S50 & source=alpha_engine`, n=187, WR_shrunk=72.5%, PF=3.68, holdout PF=4.28, z=6.80, Bonferroni-pass. This is the only cell in the entire report that survives multiple-testing correction *and* holds out-of-sample. Size it at 1% risk per trade, cap total CRYPTO exposure at 5% of book, and **re-validate weekly** — the edge is regime-dependent on crypto beta and will die in a sustained downtrend. Expected 90d P&L on this cell alone: **+$2,300 to +$2,500 net.**

**Demote per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` (mutate before kill): COMMODITY.**
It has the most closed trades (n=117) of any non-CRYPTO class, a 42% WR, and a top cell that is a textbook train/holdout overfit (train PF 10.76 → holdout PF 0.51). Before killing, mutate on the three axes: (1) **timeframe** — the current signal is likely a daily-bar artifact; test 4h and 1h; (2) **regime filter** — gate on realized vol percentile; (3) **source** — `alpha_engine` is the only source in the top cell; test whether the signal survives when `alpha_engine` is excluded. If all three mutations fail, kill. Do **not** re-derive the H-001 COT hypothesis — the current top cell's train/holdout divergence is the same leakage signature and should be flagged as a recurrence, not a new edge.

**Structural fixes required regardless of class:**
1. `passed_high_conviction = 0` everywhere → the HC gate in `hc_filter.js` is misconfigured. Either the score/conf/trust distributions never reach the thresholds, or the gate is evaluated on the wrong fields. Audit before trusting any "HC" claim.
2. `opened` >> `passed_smart` in 8 of 10 classes → the funnel is decorative. The real gate is somewhere else. Find it.
3. `trust=UNK` dominates every "PROVEN" cell → add `trust != UNK` as a hard requirement for PROVEN promotion in `quality_gates.py`.
4. `passed_verified_alpha = 0` for 7 of 10 classes → the verified-alpha gate is CRYPTO-only in practice. Either fix it or rename it.

**Bottom line:** One real edge (CRYPTO, one cell). One class to mutate-then-kill (COMMODITY). Eight classes with no edge — say so and stop trading them. The funnel report is currently measuring the wrong things; fix the instrumentation before the next 90-day review.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

**### CRYPTO**
- Real/noise verdict: Real edge in the listed cells (n=187-188, WR_shrunk 72%, PF 3.68, holdout_pass + bonferroni_pass). No obvious single-symbol concentration or leakage flags in the provided stats.
- 90d expected P&L (1% risk, $100k): ~$4,800 (188 trades × 1% risk × ~1.41% avg pnl, 0.15% slippage, 0.8 fill rate).
- Gate change: `hc_filter.js` HIGH_CONVICTION_MIN_SCORE = 75
- Confidence (1-5): 4

**### EQUITY**
- Real/noise verdict: Sample noise / leakage. 98.55% WR and PF 220 on n=69 mean_reversion LONG is statistically impossible without data error or look-ahead.
- 90d expected P&L (1% risk, $100k): $0 (edge invalid; do not trade).
- Gate change: `audit_trail/quality_gates.py` SMART_PICKS_MIN_SCORE_EQUITY = 65
- Confidence (1-5): 5

**### FOREX**
- Real/noise verdict: Noise. No proven cells; best_pf cells fail bonferroni and show marginal WR_shrunk ~55%.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: `audit_trail/quality_gates.py` SMART_PICKS_MIN_SCORE_FOREX = 70
- Confidence (1-5): 5

**### COMMODITY**
- Real/noise verdict: Noise. No proven cells; best_pf cells fail holdout and show negative wr_z.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: `audit_trail/quality_gates.py` SMART_PICKS_MIN_SCORE_COMMODITY = 75
- Confidence (1-5): 5

**### BOND**
- Real/noise verdict: Noise. No proven cells; tiny n and failing holdout metrics.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: `audit_trail/quality_gates.py` SMART_PICKS_MIN_SCORE_BOND = 80
- Confidence (1-5): 5

**### ETF / INDEX / FUTURES / MEME / UNKNOWN**
- Real/noise verdict: Noise. Zero proven cells and n_closed too low for any reliable signal.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: `audit_trail/quality_gates.py` SMART_PICKS_MIN_SCORE_ETF = 80 (apply same pattern to others)
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale CRYPTO today (only class with statistically supported, holdout-validated cells). Demote EQUITY, COMMODITY, BOND, ETF, INDEX, FUTURES, MEME, UNKNOWN, and FOREX per MUTATION_THREE_AXIS_PROTOCOL.md — they have no usable edge and should be mutated or removed before any further capital allocation.
