# Pick Funnel Swarm Verdict — 2026-10-21 04:11 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20261021T041045Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-Day Edge Analysis

Before per-class verdicts, three structural facts dominate everything below:

1. **`passed_high_conviction = 0` in every single class.** The HC gate (`score>=80, conf>=0.75, trust>=60`) is firing on *zero* trades across 90 days and ~50k scans. Either the gate is mis-wired, or the scoring distribution never reaches 80. This is the single biggest finding in the dataset — the "HIGH CONVICTION" funnel is dead.
2. **`passed_verified_alpha` is 0 for 7 of 10 classes**, and the only classes with any (CRYPTO 1979, FOREX 3, FUTURES 1, MEME 2) don't correlate with the "PROVEN" cells below. The PROVEN cells are being discovered *post-hoc* on closed trades, not gated pre-trade.
3. **Opened ≫ passed_smart in most classes** (EQUITY: 5628 opened vs 220 passed_smart; FOREX: 23335 vs 23793 — ok; BOND: 540 opened vs 0 passed_smart). This means the "opened" count is not downstream of the smart gate. The funnel is not a funnel.

---

### EQUITY
- **Real/noise verdict: NOISE / LEAKAGE.** The PROVEN cell `fam=mean_reversion & score_dec=S40` shows n=64, WR=98.44%, PF=232.85, holdout PF=99.0. A PF of 232 is not a strategy — it is a data artifact. Three red flags: (i) `trust=UNK` on 100% of the winning cell means trust scoring is not populated for these trades; (ii) `conf=C<0.60` — the *lowest* confidence band is the winner, which is the signature of a look-ahead or exit-timing bug (e.g., mean-reversion trades closed on a favorable mark, or a stop that never triggers in backtest); (iii) holdout PF=99.0 is the code's sentinel for "no losing trades in holdout" — with n=24 that's a 1-in-16M event under a true 55% WR. This is almost certainly the same class of bug as [H-001] (COT look-ahead) — a timestamp/exit-fill leakage. **Do not trade this.** The honest read on EQUITY is: 135 closed trades, 70.4% WR, but the "edge" is concentrated in a cell that cannot survive scrutiny. Treat EQUITY as **unproven**.
- **90d expected P&L (1% risk, $100k): $0** — do not size this. If you forced it at the raw 70.4% WR on 135 trades with avg R:R ~1.0 and 1% risk: ~$1,350 gross, but the leakage means the true WR is unknown and likely ≤55%. Expected value under a skeptical prior: **–$500 to +$400**, i.e. noise.
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` — currently the smart gate passes only 220/5763 (3.8%) yet 5628 open. The gate is not binding. Set `SMART_PICKS_MIN_SCORE_EQUITY = 55` and **route all opens through it** (kill the bypass). Also add a hard `trust != UNK` requirement — the winning cell is 100% UNK, which means trust is not being computed for mean_reversion.
- **Confidence (1-5): 1**

### COMMODITY
- **Real/noise verdict: NOISE (borderline).** Best cell `rr=RR>=2.0 & source=alpha_engine`: n=21, WR=71.4%, shrunk 61.0%, PF=4.31, **bonferroni_pass=false**, holdout n=10. n=21 with 10 holdout trades is not enough to distinguish 61% from 50%. The `trust=UNK` again on the top cell. This is *plausible* but unproven — and given [H-001] and [H-036] both killed COMMODITY signals on this exact dataset, the prior should be strongly against. **Not tradeable.**
- **90d expected P&L (1% risk, $100k): $0** — n=21, bonferroni fail. If forced: 21 trades × 1% × (0.61×2.0 − 0.39×1.0) ≈ 21 × $1,000 × 0.83 ≈ **+$1,740**, but the CI on that is roughly ±$3,000. Not distinguishable from zero.
- **Gate change:** `SMART_PICKS_MIN_RR_COMMODITY` — the only signal is RR≥2.0. Currently 3662/5838 pass smart (62.7%), which is absurdly loose. Set `SMART_PICKS_MIN_RR_COMMODITY = 2.0` and `SMART_PICKS_MIN_SCORE_COMMODITY = 60`. This alone would cut the pass rate to ~5% and concentrate on the only cell with any signal.
- **Confidence (1-5): 2**

### FOREX
- **Real/noise verdict: NOISE — and the "best" cell is a textbook small-n artifact.** `conf=C>=0.90 & dir=LONG & source=regime_terminal`: n=28, WR=85.7%, PF=8.89, **train_n=4, train_pf=0.0, holdout_n=24, holdout_pass=false**. The train set has *four trades and zero wins*. The holdout is 24 trades. This is not a walk-forward validation — it's a single 24-trade window that happened to win. `bonferroni_pass=true` is misleading because the effective n is 24, not 28. The class-level WR is 42.6% on 530 decisive trades — **below coin-flip**. FOREX is a losing class overall; the "edge" is one lucky regime window. **Do not trade.**
- **90d expected P&L (1% risk, $100k): –$1,200** (honest estimate from class-level 42.6% WR on 530 trades at ~1:1 R:R: 530 × $1,000 × (0.426 − 0.574) ≈ –$78,400 notional risk-adjusted... let me be careful: 530 trades × 1% risk = $5,300 total risk deployed; at 42.6% WR and 1:1, EV = 530 × $1,000 × (0.426×1 − 0.574×1) = **–$78,400** if every trade risked $1,000. That's the honest number — FOREX is bleeding. The "best cell" would have made ~+$4,000 on 28 trades but is not reproducible.)
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` — currently 23793/24650 pass (96.5%). The gate is a no-op. Set `SMART_PICKS_MIN_SCORE_FOREX = 70` and add `SMART_PICKS_MIN_CONF_FOREX = 0.85`. This will cut FOREX volume by ~95% and stop the bleed. **This is the single highest-impact gate change in the whole system** because FOREX is 23,335 of ~50k opens and is losing money.
- **Confidence (1-5): 1**

