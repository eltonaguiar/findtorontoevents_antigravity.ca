# Pick Funnel Swarm Verdict — 2026-10-04 05:29 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20261004T052846Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-day edge analysis

Before per-class verdicts, three structural observations that color everything below:

1. **`passed_high_conviction = 0` across every class.** The HC gate (`score>=80, conf>=0.75, trust>=60`) is firing on literally zero picks in 90 days. That's not a filter — it's a dead branch. Either the score distribution never reaches 80, or trust never reaches 60, or both. This is the single biggest finding in the funnel.
2. **`passed_verified_alpha` is 0 for 8 of 10 classes.** Only CRYPTO (1795) and FOREX (3) / FUTURES (1) / MEME (1) produce any. So "verified alpha" is effectively a CRYPTO-only gate.
3. **Opened ≫ closed everywhere.** CRYPTO 10256 opened / 2459 closed (24%). FOREX 21320 / 1371 (6.4%). COMMODITY 5695 / 94 (1.7%). The "WR" numbers are computed on a tiny, non-random survivor subset — likely the ones that hit TP/SL fast. **Every WR below is a biased estimator of the true WR of the opened population.** Treat all of them as upper bounds on confidence, not point estimates.

---

### COMMODITY
- **Real/noise verdict:** No PROVEN cells. Best cell (`trust=UNK & rr=RR1.5-2.0 & fam=mean_reversion`, n=20, WR 60%, PF 4.6) fails holdout (n=2) and Bonferroni. The `fam=momentum & score_dec=S50` cell (n=21, PF 4.4) has wr_z=0.218 — pure noise. **No edge.** Also note H-001 (COT leakage) and H-036 (inventory gate) are both formally dead — any "commodity edge" you find here should be assumed to be a recurrence of one of those until proven otherwise.
- **90d expected P&L (1% risk, $100k):** $0. Do not size.
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` — raise aggressively (e.g. 75→85) to stop the 3259/5789 pass-through. The class is producing 5695 opens on 94 closes; the funnel is a firehose with no drain.
- **Confidence (1-5):** 5 (that there is no edge).

### EQUITY
- **Real/noise verdict:** The "98.5% WR, PF 214" cell is **almost certainly leakage or a labeling bug**, not an edge. A 66/67 win rate with PF 214 on `mean_reversion` is not a real market phenomenon — it's what you get when (a) the exit rule is "close at first green tick," (b) the "loss" label is being dropped, or (c) the same underlying symbol is being counted 67 times. The fact that `trust=UNK`, `conf=C<0.60`, and `dir=LONG` all produce the *identical* n=67/wins=66/PF=214.85 confirms these are the same 67 trades sliced three ways — **not three independent confirmations.** Holdout "pass" (PF 99.0, n=31) is meaningless when train and holdout are the same trades re-partitioned. **Flag as leakage recurrence.** Do not trade.
- **90d expected P&L (1% risk, $100k):** $0 until the 67-trade cell is forensically audited. If it survives audit (it won't), the honest number is ~$0 because the rest of EQUITY (n=164 total, 97 trades outside this cell) is roughly coin-flip.
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` — but the real fix is upstream: add a **dedup-by-(symbol, entry_ts, direction)** guard before the edge-cell aggregator runs. The 67-trade cell is a symptom, not the disease.
- **Confidence (1-5):** 5 (that the 98.5% is fake).

### INDEX
- **Real/noise verdict:** n=5 closed. **No edge, no sample.** WR 20% on 5 trades is noise.
- **90d expected P&L (1% risk, $100k):** $0.
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` — raise to effectively disable (or set to a value that produces <50 opens/90d) until n≥100 closed.
- **Confidence (1-5):** 5.

### FOREX
- **Real/noise verdict:** The `conf=C>=0.90 & fam=regime & source=regime_terminal` cell (n=54, WR 68.5%, PF 3.2) **fails holdout** (train_pf=0.298 on n=17, holdout_pf=14.1 on n=37). That train/holdout split is the tell: the "edge" is entirely in the holdout half, which means the split is not random — it's chronological, and the regime source only started producing in the holdout window. **This is a regime-source artifact, not a strategy edge.** Also: 21320 opened / 1371 closed = 6.4% close rate. The WR is computed on the 6% that resolved. **No tradeable edge.** Note the user's prompt flagged FOREX `consensus` — the data here shows `regime_terminal`, not consensus, but the same skepticism applies: any single-source FOREX cell with PF>3 and n<100 should be assumed to be a source artifact until it survives a *random* (not chronological) holdout.
- **90d expected P&L (1% risk, $100k):** $0.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` — the 21749/22691 pass rate (95.8%) is the real problem. Raise to cut pass-through by ~90%. Also add a **per-source cap** so no single source (`regime_terminal`) can dominate a class.
- **Confidence (1-5):** 5.

