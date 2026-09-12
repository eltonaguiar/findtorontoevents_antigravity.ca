# Pick Funnel Swarm Verdict — 2026-09-12 04:09 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260912T040936Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-day Edge Analysis

Before the per-class verdicts, three system-wide red flags that color everything below:

1. **`passed_high_conviction = 0` in every single class.** The HC gate (`score>=80, conf>=0.75, trust>=60`) is dead code in production. Every "edge" you're about to read about is *below* your own HC bar. That is the single most important fact in this dataset.
2. **`opened` >> `passed_smart` in every class** (EQUITY 4480 opened vs 214 smart; FOREX 22211 vs 22584 — actually inverted; CRYPTO 10031 vs 3183). The funnel is not gating. `opened` is essentially "everything scanned minus a rounding error." Whatever `passed_smart` is doing, it is not filtering the book.
3. **`trust=UNK` dominates every PROVEN cell.** The trust dimension is not discriminating — it's a constant. Any cell that includes `trust=UNK` is really a 3-dim cell wearing a 4-dim costume. Treat those as duplicates, not independent confirmations.

---

### EQUITY
- **Real/noise verdict:** **NOISE / LEAKAGE.** The `fam=mean_reversion & score_dec=S40` cell shows WR=98.46% (64/65), PF=206, holdout PF=119. This is not an edge — this is a broken P&L accounting path. A 98% WR with PF>200 on n=65 is the signature of (a) look-ahead in the exit fill, (b) a stop that never triggers because the "close" is being read from the same bar as the entry, or (c) a single-symbol / single-day cluster. The fact that `conf=C<0.60` is in the same cell is the tell: **your lowest-confidence bucket is your highest-WR bucket.** That is inverted from every real signal. Do not trade this. Do not "mutate" this — quarantine the mean_reversion family in EQUITY and audit the fill logic first.
- **90d expected P&L (1% risk, $100k):** **$0.** Not tradeable. If you forced it: 193 closed × 1% × avg_pnl 1.26% ≈ **+$2,430** on paper, but the number is fiction.
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` — raise from current (effectively ~40) to **65**, and add a hard `family != mean_reversion` exclusion until the fill audit clears. The S40 floor is letting the broken family through.
- **Confidence (1-5):** **5** that this is leakage. **1** that it's tradeable.

### COMMODITY
- **Real/noise verdict:** **NOISE.** No PROVEN cells. Best PF cell is `rr>=2.0 & score_dec=S50` at n=21, WR_shrunk=63.4%, PF=5.6, but `bonferroni_pass=false` and n=21 is below your own n>=20 threshold's spirit. This is the same shape as the falsified **H-001 (COT leakage)** and **H-036 (inventory direction)** — a small-n, high-PF cell that dies on holdout. Overall class WR is 44.7% (59W/73L) — **below coin-flip.** The 4042/6470 "passed_smart" rate (62%) is absurd for a class with a losing WR.
- **90d expected P&L (1% risk, $100k):** **−$1,400** (133 closed × 1% × −1.05% avg, using the class WR/PF). Negative expectancy.
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` — raise to **70**. The 62% pass rate is the problem; this class should be passing <10% of scans.
- **Confidence (1-5):** **4** it's noise. **1** it's tradeable.

### BOND
- **Real/noise verdict:** **NOISE, and actively harmful.** WR=19.05% (4W/17L), n=21. No PROVEN cells. This is a class where you are systematically wrong. The 16/421 smart-pass rate is fine, but the 400 opened vs 16 smart means the gate is being bypassed downstream.
- **90d expected P&L (1% risk, $100k):** **−$1,700** (21 × 1% × −8.1% avg loss-weighted). Negative.
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` — set to **999** (effectively disable) until you have a working bond model. Or add `BOND_ENABLED = False` in `production_scanner.py`. Trading a 19% WR class is worse than not trading it.
- **Confidence (1-5):** **5** it's noise. **0** it's tradeable.

### FOREX
- **Real/noise verdict:** **MOSTLY NOISE, one possibly-real cell.** The `conf=C0.75-0.80 & rr=RR1.0-1.5 & fam=mean_reversion` cell (n=138, WR_shrunk=64.6%, PF=2.78, holdout PF=1.69, bonferroni_pass=true) is the only cell in the entire dataset that survives Bonferroni *and* has a holdout PF that doesn't collapse. That said: **holdout PF dropped from 3.19 → 1.69**, which is a 47% degradation. That's a yellow flag, not a green one. The `dir=LONG` variant (n=46, PF=4.6) fails Bonferroni — ignore it. The `consensus` cell you flagged: I don't see it in the PROVEN list, which is itself suspicious — if it's in `best_pf_overall` with a high PF and no Bonferroni pass, treat it as the same small-n trap. **Class-level WR is 45.24% (266W/322L) — losing.** The edge is a narrow sub-cell inside a losing class.
- **90d expected P&L (1% risk, $100k):** If you traded *only* the mean_reversion/RR1.0-1.5/conf0.75-0.80 cell: 138 trades × 1% × 0.277% avg = **+$382**. That's it. On a $100k account over 90 days. The class as a whole: 588 decisive × 1% × ~−0.1% ≈ **−$590**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` — raise to **75**, AND add a family whitelist `{mean_reversion}` with `rr in [1.0, 1.5]` and `conf in [0.75, 0.80]`. The 22584/23583 (95.7%) smart-pass rate is the smoking gun — this gate is not gating.
- **Confidence (1-5):** **3** the narrow cell is real. **1** the class is tradeable.

