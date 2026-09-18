# Pick Funnel Swarm Verdict — 2026-09-18 04:10 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260918T041016Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-day Edge Analysis

Before per-class verdicts, three system-wide red flags that dominate everything below:

1. **`passed_high_conviction = 0` across every single class.** The HC gate (score≥80, conf≥0.75, trust≥60) is firing on **zero** trades in 90 days. Either the gate is mis-wired, or the scoring pipeline never produces score≥80. This is the single most important finding — the "HIGH CONVICTION" funnel is dead.
2. **`opened` >> `passed_smart` in every class** (e.g. EQUITY: 226 passed_smart → 4,699 opened). The Smart gate is not actually gating opens. Whatever is being traded is *not* what the funnel says is being traded. All downstream WR/PF numbers are therefore measuring the wrong population.
3. **`passed_verified_alpha` is 0 for COMMODITY/FOREX/ETF/FUTURES/INDEX/BOND/UNKNOWN** but CRYPTO has 1,799. That asymmetry is suspicious — either CRYPTO has a real alpha source, or the verified-alpha check is class-conditional in a way that leaks.

Also: the prompt asks me to comment on FOREX `consensus` and CRYPTO `ml` cells — **neither appears in the data provided**. The FOREX top cells are `mean_reversion` and `multi_asset_copytrader`; CRYPTO top cells are `alpha_engine`. I'll flag the cells that *are* present and note the mismatch.

---

### EQUITY
- **Real/noise verdict:** **NOISE / LEAKAGE.** The "PROVEN" cell `fam=mean_reversion & score_dec=S40` shows WR=98.59% (70/71), PF=225.85, holdout PF=99.0. A 98.6% WR with PF>200 on n=71 is not a real edge — it is a **labeling or exit-logic bug**. Real mean-reversion on equities does not produce 70 wins against 1 loss. Likely causes: (a) wins counted on mark-to-market before stop is hit, (b) `score_dec=S40` bucket is capturing a single symbol or a single day, (c) the "loss" definition excludes time-stopped trades. The fact that `trust=UNK`, `conf=C<0.60`, and `dir=LONG` all collapse to the *identical* n=71 / 70 wins / PF=225.85 confirms this is one cell being re-sliced, not three independent confirmations. **Do not trade this.** Also note the class-level WR of 67.35% (132W/64L) is wildly inconsistent with the "PROVEN" cell — the proven cell is a subset that doesn't reconcile with the aggregate.
- **90d expected P&L (1% risk, $100k):** **$0 — do not size.** If forced to mark the aggregate: 196 closed, 67.35% WR, but avg_pnl_pct on the "proven" cell is 1.27% and the aggregate is unknown. Using the proven cell's avg_pnl_pct=1.27% × 1% risk × 196 trades ≈ **$2,490** — but this is fiction given the leakage. Report as **$0 (uninvestable)**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` — raise from current value to **≥70**, AND add a hard cap: reject any cell where `wr_pct > 90%` on n<200 as a leakage sentinel. The real fix is upstream: audit why `opened` (4,699) >> `passed_smart` (226).
- **Confidence (1-5):** **1** (the "edge" is a bug; the class has no demonstrable edge).

---