### CRYPTO
- **Real/noise verdict: LIKELY REAL, but the headline cell is suspicious.** `conf=C0.75-0.80 & score_dec=S50 & source=alpha_engine`: n=183, WR=78.1%, shrunk 75.4%, PF=4.49, train_pf=5.41 (n=109), holdout_pf=3.33 (n=74), **holdout_pass=true, bonferroni_pass=true, wr_z=7.61**. This is the *only* cell in the entire dataset that survives train/holdout split, Bonferroni, and has n>100. That said: (i) `trust=UNK` again — trust is not populated; (ii) the cell is defined by `score_dec=S50` which is a *decile bucket*, and the fact that the winning bucket is the *middle* decile (S50) rather than the top is a yellow flag — it suggests the score is not monotonic with edge, which is itself a finding; (iii) PF=4.49 with avg_pnl=1.6% and 78% WR implies avg loss ~0.28% — that's a very tight stop, which is where slippage and fill assumptions bite hardest. **Plausibly real, but the 78% WR will not survive live slippage on a 0.28% avg loss.** Discount to ~60-65% live WR, PF ~2.0-2.5.
- **90d expected P&L (1% risk, $100k): +$8,000 to +$12,000** on the 183-trade cell. Math: 183 trades × $1,000 risk × (0.65×1.6 − 0.35×0.28) ≈ 183 × $1,000 × 0.942 ≈ **+$17,200** at backtest WR; at discounted 60% WR and 2× slippage on losses: 183 × $1,000 × (0.60×1.6 − 0.40×0.56) ≈ **+$13,500**. Call it **+$10,000** with slippage buffer. This is the only class where I'd put a positive number with a straight face.
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` — currently 3579/13013 pass (27.5%). The winning cell is `score_dec=S50`, i.e. the *median* decile. The gate should be **narrowed to the S50 band specifically**, not raised. Concretely: add `SMART_PICKS_SCORE_BAND_CRYPTO = (45, 55)` (only pass scores in the 45-55 range) and `SMART_PICKS_MIN_CONF_CRYPTO = 0.75`. This is counterintuitive but the data says the middle decile is the edge, not the top. Also **fix trust scoring** — 100% UNK on the winning cell means the trust dimension is dead.
- **Confidence (1-5): 3**

### ETF
- **Real/noise verdict: NOISE.** n=9 closed, WR=22.2%. No cells. Nothing to say.
- **90d expected P&L (1% risk, $100k): –$500** (9 trades × $1,000 × (0.22 − 0.78) = –$5,040 if all risked $1k; but n=9 is noise). Honest: **$0, do not trade.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` — 306/357 pass (85.7%), gate is a no-op. Set to 65. But with n=9, this is not worth engineering effort. **Demote.**
- **Confidence (1-5): 1**

