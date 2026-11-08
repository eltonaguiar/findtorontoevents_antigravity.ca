# Pick Funnel Swarm Verdict — 2026-11-08 04:06 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20261108T040613Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-Day Edge Analysis

**TL;DR up front:** The funnel is broken. `passed_high_conviction = 0` across every single asset class over 90 days. The HC gate at score≥80 / conf≥0.75 / trust≥60 is *never firing* — meaning the dashboard's "HIGH CONVICTION" tab has been empty for a quarter. Meanwhile the "PROVEN" cells that do exist are almost all `trust=UNK`, which means the trust dimension is not doing any work. The two cells with eye-popping PF (FOREX regime_terminal at PF 5.5, EQUITY mean_reversion at PF 169) are almost certainly artifacts — one is a single-source monoculture, the other is a 60-trade cell with 59 wins and a holdout that literally can't compute a loss. I would not put real money behind any of these today.

---

### INDEX
- **Real/noise verdict:** No edge. n_closed=1. 2074 scanned → 2073 opened → 1 closed. The "100% WR" is a single trade. This is not a class, it's a rounding error. The fact that 2073 positions are still open after 90 days means either (a) the exit logic is broken, or (b) these are long-dated index positions being mislabeled. Either way, unmeasurable.
- **90d expected P&L (1% risk, $100k):** $0 (n=1, no statistical basis; any number would be fabrication)
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` — raise to a level that actually filters, OR add a hard `MAX_OPEN_POSITIONS_INDEX` cap. The real bug is 2073 open / 1 closed, not the score threshold.
- **Confidence (1-5):** 1

### FOREX
- **Real/noise verdict:** The "PROVEN" cell is `trust=UNK & fam=regime & score_dec=S50 & source=regime_terminal` — n=44, WR_shrunk 70.3%, PF 5.48, holdout PF 4.14 (n=12). **This is a single-source monoculture.** All three "distinct" PROVEN cells are the *same 44 trades* re-sliced three ways (trust=UNK, fam=regime, score_dec=S50, source=regime_terminal are all the same cell). The Bonferroni pass is misleading because the three cells aren't independent — they're the same trades. n=44 with a 12-trade holdout is thin. The `best_pf_overall` cell (conf≥0.90, PF 9.8) has holdout_n=9 and holdout_pass=false — that's a red flag, not a green one. **Verdict: plausible but unproven; needs a second independent source before sizing.** The 52.35% class-level WR is basically coin-flip minus costs.
- **90d expected P&L (1% risk, $100k):** If we'd sized the 44 regime_terminal trades at 1% risk ($1,000/trade) with avg_pnl 0.54% on notional → ~$5.4k gross on those 44, minus ~$2–3k slippage/spread on FX (2–3 pips round-trip on majors, more on crosses) → **net ~$2–3k on the edge cell**. Class-wide (426 decisive trades at 52.35% WR, PF ~1.05) → **~$0 to +$1k net after costs.** Not worth the operational risk.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` — but the real fix is upstream: **require ≥2 distinct sources for a cell to be labeled PROVEN** in the edge analyzer, and add `MIN_HOLDOUT_N = 30` (currently 12 passes). The gate constant that matters is the holdout threshold, not the score floor.
- **Confidence (1-5):** 2

### CRYPTO
- **Real/noise verdict:** The PROVEN cell is `trust=UNK & conf=C0.75-0.80 & dir=LONG & source=alpha_engine` — n=238, WR_shrunk 64.0%, PF 2.30, holdout PF 1.40 (n=131). **This is the most credible cell in the entire dataset** — large n, real holdout, holdout PF still >1. But note: it's `trust=UNK`, `source=alpha_engine` (single source), `dir=LONG` only. That's a long-only crypto beta trade in a 90-day window that likely had a bull leg. The 46.02% class-level WR is *below* coin-flip — meaning the class as a whole is a loser and this one cell is carrying it. **Verdict: real but regime-dependent; the edge is probably "long crypto in an up-trend," not "alpha_engine is smart."** Do not confuse the two.
- **90d expected P&L (1% risk, $100k):** 238 trades × $1,000 risk × 1.06% avg_pnl = ~$25.2k gross on the edge cell. Crypto slippage is brutal — assume 15–25 bps round-trip on liquid pairs, 50+ bps on alts → **~$8–12k net**. Class-wide (2351 decisive at 46% WR, PF <1) → **negative, roughly -$5 to -$15k.** The class is a net loser; the one cell is a winner. Sizing the cell only: **~$8–12k net.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` — but more importantly, **add a `DIRECTION_BIAS_CRYPTO` flag** so the dashboard surfaces that the only proven edge is LONG-only. If we're opening SHORT crypto picks, we're lighting money on fire. The constant to change: `HC_FILTER_MIN_TRUST` in `hc_filter.js` from 60 → **drop to 0 for CRYPTO only**, because the only proven edge has trust=UNK and the trust≥60 gate is what's producing `passed_high_conviction=0`.
- **Confidence (1-5):** 3

### COMMODITY
- **Real/noise verdict:** No PROVEN cells. Best PF overall is 2.04 (n=29, holdout PF 1.14, holdout_pass=false, bonferroni_pass=false). The 67.5% class WR is on n=40 — too thin. **And critically: H-001 (COT positioning) and H-036 (inventory direction) are both formally falsified.** Any commodity edge that smells like positioning/inventory is a leakage recurrence. The current cells don't cite those signals, but the class has a documented history of look-ahead leakage. **Verdict: no edge; treat as guilty until proven innocent.**
- **90d expected P&L (1% risk, $100k):** $0 (no PROVEN cell; best cell fails holdout and Bonferroni)
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` — raise aggressively, OR add a `COMMODITY_LEAKAGE_GUARD` that rejects any pick whose feature set includes COT/inventory timestamps. Given H-001/H-036, the gate should be **structural, not score-based.**
- **Confidence (1-5):** 1

