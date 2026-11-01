# Pick Funnel Swarm Verdict — 2026-11-01 04:07 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20261101T040640Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-Day Edge Analysis

## Pre-analysis sanity checks (read this first)

Before per-class verdicts, three structural red flags dominate the whole dataset:

1. **`passed_high_conviction = 0` in every single class.** The HC gate (`score>=80, conf>=0.75, trust>=60`) is *never* satisfied across 90 days and ~53k scans. Either the gate is mis-wired (trust never reaches 60, or score never reaches 80), or the scoring distribution is shifted. This is the single biggest finding — the "HIGH CONVICTION" funnel is dead code in production.
2. **`passed_verified_alpha` is 0 for 8 of 10 classes** and only non-zero for CRYPTO (2233) and FOREX (3). The verified-alpha gate is effectively CRYPTO-only.
3. **`opened` >> `passed_smart`** in every class (e.g. EQUITY: 234 passed_smart but 5676 opened; FOREX: 23514 passed_smart but 23023 opened). The "opened" counter is clearly counting *all* signals, not gate-passed ones. The funnel is not a funnel — it's two parallel counters. Any P&L estimate must be built from the *edge cells*, not from `opened`.

Also note: **`passed_smart` for FOREX is 96.8% of scanned** (23514/24291) and for INDEX is 80.5%. A "smart" gate that passes 97% of FOREX is not a gate. The Smart per-class floor map is mis-calibrated for FOREX/INDEX/COMMODITY.

---

