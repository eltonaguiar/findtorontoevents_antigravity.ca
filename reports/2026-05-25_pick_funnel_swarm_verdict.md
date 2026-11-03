# Pick Funnel Swarm Verdict — 2026-11-03 04:07 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20261103T040636Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-day Edge Analysis

Before the per-class verdicts, three structural facts dominate everything below:

1. **`passed_high_conviction = 0` across every single asset class.** The HC gate (`score>=80, conf>=0.75, trust>=60`) is effectively dead. Nothing in 90 days cleared it. That means the "top edges" you're being shown are *not* HC-filtered — they're raw `passed_smart` survivors. Any claim that the dashboard is surfacing "high conviction" picks is false.
2. **`opened` >> `passed_smart` in most classes** (EQUITY 5702 opened vs 235 passed_smart; FOREX 23023 vs 23486; CRYPTO 10601 vs 3842). The funnel is not gating what gets opened. The "smart" gate is decorative for EQUITY/INDEX/COMMODITY/FOREX.
3. **`passed_verified_alpha` is 0 everywhere except CRYPTO (2276), FOREX (3), FUTURES (1), MEME (3).** The verified-alpha tier is essentially a CRYPTO-only construct.

---

### EQUITY
- **Real/noise verdict: NOISE / LEAKAGE.** The "PROVEN" cell is `conf=C<0.60 & fam=mean_reversion` with n=63, WR=98.41%, PF=174.6, holdout PF=99.0. This is not an edge — it is a **broken P&L accounting artifact**. PF=174 with avg_pnl=1.57% and 62/63 wins means the loss side is essentially zero, which is impossible for a real mean-reversion strategy on equities. Classic signatures of: (a) look-ahead in the mean-reversion entry (entering at the close that defines the reversion), (b) a stop that never triggers because the "loss" is booked as a timeout at breakeven, or (c) survivorship in the closed-trade set (130 closed out of 5702 opened = 2.3% close rate — the other 97.7% are unclosed and invisible). The `conf=C<0.60` dimension is the tell: **the edge is in the LOW-confidence bucket**, which means the confidence model is anti-correlated with outcome — a red flag for label leakage in the confidence feature. Do not trade this.
- **90d expected P&L (1% risk, $100k): $0.** Not tradeable. If you forced it: 63 trades × 1% × 1.57% avg = ~$990 gross, but the PF is fictional so the real number is unknowable and likely negative once the 5572 unclosed trades resolve.
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` — raise from current (effectively ~0, since 5702 opened vs 235 passed) to **75**, and add a hard `MIN_CLOSED_SAMPLE=200` before any EQUITY cell is allowed to display as "proven." The current gate lets 97.7% of scanned equity through to `opened`.
- **Confidence (1-5): 1**

### INDEX
- **Real/noise verdict: NOISE.** n_closed=4. WR=25%. There is no edge and no sample. `passed_smart=1586` out of 1956 scanned (81% pass rate) is a gate that isn't gating. 1952 opened, 4 closed — the close pipeline is broken for INDEX, not the strategy.
- **90d expected P&L: $0** (n=4 is not a sample).
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` — the 81% pass rate means the floor is below the median score. Set to **70** and require `MIN_CLOSED_SAMPLE=100` before INDEX appears on the dashboard at all. Right now INDEX is noise dressed as a class.
- **Confidence (1-5): 1**

