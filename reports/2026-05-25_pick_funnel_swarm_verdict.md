# Pick Funnel Swarm Verdict — 2026-11-12 04:07 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20261112T040652Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-Day Edge Analysis

Before per-class verdicts, three structural facts dominate everything below:

1. **`passed_high_conviction = 0` across ALL 10 classes.** The HC gate (score≥80, conf≥0.75, trust≥60) is dead code in production. Nothing has ever cleared it in 90 days. That is the single biggest finding in this dataset.
2. **`passed_verified_alpha` is 0 for 7 of 10 classes** and only non-trivial for CRYPTO (2222/12299 = 18%). The "verified alpha" funnel is effectively CRYPTO-only.
3. **`opened` >> `passed_smart`** in every class (e.g. EQUITY: 5753 opened vs 230 passed_smart; FOREX: 23794 opened vs 24409 passed_smart — opened exceeds scanned in FOREX, which is a data-integrity bug). The funnel is not actually gating live flow; it's a post-hoc label. **Any "edge" claim below is about the labeled subset, not about what the system actually traded.**

---

### EQUITY
- **Real/noise verdict: NOISE / LEAKAGE-SUSPECT.** The PROVEN cell `rr=RR>=2.0 & fam=mean_reversion` shows n=37, WR=97.3%, PF=131.6, holdout_pf=99.0. PF of 131 with 37 trades is not a strategy — it's a data artifact. Three red flags: (i) `holdout_pf=99.0` is the code's cap value, meaning holdout had zero losing trades — impossible for a real mean-reversion book; (ii) `train_n=16` vs `holdout_n=21` means the "holdout" is larger than train, so the split is not chronological or is mislabeled; (iii) `trust=UNK` dominating the winning cell means the trust dimension is unpopulated, so the cell is really just "RR≥2.0 mean-reversion LONG" — a single strategy family with 37 trades. This is almost certainly a **stop/target fill-order artifact** (RR≥2.0 with tight stops that get hit intrabar but are recorded as wins because the target was touched first in the OHLC bar). **Do not trade this.** The 71% WR on 107 closed trades is the only number with any signal, and n=107 is too small to distinguish from 55% at 95% confidence.
- **90d expected P&L (1% risk, $100k): $0.** Not tradeable. If forced to size the 71% WR / 107-trade book at 1% risk with 1.5:1 avg RR: EV ≈ 107 × 0.01 × $100k × (0.71×1.5 − 0.29×1.0) ≈ **+$8,400**, but the CI on 107 trades spans roughly −$2k to +$19k. Not distinguishable from zero.
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` — raise from current value to **≥ 75** and require `trust != UNK`. The UNK-trust cell is where all the fake edge lives.
- **Confidence (1-5): 1**

### FOREX
- **Real/noise verdict: NOISE / LEAKAGE-SUSPECT.** The `trust=UNK & conf=C>=0.90 & fam=regime` cell (n=38, WR=89.5%, PF=14.4, holdout_pf=99.0, bonferroni_pass=true) is the most dangerous cell in the dataset because it *passes* Bonferroni. That is exactly what a leakage artifact looks like after multiple-testing correction — the correction doesn't help if the underlying data is contaminated. Specific tells: (i) `holdout_pf=99.0` again — zero holdout losses; (ii) `source=regime_terminal` with conf≥0.90 is a **terminal-state label**, i.e. the regime was already known to have resolved favorably when the pick was recorded — classic look-ahead; (iii) n=38 with 34 wins is a 4-loss sample; a single mislabeled trade flips WR by 2.6pp. The 52.09% overall WR on 430 decisive trades is the honest number and it is **coin-flip minus costs**. FOREX is a losing class after spread.
- **90d expected P&L (1% risk, $100k): −$4,000 to −$8,000.** 430 decisive trades × 1% × $100k × (0.5209×RR − 0.4791×1.0). At RR=1.0 that's −$4,300 gross; add 0.8 pip avg spread on 430 trades ≈ −$3,400 more. **Negative.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` — raise to **≥ 70** AND add a hard `source != 'regime_terminal'` exclusion in `quality_gates.py`. The regime_terminal source is the leakage vector.
- **Confidence (1-5): 1**

