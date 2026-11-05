# Pick Funnel Swarm Verdict — 2026-11-05 04:07 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20261105T040702Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-Day Edge Analysis

Before per-class verdicts, three structural facts dominate everything below:

1. **`passed_high_conviction = 0` across ALL 10 classes.** The HC gate (score≥80, conf≥0.75, trust≥60) is *never* firing. Either the scoring distribution never reaches 80, or trust never reaches 60, or the JS gate is dead. This is the single biggest finding in the dataset — the "HIGH CONVICTION" funnel stage is a no-op.
2. **`passed_verified_alpha` is 0 for 7 of 10 classes** and only non-trivial for CRYPTO (2270). The verified-alpha stage is effectively CRYPTO-only.
3. **The "PROVEN" cells are almost all `trust=UNK`.** Every single proven cell in FOREX, CRYPTO, and EQUITY is `trust=UNK`. That means the trust dimension is *not* doing work — the "edge" is being found in the *untrusted* bucket. That is a red flag, not a green one.

---

### EQUITY
- **Real/noise verdict:** **NOISE / LEAKAGE.** The "proven" cell is `conf=C<0.60 & fam=mean_reversion`, n=62, WR=98.39%, **PF=173.4**. A PF of 173 is not a strategy — it is a data artifact. 61/62 wins with avg_pnl +1.59% and *low confidence* is the signature of a look-ahead or exit-timing bug (e.g., mean-reversion exits booked at the same bar as entry, or a "win" defined by a touch that never filled). `holdout_pf=99.0` is the capped sentinel, not a real number. `wr_z=7.62` is meaningless when the underlying P&L distribution is degenerate. **Do not trade this.** Also note: 5628 opened vs 129 closed — 97.7% of equity picks never resolve, so the WR is computed on a 2.3% survivor sample. That alone invalidates the cell.
- **90d expected P&L (1% risk, $100k):** **$0.** Not tradeable. If forced to model the *reported* cell: 62 trades × 1% × 1.59% avg = ~$986, but the PF=173 and 98% WR are non-credible; treat as $0 until the exit logic is audited.
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` — raise from current floor to **≥ 65** AND add a hard `min_closed_sample >= 200` guard before any cell is promoted to PROVEN. The current floor is letting 236/5757 (4.1%) through but the *closed* sample is 129 — the gate is measuring the wrong population.
- **Confidence (1-5):** **1**

---

### COMMODITY
- **Real/noise verdict:** **NOISE.** No proven cells. Best PF overall is 2.01 on n=30 with `holdout_pass=false` and `bonferroni_pass=false`. `wr_shrunk=56%` is barely above coin-flip after shrinkage. This is consistent with the already-falsified H-001 (COT leakage) and H-036 (inventory gate) — the class has a documented history of leakage-driven fake edges. The 3703/6167 "passed_smart" rate (60%) is absurdly permissive; the gate is not filtering.
- **90d expected P&L (1% risk, $100k):** **$0.** No credible edge. The 42 closed trades at 64% WR is n=42 — below any usable threshold.
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` — raise to **≥ 70** (from current, which is clearly permissive given 60% pass rate). Also add `min_holdout_n >= 20` to the promotion rule.
- **Confidence (1-5):** **1**

---