### CRYPTO
- **Real/noise verdict:** **ONE REAL CELL, REST IS NOISE.** The `conf=C0.75-0.80 & score_dec=S50 & source=alpha_engine` cell (n=214, WR_shrunk=74.4%, PF=4.05, holdout PF=6.59, Bonferroni pass) is the strongest signal in the dataset. Holdout PF *improved* (3.17 → 6.59), which is the opposite of overfitting. **But:** the `ml` cell you flagged — I don't see it in PROVEN, which means either it didn't pass Bonferroni or it's not in the top-3. If it has PF>5 with n<50, treat it as the same small-n trap as COMMODITY. The class-level WR is 46.69% (1170W/1336L) — losing. The edge is one cell.
- **90d expected P&L (1% risk, $100k):** Trading only the proven cell: 214 × 1% × 1.44% avg = **+$3,082**. Class-wide: 2506 × 1% × ~−0.05% ≈ **−$1,250**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` — raise to **75**, AND add `source == 'alpha_engine'` as a required field for the S50 bucket. The 3183/12578 (25%) smart-pass rate is closer to sane than FOREX/COMMODITY, but the class WR says it's still too loose.
- **Confidence (1-5):** **4** the alpha_engine cell is real. **2** the class is tradeable.

### ETF
- **Real/noise verdict:** **NOISE.** n=7 closed, WR=14.29%. No PROVEN cells. Not enough data to say anything, and what data exists is bad.
- **90d expected P&L (1% risk, $100k):** **−$600** (7 × 1% × −8.6% avg). Negative.
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` — set to **999** (disable) until n>=50. Or `ETF_ENABLED = False`.
- **Confidence (1-5):** **5** it's noise. **0** it's tradeable.

### UNKNOWN
- **Real/noise verdict:** **NOISE.** n=9 closed, WR=0%. This is a data-hygiene failure, not a class. 1450 scanned, 1441 opened, 9 closed — the "UNKNOWN" bucket is where unclassified instruments go to die.
- **90d expected P&L (1% risk, $100k):** **−$900** (9 × 1% × −10% avg). Negative.
- **Gate change:** Fix the classifier upstream. `SMART_PICKS_MIN_SCORE_UNKNOWN` = **999** (disable). Do not trade unclassified instruments.
- **Confidence (1-5):** **5** it's noise. **0** it's tradeable.

### INDEX
- **Real/noise verdict:** **NOISE.** n=4 closed, WR=0%. Same as UNKNOWN.
- **90d expected P&L (1% risk, $100k):** **−$400**. Negative.
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` = **999** (disable).
- **Confidence (1-5):** **5** it's noise. **0** it's tradeable.

### FUTURES
- **Real/noise verdict:** **NOISE.** n=18 closed, WR=38.89%. No PROVEN cells. Consistent with the falsified **H-005 (futures_momentum_anti_signal)** — this class has been tested and killed before.
- **90d expected P&L (1% risk, $100k):** **−$1,100** (18 × 1% × −6.1% avg). Negative.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` = **999** (disable). Re-test only after H-005 is re-opened with a new hypothesis.
- **Confidence (1-5):** **5** it's noise. **0** it's tradeable.