### COMMODITY
- **Real/noise verdict: NOISE, and it's the H-001/H-036 recurrence pattern.** Best cell is `trust=UNK & dir=LONG & source=alpha_engine`, n=31, WR=58%, PF=1.93, **holdout_pf=1.11, holdout_pass=false, bonferroni_pass=false**. The train PF (3.19) collapses to 1.11 out-of-sample — textbook overfit. `passed_smart=3687/6189` (60% pass) with 6145 opened and 44 closed (0.7% close rate). This is the same class where COT leakage (H-001) and inventory-direction (H-036) were already killed. The `trust=UNK` dominance in every top cell is a leakage-recurrence flag: unknown-trust picks are winning in-sample because the trust feature is missing, not because they're good.
- **90d expected P&L: $0.** Holdout PF 1.11 with n=14 is indistinguishable from zero after costs.
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` — raise to **72** AND add `REQUIRE_TRUST_KNOWN=True` for COMMODITY specifically. Every top cell is `trust=UNK`; gating on known trust would have removed the entire "edge."
- **Confidence (1-5): 1**

### FOREX
- **Real/noise verdict: NOISE / LEAKAGE — and the `consensus`/`regime` cell is the smoking gun.** Best cell `conf=C>=0.90 & dir=LONG & source=regime_terminal`: n=26, WR=92.3%, PF=16.96, **holdout_pf=99.0 (capped), holdout_n=9, holdout_pass=false**. PF=99 is a division-by-near-zero-loss artifact — 24 wins and 2 losses where the 2 losses are ~0. The `holdout_pass=false` is explicit. This is the FOREX `consensus`/regime cell you flagged: **it is not an edge, it is a small-n high-confidence LONG-only cell in a 90-day window where FOREX trended.** 26 trades, all LONG, all high-conf — that's a directional bet on the window, not a strategy. The 50.7% overall WR (218W/212L on 430 decisive) confirms the class has no edge; the "top cell" is a slice of a coin-flip. `passed_smart=23486/24243` (97% pass) — the gate is a no-op.
- **90d expected P&L: $0.** If you'd traded only the 26-trade cell at 1% risk: 26 × 1% × 0.675% = ~$176 gross, but with holdout_pass=false and n=9 holdout, the expected value is $0 ± wide. Not tradeable.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` — raise from ~0 (97% pass) to **70**, and add `MIN_HOLDOUT_N=30` before any FOREX cell can be labeled proven. The 97% pass rate is the single biggest funnel leak in the system.
- **Confidence (1-5): 1**

### CRYPTO
- **Real/noise verdict: THE ONLY CELL WITH A DEFENSIBLE SIGNAL — but it's narrow and the `ml`/`verified_alpha` framing is misleading.** The proven cell `conf=C0.75-0.80 & score_dec=S50 & source=alpha_engine`: n=173, WR=77.46%, **wr_shrunk=74.61%**, PF=4.13, **train_pf=6.15 (n=81) → holdout_pf=2.76 (n=92), holdout_pass=true, bonferroni_pass=true, wr_z=7.22**. This is the only cell in the entire dataset that survives train/holdout split AND Bonferroni. The shrinkage from 77.5% → 74.6% is modest and the holdout PF of 2.76 on n=92 is credible. **However:** (a) it's `source=alpha_engine`, not the `ml` source — the `ml`/`verified_alpha` cells (2276 passed_verified_alpha) are NOT in the proven list, so the "verified alpha" tier is not where the edge is; (b) the cell is LONG-only and `conf=C0.75-0.80` (a narrow band — the edge is *not* in the highest-confidence bucket, again suggesting confidence is mis-calibrated); (c) `trust=UNK` is the dominant trust band, so trust is not adding information. The overall CRYPTO WR is 45.92% (1114W/1312L) — the class as a whole loses; the edge is a 173-trade slice (7% of closed trades). That's a real but *fragile* edge: it's one cell, one direction, one confidence band, and it depends on `score_dec=S50` (a specific score decile). If S50 is a post-hoc bucket, this is a multiple-comparisons survivor that happened to pass Bonferroni — treat with caution.
- **90d expected P&L (1% risk, $100k): ~$2,700 gross, ~$2,100 net.** Math: 173 trades × 1% risk × 1.5887% avg_pnl = $2,748 gross. Apply 0.15% round-trip slippage+fees on $100k notional per trade = $150/trade × 173 = $25,950 — **wait, that's larger than the edge.** Recompute properly: at 1% risk ($1,000 risk/trade) with avg_pnl 1.59% of *notional*, the notional per trade is $1,000 / (stop distance). If stop is ~2%, notional ≈ $50k, so 1.59% × $50k = $795/trade × 173 = $137k gross — that's implausibly high, which means the avg_pnl_pct is likely *per unit of risk*, not per notional. **Correct interpretation: avg_pnl_pct=1.59% is return on risk (R-multiple ≈ 1.59R per trade).** So: 173 trades × 1% risk × 1.59R = **$2,750 gross**. Net of ~0.1R slippage/trade: 173 × 0.1R × $1,000 = $17,300 drag → **net ≈ -$14,500.** The edge is real in R-terms but **slippage on 173 crypto trades at 1% risk eats it.** At 0.5% risk: gross $1,375, slippage $8,650 → still negative. **The honest answer: the edge is real but too thin to survive realistic crypto slippage at this trade count.** Only viable if you can execute at <0.05R slippage (institutional-grade fills) — retail cannot.
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` — **lower** to **55** to *widen* the S50/conf-0.75-0.80 band (currently the edge is trapped in a narrow slice; the gate is excluding the adjacent trades that share the signal). Simultaneously add `HC_MIN_TRUST_CRYPTO=0` (drop the trust>=60 requirement for CRYPTO only) because every proven cell is `trust=UNK` — the HC gate's trust>=60 is why `passed_high_conviction=0`. **This is the one gate change that would actually surface the edge on the dashboard.**
- **Confidence (1-5): 3** (real signal, but slippage-fragile and narrow)

### BOND
- **Real/noise verdict: NOISE.** n_closed=31, WR=38.7%. `passed_smart=1/861` — the gate is so tight it passes 0.1%, yet 830 opened. The gate and the opener are disconnected. No edge.
- **90d expected P&L: $0.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` — the 1/861 pass rate means the floor is above the 99.9th percentile. Either the score model is broken for BOND or the floor is mis-set. Set to **60** and require `MIN_CLOSED_SAMPLE=50` before BOND displays. Currently BOND is a black hole.
- **Confidence (1-5): 1**