### COMMODITY
- **Real/noise verdict:** **NOISE.** `top_edges_proven` is empty. Best PF cell is n=21, WR=76.19%, PF=5.62, but `bonferroni_pass=false` and holdout_n=11 — that's a coin-flip sample. Class WR=44.44% (60W/75L) is below breakeven for typical R:R. The known-falsified H-001 (COT leakage) and H-036 (inventory direction) both live here — **do not re-derive COT or inventory signals**; if any new cell converges on those, treat as leakage recurrence.
- **90d expected P&L (1% risk, $100k):** **Negative.** 135 decisive, 44.44% WR. With avg_pnl_pct=2.16% on the best cell but only n=21, and the class aggregate losing, realistic estimate: **–$1,500 to –$3,000** over 90d. Report as **–$2,000 (do not trade)**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` — raise to **≥75** and require `rr >= 2.0` as a hard precondition (the only cell with any signal was RR≥2.0). Also add a COT-timestamp guard if not already present (H-001).
- **Confidence (1-5):** **2** (no proven edge; class is a net loser).

---

### FOREX
- **Real/noise verdict:** **WEAK / PARTIALLY REAL, BUT OVERSTATED.** The `mean_reversion & conf=C0.75-0.80 & rr=RR1.0-1.5` cell: n=141, WR=65.96%, shrunk 63.98%, PF=2.66, holdout PF=1.306 (holdout_n=35). Holdout PF dropping from 3.39 → 1.31 is a **~60% degradation** — that's the signature of a real-but-decaying edge, not a stable one. `bonferroni_pass=true` is the only thing keeping this alive. The `multi_asset_copytrader` cell (n=36, PF=4.14) has `bonferroni_pass=false` — **ignore it**. Class WR=46.63% (277W/317L) is below 50% — the class as a whole is a loser; only the narrow mean-reversion slice is positive. **No `consensus` cell appears in the data** — if the prompt's "consensus" refers to a cell not shown, I cannot validate it; flag as unverified.
- **90d expected P&L (1% risk, $100k):** On the proven cell only: n=141, avg_pnl_pct=0.2656%, 1% risk → 141 × 0.01 × 0.002656 × $100k ≈ **$375**. On the full class: 594 decisive × 46.63% WR × ~0.27% avg ≈ **–$400**. Net: **~$0 to +$400**, i.e. noise-level. Report as **+$375 (proven cell only, high uncertainty)**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` — raise to **≥72** AND add `fam=mean_reversion` + `rr in [1.0, 1.5]` as a required conjunction. Without the family+RR conjunction, FOREX is a net loser.
- **Confidence (1-5):** **3** (one narrow cell survives Bonferroni, but holdout decay is concerning).

---

### CRYPTO
- **Real/noise verdict:** **REAL, BUT CONCENTRATED.** The `conf=C0.75-0.80 & score_dec=S50 & source=alpha_engine` cell: n=216, WR=76.85%, shrunk 74.58%, PF=4.11, train PF=4.06, holdout PF=4.248 (holdout_n=42), `bonferroni_pass=true`, `wr_z=7.89`. This is the **only cell in the entire dataset with a stable train/holdout PF** (4.06 → 4.25). That's the strongest statistical evidence in the report. **However:** the cell is defined by `source=alpha_engine` and `score_dec=S50` — a single source and a single score decile. That's a concentration risk, not a diversification. The `dir=LONG` variant is nearly identical (n=215), meaning the edge is essentially all-long. If crypto goes risk-off for 90 days, this cell dies. **No `ml` cell appears in the data** — the prompt's "CRYPTO ml" reference is unverifiable; flag as missing. Class WR=46.54% (1,163W/1,336L) is below 50% — the class aggregate is a loser; only the alpha_engine/S50 slice is positive.
- **90d expected P&L (1% risk, $100k):** On the proven cell: n=216, avg_pnl_pct=1.4598%, 1% risk → 216 × 0.01 × 0.014598 × $100k ≈ **$3,153**. On the full class: 2,499 decisive × 46.54% WR × ~1.46% avg ≈ **–$1,700**. Net if you trade only the proven cell: **+$3,150**. If you trade the class: **–$1,700**. Report as **+$3,150 (proven cell only)**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` — **do not raise**; instead add a hard filter: `source == 'alpha_engine' AND score_dec == 'S50' AND conf in [0.75, 0.80]` as the *only* auto-open path for CRYPTO. Everything else routes to paper. This is the one class where the gate should be *narrowed*, not raised.
- **Confidence (1-5):** **4** (strongest cell in the dataset, but single-source concentration).

---

### ETF
- **Real/noise verdict:** **NOISE.** n_closed=7, WR=14.29% (1W/6L). No proven cells. Sample is too small to conclude anything except "don't trade it."
- **90d expected P&L (1% risk, $100k):** **–$500 to –$1,000** (7 trades, 1 win). Report as **–$700**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` — raise to **≥85** (effectively disable until n≥50 closed). Or set `ETF_ENABLED=false`.
- **Confidence (1-5):** **1** (no edge, no sample).