### FOREX
- **Real/noise verdict:** **NOISE / LEAKAGE.** The "best PF" cell is `trust=UNK & conf=C>=0.90 & dir=LONG` with **PF=16.96**, n=26, WR=92.3%. `holdout_pass=false` (holdout_n=5, PF=99.0 sentinel). `wr_shrunk=73.9%` on n=26 is not credible — the shrinkage is doing almost nothing because the raw WR is so extreme. **This is the classic signature of a single-source, single-regime artifact:** `source=regime_terminal` appears in the cell definition, and `fam=regime` is the same cell. 26 trades from one source over 90 days = one regime, one symbol cluster. The `bonferroni_pass=true` is misleading because the multiple-testing correction was applied to a search space that already included the leakage. **Flag as potential leakage recurrence** (H-001/H-036 pattern: high WR from a single data source with timestamp issues). The class-level WR is 50.34% on 437 decisive — i.e., the *aggregate* is a coin flip. The "edge" is a 26-trade tail.
- **90d expected P&L (1% risk, $100k):** **$0.** Aggregate is 50/50. The 26-trade cell, if real, would be 26 × 1% × 0.675% = ~$176 — but it is not real. Do not size on it.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` — raise to **≥ 75** (from current, which passes 97% of scans — 23659/24382). The FOREX gate is essentially open; it is the worst offender in the funnel. Also require `trust != UNK` for any cell to be promoted to PROVEN.
- **Confidence (1-5):** **1**

---

### CRYPTO
- **Real/noise verdict:** **PARTIALLY REAL — the only class with a defensible edge, but the headline cell is overstated.** The `conf=C0.75-0.80 & dir=LONG & score_dec=S50` cell has n=168, WR=77.98%, **wr_shrunk=75.0%**, PF=3.64, **holdout_pass=true** (holdout PF=2.71 on n=93), `wr_z=7.25`, `bonferroni_pass=true`. This is the *only* cell in the entire dataset that survives holdout AND shrinkage AND multiple-testing. That is meaningful. **However:** (i) it is `trust=UNK` — the trust dimension is not contributing; (ii) the second proven cell (`source=alpha_engine`, n=247, PF=2.30) has `holdout_pf=1.42` — the edge decays by ~40% out of sample; (iii) the class-level WR is **46.24%** on 2420 decisive — the *aggregate* is losing. The edge is a *narrow slice* (LONG, mid-confidence, S50 score decile) inside a losing class. That is a real but fragile edge. **The `ml` cells you flagged are not in the proven list** — the proven cells are `alpha_engine` and `score_dec=S50`, not `ml`. If `ml` cells show PF>10 elsewhere, treat as leakage; here they don't appear, so no flag needed on `ml` specifically.
- **90d expected P&L (1% risk, $100k):** Model the proven cell: 168 trades × 1% risk × 1.54% avg_pnl = **~$2,587** gross. Apply 15 bps round-trip slippage on $100k notional per trade = 168 × $150 = $25,200 drag — **wait, that's wrong sizing.** At 1% risk ($1,000 risk/trade) with avg win ~1.54% and avg loss ~-1.0%, the per-trade expectancy is ~+0.7% of risk = ~$7/trade × 168 = **~$1,176**. Net of realistic slippage (crypto 10-20 bps round trip on notional, but risk-based sizing means slippage is ~10-15% of risk) → **~$900–$1,000 net.** Modest but real.
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` — **lower** to **≥ 55** *specifically for the LONG + conf 0.75–0.80 + S50 slice*, OR (cleaner) add a `PROMOTE_CELL_CRYPTO` allowlist in `quality_gates.py` that bypasses the generic floor for this cell. The current gate passes 3812/12932 (29%) but the edge lives in a 168-trade slice — the gate is neither tight enough nor targeted. **The single highest-leverage change: make the HC gate actually fire** (see system-wide).
- **Confidence (1-5):** **3**

---

### BOND
- **Real/noise verdict:** **NOISE.** n=31 closed, WR=38.7%, no proven cells, `passed_smart=1/910`. The gate is essentially closed (0.1% pass) and the class is losing. No edge.
- **90d expected P&L (1% risk, $100k):** **$0** (negative expectancy: 31 × 1% × (0.387×avg_win − 0.613×avg_loss) ≈ **−$150 to −$300**).
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` — **keep closed / raise to 90** or disable BOND scanning entirely until n≥100 closed. Do not spend compute here.
- **Confidence (1-5):** **1**

---

### ETF
- **Real/noise verdict:** **NOISE.** n=9 closed, WR=11.1%. `passed_smart=291/339` (86% pass — gate is broken open) but only 9 resolve. Statistically meaningless.
- **90d expected P&L (1% risk, $100k):** **$0** (negative: 9 trades, 1 win).
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` — raise to **≥ 80** and add `min_closed_sample >= 50` before any ETF cell is reported. The 86% pass rate is the tell.
- **Confidence (1-5):** **1**

---

### FUTURES
- **Real/noise verdict:** **NOISE.** n=17, WR=41.2%, no proven cells. Consistent with falsified H-005 (momentum anti-signal). No edge.
- **90d expected P&L (1% risk, $100k):** **$0** (negative expectancy).
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` — raise to **≥ 75**; `passed_smart=136/188` (72%) is too permissive.
- **Confidence (1-5):** **1**

---

### MEME
- **Real/noise verdict:** **NOISE.** n=9, WR=33.3%. `passed_verified_alpha=3` but 0 proven. Too small to judge; treat as no edge.
- **90d expected P&L (1% risk, $100k):** **$0**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME` — raise to **≥ 85** or disable until n≥50.
- **Confidence (1-5):** **1**

---

### UNKNOWN
- **Real/noise verdict:** **NOISE / DATA HYGIENE FAILURE.** n=3, WR=0%. 1368 scanned, 1365 opened, 3 closed. This class should not exist — it is a classification bug. Every trade here is a data-quality incident.
- **90d expected P&L (1% risk, $100k):** **$0**.
- **Gate change:** **Not a score gate — fix the classifier.** Route UNKNOWN to a quarantine table; do not open trades on unclassified symbols. In `production_scanner.py`, add `if asset_class == "UNKNOWN": skip`.
- **Confidence (1-5):** **1**

---

