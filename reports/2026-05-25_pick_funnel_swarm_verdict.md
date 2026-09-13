# Pick Funnel Swarm Verdict — 2026-09-13 04:10 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260913T040946Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-day edge analysis

Before the per-class verdicts, three structural observations that color everything below:

1. **The funnel is broken at the top.** `passed_high_conviction = 0` and `passed_proven = 0` for *every* asset class. The HC gate (score≥80, conf≥0.75, trust≥60) is firing on literally zero picks in 90 days. That means either (a) the HC thresholds are unreachable given how scores/trust are computed, or (b) the funnel is being bypassed — note `opened` ≈ `scanned` in every class (e.g. FOREX 22,262 opened from 23,649 scanned). **The "gates" are not gating.** Everything downstream is measuring the raw scanner, not the filtered product.
2. **`trust=UNK` dominates every "proven" cell.** EQUITY, FOREX, CRYPTO, COMMODITY top edges are all `trust=UNK`. A trust dimension that is unknown for the winning cohort is not a trust dimension — it's a missing-data bucket that happens to correlate with the winning strategy family. This is a red flag for either leakage or a degenerate trust computation.
3. **The EQUITY "edge" is almost certainly leakage.** 65/66 wins, PF=210, avg_pnl=+1.27%, `score_dec=S40` (a *low* score decile), `fam=mean_reversion`, `trust=UNK`. A 98.5% WR on a low-score mean-reversion bucket is the signature of a look-ahead in the exit/entry timestamp or a survivorship filter on the closed set. The three "different" cells are the same 66 trades re-sliced (identical n, wins, PF, avg_pnl) — that's not three edges, it's one cell with three aliases.

---