### COMMODITY
- **Real/noise verdict: NOISE.** Best cell is `trust=UNK & dir=LONG & source=alpha_engine` at n=28, WR=64.3%, PF=2.14 — but `holdout_pass=false` (holdout_pf=1.14, essentially flat) and `bonferroni_pass=false`. The train PF of 4.02 vs holdout 1.14 is textbook overfit. n=37 closed total is far too small. Note H-001 and H-036 in the registry already killed COT and inventory signals in this class — this cell is likely a residual of the same contaminated pipeline. **No edge.**
- **90d expected P&L (1% risk, $100k): $0.** 37 trades is not a sample. Even at the optimistic 70.27% WR: 37 × 0.01 × $100k × (0.70×1.5 − 0.30×1.0) ≈ **+$2,200**, CI spans −$1k to +$5k. Noise.
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` — raise to **≥ 75** and require `n_closed ≥ 100` before any cell is promoted to PROVEN. The current n≥20 threshold is too low.
- **Confidence (1-5): 1**

### CRYPTO
- **Real/noise verdict: WEAK / PROBABLY NOISE, but the only class with enough n to even ask.** 2274 closed trades, WR=45.56% — **below 50%**. The "best PF overall" cell (`trust=UNK & rr=RR1.5-2.0 & source=alpha_engine`, n=199, WR=59.8%, PF=2.05) has `bonferroni_pass=false` and `holdout_pf=1.32` — the holdout is barely above 1.0. The 45.56% overall WR with 2274 trades is the real signal: **CRYPTO is a losing class at the portfolio level.** The 59.8% cell is a subset that survived multiple-testing; with bonferroni_pass=false it is not distinguishable from the 45.56% base rate at the family-wise level. The `passed_verified_alpha=2222` is suspicious — 18% of scanned crypto picks "verified" while 0% of every other class did. That asymmetry suggests the crypto verifier is either (a) using a different, looser definition, or (b) has a look-ahead in the verification step. **Flag as potential leakage recurrence** — this is the same pattern as H-001 (class-specific pipeline contamination).
- **90d expected P&L (1% risk, $100k): −$18,000 to −$25,000.** 2274 decisive × 1% × $100k × (0.4556×RR − 0.5444×1.0). At RR=1.5: 2274 × $1,000 × (0.683 − 0.544) = **−$31,600**. At RR=1.0: **−$20,200**. Add crypto slippage (0.1–0.3% per side) and it's worse. **This is the class bleeding the most real dollars.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` — raise to **≥ 78** AND add `rr >= 1.5` as a hard filter in `quality_gates.py`. The RR1.5-2.0 cell is the only one with holdout_pf > 1.3; everything below RR1.5 is the loss engine.
- **Confidence (1-5): 2** (only because n is large enough to be confident it's *bad*)

### BOND
- **Real/noise verdict: NOISE / NEGATIVE.** 31 closed, WR=38.7%. No PROVEN cells. n too small to say anything except "not an edge." 1100 opened vs 1 passed_smart — the gate is not filtering bonds at all.
- **90d expected P&L (1% risk, $100k): −$3,000 to −$5,000.** 31 × 1% × $100k × (0.387×1.0 − 0.613×1.0) ≈ **−$7,000** at RR=1.0. Small n, but directionally negative.
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` — set to **≥ 80** (effectively disable until n≥100). Bonds have no business in a momentum/mean-reversion scanner.
- **Confidence (1-5): 2** (confident it's not an edge)

### UNKNOWN
- **Real/noise verdict: NOISE / DATA BUG.** 1313 scanned, 1310 opened, 3 closed, 0 wins. This is not an asset class — it's a routing failure. 1310 picks with no class label is a pipeline bug, not a strategy.
- **90d expected P&L (1% risk, $100k): $0** (untradeable — no class means no sizing model).
- **Gate change:** Fix the classifier upstream. In `quality_gates.py`, add `assert asset_class != 'UNKNOWN'` before any pick is emitted. This is not a threshold change; it's a correctness fix.
- **Confidence (1-5): 5** (confident this is a bug)

### ETF
- **Real/noise verdict: NOISE / NEGATIVE.** 10 closed, WR=10%. n=10. No cells. 278 passed_smart out of 319 scanned — the gate is passing 87% of ETFs, which means it's not gating.
- **90d expected P&L (1% risk, $100k): −$8,000** (10 × 1% × $100k × (0.10×1.0 − 0.90×1.0) = −$8,000). Small n, but the direction is unambiguous.
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` — set to **≥ 80** and require `n_closed ≥ 50` before any ETF cell is promoted. ETFs are index proxies; a per-pick scanner adds no alpha over buy-and-hold.
- **Confidence (1-5): 2**

### INDEX
- **Real/noise verdict: NOISE.** 1 closed trade, 100% WR. This is a single data point. 1578 passed_smart out of 2075 scanned — the gate passes 76% of index picks. Meaningless.
- **90d expected P&L (1% risk, $100k): $0** (n=1).
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` — set to **≥ 80** and require `n_closed ≥ 30`. Index picks should be a benchmark, not a tradeable signal.
- **Confidence (1-5): 5** (confident n=1 is noise)

### FUTURES
- **Real/noise verdict: NOISE / NEGATIVE.** 16 closed, WR=37.5%. No PROVEN cells. H-005 in the registry already killed futures momentum. 125 passed_smart out of 175 scanned — 71% pass rate, gate not gating.
- **90d expected P&L (1% risk, $100k): −$4,000** (16 × 1% × $100k × (0.375×1.0 − 0.625×1.0) = −$4,000). Small n.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` — set to **≥ 80** and require `n_closed ≥ 50`. Futures have the highest per-trade cost (commission + roll); a 37.5% WR is unsalvageable.
- **Confidence (1-5): 2**

### MEME
- **Real/noise verdict: NOISE.** 8 closed, WR=37.5%. n=8. No cells. 13 passed_smart out of 25 scanned — 52% pass rate.
- **90d expected P&L (1% risk, $100k): −$2,000** (8 × 1% × $100k × (0.375×1.0 − 0.625×1.0) = −$2,000). n=8 is not a sample.
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME` — set to **≥ 85** (effectively disable). MEME is not a strategy class; it's a sentiment label.
- **Confidence (1-5): 2**

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY with real money: NONE.**

There is not a single asset class in this dataset where the honest, non-leakage-suspect numbers support deploying real capital. The two classes with the largest samples (CRYPTO n=2274, FOREX n=430) are both **below 50% WR** at the portfolio level. The classes with high WR (EQUITY 71%, COMMODITY 70%) have n=107 and n=37 respectively — too small to distinguish from 55% at 95% confidence, and their "PROVEN" cells have `holdout_pf=99.0` (the code's cap value), which is a leakage signature, not an edge.

The single most important finding is **`passed_high_conviction = 0` across all 10 classes over 90 days.** The HC gate is either misconfigured (thresholds unreachable) or the scoring pipeline never produces scores ≥80 with conf≥0.75 and trust≥60. Either way, the "HIGH CONVICTION" label on the dashboard is currently a lie — nothing has ever cleared it. **Fix this before deploying any capital.** A gate that never fires is not a gate; it's a decoration.

**Demote per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` (mutate before kill):**

1. **CRYPTO** — demote to "mutate" status. It has the largest sample and the worst real-dollar bleed (−$20k to −$32k over 90d at 1% risk). The `passed_verified_alpha=2222` asymmetry vs 0 in every other class is a **leakage recurrence flag** — same pattern as H-001. Mutate the verifier before killing the class.
2. **FOREX** — demote to "mutate." The `regime_terminal` source is a look-ahead vector. Mutate by excluding that source and re-running the 90d backtest; if WR stays below 52%, kill.
3. **EQUITY** — demote to "mutate." The `rr=RR>=2.0 & fam=mean_reversion` cell with PF=131 is almost certainly a fill-order artifact. Mutate by re-simulating with intrabar stop/target ordering; if PF drops below 2.0, kill the cell.
4. **COMMODITY, BOND, ETF, FUTURES, MEME, INDEX, UNKNOWN** — kill or disable. n too small, WR too low, or (UNKNOWN) a routing bug.

**The honest summary:** 90 days of live data across 10 asset classes produced **zero statistically defensible edges** after accounting for multiple testing, holdout validation, and known leakage patterns. The dashboard is currently showing a funnel that does not gate, a HC label that never fires, and a "verified alpha" flag that only CRYPTO triggers — and CRYPTO is the worst-performing class by real dollars. **Do not deploy capital on any of this.** The correct action is to fix the HC gate, fix the UNKNOWN classifier, exclude `regime_terminal` and `trust=UNK` cells from promotion, and re-run the 90d analysis before any sizing decision.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### EQUITY
- Real/noise verdict: noise — n=37 PF=131.644 and WR_shrunk=80.7% on mean_reversion cell is statistically impossible without leakage or single-symbol concentration; bonferroni false on other cells.
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge).
- Gate change: SMART_PICKS_MIN_SCORE_EQUITY = 92
- Confidence (1-5): 5

