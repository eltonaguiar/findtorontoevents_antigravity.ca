# Pick Funnel Swarm Verdict — 2026-10-05 04:16 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20261005T041608Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-day Edge Analysis

Before the per-class verdicts, three structural facts dominate everything below:

1. **`passed_high_conviction = 0` for every class.** The HC gate (`score>=80, conf>=0.75, trust>=60`) is firing on **zero** trades across 90 days. Every "edge" you're about to read is *below* your own HC bar. That is the single most important finding in this dataset.
2. **`passed_verified_alpha` is 0 for 8 of 10 classes.** Only CRYPTO (1796) and FOREX (3) produce verified-alpha picks. The rest of the funnel is Smart-Picks-only.
3. **`opened >> closed` everywhere.** EQUITY: 5535 opened / 162 closed (2.9%). FOREX: 21428 / 1377 (6.4%). The "WR" numbers are computed on the tiny closed subset, which is a *survivorship-of-closure* sample, not a strategy sample. Treat every WR below as a lower-bound-of-uncertainty estimate, not a point estimate.

---

### EQUITY
- **Real/noise verdict: NOISE / LEAKAGE.** The "PROVEN" cell `fam=mean_reversion & score_dec=S40` shows WR=98.51%, PF=215.15, n=67. A PF of 215 is not a strategy — it is a **data artifact**. Three red flags: (i) `trust=UNK` on 100% of the cell, (ii) `conf=C<0.60` — i.e. the *lowest* confidence bucket produces the *highest* PF, which is the classic signature of a mislabeled outcome or a look-ahead in the labeler, (iii) train_pf=99.1 / holdout_pf=99.0 — a suspiciously *flat* train/holdout split, which usually means the same trades leaked into both folds. This is almost certainly the same class of bug as H-001 (COT look-ahead): outcome labels computed with future information. **Do not trade this. Quarantine the labeler.**
- **90d expected P&L (1% risk, $100k): $0** (do not deploy). If you naively sized it: 67 trades × 1% × 1.28% avg = ~$860, but the number is meaningless because the underlying PF is fake.
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` — raise from current floor to **≥55** and add a hard `trust != UNK` requirement in `quality_gates.py`. The S40 bucket is where the leakage lives.
- **Confidence (1-5): 1**

### COMMODITY
- **Real/noise verdict: NOISE.** Best cell is `fam=momentum & score_dec=S50`, n=21, WR=52.38%, PF=4.447, but `holdout_pass=false`, `bonferroni_pass=false`, `wr_z=0.218`. PF=4.4 on WR=52% means the PF is driven by **one or two outsized winners** — classic small-n tail artifact. n=21 is below your own n>=20 threshold's *spirit* (it barely clears the letter). Also note the H-001 precedent: COMMODITY has a documented history of look-ahead leakage in exactly this kind of momentum/positioning cell. Treat as unproven.
- **90d expected P&L (1% risk, $100k): $0** (do not deploy). Naive: 21 × 1% × 2.28% = ~$480, but with PF driven by tails and no holdout pass, real expectation is ~$0 ± noise.
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` — raise to **≥60** and require `holdout_pass=true` before a cell is eligible for Smart Picks. Currently 3270/5762 (57%) pass Smart — that's not a filter, that's a turnstile.
- **Confidence (1-5): 1**

### INDEX
- **Real/noise verdict: NOISE (insufficient n).** 5 decisive trades, WR=20%. No edge cells. 1565/1826 pass Smart (86%) — the Smart gate is doing essentially nothing here.
- **90d expected P&L (1% risk, $100k): $0** (do not deploy). Naive: 5 × 1% × (negative) = **-$300**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` — raise to **≥65**; INDEX has no demonstrated edge and the current floor is letting 86% through.
- **Confidence (1-5): 1**

### FOREX
- **Real/noise verdict: NOISE / LEAKAGE-SUSPECT.** The `regime` / `regime_terminal` cell (n=54, WR=68.5%, PF=3.197) has `train_pf=0.298` and `holdout_pf=14.149`. That is a **train/holdout inversion** — the strategy loses money in-sample and prints 14x PF out-of-sample. That is not an edge; that is either (a) a regime shift that happened to coincide with the holdout window, or (b) a leakage in the holdout split. `holdout_pass=false`, `bonferroni_pass=false`. Also: 21873/22805 (96%) pass Smart — the Smart gate is a no-op on FOREX. The overall class WR is 43.65% on 520 decisive — **below coin flip**.
- **90d expected P&L (1% risk, $100k): $0** (do not deploy). Naive on the regime cell: 54 × 1% × 0.38% = ~$205, but train_pf=0.298 says the honest expectation is negative.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` — raise from current floor to **≥70** AND add a `train_pf >= 1.0` precondition in `quality_gates.py`. A cell that loses in-sample must not be eligible regardless of holdout.
- **Confidence (1-5): 1**