### INDEX
- **Real/noise verdict:** **NOISE.** n=1 closed, WR=100%. Statistically meaningless. `passed_smart=1583/1961` (81% pass) — gate is open.
- **90d expected P&L (1% risk, $100k):** **$0** (n=1).
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` — raise to **≥ 75**; require n≥30 closed before reporting.
- **Confidence (1-5):** **1**

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY with real money: CRYPTO — and only the narrow proven slice.**
The `conf=C0.75-0.80 & dir=LONG & score_dec=S50` cell is the *only* cell in the entire 90-day dataset that passes holdout, shrinkage, and Bonferroni simultaneously (n=168, shrunk WR=75%, holdout PF=2.71). Size it small (0.5% risk/trade, not 1%) because the class aggregate is 46% WR and the edge decays ~40% out of sample. Expected net ~$900–$1,000 over 90d at 1% risk; halve for 0.5%. **Do not scale the class — scale the cell.**

**Demote per MUTATION_THREE_AXIS_PROTOCOL (mutate before kill): FOREX.**
FOREX is the worst offender: 97% pass rate (23659/24382), aggregate WR 50.34%, and the only "proven" cell is a 26-trade `trust=UNK` single-source artifact with PF=16.96 and `holdout_pass=false`. Per the protocol, do not kill — **mutate**: (1) raise `SMART_PICKS_MIN_SCORE_FOREX` to 75, (2) require `trust != UNK` for promotion, (3) re-run the 90d funnel and check whether the 26-trade cell survives. If it does not, kill. **EQUITY is a close second for demotion** — the PF=173 mean-reversion cell is almost certainly leakage and should be quarantined pending an exit-logic audit.

**The single most important system-wide finding:** `passed_high_conviction = 0` in all 10 classes. The HC gate in `hc_filter.js` (score≥80, conf≥0.75, trust≥60) is **dead code** — it never fires. Either the score distribution never reaches 80 (check `production_scanner.py` score ceiling), or trust never reaches 60 (check trust computation), or the JS gate is not wired to the dashboard. **Fix this before any other gate change** — the entire "HIGH CONVICTION" funnel stage is currently a lie to the user. The one gate change that would lift the edge most is not a threshold tweak; it is **making the HC gate actually evaluate**, then setting `HC_MIN_SCORE = 75` (not 80) and `HC_MIN_TRUST = 50` (not 60) so the CRYPTO proven cell (which is `trust=UNK`, i.e., trust<60) can actually surface. As written, the HC gate would *exclude* the only real edge in the dataset.

**Brutal summary:** 1 of 10 classes has a real edge (CRYPTO, narrow slice). 9 of 10 are noise, leakage, or too-small-to-judge. The funnel's headline stages (`verified_alpha`, `high_conviction`, `proven`) are 0 for almost every class — the dashboard is reporting a pipeline that does not exist. Do not invent edges to fill the table; the honest answer is that this system has one tradeable cell and nine data-hygiene problems.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### FOREX
- Real/noise verdict: noise — high PF driven by n=26 with holdout_n=5 and holdout_pass=false; classic small-sample blowup, not stable.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: none (no usable edge)
- Confidence (1-5): 5

### CRYPTO
- Real/noise verdict: real — n=168 cell passes holdout, WR_shrunk=75%, PF=3.643 with bonferroni_pass=true; second cell also passes.
- 90d expected P&L (1% risk, $100k): $18400 (168 trades × ~1.54% avg edge after 0.2% slippage, 1% risk sizing)
- Gate change: SMART_PICKS_MIN_SCORE_CRYPTO = 52
- Confidence (1-5): 4

### EQUITY
- Real/noise verdict: noise — PF=173 on n=62 is statistically impossible without leakage or single-symbol concentration; holdout_pass does not override the absurdity.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: none (no usable edge)
- Confidence (1-5): 5

### ETF
- Real/noise verdict: noise — n_closed=9, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: none
- Confidence (1-5): 5

### FUTURES
- Real/noise verdict: noise — n_closed=17, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: none
- Confidence (1-5): 5

### MEME
- Real/noise verdict: noise — n_closed=9, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: none
- Confidence (1-5): 5

### BOND
- Real/noise verdict: noise — n_closed=31, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: none
- Confidence (1-5): 5

### COMMODITY
- Real/noise verdict: noise — best_pf_overall cells fail holdout and bonferroni; matches known rejected hypotheses pattern.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: none
- Confidence (1-5): 5

### INDEX
- Real/noise verdict: noise — n_closed=1.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: none
- Confidence (1-5): 5

### UNKNOWN
- Real/noise verdict: noise — n_closed=3.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: none
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale CRYPTO today (only class with verified holdout-pass edges). Demote EQUITY and FOREX per MUTATION_THREE_AXIS_PROTOCOL.md — their cells are leakage candidates; mutate the mean_reversion and regime_terminal paths before any further allocation. All other classes have no actionable edge.