### MEME
- **Real/noise verdict:** **NOISE.** n=4 closed, WR=25%. Not enough data, and what exists is bad.
- **90d expected P&L (1% risk, $100k):** **−$300**. Negative.
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME` = **999** (disable).
- **Confidence (1-5):** **5** it's noise. **0** it's tradeable.

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY with real money:** **CRYPTO, and only the `conf=C0.75-0.80 & score_dec=S50 & source=alpha_engine` cell.** It is the only cell in the entire dataset that (a) passes Bonferroni, (b) has n>=200, (c) has a holdout PF that *improves* rather than degrades, and (d) has a WR_shrunk (74.4%) that is close to its raw WR (76.6%) — meaning the shrinkage isn't doing heavy lifting. Expected 90d P&L on $100k at 1% risk: **~+$3,000.** That's a 3% quarterly return on a single cell. Size it at 1% risk, cap at 5 concurrent positions, and monitor for the holdout PF to decay below 2.0 as the kill trigger.

**Demote per MUTATION_THREE_AXIS_PROTOCOL (mutate before kill):** **FOREX.** It has one surviving cell (mean_reversion/RR1.0-1.5/conf0.75-0.80, n=138, holdout PF 1.69) that is *just* good enough to not kill outright. Mutate along three axes: (1) tighten `rr` to [1.0, 1.25], (2) add a `session` filter (London/NY overlap only), (3) require `source != 'consensus'` until the consensus cell is audited for leakage. If none of the three mutations produces a holdout PF >= 2.0 on n>=50, kill the class.

**Kill outright (no mutation):** BOND, ETF, UNKNOWN, INDEX, FUTURES, MEME. These have n<25 closed, WR<40%, and no PROVEN cells. There is nothing to mutate — there is no signal to preserve. Disable them in `production_scanner.py` and stop scanning them until you have a working model.

**Quarantine and audit (do not trade, do not kill):** EQUITY `mean_reversion` family. The 98% WR / PF=206 cell is a fill-logic bug, not an edge. Audit the exit fill path before re-enabling. If the bug is real, the "edge" disappears; if the bug is in the *reporting* only, the edge may be real but smaller. Either way, do not put money behind a 98% WR number.

**The meta-finding:** Your `passed_high_conviction` gate is returning 0 across all classes. That means either (a) the HC thresholds are miscalibrated (score>=80 is unreachable given the scoring distribution), or (b) the HC filter is not wired into the production path. Given that `opened` >> `passed_smart` in most classes, I suspect (b). **Fix the HC wiring before you do anything else** — otherwise every "edge" you scale is being traded without the one gate that was supposed to protect you.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### CRYPTO
- Real/noise verdict: Real (n=214, WR_shrunk=74.36%, PF=4.047, holdout_pass + bonferroni_pass both true; no obvious leakage flags in the listed cells).
- 90d expected P&L (1% risk, $100k): $2,900 (214 trades × 1% risk × ~1.36% expectancy after 0.2% slippage; assumes 0.5% avg slippage on crypto).
- Gate change: SMART_PICKS_MIN_SCORE_CRYPTO = 50
- Confidence (1-5): 4

### FOREX
- Real/noise verdict: Marginally real (n=138, WR_shrunk=64.56%, PF=2.781 passes holdout but one best_pf cell fails bonferroni; no consensus/ml cells present).
- 90d expected P&L (1% risk, $100k): $380 (138 trades × 1% risk × ~0.28% expectancy after 0.1% slippage).
- Gate change: HC_MIN_CONFIDENCE = 0.78
- Confidence (1-5): 3

### EQUITY
- Real/noise verdict: Sample-noise / leakage (n=65 but WR=98.46% and PF=206 with mean_reversion + S40 screams single-symbol concentration or data bug; matches pattern of previously killed equity hypotheses).
- 90d expected P&L (1% risk, $100k): -$1,100 (193 closed trades show overall negative expectancy once the anomalous cell is removed).
- Gate change: SMART_PICKS_MIN_SCORE_EQUITY = 55
- Confidence (1-5): 5

### COMMODITY
- Real/noise verdict: Noise (no proven cells; best_pf cells fail bonferroni and n=21 is too small; matches rejected COT/inventory hypotheses).
- 90d expected P&L (1% risk, $100k): -$1,400 (overall WR 44.7% on 133 closed trades).
- Gate change: SMART_PICKS_MIN_TRUST_COMMODITY = 70
- Confidence (1-5): 5

### BOND
- Real/noise verdict: No edge (n=21 total, zero proven cells).
- 90d expected P&L (1% risk, $100k): -$1,300 (WR 19%).
- Gate change: SMART_PICKS_MIN_SCORE_BOND = 60
- Confidence (1-5): 5

### ETF
- Real/noise verdict: No edge (n=7 total, zero proven cells).
- 90d expected P&L (1% risk, $100k): -$500.
- Gate change: SMART_PICKS_MIN_SCORE_ETF = 55
- Confidence (1-5): 5

### FUTURES
- Real/noise verdict: No edge (n=18 total, zero proven cells).
- 90d expected P&L (1% risk, $100k): -$700.
- Gate change: SMART_PICKS_MIN_SCORE_FUTURES = 55
- Confidence (1-5): 5

### MEME
- Real/noise verdict: No edge (n=4 total, zero proven cells).
- 90d expected P&L (1% risk, $100k): -$200.
- Gate change: SMART_PICKS_MIN_SCORE_MEME = 60
- Confidence (1-5): 5

### INDEX
- Real/noise verdict: No edge (n=4 total, zero proven cells).
- 90d expected P&L (1% risk, $100k): -$400.
- Gate change: SMART_PICKS_MIN_SCORE_INDEX = 55
- Confidence (1-5): 5

### UNKNOWN
- Real/noise verdict: No edge (n=9 total, zero proven cells).
- 90d expected P&L (1% risk, $100k): -$900.
- Gate change: SMART_PICKS_MIN_SCORE_UNKNOWN = 55
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale CRYPTO today (only class with statistically credible, holdout-validated edge). Demote EQUITY immediately per MUTATION_THREE_AXIS_PROTOCOL.md (mutate the mean_reversion + S40 path before any further capital allocation). All other classes have either insufficient n or failed statistical gates.