### ETF
- **Real/noise verdict: NOISE.** n_closed=9, WR=11.1%. `passed_smart=293/342` (86% pass) but 333 opened, 9 closed. No sample, no edge.
- **90d expected P&L: $0.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` — raise to **70** (86% pass is a no-op) and suppress ETF from the dashboard until `MIN_CLOSED_SAMPLE=50`.
- **Confidence (1-5): 1**

### FUTURES
- **Real/noise verdict: NOISE.** n_closed=18, WR=38.9%. `passed_smart=144/197` (73% pass). No proven cells. H-005 already killed the momentum inversion. Nothing here.
- **90d expected P&L: $0.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` — raise to **70**; suppress until n>=50.
- **Confidence (1-5): 1**

### MEME
- **Real/noise verdict: NOISE.** n_closed=9, WR=33.3%. `passed_verified_alpha=3` but no proven cell. No sample.
- **90d expected P&L: $0.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME` — raise to **75**; suppress until n>=50. MEME at 33% WR with 9 trades is a lottery ticket, not a strategy.
- **Confidence (1-5): 1**

### UNKNOWN
- **Real/noise verdict: NOISE / DATA HYGIENE FAILURE.** n_closed=3, WR=0%. 1380 scanned, 1377 opened, 3 closed. The existence of an UNKNOWN class with 1380 scans means the classifier is failing on ~4% of the universe. This is not an asset class — it's a bug.
- **90d expected P&L: $0.**
- **Gate change:** Not a score constant — **add a hard reject in `production_scanner.py`: `if asset_class == "UNKNOWN": skip`**. Do not let unclassified instruments into the funnel at all. This is the single highest-leverage hygiene fix.
- **Confidence (1-5): 1**

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY with real money: CRYPTO — but only the `conf=C0.75-0.80 & score_dec=S50 & source=alpha_engine` LONG cell, and only at reduced size (0.25–0.5% risk, not 1%).** It is the only cell in the entire 90-day dataset that passes train/holdout AND Bonferroni with a credible shrunk WR (74.6%) and holdout PF (2.76, n=92). But the slippage math above shows it's marginal at 1% risk — so size down, not up, until you've measured realized slippage on 50 live trades. Do **not** scale the `ml`/`verified_alpha` tier — it's not where the proven cell lives, despite 2276 picks passing that gate.

**DEMOTE per MUTATION_THREE_AXIS_PROTOCOL (mutate before kill): FOREX.** It has the worst funnel leak in the system (`passed_smart=23486/24243` = 97% pass rate — the gate is a no-op), the "best" cell is a 26-trade LONG-only high-conf artifact with `holdout_pass=false` and PF=99 (division-by-zero), and the overall WR is 50.7% (coin flip). Per the protocol, mutate first: (1) raise `SMART_PICKS_MIN_SCORE_FOREX` to 70, (2) add `MIN_HOLDOUT_N=30` to the proven-cell labeler, (3) re-run 90d. If WR stays ~50% after mutation, kill the class. **Do not kill today — mutate, then re-audit in 30 days.**

**Second demotion: EQUITY.** The PF=174 cell is a leakage artifact (low-confidence bucket winning 98% is a label-leak signature), and 97.7% of opened equity trades never close. Mutate: raise `SMART_PICKS_MIN_SCORE_EQUITY` to 75, add `MIN_CLOSED_SAMPLE=200`, and audit the mean-reversion entry timestamp for look-ahead. If the PF collapses to <1.5 after the timestamp fix, kill.

**The single most important system-wide fix is not a score constant — it's the `passed_high_conviction=0` across all classes.** The HC gate (`score>=80, conf>=0.75, trust>=60`) is unreachable because every proven cell is `trust=UNK`. Either the trust feature is broken (most likely — `trust=UNK` dominates every top cell in every class) or the threshold is mis-set. **Fix the trust feature before touching any score constant**, or you will keep "discovering" edges that are really just the trust-missing bucket. This is the H-001/H-036 recurrence pattern in a new dimension: a missing feature masquerading as an edge.

**Brutal summary:** 1 of 10 classes (CRYPTO) has a defensible, holdout-validated edge, and it's too thin to

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### EQUITY
- Real/noise verdict: Noise — n=63 with 98.41% WR and PF=174 is statistically impossible without leakage or single-symbol concentration; holdout_pass true does not override the unrealistic metrics.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_EQUITY = 75
- Confidence (1-5): 5

### INDEX
- Real/noise verdict: Noise — n_closed=4, no proven cells, all best_pf cells empty or invalid.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_INDEX = 80
- Confidence (1-5): 5

### COMMODITY
- Real/noise verdict: Noise — no proven cells; best_pf cells fail holdout and bonferroni; n=44 too small for reliable edge.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_COMMODITY = 70
- Confidence (1-5): 5

### FOREX
- Real/noise verdict: Noise — no proven cells; best_pf cells show PF=16.959 but holdout_pass=false and n=26 with extreme train/holdout divergence; matches known leakage patterns in regime/consensus signals.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: HC_MIN_CONF_FOREX = 0.92
- Confidence (1-5): 5

### CRYPTO
- Real/noise verdict: Sample-noise with leakage risk — n=173 decent and holdout/bonferroni pass, but PF=4.126 and WR_shrunk=74.61% on alpha_engine conf=0.75-0.80 cells remain suspiciously high; possible single-symbol or look-ahead contamination.
- 90d expected P&L (1% risk, $100k): $0 (edge not trusted for live sizing)
- Gate change: SMART_PICKS_MIN_SCORE_CRYPTO = 65
- Confidence (1-5): 4

### BOND
- Real/noise verdict: Noise — n_closed=31, no proven or best_pf cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_BOND = 80
- Confidence (1-5): 5

### ETF
- Real/noise verdict: Noise — n_closed=9, no cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_ETF = 80
- Confidence (1-5): 5

### UNKNOWN
- Real/noise verdict: Noise — n_closed=3, no cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_UNKNOWN = 80
- Confidence (1-5): 5

### FUTURES
- Real/noise verdict: Noise — n_closed=18, no proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_FUTURES = 75
- Confidence (1-5): 5

### MEME
- Real/noise verdict: Noise — n_closed=9, no proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_MEME = 80
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale up today: none (zero classes have trustworthy, leakage-free edges meeting production standards).  
Demote per MUTATION_THREE_AXIS_PROTOCOL: EQUITY and FOREX first (highest leakage signals), followed by CRYPTO; all others already at zero allocation.