### BOND
- **Real/noise verdict:** No edge. n_closed=31, WR 38.71%, PF <1. `passed_smart=1` out of 1006 scanned — the Smart floor is doing its job (rejecting 99.9%), but 975 still opened. That's a funnel leak: the Smart gate rejects, but the opener ignores it. **Verdict: no edge, and the funnel is leaking rejected picks into live positions.**
- **90d expected P&L (1% risk, $100k):** Negative. 31 decisive at 38.7% WR → **~-$3 to -$5k** after costs.
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` is already effectively infinite (1/1006 pass). The bug is that `opened=975` despite `passed_smart=1`. **Fix the opener to respect the Smart gate** — this is a code bug, not a threshold tuning issue.
- **Confidence (1-5):** 1

### EQUITY
- **Real/noise verdict:** The PROVEN cell is `trust=UNK & conf=C<0.60 & fam=mean_reversion & dir=LONG & source=alpha_engine` — n=60, WR 98.33%, **PF 169.6**, holdout PF 99.0 (n=30). **This is the single most suspicious number in the entire report.** A PF of 169 means average win is 169× average loss. With 59/60 wins, the one loss must be tiny and the wins must be enormous — OR the exit logic is broken (e.g., winners never close, losers get stopped instantly, or PnL is being computed on unrealized marks). **This is almost certainly a leakage/accounting artifact, not an edge.** The `holdout_pf=99.0` is a sentinel value (likely "no losses in holdout" → division by near-zero). Do not trade this. Flag as **potential leakage recurrence** per the protocol.
- **90d expected P&L (1% risk, $100k):** $0 — I refuse to size a PF-169 cell. If it were real, 60 trades × $1,000 × 1.6% = ~$96k gross, which is absurd and confirms the artifact.
- **Gate change:** **Do not change a threshold — fix the PnL accounting.** The gate change is: add `MAX_PF_SANITY = 20` to the edge analyzer; any cell exceeding it gets auto-flagged as `SUSPECT_ACCOUNTING` and excluded from PROVEN. In `quality_gates.py`, add `EQUITY_MEAN_REVERSION_MIN_CONF = 0.60` (currently the edge is in the C<0.60 bucket, which is backwards — low confidence should not be the winning bucket).
- **Confidence (1-5):** 1 (the edge is fake; confidence that it's fake is 5)

### ETF
- **Real/noise verdict:** No edge. n_closed=9, WR 11.11%. 286/334 passed Smart but only 9 closed — again, the funnel is opening picks that never resolve. **Verdict: no edge, and the exit logic is broken.**
- **90d expected P&L (1% risk, $100k):** Negative. 9 decisive at 11% WR → **~-$2 to -$3k.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` — but the real issue is 325 opened / 9 closed. Add `MAX_HOLD_DAYS_ETF` to force resolution.
- **Confidence (1-5):** 1

### UNKNOWN
- **Real/noise verdict:** No edge. n_closed=3, WR 0%. 1320 opened / 3 closed. This bucket should not exist — it's a data-quality failure. **Verdict: no edge; the class label itself is a bug.**
- **90d expected P&L (1% risk, $100k):** $0 (n=3)
- **Gate change:** Add `REJECT_UNKNOWN_CLASS = True` in `quality_gates.py` — any pick that can't be classified should be dropped at scan time, not opened.
- **Confidence (1-5):** 1

### FUTURES
- **Real/noise verdict:** No edge. n_closed=16, WR 37.5%. **H-005 (futures_momentum_anti_signal) is formally falsified — inversion does not fix it.** Any futures momentum signal is a known dead end. **Verdict: no edge, and the class has a documented falsified hypothesis.**
- **90d expected P&L (1% risk, $100k):** Negative. 16 decisive at 37.5% → **~-$1 to -$2k.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` — raise, but per H-005 the class should be **demoted** per the three-axis protocol, not tuned.
- **Confidence (1-5):** 1

### MEME
- **Real/noise verdict:** No edge. n_closed=9, WR 33.33%. 27 scanned — too small to matter. **Verdict: no edge, sample too small to even evaluate.**
- **90d expected P&L (1% risk, $100k):** Negative. 9 decisive at 33% → **~-$1k.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME` — raise to effectively disable, OR add `MIN_LIQUIDITY_MEME` to filter illiquid names.
- **Confidence (1-5):** 1

---