### BOND
- **Real/noise verdict:** n=33 closed. Best cell n=20, WR 55%, PF 1.64, **holdout_pass=false**, wr_z=0.447. **No edge.**
- **90d expected P&L (1% risk, $100k):** $0.
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` — raise to disable. 3/548 pass_smart is already near-zero; the 515 opens are coming from somewhere else (probably a bypass path). Audit that path.
- **Confidence (1-5):** 5.

### CRYPTO
- **Real/noise verdict:** This is the only class with a **plausibly real** edge. The `conf=C0.75-0.80 & score_dec=S50 & source=alpha_engine` cell: n=182, WR 72%, wr_shrunk 69.8%, PF 3.33, **train_pf 3.05 / holdout_pf 4.52, both n≥39, holdout_pass=true, bonferroni_pass=true, wr_z=5.93.** That's a clean walk-forward. The `dir=LONG` slice (n=181) is the same trades — not independent confirmation, but it does tell you the edge is LONG-only, which is a useful constraint. **Caveat:** the user flagged CRYPTO `ml` cells — the data here shows `alpha_engine`, not `ml`, so the specific concern doesn't apply to this cell. But the same skepticism is warranted: 182 trades over 90d on a single source is ~2/day, which is plausible for a crypto scanner, and the holdout is genuinely out-of-sample. **This is the one cell I'd put real money behind — small.**
- **90d expected P&L (1% risk, $100k):** See sizing below. Rough: 182 trades × 1% risk × avg_pnl 1.34% × (WR 72% − 28% loss side) ≈ **+$8k–$12k** on $100k, before slippage. After realistic crypto slippage (10–20 bps round-trip on 1% risk = ~0.1–0.2% drag per trade × 182 = $1.8k–$3.6k drag), net **~$6k–$9k**. That's a 6–9% return on the account over 90d from one cell. Real, but not life-changing.
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` — **lower** it (or add a carve-out) so that `conf=0.75-0.80 & score_dec=S50 & source=alpha_engine` is *guaranteed* to pass. Right now 3363/12715 pass_smart (26%), but the winning cell is at conf 0.75–0.80 — if the current floor is 0.80, you're cutting the edge. **Set `SMART_PICKS_MIN_CONF_CRYPTO = 0.75`** and add a source-allowlist that includes `alpha_engine`.
- **Confidence (1-5):** 4 (real edge, but small n and single-source concentration risk).

### FUTURES
- **Real/noise verdict:** n=17 closed. **No edge.** H-005 (futures_momentum_anti_signal) is formally dead — do not re-derive.
- **90d expected P&L (1% risk, $100k):** $0.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` — raise to disable.
- **Confidence (1-5):** 5.

### ETF
- **Real/noise verdict:** n=9 closed. **No edge.**
- **90d expected P&L (1% risk, $100k):** $0.
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` — raise to disable.
- **Confidence (1-5):** 5.

### UNKNOWN
- **Real/noise verdict:** n=7 closed, 0 wins. **This is a data-integrity bug, not an asset class.** 1389 scanned, 1382 opened, 7 closed, 0 wins. Something is mislabeling asset class on ingest. Fix the classifier before this class produces another trade.
- **90d expected P&L (1% risk, $100k):** $0.
- **Gate change:** Not a gate — a **classifier fix**. Route UNKNOWN to a quarantine queue, not to the scanner.
- **Confidence (1-5):** 5.

### MEME
- **Real/noise verdict:** n=4 closed. **No edge, no sample.**
- **90d expected P&L (1% risk, $100k):** $0.
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME` — raise to disable until n≥100.
- **Confidence (1-5):** 5.

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY:** **CRYPTO**, and only the single cell `conf=C0.75-0.80 & score_dec=S50 & source=alpha_engine` (LONG-only). Size it at **0.5% risk per trade, not 1%**, because:
- n=182 is real but not huge.
- Single-source concentration (`alpha_engine`) is a key-man risk — if that source degrades, the edge vanishes.
- Crypto slippage on 1% risk is material.
- The holdout is clean, but 90 days is one regime.

Expected: **~$3k–$5k on $100k over 90d** at half-size. That's the honest number. Anyone quoting $10k+ is ignoring slippage and concentration.

**DEMOTE per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` (mutate before kill):** **EQUITY**. The 98.5% WR / PF 214 cell is a leakage recurrence — it must be mutated (dedup guard, exit-rule audit, label audit) before the class is killed, because if the leakage is fixed and the class still shows nothing, you've learned something. If you kill it now, you'll never know whether the 67-trade cell was a bug or a real (if narrow) mean-reversion edge. **Mutate first: add dedup-by-(symbol, entry_ts, direction) and re-run.** If the cell collapses to n<20, kill EQUITY.

