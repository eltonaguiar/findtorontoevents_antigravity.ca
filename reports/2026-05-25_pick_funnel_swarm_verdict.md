# Pick Funnel Swarm Verdict — 2026-11-16 04:49 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20261116T044932Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-Day Edge Analysis

Before per-class verdicts, three system-wide facts that dominate everything below:

1. **`passed_high_conviction = 0` across every single asset class.** The HC gate (`score>=80 & conf>=0.75 & trust>=60`) is firing on **zero** trades in 90 days. Either the gate is mis-wired, or the scoring distribution never reaches 80. This is the single most important finding — the "HIGH CONVICTION" funnel is dead.
2. **`passed_verified_alpha` is 0 for 7 of 10 classes.** Only CRYPTO (2406), FOREX (9), FUTURES (1), MEME (3) ever pass. The verified-alpha gate is effectively a CRYPTO-only gate.
3. **Opened ≫ closed everywhere.** COMMODITY: 5805 opened / 36 closed (0.6%). EQUITY: 5696/106 (1.9%). INDEX: 2102/1. The "closed" sample is a tiny, non-random survivor subset — likely only trades that hit a hard exit. **Every WR number below is computed on a biased subsample.** Treat all WRs as upper bounds on true WR, not point estimates.

---

### COMMODITY
- **Real/noise verdict:** NOISE / UNPROVEN. Best cell (`trust=UNK & dir=LONG & source=alpha_engine`) has n=27, WR_shrunk 57.45%, PF 2.04 — but **holdout_pf=1.137, holdout_pass=false, bonferroni_pass=false, wr_z=1.35**. That is a coin-flip with a lucky train window. The 69.44% headline WR is on 36 closed trades out of 5805 opened — pure survivor bias. Also note H-001 (COT leakage, 85% cotton concentration) and H-036 (inventory gate rejected) are both COMMODITY — this class has a documented history of leakage-driven fake edges. Do not trust any COMMODITY cell until the closed-sample problem is fixed.
- **90d expected P&L (1% risk, $100k):** **$0.** No tradeable edge. If forced to size the "best" cell at 1% risk × 27 trades × 0.80% avg_pnl ≈ **+$2,160 gross**, but holdout PF 1.14 means expected ≈ **$0 ± $3k**. Not investable.
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` — raise aggressively (e.g. 65→75) to cut the 3737/5841 (64%) pass rate. A 64% pass rate is not a filter, it's a rubber stamp.
- **Confidence (1-5):** 1

### EQUITY
- **Real/noise verdict:** **LEAKAGE FLAG — DO NOT TRADE.** The "PROVEN" cell `rr=RR>=2.0 & fam=mean_reversion` shows WR=97.37% (37/38), PF=135.6, wr_z=5.84, bonferroni_pass=true. **PF of 135 on a mean-reversion equity strategy is not a real edge — it is a data artifact.** Three specific red flags: (i) `trust=UNK` on 100% of the winning cell — the trust field is unpopulated, so the "trust band" dimension is meaningless; (ii) the three "top edges" are the *same 38 trades* re-sliced three ways (identical n, wins, PF, wr_z) — this is one cell, not three independent confirmations; (iii) PF=135 implies avg win / avg loss ≈ 135× on a mean-reversion strategy, which is mathematically impossible without either a look-ahead exit or a mis-scaled PnL field. **This is the same signature as H-001 (COT leakage): a too-good cell that collapses on timestamp fix.** Treat as suspected leakage recurrence until the PnL field and exit timestamps are audited.
- **90d expected P&L (1% risk, $100k):** **$0 (do not size).** If the cell were real at 1% risk × 38 trades × 1.59% avg = **+$60,420** — which is exactly why it's suspicious. A 60% return on a $100k account from 38 mean-reversion equity trades in 90 days is not a real edge.
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` — the 227/5802 (3.9%) pass rate is actually reasonable, but the **real fix is upstream**: add a `trust != UNK` requirement to the PROVEN promotion logic in `quality_gates.py`. A cell with 100% UNK trust should never be promotable.
- **Confidence (1-5):** 1 (edge is fake; confidence that it's fake is 5)

### INDEX
- **Real/noise verdict:** **NO DATA.** n_closed=1. 100% WR on one trade is not a statistic. 2102 opened / 1 closed means the exit logic is broken for INDEX — trades are not closing. Cannot evaluate.
- **90d expected P&L (1% risk, $100k):** **$0 (n=1).**
- **Gate change:** Fix the exit/close pipeline for INDEX before touching any gate. `SMART_PICKS_MIN_SCORE_INDEX` is irrelevant when 99.95% of opened trades never close.
- **Confidence (1-5):** 1

### FOREX
- **Real/noise verdict:** **NOISE — and the "best" cell is a textbook overfit.** `trust=UNK & conf=C>=0.90 & fam=regime` shows WR 89.47%, PF 14.4, wr_z=4.87, bonferroni_pass=true — **but holdout_pass=false (holdout_pf=99.0 on n=8, train_pf=10.5 on n=30).** A holdout PF of 99.0 on 8 trades is a degenerate artifact (likely zero/near-zero losses in a tiny holdout). The cell is 100% `trust=UNK` and 100% `source=regime_terminal` — a single source, single family. This is the "consensus/regime" cell the prompt flagged, and it fails the holdout. **Not real.** The 51.47% headline WR on 441 closed (out of 25,296 opened — 1.7% close rate) is the only honest number, and it's a coin flip.
- **90d expected P&L (1% risk, $100k):** **$0.** At 51.47% WR with unknown avg R, expected is ≈ breakeven minus costs. The "best" cell at 1% × 38 × 0.70% = +$2,660 gross, but holdout failure means **$0 expected, negative after slippage.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` — 25,966/26,621 (97.6%) pass rate is the worst in the system. This gate is not filtering anything. Raise to a value that cuts pass rate to <20% (likely 70→80+). Also: the `regime_terminal` source should be quarantined pending holdout audit.
- **Confidence (1-5):** 1

### CRYPTO
- **Real/noise verdict:** **WEAK-BUT-PLAUSIBLE — the only class with a defensible edge, and it still fails Bonferroni.** Best cell `rr=RR1.5-2.0 & source=alpha_engine`: n=192, WR 58.85%, WR_shrunk 58.02%, PF 2.00, **holdout_pf=1.45 (holdout_pass=true)**, wr_z=2.45, **bonferroni_pass=false**. This is the *only* cell in the entire dataset that passes holdout. But: (i) bonferroni fails — with ~dozens of cells tested, a z=2.45 is expected by chance; (ii) the three "top edges" are again the same 192 trades re-sliced; (iii) 44.66% headline WR on 2264 closed (out of 9914 opened — 23% close rate, the best in the system) is *below* 50%, meaning the class as a whole loses money and only this one RR-band/source slice is positive. The prompt flagged "CRYPTO ml cells" — note the winning cell is `source=alpha_engine`, not `ml`; if an `ml` cell exists elsewhere it's not in the top-3 and should be treated as suspect. **Verdict: real-ish but unproven; needs one more 90d window before sizing.**
- **90d expected P&L (1% risk, $100k):** At 1% risk × 192 trades × 1.13% avg_pnl = **+$21,700 gross**. Apply holdout haircut (PF 2.0→1.45) and 5bps slippage × 192 round-trips on $100k notional ≈ −$9,600 → **net ≈ +$12,000**, but with bonferroni failure the honest expected value is **$0 to +$12k, wide CI.** Size at 0.25% risk, not 1%, until confirmed: **≈ +$3,000.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` — 3802/12192 (31%) pass rate is the most reasonable in the system, but the *real* lift is to **add `rr >= 1.5` as a hard precondition** in `quality_gates.py` for CRYPTO (the edge lives entirely in the RR1.5-2.0 band). If a constant must be named: introduce `CRYPTO_MIN_RR = 1.5` and gate on it.
- **Confidence (1-5):** 3

### ETF
- **Real/noise verdict:** **NO EDGE — actively negative.** 1 win / 6 losses, WR 14.29% on n=7. Too small to be statistically meaningful, but the direction is bad and there's no cell with n≥20. Do not trade.
- **90d expected P&L (1% risk, $100k):** **Negative.** At 14% WR, expected ≈ **−$2k to −$4k** if sized. **$0 recommended.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` — 273/312 (87.5%) pass rate is absurd. Raise hard (e.g. 60→80) or **disable ETF picks entirely** until n≥50 closed.
- **Confidence (1-5):** 1

### UNKNOWN
- **Real/noise verdict:** **NO EDGE — 0/3 wins.** n=3. This is a data-hygiene bucket, not an asset class. 1282 opened / 3 closed means the classifier is dumping unclassifiable picks here and they're not closing. Should be **excluded from the funnel entirely**, not scored.
- **90d expected P&L (1% risk, $100k):** **$0 (n=3, 0 wins).**
- **Gate change:** Add `asset_class != UNKNOWN` as a hard reject in `quality_gates.py` before scoring. This is a routing bug, not a gate tuning issue.
- **Confidence (1-5):** 1

### BOND
- **Real/noise verdict:** **NO EDGE.** 12W/19L, WR 38.71% on n=31. Below 50%, no cell with n≥20, no PROVEN. 1136 opened / 31 closed (2.7% close rate). Not tradeable.
- **90d expected P&L (1% risk, $100k):** **Negative.** At 38.7% WR, expected ≈ **−$3k to −$5k** if sized. **$0 recommended.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` — 1/1167 (0.09%) pass rate means the gate is already effectively closed; the problem is 1136 trades still *opened* despite failing the gate. **The gate is not wired to the open path.** Fix the wiring, not the constant.
- **Confidence (1-5):** 1

### FUTURES
- **Real/noise verdict:** **NO EDGE.** 6W/10L, WR 37.5% on n=16. H-005 (futures_momentum_anti_signal) already failed. No PROVEN cell. 154 opened / 16 closed.
- **90d expected P&L (1% risk, $100k):** **Negative.** ≈ **−$1k to −$2k** if sized. **$0 recommended.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` — 122/170 (72%) pass rate is too loose for a class with 37.5% WR. Raise to cut pass rate <25%.
- **Confidence (1-5):** 1

### MEME
- **Real/noise verdict:** **NO EDGE.** 2W/4L, WR 33.33% on n=6. n too small, direction bad. 14 opened / 6 closed.
- **90d expected P&L (1% risk, $100k):** **Negative.** ≈ **−$1k** if sized. **$0 recommended.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME` — 8/20 (40%) pass rate on a 33% WR class. Raise hard or disable.
- **Confidence (1-5):** 1

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY with real money: CRYPTO — and only CRYPTO, and only at 0.25% risk, not 1%.** It is the only class where (a) the close rate is non-trivial (23%), (b) a cell passes holdout (PF 1.45), and (c) the headline WR (44.66%) is at least in the same zip code as the winning cell's WR (58.85%) — meaning the edge is a *slice* of a real distribution, not a hallucination. Expected net at 0.25% risk: **≈ +$3,000 over 90d**, with wide CI. Do not size to 1% until a second 90d window confirms and bonferroni passes.

**DEMOTE per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` (mutate before kill): EQUITY.** The PF=135 cell is a leakage recurrence with the exact signature of H-001 — 100% `trust=UNK`, three "independent" cells that are the same 38 trades, and a PF that is physically impossible for mean-reversion. **Do not kill EQUITY outright** (the 72.64% headline WR on 106 closed is intriguing) — instead mutate the *trust axis*: require `trust != UNK` for any cell to be promotable, and audit the PnL field and exit timestamps on the 38-trade cell. If the cell survives a timestamp fix, it's real; if it collapses to PF<1.5, it's H-001 all over again and EQUITY gets killed.

**Second demotion: FOREX.** 97.6% pass rate, 51.47% WR, holdout-failing "best" cell. Mutate the `regime_terminal` source axis (quarantine it) and tighten `SMART_PICKS_MIN_SCORE_FOREX` before considering kill.

**The meta-finding the user needs to hear:** `passed_high_conviction = 0` across all 10 classes means the HC gate is either mis-configured or the scoring distribution never reaches 80. **No gate change below matters until that is diagnosed.** The funnel's "HIGH CONVICTION" tier is currently a null set — every dollar of real money is being deployed by the *Smart* tier, which passes 64% of COMMODITY and 97.6% of FOREX. That is not a funnel; it is a firehose with a decorative nozzle. Fix the HC gate wiring first, then re-run this 90d analysis.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### COMMODITY
- Real/noise verdict: noise — no proven cells; best_pf cells fail holdout and bonferroni; n too small for any claim.
- 90d expected P&L (1% risk, $100k): $0 (no usable edge).
- Gate change: SMART_PICKS_MIN_SCORE_COMMODITY = 75
- Confidence (1-5): 5

### EQUITY
- Real/noise verdict: noise — the three "proven" cells are the same 38 trades with PF=135 and WR=97%; impossible without leakage or single-symbol concentration (mean_reversion on one ticker).
- 90d expected P&L (1% risk, $100k): $0 (edge is statistical artifact).
- Gate change: SMART_PICKS_MIN_SCORE_EQUITY = 85
- Confidence (1-5): 5

### INDEX
- Real/noise verdict: noise — n_closed=1, no cells.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: none (class too thin)
- Confidence (1-5): 5

### FOREX
- Real/noise verdict: noise — top cells fail holdout_pass; PF=14.4 on n=38 is classic small-sample inflation; no bonferroni-safe proven edges.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: HC_MIN_CONF_FOREX = 0.92
- Confidence (1-5): 5

### CRYPTO
- Real/noise verdict: noise — best_pf cells have bonferroni_pass=false and modest holdout PF drop; no proven cells survive.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: SMART_PICKS_MIN_SCORE_CRYPTO = 70
- Confidence (1-5): 5

### ETF
- Real/noise verdict: noise — n_closed=7, empty cells.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: none
- Confidence (1-5): 5

### UNKNOWN
- Real/noise verdict: noise — n_closed=3, empty cells.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: none
- Confidence (1-5): 5

### BOND
- Real/noise verdict: noise — n_closed=31, no proven cells.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: SMART_PICKS_MIN_SCORE_BOND = 60
- Confidence (1-5): 5

### FUTURES
- Real/noise verdict: noise — n_closed=16, empty cells.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: none
- Confidence (1-5): 5

### MEME
- Real/noise verdict: noise — n_closed=6, empty cells.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: none
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale up: none. Demote: EQUITY and CRYPTO (remove from alpha_engine production_scanner.py until n>200 and holdout-stable cells appear). All other classes already produce no actionable edge.