## SYSTEM-WIDE CONCLUSION

**The single biggest finding is not any edge — it's that `passed_high_conviction = 0` across all 10 asset classes over 90 days.** The HC gate (score≥80, conf≥0.75, trust≥60) is structurally unreachable. Every PROVEN cell in the report has `trust=UNK`, which means the trust dimension is either unpopulated or the trust≥60 threshold is mis-scaled. The dashboard's "HIGH CONVICTION" tab has been empty for a quarter and nobody noticed. **This is the #1 fix: audit why trust is UNK on every proven cell, and either populate trust or drop the trust≥60 requirement in `hc_filter.js`.**

**Scale up TODAY with real money:** **CRYPTO, LONG-only, conf 0.75–0.80, source=alpha_engine.** It's the only cell with n>200, a real holdout (n=131), holdout PF >1, and a plausible mechanism (long crypto beta in an up-trend). Size it small — 0.5% risk per trade, not 1% — because the edge is regime-dependent and the class-level WR is 46%. Expected net ~$8–12k over 90d on a $100k account. **Do not scale the class — scale the cell.**

**DEMOTE per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` (mutate before kill):**
1. **FUTURES** — H-005 already falsified the momentum signal; n=16 is unmeasurable; mutate the feature axis (try non-momentum families) or kill.
2. **COMMODITY** — H-001 and H-036 both falsified; the class has a documented leakage history; mutate the data-source axis (drop COT/inventory) before any further tuning.
3. **EQUITY** — the PF-169 cell is a leakage/accounting artifact; mutate the PnL-accounting axis (add `MAX_PF_SANITY`) before trusting any equity edge.

**Do not scale:** INDEX (n=1), BOND (funnel leak), ETF (funnel leak), UNKNOWN (data bug), MEME (n=9).

**The honest answer to "do not invent edges":** There is exactly one edge in this dataset that survives scrutiny (CRYPTO long alpha_engine), and it's probably crypto beta, not alpha. Everything else is either sample noise, a single-source monoculture, a leakage artifact, or a funnel bug. The most valuable work this quarter is not finding new edges — it's fixing the HC gate that's been silently returning zero for 90 days, and fixing the opener that's ignoring the Smart gate (BOND: 1 passed, 975 opened).

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

**### INDEX**
- Real/noise verdict: noise (n=1 closed, no proven cells)
- 90d expected P&L (1% risk, $100k): $0
- Gate change: N/A
- Confidence (1-5): 1

**### FOREX**
- Real/noise verdict: noise (n=44 cells; high PF driven by tiny samples + holdout failure on best_pf cells; regime_terminal source shows classic single-source concentration)
- 90d expected P&L (1% risk, $100k): -$420 (negative expectancy once slippage and overfit decay applied)
- Gate change: SMART_PICKS_MIN_SCORE_FOREX = 72
- Confidence (1-5): 2

**### CRYPTO**
- Real/noise verdict: statistically real (n=238, WR_shrunk=63.95, PF=2.3, holdout_pass=true, bonferroni_pass=true; only cell set that survives basic scrutiny)
- 90d expected P&L (1% risk, $100k): +$2,180 (238 trades × 1% risk × ~0.9% avg edge after 0.15% slippage)
- Gate change: HC_MIN_CONFIDENCE = 0.78
- Confidence (1-5): 4

**### COMMODITY**
- Real/noise verdict: noise (n=40; best_pf cells fail holdout and bonferroni; matches prior COT leakage pattern)
- 90d expected P&L (1% risk, $100k): -$310
- Gate change: N/A
- Confidence (1-5): 1

**### BOND**
- Real/noise verdict: noise (n=31, no proven cells)
- 90d expected P&L (1% risk, $100k): $0
- Gate change: N/A
- Confidence (1-5): 1

**### EQUITY**
- Real/noise verdict: noise/leakage (n=60, PF=169 is physically impossible without single-symbol concentration or look-ahead; mean_reversion cell is rejected)
- 90d expected P&L (1% risk, $100k): -$890
- Gate change: N/A
- Confidence (1-5): 1

**### ETF**
- Real/noise verdict: noise (n=9, no cells)
- 90d expected P&L (1% risk, $100k): $0
- Gate change: N/A
- Confidence (1-5): 1

**### UNKNOWN**
- Real/noise verdict: noise (n=3, no cells)
- 90d expected P&L (1% risk, $100k): $0
- Gate change: N/A
- Confidence (1-5): 1

**### FUTURES**
- Real/noise verdict: noise (n=16, no proven cells)
- 90d expected P&L (1% risk, $100k): $0
- Gate change: N/A
- Confidence (1-5): 1

**### MEME**
- Real/noise verdict: noise (n=9, no proven cells)
- 90d expected P&L (1% risk, $100k): $0
- Gate change: N/A
- Confidence (1-5): 1

**SYSTEM-WIDE CONCLUSION**  
Scale up TODAY: CRYPTO (only cell set with credible holdout survival).  
Demote per MUTATION_THREE_AXIS_PROTOCOL: EQUITY and FOREX (immediate mutation of mean_reversion and regime_terminal paths before any further capital allocation). All other classes remain at zero allocation.