### BOND
- **Real/noise verdict: NOISE.** 0 passed_smart, 540 opened, 33 closed, WR=39.4%. The smart gate is *blocking everything* and the system is opening anyway. This is a wiring bug, not an edge question.
- **90d expected P&L (1% risk, $100k): –$700** (33 × $1,000 × (0.394 − 0.606) = –$7,000 if all risked $1k; scaled to actual, ~–$700). **Do not trade.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` — currently 0 pass. Either the gate is set impossibly high or BOND scores never reach it. **Investigate why 0/573 pass** before changing the constant. If the gate is correct, the 540 opens are a bypass bug — fix the bypass, don't touch the constant.
- **Confidence (1-5): 1**

### UNKNOWN
- **Real/noise verdict: NOISE / DATA HYGIENE FAILURE.** 1413 scanned, 152 passed_smart, 1410 opened, 3 closed, 0 wins. The existence of an "UNKNOWN" asset class with 1413 scans is itself the finding — 2.8% of the universe is unclassified. **Do not trade.**
- **90d expected P&L (1% risk, $100k): $0** — n=3.
- **Gate change:** Not a constant — add a **hard reject on `asset_class == UNKNOWN`** in `production_scanner.py` before scoring. This is a data-quality gate, not a threshold.
- **Confidence (1-5): 1**

### INDEX
- **Real/noise verdict: NOISE.** 1488/1831 pass smart (81%), 5 closed, WR=20%. Gate is a no-op, sample is nothing.
- **90d expected P&L (1% risk, $100k): $0** — n=5.
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` — set to 70. But again, n=5 means this is not where effort goes.
- **Confidence (1-5): 1**

### FUTURES
- **Real/noise verdict: NOISE.** n=16 closed, no cells, and [H-005] already killed the futures momentum signal. Nothing here.
- **90d expected P&L (1% risk, $100k): –$200** (16 × $1,000 × (0.4375 − 0.5625) = –$2,000 if all risked $1k; scaled, ~–$200). **Do not trade.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` — 149/199 pass (75%), set to 70. Low priority.
- **Confidence (1-5): 1**

### MEME
- **Real/noise verdict: NOISE.** n=7 closed, WR=14.3%. Nothing.
- **90d expected P&L (1% risk, $100k): –$300** (7 × $1,000 × (0.143 − 0.857) = –$5,000 if all risked $1k; scaled, ~–$300). **Do not trade.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME` — 13/29 pass (45%), set to 70. Or just **disable MEME entirely** — 29 scans in 90 days is not a class, it's a rounding error.
- **Confidence (1-5): 1**

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY with real money: CRYPTO — and only CRYPTO, and only the S50 band, and only at half-size until live slippage is measured.** It is the only class with (a) n>100 on the winning cell, (b) a passing train/holdout split, (c) a passing Bonferroni correction, and (d) a class-level WR (45.2%) that is at least in the same zip code as the cell WR (78.1%) — the gap is explainable by selection, not by leakage. Expected 90d P&L at 1% risk on $100k: **+$10,000** (discounted for slippage). Start at 0.5% risk until 50 live trades confirm WR ≥ 60%.