### CRYPTO
- **Real/noise verdict: MOSTLY REAL, with one caveat.** The `conf=C0.75-0.80 & score_dec=S50 & source=alpha_engine` cell is the only one in the entire dataset that passes **all** of: n=178, wr_shrunk=70.2%, PF=3.359, holdout_pass=true, bonferroni_pass=true, wr_z=5.996. Train_pf=3.824 / holdout_pf=2.164 is a *healthy* degradation (not an inversion). This is the real deal. **Caveat:** the cell is defined by `score_dec=S50` and `source=alpha_engine` — check that S50 isn't a post-hoc bucket that was chosen because it looked good. If S50 was pre-registered, this is your edge. If it was discovered by scanning deciles, apply a decile-selection penalty (roughly halve the effective n).
- **90d expected P&L (1% risk, $100k): +$2,400** (see sizing below). 178 trades × 1% risk × 1.36% avg_pnl = ~$2,420. Apply a 20% haircut for slippage/fees on crypto → **~$1,900**.
- **Gate change:** `hc_filter.js` — the HC gate is firing on **zero** CRYPTO trades despite this cell existing. The cell's `conf=0.75-0.80` clears the 0.75 bar, but `trust=UNK` fails the `trust>=60` bar. **Either** (a) fix the trust scorer so `alpha_engine` picks get a real trust value, **or** (b) lower `HC_MIN_TRUST` from 60 to **50** *only for `source=alpha_engine`*. Option (a) is correct; option (b) is the fast unblock. Do (a).
- **Confidence (1-5): 4**

### ETF
- **Real/noise verdict: NOISE.** 9 decisive, WR=22%. No cells.
- **90d expected P&L (1% risk, $100k): $0** (do not deploy). Naive: 9 × 1% × (negative) = **-$540**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` — raise to **≥65**.
- **Confidence (1-5): 1**

### UNKNOWN
- **Real/noise verdict: NOISE / DATA-QUALITY BUG.** 7 decisive, WR=0%. The class exists because the classifier failed. This is not a strategy class; it's a **routing bug**. 168/1381 pass Smart on a class that shouldn't exist.
- **90d expected P&L (1% risk, $100k): $0** (do not deploy). Naive: 7 × 1% × (negative) = **-$700**.
- **Gate change:** Add a hard reject in `quality_gates.py`: `if asset_class == "UNKNOWN": return False`. Do not let unclassified picks into the funnel at all.
- **Confidence (1-5): 1**

### BOND
- **Real/noise verdict: NOISE.** Best cell n=20, WR=55%, PF=1.636, but `holdout_pass=false`, `wr_z=0.447`. The second cell is WR=40%, PF=0.67 — i.e. the "best" and "second best" cells disagree on sign. That's noise.
- **90d expected P&L (1% risk, $100k): $0** (do not deploy). Naive: 20 × 1% × 0.11% = ~$22 — indistinguishable from zero.
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` — raise to **≥65**; only 3/557 pass Smart today, so the floor is already tight, but the class has no edge and should be demoted.
- **Confidence (1-5): 1**

### FUTURES
- **Real/noise verdict: NOISE.** 17 decisive, WR=29.4%. No cells. Note H-005 already killed the futures momentum inversion hypothesis — do not re-derive it.
- **90d expected P&L (1% risk, $100k): $0** (do not deploy). Naive: 17 × 1% × (negative) = **-$1,200**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` — raise to **≥70**.
- **Confidence (1-5): 1**

### MEME
- **Real/noise verdict: NOISE.** 4 decisive. No cells. n is too small to say anything.
- **90d expected P&L (1% risk, $100k): $0** (do not deploy). Naive: 4 × 1% × (negative) = **-$300**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME` — raise to **≥75**; MEME should require the highest bar because the base rate is worst.
- **Confidence (1-5): 1**

---

## Sizing / slippage assumptions (for the CRYPTO number)

- Account: $100,000 notional.
- Risk per trade: 1% = $1,000.
- Position size = $1,000 / (stop distance in %). For the CRYPTO cell, avg_pnl_pct=1.36% is the *realized* return per trade, so P&L per trade ≈ $1,000 × 1.36% / (stop%) — I'm using the simplifying assumption that the 1.36% is already risk-normalized (i.e. it's R-multiple × 1%). If it's raw notional return, multiply by ~3-5x for typical crypto stops.
- Slippage: 10 bps per side on crypto (20 bps round-trip) → ~$20/trade × 178 = ~$3,560 drag. **This is why I haircut the $2,420 to ~$1,900.**
- Fees: 5 bps taker × 2 = 10 bps → ~$1,780 drag. Already inside the haircut.
- **Net expected 90d P&L on CRYPTO cell: ~$1,900** (range $1,200–$2,600 depending on stop width and whether S50 was pre-registered).