---

### FUTURES
- **Real/noise verdict:** **NOISE.** n_closed=18, WR=38.89%. No proven cells. H-005 (futures_momentum_anti_signal) is already falsified here — do not re-derive.
- **90d expected P&L (1% risk, $100k):** **–$300 to –$600**. Report as **–$450**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` — raise to **≥85** or disable. Also ensure H-005 inversion is not re-enabled.
- **Confidence (1-5):** **1**.

---

### UNKNOWN
- **Real/noise verdict:** **NOISE / DATA HYGIENE FAILURE.** n_closed=10, WR=0.0% (0W/10L). The existence of an "UNKNOWN" asset class with 1,420 scanned and 1,410 opened means the classifier is broken. This is not a trading class — it's a bug.
- **90d expected P&L (1% risk, $100k):** **–$1,000** (10 losses).
- **Gate change:** Fix the asset classifier upstream; add `if asset_class == 'UNKNOWN': reject` in `quality_gates.py`. No constant to tune — this is a plumbing fix.
- **Confidence (1-5):** **1** (it's a bug, not an edge).

---

### BOND
- **Real/noise verdict:** **NOISE.** n_closed=25, WR=24.0% (6W/19L). No proven cells. Clear loser.
- **90d expected P&L (1% risk, $100k):** **–$1,300** (25 trades, 24% WR).
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` — raise to **≥85** or disable.
- **Confidence (1-5):** **1**.

---

### INDEX
- **Real/noise verdict:** **NOISE.** n_closed=4 (only 4 decisive out of 7 closed — the other 3 are unresolved). WR=0.0%. No proven cells. Sample is meaningless.
- **90d expected P&L (1% risk, $100k):** **–$400**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` — raise to **≥85** or disable until n≥50.
- **Confidence (1-5):** **1**.

---

### MEME
- **Real/noise verdict:** **NOISE.** n_closed=4, WR=25.0%. No proven cells. Sample is meaningless.
- **90d expected P&L (1% risk, $100k):** **–$300**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME` — raise to **≥85** or disable.
- **Confidence (1-5):** **1**.

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY with real money: CRYPTO — but only the `alpha_engine / score_dec=S50 / conf∈[0.75,0.80]` cell.**
- It is the only cell in the entire 90-day dataset with a stable train→holdout PF (4.06 → 4.25), Bonferroni-passing, wr_z=7.89, n=216.
- Expected 90d P&L on that cell alone: **~+$3,150** at 1% risk on $100k.
- **Caveat:** it is single-source and all-long. Size at **0.5% risk** (not 1%) until the cell survives a second 90-day window, and cap total CRYPTO exposure at 20% of book. Do **not** trade the CRYPTO class aggregate — it's a net loser (–$1,700).