**Demote per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` (mutate before kill): FOREX.** It is 23,335 of ~50k opens (47% of system volume), it is losing money at class level (42.6% WR on 530 decisive trades), its "best" cell has train_n=4 and holdout_pass=false, and its smart gate passes 96.5% of scans — i.e. the gate is doing nothing. **Mutation axis 1 (threshold):** raise `SMART_PICKS_MIN_SCORE_FOREX` from current to 70 and add `SMART_PICKS_MIN_CONF_FOREX = 0.85`. **Mutation axis 2 (universe):** restrict FOREX to the `regime_terminal` source only (the only source with any signal, even if small-n). **Mutation axis 3 (sizing):** cut FOREX risk-per-trade to 0.25% during the mutation window. If after 90 days the mutated FOREX still shows WR < 50% on n≥100, **kill it** — do not re-mutate. The prior from [H-035] (funding/settlement sign instability) and the class-level 42.6% WR both point to "no edge, stop paying for it."

**Second demotion: EQUITY.** The 98.4% WR / PF=232 cell is a leakage artifact (same signature as [H-001]: UNK trust, low-conf band winning, holdout PF=99 sentinel). Do not trade it. Mutate by adding a `trust != UNK` hard requirement and re-running the cell discovery — if the edge survives with trust populated, it's real; if it vanishes, it was leakage.

**The meta-finding the user should act on first:** `passed_high_conviction = 0` across all 10 classes and ~50k scans. The HC gate in `hc_filter.js` (`score>=80, conf>=0.75, trust>=60`) is either mis-wired or the scoring distribution never reaches 80. **Before any of the above gate changes

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

**### EQUITY**
- Real/noise verdict: Noise/leakage. n=64, WR_shrunk=86.9, PF=232.85 is statistically impossible in live equity mean-reversion without single-symbol concentration or look-ahead; holdout PF=99.0 confirms fabrication.
- 90d expected P&L (1% risk, $100k): $0 (edge rejected).
- Gate change: SMART_PICKS_MIN_SCORE_EQUITY = 75
- Confidence (1-5): 1

**### CRYPTO**
- Real/noise verdict: Marginally real. n=183, WR_shrunk=75.37, PF=4.485 with holdout_pass=true and bonferroni_pass=true; alpha_engine source reduces (but does not eliminate) single-model leakage risk.
- 90d expected P&L (1% risk, $100k): ~$2,900 (183 trades × 1% risk × 1.60% avg_pnl, 0.4% slippage, 0.3% commission).
- Gate change: HC_MIN_CONFIDENCE = 0.78
- Confidence (1-5): 3

**### FOREX**
- Real/noise verdict: Noise. No proven cells; best_pf cells fail holdout_pass and have train_n=4.
- 90d expected P&L (1% risk, $100k): $0 (edge rejected).
- Gate change: SMART_PICKS_MIN_SCORE_FOREX = 65
- Confidence (1-5): 1

**### COMMODITY**
- Real/noise verdict: Noise. No proven cells; best_pf cells fail bonferroni_pass.
- 90d expected P&L (1% risk, $100k): $0 (edge rejected).
- Gate change: SMART_PICKS_MIN_SCORE_COMMODITY = 70
- Confidence (1-5): 1

**### FUTURES**
- Real/noise verdict: Noise. n_closed=16 < 20 threshold; no proven cells.
- 90d expected P&L (1% risk, $100k): $0 (edge rejected).
- Gate change: SMART_PICKS_MIN_SCORE_FUTURES = 80
- Confidence (1-5): 1

**### ETF / BOND / INDEX / MEME / UNKNOWN**
- Real/noise verdict: Noise. All n_closed < 20 or zero proven cells.
- 90d expected P&L (1% risk, $100k): $0 (edge rejected).
- Gate change: HC_MIN_TRUST = 70
- Confidence (1-5): 1

**SYSTEM-WIDE CONCLUSION**  
Scale CRYPTO today (only cell with credible n + holdout). Demote EQUITY immediately per MUTATION_THREE_AXIS_PROTOCOL.md (mutate the mean_reversion path before any further capital allocation). All other classes have no actionable edge.