### CRYPTO
- **Real/noise verdict:** The single PROVEN cell (`conf=C0.75-0.80 & score_dec=S50 & source=alpha_engine`) is **the same 174 trades repeated three times** with different dim labels — the three "top edges" are not independent confirmations, they are one cell. n=174, WR_shrunk=75.3%, PF=4.18, holdout PF=2.74 (n=89), wr_z=7.43, Bonferroni pass. That is genuinely strong *if* the cell is clean. **But**: (i) the cell is defined by `score_dec=S50` — a *decile* of score, which is a post-hoc bucket; (ii) `conf=C0.75-0.80` is a narrow 5bp band that smells like a bin-edge artifact; (iii) the class-level WR is 45.8% (n=2452) while this cell is 78% — a 32-point lift from a 5bp confidence band and a score decile is not credible without a mechanism. **Verdict: likely leakage or bin-selection artifact until proven otherwise.** The `ml` cell the prompt references is not in this payload — but the pattern (narrow conf band + score decile + single source) is exactly the signature of the H-001 COT leakage recurrence: a post-hoc bucket that concentrates on one regime. **Flag as potential leakage recurrence.** Do not scale.
- **90d expected P&L (1% risk, $100k):** If the cell were real: 174 trades × 1% × $100k × (avg_pnl 1.59% / 1% risk) ≈ **$276k gross**, minus ~0.05% slippage × 174 × $100k ≈ $8.7k, minus fees ~$3.5k → **~$264k**. But given the leakage flag, **expected realized P&L is closer to $0 to −$20k** (class WR 45.8% at 1% risk on 2452 trades with PF<1 → negative expectancy). Report the honest number: **$0 (do not deploy)**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` — raise from current (effectively ~50, since S50 is the modal decile) to **65**, and add a hard `conf >= 0.70 AND conf <= 0.72` exclusion band to kill the 0.75–0.80 bin artifact until it's re-validated out-of-sample on a *pre-registered* bucket. Also fix `hc_filter.js`: `trust >= 60` is unreachable — lower to **`trust >= 45`** or fix the trust scorer, otherwise HC is permanently 0.
- **Confidence (1-5):** 2

### EQUITY
- **Real/noise verdict:** The PROVEN cell `trust=UNK & conf=C<0.60 & fam=mean_reversion` has **n=63, WR=98.4%, PF=173, holdout PF=99 (n=27)**. PF=173 is not a trading edge — it is a **data bug**. A PF of 173 means average win / average loss ≈ 173:1, which is impossible on liquid equities with any realistic stop. This is almost certainly: (a) a single-symbol concentration (one ticker that went to zero or had a split-adjusted price error), (b) a look-ahead in the mean-reversion entry (entering at the low of the bar), or (c) a P&L sign/units bug. **The `trust=UNK` label is the tell** — the edge lives entirely in trades where trust is unknown, i.e. the trust scorer failed to score them, and the "edge" is an artifact of unscored trades. **Verdict: leakage/bug. Reject.** The class-level WR of 70.8% on n=130 is also suspiciously high for equities and likely contaminated by the same 63 trades (63/130 = 48% of all closed equity trades are this one cell).
- **90d expected P&L (1% risk, $100k):** If real (it isn't): 63 × 1% × $100k × 1.56 ≈ **$98k**. Honest number: **$0 — do not deploy.** The remaining 67 equity trades have WR ≈ (92−62)/(130−63) = 30/67 = 44.8%, i.e. negative expectancy.
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` — but the real fix is upstream: **add a hard `trust != UNK` requirement** to the equity smart-picks path (currently UNK trades are passing). Set `SMART_PICKS_MIN_TRUST_EQUITY = 40` and reject UNK. Also cap `fam=mean_reversion` position size to 0.25% until the PF=173 bug is root-caused.
- **Confidence (1-5):** 1 (the "edge" is a bug; confidence that it's *not* real is 5)

### FOREX
- **Real/noise verdict:** **No PROVEN cells.** The best cell (`trust=UNK & fam=regime & dir=LONG`, n=29, WR_shrunk=69.4%, PF=5.22) **fails Bonferroni** (`bonferroni_pass: false`) and has train_n=10 — a 10-trade train set is not a train set. Class-level WR is 47.7% on n=468 (decisive), i.e. **negative expectancy**. The `consensus` cell the prompt flags is not in this payload, but the pattern here (regime family, LONG-only, UNK trust, n=29) is the same signature as the rejected H-035 funding-timing hypothesis: sign instability across walk-forward windows. **Verdict: noise.** The 96.8% smart-pass rate confirms the gate is not filtering.
- **90d expected P&L (1% risk, $100k):** Class WR 47.65% on 468 decisive trades with PF<1 → **negative expectancy, roughly −$15k to −$25k** at 1% risk (assuming ~0.5R average loss on losers, 0.5R on winners). Honest number: **−$20k (do not deploy).**
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` — raise from current (~50) to **70**, and add `SMART_PICKS_MIN_CONF_FOREX = 0.65`. The 97% pass rate must come down to <20% or the gate is decorative. Also: `hc_filter.js` `trust >= 60` is unreachable for FOREX (all cells are `trust=UNK`) — the trust scorer is not populating for FX.
- **Confidence (1-5):** 1

### COMMODITY
- **Real/noise verdict:** **No PROVEN cells.** Best cell (`trust=UNK & dir=LONG & source=alpha_engine`, n=31, WR_shrunk=54.9%, PF=1.93) **fails holdout** (`holdout_pf: 1.074`, `holdout_pass: false`) and **fails Bonferroni**. Train PF 3.37 → holdout PF 1.07 is the classic overfit decay curve. Class WR 60.9% on n=46 is too small to trust and the holdout failure kills it. **Verdict: noise / overfit.** Note the H-001 COT leakage was COMMODITY — this cell's `trust=UNK & dir=LONG` signature is consistent with the same unscored-trade contamination pattern. **Flag as potential leakage recurrence.**
- **90d expected P&L (1% risk, $100k):** If the cell held: 31 × 1% × $100k × 0.69 ≈ **$21k**. But holdout PF 1.07 ≈ breakeven → **~$0 to +$2k**. Honest number: **$0.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` — raise to **65** (currently passing 60% of scans, 3671/6091). Add `SMART_PICKS_MIN_TRUST_COMMODITY = 40` to reject UNK.
- **Confidence (1-5):** 2

### INDEX
- **Real/noise verdict:** **No edge.** n_closed=4. WR 25%. `passed_smart` = 80.5% of scans. This is not a class — it's 4 trades and a broken gate. **Verdict: noise / insufficient data.**
- **90d expected P&L (1% risk, $100k):** **−$2k to −$3k** (4 trades, 3 losses). Honest number: **−$2.5k.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` — raise to **75** (from ~50). 80% pass rate is indefensible.
- **Confidence (1-5):** 1

### ETF
- **Real/noise verdict:** **No edge.** n_closed=9, WR 11.1%. **Verdict: noise.**
- **90d expected P&L (1% risk, $100k):** **−$7k to −$8k** (9 trades, 8 losses). Honest number: **−$7.5k.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` — raise to **70**. Or better: **disable ETF smart-picks entirely** until n>=30.
- **Confidence (1-5):** 1

### FUTURES
- **Real/noise verdict:** **No edge.** n_closed=18, WR 38.9%. Note H-005 (futures momentum anti-signal) is already falsified — do not re-derive. **Verdict: noise.**
- **90d expected P&L (1% risk, $100k):** **−$4k to −$5k.** Honest number: **−$4.5k.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` — raise to **70**.
- **Confidence (1-5):** 1

### MEME
- **Real/noise verdict:** **No edge.** n_closed=9, WR 33.3%. **Verdict: noise.**
- **90d expected P&L (1% risk, $100k):** **−$3k to −$4k.** Honest number: **−$3.5k.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME` — raise to **75**, or disable (n<30).
- **Confidence (1-5):** 1

### BOND
- **Real/noise verdict:** **No edge.** n_closed=31, WR 38.7%. `passed_smart` = 1/818 — the gate is *too tight* here (opposite problem to FOREX). **Verdict: noise.**
- **90d expected P&L (1% risk, $100k):** **−$5k to −$6k.** Honest number: **−$5.5k.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` — **lower** to **45** (currently ~50 but only 1/818 passes, so the floor map is mis-set for bonds). But do not deploy until n>=50.
- **Confidence (1-5):** 1

### UNKNOWN
- **Real/noise verdict:** **No edge.** n_closed=3, WR 0%. This is the bucket that should not exist — 1397 scans landed in UNKNOWN. **Verdict: data quality failure, not a class.**
- **90d expected P&L (1% risk, $100k):** **−$3k.** Honest number: **−$3k.**
- **Gate change:** Fix the classifier — `UNKNOWN` should be **rejected at ingest**, not passed to smart-picks. Add `if asset_class == UNKNOWN: reject` in `production_scanner.py`.
- **Confidence (1-5):** 1

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY with real money: NONE.**

There is not a single asset class in this 90-day window where the evidence supports deploying real capital. The two "PROVEN" cells (CRYPTO conf-band, EQUITY mean-reversion) both carry leakage signatures — narrow post-hoc bins, `trust=UNK` contamination, and in EQUITY's case a PF of 173 that is physically impossible. The FOREX/COMMODITY best cells fail Bonferroni and holdout. Every other class has n<50 and negative WR.

If forced to pick the *least-bad* candidate for a **paper-trading** (not real money) forward test: **CRYPTO**, because it is the only class with (a) meaningful n (2452 closed), (b) a holdout that passes (PF 2.74 on n=89), and (c) a plausible mechanism (alpha_engine + tight conf band). But it must be re-validated on a **pre-registered** bucket (not a post-hoc score decile) before a dollar moves.

**DEMOTE per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` (mutate before kill):**

1. **EQUITY** — demote to Ring-2 (mutate). The PF=173 cell is a bug, not an edge; the remaining 67 trades have WR 44.8%. Mutate: add `trust != UNK` requirement, cap mean_reversion size, re-run 90d. If WR stays <50% after mutation → kill.
2. **FOREX** — demote to Ring-2. 97% smart-pass rate + 47.7% WR + Bonferroni fail = the gate is not a gate. Mutate: raise `SMART_PICKS_MIN_SCORE_FOREX` to 70, re-run. If pass rate doesn't drop below 20% and WR doesn't clear 52%, kill.
3. **COMMODITY** — demote to Ring-2. Holdout PF 1.07 is the overfit tell. Mutate: reject `trust=UNK`, re-run. If holdout still fails, kill (and note H-001/H-036 already killed two commodity hypotheses — this class is on its third strike).
4. **INDEX / ETF / FUTURES / MEME / BOND / UNKNOWN** — **kill or freeze** (n<50, no path to significance in 90d). Do not mutate; there is nothing to mutate.

**The single highest-leverage fix is not a per-class constant — it is the `passed_high_conviction = 0` bug.** The HC gate is the only gate designed to concentrate edge, and it is returning zero across 53k scans. Fix `hc_filter.js` (`trust >= 60` is unreachable — lower to 45 or fix the trust scorer) and re-run the 90d funnel. Until HC produces a non-zero, non-trivial count, the dashboard is showing users a "HIGH CONVICTION" tab that is structurally empty. That is the most honest finding in this audit: **the funnel's top gate is broken, and the two cells that look like edges are the two cells most likely to be leakage.** Do not deploy. Fix the gate, re-run, then re-audit.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

**### EQUITY**
- Real/noise verdict: Noise/leakage. n=63, WR_shrunk=86.75, PF=173 is statistically impossible without single-symbol concentration or look-ahead; matches known rejected hypotheses patterns.
- 90d expected P&L (1% risk, $100k): $0 (edge invalid).
- Gate change: SMART_PICKS_MIN_SCORE_EQUITY = 75.
- Confidence (1-5): 5

**### COMMODITY**
- Real/noise verdict: Noise. No proven cells; best_pf_overall cells fail holdout and bonferroni.
- 90d expected P&L (1% risk, $100k): -$1,200 (random walk on 46 trades).
- Gate change: SMART_PICKS_MIN_SCORE_COMMODITY = 80.
- Confidence (1-5): 4

**### INDEX**
- Real/noise verdict: Noise. n=4 decisive trades, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: None (disable INDEX entirely).
- Confidence (1-5): 5

**### FOREX**
- Real/noise verdict: Noise. No proven cells; all best_pf_overall fail bonferroni; regime cells show classic small-n instability.
- 90d expected P&L (1% risk, $100k): -$4,800 (negative expectancy on 468 trades).
- Gate change: HC_MIN_CONF = 0.82.
- Confidence (1-5): 4

**### CRYPTO**
- Real/noise verdict: Likely noise/leakage. n=174, WR_shrunk=75.26, PF=4.184 is suspiciously high; matches user-flagged ml/alpha_engine pattern and prior rejected funding hypotheses.
- 90d expected P&L (1% risk, $100k): $0 (do not trust).
- Gate change: ALPHA_ENGINE_MIN_TRUST = 65.
- Confidence (1-5): 4

**### BOND**
- Real/noise verdict: Noise. n=31, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: None (remove BOND from scanner).
- Confidence (1-5): 5

**### UNKNOWN**
- Real/noise verdict: Noise. n=3.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: None.
- Confidence (1-5): 5

**### ETF**
- Real/noise verdict: Noise. n=9.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: None.
- Confidence (1-5): 5

**### FUTURES**
- Real/noise verdict: Noise. n=18, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: None.
- Confidence (1-5): 5

**### MEME**
- Real/noise verdict: Noise. n=9.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: None.
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale up nothing today. Demote CRYPTO and EQUITY first per MUTATION_THREE_AXIS_PROTOCOL.md (both show leakage signatures); freeze all other classes until n>200 closed trades with holdout_pass=true and bonferroni_pass=true.