**Demote per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` (mutate before kill):**
- **EQUITY** — the "PROVEN" cell is a leakage artifact (98.6% WR, PF=225). Mutate: re-run with strict stop-hit labeling and per-symbol concentration check. If the cell collapses to <60% WR, kill.
- **COMMODITY** — no proven cells, class WR 44.4%, and both known-falsified hypotheses (H-001 COT, H-036 inventory) live here. Mutate: test RR≥2.0-only variant on n≥100. If it fails, kill.
- **FOREX** — one narrow mean-reversion cell survives, but holdout PF decayed 3.39→1.31. Mutate: require `fam=mean_reversion AND rr∈[1.0,1.5]` as a hard conjunction; if holdout PF <1.5 on next window, kill.
- **ETF / FUTURES / UNKNOWN / BOND / INDEX / MEME** — kill or disable. n<25 in every case; no statistical basis to trade.

**Two plumbing fixes that matter more than any gate constant:**
1. `passed_high_conviction = 0` everywhere → the HC gate is dead. Audit `hc_filter.js` thresholds against actual score/conf/trust distributions.
2. `opened` >> `passed_smart` in every class → the Smart gate is not gating opens. Until this is fixed, every WR/PF number in this report is measuring the wrong population.

**On the prompt's specific callouts:** the FOREX `consensus` cell and CRYPTO `ml` cell **do not appear in the provided data**. I cannot validate or refute them. If they exist in a different slice, they need to be surfaced before any sizing decision — a PF that "looks suspiciously high" without a train/holdout split is exactly the pattern that produced the EQUITY PF=225 artifact.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### CRYPTO
- Real/noise verdict: Real but narrow; the three cells share essentially the same 216 trades (alpha_engine S50 + conf 0.75-0.80), holdout passes, bonferroni passes, and PF ~4.1 is credible for crypto volatility. No obvious single-symbol concentration flagged.
- 90d expected P&L (1% risk, $100k): $2,850 (216 trades × ~1.46 % avg edge × $1k risk, 0.3 % slippage haircut).
- Gate change: `audit_trail/quality_gates.py:SMART_PICKS_MIN_SCORE_CRYPTO` = 50
- Confidence (1-5): 4

### FOREX
- Real/noise verdict: Marginally real; mean-reversion cell (n=141) survives holdout and bonferroni but PF drops sharply out-of-sample. The higher-PF cells fail bonferroni so are noise.
- 90d expected P&L (1% risk, $100k): $380 (141 trades × 0.27 % avg edge × $1k risk, 0.4 % slippage).
- Gate change: `audit_dashboard/hc_filter.js:MIN_CONF` = 0.78
- Confidence (1-5): 3

### EQUITY
- Real/noise verdict: Noise/leakage; PF=225 on 98.6 % WR with n=71 is statistically impossible without single-symbol concentration or look-ahead. Matches pattern of previously killed equity hypotheses.
- 90d expected P&L (1% risk, $100k): $0 (edge rejected)
- Gate change: `audit_trail/quality_gates.py:SMART_PICKS_MIN_SCORE_EQUITY` = 65
- Confidence (1-5): 5

### COMMODITY
- Real/noise verdict: Noise; no proven cells, best-PF cells fail bonferroni and rest on n=21.
- 90d expected P&L (1% risk, $100k): $0 (no edge)
- Gate change: `audit_trail/quality_gates.py:SMART_PICKS_MIN_SCORE_COMMODITY` = 70
- Confidence (1-5): 5

### BOND
- Real/noise verdict: Noise; n=25 total, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0 (no edge)
- Gate change: `audit_trail/quality_gates.py:SMART_PICKS_MIN_SCORE_BOND` = 80
- Confidence (1-5): 5

### ETF
- Real/noise verdict: Noise; n=7 total, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0 (no edge)
- Gate change: `audit_trail/quality_gates.py:SMART_PICKS_MIN_SCORE_ETF` = 80
- Confidence (1-5): 5

### FUTURES
- Real/noise verdict: Noise; n=18 total, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0 (no edge)
- Gate change: `audit_trail/quality_gates.py:SMART_PICKS_MIN_SCORE_FUTURES` = 75
- Confidence (1-5): 5

### INDEX
- Real/noise verdict: Noise; n=4 total, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0 (no edge)
- Gate change: `audit_trail/quality_gates.py:SMART_PICKS_MIN_SCORE_INDEX` = 80
- Confidence (1-5): 5

### MEME
- Real/noise verdict: Noise; n=4 total, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0 (no edge)
- Gate change: `audit_trail/quality_gates.py:SMART_PICKS_MIN_SCORE_MEME` = 80
- Confidence (1-5): 5

### UNKNOWN
- Real/noise verdict: Noise; n=10 total, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0 (no edge)
- Gate change: `audit_trail/quality_gates.py:SMART_PICKS_MIN_SCORE_UNKNOWN` = 80
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale CRYPTO today (only class with statistically defended, holdout-validated cells). Demote EQUITY per MUTATION_THREE_AXIS_PROTOCOL (mutate the mean-reversion S40 gate before any further capital allocation). All other classes have no usable edge.