**Second demotion candidate:** **FOREX**. 95.8% pass-through on `SMART_PICKS_MIN_SCORE_FOREX` is a gate that isn't gating. Mutate the gate (raise floor, add per-source cap), then re-measure. If WR stays <50% on n≥500, kill.

**Immediate non-negotiable fixes (not gate changes, bugs):**
1. `passed_high_conviction = 0` everywhere — the HC gate is dead. Either fix the thresholds or delete the gate; a gate that never fires is worse than no gate because it creates false confidence in the dashboard.
2. `UNKNOWN` class routing — quarantine, don't trade.
3. Opened/closed ratio — 6–24% close rates mean every WR in this report is a survivor-biased estimate. Add a "resolved within 90d" filter to the funnel before anyone quotes these numbers to a stakeholder.

**Bottom line:** One real edge (CRYPTO, one cell, small). One probable leakage (EQUITY). Eight classes with no edge. The dashboard is currently showing a lot of green that isn't real.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### COMMODITY
- Real/noise verdict: noise (no proven cells; best_pf_overall fail holdout/bonferroni; n=20-21 too small and PF inflated by tiny samples)
- 90d expected P&L (1% risk, $100k): $0 (no usable edge; any deployment would track the observed 49.46% WR on decisive trades)
- Gate change: none (no constant change justified)
- Confidence (1-5): 5

### EQUITY
- Real/noise verdict: noise (PF=214 on n=67 with 98.51% WR is statistically impossible without leakage, single-symbol concentration, or data error; holdout numbers are artifacts)
- 90d expected P&L (1% risk, $100k): -$1,200 (expected loss from mean-reversion cells collapsing under real conditions)
- Gate change: none (do not widen any gate around these cells)
- Confidence (1-5): 5

### INDEX
- Real/noise verdict: noise (n=5 decisive; no proven cells)
- 90d expected P&L (1% risk, $100k): $0
- Gate change: none
- Confidence (1-5): 5

### FOREX
- Real/noise verdict: noise (no proven cells; best_pf_overall fail holdout and bonferroni; regime cells show classic small-n instability)
- 90d expected P&L (1% risk, $100k): $0
- Gate change: none
- Confidence (1-5): 5

### BOND
- Real/noise verdict: noise (no proven cells; best_pf_overall fail holdout/bonferroni)
- 90d expected P&L (1% risk, $100k): $0
- Gate change: none
- Confidence (1-5): 5

### CRYPTO
- Real/noise verdict: real but narrow (three overlapping cells with n=181-182, WR_shrunk 69.8-70.15, PF=3.33, holdout_pass=true, bonferroni_pass=true survive scrutiny; however the PF magnitude remains suspiciously high and should be monitored for alpha_engine leakage)
- 90d expected P&L (1% risk, $100k): +$4,800 (181 trades at ~1.34% avg win, 1% risk, 0.15% estimated slippage per side, net expectancy ~2.7% per trade after costs)
- Gate change: SMART_PICKS_MIN_SCORE_CRYPTO = 50
- Confidence (1-5): 3

### FUTURES
- Real/noise verdict: noise (n=17 decisive; no proven cells)
- 90d expected P&L (1% risk, $100k): $0
- Gate change: none
- Confidence (1-5): 5

### ETF
- Real/noise verdict: noise (n=9 decisive; no proven cells)
- 90d expected P&L (1% risk, $100k): $0
- Gate change: none
- Confidence (1-5): 5

### UNKNOWN
- Real/noise verdict: noise (n=7 decisive; no proven cells)
- 90d expected P&L (1% risk, $100k): $0
- Gate change: none
- Confidence (1-5): 5

### MEME
- Real/noise verdict: noise (n=4 decisive; no proven cells)
- 90d expected P&L (1% risk, $100k): $0
- Gate change: none
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale up TODAY: CRYPTO (only class with statistically surviving cells).  
Demote per MUTATION_THREE_AXIS_PROTOCOL: EQUITY (extreme metrics indicate leakage risk; mutate or remove mean_reversion path before any further allocation). All other classes carry zero actionable edge.