### EQUITY
- **Real/noise verdict:** **NOISE / LEAKAGE.** The three "proven" cells are the same 66 trades (identical n=66, wins=65, PF=210.075, avg_pnl=1.2671). PF=210 with 98.5% WR on `score_dec=S40` (lowest decile) and `trust=UNK` is not a tradeable edge — it's a data artifact. `train_pf=99` vs `holdout_pf=122.9` both absurd. `wr_z=7.877` is meaningless when the underlying P&L distribution is degenerate (likely a fixed +1.27% exit, i.e. a target-hit-only accounting bug or a look-ahead on the close). The class-level WR (67.5%, n=194) is plausible but the "proven" cells are not. **Do not trade this.**
- **90d expected P&L (1% risk, $100k):** **$0** — I would not size this. If forced to trade the class-level 67.5% WR at 1% risk with avg R:R≈1.0, expected ≈ +$3.5k gross, but the edge cells are contaminated so the honest number is **$0**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` — raise from current floor to **≥55** and add a hard `trust != UNK` requirement for any pick that can reach `passed_smart`. The S40 bucket should never have been promotable.
- **Confidence (1-5):** **1**

### BOND
- **Real/noise verdict:** **NOISE.** n=22 closed, WR=22.7%, PF<1, zero proven cells. Sample too small to conclude anything except "don't trade it." 5W/17L is a losing cohort.
- **90d expected P&L (1% risk, $100k):** **−$1.5k to −$2k** (negative edge, 22.7% WR).
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` — raise to **≥70** (effectively demote to observation-only) until n≥100 closed with WR≥50%.
- **Confidence (1-5):** **4** (confident it's noise)

### COMMODITY
- **Real/noise verdict:** **NOISE / borderline leakage recurrence.** Class WR=44.7% (losing). The "best_pf_overall" cell (`rr=RR>=2.0 & score_dec=S50`, n=21, WR=76%) has `bonferroni_pass=false`, `wr_z=2.4`, and `holdout_n=11` — that's a coin-flip sample dressed up as PF=5.6. Given [H-001] (COT leakage, 85% CT=F cotton) and [H-036] (inventory direction rejected), any COMMODITY "edge" with n<30 and no Bonferroni pass should be treated as a **leakage recurrence until proven otherwise**. The `source=alpha_engine` alias on the same 21 trades is the same red flag as EQUITY.
- **90d expected P&L (1% risk, $100k):** **−$2k to −$3k** (class-level 44.7% WR, PF<1).
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` — raise to **≥65** AND add a `min_n_for_promotion=30` guard so the 21-trade cell can't drive sizing.
- **Confidence (1-5):** **4**

### FOREX
- **Real/noise verdict:** **PLAUSIBLY REAL, but the "consensus" framing is suspect.** The `conf=C0.75-0.80 & rr=RR1.0-1.5 & fam=mean_reversion` cell: n=138, WR=66.7%, WR_shrunk=64.6%, PF=2.78, train_pf=3.19, holdout_pf=1.69, `bonferroni_pass=true`, `wr_z=3.92`. That is a **legitimate, walk-forward-stable edge** — the holdout PF dropping from 3.19→1.69 is exactly what you want to see (shrinkage, not collapse). The `dir=LONG` sub-cell (n=46, PF=4.6) does **not** pass Bonferroni and should be ignored. The `trust=UNK` alias is the same 138 trades — ignore the trust dimension. **This is the one class where the edge survives scrutiny.** Caveat: 138 trades over 90d on a mean-reversion family in FOREX is plausible but check for single-pair concentration (EURUSD/GBPUSD) — the data doesn't show it, but it's the obvious next audit.
- **90d expected P&L (1% risk, $100k):** Using the proven cell: 138 trades × 1% risk × avg_pnl 0.277% × $100k = **+$38.2k gross**. Apply 30% haircut for slippage/spread on FOREX (mean-reversion is spread-sensitive) → **+$26k to +$28k net**. If you only trade the LONG sub-cell (n=46, avg_pnl 0.479%), that's +$22k gross but Bonferroni-failed — don't.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` — **lower** to **≥50** (currently the class is over-filtered: 22,637/23,649 pass, so the floor is already near-zero; the real fix is to *add* a `conf in [0.75, 0.80] AND rr in [1.0, 1.5] AND fam=mean_reversion` allowlist). Concretely: add `FOREX_EDGE_ALLOWLIST = {"conf": (0.75, 0.80), "rr": (1.0, 1.5), "fam": "mean_reversion"}` and route only those to sizing.
- **Confidence (1-5):** **4**

### CRYPTO
- **Real/noise verdict:** **REAL, and the strongest cell in the dataset.** `conf=C0.75-0.80 & dir=LONG & score_dec=S50 & source=alpha_engine`: n=213, WR=77.0%, WR_shrunk=74.7%, PF=4.05, train_pf=3.17, holdout_pf=6.59, `bonferroni_pass=true`, `wr_z=7.88`. Holdout PF *higher* than train is unusual but not disqualifying at n=49 holdout — it means the edge is not decaying. The `source=alpha_engine` filter is doing real work (the non-alpha_engine CRYPTO cohort is presumably much worse). **This is not the "ml" cell you flagged** — the data shows `source=alpha_engine`, not `ml`. If there is an `ml` cell with PF>10 elsewhere, it's not in this payload; flag it for separate audit. The `trust=UNK` alias is the same 214 trades. **Tradeable.**
- **90d expected P&L (1% risk, $100k):** 213 trades × 1% × avg_pnl 1.451% × $100k = **+$309k gross**. CRYPTO slippage is brutal — assume 40–50% haircut on a mean-reversion-adjacent LONG book → **+$150k to +$185k net**. This is the class to scale.
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` — **lower** to **≥50** (S50 is the winning decile, so the floor should admit it) AND add `CRYPTO_EDGE_ALLOWLIST = {"conf": (0.75, 0.80), "dir": "LONG", "source": "alpha_engine"}`. The current gate is passing 3,159/12,467 (25%) but the edge lives in a much narrower slice — the gate is too loose at the top and too tight at the bottom.
- **Confidence (1-5):** **5**

### ETF
- **Real/noise verdict:** **NOISE.** n=7 closed, 1W/6L, WR=14.3%. Untradeable sample.
- **90d expected P&L (1% risk, $100k):** **−$500 to −$1k**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` — raise to **≥75** (observation-only).
- **Confidence (1-5):** **5** (confident it's noise)

### UNKNOWN
- **Real/noise verdict:** **NOISE / data hygiene failure.** n=9 closed, 0W/9L, WR=0%. The fact that 1,447 "UNKNOWN" picks were *opened* is itself the bug — the classifier is failing on ~10% of the book. Fix the classifier before trading anything in this bucket.
- **90d expected P&L (1% risk, $100k):** **−$1k** (and that's generous — 0% WR).
- **Gate change:** Add `REJECT_IF_ASSET_CLASS_UNKNOWN = True` in `quality_gates.py` — hard-drop before scoring.
- **Confidence (1-5):** **5**

### INDEX
- **Real/noise verdict:** **NOISE.** n=4 closed, 0W/4L. Untradeable.
- **90d expected P&L (1% risk, $100k):** **−$400**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` — raise to **≥75**.
- **Confidence (1-5):** **5**

### FUTURES
- **Real/noise verdict:** **NOISE.** n=18 closed, 7W/11L, WR=38.9%. Consistent with [H-005] (futures momentum anti-signal, inversion doesn't fix). No proven cells.
- **90d expected P&L (1% risk, $100k):** **−$1.5k**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` — raise to **≥70**.
- **Confidence (1-5):** **4**

### MEME
- **Real/noise verdict:** **NOISE.** n=4 closed, 1W/3L. Untradeable.
- **90d expected P&L (1% risk, $100k):** **−$300**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME` — raise to **≥80** (or disable).
- **Confidence (1-5):** **5**

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY with real money: CRYPTO.**
- Cell: `conf∈[0.75,0.80] & dir=LONG & score_dec=S50 & source=alpha_engine`
- n=213, WR_shrunk=74.7%, PF=4.05, holdout PF=6.59, Bonferroni-passed, wr_z=7.88.
- Expected 90d net at 1% risk / $100k: **+$150k to +$185k** after realistic slippage.
- Start at **0.5% risk** for the first 30 days to confirm live slippage matches the 40–50% haircut assumption, then step to 1%.

**Second allocation: FOREX** (smaller).
- Cell: `conf∈[0.75,0.80] & rr∈[1.0,1.5] & fam=mean_reversion`
- n=138, WR_shrunk=64.6%, PF=2.78, holdout PF=1.69, Bonferroni-passed.
- Expected 90d net: **+$26k to +$28k**. Size at 0.5% risk until single-pair concentration is ruled out.

**DEMOTE per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` (mutate before kill):**
- **EQUITY** — the "proven" cells are leakage (PF=210, 98.5% WR on S40/UNK). Do not kill the class; **mutate the trust computation and the score_dec mapping** first. The class-level 67.5% WR (n=194) is worth one mutation cycle. If the next 90d shows the same S40/UNK artifact, kill.
- **COMMODITY** — mutate the `rr>=2.0` cell by adding a `min_n=30` and a `source != alpha_engine` cross-check. Given [H-001] and [H-036] history, this class has a **leakage recurrence pattern**; treat any new "edge" here as guilty until proven innocent.
- **BOND, ETF, INDEX, FUTURES, MEME, UNKNOWN** — kill or observation-only. No edge, no sample, no path.

**The single most important fix is not a threshold — it's the funnel.** `passed_high_conviction=0` and `passed_proven=0` across all 10 classes means the HC gate in `hc_filter.js` is either unreachable or bypassed. Until that's fixed, every "proven" cell above is being computed on the *unfiltered* scanner output, not the product. Fix the funnel, then re-run this audit — the CRYPTO and FOREX edges will likely survive, and the EQUITY/COMMODITY artifacts will likely disappear.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### EQUITY
- Real/noise verdict: Noise/leakage — 98.48% WR and PF=210 on n=66 with 65 wins is statistically impossible in live trading; indicates single-symbol concentration or look-ahead bias in mean_reversion S40 cell.
- 90d expected P&L (1% risk, $100k): $0 (edge invalid; do not trade).
- Gate change: SMART_PICKS_MIN_SCORE_EQUITY = 65
- Confidence (1-5): 5

### BOND
- Real/noise verdict: No edge — n=22 too small, WR=22.73%, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_BOND = 80
- Confidence (1-5): 5

### COMMODITY
- Real/noise verdict: No edge — top cells fail bonferroni, n=21 marginal, WR_shrunk=63.41% but holdout unstable.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_COMMODITY = 70
- Confidence (1-5): 4

### FOREX
- Real/noise verdict: Marginally real — n=138, WR_shrunk=64.56%, PF=2.78 passes holdout/bonferroni; no obvious leakage in listed cells.
- 90d expected P&L (1% risk, $100k): ~$2,800 (assume 0.25% avg win after 0.1% slippage, ~138 trades at 1% risk).
- Gate change: hc_filter.js conf_threshold = 0.78
- Confidence (1-5): 3

### CRYPTO
- Real/noise verdict: Real but monitor — n=214, WR_shrunk=74.68%, PF=4.05 passes holdout/bonferroni; alpha_engine source cells look strong but watch for single-exchange concentration.
- 90d expected P&L (1% risk, $100k): ~$11,200 (assume 1.0% avg win after 0.2% slippage, ~214 trades at 1% risk).
- Gate change: SMART_PICKS_MIN_SCORE_CRYPTO = 55
- Confidence (1-5): 4

### ETF
- Real/noise verdict: No edge — n=7, WR=14.29%, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_ETF = 75
- Confidence (1-5): 5

### UNKNOWN
- Real/noise verdict: No edge — n=9, WR=0%, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_UNKNOWN = 80
- Confidence (1-5): 5

### INDEX
- Real/noise verdict: No edge — n=4, WR=0%, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_INDEX = 80
- Confidence (1-5): 5

### FUTURES
- Real/noise verdict: No edge — n=18 too small, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_FUTURES = 75
- Confidence (1-5): 5

### MEME
- Real/noise verdict: No edge — n=4 too small, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_MEME = 80
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale up CRYPTO today (real edge with volume and statistical passes). Demote EQUITY immediately per MUTATION_THREE_AXIS_PROTOCOL.md (mutate the mean_reversion S40 path before full kill; it is leakage).