### FOREX
- Real/noise verdict: noise — regime cell PF=14.449 / WR_shrunk=75.86% on n=38 with holdout_n=10 is classic small-sample overfitting; matches pattern of rejected COT-style leakage.
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge).
- Gate change: HC_MIN_CONF = 0.92
- Confidence (1-5): 5

### COMMODITY
- Real/noise verdict: noise — no proven cells; best_pf cells fail holdout and bonferroni; n=37 total closed too small.
- 90d expected P&L (1% risk, $100k): -$420 (expected loss from random regime noise).
- Gate change: SMART_PICKS_MIN_SCORE_COMMODITY = 85
- Confidence (1-5): 4

### CRYPTO
- Real/noise verdict: noise — no proven cells; best_pf cells show train/holdout PF decay (2.517→1.316) and bonferroni=false; n=2274 total but edges unstable.
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge).
- Gate change: ALPHA_MIN_TRUST = 65
- Confidence (1-5): 4

### BOND
- Real/noise verdict: noise — n=31 closed, zero proven or best_pf cells.
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge).
- Gate change: SMART_PICKS_MIN_SCORE_BOND = 80
- Confidence (1-5): 5

### UNKNOWN
- Real/noise verdict: noise — n=3 closed, zero cells.
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge).
- Gate change: SMART_PICKS_MIN_SCORE_UNKNOWN = 90
- Confidence (1-5): 5

### ETF
- Real/noise verdict: noise — n=10 closed, zero cells.
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge).
- Gate change: SMART_PICKS_MIN_SCORE_ETF = 88
- Confidence (1-5): 5

### INDEX
- Real/noise verdict: noise — n=1 closed, zero cells.
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge).
- Gate change: SMART_PICKS_MIN_SCORE_INDEX = 90
- Confidence (1-5): 5

### FUTURES
- Real/noise verdict: noise — n=16 closed, zero proven cells; best_pf empty.
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge).
- Gate change: SMART_PICKS_MIN_SCORE_FUTURES = 85
- Confidence (1-5): 5

### MEME
- Real/noise verdict: noise — n=8 closed, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge).
- Gate change: SMART_PICKS_MIN_SCORE_MEME = 92
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale up today: none (zero classes have statistically credible edges after leakage flags and small-n checks).  
Demote per MUTATION_THREE_AXIS_PROTOCOL: CRYPTO and FOREX first (highest scanned volume, lowest WR, proven cells absent or rejected-pattern).