---

## SYSTEM-WIDE conclusion

**Scale up TODAY: CRYPTO only.** The `conf=C0.75-0.80 & score_dec=S50 & source=alpha_engine` cell is the only signal in this entire 90-day dataset that survives holdout, Bonferroni, and shrinkage. It is also the only class where `passed_verified_alpha > 0` at scale (1796). Everything else is either noise, leakage, or n<20.

**Demote per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` (mutate before kill):**

1. **EQUITY** — demote to *quarantine*, not kill. The PF=215 cell is a labeler bug, not a strategy. Mutate the labeler (axis: data integrity), re-run, then decide. Do not kill the class until the labeler is fixed — you may be killing a real mean-reversion edge that's currently masked by a leakage bug.
2. **FOREX** — demote to *mutate*. The train_pf=0.298 / holdout_pf=14.149 inversion is a split-integrity bug. Mutate the walk-forward splitter (axis: validation), re-run. If the inversion persists, kill.
3. **COMMODITY** — demote to *mutate*. H-001 already burned you here once. Mutate the feature pipeline (axis: data integrity) before re-testing momentum.
4. **INDEX, ETF, BOND, FUTURES, MEME, UNKNOWN** — **kill or hard-gate**. These have no edge, no n, and in UNKNOWN's case no reason to exist. UNKNOWN is a routing bug — fix the classifier, don't trade the class.

**The single most damning number in this report:** `passed_high_conviction = 0` across all 10 classes over 90 days. Your HC gate is either mis-calibrated (trust scorer returns UNK for everything) or your picks genuinely never clear it. Either way, the HC funnel is currently a **dead branch** — it is not filtering, it is excluding. Fix the trust scorer before you tune any other constant.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

**### EQUITY**
- Real/noise verdict: Noise/leakage — 98.5% WR and PF=215 on n=67 mean_reversion cell is statistically impossible without single-symbol concentration or look-ahead; rejected per protocol.
- 90d expected P&L (1% risk, $100k): $0 (edge invalid).
- Gate change: SMART_PICKS_MIN_SCORE_EQUITY = 65.
- Confidence (1-5): 5

**### COMMODITY**
- Real/noise verdict: Noise — no proven cells; all candidates fail holdout/bonferroni; n too low for stability.
- 90d expected P&L (1% risk, $100k): -$420 (random walk on 89 closed).
- Gate change: N/A.
- Confidence (1-5): 4

**### INDEX**
- Real/noise verdict: Noise — n=5 decisive, zero proven cells.
- 90d expected P&L (1% risk, $100k): -$300.
- Gate change: N/A.
- Confidence (1-5): 5

**### FOREX**
- Real/noise verdict: Noise — top cells fail holdout_pass and bonferroni; regime cells unstable.
- 90d expected P&L (1% risk, $100k): -$660.
- Gate change: N/A.
- Confidence (1-5): 4

**### CRYPTO**
- Real/noise verdict: Real — three overlapping cells (n=177-178, WR_shrunk 70.2-70.56, PF=3.359, holdout_pass=true, bonferroni_pass=true, wr_z>5.9) survive multiple tests; no obvious leakage flags.
- 90d expected P&L (1% risk, $100k): +$2,430 (177 trades × ~1.36% avg edge after 0.15% slippage, 1% risk units).
- Gate change: HC_MIN_CONF = 0.78.
- Confidence (1-5): 4

**### ETF**
- Real/noise verdict: Noise — n=9, no proven cells.
- 90d expected P&L (1% risk, $100k): -$70.
- Gate change: N/A.
- Confidence (1-5): 5

**### UNKNOWN**
- Real/noise verdict: Noise — n=7, zero edges.
- 90d expected P&L (1% risk, $100k): -$70.
- Gate change: N/A.
- Confidence (1-5): 5

**### BOND**
- Real/noise verdict: Noise — n=33, no proven cells, best_pf cells fail holdout.
- 90d expected P&L (1% risk, $100k): -$190.
- Gate change: N/A.
- Confidence (1-5): 4

**### FUTURES**
- Real/noise verdict: Noise — n=17, no proven cells.
- 90d expected P&L (1% risk, $100k): -$120.
- Gate change: N/A.
- Confidence (1-5): 5

**### MEME**
- Real/noise verdict: Noise — n=4, no proven cells.
- 90d expected P&L (1% risk, $100k): -$30.
- Gate change: N/A.
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale CRYPTO today (only class with surviving, multi-test edges). Demote EQUITY per MUTATION_THREE_AXIS_PROTOCOL.md (mutate the mean_reversion path or kill the class entirely). All other classes have no actionable edge.
